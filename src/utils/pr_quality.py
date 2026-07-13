#!/usr/bin/env python3
"""
PR quality / substance / author-prep scoring helpers.

See btc-commons ``docs/PR_QUALITY_SCORING_PLAN.md`` (validated Phase 1).

- ``author_prep_score`` — primary for identity matching (body + tests; no reviews/LOC/merge)
- ``size_substance_score`` / ``contribution_quality_score`` — size-heavy; not \"quality\"
- ``engagement_score`` — process (reviews received); not author merit
- ``readiness_score`` — deprecated alias of engagement (historical name)

Stock contributor-timeline quality adds +0.3 for merged — circular for outcomes.
Use ``include_merged=False`` (default) there.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

# Path rules for test-file touch (prefer structured paths over bare "test" substring)
_TEST_PATH_RE = re.compile(
    r"(^|/)(tests?|qa)/"
    r"|_tests?\.(cpp|h|cc|py|rs)$"
    r"|/(test|tests)_[^/]+$"
    r"|_test\.(cpp|h|cc|py)$",
    re.I,
)


def _total_changes(pr: Dict[str, Any]) -> int:
    cx = pr.get("complexity") or {}
    if cx.get("total_changes") is not None:
        return int(cx.get("total_changes") or 0)
    additions = pr.get("additions") or pr.get("total_additions") or cx.get("additions") or 0
    deletions = pr.get("deletions") or pr.get("total_deletions") or cx.get("deletions") or 0
    return int(additions) + int(deletions)


def _files_changed(pr: Dict[str, Any]) -> int:
    cx = pr.get("complexity") or {}
    if cx.get("files_changed") is not None:
        return int(cx.get("files_changed") or 0)
    files = pr.get("files") or []
    if files:
        return len(files)
    return int(pr.get("files_changed") or pr.get("total_files_changed") or 0)


def _review_count(pr: Dict[str, Any]) -> int:
    rm = pr.get("review_metrics") or {}
    if rm.get("total_reviews") is not None:
        return int(rm.get("total_reviews") or 0)
    reviews = pr.get("reviews") or []
    return len(reviews)


def _file_name(f: Any) -> str:
    if isinstance(f, dict):
        return (f.get("filename") or f.get("path") or "").lower()
    return str(f).lower()


def touches_tests(pr: Dict[str, Any]) -> bool:
    """True if any changed path looks like a test file/dir (structured heuristics)."""
    for f in pr.get("files") or []:
        name = _file_name(f)
        if not name:
            continue
        if _TEST_PATH_RE.search(name):
            return True
        # Common Core layouts
        if "/test/" in name or name.startswith("test/") or name.startswith("tests/"):
            return True
        if "test_" in name.split("/")[-1] and name.endswith((".cpp", ".h", ".py")):
            return True
    return False


def author_prep_score(pr: Dict[str, Any]) -> float:
    """
    Author-side preparation proxy in [0, 0.80] under Phase 1 weights.

    Body length + test-path touch only. Forbidden: LOC, file count, reviews,
    approvals, merge, prior merges.
    """
    score = 0.0
    body = (pr.get("body") or "").strip()
    if len(body) > 500:
        score += 0.40
    elif len(body) > 200:
        score += 0.25
    elif len(body) > 50:
        score += 0.10

    if touches_tests(pr):
        score += 0.40

    return float(min(score, 0.80))


AUTHOR_PREP_HIGH = 0.65
AUTHOR_PREP_MID_HIGH = 0.50


def contribution_quality_score(
    pr: Dict[str, Any],
    *,
    include_merged: bool = False,
) -> float:
    """
    Size-heavy substance score in [0, 1] — **not** author quality.

    Matches ``calculate_contribution_quality_score`` in
    contributor_timeline_analysis.py when ``include_merged=True``.

    For merge-outcome analysis, keep ``include_merged=False`` (default).
    """
    score = 0.0
    total_changes = _total_changes(pr)

    if total_changes > 0:
        if total_changes >= 1000:
            score += 0.8
        elif total_changes >= 500:
            score += 0.6
        elif total_changes >= 100:
            score += 0.3
        elif total_changes >= 50:
            score += 0.2
        else:
            score += 0.1

    files_changed = _files_changed(pr)
    if files_changed >= 10:
        score += 0.2
    elif files_changed >= 5:
        score += 0.1

    if include_merged and pr.get("merged", False):
        score += 0.3

    if _review_count(pr) > 0:
        score += 0.1

    body = (pr.get("body") or "").strip()
    if len(body) > 200:
        score += 0.1

    return float(min(score, 1.0))


def size_substance_score(pr: Dict[str, Any]) -> float:
    """Alias: ex-outcome contribution score labeled as size/substance, not quality."""
    return contribution_quality_score(pr, include_merged=False)


def engagement_score(pr: Dict[str, Any], *, include_body: bool = False) -> float:
    """
    Process engagement proxy (reviews received). Not author merit.

    Optional body length for continuity with old readiness; default is reviews-only
    so engagement does not masquerade as prep.
    """
    score = 0.0
    if include_body:
        body = (pr.get("body") or "").strip()
        if len(body) > 500:
            score += 0.25
        elif len(body) > 200:
            score += 0.15
        elif len(body) > 50:
            score += 0.05

    reviews = _review_count(pr)
    if reviews >= 2:
        score += 0.50
    elif reviews >= 1:
        score += 0.30

    return float(min(score, 1.0))


def readiness_score(pr: Dict[str, Any]) -> float:
    """
    Deprecated name for historical readiness (body + tests + reviews).

    Do **not** use for identity quality-matching — use ``author_prep_score``.
    Prefer ``engagement_score`` for process metrics. Kept for backward compatibility
    with earlier premium JSON fields.
    """
    score = 0.0
    body = (pr.get("body") or "").strip()
    if len(body) > 500:
        score += 0.4
    elif len(body) > 200:
        score += 0.25
    elif len(body) > 50:
        score += 0.1

    if touches_tests(pr):
        score += 0.35

    reviews = _review_count(pr)
    if reviews >= 2:
        score += 0.25
    elif reviews >= 1:
        score += 0.15

    return float(min(score, 1.0))


def quality_tertile(score: float, edges: List[float]) -> str:
    """Assign low/mid/high given ascending tertile cutpoints [t1, t2]."""
    if len(edges) < 2:
        return "mid"
    if score <= edges[0]:
        return "low"
    if score <= edges[1]:
        return "mid"
    return "high"


def tertile_edges(scores: List[float]) -> List[float]:
    if not scores:
        return [0.0, 1.0]
    s = sorted(scores)
    n = len(s)

    def pct(p: float) -> float:
        i = min(n - 1, max(0, int(p * (n - 1))))
        return float(s[i])

    return [pct(1 / 3), pct(2 / 3)]


def author_prep_band(score: float) -> str:
    """Explicit bands per plan Decision 9 (not tertile-only)."""
    if score >= AUTHOR_PREP_HIGH:
        return "high"
    if score >= AUTHOR_PREP_MID_HIGH:
        return "mid_high"
    if score > 0:
        return "low_mid"
    return "none"


# --- Phase 2 signals ---

_CONCEPT_ACK_RE = re.compile(
    r"\b(concept\s*ack|approach\s*ack|concept\s*a?ck)\b", re.I
)
_NACK_RE = re.compile(r"\b(nack|concept\s*nack|strong\s*nack)\b", re.I)
_UTACK_RE = re.compile(r"\b(utack|tested\s*ack)\b", re.I)


def _iter_text_blobs(pr: Dict[str, Any]) -> List[str]:
    blobs: List[str] = []
    for c in pr.get("comments") or []:
        if isinstance(c, dict):
            blobs.append(c.get("body") or "")
        else:
            blobs.append(str(c))
    for r in pr.get("reviews") or []:
        if isinstance(r, dict):
            blobs.append(r.get("body") or "")
        else:
            blobs.append(str(r))
    return blobs


def consensus_ack_flags(pr: Dict[str, Any]) -> Dict[str, bool]:
    """
    Text flags from comment/review bodies (Phase 2).

    These are *received* signals (process/consensus), not author-prep.
    """
    text = "\n".join(_iter_text_blobs(pr))
    return {
        "has_concept_or_approach_ack": bool(_CONCEPT_ACK_RE.search(text)),
        "has_utack": bool(_UTACK_RE.search(text)),
        "has_nack_text": bool(_NACK_RE.search(text)),
    }


def nontrivial_test_additions(pr: Dict[str, Any]) -> int:
    """Sum of additions on test-like paths (0 if none / missing files)."""
    total = 0
    for f in pr.get("files") or []:
        if not isinstance(f, dict):
            continue
        name = _file_name(f)
        if not name:
            continue
        is_test = bool(_TEST_PATH_RE.search(name)) or (
            "/test/" in name or name.startswith("test/") or name.startswith("tests/")
        )
        if is_test:
            total += int(f.get("additions") or 0)
    return total


def has_nontrivial_test_diff(pr: Dict[str, Any], *, min_additions: int = 10) -> bool:
    """True if test-path additions sum to at least ``min_additions``."""
    return nontrivial_test_additions(pr) >= min_additions


# Path risk bands (replace keyword "importance" for premium strata)
_CONSENSUS_PATH_RE = re.compile(
    r"(^|/)src/(consensus|script|validation|primitives)/|(^|/)src/consensus\.|"
    r"chainparams|pow\.cpp|utxo",
    re.I,
)
_SECURITY_PATH_RE = re.compile(
    r"(wallet|keystore|crypter|signer|secp256k1|hmac_sha|/key\.cpp|/key\.h|crypto/aes)",
    re.I,
)
_NET_PATH_RE = re.compile(
    r"(^|/)src/(net|net_processing|protocol|banman)(/|\.cpp|\.h)"
    r"|(^|/)src/net\.cpp|(^|/)src/net_processing\.cpp"
    r"|addr(man|db)|i2p|torcontrol|socks",
    re.I,
)


def path_risk_band(pr: Dict[str, Any]) -> str:
    """
    Coarse risk from changed paths: consensus_sensitive | security_sensitive |
    networking | other.

    Prefer this over keyword importance for governance strata.
    Order: consensus → networking → security → other (net before broad wallet/security).
    """
    names = [_file_name(f) for f in (pr.get("files") or [])]
    names = [n for n in names if n]
    if not names:
        return "unknown"
    if any(_CONSENSUS_PATH_RE.search(n) for n in names):
        return "consensus_sensitive"
    if any(_NET_PATH_RE.search(n) for n in names):
        return "networking"
    if any(_SECURITY_PATH_RE.search(n) for n in names):
        return "security_sensitive"
    return "other"


def classify_importance_label(pr: Dict[str, Any]) -> Optional[str]:
    try:
        from scripts.analysis.pr_importance_matrix import classify_pr_importance

        return classify_pr_importance(pr).value
    except Exception:
        return None
