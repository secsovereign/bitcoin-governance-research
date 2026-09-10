#!/usr/bin/env python3
"""Patch root/findings docs with canonical data counts and methodology strings."""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.utils.paths import get_analysis_dir, get_data_dir, get_findings_dir

logger = setup_logger()

OLD_METHODOLOGY = (
    "Quality-weighted review counting (GitHub, ACK, IRC, email), cross-platform integrated"
)
NEW_METHODOLOGY = (
    "Quality-weighted review counting (GitHub, ACK, IRC, combined mailing lists, Delving, Bitcointalk), "
    "cross-platform integrated"
)

METHODOLOGY_REPLACEMENTS = [
    (OLD_METHODOLOGY, NEW_METHODOLOGY),
    (
        "Cross-platform reviews (IRC, email) are included with same quality weighting",
        "Cross-platform reviews (IRC, combined mailing lists, Delving, Bitcointalk) use the same quality weighting",
    ),
    (
        "Cross-platform review integration (IRC, email, GitHub)",
        "Cross-platform review integration (IRC, combined mailing lists, Delving, Bitcointalk, GitHub)",
    ),
    (
        "We analyze **cross-platform reviews** (IRC, email, GitHub)",
        "We analyze **cross-platform reviews** (IRC, combined mailing lists, Delving, Bitcointalk, GitHub)",
    ),
    (
        "Quality-weighted (GitHub, ACK, IRC, email), cross-platform integrated",
        "Quality-weighted (GitHub, ACK, IRC, combined mailing lists, Delving, Bitcointalk), cross-platform integrated",
    ),
    ("State of Mind (SOM) analysis on IRC/email", "State of Mind (SOM) analysis on informal channels"),
    ("GitHub/IRC/Email overlap analysis", "GitHub / IRC / ML / Delving / Bitcointalk overlap analysis"),
]

PR_COUNT_REPLACEMENTS = [
    ("23,478 PRs", "25,122 PRs"),
    ("23,478 Pull Requests", "25,122 Pull Requests"),
    ("23,478 PRs,", "25,122 PRs,"),
    ("~23,478 Pull Requests", "~25,122 Pull Requests"),
    ("23,615 PRs", "25,122 PRs"),
    ("23,615)", "25,122)"),
    ("19,446 Emails", "51,062 Emails (combined ML)"),
    ("433,048 IRC Messages", "430,613 IRC Messages"),
    ("433,048 IRC messages", "430,613 IRC messages"),
    ("~433,048 messages", "~430,613 messages"),
    ("441,931 IRC", "430,613 IRC"),
    ("19,351 emails", "51,062 emails (combined ML)"),
    ("9,235 maintainer merged PRs", "9,793 maintainer merged PRs"),
    ("9,235 maintainer PRs", "9,793 maintainer PRs"),
    ("9,706 maintainer merged PRs", "9,793 maintainer merged PRs"),
    ("9,706 maintainer PRs", "9,793 maintainer PRs"),
    ("2,446 of 9,235", "2,501 of 9,793"),
    ("2,501 of 9,706", "2,501 of 9,793"),
    ("26.5% self-merge", "25.5% self-merge"),
    ("25.8% self-merge", "25.5% self-merge"),
    ("self-merge rate: 26.5%", "self-merge rate: 25.5%"),
    ("self-merge rate: 25.8%", "self-merge rate: 25.5%"),
    ("stable at 26.5%", "25.5% in the current merge-pattern extract"),
    ("25.8% in the current merge-pattern extract", "25.5% in the current merge-pattern extract"),
    ("87.7% exit rate across 7,604 contributors", "90.7% exit rate across 7,827 contributors"),
    ("87.7% of 7,604", "90.7% of 7,827"),
    ("91.1% exit rate across 7,827 contributors", "90.7% exit rate across 7,827 contributors"),
    ("91.1% of 7,827", "90.7% of 7,827"),
]


def load_audit() -> Dict[str, Any]:
    path = get_analysis_dir() / "findings" / "data" / "cross_platform_networks.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8")).get("source_audit") or {}
    return {}


