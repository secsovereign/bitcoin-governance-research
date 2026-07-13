# Merge Concentration and Deputy Patterns

**Date:** 2026-07-13  
**Status:** Fair interpretation  
**Machine-readable:** `findings/data/high_volume_merger_deputies.json`  
**Related:** `scripts/analysis/merge_pattern_analysis.py`  
**Rolled into:** `EXECUTIVE_SUMMARY.md` (Power Concentration)

## Question

How thin is merge authority, and does the merger graph show recurring author funnels / co-reviewers?

## Results

### Modern window (2022+)

| Metric | Value |
|--------|------:|
| Merged PRs | 5,550 |
| Top merger | `fanquake` |
| Top-1 share | **50.4%** |
| Top-2 | **~71%** |
| Top-3 | **~83%** |

Author funnels (≥40% of an author’s merges through `fanquake`) include frequent in-group contributors — see JSON.

### Self-merge (privilege, not a disclaimer)

~26% of maintainer-authored merges are self-merges (author = `merged_by`). That **is** concentration of power (finalize your own change). It should not be used to dismiss top-merger share; if anything it clarifies how authority is exercised. For identity-vs-merits peer-review comparisons, see `MAINTAINER_PREMIUM_REPORT.md` peer-merge rates.

### All-time

`laanwj` 34.4% — historical; do not cite as the 2025 picture.

## Fair reading

Modern merge authority is highly concentrated. Co-reviewer recurrence is **observational** (who appears on the same PRs), not proof of formal deputy rights. Still consistent with a small trusted filter.

## Reproduce

Artifact: `findings/data/high_volume_merger_deputies.json` (from merge-pattern / deputies extraction).
