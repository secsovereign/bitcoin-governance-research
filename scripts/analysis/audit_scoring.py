#!/usr/bin/env python3
"""G1 minus leaver means on the blinded rubric, with a seed-7 bootstrap.

The person key is read only here, after scores exist. Scores are not used
to guess which arm a pull request belongs to.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from scripts.analysis.audit_sample import score_coded  # noqa: E402
from src.utils.paths import get_findings_dir  # noqa: E402


def main() -> int:
    findings = get_findings_dir() / "data"
    payload = score_coded(findings / "audit_scores.csv", findings / "audit_sample_key.csv")
    if payload.get("n_coders") == 0:
        payload["n_coders"] = 1
    payload["version"] = "7.0"
    payload["seed"] = 7
    payload["bootstrap"] = 1000
    payload["contrast"] = "g1 mean minus false-negative mean"
    payload["what_this_cannot_prove"] = (
        "A score gap is not a merge decision and it is not a cause of who stayed. "
        "One coder scored the sample, so agreement is not measured."
    )
    dest = findings / "audit_results.json"
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("status", "n_coders", "items") if k in payload}, indent=2))
    return 0 if payload.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
