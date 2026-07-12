#!/usr/bin/env python3
"""Export a stratified 50-PR validation sample (≥5 per major category)."""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.architectural_classification import CATEGORIES  # noqa: E402
from src.utils.paths import get_data_dir, get_findings_dir  # noqa: E402

MAJOR = [
    "debt_compensation",
    "refactor",
    "consensus_change",
    "networking_change",
    "rpc_change",
    "dependency_maintenance",
    "test_ci_build",
    "documentation",
    "other",
    "new_feature",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--per-category", type=int, default=5)
    parser.add_argument(
        "--input",
        type=Path,
        default=get_data_dir() / "processed" / "pr_architectural_classification.jsonl",
    )
    parser.add_argument(
        "--enriched",
        type=Path,
        default=get_data_dir() / "processed" / "enriched_prs.jsonl",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=get_findings_dir() / "data" / "stratified_validation_sample.json",
    )
    args = parser.parse_args()
    rng = random.Random(args.seed)

    by_cat = defaultdict(list)
    with open(args.input, encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            by_cat[row.get("primary") or "other"].append(row)

    bodies = {}
    with open(args.enriched, encoding="utf-8") as f:
        for line in f:
            pr = json.loads(line)
            if pr.get("merged"):
                bodies[pr["number"]] = {
                    "title": pr.get("title"),
                    "body": (pr.get("body") or "")[:800],
                    "labels": pr.get("labels"),
                    "files": [x.get("filename") for x in (pr.get("files") or [])[:15]],
                }

    sample = []
    for cat in MAJOR:
        pool = list(by_cat.get(cat) or [])
        if not pool:
            continue
        k = min(args.per_category, len(pool))
        chosen = rng.sample(pool, k)
        for row in chosen:
            extra = bodies.get(row["number"], {})
            sample.append(
                {
                    "number": row["number"],
                    "machine_primary": row["primary"],
                    "machine_secondary": row.get("secondary") or [],
                    "machine_confidence": row.get("confidence"),
                    "machine_ambiguous": row.get("ambiguous"),
                    "tier_used": row.get("tier_used"),
                    "title": extra.get("title") or row.get("title"),
                    "labels": extra.get("labels") or row.get("labels"),
                    "files": extra.get("files") or row.get("files_sample"),
                    "body": extra.get("body"),
                    "human_primary": None,
                    "human_agree": None,
                    "human_notes": None,
                }
            )

    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "seed": args.seed,
        "per_category_target": args.per_category,
        "categories": MAJOR,
        "count": len(sample),
        "counts_by_machine_primary": {
            c: sum(1 for s in sample if s["machine_primary"] == c) for c in MAJOR
        },
        "instructions": (
            "Set human_primary to taxonomy category; human_agree true/false vs machine_primary; "
            "optional human_notes. Then run score_stratified_validation.py."
        ),
        "prs": sample,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output} ({len(sample)} PRs)")


if __name__ == "__main__":
    main()
