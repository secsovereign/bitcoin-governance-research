# Research methodology

The question is descriptive. It asks how merge authority, review attention, and newcomer outcomes are distributed in Bitcoin Core, and which of those patterns also appear in other Bitcoin repositories of similar age.

The commons vocabulary is the lens for the measurement passes. It names the resource as reviewer attention and merge authority. It is not a prescription for what the project should do.

Observation runs from 2010 through 2026. Estimates are fit on 2010 through 2023. The holdout is 2024 through 2026, and a report states whether the holdout sign matches. Bootstrap draws are 1000, seed 7, with a 95 percent interval. A test with fewer than 20 independent units is LOW POWER. A missing input is DATA UNAVAILABLE. `comments_count` is not a participant count. The merged flag is not `merged_by`. Pre-2016 GitHub Review objects are absent and are not coded as zero. When Cohen's d is above 2 on a small cell, the rate gap is the figure to cite.

## 1. Sources

GitHub pull requests, reviews, and issues for bitcoin/bitcoin are in `data/github/prs_raw.jsonl` and `data/processed/enriched_prs.jsonl`. Comparison repositories are under `data/github/repos/`. Informal channels are the two mailing lists, IRC, Delving Bitcoin, and Bitcointalk. Bitcointalk citations use the stored post count of 158,917. The topic `n_posts` field over-counts.

The Satoshi file is `data/satoshi_archive/satoshi_communications.jsonl`. It holds 1,769 rows. Hashing the stored path together with a content prefix leaves 1,205 distinct rows. Sources are github_archive 1,174, nakamoto_institute 590, mailing_list 4, and p2p_research 1. The stored `type` field is unknown for 1,156 rows and missing for 595, so it does not support the older content-type split into 14 emails and 22 code releases. The figure 549 does not describe this file.

## 2. Identity and merge keys

Bitcoin Core uses the identity index. Comparison repositories in the seven-year set are keyed on numeric GitHub user id. That key merged 0 additional logins in those dumps, and 0 people had more than one login. Short-history repositories without an author-id file are DATA UNAVAILABLE for that check. TheCharlatan and sedited stay distinct in the index. Live merge keys since 2023 are fanquake, achow101, sedited, glozow, ryanofsky, hebasto, and maflcko.

## 3. Self-merge and review counts

A self-merge is a merged pull request whose author and `merged_by` are the same person. A missing `merged_by` is not a self-merge.

Two denominators are in the committed artifacts.

The roster breakdown in `findings/data/merge_pattern_analysis.json` (written 2026-09-10) counts merged pull requests whose author is on the maintainer roster. That file has 2,501 self-merges out of 9,793 roster-authored merges (25.5 percent). Zero-review means a GitHub review object whose state is approved, changes requested, or commented is absent. On that definition, 1,129 of the 2,501 self-merges have zero review objects (45.1 percent of those self-merges, and 11.5 percent of the 9,793).

`findings/data/revealed_rough_consensus.json` counts every merged pull request, including ones a key holder merged for someone else. That file has 2,572 self-merges out of 16,845 merges.

The same roster function, run on `prs_raw.jsonl` as it stood on 2026-10-12, returns 2,514 self-merges out of 9,874 and 1,131 zero-review self-merges (45.0 percent and 11.5 percent). The reports stay on the 2026-09-10 artifact. The later file is larger. The review definition did not change.

Quality-weighted zero-review rates are a different procedure. A pull request is zero-review when the weighted count is below a threshold. `uniform_threshold_analysis.json` applies 0.3 to every merged pull request created from 2012 through 2020 and gets 30.3 percent (2,885 of 9,537). That window includes 1 September 2016 through 2020. The weighting code treats dates before 1 September 2016 as the pre-review era, when the threshold is 0.3, and later dates as the post-review era, when the threshold is 0.5. The stored 30.3 percent is the unsplit 0.3 rule, not that era split.

MAX and SUM are also a different contrast, in `max_vs_sum_comparison.json`. On the same 2012 through 2020 window, MAX gives 34.4 percent zero-review (3,279 of 9,537) and SUM gives 34.1 percent (3,252 of 9,537). Recent MAX, 2021 through 2025, is 3.3 percent (205 of 6,216). A uniform 0.5 threshold on the historical window is 40.5 percent (3,859 of 9,537). That 40.5 percent is the uniform threshold, not the MAX figure.

## 4. Measurement passes

Passes 1 through 7 are separate from the quality-weighted counts. `scripts/run_all_analyses.py` runs the older descriptive scripts. It does not run these passes. `scripts/run_measurement_passes.py` runs passes 1 through 7 in order and writes their JSON. It does not call `generate_all()`. Report markdown for gap closure and commons mechanisms stays the committed file, because the shared formatter replaces non-numeric template values with the word missing.

