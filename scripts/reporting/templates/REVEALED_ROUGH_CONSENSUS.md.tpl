# Revealed rough consensus

**Date:** {{generated_date}}  
**Status:** v{{version}} (GitHub review/comment keywords; not a vote)  
**Machine-readable:** `findings/data/revealed_rough_consensus.json`  
**Script:** `scripts/analysis/revealed_rough_consensus.py`

{{pin}}

The written rule is in Bitcoin Core **`CONTRIBUTING.md`**, not `CONTRIBUTORS.md`: merge rests with project merge maintainers; they judge “the general consensus of contributors”; they may weigh reviewers by “common sense” and “merit”; NACKs without rationale may be disregarded.

This report asks what that judgment **looked like** when a merge-key holder merged, closed, or left a PR open: GitHub review/comment keywords, plus whether the PR number showed up in IRC/mail/Delving/Bitcointalk.

**Cite 2022+ as the current process bar.** Compare **before 2016 vs 2016+** on observed discussion, not on GitHub Review objects. {{coverage_reviews}}

Related: `MERGE_PATTERN_BREAKDOWN.md` (self-merge × review count), `MAINTAINER_PREMIUM_REPORT.md` (concept ACK as a gap, not a vote), `CONFLICT_RESOLUTION_ANALYSIS.md` (NACK volume), `VOCABULARY_AUDIT.md` (the phrase).

---

## Current process (2022+)

{{y2022.n|int}} PRs: {{y2022.n_merged|int}} merged, {{y2022.n_closed_unmerged|int}} closed unmerged, {{y2022.n_open|int}} open.

This is the window where GitHub review objects are routinely present.

| Signal | Merged share | Closed-unmerged share |
|--------|-------------:|----------------------:|
| Zero GitHub reviews | {{y2022.merged.rates.zero_reviews|pct}} | {{y2022.closed_unmerged.rates.zero_reviews|pct}} |
| ≥1 merge-key-holder ACK | {{y2022.merged.rates.at_least_one_merge_keys_ack|pct}} | {{y2022.closed_unmerged.rates.at_least_one_merge_keys_ack|pct}} |
| Code ACK (`ACK <commit>` or APPROVED) | {{y2022.merged.rates.has_code_ack|pct}} | {{y2022.closed_unmerged.rates.has_code_ack|pct}} |
| Any NACK stance (unquoted, non-hedge) | {{y2022.merged.rates.has_nack|pct}} | {{y2022.closed_unmerged.rates.has_nack|pct}} |
| ACK source none | {{y2022.merged.rates.ack_none|pct}} | {{y2022.closed_unmerged.rates.ack_none|pct}} |
| Merged despite a NACK | {{y2022.merged.rates.merged_despite_nack|pct}} | — |

Closed-unmerged in this window is mostly **silence** (no ACK), not a documented NACK.

---

## Before vs after 2016 (fair split)

The Reviews API cut is 2016, not 2022. All-time zero-review mixes a missing instrument with a working one.

{{pre2016.n|int}} PRs created before 2016: {{pre2016.n_merged|int}} merged, {{pre2016.n_closed_unmerged|int}} closed unmerged, {{pre2016.n_open|int}} open.

{{y2016.n|int}} PRs created 2016+: {{y2016.n_merged|int}} merged, {{y2016.n_closed_unmerged|int}} closed unmerged, {{y2016.n_open|int}} open.

**Comparable across the cut:** peer GitHub comments, informal `#NNNN` / pull-URL mentions, `discussion_observed`, `github_zero_unobserved`. **Not comparable:** zero GitHub Review objects (pre-2016 is the API hole). ACK/NACK keywords on GitHub comments still exist pre-2016; APPROVED review-state does not.

| Signal | Before 2016 merged | 2016+ merged | 2022+ merged |
|--------|-------------------:|-------------:|-------------:|
| Zero GitHub review objects | {{pre2016.merged.rates.zero_reviews|pct}} | {{y2016.merged.rates.zero_reviews|pct}} | {{y2022.merged.rates.zero_reviews|pct}} |
| Peer GitHub issue comment | {{pre2016.merged.rates.has_peer_github_comment|pct}} | {{y2016.merged.rates.has_peer_github_comment|pct}} | {{y2022.merged.rates.has_peer_github_comment|pct}} |
| Informal mention (any channel) | {{pre2016.merged.rates.informal_mention|pct}} | {{y2016.merged.rates.informal_mention|pct}} | {{y2022.merged.rates.informal_mention|pct}} |
| Informal review-ish keyword | {{pre2016.merged.rates.informal_reviewish|pct}} | {{y2016.merged.rates.informal_reviewish|pct}} | {{y2022.merged.rates.informal_reviewish|pct}} |
| Any observed discussion | {{pre2016.merged.rates.discussion_observed|pct}} | {{y2016.merged.rates.discussion_observed|pct}} | {{y2022.merged.rates.discussion_observed|pct}} |
| Unobserved (no review, no peer comment, no mention) | {{pre2016.merged.rates.github_zero_unobserved|pct}} | {{y2016.merged.rates.github_zero_unobserved|pct}} | {{y2022.merged.rates.github_zero_unobserved|pct}} |

