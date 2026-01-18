# Contributor Retention Analysis

## Executive Summary

Bitcoin Core has experienced **87.7% contributor exit** (1-year threshold) with only **935 of 7,604** contributors remaining active.

## Key Findings

| Metric | Value |
|--------|-------|
| **Total Contributors** | 7,604 |
| **Active Contributors** | 935 (12.3%) |
| **Exit Rate (1 year)** | 87.7% |
| **Exit Rate (2 year)** | 80.7% |

## Breakdown by Type

### PR Authors vs Participants

| Type | Count | % of Total | Exit Rate |
|------|-------|------------|-----------|
| **PR Authors** | 2,409 | 31.7% | 82.2% |
| **Participants Only** | 5,195 | 68.3% | 90.2% |

*Participants = commented, reviewed, or created issues but never authored a PR*

### One-Time Contributors

- **3,232 contributors (42.5%)** did exactly 1 activity and left
- Exit rate: 88.7%

### High-Quality Authors

- **834 authors** with 50%+ PR merge rate
- Exit rate: **83.5%**
- Quality does not protect against exit

## Activity Summary

| Activity Type | Count |
|---------------|-------|
| PRs Authored | 23,615 |
| PR Comments | 184,567 |
| PR Reviews | 114,984 |
| Issues Created | 8,936 |
| Issue Comments | 48,138 |
| **Total Activities** | **380,240** |

## Key Insights

1. **Massive Churn**: 87.7% of all contributors have exited
2. **Most Never Author PRs**: 68.3% only participate through comments/reviews/issues
3. **One-Time Dominates**: 42.5% contribute once and leave
4. **Quality Irrelevant**: High-quality authors exit at 83.5% (nearly same as overall)
5. **Participants Exit More**: 90.2% exit rate for non-PR-authors

## Methodology

### Definitions

- **Contributor**: Anyone with any GitHub activity (PR author, commenter, reviewer, issue creator, issue commenter)
- **Active**: Activity within last 365 days
- **Exited**: No activity in last 365 days
- **Author**: Authored at least 1 PR
- **Participant**: Never authored a PR (comments/reviews/issues only)
- **High-Quality**: 50%+ PR merge rate (authors only)
- **One-Time**: Exactly 1 total activity

### Data Coverage

- **First Activity**: December 19, 2010
- **Last Activity**: January 11, 2026
- **Analysis Date**: January 18, 2026

### Data Sources

- GitHub PRs (23,615)
- GitHub Issues (8,936)
- PR Comments, Reviews, Issue Comments

---

*Source: `contributor_analysis.json`*

