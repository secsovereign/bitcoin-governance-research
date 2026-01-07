# Glossary and Context: Bitcoin Core Governance Analysis

**Date**: 2026-01-07  
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
- Cross-platform reviews (IRC, email) are included with same quality weighting
- Multiple reviews from same reviewer: We take MAX (not sum) per reviewer

---

### NACK (Negative Acknowledgment)

**What it means**: A reviewer's rejection signal. Indicates the reviewer opposes the change.

**Why it matters**: NACKs can block or delay merges. In Bitcoin Core, maintainer NACKs (NACKs from maintainers) carry more weight than non-maintainer NACKs.

**In our analysis**: We track NACKs to understand conflict patterns and power dynamics.

---

### Maintainer

**What it means**: A person with **merge authority** - the ability to merge code into Bitcoin Core's main branch.

**How many**: Currently ~15-20 people have merge authority (varies over time).

**How they get status**: Not publicly documented. Appears to be by invitation/consensus of existing maintainers.

**Why it matters**: Maintainers have exclusive privileges:
- Can merge their own code (self-merge)
- Can merge others' code
- Reviews from maintainers carry more weight
- No formal accountability mechanism visible

**In our analysis**: We compare maintainer vs non-maintainer patterns to reveal power asymmetry.

---

### Merge Authority

**What it means**: The technical ability to merge code into Bitcoin Core's main branch. Only maintainers have this.

**Why it matters**: Merge authority = final say over what code enters Bitcoin Core. This is concentrated in ~15-20 people.

**In our analysis**: We show that merge authority is:
- Exclusive to maintainers (non-maintainers: 0%)
- Concentrated (top 3 = 81% of merges)
- Unaccountable (no formal challenge mechanism)

---

### Self-Merge

**What it means**: When a maintainer merges their own code (rather than having another maintainer merge it).

**Why it matters**: Self-merge bypasses final review by others. It's an exclusive privilege (only maintainers can do it).

**In our analysis**: 
- 26.5% of maintainer PRs are self-merged
- 46.1% of self-merges have zero reviews (12.2% of all maintainer PRs)
- No formal rules determine when self-merge is appropriate
- Non-maintainers: 0% self-merge (not permitted)

**The problem**: Not the rate (26.5%), but the structure:
- Arbitrary authority (no formal rules)
- Exclusive privilege (only maintainers)
- No accountability (no challenge mechanism)

---

### Rough Consensus

**What it means**: Bitcoin Core's decision-making principle. No formal voting - decisions are made by "rough consensus" of maintainers.

**Why it matters**: "Rough consensus" is undefined. It means whatever maintainers decide it means. This creates arbitrary authority.

**In our analysis**: We show that "rough consensus" results in:
- Discretionary standards (review requirements vary 0-14+)
- No formal rules
- No accountability
- Power concentration

---

### Pull Request (PR)

**What it means**: A proposed code change. Someone writes code, submits it as a PR, and it gets reviewed before (potentially) being merged.

**In our analysis**: We analyzed 23,478 PRs (2009-2025), including:
- 9,235 maintainer merged PRs
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
- Contribution Gini: 0.851 (extreme inequality)
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
- Historical (2012-2020): 30.2% (with 0.3 threshold)
- Recent (2021-2025): 3.4% (with 0.5 threshold)

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
- Structural persistence (self-merge stable at 26.5%)
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
- No accountability (no formal challenge mechanism)
- Arbitrary authority (no formal rules)

**The problem**: Not the specific numbers, but the **structure**:
- Arbitrary authority (discretionary, not rule-based)
- Exclusive privilege (some have it, others don't)
- No accountability (no oversight or challenge)
- Concentration (power in few hands)

---

## Common Misunderstandings

### "26.5% isn't that bad"

**Response**: The rate isn't the problem. The problem is:
- Arbitrary authority (no formal rules)
- Exclusive privilege (only maintainers)
- No accountability (no challenge mechanism)
- Concentration (top 10 = 49.8% of PRs)

**Even at 1%, the structural problems remain.**

---

### "But processes improved"

**Response**: Yes, processes improved (zero-review down 88.7%). But **structure didn't change**:
- Self-merge rate stable (26.5%)
- Power concentration increased (top 10: 42.7% → 49.8%)
- No accountability mechanism added

**Process got efficient. Structure stayed broken.**

---

### "Maintainers do good work"

**Response**: This isn't about maintainer quality. It's about **governance structure**:
- Why do exclusive privileges exist?
- Why no formal rules?
- Why no accountability?
- Why concentration?

**The question isn't whether maintainers do good work. The question is why this structure exists.**

---

## Reading the Analysis

### Key Documents

1. **`EXECUTIVE_SUMMARY.md`**: Start here - 37-line overview
2. **`GLOSSARY_AND_CONTEXT.md`**: This document - terminology explained
3. **`GINI_COEFFICIENT_EXPLANATION.md`**: Gini coefficient explained
4. **`REVIEW_QUALITY_WEIGHTING.md`**: Quality weighting methodology
5. **`COMPLETE_ANALYSIS_WITH_CORRECTED_DATA.md`**: Full metrics

### Understanding the Numbers

**All numbers use quality-weighted review counting**:
- ACK = 0.3 (low quality)
- Detailed review = 1.0 (high quality)
- Threshold = 0.5 for "meaningful review"

**Timeline-aware**: ACKs after detailed reviews are ignored (completion signals).

**Historical context**: Lower threshold (0.3) for pre-review era (before Sept 2016).

---

