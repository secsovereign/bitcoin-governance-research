#!/usr/bin/env python3
"""
Core development velocity decomposition by year and era.

Commons side is posture only (no PR-velocity parity claim).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.architectural_classification import (  # noqa: E402
    ARCHITECTURAL_DEBT_TAX,
    NET_NEW,
    STRUCTURAL,
    TOTAL_MAINTENANCE,
)
from src.utils.logger import setup_logger  # noqa: E402
from src.utils.paths import get_data_dir, get_findings_dir  # noqa: E402

logger = setup_logger()

# Historical eras for narrative (not causal claims)
ERAS: List[Tuple[str, int, int]] = [
    ("early", 2010, 2013),
    ("growth", 2014, 2017),
    ("professionalization", 2018, 2021),
    ("recent", 2022, 2030),
]


def era_for_year(year: int) -> str:
    for name, lo, hi in ERAS:
        if lo <= year <= hi:
            return name
    return "other"


def headline_from_counts(counts: Counter, total: int) -> Dict[str, Any]:
    total = total or 1

    def pct(keys) -> float:
        return round(100.0 * sum(counts.get(c, 0) for c in keys) / total, 2)

    return {
        "n": total,
        "architectural_debt_tax_pct": pct(ARCHITECTURAL_DEBT_TAX),
        "total_maintenance_burden_pct": pct(TOTAL_MAINTENANCE),
        "structural_work_pct": pct(STRUCTURAL),
        "net_new_capability_pct": pct(NET_NEW),
        "other_pct": pct({"other"}),
        "primary_counts": dict(counts),
        "primary_pct": {k: round(100.0 * v / total, 2) for k, v in counts.items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Core architectural velocity by year/era")
    parser.add_argument(
        "--classifications",
        type=Path,
        default=get_data_dir() / "processed" / "pr_architectural_classification.jsonl",
    )
    parser.add_argument(
        "--commons-metrics",
        type=Path,
        default=get_findings_dir() / "data" / "blvm_codebase_metrics.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=get_findings_dir() / "data" / "velocity_differential.json",
    )
    args = parser.parse_args()

    by_year: Dict[int, Counter] = defaultdict(Counter)
    by_era: Dict[str, Counter] = defaultdict(Counter)
    overall = Counter()
    missing_date = 0

    with open(args.classifications, encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            primary = row.get("primary") or "other"
            overall[primary] += 1
            merged = row.get("merged_at")
            if not merged:
                missing_date += 1
                continue
            year = int(str(merged)[:4])
            by_year[year][primary] += 1
            by_era[era_for_year(year)][primary] += 1

    yearly = {
        str(y): headline_from_counts(by_year[y], sum(by_year[y].values()))
        for y in sorted(by_year)
    }
    eras = {
        name: headline_from_counts(by_era[name], sum(by_era[name].values()))
        for name, _, _ in ERAS
        if name in by_era
    }

    # Trend: debt tax and maintenance over years
    trend = []
    for y in sorted(by_year):
        h = yearly[str(y)]
        trend.append(
            {
                "year": y,
                "n": h["n"],
                "architectural_debt_tax_pct": h["architectural_debt_tax_pct"],
                "total_maintenance_burden_pct": h["total_maintenance_burden_pct"],
                "structural_work_pct": h["structural_work_pct"],
                "net_new_capability_pct": h["net_new_capability_pct"],
                "other_pct": h["other_pct"],
            }
        )

    commons_posture = {}
    if args.commons_metrics.exists():
        cm = json.loads(args.commons_metrics.read_text(encoding="utf-8"))
        commons_posture = (cm.get("metrics") or {}).get("posture") or {}

    payload = {
        "analysis_date": datetime.now(timezone.utc).isoformat(),
        "methodology": "docs/ARCHITECTURAL_DIVERGENCE_PLAN.md Phase 3 — Core velocity; Commons posture only",
        "data_sources": [str(args.classifications), str(args.commons_metrics)],
        "definitions": {
            "architectural_debt_tax": sorted(ARCHITECTURAL_DEBT_TAX),
            "total_maintenance_burden": sorted(TOTAL_MAINTENANCE),
            "structural_work": sorted(STRUCTURAL),
            "net_new_capability": sorted(NET_NEW),
            "eras": [{"name": n, "start": a, "end": b} for n, a, b in ERAS],
        },
        "overall": headline_from_counts(overall, sum(overall.values())),
        "by_year": yearly,
        "by_era": eras,
        "trend": trend,
        "commons_posture": {
            **commons_posture,
            "velocity_claim": "none — static design posture only; no PR-throughput comparison",
        },
        "missing_merged_at": missing_date,
        "limitations": [
            "Classification heuristics + Cursor Tier 3; ~10% remain ambiguous",
            "Era buckets are narrative conveniences, not causal periods",
            "Commons has negligible comparable PR history — posture section only",
            "Do not interpret year-to-year swings as proof of governance improvement alone",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    logger.info("Wrote %s", args.output)
    logger.info(
        "overall debt_tax=%s%% maintenance=%s%% net_new=%s%%",
        payload["overall"]["architectural_debt_tax_pct"],
        payload["overall"]["total_maintenance_burden_pct"],
        payload["overall"]["net_new_capability_pct"],
    )
    for name in eras:
        logger.info(
            "  era %s n=%s debt_tax=%s%%",
            name,
            eras[name]["n"],
            eras[name]["architectural_debt_tax_pct"],
        )


if __name__ == "__main__":
    main()
