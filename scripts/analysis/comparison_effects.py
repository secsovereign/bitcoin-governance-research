#!/usr/bin/env python3
"""E2, E3, E5, E7, and E12 on comparison repositories, using the commons estimators.

E9 is not applicable outside bitcoin/bitcoin. There is no meeting list to score.
go-ethereum is DATA UNAVAILABLE until it has a pull-request list.
merged_by is not in these dumps, so the top-5 merger window for E3 is not built.
The merged flag is not used in its place.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from scripts.analysis.commons_dynamics_test import (  # noqa: E402
    HOLDOUT_FIRST_YEAR,
    N_BOOT_DEFAULT,
    N_PERM_DEFAULT,
    SEED,
    TOP_MERGERS,
    TRAIN_LAST_YEAR,
    WINDOW,
    SlidingTop,
    _pool_rate,
    bh_qvalues,
    ci_from_draws,
    controls_for_core,
    events_frame,
    fit_split,
    group_diff,
    load_core,
    p_from_draws,
    reciprocity_counts,
    shared_covariates,
    year_of,
)
from scripts.analysis.first_year_signal_test import collect_pass3, unavailable  # noqa: E402
from scripts.analysis.gap_closure_test import MIN_REPO_YEARS, collect_pass4, spearman_with_ci  # noqa: E402
from scripts.analysis.merge_durability import _collect_pass5  # noqa: E402
from scripts.analysis.rsd_ingroup_test import IdentityIndex  # noqa: E402
from scripts.analysis.commons_dynamics_test import People, collect_prior_tests  # noqa: E402
from src.utils.findings_io import save_analysis_json  # noqa: E402
from src.utils.paths import get_data_dir, get_findings_dir  # noqa: E402

EFFECTS = (
    "E2_reciprocity_excess",
    "E3_log_hours_to_next_same_direction_top5_minus_other",
    "E5_log_participants_on_log_days",
    "E7_first_tone_on_merge_given_later_tone",
    "E12_ingroup_on_no_peer_response",
)
PREDICTED = {
    "E2_reciprocity_excess": "negative",
    "E3_log_hours_to_next_same_direction_top5_minus_other": "positive",
    "E5_log_participants_on_log_days": "negative",
    "E7_first_tone_on_merge_given_later_tone": "negative",
    "E12_ingroup_on_no_peer_response": "positive",
}
CLASS_RULE = (
    "TRACKS HEALTH when the Spearman interval of the repository estimate against the size-adjusted residual excludes zero. "
    "Otherwise CORE-SPECIFIC when Core's interval excludes zero and no seven-year comparison repository has an interval that excludes zero in Core's direction. "
    "Otherwise AMBIENT when Core's interval excludes zero, at least half of those repositories share Core's sign, and at least one of those intervals excludes zero. "
    "UNDETERMINED in every other case, including a missing estimate. "
    "The seven-year minimum is the one already used for the cross-repository table."
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


def excludes_zero(ci: Any) -> bool:
    if not isinstance(ci, list) or len(ci) != 2:
        return False
    lo, hi = _finite(ci[0]), _finite(ci[1])
    if lo is None or hi is None:
        return False
    return hi < 0 or lo > 0


def same_sign(left: Optional[float], right: Optional[float]) -> Optional[bool]:
    if left is None or right is None or left == 0 or right == 0:
        return None
    return bool(np.sign(left) == np.sign(right))


def classify_effect(
    core_estimate: Optional[float],
    core_ci: Any,
    outside: Sequence[Dict[str, Any]],
    spearman_ci: Any,
) -> str:
    """Apply CLASS_RULE. outside rows are the seven-year comparison repositories."""
    if excludes_zero(spearman_ci):
        return "TRACKS HEALTH"
    if not excludes_zero(core_ci):
        return "UNDETERMINED"
    eligible = [row for row in outside if _finite(row.get("estimate")) is not None]
    if not eligible:
        return "UNDETERMINED"
    same = 0
    cleared = 0
    for row in eligible:
        estimate = _finite(row.get("estimate"))
        if not same_sign(estimate, core_estimate):
            continue
        same += 1
        if excludes_zero(row.get("ci95")):
            cleared += 1
    if cleared == 0:
        return "CORE-SPECIFIC"
    if same >= 0.5 * len(eligible):
        return "AMBIENT"
    return "UNDETERMINED"


def _pack_fit(train: Optional[Dict[str, Any]], hold: Optional[Dict[str, Any]], *, kind: str) -> Dict[str, Any]:
    if train is None or train.get("estimate") is None:
        return {
            "status": "DATA UNAVAILABLE",
            "reason": "the training model did not fit",
            "estimate": None,
            "ci95": None,
            "p": None,
            "n": None,
            "effect_size_kind": kind,
            "holdout_estimate": None,
            "holdout_same_sign": None,
            "low_power": True,
        }
    estimate = float(train["estimate"])
    hold_est = None if hold is None else _finite(hold.get("estimate"))
    n = int(train.get("n") or 0)
    return {
        "status": "ok",
        "estimate": estimate,
        "ci95": train.get("ci95"),
        "p": train.get("p"),
        "n": n,
        "effect_size": train.get("cohens_d", estimate),
        "effect_size_kind": kind,
        "cohens_d": train.get("cohens_d"),
        "holdout_estimate": hold_est,
        "holdout_same_sign": same_sign(estimate, hold_est),
        "holdout_status": "ok" if hold_est is not None else "DATA UNAVAILABLE",
        "low_power": n < 20,
    }


def e2_excess(core: Dict[str, Any], ev: Dict[str, np.ndarray], rng: np.random.Generator, n_perm: int) -> Dict[str, Any]:
    """Same excess as the commons E2 block. Reviewer labels are shuffled within calendar year."""
    if ev["ts"].size == 0:
        return {"status": "DATA UNAVAILABLE", "reason": "no peer attention events were loaded", "estimate": None}
    author_of_event = core["author"][ev["pr"]]
    ev_year = np.array([year_of(t) for t in ev["ts"].tolist()], dtype=np.int16)
    obs_hits, obs_opps = reciprocity_counts(ev["person"], author_of_event, ev["ts"], ev_year)
    obs_train = _pool_rate(obs_hits, obs_opps, lambda y: y <= TRAIN_LAST_YEAR)
    obs_hold = _pool_rate(obs_hits, obs_opps, lambda y: y >= HOLDOUT_FIRST_YEAR)
    null_train = np.empty(n_perm)
    null_hold = np.empty(n_perm)
    year_levels = sorted(obs_opps)
    for i in range(n_perm):
        shuffled = ev["person"].copy()
        for y in year_levels:
            ix = np.flatnonzero(ev_year == y)
            if ix.size:
                shuffled[ix] = rng.permutation(shuffled[ix])
        hits_i, opps_i = reciprocity_counts(shuffled, author_of_event, ev["ts"], ev_year)
        null_train[i] = _pool_rate(hits_i, opps_i, lambda y: y <= TRAIN_LAST_YEAR)
        null_hold[i] = _pool_rate(hits_i, opps_i, lambda y: y >= HOLDOUT_FIRST_YEAR)
    n_train = int(sum(v for y, v in obs_opps.items() if y <= TRAIN_LAST_YEAR))
    if not np.isfinite(obs_train) or not np.isfinite(null_train).any():
        return {"status": "DATA UNAVAILABLE", "reason": "reciprocity could not be computed on 2010-2023 events", "estimate": None, "n": n_train}
    center = float(np.nanmean(null_train))
    estimate = float(obs_train - center)
    draws = obs_train - null_train
    p = float((np.sum(np.abs(null_train - center) >= abs(obs_train - center)) + 1) / (null_train.size + 1))
    hold_est = None
    if np.isfinite(obs_hold) and np.isfinite(null_hold).any():
        hold_est = float(obs_hold - float(np.nanmean(null_hold)))
    return {
        "status": "ok",
        "estimate": estimate,
        "ci95": ci_from_draws(draws),
        "p": p,
        "n": n_train,
        "effect_size": estimate,
        "effect_size_kind": "excess_over_null",
        "holdout_estimate": hold_est,
        "holdout_same_sign": same_sign(estimate, hold_est),
        "holdout_status": "ok" if hold_est is not None else "DATA UNAVAILABLE",
        "low_power": n_train < 20,
        "permutations": n_perm,
    }


def e3_time(core: Dict[str, Any], ev: Dict[str, np.ndarray], rng: np.random.Generator, n_boot: int) -> Dict[str, Any]:
    """Same top-5-merger timing contrast. Empty when merged_by was never stored."""
    n = core["created"].size
    merge_events = [
        (float(core["merged_at"][i]), int(core["merger"][i]))
        for i in range(n)
        if core["merged"][i] and np.isfinite(core["merged_at"][i]) and int(core["merger"][i]) >= 0
    ]
    if not merge_events:
        return {
            "status": "DATA UNAVAILABLE",
            "reason": "pull records do not store merged_by, so the trailing top-5 merger window cannot be built. The merged flag is not used as a substitute.",
            "estimate": None,
            "ci95": None,
            "p": None,
            "n": None,
            "holdout_estimate": None,
            "holdout_same_sign": None,
            "low_power": True,
            "effect_size_kind": "cohens_d",
        }
    sig = np.isfinite(core["signal_ts"]) & (core["signal_dir"] != 0)
    slider_m = SlidingTop(merge_events, WINDOW, TOP_MERGERS)
    top5_first = np.zeros(n, dtype=np.int8)
    top5_known = np.zeros(n, dtype=np.int8)
    order_sig = np.argsort(np.where(sig, core["signal_ts"], np.inf), kind="mergesort")
    for i in order_sig:
        if not sig[i]:
            break
        slider_m.advance(float(core["signal_ts"][i]))
        flag = slider_m.contains(int(core["signal_person"][i]))
        if flag is None:
            continue
        top5_known[i] = 1
        top5_first[i] = 1 if flag else 0
    later_hours = np.full(n, np.nan)
    by_pr: Dict[int, List[int]] = {}
    for k in np.argsort(ev["ts"], kind="mergesort"):
        by_pr.setdefault(int(ev["pr"][k]), []).append(int(k))
    for i in np.flatnonzero(sig & top5_known.astype(bool)):
        direction_ack = int(core["signal_dir"][i]) == 1
        start = float(core["signal_ts"][i])
        same_time = None
        for k in by_pr.get(int(i), []):
            if float(ev["ts"][k]) <= start or int(ev["person"][k]) == int(core["signal_person"][i]):
                continue
            is_ack = bool(ev["ack"][k])
            is_nack = bool(ev["nack"][k])
            if not is_ack and not is_nack:
                continue
            if is_ack if direction_ack else is_nack:
                same_time = float(ev["ts"][k])
                break
        if same_time is not None:
            later_hours[i] = (same_time - start) / 3600.0
    known = top5_known.astype(bool) & sig

    def time_pack(mask: np.ndarray) -> Optional[Dict[str, Any]]:
        a = np.log1p(later_hours[mask & (top5_first == 1)])
        b = np.log1p(later_hours[mask & (top5_first == 0)])
        return group_diff(a, b, rng, n_boot)

    train = time_pack(known & (core["year"] <= TRAIN_LAST_YEAR))
    hold = time_pack(known & (core["year"] >= HOLDOUT_FIRST_YEAR))
    packed = _pack_fit(train, hold, kind="cohens_d")
    if packed["status"] != "ok":
        packed["reason"] = "not enough pull requests with a later same-direction review in both groups"
    return packed


def e5_e7_e12(core: Dict[str, Any], ctrl: Dict[str, np.ndarray], rng: np.random.Generator, n_boot: int) -> Dict[str, Dict[str, Any]]:
    n = core["created"].size
    cov_all = shared_covariates(ctrl, np.arange(n))
    decided = core["decided"].astype(bool)
    end_ts = np.where(core["merged"].astype(bool), core["merged_at"], core["closed_at"])
    days = (end_ts - core["created"]) / 86400.0
    log_days = np.where(decided & np.isfinite(days) & (days >= 0), np.log1p(days), np.nan)
    log_part = np.log1p(core["participants"].astype(float))
    train_d, hold_d = fit_split(log_days, log_part, cov_all, core["year"].astype(float), rng, n_boot, False)
    later_mean = np.where(core["later_n"] > 0, core["later_sum"] / np.maximum(core["later_n"], 1), np.nan)
    y_merge = np.where(decided, core["merged"].astype(float), np.nan)
    train_a, hold_a = fit_split(
        y_merge, core["first_tone"], cov_all + [later_mean], core["year"].astype(float), rng, n_boot, True,
    )
    no_resp = np.where(np.isfinite(core["first_peer"]), 0.0, 1.0)
    train_nr, hold_nr = fit_split(no_resp, ctrl["ingroup"], [
        ctrl["log_lines"], ctrl["files"], ctrl["tenure"], ctrl["prior"], ctrl["unidentified"],
    ], core["year"].astype(float), rng, n_boot, True)
    return {
        "E5_log_participants_on_log_days": _pack_fit(train_d, hold_d, kind="standardized_coefficient"),
        "E7_first_tone_on_merge_given_later_tone": _pack_fit(train_a, hold_a, kind="standardized_coefficient"),
        "E12_ingroup_on_no_peer_response": _pack_fit(train_nr, hold_nr, kind="standardized_coefficient"),
    }


def write_joined(slug: str, dest: Path) -> Dict[str, Any]:
    """One pull-request file in the shape load_core already reads. Missing rows are omitted."""
    owner, repo = slug.split("/", 1)
    root = get_data_dir() / "github" / "repos" / owner / repo
    prs_path = root / "prs.jsonl"
    detail_path = root / "pr_detail.jsonl"
    if not prs_path.exists():
        return {"status": "DATA UNAVAILABLE", "reason": "prs.jsonl is missing, so review objects were not requested"}
    if not detail_path.exists():
        return {"status": "DATA UNAVAILABLE", "reason": "pr_detail.jsonl is missing"}
    detail: Dict[int, Dict[str, Any]] = {}
    with detail_path.open() as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            number = row.get("number")
            if isinstance(number, int):
                detail[number] = row
    capped = {"reviews": 0, "comments": 0, "review_comments": 0, "files": 0}
    missing_rows = 0
    kept = 0
    with prs_path.open() as handle, dest.open("w") as out:
        for line in handle:
            if not line.strip():
                continue
            pr = json.loads(line)
            number = pr.get("number")
            extra = detail.get(number) if isinstance(number, int) else None
            if not extra or extra.get("missing"):
                missing_rows += 1
                continue
            files = extra.get("files") or []
            reviews = extra.get("reviews") or []
            comments = extra.get("comments") or []
            review_comments = extra.get("review_comments") or []
            for key, rows in (
                ("reviews", reviews),
                ("comments", comments),
                ("review_comments", review_comments),
                ("files", files),
            ):
                if isinstance(rows, list) and len(rows) >= 100:
                    capped[key] += 1
            adds = dels = 0
            for item in files:
                if not isinstance(item, dict):
                    continue
                adds += int(item.get("additions") or 0)
                dels += int(item.get("deletions") or 0)
            pr["reviews"] = reviews
            pr["comments"] = comments
            pr["review_comments"] = review_comments
            pr["files"] = files
            pr["total_additions"] = adds
            pr["total_deletions"] = dels
            pr["total_files_changed"] = len(files) if isinstance(files, list) else 0
            out.write(json.dumps(pr) + "\n")
            kept += 1
    return {"status": "ok", "kept": kept, "missing_rows": missing_rows, "capped_at_100": capped}


def score_repo(path: Path, rng: np.random.Generator, n_boot: int, n_perm: int) -> Dict[str, Any]:
    """Login strings only. The Bitcoin Core alias table is not applied to other projects."""
    people = People()
    core = load_core(path, IdentityIndex(), people)
    if core["created"].size == 0:
        return {"status": "DATA UNAVAILABLE", "reason": "no usable pull requests after dropping bots"}
    ctrl = controls_for_core(core, set())
    ev = events_frame(core["events"])
    effects = {
        "E2_reciprocity_excess": e2_excess(core, ev, rng, n_perm),
        "E3_log_hours_to_next_same_direction_top5_minus_other": e3_time(core, ev, rng, n_boot),
    }
    effects.update(e5_e7_e12(core, ctrl, rng, n_boot))
    years = {int(y) for y in core["year"].tolist()}
    return {
        "status": "ok",
        "n_prs": int(core["created"].size),
        "n_years": len(years),
        "year_min": min(years) if years else None,
        "year_max": max(years) if years else None,
        "n_review_objects": len(core["review_objects"]),
        "n_unidentified": int(ctrl["unidentified"].sum()),
        "effects": effects,
    }


def _core_reference(findings: Path) -> Dict[str, Dict[str, Any]]:
    path = findings / "data" / "commons_dynamics_analysis.json"
    found: Dict[str, Dict[str, Any]] = {}
    if not path.exists():
        return found
    for test in json.loads(path.read_text()).get("hypothesis_tests") or []:
        tid = test.get("id")
        if tid in EFFECTS and tid not in found:
            found[tid] = test
    return found


def _residuals(findings: Path) -> Dict[str, float]:
    path = findings / "data" / "size_adjusted_health.json"
    if not path.exists():
        return {}
    sample = (json.loads(path.read_text()).get("samples") or {}).get("all_repositories") or {}
    out = {}
    for row in sample.get("repositories") or []:
        value = _finite(row.get("residual"))
        if value is not None:
            out[row["repo"]] = value
    return out


def _family(findings: Path, missing: List[Dict[str, str]], tests: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    stored = (
        list(collect_prior_tests(findings, missing))
        + list(collect_pass3(findings, missing))
        + list(collect_pass4(findings, missing))
        + list(_collect_pass5(findings, missing))
    )
    durability = findings / "data" / "merge_durability.json"
    if durability.exists():
        for test in json.loads(durability.read_text()).get("hypothesis_tests") or []:
            if test.get("in_bh_family") and test.get("p") is not None:
                stored.append(test)
    old_q = {str(row.get("id")): row.get("q") for row in stored}
    family = [row for row in stored + list(tests) if row.get("in_bh_family") and row.get("p") is not None]
    qvals = bh_qvalues([float(row["p"]) for row in family])
    crossed = []
    for row, q in zip(family, qvals):
        previous = old_q.get(str(row.get("id")))
        row["q"] = float(q)
        if previous is None:
            continue
        was = float(previous) < 0.05
        now = float(q) < 0.05
        if was != now:
            crossed.append({
                "id": row.get("id"),
                "q_before": float(previous),
                "q_after": float(q),
                "crossed": "above 0.05" if was and not now else "below 0.05",
            })
    return family, crossed


def analyze(n_boot: int = N_BOOT_DEFAULT, n_perm: int = N_PERM_DEFAULT, seed: int = SEED) -> Dict[str, Any]:
    findings = get_findings_dir()
    missing: List[Dict[str, str]] = []
    config_path = project_root / "scripts" / "data_collection" / "comparison_repos.json"
    slugs = [row["slug"] for row in json.loads(config_path.read_text()).get("repos") or []]
    rng = np.random.default_rng(seed)
    rows = []
    with tempfile.TemporaryDirectory(prefix="comparison-effects-") as tmp:
        scratch = Path(tmp)
        for slug in slugs:
            print(f"scoring {slug}", flush=True)
            joined = scratch / "joined.jsonl"
            built = write_joined(slug, joined)
            if built.get("status") != "ok":
                unavailable(missing, slug, built.get("reason", "detail was not collected"))
                rows.append({"repo": slug, "status": "DATA UNAVAILABLE", "reason": built.get("reason"), "effects": {}})
                continue
            scored = score_repo(joined, rng, n_boot, n_perm)
            scored["repo"] = slug
            scored["missing_rows"] = built["missing_rows"]
            scored["capped_at_100"] = built["capped_at_100"]
            scored["eligible_for_spearman"] = scored.get("n_years", 0) >= MIN_REPO_YEARS
            if not scored["eligible_for_spearman"]:
                unavailable(
                    missing, f"spearman_{slug}",
                    f"{scored.get('n_years')} distinct years of history, below the 7-year minimum",
                )
            rows.append(scored)
            print(f"scored {slug} prs={scored.get('n_prs')}", flush=True)
    reference = _core_reference(findings)
    residuals = _residuals(findings)
    if "bitcoin/bitcoin" not in residuals:
        unavailable(missing, "core_residual", "size_adjusted_health.json has no bitcoin/bitcoin residual")
    tests: List[Dict[str, Any]] = []
    for row in rows:
        if row.get("status") != "ok":
            continue
        for effect_id, fit in (row.get("effects") or {}).items():
            if fit.get("p") is None:
                continue
            tests.append({
                "id": f"pass6.{effect_id}.{row['repo']}",
                "estimate": fit.get("estimate"),
                "ci95": fit.get("ci95"),
                "p": fit.get("p"),
                "n": fit.get("n"),
                "source": "pass6",
                "in_bh_family": True,
                "low_power": fit.get("low_power"),
                "holdout_same_sign": fit.get("holdout_same_sign"),
            })
    spearman = {}
    classifications = {}
    for effect_id in EFFECTS:
        pairs_x = []
        pairs_y = []
        core = reference.get(effect_id) or {}
        core_est = _finite(core.get("estimate"))
        if core_est is not None and "bitcoin/bitcoin" in residuals:
            pairs_x.append(core_est)
            pairs_y.append(residuals["bitcoin/bitcoin"])
        outside = []
        for row in rows:
            if row.get("status") != "ok" or not row.get("eligible_for_spearman"):
                continue
            fit = (row.get("effects") or {}).get(effect_id) or {}
            outside.append(fit)
            estimate = _finite(fit.get("estimate"))
            residual = residuals.get(row["repo"])
            if estimate is None or residual is None:
                continue
            pairs_x.append(estimate)
            pairs_y.append(residual)
        fit = spearman_with_ci(np.asarray(pairs_x, dtype=float), np.asarray(pairs_y, dtype=float), rng, n_boot)
        fit["predicted_sign"] = PREDICTED[effect_id]
        fit["low_power"] = True
        if fit.get("status") == "ok" and fit.get("p") is not None:
            tests.append({
                "id": f"pass6.spearman.{effect_id}",
                "estimate": fit.get("estimate"),
                "ci95": fit.get("ci95"),
                "p": fit.get("p"),
                "n": fit.get("n"),
                "source": "pass6",
                "in_bh_family": True,
                "low_power": True,
            })
        else:
            unavailable(missing, f"spearman_{effect_id}", fit.get("reason", "Spearman correlation was not defined"))
        point = _finite(fit.get("estimate"))
        predicted = PREDICTED[effect_id]
        fit["point_matches_prediction"] = same_sign(point, -1.0 if predicted == "negative" else 1.0)
        fit["interval_excludes_zero"] = excludes_zero(fit.get("ci95"))
        spearman[effect_id] = fit
        label = classify_effect(core_est, core.get("ci95"), outside, fit.get("ci95"))
        present_outside = any(
            excludes_zero(item.get("ci95")) and same_sign(_finite(item.get("estimate")), core_est)
            for item in outside
        )
        classifications[effect_id] = {
            "class": label,
            "present_outside_core": present_outside,
            "tracks_health": excludes_zero(fit.get("ci95")),
            "core_estimate": core_est,
            "core_ci95": core.get("ci95"),
            "predicted_sign": predicted,
            "spearman_r": point,
            "spearman_ci95": fit.get("ci95"),
        }
    family, crossed = _family(findings, missing, tests)
    for test in tests:
        match = next((row for row in family if row.get("id") == test["id"]), None)
        if match is not None:
            test["q"] = match.get("q")
    return {
        "version": "6.0",
        "task": 4,
        "status": "ok",
        "preregistration_timestamp": "2026-10-10T01:00:09Z",
        "classification_rule": CLASS_RULE,
        "e9": {
            "status": "not_applicable",
            "reason": "E9 stays on bitcoin/bitcoin. No other project in this set has a meeting list.",
        },
        "shared_health_rerun": {
            "status": "unchanged",
            "reason": (
                "H2, H3, H4 merge Gini, H5, and H6 are computed from open and close timestamps, author, and merged state. "
                "Review objects, comment authors, and file paths do not enter them. The shared-health rank and the Task 3 residual are not refit."
            ),
        },
        "repositories": rows,
        "spearman_versus_size_adjusted_residual": spearman,
        "classifications": classifications,
        "hypothesis_tests": tests,
        "bh_family_size": len(family),
        "bh_crossed_0_05": crossed,
        "data_unavailable": missing,
        "what_this_cannot_prove": [
            "A correlation between an effect and a size-adjusted residual is not a cause of that residual.",
            "Fewer than 20 repositories make every cross-repository correlation LOW POWER.",
            "Pull requests GitHub no longer serves are omitted, not scored as having no review.",
            "Lists longer than 100 reviews, comments, or files are cut at the first page, so those pull requests are under-counted.",
            "E3 is not identified outside Core because merged_by was not stored. That absence is not evidence the cascade is Core-specific.",
            "E9 is not applicable outside bitcoin/bitcoin.",
        ],
    }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Score comparison-repo effects against the size-adjusted residual")
    parser.add_argument("--bootstrap", type=int, default=N_BOOT_DEFAULT)
    parser.add_argument("--permutations", type=int, default=N_PERM_DEFAULT)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    result = analyze(n_boot=args.bootstrap, n_perm=args.permutations, seed=args.seed)
    save_analysis_json("comparison_effects.json", result)
    print(json.dumps({
        "family": result["bh_family_size"],
        "crossed": result["bh_crossed_0_05"],
        "classes": {key: row["class"] for key, row in result["classifications"].items()},
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
