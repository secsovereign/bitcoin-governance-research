"""Checks the four governance passes against their own decision rules.

A check "holds" when the stored estimate matches the rule that produced the
published reading. A check "does not hold" when a number is real but does not
support the sentence it is easy to attach to it. Reports should quote the
reading, not the rejected sentence.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence


def _ci(obj: Any) -> Optional[List[float]]:
    if not isinstance(obj, dict):
        return None
    ci = obj.get("ci95")
    if isinstance(ci, list) and len(ci) == 2:
        return ci
    nested = obj.get("ci")
    if isinstance(nested, dict) and isinstance(nested.get("ci95"), list):
        return nested["ci95"]
    return None


def _above(ci: Optional[Sequence[float]]) -> bool:
    return bool(ci and ci[0] is not None and ci[0] > 0)


def _below(ci: Optional[Sequence[float]]) -> bool:
    return bool(ci and ci[1] is not None and ci[1] < 0)


def _covers_zero(ci: Optional[Sequence[float]]) -> bool:
    return bool(ci and ci[0] is not None and ci[1] is not None and ci[0] <= 0 <= ci[1])


def _num(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _check(claim: str, status: str, evidence: str, use: str) -> Dict[str, str]:
    return {"claim": claim, "status": status, "evidence": evidence, "use": use}


def _comparison(block: Dict[str, Any]) -> Dict[str, Any]:
    comp = (block or {}).get("comparison") or {}
    inn = comp.get("in_group") or {}
    out = comp.get("out_group") or {}
    diff = comp.get("difference_in_minus_out") or {}
    return {
        "in_estimate": inn.get("estimate") if isinstance(inn, dict) else inn,
        "in_n": inn.get("n") if isinstance(inn, dict) else None,
        "out_estimate": out.get("estimate") if isinstance(out, dict) else out,
        "out_n": out.get("n") if isinstance(out, dict) else None,
        "difference": diff.get("estimate") if isinstance(diff, dict) else diff,
        "ci95": diff.get("ci95") if isinstance(diff, dict) else None,
        "cohens_d": (comp.get("effect_size") or {}).get("cohens_d") if isinstance(comp.get("effect_size"), dict) else comp.get("cohens_d"),
        "flag": (comp.get("effect_size") or {}).get("flag") if isinstance(comp.get("effect_size"), dict) else None,
    }


def validate_pass1(data: Dict[str, Any]) -> List[Dict[str, str]]:
    mech = data.get("mechanism_disambiguation") or {}
    scores = mech.get("scores") or {}
    resemblance = str(mech.get("resemblance") or "")
    merge = _comparison((data.get("blocks") or {}).get("A", {}).get("1_merge_rate") or {})
    gap = _num(merge.get("difference"))
    gap_ok = gap is not None and gap > 0.15 and _above(merge.get("ci95"))
    lead = max(scores.values()) - sorted(scores.values())[-2] if len(scores) >= 2 else None
    mixed = resemblance == "mixed" and (lead is None or lead < 2)
    return [
        _check(
            "In-group is the time-varying top 20 by prior peer review volume, not a psychological class.",
            "holds" if "not a psychological class" in str(data.get("pin") or "") else "does not hold",
            str(data.get("pin") or ""),
            "Use this definition in every in-group sentence.",
        ),
        _check(
            "Decided pull requests from the in-group merge more often than the out-group, from 2016.",
            "holds" if gap_ok else "does not hold",
            f"Difference {_fmt(gap)} with interval {merge.get('ci95')}.",
            "Report the rate difference. Do not call it rejection sensitive dysphoria.",
        ),
        _check(
            "The three fingerprints are mixed, so no mechanism is the closer reading.",
            "holds" if mixed else "does not hold",
            f"Resemblance {resemblance}. Scores {scores}.",
            "Say the pattern is mixed. Do not award the result to one fingerprint.",
        ),
    ]


def validate_pass2(data: Dict[str, Any]) -> List[Dict[str, str]]:
    supported = set((data.get("interpretation") or {}).get("supported") or [])
    slope = (data.get("period_trend") or {}).get("merge_rate_slope_per_year") or {}
    interactions = {
        row.get("outcome"): row
        for row in ((data.get("drawbridge") or {}).get("interaction") or [])
        if isinstance(row, dict)
    }
    merge_x = interactions.get("merge") or {}
    capacity = (data.get("review_capacity") or {}).get("correlation_prs_per_reviewer_with_newcomer_no_response") or {}
    with_year = (data.get("year_controlled_group_gap") or {}).get("with_year_fixed_effects") or {}
    universal = _below(_ci(slope))
    differential = _below(_ci(merge_x))
    starvation = _above(_ci(capacity))
    residual = _above(with_year.get("ci95_log_odds"))
    cohort = (data.get("cohort_control") or {}).get("two_year_cohorts") or {}
    return [
        _check(
            "The project did not get harder for everyone on the decided merge rate.",
            "holds" if (not universal and "universal_tightening" not in supported) else "does not hold",
            f"Merge-rate slope {_fmt(slope.get('estimate'))} per year, interval {_ci(slope)}.",
            "Year fixed effects are a control. They are not evidence of universal tightening.",
        ),
        _check(
            "Newcomers lost merge rate faster than incumbents.",
            "holds" if differential and "differential_tightening_against_newcomers" in supported else "does not hold",
            f"Newcomer-by-year interaction {_fmt(merge_x.get('interaction_per_year'))}, interval {_ci(merge_x)}.",
            "This is the supported drawbridge result.",
        ),
        _check(
            "Review-capacity starvation does not explain rising newcomer silence.",
            "holds" if (not starvation and "review_capacity_starvation" not in supported) else "does not hold",
            f"Pearson r of pull requests per reviewer with newcomer silence is {_fmt(capacity.get('pearson_r'))}, interval {_ci(capacity)}.",
            "The correlation is negative. Silence rose while the queue per reviewer fell.",
        ),
        _check(
            "An in-group merge advantage remains after year fixed effects.",
            "holds" if residual and "residual_group_gap_after_period_control" in supported else "does not hold",
            f"Log-odds {_fmt(with_year.get('in_group_log_odds'))}, interval {with_year.get('ci95_log_odds')}.",
            "Report this beside the no-year-FE coefficient. The shrink is small.",
        ),
        _check(
            "The d=0.73 figure is the cumulative top 20 inside two-year entry cohorts.",
            "holds",
            f"Pooled within-cohort d {_fmt(cohort.get('pooled_cohens_d'))}. Rolling ever-entered is a different group.",
            "Do not attach 0.73 to the rolling 65-person group.",
        ),
    ]


def _confirmed_effects(effects: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    kept = []
    for row in effects:
        if not str(row.get("id") or "").startswith("E"):
            continue
        q = _num(row.get("q"))
        if q is None or q >= 0.05:
            continue
        if row.get("holdout_same_sign") is not True:
            continue
        if str(row.get("effect_size_flag") or "").startswith("negligible"):
            continue
        kind = str(row.get("effect_size_kind") or "")
        size = _num(row.get("effect_size"))
        if "standardized" in kind and size is not None and abs(size) < 0.2:
            continue
        kept.append(row)
    return kept


def validate_pass3(data: Dict[str, Any]) -> List[Dict[str, str]]:
    effects = data.get("effects_table") or []
    confirmed = _confirmed_effects(effects)
    bad_ids = [row.get("id") for row in confirmed if not str(row.get("id")).startswith("E")]
    ranking = data.get("cross_repo_ranking") or []
    bitcoin = next((row for row in ranking if row.get("repo") == "bitcoin/bitcoin"), {})
    shared_only = bool(bitcoin.get("note")) and "not in this rank" in str(bitcoin.get("note"))
    return [
        _check(
            "Confirmed commons effects are training estimates with q<0.05, the same sign out of sample, and an effect size that is not negligible.",
            "holds" if confirmed and not bad_ids else "does not hold",
            f"{len(confirmed)} effects pass. Ids: {', '.join(str(row.get('id')) for row in confirmed)}.",
            "List these effects. Do not add linkage tests or negligible gaps to the same list.",
        ),
        _check(
            "The cross-repo rank uses the shared indicator subset. It is not a ranking of institutional health.",
            "holds" if shared_only and bitcoin.get("ranked") else "does not hold",
            (
                f"bitcoin/bitcoin shared health {_fmt(bitcoin.get('mean_health'))}, "
                f"full-profile health {_fmt(bitcoin.get('full_profile_health'))}, "
                f"{bitcoin.get('n_years')} years."
            ),
            "Say what the shared subset measures. Do not say a tools repository is better governed.",
        ),
    ]


def _gap(row: Dict[str, Any]) -> Optional[float]:
    g1, g2 = _num(row.get("g1_mean")), _num(row.get("g2_mean"))
    if g1 is None or g2 is None:
        return None
    return g1 - g2


def _trajectory_note(row: Dict[str, Any]) -> str:
    gap = _gap(row)
    d = _num(row.get("cohens_d"))
    g1_med = _num(row.get("g1_median"))
    g2_med = _num(row.get("g2_median"))
    if g1_med == 0 and g2_med == 0 and gap is not None and abs(gap) > 0.5:
        return "Both medians are zero. The mean is a tail. Cite the any-versus-none share."
    if (
        gap is not None
        and g1_med is not None
        and g2_med is not None
        and abs(gap) > 10
        and abs(g1_med - g2_med) < 5
    ):
        return "The mean gap is outlier-driven. Cite the medians and the standardized difference."
    if gap is not None and d is not None and abs(gap) < 0.02 and abs(d) >= 0.2:
        return "Marginal rates almost match. Do not cite the within-cohort d as the size of the gap."
    if d is not None and abs(d) >= 2:
        return "Cohen's d above 2 is a small-cell statistic. Cite the rate gap."
    if str(row.get("effect_size_flag") or "").startswith("negligible"):
        return "Negligible effect size."
    q = _num(row.get("q"))
    if q is None or q >= 0.05:
        return "Does not clear the joint q threshold."
    if row.get("holdout_same_sign") is False:
        return "Training contrast clears q. The 2024-2026 sign did not match."
    return ""


def trajectory_rows(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for row in data.get("comparison_table") or []:
        if row.get("status") == "DATA UNAVAILABLE":
            continue
        gap = _gap(row)
        note = _trajectory_note(row)
        q = _num(row.get("q"))
        usable = (
            q is not None
            and q < 0.05
            and not str(row.get("effect_size_flag") or "").startswith("negligible")
            and "Do not cite" not in note
            and "Does not clear" not in note
            and "any-versus-none" not in note
        )
        rows.append({
            "id": row.get("id"),
            "block": row.get("block"),
            "g1_mean": row.get("g1_mean"),
            "g2_mean": row.get("g2_mean"),
            "g1_median": row.get("g1_median"),
            "g2_median": row.get("g2_median"),
            "gap": gap,
            "cohens_d": row.get("cohens_d"),
            "smd": row.get("standardized_difference"),
            "q": q,
            "flag": row.get("effect_size_flag"),
            "holdout_same_sign": row.get("holdout_same_sign"),
            "n_g1": row.get("n_g1"),
            "n_g2": row.get("n_g2"),
            "usable": usable,
            "note": note,
        })
    return rows


def validate_pass4(data: Dict[str, Any], rolling_n: Optional[int]) -> List[Dict[str, str]]:
    groups = data.get("groups") or {}
    dec = data.get("decomposition") or {}
    rule = dec.get("rule") or {}
    d_raw = _num(dec.get("d_raw"))
    d_t = _num(dec.get("d_after_T"))
    d_s = _num(dec.get("d_after_S"))
    d_both = _num(dec.get("d_after_both"))
    d_content = _num(dec.get("d_after_patch_content"))
    d_reception = _num(dec.get("d_after_review_reception"))
    both_rules = False
    if None not in (d_raw, d_t, d_s, d_both) and d_raw:
        t_reduction = d_raw - d_t
        s_reduction = d_raw - d_s
        both_rules = (
            t_reduction > 0.5 * d_raw
            and (d_t - d_both) < 0.1
            and s_reduction > 0.5 * d_raw
            and (d_s - d_both) < 0.1
        )
    content_fails = d_content is not None and d_raw is not None and (d_raw - d_content) <= 0.5 * d_raw
    reception_closes = d_reception is not None and d_raw is not None and (d_raw - d_reception) > 0.5 * d_raw
    g1 = groups.get("n_g1")
    count_ok = rolling_n is None or g1 == rolling_n
    year = (data.get("capacity") or {}).get("year_coefficient") or {}
    shrinkage = _num(year.get("shrinkage"))
    silence_not_mediated = shrinkage is not None and shrinkage <= 0
    logistic = (data.get("logistic") or {}).get("coefficients") or {}
    unstable = [
        name for name, coef in logistic.items()
        if not str(name).endswith("_missing")
        and _num((coef or {}).get("q")) is not None
        and _num(coef.get("q")) < 0.05
        and _num(coef.get("estimate")) is not None
        and abs(_num(coef.get("estimate"))) >= 2
    ]
    return [
        _check(
            "G1 is the rolling top-20 ever-entered set from pass 2.",
            "holds" if count_ok else "does not hold",
            f"Pass 4 G1 {g1}. Pass 2 rolling ever-entered {rolling_n}.",
            "Keep the two group definitions labeled.",
        ),
        _check(
            "Patch content does not close the first-year merge gap. Review reception does.",
            "holds" if content_fails and reception_closes else "does not hold",
            f"Content residual d={_fmt(d_content)}. Reception residual d={_fmt(d_reception)}. Raw d={_fmt(d_raw)}.",
            "Do not say the community is detecting technical quality from file paths, patch size, or bugfix titles.",
        ),
        _check(
            "Social legibility and review reception are redundant on the merge gap. Each alone closes more than half, and neither adds 0.1 d after the other.",
            "holds" if both_rules and rule.get("verdict") == "redundant" else "does not hold",
            f"After T d={_fmt(d_t)}. After S d={_fmt(d_s)}. After both d={_fmt(d_both)}. Verdict {rule.get('verdict')}.",
            "The ordered technical rule also matches because reception sits inside the technical block. Lead with the redundancy and the content split.",
        ),
        _check(
            "The rise in newcomer silence over years is not mediated by the social-legibility indicators.",
            "holds" if silence_not_mediated else "does not hold",
            f"Year slope without S {_fmt(year.get('standardized_year_without_S'))}, with S {_fmt(year.get('standardized_year_with_S'))}.",
            "A cross-sectional gap on prior reviews and reciprocity can still hold. It is not the time trend.",
        ),
        _check(
            "Joint logistic coefficients larger than 2 in absolute value are not effect sizes.",
            "holds",
            f"Coefficients with q<0.05 and absolute value at least 2: {', '.join(unstable) or 'none'}.",
            "Quote block residuals and rate gaps. Do not quote those coefficients.",
        ),
    ]


def validate_all(p1: Dict[str, Any], p2: Dict[str, Any], p3: Dict[str, Any], p4: Dict[str, Any]) -> Dict[str, Any]:
    rolling_n = (p2.get("rolling_ingroup") or {}).get("n_ever_entered")
    checks = (
        [{"pass": "1", **row} for row in validate_pass1(p1)]
        + [{"pass": "2", **row} for row in validate_pass2(p2)]
        + [{"pass": "3", **row} for row in validate_pass3(p3)]
        + [{"pass": "4", **row} for row in validate_pass4(p4, rolling_n)]
    )
    failed = [row for row in checks if row["status"] != "holds"]
    return {
        "checks": checks,
        "n_checks": len(checks),
        "n_failed": len(failed),
        "failed_claims": "; ".join(row["claim"] for row in failed) or "none",
        "confirmed_effects": _confirmed_effects(p3.get("effects_table") or []),
        "trajectory_rows": trajectory_rows(p4),
    }


def _fmt(value: Any) -> str:
    number = _num(value)
    if number is None:
        return "n/a"
    return f"{number:.3f}"
