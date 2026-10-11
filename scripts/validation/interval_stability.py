#!/usr/bin/env python3
"""Compare published intervals with a fresh seed-7 bootstrap.

FRAGILE means the two disagree on whether zero is excluded, or the published
bound sits within 0.02 standardized units of zero. A correlation is already
in standardized units. Any other estimate uses the distance to zero divided
by the published interval's standard deviation. Published intervals are not
rewritten.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from scripts.analysis.commons_dynamics_test import ci_from_draws  # noqa: E402
from scripts.analysis.gap_closure_test import _spearman  # noqa: E402
from src.utils.paths import get_findings_dir  # noqa: E402

SEED = 7
N_BOOT = 1000
Z_95 = 1.959963984540054
INTERVAL_RE = re.compile(
    r"interval\s+(-?\d+(?:\.\d+)?)\s+to\s+(-?\d+(?:\.\d+)?)",
    re.IGNORECASE,
)


def excludes_zero(ci: Optional[Sequence[float]]) -> Optional[bool]:
    if not isinstance(ci, (list, tuple)) or len(ci) != 2:
        return None
    try:
        lo, hi = float(ci[0]), float(ci[1])
    except (TypeError, ValueError):
        return None
    if not np.isfinite(lo) or not np.isfinite(hi):
        return None
    return hi < 0 or lo > 0


def nearer_bound(ci: Sequence[float]) -> Optional[float]:
    flag = excludes_zero(ci)
    if flag is None:
        return None
    lo, hi = float(ci[0]), float(ci[1])
    if not flag:
        return 0.0
    return abs(hi) if hi < 0 else abs(lo)


def standardized_gap(ci: Sequence[float], kind: str) -> Optional[float]:
    """Distance from the nearer bound to zero, in standardized units."""
    dist = nearer_bound(ci)
    if dist is None:
        return None
    if kind == "correlation":
        return dist
    lo, hi = float(ci[0]), float(ci[1])
    sd = (hi - lo) / (2 * Z_95)
    if sd <= 0:
        return None
    return dist / sd


def stability(published_ci: Sequence[float], fresh_ci: Optional[Sequence[float]], kind: str) -> str:
    """FRAGILE, STABLE, or UNCHECKED."""
    published = excludes_zero(published_ci)
    if published is None:
        return "UNCHECKED"
    gap = standardized_gap(published_ci, kind)
    close = gap is not None and gap < 0.02 and published
    fresh = excludes_zero(fresh_ci) if fresh_ci is not None else None
    if fresh is None:
        return "FRAGILE" if close else "UNCHECKED"
    if published != fresh or close:
        return "FRAGILE"
    return "STABLE"


def _fresh_spearman(x: np.ndarray, y: np.ndarray, rng: np.random.Generator, n_boot: int) -> Dict[str, Any]:
    estimate, pvalue = _spearman(x, y)
    draws = np.full(n_boot, np.nan)
    n = int(x.size)
    for i in range(n_boot):
        take = rng.integers(0, n, n)
        stat, _p = _spearman(x[take], y[take])
        if stat is not None:
            draws[i] = stat
    return {"estimate": estimate, "ci95": ci_from_draws(draws), "p": pvalue, "n": n}


def _volume_pairs(findings: Path) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
    from scripts.analysis.size_adjusted_health import _indicator_means

    commons = json.loads((findings / "data" / "commons_dynamics_analysis.json").read_text())
    sized = json.loads((findings / "data" / "size_adjusted_health.json").read_text())
    means = _indicator_means(commons.get("repo_year_table") or [])
    scale = {}
    for row in ((sized.get("samples") or {}).get("all_repositories") or {}).get("repositories") or []:
        count = row.get("n_prs")
        if count:
            scale[row["repo"]] = float(np.log(count))
    pairs = {}
    names = list((sized.get("indicator_volume_spearman") or {}).keys())
    for name in names:
        xs, ys = [], []
        for repo, columns in means.items():
            if repo not in scale or name not in columns:
                continue
            xs.append(float(columns[name]))
            ys.append(float(scale[repo]))
        pairs[name] = (np.asarray(xs, dtype=float), np.asarray(ys, dtype=float))
    return pairs


def _cited_intervals(findings: Path) -> List[Dict[str, Any]]:
    cited = []
    for path in sorted(findings.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in INTERVAL_RE.finditer(text):
            lo, hi = float(match.group(1)), float(match.group(2))
            window = text[max(0, match.start() - 180) : match.end() + 180].lower()
            claims = any(phrase in window for phrase in ("excludes zero", "below zero", "above zero", "supported"))
            if not claims and not excludes_zero([lo, hi]):
                continue
            if not excludes_zero([lo, hi]):
                continue
            if not claims and "excludes zero" not in window and "below zero" not in window and "above zero" not in window:
                continue
            cited.append({
                "file": path.name,
                "published_ci": [lo, hi],
                "claims_exclusion": claims,
            })
    return cited


def analyze(n_boot: int = N_BOOT, seed: int = SEED) -> Dict[str, Any]:
    findings = get_findings_dir()
    rng = np.random.default_rng(seed)
    rows: List[Dict[str, Any]] = []
    discourse = json.loads((findings / "data" / "discourse_recall.json").read_text())
    published_s1 = ((discourse.get("published_comparison") or {}).get("s1") or {})
    fresh_s1 = ((discourse.get("s1") or {}).get("number_only") or {})
    rows.append({
        "id": "capacity_S1_irc_linked",
        "kind": "coefficient",
        "source": "findings/data/first_year_signal_analysis.json",
        "fresh_source": "discourse_recall.json number_only, seed 7",
        "published_estimate": published_s1.get("estimate"),
        "published_ci95": published_s1.get("ci95"),
        "fresh_estimate": fresh_s1.get("estimate"),
        "fresh_ci95": fresh_s1.get("ci95"),
        "status": stability(published_s1.get("ci95") or [], fresh_s1.get("ci95"), "coefficient"),
        "standardized_gap": standardized_gap(published_s1.get("ci95") or [], "coefficient"),
    })
    sized = json.loads((findings / "data" / "size_adjusted_health.json").read_text())
    pairs = _volume_pairs(findings)
    for name, published in (sized.get("indicator_volume_spearman") or {}).items():
        xs, ys = pairs.get(name, (np.asarray([]), np.asarray([])))
        fresh = _fresh_spearman(xs, ys, rng, n_boot) if xs.size else {"estimate": None, "ci95": None}
        published_ci = published.get("ci95") or []
        rows.append({
            "id": f"volume_spearman.{name}",
            "kind": "correlation",
            "source": "findings/data/size_adjusted_health.json",
            "fresh_source": "seed 7 bootstrap of the same repository pairs",
            "published_estimate": published.get("estimate"),
            "published_ci95": published.get("ci95"),
            "fresh_estimate": fresh.get("estimate"),
            "fresh_ci95": fresh.get("ci95"),
            "status": stability(published_ci, fresh.get("ci95"), "correlation"),
            "standardized_gap": standardized_gap(published_ci, "correlation") if published_ci else None,
        })
    newcomer_path = findings / "data" / "newcomer_divergence.json"
    published_newcomer = json.loads((findings / "data" / "rsd_ingroup_analysis_v2.json").read_text())
    published_interaction = None
    for block in ((published_newcomer.get("drawbridge") or {}).get("interaction") or []):
        if block.get("outcome") == "merge":
            published_interaction = block
            break
    if newcomer_path.exists() and published_interaction:
        fresh_new = ((json.loads(newcomer_path.read_text()).get("core") or {}).get("interaction") or {})
        published_ci = published_interaction.get("ci95") or []
        rows.append({
            "id": "newcomer_merge_interaction",
            "kind": "coefficient",
            "source": "findings/data/rsd_ingroup_analysis_v2.json",
            "fresh_source": "newcomer_divergence.json core interaction, seed 7",
            "published_estimate": published_interaction.get("interaction_per_year"),
            "published_ci95": published_ci,
            "fresh_estimate": fresh_new.get("estimate"),
            "fresh_ci95": fresh_new.get("ci95"),
            "status": stability(published_ci, fresh_new.get("ci95"), "coefficient"),
            "standardized_gap": standardized_gap(published_ci, "coefficient") if published_ci else None,
        })
    cited = _cited_intervals(findings)
    payload = {
        "version": "7.0",
        "seed": seed,
        "bootstrap": n_boot,
        "rule": (
            "FRAGILE when a fresh seed-7 bootstrap disagrees with the published interval on whether zero is excluded, "
            "or the published bound is within 0.02 standardized units of zero. "
            "A correlation uses the correlation unit. Any other estimate divides the distance to zero by the published interval's standard deviation. "
            "Published intervals are not changed."
        ),
        "estimates": rows,
        "fragile": [row["id"] for row in rows if row["status"] == "FRAGILE"],
        "cited_excluding_intervals": cited,
        "what_this_cannot_prove": [
            "A FRAGILE mark is about the interval, not about the point estimate.",
            "An estimate with no fresh bootstrap stays UNCHECKED unless its published bound is within 0.02 standardized units of zero.",
        ],
    }
    out = findings / "data" / "interval_stability.json"
    out.write_text(json.dumps(payload, indent=2))
    analysis = project_root / "analysis" / "findings" / "data" / "interval_stability.json"
    analysis.parent.mkdir(parents=True, exist_ok=True)
    analysis.write_text(json.dumps(payload, indent=2))
    return payload


def main() -> int:
    payload = analyze()
    print(json.dumps({"fragile": payload["fragile"], "n": len(payload["estimates"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