Zero GitHub **Review objects** is not “nobody talked about it.” Informal hits are mentions ({{informal_index.prs_mentioned|int}} PRs in the index), not ACKs.

---

## Since GitHub Reviews (2016+)

{{y2016.n|int}} PRs: {{y2016.n_merged|int}} merged, {{y2016.n_closed_unmerged|int}} closed unmerged, {{y2016.n_open|int}} open.

| Signal | Merged share | Closed-unmerged share |
|--------|-------------:|----------------------:|
| Zero GitHub reviews | {{y2016.merged.rates.zero_reviews|pct}} | {{y2016.closed_unmerged.rates.zero_reviews|pct}} |
| ≥1 merge-key-holder ACK | {{y2016.merged.rates.at_least_one_merge_keys_ack|pct}} | {{y2016.closed_unmerged.rates.at_least_one_merge_keys_ack|pct}} |
| Any NACK stance | {{y2016.merged.rates.has_nack|pct}} | {{y2016.closed_unmerged.rates.has_nack|pct}} |
| ACK source none | {{y2016.merged.rates.ack_none|pct}} | {{y2016.closed_unmerged.rates.ack_none|pct}} |

---

## All-time (coverage artifact on reviews)

{{all.n|int}} PRs: {{all.n_merged|int}} merged, {{all.n_closed_unmerged|int}} closed unmerged, {{all.n_open|int}} open.

2011–2015 merged PRs are ~99% zero review *objects* because the Reviews API is not in this dump. That is **not** “no human looked at the patch.” The fair split is **Before vs after 2016** above. Do not cite all-time zero-review as the CONTRIBUTING.md bar.

### What merged

| Signal | Merged n | Merged share | Closed-unmerged share | Open share |
|--------|--------:|-------------:|----------------------:|-----------:|
| Zero GitHub reviews | {{all.merged.review_buckets.zero|int}} | {{all.merged.rates.zero_reviews|pct}} | {{all.closed_unmerged.rates.zero_reviews|pct}} | {{all.open.rates.zero_reviews|pct}} |
| One review | {{all.merged.review_buckets.one|int}} | {{all.merged.rates.one_review|pct}} | {{all.closed_unmerged.rates.one_review|pct}} | {{all.open.rates.one_review|pct}} |
| 2–3 reviews | {{all.merged.review_buckets.two_three|int}} | {{all.merged.rates.two_three_reviews|pct}} | {{all.closed_unmerged.rates.two_three_reviews|pct}} | {{all.open.rates.two_three_reviews|pct}} |
| 4+ reviews | {{all.merged.review_buckets.four_plus|int}} | {{all.merged.rates.four_plus_reviews|pct}} | {{all.closed_unmerged.rates.four_plus_reviews|pct}} | {{all.open.rates.four_plus_reviews|pct}} |
| Self-merge | {{all.merged.self_merge|int}} | {{all.merged.rates.self_merge|pct}} | {{all.closed_unmerged.rates.self_merge|pct}} | — |
| ≥1 merge-key-holder ACK | {{all.merged.at_least_one_merge_keys_ack|int}} | {{all.merged.rates.at_least_one_merge_keys_ack|pct}} | {{all.closed_unmerged.rates.at_least_one_merge_keys_ack|pct}} | {{all.open.rates.at_least_one_merge_keys_ack|pct}} |
| Code ACK (`ACK <commit>` or APPROVED) | {{all.merged.has_code_ack|int}} | {{all.merged.rates.has_code_ack|pct}} | {{all.closed_unmerged.rates.has_code_ack|pct}} | {{all.open.rates.has_code_ack|pct}} |
| Concept/Approach ACK | {{all.merged.has_concept_ack|int}} | {{all.merged.rates.has_concept_ack|pct}} | {{all.closed_unmerged.rates.has_concept_ack|pct}} | {{all.open.rates.has_concept_ack|pct}} |
| utACK | {{all.merged.has_utack|int}} | {{all.merged.rates.has_utack|pct}} | {{all.closed_unmerged.rates.has_utack|pct}} | {{all.open.rates.has_utack|pct}} |
| Concept ACK only (no code ACK / utACK) | {{all.merged.concept_only|int}} | {{all.merged.rates.concept_only|pct}} | {{all.closed_unmerged.rates.concept_only|pct}} | {{all.open.rates.concept_only|pct}} |
| Any NACK stance | {{all.merged.has_nack|int}} | {{all.merged.rates.has_nack|pct}} | {{all.closed_unmerged.rates.has_nack|pct}} | {{all.open.rates.has_nack|pct}} |
| NACK with leftover rationale | {{all.merged.has_nack_rationale|int}} | {{all.merged.rates.has_nack_rationale|pct}} | {{all.closed_unmerged.rates.has_nack_rationale|pct}} | {{all.open.rates.has_nack_rationale|pct}} |
| Bare NACK | {{all.merged.has_nack_bare|int}} | {{all.merged.rates.has_nack_bare|pct}} | {{all.closed_unmerged.rates.has_nack_bare|pct}} | {{all.open.rates.has_nack_bare|pct}} |
| Merged despite a NACK | {{all.merged.merged_despite_nack|int}} | {{all.merged.rates.merged_despite_nack|pct}} | — | — |

