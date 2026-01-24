# Coordination Costs Analysis

**Date**: 2026-01-24  
**Last Updated**: 2026-01-24  
**Purpose**: Analyze communication volume, participants, and decision time per PR  
**Methodology**: GitHub comments/reviews, email mentions, IRC mentions, participant counting

---

## Executive Summary

Bitcoin Core governance requires significant coordination overhead: average 22.0 messages per PR, 5.2 participants, and 41.2 days to decision. Governance complexity scales 3.8x with code complexity (low: 15.6 msgs, medium: 43.9 msgs, high: 59.7 msgs).

---

## Overall Statistics

### Communication Volume

- **Total PRs analyzed**: 15,840
- **Average communication per PR**: 22.0 messages
  - GitHub comments/reviews/review comments
  - Email mentions (PR number referenced)
  - IRC mentions (PR number referenced)
- **Average participants per PR**: 5.2 people
- **Average decision time**: 41.2 days

---

## Coordination Costs by Complexity

### Code Complexity Levels

**Low complexity** (≤5 files):
- **PRs**: 12,714 (80.3%)
- **Avg communication**: 15.6 messages
- **Avg participants**: 4.8 people
- **Avg decision time**: 33.2 days

**Medium complexity** (6-15 files):
- **PRs**: 2,277 (14.4%)
- **Avg communication**: 43.9 messages (2.8x more than low)
- **Avg participants**: 6.8 people (1.4x more than low)
- **Avg decision time**: 67.7 days (2.0x longer than low)

**High complexity** (>15 files):
- **PRs**: 849 (5.4%)
- **Avg communication**: 59.7 messages (3.8x more than low)
- **Avg participants**: 7.4 people (1.5x more than low)
- **Avg decision time**: 66.0 days (2.0x longer than low)

### Scaling Analysis

**Communication scaling**: 3.8x from low to high complexity
- Low: 15.6 messages
- Medium: 43.9 messages (2.8x)
- High: 59.7 messages (3.8x)

**Participant scaling**: 1.5x from low to high complexity
- Low: 4.8 participants
- Medium: 6.8 participants (1.4x)
- High: 7.4 participants (1.5x)

**Decision time scaling**: 2.0x from low to high complexity
- Low: 33.2 days
- Medium: 67.7 days (2.0x)
- High: 66.0 days (2.0x)

---

## Interpretation

### 1. Governance Complexity Scales with Code Complexity

- **3.8x more communication** for high complexity PRs
- **1.5x more participants** for high complexity PRs
- **2.0x longer decision time** for high complexity PRs

**Implication**: Complex code requires significantly more governance overhead. This creates a natural barrier to complex changes, potentially favoring simpler, incremental changes.

### 2. Coordination Overhead Is Significant

- **22.0 messages per PR** on average
- **5.2 participants** per PR on average
- **41.2 days** to decision on average

**Implication**: Governance requires substantial coordination effort. Every decision involves multiple people and significant communication.

### 3. Complexity Creates Barriers

- High complexity PRs require 3.8x more communication
- This creates a natural disincentive for complex changes
- May favor incremental, simpler changes over comprehensive refactoring

---

## Temporal Evolution

**Note**: Full temporal analysis of coordination costs is computationally expensive due to email/IRC matching. Current analysis uses GitHub data only for temporal patterns.

**GitHub-only temporal analysis** (future enhancement):
- Track communication volume trends over time
- See if coordination costs are increasing or decreasing
- Identify periods of high coordination overhead

---

## Data Sources

- **Analysis script**: `scripts/analysis/communication_patterns.py`
- **Results**: `analysis/communication_patterns/communication_patterns_analysis.json`
- **Key method**: `_analyze_coordination_costs()`

---

## Related Analyses

- **Code Complexity vs Governance Complexity**: See correlation between code and governance complexity
- **Temporal Analysis**: See how coordination costs change over time
- **Response Time Analysis**: See how coordination affects decision time

