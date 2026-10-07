# Revealed rough consensus

**Date:** 2026-09-23  
**Status:** v1.3 (GitHub review/comment keywords; not a vote)  
**Machine-readable:** `findings/data/revealed_rough_consensus.json`  
**Script:** `scripts/analysis/revealed_rough_consensus.py`

Revealed rough consensus is the ACK/NACK/review vector on PRs a merge-key holder merged. Bitcoin Core CONTRIBUTING.md — not CONTRIBUTORS.md — says merge rests with project merge maintainers, who judge the general consensus of contributors and may weigh reviewers by common sense and merit; NACKs without rationale may be disregarded. This is not IETF rough consensus, not a vote, and not a legitimacy score. People without merge keys cannot declare merge; 0 as merger is lack of keys. GitHub Review objects are missing before 2016; peer issue comments and IRC/mail/Delving/Bitcointalk PR mentions are joined as observed discussion, not as equivalent GitHub ACKs. A #NNNN mention is not a review. Compare before-2016 vs 2016+ on discussion_observed, not on zero GitHub Review objects. Closed-unmerged is not interchangeable with NACK'd.

The written rule is in Bitcoin Core **`CONTRIBUTING.md`**, not `CONTRIBUTORS.md`: merge rests with project merge maintainers; they judge “the general consensus of contributors”; they may weigh reviewers by “common sense” and “merit”; NACKs without rationale may be disregarded.

This report asks what that judgment **looked like** when a merge-key holder merged, closed, or left a PR open: GitHub review/comment keywords, plus whether the PR number showed up in IRC/mail/Delving/Bitcointalk.

**Cite 2022+ as the current process bar.** Compare **before 2016 vs 2016+** on observed discussion, not on GitHub Review objects. GitHub Pull Request Reviews are effectively absent from this dump before 2016. Compare before_2016 vs from_2016 on discussion_observed (peer comments + informal mentions). Compare from_2016 vs from_2022 on GitHub Review objects. Do not compare pre-2016 zero_reviews to later windows, and do not cite all-time zero-review as the process bar. A mention is not a review.

Related: `MERGE_PATTERN_BREAKDOWN.md` (self-merge × review count), `MAINTAINER_PREMIUM_REPORT.md` (concept ACK as a gap, not a vote), `CONFLICT_RESOLUTION_ANALYSIS.md` (NACK volume), `VOCABULARY_AUDIT.md` (the phrase).

---

## Current process (2022+)

8,615 PRs: 5,611 merged, 2,642 closed unmerged, 362 open.

This is the window where GitHub review objects are routinely present.

| Signal | Merged share | Closed-unmerged share |
|--------|-------------:|----------------------:|
| Zero GitHub reviews | 7.3% | 55.3% |
| ≥1 merge-key-holder ACK | 80.5% | 13.2% |
| Code ACK (`ACK <commit>` or APPROVED) | 97.9% | 17.1% |
| Any NACK stance (unquoted, non-hedge) | 1.9% | 11.4% |
| ACK source none | 1.2% | 69.9% |
| Merged despite a NACK | 1.9% | — |

Closed-unmerged in this window is mostly **silence** (no ACK), not a documented NACK.

---

## Before vs after 2016 (fair split)

The Reviews API cut is 2016, not 2022. All-time zero-review mixes a missing instrument with a working one.

4,956 PRs created before 2016: 3,404 merged, 1,552 closed unmerged, 0 open.

20,166 PRs created 2016+: 13,441 merged, 6,355 closed unmerged, 370 open.

**Comparable across the cut:** peer GitHub comments, informal `#NNNN` / pull-URL mentions, `discussion_observed`, `github_zero_unobserved`. **Not comparable:** zero GitHub Review objects (pre-2016 is the API hole). ACK/NACK keywords on GitHub comments still exist pre-2016; APPROVED review-state does not.

| Signal | Before 2016 merged | 2016+ merged | 2022+ merged |
|--------|-------------------:|-------------:|-------------:|
| Zero GitHub review objects | 99.4% | 22.4% | 7.3% |
| Peer GitHub issue comment | 88.0% | 91.6% | 86.4% |
| Informal mention (any channel) | 29.3% | 92.9% | 84.1% |
| Informal review-ish keyword | 0.4% | 3.4% | 0.3% |
| Any observed discussion | 89.4% | 100.0% | 100.0% |
| Unobserved (no review, no peer comment, no mention) | 10.6% | 0.0% | 0.0% |

Zero GitHub **Review objects** is not “nobody talked about it.” Informal hits are mentions (20,949 PRs in the index), not ACKs.

---

## Since GitHub Reviews (2016+)

20,166 PRs: 13,441 merged, 6,355 closed unmerged, 370 open.