Self-merge share on closed/open is structurally ~0: only key holders merge.

Zero-review here is GitHub **review objects** on **all** merged PRs (any author). `MERGE_PATTERN_BREAKDOWN.md` cites **11.5%** zero-review **self-merges among roster-authored** maintainer-merged PRs, and **25.5%** self-merge on that same roster-authored set. This table’s self-merge share is of every merge (including outsider-authored PRs a key holder merged). Do not collapse the denominators.

### Whose ACK counted (peer reviewers only)

Author comments and bots are excluded. `cannot_merge` ACKs are signals; those people still cannot merge.

| ACK source mix | Merged | Closed unmerged | Open |
|----------------|-------:|----------------:|-----:|
| None | {{all.merged.rates.ack_none|pct}} | {{all.closed_unmerged.rates.ack_none|pct}} | {{all.open.rates.ack_none|pct}} |
| Merge-key holders only | {{all.merged.rates.ack_merge_keys_only|pct}} | {{all.closed_unmerged.rates.ack_merge_keys_only|pct}} | {{all.open.rates.ack_merge_keys_only|pct}} |
| Cannot-merge only | {{all.merged.rates.ack_cannot_merge_only|pct}} | {{all.closed_unmerged.rates.ack_cannot_merge_only|pct}} | {{all.open.rates.ack_cannot_merge_only|pct}} |
| Roster without keys only | {{all.merged.rates.ack_roster_without_keys_only|pct}} | {{all.closed_unmerged.rates.ack_roster_without_keys_only|pct}} | {{all.open.rates.ack_roster_without_keys_only|pct}} |
| Mixed roles | {{all.merged.rates.ack_mixed|pct}} | {{all.closed_unmerged.rates.ack_mixed|pct}} | {{all.open.rates.ack_mixed|pct}} |

---

## Consensus-sensitive paths vs the rest

`CONTRIBUTING.md` sets a higher bar for consensus-critical code. Path band is `path_risk_band` (consensus → networking → security → other).

{{coverage_path}}

| Band | Merged n | Merged zero-review | Merged ≥1 key-holder ACK | Merged any NACK | Closed n | Closed any NACK |
|------|--------:|-------------------:|-------------------------:|----------------:|---------:|----------------:|
{% for item in path_rows %}
| {{item.band}} | {{item.merged_n|int}} | {{item.merged_zero|pct}} | {{item.merged_keys_ack|pct}} | {{item.merged_nack|pct}} | {{item.closed_n|int}} | {{item.closed_nack|pct}} |
{% endfor %}

---

## What this does not show

- Inner judgment (“I thought there was consensus”).
- Informal **ACK language** equivalent to a GitHub review — mentions are joined; review-ish keywords on IRC/mail are rare.
- Weighted “merit” scores CONTRIBUTING.md allows the merger to apply.
- That a closed PR was NACK’d — most closes have no NACK keyword.
- All-time zero GitHub **Review objects** as proof nobody discussed the patch (use before-2016 vs 2016+ `github_zero_unobserved`).

**Generated by:** `scripts/reporting/generate_from_templates.py`
