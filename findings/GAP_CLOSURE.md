# What the four open measurements show

**Date:** 2026-10-07  
**Machine-readable:** `findings/data/gap_closure_analysis.json`  
**Problem:** Which of the measurements left open after the first four passes can be closed with the records already in the corpus?

Fit 2010–2023, confirm 2024–2026. Bootstrap 1000, seed 7. Benjamini-Hochberg family size 159, passes 1–5. Year enters the silence model as a linear term because year dummies would absorb the slope under test. The other shared controls are log lines changed, files touched, and author tenure.

Related: `COMMONS_MECHANISMS.md` (the six effects and the shared-indicator rank), `FIRST_YEAR_TRAJECTORY.md` (the 340 patch-content leavers and the silence slope those indicators do not explain).

## Principle scores and later health

Ranked by the t+1 correlation, the top two are P6 and P1 and the bottom two are P4 and P8. A positive correlation means a lower score in year t lines up with a lower health index in t+1. P6 is r=0.714 (n=13, interval 0.271 to 0.944, q=0.016). The t+2 correlation is r=0.853, q=0.002. P1 is second in the ranking and does not clear the threshold. Every lag is LOW POWER. P8 clears the threshold in the opposite direction: a higher nested-decision score lines up with a lower later health index.

| Principle | Largest drop | Score that year | Year before | Year after | t+1 r | t+1 interval | t+1 q | t+2 r | t+2 q |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P1 boundaries | 2011 | 0.454 | 2010 (1.000) | 2012 (0.772) | 0.258 | -0.378 to 0.743 | 0.543 LOW POWER | -0.105 | 0.841 |
| P2 congruence | 2024 | 0.671 | 2023 (0.975) | 2025 (0.889) | -0.510 | -0.920 to 0.090 | 0.164 LOW POWER | -0.655 | 0.065 |
| P3 collective choice | 2025 | 0.268 | 2024 (0.758) | 2026 (0.454) | -0.490 | -0.814 to -0.015 | 0.190 LOW POWER | -0.255 | 0.596 |
| P4 monitoring | 2014 | 0.621 | 2013 (0.768) | 2015 (0.665) | -0.516 | -0.842 to 0.096 | 0.134 LOW POWER | -0.294 | 0.503 |
| P5 sanctions | DATA UNAVAILABLE | — | — | — | — | — | — | — | — |
| P6 conflict resolution | 2014 | 0.519 | 2013 (0.857) | 2015 (0.592) | 0.714 | 0.271 to 0.944 | 0.016 LOW POWER | 0.853 | 0.002 |
| P7 organizing rights | DATA UNAVAILABLE | — | — | — | — | — | — | — | — |
| P8 nested decisions | 2026 | 0.333 | 2025 (1.000) | — | -0.717 | -0.957 to -0.175 | 0.016 LOW POWER | -0.681 | 0.037 |


2024–2026 does not contain enough paired years to confirm any lagged correlation.

### P1 boundaries

| Year | Score | Health | Health next year |
| --- | --- | --- | --- |
| 2010 | 1.000 | 0.823 | 0.495 |
| 2011 | 0.454 | 0.495 | 0.481 |
| 2012 | 0.772 | 0.481 | 0.467 |
| 2013 | 0.518 | 0.467 | 0.459 |
| 2014 | 0.546 | 0.459 | 0.485 |
| 2015 | 0.724 | 0.485 | 0.472 |
| 2016 | 0.581 | 0.472 | 0.457 |
| 2017 | 0.530 | 0.457 | 0.424 |
| 2018 | 0.677 | 0.424 | 0.436 |
| 2019 | 0.760 | 0.436 | 0.460 |
| 2020 | 0.399 | 0.460 | 0.446 |
| 2021 | 0.763 | 0.446 | 0.447 |
| 2022 | 0.660 | 0.447 | 0.419 |
| 2023 | 0.768 | 0.419 | 0.428 |
| 2024 | 0.562 | 0.428 | 0.407 |
| 2025 | 0.591 | 0.407 | 0.478 |
| 2026 | 0.411 | 0.478 | — |

