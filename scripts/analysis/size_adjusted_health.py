#!/usr/bin/env python3
"""Size-adjusted shared health on the comparison set already on disk.

Shared health is the cross-repository index from the commons pass.
Scale comes from the pull-request dumps. Review objects are not required
and are not imputed from comments_count.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from scripts.analysis.commons_dynamics_test import ci_from_draws, p_from_draws  # noqa: E402
from scripts.analysis.first_year_signal_test import N_BOOT, SEED, jsonable, unavailable  # noqa: E402
from scripts.analysis.gap_closure_test import spearman_with_ci  # noqa: E402
from src.utils.findings_io import save_analysis_json  # noqa: E402
from src.utils.paths import get_data_dir, get_findings_dir  # noqa: E402

SHARED_HEALTH = [
    "H2_open_stock_per_pr_opened",
    "H2_stale_open_per_pr_opened",
    "H3_cohort_active_24m",
    "H4_gini_merges",
    "H5_bus_factor",
    "H6_median_days_to_decision",
]

ROLES = {
    "bitcoin/bitcoin": "node",
    "lightningnetwork/lnd": "implementation",
    "ElementsProject/lightning": "implementation",
    "ACINQ/eclair": "implementation",
    "lightningdevkit/rust-lightning": "implementation",
    "rust-bitcoin/rust-bitcoin": "library",
    "rust-bitcoin/rust-miniscript": "library",
    "bitcoindevkit/bdk": "library",
    "bitcoin-core/secp256k1": "library",
    "sparrowwallet/sparrow": "wallet_hardware",
    "SeedSigner/seedsigner": "wallet_hardware",
    "bitcoin-core/HWI": "wallet_hardware",
    "lightning/bolts": "spec",
    "bitcoin-core/bitcoin-maintainer-tools": "tooling",
}
SHARED_MAINTAINERS = {
    "bitcoin-core/secp256k1",
    "bitcoin-core/HWI",
    "bitcoin-core/bitcoin-maintainer-tools",
}
CORE = "bitcoin/bitcoin"


def _year(created: str) -> Optional[int]:
    text = str(created or "")
    if len(text) < 4 or not text[:4].isdigit():
        return None
    return int(text[:4])


def repo_scale(path: Path) -> Dict[str, Any]:
    authors_by_year: Dict[int, set] = {}
    n = 0
    if not path.exists():
        return {"status": "DATA UNAVAILABLE", "reason": f"{path} is missing"}
    with path.open() as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            n += 1
            year = _year(row.get("created_at") or "")
            author = row.get("author")
            if year is None or not author:
                continue
            authors_by_year.setdefault(year, set()).add(str(author))
    if n == 0 or not authors_by_year:
        return {"status": "DATA UNAVAILABLE", "reason": "the dump has no pull requests with an author and a year"}
    annual = [len(authors) for authors in authors_by_year.values()]
    mean_annual = float(np.mean(annual))
    first, last = min(authors_by_year), max(authors_by_year)
    return {
        "status": "ok",
        "n_prs": n,
        "log_total_prs": float(np.log(n)),
        "mean_annual_authors": mean_annual,
        "log_mean_annual_authors": float(np.log(mean_annual)),
        "years_of_history": int(last - first + 1),
    }


def _design(rows: Sequence[Dict[str, Any]]) -> np.ndarray:
    return np.column_stack([
        np.ones(len(rows)),
        np.asarray([row["log_total_prs"] for row in rows], dtype=float),
        np.asarray([row["log_mean_annual_authors"] for row in rows], dtype=float),
        np.asarray([row["years_of_history"] for row in rows], dtype=float),
    ])


def _fit(rows: Sequence[Dict[str, Any]]) -> Optional[np.ndarray]:
    if len(rows) < 5:
        return None
    y = np.asarray([row["health"] for row in rows], dtype=float)
    beta, *_ = np.linalg.lstsq(_design(rows), y, rcond=None)
    return beta


def _predict(beta: np.ndarray, row: Dict[str, Any]) -> float:
    x = np.asarray([1.0, row["log_total_prs"], row["log_mean_annual_authors"], row["years_of_history"]], dtype=float)
    return float(x @ beta)


def loo_residual(rows: Sequence[Dict[str, Any]], index: int, rng: np.random.Generator, n_boot: int) -> Dict[str, Any]:
    held = rows[index]
    train = [row for i, row in enumerate(rows) if i != index]
    beta = _fit(train)
    if beta is None:
        return {"status": "DATA UNAVAILABLE", "reason": "leave-one-out fit has fewer than 5 repositories"}
    residual = float(held["health"] - _predict(beta, held))
    draws = np.full(n_boot, np.nan)
    if n_boot and len(train) >= 5:
        pool = np.arange(len(train))
        for i in range(n_boot):
            take = pool[rng.integers(0, pool.size, pool.size)]
            sample = [train[j] for j in take]
            fitted = _fit(sample)
            if fitted is None:
                continue
            draws[i] = float(held["health"] - _predict(fitted, held))
    return {
        "status": "ok",
        "residual": residual,
        "ci95": ci_from_draws(draws),
        "p": p_from_draws(draws),
        "low_power": len(rows) < 20,
        "n": len(rows),
    }


def _rank_of_core(rows: Sequence[Dict[str, Any]]) -> Optional[int]:
    ordered = sorted(rows, key=lambda row: row["residual"])
    for position, row in enumerate(ordered, start=1):
        if row["repo"] == CORE:
            return position
    return None


def _indicator_means(table: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    buckets: Dict[str, Dict[str, List[float]]] = {}
    for row in table:
        repo = row["repo"]
        indicators = row.get("indicators") or {}
        slot = buckets.setdefault(repo, {name: [] for name in SHARED_HEALTH})
        for name in SHARED_HEALTH:
            value = indicators.get(name)
            if value is not None and np.isfinite(value):
                slot[name].append(float(value))
    means = {}
    for repo, columns in buckets.items():
        means[repo] = {name: float(np.mean(values)) for name, values in columns.items() if values}
    return means


def _sample(rows: Sequence[Dict[str, Any]], which: str) -> List[Dict[str, Any]]:
    if which == "all_repositories":
        return list(rows)
    if which == "bolts_excluded":
        return [row for row in rows if row["repo"] != "lightning/bolts"]
    if which == "shared_maintainers_excluded":
        return [row for row in rows if not row["shared_maintainers"]]
    raise KeyError(which)


def analyze(n_boot: int = N_BOOT, seed: int = SEED) -> Dict[str, Any]:
    rng = np.random.default_rng(seed)
    findings = get_findings_dir()
    data_dir = get_data_dir()
    missing: List[Dict[str, str]] = []
    commons_path = findings / "data" / "commons_dynamics_analysis.json"
    prereg = json.loads((findings / "data" / "pass6_preregistration.json").read_text())
    if not commons_path.exists():
        unavailable(missing, "shared_health", "commons_dynamics_analysis.json is missing")
        payload = {"status": "DATA UNAVAILABLE", "data_unavailable": missing}
        save_analysis_json("size_adjusted_health.json", payload)
        return payload
    commons = json.loads(commons_path.read_text())
    health = {row["repo"]: row.get("mean_health") for row in commons.get("cross_repo_ranking") or []}
    indicator_means = _indicator_means(commons.get("repo_year_table") or [])
    rows = []
    for repo, score in sorted(health.items()):
        if score is None:
            unavailable(missing, repo, "shared health is missing")
            continue
        dump = data_dir / "github" / "repos" / repo / "prs.jsonl"
        if repo == CORE:
            dump = data_dir / "github" / "prs_raw.jsonl"
        scale = repo_scale(dump)
        if scale.get("status") != "ok":
            unavailable(missing, repo, scale.get("reason", "scale data missing"))
            continue
        rows.append({
            "repo": repo,
            "role": ROLES.get(repo, "other"),
            "shared_maintainers": repo in SHARED_MAINTAINERS,
            "health": float(score),
            **{key: scale[key] for key in ("n_prs", "log_total_prs", "log_mean_annual_authors", "years_of_history", "mean_annual_authors")},
        })
    samples = {}
    for name in ("all_repositories", "bolts_excluded", "shared_maintainers_excluded"):
        sample = _sample(rows, name)
        fitted = []
        for index, row in enumerate(sample):
            residual = loo_residual(sample, index, rng, n_boot)
            fitted.append({**row, **residual})
        core = next((row for row in fitted if row["repo"] == CORE), None)
        ci = None if core is None else core.get("ci95")
        covers = bool(ci and ci[0] <= 0 <= ci[1])
        samples[name] = {
            "n": len(sample),
            "low_power": len(sample) < 20,
            "core_residual": None if core is None else core.get("residual"),
            "core_ci95": None if core is None else core.get("ci95"),
            "core_sign": None if core is None or core.get("residual") is None else ("negative" if core["residual"] < 0 else "positive" if core["residual"] > 0 else "zero"),
            "core_rank_most_negative": _rank_of_core(fitted),
            "matches_preregistration": None if core is None or core.get("residual") is None else bool(core["residual"] < 0),
            "interval_covers_zero": covers,
            "repositories": [
                {
                    "repo": row["repo"],
                    "role": row["role"],
                    "shared_maintainers": row["shared_maintainers"],
                    "health": row["health"],
                    "n_prs": row["n_prs"],
                    "years_of_history": row["years_of_history"],
                    "residual": row.get("residual"),
                    "ci95": row.get("ci95"),
                    "low_power": True,
                }
                for row in sorted(fitted, key=lambda item: (item.get("residual") is None, item.get("residual") or 0))
            ],
        }
    volume = np.asarray([row["log_total_prs"] for row in rows], dtype=float)
    correlations = {}
    for name in SHARED_HEALTH:
        ys = []
        xs = []
        for row in rows:
            value = (indicator_means.get(row["repo"]) or {}).get(name)
            if value is None:
                continue
            xs.append(row["log_total_prs"])
            ys.append(value)
        correlations[name] = spearman_with_ci(np.asarray(xs, dtype=float), np.asarray(ys, dtype=float), rng, n_boot)
        correlations[name]["measures_scale"] = bool(
            correlations[name].get("ci95") and correlations[name]["ci95"][0] * correlations[name]["ci95"][1] > 0
        )
    payload = {
        "version": "6.0",
        "task": 3,
        "preregistration": prereg["predictions"]["task3_core_residual"],
        "preregistration_timestamp": prereg["timestamp"],
        "status": "ok",
        "low_power": True,
        "outcome": "shared health from cross_repo_ranking.mean_health",
        "controls": ["log total pull requests", "log mean distinct authors per year", "years of history"],
        "samples": samples,
        "indicator_volume_spearman": correlations,
        "scale_indicators": [name for name, row in correlations.items() if row.get("measures_scale")],
        "data_unavailable": missing,
        "what_this_cannot_prove": [
            "Seventeen repositories cannot separate size from governance. Every residual is LOW POWER.",
            "Shared health omits review labor, which the thin dumps do not carry. Adjusting it for size does not create that missing labor measure.",
            "A negative residual says Core sits below the size line. It does not say why.",
        ],
    }
    del volume
    save_analysis_json("size_adjusted_health.json", jsonable(payload))
    return payload


def main() -> int:
    result = analyze()
    core = (result.get("samples") or {}).get("all_repositories") or {}
    print(result.get("status"), "core residual", core.get("core_residual"), "sign", core.get("core_sign"))
    return 0 if result.get("status") == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
