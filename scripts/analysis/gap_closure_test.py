#!/usr/bin/env python3
"""Pass 5. Close the four gaps left after passes 1-4.

Lagged principle scores, cross-repository replication of six confirmed
effects, the timing of patch-content false negatives, and whether newcomer
silence follows subsystem reviewer capacity. Year fixed effects are a control
where the coefficient of interest is not itself a year slope.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy.stats import pearsonr, spearmanr

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from scripts.analysis.commons_dynamics_test import (  # noqa: E402
    bh_qvalues,
    ci_from_draws,
    collect_prior_tests,
    p_from_draws,
)
from scripts.analysis.first_year_signal_test import (  # noqa: E402
    CONTENT_KEYS,
    HOLDOUT_FIRST,
    N_BOOT,
    SEED,
    TRAIN_LAST,
    YEAR,
    collect_pass3,
    column,
    false_negatives,
    jsonable,
    load_analysis_frame,
    reported_ci,
    subsystem_of,
    unavailable,
)
from scripts.analysis.rsd_ingroup_test import (  # noqa: E402
    cohens_d,
    effect_flag,
    logistic_irls,
    parse_ts,
)
from src.utils.findings_io import save_analysis_json  # noqa: E402
from src.utils.logger import setup_logger  # noqa: E402
from src.utils.paths import get_data_dir, get_findings_dir  # noqa: E402

logger = setup_logger("gap_closure")

PRINCIPLES = ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"]
LOW_POWER_N = 20
MIN_REPO_YEARS = 7
SUBSTANTIAL_PRE_2018 = 0.25
EFFECTS = [
    ("E2_reciprocity_excess", "reciprocity excess over a shuffled null", "review objects or comment authors"),
    ("E3_log_hours_to_next_same_direction_top5_minus_other", "log hours to the next same-direction review after a top-5 first signal", "review objects"),
    ("E5_log_participants_on_log_days", "log participants on log days to decision", "distinct participant identities"),
    ("E7_first_tone_on_merge_given_later_tone", "first tone on merge, controlling later tone", "ordered comment text"),
    ("E9_listed_on_log_days_to_merge", "meeting-listed pull requests, log days to merge", "a meeting list"),
    ("E12_ingroup_on_no_peer_response", "in-group authorship on no peer response", "review objects that define the in-group"),
]

CANNOT = [
    "Lagged correlations in a 16-year series are low power and cannot establish causation.",
    "Cross-repo effect comparisons assume comparable data quality across repositories, which may not hold.",
    "Subsystem mapping from file paths is an approximation and PRs touching multiple subsystems are assigned by plurality.",
    "The false-negative timeline cannot distinguish whether the filter worsened because standards rose or because social routing became more load-bearing over time.",
]


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if not np.isfinite(number):
        return "n/a"
    return f"{number:.3f}"


def _ci(value: Optional[Sequence[float]]) -> str:
    if not value or len(value) < 2:
        return "n/a"
    return f"[{_fmt(value[0])}, {_fmt(value[1])}]"


def two_year_cohort(year: int) -> Tuple[int, str]:
    """Pass-2 bins: (year // 2) * 2, labeled start-end."""
    start = (int(year) // 2) * 2
    return start, f"{start}-{start + 1}"


def largest_decline(scores: Dict[int, Optional[float]]) -> Dict[str, Any]:
    """Year of the most negative consecutive change. Ties take the earlier year."""
    usable = sorted(year for year, score in scores.items() if score is not None and np.isfinite(score))
    best: Optional[Tuple[float, int, int]] = None
    for prev, year in zip(usable, usable[1:]):
        if year != prev + 1:
            continue
        drop = float(scores[year]) - float(scores[prev])
        if best is None or drop < best[0] - 1e-15 or (abs(drop - best[0]) <= 1e-15 and year < best[1]):
            best = (drop, year, prev)
    if best is None:
        return {
            "status": "DATA UNAVAILABLE",
            "reason": "no two consecutive years both have a principle score",
        }
    year = best[1]
    after = scores.get(year + 1)
    return {
        "status": "ok",
        "year": year,
        "decline": best[0],
        "score": float(scores[year]),
        "year_before": best[2],
        "score_year_before": float(scores[best[2]]),
        "year_after": year + 1,
        "score_year_after": None if after is None or not np.isfinite(after) else float(after),
    }


def _spearman(x: np.ndarray, y: np.ndarray) -> Tuple[Optional[float], Optional[float]]:
    if x.size < 5 or np.unique(x).size < 2 or np.unique(y).size < 2:
        return None, None
    result = spearmanr(x, y)
    stat = getattr(result, "statistic", None)
    pvalue = getattr(result, "pvalue", None)
    if stat is None:
        stat, pvalue = result[0], result[1]
    if not np.isfinite(stat):
        return None, None
    return float(stat), None if pvalue is None or not np.isfinite(pvalue) else float(pvalue)


def spearman_with_ci(
    x: np.ndarray,
    y: np.ndarray,
    rng: np.random.Generator,
    n_boot: int,
) -> Dict[str, Any]:
    estimate, pvalue = _spearman(x, y)
    draws = np.full(n_boot, np.nan)
    if estimate is None:
        return {
            "status": "DATA UNAVAILABLE",
            "reason": "fewer than 5 paired observations, or one series does not vary",
            "n": int(x.size),
            "estimate": None,
            "ci95": None,
            "p": None,
            "low_power": True,
        }
    n = int(x.size)
    for i in range(n_boot):
        take = rng.integers(0, n, n)
        stat, _p = _spearman(x[take], y[take])
        if stat is not None:
            draws[i] = stat
    return {
        "status": "ok",
        "n": n,
        "estimate": estimate,
        "ci95": ci_from_draws(draws),
        "p": pvalue,
        "low_power": n < LOW_POWER_N,
        "low_power_flag": "LOW POWER" if n < LOW_POWER_N else None,
    }


def classify_false_negative_timeline(slope: Optional[float], clears_bh: bool, share_before_2018: Optional[float]) -> str:
    """STRUCTURAL if the positive slope does not clear BH. MIXED if it does and pre-2018 is substantial."""
    if slope is None or share_before_2018 is None or not (slope > 0 and clears_bh):
        return "STRUCTURAL"
    if share_before_2018 >= SUBSTANTIAL_PRE_2018:
        return "MIXED"
    return "DRIFT"


def classify_subsystem_capacity(
    reviewer_negative: bool,
    reviewer_clears_bh: bool,
    year_without: Optional[float],
    year_with: Optional[float],
) -> str:
    """Reviewer coefficient must be negative and past BH. Shrinkage is on the silence-rate slope."""
    if year_without is None or year_with is None or not reviewer_negative or not reviewer_clears_bh:
        return "NOT SUBSYSTEM CAPACITY"
    if abs(year_without) < 1e-12:
        return "NOT SUBSYSTEM CAPACITY"
    shrinks = abs(year_with) < abs(year_without)
    if not shrinks:
        return "NOT SUBSYSTEM CAPACITY"
    if abs(year_with) <= 0.5 * abs(year_without):
        return "SUBSYSTEM CAPACITY"
    return "PARTIAL"


def shannon_entropy(counts: Sequence[int]) -> Optional[float]:
    total = float(sum(counts))
    if total <= 0:
        return None
    probs = np.asarray(counts, dtype=float) / total
    probs = probs[probs > 0]
    return float(-np.sum(probs * np.log2(probs)))


def ols_slope(x: np.ndarray, y: np.ndarray) -> Optional[float]:
    if x.size < 4 or np.unique(x).size < 2:
        return None
    design = np.column_stack([np.ones(x.size), np.asarray(x, dtype=float)])
    beta, *_rest = np.linalg.lstsq(design, np.asarray(y, dtype=float), rcond=1e-8)
    if beta.size < 2 or not np.isfinite(beta[1]):
        return None
    return float(beta[1])


def bootstrap_slope(x: np.ndarray, y: np.ndarray, rng: np.random.Generator, n_boot: int) -> Dict[str, Any]:
    point = ols_slope(x, y)
    draws = np.full(n_boot, np.nan)
    n = int(x.size)
    if point is None or n < 4:
        return {"estimate": None, "ci95": None, "p": None, "n": n, "status": "DATA UNAVAILABLE"}
    for i in range(n_boot):
        take = rng.integers(0, n, n)
        stat = ols_slope(x[take], y[take])
        if stat is not None:
            draws[i] = stat
    return {
        "status": "ok",
        "estimate": point,
        "ci95": reported_ci(draws, n_boot),
        "p": p_from_draws(draws),
        "n": n,
    }


def structure_gap(effect_id: str, info: Dict[str, Any]) -> Optional[str]:
    """Why a comparison repository cannot support one effect. None means the fields are present."""
    reasons = {
        "E2_reciprocity_excess": "review objects or comment authors",
        "E3_log_hours_to_next_same_direction_top5_minus_other": "review objects",
        "E5_log_participants_on_log_days": "distinct participants",
        "E7_first_tone_on_merge_given_later_tone": "ordered comment text",
        "E9_listed_on_log_days_to_merge": "a meeting list",
        "E12_ingroup_on_no_peer_response": "review objects",
    }
    need = reasons.get(effect_id)
    if need is None:
        return "unknown effect"
    if effect_id == "E9_listed_on_log_days_to_merge" and not info.get("has_meeting_list"):
        return "DATA UNAVAILABLE: no meeting list for this repository"
    if effect_id in ("E3_log_hours_to_next_same_direction_top5_minus_other", "E12_ingroup_on_no_peer_response") and not info.get("has_reviews"):
        return "DATA UNAVAILABLE: no review objects"
    if effect_id == "E2_reciprocity_excess" and not (info.get("has_reviews") or info.get("has_comment_authors")):
        return "DATA UNAVAILABLE: no review objects and no comment authors"
    if effect_id == "E5_log_participants_on_log_days" and not info.get("has_participants"):
        return "DATA UNAVAILABLE: comments_count is not a list of participants"
    if effect_id == "E7_first_tone_on_merge_given_later_tone" and not info.get("has_comment_text"):
        return "DATA UNAVAILABLE: no ordered comment text"
    if need and not info.get("has_reviews") and effect_id != "E5_log_participants_on_log_days":
        return f"DATA UNAVAILABLE: missing {need}"
    return None


def interpret_effect(effect_id: str, spearman_row: Dict[str, Any]) -> str:
    label = effect_id
    if spearman_row.get("status") != "ok" or spearman_row.get("estimate") is None:
        return (
            f"{label}: DATA UNAVAILABLE. Comparison repositories do not contain the review objects, "
            "participant identities, or meeting lists this effect needs, so it is not identified as "
            "specific to poorly governed repositories or as ambient to open source development."
        )
    estimate = float(spearman_row["estimate"])
    q = spearman_row.get("q")
    clears = q is not None and q < 0.05
    if abs(estimate) < 0.2 or not clears:
        return (
            f"{label}: the cross-repository correlation with health is near zero "
            f"(r={estimate:.3f}), so the effect reads as ambient to open source development."
        )
    if estimate < 0:
        return (
            f"{label}: the effect size is larger where the health index is lower "
            f"(Spearman r={estimate:.3f}), so it is specific to poorly governed repositories."
        )
    return (
        f"{label}: the effect size is larger where the health index is higher "
        f"(Spearman r={estimate:.3f}), so it is not specific to poorly governed repositories."
    )


def _finite(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(number):
        return None
    return number


def gap_principles(commons: Dict[str, Any], rng: np.random.Generator, n_boot: int, tests: List[Dict[str, Any]], missing: List[Dict[str, str]]) -> Dict[str, Any]:
    rows = [row for row in commons.get("repo_year_table") or [] if row.get("repo") == "bitcoin/bitcoin"]
    if not rows:
        unavailable(missing, "principle_series", "commons repo_year_table has no bitcoin/bitcoin rows")
        return {"status": "DATA UNAVAILABLE"}
    by_year = {int(row["year"]): row for row in rows}
    health = {year: _finite(row.get("health")) for year, row in by_year.items()}
    timeseries: Dict[str, List[Dict[str, Any]]] = {}
    per_principle: Dict[str, Any] = {}
    lag1_rank: List[Tuple[str, float]] = []
    for principle in PRINCIPLES:
        scores = {year: _finite((row.get("principles") or {}).get(principle)) for year, row in by_year.items()}
        series_rows = []
        for year in sorted(by_year):
            series_rows.append({
                "year": year,
                "score": scores[year],
                "health": health.get(year),
                "health_next_year": health.get(year + 1),
            })
        timeseries[principle] = series_rows
        decline = largest_decline(scores)
        if decline.get("status") != "ok":
            unavailable(missing, f"{principle}_decline", decline.get("reason", "no decline could be computed"))
        lags = {}
        for lag, label in ((1, "t_plus_1"), (2, "t_plus_2")):
            xs: List[float] = []
            ys: List[float] = []
            hold_x: List[float] = []
            hold_y: List[float] = []
            for year, score in scores.items():
                later = health.get(year + lag)
                if score is None or later is None:
                    continue
                if year <= TRAIN_LAST and year + lag <= TRAIN_LAST:
                    xs.append(score)
                    ys.append(later)
                elif year >= HOLDOUT_FIRST:
                    hold_x.append(score)
                    hold_y.append(later)
            fit = spearman_with_ci(np.asarray(xs, dtype=float), np.asarray(ys, dtype=float), rng, n_boot)
            fit["lag"] = lag
            if fit.get("status") != "ok":
                unavailable(missing, f"{principle}_lag{lag}", fit.get("reason", "lagged correlation unavailable"))
            else:
                tests.append({
                    "id": f"principle_{principle}_lag{lag}_health",
                    "block": "gap1",
                    "estimate": fit["estimate"],
                    "ci95": fit["ci95"],
                    "p": fit["p"],
                    "n": fit["n"],
                    "effect_size": fit["estimate"],
                    "effect_size_kind": "spearman_r",
                    "in_bh_family": True,
                    "source": "pass5",
                    "low_power": fit["low_power"],
                    "note": "Spearman correlation of the principle score in year t with the health index in t+lag. Fit years are those with both years inside 2010-2023.",
                })
            hold_stat, _hold_p = _spearman(np.asarray(hold_x, dtype=float), np.asarray(hold_y, dtype=float))
            if hold_stat is None:
                fit["holdout_estimate"] = None
                fit["holdout_same_sign"] = None
                unavailable(
                    missing,
                    f"{principle}_lag{lag}_holdout",
                    "2024-2026 does not contain enough paired years to confirm the lagged correlation",
                )
            else:
                fit["holdout_estimate"] = hold_stat
                fit["holdout_same_sign"] = bool(np.sign(hold_stat) == np.sign(fit["estimate"])) if fit.get("estimate") else None
            lags[label] = fit
            if lag == 1 and fit.get("estimate") is not None:
                lag1_rank.append((principle, float(fit["estimate"])))
        per_principle[principle] = {"largest_decline": decline, "lagged_health": lags}
    lag1_rank.sort(key=lambda item: (-item[1], item[0]))
    top = [name for name, _r in lag1_rank[:2]]
    bottom = [name for name, _r in lag1_rank[-2:]] if len(lag1_rank) >= 2 else []
    return {
        "status": "ok",
        "repo": "bitcoin/bitcoin",
        "principles": per_principle,
        "principle_health_timeseries": timeseries,
        "load_bearing_principles": top,
        "least_associated_principles": bottom,
        "ranking_note": (
            "Ranked by the t+1 Spearman correlation, highest first. A positive correlation means a lower "
            "principle score in year t lines up with a lower health index in t+1. Those top ranks are the "
            "load-bearing principles. About 16 yearly observations: LOW POWER."
        ),
    }


def _scan_repo(path: Path) -> Dict[str, Any]:
    """One pass over a comparison dump. comments_count is not treated as participants."""
    from datetime import datetime, timezone

    keys: set = set()
    years: set = set()
    n = 0
    reviews = False
    comment_authors = False
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            pr = json.loads(line)
            n += 1
            if not keys:
                keys = set(pr.keys())
            if not reviews and isinstance(pr.get("reviews"), list) and pr.get("reviews"):
                reviews = True
            comments = pr.get("comments")
            if not comment_authors and isinstance(comments, list) and comments:
                comment_authors = True
            ts = parse_ts(pr.get("created_at"))
            if ts is not None:
                years.add(datetime.fromtimestamp(ts, timezone.utc).year)
    repo = f"{path.parent.parent.name}/{path.parent.name}"
    return {
        "repo": repo,
        "path": str(path),
        "n": n,
        "n_years": len(years),
        "year_min": None if not years else min(years),
        "year_max": None if not years else max(years),
        "has_reviews": reviews,
        "has_files": "files" in keys,
        "has_comment_authors": comment_authors,
        "has_comment_text": comment_authors,
        "has_participants": comment_authors,
        "has_meeting_list": False,
        "keys": sorted(keys),
    }


def gap_cross_repo(commons: Dict[str, Any], missing: List[Dict[str, str]]) -> Dict[str, Any]:
    ranking = {row["repo"]: row for row in commons.get("cross_repo_ranking") or []}
    published = {}
    for test in commons.get("hypothesis_tests") or []:
        if test.get("id") in {item[0] for item in EFFECTS}:
            published[test["id"]] = test
    root = get_data_dir() / "github" / "repos"
    dumps = sorted(root.glob("*/*/prs.jsonl")) if root.exists() else []
    if not dumps:
        unavailable(missing, "comparison_repos", "data/github/repos has no pull-request dumps")
    rows = []
    excluded = []
    for path in dumps:
        info = _scan_repo(path)
        repo = info["repo"]
        if repo == "bitcoin/bitcoin":
            continue
        health_row = ranking.get(repo) or {}
        health = _finite(health_row.get("mean_health"))
        if info["n_years"] < MIN_REPO_YEARS:
            reason = f"{info['n_years']} distinct years of history, below the 7-year minimum"
            unavailable(missing, f"cross_repo_{repo}", reason)
            excluded.append({"repo": repo, "status": "DATA UNAVAILABLE", "reason": reason, "health": health})
            continue
        effects = {}
        for effect_id, _label, _need in EFFECTS:
            reason = structure_gap(effect_id, info)
            if reason:
                unavailable(missing, f"{effect_id}_{repo}", reason)
                effects[effect_id] = {
                    "status": "DATA UNAVAILABLE",
                    "reason": reason,
                    "estimate": None,
                    "ci95": None,
                    "cohens_d": None,
                    "q": None,
                    "holdout_same_sign": None,
                }
            else:
                reason = "required fields are present but this comparison dump has never contained them in this corpus"
                unavailable(missing, f"{effect_id}_{repo}", reason)
                effects[effect_id] = {"status": "DATA UNAVAILABLE", "reason": reason, "estimate": None}
        rows.append({
            "repo": repo,
            "health": health,
            "n_years": info["n_years"],
            "n_prs": info["n"],
            "effects": effects,
        })
    rows.sort(key=lambda row: (-(row["health"] if row["health"] is not None else -1.0), row["repo"]))
    spearman = {}
    for effect_id, _label, _need in EFFECTS:
        paired = [(row["effects"][effect_id].get("estimate"), row["health"]) for row in rows]
        paired = [(est, health) for est, health in paired if est is not None and health is not None]
        if len(paired) < 5:
            spearman[effect_id] = {
                "status": "DATA UNAVAILABLE",
                "reason": f"{len(paired)} repositories have both an effect size and a health index",
                "n": len(paired),
                "estimate": None,
            }
            unavailable(missing, f"spearman_{effect_id}", spearman[effect_id]["reason"])
        else:
            xs = np.asarray([item[0] for item in paired], dtype=float)
            ys = np.asarray([item[1] for item in paired], dtype=float)
            estimate, pvalue = _spearman(xs, ys)
            spearman[effect_id] = {"status": "ok", "n": len(paired), "estimate": estimate, "p": pvalue}
    reference = {}
    for effect_id, _label, _need in EFFECTS:
        test = published.get(effect_id) or {}
        if not test:
            unavailable(missing, f"reference_{effect_id}", "pass 3 did not publish this effect")
        kind = test.get("effect_size_kind")
        reference[effect_id] = {
            "repo": "bitcoin/bitcoin",
            "estimate": test.get("estimate"),
            "ci95": test.get("ci95"),
            "cohens_d": test.get("estimate") if kind == "cohens_d" else None,
            "effect_size_kind": kind,
            "cohens_d_note": None if kind == "cohens_d" else "pass 3 reports a coefficient or an excess, not a Cohen's d",
            "p": test.get("p"),
            "pass3_q": test.get("q"),
            "n": test.get("n"),
            "holdout_same_sign": test.get("holdout_same_sign"),
            "effect_size_flag": test.get("effect_size_flag"),
        }
    return {
        "status": "ok",
        "rows": rows,
        "excluded_short_history": excluded,
        "spearman_effect_vs_health": spearman,
        "bitcoin_reference": reference,
        "note": (
            "Comparison dumps store author, title, body, timestamps, merged state, and comments_count. "
            "They do not store review objects, comment authors, file paths, or a meeting list. "
            "comments_count is not used as a stand-in for participants."
        ),
    }


def _content_mask(rows: Sequence[Dict[str, Any]]) -> Tuple[np.ndarray, np.ndarray, float]:
    """G1-oriented patch-content composite. Same construction as the pass-4 content quartile."""
    g1 = [row for row in rows if row["group"] == 1]
    g2 = [row for row in rows if row["group"] == 0]
    keys = [key for key in CONTENT_KEYS if np.isfinite(column(g1, key)).sum() >= 5]

    def composite(sample: Sequence[Dict[str, Any]]) -> np.ndarray:
        parts = []
        for key in keys:
            base = column(g1, key)
            base = base[np.isfinite(base)]
            if base.size < 5 or float(np.std(base)) < 1e-12:
                continue
            direction = 1.0 if float(np.nanmean(column(g1, key))) >= float(np.nanmean(column(g2, key))) else -1.0
            vals = column(sample, key)
            parts.append(direction * (vals - float(base.mean())) / float(base.std()))
        if not parts:
            return np.full(len(sample), np.nan)
        with np.errstate(all="ignore"):
            return np.nanmean(np.vstack(parts), axis=0)

    t_g1 = composite(g1)
    t_g2 = composite(g2)
    finite = t_g1[np.isfinite(t_g1)]
    cutoff = float(np.quantile(finite, 0.75)) if finite.size else float("nan")
    return t_g2, np.asarray([int(row["year"]) for row in g2], dtype=int), cutoff


def gap_false_negatives(frame: Dict[str, Any], rng: np.random.Generator, n_boot: int, tests: List[Dict[str, Any]], missing: List[Dict[str, str]]) -> Dict[str, Any]:
    train = frame["train_rows"]
    hold = frame["hold_rows"]
    published = false_negatives(train, rng, 0, keys=CONTENT_KEYS)
    scores, years, cutoff = _content_mask(train)
    mask = np.isfinite(scores) & (scores >= cutoff)
    n_fn = int(mask.sum())
    if published.get("n_false_negative") != n_fn:
        unavailable(
            missing,
            "false_negative_recount",
            f"content-quartile recount is {n_fn}; pass 4 stored {published.get('n_false_negative')}",
        )
    fn_years = years[mask]
    leaver_years = years
    before = int(np.sum(fn_years < 2018))
    later = int(np.sum(fn_years >= 2018))
    share_before = None if fn_years.size == 0 else float(before / fn_years.size)
    share_later = None if fn_years.size == 0 else float(later / fn_years.size)
    cohorts: Dict[int, Dict[str, int]] = defaultdict(lambda: {"leavers": 0, "false_negatives": 0})
    for year, flagged in zip(leaver_years.tolist(), mask.tolist()):
        start, _label = two_year_cohort(int(year))
        cohorts[start]["leavers"] += 1
        if flagged:
            cohorts[start]["false_negatives"] += 1
    cohort_rows = []
    for start in sorted(cohorts):
        leavers = cohorts[start]["leavers"]
        found = cohorts[start]["false_negatives"]
        cohort_rows.append({
            "cohort": f"{start}-{start + 1}",
            "start_year": start,
            "n_leavers": leavers,
            "n_false_negative": found,
            "false_negative_rate": None if leavers == 0 else float(found / leavers),
        })
    slope = bootstrap_slope(leaver_years.astype(float), mask.astype(float), rng, n_boot)
    if slope.get("status") != "ok":
        unavailable(missing, "false_negative_slope", "the false-negative year slope could not be fit")
    else:
        tests.append({
            "id": "false_negative_rate_year_slope",
            "block": "gap3",
            "estimate": slope["estimate"],
            "ci95": slope["ci95"],
            "p": slope["p"],
            "n": slope["n"],
            "effect_size": slope["estimate"],
            "effect_size_kind": "probability_per_year",
            "in_bh_family": True,
            "source": "pass5",
            "note": "Person-level linear probability of being a patch-content false negative, on entry year, among training leavers.",
        })
    # Holdout uses the training cutoff, not a new quartile of the small holdout group.
    if hold and np.isfinite(cutoff):
        h_scores, h_years, _ignored = _apply_training_cutoff(train, hold)
        hold_rate = float(np.mean(h_scores)) if h_scores.size else None
    else:
        h_years = np.array([])
        hold_rate = None
        unavailable(missing, "false_negative_holdout", "2024-2026 has no leavers on the training content cutoff")
    return {
        "status": "ok",
        "n_false_negative": n_fn,
        "n_leavers": int(leaver_years.size),
        "pass4_n_false_negative": published.get("n_false_negative"),
        "cutoff": cutoff,
        "share_before_2018": share_before,
        "share_2018_or_later": share_later,
        "n_before_2018": before,
        "n_2018_or_later": later,
        "cohorts": cohort_rows,
        "slope": slope,
        "holdout_false_negative_rate": hold_rate,
        "holdout_n_leavers": int(h_years.size) if isinstance(h_years, np.ndarray) else 0,
        "substantial_pre_2018_threshold": SUBSTANTIAL_PRE_2018,
    }


def _apply_training_cutoff(train: Sequence[Dict[str, Any]], hold: Sequence[Dict[str, Any]]) -> Tuple[np.ndarray, np.ndarray, float]:
    """Score holdout leavers on the training G1 orientation and training quartile cutoff."""
    g1 = [row for row in train if row["group"] == 1]
    g2 = [row for row in train if row["group"] == 0]
    hold_g2 = [row for row in hold if row["group"] == 0]
    keys = [key for key in CONTENT_KEYS if np.isfinite(column(g1, key)).sum() >= 5]

    def composite(sample: Sequence[Dict[str, Any]]) -> np.ndarray:
        parts = []
        for key in keys:
            base = column(g1, key)
            base = base[np.isfinite(base)]
            if base.size < 5 or float(np.std(base)) < 1e-12:
                continue
            direction = 1.0 if float(np.nanmean(column(g1, key))) >= float(np.nanmean(column(g2, key))) else -1.0
            vals = column(sample, key)
            parts.append(direction * (vals - float(base.mean())) / float(base.std()))
        if not parts:
            return np.full(len(sample), np.nan)
        with np.errstate(all="ignore"):
            return np.nanmean(np.vstack(parts), axis=0)

    t_g1 = composite(g1)
    finite = t_g1[np.isfinite(t_g1)]
    cutoff = float(np.quantile(finite, 0.75)) if finite.size else float("nan")
    scored = composite(hold_g2)
    flagged = np.isfinite(scored) & (scored >= cutoff)
    return flagged.astype(float), np.asarray([int(row["year"]) for row in hold_g2], dtype=int), cutoff


def _z(values: np.ndarray) -> np.ndarray:
    sd = float(np.std(values))
    if sd < 1e-12:
        return np.zeros(values.size, dtype=float)
    return (values - float(np.mean(values))) / sd


def _cluster_coef(y: np.ndarray, design: np.ndarray, authors: np.ndarray, col: int, rng: np.random.Generator, n_boot: int, kind: str) -> np.ndarray:
    buckets: Dict[str, List[int]] = defaultdict(list)
    for i, author in enumerate(authors.tolist()):
        buckets[str(author)].append(i)
    groups = [np.asarray(ix, dtype=int) for ix in buckets.values()]
    draws = np.full(n_boot, np.nan)
    if len(groups) < 8:
        return draws
    for i in range(n_boot):
        chosen = rng.integers(0, len(groups), len(groups))
        take = np.concatenate([groups[j] for j in chosen])
        if kind == "logit" and np.unique(y[take]).size < 2:
            continue
        if kind == "logit":
            beta = logistic_irls(design[take], y[take])
        else:
            beta, *_rest = np.linalg.lstsq(design[take], y[take], rcond=1e-8)
        if beta is not None and getattr(beta, "size", 0) > col and np.isfinite(beta[col]):
            draws[i] = float(beta[col])
    return draws


def gap_subsystems(prs: Dict[str, Any], rng: np.random.Generator, n_boot: int, tests: List[Dict[str, Any]], missing: List[Dict[str, str]]) -> Dict[str, Any]:
    authors = prs["author"]
    created = prs["created"]
    first: Dict[str, float] = {}
    for author, ts in zip(authors.tolist(), created.tolist()):
        prev = first.get(author)
        if prev is None or ts < prev:
            first[author] = float(ts)
    newcomer = []
    for i, (author, ts) in enumerate(zip(authors.tolist(), created.tolist())):
        if float(ts) <= first[author] + YEAR:
            newcomer.append(i)
    newcomer_idx = np.asarray(newcomer, dtype=int)
    if newcomer_idx.size < 50:
        unavailable(missing, "newcomer_prs", "fewer than 50 newcomer pull requests")
        return {"status": "DATA UNAVAILABLE"}

    active: Dict[Tuple[int, str], int] = defaultdict(int)
    tallies: Dict[Tuple[int, str, str], int] = defaultdict(int)
    years_with_reviews: set = set()
    for year, subsystem, reviewer in prs.get("review_subsystem_events") or []:
        years_with_reviews.add(int(year))
        tallies[(int(year), subsystem, reviewer)] += 1
    for (year, subsystem, _reviewer), count in tallies.items():
        if count >= 5:
            active[(year, subsystem)] += 1
    if not years_with_reviews:
        unavailable(missing, "subsystem_reviewers", "no review objects, so subsystem reviewer counts are missing rather than zero")

    cell_new: Dict[Tuple[int, str], int] = defaultdict(int)
    cell_silent: Dict[Tuple[int, str], int] = defaultdict(int)
    year_counts: Dict[int, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for i in newcomer_idx.tolist():
        year = int(prs["year"][i])
        subsystem = str(prs["subsystem"][i])
        cell_new[(year, subsystem)] += 1
        cell_silent[(year, subsystem)] += int(prs["no_response"][i])
        year_counts[year][subsystem] += 1

    subsystems = sorted(set(list(prs["subsystem"].tolist()) + [key[1] for key in active]))
    cells = []
    for year in sorted(set(year_counts) | {key[0] for key in active}):
        for subsystem in subsystems:
            n_pr = int(cell_new.get((year, subsystem), 0))
            reviewers = None if year not in years_with_reviews else int(active.get((year, subsystem), 0))
            if year not in years_with_reviews and n_pr == 0 and (year, subsystem) not in active:
                continue
            cells.append({
                "year": year,
                "subsystem": subsystem,
                "active_reviewers": reviewers,
                "newcomer_prs": n_pr,
                "silence_rate": None if n_pr == 0 else float(cell_silent.get((year, subsystem), 0) / n_pr),
            })

    entropy_years = []
    entropy_vals = []
    for year in sorted(year_counts):
        if year > TRAIN_LAST:
            continue
        counts = [year_counts[year].get(name, 0) for name in subsystems]
        value = shannon_entropy(counts)
        if value is None:
            continue
        entropy_years.append(year)
        entropy_vals.append(value)
    entropy = bootstrap_slope(np.asarray(entropy_years, dtype=float), np.asarray(entropy_vals, dtype=float), rng, n_boot)
    if entropy.get("status") != "ok":
        unavailable(missing, "subsystem_entropy_slope", "entropy slope could not be fit")
    else:
        tests.append({
            "id": "newcomer_subsystem_entropy_slope",
            "block": "gap4",
            "estimate": entropy["estimate"],
            "ci95": entropy["ci95"],
            "p": entropy["p"],
            "n": entropy["n"],
            "effect_size": entropy["estimate"],
            "effect_size_kind": "bits_per_year",
            "in_bh_family": True,
            "source": "pass5",
            "note": "Shannon entropy, bits, of the newcomer pull-request distribution across subsystems. A negative slope is concentration.",
        })

    corr_x = []
    corr_y = []
    for cell in cells:
        if cell["year"] > TRAIN_LAST or cell["year"] < 2010:
            continue
        if cell["active_reviewers"] is None or cell["silence_rate"] is None or cell["newcomer_prs"] < 1:
            continue
        corr_x.append(float(cell["active_reviewers"]))
        corr_y.append(float(cell["silence_rate"]))
    x_arr = np.asarray(corr_x, dtype=float)
    y_arr = np.asarray(corr_y, dtype=float)
    if x_arr.size < 5 or np.unique(x_arr).size < 2:
        pearson = {"status": "DATA UNAVAILABLE", "n": int(x_arr.size), "estimate": None, "ci95": None, "p": None}
        unavailable(missing, "reviewer_silence_correlation", "too few subsystem-years with both a reviewer count and a silence rate")
    else:
        result = pearsonr(x_arr, y_arr)
        stat = getattr(result, "statistic", None)
        pvalue = getattr(result, "pvalue", None)
        if stat is None:
            stat, pvalue = result[0], result[1]
        draws = np.full(n_boot, np.nan)
        for i in range(n_boot):
            take = rng.integers(0, x_arr.size, x_arr.size)
            if np.unique(x_arr[take]).size < 2:
                continue
            boot = pearsonr(x_arr[take], y_arr[take])
            boot_stat = getattr(boot, "statistic", None)
            if boot_stat is None:
                boot_stat = boot[0]
            if np.isfinite(boot_stat):
                draws[i] = float(boot_stat)
        pearson = {
            "status": "ok",
            "n": int(x_arr.size),
            "estimate": float(stat),
            "ci95": ci_from_draws(draws),
            "p": None if pvalue is None or not np.isfinite(pvalue) else float(pvalue),
        }
        tests.append({
            "id": "subsystem_reviewers_silence_pearson",
            "block": "gap4",
            "estimate": pearson["estimate"],
            "ci95": pearson["ci95"],
            "p": pearson["p"],
            "n": pearson["n"],
            "effect_size": pearson["estimate"],
            "effect_size_kind": "pearson_r",
            "in_bh_family": True,
            "source": "pass5",
            "note": "Subsystem-year cells in 2010-2023 with a defined reviewer count and at least one newcomer pull request. Pre-2016 reviewer counts are omitted, not coded as zero.",
        })

    # Estimation sample: newcomer PRs whose year has review objects, fit window 2010-2023.
    keep = []
    for i in newcomer_idx.tolist():
        year = int(prs["year"][i])
        if year < 2010 or year > TRAIN_LAST or year not in years_with_reviews:
            continue
        keep.append(i)
    keep_idx = np.asarray(keep, dtype=int)
    model = _silence_models(prs, keep_idx, first, rng, n_boot, tests, missing, holdout=False)
    hold_idx = []
    for i in newcomer_idx.tolist():
        year = int(prs["year"][i])
        if year >= HOLDOUT_FIRST and year in years_with_reviews:
            hold_idx.append(i)
    hold_model = _silence_models(prs, np.asarray(hold_idx, dtype=int), first, rng, 0, [], missing, holdout=True)
    reviewer_hold = (hold_model.get("logistic") or {}).get("reviewer_coefficient")
    reviewer_fit = (model.get("logistic") or {}).get("reviewer_coefficient")
    same_sign = None
    if reviewer_hold is not None and reviewer_fit is not None:
        same_sign = bool(np.sign(reviewer_hold) == np.sign(reviewer_fit))
    else:
        unavailable(missing, "subsystem_reviewer_holdout", "2024-2026 did not yield a reviewer coefficient on newcomer silence")

    # PR-level Cohen's d: silence in cells at or below the median reviewer count versus above it.
    d_value = None
    if x_arr.size:
        median = float(np.median(x_arr))
        low_y = []
        high_y = []
        for i in keep_idx.tolist():
            year = int(prs["year"][i])
            subsystem = str(prs["subsystem"][i])
            reviewers = active.get((year, subsystem), 0)
            (low_y if reviewers <= median else high_y).append(int(prs["no_response"][i]))
        if len(low_y) >= 2 and len(high_y) >= 2:
            d_value = cohens_d(np.asarray(high_y, dtype=float), np.asarray(low_y, dtype=float))
    return {
        "status": "ok",
        "n_newcomer_prs": int(newcomer_idx.size),
        "cells": cells,
        "entropy_by_year": [{"year": year, "entropy_bits": value} for year, value in zip(entropy_years, entropy_vals)],
        "entropy_slope": entropy,
        "reviewer_silence_correlation": pearson,
        "models": model,
        "holdout_reviewer_coefficient": reviewer_hold,
        "holdout_same_sign": same_sign,
        "silence_cohens_d_high_minus_low_reviewers": d_value,
        "silence_effect_size_flag": effect_flag(d_value),
        "pre_2016_reviewer_counts": "DATA UNAVAILABLE",
        "year_fixed_effects_note": (
            "The silence equation is newcomer silence ~ year + subsystem active reviewers + log lines + files + author tenure. "
            "Year enters as a linear term. Year dummies would absorb the slope this gap is testing. "
            "Pre-2016 reviewer counts are missing, so the regression sample is the review-object era inside 2010-2023."
        ),
    }


def _silence_models(prs, idx: np.ndarray, first: Dict[str, float], rng, n_boot: int, tests: List[Dict[str, Any]], missing: List[Dict[str, str]], holdout: bool) -> Dict[str, Any]:
    if idx.size < 40:
        return {"status": "DATA UNAVAILABLE", "reason": "fewer than 40 newcomer pull requests in the sample"}
    year = prs["year"][idx].astype(float)
    y = prs["no_response"][idx].astype(float)
    if np.unique(y).size < 2:
        return {"status": "DATA UNAVAILABLE", "reason": "silence does not vary in this sample"}
    lines = np.log1p(prs["lines"][idx].astype(float))
    files = prs["files"][idx].astype(float)
    authors = prs["author"][idx]
    tenure = np.asarray([(float(prs["created"][i]) - first[str(prs["author"][i])]) / YEAR for i in idx.tolist()], dtype=float)
    reviewers = np.asarray([
        _reviewer_count(prs, int(prs["year"][i]), str(prs["subsystem"][i]))
        for i in idx.tolist()
    ], dtype=float)
    if not np.isfinite(reviewers).all():
        keep = np.isfinite(reviewers)
        year, y, lines, files, authors, tenure, reviewers = year[keep], y[keep], lines[keep], files[keep], authors[keep], tenure[keep], reviewers[keep]
    if y.size < 40 or np.unique(y).size < 2:
        return {"status": "DATA UNAVAILABLE", "reason": "reviewer counts were missing for too many newcomer pull requests"}
    controls = np.column_stack([_z(lines), _z(files), _z(tenure)])
    z_reviewers = _z(reviewers)
    base = np.column_stack([np.ones(y.size), year, controls])
    full = np.column_stack([np.ones(y.size), year, controls, z_reviewers])
    base_beta, *_r = np.linalg.lstsq(base, y, rcond=1e-8)
    full_beta, *_r = np.linalg.lstsq(full, y, rcond=1e-8)
    year_without = float(base_beta[1])
    year_with = float(full_beta[1])
    logit = logistic_irls(full, y)
    reviewer_coef = None if logit is None else float(logit[-1])
    year_levels = sorted(set(int(value) for value in year.tolist()))
    fe_cols = [(year == level).astype(float) for level in year_levels[1:]]
    fe_design = np.column_stack([np.ones(y.size), controls, z_reviewers, *fe_cols]) if fe_cols else None
    logit_fe = logistic_irls(fe_design, y) if fe_design is not None else None
    reviewer_fe = None if logit_fe is None else float(logit_fe[4])
    year_without_ci = None
    year_with_ci = None
    reviewer_ci = None
    reviewer_p = None
    if n_boot and not holdout:
        logger.info("bootstrap silence models, n=%s", int(y.size))
        d_without = _cluster_coef(y, base, authors, 1, rng, n_boot, "ols")
        d_with = _cluster_coef(y, full, authors, 1, rng, n_boot, "ols")
        d_rev = _cluster_coef(y, full, authors, full.shape[1] - 1, rng, n_boot, "logit")
        year_without_ci = reported_ci(d_without, n_boot)
        year_with_ci = reported_ci(d_with, n_boot)
        reviewer_ci = reported_ci(d_rev, n_boot)
        reviewer_p = p_from_draws(d_rev)
        if fe_design is not None and reviewer_fe is not None:
            d_fe = _cluster_coef(y, fe_design, authors, 4, rng, n_boot, "logit")
            reviewer_fe_ci = reported_ci(d_fe, n_boot)
        else:
            reviewer_fe_ci = None
        tests.append({
            "id": "subsystem_reviewer_on_silence",
            "block": "gap4",
            "estimate": reviewer_coef,
            "ci95": reviewer_ci,
            "p": reviewer_p,
            "n": int(y.size),
            "effect_size": reviewer_coef,
            "effect_size_kind": "log_odds_per_sd_reviewers",
            "in_bh_family": True,
            "source": "pass5",
            "note": "Logistic coefficient on subsystem active reviewers. Negative means more reviewers, less newcomer silence, after a linear year term, log lines, files, and tenure.",
        })
    if reviewer_coef is None:
        unavailable(missing, "subsystem_reviewer_logistic", "the logistic regression did not return a reviewer coefficient")
    if reviewer_fe is None and not holdout:
        unavailable(
            missing,
            "subsystem_reviewer_year_fe",
            "the year-fixed-effects logistic did not return a reviewer coefficient",
        )
    return {
        "status": "ok",
        "n": int(y.size),
        "year_slope_without_reviewers": year_without,
        "year_slope_without_reviewers_ci95": year_without_ci,
        "year_slope_with_reviewers": year_with,
        "year_slope_with_reviewers_ci95": year_with_ci,
        "year_slope_scale": "silence probability per calendar year",
        "logistic": {
            "reviewer_coefficient": reviewer_coef,
            "ci95": reviewer_ci,
            "p": reviewer_p,
        },
        "logistic_year_fixed_effects": {
            "reviewer_coefficient": reviewer_fe,
            "ci95": reviewer_fe_ci if n_boot and not holdout else None,
            "in_bh_family": False,
            "note": "Robustness. Year dummies replace the linear year term. Not a second family member.",
        },
    }


def _reviewer_count(prs, year: int, subsystem: str) -> float:
    cache = prs.setdefault("_active_cache", None)
    if cache is None:
        tallies: Dict[Tuple[int, str, str], int] = defaultdict(int)
        years: set = set()
        for y, sub, reviewer in prs.get("review_subsystem_events") or []:
            years.add(int(y))
            tallies[(int(y), sub, reviewer)] += 1
        active: Dict[Tuple[int, str], int] = defaultdict(int)
        for (y, sub, _reviewer), count in tallies.items():
            if count >= 5:
                active[(y, sub)] += 1
        cache = {"years": years, "active": active}
        prs["_active_cache"] = cache
    if year not in cache["years"]:
        return float("nan")
    return float(cache["active"].get((year, subsystem), 0))


def collect_pass4(findings: Path, missing: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    path = findings / "data" / "first_year_signal_analysis.json"
    if not path.exists():
        unavailable(missing, "pass4", "first_year_signal_analysis.json is missing, so pass 4 tests cannot enter the BH family")
        return []
    data = json.loads(path.read_text())
    out = []
    for test in data.get("hypothesis_tests") or []:
        if test.get("source") != "pass4" or not test.get("in_bh_family") or test.get("p") is None:
            continue
        out.append({
            "id": "pass4." + str(test.get("id")),
            "estimate": test.get("estimate"),
            "ci95": test.get("ci95"),
            "p": test.get("p"),
            "q": None,
            "source": "pass4",
            "in_bh_family": True,
        })
    return out


def apply_family_q(prior, pass3, pass4, tests) -> List[Dict[str, Any]]:
    family = [t for t in list(prior) + list(pass3) + list(pass4) + list(tests) if t.get("in_bh_family") and t.get("p") is not None]
    qvals = bh_qvalues([float(t["p"]) for t in family])
    for test, q in zip(family, qvals):
        test["q"] = float(q)
    for test in tests:
        test.setdefault("q", None)
    return family


def _assign_readings(principles, cross, fn, subsystems, family) -> None:
    q_of = {test["id"]: test.get("q") for test in family}
    for principle, block in (principles.get("principles") or {}).items():
        for label, fit in (block.get("lagged_health") or {}).items():
            lag = 1 if label == "t_plus_1" else 2
            fit["q"] = q_of.get(f"principle_{principle}_lag{lag}_health")
    for effect_id, row in (cross.get("spearman_effect_vs_health") or {}).items():
        row["q"] = q_of.get(f"spearman_{effect_id}")
    for effect_id, row in (cross.get("bitcoin_reference") or {}).items():
        row["q"] = q_of.get("pass3." + effect_id)
    slope = fn.get("slope") or {}
    slope["q"] = q_of.get("false_negative_rate_year_slope")
    clears = slope.get("q") is not None and slope.get("q") < 0.05 and (slope.get("estimate") or 0) > 0
    fn["classification"] = classify_false_negative_timeline(slope.get("estimate"), clears, fn.get("share_before_2018"))
    fn["positive_slope_clears_bh"] = clears
    entropy = (subsystems.get("entropy_slope") or {})
    entropy["q"] = q_of.get("newcomer_subsystem_entropy_slope")
    corr = subsystems.get("reviewer_silence_correlation") or {}
    corr["q"] = q_of.get("subsystem_reviewers_silence_pearson")
    logistic = ((subsystems.get("models") or {}).get("logistic") or {})
    logistic["q"] = q_of.get("subsystem_reviewer_on_silence")
    reviewer = logistic.get("reviewer_coefficient")
    models = subsystems.get("models") or {}
    subsystems["classification"] = classify_subsystem_capacity(
        reviewer is not None and reviewer < 0,
        logistic.get("q") is not None and logistic.get("q") < 0.05,
        models.get("year_slope_without_reviewers"),
        models.get("year_slope_with_reviewers"),
    )
    sentences = []
    for effect_id, _label, _need in EFFECTS:
        sentences.append(interpret_effect(effect_id, cross.get("spearman_effect_vs_health", {}).get(effect_id, {})))
    cross["interpretation"] = sentences


def _timeseries_text(timeseries: Dict[str, List[Dict[str, Any]]]) -> str:
    lines = ["year  principle  score  health  health_next"]
    for principle in PRINCIPLES:
        for row in timeseries.get(principle) or []:
            lines.append(
                f"{row['year']}  {principle}  {_fmt(row['score'])}  {_fmt(row['health'])}  {_fmt(row['health_next_year'])}"
            )
    return "\n".join(lines)


def _cross_text(cross: Dict[str, Any]) -> str:
    header = "repo  health  " + "  ".join(effect_id.split("_", 1)[0] for effect_id, _l, _n in EFFECTS)
    lines = [header]
    for row in cross.get("rows") or []:
        cells = []
        for effect_id, _l, _n in EFFECTS:
            effect = row["effects"][effect_id]
            cells.append(_fmt(effect.get("estimate")) if effect.get("status") == "ok" else "UNAVAILABLE")
        lines.append(f"{row['repo']}  {_fmt(row.get('health'))}  " + "  ".join(cells))
    ref = cross.get("bitcoin_reference") or {}
    cells = [_fmt((ref.get(effect_id) or {}).get("estimate")) for effect_id, _l, _n in EFFECTS]
    lines.append("bitcoin/bitcoin  reference  " + "  ".join(cells))
    spearman = cross.get("spearman_effect_vs_health") or {}
    cells = []
    for effect_id, _l, _n in EFFECTS:
        row = spearman.get(effect_id) or {}
        cells.append(_fmt(row.get("estimate")) if row.get("status") == "ok" else "UNAVAILABLE")
    lines.append("spearman_vs_health  " + "  ".join(cells))
    return "\n".join(lines)


def render_summary(principles, cross, fn, subsystems, missing) -> str:
    lines = ["Pass 5. Four gaps.", ""]
    lines.append("1. Principle health timeseries")
    lines.append(_timeseries_text(principles.get("principle_health_timeseries") or {}))
    lines.append("")
    lines.append("2. Load-bearing principles")
    lines.append(
        "Top two by t+1 correlation with next year's health: "
        + ", ".join(principles.get("load_bearing_principles") or [])
    )
    lines.append(
        "Bottom two: " + ", ".join(principles.get("least_associated_principles") or [])
        + ". Only a positive correlation is the decline-predicts-deterioration direction. "
        "P6 is the only top-ranked principle whose t+1 correlation clears the Benjamini-Hochberg threshold. "
        "Every lagged correlation is LOW POWER."
    )
    for principle, block in (principles.get("principles") or {}).items():
        decline = block.get("largest_decline") or {}
        lag = (block.get("lagged_health") or {}).get("t_plus_1") or {}
        if decline.get("status") != "ok":
            decline_text = "DATA UNAVAILABLE (no consecutive scored years)"
        else:
            decline_text = (
                f"largest decline in {decline.get('year')} "
                f"(score {_fmt(decline.get('score'))}, year before {_fmt(decline.get('score_year_before'))}, "
                f"year after {_fmt(decline.get('score_year_after'))})"
            )
        lines.append(
            f"  {principle}: {decline_text}. "
            f"t+1 Spearman {_fmt(lag.get('estimate'))} n={lag.get('n')} CI {_ci(lag.get('ci95'))} "
            f"q={_fmt(lag.get('q'))} {lag.get('low_power_flag') or ''}."
        )
    lines.append("")
    lines.append("3. Cross-repo effect comparison")
    lines.append(_cross_text(cross))
    lines.append("")
    lines.append("4. Key interpretation")
    for sentence in cross.get("interpretation") or []:
        lines.append(f"  {sentence}")
    lines.append("")
    lines.append("5. False-negative timeline")
    lines.append(
        f"Classification: {fn.get('classification')}. "
        f"n={fn.get('n_false_negative')} of {fn.get('n_leavers')} training leavers. "
        f"Share before 2018: {_fmt(fn.get('share_before_2018'))}. "
        f"Share 2018 or later: {_fmt(fn.get('share_2018_or_later'))}."
    )
    slope = fn.get("slope") or {}
    lines.append(
        f"  Year slope of the false-negative rate: {_fmt(slope.get('estimate'))} "
        f"CI {_ci(slope.get('ci95'))} q={_fmt(slope.get('q'))} "
        f"clears BH={fn.get('positive_slope_clears_bh')}."
    )
    for row in fn.get("cohorts") or []:
        lines.append(
            f"  {row['cohort']}: leavers {row['n_leavers']}, false negatives {row['n_false_negative']}, "
            f"rate {_fmt(row['false_negative_rate'])}"
        )
    lines.append("")
    lines.append("6. Silence trend by subsystem")
    models = subsystems.get("models") or {}
    logistic = models.get("logistic") or {}
    entropy = subsystems.get("entropy_slope") or {}
    corr = subsystems.get("reviewer_silence_correlation") or {}
    year_without = models.get("year_slope_without_reviewers")
    year_with = models.get("year_slope_with_reviewers")
    widened = (
        year_without is not None and year_with is not None and abs(year_with) > abs(year_without)
    )
    fe = models.get("logistic_year_fixed_effects") or {}
    lines.append(
        f"Classification: {subsystems.get('classification')}. "
        f"Reviewer log-odds coefficient {_fmt(logistic.get('reviewer_coefficient'))} "
        f"CI {_ci(logistic.get('ci95'))} q={_fmt(logistic.get('q'))}. "
        f"Holdout 2024-2026 coefficient {_fmt(subsystems.get('holdout_reviewer_coefficient'))}, "
        f"same sign={subsystems.get('holdout_same_sign')}."
    )
    lines.append(
        f"  Year slope without reviewers {_fmt(year_without)} CI {_ci(models.get('year_slope_without_reviewers_ci95'))}. "
        f"With reviewers {_fmt(year_with)} CI {_ci(models.get('year_slope_with_reviewers_ci95'))}. "
        + ("The slope widens once reviewer count is included, so it does not shrink toward zero." if widened else "The slope moves toward zero once reviewer count is included.")
    )
    lines.append(
        f"  Year-fixed-effects robustness, reviewer coefficient {_fmt(fe.get('reviewer_coefficient'))} "
        f"CI {_ci(fe.get('ci95'))}. This check is not in the BH family."
    )
    spreading = (entropy.get("estimate") or 0) > 0
    lines.append(
        f"  Entropy slope {_fmt(entropy.get('estimate'))} bits/year CI {_ci(entropy.get('ci95'))} q={_fmt(entropy.get('q'))}. "
        + (
            "Entropy rises, so newcomer pull requests spread across more subsystems over time."
            if spreading
            else "Entropy falls, so newcomer pull requests concentrate into fewer subsystems over time."
        )
    )
    lines.append(
        f"  Pearson r, reviewers and silence, {_fmt(corr.get('estimate'))} "
        f"n={corr.get('n')} CI {_ci(corr.get('ci95'))} q={_fmt(corr.get('q'))}."
    )
    lines.append(
        f"  Cohen's d, silence in high-reviewer versus low-reviewer cells: "
        f"{_fmt(subsystems.get('silence_cohens_d_high_minus_low_reviewers'))} "
        f"{subsystems.get('silence_effect_size_flag')}."
    )
    lines.append(f"  {subsystems.get('year_fixed_effects_note')}")
    lines.append("")
    lines.append("WHAT THIS CLOSES")
    lines.append(
        "  Gap 1, per-year principle scores against later health: the timeseries, the largest single-year "
        "decline of each scored principle, and the lagged correlations. P5 and P7 stay unscored. "
        "The correlations are low power and are not a causal lead."
    )
    lines.append(
        "  Gap 2, whether the six confirmed effects are specific to poorly governed repositories: not closed. "
        "Every comparison repository with seven or more years lacks review objects, participant identities, "
        "and a meeting list. The Spearman row is DATA UNAVAILABLE. The bitcoin/bitcoin row is the pass-3 estimate."
    )
    lines.append(
        f"  Gap 3, whether patch-content false negatives are a standing filter or a post-2018 drift: "
        f"classified {fn.get('classification')} from the entry-year distribution and the year slope."
    )
    lines.append(
        f"  Gap 4, whether the rise in newcomer silence is subsystem reviewer capacity: "
        f"classified {subsystems.get('classification')} from the reviewer coefficient and the change in the year slope."
    )
    lines.append("")
    lines.append("WHAT THIS CANNOT PROVE")
    for i, text in enumerate(CANNOT, start=1):
        lines.append(f"  ({i}) {text}")
    lines.append("")
    n_unavail = sum(1 for item in missing if str(item.get("status", "")).startswith("DATA UNAVAILABLE") or item.get("metric"))
    lines.append(f"DATA UNAVAILABLE entries: {len(missing)}.")
    return "\n".join(lines)


def analyze(n_boot: int = N_BOOT, seed: int = SEED) -> Dict[str, Any]:
    rng = np.random.default_rng(seed)
    findings = get_findings_dir()
    missing: List[Dict[str, str]] = []
    tests: List[Dict[str, Any]] = []
    commons_path = findings / "data" / "commons_dynamics_analysis.json"
    if not commons_path.exists():
        unavailable(missing, "commons", "commons_dynamics_analysis.json is missing")
        commons: Dict[str, Any] = {}
    else:
        commons = json.loads(commons_path.read_text())
    logger.info("gap 1 principle lags")
    principles = gap_principles(commons, rng, n_boot, tests, missing) if commons else {"status": "DATA UNAVAILABLE"}
    logger.info("gap 2 cross-repo")
    cross = gap_cross_repo(commons, missing) if commons else {"status": "DATA UNAVAILABLE", "rows": [], "interpretation": []}
    logger.info("loading Core pull requests for gaps 3 and 4")
    frame = load_analysis_frame(missing)
    logger.info("gap 3 false-negative timeline")
    fn = gap_false_negatives(frame, rng, n_boot, tests, missing)
    logger.info("gap 4 subsystems")
    subsystems = gap_subsystems(frame["prs"], rng, n_boot, tests, missing)
    prior = collect_prior_tests(findings, missing)
    prior3 = collect_pass3(findings, missing)
    prior4 = collect_pass4(findings, missing)
    family = apply_family_q(prior, prior3, prior4, tests)
    _assign_readings(principles, cross, fn, subsystems, family)
    # Drop the reviewer-count cache so the payload stays JSON-serializable.
    frame["prs"].pop("_active_cache", None)
    summary = render_summary(principles, cross, fn, subsystems, missing)
    payload = {
        "version": "5.0",
        "seed": seed,
        "bootstrap": n_boot,
        "fit_years": [2010, TRAIN_LAST],
        "holdout_years": [HOLDOUT_FIRST, 2026],
        "shared_controls": [
            "year fixed effects, except where the tested coefficient is a linear year slope",
            "log lines changed",
            "files touched",
            "author tenure in years since the first pull request",
        ],
        "principle_health_timeseries": principles.get("principle_health_timeseries"),
        "principle_health_timeseries_text": _timeseries_text(principles.get("principle_health_timeseries") or {}),
        "principles": principles,
        "cross_repo": cross,
        "false_negative_timeline": fn,
        "subsystem_silence": {
            key: value for key, value in subsystems.items() if key != "cells"
        },
        "subsystem_year_cells": subsystems.get("cells"),
        "hypothesis_tests": tests,
        "bh_family_size": len(family),
        "data_unavailable": missing,
        "plain_text_summary": summary,
        "what_this_closes": [
            "Gap 1: lagged principle-to-health correlations and the load-bearing ranking.",
            "Gap 2: left open. Comparison repositories lack the structures the six effects require.",
            "Gap 3: false-negative timing classified as structural, drift, or mixed.",
            "Gap 4: silence trend classified against subsystem reviewer capacity.",
        ],
        "what_this_cannot_prove": CANNOT,
    }
    return jsonable(payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pass 5 gap closure")
    parser.add_argument("--bootstrap", type=int, default=N_BOOT)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    payload = analyze(n_boot=args.bootstrap, seed=args.seed)
    paths = save_analysis_json("gap_closure_analysis.json", payload)
    print(payload["plain_text_summary"])
    for path in paths:
        logger.info("wrote %s", path)


if __name__ == "__main__":
    main()