### P2 congruence

| Year | Score | Health | Health next year |
| --- | --- | --- | --- |
| 2011 | 0.362 | 0.495 | 0.481 |
| 2012 | 0.305 | 0.481 | 0.467 |
| 2013 | 0.084 | 0.467 | 0.459 |
| 2014 | 0.216 | 0.459 | 0.485 |
| 2015 | 0.583 | 0.485 | 0.472 |
| 2016 | 0.533 | 0.472 | 0.457 |
| 2017 | 0.354 | 0.457 | 0.424 |
| 2018 | 0.402 | 0.424 | 0.436 |
| 2019 | 0.399 | 0.436 | 0.460 |
| 2020 | 0.716 | 0.460 | 0.446 |
| 2021 | 0.674 | 0.446 | 0.447 |
| 2022 | 0.765 | 0.447 | 0.419 |
| 2023 | 0.975 | 0.419 | 0.428 |
| 2024 | 0.671 | 0.428 | 0.407 |
| 2025 | 0.889 | 0.407 | 0.478 |
| 2026 | 0.744 | 0.478 | — |

### P3 collective choice

| Year | Score | Health | Health next year |
| --- | --- | --- | --- |
| 2011 | 0.344 | 0.495 | 0.481 |
| 2012 | 0.311 | 0.481 | 0.467 |
| 2013 | 0.368 | 0.467 | 0.459 |
| 2014 | 0.412 | 0.459 | 0.485 |
| 2015 | 0.176 | 0.485 | 0.472 |
| 2016 | 0.185 | 0.472 | 0.457 |
| 2017 | 0.438 | 0.457 | 0.424 |
| 2018 | 0.368 | 0.424 | 0.436 |
| 2019 | 0.748 | 0.436 | 0.460 |
| 2020 | 0.839 | 0.460 | 0.446 |
| 2021 | 0.592 | 0.446 | 0.447 |
| 2022 | 0.631 | 0.447 | 0.419 |
| 2023 | 0.347 | 0.419 | 0.428 |
| 2024 | 0.758 | 0.428 | 0.407 |
| 2025 | 0.268 | 0.407 | 0.478 |
| 2026 | 0.454 | 0.478 | — |

### P4 monitoring

| Year | Score | Health | Health next year |
| --- | --- | --- | --- |
| 2010 | 0.281 | 0.823 | 0.495 |
| 2011 | 0.190 | 0.495 | 0.481 |
| 2012 | 0.403 | 0.481 | 0.467 |
| 2013 | 0.768 | 0.467 | 0.459 |
| 2014 | 0.621 | 0.459 | 0.485 |
| 2015 | 0.665 | 0.485 | 0.472 |
| 2016 | 0.656 | 0.472 | 0.457 |
| 2017 | 0.723 | 0.457 | 0.424 |
| 2018 | 0.721 | 0.424 | 0.436 |
| 2019 | 0.666 | 0.436 | 0.460 |
| 2020 | 0.621 | 0.460 | 0.446 |
| 2021 | 0.758 | 0.446 | 0.447 |
| 2022 | 0.630 | 0.447 | 0.419 |
| 2023 | 0.651 | 0.419 | 0.428 |
| 2024 | 0.690 | 0.428 | 0.407 |
| 2025 | 0.853 | 0.407 | 0.478 |
| 2026 | 0.903 | 0.478 | — |

### P6 conflict resolution

