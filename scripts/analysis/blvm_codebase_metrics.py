#!/usr/bin/env python3
"""
Commons (btc-commons) static codebase metrics by architectural layer.

Phase 2 of ARCHITECTURAL_DIVERGENCE_PLAN. Does not apply Core patch-debt
formula. Reuses blvm_architecture_manifest.json where possible; augments with
per-layer path scans. blvm-bench/scripts/metrics/ provides shell LOC tooling —
this script is the research-repo JSON companion for divergence tables.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger  # noqa: E402
from src.utils.paths import get_data_dir, get_findings_dir  # noqa: E402

logger = setup_logger()

# Layer definitions from ARCHITECTURAL_DIVERGENCE_PLAN §3
LAYERS: Dict[str, Dict[str, Any]] = {
    "consensus": {
        "paths": ["blvm-consensus", "blvm-primitives"],
        "metrics_note": "spec-lock %, #[spec_locked] count, fuzz/property tests, LOC",
    },
    "protocol": {
        "paths": ["blvm-protocol"],
        "metrics_note": "spec-lock count, BIP modules, LOC",
    },
    "node_network": {
        "paths": ["blvm-node/src/network"],
        "metrics_note": "transport features, test count, LOC",
    },
    "node_rpc": {
        "paths": ["blvm-node/src/rpc"],
        "metrics_note": "method count, LOC vs module endpoints",
    },
    "node_storage": {
        "paths": ["blvm-node/src/storage"],
        "metrics_note": "backend count, IBD engine LOC",
    },
    "modules": {
        "paths": ["blvm-node/src/module"],
        "satellite_glob": True,
        "metrics_note": "count, module.toml manifests, isolation boundary",
    },
    "parallel_ibd": {
        "paths": ["blvm-node/src/node/parallel_ibd"],
        "metrics_note": "parallel IBD engine",
    },
    "utxo_commitments": {
        "paths": ["blvm-protocol/src/utxo_commitments"],
        "metrics_note": "UTXO commitment protocol surface",
    },
    "spec_lock": {
        "paths": ["blvm-spec-lock"],
        "metrics_note": "Z3-linked formal verification crate",
    },
    "secp256k1": {
        "paths": ["blvm-secp256k1"],
        "metrics_note": "pure Rust secp256k1",
    },
    "bench": {
        "paths": ["blvm-bench"],
        "metrics_note": "differential / benchmarking harness",
    },
}


def _is_test_path(p: Path) -> bool:
    parts = {x.lower() for x in p.parts}
    name = p.name.lower()
    return (
        "tests" in parts
        or "test" in parts
        or name.endswith("_tests.rs")
        or name.startswith("test_")
        or "/benches/" in str(p).replace("\\", "/")
    )


def scan_rust_tree(root: Path) -> Dict[str, Any]:
    if not root.exists():
        return {
            "present": False,
            "src_loc": 0,
            "test_loc": 0,
            "rust_files": 0,
            "test_rust_files": 0,
            "spec_locked_attrs": 0,
        }
    src_loc = test_loc = 0
    rust_files = test_files = 0
    locked = 0
    for p in root.rglob("*.rs"):
        if "target" in p.parts:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        n = text.count("\n") + (1 if text else 0)
        locked += len(re.findall(r"#\[spec_locked\b", text))
        if _is_test_path(p):
            test_loc += n
            test_files += 1
        else:
            src_loc += n
            rust_files += 1
    return {
        "present": True,
        "src_loc": src_loc,
        "test_loc": test_loc,
        "rust_files": rust_files,
        "test_rust_files": test_files,
        "spec_locked_attrs": locked,
        "test_density": round(test_loc / src_loc, 3) if src_loc else 0.0,
    }


def count_rpc_methods(rpc_dir: Path) -> int:
    if not rpc_dir.exists():
        return 0
    # Prefer explicit method registration patterns; fallback to pub async fn in handlers
    count = 0
    for p in rpc_dir.rglob("*.rs"):
        if "target" in p.parts or _is_test_path(p):
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        count += len(re.findall(r'"method"\s*:\s*"|register_method\(|\.method\(|rpc_method!', text))
        # jsonrpsee / custom macros
        count += len(re.findall(r"#\[method\(", text))
    return count


def detect_transports(network_dir: Path) -> List[str]:
    found = []
    if not network_dir.exists():
        return found
    names = " ".join(p.name.lower() for p in network_dir.rglob("*") if p.is_file())
    for label, needles in [
        ("iroh", ["iroh"]),
        ("tcp", ["tcp_transport", "tcp"]),
        ("dandelion", ["dandelion"]),
        ("erlay", ["erlay"]),
        ("quic", ["quic"]),
        ("tor", ["tor_"]),
    ]:
        if any(n in names for n in needles):
            found.append(label)
    return found


def storage_backends(storage_dir: Path) -> List[str]:
    if not storage_dir.exists():
        return []
    backends = []
    for p in storage_dir.iterdir():
        if p.is_dir() and p.name not in {"tests", "test"}:
            backends.append(p.name)
        elif p.suffix == ".rs" and any(
            k in p.name.lower() for k in ("rocks", "sqlite", "memory", "redb", "sled")
        ):
            backends.append(p.stem)
    return sorted(set(backends))


def build_metrics(commons_root: Path, manifest: Dict[str, Any]) -> Dict[str, Any]:
    layers_out: Dict[str, Any] = {}
    for name, cfg in LAYERS.items():
        path_metrics = []
        agg = {
            "src_loc": 0,
            "test_loc": 0,
            "rust_files": 0,
            "test_rust_files": 0,
            "spec_locked_attrs": 0,
        }
        for rel in cfg["paths"]:
            m = scan_rust_tree(commons_root / rel)
            path_metrics.append({"path": rel, **m})
            for k in agg:
                agg[k] += m.get(k, 0)
        entry: Dict[str, Any] = {
            "note": cfg["metrics_note"],
            "paths": cfg["paths"],
            "path_metrics": path_metrics,
            **agg,
            "test_density": round(agg["test_loc"] / agg["src_loc"], 3) if agg["src_loc"] else 0.0,
        }
        layers_out[name] = entry

    # Enrich specific layers
    net = commons_root / "blvm-node/src/network"
    layers_out["node_network"]["transports"] = detect_transports(net)
    layers_out["node_rpc"]["rpc_method_heuristic"] = count_rpc_methods(
        commons_root / "blvm-node/src/rpc"
    )
    layers_out["node_storage"]["backends"] = storage_backends(
        commons_root / "blvm-node/src/storage"
    )

    module_manifests = manifest.get("module_manifests") or []
    satellite = manifest.get("module_crates") or {}
    layers_out["modules"]["module_toml_count"] = len(module_manifests)
    layers_out["modules"]["satellite_crates"] = {
        k: {
            "src_loc": v.get("src_loc"),
            "test_loc": v.get("test_loc"),
            "spec_locked_count": v.get("spec_locked_count"),
        }
        for k, v in satellite.items()
    }
    layers_out["modules"]["satellite_count"] = len(satellite)
    layers_out["modules"]["isolation"] = "process_subprocess_plus_optional_wasm"

    # Spec / lock summary from manifest (authoritative counts)
    layers_out["consensus"]["manifest_spec_locked"] = (
        (manifest.get("spec_lock") or {}).get("by_crate", {}).get("blvm-consensus")
    )
    layers_out["protocol"]["manifest_spec_locked"] = (
        (manifest.get("spec_lock") or {}).get("by_crate", {}).get("blvm-protocol")
    )

    consensus_spec = manifest.get("consensus_spec") or {}
    posture = {
        "consensus_rule_count": consensus_spec.get("rule_count"),
        "spec_locked_production_total": (manifest.get("spec_lock") or {}).get(
            "total_production_locked"
        ),
        "module_toml_count": len(module_manifests),
        "satellite_module_crates": len(satellite),
        "tier_stack": [
            "blvm-spec",
            "blvm-consensus",
            "blvm-protocol",
            "blvm-node",
            "blvm / blvm-sdk",
            "blvm-commons",
        ],
        "age_note": "Young codebase; no multi-decade patch debt on consensus layer",
        "methodology": "static_metrics_only_no_pr_velocity",
    }

    return {
        "commons_root": str(commons_root),
        "layers": layers_out,
        "posture": posture,
        "manifest_generated_at": manifest.get("generated_at"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Commons static layer metrics (Phase 2)")
    parser.add_argument(
        "--commons-root",
        type=Path,
        default=Path("/home/user/src/btc-commons"),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=get_data_dir() / "reference" / "blvm_architecture_manifest.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=get_findings_dir() / "data" / "blvm_codebase_metrics.json",
    )
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    metrics = build_metrics(args.commons_root, manifest)
    payload = {
        "analysis_date": datetime.now(timezone.utc).isoformat(),
        "methodology": "docs/ARCHITECTURAL_DIVERGENCE_PLAN.md Phase 2 — static Commons metrics",
        "data_sources": [str(args.manifest), str(args.commons_root)],
        "limitations": [
            "Does not apply Core patch-frequency debt formula to Commons",
            "rpc_method_heuristic is pattern-based, not a formal API registry dump",
            "test_density undercounts inline #[cfg(test)] modules in src/",
            "blvm-bench operator differential-test counts are not re-verified here",
        ],
        "metrics": metrics,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    logger.info("Wrote %s", args.output)
    logger.info(
        "layers=%s rule_count=%s locked=%s",
        list(metrics["layers"].keys()),
        metrics["posture"].get("consensus_rule_count"),
        metrics["posture"].get("spec_locked_production_total"),
    )


if __name__ == "__main__":
    main()
