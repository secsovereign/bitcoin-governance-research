# Comprehensive Temporal Analysis Report

**Date**: 2026-01-07  
**Last Updated**: 2026-01-24 (response time inequality, network evolution, voting bloc temporal, conflict resolution temporal added)  
**Purpose**: Extract maximum useful information from temporal patterns  
**Methodology**: Quality-weighted review counting (GitHub, ACK, IRC, email), cross-platform integrated, PR importance classification, timeline-aware ACK handling, MAX per reviewer (ACK=0.3, detailed review=1.0, threshold=0.5 for recent era)

---

## Executive Summary

Temporal analysis reveals significant changes in Bitcoin Core governance patterns over time, with clear generational shifts and behavioral evolution among maintainers.

---

## 1. Temporal Self-Merge Patterns

### Year-by-Year Analysis (2016-2025)

| Year | Total PRs | Self-Merge Rate | Zero-Review Self-Merge | Avg Reviews |
|------|-----------|-----------------|------------------------|-------------|
| 2016 | 666 | 23.3% | 83.9% | 1.0 |
| 2017 | 660 | 15.5% | 42.2% | 4.9 |
| 2018 | 648 | 19.0% | 36.6% | 5.7 |
| 2019 | 768 | 24.0% | 38.0% | 5.5 |
| 2020 | 957 | 26.4% | 32.0% | 7.3 |
| 2021 | 929 | 30.4% | 24.1% | 6.3 |
| 2022 | 848 | 28.5% | 10.7% | 5.1 |
| 2023 | 682 | 24.8% | 11.2% | 6.7 |
| 2024 | 644 | 24.7% | 0.6% | 9.7 |
| 2025 | 619 | 21.6% | 3.7% | 9.6 |

### Key Findings

1. **Self-merge rate relatively stable**: 21-30% range, no dramatic decline
2. **Zero-review self-merge dramatically reduced**: 83.9% (2016) → 3.7% (2025) - **95.6% reduction** (quality-weighted)
3. **Review depth increased**: 1.0 reviews (2016) → 9.6 reviews (2025) - **9.6x increase**
4. **Process improvement**: While self-merge rate stable, zero-review self-merge nearly eliminated

**Note**: Zero-review rates use quality-weighted counting (ACK=0.3, detailed review=1.0, threshold=0.5). ACKs after detailed reviews are ignored as completion signals.

### PR Type Breakdown

**By PR importance** (all time):
- **Trivial PRs**: 36.4% zero-review (housekeeping, typo fixes)
- **Low importance**: 31.5% zero-review (documentation, tests)
- **Critical PRs**: 23.2% zero-review (consensus, security, protocol)

**Insight**: Even trivial/housekeeping PRs have high zero-review rates. Critical PRs get more review (as they should), but all types still have significant zero-review rates.

---

## 2. Maintainer Era Patterns

### Generational Differences

| Era | Members | Self-Merge Rate | Zero-Review Rate | Avg Reviews |
|-----|---------|----------------|------------------|-------------|
| **Early 2010s** (2010-2013) | 10 | 36.9% | 59.1% | 2.9 |
| **Mid 2010s** (2014-2016) | 6 | 23.6% | 23.6% | 6.3 |
| **Late 2010s** (2017-2019) | 3 | 1.3% | 18.1% | 6.8 |
| **2020s** (2020+) | 1 | 8.4% | 2.3% | 19.7 |

### Key Findings

1. **Clear generational shift**: Newer maintainers have much lower self-merge rates
   - Early 2010s: 36.9%
   - Late 2010s: 1.3%
   - 2020s: 8.4%

2. **Review depth increased dramatically**: 
   - Early 2010s: 2.9 reviews
   - 2020s: 19.7 reviews (6.8x increase)

3. **Zero-review rate declined**: 
   - Early 2010s: 59.1%
   - 2020s: 2.3% (96.1% reduction)

**Interpretation**: Newer maintainers follow stricter standards, suggesting either:
- Process improvements over time
- Different selection criteria for newer maintainers
- Cultural shift toward more review

---

## 3. Quarterly Trends (Recent)

### Last 8 Quarters

| Quarter | Total | Self-Merge | Zero-Review | Avg Reviews |
|---------|-------|------------|-------------|-------------|
| 2024-Q1 | 137 | 23.4% | 4.4% | 8.5 |
| 2024-Q2 | 175 | 32.6% | 7.4% | 8.3 |
| 2024-Q3 | 203 | 21.2% | 2.5% | 12.0 |
| 2024-Q4 | 129 | 20.9% | 0.0% | 9.3 |
| 2025-Q1 | 154 | 13.0% | 4.5% | 10.3 |
| 2025-Q2 | 183 | 19.1% | 4.9% | 10.5 |
| 2025-Q3 | 151 | 26.5% | 6.0% | 9.4 |
| 2025-Q4 | 131 | 29.8% | 5.3% | 7.9 |

