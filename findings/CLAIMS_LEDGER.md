# Claims ledger

Each row is a headline claim. The number is taken from the committed JSON named in the row. Older reports keep the q they were written against. The pass 7 family is 229, and those recomputed q values are in `pass7_merged_by.json`.

| Status | Claim | Number | Source | JSON | Family |
| --- | --- | --- | --- | --- | --- |
| NOT IN FAMILY, LOW POWER | The Core newcomer interaction is -3.7 percentage points per year, driver BOTH. Classification is AMBIENT on 5 of 9 eligible negative points after the 3-year series rule, and 7 of 12 before it. | -3.7 percentage points per year | findings/NEWCOMER_DIVERGENCE.md | findings/data/newcomer_divergence.json published_core_interaction | not in family |
| NOT IN FAMILY, LOW POWER | Among eligible repositories, the interaction is NEWCOMER DECLINE in 0, INCUMBENT GAIN in 1, BOTH in 1, INCUMBENT DECLINE in 2, and UNRESOLVED in 5. Core and bdk are the two repositories where newcomer decline and incumbent gain both resolve. | 4 resolved, 5 unresolved | findings/NEWCOMER_DIVERGENCE.md | findings/data/newcomer_divergence.json driver_counts | not in family |
| RETRACTED | rust-bitcoin and rust-miniscript show a practice that serves newcomers |  | findings/CLAIMS_LEDGER.md | findings/data/newcomer_divergence.json driver_counts | not in family |
| EXPLORATORY, NOT IN FAMILY | The newcomer interaction against the size-adjusted residual has Spearman 0.370, and the interval covers zero. | 0.370 | findings/NEWCOMER_DIVERGENCE.md | findings/data/newcomer_divergence.json health_link.estimate | not in family |
| CONFIRMED | Numeric user ids merged 0 additional logins in the seven-year dumps, and 0 people had more than one login. | 0 | findings/NEWCOMER_DIVERGENCE.md | findings/data/newcomer_divergence.json logins_collapsed | not in family |
| AMBIENT, LOW POWER | E12 stays AMBIENT. Its Spearman interval touches -1, with 0.5 percent degenerate draws. | 0.5 percent degenerate | findings/SIZE_ADJUSTED_COMPARISON.md | findings/data/comparison_effects.json classifications.E12_ingroup_on_no_peer_response | pass 6 Spearman, family at the time 228 |
| FRAGILE | S1 is FRAGILE. Summaries do not describe it as excluding zero. |  | findings/DISCOURSE_RECALL.md | findings/data/interval_stability.json fragile | in family as capacity_S1_irc_linked |
| FRAGILE | The H6 volume correlation is FRAGILE. Summaries do not describe it as excluding zero. Indicators that move with scale name merge Gini (H4) only. |  | findings/SIZE_ADJUSTED_COMPARISON.md | findings/data/interval_stability.json fragile | pass 6 volume correlation |
| STABLE | Author-basis merge Gini (H4) tracks log pull-request volume at 0.860. | 0.860 | findings/SIZE_ADJUSTED_COMPARISON.md | findings/data/size_adjusted_health.json indicator_volume_spearman.H4_gini_merges | pass 6 |
| AMBIENT, LOW POWER | E3's Spearman correlation with the refit residual is 0.429, q=0.431. The class is AMBIENT. The interval touches 1, with 2.4 percent degenerate draws. | 0.429 | findings/RESEARCH_METHODOLOGY.md | findings/data/pass7_merged_by.json e3.correlation | pass7.E3_spearman_versus_size_adjusted_residual |
| CONFIRMED | The Benjamini-Hochberg family is 229 tests. No prior q crossed 0.05. | 229 | findings/RESEARCH_METHODOLOGY.md | findings/data/pass7_merged_by.json bh_family_size | passes 1 through 7 |
| EXPLORATORY, NOT IN FAMILY | Core's matched-size self-merge residual with the distinct-mergers control is 0.343, and the interval covers zero. | 0.343 | findings/RESEARCH_METHODOLOGY.md | findings/data/pass7_merged_by.json self_merge.core.residual | not in family |
| LOW POWER | Core's published size-adjusted residual is about -0.0003, rank 10 of 17, and the interval covers zero. | -0.0003 | findings/SIZE_ADJUSTED_COMPARISON.md | findings/data/size_adjusted_health.json samples.all_repositories.core_residual | pass 6 |
| LOW POWER | After merger Gini replaces author-basis H4, Core's refit residual is -0.070, rank 3 of 17, and the interval covers zero. | -0.070 | findings/RESEARCH_METHODOLOGY.md | findings/data/pass7_merged_by.json size_adjusted_health.core_residual | not a new family test |
| CONFIRMED | Out-group merged code fixes forward at 7.0 percent against 8.3 percent for in-group. The coefficient is -0.417, q=0.098. The claim is that out-group code does not fail more. | 0.070 and 0.083 | findings/MERGE_DURABILITY.md | findings/data/merge_durability.json out_vs_in.fix_forward | in family |
| CONFIRMED | The 2026-09-10 roster snapshot has 2,501 self-merges out of 9,793, and 1,129 of those self-merges have zero GitHub review objects (45.1 percent). | 2,501 of 9,793 | findings/MERGE_PATTERN_BREAKDOWN.md | findings/data/merge_pattern_analysis.json self_merge_breakdown | not in family |
| CONFIRMED | Revealed rough consensus counts 2,572 self-merges out of 16,845 merges of any author. | 2,572 of 16,845 | findings/REVEALED_ROUGH_CONSENSUS.md | findings/data/revealed_rough_consensus.json windows.all_time.merged | not in family |
| DATA FRESHNESS | A 2026-10-12 recount of the same roster function on the current dump returns 2,514 self-merges out of 9,874, and 1,131 with zero review objects. Reports stay on the September snapshot. | 2,514 of 9,874 | findings/RESEARCH_METHODOLOGY.md | live recount, not a replacement of merge_pattern_analysis.json | not in family |
| CONFIRMED | The Satoshi file holds 1,769 rows, and 1,205 remain after hashing path plus a content prefix. The figure 549 does not describe this file. | 1,769 | findings/RESEARCH_METHODOLOGY.md | data/satoshi_archive/satoshi_communications.jsonl | not in family |
| RETRACTED | the project got harder for everyone |  | findings/CLAIMS_LEDGER.md | findings/data/newcomer_divergence.json |  |
| RETRACTED | review capacity starvation explains newcomer silence |  | findings/CLAIMS_LEDGER.md | findings/data/first_year_signal_analysis.json |  |
| RETRACTED | the first-year merge gap detects patch quality |  | findings/CLAIMS_LEDGER.md | findings/data/first_year_signal_analysis.json |  |
| RETRACTED | Core is uniquely sick on the attention effects |  | findings/CLAIMS_LEDGER.md | findings/data/comparison_effects.json classifications |  |
| RETRACTED | last-place shared-health rank survives size adjustment |  | findings/CLAIMS_LEDGER.md | findings/data/pass7_merged_by.json size_adjusted_health.core_residual |  |
| RETRACTED | merge Gini of 0.85 is extreme by comparison with income inequality |  | findings/CLAIMS_LEDGER.md | findings/data/size_adjusted_health.json indicator_volume_spearman.H4_gini_merges |  |
| RETRACTED | out-group code is worse after merge |  | findings/CLAIMS_LEDGER.md | findings/data/merge_durability.json out_vs_in.fix_forward |  |
| FRAGILE | Fragile ids are capacity_S1_irc_linked, volume_spearman.H6_median_days_to_decision. |  | findings/data/interval_stability.json | findings/data/interval_stability.json fragile |  |