| Year | Score | Health | Health next year |
| --- | --- | --- | --- |
| 2010 | 1.000 | 0.823 | 0.495 |
| 2011 | 0.770 | 0.495 | 0.481 |
| 2012 | 0.675 | 0.481 | 0.467 |
| 2013 | 0.857 | 0.467 | 0.459 |
| 2014 | 0.519 | 0.459 | 0.485 |
| 2015 | 0.592 | 0.485 | 0.472 |
| 2016 | 0.384 | 0.472 | 0.457 |
| 2017 | 0.357 | 0.457 | 0.424 |
| 2018 | 0.535 | 0.424 | 0.436 |
| 2019 | 0.411 | 0.436 | 0.460 |
| 2020 | 0.325 | 0.460 | 0.446 |
| 2021 | 0.216 | 0.446 | 0.447 |
| 2022 | 0.311 | 0.447 | 0.419 |
| 2023 | 0.000 | 0.419 | 0.428 |
| 2024 | 0.435 | 0.428 | 0.407 |
| 2025 | 0.475 | 0.407 | 0.478 |
| 2026 | 0.648 | 0.478 | — |

### P8 nested decisions

| Year | Score | Health | Health next year |
| --- | --- | --- | --- |
| 2010 | 0.000 | 0.823 | 0.495 |
| 2011 | 0.167 | 0.495 | 0.481 |
| 2012 | 0.167 | 0.481 | 0.467 |
| 2013 | 0.167 | 0.467 | 0.459 |
| 2014 | 0.167 | 0.459 | 0.485 |
| 2015 | 0.414 | 0.485 | 0.472 |
| 2016 | 0.333 | 0.472 | 0.457 |
| 2017 | 0.333 | 0.457 | 0.424 |
| 2018 | 0.368 | 0.424 | 0.436 |
| 2019 | 0.368 | 0.436 | 0.460 |
| 2020 | 0.498 | 0.460 | 0.446 |
| 2021 | 0.444 | 0.446 | 0.447 |
| 2022 | 0.566 | 0.447 | 0.419 |
| 2023 | 0.581 | 0.419 | 0.428 |
| 2024 | 0.500 | 0.428 | 0.407 |
| 2025 | 1.000 | 0.407 | 0.478 |
| 2026 | 0.333 | 0.478 | — |



P5 (sanctions) and P7 (organizing rights) have no scored year. Both are DATA UNAVAILABLE.

## Cross-repository effects

Comparison dumps store author, title, body, timestamps, merged state, and comments_count. They do not store review objects, comment authors, file paths, or a meeting list. comments_count is not used as a stand-in for participants.

- bitcoin-core/bitcoin-maintainer-tools: shared health 0.72, 11 years. E2, E3, E5, E7, E9, and E12 are DATA UNAVAILABLE.
- rust-bitcoin/rust-miniscript: shared health 0.70, 9 years. E2, E3, E5, E7, E9, and E12 are DATA UNAVAILABLE.
- ACINQ/eclair: shared health 0.65, 11 years. E2, E3, E5, E7, E9, and E12 are DATA UNAVAILABLE.
- bitcoindevkit/bdk: shared health 0.65, 7 years. E2, E3, E5, E7, E9, and E12 are DATA UNAVAILABLE.
- lightningnetwork/lnd: shared health 0.65, 11 years. E2, E3, E5, E7, E9, and E12 are DATA UNAVAILABLE.
- sparrowwallet/sparrow: shared health 0.64, 7 years. E2, E3, E5, E7, E9, and E12 are DATA UNAVAILABLE.
- rust-bitcoin/rust-bitcoin: shared health 0.64, 13 years. E2, E3, E5, E7, E9, and E12 are DATA UNAVAILABLE.
- ElementsProject/lightning: shared health 0.64, 12 years. E2, E3, E5, E7, E9, and E12 are DATA UNAVAILABLE.
- lightningdevkit/rust-lightning: shared health 0.62, 9 years. E2, E3, E5, E7, E9, and E12 are DATA UNAVAILABLE.
- SeedSigner/seedsigner: shared health 0.62, 7 years. E2, E3, E5, E7, E9, and E12 are DATA UNAVAILABLE.
- lightning/bolts: shared health 0.61, 11 years. E2, E3, E5, E7, E9, and E12 are DATA UNAVAILABLE.
- bitcoin-core/HWI: shared health 0.60, 9 years. E2, E3, E5, E7, E9, and E12 are DATA UNAVAILABLE.
- bitcoin-core/secp256k1: shared health 0.59, 13 years. E2, E3, E5, E7, E9, and E12 are DATA UNAVAILABLE.


