# Glossary and Context: Bitcoin Core Governance Analysis

**Date**: 2026-09-10  
**Purpose**: Explain Bitcoin Core-specific terminology and concepts for non-experts

---

## Bitcoin Core Basics

### What is Bitcoin Core?

**Bitcoin Core** is the reference implementation of the Bitcoin protocol. It's the software that most Bitcoin nodes run. Changes to Bitcoin Core can affect the entire Bitcoin network.

**Why this matters**: Governance of Bitcoin Core directly impacts Bitcoin itself. Poor governance in Bitcoin Core = potential risks to Bitcoin.

---

## Key Terminology

### ACK (Acknowledgment)

**What it means**: A reviewer's approval signal. In Bitcoin Core, reviewers use "ACK" to indicate they've reviewed and approve code.

**Types of ACK**:
- **ACK**: Simple approval (low quality review)
- **ACK <hash>**: Approval with commit hash (e.g., "ACK abc1234") - indicates reviewer checked specific commit
- **utACK**: "Untested ACK" - approval without testing
- **concept ACK**: Approval of the concept/idea, but not implementation details
- **re-ACK**: Re-approval after changes

**Why it matters**: ACK comments are a major review mechanism in Bitcoin Core, especially before GitHub's formal review feature (introduced Sept 2016). Our analysis counts ACK comments as reviews, weighted by quality.

**In our analysis**: 
- ACK with hash = 0.3 quality score (low quality)
- Detailed review = 1.0 quality score (high quality)
- ACKs after detailed reviews are ignored (completion signals, not separate reviews)
- Cross-platform reviews (IRC, combined mailing lists, Delving, Bitcointalk) use the same quality weighting
- Multiple reviews from same reviewer: We take MAX (not sum) per reviewer

---

### NACK (Negative Acknowledgment)

**What it means**: A reviewer's rejection signal. Indicates the reviewer opposes the change.

**Why it matters**: NACKs can block or delay merges. In Bitcoin Core, maintainer NACKs (NACKs from maintainers) carry more weight than non-maintainer NACKs.

**In our analysis**: We track NACKs to understand conflict patterns and power dynamics.

---

### Maintainer (roster)

**What it means in this dataset**: A GitHub login on the **canonical roster** (`data/maintainers/canonical_maintainers.json`). That is a social/historical label used for maintainer-vs-outsider *author* splits.

**It is not automatically merge keys.** Some roster logins never appear as GitHub `merged_by` in this dump (`roster_without_keys` in `data/maintainers/merge_capability.json`). Do not cite that as “they had keys and chose not to merge.”

**How they get status**: Not publicly documented. GitHub collaborators API is closed. There is no in-tree `MAINTAINERS` file.

**In our analysis**: `author_is_maintainer` / ever-maintainer is the roster identity label. Merge privilege is a separate field.

---

### Merge keys (observed)

**What it means**: The technical ability to land code on `bitcoin/bitcoin` master. In this dump that is **only** logins that appear as GitHub `merged_by`.

**Who has them**: 23 unique `merged_by` logins. 14 of 22 roster logins. Plus historical holders not on the current roster (`jgarzik`, `meshcollider`, and a handful of early one-off mergers).

**Everyone else cannot merge.** A zero as merger is lack of keys, not unused privilege. Reviewer, ACK, commenter, BIP author, Delving poster — none of those grant keys.

**In our analysis**: `person_role` / `has_merge_keys` / `cannot_merge`. See `merge_capability.json`.

---

### Reviewer

**What it means**: Someone who left a GitHub review or an ACK/NACK. Behavioral, not a permission bit.

**Why it matters**: High-volume reviewers are not merge-key holders unless they also appear as `merged_by`. Co-reviewer recurrence is observational, not deputy rights.

---

### Author-success vs merging

**Non-maintainer “merge rate”** is the share of *their authored PRs* that a **key holder** merged. They did not merge. They cannot. 0% self-merge is structural.

**Maintainer self-merge** is a key holder merging their own PR — an exclusive privilege.

---

### Merge Authority

**What it means**: Same as merge keys. Only observed `merged_by` logins have it.

**In our analysis**: Merge authority is:
- Exclusive to key holders (everyone else: cannot merge)
- Concentrated (top 3 ≈ 81% of merges)
- Unaccountable (no formal challenge mechanism)

