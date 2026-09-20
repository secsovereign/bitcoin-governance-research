#!/usr/bin/env python3
"""Regenerate markdown findings reports from cross-platform analysis JSON."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.utils.paths import get_analysis_dir, get_findings_dir

logger = setup_logger()

SOM_LABELS = {
    "som1": "Passionate advocate",
    "som2": "Supportive",
    "som3": "Apathetic/undecided",
    "som4": "Unaware",
    "som5": "Not supportive, not fighting",
    "som6": "Passionately against",
}


def _load(name: str) -> Dict[str, Any]:
    path = get_analysis_dir() / "findings" / "data" / name
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _pct(value: float, digits: int = 1) -> str:
    return f"{value * 100:.{digits}f}%"


def _fmt_int(n: int) -> str:
    return f"{n:,}"


def _sentiment_table(sentiment: Dict[str, Any]) -> List[str]:
    total = sentiment.get("total_messages") or 0
    dist = sentiment.get("sentiment_distribution") or {}
    counts = sentiment.get("sentiment_counts") or {}
    lines = [f"**Total messages**: {_fmt_int(total)}", "", "| Sentiment | Percentage | Count |", "|-----------|------------|-------|"]
    for label in ("positive", "neutral", "negative"):
        if label in dist or label in counts:
            lines.append(
                f"| {label.capitalize()} | {_pct(dist.get(label, 0))} | {_fmt_int(counts.get(label, 0))} |"
            )
    return lines


def _som_table(som: Dict[str, Any], title: str) -> List[str]:
    dist = som.get("som_distribution") or {}
    lines = [f"**{title}**:", "", "| SOM | Description | Percentage |", "|-----|-------------|------------|"]
    for key in ("som1", "som2", "som3", "som4", "som5", "som6"):
        if key in dist:
            lines.append(f"| {key.upper()} | {SOM_LABELS[key]} | {_pct(dist[key])} |")
    return lines


def generate_cross_platform_networks_report(cp: Dict[str, Any], identity: Dict[str, Any]) -> str:
    audit = cp.get("source_audit") or {}
    ml = audit.get("mailing_lists") or {}
    forums = audit.get("forums") or {}
    email_meta = cp.get("email_load_meta") or {}
    id_res = cp.get("identity_resolution") or {}
    influence = cp.get("influence_flow") or {}
    stats = (cp.get("statistics") or {}).get("summary") or {}
    github_prs = cp.get("github_network", {}).get("total_prs") or 25122

    today = date.today().isoformat()
    lines = [
        "# Cross-Platform Influence Networks Report",
        "",
        f"**Analysis Date**: {today}  ",
        f"**Data Sources**: GitHub PRs ({_fmt_int(int(github_prs))}), IRC ({_fmt_int(id_res.get('irc_users', stats.get('irc_actors', 0)))} actors / "
        f"{_fmt_int(ml.get('bitcoin_dev_count', 0) + ml.get('cryptography_count', 0))} ML messages deduped to {_fmt_int(email_meta.get('total_loaded', 0))}), "
        f"Delving ({_fmt_int(forums.get('delving_posts', 0))} posts), "
        f"Bitcointalk ({_fmt_int(forums.get('bitcointalk_posts', 0))} posts)  ",
        "**Purpose**: Build comprehensive influence networks across platforms and identify hidden influencers",
        "",
        "---",
        "",
        "## Overview",
        "",
        "This report analyzes influence networks across GitHub, IRC, mailing lists, Delving Bitcoin, and Bitcointalk (board 6), "
        "identifying actors who span multiple platforms and those who operate primarily in informal channels.",
        "",
        "---",
        "",
        "## Key Findings",
        "",
        "### 1. Platform Actor Counts",
        "",
        "| Platform | Unique Actors |",
        "|----------|---------------|",
        f"| **GitHub** | {_fmt_int(id_res.get('github_users', stats.get('github_actors', 0)))} |",
        f"| **IRC** | {_fmt_int(id_res.get('irc_users', stats.get('irc_actors', 0)))} |",
        f"| **Email (combined ML)** | {_fmt_int(id_res.get('email_users', stats.get('email_actors', 0)))} |",
        f"| **Delving** | {_fmt_int(id_res.get('delving_users', stats.get('delving_actors', 0)))} |",
        f"| **Bitcointalk** | {_fmt_int(id_res.get('bitcointalk_users', stats.get('bitcointalk_actors', 0)))} |",
        "",
        "### 2. Identity Overlap (canonical nick/email join)",
        "",
        "| Overlap | Count | % of GitHub |",
        "|---------|-------|-------------|",
        f"| GitHub–IRC | {id_res.get('github_irc_overlap', 0)} | {_pct(id_res.get('overlap_rate_github_irc', 0))} |",
        f"| GitHub–Email | {id_res.get('github_email_overlap', 0)} | {_pct(id_res.get('overlap_rate_github_email', 0))} |",
        f"| GitHub–Delving | {id_res.get('github_delving_overlap', 0)} | {_pct(id_res.get('overlap_rate_github_delving', 0))} |",
        f"| GitHub–Bitcointalk | {id_res.get('github_bitcointalk_overlap', 0)} | — |",
        f"| IRC–Email | {id_res.get('irc_email_overlap', 0)} | {_pct(id_res.get('overlap_rate_irc_email', 0))} |",
        f"| All platforms (4+) | {id_res.get('all_platform_overlap', 0)} | — |",
        "",
        "### 3. PR Discussion Across Platforms",
        "",
        "| Channel | PRs mentioned |",
        "|---------|---------------|",
        f"| IRC | {_fmt_int(influence.get('prs_mentioned_in_irc', 0))} |",
        f"| Email (combined ML) | {_fmt_int(influence.get('prs_mentioned_in_email', 0))} |",
        f"| Delving | {_fmt_int(influence.get('prs_mentioned_in_delving', 0))} |",
        f"| Bitcointalk | {_fmt_int(influence.get('prs_mentioned_in_bitcointalk', 0))} |",
        f"| Discussed off-GitHub before merge | {_fmt_int(influence.get('prs_discussed_before_github', 0))} |",
        f"| Informal→GitHub flow rate | {influence.get('flow_rate', 0):.3f} |",
        "",
        "### 3b. Informal→GitHub flow by era",
        "",
        "| Era | GitHub PRs | IRC mentions | Email | Delving | Bitcointalk | Discussed first | Flow rate |",
        "|-----|------------|--------------|-------|---------|-------------|-----------------|-----------|",
    ]
    era_labels = {
        "early_2010_2014": "Early (2010–2014)",
        "scaling_segwit_2015_2017": "Scaling / SegWit (2015–2017)",
        "taproot_2018_2021": "Taproot (2018–2021)",
        "modern_2022_plus": "Modern (2022+)",
    }
    for era_key, label in era_labels.items():
        row = (influence.get("by_era") or {}).get(era_key) or {}
        lines.append(
            f"| {label} | {_fmt_int(row.get('github_prs', 0))} | "
            f"{_fmt_int(row.get('prs_mentioned_in_irc', 0))} | "
            f"{_fmt_int(row.get('prs_mentioned_in_email', 0))} | "
            f"{_fmt_int(row.get('prs_mentioned_in_delving', 0))} | "
            f"{_fmt_int(row.get('prs_mentioned_in_bitcointalk', 0))} | "
            f"{_fmt_int(row.get('prs_discussed_before_github', 0))} | "
            f"{row.get('flow_rate', 0):.3f} |"
        )
    lines.extend([
        "",
        "### 4. Enhanced Identity Resolution",
        "",
        f"- **Manual alias identities verified**: {identity.get('manual_alias_resolution', {}).get('cross_platform_unified_identities', 20)}",
        f"- **GitHub–Delving exact overlap**: {identity.get('improved_overlap', {}).get('github_delving_exact_overlap', 0)}",
        f"- **Delving users mentioning PRs**: {identity.get('pr_mention_resolution', {}).get('delving_users_mentioning_prs', 0)}",
        f"- **Bitcointalk users mentioning PRs**: {identity.get('pr_mention_resolution', {}).get('bitcointalk_users_mentioning_prs', 0)}",
        "",
        "---",
        "",
        "## Implications",
        "",
        "1. **Governance extends beyond GitHub** — thousands of PR references appear in IRC, mailing lists, Delving, and Bitcointalk.",
        "2. **Email overlap was undercounted** — combining cryptography ML with bitcoin-dev raises GitHub–email links substantially vs bitcoin-dev alone.",
        "3. **Forums add distinct actors** — Delving and Bitcointalk contribute actors with limited GitHub presence.",
        "4. **Hidden influencers** — many high-activity informal participants never open GitHub PRs.",
        "5. **Agenda-setting is era-specific** — informal→GitHub *before PR open* is a 2015–2021 (IRC/email) pattern. 2022+ Delving/IRC volume is mostly talk *about* already-opened PRs.",
        "",
        "---",
        "",
        "## Methodology",
        "",
        "### Data Sources",
        "",
        f"- **bitcoin-dev (gnusha)**: {_fmt_int(ml.get('bitcoin_dev_count', 0))} messages",
        f"- **cryptography (metzdowd)**: {_fmt_int(ml.get('cryptography_count', 0))} messages ({ml.get('message_id_overlap', 0)} cross-list duplicates removed when combined)",
        f"- **Delving Bitcoin**: {_fmt_int(forums.get('delving_posts', 0))} posts ({_fmt_int(forums.get('delving_posts_mentioning_core_prs', 0))} mention Core PRs)",
        f"- **Bitcointalk board 6**: {_fmt_int(forums.get('bitcointalk_posts', 0))} posts",
        "- **Satoshi Bitcointalk archive**: separate curated export (not merged into board scrape)",
        "",
        "### Limitations",
        "",
        "- Exact username matching is a lower bound on identity overlap.",
        "- Bitcointalk scrape covers board 6 only (~159k unique posts after key dedupe; ~18k gap vs topic metadata).",
        "- Delving postdates SegWit; zero keyword-filtered Delving traffic during SegWit is expected.",
        "",
        "### Data Files",
        "",
        "- `analysis/findings/data/cross_platform_networks.json`",
        "- `analysis/findings/data/enhanced_identity_resolution.json`",
        "",
        "---",
        "",
        "**Generated by**: `scripts/reporting/generate_cross_platform_reports.py`",
        "",
    ])
    return "\n".join(lines) + "\n"


def generate_informal_sentiment_report(sent: Dict[str, Any]) -> str:
    audit = sent.get("source_audit") or {}
    summary = (sent.get("statistics") or {}).get("summary") or {}
    corr = sent.get("pr_correlation") or {}
    today = date.today().isoformat()

    lines = [
        "# Informal Communication Sentiment Analysis Report",
        "",
        f"**Analysis Date**: {today}  ",
        f"**Data Sources**: IRC ({_fmt_int(summary.get('irc_messages', 0))}), "
        f"combined mailing lists ({_fmt_int(summary.get('email_messages', 0))}), "
        f"cryptography ML ({_fmt_int(summary.get('cryptography_messages', 0))}), "
        f"Delving ({_fmt_int(summary.get('delving_messages', 0))}), "
        f"Bitcointalk ({_fmt_int(summary.get('bitcointalk_messages', 0))})  ",
        "**Purpose**: Analyze sentiment and BCAP State of Mind (SOM) across informal channels",
        "",
        "---",
        "",
        "## Overview",
        "",
        "This report analyzes sentiment and engagement patterns across IRC, mailing lists (bitcoin-dev + cryptography), "
        "Delving Bitcoin, and Bitcointalk, applying BCAP's State of Mind framework to informal governance dynamics.",
        "",
        "---",
        "",
        "## Key Findings",
        "",
        "### 1. IRC Sentiment",
        "",
        *_sentiment_table(sent.get("irc_sentiment") or {}),
        "",
        "### 2. Combined Email Sentiment (bitcoin-dev + cryptography, deduped)",
        "",
        *_sentiment_table(sent.get("email_sentiment") or {}),
        "",
        "### 3. Cryptography ML Sentiment (standalone)",
        "",
        *_sentiment_table(sent.get("cryptography_sentiment") or {}),
        "",
        "### 4. Delving Sentiment",
        "",
        *_sentiment_table(sent.get("delving_sentiment") or {}),
        "",
        "### 5. Bitcointalk Sentiment",
        "",
        *_sentiment_table(sent.get("bitcointalk_sentiment") or {}),
        "",
        "### 6. State of Mind (SOM) Distribution",
        "",
        *_som_table(sent.get("irc_som") or {}, "IRC SOM"),
        "",
        *_som_table(sent.get("email_som") or {}, "Combined email SOM"),
        "",
        *_som_table(sent.get("delving_som") or {}, "Delving SOM"),
        "",
        "### 7. PR Mention Correlation",
        "",
        f"- **Unique PRs mentioned informally**: {_fmt_int(corr.get('total_unique_prs_mentioned', 0))}",
        f"- **Merge rate (mentioned PRs)**: {_pct(corr.get('merged_rate_mentioned', 0))}",
        f"- **Overall merge rate**: {_pct(corr.get('overall_merge_rate', 0))}",
        f"- **PRs mentioned in Delving**: {_fmt_int(corr.get('prs_mentioned_in_delving', 0))}",
        f"- **PRs mentioned in Bitcointalk**: {_fmt_int(corr.get('prs_mentioned_in_bitcointalk', 0))}",
        "",
        "---",
        "",
        "## Key Insights",
        "",
        "1. **Cryptography ML shifts blended email sentiment** — more negative than bitcoin-dev alone.",
        "2. **IRC remains high-volume but neutral** — technical chat dominates.",
        "3. **Bitcointalk is the largest informal corpus** — sentiment skews negative on keyword measures.",
        "4. **Delving is GitHub-adjacent** — smaller volume but high maintainer overlap.",
        "",
        "---",
        "",
        "## Methodology Limitations",
        "",
        "Keyword-based sentiment/SOM classification (not ML/BERT). Results are directional.",
        "",
        "**Data file**: `analysis/findings/data/informal_sentiment.json`",
        "",
        "**Generated by**: `scripts/reporting/generate_cross_platform_reports.py`",
        "",
    ]
    return "\n".join(lines) + "\n"


def generate_funding_report(fund: Dict[str, Any]) -> str:
    pr = fund.get("pr_analysis") or {}
    issue = fund.get("issue_analysis") or {}
    email = fund.get("email_analysis") or {}
    by_list = fund.get("email_by_list_analysis") or {}
    forum = fund.get("forum_analysis") or {}
    temporal = fund.get("temporal_analysis") or {}
    corr = fund.get("correlation_analysis") or {}
    today = date.today().isoformat()

    lines = [
        "# Enhanced Funding Analysis Report",
        "",
        f"**Date**: {today}  ",
        "**Purpose**: Funding mentions across GitHub and informal channels  ",
        "**Methodology**: Keyword extraction; combined mailing lists (bitcoin-dev + cryptography, message_id dedupe)",
        "",
        "---",
        "",
        "## 1. Coverage Summary",
        "",
        "| Channel | With funding mentions | Total | Rate |",
        "|---------|----------------------|-------|------|",
        f"| PRs | {_fmt_int(pr.get('prs_with_funding_mentions', 0))} | {_fmt_int(pr.get('total_prs', 0))} | {_pct(pr.get('funding_mention_rate', 0))} |",
        f"| Issues | {_fmt_int(issue.get('issues_with_funding_mentions', 0))} | {_fmt_int(issue.get('total_issues', 0))} | {_pct(issue.get('funding_mention_rate', 0))} |",
        f"| Email (combined ML) | {_fmt_int(email.get('emails_with_funding_mentions', 0))} | {_fmt_int(email.get('total_emails', 0))} | {_pct(email.get('funding_mention_rate', 0))} |",
    ]
    for list_name, stats in sorted(by_list.items()):
        lines.append(
            f"| Email ({list_name}) | {_fmt_int(stats.get('emails_with_funding_mentions', 0))} | "
            f"{_fmt_int(stats.get('total_emails', 0))} | {_pct(stats.get('funding_mention_rate', 0))} |"
        )
    for channel, stats in forum.items():
        lines.append(
            f"| {channel.title()} | {_fmt_int(stats.get('posts_with_funding_mentions', 0))} | "
            f"{_fmt_int(stats.get('total_posts', 0))} | {_pct(stats.get('funding_mention_rate', 0))} |"
        )

    lines.extend(["", "---", "", "## 2. Temporal PR Funding Mentions (recent years)", ""])
    yearly = temporal.get("yearly_data") or {}
    if yearly:
        lines.extend(["| Year | PRs | With funding | Rate |", "|------|-----|--------------|------|"])
        for year in sorted(yearly.keys())[-10:]:
            row = yearly[year]
            lines.append(
                f"| {year} | {_fmt_int(row.get('total_prs', 0))} | "
                f"{_fmt_int(row.get('prs_with_funding', 0))} | {_pct(row.get('funding_mention_rate', 0))} |"
            )

    wf = corr.get("with_funding") or {}
    wof = corr.get("without_funding") or {}
    lines.extend([
        "",
        "---",
        "",
        "## 3. PR Outcome Correlation (GitHub body/title mentions only)",
        "",
        "| Metric | With funding mention | Without |",
        "|--------|---------------------|---------|",
        f"| Merge rate | {_pct(wf.get('merge_rate', 0))} | {_pct(wof.get('merge_rate', 0))} |",
        f"| Avg reviews | {wf.get('avg_reviews', 0):.1f} | {wof.get('avg_reviews', 0):.1f} |",
        "",
        "**Note**: Correlation ≠ causation. Most actual funding is never mentioned publicly.",
        "",
        "---",
        "",
        "## 4. Top funding types (PRs)",
        "",
    ])
    for ftype, count in list((pr.get("top_funding_types") or {}).items())[:8]:
        lines.append(f"- **{ftype}**: {_fmt_int(count)}")
    lines.extend([
        "",
        "**Data file**: `analysis/findings/data/funding_analysis.json`",
        "",
        "**Generated by**: `scripts/reporting/generate_cross_platform_reports.py`",
        "",
    ])
    return "\n".join(lines) + "\n"


def _bcap_phase_row(phase_data: Dict[str, Any]) -> str:
    pc = phase_data.get("power_concentration") or {}
    ma = phase_data.get("merge_authority") or {}
    rp = phase_data.get("review_patterns") or {}
    zero_review = rp.get("zero_review_rate", 0)
    if zero_review <= 1:
        zero_review = zero_review * 100
    return (
        f"| {phase_data.get('phase', '?')} | {_fmt_int(phase_data.get('merged_prs', 0))} | "
        f"{_pct(pc.get('top3_merge_share', 0))} | "
        f"{ma.get('self_merge_rate', 0):.1f}% | "
        f"{zero_review:.1f}% |"
    )


def _informal_activity_table(activity: Dict[str, Any]) -> List[str]:
    if not activity:
        return ["*(no informal activity data)*"]
    lines = ["| Channel | Keyword-filtered messages | Unique authors |", "|---------|---------------------------|----------------|"]
    for channel in ("email", "irc", "delving", "bitcointalk", "mailing_list_bitcoin-dev", "mailing_list_cryptography"):
        if channel not in activity:
            continue
        row = activity[channel]
        lines.append(
            f"| {channel} | {_fmt_int(row.get('messages', 0))} | {_fmt_int(row.get('unique_authors', 0))} |"
        )
    return lines


def generate_bcap_report(bcap_som: Dict[str, Any], bcap_ps: Dict[str, Any]) -> str:
    today = date.today().isoformat()
    lines = [
        "# BCAP Framework Integration Report",
        "",
        f"**Analysis Date**: {today}  ",
        "**Framework**: BCAP (Bitcoin Consensus Analysis Project)  ",
        "**Reference**: [bitcoin-cap/bcap](https://github.com/bitcoin-cap/bcap)  ",
        "**Purpose**: Apply BCAP SOM and power-shift concepts to Bitcoin Core governance during SegWit and Taproot",
        "",
        "---",
        "",
        "## Overview",
        "",
        "BCAP ecosystem concepts are applied to **Core-internal** governance during consensus periods. "
        "Analysis now includes **informal channels** (IRC, bitcoin-dev + cryptography ML, Delving, Bitcointalk) "
        "in addition to GitHub PRs/issues.",
        "",
        "---",
        "",
        "## 1. GitHub State of Mind (PR/issue activity)",
        "",
    ]

    for period in ("segwit", "taproot"):
        analysis = bcap_som.get(f"{period}_analysis") or {}
        dist = (analysis.get("temporal_distribution") or {}).get("percentages") or {}
        lines.extend([
            f"### {period.title()} ({analysis.get('start_date')} → {analysis.get('end_date')})",
            "",
            f"- **Developers classified**: {analysis.get('total_developers', 0)}",
            f"- **Consensus-related PRs**: {analysis.get('related_prs_count', 0)}",
            f"- **Consensus-related issues**: {analysis.get('related_issues_count', 0)}",
            "",
            "| SOM | % of developers |",
            "|-----|-----------------|",
        ])
        for key in ("som1", "som2", "som3", "som5", "som6"):
            if key in dist:
                lines.append(f"| {key.upper()} ({SOM_LABELS[key]}) | {dist[key]:.1f}% |")
        lines.extend(["", "#### Informal channel activity (keyword-filtered)", ""])
        lines.extend(_informal_activity_table(analysis.get("informal_activity") or {}))
        lines.append("")

    lines.extend(["---", "", "## 2. Power shift phases (GitHub merges)", ""])
    for period in ("segwit", "taproot"):
        ps = bcap_ps.get(f"{period}_analysis") or {}
        lines.extend([
            f"### {period.title()}",
            "",
            "| Phase | Merged PRs | Top-3 merge share | Self-merge rate | Zero-review rate |",
            "|-------|------------|-------------------|-----------------|------------------|",
        ])
        baseline = (bcap_ps.get("baseline_comparison") or {}).get(period) or {}
        if baseline:
            lines.append(_bcap_phase_row({**baseline, "phase": "Baseline"}))
        for phase_name, phase_data in (ps.get("phase_analyses") or {}).items():
            lines.append(_bcap_phase_row({**phase_data, "phase": phase_name.replace("_", " ").title()}))
        overall = ps.get("overall_analysis")
        if overall:
            lines.append(_bcap_phase_row({**overall, "phase": "Overall"}))
        lines.extend(["", "#### Informal activity by phase (keyword-filtered)", ""])
        by_phase = ps.get("informal_by_phase") or {}
        for phase_name, activity in by_phase.items():
            total_msgs = sum((activity.get(ch) or {}).get("messages", 0) for ch in activity)
            lines.append(f"- **{phase_name}**: {_fmt_int(total_msgs)} informal messages across channels")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## Data Files",
        "",
        "- `analysis/findings/data/bcap_som_analysis.json`",
        "- `analysis/findings/data/bcap_power_shift.json`",
        "",
        "**Generated by**: `scripts/reporting/generate_cross_platform_reports.py`",
        "",
    ])
    return "\n".join(lines) + "\n"


def patch_executive_summary_header(findings_dir: Path, audit: Dict[str, Any]) -> None:
    path = findings_dir / "EXECUTIVE_SUMMARY.md"
    if not path.exists():
        return
    ml = audit.get("mailing_lists") or {}
    forums = audit.get("forums") or {}
    email_total = ml.get("bitcoin_dev_count", 0) + ml.get("cryptography_count", 0) - ml.get("message_id_overlap", 0)
    new_header = (
        f"**25,122 PRs | 8,890 Issues | {email_total:,} Emails (2 ML lists) | "
        f"430,613 IRC | {forums.get('delving_posts', 0):,} Delving | "
        f"{forums.get('bitcointalk_posts', 0):,} Bitcointalk | 339 Releases | 2010-2026**"
    )
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("**") and "PRs" in line and "Issues" in line:
            lines[i] = new_header
            break
    for i, line in enumerate(lines):
        if line.startswith("**Last Updated**"):
            lines[i] = f"**Last Updated**: {date.today().isoformat()} (informal-channel integration: cryptography ML, Delving, Bitcointalk)"
            break
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("Patched %s header", path.name)


def patch_research_methodology(findings_dir: Path, audit: Dict[str, Any]) -> None:
    path = findings_dir / "RESEARCH_METHODOLOGY.md"
    if not path.exists():
        return
    ml = audit.get("mailing_lists") or {}
    forums = audit.get("forums") or {}
    email_total = ml.get("bitcoin_dev_count", 0) + ml.get("cryptography_count", 0) - ml.get("message_id_overlap", 0)
    replacement = f"""**Secondary Sources**:
