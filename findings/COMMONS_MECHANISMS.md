# Commons mechanisms and the shared comparison

**Date:** 2026-10-07  
**Machine-readable:** `findings/data/commons_dynamics_analysis.json`  
**Problem:** Which repeatable patterns in reviewer attention show up under year, size, and tenure controls, and what can a cross-repository rank actually say?

Part A effects are behavioral signatures, not psychological states. Part B scores institutional conditions. Part C is health and does not reuse A or B indicators. Year fixed effects are included because pass 2 found time-structured gaps, not because the bar rose for everyone.

The resource is reviewer attention and merge authority. The code is not the resource. Health indicators are a different set from the design-principle indicators.

## Confirmed effects

A row is here when the id starts with E, q is below 0.05, the 2024–2026 sign matches, the effect size is not negligible, and a standardized coefficient is at least 0.2 in absolute value.

### E2_reciprocity_excess

Estimate 0.024 (interval 0.023 to 0.025). q=0.005. Holdout 0.024. n=113714.

Attention events are one per reviewer per PR per day. The null shuffles reviewer labels within calendar year,  500 times. Index is the share of events matched by the reverse pair within 30 days.

### E3_log_hours_to_next_same_direction_top5_minus_other

Estimate -0.471 (interval -0.555 to -0.383). q=0.003. Holdout -0.524. n=9562.

Negative means the next same-direction review arrives sooner after a top-5 merger speaks first. Cohen's d uses the same sign.

### E5_log_participants_on_log_days

Estimate 0.863 (interval 0.841 to 0.884). q=0.003. Holdout 0.912. n=20067.

Decided PRs only. Open PRs are right-censored and excluded. Positive means more participants, slower decisions. This is not identified as diffusion of responsibility: a harder PR can draw both more people and a longer wait.

### E7_first_tone_on_merge_given_later_tone

Estimate 0.310 (interval 0.265 to 0.355). q=0.003. Holdout 0.482. n=16664.

Decided PRs with a first peer tone and at least one later peer tone. Logistic. Later mean tone is an added control on top of the shared set.

### E9_listed_on_log_days_to_merge

Estimate 0.251 (interval 0.224 to 0.278). q=0.003. Holdout 0.079. n=9256.

Among merged PRs in the meeting era. Negative means listed PRs merge faster.

### E12_ingroup_on_no_peer_response

Estimate -0.493 (interval -0.596 to -0.396). q=0.003. Holdout -0.738. n=20087.

No peer response means no review object, issue comment, or line comment by someone other than the author. In-group is the trailing-24-month top 20 by review-object volume, unidentified when fewer than 20 reviewers exist. Unidentified is a control, not coded as out-group.



## Shared-indicator rank

The rank uses entry-wait variation, scope language, recurring dispute topics, open backlog, 24-month retention, merge concentration, bus factor, and median time to decision. Review labor, monitoring, and exits are in the Bitcoin Core profile and are not in this rank. Repositories with fewer than 7 years are omitted here.

- bitcoin-core/bitcoin-maintainer-tools: shared health 0.72, shared principles 0.96, 11 years. Full-profile health 0.72, full-profile principles 0.97.
- rust-bitcoin/rust-miniscript: shared health 0.70, shared principles 0.91, 9 years. Full-profile health 0.70, full-profile principles 0.94.
- ACINQ/eclair: shared health 0.65, shared principles 0.94, 11 years. Full-profile health 0.65, full-profile principles 0.94.
- bitcoindevkit/bdk: shared health 0.65, shared principles 0.85, 7 years. Full-profile health 0.65, full-profile principles 0.85.
- lightningnetwork/lnd: shared health 0.65, shared principles 0.78, 11 years. Full-profile health 0.65, full-profile principles 0.79.
- sparrowwallet/sparrow: shared health 0.64, shared principles 0.96, 7 years. Full-profile health 0.64, full-profile principles 0.97.
- rust-bitcoin/rust-bitcoin: shared health 0.64, shared principles 0.87, 13 years. Full-profile health 0.64, full-profile principles 0.88.
- ElementsProject/lightning: shared health 0.64, shared principles 0.81, 12 years. Full-profile health 0.64, full-profile principles 0.83.
- lightningdevkit/rust-lightning: shared health 0.62, shared principles 0.83, 9 years. Full-profile health 0.62, full-profile principles 0.84.
- SeedSigner/seedsigner: shared health 0.62, shared principles 0.85, 7 years. Full-profile health 0.62, full-profile principles 0.86.
- lightning/bolts: shared health 0.61, shared principles 0.91, 11 years. Full-profile health 0.61, full-profile principles 0.92.
- bitcoin-core/HWI: shared health 0.60, shared principles 0.92, 9 years. Full-profile health 0.60, full-profile principles 0.93.
- bitcoin-core/secp256k1: shared health 0.59, shared principles 0.92, 13 years. Full-profile health 0.59, full-profile principles 0.94.
- bitcoin/bitcoin: shared health 0.58, shared principles 0.49, 17 years. Full-profile health 0.48, full-profile principles 0.52.


Bitcoin Core on the shared subset is last among ranked repositories. Its full profile is health 0.48 and principles 0.52. That is a partial comparison, not a judgment that a tools repository is better governed.

## Lagged principle scores

On bitcoin/bitcoin, the conflict-resolution score (P6) in year t has Spearman r=0.714 with the health index in t+1 (n=13, interval 0.271 to 0.944, q=0.016). That is the only positive lag that clears the passes 1–5 threshold. It is LOW POWER. The nested-decision score (P8) runs the other way: r=-0.717, q=0.016. P5 and P7 have no scored year. 2024–2026 does not contain enough pairs to confirm the lags.

## The six effects on other repositories

13 comparison repositories have at least seven years of history. Their pull-request dumps store author, title, body, timestamps, merged state, and comments_count. Review objects, comment authors, file paths, and meeting lists are absent, so E2, E3, E5, E7, E9, and E12 are DATA UNAVAILABLE on every one of them. The Spearman correlation of effect size with health is DATA UNAVAILABLE. Whether those effects are specific to poorly governed repositories or ambient to open source development is not identified. The Bitcoin Core row in the effect list above is the reference.

The principle series and the repository table are in `GAP_CLOSURE.md`.

## What this cannot prove

- Psychological states are not observable. The effects are behavioral signatures only.
- Ostrom's principles are correlates of durable commons, not proven causes of these outcomes.
- A series of about 16 years cannot establish causation. Lagged correlations are low power.
- P5, P7, E4b, and E11 rely on thin or model-dependent data. P5 and E11 are low observability because deleted and off-platform sanctions are missing. P7 has no person-to-funder ledger, and its sentiment is a keyword model. E4b depends on the function-word lists.
- Results that fail the 2024-2026 holdout or the Benjamini-Hochberg correction are exploratory.
- A commons can score poorly and still survive for a time on funding or reputation before the health metrics show it.


**Generated by:** `scripts/reporting/generate_from_templates.py`
