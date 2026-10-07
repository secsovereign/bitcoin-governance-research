# Bitcoin Core Governance Analysis: Findings Directory

**Start here**: `EXECUTIVE_SUMMARY.md` then `GOVERNANCE_FRAMES.md`.

**What uses which data:** GitHub merge/review reports (merge pattern, contributor retention, review-body quality, Gini, temporal) are **GitHub-only**. Informal channels (IRC, both mailing lists, Delving, Bitcointalk) are in `CROSS_PLATFORM_NETWORKS.md`, `INFORMAL_SENTIMENT_ANALYSIS.md`, `LANGUAGE_EVOLUTION.md`, `REVIEW_QUALITY_ENHANCED_ANALYSIS.md` (mention counts only), and the era table in `GOVERNANCE_FRAMES.md`. Do not treat a GitHub exit rate as “the whole community left.”

**Cite stored Bitcointalk posts (158,917), not topic `n_posts`.** The metadata field over-counts by ~18k (parser ceiling). Satoshi / architectural-divergence / technical-debt markdown files are separate dated analyses, not this report pipeline.

---

## Document Structure

### Core Reports (Essential Reading)

1. **`EXECUTIVE_SUMMARY.md`** ⭐ START HERE
   - Summary of all findings
   - Key metrics and insights

2. **`GOVERNANCE_FRAMES.md`** ⭐ HOW TO CUT THIS CORPUS
   - Agenda-setting vs decision by era
   - Funnel / deputy graph as informal org chart
   - Multiplex identity (power is not portable)
   - Exit as selection, not collapse

2b. **`ARCHIVE_GEMS.md`** ⭐ QUOTES THE FRAMES POINTED AT
   - Satoshi, stalled BIPs, list → GitHub, process NACKs
   - Machine list: `ARCHIVE_GEMS_INDEX.md`

3. **`GLOSSARY_AND_CONTEXT.md`** ⭐ FOR NON-EXPERTS
   - Bitcoin Core terminology explained
   - ACK, NACK, maintainer roster vs merge keys vs cannot-merge
   - Why metrics matter
   - Historical context

4. **`MERGE_PATTERN_BREAKDOWN.md`**
   - Detailed merge analysis
   - Self-merge breakdown, friend patterns, individual maintainer patterns

5. **`TEMPORAL_ANALYSIS_REPORT.md`**
   - Temporal patterns (yearly, quarterly, generational)
   - Process improvements vs structural persistence
   - Speed hack (time-to-merge) by period
   - PR importance analysis by period
   - Power concentration by period
   - Review quality by period
   - Response time inequality analysis
   - Network evolution over time
   - Voting bloc temporal evolution
   - Conflict resolution temporal evolution

6. **`NOVEL_INTERPRETATIONS.md`**
   - Behavioral clusters, power hierarchy, review reciprocity
   - Novel insights from data

6. **`INTERDISCIPLINARY_ANALYSIS_REPORT.md`**
   - Network science, game theory, information theory
   - Multi-disciplinary perspectives

7. **`GINI_COEFFICIENT_EXPLANATION.md`**
   - Gini coefficient explanation and values
   - Inequality metrics

8. **`REVIEW_QUALITY_ENHANCED_ANALYSIS.md`**
   - Review quality metrics
   - Temporal trends in review depth

9. **`ENHANCED_FUNDING_ANALYSIS_REPORT.md`**
   - Funding mention analysis
   - Temporal patterns, correlations

10. **`EXTERNAL_RESEARCH_COMPARISON.md`** ⭐
    - Comparison with BitMEX Research, Angela Walch, Stanford JBLP
    - What external research found vs. what we add
    - Unique contributions and quantitative metrics

11. **`RESEARCH_METHODOLOGY.md`** ⭐ METHODOLOGY
    - Comprehensive methodology documentation
    - Data collection, processing, analysis methods
    - Review counting methodology (detailed)
    - Validation procedures (including statistical validation)
    - Limitations and assumptions
    - Reproducibility guide

12. **`STATISTICAL_DEFENSE_RESULTS.md`** ⭐ STATISTICAL VALIDATION
    - Complete results of all statistical defense analyses
    - Sensitivity analysis, MAX vs. SUM, uniform threshold, statistical tests
    - Validates robustness of methodological choices

