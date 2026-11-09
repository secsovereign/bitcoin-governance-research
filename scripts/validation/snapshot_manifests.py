"""Fail when a banner citation disagrees with its snapshot manifest."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_DIR = ROOT / "findings" / "snapshots"
CITATIONS = ROOT / "findings" / "snapshots" / "banner_citations.json"


def load_snapshot(snapshot_id: str) -> Dict[str, Any]:
    path = SNAPSHOT_DIR / f"{snapshot_id}.json"
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def check_citations(root: Path | None = None) -> List[str]:
    root = root or ROOT
    citations = json.loads((root / "findings" / "snapshots" / "banner_citations.json").read_text(encoding="utf-8"))
    failures: List[str] = []
    for row in citations:
        snapshot = load_snapshot(row["snapshot"]) if root == ROOT else json.loads(
            (root / "findings" / "snapshots" / f"{row['snapshot']}.json").read_text(encoding="utf-8")
        )
        counts = snapshot["counts"]
        actual = counts.get(row["field"])
        if actual != row["value"]:
            failures.append(
                f"{row['snapshot']} {row['field']} is {actual}, citation says {row['value']}"
            )
        for rel in row["files"]:
            text = (root / rel).read_text(encoding="utf-8")
            if row["text"] not in text:
                failures.append(f"{rel} is missing {row['text']!r}")
    return failures


def check_publication_ids(root: Path | None = None) -> List[str]:
    """An S-id in the claims ledger must be a manifest. Publication batches list real files."""
    root = root or ROOT
    failures: List[str] = []
    ledger = (root / "findings" / "CLAIMS_LEDGER.md").read_text(encoding="utf-8")
    for line in ledger.splitlines():
        if not line.startswith("| ") or line.startswith("| Status") or line.startswith("| ---"):
            continue
        cell = line.rstrip().rstrip("|").split("|")[-1].strip()
        if cell.startswith("S") and not (root / "findings" / "snapshots" / f"{cell}.json").exists():
            failures.append(f"ledger snapshot {cell} has no manifest")
    for snapshot_id in ("S0920", "S0923"):
        manifest = json.loads((root / "findings" / "snapshots" / f"{snapshot_id}.json").read_text(encoding="utf-8"))
        if manifest.get("counts"):
            failures.append(f"{snapshot_id} invented counts")
        for name in manifest["files"]:
            if not (root / "findings" / name).exists():
                failures.append(f"{snapshot_id} lists missing {name}")
    return failures