def canonical_counts(audit: Dict[str, Any]) -> Dict[str, int]:
    ml = audit.get("mailing_lists") or {}
    forums = audit.get("forums") or {}
    email_combined = (
        ml.get("bitcoin_dev_count", 0)
        + ml.get("cryptography_count", 0)
        - ml.get("message_id_overlap", 0)
    )
    prs = sum(1 for _ in open(get_data_dir() / "github" / "prs_raw.jsonl") if _.strip()) if (
        get_data_dir() / "github" / "prs_raw.jsonl"
    ).exists() else 25122
    issues = sum(1 for _ in open(get_data_dir() / "github" / "issues_raw.jsonl") if _.strip()) if (
        get_data_dir() / "github" / "issues_raw.jsonl"
    ).exists() else 8890
    irc = sum(1 for _ in open(get_data_dir() / "irc" / "messages.jsonl") if _.strip()) if (
        get_data_dir() / "irc" / "messages.jsonl"
    ).exists() else 430613
    return {
        "prs": prs,
        "issues": issues,
        "email_combined": email_combined,
        "bitcoin_dev": ml.get("bitcoin_dev_count", 24644),
        "cryptography": ml.get("cryptography_count", 26420),
        "ml_overlap": ml.get("message_id_overlap", 2),
        "delving": forums.get("delving_posts", 4662),
        "bitcointalk": forums.get("bitcointalk_posts", 158917),
        "irc": irc,
    }


def patch_executive_summary_data_sources(findings_dir: Path, counts: Dict[str, int]) -> None:
    path = findings_dir / "EXECUTIVE_SUMMARY.md"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    new_section = f"""## Data Sources

**{counts['prs']:,} PRs** (GitHub) - Formal decisions, review patterns, merge authority  
**{counts['issues']:,} Issues** (GitHub) - Discussions, problem-solving, coordination  
**{counts['email_combined']:,} Emails** (bitcoin-dev + cryptography ML, deduped) - Consensus-building, rationale  
**{counts['irc']:,} IRC Messages** - Real-time coordination, informal decision-making  
**{counts['delving']:,} Delving posts** - Modern spec/governance forum (2023+)  
**{counts['bitcointalk']:,} Bitcointalk posts** (board 6) - Historical public forum discourse  
**339 Releases** - Protocol evolution, release signing authority

**Total**: 1+ million GitHub/informal data points across 16+ years, synthesized to reveal governance patterns."""

    text = re.sub(
        r"## Data Sources\n\n.*?\n\n---",
        new_section + "\n\n---",
        text,
        count=1,
        flags=re.DOTALL,
    )
    text = text.replace(OLD_METHODOLOGY, NEW_METHODOLOGY)
    path.write_text(text, encoding="utf-8")
    logger.info("Patched EXECUTIVE_SUMMARY data sources")


def patch_research_methodology_irc(findings_dir: Path, counts: Dict[str, int]) -> None:
    path = findings_dir / "RESEARCH_METHODOLOGY.md"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    text = text.replace("- **433,048 IRC messages**", f"- **{counts['irc']:,} IRC messages**")
    text = text.replace(OLD_METHODOLOGY, NEW_METHODOLOGY)

    if "### 2.6 Cryptography Mailing List" not in text:
        insert = f"""
### 2.6 Cryptography Mailing List Collection

**Script**: `scripts/data_collection/cryptography_ml_collector.py`  
**Source**: https://www.metzdowd.com/pipermail/cryptography/  
**Output**: `data/mailing_lists/cryptography.jsonl`

**Data Collected**: **{counts['cryptography']:,} messages** (deduped with bitcoin-dev by `message_id` when combined: {counts['ml_overlap']} overlap)

### 2.7 Delving Bitcoin Collection

**Script**: `scripts/data_collection/delving_collector.py`  
**Output**: `data/delving/{{topics,posts}}.jsonl`

**Data Collected**: **{counts['delving']:,} posts**

### 2.8 Bitcointalk Collection

**Script**: `scripts/data_collection/bitcointalk_collector.py`  
**Scope**: Board 6 (Development & Technical Discussion)  
**Output**: `data/bitcointalk/{{topics,posts}}.jsonl`

**Data Collected**: **{counts['bitcointalk']:,} posts** (~159k unique after stable-key dedupe; Satoshi archive kept separate)

"""
        anchor = "### 2.5 Satoshi Archive Data Collection"
        if anchor in text:
            text = text.replace(anchor, insert + anchor)

    path.write_text(text, encoding="utf-8")
    logger.info("Patched RESEARCH_METHODOLOGY IRC + new collectors")


