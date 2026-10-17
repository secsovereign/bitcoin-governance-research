# Post-merge durability

**Date:** 2026-10-09
**Machine-readable:** `findings/data/merge_durability.json`
**Problem:** Do merged patches from later entrants, from the 340 patch-content leavers, or from out-group authors fail more often after the merge, when failure is read from the code rather than from a reviewer.

Production lines introduced by a merge are followed for 12 and 24 months. A fix-forward is a later commit with a bugfix title, a Fixes reference, or a CVE reference that changes one of those lines. A revert is a later commit whose title starts with Revert and names the pull request, or whose message cites the merge hash. Neutral churn is every other removal. It is not counted as a defect. Survival is secondary, because a refactor removes a line without implying a defect. Pull requests whose horizon is past the tip of the repository are right-censored.

## Result

Out-group raw rates are not higher than in-group rates. The adjusted fix-forward coefficient is negative. The adjusted revert coefficient is the other way and its interval covers zero. The quality explanation does not gain support.

340 authors are the patch-content false negatives under the existing quartile rule. 16074 merges were traced.

Coded-group coefficients are log odds. For G1 versus G2 the coded group is G1. For the false-negative split the coded group is the 340. For the out-group split the coded group is out-group, so a negative coefficient is a lower failure log odds for out-group code. Year fixed effects, log lines changed, files touched, author tenure, path risk, and primary subsystem are the controls. Fit 2010 to 2023. The holdout is 2024 to 2026.

### G1 versus G2, first-year merged pull requests, 12 months

Fix-forward coefficient -0.182 (interval -0.751 to 0.512). q=0.719. n=1708. Cohen's d 0.055. Rate for the coded group 0.054, rate for the reference group 0.042. Holdout sign matches yes.

Revert coefficient 0.073 (interval -0.882 to 1.247). q=0.852. n=1708. Cohen's d -0.012. Rate for the coded group 0.019, rate for the reference group 0.020. Holdout sign matches yes.

Secondary survival, share of introduced production lines still present. G1 0.646. G2 0.670.

### The 340 patch-content leavers versus G1, first-year merged pull requests, 12 months

Fix-forward coefficient -0.202 (interval -2.405 to 1.136). q=0.781. n=1189. Cohen's d -0.093. Rate for the coded group 0.034, rate for the reference group 0.054. Holdout sign matches missing.

Revert coefficient -0.437 (interval -9.512 to 1.396). q=0.724. n=1189. Cohen's d -0.014. Rate for the coded group 0.017, rate for the reference group 0.019. Holdout sign matches missing.

Secondary survival, share of introduced production lines still present. false negatives 0.676. G1 0.646.

### Out-group versus in-group merged pull requests from 2016-09-23, 12 months

Fix-forward coefficient -0.417 (interval -0.805 to -0.012). q=0.098. n=5900. Cohen's d -0.048. Rate for the coded group 0.070, rate for the reference group 0.083. Holdout sign matches yes.

Revert coefficient 0.099 (interval -0.312 to 0.491). q=0.708. n=5900. Cohen's d -0.012. Rate for the coded group 0.057, rate for the reference group 0.060. Holdout sign matches no.

Secondary survival, share of introduced production lines still present. out-group 0.740. in-group 0.687.

### G1 versus G2, first-year merged pull requests, 24 months

Fix-forward coefficient 0.040 (interval -0.492 to 0.643). q=0.892. n=1708. Cohen's d 0.106. Rate for the coded group 0.080, rate for the reference group 0.053. Holdout sign matches no.

Revert coefficient -0.074 (interval -0.894 to 1.041). q=0.988. n=1708. Cohen's d -0.014. Rate for the coded group 0.021, rate for the reference group 0.024. Holdout sign matches no.

Secondary survival, share of introduced production lines still present. G1 0.486. G2 0.523.

### The 340 patch-content leavers versus G1, first-year merged pull requests, 24 months

Fix-forward coefficient -0.390 (interval -2.123 to 0.571). q=0.649. n=1189. Cohen's d -0.144. Rate for the coded group 0.042, rate for the reference group 0.080. Holdout sign matches missing.

Revert coefficient -0.340 (interval -9.930 to 1.377). q=0.792. n=1189. Cohen's d -0.033. Rate for the coded group 0.017, rate for the reference group 0.021. Holdout sign matches missing.

Secondary survival, share of introduced production lines still present. false negatives 0.542. G1 0.486.

### Out-group versus in-group merged pull requests from 2016-09-23, 24 months

Fix-forward coefficient -0.452 (interval -0.898 to -0.023). q=0.098. n=5900. Cohen's d -0.061. Rate for the coded group 0.099, rate for the reference group 0.118. Holdout sign matches yes.

Revert coefficient 0.131 (interval -0.297 to 0.528). q=0.687. n=5900. Cohen's d -0.007. Rate for the coded group 0.063, rate for the reference group 0.065. Holdout sign matches no.

Secondary survival, share of introduced production lines still present. out-group 0.603. in-group 0.538.



## Selection

Only merged code is observable. Unmerged out-group patches cannot be scored, so the test bounds the bar. It does not measure rejected quality.

The blinded first-pull-request audit is separate from these durability estimates. The rubric is `findings/AUDIT_RUBRIC.md`. Scores are in `findings/data/audit_scores.csv`, and the later-reviewer minus leaver differences are in `findings/data/audit_results.json`. Correctness, scope, and clarity cover zero. Test coverage is -0.680 (interval -1.307 to -0.087). One coder, so agreement is not measured.

## What this cannot prove

- Only merged code is observable. Unmerged out-group patches cannot be scored, so a lower failure rate among out-group merges bounds the acceptance bar and does not measure the quality of rejected work.
- A line that a later refactor rewrites is gone even when the behavior remains. Neutral churn is separated from fix-forward and revert, and survival stays a secondary description because of that.
- Blame through renames still misses a line that moved to a file the rename detector did not connect.
- The 12-month and 24-month windows are calendar horizons from the merge commit. A defect found later is outside the outcome.


**Generated by:** `scripts/reporting/generate_from_templates.py`
