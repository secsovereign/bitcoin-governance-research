#!/usr/bin/env python3
"""Revealed rough consensus — ACK/NACK/review vectors on PRs a merge-key holder merged.

CONTRIBUTING.md assigns the merge judgment to project merge maintainers. This
script does not score legitimacy or IETF-style humming. It reports what the
GitHub thread looked like when a key holder merged, closed, or left open.

Non-key-holders cannot declare merge. Their ACK is a signal the merger may weigh.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Set, Tuple

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.utils.findings_io import save_analysis_json
from src.utils.logger import setup_logger
from src.utils.maintainers import (
    ROLE_CANNOT_MERGE,
    ROLE_MERGE_KEYS,
    ROLE_ROSTER_WITHOUT_KEYS,
    canonicalize_actor,
    person_role,
)
from src.utils.paths import get_data_dir
from src.utils.pr_quality import path_risk_band

try:
    from scripts.analysis.cross_platform_reviews import load_cross_platform_pr_references
except ImportError:  # pragma: no cover
    load_cross_platform_pr_references = None  # type: ignore

logger = setup_logger()

PIN = (
    "Revealed rough consensus is the ACK/NACK/review vector on PRs a merge-key "
    "holder merged. Bitcoin Core CONTRIBUTING.md — not CONTRIBUTORS.md — says "
    "merge rests with project merge maintainers, who judge the general consensus "
    "of contributors and may weigh reviewers by common sense and merit; NACKs "
    "without rationale may be disregarded. This is not IETF rough consensus, not "
    "a vote, and not a legitimacy score. People without merge keys cannot declare "
    "merge; 0 as merger is lack of keys. GitHub Review objects are missing before "
    "2016; peer issue comments and IRC/mail/Delving/Bitcointalk PR mentions are "
    "joined as observed discussion, not as equivalent GitHub ACKs. A #NNNN "
    "mention is not a review. Compare before-2016 vs 2016+ on discussion_observed, "
    "not on zero GitHub Review objects. Closed-unmerged is not interchangeable "
    "with NACK'd."
)


def window_keys(created_at: str) -> Tuple[str, ...]:
    """Bucket by PR created_at. Empty dates stay all_time only."""
    keys = ["all_time"]
    created = created_at or ""
    if created and created < "2016-01-01":
        keys.append("before_2016")
    if created >= "2016-01-01":
        keys.append("from_2016")
    if created >= "2022-01-01":
        keys.append("from_2022")
    return tuple(keys)

_NACK_RE = re.compile(
    r"\b(?:concept\s+nack|approach\s+nack|strong\s+nack|nack)\b", re.I
)
_NACK_HEDGE_RE = re.compile(
    r"\b(not a nack|would nack|removed my nack|nack/ack|ack/nack|"
    r"ack\s*/\s*nack|nack\s*/\s*ack|ready for nack|qualified to nack|"
    r"approach ack\s*/\s*nack)\b",
    re.I,
)
_CONCEPT_ACK_RE = re.compile(r"\b(?:concept|approach)\s+ack\b", re.I)
_UTACK_RE = re.compile(r"\b(?:utack|tested\s+ack)\b", re.I)
_CODE_ACK_RE = re.compile(r"(?<![A-Za-z])ACK\s+[0-9a-fA-F]{6,}\b", re.I)
_NACK_TOKEN_RE = re.compile(
    r"\b(?:concept\s+nack|approach\s+nack|strong\s+nack|nack)\b", re.I
)
_REASON_RE = re.compile(r"\b(?:because|reason|since|due to)\b", re.I)
_BOTS = frozenset({"drahtbot", "bitcoin-core-ai", "github-actions[bot]", "github-actions"})
_PULL_URL_RE = re.compile(r"github\.com/bitcoin/bitcoin/pull/(\d{1,6})\b", re.I)
_INFORMAL_REVIEWISH_RE = re.compile(
    r"\b(?:concept\s+ack|approach\s+ack|utack|tested\s+ack|lgtm|looks good)\b"
    r"|(?<![A-Za-z])ACK\s+[0-9a-fA-F]{6,}\b"
    r"|\b(?:concept\s+nack|approach\s+nack|strong\s+nack|\bnack\b)",
    re.I,
)

ACK_ROLES = (ROLE_MERGE_KEYS, ROLE_ROSTER_WITHOUT_KEYS, ROLE_CANNOT_MERGE)
PATH_BANDS = (
    "consensus_sensitive",
    "networking",
    "security_sensitive",
    "other",
    "unknown",
)
REVIEW_BUCKETS = ("zero", "one", "two_three", "four_plus")


def nack_has_rationale(text: str) -> bool:
    """CONTRIBUTING.md: a NACK needs a rationale; bare NACK may be disregarded."""
    stripped = _NACK_TOKEN_RE.sub(" ", text or "")
    stripped = re.sub(r"\s+", " ", stripped).strip(" \t\n\r:-")
    if len(stripped) >= 40:
        return True
    return bool(_REASON_RE.search(stripped))


def nack_is_stance(text: str) -> bool:
    """True when NACK is an unquoted stance, not an invitation or hedge."""
    blob = text or ""
    if not _NACK_RE.search(blob):
        return False
    if _NACK_HEDGE_RE.search(blob):
        return False
    for line in blob.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(">"):
            continue
        if _NACK_RE.search(line):
            return True
    return False


def classify_text(text: str) -> Dict[str, bool]:
    """Keyword flags for one comment/review body. NACK is not an ACK."""
    blob = text or ""
    nack = nack_is_stance(blob)
    return {
        "nack": nack,
        "nack_rationale": nack_has_rationale(blob) if nack else False,
        "concept_ack": (not nack) and bool(_CONCEPT_ACK_RE.search(blob)),
        "utack": (not nack) and bool(_UTACK_RE.search(blob)),
        "code_ack": (not nack) and bool(_CODE_ACK_RE.search(blob)),
    }


def _iter_review_items(pr: Dict[str, Any]) -> Iterable[Tuple[str, str, str]]:
    for r in pr.get("reviews") or []:
        if not isinstance(r, dict):
            continue
        login = canonicalize_actor(login=r.get("author") or r.get("user"))
        if login in _BOTS:
            continue
        yield (
            login,
            r.get("body") or "",
            (r.get("state") or "").upper(),
        )
    for c in pr.get("comments") or []:
        if not isinstance(c, dict):
            continue
        login = canonicalize_actor(login=c.get("author") or c.get("user"))
        if login in _BOTS:
            continue
        yield (
            login,
            c.get("body") or "",
            "",
        )


def _record_text(record: Dict[str, Any]) -> str:
    return " ".join(
        str(record.get(k) or "")
        for k in ("message", "body", "subject", "content", "cooked_html")
    )


def load_informal_pr_sets() -> Dict[str, Set[int]]:
    """PR numbers mentioned on IRC/mail/Delving/Bitcointalk. Mention ≠ review."""
    any_ids: Set[int] = set()
    reviewish: Set[int] = set()
    by_channel: Dict[str, Set[int]] = {}
    if load_cross_platform_pr_references is None:
        return {"any": any_ids, "reviewish": reviewish}
    refs = load_cross_platform_pr_references()
    for channel, mapping in refs.items():
        ids: Set[int] = set()
        for num, msgs in mapping.items():
            try:
                n = int(num)
            except (TypeError, ValueError):
                continue
            ids.add(n)
            any_ids.add(n)
            for msg in msgs:
                if isinstance(msg, dict) and _INFORMAL_REVIEWISH_RE.search(_record_text(msg)):
                    reviewish.add(n)
                    break
        by_channel[channel] = ids
    # Early PRs are 1–3 digits; the shared extractor only keeps 4–6. Pull URLs are precise.
    irc = get_data_dir() / "irc" / "messages.jsonl"
    if irc.exists():
        with irc.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line.strip():
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue
                text = _record_text(msg)
                for raw in _PULL_URL_RE.findall(text):
                    n = int(raw)
                    any_ids.add(n)
                    by_channel.setdefault("irc", set()).add(n)
                    if _INFORMAL_REVIEWISH_RE.search(text):
                        reviewish.add(n)
    return {"any": any_ids, "reviewish": reviewish, **{f"ch_{k}": v for k, v in by_channel.items()}}


def pr_consensus_vector(
    pr: Dict[str, Any],
    informal_any: Optional[Set[int]] = None,
    informal_reviewish: Optional[Set[int]] = None,
) -> Dict[str, Any]:
    """Peer ACK/NACK vector. Author's own comments are excluded."""
    author = canonicalize_actor(login=pr.get("author"))
    rm = pr.get("review_metrics") or {}
    total_reviews = int(rm.get("total_reviews") or pr.get("total_reviews") or 0)
    if not total_reviews:
        total_reviews = len(pr.get("reviews") or [])

    ack_by_role = {role: set() for role in ACK_ROLES}
    nack_by_role = {role: set() for role in ACK_ROLES}
    has_nack = False
    has_nack_rationale = False
    has_nack_bare = False
    has_concept = False
    has_utack = False
    has_code = False

    for login, body, state in _iter_review_items(pr):
        if not login or login == author:
            continue
        flags = classify_text(body)
        if state == "APPROVED":
            flags["code_ack"] = True
        role = person_role(login)
        if flags["nack"]:
            has_nack = True
            nack_by_role[role].add(login)
            if flags["nack_rationale"]:
                has_nack_rationale = True
            else:
                has_nack_bare = True
        acked = flags["concept_ack"] or flags["utack"] or flags["code_ack"]
        if acked:
            ack_by_role[role].add(login)
            has_concept = has_concept or flags["concept_ack"]
            has_utack = has_utack or flags["utack"]
            has_code = has_code or flags["code_ack"]

    n_keys = len(ack_by_role[ROLE_MERGE_KEYS])
    n_roster = len(ack_by_role[ROLE_ROSTER_WITHOUT_KEYS])
    n_out = len(ack_by_role[ROLE_CANNOT_MERGE])
    if n_keys + n_roster + n_out == 0:
        ack_source = "none"
    elif n_keys and not n_roster and not n_out:
        ack_source = "merge_keys_only"
    elif n_out and not n_keys and not n_roster:
        ack_source = "cannot_merge_only"
    elif n_roster and not n_keys and not n_out:
        ack_source = "roster_without_keys_only"
    else:
        ack_source = "mixed"

    if total_reviews <= 0:
        review_bucket = "zero"
    elif total_reviews == 1:
        review_bucket = "one"
    elif total_reviews <= 3:
        review_bucket = "two_three"
    else:
        review_bucket = "four_plus"

    merged = bool(pr.get("merged"))
    state = (pr.get("state") or "").lower()
    if merged:
        outcome = "merged"
    elif state == "open":
        outcome = "open"
    else:
        outcome = "closed_unmerged"

    merged_by = canonicalize_actor(login=pr.get("merged_by"))
    self_merge = bool(merged and merged_by and author and merged_by == author)

    peer_issue_comments = 0
    for c in pr.get("comments") or []:
        if not isinstance(c, dict):
            continue
        login = canonicalize_actor(login=c.get("author") or c.get("user"))
        if login and login != author and login not in _BOTS:
            peer_issue_comments += 1

    try:
        n_pr = int(pr.get("number") or 0)
    except (TypeError, ValueError):
        n_pr = 0
    informal_mention = bool(informal_any and n_pr in informal_any)
    informal_rev = bool(informal_reviewish and n_pr in informal_reviewish)
    github_zero = review_bucket == "zero"
    discussion_observed = (not github_zero) or peer_issue_comments > 0 or informal_mention
    github_zero_unobserved = github_zero and not discussion_observed

    return {
        "outcome": outcome,
        "self_merge": self_merge,
        "path_risk": path_risk_band(pr),
        "total_reviews": total_reviews,
        "review_bucket": review_bucket,
        "has_nack": has_nack,
        "has_nack_rationale": has_nack_rationale,
        "has_nack_bare": has_nack_bare,
        "has_concept_ack": has_concept,
        "has_utack": has_utack,
        "has_code_ack": has_code,
        "concept_only": has_concept and not has_utack and not has_code,
        "ack_source": ack_source,
        "n_ack_merge_keys": n_keys,
        "n_ack_roster_without_keys": n_roster,
        "n_ack_cannot_merge": n_out,
        "n_nack_merge_keys": len(nack_by_role[ROLE_MERGE_KEYS]),
        "n_nack_cannot_merge": len(nack_by_role[ROLE_CANNOT_MERGE]),
        "at_least_one_merge_keys_ack": n_keys > 0,
        "has_peer_github_comment": peer_issue_comments > 0,
        "informal_mention": informal_mention,
        "informal_reviewish": informal_rev,
        "discussion_observed": discussion_observed,
        "github_zero_unobserved": github_zero_unobserved,
    }


