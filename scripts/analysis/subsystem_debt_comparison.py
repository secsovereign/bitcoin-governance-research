#!/usr/bin/env python3
"""
Subsystem debt comparison: Core turnover debt vs Commons static layer metrics.

Does NOT apply Core debt_score formula to Commons.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger  # noqa: E402
from src.utils.paths import get_findings_dir  # noqa: E402

logger = setup_logger()

# Map Core subsystem keys → Commons layer keys / narrative
SIDE_BY_SIDE = [
    {
        "axis": "consensus",
        "core_subsystem": "consensus",
        "commons_layers": ["consensus", "spec_lock"],
        "interpretation": (
            "Core consensus files show accumulated patch debt; Commons consensus is "
            "spec-locked with formal verification surface."
        ),
    },
    {
        "axis": "rpc",
        "core_subsystem": "rpc",
        "commons_layers": ["node_rpc", "modules"],
        "interpretation": (
            "Core RPC is a high-debt growth surface (monolith). Commons splits node RPC "
            "from process-isolated module endpoints."
        ),
    },
    {
        "axis": "network",
        "core_subsystem": "network",
        "commons_layers": ["node_network", "parallel_ibd"],
        "interpretation": (
            "Core P2P evolves on a legacy stack via networking_change / debt patches; "
            "Commons ships multi-transport + parallel IBD as designed subsystems."
        ),
    },
    {
        "axis": "script",
        "core_subsystem": "script",
        "commons_layers": ["consensus"],
        "interpretation": (
            "Core script interpreter sits in the consensus debt surface; Commons folds "
            "script rules into the consensus crate + CONSENSUS_SPEC."
        ),
    },
    {
        "axis": "wallet",
        "core_subsystem": "wallet",
        "commons_layers": [],
        "interpretation": (
            "Wallet is out of primary divergence axes (classified Core 'other'). "
            "Commons wallet surfaces live in SDK/app layers, not consensus."
        ),
    },
    {
        "axis": "test",
        "core_subsystem": "test",
        "commons_layers": ["bench", "consensus"],
        "interpretation": (
            "Core test_ci_build is a large share of PR volume; Commons emphasizes "
            "spec-lock + differential bench posture rather than PR test churn."
        ),
    },
]


def slim_core_subsystem(entry: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "files": entry.get("files"),
        "avg_debt_score": round(float(entry.get("avg_debt_score") or 0), 2),
        "high_debt_percentage": round(float(entry.get("high_debt_percentage") or 0), 2),
        "untouchable_percentage": round(float(entry.get("untouchable_percentage") or 0), 2),
        "total_patches": entry.get("total_patches"),
        "total_refactors": entry.get("total_refactors"),
        "patch_to_refactor_ratio": round(float(entry.get("patch_to_refactor_ratio") or 0), 3),
    }


def slim_commons_layer(entry: Dict[str, Any]) -> Dict[str, Any]:
    if not entry:
        return {}
    keep = [
        "src_loc",
        "test_loc",
        "test_density",
        "rust_files",
        "spec_locked_attrs",
        "manifest_spec_locked",
        "transports",
        "rpc_method_heuristic",
        "backends",
        "module_toml_count",
        "satellite_count",
        "isolation",
    ]
    return {k: entry[k] for k in keep if k in entry}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--turnover",
        type=Path,
        default=get_findings_dir() / "data" / "code_turnover_analysis.json",
    )
    parser.add_argument(
        "--commons-metrics",
        type=Path,
        default=get_findings_dir() / "data" / "blvm_codebase_metrics.json",
    )
    parser.add_argument(
        "--phase1",
        type=Path,
        default=get_findings_dir() / "data" / "pr_architectural_classification.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=get_findings_dir() / "data" / "subsystem_debt_comparison.json",
    )
    args = parser.parse_args()

    turnover = json.loads(args.turnover.read_text(encoding="utf-8"))
    commons = json.loads(args.commons_metrics.read_text(encoding="utf-8"))
    phase1 = json.loads(args.phase1.read_text(encoding="utf-8")) if args.phase1.exists() else {}

    agg = turnover.get("aggregate_metrics") or {}
    core_debt = agg.get("subsystem_debt") or {}
    core_dist = agg.get("subsystem_distribution") or {}
    layers = (commons.get("metrics") or {}).get("layers") or {}
    posture = (commons.get("metrics") or {}).get("posture") or {}

    rows: List[Dict[str, Any]] = []
    for spec in SIDE_BY_SIDE:
        core_key = spec["core_subsystem"]
        core_entry = core_debt.get(core_key) or {}
        commons_side = {
            layer: slim_commons_layer(layers.get(layer) or {})
            for layer in spec["commons_layers"]
        }
        rows.append(
            {
                "axis": spec["axis"],
                "interpretation": spec["interpretation"],
                "core": {
                    "subsystem": core_key,
                    "file_count_in_distribution": core_dist.get(core_key),
                    "debt": slim_core_subsystem(core_entry) if core_entry else None,
                },
                "commons": commons_side,
            }
        )

    # Highlight RPC debt contrast (plan headline)
    rpc = slim_core_subsystem(core_debt.get("rpc") or {})
    payload = {
        "analysis_date": datetime.now(timezone.utc).isoformat(),
        "methodology": (
            "docs/ARCHITECTURAL_DIVERGENCE_PLAN.md Phase 2 — Core turnover debt vs "
            "Commons static layers (asymmetric metrics)"
        ),
        "data_sources": [str(args.turnover), str(args.commons_metrics), str(args.phase1)],
        "core_turnover_meta": {
            "analysis_date": turnover.get("analysis_date"),
            "total_prs_analyzed": turnover.get("total_prs_analyzed"),
            "overall_patch_to_refactor_ratio": agg.get("overall_patch_to_refactor_ratio"),
            "technical_debt_metrics": agg.get("technical_debt_metrics"),
        },
        "phase1_headline_metrics": (phase1.get("metrics") or {}).get("headline_metrics"),
        "headline_contrasts": {
            "core_rpc_avg_debt_score": rpc.get("avg_debt_score"),
            "core_rpc_high_debt_pct": rpc.get("high_debt_percentage"),
            "core_rpc_patch_to_refactor": rpc.get("patch_to_refactor_ratio"),
            "commons_module_isolation": (layers.get("modules") or {}).get("isolation"),
            "commons_spec_locked_total": posture.get("spec_locked_production_total"),
            "commons_consensus_rules": posture.get("consensus_rule_count"),
        },
        "comparison_table": rows,
        "limitations": [
            "Core debt scores from Feb 2026 turnover snapshot (15,884 PRs); may lag regenerated corpus",
            "Commons metrics are static (LOC/spec-lock/features) — not debt_score",
            "Subsystem taxonomies are not 1:1 across C++ monolith vs Rust crates",
            "Do not interpret lower Commons LOC as lower complexity",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    logger.info("Wrote %s", args.output)
    logger.info(
        "RPC avg_debt=%s high_debt_pct=%s commons_locked=%s",
        rpc.get("avg_debt_score"),
        rpc.get("high_debt_percentage"),
        posture.get("spec_locked_production_total"),
    )


if __name__ == "__main__":
    main()