### Key Findings

1. **Self-merge rate variable**: 13-33% range, no clear trend
2. **Zero-review rate low and stable**: 0-7% range (much improved from historical)
3. **Review depth high**: 7.9-12.0 reviews (consistent high review standards)

---

### Individual Maintainer Evolution

**laanwj** (High-volume maintainer):
- 2010-2015: 83.6% self-merge, 0.0 avg reviews
- 2016-2020: 75.4% self-merge, 1.9 avg reviews
- 2021-2025: 36.5% self-merge, 10.0 avg reviews
- **Change**: 47.1 percentage point reduction in self-merge, 10x increase in reviews

**sipa** (Core maintainer):
- 2010-2015: 30.8% self-merge, 0.0 avg reviews
- 2016-2020: 10.0% self-merge, 10.3 avg reviews
- 2021-2025: 0.0% self-merge, 21.9 avg reviews
- **Change**: Eliminated self-merge entirely, 21.9x increase in reviews

**gmaxwell** (Security-focused):
- 2010-2015: 12.7% self-merge, 0.0 avg reviews
- 2016-2020: 0.0% self-merge, 3.4 avg reviews
- **Change**: Eliminated self-merge, increased reviews

### Key Findings

1. **Individual evolution**: Many maintainers reduced self-merge rates over time
2. **Review depth increased**: All maintainers show increased review counts
3. **Some eliminated self-merge**: sipa, gmaxwell, luke-jr eliminated self-merge entirely
4. **High-volume maintainers slower to change**: laanwj still has 36.5% self-merge in recent period

---

## 4. Behavioral Changes Over Time

**Question**: How did individual maintainer behavior change over time?

### Key Findings

1. **Individual evolution**: Many maintainers reduced self-merge rates over time
2. **Review depth increased**: All maintainers show increased review counts
3. **Some eliminated self-merge**: sipa, gmaxwell, luke-jr eliminated self-merge entirely
4. **High-volume maintainers slower to change**: laanwj still has 36.5% self-merge in recent period

**Note**: Detailed behavioral changes by maintainer are available in the analysis data. See `data/temporal_analysis.json` for complete maintainer-by-maintainer breakdown.

---

## 5. Speed Hack Temporal Analysis

**Question**: Did the "speed hack" (self-merged PRs merging 2x faster) persist over time?

### Time-to-Merge by Period

| Period | Self-Merge Avg Days | Other-Merge Avg Days | Speed Ratio | Self-Merge Count | Other-Merge Count |
|--------|---------------------|---------------------|-------------|------------------|-------------------|
| **Historical (2012-2020)** | 10.3 | 24.9 | **2.4x** | 1,422 | 3,926 |
| **Recent (2021-2025)** | 22.7 | 41.5 | **1.8x** | 986 | 2,736 |
| **All-Time** | 15.3 | 31.2 | **2.0x** | 2,446 | 6,789 |

### Key Findings

1. **Speed hack persists**: Self-merged PRs merge faster in both periods
2. **Historical period**: 2.4x faster (10.3 vs 24.9 days)
3. **Recent period**: 1.8x faster (22.7 vs 41.5 days) - **speed advantage decreased**
4. **Absolute times increased**: Both self-merge and other-merge times increased in recent period (process got slower overall, but speed advantage remains)

---

## 6. PR Importance Temporal Analysis

**Question**: Did review quality by PR importance change over time?

### Zero-Review Rates by PR Type and Period

