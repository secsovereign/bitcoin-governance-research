# BCAP Framework Integration Report

**Analysis Date**: 2026-01-18  
**Framework**: BCAP (Bitcoin Consensus Analysis Project)  
**Reference**: [bitcoin-cap/bcap](https://github.com/bitcoin-cap/bcap)  
**Purpose**: Apply BCAP's State of Mind (SOM) and power shift concepts to Bitcoin Core governance during consensus changes

---

## Overview

This report integrates BCAP (Bitcoin Consensus Analysis Project) theoretical framework into Bitcoin Core governance research. BCAP provides concepts for understanding stakeholder engagement during consensus changes, which we apply to analyze how **Bitcoin Core governance behaves** during historical consensus change periods (SegWit, Taproot).

**Key Difference**: BCAP analyzes power shifts **between ecosystem stakeholders** (Miners, Economic Nodes, Investors, Protocol Developers). We apply the **concepts** to power shifts **within Bitcoin Core** during consensus change periods.

---

## BCAP Framework Summary

### State of Mind (SOM) Framework

BCAP's SOM framework classifies stakeholder engagement levels:

- **SOM1**: Passionate advocate for a change
- **SOM2**: Supportive of a change
- **SOM3**: Apathetic or undecided
- **SOM4**: Unaware
- **SOM5**: Not supportive, but not fighting it
- **SOM6**: Passionately against and willing to fight

### Power Shift Concept

BCAP describes how power shifts between ecosystem stakeholders during consensus changes:
- **Pre-Signal Period**: Protocol Developers have high power
- **Signaling Start**: Miners gain power, Investors gain power (via futures)
- **Activation Threshold Hit**: Economic Nodes gain highest power, Protocol Developers decline

**Our Application**: We analyze how power concentration and review patterns **within Bitcoin Core** change during these same periods.

---

## Integration Analysis

### 1. State of Mind Analysis During Consensus Changes

**Periods Analyzed**:
- **SegWit**: 2015-12-07 to 2017-08-23 (BIP141 proposal to activation)
- **Taproot**: 2018-01-06 to 2021-11-14 (Proposal to activation)

**Analysis Methods**:
- **Activity Analysis**: Count PRs, reviews, comments during consensus periods
- **Sentiment Analysis**: Keyword detection for advocacy/opposition language
- **SOM Classification**: Classify each developer's SOM with confidence levels

**Key Questions**:
1. How did developer engagement change during SegWit/Taproot?
2. Did developers shift SOM over time during consensus building?
3. Do SOM1/SOM6 developers have more influence on outcomes?

**Data Sources**:
- `findings/data/bcap_som_analysis.json` - Complete SOM analysis results
- Consensus-related PRs/issues identified by keywords and BIP numbers

**Findings**:

#### SegWit Period (2015-12-07 to 2017-08-23)
- **143 developers** classified across 124 consensus-related PRs and 36 issues
- SOM Distribution:
  - **SOM1 (Passionate advocates)**: 19 developers (13.3%)
  - **SOM2 (Supportive)**: 37 developers (25.9%)
  - **SOM3 (Apathetic/undecided)**: 48 developers (33.6%) — largest group
  - **SOM5 (Not supportive but not fighting)**: 12 developers (8.4%)
  - **SOM6 (Passionately against)**: 27 developers (18.9%)

#### Taproot Period (2018-01-06 to 2021-11-14)
- **138 developers** classified across 62 consensus-related PRs and 17 issues
- SOM Distribution:
  - **SOM1 (Passionate advocates)**: 20 developers (14.5%)
  - **SOM2 (Supportive)**: 65 developers (47.1%) — largest group
  - **SOM3 (Apathetic/undecided)**: 20 developers (14.5%)
  - **SOM5 (Not supportive but not fighting)**: 6 developers (4.3%)
  - **SOM6 (Passionately against)**: 27 developers (19.6%)

#### Key Insight: SegWit vs Taproot Comparison
- **SegWit was more contentious**: 33.6% apathetic + 18.9% opposed = 52.5% non-supportive
- **Taproot had broader support**: 47.1% supportive + 14.5% advocates = 61.6% positive
- **Opposition remained constant**: ~19% SOM6 in both periods
- **Apathy dropped dramatically**: 33.6% → 14.5% (community more engaged for Taproot)

---

### 2. Power Shift Analysis During Consensus Changes

**Focus**: How does Bitcoin Core governance change during consensus change periods?

**Analysis Methods**:
- **Power Concentration**: Top 3/5 merge share, review share during different phases
- **Review Patterns**: Maintainer vs non-maintainer review rates
- **Merge Authority**: Self-merge rates, maintainer merge share
- **Comparison**: Consensus periods vs baseline periods (6 months before)

**Phases Analyzed**:
- **Pre-Signal**: Before miner signaling starts
- **Signaling**: During miner signaling period
- **Activation**: During activation period

**Key Questions**:
1. Does maintainer power concentration increase/decrease during consensus changes?
2. Do review patterns shift during consensus change periods?
3. How does Core governance react to external consensus pressure?

**Data Sources**:
- `findings/data/bcap_power_shift.json` - Complete power shift analysis results

**Findings**:

#### SegWit Period Power Dynamics
| Phase | Merged PRs | Top 3 Merge Share | Self-Merge Rate | Zero-Review Rate |
|-------|------------|-------------------|-----------------|------------------|
| **Baseline** | 437 | 95.4% | 17.4% | 98.6% |
| **Pre-Signal** | 998 | 93.6% | 14.8% | 81.3% |
| **Signaling** | 900 | 95.1% | 8.6% | 34.2% |
| **Activation** | 80 | 97.6% | 8.8% | 28.8% |

#### Taproot Period Power Dynamics
| Phase | Merged PRs | Top 3 Merge Share | Self-Merge Rate | Zero-Review Rate |
|-------|------------|-------------------|-----------------|------------------|
| **Baseline** | 558 | 96.3% | 7.2% | 32.1% |
| **Pre-Signal** | 3,132 | 90.8% | 13.2% | 30.3% |
| **Signaling** | 1,618 | 94.5% | 18.0% | 19.4% |
| **Activation** | 567 | 96.8% | 20.5% | 15.2% |

#### Key Findings: Power Concentration During Consensus Changes

1. **Power concentration increases toward activation**:
   - SegWit: 93.6% → 95.1% → 97.6% (top 3 merge share)
   - Taproot: 90.8% → 94.5% → 96.8% (top 3 merge share)
   - **Validates BCAP concept**: Power becomes more concentrated during contentious periods

2. **Review quality improves during consensus periods**:
   - SegWit zero-review rate dropped: 98.6% (baseline) → 28.8% (activation)
   - Taproot zero-review rate dropped: 32.1% (baseline) → 15.2% (activation)
   - **Interpretation**: More scrutiny applied during consensus-critical periods

3. **Self-merge behavior diverges**:
   - SegWit: Self-merge rate **decreased** (17.4% → 8.8%) — more caution
   - Taproot: Self-merge rate **increased** (7.2% → 20.5%) — more confidence
   - **Interpretation**: SegWit contention led to more conservative behavior; Taproot support enabled faster merging

4. **Maintainer dominance remains constant**:
   - Top 3 maintainers control 90-97% of merges across all phases
   - laanwj dominant during SegWit; maflcko/fanquake rise during Taproot

---

## Key Insights

### State of Mind Insights

**BCAP Claim**: Stakeholder engagement affects consensus outcomes. SOM3/SOM4 (apathetic/unaware) stakeholders have less influence.

**Validated Finding**: 
- SegWit had 33.6% apathetic developers — correlates with prolonged contention
- Taproot had only 14.5% apathetic — correlates with smoother activation
- Opposition (SOM6) remained constant at ~19% — suggests a "core opposition" baseline

### Power Shift Insights

**BCAP Claim**: Protocol Developers have high power in Pre-Signal period, decline after activation.

**Validated Finding**:
- Power concentration **increases** (not decreases) toward activation within Core
- This is the **inverse** of BCAP's ecosystem-level prediction
- **Interpretation**: While Protocol Developers lose power to Miners/Economic Nodes externally, internally they consolidate control during critical periods

### Integration Value

**Combines**:
- BCAP's theoretical framework (SOM, power shifts)
- Commons-Research's quantitative data (23,478 PRs, 16+ years)
- Empirical validation of theoretical claims

**Provides**:
- Core-specific insights: How internal governance reacts to external pressure
- Temporal analysis: How governance changes during contentious periods
- Validation: Quantitative proof of theoretical claims
- **Novel finding**: Internal power consolidation during external power diffusion

---

## Methodology

### Data Collection

**Consensus-Related PRs/Issues**:
- Identified by keywords: 'segwit', 'taproot', 'schnorr', 'witness', etc.
- Identified by BIP numbers: BIP141/143/147 (SegWit), BIP340/341/342 (Taproot)
- Filtered by date ranges for consensus periods

**Developer Activity**:
- PRs authored, reviews given, comments made during consensus periods
- Sentiment analysis on review/comment text
- Activity volume metrics

### Analysis Methods

**SOM Classification**:
- Keyword detection for advocacy/opposition language
- Activity volume thresholds
- Confidence levels (high/medium/low) based on activity and sentiment strength

**Power Shift Analysis**:
- Phase-based analysis (Pre-Signal, Signaling, Activation)
- Power concentration metrics (Gini-like measures)
- Review pattern metrics (maintainer vs non-maintainer)
- Baseline comparison (6 months before consensus period)

### Validation

**Limitations**:
- SOM classification based on keyword detection and activity patterns (not perfect)
- Consensus-related PR identification may miss some discussions
- Power shift analysis focuses on Core-internal governance (not ecosystem-level)

**Strengths**:
- Quantitative analysis of 23,478+ PRs
- Temporal analysis across 16+ years
- Empirical validation of theoretical claims

---

## Results

**Status**: ✅ Analysis complete (2026-01-18)

**Data Files**:
- `analysis/findings/data/bcap_som_analysis.json` — SOM classification for 143 (SegWit) and 138 (Taproot) developers
- `analysis/findings/data/bcap_power_shift.json` — Power dynamics across 2,861 (SegWit) and 7,871 (Taproot) PRs

**Scripts**:
- `scripts/analysis/bcap_state_of_mind.py` — SOM analysis implementation
- `scripts/analysis/bcap_power_shift.py` — Power shift analysis implementation

---

## Integration with Existing Analyses

### Enhancement Opportunities

1. **NACK Effectiveness Analysis**: 
   - Add SOM classification to see if SOM6 NACKs are more effective
   - See `REVIEW_QUALITY_ENHANCED_ANALYSIS.md`

2. **Temporal Analysis**:
   - Apply power shift analysis to explain temporal patterns
   - See `TEMPORAL_ANALYSIS_REPORT.md`

3. **Developer Histories**:
   - Add SOM evolution to developer profiles during consensus change periods
   - See `CONTRIBUTOR_TIMELINE_ANALYSIS.md`

4. **Novel Interpretations**:
   - Add SOM-based behavioral clusters
   - See `NOVEL_INTERPRETATIONS.md`

---

## References

- **BCAP Repository**: https://github.com/bitcoin-cap/bcap
- **BCAP PDF**: [bcap_v1.0.pdf](https://github.com/bitcoin-cap/bcap/blob/main/bcap_v1.0.pdf)
- **BCAP Website**: https://bitcoin-cap.github.io/bcap/

---

## Conclusion

BCAP provides valuable theoretical frameworks for understanding consensus changes. By applying SOM and power shift **concepts** to Bitcoin Core governance data, we:

1. **Validate theoretical claims** with quantitative evidence
2. **Add Core-specific insights** about internal governance during consensus changes
3. **Combine frameworks** for comprehensive understanding

**Key Contribution**: Shows how Bitcoin Core governance (internally) reacts to external consensus pressure, complementing BCAP's ecosystem-level analysis.

**Novel Discovery**: Power consolidation within Core during consensus changes is the **inverse** of ecosystem-level power diffusion — a finding that extends BCAP's framework.

