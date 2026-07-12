#!/usr/bin/env python3
"""
Classify merged Bitcoin Core PRs into architectural categories (Phase 1).

Tiers 1–2b only. Ambiguous PRs are flagged for Cursor Tier 3 export.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.architectural_classification import (  # noqa: E402
    ArchitecturalClassifier,
    aggregate_results,
)
from src.utils.logger import setup_logger  # noqa: E402
from src.utils.paths import get_data_dir, get_findings_dir  # noqa: E402

logger = setup_logger()


def load_merged_prs(path: Path, limit: int | None = None) -> list:
    prs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            pr = json.loads(line)
            if not pr.get("merged"):
                continue
            prs.append(pr)
            if limit and len(prs) >= limit:
                break
    return prs


def main() -> None:
    parser = argparse.ArgumentParser(description="Architectural PR classification (tiers 1–2b)")
    parser.add_argument(
        "--input",
        type=Path,
        default=get_data_dir() / "processed" / "enriched_prs.jsonl",
    )
    parser.add_argument(
        "--debt-json",
        type=Path,
        default=get_findings_dir() / "data" / "code_turnover_analysis.json",
    )
    parser.add_argument(
        "--classification-dir",
        type=Path,
        default=get_data_dir() / "classification",
    )
    parser.add_argument(
        "--output-jsonl",
        type=Path,
        default=get_data_dir() / "processed" / "pr_architectural_classification.jsonl",
    )
    parser.add_argument(
        "--output-aggregate",
        type=Path,
        default=get_findings_dir() / "data" / "pr_architectural_classification.json",
    )
    parser.add_argument("--limit", type=int, default=None, help="Limit merged PRs (testing)")
    parser.add_argument(
        "--debt-threshold",
        type=float,
        default=50.0,
        help="file debt_score threshold for Tier 2b",
    )
    args = parser.parse_args()

    logger.info("Loading merged PRs from %s", args.input)
    prs = load_merged_prs(args.input, args.limit)
    logger.info("Loaded %s merged PRs", len(prs))

    classifier = ArchitecturalClassifier(
        classification_dir=args.classification_dir,
        debt_json_path=args.debt_json,
        debt_score_threshold=args.debt_threshold,
    )
    logger.info("Debt file scores loaded: %s", len(classifier.debt_scores))

    results = []
    for i, pr in enumerate(prs, 1):
        results.append(classifier.classify(pr))
        if i % 2000 == 0:
            logger.info("Classified %s/%s", i, len(prs))

    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_jsonl, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")

    aggregate = aggregate_results(results)
    payload = {
        "analysis_date": datetime.now(timezone.utc).isoformat(),
        "methodology": "docs/ARCHITECTURAL_DIVERGENCE_PLAN.md (Phase 1 tiers 1–2b)",
        "data_sources": [
            str(args.input),
            str(args.debt_json),
            str(args.classification_dir),
        ],
        "parameters": {"debt_score_threshold": args.debt_threshold},
        "metrics": aggregate,
        "limitations": [
            "Tier 3 (Cursor) not yet applied; ambiguous_pct includes unresolved cases",
            "code_turnover_analysis.json may predate full regenerated PR corpus",
            "Labels and keywords are heuristics; debt_compensation is hardest category",
        ],
    }
    args.output_aggregate.parent.mkdir(parents=True, exist_ok=True)
    args.output_aggregate.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    logger.info("Wrote %s", args.output_jsonl)
    logger.info("Wrote %s", args.output_aggregate)
    logger.info(
        "primary_pct=%s ambiguous=%s%% debt_tax=%s%%",
        aggregate["primary_pct"],
        aggregate["ambiguous_pct"],
        aggregate["headline_metrics"]["architectural_debt_tax_pct"],
    )


if __name__ == "__main__":
    main()
