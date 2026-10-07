#!/usr/bin/env python3
"""Population-level proxies for in-group filtering hypotheses.

This does not observe psychological state and does not diagnose any person.
In-group means: at time T, this author is in the top-N identities by peer
review-object volume strictly before T. People without that review history
are out-group. Unidentified (fewer than N distinct reviewers so far) is
neither group.

GitHub Review objects are missing before 2016. Headline group comparisons
use PRs created on or after 2016-01-01, once the top-N is defined.
"""

from __future__ import annotations

import argparse
import heapq
import json
import math
import re
import sys
from bisect import bisect_left, bisect_right
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.utils.findings_io import save_analysis_json
from src.utils.logger import setup_logger
from src.utils.maintainers import load_canonical_maintainers
from src.utils.paths import get_analysis_dir, get_data_dir, get_project_root

logger = setup_logger()

ERA_2016 = datetime(2016, 1, 1, tzinfo=timezone.utc).timestamp()
DAY = 86400.0
HORIZON_DAYS = {6: 182.625, 12: 365.25, 24: 730.5, 48: 1461.0}

VOCAB_NAMES = (
    "security",
    "consensus_risk",
    "conservative",
    "break_consensus",
    "nack",
    "dangerous",
)
_VOCAB_RES = (
    re.compile(r"\bsecurity\b", re.I),
    re.compile(r"\bconsensus\s+risk\b", re.I),
    re.compile(r"\bconservati(?:ve|sm)\b", re.I),
    re.compile(r"\bbreak(?:s|ing)?\s+consensus\b", re.I),
    re.compile(r"\bnack\b", re.I),
    re.compile(r"\bdangerous\b", re.I),
)
_HEDGE_RE = re.compile(
    r"\b(not a nack|would nack|removed my nack|nack/ack|ack/nack|"
    r"ack\s*/\s*nack|nack\s*/\s*ack|ready for nack)\b",
    re.I,
)
_NACK_RE = re.compile(r"\b(?:concept\s+nack|approach\s+nack|strong\s+nack|nack)\b", re.I)
_POS_RE = re.compile(
    r"\b(?:concept\s+ack|approach\s+ack|utack|tested\s+ack|lgtm|looks good)\b"
    r"|(?<![A-Za-z])ACK\b",
    re.I,
)
_OBJECTION_RE = re.compile(
    r"\b(?:security|dangerous|bug|wrong|broken|unsafe|concern|oppose|risk|fail)\b",
    re.I,
)
_APPROVAL_RE = re.compile(
    r"\b(?:ack|good|lgtm|correct|works|agree|approve|nice)\b",
    re.I,
)
_CONCEPT_RE = re.compile(
    r"\b(?:what if|should we|how about|would it make sense|thoughts on|"
    r"i think we should|proposal:|an idea|rfc:)\b",
    re.I,
)
_NEG_REPLY_RE = re.compile(
    r"\b(?:nack|disagree|dangerous|bad idea|oppose|reject|harmful|don't do|do not do)\b",
    re.I,
)
_AMB_REPLY_RE = re.compile(
    r"\b(?:maybe|not sure|unsure|perhaps|unclear|not convinced|depends|idk)\b",
    re.I,
)
_PR_TOPIC_RE = re.compile(
    r"github\.com/bitcoin/bitcoin/pull/\d+|\bpull request\b",
    re.I,
)
_TOKEN_RE = re.compile(r"[a-z][a-z0-9]{4,}")
_BOT_LOGIN_RE = re.compile(
    r"^(?:drahtbot|bitcoin-core-ai|github-actions(?:\[bot\])?)$|\[bot\]$",
    re.I,
)

TITLE_STOP = frozenset(
    {
        "bitcoin",
        "core",
        "change",
        "changes",
        "update",
        "updated",
        "fix",
        "fixed",
        "fixes",
        "test",
        "tests",
        "added",
        "using",
        "remove",
        "removed",
        "commit",
        "branch",
        "master",
        "review",
        "pull",
        "request",
        "minor",
        "small",
        "build",
        "ci",
        "doc",
        "docs",
        "script",
        "scripts",
        "refactor",
        "cleanup",
        "move",
        "make",
        "add",
        "adding",
    }
)

CANNOT_PROVE = [
    "We cannot observe psychological state. Nothing here is a diagnosis of rejection sensitive dysphoria, negativity bias, or any other trait in a person.",
    "A population difference in merge rate, tone, attrition, or vocabulary is consistent with those mechanisms and does not require them.",
    "Alternative explanations this design cannot rule out include a quality difference the proxies miss, topic selection, when the PR was opened, and structural access (who is already in the review channel).",
    "The social-filtering reading needs both an asymmetric justification vocabulary and a sentiment gap that remains after the complexity and experience strata. Either one alone is not that reading.",
    "Preemptive withdrawal is only the IRC-silence proxy defined in metric 7. This dataset cannot show who almost submitted a PR and did not.",
]

LINE_BINS = ((0, 50, "0-50 lines"), (51, 200, "51-200"), (201, 1000, "201-1000"), (1001, 10**12, "1001+"))
FILE_BINS = ((0, 1, "0-1 files"), (2, 3, "2-3 files"), (4, 10, "4-10 files"), (11, 10**12, "11+ files"))
PRIOR_BINS = ((0, 0, "0 prior PRs"), (1, 2, "1-2 prior"), (3, 10, "3-10 prior"), (11, 10**12, "11+ prior"))


def parse_ts(value: Any) -> Optional[float]:
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def is_bot_login(login: str) -> bool:
    if not login:
        return True
    low = login.lower()
    if _BOT_LOGIN_RE.search(low):
        return True
    if re.fullmatch(r"github\d+", low):
        return True
    return low.endswith("bot")


def keyword_tone(text: str) -> float:
    """Map one comment to -1, 0, or +1. Hedged NACK is not a negative stance."""
    cleaned = _HEDGE_RE.sub(" ", text or "")
    neg = bool(_NACK_RE.search(cleaned) or _NEG_REPLY_RE.search(cleaned))
    pos = bool(_POS_RE.search(cleaned))
    if neg and not pos:
        return -1.0
    if pos and not neg:
        return 1.0
    if neg and pos:
        return -1.0
    objections = len(_OBJECTION_RE.findall(cleaned))
    approvals = len(_APPROVAL_RE.findall(cleaned))
    if objections > approvals and objections >= 2:
        return -1.0
    if approvals > objections and approvals >= 2:
        return 1.0
    return 0.0


def review_tone(review: Dict[str, Any]) -> float:
    if review.get("is_nack"):
        return -1.0
    existing = str(review.get("sentiment") or "").lower()
    if existing in {"positive", "neutral", "negative"}:
        return {"positive": 1.0, "neutral": 0.0, "negative": -1.0}[existing]
    state = str(review.get("state") or "").upper()
    if state == "APPROVED":
        return 1.0
    if state == "CHANGES_REQUESTED":
        return -1.0
    body = review.get("body") or ""
    if not str(body).strip():
        return 0.0
    return keyword_tone(str(body))


def vocab_counts(text: str) -> List[int]:
    cleaned = _HEDGE_RE.sub(" ", text or "")
    return [len(rx.findall(cleaned)) for rx in _VOCAB_RES]


def title_tokens(title: str) -> Tuple[str, ...]:
    seen = []
    for tok in _TOKEN_RE.findall((title or "").lower()):
        if tok in TITLE_STOP or tok in seen:
            continue
        seen.append(tok)
        if len(seen) >= 12:
            break
    return tuple(seen)


def cohens_d(a: np.ndarray, b: np.ndarray) -> Optional[float]:
    aa = np.asarray(a, dtype=float)
    bb = np.asarray(b, dtype=float)
    aa = aa[np.isfinite(aa)]
    bb = bb[np.isfinite(bb)]
    if aa.size < 2 or bb.size < 2:
        return None
    va = float(aa.var(ddof=1))
    vb = float(bb.var(ddof=1))
    pooled = math.sqrt(((aa.size - 1) * va + (bb.size - 1) * vb) / (aa.size + bb.size - 2))
    if pooled == 0:
        return 0.0
    return float((aa.mean() - bb.mean()) / pooled)


def effect_flag(d: Optional[float]) -> str:
    if d is None or not math.isfinite(d):
        return "effect size unavailable"
    mag = abs(d)
    if mag < 0.2:
        return "negligible effect size regardless of p-value"
    if mag < 0.5:
        return "small"
    if mag < 0.8:
        return "medium"
    return "large"


def walk_ingroup(
    review_events: Sequence[Tuple[float, str]],
    query_ts: Sequence[float],
    query_author: Sequence[str],
    top_n: int,
) -> Tuple[List[Optional[bool]], Dict[str, float], List[str], int]:
    """In-group at T uses peer review volume strictly before T.

    Returns flags (True/False/None), first query-time each identity is seen
    inside a defined top-N, the final top-N, and distinct reviewer count.
    None means fewer than top_n distinct reviewers exist yet (unidentified).
    Ties at the cutoff break by identity string descending so the set size is
    exactly top_n once enough reviewers exist.
    """
    reviews = sorted(review_events, key=lambda row: row[0])
    order = sorted(range(len(query_ts)), key=lambda i: query_ts[i])
    counts: Dict[str, int] = {}
    ri = 0
    flags: List[Optional[bool]] = [None] * len(query_ts)
    first_entry: Dict[str, float] = {}
    top: set[str] = set()
    for qi in order:
        ts = query_ts[qi]
        dirty = False
        while ri < len(reviews) and reviews[ri][0] < ts:
            who = reviews[ri][1]
            counts[who] = counts.get(who, 0) + 1
            ri += 1
            dirty = True
        if dirty or not top:
            if len(counts) >= top_n:
                top = set(heapq.nlargest(top_n, counts, key=lambda k: (counts[k], k)))
                for member in top:
                    first_entry.setdefault(member, ts)
            else:
                top = set()
        if len(counts) < top_n:
            flags[qi] = None
        else:
            flags[qi] = query_author[qi] in top
    if len(counts) >= top_n:
        final = list(heapq.nlargest(top_n, counts, key=lambda k: (counts[k], k)))
    else:
        final = []
    return flags, first_entry, final, len(counts)


def _finite(arr: np.ndarray) -> np.ndarray:
    out = np.asarray(arr, dtype=float)
    return out[np.isfinite(out)]


def boot_mean(arr: np.ndarray, rng: np.random.Generator, n_boot: int) -> Optional[Dict[str, Any]]:
    clean = _finite(arr)
    n = int(clean.size)
    if n == 0:
        return None
    est = float(clean.mean())
    if n == 1 or n_boot <= 0:
        return {"n": n, "estimate": est, "ci95": [est, est]}
    idx = rng.integers(0, n, size=(n_boot, n))
    means = clean[idx].mean(axis=1)
    lo, hi = np.quantile(means, [0.025, 0.975])
    return {"n": n, "estimate": est, "ci95": [float(lo), float(hi)]}


def compare(
    in_vals: np.ndarray,
    out_vals: np.ndarray,
    rng: np.random.Generator,
    n_boot: int,
    kind: str,
) -> Dict[str, Any]:
    aa = _finite(in_vals)
    bb = _finite(out_vals)
    d = cohens_d(aa, bb)
    diff = None
    if aa.size and bb.size:
        est = float(aa.mean() - bb.mean())
        if aa.size >= 2 and bb.size >= 2 and n_boot > 0:
            ia = rng.integers(0, aa.size, size=(n_boot, aa.size))
            ib = rng.integers(0, bb.size, size=(n_boot, bb.size))
            deltas = aa[ia].mean(axis=1) - bb[ib].mean(axis=1)
            lo, hi = np.quantile(deltas, [0.025, 0.975])
            diff = {"estimate": est, "ci95": [float(lo), float(hi)]}
        else:
            diff = {"estimate": est, "ci95": [est, est]}
    return {
        "kind": kind,
        "in_group": boot_mean(aa, rng, n_boot),
        "out_group": boot_mean(bb, rng, n_boot),
        "difference_in_minus_out": diff,
        "cohens_d": None if d is None else float(d),
        "effect_size_flag": effect_flag(d),
    }


def bin_index(value: float, bins: Sequence[Tuple[float, float, str]]) -> int:
    for i, (lo, hi, _label) in enumerate(bins):
        if lo <= value <= hi:
            return i
    return len(bins) - 1


def weighted_gap(rows: Sequence[Dict[str, Any]]) -> Optional[float]:
    num = 0.0
    den = 0.0
    for row in rows:
        if not row.get("usable"):
            continue
        gap = row["estimate_in"] - row["estimate_out"]
        w = min(row["n_in"], row["n_out"])
        num += w * gap
        den += w
    if den <= 0:
        return None
    return num / den


def stratify(
    mask: np.ndarray,
    group: np.ndarray,
    values: np.ndarray,
    labels_arr: np.ndarray,
    bins: Sequence[Tuple[float, float, str]],
    rng: np.random.Generator,
    n_boot: int,
    kind: str,
) -> Dict[str, Any]:
    rows = []
    for i, (_lo, _hi, label) in enumerate(bins):
        in_m = mask & (group == 1) & (labels_arr == i)
        out_m = mask & (group == 0) & (labels_arr == i)
        comp = compare(values[in_m], values[out_m], rng, n_boot, kind)
        n_in = 0 if comp["in_group"] is None else comp["in_group"]["n"]
        n_out = 0 if comp["out_group"] is None else comp["out_group"]["n"]
        usable = n_in >= 30 and n_out >= 30 and comp["difference_in_minus_out"] is not None
        est_in = None if comp["in_group"] is None else comp["in_group"]["estimate"]
        est_out = None if comp["out_group"] is None else comp["out_group"]["estimate"]
        rows.append(
            {
                "stratum": label,
                "usable": usable,
                "n_in": n_in,
                "n_out": n_out,
                "estimate_in": est_in,
                "estimate_out": est_out,
                "comparison": comp,
            }
        )
    return {"strata": rows, "weighted_gap": weighted_gap(rows), "n_usable_strata": sum(1 for r in rows if r["usable"])}


def gap_persists(raw_diff: Optional[float], raw_d: Optional[float], weighted: Optional[float], n_usable: int) -> Dict[str, Any]:
    """A gap persists when it was not already negligible and the strata keep at least half of it."""
    if raw_diff is None or weighted is None or n_usable < 2:
        return {"persists": False, "reason": "underpowered or undefined", "weighted_gap": weighted}
    if raw_d is None or abs(raw_d) < 0.2:
        return {
            "persists": False,
            "reason": "raw effect size already negligible (d < 0.2)",
            "weighted_gap": weighted,
        }
    same_sign = raw_diff * weighted > 0
    keeps_half = abs(weighted) >= 0.5 * abs(raw_diff)
    return {
        "persists": bool(same_sign and keeps_half),
        "reason": "same sign and at least half the raw gap remains inside strata" if same_sign and keeps_half else "strata remove or shrink the gap",
        "weighted_gap": weighted,
        "raw_gap": raw_diff,
    }


def shrinks_substantially(raw_diff: Optional[float], weighted: Optional[float], n_usable: int) -> Optional[bool]:
    if raw_diff is None or weighted is None or n_usable < 2 or abs(raw_diff) < 1e-12:
        return None
    return abs(weighted) <= 0.5 * abs(raw_diff)


class IdentityIndex:
    def __init__(self) -> None:
        self.source = "login string only"
        self.gh: Dict[str, str] = {}
        self.irc: Dict[str, str] = {}
        self.aliases: Dict[str, str] = {}
        self.nick_aliases: Dict[str, str] = {}
        self.uid_login: Dict[str, str] = {}
        self.notes: List[str] = []

    def ident(self, login: str, *, irc: bool = False) -> str:
        raw = (login or "").strip().lower()
        if not raw or is_bot_login(raw):
            return ""
        if irc:
            raw = self.nick_aliases.get(raw, raw)
            canon = self.aliases.get(raw, raw)
            # Same login string joins GitHub and IRC even when the resolver
            # stored two ids. A resolver uid is used only if it is already a
            # GitHub id, or the nick is not a GitHub login at all.
            # nick_aliases are informal nicks only. GitHub logins are not run
            # through that map, so TheCharlatan and sedited stay distinct there.
            gh_uid = self.gh.get(canon) or self.gh.get(raw)
            if gh_uid:
                return gh_uid
            if raw in self.irc:
                return self.irc[raw]
            if canon in self.irc:
                return self.irc[canon]
        canon = self.aliases.get(raw, raw)
        return self.gh.get(canon) or self.gh.get(raw) or f"gh:{canon}"

    def label(self, ident: str) -> str:
        return self.uid_login.get(ident, ident)