def _zero_outcome() -> Dict[str, Any]:
    return {
        "n": 0,
        "self_merge": 0,
        "review_buckets": {k: 0 for k in REVIEW_BUCKETS},
        "has_nack": 0,
        "has_nack_rationale": 0,
        "has_nack_bare": 0,
        "has_concept_ack": 0,
        "has_utack": 0,
        "has_code_ack": 0,
        "concept_only": 0,
        "ack_source": {
            "none": 0,
            "merge_keys_only": 0,
            "cannot_merge_only": 0,
            "roster_without_keys_only": 0,
            "mixed": 0,
        },
        "at_least_one_merge_keys_ack": 0,
        "merged_despite_nack": 0,
        "has_peer_github_comment": 0,
        "informal_mention": 0,
        "informal_reviewish": 0,
        "discussion_observed": 0,
        "github_zero_unobserved": 0,
    }


def _add(dst: Dict[str, Any], vec: Dict[str, Any], *, is_merged: bool) -> None:
    dst["n"] += 1
    if vec["self_merge"]:
        dst["self_merge"] += 1
    dst["review_buckets"][vec["review_bucket"]] += 1
    for key in (
        "has_nack",
        "has_nack_rationale",
        "has_nack_bare",
        "has_concept_ack",
        "has_utack",
        "has_code_ack",
        "concept_only",
        "at_least_one_merge_keys_ack",
        "has_peer_github_comment",
        "informal_mention",
        "informal_reviewish",
        "discussion_observed",
        "github_zero_unobserved",
    ):
        if vec[key]:
            dst[key] += 1
    dst["ack_source"][vec["ack_source"]] += 1
    if is_merged and vec["has_nack"]:
        dst["merged_despite_nack"] += 1


