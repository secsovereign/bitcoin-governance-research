#!/usr/bin/env python3
"""
Architectural comparison table: Commons design dimensions ↔ Core PR proxies.

Driven by data/classification/dimension_queries.yaml and Phase 1 classifications.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger  # noqa: E402
from src.utils.paths import get_data_dir, get_findings_dir  # noqa: E402

logger = setup_logger()

# Commons evidence snippets keyed by dimension id
COMMONS_EVIDENCE = {
    "formal_spec": {
        "artifact": "blvm-spec/CONSENSUS_SPEC.md",
        "summary": "RFC-style consensus rule register (manifest rule_count)",
    },
    "spec_lock": {
        "artifact": "blvm-spec-lock/ + #[spec_locked]",
        "summary": "Z3-linked formal verification of production consensus paths",
    },
    "pure_rust_secp256k1": {
        "artifact": "blvm-secp256k1/",
        "summary": "Pure Rust secp256k1 (no C FFI at runtime)",
    },
    "utxo_commitments": {
        "artifact": "blvm-protocol/src/utxo_commitments/",
        "summary": "UTXO commitment protocol surface",
    },
    "parallel_ibd": {
        "artifact": "blvm-node/src/node/parallel_ibd/",
        "summary": "Parallel IBD engine as first-class design",
    },
    "multi_transport_p2p": {
        "artifact": "blvm-node/src/network/",
        "summary": "Multi-transport P2P (Iroh/TCP/Dandelion/Erlay)",
    },
    "module_system": {
        "artifact": "blvm-node/src/module/ + satellite module.toml",
        "summary": "Process-isolated modules (+ optional WASM), not DLL plugins",
    },
    "selective_sync": {
        "artifact": "blvm-selective-sync/",
        "summary": "Selective sync as satellite module",
    },
    "differential_testing": {
        "artifact": "blvm-bench/",
        "summary": "Differential / operator-scale testing harness",
    },
    "layered_crates": {
        "artifact": "6-tier crate stack (spec→consensus→protocol→node→bin/sdk→commons)",
        "summary": "ADR volatility gradient; layer boundaries enforced by crates",
    },
}


def _norm_labels(raw: Any) -> List[str]:
    out = []
    for item in raw or []:
        if isinstance(item, dict):
            out.append(item.get("name") or "")
        else:
            out.append(str(item))
    return [x for x in out if x]


def load_classifications(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))
    return rows


def load_enriched_index(path: Path) -> Dict[int, Dict[str, Any]]:
    """number → {title, files, body snippet} for path/title matching."""
    idx: Dict[int, Dict[str, Any]] = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            pr = json.loads(line)
            if not pr.get("merged"):
                continue
            num = int(pr["number"])
            idx[num] = {
                "title": pr.get("title") or "",
                "body": (pr.get("body") or "")[:2000],
                "files": [x.get("filename") for x in (pr.get("files") or []) if x.get("filename")],
            }
    return idx


def match_dimension(
    row: Dict[str, Any],
    enriched: Optional[Dict[str, Any]],
    dim_cfg: Dict[str, Any],
) -> bool:
    """Match Core PR to a dimension.

    If primary_categories are set: primary match, OR (path AND title) when both
    query lists are non-empty (avoids every validation.cpp touch counting as
    parallel_ibd). If no primary categories: path or title (interpretive dims).
    """
    cats = set(dim_cfg.get("primary_categories") or [])
    if cats and row.get("primary") in cats:
        return True

    if not enriched:
        return False
    files = enriched.get("files") or []
    title = (enriched.get("title") or "").lower()
    body = (enriched.get("body") or "").lower()
    text = title + "\n" + body

    path_any = dim_cfg.get("path_any") or []
    title_any = dim_cfg.get("title_any") or []

    path_hit = False
    for prefix in path_any:
        for fn in files:
            if fn.startswith(prefix) or (prefix.rstrip("/") and prefix.rstrip("/") in fn):
                path_hit = True
                break
        if path_hit:
            break

    title_hit = any(kw.lower() in text for kw in title_any)

    if cats:
        # Expand beyond primary only with path∧title (precision over recall)
        if path_any and title_any:
            return path_hit and title_hit
        return path_hit
    return path_hit or title_hit


def multi_subsystem_span(files: List[str]) -> int:
    """Count coarse Core subsystems touched (layered_crates proxy)."""
    buckets = set()
    for fn in files:
        if fn.startswith("src/rpc/") or fn.startswith("src/rest"):
            buckets.add("rpc")
        elif fn.startswith("src/net") or fn.startswith("src/addrman") or fn.startswith("src/protocol"):
            buckets.add("network")
        elif (
            fn.startswith("src/consensus/")
            or fn.startswith("src/script/")
            or fn.startswith("src/validation")
        ):
            buckets.add("consensus")
        elif fn.startswith("src/wallet/"):
            buckets.add("wallet")
        elif fn.startswith("src/qt/"):
            buckets.add("gui")
        elif fn.startswith("test/") or fn.startswith("src/test/"):
            buckets.add("test")
        elif fn.startswith("src/"):
            buckets.add("other_src")
    return len(buckets)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--queries",
        type=Path,
        default=get_data_dir() / "classification" / "dimension_queries.yaml",
    )
    parser.add_argument(
        "--classifications",
        type=Path,
        default=get_data_dir() / "processed" / "pr_architectural_classification.jsonl",
    )
    parser.add_argument(
        "--enriched",
        type=Path,
        default=get_data_dir() / "processed" / "enriched_prs.jsonl",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=get_data_dir() / "reference" / "blvm_architecture_manifest.json",
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
        default=get_findings_dir() / "data" / "architectural_comparison.json",
    )
    args = parser.parse_args()

    if yaml is None:
        raise SystemExit("PyYAML required")

    queries = yaml.safe_load(args.queries.read_text(encoding="utf-8")) or {}
    dimensions = queries.get("dimensions") or {}
    rows = load_classifications(args.classifications)
    logger.info("Loaded %s classifications", len(rows))
    enriched = load_enriched_index(args.enriched)
    logger.info("Loaded %s enriched merged PRs", len(enriched))

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    commons_metrics = {}
    if args.commons_metrics.exists():
        commons_metrics = json.loads(args.commons_metrics.read_text(encoding="utf-8"))
    phase1 = {}
    if args.phase1.exists():
        phase1 = json.loads(args.phase1.read_text(encoding="utf-8"))

    total = len(rows) or 1
    by_number = {r["number"]: r for r in rows}

    comparison_table: List[Dict[str, Any]] = []
    for dim_id, dim_cfg in dimensions.items():
        matched_nums: Set[int] = set()
        if dim_id == "layered_crates":
            cross = 0
            for num, en in enriched.items():
                span = multi_subsystem_span(en.get("files") or [])
                if span >= 3:
                    cross += 1
                    matched_nums.add(num)
            core_side = {
                "pr_proxy_count": cross,
                "pr_proxy_pct": round(100.0 * cross / total, 2),
                "definition": "merged PRs touching ≥3 coarse subsystems",
                "note": dim_cfg.get("note"),
                "exemplar_prs": sorted(matched_nums, reverse=True)[:8],
            }
        elif dim_cfg.get("note") and not (
            dim_cfg.get("primary_categories")
            or dim_cfg.get("path_any")
            or dim_cfg.get("title_any")
        ):
            # interpretive / no proxy
            core_side = {
                "pr_proxy_count": None,
                "pr_proxy_pct": None,
                "note": dim_cfg.get("note"),
            }
        else:
            for r in rows:
                en = enriched.get(r["number"])
                if match_dimension(r, en, dim_cfg):
                    matched_nums.add(r["number"])
            cat_hits = sum(
                1
                for r in rows
                if r.get("primary") in set(dim_cfg.get("primary_categories") or [])
            )
            core_side = {
                "pr_proxy_count": len(matched_nums),
                "pr_proxy_pct": round(100.0 * len(matched_nums) / total, 2),
                "primary_category_only_count": cat_hits,
                "primary_categories": dim_cfg.get("primary_categories") or [],
                "query": {
                    "path_any": dim_cfg.get("path_any") or [],
                    "title_any": dim_cfg.get("title_any") or [],
                },
                "note": dim_cfg.get("note"),
                "exemplar_prs": sorted(matched_nums, reverse=True)[:8],
            }

        commons_ev = dict(COMMONS_EVIDENCE.get(dim_id) or {})
        # Attach quantitative Commons bits where available
        posture = (commons_metrics.get("metrics") or {}).get("posture") or {}
        layers = (commons_metrics.get("metrics") or {}).get("layers") or {}
        if dim_id == "formal_spec":
            commons_ev["rule_count"] = posture.get("consensus_rule_count") or (
                manifest.get("consensus_spec") or {}
            ).get("rule_count")
        elif dim_id == "spec_lock":
            commons_ev["spec_locked_production_total"] = posture.get(
                "spec_locked_production_total"
            ) or (manifest.get("spec_lock") or {}).get("total_production_locked")
            commons_ev["core_equivalent"] = 0
        elif dim_id == "pure_rust_secp256k1":
            commons_ev["layer"] = layers.get("secp256k1")
        elif dim_id == "utxo_commitments":
            commons_ev["layer"] = layers.get("utxo_commitments")
        elif dim_id == "parallel_ibd":
            commons_ev["layer"] = layers.get("parallel_ibd")
        elif dim_id == "multi_transport_p2p":
            commons_ev["layer"] = {
                k: layers.get("node_network", {}).get(k)
                for k in ("src_loc", "transports", "test_density")
            }
        elif dim_id == "module_system":
            commons_ev["layer"] = {
                k: layers.get("modules", {}).get(k)
                for k in (
                    "src_loc",
                    "module_toml_count",
                    "satellite_count",
                    "isolation",
                )
            }
        elif dim_id == "selective_sync":
            sat = (layers.get("modules") or {}).get("satellite_crates") or {}
            commons_ev["selective_sync_crate"] = sat.get("blvm-selective-sync")
        elif dim_id == "differential_testing":
            commons_ev["layer"] = layers.get("bench")
        elif dim_id == "layered_crates":
            commons_ev["tier_stack"] = posture.get("tier_stack")

        comparison_table.append(
            {
                "dimension": dim_id,
                "description": dim_cfg.get("description"),
                "commons": commons_ev,
                "core": core_side,
            }
        )

    # Headline join from Phase 1
    headline = (phase1.get("metrics") or {}).get("headline_metrics") or {}

    payload = {
        "analysis_date": datetime.now(timezone.utc).isoformat(),
        "methodology": "docs/ARCHITECTURAL_DIVERGENCE_PLAN.md Phase 2 — dimension_queries.yaml",
        "data_sources": [
            str(args.queries),
            str(args.classifications),
            str(args.enriched),
            str(args.manifest),
            str(args.commons_metrics),
        ],
        "core_total_merged_prs": total,
        "phase1_headline_metrics": headline,
        "comparison_table": comparison_table,
        "limitations": [
            "Core side is PR-proxy counts, not proof of missing Commons features",
            "Path/title OR matching can double-count across dimensions",
            "spec_lock / selective_sync have no Core PR proxy by design",
            "layered_crates uses coarse subsystem span heuristic",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    logger.info("Wrote %s (%s dimensions)", args.output, len(comparison_table))
    for row in comparison_table:
        c = row["core"]
        logger.info(
            "  %s → proxy=%s pct=%s",
            row["dimension"],
            c.get("pr_proxy_count"),
            c.get("pr_proxy_pct"),
        )


if __name__ == "__main__":
    main()
