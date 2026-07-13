#!/usr/bin/env python3
"""
Author-prep sensitivity + high-prep closed-outsider sample (plan Phase 2/3).

Writes:
  findings/data/author_prep_sensitivity.json
  findings/data/high_prep_outsider_closed_sample.json
"""

from __future__ import annotations

import json
import math
import random
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.pr_quality import (  # noqa: E402
    AUTHOR_PREP_HIGH,
    AUTHOR_PREP_MID_HIGH,
    author_prep_score,
    consensus_ack_flags,
    has_nontrivial_test_diff,
    path_risk_band,
    touches_tests,
)
from src.utils.paths import get_data_dir, get_findings_dir  # noqa: E402

CLOSE_WIP_RE = re.compile(
    r"do not merge|don't merge|\[wip\]|\bwip\b|\[do not merge\]", re.I
)
CLOSE_SUPERSEDED_RE = re.compile(
    r"superse?ded|replaced by|closed in favor|obsoleted", re.I
)
CLOSE_WITHDRAW_RE = re.compile(
    r"\b(withdrawn|closing this|closing for now)\b", re.I
)


def _load_prs() -> List[Dict[str, Any]]:
    path = get_data_dir() / "processed" / "enriched_prs.jsonl"
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))
    return rows


def _is_maint(pr: Dict[str, Any]) -> bool:
    tags = pr.get("maintainer_tags") or {}
    inv = pr.get("maintainer_involvement") or {}
    return bool(tags.get("author_is_maintainer") or inv.get("author_is_maintainer"))


def _merge_rate(prs: List[Dict[str, Any]], pred) -> Dict[str, Any]:
    m = [p for p in prs if pred(p) and _is_maint(p)]
    n = [p for p in prs if pred(p) and not _is_maint(p)]
    def rate(xs):
        return sum(1 for p in xs if p.get("merged")) / len(xs) if xs else None
    rm, rn = rate(m), rate(n)
    return {
        "n_maintainer": len(m),
        "n_non_maintainer": len(n),
        "maint_merge_rate": rm,
        "non_merge_rate": rn,
        "gap_pp": ((rm - rn) * 100) if rm is not None and rn is not None else None,
    }


def _body_len(pr: Dict[str, Any]) -> int:
    return len((pr.get("body") or "").strip())