**Note**: PR importance classification is simplified in temporal analysis. Full classification available in `PR_IMPORTANCE_ANALYSIS.md.

| Period | PR Type | Total | Zero Review | Zero-Review Rate | Self-Merge Rate |
|---------|---------|-------|-------------|------------------|-----------------|
| **Historical** | All PRs | 5,348 | 3,461 | **64.7%** | 26.6% |
| **Recent** | All PRs | 3,722 | 1,212 | **32.6%** | 26.5% |

**All-time aggregate** (from `PR_IMPORTANCE_ANALYSIS.md`):
- Critical PRs: 23.2% zero-review
- Trivial PRs: 36.4% zero-review

**Key Finding**: Zero-review rate improved dramatically (64.7% → 32.6%), but self-merge rate remained stable (26.6% → 26.5%).

---

## 7. Power Concentration Temporal Analysis

**Question**: Did power concentration increase or decrease over time?

### Concentration Metrics by Period

| Period | Top 3 Control | Top 10 Control | Unique Mergers | Top Mergers |
|--------|---------------|----------------|----------------|-------------|
| **Historical (2012-2020)** | **81.0%** | 100% | 9 | laanwj (54.2%), maflcko (20.7%), fanquake (6.1%) |
| **Recent (2021-2025)** | **84.5%** | 100% | 9 | fanquake (55.1%), maflcko (21.0%), achow101 (8.3%) |

### Key Findings

1. **Power concentration increased**: Top 3 control increased from 81.0% → 84.5%
2. **Concentration calcified**: Same 9 unique mergers in both periods
3. **Top 3 shifted**: Historical (laanwj, maflcko, fanquake) → Recent (fanquake, maflcko, achow101)
4. **laanwj stepped back**: From 54.2% (historical) to 8.0% (recent)
5. **fanquake dominance**: Increased from 6.1% (historical) to 55.1% (recent)

**All-time aggregate**: Top 3 control 81.1% of merges (from merge pattern analysis).

---

## 8. Review Quality Temporal Analysis

**Question**: Did review quality improve over time?

### Review Quality Metrics by Period

| Period | Total PRs | Zero Review | Zero-Review Rate | Avg Review Score | Avg Review Count |
|--------|-----------|-------------|------------------|------------------|------------------|
| **Historical (2012-2020)** | 5,348 | 3,461 | **64.7%** | 3.05 | 3.5 |
| **Recent (2021-2025)** | 3,722 | 1,212 | **32.6%** | 5.67 | 7.2 |

### Key Findings

1. **Zero-review rate improved**: 64.7% → 32.6% (49.6% reduction)
2. **Review depth increased**: 3.5 → 7.2 reviews (2.1x increase)
3. **Review quality increased**: 3.05 → 5.67 review score (1.9x increase)
4. **Significant improvement**: All review quality metrics improved substantially

**Note**: These numbers use simplified review scoring. Quality-weighted analysis (see `RESEARCH_METHODOLOGY.md`) shows 30.2% historical → 3.4% recent (88.7% reduction) using proper quality weighting.

---

## 9. Response Time Inequality Analysis

### Findings

**Overall response time inequality**:
- **First review**: Nearly equal (12.3h vs 12.4h median) - no bias in initial response
- **Merge time**: 1.41x inequality (non-maintainers wait 41% longer: 145.4h vs 93.3h median)

**Response time by complexity**:
- **Low complexity**: 1.51x merge inequality, 1.08x review inequality
- **Medium complexity**: 1.56x merge inequality (highest), 0.73x review inequality
- **High complexity**: 1.35x merge inequality, 0.42x review inequality (lowest)

### Key Findings

1. **No bias in first review**: Maintainer and non-maintainer PRs get reviewed at nearly the same speed
2. **Merge time inequality**: Non-maintainers wait 41% longer to merge
3. **Complexity effect**: Review inequality decreases with complexity (complex PRs get faster reviews regardless of author status)
4. **Merge inequality highest for medium complexity**: Suggests medium complexity PRs face the most status-based delays

**Interpretation**: 
- Initial review is fair, but merge decisions favor maintainers
- Complex PRs get urgent attention regardless of author status (complexity creates urgency)
- Medium complexity PRs face the most inequality (not urgent enough to override status bias, but complex enough to require review)

---

## 10. Temporal Network Evolution

### Findings

**Network concentration over time** (top 3 control):
- **2020**: 91.3% concentration (225 nodes)
- **2021**: 96.7% concentration (257 nodes)
- **2022**: 93.6% concentration (229 nodes)
- **2023**: 95.9% concentration (192 nodes)
- **2024**: 93.8% concentration (217 nodes)
- **2025**: 90.0% concentration (214 nodes)

**Network size**: 192-257 nodes (varies by year, 214-217 in recent years)

**Top merger by year**: fanquake consistently top merger in recent years (2022-2025)

### Key Findings

1. **90%+ concentration persists**: Top 3 maintainers control 90%+ of merges consistently
2. **No decentralization trend**: Concentration remains high over 16 years
3. **Network size stable**: 192-257 nodes (214-217 in recent years)
4. **Power structure calcified**: fanquake dominates recent years

**Interpretation**: 
- Network concentration is structural, not temporary
- Power structure hasn't decentralized over time
- Recent dominance by fanquake suggests further concentration, not distribution

---

## 11. Voting Bloc Temporal Evolution

### Findings

**Voting bloc cohesion over time** (2016-2025):
- **2016**: 100% cohesion (1 voting pair)
- **2017**: 100% cohesion (3 voting pairs)
- **2019**: 97.1% cohesion (7 voting pairs)
- **2020**: 95.8% cohesion (12 voting pairs)
- **2021**: 87.8% cohesion (8 voting pairs)
- **2022**: 92.9% cohesion (9 voting pairs)
- **2023**: 100% cohesion (9 voting pairs)
- **2024**: 98.3% cohesion (12 voting pairs)
- **2025**: 98.3% cohesion (10 voting pairs)

**Strong blocs** (>80% cohesion): 0-12 per year

### Key Findings

1. **High cohesion persists**: 87.8% to 100% across all years
2. **Stable over time**: No decline in voting bloc cohesion
3. **More blocs over time**: Number of voting pairs increased (1 → 12)

**Interpretation**: 
- Voting blocs are stable structural features
- Cohesion remains high over time (no breakdown)
- More blocs form over time, but cohesion stays high

---

## 12. Conflict Resolution Temporal Evolution

### Findings

**Conflict rates over time** (2016-2025):
- **2016**: 9.3% conflict rate (146 conflicts)
- **2017**: 14.0% conflict rate (257 conflicts)
- **2018**: 13.3% conflict rate (276 conflicts)
- **2019**: 15.8% conflict rate (309 conflicts) - **peak**
- **2020**: 15.8% conflict rate (336 conflicts) - **peak**
- **2021**: 12.4% conflict rate (248 conflicts)
- **2022**: 11.9% conflict rate (239 conflicts)
- **2023**: 12.1% conflict rate (192 conflicts)
- **2024**: 12.8% conflict rate (210 conflicts)
- **2025**: 13.1% conflict rate (240 conflicts)

**Resolution time over time**:
- **2016**: 125.5 days average
- **2017**: 122.8 days average
- **2019**: 160.1 days average (peak)
- **2020**: 138.3 days average
- **2021**: 169.9 days average (peak)
- **2025**: 47.0 days average - **significant improvement**

### Key Findings

1. **Conflict rate stable**: 9-16% of PRs have conflicts
2. **Peak conflicts**: 2019-2020 had highest conflict rates (15.8%)
3. **Resolution time improving**: 47 days in 2025 (down from 160+ days)
4. **Conflicts are common**: 9-16% of PRs experience conflicts

**Interpretation**: 
- Conflicts are a regular feature of governance (not rare)
- Conflict resolution processes have improved significantly (47 days vs 160+ days)
- Peak conflicts in 2019-2020 may correlate with major events (Taproot, etc.)

---

## 13. Maintainer Lifecycle

### First PR Patterns

- **First PR merged rate**: Analysis of maintainer first PRs
- **Time to first merge**: Patterns in how quickly maintainers' first PRs were merged
- **Path to maintainer status**: Evolution from first PR to maintainer

**Note**: Full lifecycle analysis requires maintainer history data (can be enhanced with maintainers_history_collector.py)

---

## Key Temporal Insights

### 1. Process Improvements Are Real

- **Zero-review self-merge**: 95.6% reduction (2016: 83.9% → 2025: 3.7%)
- **Review depth**: 9.6x increase (2016: 1.0 → 2025: 9.6)
- **These improvements are significant and measurable**

### 2. Self-Merge Rate Stable

- **Self-merge rate**: Relatively stable at 21-30% range
- **Not declining**: Despite process improvements, self-merge rate hasn't decreased
- **Structural issue persists**: The capability and practice remain

### 3. Generational Divide

- **Early maintainers**: Higher self-merge rates (36.9%)
- **Newer maintainers**: Much lower rates (1.3-8.4%)
- **Cultural shift**: Newer maintainers follow stricter standards

### 4. Individual Evolution

- **Many maintainers improved**: Reduced self-merge, increased reviews
- **Some eliminated self-merge**: sipa, gmaxwell, luke-jr
- **High-volume maintainers slower**: laanwj still 36.5% in recent period

---

## Implications

### Process vs Structure

1. **Process improvements**: Zero-review merges dramatically reduced, review depth increased
2. **Structural persistence**: Self-merge rate stable, capability remains exclusive
3. **Mixed picture**: Better processes but same structural issues

### Governance Evolution

1. **Cultural shift**: Newer maintainers follow stricter standards
2. **Individual variation**: Some maintainers evolved, others didn't
3. **No formal rules**: Changes appear cultural, not rule-based

---

## Data Sources

- **PRs analyzed**: 23,478 PRs (2009-2025)
- **Maintainer PRs**: 9,235 merged PRs
- **Temporal coverage**: Full repository history
- **Analysis date**: 2026-01-24

---

## Files

- **Analysis script**: `scripts/analysis/temporal_analysis.py`
- **Results**: `data/temporal_analysis.json`
- **This report**: `TEMPORAL_ANALYSIS_REPORT.md`
