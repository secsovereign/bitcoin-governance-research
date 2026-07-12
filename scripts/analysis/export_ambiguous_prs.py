#!/usr/bin/env python3
"""Export ambiguous architectural classifications for Cursor Tier 3 batches."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger  # noqa: E402
from src.utils.paths import get_data_dir  # noqa: E402

logger = setup_logger()


def main() -> None:
    parser = argparse.ArgumentParser()
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
        "--outdir",
        type=Path,
        default=get_data_dir() / "classification" / "batches",
    )
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--max-batches", type=int, default=3, help="Export first N batches only")
    parser.add_argument("--confidence", choices=["low", "medium", "all"], default="all")
    args = parser.parse_args()

    # Index enriched for body snippets
    bodies = {}
    with open(args.enriched, encoding="utf-8") as f:
        for line in f:
            pr = json.loads(line)
            if pr.get("merged"):
                bodies[pr["number"]] = {
                    "body": (pr.get("body") or "")[:1500],
                    "title": pr.get("title"),
                    "labels": pr.get("labels"),
                    "files": [x.get("filename") for x in (pr.get("files") or [])[:20]],
                }

    ambiguous = []
    with open(args.input, encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            if not row.get("ambiguous"):
                continue
            if args.confidence != "all" and row.get("confidence") != args.confidence:
                continue
            extra = bodies.get(row["number"], {})
            ambiguous.append({**row, **{k: v for k, v in extra.items() if k not in row}})

    # Prefer medium/high-signal ambiguous (have some scores) first, then by number desc
    ambiguous.sort(key=lambda r: (-len(r.get("scores") or {}), -(r.get("number") or 0)))

    args.outdir.mkdir(parents=True, exist_ok=True)
    prompt_path = project_root / "scripts" / "analysis" / "prompts" / "architectural_category.md"
    prompt_hash = hashlib.sha256(prompt_path.read_bytes()).hexdigest()[:16] if prompt_path.exists() else "missing"

    batch_id_base = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    exported = 0
    for i in range(0, min(len(ambiguous), args.batch_size * args.max_batches), args.batch_size):
        chunk = ambiguous[i : i + args.batch_size]
        batch_id = f"{batch_id_base}_{i // args.batch_size:03d}"
        out = {
            "batch_id": batch_id,
            "prompt_hash": prompt_hash,
            "prompt_path": str(prompt_path),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "count": len(chunk),
            "instructions": (
                "Classify each PR into primary architectural_category and optional secondary[]. "
                "Use scripts/analysis/prompts/architectural_category.md. "
                "Return JSONL lines: {number, primary, secondary, confidence, rationale}."
            ),
            "prs": chunk,
        }
        path = args.outdir / f"ambiguous_prs_batch_{batch_id}.json"
        path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
        logger.info("Wrote %s (%s PRs)", path, len(chunk))
        exported += 1

    logger.info(
        "Exported %s batches / %s ambiguous of pool size %s",
        exported,
        min(len(ambiguous), args.batch_size * args.max_batches),
        len(ambiguous),
    )


if __name__ == "__main__":
    main()
