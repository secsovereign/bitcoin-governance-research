# What the first year shows

**Date:** 2026-10-07  
**Machine-readable:** `findings/data/first_year_signal_analysis.json`  
**Problem:** What in a contributor's first year separates people who later enter the rolling top 20 from people who are gone by 24 months?

G1 later entered the rolling 24-month top 20. G2 never entered and authored no PR at or after 24 months. The pass-2 d=0.73 used the cumulative top 20. This pass recomputes the within-cohort merge gap on the rolling groups and decomposes that gap. T2c, the merge rate, is not used as a predictor of itself.

G1: 65 people who entered the rolling 24-month top 20. G2: 1823 people who never entered it and authored nothing at or after 24 months. Training years 2010–2023. The pass-2 figure d=0.73 is the cumulative top 20 in two-year cohorts. The rolling groups recomputed here have within-cohort merge d=0.78 (interval 0.593 to 0.972).

## Decomposition

Size and prior pull requests leave d=0.41. Patch content (lines, files, consensus paths, test-only share, bugfix titles, directories) leaves d=0.44 (interval 0.244 to 0.600). Review reception (tone received, a top-5 ACK, review cycles), with size held fixed, leaves d=0.02 (interval -0.234 to 0.286).

The social block alone leaves d=0.17 (interval 0.011 to 0.327). Reception and social participation together leave d=0.14.

Each block alone closes more than half the gap, and neither adds as much as 0.1 d once the other is controlled. The blocks are redundant on the merge-rate gap. The ordered technical rule also matches, but the technical block contains review reception (tone, a top-5 ACK, review cycles), which is a community response. Use the content-versus-reception split before reading the gap as detection of technical quality.

Patch content does not close the gap. The closure inside the technical block is review reception, which is the community's own first-year response.

## Contrasts that clear the joint q threshold

Means of lines changed are outlier-driven. Medians are the readable size comparison. Where Cohen's d exceeds 2, the rate gap is the effect to cite.

### T1b

G1 median 2.00, mean 2.77 (n=60). G2 median 1.00, mean 55.82 (n=1740). Mean gap -53.052. Cohen's d -0.27 (small). Standardized difference -0.21. q=0.003. Holdout same sign: True.

The mean gap is outlier-driven. Cite the medians and the standardized difference.

### T2b

G1 median 0.61, mean 0.58 (n=36). G2 median 0.00, mean 0.21 (n=1226). Mean gap 0.371. Cohen's d 0.92 (large). Standardized difference 0.68. q=0.011. Holdout same sign: True.



### T2c

G1 median 0.70, mean 0.67 (n=60). G2 median 0.00, mean 0.31 (n=1740). Mean gap 0.359. Cohen's d 0.78 (medium). Standardized difference 0.60. q=0.003. Holdout same sign: True.



### T2d

G1 median 4.10, mean 5.68 (n=38). G2 median 1.33, mean 2.87 (n=447). Mean gap 2.813. Cohen's d 1.25 (large). Standardized difference 0.78. q=0.003. Holdout same sign: False.

Training contrast clears q. The 2024-2026 sign did not match.

### S2

G1 median 0.18, mean 0.19 (n=59). G2 median 0.00, mean 0.05 (n=1009). Mean gap 0.140. Cohen's d 1.44 (large). Standardized difference 0.93. q=0.003. Holdout same sign: True.



### S3_any

G1 median 0.00, mean 0.31 (n=35). G2 median 0.00, mean 0.05 (n=1299). Mean gap 0.269. Cohen's d 1.34 (large). Standardized difference 1.53. q=0.003. Holdout same sign: True.



### S4

G1 median 1.00, mean 0.60 (n=42). G2 median 0.00, mean 0.03 (n=1403). Mean gap 0.567. Cohen's d 3.35 (large). Standardized difference 1.72. q=0.003. Holdout same sign: True.

Cohen's d above 2 is a small-cell statistic. Cite the rate gap.



## Contrasts withheld from the lead

- **T1a:** G1 mean 50.72, G2 mean 11025.35, d=-0.21, q=0.296. Does not clear the joint q threshold.
- **T1c:** G1 mean 0.10, G2 mean 0.13, d=0.00, q=0.807. Negligible effect size.
- **T1d:** G1 mean 0.07, G2 mean 0.07, d=0.17, q=0.348. Negligible effect size.
- **T1e:** G1 mean 0.17, G2 mean 0.17, d=-0.02, q=0.903. Negligible effect size.
- **T2a:** G1 mean 0.21, G2 mean 0.18, d=0.09, q=0.911. Negligible effect size.
- **T3a:** G1 mean 35.23, G2 mean 13.04, d=1.08, q=0.792. Does not clear the joint q threshold.
- **T3b:** G1 mean 32.25, G2 mean 11.10, d=1.21, q=0.810. Does not clear the joint q threshold.
- **S1:** G1 mean 0.72, G2 mean 0.71, d=0.56, q=0.006. Marginal rates almost match. Do not cite the within-cohort d as the size of the gap.
- **S3_count:** G1 mean 3.86, G2 mean 0.21, d=1.88, q=0.026. Both medians are zero. The mean is a tail. Cite the any-versus-none share.
- **S5:** G1 mean 0.03, G2 mean 0.01, d=0.12, q=0.479. Negligible effect size.


## False negatives

Full technical composite, which includes reception and the merge rate: 284 of 1740 leavers sit in G1's top quartile. Their social composite minus G1 is -0.39 (d=-0.79).

Patch content only: 340 of 1740. Social gap -0.40 (d=-0.90, large). These leavers resemble later entrants on the patch measures and score lower on social legibility.

## Silence

Unanswered newcomer pull requests are lower on S3_reviews_before_first, S4_early_reciprocity after technical controls. The year slope of silence is 0.014 without those indicators and 0.039 with them. The slope does not shrink. The cross-section is not the time trend.

## Follow-up

The 340 patch-content leavers are classified STRUCTURAL. 45.6% entered before 2018 and 54.4% entered in 2018 or later. The false-negative rate changes by -0.2 percentage points per year of entry (interval -0.8 to 0.4 percentage points, q=0.644). The positive-slope test does not clear the threshold, so the filter is present across the whole series.

Subsystem reviewer capacity is classified NOT SUBSYSTEM CAPACITY. On newcomer pull requests in the review-object era, silence rises 2.4 percentage points per year before the subsystem's active-reviewer count and 4.1 percentage points per year after it. The slope widens. Those figures are percentage points per calendar year. They are a different scale from the standardized coefficients 0.014 and 0.039 above.

The year-by-year counts, cohort rates, and subsystem cells are in `GAP_CLOSURE.md`.

## What this cannot prove

- T and S proxies are imperfect measures of technical quality and social legibility.
- IRC-linked PRs are identified by number matching and miss discussions that never name the PR.
- G1 has on the order of 65 members and matched cohort cells are small. Treat the results as exploratory until they are replicated on comparison repositories.
- Social legibility and technical quality are partly correlated in any expert community. Separating them from observational data is inherently limited.


**Generated by:** `scripts/reporting/generate_from_templates.py`
