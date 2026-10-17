# Size-adjusted comparison

**Date:** 2026-10-11
**Machine-readable:** `findings/data/size_adjusted_health.json`
**Problem:** After size is held fixed, does bitcoin/bitcoin still sit below the other repositories on the shared health index?

Shared health is the index already published in `COMMONS_MECHANISMS.md`. The regression uses log total pull requests, log mean distinct authors per year, and years of history. The residual is leave-one-out. Review objects, comment authors, and file paths do not enter that regression. `comments_count` is not used.

## Result

All repositories. Core residual -0.0003 (interval -0.049 to 0.084). Rank 10 of 17, counting from the most negative. Point sign is negative. The interval covers zero.

Bolts excluded. Core residual -0.0082 (interval -0.067 to 0.083). Rank 8 of 16, counting from the most negative. Point sign is negative. The interval covers zero.

Shared-maintainer repositories excluded. Core residual -0.0170 (interval -0.074 to 0.051). Rank 6 of 14, counting from the most negative. Point sign is negative. The interval covers zero.

The point is negative in all three fits. Each interval covers zero.

| Repository | Role | Shared health | Pull requests | Years | Residual |
| --- | --- | --- | --- | --- | --- |
| bitcoin-core/secp256k1 | library shared maintainers | 0.587 | 1336 | 13 | -0.061 |
| bitcoin-core/HWI | wallet_hardware shared maintainers | 0.596 | 550 | 9 | -0.060 |
| lightning/bolts | spec | 0.611 | 872 | 11 | -0.029 |
| SeedSigner/seedsigner | wallet_hardware | 0.616 | 696 | 7 | -0.028 |
| foundation-devices/passport-firmware | other | 0.674 | 65 | 3 | -0.022 |
| ACINQ/eclair | implementation | 0.648 | 2482 | 11 | -0.020 |
| sparrowwallet/sparrow | wallet_hardware | 0.640 | 133 | 7 | -0.017 |
| lightningdevkit/rust-lightning | implementation | 0.621 | 3532 | 9 | -0.016 |
| stratum-mining/stratum | other | 0.650 | 1258 | 6 | -0.001 |
| bitcoin/bitcoin | node | 0.585 | 25495 | 17 | -0.000 |
| ElementsProject/lightning | implementation | 0.635 | 5929 | 12 | 0.012 |
| rust-bitcoin/rust-bitcoin | library | 0.638 | 4847 | 13 | 0.012 |
| bitcoindevkit/bdk | library | 0.648 | 1381 | 7 | 0.022 |
| stratum-mining/sv2-spec | other | 0.692 | 131 | 5 | 0.033 |
| lightningnetwork/lnd | implementation | 0.646 | 6181 | 11 | 0.045 |
| rust-bitcoin/rust-miniscript | library | 0.702 | 772 | 9 | 0.055 |
| bitcoin-core/bitcoin-maintainer-tools | tooling shared maintainers | 0.722 | 139 | 11 | 0.098 |

Roles follow the pass 6 list. foundation-devices/passport-firmware, stratum-mining/stratum, and stratum-mining/sv2-spec are marked other because that list did not name them. bitcoin-core/secp256k1, bitcoin-core/HWI, and bitcoin-core/bitcoin-maintainer-tools are flagged shared maintainers.

## Indicators that move with volume

The indicator whose Spearman interval with log pull-request volume excludes zero is H4_gini_merges. The published H6 interval is -0.743 to -0.002, and that bound is not treated as an exclusion.

| Indicator | Spearman r | Interval | n | Interval excludes zero |
| --- | --- | --- | --- | --- |
| H2_open_stock_per_pr_opened | -0.358 | -0.656 to 0.048 | 17 | no |
| H2_stale_open_per_pr_opened | -0.002 | -0.547 to 0.520 | 17 | no |
| H3_cohort_active_24m | 0.007 | -0.696 to 0.623 | 14 | no |
| H4_gini_merges | 0.860 | 0.588 to 0.970 | 17 | yes |
| H5_bus_factor | 0.368 | -0.201 to 0.812 | 17 | no |
| H6_median_days_to_decision | -0.431 | -0.743 to -0.002 | 17 | bound near zero |

## Comparison-repository effects

Each effect is a Spearman correlation with the size-adjusted residual, not the raw health index.
No Spearman interval excludes zero.
TRACKS HEALTH when the Spearman interval of the repository estimate against the size-adjusted residual excludes zero. Otherwise CORE-SPECIFIC when Core's interval excludes zero and no seven-year comparison repository has an interval that excludes zero in Core's direction. Otherwise AMBIENT when Core's interval excludes zero, at least half of those repositories share Core's sign, and at least one of those intervals excludes zero. UNDETERMINED in every other case, including a missing estimate. The seven-year minimum is the one already used for the cross-repository table.

| Effect | Class | Repositories | Outside Core | Spearman r | Interval | Degenerate share |
| --- | --- | --- | --- | --- | --- | --- |
| E2_reciprocity_excess | AMBIENT | 14 | yes | 0.231 | -0.321 to 0.678 | not applicable |
| E3_log_hours_to_next_same_direction_top5_minus_other | UNDETERMINED | 1 | no | missing | not defined | not applicable |
| E5_log_participants_on_log_days | AMBIENT | 14 | yes | -0.393 | -0.861 to 0.142 | not applicable |
| E7_first_tone_on_merge_given_later_tone | AMBIENT | 13 | yes | -0.319 | -0.730 to 0.298 | not applicable |
| E12_ingroup_on_no_peer_response | AMBIENT | 9 | yes | 0.117 | -1.000 to 0.675 | 0.005 |

The E3 row is the estimate from before merger identities were collected. One repository had an estimate, so that class was UNDETERMINED. After `merged_by` was collected, eight repositories have an estimate. The Spearman correlation with the refit residual is 0.429, interval -0.519 to 1.000. The class is AMBIENT. Its q is 0.431. The interval covers zero. The merged flag was not used as a substitute.
H2, H3, H4 merge Gini, H5, and H6 are computed from open and close timestamps, author, and merged state. Review objects, comment authors, and file paths do not enter them. This file's residual is the pass 6 fit. The later fit, after merger Gini replaces author-basis H4, is in `pass7_merged_by.json`. Core's refit residual is -0.070, interval -0.156 to 0.068, rank 3 of 17, and that interval covers zero.
E9 stays on bitcoin/bitcoin. No other project in this set has a meeting list.
ethereum/go-ethereum is DATA UNAVAILABLE because prs.jsonl is missing, so review objects were not requested.
Lists that had stopped at 100 rows were followed to the last page. No list in this frame is still cut.
No effect changed class after the repository minimum and the degeneracy count.

## What this cannot prove

- Seventeen repositories cannot separate size from governance.
- Shared health still omits review labor. H2 through H6 do not read review objects, so the backfill does not move the rank.
- A negative residual says Core sits below the size line. It does not say why.
- A correlation between an effect and a size-adjusted residual is not a cause of that residual.
- Fewer than 20 repositories enter every cross-repository correlation.
- A Spearman correlation with fewer than 6 repository estimates is DATA UNAVAILABLE and is not given an interval.
- Pull requests GitHub no longer serves are omitted, not scored as having no review.
- A list is under-counted only when it still has at least 100 rows and pages_complete is not set.
- The later E3 correlation covers zero. That does not show the cascade is Core-specific.
- E9 is not applicable outside bitcoin/bitcoin.


**Generated by:** `scripts/reporting/generate_from_templates.py`
