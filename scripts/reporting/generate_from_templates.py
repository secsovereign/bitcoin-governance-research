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

from pass_validation import validate_all
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
    catalog = dict(data.get("dump_catalog") or {})
    catalog.setdefault("status", [])
    catalog.setdefault("type", [])
    catalog.setdefault("layer", [])
    catalog.setdefault("prs", {})
    catalog.setdefault("issues", {})
    ctx["dump_catalog"] = catalog
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


def _ledger_cell(value: Any) -> str:
    """Flatten ledger lists/empties for the one-level template engine."""
    if value is None or value == "" or value == []:
        return "—"
    if isinstance(value, list):
        parts: List[str] = []
        for item in value:
            if isinstance(item, dict):
                parts.append(
                    str(
                        item.get("text")
                        or item.get("passage_id")
                        or item.get("canonical_key")
                        or item.get("phrase")
                        or ""
                    )
                )
            else:
                parts.append(str(item))
        joined = ", ".join(p for p in parts if p)
        return joined or "—"
    return str(value)


def _flatten_episode(row: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(row)
    for key in (
        "venue",
        "outcome",
        "parent_episode",
        "technical_objections",
        "process_objections",
        "corpus_cites",
        "existing_findings",
        "github_anchors",
    ):
        out[key] = _ledger_cell(row.get(key))
    return out


def _flatten_stall(row: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(row)
    for key in (
        "first_proposed",
        "last_activity",
        "stated_reason_for_stall",
        "nack_source",
        "corpus_cites",
        "existing_findings",
    ):
        out[key] = _ledger_cell(row.get(key))
    out["nack_exists"] = row.get("nack_exists") or "unknown"
    return out


def _flatten_phrase(row: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(row)
    out["episode_ids"] = _ledger_cell(row.get("episode_ids"))
    out["corpus_cites"] = _ledger_cell(row.get("corpus_cites"))
    out["count"] = row.get("count")
    return out


def _flatten_contributor(row: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(row)
    out["canonical_key"] = row.get("canonical_key") or "—"
    out["github_handle"] = row.get("github_handle") or "—"
    out["episodes_involved"] = _ledger_cell(row.get("episodes_involved"))
    out["episode_roles"] = _ledger_cell(row.get("episode_roles"))
    out["corpus_cites"] = _ledger_cell(row.get("corpus_cites"))
    return out


def ctx_episode_ledger(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "generated_date": date.today().isoformat(),
        "pin": data.get("pin") or "",
        "episodes": [_flatten_episode(row) for row in (data.get("episodes") or [])],
        "agreement_stalls": [_flatten_stall(row) for row in (data.get("agreement_stalls") or [])],
        "phrases": [_flatten_phrase(row) for row in (data.get("phrases") or [])],
        "contributors": [_flatten_contributor(row) for row in (data.get("contributors") or [])],
        "contributor_count": len(data.get("contributors") or []),
    }


def ctx_revealed_consensus(data: Dict[str, Any]) -> Dict[str, Any]:
    all_w = data.get("windows", {}).get("all_time") or {}
    pre2016 = data.get("windows", {}).get("before_2016") or {}
    y2016 = data.get("windows", {}).get("from_2016") or {}
    y2022 = data.get("windows", {}).get("from_2022") or {}
    path = all_w.get("by_path_risk") or {}
    rows = []
    for band in (
        "consensus_sensitive",
        "networking",
        "security_sensitive",
        "other",
        "unknown",
    ):
        pair = path.get(band) or {}
        merged = pair.get("merged") or {}
        closed = pair.get("closed_unmerged") or {}
        mr = merged.get("rates") or {}
        cr = closed.get("rates") or {}
        rows.append(
            {
                "band": band,
                "merged_n": merged.get("n"),
                "merged_zero": mr.get("zero_reviews"),
                "merged_keys_ack": mr.get("at_least_one_merge_keys_ack"),
                "merged_nack": mr.get("has_nack"),
                "closed_n": closed.get("n"),
                "closed_nack": cr.get("has_nack"),
            }
        )
    return {
        "generated_date": date.today().isoformat(),
        "version": data.get("version") or "1.0",
        "pin": data.get("pin") or "",
        "all": all_w,
        "pre2016": pre2016,
        "y2016": y2016,
        "y2022": y2022,
        "path_rows": rows,
        "coverage_reviews": (data.get("coverage") or {}).get("github_reviews_api") or "",
        "coverage_path": (data.get("coverage") or {}).get("path_risk") or "",
        "informal_index": data.get("informal_index") or {},
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


def _fmt(value: Any, digits: int = 3) -> str:
    if value is None or isinstance(value, bool):
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    if number != number:
        return "—"
    return f"{number:.{digits}f}"


def _pct(value: Any) -> str:
    if value is None or isinstance(value, bool):
        return "—"
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return "—"


def _pp(value: Any) -> str:
    if value is None or isinstance(value, bool):
        return "—"
    try:
        return f"{float(value) * 100:.1f} percentage points"
    except (TypeError, ValueError):
        return "—"


def _ci(ci: Any) -> str:
    if not isinstance(ci, list) or len(ci) != 2:
        return "—"
    return f"{_fmt(ci[0])} to {_fmt(ci[1])}"


def _ci_pp(ci: Any) -> str:
    if not isinstance(ci, list) or len(ci) != 2:
        return "—"
    try:
        return f"{float(ci[0]) * 100:.1f} to {float(ci[1]) * 100:.1f} percentage points"
    except (TypeError, ValueError):
        return "—"


def _rate_block(block: Dict[str, Any]) -> Dict[str, Any]:
    comp = (block or {}).get("comparison") or {}
    inn = comp.get("in_group") if isinstance(comp.get("in_group"), dict) else {}
    out = comp.get("out_group") if isinstance(comp.get("out_group"), dict) else {}
    diff = comp.get("difference_in_minus_out") if isinstance(comp.get("difference_in_minus_out"), dict) else {}
    return {"in": inn, "out": out, "diff": diff}


def _sentences(value: Any) -> List[Dict[str, str]]:
    if isinstance(value, list):
        return [{"text": str(item)} for item in value]
    if isinstance(value, str) and value.strip():
        return [{"text": value.strip()}]
    return []


def ctx_ingroup(data: Dict[str, Any]) -> Dict[str, Any]:
    blocks = (data.get("blocks") or {}).get("A") or {}
    merge = _rate_block(blocks.get("1_merge_rate") or {})
    silence = _rate_block(blocks.get("3b_no_peer_response_rate") or {})
    tone = _rate_block(blocks.get("2_mean_sentiment") or {})
    hours = _rate_block(blocks.get("3_time_to_first_response_hours") or {})
    mech = data.get("mechanism_disambiguation") or {}
    scores = mech.get("scores") or {}
    params = data.get("parameters") or {}
    sources = data.get("data_sources") or {}
    return {
        "generated_date": date.today().isoformat(),
        "pin": data.get("pin") or "",
        "top_n": params.get("top_n"),
        "defined_from": sources.get("ingroup_defined_from") or "—",
        "headline_window": params.get("headline_window") or "—",
        "n_prs": sources.get("n_prs_used"),
        "merge_in": _pct(merge["in"].get("estimate")),
        "merge_out": _pct(merge["out"].get("estimate")),
        "merge_gap": _pp(merge["diff"].get("estimate")),
        "merge_ci": _ci_pp(merge["diff"].get("ci95")),
        "silence_in": _pct(silence["in"].get("estimate")),
        "silence_out": _pct(silence["out"].get("estimate")),
        "silence_gap": _pp(silence["diff"].get("estimate")),
        "tone_in": _fmt(tone["in"].get("estimate")),
        "tone_out": _fmt(tone["out"].get("estimate")),
        "tone_gap": _fmt(tone["diff"].get("estimate")),
        "hours_in": _fmt(hours["in"].get("estimate"), 1),
        "hours_out": _fmt(hours["out"].get("estimate"), 1),
        "hours_gap": _fmt(hours["diff"].get("estimate"), 1),
        "score_filter": scores.get("active_social_filtering"),
        "score_dropout": scores.get("passive_dropout"),
        "score_access": scores.get("structural_access_asymmetry"),
        "resemblance": mech.get("resemblance") or "—",
        "unmet": _sentences(mech.get("conditions_not_met_or_unknown")),
        "cannot": _sentences(data.get("what_this_cannot_prove")),
    }


def ctx_newcomer(data: Dict[str, Any]) -> Dict[str, Any]:
    slope = (data.get("period_trend") or {}).get("merge_rate_slope_per_year") or {}
    draw = data.get("drawbridge") or {}
    interactions = {row.get("outcome"): row for row in (draw.get("interaction") or []) if isinstance(row, dict)}
    merge_x = interactions.get("merge") or {}
    silence_x = interactions.get("no_response") or {}
    capacity = (data.get("review_capacity") or {}).get("correlation_prs_per_reviewer_with_newcomer_no_response") or {}
    raw = (data.get("year_controlled_group_gap") or {}).get("without_year_fixed_effects") or {}
    year = (data.get("year_controlled_group_gap") or {}).get("with_year_fixed_effects") or {}
    cohort = data.get("cohort_control") or {}
    two = cohort.get("two_year_cohorts") or {}
    supported = (data.get("interpretation") or {}).get("supported") or []
    return {
        "generated_date": date.today().isoformat(),
        "pin": data.get("pin") or "",
        "supported": ", ".join(supported) or "none",
        "merge_slope": _pp(slope.get("estimate")),
        "merge_slope_ci": _ci_pp(slope.get("ci95")),
        "incumbent_slope": _pp((draw.get("incumbent_merge_slope") or {}).get("slope_merge_rate_per_year")),
        "newcomer_slope": _pp((draw.get("newcomer_merge_slope") or {}).get("slope_merge_rate_per_year")),
        "merge_interaction": _pp(merge_x.get("interaction_per_year")),
        "merge_interaction_ci": _ci_pp(merge_x.get("ci95")),
        "silence_interaction": _pp(silence_x.get("interaction_per_year")),
        "silence_interaction_ci": _ci_pp(silence_x.get("ci95")),
        "capacity_r": _fmt(capacity.get("pearson_r")),
        "capacity_ci": _ci(capacity.get("ci95")),
        "capacity_years": capacity.get("n_years"),
        "logit_raw": _fmt(raw.get("in_group_log_odds")),
        "or_raw": _fmt(raw.get("odds_ratio"), 2),
        "logit_year": _fmt(year.get("in_group_log_odds")),
        "or_year": _fmt(year.get("odds_ratio"), 2),
        "logit_year_ci": _ci(year.get("ci95_log_odds")),
        "logit_n": year.get("n"),
        "cohort_d": _fmt(two.get("pooled_cohens_d"), 2),
        "rolling_n": (data.get("rolling_ingroup") or {}).get("n_ever_entered"),
        "fraction_remaining": _pct(cohort.get("fraction_of_raw_merge_gap_remaining_after_two_year_fe")),
        "cohort_fe_gap": _pp((cohort.get("cohort_fe_merge_rate_two_year") or {}).get("estimate")),
    }


PRINCIPLE_LABELS = {
    "P1": "P1 boundaries",
    "P2": "P2 congruence",
    "P3": "P3 collective choice",
    "P4": "P4 monitoring",
    "P5": "P5 sanctions",
    "P6": "P6 conflict resolution",
    "P7": "P7 organizing rights",
    "P8": "P8 nested decisions",
}
SUBSYSTEM_COLUMNS = ("consensus", "core", "wallet", "p2p", "rpc", "gui", "test", "docs", "build", "other")


def _md_table(headers: List[str], rows: List[List[str]]) -> str:
    head = "| " + " | ".join(headers) + " |"
    rule = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([head, rule, *body])


def _cell_map(gap: Dict[str, Any]) -> Dict[Tuple[int, str], Dict[str, Any]]:
    found: Dict[Tuple[int, str], Dict[str, Any]] = {}
    for cell in gap.get("subsystem_year_cells") or []:
        found[(int(cell["year"]), str(cell["subsystem"]))] = cell
    return found


def _endpoint(cells: Dict[Tuple[int, str], Dict[str, Any]], year: int, subsystem: str, field: str, digits: int = 0) -> str:
    cell = cells.get((year, subsystem))
    if not cell:
        return "—"
    value = cell.get(field)
    if field == "silence_rate":
        return _pct(value) if value is not None else "—"
    if value is None:
        return "—"
    if digits:
        return _fmt(value, digits)
    return str(int(value))


def ctx_commons(data: Dict[str, Any], confirmed: List[Dict[str, Any]], gap: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    effects = []
    for row in confirmed:
        note = str(row.get("note") or "").replace("\n", " ").strip()
        effects.append({
            "id": row.get("id"),
            "estimate": _fmt(row.get("estimate")),
            "ci": _ci(row.get("ci95")),
            "q": _fmt(row.get("q")),
            "holdout": _fmt(row.get("holdout_estimate")),
            "n": row.get("n"),
            "note": note[:420],
        })
    ranks = []
    bitcoin_full_health = "—"
    bitcoin_full_principles = "—"
    for row in data.get("cross_repo_ranking") or []:
        if not row.get("ranked"):
            continue
        if row.get("repo") == "bitcoin/bitcoin":
            bitcoin_full_health = _fmt(row.get("full_profile_health"), 2)
            bitcoin_full_principles = _fmt(row.get("full_profile_principle_score"), 2)
        ranks.append({
            "repo": row.get("repo"),
            "health": _fmt(row.get("mean_health"), 2),
            "principles": _fmt(row.get("mean_principle_score"), 2),
            "years": row.get("n_years"),
            "full_health": _fmt(row.get("full_profile_health"), 2),
            "full_principles": _fmt(row.get("full_profile_principle_score"), 2),
        })
    return {
        "generated_date": date.today().isoformat(),
        "pin": data.get("pin") or "",
        "effects": effects,
        "ranks": ranks,
        "bitcoin_full_health": bitcoin_full_health,
        "bitcoin_full_principles": bitcoin_full_principles,
        "cannot": _sentences(data.get("what_this_cannot_prove")),
        **_commons_followup(gap),
    }


def _commons_followup(gap: Optional[Dict[str, Any]]) -> Dict[str, str]:
    if not gap:
        return {
            "lag_text": "The lagged principle test is not in the findings data.",
            "cross_repo_text": "The cross-repository rerun of the six effects is not in the findings data.",
        }
    principles = (gap.get("principles") or {}).get("principles") or {}
    p6 = ((principles.get("P6") or {}).get("lagged_health") or {}).get("t_plus_1") or {}
    p8 = ((principles.get("P8") or {}).get("lagged_health") or {}).get("t_plus_1") or {}
    lag_text = (
        f"On bitcoin/bitcoin, the conflict-resolution score (P6) in year t has Spearman r={_fmt(p6.get('estimate'))} "
        f"with the health index in t+1 (n={p6.get('n')}, interval {_ci(p6.get('ci95'))}, q={_fmt(p6.get('q'))}). "
        f"That is the only positive lag that clears the passes 1–5 threshold. It is LOW POWER. "
        f"The nested-decision score (P8) runs the other way: r={_fmt(p8.get('estimate'))}, q={_fmt(p8.get('q'))}. "
        "P5 and P7 have no scored year. 2024–2026 does not contain enough pairs to confirm the lags."
    )
    cross = gap.get("cross_repo") or {}
    n_repos = len(cross.get("rows") or [])
    cross_repo_text = (
        f"{n_repos} comparison repositories have at least seven years of history. "
        "Their pull-request dumps store author, title, body, timestamps, merged state, and comments_count. "
        "Review objects, comment authors, file paths, and meeting lists are absent, so E2, E3, E5, E7, E9, and E12 "
        "are DATA UNAVAILABLE on every one of them. The Spearman correlation of effect size with health is "
        "DATA UNAVAILABLE. Whether those effects are specific to poorly governed repositories or ambient to "
        "open source development is not identified. The Bitcoin Core row in the effect list above is the reference."
    )
    return {"lag_text": lag_text, "cross_repo_text": cross_repo_text}


def _trajectory_followup(gap: Optional[Dict[str, Any]]) -> Dict[str, str]:
    if not gap:
        return {
            "followup_fn": "The false-negative timeline is not in the findings data.",
            "followup_silence": "The subsystem silence test is not in the findings data.",
        }
    fn = gap.get("false_negative_timeline") or {}
    slope = fn.get("slope") or {}
    sub = gap.get("subsystem_silence") or {}
    models = sub.get("models") or {}
    followup_fn = (
        f"The {fn.get('n_false_negative')} patch-content leavers are classified {fn.get('classification')}. "
        f"{_pct(fn.get('share_before_2018'))} entered before 2018 and {_pct(fn.get('share_2018_or_later'))} entered in 2018 or later. "
        f"The false-negative rate changes by {_pp(slope.get('estimate'))} per year of entry "
        f"(interval {_ci_pp(slope.get('ci95'))}, q={_fmt(slope.get('q'))}). "
        "The positive-slope test does not clear the threshold, so the filter is present across the whole series."
    )
    followup_silence = (
        f"Subsystem reviewer capacity is classified {sub.get('classification')}. "
        f"On newcomer pull requests in the review-object era, silence rises {_pp(models.get('year_slope_without_reviewers'))} per year "
        f"before the subsystem's active-reviewer count and {_pp(models.get('year_slope_with_reviewers'))} per year after it. "
        "The slope widens. Those figures are percentage points per calendar year. "
        "They are a different scale from the standardized coefficients 0.014 and 0.039 above."
    )
    return {"followup_fn": followup_fn, "followup_silence": followup_silence}


def ctx_trajectory(data: Dict[str, Any], rows: List[Dict[str, Any]], gap: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    dec = data.get("decomposition") or {}
    ci = dec.get("ci95") or {}
    fn = data.get("false_negatives") or {}
    content = fn.get("content_only") or {}
    groups = data.get("groups") or {}
    params = data.get("parameters") or {}
    capacity = data.get("capacity") or {}
    year = capacity.get("year_coefficient") or {}
    usable = []
    withheld = []
    for row in rows:
        view = {
            "id": row.get("id"),
            "g1_mean": _fmt(row.get("g1_mean"), 2),
            "g2_mean": _fmt(row.get("g2_mean"), 2),
            "g1_median": _fmt(row.get("g1_median"), 2),
            "g2_median": _fmt(row.get("g2_median"), 2),
            "gap": _fmt(row.get("gap"), 3),
            "d": _fmt(row.get("cohens_d"), 2),
            "smd": _fmt(row.get("smd"), 2),
            "q": _fmt(row.get("q"), 3),
            "flag": row.get("flag") or "—",
            "holdout": row.get("holdout_same_sign"),
            "n_g1": row.get("n_g1"),
            "n_g2": row.get("n_g2"),
            "note": row.get("note") or "",
        }
        if row.get("usable"):
            usable.append(view)
        elif row.get("note"):
            withheld.append(view)
    return {
        "generated_date": date.today().isoformat(),
        "pin": data.get("pin") or "",
        "n_g1": groups.get("n_g1"),
        "n_g2": groups.get("n_g2"),
        "reference_d": _fmt(params.get("pass2_reference_d"), 2),
        "d_raw": _fmt(dec.get("d_raw"), 2),
        "d_raw_ci": _ci(ci.get("d_raw")),
        "d_size": _fmt(dec.get("d_after_size_controls"), 2),
        "d_content": _fmt(dec.get("d_after_patch_content"), 2),
        "d_content_ci": _ci(ci.get("d_after_patch_content")),
        "d_reception": _fmt(dec.get("d_after_review_reception"), 2),
        "d_reception_ci": _ci(ci.get("d_after_review_reception")),
        "d_s": _fmt(dec.get("d_after_S"), 2),
        "d_s_ci": _ci(ci.get("d_after_S")),
        "d_both": _fmt(dec.get("d_after_both"), 2),
        "rule_text": (dec.get("rule") or {}).get("text") or "",
        "usable": usable,
        "withheld": withheld,
        "fn_full": fn.get("n_false_negative"),
        "fn_g2": fn.get("n_g2"),
        "fn_full_s": _fmt(fn.get("s_difference"), 2),
        "fn_full_d": _fmt(fn.get("cohens_d"), 2),
        "fn_content": content.get("n_false_negative"),
        "fn_content_s": _fmt(content.get("s_difference"), 2),
        "fn_content_d": _fmt(content.get("cohens_d"), 2),
        "fn_content_flag": content.get("effect_size_flag") or "—",
        "silence_predictors": ", ".join(capacity.get("predictors_with_q_below_05") or []) or "none",
        "year_without": _fmt(year.get("standardized_year_without_S"), 3),
        "year_with": _fmt(year.get("standardized_year_with_S"), 3),
        "cannot": _sentences(data.get("what_this_cannot_prove")),
        **_trajectory_followup(gap),
    }


def ctx_gap(gap: Dict[str, Any]) -> Dict[str, Any]:
    principles = gap.get("principles") or {}
    blocks = principles.get("principles") or {}
    principle_rows = []
    series = []
    timeseries = gap.get("principle_health_timeseries") or {}
    for key in ("P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"):
        block = blocks.get(key) or {}
        decline = block.get("largest_decline") or {}
        lags = block.get("lagged_health") or {}
        t1 = lags.get("t_plus_1") or {}
        t2 = lags.get("t_plus_2") or {}
        label = PRINCIPLE_LABELS.get(key, key)
        if decline.get("status") == "ok":
            drop = f"{decline.get('year')}"
            score = _fmt(decline.get("score"))
            before = f"{decline.get('year_before')} ({_fmt(decline.get('score_year_before'))})"
            after_score = decline.get("score_year_after")
            after = f"{decline.get('year_after')} ({_fmt(after_score)})" if after_score is not None else "—"
        else:
            drop, score, before, after = "DATA UNAVAILABLE", "—", "—", "—"
        power = " LOW POWER" if t1.get("low_power") else ""
        principle_rows.append({
            "label": label,
            "decline": drop,
            "score": score,
            "before": before,
            "after": after,
            "r1": _fmt(t1.get("estimate")),
            "ci1": _ci(t1.get("ci95")),
            "q1": (_fmt(t1.get("q")) + power) if t1.get("estimate") is not None else "—",
            "r2": _fmt(t2.get("estimate")),
            "q2": _fmt(t2.get("q")),
        })
        rows = []
        for point in timeseries.get(key) or []:
            if point.get("score") is None:
                continue
            rows.append([
                str(point.get("year")),
                _fmt(point.get("score")),
                _fmt(point.get("health")),
                _fmt(point.get("health_next_year")),
            ])
        if rows:
            series.append({
                "label": label,
                "table": _md_table(["Year", "Score", "Health", "Health next year"], rows),
            })
    def _pair(items: Any) -> str:
        names = list(items or [])
        if len(names) == 2:
            return f"{names[0]} and {names[1]}"
        return ", ".join(names)

    p6 = ((blocks.get("P6") or {}).get("lagged_health") or {}).get("t_plus_1") or {}
    p6_lag2 = ((blocks.get("P6") or {}).get("lagged_health") or {}).get("t_plus_2") or {}
    principle_lead = (
        f"Ranked by the t+1 correlation, the top two are {_pair(principles.get('load_bearing_principles'))} "
        f"and the bottom two are {_pair(principles.get('least_associated_principles'))}. "
        f"A positive correlation means a lower score in year t lines up with a lower health index in t+1. "
        f"P6 is r={_fmt(p6.get('estimate'))} (n={p6.get('n')}, interval {_ci(p6.get('ci95'))}, q={_fmt(p6.get('q'))}). "
        f"The t+2 correlation is r={_fmt(p6_lag2.get('estimate'))}, q={_fmt(p6_lag2.get('q'))}. "
        "P1 is second in the ranking and does not clear the threshold. Every lag is LOW POWER. "
        "P8 clears the threshold in the opposite direction: a higher nested-decision score lines up with a lower later health index."
    )
    cross = gap.get("cross_repo") or {}
    repo_rows = []
    for row in cross.get("rows") or []:
        repo_rows.append({
            "repo": row.get("repo"),
            "health": _fmt(row.get("health"), 2),
            "years": row.get("n_years"),
            "effects": "E2, E3, E5, E7, E9, and E12 are DATA UNAVAILABLE.",
        })
    short_rows = []
    for row in cross.get("excluded_short_history") or []:
        short_rows.append({
            "repo": row.get("repo"),
            "reason": row.get("reason"),
            "health": _fmt(row.get("health"), 2),
        })
    reference_rows = []
    for effect_id, row in (cross.get("bitcoin_reference") or {}).items():
        kind = row.get("effect_size_kind") or "—"
        d_note = row.get("cohens_d_note") or ""
        if kind == "cohens_d":
            d_note = f"Cohen's d={_fmt(row.get('cohens_d'))}."
        reference_rows.append({
            "id": effect_id,
            "estimate": _fmt(row.get("estimate")),
            "ci": _ci(row.get("ci95")),
            "kind": kind,
            "q": _fmt(row.get("q")),
            "holdout": row.get("holdout_same_sign"),
            "d_note": d_note,
        })
    spearman_rows = []
    for effect_id, row in (cross.get("spearman_effect_vs_health") or {}).items():
        if row.get("status") == "ok":
            text = f"r={_fmt(row.get('estimate'))}, n={row.get('n')}, q={_fmt(row.get('q'))}."
        else:
            text = f"DATA UNAVAILABLE. {row.get('reason') or ''}".strip()
        spearman_rows.append({"id": effect_id, "text": text})
    fn = gap.get("false_negative_timeline") or {}
    slope = fn.get("slope") or {}
    cohorts = []
    for row in fn.get("cohorts") or []:
        cohorts.append({
            "cohort": row.get("cohort"),
            "leavers": row.get("n_leavers"),
            "false_negatives": row.get("n_false_negative"),
            "rate": _pct(row.get("false_negative_rate")),
        })
    fn_lead = (
        f"Classification: {fn.get('classification')}. "
        f"{fn.get('n_false_negative')} of {fn.get('n_leavers')} training leavers sit in the top patch-content quartile of later top-20 entrants. "
        f"The recount matches the pass-4 count of {fn.get('pass4_n_false_negative')}. "
        f"{fn.get('n_before_2018')} ({_pct(fn.get('share_before_2018'))}) entered before 2018 and "
        f"{fn.get('n_2018_or_later')} ({_pct(fn.get('share_2018_or_later'))}) entered in 2018 or later. "
        f"The rate changes by {_pp(slope.get('estimate'))} per year of entry "
        f"(interval {_ci_pp(slope.get('ci95'))}, q={_fmt(slope.get('q'))})."
    )
    fn_holdout = (
        f"On the training cutoff, {_pct(fn.get('holdout_false_negative_rate'))} of "
        f"{fn.get('holdout_n_leavers')} leavers who entered in 2024–2026 are in the same patch-content quartile. "
        "That rate is a description of the holdout. It is not a second test."
    )
    sub = gap.get("subsystem_silence") or {}
    models = sub.get("models") or {}
    logistic = models.get("logistic") or {}
    fe = models.get("logistic_year_fixed_effects") or {}
    entropy = sub.get("entropy_slope") or {}
    corr = sub.get("reviewer_silence_correlation") or {}
    silence_lead = (
        f"Classification: {sub.get('classification')}. "
        f"The logistic coefficient on a subsystem's active reviewers is {_fmt(logistic.get('reviewer_coefficient'))} log-odds per standard deviation "
        f"(interval {_ci(logistic.get('ci95'))}, q={_fmt(logistic.get('q'))}, n={models.get('n')}). "
        f"The 2024–2026 coefficient is {_fmt(sub.get('holdout_reviewer_coefficient'))}, same sign={sub.get('holdout_same_sign')}. "
        f"With year dummies in place of the linear year term, the coefficient is {_fmt(fe.get('reviewer_coefficient'))} "
        f"(interval {_ci(fe.get('ci95'))}). That check is outside the correction family."
    )
    silence_slopes = (
        f"Silence rises {_pp(models.get('year_slope_without_reviewers'))} per year "
        f"(interval {_ci_pp(models.get('year_slope_without_reviewers_ci95'))}) before reviewer count, and "
        f"{_pp(models.get('year_slope_with_reviewers'))} per year "
        f"(interval {_ci_pp(models.get('year_slope_with_reviewers_ci95'))}) after it. "
        "The slope widens. Reviewer count is associated with less silence in the cross-section, and the time trend remains."
    )
    silence_other = (
        f"Pearson r of active reviewers with the newcomer silence rate, across subsystem-years, is {_fmt(corr.get('estimate'))} "
        f"(n={corr.get('n')}, interval {_ci(corr.get('ci95'))}, q={_fmt(corr.get('q'))}). "
        f"Cohen's d for silence in high-reviewer versus low-reviewer cells is {_fmt(sub.get('silence_cohens_d_high_minus_low_reviewers'))} "
        f"({sub.get('silence_effect_size_flag') or '—'}). "
        f"Entropy changes by {_fmt(entropy.get('estimate'))} bits per year "
        f"(interval {_ci(entropy.get('ci95'))}, q={_fmt(entropy.get('q'))}, n={entropy.get('n')} years). "
        f"Newcomer pull requests in the corpus: {sub.get('n_newcomer_prs')}."
    )
    def _bits(value: Any) -> str:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return "—"
        if abs(number) < 0.005:
            return "0.00"
        return _fmt(number, 2)

    entropy_rows = []
    by_year = {int(row["year"]): row for row in sub.get("entropy_by_year") or []}
    for year in sorted(by_year):
        entropy_rows.append({"year": year, "entropy": _bits(by_year[year].get("entropy_bits"))})
    early = by_year.get(2011) or {}
    mid = by_year.get(2016) or {}
    late = by_year.get(2023) or {}
    entropy_shape = (
        f"2010 is three newcomer pull requests and entropy {_bits((by_year.get(2010) or {}).get('entropy_bits'))}. "
        f"The series is {_bits(early.get('entropy_bits'))} bits in 2011, {_bits(mid.get('entropy_bits'))} in 2016, "
        f"and {_bits(late.get('entropy_bits'))} in 2023. The positive slope is the rise out of the early years."
    )
    cells = _cell_map(gap)
    years = sorted({year for year, _name in cells})
    count_rows = []
    for year in years:
        count_rows.append([
            str(year),
            *[_endpoint(cells, year, name, "newcomer_prs") if (year, name) in cells else "0" for name in SUBSYSTEM_COLUMNS],
        ])
    count_table = _md_table(["Year", *SUBSYSTEM_COLUMNS], count_rows)
    endpoint_rows = []
    for name in SUBSYSTEM_COLUMNS:
        endpoint_rows.append({
            "subsystem": name,
            "n2016": _endpoint(cells, 2016, name, "newcomer_prs"),
            "s2016": _endpoint(cells, 2016, name, "silence_rate"),
            "r2016": _endpoint(cells, 2016, name, "active_reviewers"),
            "n2023": _endpoint(cells, 2023, name, "newcomer_prs"),
            "s2023": _endpoint(cells, 2023, name, "silence_rate"),
            "r2023": _endpoint(cells, 2023, name, "active_reviewers"),
        })
    gui = cells.get((2023, "gui")) or {}
    core = cells.get((2023, "core")) or {}
    cell_reading = (
        f"In 2023, GUI newcomer silence is {_pct(gui.get('silence_rate'))} "
        f"({gui.get('newcomer_prs')} pull requests, {gui.get('active_reviewers')} active reviewers). "
        f"Core newcomer silence is {_pct(core.get('silence_rate'))} "
        f"({core.get('newcomer_prs')} pull requests, {core.get('active_reviewers')} active reviewers). "
        "The project-wide year slope still widens once reviewer count is held fixed."
    )
    closes = [
        f"Gap 1. P6's t+1 correlation with later health is {_fmt(p6.get('estimate'))} (q={_fmt(p6.get('q'))}) on {p6.get('n')} years, marked LOW POWER. P5 and P7 stay unscored.",
        "Gap 2 stays open. Comparison repositories lack review objects, participant identities, and meeting lists, so the six effects cannot be placed against health.",
        f"Gap 3. The {fn.get('n_false_negative')} patch-content false negatives are {fn.get('classification')}.",
        f"Gap 4. The silence trend is {sub.get('classification')}. The reviewer coefficient is negative and the year slope widens.",
    ]
    cross_lead = cross.get("note") or ""
    return {
        "generated_date": date.today().isoformat(),
        "pin": (
            f"Fit {(gap.get('fit_years') or ['—', '—'])[0]}–{(gap.get('fit_years') or ['—', '—'])[1]}, "
            f"confirm {(gap.get('holdout_years') or ['—', '—'])[0]}–{(gap.get('holdout_years') or ['—', '—'])[1]}. "
            f"Bootstrap {gap.get('bootstrap')}, seed {gap.get('seed')}. "
            f"Benjamini-Hochberg family size {gap.get('bh_family_size')}, passes 1–5. "
            "Year enters the silence model as a linear term because year dummies would absorb the slope under test. "
            "The other shared controls are log lines changed, files touched, and author tenure."
        ),
        "principle_lead": principle_lead,
        "principle_rows": principle_rows,
        "principle_series": series,
        "holdout_lags": "2024–2026 does not contain enough paired years to confirm any lagged correlation.",
        "cross_lead": cross_lead,
        "repo_rows": repo_rows,
        "short_rows": short_rows,
        "reference_rows": reference_rows,
        "spearman_rows": spearman_rows,
        "interpretations": _sentences(cross.get("interpretation")),
        "fn_lead": fn_lead,
        "cohorts": cohorts,
        "fn_holdout": fn_holdout,
        "silence_lead": silence_lead,
        "silence_slopes": silence_slopes,
        "silence_other": silence_other,
        "entropy_rows": entropy_rows,
        "entropy_shape": entropy_shape,
        "count_table": count_table,
        "endpoint_rows": endpoint_rows,
        "cell_reading": cell_reading,
        "closes": _sentences(closes),
        "cannot": _sentences(gap.get("what_this_cannot_prove")),
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

    ledger = _maybe(findings_data / "governance_episode_ledger.json") or _maybe(
        analysis / "governance_episode_ledger.json"
    )
    if ledger:
        ledger_ctx = ctx_episode_ledger(ledger)
        jobs.append(
            ("REJECTION_ANATOMY.md", TEMPLATES / "REJECTION_ANATOMY.md.tpl", ledger_ctx)
        )
        jobs.append(
            (
                "STALLED_AGREEMENT_LEDGER.md",
                TEMPLATES / "STALLED_AGREEMENT_LEDGER.md.tpl",
                ledger_ctx,
            )
        )
        jobs.append(
            ("VOCABULARY_AUDIT.md", TEMPLATES / "VOCABULARY_AUDIT.md.tpl", ledger_ctx)
        )
        jobs.append(
            (
                "CONTRIBUTOR_CROSS_REF.md",
                TEMPLATES / "CONTRIBUTOR_CROSS_REF.md.tpl",
                ledger_ctx,
            )
        )

    p1 = _maybe(findings_data / "rsd_ingroup_analysis.json") or _maybe(analysis / "rsd_ingroup_analysis.json")
    p2 = _maybe(findings_data / "rsd_ingroup_analysis_v2.json") or _maybe(analysis / "rsd_ingroup_analysis_v2.json")
    p3 = _maybe(findings_data / "commons_dynamics_analysis.json") or _maybe(analysis / "commons_dynamics_analysis.json")
    p4 = _maybe(findings_data / "first_year_signal_analysis.json") or _maybe(analysis / "first_year_signal_analysis.json")
    p5 = _maybe(findings_data / "gap_closure_analysis.json") or _maybe(analysis / "gap_closure_analysis.json")
    if p1 and p2 and p3 and p4:
        bundle = validate_all(p1, p2, p3, p4)
        jobs.append(("INGROUP_REVIEW_TREATMENT.md", TEMPLATES / "INGROUP_REVIEW_TREATMENT.md.tpl", ctx_ingroup(p1)))
        jobs.append(("NEWCOMER_BAR.md", TEMPLATES / "NEWCOMER_BAR.md.tpl", ctx_newcomer(p2)))
        jobs.append((
            "COMMONS_MECHANISMS.md",
            TEMPLATES / "COMMONS_MECHANISMS.md.tpl",
            ctx_commons(p3, bundle["confirmed_effects"], p5),
        ))
        jobs.append((
            "FIRST_YEAR_TRAJECTORY.md",
            TEMPLATES / "FIRST_YEAR_TRAJECTORY.md.tpl",
            ctx_trajectory(p4, bundle["trajectory_rows"], p5),
        ))
    if p5:
        jobs.append(("GAP_CLOSURE.md", TEMPLATES / "GAP_CLOSURE.md.tpl", ctx_gap(p5)))

    revealed = _maybe(findings_data / "revealed_rough_consensus.json") or _maybe(
        analysis / "revealed_rough_consensus.json"
    )
    if revealed:
        jobs.append(
            (
                "REVEALED_ROUGH_CONSENSUS.md",
                TEMPLATES / "REVEALED_ROUGH_CONSENSUS.md.tpl",
                ctx_revealed_consensus(revealed),
            )
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
