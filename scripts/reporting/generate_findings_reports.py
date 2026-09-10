#!/usr/bin/env python3
"""Regenerate findings markdown. Canonical report entry point.

See scripts/reporting/README.md.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]


def _run(script: str) -> int:
    cmd = [sys.executable, str(project_root / script)]
    print(f"\n>>> {' '.join(cmd)}")
    return subprocess.call(cmd, cwd=str(project_root))


def _mirror() -> int:
    sys.path.insert(0, str(project_root))
    from src.utils.findings_io import extract_nested_json, mirror_analysis_json

    copied = mirror_analysis_json()
    deputies = extract_nested_json(
        "merge_pattern_analysis.json",
        "merge_relationships.high_volume_merger_deputies",
        "high_volume_merger_deputies.json",
    )
    if copied:
        print("Mirrored JSON: " + ", ".join(copied))
    if deputies:
        print("Extracted high_volume_merger_deputies.json")
    return 0


def main() -> int:
    steps = [
        _mirror,
        "scripts/analysis/governance_frames.py",
        "scripts/reporting/generate_cross_platform_reports.py",
        "scripts/reporting/generate_from_templates.py",
        "scripts/reporting/patch_project_docs.py",
    ]
    failed = []
    for step in steps:
        if callable(step):
            print("\n>>> mirror analysis JSON")
            if step() != 0:
                failed.append("mirror_analysis_json")
        elif _run(step) != 0:
            failed.append(step)
    if failed:
        print(f"\nFailed: {', '.join(str(s) for s in failed)}")
        return 1
    print("\nAll findings reports and doc patches complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
