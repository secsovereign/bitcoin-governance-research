# Enhanced Funding Analysis Report

**Date**: 2026-01-07  
**Last Updated**: 2026-01-07 (cross-platform integration, PR importance analysis)  
**Purpose**: Extract maximum structured information from funding mentions  
**Methodology**: Quality-weighted review counting (GitHub, ACK, IRC, email), cross-platform integrated, PR importance classification

---

## 1. Temporal Funding Patterns

### Year-by-Year Analysis (2016-2025)

| Year | Total PRs | Funding Rate | Top Type | Top Source |
|------|-----------|--------------|----------|------------|
| 2016 | 1,562 | 0.9% | salary | mit |
| 2017 | 1,842 | 0.8% | salary | mit |
| 2018 | 2,081 | 0.5% | salary | N/A |
| 2019 | 1,954 | 0.7% | salary | coinbase |
| 2020 | 2,122 | 1.8% | donation | block |
| 2021 | 1,994 | 1.0% | salary | block |
| 2022 | 2,002 | 1.1% | donation | mit |
| 2023 | 1,581 | 1.6% | donation | mit |
| 2024 | 1,637 | 1.1% | salary | mit |
| 2025 | 1,747 | 1.3% | donation | block |

### Key Findings

1. **Low mention rate**: 0.5-1.8% of PRs mention funding (very low)
2. **Temporal variation**: Funding mentions increased in 2020 (1.8%) and 2023 (1.6%)
3. **Top types**: Salary and donation are most common
4. **Top sources**: MIT, Block (Square), Coinbase frequently mentioned

---

## 2. Enhanced Funding Correlation

### With vs Without Funding Mentions

| Metric | With Funding | Without Funding | Difference |
|--------|-------------|-----------------|------------|
| **Merge rate** | 58.8% | 67.6% | **-8.8 pp** (worse) |
| **Avg time to merge** | 48.2 days | 31.4 days | **+16.8 days** (slower) |
| **Avg reviews** | 9.7 | 5.6 | **+4.1 reviews** (more scrutiny) |

### Key Findings

1. **Lower merge rate**: PRs with funding mentions have 8.8 percentage point lower merge rate
2. **Slower merges**: 16.8 days slower on average
3. **More reviews**: 4.1 more reviews on average (73% more)
4. **Counterintuitive**: Funding mentions correlate with worse outcomes, not better

### Interpretation

**Possible explanations**:
1. **Complexity**: Funded work may be more complex, requiring more review
2. **Scrutiny**: Funding disclosure may trigger additional scrutiny
3. **Controversy**: Funded work may be more controversial
4. **Selection bias**: People mention funding when asking for help/review

**Note**: This does NOT mean funding causes worse outcomes. Correlation ≠ causation.

---

## 4. Maintainer vs Non-Maintainer Funding

### Patterns

- **Maintainer funding rate**: Similar to overall rate
- **Non-maintainer funding rate**: Similar to overall rate
- **No significant difference**: Funding mentions don't vary by maintainer status

---

## Key Insights

### 1. Funding Mentions Are Rare

- **Only 0.5-1.8%** of PRs mention funding
- **Very low visibility**: Most funding is not publicly disclosed in PRs
- **Limitation**: This analysis only covers public mentions, not actual funding

### 2. Counterintuitive Correlation

- **Funding mentions = worse outcomes**: Lower merge rate, slower merges, more reviews
- **Not preferential treatment**: If anything, funding mentions correlate with more scrutiny
- **May reflect complexity**: Funded work might be more complex/controversial

### 3. Temporal Patterns

- **2020 spike**: Funding mentions increased (1.8%)
- **2023 increase**: Another increase (1.6%)
- **Generally stable**: Most years 0.5-1.1%

---

## Limitations

### Data Limitations

1. **Only mentions**: This analysis covers funding mentions, not actual funding
2. **No amounts**: Cannot determine funding amounts from mentions
3. **Incomplete**: Most funding is likely not mentioned in PRs
4. **Private data**: Actual funding data is private

### What We Cannot Know

1. **Actual funding amounts**: Not publicly available
2. **All funding sources**: Only those mentioned in PRs
3. **Funding recipients**: Cannot determine who received funding
4. **Funding influence**: Cannot determine if funding affects decisions

---

## Recommendations

### For Analysis

1. **Acknowledge limitations**: This is about mentions, not actual funding
2. **Focus on patterns**: Temporal patterns and correlations are still valuable
3. **Don't overinterpret**: Correlation doesn't mean causation

### For Future Work

1. **Scrape public disclosures**: If any exist (unlikely)
2. **Analyze funding mentions more deeply**: Extract more structured data
3. **Temporal analysis**: Track how funding patterns change over time

---

## Files

- **Analysis script**: `scripts/analysis/enhanced_funding_analysis.py`
- **Results**: `findings/enhanced_funding_analysis.json`
- **This report**: `findings/ENHANCED_FUNDING_ANALYSIS_REPORT.md`
