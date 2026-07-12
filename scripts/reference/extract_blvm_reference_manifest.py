#!/usr/bin/env python3
"""
Extract a static architectural reference manifest from a btc-commons checkout.

Phase 0 artifact for the Core vs Commons divergence study. Read-only over the
Commons tree; no GitHub API calls.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger

logger = setup_logger()

DEFAULT_COMMONS_ROOT = Path("/home/user/src/btc-commons")

PRODUCTION_CRATES = [
    "blvm-spec",
    "blvm-spec-lock",
    "blvm-primitives",
    "blvm-consensus",
    "blvm-protocol",
    "blvm-node",
    "blvm-sdk",
    "blvm-commons",
    "blvm-secp256k1",
    "blvm-muhash",
    "blvm",
]

MODULE_CRATES = [
    "blvm-governance",
    "blvm-lightning",
    "blvm-mesh",
    "blvm-stratum-v2",
    "blvm-selective-sync",
    "blvm-miningos",
    "blvm-datum",
]

COMPARISON_DIMENSIONS = {
    "formal_spec": {
        "description": "RFC-style consensus rule register",
        "paths": ["blvm-spec/CONSENSUS_SPEC.md", "blvm-spec/PROTOCOL.md"],
    },
    "spec_lock": {
        "description": "Z3-linked formal verification via blvm-spec-lock",
        "paths": ["blvm-spec-lock/", "blvm-consensus/scripts/spec-lock-verify.sh"],
    },
    "pure_rust_secp256k1": {
        "description": "Pure Rust secp256k1 (no C FFI at runtime)",
        "paths": ["blvm-secp256k1/README.md", "blvm-secp256k1/TIMING.md"],
    },
    "utxo_commitments": {
        "description": "UTXO set commitments protocol + node integration",
        "paths": [
            "blvm-protocol/src/utxo_commitments/",
            "blvm-node/src/storage/commitment_store.rs",
            "blvm-node/src/network/utxo_commitments_client.rs",
        ],
    },
    "parallel_ibd": {
        "description": "Parallel initial block download engine",
        "paths": ["blvm-node/src/node/parallel_ibd/"],
    },
    "multi_transport_p2p": {
        "description": "Iroh/QUIC/TCP multi-transport networking",
        "paths": [
            "blvm-node/src/network/iroh_transport.rs",
            "blvm-node/src/network/quinn_transport.rs",
            "blvm-node/src/network/dandelion.rs",
        ],
    },
    "module_system": {
        "description": "Process-isolated modules with optional WASM",
        "paths": ["blvm-node/docs/MODULE_SYSTEM.md", "blvm-node/src/module/"],
    },
    "selective_sync": {
        "description": "Registry-driven selective synchronization module",
        "paths": ["blvm-selective-sync/", "blvm-node/modules/selective-sync/"],
    },
    "differential_testing": {
        "description": "Empirical parity testing against Bitcoin Core",
        "paths": [
            "blvm-bench/README_DIFFERENTIAL_TESTING.md",
            "blvm-bench/src/bin/block_kernel_diff.rs",
            "blvm-bench/src/bin/sort_merge_test.rs",
        ],
    },
    "layered_crates": {
        "description": "Volatility-gradient layered crate architecture",
        "paths": ["docs/architecture/REPOSITORY_ARCHITECTURE_ADR.md"],
    },
    "rpc_vs_modules": {
        "description": "Core-compatible RPC plus module extension surface",
        "paths": ["blvm-node/src/rpc/", "blvm-node/src/module/rpc/"],
    },
}


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        try:
            return sum(1 for _ in path.open("rb"))
        except OSError:
            return 0
    total = 0
    for p in path.rglob("*"):
        if p.is_file() and p.suffix in {".rs", ".md", ".toml"}:
            try:
                total += sum(1 for _ in p.open("rb"))
            except OSError:
                continue
    return total


def count_rust_files(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return 1 if path.suffix == ".rs" else 0
    return sum(1 for p in path.rglob("*.rs"))


def count_spec_locked(root: Path, crate: str) -> int:
    crate_src = root / crate / "src"
    if not crate_src.exists():
        return 0
    pattern = re.compile(r"#\[spec_locked")
    total = 0
    for rs_file in crate_src.rglob("*.rs"):
        try:
            text = rs_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        total += len(pattern.findall(text))
    return total


def count_consensus_rules(consensus_spec: Path) -> dict[str, Any]:
    if not consensus_spec.exists():
        return {"rule_count": 0, "sections": 0, "present": False}
    text = consensus_spec.read_text(encoding="utf-8", errors="replace")
    rules = re.findall(r"^### ([A-Z]+-\d+)", text, re.MULTILINE)
    sections = len(re.findall(r"^## \d+\.", text, re.MULTILINE))
    prefixes = defaultdict(int)
    for rule in rules:
        prefixes[rule.split("-")[0]] += 1
    return {
        "present": True,
        "rule_count": len(rules),
        "sections": sections,
        "prefix_counts": dict(sorted(prefixes.items())),
        "path": str(consensus_spec),
    }


def list_module_manifests(root: Path) -> list[dict[str, Any]]:
    manifests = []
    for path in sorted(root.glob("blvm-*/module.toml")):
        manifests.append(
            {
                "crate": path.parent.name,
                "path": str(path.relative_to(root)),
            }
        )
    node_modules = root / "blvm-node" / "modules"
    if node_modules.exists():
        for path in sorted(node_modules.glob("*/module.toml")):
            manifests.append(
                {
                    "crate": path.parent.name,
                    "path": str(path.relative_to(root)),
                }
            )
    return manifests


def crate_metrics(root: Path, crate: str) -> dict[str, Any]:
    crate_dir = root / crate
    if not crate_dir.exists():
        return {"present": False}
    src = crate_dir / "src"
    tests = crate_dir / "tests"
    return {
        "present": True,
        "src_loc": count_lines(src),
        "test_loc": count_lines(tests),
        "rust_files": count_rust_files(src),
        "test_rust_files": count_rust_files(tests),
        "spec_locked_count": count_spec_locked(root, crate),
        "has_cargo_toml": (crate_dir / "Cargo.toml").exists(),
    }


def resolve_dimension_paths(root: Path) -> dict[str, Any]:
    rows = []
    for key, spec in COMPARISON_DIMENSIONS.items():
        entries = []
        for rel in spec["paths"]:
            path = root / rel
            entries.append(
                {
                    "path": rel,
                    "exists": path.exists(),
                    "loc": count_lines(path),
                    "rust_files": count_rust_files(path),
                }
            )
        rows.append(
            {
                "dimension": key,
                "description": spec["description"],
                "artifacts": entries,
                "all_present": all(e["exists"] for e in entries),
            }
        )
    return {"dimensions": rows}


def git_head(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def build_manifest(commons_root: Path) -> dict[str, Any]:
    consensus_spec = commons_root / "blvm-spec" / "CONSENSUS_SPEC.md"
    production = {crate: crate_metrics(commons_root, crate) for crate in PRODUCTION_CRATES}
    modules = {crate: crate_metrics(commons_root, crate) for crate in MODULE_CRATES}

    spec_locked_by_crate = {
        crate: production[crate].get("spec_locked_count", 0)
        for crate in ("blvm-consensus", "blvm-protocol", "blvm-node")
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "commons_root": str(commons_root),
        "commons_git_head": git_head(commons_root),
        "consensus_spec": count_consensus_rules(consensus_spec),
        "spec_lock": {
            "by_crate": spec_locked_by_crate,
            "total_production_locked": sum(spec_locked_by_crate.values()),
        },
        "production_crates": production,
        "module_crates": modules,
        "module_manifests": list_module_manifests(commons_root),
        "comparison_dimensions": resolve_dimension_paths(commons_root),
        "notes": {
            "module_model": "subprocess binaries with optional WASM; not DLL hot-load",
            "differential_testing": "operator-driven; CI differential workflow paused per blvm-bench docs",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract BLVM architectural reference manifest")
    parser.add_argument(
        "--commons-root",
        type=Path,
        default=DEFAULT_COMMONS_ROOT,
        help="Path to btc-commons checkout",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=project_root / "data" / "reference" / "blvm_architecture_manifest.json",
        help="Output JSON path",
    )
    args = parser.parse_args()

    commons_root = args.commons_root.resolve()
    if not commons_root.exists():
        logger.error("Commons root not found: %s", commons_root)
        sys.exit(1)

    manifest = build_manifest(commons_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    logger.info("Wrote manifest: %s", args.output)
    logger.info(
        "CONSENSUS_SPEC rules=%s spec_locked=%s modules=%s",
        manifest["consensus_spec"]["rule_count"],
        manifest["spec_lock"]["total_production_locked"],
        len(manifest["module_manifests"]),
    )


if __name__ == "__main__":
    main()
