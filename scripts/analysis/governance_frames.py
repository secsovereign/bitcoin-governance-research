#!/usr/bin/env python3
"""Compose the four reading frames from existing analysis JSON (no raw corpus scan)."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.utils.findings_io import save_analysis_json
from src.utils.paths import get_analysis_dir, get_findings_dir


def _load(*candidates: Path) -> Optional[Dict[str, Any]]:
    for path in candidates:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    return None


def compose() -> Dict[str, Any]:
    analysis = get_analysis_dir() / "findings" / "data"
    findings = get_findings_dir() / "data"

    cross = _load(analysis / "cross_platform_networks.json") or {}
    identity = _load(analysis / "enhanced_identity_resolution.json") or {}
    repo = _load(analysis / "cross_repo_comparison.json") or {}
    deputies = _load(findings / "high_volume_merger_deputies.json") or {}
    merge = _load(findings / "merge_pattern_analysis.json", analysis / "merge_pattern_analysis.json") or {}
    contrib = _load(analysis / "contributor_analysis.json") or {}
    bip = _load(analysis / "bip_analysis.json") or {}

    influence = cross.get("influence_flow") or {}
    by_era = influence.get("by_era") or {}
    hidden = cross.get("hidden_influencers") or {}
    port = repo.get("power_portability") or {}
    gov = repo.get("governance_comparison") or {}
    recent = deputies.get("recent_2022_plus") or {}
    top5 = recent.get("top5_mergers") or {}
    n_recent = recent.get("n_merged_prs") or 1
    values = list(top5.values())
    friends = ((merge.get("merge_relationships") or {}).get("friend_patterns") or [])[:8]
    retention = contrib.get("retention") or {}
    authors = contrib.get("authors") or {}
    participants = contrib.get("participants_only") or {}
    one_time = contrib.get("one_time") or {}
    quality = contrib.get("quality") or {}
    established = contrib.get("established_authors") or {}
    manual = identity.get("manual_alias_resolution") or {}

    frames = {
        "generated_date": date.today().isoformat(),
        "agenda_setting": {
            "all_time_flow_rate": influence.get("flow_rate"),
            "prs_discussed_before_github": influence.get("prs_discussed_before_github"),
            "prs_mentioned_in_irc": influence.get("prs_mentioned_in_irc"),
            "prs_mentioned_in_email": influence.get("prs_mentioned_in_email"),
            "prs_mentioned_in_delving": influence.get("prs_mentioned_in_delving"),
            "prs_mentioned_in_bitcointalk": influence.get("prs_mentioned_in_bitcointalk"),
            "by_era": by_era,
            "reading": (
                "Informal talk before a PR exists is a 2015–2021 IRC/email pattern. "
                "2022+ Delving/IRC volume is mostly commentary on already-opened PRs."
            ),
        },
        "informal_org_chart": {
            "recent_window": "2022+",
            "n_merged_prs": recent.get("n_merged_prs"),
            "top_merger": recent.get("top_merger"),
            "top1_share": (recent.get("top_merger_share_pct") or 0) / 100.0,
            "top2_share": sum(values[:2]) / n_recent if n_recent else 0,
            "top3_share": sum(values[:3]) / n_recent if n_recent else 0,
            "top5_mergers": top5,
            "funnels": (recent.get("authors_funneled_ge_40pct") or [])[:10],
            "coreviewers": dict(
                list((recent.get("top_co_reviewers_on_their_merges") or {}).items())[:8]
            ),
            "friend_patterns": friends,
            "self_merge_rate": (merge.get("self_merge_breakdown") or {}).get("self_merge_rate"),
            "reading": (
                "MAINTAINERS is not the org chart. 2022+ merge funnels show who the filter is."
            ),
        },
        "multiplex_identity": {
            "bip_top10": port.get("bip_top10") or [],
            "core_top10": port.get("core_top10") or [],
            "overlap_actors": port.get("power_overlap") or [],
            "overlap_count": port.get("overlap_count"),
            "overlap_rate": port.get("power_overlap_rate"),
            "overlapping_detail": port.get("overlapping_actors") or [],
            "core_unique_mergers": (gov.get("core_repo") or {}).get("unique_mergers"),
            "bip_unique_mergers": (gov.get("bips_repo") or {}).get("unique_mergers"),
            "core_top3_share": (gov.get("core_repo") or {}).get("top3_share"),
            "bip_top3_share": (gov.get("bips_repo") or {}).get("top3_share"),
            "verified_aliases": manual.get("cross_platform_unified_identities"),
            "github_delving_overlap": manual.get("github_delving_exact_overlap"),
            "github_bitcointalk_overlap": manual.get("github_bitcointalk_exact_overlap"),
            "hidden_irc": (hidden.get("irc_only_influencers") or [])[:8],
            "hidden_delving": (hidden.get("delving_only_influencers") or [])[:8],
            "bip_proposers": (bip.get("proposer_analysis") or {}).get("total_proposers"),
            "reading": (
                "The unit is person-in-channel. BIP-repo activity is a weak predictor of Core merge keys. "
                "A reviewer with 0 merges cannot merge; that zero is lack of keys, not unused privilege."
            ),
        },
        "exit_as_selection": {
            "total_contributors": (contrib.get("summary") or {}).get("total_contributors"),
            "active_1yr": retention.get("active_1yr"),
            "exit_rate_1yr": retention.get("exit_rate_1yr"),
            "authors_total": authors.get("total"),
            "authors_exit": authors.get("exit_rate_1yr"),
            "participants_total": participants.get("total"),
            "participants_exit": participants.get("exit_rate_1yr"),
            "one_time_share": one_time.get("percentage"),
            "one_time_exit": one_time.get("exit_rate_1yr"),
            "high_quality_authors": quality.get("high_quality_authors"),
            "high_quality_exit": quality.get("high_quality_exit_rate_1yr"),
            "established_total": established.get("total"),
            "established_exit": established.get("exit_rate_1yr"),
            "established_non_exit": established.get("non_maintainer_exit_rate"),
            "established_maint_exit": established.get("maintainer_exit_rate"),
            "reading": (
                "91% exit is selection, not collapse. Participants and one-timers leave; "
                "the continuing set is small and already inside the merge graph."
            ),
        },
    }
    return frames


def main() -> int:
    frames = compose()
    written = save_analysis_json("governance_frames.json", frames)
    print("Wrote " + ", ".join(str(p) for p in written))
    return 0


if __name__ == "__main__":
    sys.exit(main())