| Signal | Merged share | Closed-unmerged share |
|--------|-------------:|----------------------:|
| Zero GitHub reviews | 22.4% | 55.9% |
| ≥1 merge-key-holder ACK | 82.7% | 20.6% |
| Any NACK stance | 2.1% | 11.8% |
| ACK source none | 3.0% | 63.1% |

---

## All-time (coverage artifact on reviews)

25,122 PRs: 16,845 merged, 7,907 closed unmerged, 370 open.

2011–2015 merged PRs are ~99% zero review *objects* because the Reviews API is not in this dump. That is **not** “no human looked at the patch.” The fair split is **Before vs after 2016** above. Do not cite all-time zero-review as the CONTRIBUTING.md bar.

### What merged

| Signal | Merged n | Merged share | Closed-unmerged share | Open share |
|--------|--------:|-------------:|----------------------:|-----------:|
| Zero GitHub reviews | 6,400 | 38.0% | 64.6% | 18.9% |
| One review | 2,229 | 13.2% | 8.3% | 14.3% |
| 2–3 reviews | 2,498 | 14.8% | 9.1% | 17.0% |
| 4+ reviews | 5,718 | 33.9% | 18.0% | 49.7% |
| Self-merge | 2,572 | 15.3% | 0.0% | — |
| ≥1 merge-key-holder ACK | 11,843 | 70.3% | 18.2% | 29.5% |
| Code ACK (`ACK <commit>` or APPROVED) | 11,003 | 65.3% | 13.7% | 42.2% |
| Concept/Approach ACK | 5,690 | 33.8% | 22.3% | 60.5% |
| utACK | 6,809 | 40.4% | 9.6% | 8.1% |
| Concept ACK only (no code ACK / utACK) | 144 | 0.9% | 12.5% | 28.1% |
| Any NACK stance | 355 | 2.1% | 12.0% | 7.3% |
| NACK with leftover rationale | 348 | 2.1% | 11.3% | 7.3% |
| Bare NACK | 12 | 0.1% | 1.3% | 0.0% |
| Merged despite a NACK | 355 | 2.1% | — | — |

Self-merge share on closed/open is structurally ~0: only key holders merge.

Zero-review here is GitHub **review objects** on **all** merged PRs (any author). `MERGE_PATTERN_BREAKDOWN.md` cites **11.5%** zero-review **self-merges among roster-authored** maintainer-merged PRs, and **25.5%** self-merge on that same roster-authored set. This table’s self-merge share is of every merge (including outsider-authored PRs a key holder merged). Do not collapse the denominators.

### Whose ACK counted (peer reviewers only)

Author comments and bots are excluded. `cannot_merge` ACKs are signals; those people still cannot merge.

| ACK source mix | Merged | Closed unmerged | Open |
|----------------|-------:|----------------:|-----:|
| None | 18.0% | 68.0% | 29.2% |
| Merge-key holders only | 22.7% | 7.9% | 8.4% |
| Cannot-merge only | 7.9% | 9.6% | 36.8% |
| Roster without keys only | 1.3% | 2.0% | 1.4% |
| Mixed roles | 50.2% | 12.5% | 24.3% |

---

## Consensus-sensitive paths vs the rest

`CONTRIBUTING.md` sets a higher bar for consensus-critical code. Path band is `path_risk_band` (consensus → networking → security → other).

consensus_sensitive includes tests/docs/seeds that touch utxo|chainparams|script|validation. It is not a consensus-rule-change set.

| Band | Merged n | Merged zero-review | Merged ≥1 key-holder ACK | Merged any NACK | Closed n | Closed any NACK |
|------|--------:|-------------------:|-------------------------:|----------------:|---------:|----------------:|
| consensus_sensitive | 1,140 | 29.1% | 80.7% | 3.0% | 1,081 | 13.1% |
| networking | 1,504 | 31.1% | 72.6% | 2.5% | 838 | 11.9% |
| security_sensitive | 2,919 | 28.7% | 76.5% | 2.4% | 1,257 | 13.8% |
| other | 11,266 | 42.2% | 67.4% | 1.9% | 4,645 | 11.4% |
| unknown | 16 | 93.8% | 0.0% | 6.2% | 86 | 1.2% |


---

## What this does not show

- Inner judgment (“I thought there was consensus”).
- Informal **ACK language** equivalent to a GitHub review — mentions are joined; review-ish keywords on IRC/mail are rare.
- Weighted “merit” scores CONTRIBUTING.md allows the merger to apply.
- That a closed PR was NACK’d — most closes have no NACK keyword.
- All-time zero GitHub **Review objects** as proof nobody discussed the patch (use before-2016 vs 2016+ `github_zero_unobserved`).

**Generated by:** `scripts/reporting/generate_from_templates.py`
