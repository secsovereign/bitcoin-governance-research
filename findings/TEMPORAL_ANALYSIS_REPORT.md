# Comprehensive Temporal Analysis Report

**Date**: 2026-01-07  
**Last Updated**: 2026-01-07 (quality-weighted review counting, consistency fixes)  
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

## 5. Maintainer Lifecycle

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
- **Analysis date**: 2026-01-07

---

## Files

- **Analysis script**: `scripts/analysis/temporal_analysis.py`
- **Results**: `findings/temporal_analysis.json`
- **This report**: `findings/TEMPORAL_ANALYSIS_REPORT.md`
