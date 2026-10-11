# Size-adjusted comparison

**Date:** 2026-10-10
**Machine-readable:** `findings/data/size_adjusted_health.json`
**Problem:** After size is held fixed, does bitcoin/bitcoin still sit below the other repositories on the shared health index?

Shared health is the index already published in `COMMONS_MECHANISMS.md`. The regression uses log total pull requests, log mean distinct authors per year, and years of history. The residual is leave-one-out. Review objects are not in these dumps, and `comments_count` is not used.

The preregistered prediction is this. The bitcoin/bitcoin residual of shared health, after log total pull requests, log distinct active contributors per year, and years of history, is negative.

## Result

All repositories. Core residual -0.0003 (interval -0.049 to 0.084). Rank 10 of 17, counting from the most negative. Point sign is negative. The interval covers zero. LOW POWER.

Bolts excluded. Core residual -0.0082 (interval -0.067 to 0.083). Rank 8 of 16, counting from the most negative. Point sign is negative. The interval covers zero. LOW POWER.

Shared-maintainer repositories excluded. Core residual -0.0170 (interval -0.074 to 0.051). Rank 6 of 14, counting from the most negative. Point sign is negative. The interval covers zero. LOW POWER.

The point is negative in all three fits, which is the preregistered sign. Each interval covers zero. The prediction is not resolved.

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

Indicators whose Spearman interval with log pull-request volume excludes zero are H4_gini_merges, H6_median_days_to_decision. Those indicators move with scale. The series is LOW POWER.

| Indicator | Spearman r | Interval | n | Interval excludes zero |
| --- | --- | --- | --- | --- |
| H2_open_stock_per_pr_opened | -0.358 | -0.656 to 0.048 | 17 | no |
| H2_stale_open_per_pr_opened | -0.002 | -0.547 to 0.520 | 17 | no |
| H3_cohort_active_24m | 0.007 | -0.696 to 0.623 | 14 | no |
| H4_gini_merges | 0.860 | 0.588 to 0.970 | 17 | yes |
| H5_bus_factor | 0.368 | -0.201 to 0.812 | 17 | no |
| H6_median_days_to_decision | -0.431 | -0.743 to -0.002 | 17 | yes |

## Comparison-repository effects

The preregistered prediction is a Spearman correlation of each effect with the size-adjusted residual, not the raw health index.
No Spearman interval excludes zero, so none of those predicted signs is resolved.
TRACKS HEALTH when the Spearman interval of the repository estimate against the size-adjusted residual excludes zero. Otherwise CORE-SPECIFIC when Core's interval excludes zero and no seven-year comparison repository has an interval that excludes zero in Core's direction. Otherwise AMBIENT when Core's interval excludes zero, at least half of those repositories share Core's sign, and at least one of those intervals excludes zero. UNDETERMINED in every other case, including a missing estimate. The seven-year minimum is the one already used for the cross-repository table.

| Effect | Class | Outside Core | Spearman r | Interval | Predicted sign | Point matches |
| --- | --- | --- | --- | --- | --- | --- |
| E2_reciprocity_excess | AMBIENT | yes | 0.191 | -0.342 to 0.655 | negative | no |
| E3_log_hours_to_next_same_direction_top5_minus_other | UNDETERMINED | no | missing | not defined | positive | not defined |
| E5_log_participants_on_log_days | AMBIENT | yes | -0.389 | -0.827 to 0.161 | negative | yes |
| E7_first_tone_on_merge_given_later_tone | AMBIENT | yes | -0.319 | -0.755 to 0.322 | negative | yes |
| E12_ingroup_on_no_peer_response | AMBIENT | yes | 0.167 | -0.765 to 0.779 | positive | yes |

The Benjamini-Hochberg family is now 228 tests, passes 1 through 6. No prior result crossed q = 0.05.
H2, H3, H4 merge Gini, H5, and H6 are computed from open and close timestamps, author, and merged state. Review objects, comment authors, and file paths do not enter them. The shared-health rank and the Task 3 residual are not refit.
E9 stays on bitcoin/bitcoin. No other project in this set has a meeting list.
ethereum/go-ethereum is DATA UNAVAILABLE because prs.jsonl is missing, so review objects were not requested.
E3 is UNDETERMINED because pull records do not store merged_by, so the trailing top-5 merger window was not built. The merged flag was not used as a substitute.
564 review, comment, or file lists were cut at 100 rows because the collector stored one page.
Every cross-repository correlation is LOW POWER.

## What this cannot prove

- Seventeen repositories cannot separate size from governance. Every residual is LOW POWER.
- Shared health still omits review labor. H2 through H6 do not read review objects, so the backfill does not move the rank.
- A negative residual says Core sits below the size line. It does not say why.
- A correlation between an effect and a size-adjusted residual is not a cause of that residual.
- Fewer than 20 repositories make every cross-repository correlation LOW POWER.
- Pull requests GitHub no longer serves are omitted, not scored as having no review.
- Lists longer than 100 reviews, comments, or files are cut at the first page, so those pull requests are under-counted.
- E3 is not identified outside Core because merged_by was not stored. That absence is not evidence the cascade is Core-specific.
- E9 is not applicable outside bitcoin/bitcoin.


**Generated by:** `scripts/reporting/generate_from_templates.py`
