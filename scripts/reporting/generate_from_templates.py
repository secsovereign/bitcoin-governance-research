#!/usr/bin/env python3
"""Render findings markdown from templates + analysis JSON.

See scripts/reporting/README.md. Add a report: ctx_* + templates/*.md.tpl + a job in generate_all().
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from template_engine import render_file
from src.utils.logger import setup_logger
from src.utils.paths import get_analysis_dir, get_findings_dir

logger = setup_logger()

TEMPLATES = Path(__file__).resolve().parent / "templates"


def _load(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _maybe(path: Path) -> Optional[Dict[str, Any]]:
    return _load(path) if path.exists() else None


def _pairs(items: Any, limit: int = 10) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not items:
        return out
    for i, item in enumerate(items[:limit], start=1):
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            out.append({"0": item[0], "1": item[1], "name": item[0], "count": item[1], "rank": i})
        elif isinstance(item, dict):
            row = dict(item)
            row.setdefault("rank", i)
            out.append(row)
    return out


def _window_view(window: Dict[str, Any]) -> Dict[str, Any]:
    fair = window.get("bivariate_fair") or {}
    raw = window.get("bivariate_raw") or {}
    maint = fair.get("maintainer") or {}
    non = fair.get("non_maintainer") or {}
    segs = window.get("outsider_segments") or {}
    cold = segs.get("cold_start_first_pr") or {}
    established = segs.get("established_ge_5_prior_merges") or {}
    top20 = segs.get("top_20_volume_non_maintainer_authors") or {}
    size = window.get("size_strata") or {}
    large = ((size.get("ge_2000_loc") or {}).get("closed_only") or {})
    quality = window.get("quality_matched") or {}
    means = quality.get("mean_scores") or {}
    high_prep = quality.get("high_author_prep_ge_065") or {}
    phase2 = quality.get("phase2") or {}
    concept = phase2.get("concept_ack_received") or {}
    tests = phase2.get("high_prep_and_nontrivial_tests") or {}
    maint_high = (high_prep.get("maintainer") or {}).get("raw_merge_rate")
    non_high = (high_prep.get("non_maintainer") or {}).get("raw_merge_rate")
    gap = high_prep.get("raw_merge_gap_pp")
    if gap is None and maint_high is not None and non_high is not None:
        gap = (maint_high - non_high) * 100
    return {
        "raw_maint": maint.get("raw_merge_rate", raw.get("maintainer_merge_rate")),
        "raw_non": non.get("raw_merge_rate", raw.get("non_maintainer_merge_rate")),
        "peer_maint": maint.get("peer_merge_rate"),
        "peer_non": non.get("peer_merge_rate"),
        "self_merge_share_of_maintainer_merges": fair.get("self_merge_share_of_maintainer_merges"),
        "cold_start_merge": cold.get("raw_merge_rate"),
        "established_outsider_merge": established.get("raw_merge_rate"),
        "top20_outsider_merge": top20.get("raw_merge_rate"),
        "large_2k_closed_non_merge": large.get("non_raw_merge"),
        "mean_prep_maint": means.get("maintainer_author_prep"),
        "mean_prep_non": means.get("non_maintainer_author_prep"),
        "high_author_prep_maint_merge": maint_high,
        "high_author_prep_non_merge": non_high,
        "high_author_prep_gap_pp": gap,
        "phase2_concept_ack_gap_pp": concept.get("raw_merge_gap_pp"),
        "phase2_high_prep_test_diff_gap_pp": tests.get("raw_merge_gap_pp"),
        "phase2_ci": phase2.get("ci_status") or "unavailable_on_enriched_corpus",
    }


def _complexity_band(band: Dict[str, Any]) -> Dict[str, Any]:
    reviews = float(band.get("avg_review_count") or 0)
    comments = float(band.get("avg_comment_count") or 0)
    out = dict(band)
    out["msgs"] = reviews + comments
    return out


def ctx_bip(data: Dict[str, Any]) -> Dict[str, Any]:
    champ = data.get("champion_analysis") or {}
    ctx = dict(data)
    ctx["generated_date"] = date.today().isoformat()
    ctx["proposer_analysis"] = dict(data.get("proposer_analysis") or {})
    ctx["proposer_analysis"]["top_proposers"] = _pairs(
        (data.get("proposer_analysis") or {}).get("top_proposers"), 15
    )
    ctx["champion_analysis"] = dict(champ)
    ctx["champion_analysis"]["top_champions"] = _pairs(champ.get("top_champions"), 10)
    return ctx


def ctx_signing(data: Dict[str, Any]) -> Dict[str, Any]:
    conc = data.get("concentration") or {}
    signers = []
    for i, row in enumerate(conc.get("top_signers") or [], start=1):
        item = dict(row)
        item["rank"] = i
        signers.append(item)
    years = data.get("temporal_patterns") or {}
    recent = []
    for year in sorted(years)[-6:]:
        row = dict(years[year])
        row["year"] = year
        recent.append(row)
    return {
        "generated_date": date.today().isoformat(),
        "concentration": {**conc, "top_signers": signers},
        "recent_years": recent,
        "transparency": data.get("transparency") or {},
    }


def ctx_cross_repo(data: Dict[str, Any]) -> Dict[str, Any]:
    port = dict(data.get("power_portability") or {})
    port["bip_top10_joined"] = ", ".join(port.get("bip_top10") or [])
    port["core_top10_joined"] = ", ".join(port.get("core_top10") or [])
    return {
        "generated_date": date.today().isoformat(),
        "actor_overlap": data.get("actor_overlap") or {},
        "governance_comparison": data.get("governance_comparison") or {},
        "power_portability": port,
        "process_comparison": data.get("process_comparison") or {},
    }


def ctx_merge_deputies(data: Dict[str, Any]) -> Dict[str, Any]:
    recent = data.get("recent_2022_plus") or {}
    top5 = recent.get("top5_mergers") or {}
    values = list(top5.values())
    n = recent.get("n_merged_prs") or 1
    top2 = 100.0 * sum(values[:2]) / n if n else 0
    top3 = 100.0 * sum(values[:3]) / n if n else 0
    return {
        "generated_date": date.today().isoformat(),
        "top_merger": data.get("top_merger"),
        "top_merger_share_pct": data.get("top_merger_share_pct"),
        "recent_2022_plus": recent,
        "recent_top2_pct": top2,
        "recent_top3_pct": top3,
        "recent_funnels": (recent.get("authors_funneled_ge_40pct") or [])[:12],
        "recent_coreviewers": dict(
            list((recent.get("top_co_reviewers_on_their_merges") or {}).items())[:10]
        ),
    }


def ctx_stalled(data: Dict[str, Any]) -> Dict[str, Any]:
    proposals = data.get("proposals") or []
    erlay = next((p for p in proposals if p.get("id") == "erlay"), {})
    roles = erlay.get("erlay_by_role") or {}
    full = roles.get("full_or_core_protocol") or {}
    if full:
        outcome = (
            f"Full-protocol Erlay PRs: {full.get('n', 0)} tracked, "
            f"{full.get('n_merged', 0)} merged, "
            f"{full.get('n_closed_unmerged', 0)} closed unmerged, "
            f"{full.get('n_open', 0)} open. Scaffolding merges are not delivery."
        )
    else:
        outcome = "Erlay role split unavailable in this artifact."
    guidance = []
    for row in data.get("fair_cite_guidance") or []:
        if isinstance(row, dict):
            guidance.append(f"{row.get('id')}: {row.get('statement')}")
        else:
            guidance.append(str(row))
    return {
        "generated_date": date.today().isoformat(),
        "version": data.get("version") or "2.1",
        "proposals": proposals,
        "erlay_by_role": {
            k: {
                "n": v.get("n"),
                "merged": v.get("n_merged"),
                "closed_unmerged": v.get("n_closed_unmerged"),
                "open": v.get("n_open"),
            }
            for k, v in roles.items()
            if isinstance(v, dict)
        },
        "erlay_full_protocol_outcome": outcome,
        "fair_cite_guidance": guidance,
    }


def ctx_maintainer(data: Dict[str, Any], sensitivity: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    windows = data.get("windows") or {}
    variants = []
    for name, row in ((sensitivity or {}).get("variants") or {}).items():
        variants.append({"name": name, **row})
    all_view = _window_view(windows.get("all_time") or data)
    y2022 = _window_view(windows.get("from_2022") or {})
    interpretation = (
        "Self-merge drives most of the average-case raw gap "
        f"({_fmt_pct(all_view.get('raw_maint'))} vs {_fmt_pct(all_view.get('raw_non'))} raw; "
        f"{_fmt_pct(all_view.get('peer_maint'))} vs {_fmt_pct(all_view.get('peer_non'))} peer). "
        f"Cold-start first PRs land at {_fmt_pct(all_view.get('cold_start_merge'))} all-time "
        f"({_fmt_pct(y2022.get('cold_start_merge'))} since 2022). "
        f"Established outsiders do comparatively well ({_fmt_pct(all_view.get('established_outsider_merge'))}). "
        f"Closed ≥2k LOC outsider PRs almost never land "
        f"({_fmt_pct(all_view.get('large_2k_closed_non_merge'))} all-time / "
        f"{_fmt_pct(y2022.get('large_2k_closed_non_merge'))} since 2022). "
        "Author-prep matching (body + tests, no reviews) still shows an identity gap; "
        "size_substance is size-heavy and must not be read as quality."
    )
    return {
        "generated_date": date.today().isoformat(),
        "version": data.get("version") or "7.0",
        "n_prs": data.get("n_prs"),
        "n_maintainer_authored": data.get("n_maintainer_authored"),
        "interpretation": interpretation,
        "all": all_view,
        "y2022": y2022,
        "prep_variants": variants,
        "logistic_or_with_prior": ((data.get("controlled_logistic_merge") or {}).get("odds_ratios") or {}).get("is_maintainer"),
        "logistic_or_without_prior": ((data.get("controlled_logistic_merge_without_prior") or {}).get("odds_ratios") or {}).get("is_maintainer"),
    }


def _fmt_pct(value: Any) -> str:
    if value is None:
        return "—"
    return f"{float(value) * 100:.1f}%"


def ctx_importance(data: Dict[str, Any]) -> Dict[str, Any]:
    types = []
    type_data = data.get("type_analysis") or {}
    for name in ("trivial", "low", "normal", "high", "critical"):
        row = dict(type_data.get(name) or {})
        row["name"] = name
        for key in ("zero_review_rate", "maintainer_zero_review_rate"):
            val = row.get(key)
            if isinstance(val, (int, float)) and val > 1:
                row[key] = val / 100.0
        types.append(row)
    critical = next((t for t in types if t["name"] == "critical"), {})
    return {
        "generated_date": date.today().isoformat(),
        "types": types,
        "critical_zero": critical.get("zero_review_rate"),
    }


def ctx_coordination(data: Dict[str, Any]) -> Dict[str, Any]:
    by_c = data.get("by_code_complexity") or {}
    low = _complexity_band(by_c.get("low") or {})
    medium = _complexity_band(by_c.get("medium") or {})
    high = _complexity_band(by_c.get("high") or {})
    low_msgs = low.get("msgs") or 1
    overall = data.get("overall") or {}
    total_prs = sum(float(b.get("count") or 0) for b in (low, medium, high))
    weighted_msgs = (
        sum(float(b.get("count") or 0) * float(b.get("msgs") or 0) for b in (low, medium, high))
        / total_prs
        if total_prs
        else 0
    )
    return {
        "generated_date": date.today().isoformat(),
        "overall": overall,
        "overall_msgs": weighted_msgs,
        "correlation_files_vs_reviews": data.get("correlation_files_vs_reviews"),
        "low": low,
        "medium": medium,
        "high": high,
        "scale_med_vs_low": (medium.get("msgs") or 0) / low_msgs,
        "scale_high_vs_low": (high.get("msgs") or 0) / low_msgs,
        "scale_med_time": (medium.get("avg_decision_time") or 0) / (low.get("avg_decision_time") or 1),
        "scale_high_time": (high.get("avg_decision_time") or 0) / (low.get("avg_decision_time") or 1),
    }


def ctx_contributor(data: Dict[str, Any]) -> Dict[str, Any]:
    summary = data.get("summary") or {}
    total = summary.get("total_contributors") or 0
    authors = data.get("authors") or {}
    participants = data.get("participants_only") or {}
    data_range = data.get("data_range") or {}
    return {
        "generated_date": date.today().isoformat(),
        "summary": summary,
        "activities": data.get("activities") or {},
        "retention": data.get("retention") or {},
        "authors": authors,
        "participants_only": participants,
        "one_time": data.get("one_time") or {},
        "quality": data.get("quality") or {},
        "established_authors": data.get("established_authors") or {},
        "tenure": data.get("tenure") or {},
        "author_share": (authors.get("total") or 0) / total if total else 0,
        "participant_share": (participants.get("total") or 0) / total if total else 0,
        "first_activity": (data_range.get("first_activity") or "")[:10],
        "last_activity": (data_range.get("last_activity") or "")[:10],
        "analysis_date": (data_range.get("analysis_date") or "")[:10],
    }


def _year_table(mapping: Dict[str, Any], min_year: int = 2016) -> List[Dict[str, Any]]:
    rows = []
    for year in sorted(mapping):
        try:
            y = int(year)
        except (TypeError, ValueError):
            continue
        if y < min_year:
            continue
        row = dict(mapping[year])
        row["year"] = y
        rows.append(row)
    return rows


ERA_LABELS = {
    "early_2010s": "Early 2010s (2010–2013)",
    "mid_2010s": "Mid 2010s (2014–2016)",
    "late_2010s": "Late 2010s (2017–2019)",
    "2020s": "2020s (2020+)",
}


def ctx_temporal(data: Dict[str, Any]) -> Dict[str, Any]:
    years = _year_table(data.get("temporal_self_merge") or {})
    eras = []
    for key, stats in (data.get("maintainer_eras") or {}).items():
        row = dict(stats)
        row["label"] = ERA_LABELS.get(key, key)
        row["n_members"] = len(stats.get("members") or [])
        eras.append(row)
    power = []
    for period, stats in (data.get("power_concentration_temporal") or {}).items():
        row = dict(stats)
        row["period"] = period
        power.append(row)
    gini_periods = []
    authors = data.get("authorship_concentration_temporal") or {}
    reviews = data.get("review_concentration_temporal") or {}
    for period in ("historical", "recent", "other"):
        a = authors.get(period) or {}
        r = reviews.get(period) or {}
        if not a and not r:
            continue
        gini_periods.append({
            "period": period,
            "author_gini": a.get("gini_coefficient"),
            "author_top10": a.get("top10_share"),
            "review_gini": r.get("gini_coefficient"),
            "review_top10": r.get("top10_share"),
        })
    conflicts = _year_table(data.get("conflict_resolution_temporal") or {})
    c_total = sum(int(r.get("total_conflicts") or 0) for r in conflicts)
    c_prs = sum(int(r.get("total_prs_in_year") or 0) for r in conflicts)
    return {
        "generated_date": date.today().isoformat(),
        "self_merge_years": years,
        "first_zero": years[0].get("zero_review_self_merge_rate") if years else None,
        "last_zero": years[-1].get("zero_review_self_merge_rate") if years else None,
        "first_reviews": years[0].get("avg_reviews") if years else None,
        "last_reviews": years[-1].get("avg_reviews") if years else None,
        "eras": eras,
        "power_periods": power,
        "gini_periods": gini_periods,
        "conflict_years": conflicts,
        "conflict_total": c_total,
        "conflict_prs": c_prs,
        "conflict_rate": c_total / c_prs if c_prs else 0,
    }


def ctx_merge_pattern(data: Dict[str, Any]) -> Dict[str, Any]:
    sm = data.get("self_merge_breakdown") or {}
    by_rev = sm.get("self_merge_by_reviews") or {}
    friends = []
    friend_rows = ((data.get("merge_relationships") or {}).get("friend_patterns") or [])[:15]
    for i, row in enumerate(friend_rows, start=1):
        item = dict(row)
        item["rank"] = i
        share = row.get("pct_of_author_prs")
        item["share"] = share / 100.0 if isinstance(share, (int, float)) and share > 1 else share
        friends.append(item)
    janitors = ((data.get("merge_relationships") or {}).get("janitor_patterns") or [])[:10]
    individual = data.get("individual_patterns") or {}
    maintainers = (individual.get("maintainers") or [])[:15]
    return {
        "generated_date": date.today().isoformat(),
        "self_merge_breakdown": sm,
        "zero": by_rev.get("zero_reviews") or {},
        "one": by_rev.get("one_review") or {},
        "two": by_rev.get("two_plus_reviews") or {},
        "friends": friends,
        "janitors": janitors,
        "individual_avg": (individual.get("summary") or {}).get("avg_self_merge_rate"),
        "individual_zero_avg": (individual.get("summary") or {}).get("avg_zero_review_self_merge_rate"),
        "maintainers": maintainers,
    }


def ctx_gini(temporal: Dict[str, Any]) -> Dict[str, Any]:
    authors = temporal.get("authorship_concentration_temporal") or {}
    reviews = temporal.get("review_concentration_temporal") or {}
    merges = temporal.get("power_concentration_temporal") or {}
    return {
        "generated_date": date.today().isoformat(),
        "hist_author": authors.get("historical") or {},
        "recent_author": authors.get("recent") or {},
        "hist_review": reviews.get("historical") or {},
        "recent_review": reviews.get("recent") or {},
        "hist_merge": merges.get("historical") or {},
        "recent_merge": merges.get("recent") or {},
    }


def ctx_review_quality(data: Dict[str, Any]) -> Dict[str, Any]:
    trends = data.get("temporal_trends") or {}
    years = []
    for year in sorted(trends):
        try:
            y = int(year)
        except (TypeError, ValueError):
            continue
        if y < 2016:
            continue
        row = dict(trends[year])
        row["year"] = y
        years.append(row)
    sizes = []
    for name, row in (data.get("pr_size_analysis") or {}).items():
        item = dict(row)
        item["name"] = name
        sizes.append(item)
    top = []
    profiles = (data.get("reviewer_profiles") or {}).get("top_by_volume") or {}
    if isinstance(profiles, dict):
        items = list(profiles.items())[:10]
        for name, metrics in items:
            row = dict(metrics)
            row["name"] = name
            row["tag"] = " (maintainer)" if metrics.get("is_maintainer") else ""
            top.append(row)
    return {
        "generated_date": date.today().isoformat(),
        "total_prs": data.get("total_prs"),
        "years": years,
        "first_year": years[0]["year"] if years else "",
        "last_year": years[-1]["year"] if years else "",
        "first_len": years[0].get("avg_body_length") if years else None,
        "last_len": years[-1].get("avg_body_length") if years else None,
        "first_stamp": years[0].get("rubber_stamp_rate") if years else None,
        "last_stamp": years[-1].get("rubber_stamp_rate") if years else None,
        "review_types": data.get("review_types") or {},
        "sizes": sizes,
        "top_reviewers": top,
        "cross_platform": data.get("cross_platform") or {},
    }


def ctx_conflict(temporal: Dict[str, Any], blocs: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    conflicts = _year_table(temporal.get("conflict_resolution_temporal") or {})
    c_total = sum(int(r.get("total_conflicts") or 0) for r in conflicts)
    c_prs = sum(int(r.get("total_prs_in_year") or 0) for r in conflicts)
    days = [r.get("avg_resolution_time_days") or 0 for r in conflicts if r.get("total_conflicts")]
    weighted = 0.0
    weight = 0
    for r in conflicts:
        n = int(r.get("total_conflicts") or 0)
        weighted += n * float(r.get("avg_resolution_time_days") or 0)
        weight += n
    analysis = (blocs or {}).get("bloc_conflict_analysis") or {}
    comparison = analysis.get("comparison") or {}
    conflict_side = comparison.get("conflict_prs") or {}
    non = comparison.get("non_conflict_prs") or {}
    top = ((analysis.get("conflict_bloc_analysis") or {}).get("top_blocs") or [])[:8]
    return {
        "generated_date": date.today().isoformat(),
        "conflict_years": conflicts,
        "conflict_total": c_total,
        "conflict_prs": c_prs,
        "conflict_rate": c_total / c_prs if c_prs else 0,
        "avg_resolution": weighted / weight if weight else 0,
        "conflict_cohesion": conflict_side.get("avg_cohesion"),
        "conflict_strong": conflict_side.get("strong_blocs_count"),
        "nonconflict_cohesion": non.get("avg_cohesion"),
        "nonconflict_strong": non.get("strong_blocs_count"),
        "top_blocs": top,
    }


def ctx_interdisciplinary(data: Dict[str, Any]) -> Dict[str, Any]:
    ctx = dict(data)
    ctx["generated_date"] = date.today().isoformat()
    coalitions = (data.get("coalition_formation") or {}).get("top_coalitions") or []
    ctx.setdefault("coalition_formation", data.get("coalition_formation") or {})
    ctx["coalition_formation"] = dict(ctx["coalition_formation"])
    ctx["coalition_formation"]["top_coalitions"] = coalitions[:8]
    return ctx


def ctx_novel(data: Dict[str, Any]) -> Dict[str, Any]:
    recip = data.get("review_reciprocity") or {}
    top = []
    pairs = recip.get("top_pairs") or recip.get("reciprocal_pairs") or []
    if isinstance(pairs, dict):
        top = [{"pair": k, "count": v} for k, v in list(pairs.items())[:8]]
    elif isinstance(pairs, list):
        for row in pairs[:8]:
            if not isinstance(row, dict):
                continue
            pair = row.get("pair")
            if isinstance(pair, (list, tuple)) and len(pair) >= 2:
                pair_label = f"{pair[0]} / {pair[1]}"
            else:
                pair_label = pair or f"{row.get('a')}/{row.get('b')}"
            top.append({"pair": pair_label, "count": row.get("count") or row.get("total")})
    hierarchy = data.get("power_hierarchy") or {}
    return {
        "generated_date": date.today().isoformat(),
        "behavioral_clusters": data.get("behavioral_clusters") or {},
        "power_hierarchy": {"hierarchy": (hierarchy.get("hierarchy") or [])[:8]},
        "reciprocity_top": top,
    }


ERA_FLOW_LABELS = {
    "early_2010_2014": "Early (2010–2014)",
    "scaling_segwit_2015_2017": "SegWit (2015–2017)",
    "taproot_2018_2021": "Taproot (2018–2021)",
    "modern_2022_plus": "2022+",
}


def ctx_frames(data: Dict[str, Any]) -> Dict[str, Any]:
    eras = []
    for key, stats in ((data.get("agenda_setting") or {}).get("by_era") or {}).items():
        row = dict(stats)
        row["label"] = ERA_FLOW_LABELS.get(key, key)
        eras.append(row)
    mux = dict(data.get("multiplex_identity") or {})
    overlap = mux.get("overlapping_detail") or []
    overlap_joined = ", ".join(
        f"**{row.get('actor')}** ({row.get('bip_power')} BIP → {row.get('core_power')} Core)"
        for row in overlap
        if isinstance(row, dict)
    )
    return {
        "generated_date": date.today().isoformat(),
        "agenda_setting": data.get("agenda_setting") or {},
        "informal_org_chart": data.get("informal_org_chart") or {},
        "multiplex_identity": mux,
        "exit_as_selection": data.get("exit_as_selection") or {},
        "eras": eras,
        "bip_top10_joined": ", ".join(mux.get("bip_top10") or []),
        "core_top10_joined": ", ".join(mux.get("core_top10") or []),
        "overlap_joined": overlap_joined or "—",
    }


def ctx_archive_gems(data: Dict[str, Any]) -> Dict[str, Any]:
    rows = []
    for g in data.get("gems") or []:
        quote = (g.get("quote") or "").replace("|", "/")
        if len(quote) < 60:
            continue
        if "following sections might be updated" in quote.lower():
            continue
        rows.append(
            {
                "era": g.get("era") or "",
                "frame": g.get("frame") or "",
                "pr": g.get("pr") if g.get("pr") is not None else "—",
                "quote_short": quote[:220] + ("…" if len(quote) > 220 else ""),
            }
        )
        if len(rows) >= 24:
            break
    return {
        "generated_date": date.today().isoformat(),
        "method": data.get("method"),
        "n_candidates": data.get("n_candidates"),
        "n_gems": data.get("n_gems"),
        "gems": rows,
    }


def ctx_language(data: Dict[str, Any]) -> Dict[str, Any]:
    trends = ((data.get("terminology_evolution") or {}).get("terminology_trends") or {})
    terms = []
    for term, row in sorted(trends.items(), key=lambda kv: -(kv[1].get("total_mentions") or 0)):
        item = dict(row)
        item["term"] = term
        terms.append(item)
    early = []
    adopters = ((data.get("language_adoption") or {}).get("early_adopters") or {})
    for term, row in list(adopters.items())[:12]:
        users = ", ".join(
            f"{u.get('author')} ({u.get('platform')})"
            for u in (row.get("early_users") or [])[:3]
        )
        early.append({"term": term, "first_year": row.get("first_year"), "users": users})
    return {
        "generated_date": date.today().isoformat(),
        "source_counts": data.get("source_counts") or {},
        "terms": terms,
        "early": early,
    }


def _write(name: str, text: str, findings: Path) -> Path:
    out = findings / name
    out.write_text(text, encoding="utf-8")
    logger.info("Wrote %s", out)
    return out


def generate_all() -> List[str]:
    analysis = get_analysis_dir() / "findings" / "data"
    findings_data = get_findings_dir() / "data"
    findings = get_findings_dir()
    written: List[str] = []

    jobs: List[Tuple[str, Path, Dict[str, Any]]] = []

    bip = _maybe(analysis / "bip_analysis.json")
    if bip:
        jobs.append(("BIP_PROCESS_ANALYSIS.md", TEMPLATES / "BIP_PROCESS_ANALYSIS.md.tpl", ctx_bip(bip)))

    signing = _maybe(analysis / "release_signing.json")
    if signing:
        jobs.append(
            ("RELEASE_SIGNING_ANALYSIS.md", TEMPLATES / "RELEASE_SIGNING_ANALYSIS.md.tpl", ctx_signing(signing))
        )

    cross = _maybe(analysis / "cross_repo_comparison.json")
    if cross:
        jobs.append(
            ("CROSS_REPO_COMPARISON.md", TEMPLATES / "CROSS_REPO_COMPARISON.md.tpl", ctx_cross_repo(cross))
        )

    deputies = (
        _maybe(findings_data / "high_volume_merger_deputies.json")
        or _maybe(analysis / "high_volume_merger_deputies.json")
    )
    if not deputies:
        merge_src = _maybe(findings_data / "merge_pattern_analysis.json") or _maybe(
            analysis / "merge_pattern_analysis.json"
        )
        if merge_src:
            deputies = (merge_src.get("merge_relationships") or {}).get(
                "high_volume_merger_deputies"
            ) or merge_src.get("high_volume_merger_deputies")
    if deputies:
        jobs.append(
            (
                "MERGE_CONCENTRATION_DEPUTIES_REPORT.md",
                TEMPLATES / "MERGE_CONCENTRATION_DEPUTIES_REPORT.md.tpl",
                ctx_merge_deputies(deputies),
            )
        )

    stalled = _maybe(findings_data / "stalled_proposal_dossiers.json")
    if stalled:
        jobs.append(
            (
                "STALLED_PROPOSALS_REPORT.md",
                TEMPLATES / "STALLED_PROPOSALS_REPORT.md.tpl",
                ctx_stalled(stalled),
            )
        )

    premium = _maybe(findings_data / "maintainer_premium.json")
    if premium:
        jobs.append(
            (
                "MAINTAINER_PREMIUM_REPORT.md",
                TEMPLATES / "MAINTAINER_PREMIUM_REPORT.md.tpl",
                ctx_maintainer(premium, _maybe(findings_data / "author_prep_sensitivity.json")),
            )
        )

    importance = _maybe(findings_data / "pr_importance_matrix.json") or _maybe(
        analysis / "pr_importance_matrix.json"
    )
    if importance:
        jobs.append(
            (
                "PR_IMPORTANCE_ANALYSIS.md",
                TEMPLATES / "PR_IMPORTANCE_ANALYSIS.md.tpl",
                ctx_importance(importance),
            )
        )

    coord = _maybe(analysis / "complexity_correlation.json") or _maybe(findings_data / "complexity_correlation.json")
    if coord:
        jobs.append(
            (
                "COORDINATION_COSTS_ANALYSIS.md",
                TEMPLATES / "COORDINATION_COSTS_ANALYSIS.md.tpl",
                ctx_coordination(coord),
            )
        )

    contrib = _maybe(analysis / "contributor_analysis.json")
    if contrib:
        jobs.append(
            (
                "CONTRIBUTOR_ANALYSIS.md",
                TEMPLATES / "CONTRIBUTOR_ANALYSIS.md.tpl",
                ctx_contributor(contrib),
            )
        )

    temporal = _maybe(analysis / "temporal_analysis.json") or _maybe(findings_data / "temporal_analysis.json")
    if temporal:
        jobs.append(
            ("TEMPORAL_ANALYSIS_REPORT.md", TEMPLATES / "TEMPORAL_ANALYSIS_REPORT.md.tpl", ctx_temporal(temporal))
        )
        jobs.append(
            ("GINI_COEFFICIENT_EXPLANATION.md", TEMPLATES / "GINI_COEFFICIENT_EXPLANATION.md.tpl", ctx_gini(temporal))
        )

    merge = _maybe(findings_data / "merge_pattern_analysis.json") or _maybe(analysis / "merge_pattern_analysis.json")
    if merge:
        jobs.append(
            ("MERGE_PATTERN_BREAKDOWN.md", TEMPLATES / "MERGE_PATTERN_BREAKDOWN.md.tpl", ctx_merge_pattern(merge))
        )

    review_q = _maybe(findings_data / "review_quality_enhanced.json") or _maybe(analysis / "review_quality_enhanced.json")
    if review_q:
        xref = _maybe(findings_data / "cross_platform_reviews.json") or _maybe(analysis / "cross_platform_reviews.json") or {}
        channels = xref.get("channels") or {}
        review_q["cross_platform"] = {
            "unique_prs_mentioned": xref.get("unique_prs_mentioned") or 0,
            "channel_rows": [
                {
                    "name": name,
                    "prs": (row or {}).get("prs_with_discussion") or 0,
                    "messages": (row or {}).get("messages") or 0,
                }
                for name, row in channels.items()
            ],
        }
        jobs.append(
            (
                "REVIEW_QUALITY_ENHANCED_ANALYSIS.md",
                TEMPLATES / "REVIEW_QUALITY_ENHANCED_ANALYSIS.md.tpl",
                ctx_review_quality(review_q),
            )
        )

    blocs = _maybe(analysis / "voting_bloc_conflict.json") or _maybe(findings_data / "voting_bloc_conflict.json")
    if temporal:
        jobs.append(
            (
                "CONFLICT_RESOLUTION_ANALYSIS.md",
                TEMPLATES / "CONFLICT_RESOLUTION_ANALYSIS.md.tpl",
                ctx_conflict(temporal, blocs),
            )
        )

    inter = _maybe(analysis / "interdisciplinary_analysis.json") or _maybe(findings_data / "interdisciplinary_analysis.json")
    if inter:
        jobs.append(
            (
                "INTERDISCIPLINARY_ANALYSIS_REPORT.md",
                TEMPLATES / "INTERDISCIPLINARY_ANALYSIS_REPORT.md.tpl",
                ctx_interdisciplinary(inter),
            )
        )

    novel = _maybe(findings_data / "novel_interpretations.json") or _maybe(analysis / "novel_interpretations.json")
    if novel:
        jobs.append(
            ("NOVEL_INTERPRETATIONS.md", TEMPLATES / "NOVEL_INTERPRETATIONS.md.tpl", ctx_novel(novel))
        )

    lang = _maybe(analysis / "language_evolution.json") or _maybe(findings_data / "language_evolution.json")
    if lang:
        jobs.append(("LANGUAGE_EVOLUTION.md", TEMPLATES / "LANGUAGE_EVOLUTION.md.tpl", ctx_language(lang)))

    frames = _maybe(analysis / "governance_frames.json") or _maybe(findings_data / "governance_frames.json")
    if frames:
        jobs.append(("GOVERNANCE_FRAMES.md", TEMPLATES / "GOVERNANCE_FRAMES.md.tpl", ctx_frames(frames)))

    gems = _maybe(analysis / "archive_gems.json") or _maybe(findings_data / "archive_gems.json")
    if gems:
        jobs.append(
            ("ARCHIVE_GEMS_INDEX.md", TEMPLATES / "ARCHIVE_GEMS.md.tpl", ctx_archive_gems(gems))
        )

    for name, tpl, ctx in jobs:
        if not tpl.exists():
            logger.warning("Missing template %s", tpl)
            continue
        _write(name, render_file(tpl, ctx), findings)
        written.append(name)
    return written


def main() -> int:
    written = generate_all()
    print(f"Generated {len(written)} reports: {', '.join(written)}")
    return 0 if written else 1


if __name__ == "__main__":
    sys.exit(main())