| Pass | Script | JSON |
| --- | --- | --- |
| 1 and 2 | `scripts/analysis/rsd_ingroup_test.py` | `rsd_ingroup_analysis.json`, `rsd_ingroup_analysis_v2.json` |
| 3 | `scripts/analysis/commons_dynamics_test.py` | `commons_dynamics_analysis.json` |
| 4 | `scripts/analysis/first_year_signal_test.py` | `first_year_signal_analysis.json` |
| 5 | `scripts/analysis/gap_closure_test.py`, `scripts/analysis/merge_durability.py` | `gap_closure_analysis.json`, `merge_durability.json` |
| 6 | `scripts/analysis/size_adjusted_health.py`, `scripts/analysis/comparison_effects.py`, `scripts/analysis/discourse_recall.py` | `size_adjusted_health.json`, `comparison_effects.json`, `discourse_recall.json` |
| 7 | `scripts/analysis/newcomer_divergence.py`, `scripts/validation/interval_stability.py`, `scripts/analysis/pass7_merged_by.py` | `newcomer_divergence.json`, `interval_stability.json`, `pass7_merged_by.json` |

The Benjamini-Hochberg family for passes 1 through 5 is 159 tests, in `gap_closure_analysis.json`. Quoted q values in the pass 1 through 5 reports are the family those reports were written against. They were not rewritten. Pass 6 brought the family to 228. Pass 7 adds one test, `pass7.E3_spearman_versus_size_adjusted_residual`, and the family is 229. The recomputed q values are in `pass7_merged_by.json`. No prior q crossed 0.05.

## 5. Cross-repository rules

Each rule is dated against the estimates it governs.

The 3-year series rule was set on 2026-10-11 in the newcomer divergence repair, before that file's gated classification was written. A group slope needs at least 3 years. A repository whose newcomer series or incumbent series is shorter is DATA UNAVAILABLE and is left out of the class count. The published Core interaction remains the pass 2 point.

The 6-repository minimum and the degeneracy check were set on 2026-10-11 in the comparison-effect rerun, and that rerun is the set of correlations they govern. A Spearman correlation with fewer than 6 repository estimates is DATA UNAVAILABLE, the class is UNDETERMINED, and no interval is reported. A bootstrap draw with fewer than 4 distinct repositories or with zero variance is degenerate. When an interval touches -1 or 1, the share of degenerate draws is reported. The minimum of 6 was not lowered.

The FRAGILE rule was set on 2026-10-11 after the published intervals existed. An estimate is FRAGILE when a fresh seed-7 bootstrap disagrees with the published interval on whether zero is excluded, or the published bound sits within 0.02 standardized units of zero. Published intervals are not replaced. S1 (`capacity_S1_irc_linked`) and the H6 volume correlation are FRAGILE. Summaries do not describe either as excluding zero. H4 and the Core newcomer interaction are stable. A sentence that lists indicators moving with scale names merge Gini (H4) only.

The 5-merger E3 rule and the distinct-mergers control were preregistered at 2026-10-11T21:48:08Z, before any comparison `merged_by` estimate and before any self-merge rate. A repository has an E3 estimate only when at least 5 distinct mergers appear in the trailing window for the pull requests being scored. If fewer than 6 repositories have an estimate, the correlation is DATA UNAVAILABLE and the class stays UNDETERMINED. Neither minimum is lowered. The matched-size self-merge regression adds log mean distinct mergers per year to log total pull requests, log mean distinct active contributors per year, and years of history. In a project with one or two mergers, self-merge is close to mandatory, so the rate falls as the merger count rises. That comparison is descriptive and outside the family.

## 6. Pass 7 measurements

H4 in the commons scoring spec is the Gini of merged pull-request counts across people who opened a pull request that year. That is an author basis. Merger Gini from `merged_by` replaces it. Shared health and the size-adjusted residual were refit because the indicator changed. The pass 6 residual file is unchanged. The refit is in `pass7_merged_by.json`. Core's published residual is about -0.0003, rank 10 of 17, and its interval covers zero. The refit residual is -0.070, interval -0.156 to 0.068, rank 3 of 17, and that interval also covers zero.

The pass 6 author-basis H4 correlation with log pull-request volume is 0.860, interval 0.588 to 0.970. That interval excludes zero. The figure is the volume correlation for author-basis H4.

E3 is the log-hour gap until the next same-direction review after a top-5 merger speaks first, minus the same gap after anyone else. Eight repositories have an estimate. The Spearman correlation with the refit residual is 0.429, interval -0.519 to 1.000. The interval touches 1, and 2.4 percent of draws are degenerate. The class is AMBIENT. The test is in the family. Its q is 0.431. The preregistered sign is positive, and the point is positive. The interval covers zero. The correlation is LOW POWER.

Core's self-merge rate on the identity index is 15.1 percent of merged pull requests, and 30.3 percent among pull requests authored by Core's own mergers. The size-and-merger residual is 0.343, interval -0.100 to 0.822. The interval covers zero.

The `merged_by` crawl covered 22,461 merged pull requests in the 13 seven-year repositories. 22,459 returned a merger login and a numeric user id. secp256k1 pull request 1804 is no longer served. Every repository is above 95 percent.

## 7. What this cannot prove

A size-adjusted residual is not a cause. Fewer than 20 repositories make every cross-repository correlation LOW POWER. The blinded audit of 160 pull requests has a rubric and a sample and no scores. Path-link precision is 0.015, from one reading of the first 280 characters. A second coder is still required. P5 and P7 need sources this corpus does not have, deleted comments and a person-to-funder ledger. ethereum/go-ethereum has no pull-request list, so it is not an outside peer.
