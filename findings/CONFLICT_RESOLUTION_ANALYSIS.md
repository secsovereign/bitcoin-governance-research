# Conflict Resolution Analysis

**Date**: 2026-01-24  
**Last Updated**: 2026-01-24  
**Purpose**: Analyze conflict detection, resolution patterns, and temporal evolution  
**Methodology**: NACK detection, CHANGES_REQUESTED reviews, heated discussion identification

---

## Executive Summary

Bitcoin Core governance experiences significant conflicts: 5,128 conflicts identified across 15,840 PRs (32.4% conflict rate). Average resolution time is 103.2 days. Many conflicts result in PRs being merged anyway (2,649 cases), suggesting conflicts don't always prevent merges.

---

## Conflict Detection Methodology

### Conflict Types

1. **NACKs**: Explicit negative acknowledgements
   - Keywords: 'nack', 'nacked', 'nacking', 'concept nack', 'approach nack', 'utack nack', 'strong nack', 'weak nack'
   - **Count**: 1,469 NACKs identified

2. **CHANGES_REQUESTED Reviews**: Formal GitHub reviews requesting changes
   - **Count**: 899 CHANGES_REQUESTED reviews

3. **Heated Discussions**: Multiple negative comments indicating disagreement
   - Keywords: 'disagree', 'oppose', 'against', 'wrong', 'bad idea', 'concern', 'problem'
   - Threshold: 3+ negative comments
   - **Count**: 3,823 heated discussions

**Total conflicts**: 5,128 (some PRs have multiple conflict types)

---

## Conflict Statistics

### Overall Statistics

- **Total PRs analyzed**: 15,840
- **Total conflicts identified**: 5,128
- **Conflict rate**: 32.4% of PRs experience conflicts
- **Average resolution time**: 103.2 days

### Conflicts by Type

- **NACK**: 1,469 (28.6% of conflicts)
- **CHANGES_REQUESTED**: 899 (17.5% of conflicts)
- **Heated discussion**: 3,823 (74.6% of conflicts)

**Note**: Some PRs have multiple conflict types, so percentages don't sum to 100%.

---

## Resolution Paths

### How Conflicts Are Resolved

- **Merged anyway**: 2,649 conflicts (51.7%)
- **Closed**: 2,339 conflicts (45.6%)
- **Still open**: 140 conflicts (2.7%)
- **Withdrawn**: 0 conflicts (0%)
- **Modified**: 0 conflicts (0%)

**Key Finding**: Over half of conflicts (51.7%) result in PRs being merged anyway, suggesting conflicts don't always prevent merges.

---

## Temporal Evolution

### Conflict Rates Over Time (2016-2025)

| Year | PRs | Conflicts | Conflict Rate | Avg Resolution (days) |
|------|-----|-----------|---------------|----------------------|
| 2016 | 1,562 | 146 | 9.3% | 125.5 |
| 2017 | 1,842 | 257 | 14.0% | 122.8 |
| 2018 | 2,081 | 276 | 13.3% | 121.8 |
| 2019 | 1,954 | 309 | 15.8% | 160.1 |
| 2020 | 2,122 | 336 | 15.8% | 138.3 |
| 2021 | 1,994 | 248 | 12.4% | 169.9 |
| 2022 | 2,002 | 239 | 11.9% | 151.0 |
| 2023 | 1,581 | 192 | 12.1% | 144.5 |
| 2024 | 1,637 | 210 | 12.8% | 114.4 |
| 2025 | 1,835 | 240 | 13.1% | 47.0 |

### Key Temporal Findings

1. **Conflict rate stable**: 9-16% of PRs have conflicts (peaked 2019-2020 at 15.8%)
2. **Resolution time improving**: 47 days in 2025 (down from 160+ days in 2019-2021)
3. **Peak conflicts**: 2019-2020 had highest conflict rates (may correlate with Taproot, major events)
4. **Recent improvement**: Resolution time dropped significantly in 2025 (47 days vs 160+ days)

---

## Conflict Resolution and Voting Blocs

### Bloc Behavior During Conflicts

**Finding**: Voting bloc cohesion drops during conflicts.

- **Non-conflict PRs**: 100% average cohesion
- **Conflict PRs**: 76.7% average cohesion
- **Difference**: -23.3% cohesion drop

**Interpretation**: 
- Conflicts stress-test voting blocs
- Bloc cohesion breaks down during conflicts (100% → 76.7%)
- Conflicts reveal true bloc boundaries
- Blocs are less cohesive under pressure

**Key Insight**: Voting blocs are stable in normal circumstances (100% cohesion) but break down during conflicts, revealing their boundaries.

---

## Top Conflict Participants

**Note**: Detailed participant analysis requires additional processing. The conflict resolution analysis identifies conflicts and resolution paths, but individual participant rankings are not included in the current output format.

**Future enhancement**: Could identify:
- Top conflict drivers (who initiates most conflicts)
- Top mediators (who resolves conflicts)
- Conflict networks (who conflicts with whom)

---

## Interpretation

### 1. Conflicts Are Common

- **32.4% conflict rate** means nearly 1 in 3 PRs experiences some form of conflict
- Conflicts are a regular feature of governance, not rare exceptions
- Multiple conflict types (NACKs, CHANGES_REQUESTED, heated discussions) indicate various forms of disagreement

### 2. Resolution Is Slow But Improving

- **Average 103.2 days** to resolve conflicts
- Recent improvement: 47 days in 2025 (down from 160+ days)
- Suggests conflict resolution processes are improving

### 3. Conflicts Don't Always Prevent Merges

- **51.7% of conflicts result in merges anyway**
- Suggests conflicts may not always be decisive
- Some conflicts may be resolved through discussion or compromise

### 4. Conflicts Reveal Bloc Boundaries

- Voting bloc cohesion drops from 100% to 76.7% during conflicts
- Conflicts stress-test voting blocs
- Bloc boundaries become visible when cohesion breaks down

---

## Data Sources

- **Analysis script**: `scripts/analysis/nack_effectiveness.py`
- **Results**: `analysis/nack_effectiveness/nack_effectiveness_analysis.json`
- **Temporal analysis**: `scripts/analysis/temporal_analysis.py` (conflict_resolution_temporal)
- **Voting bloc + conflicts**: `scripts/analysis/voting_bloc_conflict_analysis.py`

---

## Related Analyses

- **Voting Bloc Analysis**: See how voting blocs behave during conflicts
- **Temporal Analysis**: See conflict rates and resolution times over time
- **NACK Effectiveness**: See how effective NACKs are at preventing merges