def patch_readme_data_sources(repo_root: Path, counts: Dict[str, int]) -> None:
    path = repo_root / "README.md"
    if not path.exists():
        return
    replacement = f"""## Data sources (public)

| Channel | Approx. size |
|---------|-------------:|
| GitHub `bitcoin/bitcoin` PRs / issues | {counts['prs']:,} / {counts['issues']:,} |
| bitcoin-dev + cryptography ML (deduped) | {counts['email_combined']:,} emails |
| IRC `#bitcoin-core-dev` and related | {counts['irc']:,} messages |
| Delving Bitcoin | {counts['delving']:,} posts |
| Bitcointalk board 6 | {counts['bitcointalk']:,} posts |
"""

    text = path.read_text(encoding="utf-8")
    text = re.sub(
        r"## Data sources \(public\)\n\n\| Channel \| Approx\. size \|.*?\| Bitcointalk board 6 \| [^\n]+\n",
        replacement,
        text,
        count=1,
        flags=re.DOTALL,
    )
    path.write_text(text, encoding="utf-8")
    logger.info("Patched README.md data sources")


def patch_data_sourcing(repo_root: Path, counts: Dict[str, int]) -> None:
    path = repo_root / "DATA_SOURCING_AND_REPRODUCIBILITY.md"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    text = text.replace("- Pull Requests (PRs): 23,478 PRs", f"- Pull Requests (PRs): {counts['prs']:,} PRs")
    text = text.replace("All PRs (23,478)", f"All PRs ({counts['prs']:,})")

    secondary = f"""**Mailing Lists (bitcoin-dev)**: `scripts/data_collection/gnusha_collector.py`  
**Source**: https://gnusha.org/pi/bitcoindev public-inbox  
**Coverage**: {counts['bitcoin_dev']:,} emails → `data/mailing_lists/emails.jsonl`

**Mailing Lists (cryptography)**: `scripts/data_collection/cryptography_ml_collector.py`  
**Source**: https://www.metzdowd.com/pipermail/cryptography/  
**Coverage**: {counts['cryptography']:,} emails → `data/mailing_lists/cryptography.jsonl`  
**Dedupe**: {counts['ml_overlap']} `message_id` overlaps with bitcoin-dev when analyses combine lists

**IRC Channels**: `scripts/data_collection/irc_collector.py` → `{counts['irc']:,}` messages in `data/irc/messages.jsonl`

**Delving Bitcoin**: `scripts/data_collection/delving_collector.py` → `{counts['delving']:,}` posts

**Bitcointalk (board 6)**: `scripts/data_collection/bitcointalk_collector.py` → `{counts['bitcointalk']:,}` posts

**Satoshi Archive**: `scripts/data_collection/satoshi_archive_collector.py` (549 communications, separate from board scrape)

**Orchestration**: `scripts/collect_all.py` (initial) / `scripts/update_all.py` (incremental)"""

    text = re.sub(
        r"\*\*Mailing Lists\*\*:.*?(\*\*Other\*\*: Various collectors.*?\n)",
        secondary + "\n\n",
        text,
        count=1,
        flags=re.DOTALL,
    )

    repro = """3. **Collect Raw Data** (if needed):
   ```bash
   python scripts/collect_all.py          # initial full collect
   # or incremental:
   python scripts/update_all.py
   ```
   **Note**: GitHub collection takes hours (API rate limits). Forum/list collectors are separate long poles."""

    text = re.sub(
        r"3\. \*\*Collect Raw Data\*\* \(if needed\):.*?(\*\*Note\*\*: Satoshi archive.*?\n)",
        repro + "\n\n",
        text,
        count=1,
        flags=re.DOTALL,
    )

    text = text.replace(
        "**Date**: 2026-01-07",
        f"**Date**: {date.today().isoformat()} (informal sources integrated)",
    )
    path.write_text(text, encoding="utf-8")
    logger.info("Patched DATA_SOURCING_AND_REPRODUCIBILITY.md")