def load_identity() -> IdentityIndex:
    idx = IdentityIndex()
    doc = load_canonical_maintainers()
    idx.aliases = {str(k).strip().lower(): str(v).strip().lower() for k, v in (doc.get("aliases") or {}).items()}
    idx.nick_aliases = {
        str(k).strip().lower(): str(v).strip().lower() for k, v in (doc.get("nick_aliases") or {}).items()
    }
    path = get_analysis_dir() / "user_identities" / "identity_mappings.json"
    enhanced = get_project_root() / "findings" / "data" / "enhanced_identity_resolution.json"
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        gh = payload.get("github_to_unified") or {}
        irc = payload.get("irc_to_unified") or {}
        for login, uid in gh.items():
            key = str(login).strip().lower()
            uid_s = str(uid)
            idx.gh.setdefault(key, uid_s)
            prev = idx.uid_login.get(uid_s)
            if prev is None or len(key) < len(prev):
                idx.uid_login[uid_s] = key
        for nick, uid in irc.items():
            idx.irc.setdefault(str(nick).strip().lower(), str(uid))
        idx.source = str(path.relative_to(get_project_root()))
        idx.notes.append(
            "Join table is analysis/user_identities/identity_mappings.json "
            f"({len(idx.gh)} GitHub logins, {len(idx.irc)} IRC nicks). "
            "findings/data/enhanced_identity_resolution.json is a short manual alias list, not a per-login map, so it is not the join."
        )
    elif enhanced.exists():
        idx.source = str(enhanced.relative_to(get_project_root()))
        idx.notes.append("Full identity_mappings.json missing; GitHub logins stay as gh:<login>. IRC match will be weak.")
    else:
        idx.notes.append("No identity file found. GitHub login strings are the identity. IRC metrics will say so.")
    return idx


def resolve_pr_path(data_dir: Path) -> Tuple[Path, str]:
    enriched = data_dir / "processed" / "enriched_prs.jsonl"
    raw = data_dir / "github" / "prs_raw.jsonl"
    if enriched.exists():
        return enriched, "processed/enriched_prs.jsonl"
    if raw.exists():
        return raw, "github/prs_raw.jsonl FALLBACK (enriched_prs.jsonl missing; review sentiment uses the keyword heuristic)"
    raise FileNotFoundError(f"No PR file at {enriched} or {raw}")


def _actor(obj: Dict[str, Any]) -> str:
    return str(obj.get("author") or obj.get("user") or "")


def load_prs(path: Path, ident: IdentityIndex) -> Dict[str, Any]:
    authors: List[str] = []
    created: List[float] = []
    outcome: List[int] = []
    lines: List[int] = []
    files: List[int] = []
    draft: List[int] = []
    cycles: List[int] = []
    comments_n: List[int] = []
    sentiment: List[float] = []
    negative: List[float] = []
    sent_source: List[int] = []
    response_h: List[float] = []
    decision_h: List[float] = []
    first_tone: List[float] = []
    first_ts: List[float] = []
    vocab_rows: List[List[int]] = []
    tokens: List[Tuple[str, ...]] = []
    review_events: List[Tuple[float, str]] = []
    saw_request = False
    saw_draft_ts = False
    n_read = 0

    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            pr = json.loads(line)
            n_read += 1
            author = ident.ident(_actor(pr))
            ts = parse_ts(pr.get("created_at"))
            if not author or ts is None:
                continue
            if any(k in pr for k in ("requested_reviewers", "requested_reviewers_count", "review_requests")):
                saw_request = True
            if any(k in pr for k in ("ready_for_review_at", "draft_created_at", "converted_from_draft_at")):
                saw_draft_ts = True

            merged = bool(pr.get("merged"))
            state = str(pr.get("state") or "").lower()
            if merged:
                code = 1
                end = parse_ts(pr.get("merged_at")) or parse_ts(pr.get("closed_at"))
            elif state == "open":
                code = -1
                end = None
            else:
                code = 0
                end = parse_ts(pr.get("closed_at"))

            comp = pr.get("complexity") or {}
            n_lines = int(comp.get("total_changes") or (pr.get("total_additions") or 0) + (pr.get("total_deletions") or 0) or 0)
            n_files = int(comp.get("files_changed") or pr.get("total_files_changed") or len(pr.get("files") or []) or 0)

            review_scores: List[float] = []
            comment_scores: List[float] = []
            vocab = [0, 0, 0, 0, 0, 0]
            earliest: Optional[float] = None
            earliest_tone = math.nan
            n_cycles = 0
            n_peer_comments = 0

            def _bump_vocab(text: str) -> None:
                counts = vocab_counts(text)
                for i, c in enumerate(counts):
                    vocab[i] += c

            def _see(when: Optional[float], tone: float) -> None:
                nonlocal earliest, earliest_tone
                if when is None:
                    return
                if earliest is None or when < earliest:
                    earliest = when
                    earliest_tone = tone

            for rev in pr.get("reviews") or []:
                if not isinstance(rev, dict):
                    continue
                reviewer = ident.ident(_actor(rev))
                if not reviewer or reviewer == author:
                    continue
                when = parse_ts(rev.get("submitted_at") or rev.get("created_at"))
                if when is not None:
                    review_events.append((when, reviewer))
                tone = review_tone(rev)
                review_scores.append(tone)
                n_cycles += 1
                _see(when, tone)
                _bump_vocab(str(rev.get("body") or ""))

            for rc in pr.get("review_comments") or []:
                if not isinstance(rc, dict):
                    continue
                who = ident.ident(_actor(rc))
                if not who or who == author:
                    continue
                _bump_vocab(str(rc.get("body") or ""))
                when = parse_ts(rc.get("created_at"))
                tone = keyword_tone(str(rc.get("body") or ""))
                comment_scores.append(tone)
                n_peer_comments += 1
                _see(when, tone)

            for cmt in pr.get("comments") or []:
                if not isinstance(cmt, dict):
                    continue
                who = ident.ident(_actor(cmt))
                if not who or who == author:
                    continue
                _bump_vocab(str(cmt.get("body") or ""))
                when = parse_ts(cmt.get("created_at"))
                tone = keyword_tone(str(cmt.get("body") or ""))
                comment_scores.append(tone)
                n_peer_comments += 1
                _see(when, tone)

            if review_scores:
                sent = float(np.mean(review_scores))
                neg = 1.0 if any(s < 0 for s in review_scores) else 0.0
                src = 1
            elif comment_scores:
                sent = float(np.mean(comment_scores))
                neg = 1.0 if any(s < 0 for s in comment_scores) else 0.0
                src = 2
            else:
                sent = math.nan
                neg = math.nan
                src = 0

            authors.append(author)
            created.append(ts)
            outcome.append(code)
            lines.append(n_lines)
            files.append(max(n_files, 0))
            draft.append(1 if pr.get("draft") else 0)
            cycles.append(n_cycles)
            comments_n.append(n_peer_comments)
            sentiment.append(sent)
            negative.append(neg)
            sent_source.append(src)
            if earliest is None:
                response_h.append(math.nan)
                first_ts.append(math.nan)
                first_tone.append(math.nan)
            else:
                response_h.append(max(0.0, (earliest - ts) / 3600.0))
                first_ts.append(earliest)
                first_tone.append(earliest_tone)
            if end is None:
                decision_h.append(math.nan)
            else:
                decision_h.append(max(0.0, (end - ts) / 3600.0))
            vocab_rows.append(vocab)
            tokens.append(title_tokens(str(pr.get("title") or "")))
            if n_read % 5000 == 0:
                logger.info("Read %s PR rows", n_read)

    n = len(authors)
    created_a = np.asarray(created, dtype=float)
    order = np.argsort(created_a, kind="mergesort")
    # prior PR count in author history
    prior = np.zeros(n, dtype=np.int32)
    by_author: Dict[str, List[int]] = defaultdict(list)
    for i, author in enumerate(authors):
        by_author[author].append(i)
    for idxs in by_author.values():
        idxs.sort(key=lambda i: created_a[i])
        for k, i in enumerate(idxs):
            prior[i] = k

    return {
        "n_rows_read": n_read,
        "authors": authors,
        "by_author": by_author,
        "created": created_a,
        "outcome": np.asarray(outcome, dtype=np.int8),
        "lines": np.asarray(lines, dtype=np.int32),
        "files": np.asarray(files, dtype=np.int32),
        "draft": np.asarray(draft, dtype=np.int8),
        "cycles": np.asarray(cycles, dtype=np.int32),
        "comments_n": np.asarray(comments_n, dtype=np.int32),
        "sentiment": np.asarray(sentiment, dtype=float),
        "negative": np.asarray(negative, dtype=float),
        "sent_source": np.asarray(sent_source, dtype=np.int8),
        "response_h": np.asarray(response_h, dtype=float),
        "decision_h": np.asarray(decision_h, dtype=float),
        "first_tone": np.asarray(first_tone, dtype=float),
        "first_ts": np.asarray(first_ts, dtype=float),
        "vocab": np.asarray(vocab_rows, dtype=np.int32),
        "tokens": tokens,
        "prior": prior,
        "review_events": review_events,
        "saw_request": saw_request,
        "saw_draft_ts": saw_draft_ts,
        "author_order_hint": order,
    }


def _dev_channel(name: str) -> bool:
    return "bitcoin" in (name or "").lower()