13. **`CRITICAL_REVIEW_ADVERSARIAL.md`** ⭐ VALIDATION
    - Adversarial review of methodology
    - Identified vulnerabilities and fixes
    - Strengthens defensibility

14. **`SATOSHI_GOVERNANCE_INSIGHTS.md`** ⭐ HISTORICAL CONTEXT
    - Analysis of 549 Satoshi Nakamoto communications (2008-2015)
    - Governance philosophy and principles
    - Comparison with current Bitcoin Core governance
    - Historical baseline for evaluation

15. **`SATOSHI_GOVERNANCE_ANALYSIS.md`**
    - Detailed technical analysis of Satoshi's communications
    - Governance mentions, decision patterns, authority statements
    - Full data and excerpts

16. **`MAINTAINER_LIST_SOURCE.md`**
    - Maintainer list documentation and validation
    - Current vs historical maintainers

### Supporting Analysis

17. **`PR_IMPORTANCE_ANALYSIS.md`** ⭐
    - PR classification by importance (trivial, low, normal, high, critical)
    - Zero-review rates by PR type
    - Review quality matrix analysis
    - Addresses "housekeeping doesn't need review" argument

18. **`MAINTAINER_TIMELINE_ANALYSIS.md`** - Maintainer activity timeline (includes current vs historical distinction)
19. **`CONTRIBUTOR_TIMELINE_ANALYSIS.md`** - Contributor activity timeline
20. **`CONTRIBUTOR_ANALYSIS.md`** ⭐ CONTRIBUTOR RETENTION
    - 7,827 total contributors analyzed
    - 90.7% exit rate (1-year threshold)
    - Breakdown by type (authors vs participants)
