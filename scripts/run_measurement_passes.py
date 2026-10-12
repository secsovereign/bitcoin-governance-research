#!/usr/bin/env python3
"""Run measurement passes 1 through 7 in order.

This writes the pass JSON files. It does not call generate_all(). Gap closure
and commons report markdown stay the committed files. The shared formatter
replaces non-numeric template values with the word missing.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Pass 1 and pass 2 are one script. It writes both ingroup JSON files.
PASSES = (
    {
        "pass": 1,
        "scripts": ("scripts/analysis/rsd_ingroup_test.py",),
        "also_writes_pass": 2,
    },
    {
        "pass": 3,
        "scripts": ("scripts/analysis/commons_dynamics_test.py",),
    },
    {
        "pass": 4,
        "scripts": ("scripts/analysis/first_year_signal_test.py",),
    },
    {
        "pass": 5,
        "scripts": (
            "scripts/analysis/gap_closure_test.py",
            "scripts/analysis/merge_durability.py",
        ),
    },
    {
        "pass": 6,
        "scripts": (
            "scripts/analysis/size_adjusted_health.py",
            "scripts/analysis/comparison_effects.py",
            "scripts/analysis/discourse_recall.py",
        ),
    },
    {
        "pass": 7,
        "scripts": (
            "scripts/analysis/newcomer_divergence.py",
            "scripts/validation/interval_stability.py",
            "scripts/analysis/pass7_merged_by.py",
        ),
    },
)


def commands() -> list[list[str]]:
    ordered = []
    for block in PASSES:
        for script in block["scripts"]:
            ordered.append([sys.executable, str(ROOT / script)])
    return ordered


def main() -> int:
    if any("generate_all" in part for cmd in commands() for part in cmd):
        raise SystemExit("measurement passes must not call generate_all")
    for cmd in commands():
        print(" ".join(cmd), flush=True)
        subprocess.run(cmd, cwd=ROOT, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