## Retracted claims

- RETRACTED. rust-bitcoin and rust-miniscript show a practice that serves newcomers. Replacement: A positive interaction in this set is unresolved or driven by incumbent decline. It is not evidence of better newcomer treatment.
- RETRACTED. the project got harder for everyone. Replacement: Newcomer merge rates fall while incumbent rates rise. The series are not one bar for everyone.
- RETRACTED. review capacity starvation explains newcomer silence. Replacement: Silence rises while the queue per reviewer falls.
- RETRACTED. the first-year merge gap detects patch quality. Replacement: Reception, not the patch-content score, lines up with the first-year merge gap.
- RETRACTED. Core is uniquely sick on the attention effects. Replacement: The attention effects that have estimates are AMBIENT.
- RETRACTED. last-place shared-health rank survives size adjustment. Replacement: After merger Gini replaces author-basis H4, Core's refit residual is -0.070, rank 3 of 17, and the interval covers zero.
- RETRACTED. merge Gini of 0.85 is extreme by comparison with income inequality. Replacement: Author-basis H4 is a volume correlation inside this corpus.
- RETRACTED. out-group code is worse after merge. Replacement: Out-group merged code does not fail more on the fix-forward contrast.

## What this cannot prove

The ledger records the status of a measurement. It does not turn a LOW POWER interval that covers zero into a cause. The blinded audit is scored in `findings/data/audit_results.json`. Later reviewers minus leavers: correctness 0.020 (interval -0.207 to 0.260), scope discipline -0.033 (interval -0.280 to 0.193), test coverage -0.680 (interval -1.307 to -0.087), clarity 0.093 (interval -0.267 to 0.493). n is 60 and 100. One coder, so agreement is not measured.