21. **`BCAP_INTEGRATION_REPORT.md`** - BCAP framework integration analysis
    - State of Mind (SOM) analysis during SegWit/Taproot
    - Power shift analysis during consensus changes
    - Based on [BCAP (Bitcoin Consensus Analysis Project)](https://github.com/bitcoin-cap/bcap)
22. **`CROSS_PLATFORM_NETWORKS.md`** - Cross-platform influence analysis (GitHub, IRC, ML lists, Delving, Bitcointalk)
    - GitHub / IRC / ML / Delving / Bitcointalk overlap analysis
    - Verified maintainer identities across platforms
23. **`INFORMAL_SENTIMENT_ANALYSIS.md`** - Informal-channel sentiment/SOM (IRC, ML lists, Delving, Bitcointalk)
    - Sentiment distribution across informal channels
    - State of Mind (SOM) analysis on informal channels
24. **`BIP_PROCESS_ANALYSIS.md`** - BIP governance analysis
    - Proposer/champion patterns
    - BIP-to-Core implementation pipeline
25. **`RELEASE_SIGNING_ANALYSIS.md`** - Release signing authority
    - Signer concentration analysis
    - Signing patterns over time
26. **`CROSS_REPO_COMPARISON.md`** - Core vs BIP repository comparison
    - Actor overlap analysis
    - Governance pattern comparison
27. **`CONFLICT_RESOLUTION_ANALYSIS.md`** ⭐ CONFLICT ANALYSIS
    - Conflicts from temporal + voting-bloc detectors (see generated report for current n)
    - Resolution paths and timing analysis
    - Temporal evolution of conflicts
    - Voting bloc behavior during conflicts
28. **`COORDINATION_COSTS_ANALYSIS.md`** ⭐ COORDINATION OVERHEAD
    - Communication volume per PR (reviews + comments; see generated report)
    - Coordination costs by complexity (high vs low band)
    - Participant and decision time analysis
    - Governance complexity scaling with code complexity
29. **`TECHNICAL_DEBT_ANALYSIS.md`** ⭐ TECHNICAL DEBT
    - 26.8% of codebase has high technical debt (1,108 files)
    - Patch-to-refactor ratio: 3.0 (debt accumulation)
    - RPC subsystem highest debt (61.5% high debt files)
    - Quantifies technical debt in Bitcoin Core codebase
30. **`ARCHITECTURAL_DIVERGENCE_FINAL_REPORT.md`** ⭐ CORE vs COMMONS (SINGLE FINAL REPORT)
    - Findings, methodology, validation, citations, exemplars, limitations, reproducibility
    - Recomputed from primary data (2026-07-12)
31. **`MAINTAINER_PREMIUM_REPORT.md`** — Identity vs merits (fair pass: self-merge, author-prep matching, path-risk)
32. **`STALLED_PROPOSALS_REPORT.md`** — Dandelion / Erlay / related case dossiers
33. **`MERGE_CONCENTRATION_DEPUTIES_REPORT.md`** — 2022+ fanquake share + co-review funnels
34. **`LANGUAGE_EVOLUTION.md`** — terminology trends across GitHub + informal channels
35. **`REJECTION_ANATOMY.md`** — high-stakes episode rows (objections empty until BTCDecoded cites)
36. **`STALLED_AGREEMENT_LEDGER.md`** — stated-agreement / unmerged candidates (`nack_exists` unknown until cited); not `STALLED_PROPOSALS.md`
37. **`VOCABULARY_AUDIT.md`** — phrase × process/technical context (counts empty)
38. **`CONTRIBUTOR_CROSS_REF.md`** — same person across episodes via `canonical_key`; not an identity store
39. **`REVEALED_ROUGH_CONSENSUS.md`** — ACK/NACK/review vectors on PRs a merge-key holder merged (`CONTRIBUTING.md` judgment, not a vote)
40. **`INGROUP_REVIEW_TREATMENT.md`** — in-group versus out-group review treatment on decided pull requests
41. **`NEWCOMER_BAR.md`** — newcomer versus incumbent slopes, and the project-wide reviewer-load test
42. **`COMMONS_MECHANISMS.md`** — six confirmed attention effects and the shared-indicator rank
43. **`FIRST_YEAR_TRAJECTORY.md`** — first-year merge gap, the 340 patch-content leavers, and the silence slope
44. **`GAP_CLOSURE.md`** — lagged principle scores, the cross-repository limit, the false-negative timeline, and subsystem silence

Related data: `data/maintainer_premium.json`, `author_prep_sensitivity.json`, `high_prep_outsider_closed_sample.json`, `stalled_proposal_dossiers.json`, `high_volume_merger_deputies.json`, `governance_episode_ledger.json`, `revealed_rough_consensus.json`, `rsd_ingroup_analysis.json`, `rsd_ingroup_analysis_v2.json`, `commons_dynamics_analysis.json`, `first_year_signal_analysis.json`, `gap_closure_analysis.json`

---

## Reading Order

**Quick Overview** (5 minutes):
1. `EXECUTIVE_SUMMARY.md`
2. `GOVERNANCE_FRAMES.md`

**Full Understanding** (30 minutes):
1. `EXECUTIVE_SUMMARY.md`
2. `GOVERNANCE_FRAMES.md`
3. `MERGE_PATTERN_BREAKDOWN.md`
4. `TEMPORAL_ANALYSIS_REPORT.md`

**Later measurements** (after the frames):
1. `REVEALED_ROUGH_CONSENSUS.md`
2. `NEWCOMER_BAR.md` and `INGROUP_REVIEW_TREATMENT.md`
3. `COMMONS_MECHANISMS.md` and `FIRST_YEAR_TRAJECTORY.md`
4. `GAP_CLOSURE.md` for the tables those two close with

**Deep Dive** (2+ hours):
- Read all Core Reports
- Review Supporting Analysis as needed
- Check Reference Documents for specific questions

---

## Data Files

**Location**: `data/` subdirectory

All JSON data files are organized in the `data/` subdirectory for cleaner organization:
- Analysis results (for programmatic access)
- Network data for visualization
- Statistical validation results
- Timeline analyses
- Pattern analyses

**Note**: Markdown reports reference these files with paths like `data/filename.json`

---

## Archive

- Older/redundant documents kept for reference in repository archives

---

**Regenerate cross-platform reports** (after re-running analyses):

```bash
venv/bin/python scripts/reporting/generate_findings_reports.py
# or: venv/bin/python scripts/run_all_analyses.py --reports
```

**Last Updated**: 2026-10-07  
**Status**: Frames unchanged. Items 35–44 are the episode ledger, revealed consensus, and the five measurement passes.