def run_sensitivity(prs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Phase 3: body thresholds, test-touch on/off, prep cutoffs."""
    variants = {
        "prep_ge_065_canonical": lambda p: author_prep_score(p) >= AUTHOR_PREP_HIGH,
        "prep_ge_050": lambda p: author_prep_score(p) >= AUTHOR_PREP_MID_HIGH,
        "body_gt_200_only": lambda p: _body_len(p) > 200,
        "body_gt_500_only": lambda p: _body_len(p) > 500,
        "tests_touch_only": lambda p: touches_tests(p),
        "body_gt_200_and_tests": lambda p: _body_len(p) > 200 and touches_tests(p),
        "body_gt_500_and_tests": lambda p: _body_len(p) > 500 and touches_tests(p),
        "prep_ge_065_and_nontrivial_test_diff": lambda p: (
            author_prep_score(p) >= AUTHOR_PREP_HIGH and has_nontrivial_test_diff(p)
        ),
    }
    out = {name: _merge_rate(prs, pred) for name, pred in variants.items()}

    # Corr author_prep vs log LOC / reviews (sanity)
    preps, locs, revs = [], [], []
    for p in prs:
        preps.append(author_prep_score(p))
        locs.append(math.log1p(int((p.get("complexity") or {}).get("total_changes") or 0)))
        revs.append(int((p.get("review_metrics") or {}).get("total_reviews") or 0))

    def corr(a, b):
        ma, mb = sum(a) / len(a), sum(b) / len(b)
        num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
        den = (sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) ** 0.5
        return num / den if den else 0.0

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_prs": len(prs),
        "variants": out,
        "correlations": {
            "author_prep_vs_log_loc": corr(preps, locs),
            "author_prep_vs_reviews": corr(preps, revs),
            "note": "prep vs log LOC should be << 0.85 (substance); flag if >= 0.6",
        },
        "ci_status": {
            "status": "unavailable_on_enriched_corpus",
            "resolution": "closed_as_documented_unavailable",
            "note": (
                "No check_runs/CI fields on enriched_prs.jsonl. "
                "Plan Phase 2 CI exit satisfied by documenting unavailability; "
                "collection is a separate future backlog item."
            ),
        },
    }


def _code_label(pr: Dict[str, Any]) -> Dict[str, Any]:
    """Structured close-outcome code (not LLM semantic quality)."""
    rm = pr.get("review_metrics") or {}
    reviews = int(rm.get("total_reviews") or 0)
    nacks = int(rm.get("nack_count") or 0)
    blob = f"{pr.get('title') or ''} {(pr.get('body') or '')[:800]}"
    ack = consensus_ack_flags(pr)
    codes = []
    if CLOSE_WIP_RE.search(blob):
        codes.append("staging_or_wip")
    if CLOSE_SUPERSEDED_RE.search(blob):
        codes.append("superseded_keyword")
    if CLOSE_WITHDRAW_RE.search(blob):
        codes.append("withdrawn_keyword")
    if nacks >= 1 or ack["has_nack_text"]:
        codes.append("nack_signal")
    if ack["has_concept_or_approach_ack"]:
        codes.append("had_concept_or_approach_ack")
    if reviews == 0:
        codes.append("no_reviews")
    elif reviews >= 1:
        codes.append("reviewed_then_closed")
    loc = int((pr.get("complexity") or {}).get("total_changes") or 0)
    if loc >= 2000:
        codes.append("large_ge_2000_loc")
    if has_nontrivial_test_diff(pr):
        codes.append("nontrivial_test_diff")

    # Primary code priority
    primary = "reviewed_then_closed"
    for cand in (
        "staging_or_wip",
        "superseded_keyword",
        "withdrawn_keyword",
        "nack_signal",
        "no_reviews",
        "reviewed_then_closed",
    ):
        if cand in codes:
            primary = cand
            break

    return {
        "primary_code": primary,
        "codes": codes,
        "total_reviews": reviews,
        "nack_count": nacks,
        "total_changes": loc,
        "path_risk": path_risk_band(pr),
        "author_prep_score": author_prep_score(pr),
        "days_to_decision": (pr.get("time_to_decision") or {}).get("days_to_decision"),
    }


def build_sample(prs: List[Dict[str, Any]], n: int = 100, seed: int = 13) -> Dict[str, Any]:
    """Stratified sample of high-prep, closed-unmerged, non-maintainer PRs."""
    pool = []
    for p in prs:
        if _is_maint(p):
            continue
        if p.get("merged") or p.get("state") != "closed":
            continue
        if author_prep_score(p) < AUTHOR_PREP_HIGH:
            continue
        pool.append(p)

    by_risk: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for p in pool:
        by_risk[path_risk_band(p)].append(p)

    rng = random.Random(seed)
    # Target mix: oversample consensus/security/networking relative to other
    quotas = {
        "consensus_sensitive": 25,
        "security_sensitive": 20,
        "networking": 20,
        "other": 30,
        "unknown": 5,
    }
    picked: List[Dict[str, Any]] = []
    for band, quota in quotas.items():
        bucket = list(by_risk.get(band) or [])
        rng.shuffle(bucket)
        picked.extend(bucket[:quota])

    # Fill to n from remaining pool
    picked_nums = {p["number"] for p in picked}
    rest = [p for p in pool if p["number"] not in picked_nums]
    rng.shuffle(rest)
    while len(picked) < n and rest:
        picked.append(rest.pop())
    picked = picked[:n]

    items = []
    code_counts: Dict[str, int] = defaultdict(int)
    for p in sorted(picked, key=lambda x: x.get("number") or 0):
        label = _code_label(p)
        code_counts[label["primary_code"]] += 1
        items.append(
            {
                "number": p.get("number"),
                "title": p.get("title"),
                "author": p.get("author"),
                "created_at": p.get("created_at"),
                "closed_at": p.get("closed_at"),
                "url": f"https://github.com/bitcoin/bitcoin/pull/{p.get('number')}",
                **label,
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": (
            "Stratified random sample (seed=13) of non-maintainer, closed-unmerged PRs "
            f"with author_prep_score >= {AUTHOR_PREP_HIGH}. "
            "Labels are structured codes from reviews/NACK/keywords — not semantic "
            "code-quality judgments. Manual narrative review of threads not performed."
        ),
        "n_pool": len(pool),
        "n_sample": len(items),
        "primary_code_counts": dict(code_counts),
        "quotas_requested": quotas,
        "items": items,
        "reading": (
            "High share of no_reviews ⇒ non-engagement/abandon dominates this "
            "high-prep closed-outsider set; nack_signal / reviewed_then_closed are "
            "closer to contested non-merge."
        ),
    }


def main() -> int:
    prs = _load_prs()
    sens = run_sensitivity(prs)
    sample = build_sample(prs, n=100)

    out = get_findings_dir() / "data"
    out.mkdir(parents=True, exist_ok=True)
    sens_path = out / "author_prep_sensitivity.json"
    sample_path = out / "high_prep_outsider_closed_sample.json"
    sens_path.write_text(json.dumps(sens, indent=2) + "\n", encoding="utf-8")
    sample_path.write_text(json.dumps(sample, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {sens_path}")
    print(f"Wrote {sample_path}")
    print("sensitivity gaps (pp):")
    for k, v in sens["variants"].items():
        print(f"  {k}: gap_pp={v.get('gap_pp')} non={v.get('non_merge_rate')} n_non={v.get('n_non_maintainer')}")
    print("correlations", sens["correlations"])
    print("sample primary codes", sample["primary_code_counts"])
    print("ci", sens["ci_status"]["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