Repositories below seven years, omitted from the comparison:

- foundation-devices/passport-firmware: 3 distinct years of history, below the 7-year minimum. Shared health 0.67.
- stratum-mining/stratum: 6 distinct years of history, below the 7-year minimum. Shared health 0.65.
- stratum-mining/sv2-spec: 5 distinct years of history, below the 7-year minimum. Shared health 0.69.


Bitcoin Core reference, the pass-3 estimates. The q column here is the passes 1–5 family. `COMMONS_MECHANISMS.md` keeps the q from the pass-3 family. The estimates are the same numbers.

- **E2_reciprocity_excess:** 0.024 (interval 0.023 to 0.025). Kind: excess_over_null. Passes 1–5 q=0.006. 2024–2026 same sign: True. pass 3 reports a coefficient or an excess, not a Cohen's d
- **E3_log_hours_to_next_same_direction_top5_minus_other:** -0.471 (interval -0.555 to -0.383). Kind: cohens_d. Passes 1–5 q=0.003. 2024–2026 same sign: True. Cohen's d=-0.471.
- **E5_log_participants_on_log_days:** 0.863 (interval 0.841 to 0.884). Kind: standardized_coefficient. Passes 1–5 q=0.003. 2024–2026 same sign: True. pass 3 reports a coefficient or an excess, not a Cohen's d
- **E7_first_tone_on_merge_given_later_tone:** 0.310 (interval 0.265 to 0.355). Kind: standardized_coefficient. Passes 1–5 q=0.003. 2024–2026 same sign: True. pass 3 reports a coefficient or an excess, not a Cohen's d
- **E9_listed_on_log_days_to_merge:** 0.251 (interval 0.224 to 0.278). Kind: standardized_coefficient. Passes 1–5 q=0.003. 2024–2026 same sign: True. pass 3 reports a coefficient or an excess, not a Cohen's d
- **E12_ingroup_on_no_peer_response:** -0.493 (interval -0.596 to -0.396). Kind: standardized_coefficient. Passes 1–5 q=0.003. 2024–2026 same sign: True. pass 3 reports a coefficient or an excess, not a Cohen's d


Spearman correlation of each effect size with repository health:

- E2_reciprocity_excess: DATA UNAVAILABLE. 0 repositories have both an effect size and a health index
- E3_log_hours_to_next_same_direction_top5_minus_other: DATA UNAVAILABLE. 0 repositories have both an effect size and a health index
- E5_log_participants_on_log_days: DATA UNAVAILABLE. 0 repositories have both an effect size and a health index
- E7_first_tone_on_merge_given_later_tone: DATA UNAVAILABLE. 0 repositories have both an effect size and a health index
- E9_listed_on_log_days_to_merge: DATA UNAVAILABLE. 0 repositories have both an effect size and a health index
- E12_ingroup_on_no_peer_response: DATA UNAVAILABLE. 0 repositories have both an effect size and a health index


E2_reciprocity_excess: DATA UNAVAILABLE. Comparison repositories do not contain the review objects, participant identities, or meeting lists this effect needs, so it is not identified as specific to poorly governed repositories or as ambient to open source development.

E3_log_hours_to_next_same_direction_top5_minus_other: DATA UNAVAILABLE. Comparison repositories do not contain the review objects, participant identities, or meeting lists this effect needs, so it is not identified as specific to poorly governed repositories or as ambient to open source development.

E5_log_participants_on_log_days: DATA UNAVAILABLE. Comparison repositories do not contain the review objects, participant identities, or meeting lists this effect needs, so it is not identified as specific to poorly governed repositories or as ambient to open source development.

E7_first_tone_on_merge_given_later_tone: DATA UNAVAILABLE. Comparison repositories do not contain the review objects, participant identities, or meeting lists this effect needs, so it is not identified as specific to poorly governed repositories or as ambient to open source development.