def _rates(block: Dict[str, Any]) -> Dict[str, Optional[float]]:
    n = block["n"] or 0

    def r(k: str) -> Optional[float]:
        return (block[k] / n) if n else None

    src = block["ack_source"]
    buckets = block["review_buckets"]
    return {
        "self_merge": r("self_merge"),
        "zero_reviews": (buckets["zero"] / n) if n else None,
        "one_review": (buckets["one"] / n) if n else None,
        "two_three_reviews": (buckets["two_three"] / n) if n else None,
        "four_plus_reviews": (buckets["four_plus"] / n) if n else None,
        "has_nack": r("has_nack"),
        "has_nack_rationale": r("has_nack_rationale"),
        "has_nack_bare": r("has_nack_bare"),
        "has_concept_ack": r("has_concept_ack"),
        "has_utack": r("has_utack"),
        "has_code_ack": r("has_code_ack"),
        "concept_only": r("concept_only"),
        "ack_none": (src["none"] / n) if n else None,
        "ack_merge_keys_only": (src["merge_keys_only"] / n) if n else None,
        "ack_cannot_merge_only": (src["cannot_merge_only"] / n) if n else None,
        "ack_roster_without_keys_only": (src["roster_without_keys_only"] / n) if n else None,
        "ack_mixed": (src["mixed"] / n) if n else None,
        "at_least_one_merge_keys_ack": r("at_least_one_merge_keys_ack"),
        "merged_despite_nack": r("merged_despite_nack") if "merged_despite_nack" in block else None,
        "has_peer_github_comment": r("has_peer_github_comment"),
        "informal_mention": r("informal_mention"),
        "informal_reviewish": r("informal_reviewish"),
        "discussion_observed": r("discussion_observed"),
        "github_zero_unobserved": r("github_zero_unobserved"),
    }