---

### Self-Merge

**What it means**: When a maintainer merges their own code (rather than having another maintainer merge it).

**Why it matters**: Self-merge bypasses final review by others. It's an exclusive privilege (only maintainers can do it).

**In our analysis**: 
- 25.5% of maintainer-merged PRs are self-merged
- 46.1% of self-merges have zero reviews (12.2% of all maintainer PRs)
- `CONTRIBUTING.md` sets no numeric minimum for when self-merge is appropriate
- Non-maintainers: 0% self-merge (not permitted)

**The problem**: Not the rate (25.5%), but the structure:
- `CONTRIBUTING.md` sets no numeric minimum for when self-merge is appropriate
- Exclusive privilege (only merge-key holders can merge)
- No public challenge procedure in this corpus

---

### Rough Consensus

**What it means**: Bitcoin Core's decision-making principle. No formal voting - decisions are made by "rough consensus" of maintainers.

**Why it matters**: "Rough consensus" is undefined. It means whatever maintainers decide it means. This creates arbitrary authority.

**In our analysis**: Observed review counts still vary from 0 to 14+. Merge stays with people who hold keys. What the written judgment looked like is the next paragraph.

The written rule is `CONTRIBUTING.md` (not `CONTRIBUTORS.md`): merge rests with merge maintainers, who judge contributor consensus and may weigh reviewers by merit. What that looked like is `REVEALED_ROUGH_CONSENSUS.md` — GitHub ACK/NACK plus peer comments and IRC/mail/Delving/Bitcointalk PR **mentions**. Compare before-2016 vs 2016+ on observed discussion, not on zero GitHub Review objects. A mention is not an ACK.

---

### Pull Request (PR)

**What it means**: A proposed code change. Someone writes code, submits it as a PR, and it gets reviewed before (potentially) being merged.

**In our analysis**: We analyzed 25,122 PRs (2009-2025), including:
- 9,793 maintainer merged PRs
- 15,840 total merged PRs
- Review patterns, merge patterns, response times

---

## Metrics Explained

### Gini Coefficient

**What it measures**: Inequality in contributions/reviews.

**Scale**: 0.0 (perfect equality) to 1.0 (perfect inequality)

**Thresholds**:
- < 0.3: Low inequality
- 0.3-0.6: Moderate inequality
- ≥ 0.6: Extreme inequality

**Bitcoin Core values**:
- Authorship Gini: 0.851 historical / 0.834 recent (extreme); merge Gini 0.623 / 0.667
- Review Gini: 0.922 (extreme inequality)

**Why it matters**: High Gini = power concentration. A few people control most contributions/reviews.

**Example**: If 10 people each contribute 10%, Gini = 0.0. If one person contributes 90% and 9 people contribute 1.1% each, Gini ≈ 0.8.

---

### Homophily Coefficient

**What it measures**: Segregation in reviews. Do maintainers review maintainers, or do they review non-maintainers?

**Scale**: 0.0 (perfect integration) to 1.0 (perfect segregation)

**Bitcoin Core values**:
- Historical: 0.495 (moderate segregation)
- Recent: 0.285 (less segregation)

**Why it matters**: High homophily = maintainers only review each other, excluding non-maintainers from the review process.

---

### Zero-Review Merge Rate

**What it measures**: Percentage of merged PRs that had zero meaningful reviews before merge.

**Quality-weighted**: Uses quality-weighted counting:
- ACK <hash> = 0.3 (low quality)
- Detailed review = 1.0 (high quality)
- Threshold: 0.5 for "meaningful review"

**Bitcoin Core values** (quality-weighted, using MAX per reviewer with 0.3/0.5 thresholds):
- Historical (2012-2020): 30.3% (with 0.3 threshold)
- Recent (2021-2025): 3.3% (with 0.5 threshold)

**Note**: Alternative calculations (SUM approach with 0.5 threshold) produce 34.1% historical. See `RESEARCH_METHODOLOGY.md` for details.

**Why it matters**: High zero-review rate = code entering Bitcoin Core without review. This is a governance risk.

**Note**: Our analysis uses quality-weighted counting, not binary counting. This is more accurate but yields different numbers than simple "has review" vs "no review".