- Mailing lists: **bitcoin-dev** (gnusha.org public-inbox, {ml.get('bitcoin_dev_count', 0):,} messages)
- Mailing lists: **cryptography** (metzdowd pipermail, {ml.get('cryptography_count', 0):,} messages; {ml.get('message_id_overlap', 0)} cross-list duplicates removed when combined)
- IRC: `#bitcoin-core-dev` and related logs
- **Delving Bitcoin** ({forums.get('delving_posts', 0):,} posts)
- **Bitcointalk board 6** ({forums.get('bitcointalk_posts', 0):,} posts; Satoshi archive kept separate)

**Total Informal + GitHub Data (2026-09 refresh)**:
- **25,122 Pull Requests**
- **8,890 Issues**
- **{email_total:,} Emails** (combined ML, deduped)
- **430,613 IRC Messages**
- **{forums.get('delving_posts', 0):,} Delving posts**
- **{forums.get('bitcointalk_posts', 0):,} Bitcointalk posts**
- **339 Releases**
- **549 Satoshi Nakamoto Communications** (2008-2015)"""

    text = path.read_text(encoding="utf-8")
    start = text.find("**Secondary Sources**:")
    end = text.find("### 2.2 GitHub Data Collection")
    if start == -1 or end == -1:
        logger.warning("Could not patch RESEARCH_METHODOLOGY.md section boundaries")
        return
    # also replace Total Data Collected block
    total_start = text.find("**Total Data Collected**:")
    if total_start != -1 and total_start < start:
        text = text[:total_start] + replacement + text[end:]
    else:
        text = text[:start] + replacement + "\n\n" + text[end:]
    path.write_text(text, encoding="utf-8")
    logger.info("Patched %s data sources section", path.name)


def main() -> int:
    findings_dir = get_findings_dir()
    findings_dir.mkdir(parents=True, exist_ok=True)

    cp = _load("cross_platform_networks.json")
    identity = _load("enhanced_identity_resolution.json")
    sent = _load("informal_sentiment.json")
    fund = _load("funding_analysis.json")
    bcap_som = _load("bcap_som_analysis.json")
    bcap_ps = _load("bcap_power_shift.json")

    reports = {
        "CROSS_PLATFORM_NETWORKS.md": generate_cross_platform_networks_report(cp, identity),
        "INFORMAL_SENTIMENT_ANALYSIS.md": generate_informal_sentiment_report(sent),
        "ENHANCED_FUNDING_ANALYSIS_REPORT.md": generate_funding_report(fund),
        "BCAP_INTEGRATION_REPORT.md": generate_bcap_report(bcap_som, bcap_ps),
    }

    for name, content in reports.items():
        out = findings_dir / name
        out.write_text(content, encoding="utf-8")
        logger.info("Wrote %s", out)

    audit = cp.get("source_audit") or {}
    patch_executive_summary_header(findings_dir, audit)
    patch_research_methodology(findings_dir, audit)

    print(f"Generated {len(reports)} reports in {findings_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
