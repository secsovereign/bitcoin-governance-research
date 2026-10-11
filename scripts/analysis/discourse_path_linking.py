"""Path and symbol links from IRC, mail, Delving, and Bitcointalk onto pull requests.

Number matching is the existing pull-URL and #NNNN extractor. This module adds
a second linker. A message links to a pull request when it names a file path
or symbol that pull request touches and its timestamp falls between open and
close plus 14 days. Open pull requests are right-censored at the data end.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from scripts.analysis.first_year_signal_test import HASH_RE, PULL_URL_RE

DAY = 86400.0
TAIL_DAYS = 14
PATH_RE = re.compile(
    r"(?<![\w./])((?:[\w.+-]+/)*[\w.+-]+\.(?:cpp|cc|h|hpp|py|rs|md))\b",
    re.I,
)
SYMBOL_RE = re.compile(r"(?<![A-Za-z0-9_])([A-Za-z_][A-Za-z0-9_]{7,})(?![A-Za-z0-9_])")


def number_ids(text: str) -> Set[int]:
    """The existing number matcher. Pull URLs and #NNNN with 4 to 6 digits."""
    nums = {int(n) for n in PULL_URL_RE.findall(text or "")}
    nums.update(int(n) for n in HASH_RE.findall(text or ""))
    return nums


def path_mentions(text: str) -> Set[str]:
    return {m.group(1).replace("\\", "/").lower() for m in PATH_RE.finditer(text or "")}


def symbol_mentions(text: str, allowed: Set[str]) -> Set[str]:
    if not allowed or not text:
        return set()
    return {m.group(1) for m in SYMBOL_RE.finditer(text) if m.group(1) in allowed}


def pr_path_tokens(filenames: Sequence[str]) -> Set[str]:
    tokens: Set[str] = set()
    for raw in filenames:
        name = str(raw or "").replace("\\", "/").lower().lstrip("./")
        if not name or "." not in name:
            continue
        tokens.add(name)
        base = name.rsplit("/", 1)[-1]
        if len(base) >= 12:
            tokens.add(base)
    return tokens


@dataclass
class PullWindow:
    number: int
    opened: float
    closed: float
    paths: Set[str]
    symbols: Set[str] = field(default_factory=set)
    title: str = ""

    def covers(self, ts: float) -> bool:
        return self.opened <= ts <= self.closed + TAIL_DAYS * DAY


def link_message(
    text: str,
    ts: float,
    pulls: Sequence[PullWindow],
    by_token: Dict[str, List[int]],
    symbol_universe: Optional[Set[str]] = None,
) -> Tuple[Set[int], Set[int]]:
    """Return (number links, path-or-symbol links).

    Number links use the existing extractor and are not windowed.
    Path and symbol links must fall inside that pull request's window.
    """
    numbered = number_ids(text)
    hits: Set[int] = set()
    for token in path_mentions(text):
        for idx in by_token.get(token, []):
            pull = pulls[idx]
            if pull.covers(ts) and token in pull.paths:
                hits.add(pull.number)
    if symbol_universe:
        for token in symbol_mentions(text, symbol_universe):
            for idx in by_token.get(token, []):
                pull = pulls[idx]
                if pull.covers(ts) and token in pull.symbols:
                    hits.add(pull.number)
    return numbered, hits


def index_pulls(pulls: Sequence[PullWindow]) -> Dict[str, List[int]]:
    by_token: Dict[str, List[int]] = {}
    for idx, pull in enumerate(pulls):
        for token in pull.paths | pull.symbols:
            by_token.setdefault(token, []).append(idx)
    return by_token


def path_only_hits(numbered: Set[int], path_hits: Set[int]) -> Set[int]:
    """Path links that the number matcher did not already claim on this message."""
    return {n for n in path_hits if n not in numbered}


def message_links_pull(text: str, ts: float, pull: PullWindow, by_token: Dict[str, List[int]], pulls: Sequence[PullWindow], symbol_universe: Set[str]) -> bool:
    _nums, hits = link_message(text, ts, pulls, by_token, symbol_universe)
    return pull.number in hits