def load_irc(data_dir: Path, ident: IdentityIndex) -> Dict[str, Any]:
    path = data_dir / "irc" / "messages.jsonl"
    source = "irc/messages.jsonl"
    if not path.exists():
        alt = data_dir / "processed" / "cleaned_irc.jsonl"
        if not alt.exists():
            return {"available": False, "reason": f"No IRC file at {path} or {alt}", "source": source}
        path = alt
        source = "processed/cleaned_irc.jsonl"
    rows: List[Tuple[float, str, str, str, str]] = []
    channels: Dict[str, int] = defaultdict(int)
    with path.open(encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            if not line.strip():
                continue
            msg = json.loads(line)
            nick = str(msg.get("nickname") or msg.get("author") or "").strip().lower()
            if not nick or is_bot_login(nick):
                continue
            ts = parse_ts(msg.get("timestamp"))
            if ts is None:
                continue
            channel = str(msg.get("channel") or "")
            channels[channel] += 1
            text = str(msg.get("message") or msg.get("content") or "")[:2000]
            who = ident.ident(nick, irc=True)
            if not who:
                continue
            rows.append((ts, nick, who, channel, text))
            if (i + 1) % 100000 == 0:
                logger.info("Read %s IRC lines", i + 1)
    use_filter = any(_dev_channel(name) for name in channels)
    if use_filter:
        rows = [r for r in rows if _dev_channel(r[3])]
    rows.sort(key=lambda r: (r[3], r[0]))
    by_ident: Dict[str, List[Tuple[float, str]]] = defaultdict(list)
    for ts, _nick, who, _ch, text in rows:
        by_ident[who].append((ts, text))
    for who in by_ident:
        by_ident[who].sort(key=lambda item: item[0])
    return {
        "available": True,
        "source": source,
        "reason": "",
        "rows": rows,
        "by_ident": by_ident,
        "channels": dict(channels),
        "filtered_to_bitcoin_channels": use_filter,
        "n_messages": len(rows),
    }


def attach_preface(prs: Dict[str, Any], irc: Dict[str, Any]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    n = len(prs["authors"])
    resolved = np.zeros(n, dtype=np.int8)
    present = np.zeros(n, dtype=np.int8)
    prefaced = np.zeros(n, dtype=np.int8)
    if not irc.get("available"):
        return resolved, present, prefaced
    by_ident: Dict[str, List[Tuple[float, str]]] = irc["by_ident"]
    irc_idents = set(by_ident)
    for i, author in enumerate(prs["authors"]):
        series = by_ident.get(author)
        if not series:
            continue
        resolved[i] = 1
        created = float(prs["created"][i])
        times = [item[0] for item in series]
        lo = bisect_left(times, created - 2 * DAY)
        hi = bisect_left(times, created)
        if lo >= hi:
            continue
        present[i] = 1
        toks = prs["tokens"][i]
        hit = False
        for ts, text in series[lo:hi]:
            low = text.lower()
            if _PR_TOPIC_RE.search(low) or any(tok in low for tok in toks):
                hit = True
                break
        if hit:
            prefaced[i] = 1
    # authors with an identity that never speaks still unresolved (resolved means we saw the ident in IRC)
    _ = irc_idents
    return resolved, present, prefaced


def concept_silence(irc: Dict[str, Any], prs: Dict[str, Any], ever_in: set[str], dataset_end: float) -> Dict[str, Any]:
    """Weak proxy: concept line, negative or ambiguous reply, then gone through day 90."""
    if not irc.get("available"):
        return {"available": False, "reason": irc.get("reason") or "IRC missing", "weak_proxy": True}
    rows: List[Tuple[float, str, str, str, str]] = irc["rows"]
    pr_times: Dict[str, List[float]] = defaultdict(list)
    for author, ts in zip(prs["authors"], prs["created"]):
        pr_times[author].append(float(ts))
    for who in pr_times:
        pr_times[who].sort()
    msg_times: Dict[str, List[float]] = {
        who: [item[0] for item in series] for who, series in irc["by_ident"].items()
    }

    events = []
    i = 0
    n = len(rows)
    while i < n:
        j = i + 1
        while j < n and rows[j][3] == rows[i][3]:
            j += 1
        block = rows[i:j]
        for k, (ts, nick, who, _ch, text) in enumerate(block):
            if len(text) < 40 or not _CONCEPT_RE.search(text):
                continue
            reply = None
            for m in range(k + 1, min(k + 25, len(block))):
                rts, rnick, rwho, _rch, rtext = block[m]
                if rts > ts + 2 * 3600:
                    break
                if rwho == who:
                    continue
                mentioned = bool(re.search(rf"\b{re.escape(nick)}\b", rtext, re.I)) if len(nick) >= 3 else False
                near = m <= k + 8
                if not (mentioned or near):
                    continue
                if _NEG_REPLY_RE.search(rtext):
                    reply = (rts, "negative")
                    break
                if _AMB_REPLY_RE.search(rtext):
                    reply = (rts, "ambiguous")
                    break
            if reply is None:
                continue
            rts, kind = reply
            if dataset_end < rts + 90 * DAY:
                events.append({"who": who, "kind": kind, "censored": True, "silent": False})
                continue
            times = msg_times.get(who, [])
            after = bisect_right(times, rts)
            late = False
            if after < len(times):
                for t in times[after:]:
                    if t > rts + 90 * DAY:
                        break
                    if t > rts + 14 * DAY:
                        late = True
                        break
            ptimes = pr_times.get(who, [])
            p_at = bisect_right(ptimes, rts)
            pr_within = p_at < len(ptimes) and ptimes[p_at] <= rts + 90 * DAY
            events.append(
                {
                    "who": who,
                    "kind": kind,
                    "censored": False,
                    "silent": (not pr_within) and (not late),
                    "rts": rts,
                }
            )
        i = j

    uncensored = [e for e in events if not e["censored"]]
    latest: Dict[str, Dict[str, Any]] = {}
    for e in uncensored:
        prev = latest.get(e["who"])
        if prev is None or e["rts"] >= prev["rts"]:
            latest[e["who"]] = e
    people = {who: bool(e["silent"]) for who, e in latest.items()}
    def _class(who: str) -> str:
        if who in ever_in:
            return "ever_ingroup"
        if who in pr_times:
            return "pr_author_never_ingroup"
        return "no_pr"

    by_class: Dict[str, List[int]] = defaultdict(list)
    for who, silent in people.items():
        by_class[_class(who)].append(1 if silent else 0)

    discussants = set(irc["by_ident"])
    submitted = discussants & set(pr_times)
    return {
        "available": True,
        "weak_proxy": True,
        "reason": "",
        "rule": (
            "Weak proxy. A concept-like IRC line (explicit idea phrasing, length >= 40) "
            "gets a negative or ambiguous reply in the same channel within 2 hours "
            "(nick mention, or one of the next 8 messages). The speaker then has no PR "
            "in the next 90 days and no IRC message after day 14 through day 90. "
            "Speech inside the first 14 days is allowed. Events still inside the log's "
            "last 90 days are censored. This is not observed preemptive withdrawal."
        ),
        "n_response_events_uncensored": len(uncensored),
        "n_response_events_censored": sum(1 for e in events if e["censored"]),
        "n_silent_events": sum(1 for e in uncensored if e["silent"]),
        "n_people": len(people),
        "n_people_silent": sum(1 for v in people.values() if v),
        "by_class_silent_flags": {k: v for k, v in by_class.items()},
        "n_irc_discussants": len(discussants),
        "n_irc_and_pr": len(submitted),
        "n_irc_never_pr": len(discussants - set(pr_times)),
    }


def _mask_vals(mask: np.ndarray, group: np.ndarray, which: int, values: np.ndarray) -> np.ndarray:
    return values[mask & (group == which)]


def _record_pair(
    name: str,
    mask: np.ndarray,
    group: np.ndarray,
    values: np.ndarray,
    rng: np.random.Generator,
    n_boot: int,
    kind: str,
    notes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    comp = compare(_mask_vals(mask, group, 1, values), _mask_vals(mask, group, 0, values), rng, n_boot, kind)
    return {"name": name, "comparison": comp, "notes": notes or []}


def _diff(comp: Dict[str, Any]) -> Optional[float]:
    block = comp.get("difference_in_minus_out") or {}
    return block.get("estimate")


def _d(comp: Dict[str, Any]) -> Optional[float]:
    return comp.get("cohens_d")


def analyze(top_n: int = 20, n_boot: int = 1000, seed: int = 7) -> Dict[str, Any]:
    rng = np.random.default_rng(seed)
    data_dir = get_data_dir()
    ident = load_identity()
    pr_path, pr_source = resolve_pr_path(data_dir)
    logger.info("Loading PRs from %s", pr_path)
    prs = load_prs(pr_path, ident)
    logger.info("Assigning time-varying top-%s", top_n)
    flags, first_entry, final_top, n_reviewers = walk_ingroup(
        prs["review_events"],
        prs["created"].tolist(),
        prs["authors"],
        top_n,
    )
    n = len(prs["authors"])
    group = np.full(n, -1, dtype=np.int8)
    for i, flag in enumerate(flags):
        if flag is True:
            group[i] = 1
        elif flag is False:
            group[i] = 0
    defined = group >= 0
    from_2016 = prs["created"] >= ERA_2016
    primary = defined & from_2016
    decided = prs["outcome"] >= 0
    merge = np.full(n, np.nan)
    merge[prs["outcome"] == 1] = 1.0
    merge[prs["outcome"] == 0] = 0.0

    logger.info("Loading IRC")
    irc = load_irc(data_dir, ident)
    resolved, present, prefaced = attach_preface(prs, irc)
    ever_in = set(first_entry)
    dataset_end = float(prs["created"].max()) if n else 0.0
    logger.info("Scoring IRC concept-silence proxy")
    silence = concept_silence(irc, prs, ever_in, dataset_end)

    # identity match: PR authors who appear in the IRC ident set
    irc_idents = set(irc["by_ident"]) if irc.get("available") else set()
    author_set = set(prs["authors"])
    matched_authors = author_set & irc_idents
    match_rate = (len(matched_authors) / len(author_set)) if author_set else 0.0
    irc_uncertain = (not irc.get("available")) or match_rate < 0.60

    # circularity at the final snapshot
    submit_counts: Dict[str, int] = defaultdict(int)
    for author in prs["authors"]:
        submit_counts[author] += 1
    top_submitters = [a for a, _c in sorted(submit_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:top_n]]
    overlap_n = len(set(final_top) & set(top_submitters))
    overlap = (overlap_n / top_n) if top_n else None

    defined_times = prs["created"][defined]
    defined_from = float(defined_times.min()) if defined_times.size else None

    notes_common = [
        "In-group is time-varying: top-N by cumulative peer GitHub review objects with submitted_at < PR created_at. "
        "Self-reviews and bots are excluded. Ties break by identity string descending.",
        "Before N distinct reviewers exist, group is unidentified and those PRs are left out of group comparisons, not dumped into out-group.",
        "Headline windows are PRs created on or after 2016-01-01. Earlier review-object counts are an API hole.",
        "Bootstrap is the percentile interval of the analysis unit (PR or contributor), 95%, independent resamples. It is not clustered on reviewer.",
    ]

    m_merge = _record_pair(
        "merge_rate_decided_from_2016",
        primary & decided,
        group,
        merge,
        rng,
        n_boot,
        "rate",
        ["Open PRs are excluded (not yet a rejection)."],
    )
    m_merge_all = _record_pair(
        "merge_rate_decided_wherever_group_defined",
        defined & decided,
        group,
        merge,
        rng,
        n_boot,
        "rate",
        ["Includes pre-2016 once the top-N exists. Prefer the 2016+ row."],
    )
    m_sent = _record_pair(
        "mean_review_sentiment_from_2016",
        primary,
        group,
        prs["sentiment"],
        rng,
        n_boot,
        "score",
        [
            "PR-level mean. Uses peer review-object sentiment when any exist (enriched labels, else keywords). "
            "Otherwise peer issue/line comments. +1 positive, 0 neutral, -1 negative. Author and bots excluded."
        ],
    )
    m_neg = _record_pair(
        "any_negative_tone_rate_from_2016",
        primary,
        group,
        prs["negative"],
        rng,
        n_boot,
        "rate",
        ["Share of PRs whose scored peer texts include at least one negative tone. The mean can hide a rare negative tail."],
    )
    m_speed = _record_pair(
        "hours_to_first_peer_response_from_2016",
        primary,
        group,
        prs["response_h"],
        rng,
        n_boot,
        "hours",
        ["First peer review object, else first peer comment. PRs with no peer response are excluded here and reported as a rate."],
    )
    no_response = np.isnan(prs["response_h"]).astype(float)
    m_noresp = _record_pair(
        "no_peer_response_rate_from_2016",
        primary,
        group,
        no_response,
        rng,
        n_boot,
        "rate",
    )
    m_decision = _record_pair(
        "hours_to_merge_or_close_from_2016",
        primary & decided,
        group,
        prs["decision_h"],
        rng,
        n_boot,
        "hours",
    )
    m_cycles = _record_pair(
        "peer_review_object_count_from_2016",
        primary,
        group,
        prs["cycles"].astype(float),
        rng,
        n_boot,
        "count",
        ["Count of peer GitHub review objects. Pre-2016 this is mostly zero because the Reviews API is absent; this row is 2016+."],
    )
    vocab_total = prs["vocab"].sum(axis=1).astype(float)
    m_vocab = _record_pair(
        "justification_hits_per_pr_from_2016",
        primary,
        group,
        vocab_total,
        rng,
        n_boot,
        "count",
        [
            "Sum of appearances of security, consensus risk, conservative/conservatism, break(s/ing) consensus, NACK, dangerous "
            "in peer review bodies, line comments, and issue comments. Hedged 'not a NACK' is removed before the NACK count. "
            "Normalized by PR (zeros included)."
        ],
    )
    vocab_terms = {}
    for j, name in enumerate(VOCAB_NAMES):
        vocab_terms[name] = compare(
            _mask_vals(primary, group, 1, prs["vocab"][:, j].astype(float)),
            _mask_vals(primary, group, 0, prs["vocab"][:, j].astype(float)),
            rng,
            n_boot,
            "count",
        )

    # quality strata
    line_lab = np.array([bin_index(int(v), LINE_BINS) for v in prs["lines"]], dtype=np.int8)
    file_lab = np.array([bin_index(int(v), FILE_BINS) for v in prs["files"]], dtype=np.int8)
    prior_lab = np.array([bin_index(int(v), PRIOR_BINS) for v in prs["prior"]], dtype=np.int8)
    base_mask = primary & decided
    strat_merge_lines = stratify(base_mask, group, merge, line_lab, LINE_BINS, rng, n_boot, "rate")
    strat_sent_lines = stratify(primary, group, prs["sentiment"], line_lab, LINE_BINS, rng, n_boot, "score")
    strat_merge_files = stratify(base_mask, group, merge, file_lab, FILE_BINS, rng, n_boot, "rate")
    strat_sent_files = stratify(primary, group, prs["sentiment"], file_lab, FILE_BINS, rng, n_boot, "score")
    strat_merge_prior = stratify(base_mask, group, merge, prior_lab, PRIOR_BINS, rng, n_boot, "rate")
    strat_sent_prior = stratify(primary, group, prs["sentiment"], prior_lab, PRIOR_BINS, rng, n_boot, "score")
    persist_sent_lines = gap_persists(_diff(m_sent["comparison"]), _d(m_sent["comparison"]), strat_sent_lines["weighted_gap"], strat_sent_lines["n_usable_strata"])
    persist_merge_lines = gap_persists(_diff(m_merge["comparison"]), _d(m_merge["comparison"]), strat_merge_lines["weighted_gap"], strat_merge_lines["n_usable_strata"])
    shrink_sent_lines = shrinks_substantially(_diff(m_sent["comparison"]), strat_sent_lines["weighted_gap"], strat_sent_lines["n_usable_strata"])

    # attrition: first neutral/negative peer response
    attr_in: List[float] = []
    attr_out: List[float] = []
    attr_in_neg: List[float] = []
    attr_out_neg: List[float] = []
    attr_skipped_unidentified = 0
    attr_skipped_positive = 0
    attr_skipped_censored = 0
    for author, idxs in prs["by_author"].items():
        first_i = None
        for i in idxs:
            if math.isfinite(prs["first_ts"][i]):
                first_i = i
                break
        if first_i is None:
            continue
        tone = float(prs["first_tone"][first_i])
        if not math.isfinite(tone):
            continue
        rts = float(prs["first_ts"][first_i])
        if dataset_end < rts + 90 * DAY:
            attr_skipped_censored += 1
            continue
        if tone > 0:
            attr_skipped_positive += 1
            continue
        later = 0.0
        for j in idxs:
            cts = float(prs["created"][j])
            if rts < cts <= rts + 90 * DAY:
                later = 1.0
                break
        g = int(group[first_i])
        if g < 0:
            attr_skipped_unidentified += 1
            continue
        bucket = attr_in if g == 1 else attr_out
        bucket.append(later)
        if tone < 0:
            (attr_in_neg if g == 1 else attr_out_neg).append(later)
    m_attr = compare(np.asarray(attr_in), np.asarray(attr_out), rng, n_boot, "rate")
    m_attr_neg = compare(np.asarray(attr_in_neg), np.asarray(attr_out_neg), rng, n_boot, "rate")

    # cohort survival and first-year treatment
    became_sent: List[float] = []
    left_sent: List[float] = []
    became_merge: List[float] = []
    left_merge: List[float] = []
    cohort_rows = []
    n_ingroup_at_entry = 0
    n_became = 0
    n_left = 0
    n_persisted_out = 0
    active_counts = {
        "became": {h: [0, 0] for h in HORIZON_DAYS},
        "never": {h: [0, 0] for h in HORIZON_DAYS},
    }
    by_year: Dict[int, List[str]] = defaultdict(list)
    author_meta = {}
    for author, idxs in prs["by_author"].items():
        first_ts_a = float(prs["created"][idxs[0]])
        year = datetime.fromtimestamp(first_ts_a, tz=timezone.utc).year
        by_year[year].append(author)
        entry = first_entry.get(author)
        became = entry is not None and entry > first_ts_a + 1
        at_entry = entry is not None and entry <= first_ts_a + 1
        if at_entry:
            n_ingroup_at_entry += 1
        year_end = first_ts_a + 365.25 * DAY
        window = [i for i in idxs if float(prs["created"][i]) < year_end]
        sent_vals = [float(prs["sentiment"][i]) for i in window if math.isfinite(float(prs["sentiment"][i]))]
        mer_vals = [float(merge[i]) for i in window if math.isfinite(float(merge[i]))]
        sent_m = float(np.mean(sent_vals)) if sent_vals else math.nan
        mer_m = float(np.mean(mer_vals)) if mer_vals else math.nan
        active = {}
        for months, days in HORIZON_DAYS.items():
            horizon = first_ts_a + days * DAY
            observable = dataset_end >= horizon
            still = any(float(prs["created"][i]) >= horizon for i in idxs)
            active[months] = {"observable": observable, "active": bool(still) if observable else None}
        author_meta[author] = {"became": became, "at_entry": at_entry, "active": active, "year": year}
        if became:
            n_became += 1
            if math.isfinite(sent_m):
                became_sent.append(sent_m)
            if math.isfinite(mer_m):
                became_merge.append(mer_m)
        never = entry is None
        left = never and active[24]["observable"] and active[24]["active"] is False
        persisted = never and active[24]["observable"] and active[24]["active"] is True
        if left:
            n_left += 1
            if math.isfinite(sent_m):
                left_sent.append(sent_m)
            if math.isfinite(mer_m):
                left_merge.append(mer_m)
        if persisted:
            n_persisted_out += 1
        label = "became" if became else "never"
        if not at_entry:
            for months, info in active.items():
                if info["observable"]:
                    active_counts[label][months][1] += 1
                    if info["active"]:
                        active_counts[label][months][0] += 1

    for year in sorted(by_year):
        members = by_year[year]
        row: Dict[str, Any] = {"year": year, "n": len(members)}
        for months in HORIZON_DAYS:
            obs = [author_meta[a]["active"][months] for a in members]
            observable = [o for o in obs if o["observable"]]
            row[f"active_{months}m"] = {
                "n_observable": len(observable),
                "fraction": (sum(1 for o in observable if o["active"]) / len(observable)) if observable else None,
            }
        became_m = [a for a in members if author_meta[a]["became"]]
        left_m = [
            a
            for a in members
            if author_meta[a]["active"][24]["observable"]
            and author_meta[a]["active"][24]["active"] is False
            and first_entry.get(a) is None
        ]
        row["n_became_ingroup"] = len(became_m)
        row["n_left_by_24m"] = len(left_m)
        cohort_rows.append(row)

    m_treat_sent = compare(np.asarray(became_sent), np.asarray(left_sent), rng, n_boot, "score")
    m_treat_merge = compare(np.asarray(became_merge), np.asarray(left_merge), rng, n_boot, "rate")
    survival_summary = {}
    for label in ("became", "never"):
        survival_summary[label] = {}
        for months, (num, den) in active_counts[label].items():
            survival_summary[label][f"{months}m"] = {
                "n_active": num,
                "n_observable": den,
                "fraction": (num / den) if den else None,
            }

    # IRC conversion and preface
    data_unavailable = []
    if not prs["saw_draft_ts"]:
        data_unavailable.append(
            {
                "metric": "8_draft_to_submission_gap",
                "reason": "DATA UNAVAILABLE: enriched and raw PR rows have a draft boolean, not draft-creation versus ready-for-review timestamps.",
            }
        )
    if not prs["saw_request"]:
        data_unavailable.append(
            {
                "metric": "10_reviewer_request_patterns",
                "reason": "DATA UNAVAILABLE: no requested_reviewers or review-request field on enriched_prs.jsonl or prs_raw.jsonl.",
            }
        )
    if not irc.get("available"):
        data_unavailable.append({"metric": "7_irc_to_pr_conversion", "reason": "DATA UNAVAILABLE: " + irc.get("reason", "IRC missing")})
        data_unavailable.append({"metric": "9_irc_presocialization", "reason": "DATA UNAVAILABLE: " + irc.get("reason", "IRC missing")})

    # draft snapshot abandonment among decided drafts, 2016+
    draft_mask = primary & (prs["draft"] == 1) & decided
    abandoned = ((prs["draft"] == 1) & (prs["outcome"] == 0) & (prs["cycles"] == 0) & np.isnan(prs["response_h"])).astype(float)
    # only meaningful on drafts; non-drafts are nan
    abandoned_vals = np.full(n, np.nan)
    abandoned_vals[(prs["draft"] == 1) & decided] = abandoned[(prs["draft"] == 1) & decided]
    m_draft = compare(
        _mask_vals(primary & decided, group, 1, abandoned_vals),
        _mask_vals(primary & decided, group, 0, abandoned_vals),
        rng,
        n_boot,
        "rate",
    )

    m_pref_merge = None
    m_pref_speed = None
    m_pref_share = None
    strat_merge_pref = None
    strat_sent_pref = None
    strat_vocab_pref = None
    if irc.get("available"):
        resolved_m = primary & (resolved == 1)
        m_pref_merge = compare(
            merge[resolved_m & decided & (prefaced == 1)],
            merge[resolved_m & decided & (prefaced == 0)],
            rng,
            n_boot,
            "rate",
        )
        m_pref_speed = compare(
            prs["response_h"][resolved_m & (prefaced == 1)],
            prs["response_h"][resolved_m & (prefaced == 0)],
            rng,
            n_boot,
            "hours",
        )
        m_pref_share = compare(
            prefaced[primary & (group == 1)].astype(float),
            prefaced[primary & (group == 0)].astype(float),
            rng,
            n_boot,
            "rate",
        )
        pref_lab = prefaced.astype(np.int8)
        pref_bins = ((0, 0, "no topic preface"), (1, 1, "topic preface"))
        strat_merge_pref = stratify(primary & decided & (resolved == 1), group, merge, pref_lab, pref_bins, rng, n_boot, "rate")
        strat_sent_pref = stratify(primary & (resolved == 1), group, prs["sentiment"], pref_lab, pref_bins, rng, n_boot, "score")
        strat_vocab_pref = stratify(primary & (resolved == 1), group, vocab_total, pref_lab, pref_bins, rng, n_boot, "count")

    # silence class rates for bootstrap
    silence_compare = None
    if silence.get("available"):
        flags_in = silence["by_class_silent_flags"].get("ever_ingroup", [])
        flags_out = silence["by_class_silent_flags"].get("pr_author_never_ingroup", []) + silence[
            "by_class_silent_flags"
        ].get("no_pr", [])
        silence_compare = compare(np.asarray(flags_in, dtype=float), np.asarray(flags_out, dtype=float), rng, n_boot, "rate")
        conv_flags = np.array(
            [1.0] * silence["n_irc_and_pr"] + [0.0] * silence["n_irc_never_pr"],
            dtype=float,
        )
        conversion = boot_mean(conv_flags, rng, n_boot)
    else:
        conversion = None

    mechanism = _disambiguate(
        m_sent["comparison"],
        m_vocab["comparison"],
        m_attr,
        m_pref_merge,
        persist_sent_lines,
        shrink_sent_lines,
        m_treat_sent,
        m_treat_merge,
        silence_compare,
        strat_merge_pref,
        strat_sent_pref,
        strat_vocab_pref,
        m_pref_share,
        m_merge["comparison"],
        irc_uncertain,
    )

    confounds = {
        "quality": {
            "flag": True,
            "text": (
                "Out-group authors may submit different work. Lines changed, files touched, and prior PR count "
                "are partial proxies. A remaining gap is still not proof of hostility. Prior-PR strata are partly "
                "circular with who later reviews a lot."
            ),
            "merge_gap_persists_lines": persist_merge_lines,
            "sentiment_gap_persists_lines": persist_sent_lines,
            "sentiment_shrinks_after_lines": shrink_sent_lines,
        },
        "circularity": {
            "flag": bool(overlap is not None and overlap > 0.5),
            "overlap_final_top_reviewers_vs_top_submitters": overlap,
            "overlap_count": overlap_n,
            "top_n": top_n,
            "text": (
                "Final top-N reviewers versus top-N PR authors. Overlap above 50% means the in-group/out-group "
                "cut is weaker than a newcomers-versus-regulars story: the same people are on both sides."
            ),
        },
        "survival_bias": {
            "flag": True,
            "addressed_by": "metric_6",
            "text": (
                "A fixed end-of-sample reviewer list would treat everyone who left as out-group and hide the "
                "dropout path. Metric 6 uses the time-varying set plus a retrospective 'later entered top-N' label. "
                "That label is not available at the first PR."
            ),
        },
        "irc_nick_resolution": {
            "flag": bool(irc_uncertain),
            "match_rate_pr_authors_seen_in_irc": match_rate,
            "n_pr_authors": len(author_set),
            "n_pr_authors_seen_in_irc": len(matched_authors),
            "threshold": 0.60,
            "text": (
                "Match rate is the share of PR-author identities that appear at least once in the IRC log under "
                "the same unified id (or the same login string when the map has no IRC row). "
                "Below 60%, metrics 7 and 9 have elevated uncertainty."
            ),
        },
    }

    result = {
        "pin": (
            "Population-level behavioral proxies only. In-group is the time-varying top-N peer reviewers, "
            "not a psychological class and not the merge-key set. This file does not show that rejection "
            "sensitive dysphoria, negativity bias, or in-group preference caused any Bitcoin Core outcome."
        ),
        "version": "1.0",
        "parameters": {"top_n": top_n, "bootstrap": n_boot, "seed": seed, "headline_window": "created_at >= 2016-01-01"},
        "data_sources": {
            "prs": pr_source,
            "n_pr_rows_read": prs["n_rows_read"],
            "n_prs_used": n,
            "identity": ident.source,
            "identity_notes": ident.notes,
            "irc": irc.get("source"),
            "irc_messages_used": irc.get("n_messages"),
            "irc_channels": irc.get("channels"),
            "irc_filtered_to_bitcoin_channels": irc.get("filtered_to_bitcoin_channels"),
            "review_volume": "peer GitHub review objects only (not issue comments)",
            "n_review_events": len(prs["review_events"]),
            "n_distinct_reviewers": n_reviewers,
            "ingroup_defined_from": datetime.fromtimestamp(defined_from, tz=timezone.utc).isoformat() if defined_from else None,
            "n_unidentified_prs": int((~defined).sum()),
            "n_primary_prs": int(primary.sum()),
            "final_top_reviewers": [ident.label(x) for x in final_top],
        },
        "method_notes": notes_common,
        "blocks": {
            "A": {
                "1_merge_rate": m_merge,
                "1b_merge_rate_wherever_defined": m_merge_all,
                "2_mean_sentiment": m_sent,
                "2b_any_negative_tone": m_neg,
                "3_time_to_first_response_hours": m_speed,
                "3b_no_peer_response_rate": m_noresp,
                "3c_time_to_decision_hours": m_decision,
                "3d_review_cycles": m_cycles,
                "4_justification_vocabulary": {"total": m_vocab, "per_term_per_pr": vocab_terms},
            },
            "B": {
                "5_return_within_90d_after_neutral_or_negative_first_response": {
                    "comparison": m_attr,
                    "negative_only_sensitivity": m_attr_neg,
                    "notes": [
                        "Unit is the contributor. First peer response on their history. Included when that tone is neutral or negative. "
                        "Outcome is another PR in the next 90 days. Censored when the log ends inside those 90 days. "
                        "Group is in-group status on that PR, not a final label. "
                        "Neutral is the common enriched label, so the negative-only row is the stricter cut.",
                        "If the in-group cell is empty, nobody was already in the top-N when their first peer response arrived. "
                        "First responses sit earlier than reviewer-volume rank, so the in-group contrast is unidentified. "
                        "The out-group figure is the newcomer return rate only.",
                    ],
                    "n_skipped_positive_first_response": attr_skipped_positive,
                    "n_skipped_censored": attr_skipped_censored,
                    "n_skipped_unidentified_group": attr_skipped_unidentified,
                },
                "6_entry_cohort_survival": {
                    "cohorts": cohort_rows,
                    "survival_by_retrospective_label": survival_summary,
                    "n_became_ingroup_later": n_became,
                    "n_left_by_24m_never_ingroup": n_left,
                    "n_still_active_24m_never_ingroup": n_persisted_out,
                    "n_already_ingroup_at_first_pr": n_ingroup_at_entry,
                    "first_year_sentiment_became_vs_left": m_treat_sent,
                    "first_year_merge_became_vs_left": m_treat_merge,
                    "notes": [
                        "Active at a horizon means some later PR is at or after that horizon. People whose first PR is too close to the dump end are not in that denominator.",
                        "became = entered the time-varying top-N after their first PR. left = never entered and no PR at or after 24 months, among people observable that long.",
                        "The outcome split is the group definition. Similar first-year treatment is the evidence. The survival gap between these two labels is not a separate finding.",
                        "Retrospective in-group membership was not knowable at entry. A fixed snapshot would have hidden that.",
                    ],
                },
            },
            "C": {
                "7_irc_silence_proxy": {
                    **silence,
                    "conversion_rate_irc_discussant_submitted_a_pr": conversion,
                    "silence_rate_ever_ingroup_vs_everyone_else": silence_compare,
                    "elevated_uncertainty": irc_uncertain,
                },
                "8_draft_abandonment_snapshot": {
                    "timestamp_gap": "DATA UNAVAILABLE" if not prs["saw_draft_ts"] else "present",
                    "comparison_abandoned_closed_unreviewed_drafts": m_draft,
                    "notes": [
                        "Abandonment here is a collected draft=true PR that closed unmerged with no peer response. "
                        "It is not time from draft creation to publish. Open drafts are excluded."
                    ],
                },
            },
            "D": {
                "9_irc_presocialization": {
                    "available": bool(irc.get("available")),
                    "elevated_uncertainty": irc_uncertain,
                    "match_rate": match_rate,
                    "definition": (
                        "Topic preface: in the 48 hours before created_at, the submitter's IRC identity posted in a "
                        "bitcoin* channel and the line contained a title token (length >= 5, stopwords removed) "
                        "or a bitcoin/bitcoin pull URL or the phrase 'pull request'. "
                        "Presence is any such post, without the topic match. "
                        "Unresolved authors (never seen in IRC) are not in the preface comparison."
                    ),
                    "merge_rate_prefaced_vs_not": m_pref_merge,
                    "hours_to_response_prefaced_vs_not": m_pref_speed,
                    "preface_rate_ingroup_vs_outgroup": m_pref_share,
                    "n_primary_resolved": int((primary & (resolved == 1)).sum()) if irc.get("available") else 0,
                    "n_primary_prefaced": int((primary & (prefaced == 1)).sum()) if irc.get("available") else 0,
                    "n_primary_present_48h": int((primary & (present == 1)).sum()) if irc.get("available") else 0,
                    "merge_gap_within_preface": strat_merge_pref,
                    "sentiment_gap_within_preface": strat_sent_pref,
                    "vocab_gap_within_preface": strat_vocab_pref,
                },
                "10_reviewer_requests": {
                    "available": bool(prs["saw_request"]),
                    "reason": None
                    if prs["saw_request"]
                    else "DATA UNAVAILABLE: no requested_reviewers or review-request field on enriched_prs.jsonl or prs_raw.jsonl.",
                },
            },
        },
        "stratification": {
            "lines_merge": strat_merge_lines,
            "lines_sentiment": strat_sent_lines,
            "files_merge": strat_merge_files,
            "files_sentiment": strat_sent_files,
            "prior_prs_merge": strat_merge_prior,
            "prior_prs_sentiment": strat_sent_prior,
            "note": "Usable stratum: at least 30 finite observations on each side. Prior-PR bins are partly circular with later reviewer status.",
        },
        "confounds": confounds,
        "mechanism_disambiguation": mechanism,
        "what_this_cannot_prove": CANNOT_PROVE,
        "data_unavailable": data_unavailable,
    }
    result["plain_text_summary"] = render_summary(result)
    return _jsonable(result)


def _known(comp: Optional[Dict[str, Any]]) -> bool:
    return bool(comp) and comp.get("cohens_d") is not None


def _disambiguate(
    sent: Dict[str, Any],
    vocab: Dict[str, Any],
    attr: Dict[str, Any],
    pref_merge: Optional[Dict[str, Any]],
    persist_sent: Dict[str, Any],
    shrink_sent: Optional[bool],
    treat_sent: Dict[str, Any],
    treat_merge: Dict[str, Any],
    silence_cmp: Optional[Dict[str, Any]],
    strat_merge_pref: Optional[Dict[str, Any]],
    strat_sent_pref: Optional[Dict[str, Any]],
    strat_vocab_pref: Optional[Dict[str, Any]],
    pref_share: Optional[Dict[str, Any]],
    merge_comp: Optional[Dict[str, Any]],
    irc_uncertain: bool,
) -> Dict[str, Any]:
    fired: Dict[str, List[str]] = {
        "active_social_filtering": [],
        "passive_dropout": [],
        "structural_access_asymmetry": [],
    }
    unknown: List[str] = []

    if persist_sent.get("persists"):
        fired["active_social_filtering"].append("sentiment gap persists after lines-changed strata")
    else:
        unknown.append("active: sentiment persistence not met (" + str(persist_sent.get("reason")) + ")")

    if _known(vocab) and abs(vocab["cohens_d"]) >= 0.2:
        fired["active_social_filtering"].append("justification vocabulary differs with d >= 0.2")
    elif _known(vocab):
        unknown.append("active: vocabulary |d| < 0.2")

    if _known(attr) and attr["cohens_d"] >= 0.2:
        fired["active_social_filtering"].append("in-group returns more often within 90 days after neutral/negative first response (d >= 0.2)")
        fired["passive_dropout"].append("return-rate gap after neutral/negative first response (d >= 0.2)")
    elif _known(attr):
        unknown.append("attrition |d| < 0.2")

    if pref_merge and _known(pref_merge) and abs(pref_merge["cohens_d"]) < 0.2:
        fired["active_social_filtering"].append("IRC topic-preface merge effect is negligible")
    elif pref_merge is None:
        unknown.append("IRC preface merge effect unavailable")
    elif not _known(pref_merge):
        unknown.append("IRC preface merge effect underpowered")

    if silence_cmp and _known(silence_cmp) and silence_cmp["cohens_d"] <= -0.2:
        # d is ever-ingroup minus everyone else; negative means everyone else is more often silent
        fired["passive_dropout"].append("IRC silence proxy is higher outside the ever-in-group set (d <= -0.2)")
    elif silence_cmp is None:
        unknown.append("IRC silence comparison unavailable")
    else:
        unknown.append("IRC silence gap does not clear d = 0.2")

    sent_ok = _known(treat_sent) and abs(treat_sent["cohens_d"]) < 0.2
    mer_ok = _known(treat_merge) and abs(treat_merge["cohens_d"]) < 0.2
    if sent_ok and mer_ok:
        fired["passive_dropout"].append("first-year sentiment and merge rate are similar for later-in-group vs 24-month leavers")
    else:
        unknown.append("early treatment similarity not met (needs both |d| < 0.2)")

    if shrink_sent is True:
        fired["passive_dropout"].append("sentiment gap shrinks by at least half after lines-changed strata")
    elif shrink_sent is False:
        unknown.append("sentiment gap does not shrink by half after lines strata")

    within = None if not strat_merge_pref else strat_merge_pref.get("weighted_gap")
    raw_share = _diff(pref_share) if pref_share else None
    raw_merge = _diff(merge_comp) if merge_comp else None
    # Structural reading: preface is common for one group, and the in/out merge gap shrinks once preface is held fixed.
    if (
        strat_merge_pref
        and strat_merge_pref.get("n_usable_strata", 0) >= 2
        and within is not None
        and raw_merge is not None
        and abs(raw_merge) > 0
        and abs(within) <= 0.5 * abs(raw_merge)
        and raw_share is not None
        and abs(raw_share) >= 0.10
    ):
        fired["structural_access_asymmetry"].append(
            "in/out merge gap inside preface strata is at most half the raw in/out merge gap, and preface share differs by >= 10 points"
        )
    else:
        unknown.append("structural: preface does not account for most of the in/out merge gap under the stated rule")

    if strat_sent_pref and shrinks_substantially(_diff(sent), strat_sent_pref.get("weighted_gap"), strat_sent_pref.get("n_usable_strata", 0)) is True:
        fired["structural_access_asymmetry"].append("sentiment gap shrinks by at least half inside IRC-preface strata")

    if strat_vocab_pref and strat_vocab_pref.get("n_usable_strata", 0) >= 2:
        usable = [r for r in strat_vocab_pref["strata"] if r["usable"]]
        ds = [r["comparison"]["cohens_d"] for r in usable if r["comparison"].get("cohens_d") is not None]
        if ds and all(abs(d) < 0.2 for d in ds):
            fired["structural_access_asymmetry"].append("justification vocabulary |d| < 0.2 inside both preface strata")

    scores = {k: len(v) for k, v in fired.items()}
    ranking = sorted(scores, key=lambda k: (-scores[k], k))
    top = ranking[0]
    second = ranking[1]
    if scores[top] == 0:
        resemblance = "no candidate fingerprint is strongly present"
    elif scores[top] >= scores[second] + 2 and scores[top] >= 2:
        resemblance = top
    else:
        resemblance = "mixed"
    if irc_uncertain and resemblance == "structural_access_asymmetry":
        resemblance = "mixed"
        unknown.append("IRC match rate is under 60% or IRC is missing, so a structural reading stays uncertain")
    return {
        "resemblance": resemblance,
        "scores": scores,
        "conditions_met": fired,
        "conditions_not_met_or_unknown": unknown,
        "reading": (
            "Scores count pre-specified conditions, not a model probability. "
            "A lead of 2 or more, with at least 2 conditions, is reported as the closer fingerprint. "
            "Otherwise the pattern is mixed or absent. Do not treat the label as a cause."
        ),
    }


def _fmt_est(block: Optional[Dict[str, Any]], kind: str) -> str:
    if not block or block.get("estimate") is None:
        return "n/a"
    est = block["estimate"]
    ci = block.get("ci95") or [est, est]
    n = block.get("n")
    if kind == "rate":
        body = f"{100 * est:.1f}% (95% CI {100 * ci[0]:.1f}–{100 * ci[1]:.1f}%)"
    elif kind == "hours":
        body = f"{est:.1f}h (95% CI {ci[0]:.1f}–{ci[1]:.1f})"
    else:
        body = f"{est:.3f} (95% CI {ci[0]:.3f}–{ci[1]:.3f})"
    return f"{body}  n={n}"


def _fmt_cmp(comp: Optional[Dict[str, Any]], left: str = "in-group", right: str = "out-group") -> List[str]:
    if not comp:
        return ["  DATA UNAVAILABLE"]
    kind = comp.get("kind") or "count"
    lines = [
        f"  {left}: {_fmt_est(comp.get('in_group'), kind)}",
        f"  {right}: {_fmt_est(comp.get('out_group'), kind)}",
    ]
    diff = comp.get("difference_in_minus_out")
    d = comp.get("cohens_d")
    flag = comp.get("effect_size_flag")
    if diff and diff.get("estimate") is not None:
        ci = diff["ci95"]
        if kind == "rate":
            dtext = f"{100 * diff['estimate']:.1f} pp (95% CI {100 * ci[0]:.1f}–{100 * ci[1]:.1f} pp)"
        elif kind == "hours":
            dtext = f"{diff['estimate']:.1f}h (95% CI {ci[0]:.1f}–{ci[1]:.1f})"
        else:
            dtext = f"{diff['estimate']:.3f} (95% CI {ci[0]:.3f}–{ci[1]:.3f})"
        dpart = "n/a" if d is None else f"{d:.2f}"
        lines.append(f"  difference ({left} minus {right}): {dtext}  Cohen's d={dpart}  {flag}")
    else:
        lines.append(f"  difference: n/a  {flag}")
    return lines


def render_summary(data: Dict[str, Any]) -> str:
    lines: List[str] = []
    src = data["data_sources"]
    lines.append(data["pin"])
    lines.append("")
    lines.append(
        f"PRs used {src['n_prs_used']} of {src['n_pr_rows_read']} read from {src['prs']}. "
        f"Review events {src['n_review_events']}. Distinct reviewers {src['n_distinct_reviewers']}. "
        f"Top-N defined from {src['ingroup_defined_from']}. "
        f"Unidentified PRs {src['n_unidentified_prs']}. Headline PRs {src['n_primary_prs']}."
    )
    lines.append("Final top reviewers (labels, not a psych class): " + ", ".join(src["final_top_reviewers"]))
    lines.append("Identity: " + src["identity"])
    A = data["blocks"]["A"]
    B = data["blocks"]["B"]
    C = data["blocks"]["C"]
    D = data["blocks"]["D"]

    lines.append("")
    lines.append("BLOCK A — Active social filtering")
    lines.append("1. Merge rate, decided PRs, 2016+")
    lines.extend(_fmt_cmp(A["1_merge_rate"]["comparison"]))
    lines.append("1b. Merge rate wherever the top-N is already defined (coverage-mixed)")
    lines.extend(_fmt_cmp(A["1b_merge_rate_wherever_defined"]["comparison"]))
    lines.append("2. Mean review sentiment, 2016+")
    lines.extend(_fmt_cmp(A["2_mean_sentiment"]["comparison"]))
    lines.append("2b. Any-negative-tone rate, 2016+")
    lines.extend(_fmt_cmp(A["2b_any_negative_tone"]["comparison"]))
    lines.append("3. Hours to first peer response, 2016+")
    lines.extend(_fmt_cmp(A["3_time_to_first_response_hours"]["comparison"]))
    lines.append("3b. No peer response rate, 2016+")
    lines.extend(_fmt_cmp(A["3b_no_peer_response_rate"]["comparison"]))
    lines.append("3c. Hours to merge or close, 2016+")
    lines.extend(_fmt_cmp(A["3c_time_to_decision_hours"]["comparison"]))
    lines.append("3d. Peer review-object count, 2016+")
    lines.extend(_fmt_cmp(A["3d_review_cycles"]["comparison"]))
    lines.append("4. Justification vocabulary hits per PR, 2016+")
    lines.extend(_fmt_cmp(A["4_justification_vocabulary"]["total"]["comparison"]))
    for term, comp in A["4_justification_vocabulary"]["per_term_per_pr"].items():
        lines.append(f"   term {term}")
        lines.extend(_fmt_cmp(comp))

    lines.append("")
    lines.append("BLOCK B — Attrition and dropout")
    lines.append("5. Another PR within 90 days after a neutral or negative first response")
    lines.extend(_fmt_cmp(B["5_return_within_90d_after_neutral_or_negative_first_response"]["comparison"]))
    lines.append("5b. Negative-only first response (sensitivity)")
    lines.extend(_fmt_cmp(B["5_return_within_90d_after_neutral_or_negative_first_response"]["negative_only_sensitivity"]))
    for note in B["5_return_within_90d_after_neutral_or_negative_first_response"]["notes"]:
        lines.append("  " + note)
    surv = B["6_entry_cohort_survival"]
    lines.append(
        f"6. Entry cohorts. Later entered top-N: {surv['n_became_ingroup_later']}. "
        f"Left by 24 months and never in top-N: {surv['n_left_by_24m_never_ingroup']}. "
        f"Still active at 24 months and never in top-N: {surv['n_still_active_24m_never_ingroup']}. "
        f"Already in top-N at first PR: {surv['n_already_ingroup_at_first_pr']}."
    )
    lines.append("6a. First-year sentiment, later-in-group minus leavers")
    lines.extend(_fmt_cmp(surv["first_year_sentiment_became_vs_left"], "later-in-group", "leavers"))
    lines.append("6b. First-year merge rate, later-in-group minus leavers")
    lines.extend(_fmt_cmp(surv["first_year_merge_became_vs_left"], "later-in-group", "leavers"))
    lines.append("6c. Still active at horizon (retrospective label; not a treatment effect)")
    for label in ("became", "never"):
        bits = []
        for key, row in surv["survival_by_retrospective_label"][label].items():
            frac = row["fraction"]
            shown = "n/a" if frac is None else f"{100 * frac:.1f}%"
            bits.append(f"{key} {shown} (n={row['n_observable']})")
        lines.append(f"  {label}: " + "; ".join(bits))
    lines.append("6d. Cohort year, share still active among people observable at that horizon")
    for row in surv["cohorts"]:
        bits = [f"n={row['n']}"]
        for months in (6, 12, 24, 48):
            cell = row[f"active_{months}m"]
            frac = cell["fraction"]
            shown = "n/a" if frac is None else f"{100 * frac:.0f}%"
            bits.append(f"{months}m {shown}/{cell['n_observable']}")
        bits.append(f"became {row['n_became_ingroup']}")
        bits.append(f"left24 {row['n_left_by_24m']}")
        lines.append(f"  {row['year']}: " + " ".join(bits))

    lines.append("")
    lines.append("BLOCK C — Preemptive withdrawal proxy")
    sil = C["7_irc_silence_proxy"]
    if not sil.get("available"):
        lines.append("7. DATA UNAVAILABLE: " + str(sil.get("reason")))
    else:
        conv = sil.get("conversion_rate_irc_discussant_submitted_a_pr")
        lines.append(
            f"7. IRC discussants {sil['n_irc_discussants']}; also submitted a PR {sil['n_irc_and_pr']}; "
            f"never in the PR record {sil['n_irc_never_pr']}."
        )
        lines.append("  conversion (IRC discussant submitted a PR): " + _fmt_est(conv, "rate"))
        lines.append(
            f"  concept-reply events uncensored {sil['n_response_events_uncensored']}; "
            f"censored {sil['n_response_events_censored']}; silent events {sil['n_silent_events']}; "
            f"people {sil['n_people']}; people silent {sil['n_people_silent']}."
        )
        lines.append("  WEAK PROXY. " + sil.get("rule", ""))
        lines.append("  silence rate, ever-in-group minus everyone else")
        lines.extend(_fmt_cmp(sil.get("silence_rate_ever_ingroup_vs_everyone_else"), "ever-in-group", "everyone-else"))
        if sil.get("elevated_uncertainty"):
            lines.append("  CONFOUND: IRC match rate under 60% or IRC missing — elevated uncertainty.")
    draft = C["8_draft_abandonment_snapshot"]
    lines.append("8. Draft creation versus publish timestamps: " + draft["timestamp_gap"])
    lines.append("  snapshot: closed unmerged draft with no peer response, among decided drafts, 2016+")
    lines.extend(_fmt_cmp(draft["comparison_abandoned_closed_unreviewed_drafts"]))

    lines.append("")
    lines.append("BLOCK D — Structural access asymmetry")
    pref = D["9_irc_presocialization"]
    if not pref.get("available"):
        lines.append("9. DATA UNAVAILABLE")
    else:
        lines.append(
            f"9. Primary resolved {pref['n_primary_resolved']}; topic-prefaced {pref['n_primary_prefaced']}; "
            f"any IRC in prior 48h {pref['n_primary_present_48h']}. Match rate {100 * pref['match_rate']:.1f}%."
        )
        lines.append("  merge rate, topic-prefaced minus not (resolved authors)")
        lines.extend(_fmt_cmp(pref["merge_rate_prefaced_vs_not"], "prefaced", "not-prefaced"))
        lines.append("  hours to first response, topic-prefaced minus not")
        lines.extend(_fmt_cmp(pref["hours_to_response_prefaced_vs_not"], "prefaced", "not-prefaced"))
        lines.append("  topic-preface rate, in-group minus out-group")
        lines.extend(_fmt_cmp(pref["preface_rate_ingroup_vs_outgroup"]))
        if pref.get("elevated_uncertainty"):
            lines.append("  CONFOUND: IRC match rate under 60% — elevated uncertainty on this block.")
    req = D["10_reviewer_requests"]
    if req.get("available"):
        lines.append("10. Reviewer request metadata present.")
    else:
        lines.append("10. " + req["reason"])

    lines.append("")
    lines.append("CONFOUND FLAGS")
    q = data["confounds"]["quality"]
    lines.append("Quality confound: flagged. " + q["text"])
    lines.append(
        "  lines strata, merge gap persists: "
        + str(q["merge_gap_persists_lines"]["persists"])
        + " ("
        + q["merge_gap_persists_lines"]["reason"]
        + ")"
    )
    lines.append(
        "  lines strata, sentiment gap persists: "
        + str(q["sentiment_gap_persists_lines"]["persists"])
        + " ("
        + q["sentiment_gap_persists_lines"]["reason"]
        + ")"
    )
    circ = data["confounds"]["circularity"]
    lines.append(
        f"Circularity: overlap {circ['overlap_count']}/{circ['top_n']} = "
        f"{None if circ['overlap_final_top_reviewers_vs_top_submitters'] is None else round(100 * circ['overlap_final_top_reviewers_vs_top_submitters'], 1)}%. "
        f"Flagged={circ['flag']}. {circ['text']}"
    )
    lines.append("Survival bias: flagged as a design risk that metric 6 is there to show. " + data["confounds"]["survival_bias"]["text"])
    irc_c = data["confounds"]["irc_nick_resolution"]
    lines.append(
        f"IRC resolution: match rate {100 * irc_c['match_rate_pr_authors_seen_in_irc']:.1f}% "
        f"({irc_c['n_pr_authors_seen_in_irc']}/{irc_c['n_pr_authors']}). Flagged={irc_c['flag']}. {irc_c['text']}"
    )

    lines.append("")
    lines.append("MECHANISM DISAMBIGUATION")
    mech = data["mechanism_disambiguation"]
    lines.append("Closer fingerprint: " + mech["resemblance"])
    lines.append("Condition counts: " + ", ".join(f"{k}={v}" for k, v in mech["scores"].items()))
    for key, items in mech["conditions_met"].items():
        lines.append(f"  met {key}: " + ("; ".join(items) if items else "none"))
    lines.append("  not met or unknown:")
    for item in mech["conditions_not_met_or_unknown"]:
        lines.append("    - " + item)
    lines.append(mech["reading"])

    lines.append("")
    lines.append("WHAT THIS CANNOT PROVE")
    for i, sentence in enumerate(data["what_this_cannot_prove"], start=1):
        lines.append(f"{i}. {sentence}")
    if data["data_unavailable"]:
        lines.append("")
        lines.append("DATA UNAVAILABLE")
        for row in data["data_unavailable"]:
            lines.append(f"- {row['metric']}: {row['reason']}")
    return "\n".join(lines)


def _jsonable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return _jsonable(obj.tolist())
    if isinstance(obj, (np.floating,)):
        x = float(obj)
        return None if not math.isfinite(x) else x
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, float):
        return None if not math.isfinite(obj) else obj
    if isinstance(obj, (str, int, bool)) or obj is None:
        return obj
    return str(obj)


def boot_stat(arr: np.ndarray, rng: np.random.Generator, n_boot: int, fn) -> Optional[Dict[str, Any]]:
    clean = _finite(arr)
    n = int(clean.size)
    if n == 0:
        return None
    est = float(fn(clean))
    if n == 1 or n_boot <= 0:
        return {"n": n, "estimate": est, "ci95": [est, est]}
    idx = rng.integers(0, n, size=(n_boot, n))
    draws = fn(clean[idx], axis=1)
    lo, hi = np.quantile(draws, [0.025, 0.975])
    return {"n": n, "estimate": est, "ci95": [float(lo), float(hi)]}


def _years_of(ts: np.ndarray) -> np.ndarray:
    out = np.empty(ts.shape[0], dtype=np.int16)
    for i, t in enumerate(ts):
        out[i] = datetime.fromtimestamp(float(t), tz=timezone.utc).year
    return out


def walk_rolling(
    review_events: Sequence[Tuple[float, str]],
    query_ts: Sequence[float],
    query_author: Sequence[str],
    top_n: int,
    window_sec: float,
) -> Tuple[List[Optional[bool]], Dict[str, float], List[str], Optional[float]]:
    """Top-N by peer review volume in [T - window, T). None if fewer than top_n reviewers in the window."""
    reviews = sorted(review_events, key=lambda row: row[0])
    order = sorted(range(len(query_ts)), key=lambda i: query_ts[i])
    counts: Dict[str, int] = {}
    left = 0
    right = 0
    flags: List[Optional[bool]] = [None] * len(query_ts)
    first_entry: Dict[str, float] = {}
    last_top: List[str] = []
    last_defined: Optional[float] = None
    for qi in order:
        ts = float(query_ts[qi])
        cutoff = ts - window_sec
        while right < len(reviews) and reviews[right][0] < ts:
            who = reviews[right][1]
            counts[who] = counts.get(who, 0) + 1
            right += 1
        while left < right and reviews[left][0] < cutoff:
            who = reviews[left][1]
            counts[who] = counts.get(who, 0) - 1
            if counts[who] <= 0:
                counts.pop(who, None)
            left += 1
        if len(counts) >= top_n:
            top = heapq.nlargest(top_n, counts, key=lambda k: (counts[k], k))
            last_top = list(top)
            last_defined = ts
            flags[qi] = query_author[qi] in set(top)
            for member in top:
                first_entry.setdefault(member, ts)
        else:
            flags[qi] = None
    return flags, first_entry, last_top, last_defined


def mantel_haenszel_rd(tables: Sequence[Tuple[int, float, int, float]]) -> Optional[float]:
    """Risk difference pooled with weights n1*n0/n. Each row is (n1, successes1, n0, successes0)."""
    num = 0.0
    den = 0.0
    for n1, s1, n0, s0 in tables:
        if n1 <= 0 or n0 <= 0:
            continue
        w = (n1 * n0) / (n1 + n0)
        num += w * ((s1 / n1) - (s0 / n0))
        den += w
    if den <= 0:
        return None
    return num / den


def mantel_haenszel_or(tables: Sequence[Tuple[int, float, int, float]]) -> Optional[float]:
    num = 0.0
    den = 0.0
    used = 0
    for n1, s1, n0, s0 in tables:
        if n1 <= 0 or n0 <= 0:
            continue
        a = float(s1)
        b = float(n1) - a
        c = float(s0)
        d = float(n0) - c
        n = float(n1 + n0)
        if min(a, b, c, d) < 0 or n <= 0:
            continue
        num += a * d / n
        den += b * c / n
        used += 1
    if used == 0 or den <= 0 or num <= 0:
        return None
    return num / den


def logistic_irls(x_mat: np.ndarray, y: np.ndarray, max_iter: int = 40) -> Optional[np.ndarray]:
    """Bernoulli IRLS. Returns coefficients, or None if the design is singular."""
    beta = np.zeros(x_mat.shape[1], dtype=float)
    for _ in range(max_iter):
        eta = np.clip(x_mat @ beta, -20, 20)
        prob = 1.0 / (1.0 + np.exp(-eta))
        w = np.clip(prob * (1.0 - prob), 1e-6, None)
        z = eta + (y - prob) / w
        xtw = x_mat * w[:, None]
        gram = xtw.T @ x_mat
        step, *_rest = np.linalg.lstsq(gram, xtw.T @ z, rcond=1e-8)
        if step.size != beta.size or not np.all(np.isfinite(step)):
            return None
        if float(np.max(np.abs(step - beta))) < 1e-8:
            return step
        beta = step
    return beta


def _ols_group_coef(y: np.ndarray, group: np.ndarray, cohort: np.ndarray) -> Optional[float]:
    """Coefficient on group in y ~ group + cohort fixed effects."""
    if y.size < 4 or np.unique(group).size < 2:
        return None
    levels = sorted(set(int(c) for c in cohort))
    if len(levels) < 2:
        x_mat = np.column_stack([np.ones(y.size), group])
    else:
        dummies = [(cohort == lev).astype(float) for lev in levels[1:]]
        x_mat = np.column_stack([np.ones(y.size), group, *dummies])
    try:
        coef, *_ = np.linalg.lstsq(x_mat, y, rcond=None)
    except np.linalg.LinAlgError:
        return None
    return float(coef[1])


def _weighted_slope(x: np.ndarray, y: np.ndarray, w: np.ndarray) -> Optional[float]:
    if x.size < 3:
        return None
    sw = np.sqrt(np.clip(w, 1, None))
    x_mat = np.column_stack([np.ones(x.size), x]) * sw[:, None]
    try:
        coef, *_ = np.linalg.lstsq(x_mat, y * sw, rcond=None)
    except np.linalg.LinAlgError:
        return None
    return float(coef[1])


def _boot_coef(draws: List[float]) -> Optional[Dict[str, Any]]:
    clean = np.asarray([d for d in draws if d is not None and math.isfinite(d)], dtype=float)
    if clean.size == 0:
        return None
    lo, hi = np.quantile(clean, [0.025, 0.975]) if clean.size > 1 else (clean[0], clean[0])
    return {"n": int(clean.size), "estimate": float(np.median(clean)), "ci95": [float(lo), float(hi)], "n_failed": None}


def analyze_v2(top_n: int = 20, n_boot: int = 1000, seed: int = 7) -> Dict[str, Any]:
    """Period controls. Does not observe psychological state."""
    rng = np.random.default_rng(seed)
    data_dir = get_data_dir()
    ident = load_identity()
    pr_path, pr_source = resolve_pr_path(data_dir)
    logger.info("v2 loading PRs from %s", pr_path)
    prs = load_prs(pr_path, ident)
    n = len(prs["authors"])
    created = prs["created"]
    years = _years_of(created)
    outcome = prs["outcome"]
    merge = np.full(n, np.nan)
    merge[outcome == 1] = 1.0
    merge[outcome == 0] = 0.0
    no_response = np.isnan(prs["response_h"]).astype(float)
    dataset_end = float(created.max()) if n else 0.0
    unavailable: List[Dict[str, str]] = []

    logger.info("v2 cumulative top-%s for the cohort and logistic sections", top_n)
    flags, first_entry, final_top, _n_reviewers = walk_ingroup(
        prs["review_events"], created.tolist(), prs["authors"], top_n
    )
    group = np.full(n, -1, dtype=np.int8)
    for i, flag in enumerate(flags):
        if flag is True:
            group[i] = 1
        elif flag is False:
            group[i] = 0

    # --- 1. period trend ---
    period_rows = []
    for year in range(2010, 2027):
        m = years == year
        n_year = int(m.sum())
        if n_year == 0:
            unavailable.append({"metric": f"period_trend_{year}", "reason": "DATA UNAVAILABLE: no PRs opened in this calendar year."})
            period_rows.append({"year": year, "n": 0, "available": False})
            continue
        open_share = float((outcome[m] < 0).mean())
        period_rows.append(
            {
                "year": year,
                "available": True,
                "n": n_year,
                "n_open": int((outcome[m] < 0).sum()),
                "open_share": open_share,
                "right_censored": open_share > 0.20,
                "merge_rate_decided": boot_mean(merge[m], rng, n_boot),
                "mean_tone": boot_mean(prs["sentiment"][m], rng, n_boot),
                "no_peer_response_rate": boot_mean(no_response[m], rng, n_boot),
                "median_review_cycles": boot_stat(prs["cycles"][m].astype(float), rng, n_boot, np.median),
            }
        )

    trend_x = []
    trend_y = []
    trend_w = []
    for row in period_rows:
        block = row.get("merge_rate_decided")
        if not row.get("available") or row.get("right_censored") or not block or block.get("estimate") is None:
            continue
        if block["n"] < 30:
            continue
        trend_x.append(row["year"])
        trend_y.append(block["estimate"])
        trend_w.append(block["n"])
    trend_x_a = np.asarray(trend_x, dtype=float)
    trend_y_a = np.asarray(trend_y, dtype=float)
    trend_w_a = np.asarray(trend_w, dtype=float)
    slope = _weighted_slope(trend_x_a, trend_y_a, trend_w_a)
    slope_draws = []
    if trend_x_a.size >= 3 and n_boot > 0:
        for _ in range(n_boot):
            take = rng.integers(0, trend_x_a.size, size=trend_x_a.size)
            slope_draws.append(_weighted_slope(trend_x_a[take], trend_y_a[take], trend_w_a[take]))
    slope_ci = _boot_coef([s for s in slope_draws if s is not None])
    if slope_ci and slope is not None:
        slope_ci["estimate"] = slope
        slope_ci["n_years"] = int(trend_x_a.size)
        slope_ci["years_excluded_as_right_censored"] = [r["year"] for r in period_rows if r.get("right_censored")]

    # --- author table shared by 2, 4, 7 ---
    author_rows = []
    for author, idxs in prs["by_author"].items():
        first = float(created[idxs[0]])
        year = int(years[idxs[0]])
        entry = first_entry.get(author)
        became = entry is not None and entry > first + 1
        horizon = first + HORIZON_DAYS[24] * DAY
        observable24 = dataset_end >= horizon
        active24 = any(float(created[i]) >= horizon for i in idxs) if observable24 else False
        left = (entry is None) and observable24 and (not active24)
        window = [i for i in idxs if float(created[i]) <= first + 365.25 * DAY]
        mer_vals = [float(merge[i]) for i in window if math.isfinite(float(merge[i]))]
        sent_vals = [float(prs["sentiment"][i]) for i in window if math.isfinite(float(prs["sentiment"][i]))]
        merged_at = None
        for i in idxs:
            if int(outcome[i]) == 1 and math.isfinite(float(prs["decision_h"][i])):
                merged_at = float(created[i]) + float(prs["decision_h"][i]) * 3600.0
                break
            if int(outcome[i]) == 1:
                merged_at = float(created[i])
                break
        author_rows.append(
            {
                "author": author,
                "first": first,
                "year": year,
                "became": became,
                "left": left,
                "observable24": observable24,
                "merge_rate": float(np.mean(mer_vals)) if mer_vals else math.nan,
                "n_decided": len(mer_vals),
                "n_merged": float(np.sum(mer_vals)) if mer_vals else 0.0,
                "tone": float(np.mean(sent_vals)) if sent_vals else math.nan,
                "merged_at": merged_at,
            }
        )

    became_rows = [r for r in author_rows if r["became"] and math.isfinite(r["merge_rate"])]
    left_rows = [r for r in author_rows if r["left"] and math.isfinite(r["merge_rate"])]
    raw_merge_gap = None
    raw_d = None
    if became_rows and left_rows:
        b_rates = np.asarray([r["merge_rate"] for r in became_rows], dtype=float)
        l_rates = np.asarray([r["merge_rate"] for r in left_rows], dtype=float)
        raw_merge_gap = float(b_rates.mean() - l_rates.mean())
        raw_d = cohens_d(b_rates, l_rates)

    def _cohort_key(year: int, width: int) -> int:
        return (year // width) * width

    def _cohort_table(width: int) -> Dict[str, Any]:
        buckets: Dict[int, Dict[str, List]] = defaultdict(lambda: {"b_rate": [], "l_rate": [], "b_tone": [], "l_tone": [], "b_s": 0.0, "b_n": 0, "l_s": 0.0, "l_n": 0, "b_people": 0, "l_people": 0})
        for row, side in ((became_rows, "b"), (left_rows, "l")):
            for rec in row:
                key = _cohort_key(rec["year"], width)
                buckets[key][f"{side}_rate"].append(rec["merge_rate"])
                buckets[key][f"{side}_people"] += 1
                buckets[key][f"{side}_s"] += rec["n_merged"]
                buckets[key][f"{side}_n"] += rec["n_decided"]
                if math.isfinite(rec["tone"]):
                    buckets[key][f"{side}_tone"].append(rec["tone"])
        strata = []
        mh_tables = []
        person_tables = []
        for key in sorted(buckets):
            bucket = buckets[key]
            b_rate = np.asarray(bucket["b_rate"], dtype=float)
            l_rate = np.asarray(bucket["l_rate"], dtype=float)
            usable = b_rate.size >= 3 and l_rate.size >= 10
            gap = float(b_rate.mean() - l_rate.mean()) if b_rate.size and l_rate.size else None
            d_val = cohens_d(b_rate, l_rate) if usable else None
            label = f"{key}-{key + width - 1}" if width > 1 else str(key)
            strata.append(
                {
                    "cohort": label,
                    "start_year": key,
                    "n_became": int(b_rate.size),
                    "n_left": int(l_rate.size),
                    "usable": usable,
                    "merge_gap_became_minus_left": gap,
                    "cohens_d": d_val,
                    "effect_size_flag": effect_flag(d_val),
                    "mean_became": float(b_rate.mean()) if b_rate.size else None,
                    "mean_left": float(l_rate.mean()) if l_rate.size else None,
                }
            )
            if bucket["b_n"] and bucket["l_n"]:
                mh_tables.append((int(bucket["b_n"]), float(bucket["b_s"]), int(bucket["l_n"]), float(bucket["l_s"])))
            if b_rate.size and l_rate.size:
                person_tables.append((int(b_rate.size), float(b_rate.sum()), int(l_rate.size), float(l_rate.sum())))
        usable_strata = [s for s in strata if s["usable"] and s["merge_gap_became_minus_left"] is not None]
        weights = []
        gaps = []
        ds = []
        d_w = []
        for s in usable_strata:
            w = (s["n_became"] * s["n_left"]) / (s["n_became"] + s["n_left"])
            weights.append(w)
            gaps.append(s["merge_gap_became_minus_left"])
            if s["cohens_d"] is not None:
                ds.append(s["cohens_d"])
                d_w.append(w)
        pooled_gap = float(np.average(gaps, weights=weights)) if weights else None
        pooled_d = float(np.average(ds, weights=d_w)) if d_w else None
        return {
            "width_years": width,
            "strata": strata,
            "n_usable_strata": len(usable_strata),
            "pooled_person_rate_gap": pooled_gap,
            "pooled_cohens_d": pooled_d,
            "pooled_d_effect_size_flag": effect_flag(pooled_d),
            "mantel_haenszel_risk_difference_person": mantel_haenszel_rd(person_tables),
            "mantel_haenszel_risk_difference_first_year_prs": mantel_haenszel_rd(mh_tables),
            "mantel_haenszel_odds_ratio_first_year_prs": mantel_haenszel_or(mh_tables),
            "note": "Usable stratum: at least 3 later-top-20 people and 10 leavers. MH risk difference uses Mantel-Haenszel weights n1*n0/n. PR-level MH counts decided PRs in the first year. Person-level MH treats each contributor's first-year merge rate as successes/n.",
        }

    cohort_1 = _cohort_table(1)
    cohort_2 = _cohort_table(2)
    # cohort fixed effects on the person-level rates, 2-year cohorts
    fe_sample = [r for r in became_rows + left_rows if math.isfinite(r["merge_rate"])]
    fe_y = np.asarray([r["merge_rate"] for r in fe_sample], dtype=float)
    fe_g = np.asarray([1.0 if r["became"] else 0.0 for r in fe_sample], dtype=float)
    fe_c = np.asarray([_cohort_key(r["year"], 2) for r in fe_sample], dtype=int)
    fe_merge = _ols_group_coef(fe_y, fe_g, fe_c)
    tone_sample = [r for r in fe_sample if math.isfinite(r["tone"])]
    fe_tone = _ols_group_coef(
        np.asarray([r["tone"] for r in tone_sample], dtype=float),
        np.asarray([1.0 if r["became"] else 0.0 for r in tone_sample], dtype=float),
        np.asarray([_cohort_key(r["year"], 2) for r in tone_sample], dtype=int),
    )
    fe_merge_draws = []
    if fe_y.size and n_boot > 0:
        for _ in range(n_boot):
            take = rng.integers(0, fe_y.size, size=fe_y.size)
            fe_merge_draws.append(_ols_group_coef(fe_y[take], fe_g[take], fe_c[take]))
    fe_merge_ci = _boot_coef(fe_merge_draws)
    if fe_merge_ci and fe_merge is not None:
        fe_merge_ci["estimate"] = fe_merge
    raw_tone_gap = None
    if tone_sample:
        bt = np.asarray([r["tone"] for r in tone_sample if r["became"]], dtype=float)
        lt = np.asarray([r["tone"] for r in tone_sample if not r["became"]], dtype=float)
        raw_tone_gap = float(bt.mean() - lt.mean()) if bt.size and lt.size else None
    fraction_gap_left = None
    fraction_d_left = None
    if raw_merge_gap not in (None, 0) and fe_merge is not None:
        fraction_gap_left = fe_merge / raw_merge_gap
    if raw_d not in (None, 0) and cohort_2.get("pooled_cohens_d") is not None:
        fraction_d_left = cohort_2["pooled_cohens_d"] / raw_d
    became_years = {}
    left_years = {}
    for rec in author_rows:
        if rec["became"]:
            became_years[rec["year"]] = became_years.get(rec["year"], 0) + 1
        if rec["left"]:
            left_years[rec["year"]] = left_years.get(rec["year"], 0) + 1

    # --- 3. logistic year FE ---
    logger.info("v2 logistic year fixed effects")
    defined = group >= 0
    decided = outcome >= 0
    est_mask = defined & decided
    y_est = merge[est_mask]
    g_est = group[est_mask].astype(float)
    log_lines = np.log1p(prs["lines"][est_mask].astype(float))
    files_est = prs["files"][est_mask].astype(float)
    prior_est = prs["prior"][est_mask].astype(float)
    year_est = years[est_mask]
    year_levels = sorted(set(int(v) for v in year_est))
    ref_year = year_levels[0] if year_levels else None

    def _design(idx: np.ndarray, with_year: bool) -> np.ndarray:
        cols = [
            np.ones(idx.size),
            g_est[idx],
            log_lines[idx],
            files_est[idx],
            prior_est[idx],
        ]
        if with_year and ref_year is not None:
            ysub = year_est[idx]
            for lev in year_levels:
                if lev == ref_year:
                    continue
                cols.append((ysub == lev).astype(float))
        return np.column_stack(cols)

    def _coef_boot(with_year: bool) -> Dict[str, Any]:
        if y_est.size < 50 or np.unique(g_est).size < 2:
            return {"available": False, "reason": "DATA UNAVAILABLE: estimation sample has fewer than 50 decided PRs or only one group."}
        full = np.arange(y_est.size)
        beta = logistic_irls(_design(full, with_year), y_est)
        if beta is None:
            return {"available": False, "reason": "DATA UNAVAILABLE: logistic IRLS did not converge."}
        draws = []
        for _ in range(n_boot):
            take = rng.integers(0, y_est.size, size=y_est.size)
            if np.unique(g_est[take]).size < 2:
                continue
            fitted = logistic_irls(_design(take, with_year), y_est[take])
            if fitted is not None and math.isfinite(float(fitted[1])):
                draws.append(float(fitted[1]))
        clean = np.asarray(draws, dtype=float)
        ci = None
        if clean.size:
            lo, hi = np.quantile(clean, [0.025, 0.975])
            ci = [float(lo), float(hi)]
        point = float(beta[1])
        return {
            "available": True,
            "in_group_log_odds": point,
            "odds_ratio": float(math.exp(point)),
            "ci95_log_odds": ci,
            "n": int(y_est.size),
            "n_bootstrap_fits": int(clean.size),
            "reference_year": ref_year,
            "controls": ["log1p(lines changed)", "files touched", "prior PR count"],
            "year_fixed_effects": with_year,
        }

    logit_no_year = _coef_boot(False)
    logit_year = _coef_boot(True)

    # --- 4. drawbridge ---
    logger.info("v2 incumbent versus newcomer")
    first_of = np.array([float(created[prs["by_author"][a][0]]) for a in prs["authors"]], dtype=float)
    age_days = (created - first_of) / DAY
    newcomer = age_days <= 365.25
    incumbent = age_days >= (3 * 365.25)
    draw_rows = []
    for year in range(2010, 2027):
        m = years == year
        cell = {"year": year}
        for label, mask_g in (("newcomer", newcomer), ("incumbent", incumbent)):
            mm = m & mask_g
            if int(mm.sum()) == 0:
                cell[label] = {"n": 0, "available": False}
                continue
            cell[label] = {
                "available": True,
                "n": int(mm.sum()),
                "merge_rate_decided": boot_mean(merge[mm], rng, n_boot),
                "no_peer_response_rate": boot_mean(no_response[mm], rng, n_boot),
            }
        draw_rows.append(cell)

    both = newcomer | incumbent
    inter_rows = []
    for label, yvec in (("merge", merge), ("no_response", no_response)):
        m = both & np.isfinite(yvec)
        censored_years = {r["year"] for r in period_rows if r.get("right_censored")}
        m = m & np.array([int(y) not in censored_years for y in years])
        if int(m.sum()) < 50:
            inter_rows.append({"outcome": label, "available": False, "reason": "DATA UNAVAILABLE: fewer than 50 newcomer/incumbent PRs."})
            continue
        y = yvec[m]
        new = newcomer[m].astype(float)
        yr = years[m].astype(float) - 2010.0
        x_full = np.column_stack([np.ones(y.size), new, yr, new * yr])

        def _inter(idx: np.ndarray) -> Optional[float]:
            if np.unique(new[idx]).size < 2:
                return None
            coef, *_rest = np.linalg.lstsq(x_full[idx], y[idx], rcond=None)
            return float(coef[3])

        point = _inter(np.arange(y.size))
        draws = [_inter(rng.integers(0, y.size, size=y.size)) for _ in range(n_boot)]
        clean = np.asarray([d for d in draws if d is not None and math.isfinite(d)], dtype=float)
        ci = None
        if clean.size:
            lo, hi = np.quantile(clean, [0.025, 0.975])
            ci = [float(lo), float(hi)]
        inter_rows.append(
            {
                "outcome": label,
                "available": point is not None,
                "model": "linear probability: outcome ~ newcomer + year_since_2010 + newcomer x year_since_2010",
                "interaction_per_year": point,
                "ci95": ci,
                "n": int(y.size),
                "reading": (
                    "For merge rate, a negative interaction means the incumbent advantage widens each year. "
                    "For no-response, a positive interaction means newcomers go unanswered more often as years pass."
                    if point is not None
                    else "DATA UNAVAILABLE"
                ),
            }
        )

    # --- 5. rolling top 20 ---
    logger.info("v2 rolling 24-month top-%s", top_n)
    window = HORIZON_DAYS[24] * DAY
    rflags, r_entry, r_top, r_defined_ts = walk_rolling(
        prs["review_events"], created.tolist(), prs["authors"], top_n, window
    )
    rgroup = np.full(n, -1, dtype=np.int8)
    for i, flag in enumerate(rflags):
        if flag is True:
            rgroup[i] = 1
        elif flag is False:
            rgroup[i] = 0
    r_defined = rgroup >= 0
    r_primary = r_defined & (created >= ERA_2016)
    vocab_total = prs["vocab"].sum(axis=1).astype(float)
    rolling_block = {
        "merge_rate_decided_from_2016": compare(merge[r_primary & decided & (rgroup == 1)], merge[r_primary & decided & (rgroup == 0)], rng, n_boot, "rate"),
        "mean_tone_from_2016": compare(prs["sentiment"][r_primary & (rgroup == 1)], prs["sentiment"][r_primary & (rgroup == 0)], rng, n_boot, "score"),
        "no_peer_response_from_2016": compare(no_response[r_primary & (rgroup == 1)], no_response[r_primary & (rgroup == 0)], rng, n_boot, "rate"),
        "hours_to_first_response_from_2016": compare(prs["response_h"][r_primary & (rgroup == 1)], prs["response_h"][r_primary & (rgroup == 0)], rng, n_boot, "hours"),
        "median_comparison_note": "Review-cycle medians are in the period table. This block matches pass-1 means.",
        "peer_review_object_count_from_2016": compare(prs["cycles"][r_primary & (rgroup == 1)].astype(float), prs["cycles"][r_primary & (rgroup == 0)].astype(float), rng, n_boot, "count"),
        "justification_hits_per_pr_from_2016": compare(vocab_total[r_primary & (rgroup == 1)], vocab_total[r_primary & (rgroup == 0)], rng, n_boot, "count"),
        "any_negative_tone_from_2016": compare(prs["negative"][r_primary & (rgroup == 1)], prs["negative"][r_primary & (rgroup == 0)], rng, n_boot, "rate"),
    }
    submit_counts: Dict[str, int] = defaultdict(int)
    for author in prs["authors"]:
        submit_counts[author] += 1
    top_submitters = [a for a, _c in sorted(submit_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:top_n]]
    overlap_n = len(set(r_top) & set(top_submitters))
    entry_counts: Dict[int, int] = defaultdict(int)
    for ts in r_entry.values():
        entry_counts[datetime.fromtimestamp(ts, tz=timezone.utc).year] += 1
    reviews_by_year: Dict[int, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for ts, who in prs["review_events"]:
        reviews_by_year[datetime.fromtimestamp(ts, tz=timezone.utc).year][who] += 1
    entry_rows = []
    for year in range(2010, 2027):
        reviewers = reviews_by_year.get(year) or {}
        denom = len(reviewers)
        entrants = entry_counts.get(year, 0)
        entry_rows.append(
            {
                "year": year,
                "new_entrants": entrants,
                "distinct_reviewers": denom,
                "entry_rate_among_reviewers": (entrants / denom) if denom else None,
            }
        )

    # --- 6. review capacity ---
    prs_by_year = {int(y): int((years == y).sum()) for y in range(2010, 2027)}
    capacity_rows = []
    xs = []
    ys = []
    for year in range(2010, 2027):
        counts = reviews_by_year.get(year) or {}
        active = [who for who, c in counts.items() if c >= 5]
        total_reviews = sum(counts.values())
        top5 = sorted(counts.values(), reverse=True)[:5]
        share = (sum(top5) / total_reviews) if total_reviews else None
        per = (prs_by_year[year] / len(active)) if active else None
        new_cell = next((c["newcomer"] for c in draw_rows if c["year"] == year), {})
        new_nr = None
        if new_cell.get("available") and new_cell.get("no_peer_response_rate"):
            new_nr = new_cell["no_peer_response_rate"].get("estimate")
        capacity_rows.append(
            {
                "year": year,
                "prs_opened": prs_by_year[year],
                "active_reviewers_5plus": len(active),
                "prs_per_active_reviewer": per,
                "top5_review_share": share,
                "newcomer_no_response_rate": new_nr,
            }
        )
        if per is not None and new_nr is not None and len(active) > 0 and prs_by_year[year] >= 30:
            xs.append(per)
            ys.append(new_nr)
    corr = None
    corr_ci = None
    if len(xs) >= 5:
        x_a = np.asarray(xs, dtype=float)
        y_a = np.asarray(ys, dtype=float)
        x_c = x_a - x_a.mean()
        y_c = y_a - y_a.mean()
        denom = math.sqrt(float((x_c * x_c).sum() * (y_c * y_c).sum()))
        corr = float((x_c * y_c).sum() / denom) if denom else None
        draws = []
        for _ in range(n_boot):
            take = rng.integers(0, x_a.size, size=x_a.size)
            xx = x_a[take]
            yy = y_a[take]
            xc = xx - xx.mean()
            yc = yy - yy.mean()
            d = math.sqrt(float((xc * xc).sum() * (yc * yc).sum()))
            if d:
                draws.append(float((xc * yc).sum() / d))
        if draws:
            lo, hi = np.quantile(np.asarray(draws), [0.025, 0.975])
            corr_ci = [float(lo), float(hi)]
    else:
        unavailable.append(
            {
                "metric": "review_capacity_correlation",
                "reason": "DATA UNAVAILABLE: fewer than 5 years have both an active-reviewer ratio and a newcomer no-response rate.",
            }
        )

    # --- 7. time to first merge ---
    ttf_rows = []
    for year in range(2010, 2027):
        members = [r for r in author_rows if r["year"] == year]
        if not members:
            ttf_rows.append({"year": year, "n": 0, "available": False})
            continue
        days = []
        for rec in members:
            if rec["merged_at"] is None:
                continue
            days.append((rec["merged_at"] - rec["first"]) / DAY)
        observable = [r for r in members if r["observable24"]]
        never = []
        for rec in observable:
            if rec["merged_at"] is None or rec["merged_at"] > rec["first"] + HORIZON_DAYS[24] * DAY:
                never.append(1.0)
            else:
                never.append(0.0)
        ttf_rows.append(
            {
                "year": year,
                "available": True,
                "n_authors": len(members),
                "n_eventually_merged": len(days),
                "median_days_to_first_merge_among_those_who_merged": boot_stat(np.asarray(days, dtype=float), rng, n_boot, np.median),
                "n_observable_24m": len(observable),
                "share_never_merged_within_24m": boot_mean(np.asarray(never, dtype=float), rng, n_boot) if never else None,
            }
        )

    # slopes for incumbents and newcomers, uncensored years
    def _group_slope(label: str) -> Dict[str, Any]:
        gx, gy, gw = [], [], []
        for row in draw_rows:
            cell = row.get(label) or {}
            block = cell.get("merge_rate_decided") if cell.get("available") else None
            period = next((p for p in period_rows if p["year"] == row["year"]), {})
            if not block or block.get("estimate") is None or period.get("right_censored") or block["n"] < 20:
                continue
            gx.append(row["year"])
            gy.append(block["estimate"])
            gw.append(block["n"])
        xa, ya, wa = np.asarray(gx, float), np.asarray(gy, float), np.asarray(gw, float)
        point = _weighted_slope(xa, ya, wa)
        draws = []
        if xa.size >= 3:
            for _ in range(n_boot):
                take = rng.integers(0, xa.size, size=xa.size)
                draws.append(_weighted_slope(xa[take], ya[take], wa[take]))
        ci = _boot_coef([d for d in draws if d is not None])
        if ci and point is not None:
            ci["estimate"] = point
        return {"slope_merge_rate_per_year": point, "ci": ci, "n_years": int(xa.size)}

    inc_slope = _group_slope("incumbent")
    new_slope = _group_slope("newcomer")

    def _ci_entirely(ci: Optional[List[float]], sign: str) -> bool:
        if not ci or ci[0] is None:
            return False
        if sign == "neg":
            return ci[1] < 0
        return ci[0] > 0

    slope_neg = bool(slope_ci and _ci_entirely(slope_ci.get("ci95"), "neg"))
    inc_neg = bool(inc_slope["ci"] and _ci_entirely(inc_slope["ci"].get("ci95"), "neg"))
    new_neg = bool(new_slope["ci"] and _ci_entirely(new_slope["ci"].get("ci95"), "neg"))
    merge_inter = next((r for r in inter_rows if r["outcome"] == "merge"), {})
    nr_inter = next((r for r in inter_rows if r["outcome"] == "no_response"), {})
    widen_merge = bool(merge_inter.get("available") and _ci_entirely(merge_inter.get("ci95"), "neg"))
    widen_nr = bool(nr_inter.get("available") and _ci_entirely(nr_inter.get("ci95"), "pos"))
    capacity_pos = bool(corr_ci and _ci_entirely(corr_ci, "pos"))
    residual = bool(logit_year.get("available") and _ci_entirely(logit_year.get("ci95_log_odds"), "pos"))

    supported = []
    if slope_neg and (inc_neg or new_neg):
        supported.append("universal_tightening")
    if widen_merge or widen_nr:
        supported.append("differential_tightening_against_newcomers")
    if capacity_pos:
        supported.append("review_capacity_starvation")
    if residual:
        supported.append("residual_group_gap_after_period_control")
    if not supported:
        supported.append("none_of_the_four_cleared_its_pre_set_bar")

    interpretation = {
        "supported": supported,
        "rules": {
            "universal_tightening": "Weighted slope of annual decided merge rate on calendar year is entirely below 0, on years whose open share is at most 20%, and at least one of incumbent or newcomer slopes is also entirely below 0.",
            "differential_tightening_against_newcomers": "The newcomer x year interaction is entirely below 0 for merge rate, or entirely above 0 for no-response rate.",
            "review_capacity_starvation": "Across years, PRs per active reviewer (5+ reviews) correlates with the newcomer no-response rate and the bootstrap interval is entirely above 0.",
            "residual_group_gap_after_period_control": "The in-group log-odds coefficient in the logistic model with year fixed effects, log1p(lines), files, and prior PR count has a bootstrap interval entirely above 0.",
        },
        "more_than_one_allowed": True,
        "text": (
            "These four readings can hold together. A falling merge rate for incumbents and newcomers is universal tightening. "
            "A negative newcomer-by-year interaction on top of that is differential tightening. "
            "A positive capacity correlation is starvation. "
            "An in-group coefficient that stays positive with year fixed effects is a residual group gap. "
            "None of these is a psychological finding."
        ),
    }

    result = {
        "pin": (
            "Pass 2 asks whether the pass-1 group gap is calendar time, a higher bar for newcomers, "
            "review capacity, or a gap that remains after year controls. "
            "In-group in sections 2 and 3 is still the cumulative top 20. Section 5 replaces that with a trailing 24-month top 20. "
            "This file does not show that rejection sensitive dysphoria caused any outcome."
        ),
        "version": "2.0",
        "parameters": {
            "top_n": top_n,
            "bootstrap": n_boot,
            "seed": seed,
            "rolling_window_days": HORIZON_DAYS[24],
            "newcomer_days": 365.25,
            "incumbent_days": 3 * 365.25,
            "right_censor_open_share": 0.20,
        },
        "data_sources": {"prs": pr_source, "n_prs_used": n, "n_pr_rows_read": prs["n_rows_read"]},
        "period_trend": {
            "years": period_rows,
            "merge_rate_slope_per_year": slope_ci,
            "note": "Merge rate is among decided PRs. Open PRs are out of that denominator. Years with open share above 20% are marked right-censored and left out of the slope.",
        },
        "cohort_control": {
            "raw_first_year_merge_gap_became_minus_left": raw_merge_gap,
            "raw_cohens_d": raw_d,
            "raw_effect_size_flag": effect_flag(raw_d),
            "pass1_reported_d": 0.88,
            "one_year_cohorts": cohort_1,
            "two_year_cohorts": cohort_2,
            "cohort_fe_merge_rate_two_year": fe_merge_ci,
            "cohort_fe_tone_two_year": fe_tone,
            "raw_tone_gap": raw_tone_gap,
            "fraction_of_raw_merge_gap_remaining_after_two_year_fe": fraction_gap_left,
            "fraction_of_raw_d_remaining_as_pooled_within_cohort_d": fraction_d_left,
            "entry_year_became": became_years,
            "entry_year_left": left_years,
            "n_became": len(became_rows),
            "n_left": len(left_rows),
            "note": "The pass-1 d=0.88 is the unadjusted person-level first-year merge contrast. Fraction remaining uses the recomputed raw gap in this run, not a hardcoded 0.88, and is reported next to that pass-1 figure.",
        },
        "year_controlled_group_gap": {
            "without_year_fixed_effects": logit_no_year,
            "with_year_fixed_effects": logit_year,
            "sample": "Decided PRs whose cumulative top-20 status is already defined. Open PRs and unidentified early PRs are excluded.",
        },
        "drawbridge": {
            "by_year": draw_rows,
            "interaction": inter_rows,
            "incumbent_merge_slope": inc_slope,
            "newcomer_merge_slope": new_slope,
            "definition": "Newcomer: this PR is within 12 months of the author's first PR. Incumbent: the author's first PR was at least 3 years earlier. Authors in between are in neither series.",
        },
        "rolling_ingroup": {
            "window": "trailing 24 months, reviews strictly before the PR",
            "n_ever_entered": len(r_entry),
            "entry_by_year": entry_rows,
            "defined_through": datetime.fromtimestamp(r_defined_ts, tz=timezone.utc).isoformat() if r_defined_ts else None,
            "final_rolling_top": [ident.label(x) for x in r_top],
            "overlap_with_top_submitters": {
                "overlap_count": overlap_n,
                "top_n": top_n,
                "overlap": (overlap_n / top_n) if top_n else None,
                "flag_above_half": overlap_n / top_n > 0.5 if top_n else False,
            },
            "block_a": rolling_block,
            "n_primary_prs": int(r_primary.sum()),
        },
        "review_capacity": {
            "by_year": capacity_rows,
            "correlation_prs_per_reviewer_with_newcomer_no_response": {
                "pearson_r": corr,
                "ci95": corr_ci,
                "n_years": len(xs),
                "effect_note": "The unit is the calendar year. The interval resamples years.",
            },
        },
        "time_to_first_merge": {
            "by_entry_year": ttf_rows,
            "note": "Median days are among authors who eventually merged, from first PR open time to that PR's merge time. The 24-month share is among authors observable for 24 months and counts a merge only if merge time falls inside the window.",
        },
        "interpretation": interpretation,
        "data_unavailable": unavailable,
    }
    result["plain_text_summary"] = render_v2(result)
    return _jsonable(result)


def render_v2(data: Dict[str, Any]) -> str:
    lines = [data["pin"], ""]
    lines.append("1. PERIOD TREND (decided merge rate; tone; no response; median review cycles)")
    for row in data["period_trend"]["years"]:
        if not row.get("available"):
            lines.append(f"  {row['year']}: DATA UNAVAILABLE")
            continue
        censor = " right-censored" if row.get("right_censored") else ""
        lines.append(
            f"  {row['year']}: n={row['n']} open={100 * row['open_share']:.0f}%{censor} "
            f"merge {_fmt_est(row.get('merge_rate_decided'), 'rate')} | "
            f"tone {_fmt_est(row.get('mean_tone'), 'score')} | "
            f"no-response {_fmt_est(row.get('no_peer_response_rate'), 'rate')} | "
            f"median cycles {_fmt_est(row.get('median_review_cycles'), 'count')}"
        )
    slope = data["period_trend"].get("merge_rate_slope_per_year") or {}
    if slope.get("estimate") is not None:
        ci = slope.get("ci95") or [None, None]
        lines.append(
            f"  slope of decided merge rate per year, uncensored years: {slope['estimate']:.4f} "
            f"(95% CI {ci[0]:.4f}–{ci[1]:.4f}) n_years={slope.get('n_years')}"
        )
    else:
        lines.append("  slope: DATA UNAVAILABLE")

    cc = data["cohort_control"]
    lines.append("")
    lines.append("2. COHORT CONTROL")
    lines.append(
        f"  recomputed raw first-year merge gap (later top-20 minus leavers): {cc.get('raw_first_year_merge_gap_became_minus_left')} "
        f"Cohen's d={cc.get('raw_cohens_d')} {cc.get('raw_effect_size_flag')} "
        f"(pass 1 reported d={cc.get('pass1_reported_d')})"
    )
    lines.append(
        f"  two-year FE merge gap: {_fmt_est(cc.get('cohort_fe_merge_rate_two_year'), 'score')} "
        f"fraction of raw gap remaining={cc.get('fraction_of_raw_merge_gap_remaining_after_two_year_fe')}"
    )
    lines.append(
        f"  two-year pooled within-cohort d={cc['two_year_cohorts'].get('pooled_cohens_d')} "
        f"{cc['two_year_cohorts'].get('pooled_d_effect_size_flag')} "
        f"fraction of raw d remaining={cc.get('fraction_of_raw_d_remaining_as_pooled_within_cohort_d')}"
    )
    lines.append(
        f"  MH risk difference, person rates, 2-year={cc['two_year_cohorts'].get('mantel_haenszel_risk_difference_person')} "
        f"PR-level={cc['two_year_cohorts'].get('mantel_haenszel_risk_difference_first_year_prs')} "
        f"MH odds ratio PR-level={cc['two_year_cohorts'].get('mantel_haenszel_odds_ratio_first_year_prs')}"
    )
    lines.append(f"  tone FE coefficient (2-year)={cc.get('cohort_fe_tone_two_year')} raw tone gap={cc.get('raw_tone_gap')}")
    lines.append("  within 2-year cohorts:")
    for s in cc["two_year_cohorts"]["strata"]:
        gap = s["merge_gap_became_minus_left"]
        gap_s = "n/a" if gap is None else f"{gap:.3f}"
        d_s = "n/a" if s["cohens_d"] is None else f"{s['cohens_d']:.2f}"
        lines.append(
            f"    {s['cohort']}: became n={s['n_became']} left n={s['n_left']} "
            f"gap={gap_s} d={d_s} {s['effect_size_flag']} usable={s['usable']}"
        )
    lines.append("  entry years, later top-20: " + ", ".join(f"{y}:{c}" for y, c in sorted(cc["entry_year_became"].items())))
    lines.append("  entry years, leavers: " + ", ".join(f"{y}:{c}" for y, c in sorted(cc["entry_year_left"].items())))

    lines.append("")
    lines.append("3. YEAR-CONTROLLED GROUP GAP (logistic, in-group log-odds)")
    for label, block in (
        ("without year FE", data["year_controlled_group_gap"]["without_year_fixed_effects"]),
        ("with year FE", data["year_controlled_group_gap"]["with_year_fixed_effects"]),
    ):
        if not block.get("available"):
            lines.append(f"  {label}: {block.get('reason')}")
            continue
        ci = block.get("ci95_log_odds")
        ci_s = "n/a" if not ci else f"{ci[0]:.3f}–{ci[1]:.3f}"
        lines.append(
            f"  {label}: log-odds {block['in_group_log_odds']:.3f} (95% CI {ci_s}) "
            f"OR {block['odds_ratio']:.3f} n={block['n']}"
        )

    lines.append("")
    lines.append("4. DIFFERENTIAL TIGHTENING")
    for row in data["drawbridge"]["by_year"]:
        bits = [str(row["year"])]
        for label in ("incumbent", "newcomer"):
            cell = row.get(label) or {}
            if not cell.get("available"):
                bits.append(f"{label}=n/a")
                continue
            bits.append(
                f"{label} n={cell['n']} merge {_fmt_est(cell.get('merge_rate_decided'), 'rate')} "
                f"no-response {_fmt_est(cell.get('no_peer_response_rate'), 'rate')}"
            )
        lines.append("  " + " | ".join(bits))
    for block in data["drawbridge"]["interaction"]:
        if not block.get("available"):
            lines.append(f"  interaction {block.get('outcome')}: {block.get('reason')}")
            continue
        ci = block.get("ci95")
        ci_s = "n/a" if not ci else f"{ci[0]:.4f}–{ci[1]:.4f}"
        lines.append(f"  interaction {block['outcome']} per year: {block['interaction_per_year']:.4f} (95% CI {ci_s}) n={block['n']}")
    for label in ("incumbent_merge_slope", "newcomer_merge_slope"):
        block = data["drawbridge"][label]
        ci = (block.get("ci") or {}).get("ci95")
        point = block.get("slope_merge_rate_per_year")
        if point is None:
            lines.append(f"  {label}: DATA UNAVAILABLE")
        else:
            ci_s = "n/a" if not ci else f"{ci[0]:.4f}–{ci[1]:.4f}"
            lines.append(f"  {label}: {point:.4f} per year (95% CI {ci_s}) n_years={block.get('n_years')}")

    roll = data["rolling_ingroup"]
    lines.append("")
    lines.append("5. ROLLING IN-GROUP (trailing 24 months)")
    lines.append(f"  distinct people who ever enter: {roll['n_ever_entered']}")
    ov = roll["overlap_with_top_submitters"]
    lines.append(
        f"  overlap with top submitters: {ov['overlap_count']}/{ov['top_n']} "
        f"flagged_above_half={ov['flag_above_half']}"
    )
    lines.append("  final rolling top: " + ", ".join(roll["final_rolling_top"]))
    lines.append("  Block A, 2016+, rolling label")
    for key, comp in roll["block_a"].items():
        if not isinstance(comp, dict) or "cohens_d" not in comp:
            continue
        lines.append(f"  {key}")
        lines.extend(_fmt_cmp(comp))
    lines.append("  entry rate by year (new entrants / distinct reviewers):")
    for row in roll["entry_by_year"]:
        rate = row["entry_rate_among_reviewers"]
        rate_s = "n/a" if rate is None else f"{100 * rate:.1f}%"
        if row["new_entrants"] or row["distinct_reviewers"]:
            lines.append(f"    {row['year']}: entrants {row['new_entrants']} / reviewers {row['distinct_reviewers']} = {rate_s}")

    lines.append("")
    lines.append("6. REVIEW CAPACITY")
    for row in data["review_capacity"]["by_year"]:
        if row["prs_opened"] == 0 and row["active_reviewers_5plus"] == 0:
            continue
        per = row["prs_per_active_reviewer"]
        share = row["top5_review_share"]
        per_s = "n/a" if per is None else f"{per:.1f}"
        share_s = "n/a" if share is None else f"{100 * share:.0f}%"
        nr = row["newcomer_no_response_rate"]
        nr_s = "n/a" if nr is None else f"{100 * nr:.1f}%"
        lines.append(
            f"  {row['year']}: PRs {row['prs_opened']} active {row['active_reviewers_5plus']} "
            f"PRs/reviewer {per_s} top5 share {share_s} newcomer no-response {nr_s}"
        )
    corr = data["review_capacity"]["correlation_prs_per_reviewer_with_newcomer_no_response"]
    if corr.get("pearson_r") is None:
        lines.append("  correlation: DATA UNAVAILABLE")
    else:
        ci = corr.get("ci95")
        ci_s = "n/a" if not ci else f"{ci[0]:.2f}–{ci[1]:.2f}"
        lines.append(f"  pearson r(PRs per reviewer, newcomer no-response)={corr['pearson_r']:.2f} (95% CI {ci_s}) n_years={corr['n_years']}")

    lines.append("")
    lines.append("7. TIME TO FIRST MERGE")
    for row in data["time_to_first_merge"]["by_entry_year"]:
        if not row.get("available"):
            continue
        lines.append(
            f"  {row['year']}: authors {row['n_authors']} eventually merged {row['n_eventually_merged']} "
            f"median days {_fmt_est(row.get('median_days_to_first_merge_among_those_who_merged'), 'count')} "
            f"never merged within 24m {_fmt_est(row.get('share_never_merged_within_24m'), 'rate')}"
        )

    lines.append("")
    lines.append("INTERPRETATION")
    interp = data["interpretation"]
    lines.append("Supported: " + ", ".join(interp["supported"]))
    for key, rule in interp["rules"].items():
        mark = "yes" if key in interp["supported"] else "no"
        lines.append(f"  {mark}: {key}. {rule}")
    lines.append(interp["text"])
    if data.get("data_unavailable"):
        lines.append("")
        lines.append("DATA UNAVAILABLE")
        for row in data["data_unavailable"]:
            lines.append(f"- {row['metric']}: {row['reason']}")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Population proxies for in-group filtering hypotheses")
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--bootstrap", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--which", choices=["1", "2", "both"], default="1")
    args = parser.parse_args(argv)
    if args.which in ("1", "both"):
        payload = analyze(top_n=args.top_n, n_boot=args.bootstrap, seed=args.seed)
        print(payload["plain_text_summary"])
        written = save_analysis_json("rsd_ingroup_analysis.json", payload)
        for path in written:
            logger.info("Wrote %s", path)
    if args.which in ("2", "both"):
        payload2 = analyze_v2(top_n=args.top_n, n_boot=args.bootstrap, seed=args.seed)
        print(payload2["plain_text_summary"])
        written2 = save_analysis_json("rsd_ingroup_analysis_v2.json", payload2)
        for path in written2:
            logger.info("Wrote %s", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