E9_listed_on_log_days_to_merge: DATA UNAVAILABLE. Comparison repositories do not contain the review objects, participant identities, or meeting lists this effect needs, so it is not identified as specific to poorly governed repositories or as ambient to open source development.

E12_ingroup_on_no_peer_response: DATA UNAVAILABLE. Comparison repositories do not contain the review objects, participant identities, or meeting lists this effect needs, so it is not identified as specific to poorly governed repositories or as ambient to open source development.



## False-negative timeline

Classification: STRUCTURAL. 340 of 1740 training leavers sit in the top patch-content quartile of later top-20 entrants. The recount matches the pass-4 count of 340. 155 (45.6%) entered before 2018 and 185 (54.4%) entered in 2018 or later. The rate changes by -0.2 percentage points per year of entry (interval -0.8 to 0.4 percentage points, q=0.644).

| Cohort | Leavers | False negatives | Rate |
| --- | --- | --- | --- |
| 2010-2011 | 75 | 15 | 20.0% |
| 2012-2013 | 129 | 24 | 18.6% |
| 2014-2015 | 237 | 55 | 23.2% |
| 2016-2017 | 311 | 61 | 19.6% |
| 2018-2019 | 390 | 60 | 15.4% |
| 2020-2021 | 324 | 78 | 24.1% |
| 2022-2023 | 274 | 47 | 17.2% |


On the training cutoff, 20.5% of 83 leavers who entered in 2024–2026 are in the same patch-content quartile. That rate is a description of the holdout. It is not a second test.

## Silence and subsystem capacity

Classification: NOT SUBSYSTEM CAPACITY. The logistic coefficient on a subsystem's active reviewers is -0.244 log-odds per standard deviation (interval -0.389 to -0.118, q=0.003, n=4124). The 2024–2026 coefficient is -0.322, same sign=True. With year dummies in place of the linear year term, the coefficient is -0.556 (interval -0.704 to -0.418). That check is outside the correction family.

Silence rises 2.4 percentage points per year (interval 1.6 to 3.2 percentage points) before reviewer count, and 4.1 percentage points per year (interval 3.2 to 5.0 percentage points) after it. The slope widens. Reviewer count is associated with less silence in the cross-section, and the time trend remains.

Pearson r of active reviewers with the newcomer silence rate, across subsystem-years, is -0.102 (n=80, interval -0.265 to 0.097, q=0.520). Cohen's d for silence in high-reviewer versus low-reviewer cells is -0.030 (negligible effect size regardless of p-value). Entropy changes by 0.148 bits per year (interval 0.073 to 0.241, q=0.006, n=14 years). Newcomer pull requests in the corpus: 7733.

Entropy of the newcomer-pull-request distribution, in bits. The fitted slope uses these years.

| Year | Entropy |
| --- | --- |
| 2010 | 0.00 |
| 2011 | 1.76 |
| 2012 | 1.82 |
| 2013 | 2.02 |
| 2014 | 2.18 |
| 2015 | 2.00 |
| 2016 | 2.85 |
| 2017 | 2.90 |
| 2018 | 2.89 |
| 2019 | 2.96 |
| 2020 | 2.85 |
| 2021 | 2.85 |
| 2022 | 2.80 |
| 2023 | 2.65 |


2010 is three newcomer pull requests and entropy 0.00. The series is 1.76 bits in 2011, 2.85 in 2016, and 2.65 in 2023. The positive slope is the rise out of the early years.

Newcomer pull requests by primary subsystem. A pull request that touches several subsystems is assigned to the one with the most files changed.

