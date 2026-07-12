#!/usr/bin/env python3
"""Re-run tiers 1–2b, then re-apply all Cursor Tier 3 overrides."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.paths import get_data_dir  # noqa: E402


def main() -> None:
    results_dir = get_data_dir() / "classification" / "cursor_results"
    batches = sorted(results_dir.glob("batch_*.jsonl")) if results_dir.exists() else []

    classify = project_root / "scripts" / "analysis" / "classify_prs_architectural.py"
    importer = project_root / "scripts" / "analysis" / "import_cursor_classifications.py"

    subprocess.check_call([sys.executable, str(classify)], cwd=str(project_root))
    for batch in batches:
        batch_id = batch.stem.replace("batch_", "", 1)
        subprocess.check_call(
            [
                sys.executable,
                str(importer),
                "--cursor-results",
                str(batch),
                "--batch-id",
                batch_id,
            ],
            cwd=str(project_root),
        )

    agg_path = project_root / "findings" / "data" / "pr_architectural_classification.json"
    agg = json.loads(agg_path.read_text(encoding="utf-8"))
    m = agg.get("metrics") or agg
    print(
        json.dumps(
            {
                "ambiguous_pct": m.get("ambiguous_pct"),
                "ambiguous_count": m.get("ambiguous_count"),
                "headline_metrics": m.get("headline_metrics"),
                "primary_pct": m.get("primary_pct"),
                "cursor_batches_reapplied": len(batches),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
