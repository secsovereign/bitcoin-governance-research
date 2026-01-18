# Gini Coefficient: Explanation and Bitcoin Core Analysis

**Date**: 2026-01-07  
**Last Updated**: 2026-01-07 (cross-platform integration, PR importance analysis)  
**Methodology**: Quality-weighted review counting (GitHub, ACK, IRC, email), cross-platform integrated, PR importance classification

---

## What is the Gini Coefficient?

The **Gini coefficient** is a measure of inequality, ranging from 0 to 1:

- **0.0** = Perfect equality (everyone contributes equally)
- **1.0** = Perfect inequality (one person does everything)

**Common thresholds:**
- **< 0.3**: Low inequality
- **0.3 - 0.6**: Moderate inequality
- **≥ 0.6**: High/extreme inequality

**Example**: If 10 people each contribute 10%, Gini = 0.0. If one person contributes 90% and 9 people contribute 1.1% each, Gini ≈ 0.8.

---

## Bitcoin Core Gini Coefficients

### Contribution Inequality (PR Authorship)

**Historical Period (2012-2020)**:
- **Gini coefficient**: 0.851
- **Status**: **EXTREME INEQUALITY** (42% above the 0.6 threshold)
- **Top 10 authors**: 42.7% of all PRs

**Recent Period (2021-2025)**:
- **Gini coefficient**: 0.837
- **Status**: **EXTREME INEQUALITY** (40% above the 0.6 threshold)
- **Top 10 authors**: 49.8% of all PRs

**Change**: Minimal improvement (0.851 → 0.837, -1.6%), still extreme inequality.

**Interpretation**: Contribution is highly concentrated. A small number of authors account for the majority of PRs, with minimal change over time.

**Temporal analysis**: See `TEMPORAL_ANALYSIS_REPORT.md` for detailed power concentration metrics by period, including merge authority concentration (who merges PRs) in addition to authorship concentration.

---

### Review Concentration (Review Inequality)

**Historical Period (2012-2020)**:
- **Gini coefficient**: 0.922
- **Status**: **EXTREME INEQUALITY**
- **Top 5 reviewers**: 32.7% of all reviews
- **Top 10 reviewers**: ~55% of all reviews

**Recent Period (2021-2025)**:
- **Gini coefficient**: 0.925
- **Status**: **EXTREME INEQUALITY**
- **Top 5 reviewers**: 25.3% of all reviews
- **Top 10 reviewers**: ~54% of all reviews

**Change**: Slight increase (0.922 → 0.925, +0.3%), still extreme inequality.

**Interpretation**: Review activity is even more concentrated than contributions. A very small number of reviewers account for the majority of reviews.

---

## Comparison: Contribution vs Review Inequality

| Metric | Historical | Recent | Change |
|--------|-----------|--------|--------|
| **Contribution Gini** | 0.851 | 0.837 | -1.6% (slight improvement) |
| **Review Gini** | 0.922 | 0.925 | +0.3% (slight increase) |

**Pattern**: 
- Both show extreme inequality (well above 0.6 threshold)
- Contribution inequality improved slightly
- Review inequality increased slightly
- Review concentration is higher than contribution concentration

---

## Interpretation

### Extreme Inequality

**Bitcoin Core's Gini coefficients (0.84-0.93) indicate:**
- **Extreme concentration**: Small number of people control most activity
- **Persistent pattern**: Minimal change over time despite process improvements
- **Structural characteristic**: Not a temporary phenomenon

### Context

**For comparison:**
- **Income inequality (US)**: ~0.48 (moderate-high)
- **Income inequality (most unequal countries)**: ~0.60-0.65
- **Bitcoin Core contribution**: 0.84-0.85 (extreme)
- **Bitcoin Core reviews**: 0.92-0.93 (extreme)

**Bitcoin Core's inequality is comparable to or exceeds the most unequal countries in terms of income distribution.**

---

## Overall Pattern

### Extreme Concentration Across All Metrics

1. **Contributions**: Gini 0.84 (top 10 = 50% of PRs)
2. **Reviews**: Gini 0.93 (top 10 = 54% of reviews)
3. **Merges**: Top 3 = 81.1% of merges
4. **Release signing**: 7 people over 16 years (top signer = 51%)

**Pattern**: Extreme concentration is consistent across all governance functions.

---

## Implications

### Structural Characteristic

**Extreme inequality is:**
- **Persistent**: Minimal change over time
- **Consistent**: Present across all metrics
- **Structural**: Not a temporary phenomenon

### Governance Impact

**High concentration means:**
- **Single points of failure**: Few people control critical functions
- **Limited diversity**: Small group makes most decisions
- **Barrier to participation**: High concentration may discourage new contributors
- **Power concentration**: Authority concentrated in few hands

---

## Data Sources

- **Analysis**: Historical analysis from `comprehensive_recent_analysis.py` (legacy script). Current analyses use `scripts/run_all_analyses.py`.
- **Periods**: Historical (2012-2020) vs Recent (2021-2025)
- **Data**: 23,478 PRs, 9,235 maintainer merged PRs with merged_by data

---

## Key Takeaways

1. **Extreme inequality**: Gini 0.84-0.93 (well above 0.6 threshold)
2. **Persistent pattern**: Minimal change over time
3. **Consistent across metrics**: Contributions, reviews, merges all show extreme concentration
4. **Structural issue**: Not a temporary phenomenon
5. **Increased concentration**: Top 10 control increased from 42.7% to 49.8%