def _new_window() -> Dict[str, Any]:
    path = {band: {"merged": _zero_outcome(), "closed_unmerged": _zero_outcome()} for band in PATH_BANDS}
    return {
        "n": 0,
        "merged": _zero_outcome(),
        "closed_unmerged": _zero_outcome(),
        "open": _zero_outcome(),
        "by_path_risk": path,
    }


def _finish_window(w: Dict[str, Any]) -> Dict[str, Any]:
    out = {
        "n": w["n"],
        "n_merged": w["merged"]["n"],
        "n_closed_unmerged": w["closed_unmerged"]["n"],
        "n_open": w["open"]["n"],
    }
    for key in ("merged", "closed_unmerged", "open"):
        block = dict(w[key])
        block["rates"] = _rates(w[key])
        out[key] = block
    path_out = {}
    for band, pair in w["by_path_risk"].items():
        path_out[band] = {}
        for outcome in ("merged", "closed_unmerged"):
            block = dict(pair[outcome])
            block["rates"] = _rates(pair[outcome])
            path_out[band][outcome] = block
    out["by_path_risk"] = path_out
    return out


def analyze(path: Path) -> Dict[str, Any]:
    logger.info("Loading informal PR mentions (IRC/mail/Delving/Bitcointalk)")
    informal = load_informal_pr_sets()
    informal_any = informal.get("any") or set()
    informal_reviewish = informal.get("reviewish") or set()
    windows = {
        "all_time": _new_window(),
        "before_2016": _new_window(),
        "from_2016": _new_window(),
        "from_2022": _new_window(),
    }
    n = 0
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            pr = json.loads(line)
            n += 1
            vec = pr_consensus_vector(pr, informal_any, informal_reviewish)
            targets = [windows[k] for k in window_keys(pr.get("created_at") or "")]
            outcome = vec["outcome"]
            risk = vec["path_risk"] if vec["path_risk"] in PATH_BANDS else "unknown"
            for w in targets:
                w["n"] += 1
                _add(w[outcome], vec, is_merged=(outcome == "merged"))
                if outcome in ("merged", "closed_unmerged") and risk in w["by_path_risk"]:
                    _add(
                        w["by_path_risk"][risk][outcome],
                        vec,
                        is_merged=(outcome == "merged"),
                    )
    return {
        "pin": PIN,
        "version": "1.3",
        "source": "data/processed/enriched_prs.jsonl",
        "n_prs": n,
        "informal_index": {
            "prs_mentioned": len(informal_any),
            "prs_reviewish_keyword": len(informal_reviewish),
            "irc": len(informal.get("ch_irc") or []),
            "email": len(informal.get("ch_email") or []),
            "delving": len(informal.get("ch_delving") or []),
            "bitcointalk": len(informal.get("ch_bitcointalk") or []),
            "note": "Mention of #NNNN or a pull URL. Not a GitHub ACK. 1–3 digit PRs only join via github.com/bitcoin/bitcoin/pull/N (bare #12 is too noisy).",
        },
        "windows": {k: _finish_window(v) for k, v in windows.items()},
        "contributing_md": {
            "file": "CONTRIBUTING.md",
            "rests_with": "project merge maintainers",
            "judge": "general consensus of contributors",
            "weigh": "common sense judgement and merit",
            "nack_without_rationale": "may be disregarded",
        },
        "coverage": {
            "github_reviews_api": "GitHub Pull Request Reviews are effectively absent from this dump before 2016. Compare before_2016 vs from_2016 on discussion_observed (peer comments + informal mentions). Compare from_2016 vs from_2022 on GitHub Review objects. Do not compare pre-2016 zero_reviews to later windows, and do not cite all-time zero-review as the process bar. A mention is not a review.",
            "path_risk": "consensus_sensitive includes tests/docs/seeds that touch utxo|chainparams|script|validation. It is not a consensus-rule-change set.",
        },
    }


def main() -> int:
    src = get_data_dir() / "processed" / "enriched_prs.jsonl"
    if not src.exists():
        logger.error("Missing %s", src)
        return 1
    logger.info("Scanning %s", src)
    payload = analyze(src)
    written = save_analysis_json("revealed_rough_consensus.json", payload)
    m = payload["windows"]["all_time"]["merged"]
    logger.info(
        "merged=%s zero_reviews=%s nack=%s merge_keys_ack=%s",
        m["n"],
        m["review_buckets"]["zero"],
        m["has_nack"],
        m["at_least_one_merge_keys_ack"],
    )
    for p in written:
        print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