---

### Quality-Weighted Review Counting

**What it means**: Not all reviews are equal. We assign quality scores:
- Detailed review (>50 chars): 1.0
- Good review (10-50 chars): 0.8
- Minimal review (1-10 chars): 0.7
- ACK with hash: 0.3
- Simple ACK: 0.2

**Threshold**: 0.5 for "meaningful review"

**Why it matters**: "ACK abc123" is not the same as a detailed technical review. Quality weighting reflects this.

**Timeline awareness**: ACKs that come AFTER detailed reviews from the same reviewer are ignored (completion signals, not reviews).

---

## Historical Context

### GitHub Reviews Timeline

**September 2016**: GitHub introduced formal pull request reviews.

**Before Sept 2016**: Only ACK comments existed. No formal review feature.

**Implication**: PRs before Sept 2016 could only use ACK comments for review. Our analysis uses a lower threshold (0.3) for pre-review era PRs.

---

### Bitcoin Core Evolution

**2009-2011**: Early development, small team
**2012-2016**: Growth period, GitHub becomes primary platform
**2017-2020**: Maturation, formal review processes
**2021-2025**: Recent period, process improvements

**In our analysis**: We compare historical (2012-2020) vs recent (2021-2025) to show:
- Process improvements (zero-review down 88.7%)
- Structural persistence (self-merge 25.5% in the current extract)
- Power concentration (top 10 control increased from 42.7% to 49.8%)

---

## Why These Metrics Matter

### For Bitcoin

**Bitcoin Core governance affects Bitcoin itself**:
- Changes to Bitcoin Core can affect the entire network
- Poor governance = potential risks to Bitcoin
- Centralized control = single points of failure

### For Governance

**Our analysis reveals**:
- Power concentration (top 3 = 81.1% of merges)
- Exclusive privileges (maintainers vs non-maintainers)
- No public challenge procedure in this corpus
- `CONTRIBUTING.md` is the written rule and sets no numeric review minimum

**The problem**: Not the specific numbers, but the **structure**:
- Discretion inside `CONTRIBUTING.md` (weigh reviewers by merit; no numeric minimum)
- Exclusive privilege (some have it, others don't)
- No accountability (no oversight or challenge)
- Concentration (power in few hands)

---

## Common Misunderstandings

### "25.5% isn't that bad"

**Response**: The rate isn't the problem. The problem is:
- `CONTRIBUTING.md` sets no numeric minimum
- Exclusive privilege (only merge-key holders can merge)
- No public challenge procedure in this corpus
- Concentration (top 10 = 49.8% of PRs)

**Even at 1%, the structural problems remain.**

---

### "But processes improved"

**Response**: Yes, processes improved (zero-review down 88.7%). But **structure didn't change**:
- Self-merge rate 25.5% in the current extract
- Power concentration increased (top 10: 42.7% → 49.8%)
- No accountability mechanism added

**Process got efficient. Structure stayed broken.**

---

### "Maintainers do good work"

**Response**: This isn't about maintainer quality. It's about **governance structure**:
- Why do exclusive privileges exist?
- Why does `CONTRIBUTING.md` set no numeric minimum?
- Why is there no public challenge procedure in this corpus?
- Why concentration?

**The question isn't whether maintainers do good work. The question is why this structure exists.**

---

## Reading the Analysis

### Key Documents

1. **`EXECUTIVE_SUMMARY.md`**: Start here, then the later-measurements section
2. **`GOVERNANCE_FRAMES.md`**: How to cut all-time rates
3. **`GLOSSARY_AND_CONTEXT.md`**: This document
4. **`REVEALED_ROUGH_CONSENSUS.md`**: What `CONTRIBUTING.md` judgment looked like
5. **`RESEARCH_METHODOLOGY.md`**: Quality-weighted counting and the older validation suite

### Understanding the Numbers

**All numbers use quality-weighted review counting**:
- ACK = 0.3 (low quality)
- Detailed review = 1.0 (high quality)
- Threshold = 0.5 for "meaningful review"

**Timeline-aware**: ACKs after detailed reviews are ignored (completion signals).

**Historical context**: Lower threshold (0.3) for pre-review era (before Sept 2016).

---