| Year | consensus | core | wallet | p2p | rpc | gui | test | docs | build | other |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2010 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| 2011 | 0 | 187 | 0 | 24 | 0 | 32 | 3 | 8 | 4 | 193 |
| 2012 | 0 | 278 | 0 | 29 | 0 | 198 | 4 | 29 | 2 | 41 |
| 2013 | 0 | 137 | 0 | 4 | 0 | 74 | 7 | 30 | 2 | 47 |
| 2014 | 9 | 256 | 2 | 11 | 0 | 78 | 23 | 60 | 2 | 95 |
| 2015 | 2 | 195 | 10 | 7 | 0 | 37 | 7 | 32 | 0 | 86 |
| 2016 | 19 | 118 | 35 | 5 | 25 | 45 | 37 | 37 | 4 | 90 |
| 2017 | 57 | 264 | 84 | 33 | 46 | 97 | 151 | 52 | 2 | 124 |
| 2018 | 48 | 231 | 50 | 18 | 26 | 113 | 115 | 74 | 14 | 161 |
| 2019 | 25 | 128 | 39 | 12 | 29 | 74 | 95 | 49 | 10 | 111 |
| 2020 | 15 | 77 | 32 | 15 | 21 | 32 | 120 | 26 | 2 | 57 |
| 2021 | 18 | 63 | 25 | 10 | 9 | 19 | 94 | 37 | 8 | 86 |
| 2022 | 14 | 79 | 29 | 6 | 20 | 15 | 97 | 22 | 5 | 61 |
| 2023 | 13 | 70 | 10 | 9 | 2 | 10 | 48 | 23 | 3 | 75 |
| 2024 | 21 | 80 | 13 | 7 | 8 | 4 | 104 | 50 | 4 | 81 |
| 2025 | 29 | 131 | 22 | 13 | 10 | 11 | 114 | 63 | 2 | 127 |
| 2026 | 27 | 130 | 41 | 19 | 18 | 7 | 114 | 47 | 1 | 63 |

Silence rate and active reviewers at the two ends of the review-object window. An active reviewer has five or more review objects in that subsystem that year. Pre-2016 reviewer counts are DATA UNAVAILABLE.

| Subsystem | 2016 newcomers | 2016 silence | 2016 reviewers | 2023 newcomers | 2023 silence | 2023 reviewers |
| --- | --- | --- | --- | --- | --- | --- |
| consensus | 19 | 15.8% | 8 | 13 | 15.4% | 18 |
| core | 118 | 8.5% | 17 | 70 | 20.0% | 49 |
| wallet | 35 | 11.4% | 6 | 10 | 0.0% | 25 |
| p2p | 5 | 0.0% | 7 | 9 | 11.1% | 22 |
| rpc | 25 | 4.0% | 7 | 2 | 0.0% | 12 |
| gui | 45 | 22.2% | 5 | 10 | 90.0% | 4 |
| test | 37 | 0.0% | 3 | 48 | 10.4% | 48 |
| docs | 37 | 2.7% | 3 | 23 | 8.7% | 11 |
| build | 4 | 0.0% | 0 | 3 | 66.7% | 2 |
| other | 90 | 7.8% | 5 | 75 | 76.0% | 20 |


In 2023, GUI newcomer silence is 90.0% (10 pull requests, 4 active reviewers). Core newcomer silence is 20.0% (70 pull requests, 49 active reviewers). The project-wide year slope still widens once reviewer count is held fixed.

## What this closes

- Gap 1. P6's t+1 correlation with later health is 0.714 (q=0.016) on 13 years, marked LOW POWER. P5 and P7 stay unscored.
- Gap 2 stays open. Comparison repositories lack review objects, participant identities, and meeting lists, so the six effects cannot be placed against health.
- Gap 3. The 340 patch-content false negatives are STRUCTURAL.
- Gap 4. The silence trend is NOT SUBSYSTEM CAPACITY. The reviewer coefficient is negative and the year slope widens.


## What this cannot prove

- Lagged correlations in a 16-year series are low power and cannot establish causation.
- Cross-repo effect comparisons assume comparable data quality across repositories, which may not hold.
- Subsystem mapping from file paths is an approximation and PRs touching multiple subsystems are assigned by plurality.
- The false-negative timeline cannot distinguish whether the filter worsened because standards rose or because social routing became more load-bearing over time.


**Generated by:** `scripts/reporting/generate_from_templates.py`
