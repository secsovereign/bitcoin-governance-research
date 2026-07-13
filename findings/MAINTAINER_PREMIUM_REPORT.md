# Maintainer Premium: Identity vs Merits (Fair Pass)

**Date:** 2026-07-13  
**Status:** Fair/complete v7 (author-prep + Phase 2 path/ACK/test-diff signals)  
**Machine-readable:** `findings/data/maintainer_premium.json`  
**Script:** `scripts/analysis/maintainer_premium.py`  
**Quality helpers:** `src/utils/pr_quality.py`  
**Rolled into:** `EXECUTIVE_SUMMARY.md` (Exclusive Privilege / Long-Term Problem)

## Question

Do outcomes favor **who** submitted a change — via merge privilege, reputation, or cold-start barriers — after fair controls, including **author-prep** matching (not false “quality”)?

## Fairness rules (applied)

| Rule | Treatment |
|------|-----------|
| Self-merge | Counted in **raw** rates; excluded from **peer-merge** success |
| Prior author merges | Reputation/access — report OR **with and without** this control |
| Closed-unmerged | Not equated to “Core rejected”; split into close proxies |
| Non-maintainer | Split cold-start / mid / established / top-volume |
| Identity label | Primary = ever-maintainer; sensitivity = active-at-creation |
| Author prep | `author_prep_score` = body length + test paths only (**no** reviews/LOC/merge) |
| Size substance | Descriptive only — **not** quality |
| Engagement | Reviews received — process only; not used for matching |
| Importance bands | **Excluded** (over-tags critical) — use **path_risk** instead |
| Concept/approach ACK | Received text flag — process/consensus signal, **not** author prep |
| CI | Unavailable on enriched corpus |

## Results that survive fairness cuts

### 1. Average-case raw gap is mostly self-merge privilege

| Window | Raw maint / non | Peer-merge maint / non | Self-merge share of maint merges |
|--------|----------------:|-----------------------:|---------------------------------:|
| All-time | 80.0% / 54.5% | **59.2% / 54.4%** | 25.9% |
| 2022+ | 81.7% / 50.8% | **62.8% / 50.8%** | 23.2% |

### 2. Established outsiders are not broadly blocked

| Segment (non-maintainers) | All-time merge | 2022+ merge |
|---------------------------|---------------:|------------:|
| First PR (cold start) | **28.9%** | **16.0%** |
| Prior merges ≥5 | 67.3% | 68.6% |
| Top-20 volume authors | 70.1% | 71.1% |

### 3. Large outsider PRs almost never land

Closed ≥2k LOC: non-maint **~7.7%** all-time / **~4.4%** since 2022. Closed ≥5k LOC since 2022: **~1.3%**.

### 4. Author-prep matched gaps

Mean author-prep equal/higher for outsiders. High band (**≥ 0.65**): **~76% / ~59%** all-time (**~17 pp**); **~78% / ~58%** since 2022 (**~20 pp**).

### 5. Phase 2 signals (descriptive)

| Stratum | All-time maint / non | Gap |
|---------|---------------------:|----:|
| Concept/approach ACK received | 79.0% / 68.0% | **~11 pp** |
| High prep **and** nontrivial test diff (≥10 test LOC) | 74.5% / 55.2% | **~19 pp** |
| Path risk: **consensus_sensitive** | 72.9% / **34.5%** | **~38 pp** |
| Path risk: networking | 74.4% / 52.2% | ~22 pp |
| Path risk: security_sensitive | 78.6% / 56.9% | ~22 pp |
| Path risk: other | 81.9% / 58.2% | ~24 pp |

Consensus-path outsider failure is sharper than the average-case story. Concept ACK narrows but does not close the gap.

**CI:** unavailable on enriched corpus — closed as documented unavailable (`author_prep_sensitivity.json` → `ci_status`). Check-run collection is future backlog, not a soft claim.

### 6. Phase 3 sensitivity (`findings/data/author_prep_sensitivity.json`)

| Variant | Gap (pp) |
|---------|---------:|
| prep ≥ 0.65 (canonical) | **17.0** |
| prep ≥ 0.50 | 18.1 |
| body > 200 only | 22.7 |
| body > 500 only | 25.9 |
| tests touch only | 20.5 |
| body > 200 ∧ tests (= prep ≥ 0.65 atoms) | 17.0 |
| body > 500 ∧ tests | 17.8 |
| prep ≥ 0.65 ∧ nontrivial test diff | 19.4 |

`corr(author_prep, log LOC) ≈ 0.38` (vs substance ~0.85); below 0.6 flag threshold.

### 7. High-prep closed-outsider sample (n=100)

Artifact: `findings/data/high_prep_outsider_closed_sample.json`  
Pool: non-maintainer, closed-unmerged, author_prep ≥ 0.65; stratified by path_risk.

| Primary code | Count |
|--------------|------:|
| no_reviews | **45** |
| reviewed_then_closed | 31 |
| nack_signal | 22 |
| staging_or_wip | 2 |

Structured codes (reviews/keywords), not semantic “deserved merge” labels. Nearly half never got a formal review — non-engagement dominates this slice.

### 8. Reputation channel (logistic)

| Model | All-time maint OR | 2022+ maint OR |
|-------|------------------:|---------------:|
| **Without** prior-merge control | **~3.6** | **~5.4** |
| **With** prior-merge control | ~1.36 | ~0.61 |

## What this supports / does not support

**Supports:** self-merge privilege; cold-start; large-PR outsider failure; author-prep matched gap; sharper consensus-path outsider gap; high-prep closed outsiders often unreviewed.

**Does not support:** raw 80/55 as peer-review fairness; “outsiders have lower prep”; treating concept ACK or size-substance as quality; CI-based claims.

## Reproduce

```bash
cd /home/user/src/bitcoin-governance-research && source venv/bin/activate
python tests/test_pr_quality.py
python scripts/analysis/maintainer_premium.py
python scripts/analysis/author_prep_phase23_finish.py
```