def patch_findings_methodology_and_counts(findings_dir: Path) -> List[str]:
    patched: List[str] = []
    skip = {
        "CROSS_PLATFORM_NETWORKS.md",
        "INFORMAL_SENTIMENT_ANALYSIS.md",
        "ENHANCED_FUNDING_ANALYSIS_REPORT.md",
        "BCAP_INTEGRATION_REPORT.md",
        "CONTRIBUTOR_ANALYSIS.md",
        "BIP_PROCESS_ANALYSIS.md",
        "RELEASE_SIGNING_ANALYSIS.md",
        "CROSS_REPO_COMPARISON.md",
        "MERGE_CONCENTRATION_DEPUTIES_REPORT.md",
        "STALLED_PROPOSALS_REPORT.md",
        "MAINTAINER_PREMIUM_REPORT.md",
        "PR_IMPORTANCE_ANALYSIS.md",
        "COORDINATION_COSTS_ANALYSIS.md",
        "TEMPORAL_ANALYSIS_REPORT.md",
        "MERGE_PATTERN_BREAKDOWN.md",
        "GINI_COEFFICIENT_EXPLANATION.md",
        "REVIEW_QUALITY_ENHANCED_ANALYSIS.md",
        "CONFLICT_RESOLUTION_ANALYSIS.md",
        "INTERDISCIPLINARY_ANALYSIS_REPORT.md",
        "NOVEL_INTERPRETATIONS.md",
        "LANGUAGE_EVOLUTION.md",
        "GOVERNANCE_FRAMES.md",
    }
    for path in sorted(findings_dir.glob("*.md")):
        if path.name in skip:
            continue
        text = path.read_text(encoding="utf-8")
        original = text
        for old, new in METHODOLOGY_REPLACEMENTS + PR_COUNT_REPLACEMENTS:
            text = text.replace(old, new)
        if text != original:
            path.write_text(text, encoding="utf-8")
            patched.append(path.name)
    return patched


def patch_findings_readme_index(findings_dir: Path) -> None:
    path = findings_dir / "README.md"
    if not path.exists():
        return
    contrib_path = get_analysis_dir() / "findings" / "data" / "contributor_analysis.json"
    if not contrib_path.exists():
        return
    data = json.loads(contrib_path.read_text(encoding="utf-8"))
    total = (data.get("summary") or {}).get("total_contributors")
    exit_rate = (data.get("retention") or {}).get("exit_rate_1yr")
    if not total or exit_rate is None:
        return
    text = path.read_text(encoding="utf-8")
    text = re.sub(
        r"    - [\d,]+ total contributors analyzed\n    - [\d.]+% exit rate \(1-year threshold\)",
        f"    - {total:,} total contributors analyzed\n    - {exit_rate * 100:.1f}% exit rate (1-year threshold)",
        text,
        count=1,
    )
    path.write_text(text, encoding="utf-8")
    logger.info("Patched findings/README.md contributor index")


def main() -> int:
    repo_root = project_root
    findings_dir = get_findings_dir()
    audit = load_audit()
    counts = canonical_counts(audit)

    patch_executive_summary_data_sources(findings_dir, counts)
    patch_research_methodology_irc(findings_dir, counts)
    patch_readme_data_sources(repo_root, counts)
    patch_data_sourcing(repo_root, counts)
    patch_findings_readme_index(findings_dir)
    patched = patch_findings_methodology_and_counts(findings_dir)

    print(f"Canonical counts: PRs={counts['prs']:,}, emails={counts['email_combined']:,}, IRC={counts['irc']:,}")
    print(f"Patched methodology/counts in {len(patched)} findings files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
