#!/usr/bin/env python3
"""Import Cursor Tier 3 classifications into the architectural classification JSONL."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.architectural_classification import CATEGORIES  # noqa: E402
from src.utils.logger import setup_logger  # noqa: E402
from src.utils.paths import get_data_dir, get_findings_dir  # noqa: E402
from src.utils.architectural_classification import (  # noqa: E402
    ClassificationResult,
    aggregate_results,
)

logger = setup_logger()


def load_cursor_rows(path: Path) -> dict:
    """Accept JSONL ({...}\\n) or JSON list."""
    text = path.read_text(encoding="utf-8").strip()
    rows = {}
    if text.startswith("["):
        data = json.loads(text)
        items = data
    else:
        items = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    for item in items:
        num = int(item["number"])
        primary = item["primary"]
        if primary not in CATEGORIES:
            raise ValueError(f"PR #{num}: invalid primary {primary}")
        rows[num] = item
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cursor-results", type=Path, required=True, help="JSONL or JSON list from Cursor")
    parser.add_argument(
        "--input",
        type=Path,
        default=get_data_dir() / "processed" / "pr_architectural_classification.jsonl",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=get_data_dir() / "processed" / "pr_architectural_classification.jsonl",
    )
    parser.add_argument(
        "--aggregate",
        type=Path,
        default=get_findings_dir() / "data" / "pr_architectural_classification.json",
    )
    parser.add_argument("--batch-id", type=str, default="")
    args = parser.parse_args()

    updates = load_cursor_rows(args.cursor_results)
    logger.info("Loaded %s Cursor classifications", len(updates))

    results = []
    updated = 0
    with open(args.input, encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            num = row["number"]
            if num in updates:
                u = updates[num]
                row["primary"] = u["primary"]
                row["secondary"] = u.get("secondary") or []
                row["confidence"] = u.get("confidence") or "medium"
                row["ambiguous"] = False
                row["tier_used"] = (row.get("tier_used") or "") + "+3"
                row["evidence"] = list(row.get("evidence") or []) + [
                    f"cursor:{args.batch_id or 'batch'}:{u.get('rationale', '')[:200]}"
                ]
                updated += 1
            results.append(ClassificationResult(**{k: row[k] for k in ClassificationResult.__dataclass_fields__ if k in row}))

    with open(args.output, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")

    # Rebuild aggregate from full jsonl for accuracy
    full = []
    with open(args.output, encoding="utf-8") as f:
        for line in f:
            full.append(ClassificationResult(**{k: v for k, v in json.loads(line).items() if k in ClassificationResult.__dataclass_fields__}))

    from datetime import datetime, timezone

    agg = aggregate_results(full)
    payload = {
        "analysis_date": datetime.now(timezone.utc).isoformat(),
        "methodology": "docs/ARCHITECTURAL_DIVERGENCE_PLAN.md (Phase 1 + Cursor Tier 3 import)",
        "cursor_batch_id": args.batch_id,
        "cursor_updated": updated,
        "metrics": agg,
    }
    if args.aggregate.exists():
        prev = json.loads(args.aggregate.read_text(encoding="utf-8"))
        payload["data_sources"] = prev.get("data_sources")
        payload["parameters"] = prev.get("parameters")
        payload["limitations"] = prev.get("limitations")
    args.aggregate.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    logger.info("Updated %s rows; ambiguous now %s%%", updated, agg["ambiguous_pct"])


if __name__ == "__main__":
    main()
