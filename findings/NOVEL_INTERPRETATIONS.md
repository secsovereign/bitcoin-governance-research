# Novel Interpretations: New Ways of Looking at Bitcoin Core Governance

**Analysis Date**: 2026-01-07  
**Last Updated**: 2026-01-07 (cross-platform integration, PR importance analysis)  
**Purpose**: Provide novel aggregations and interpretations that reveal hidden patterns  
**Methodology**: Quality-weighted review counting (GitHub, ACK, IRC, email), cross-platform integrated, PR importance classification

---

## 1. Behavioral Clusters: Four Types of Maintainers ⭐⭐⭐

Maintainers cluster into distinct behavioral patterns:

### High Self-Merge + High Authority (Power Users)
**Pattern**: Self-merge frequently AND merge many others' PRs
- **laanwj**: 77.1% self-merge, merges 20 different authors
- **fanquake**: 51.2% self-merge, merges 18 different authors
- **maflcko**: 37.4% self-merge, merges 19 different authors

**Interpretation**: These are the "power users" - they have both self-merge privilege AND merge authority over others. They control both their own work and others' work.

### High Self-Merge + Low Authority (Solo Operators)
**Pattern**: Self-merge frequently but merge few others
- **gavinandresen**: 68.3% self-merge, merges only 10 authors

**Interpretation**: These maintainers primarily work on their own code and rarely merge others. They have self-merge privilege but limited merge authority.

### Low Self-Merge + High Authority (Gatekeepers)
**Pattern**: Rarely self-merge but merge many others
- **sipa**: 19.0% self-merge, merges 18 authors
- **gmaxwell**: 7.0% self-merge, merges 12 authors
- **achow101**: 3.3% self-merge, merges 14 authors
- **ryanofsky**: 0.4% self-merge, merges 11 authors

**Interpretation**: These are "gatekeepers" - they rarely self-merge (suggesting they follow stricter standards for their own work) but have significant merge authority over others. They may be more selective about their own PRs but actively merge others.

### Low Self-Merge + Low Authority (Contributors)
**Pattern**: Rarely self-merge and merge few others
- Multiple maintainers with 0% self-merge rates

**Interpretation**: These maintainers have limited privilege in both dimensions - they neither self-merge nor merge many others.

**Key Insight**: The distribution reveals a **power hierarchy** where some maintainers have both self-merge privilege AND merge authority, while others have neither.

---

## 2. Review Reciprocity: 88.7% Reciprocal ⭐⭐

**Finding**: 88.7% of maintainer review relationships are reciprocal (they review each other).

**Top Reciprocal Pairs:**
1. **hebasto ↔ fanquake**: 881 and 555 reviews (mutual)
2. **hebasto ↔ maflcko**: 485 and 725 reviews (mutual)
3. **maflcko ↔ fanquake**: 374 and 382 reviews (mutual)
4. **ryanofsky ↔ maflcko**: 412 and 288 reviews (mutual)
5. **maflcko ↔ jonatack**: 279 and 239 reviews (mutual)

**Interpretation**: 
- High reciprocity suggests **mutual respect** and **collaborative norms**
- However, this could also indicate **cliques** or **mutual back-scratching**
- The fact that 11.3% are one-way suggests some **asymmetric relationships** (power dynamics)

**Key Insight**: The high reciprocity rate (88.7%) suggests that review relationships are largely mutual, but this doesn't necessarily mean equal power - it could reflect mutual accommodation within a closed group.

---

## 3. Power Hierarchy: Who Merges Whom ⭐⭐⭐

**Top Mergers of Other Maintainers:**
1. **laanwj**: 2,570 maintainer PRs merged (most frequently merges maflcko: 490 times)
2. **fanquake**: 1,737 maintainer PRs merged (most frequently merges maflcko: 701 times)
3. **maflcko**: 1,083 maintainer PRs merged (most frequently merges fanquake: 202 times)

**Strong Subordinate Relationships:**
- **fanquake → maflcko**: 701 merges (fanquake merges maflcko's PRs)
- **fanquake → hebasto**: 494 merges
- **laanwj → maflcko**: 490 merges
- **laanwj → sipa**: 309 merges
- **laanwj → fanquake**: 303 merges

**Interpretation**: 
- **laanwj** and **fanquake** are at the top of the hierarchy - they merge the most maintainer PRs
- **maflcko** is frequently merged by both laanwj and fanquake (701 + 490 = 1,191 times), suggesting they are a **subordinate** in the hierarchy despite being a high-volume contributor
- The hierarchy is **asymmetric**: laanwj merges fanquake 303 times, but fanquake merges laanwj much less frequently

**Key Insight**: The merge relationships reveal a **clear power hierarchy** where some maintainers consistently merge others' work, creating **subordinate relationships**. This is not just about volume - it's about **who has authority over whom**.

---

## 4. Escalation Patterns: What Triggers More Reviews? ⭐⭐

**Low Review PRs (0-1 reviews):**
- Maintainer rate: 47.3%
- NACK rate: 0.3%

**High Review PRs (5+ reviews):**
- Maintainer rate: 48.3%
- NACK rate: 1.9%

**Interpretation**: 
- **Maintainer status doesn't predict review count** - both groups have similar maintainer rates (~47-48%)
- **NACK rate is 6x higher** in high-review PRs (1.9% vs 0.3%), suggesting **controversy triggers escalation**
- The fact that maintainer rate is similar suggests that **controversy, not author status**, drives review escalation

**Key Insight**: Review escalation is driven by **controversy** (NACKs), not by author status. Maintainers don't automatically get fewer reviews - controversial PRs get more reviews regardless of who wrote them.

---

## 5. Temporal Cohorts: How Behavior Changed Over Time ⭐⭐⭐

**Early 2010s (2010-2013):**
- Members: gavinandresen, thebluematt, sipa, laanwj, gmaxwell
- Self-merge rate: **36.9%**
- Avg reviews: **2.9**

**Mid 2010s (2014-2016):**
- Members: maflcko, promag, instagibbs, achow101, jnewbery
- Self-merge rate: **23.6%**
- Avg reviews: **6.3**

**Late 2010s (2017-2019):**
- Members: sjors, hebasto, jonatack
- Self-merge rate: **1.3%**
- Avg reviews: **6.8**

**2020s (2020+):**
- Members: glozow
- Self-merge rate: **8.4%**
- Avg reviews: **19.7**

**Interpretation**: 
- **Self-merge rate declined dramatically**: 36.9% → 23.6% → 1.3% → 8.4%
- **Review count increased dramatically**: 2.9 → 6.3 → 6.8 → 19.7
- **Late 2010s cohort** has the lowest self-merge rate (1.3%) and higher reviews (6.8)
- **2020s cohort** has very high reviews (19.7) but slightly higher self-merge (8.4%)

**Key Insight**: There's a **generational shift** - newer maintainers (late 2010s, 2020s) have much lower self-merge rates and higher review counts. This suggests **process improvements** but also reveals that **early maintainers** (laanwj, gavinandresen) still have high self-merge rates from the old era.

---

## 6. Decision Patterns: What Distinguishes Merged vs Rejected? ⭐⭐

### Maintainer PRs

| Metric | Merged | Rejected | Difference |
|--------|--------|----------|------------|
| **Avg reviews** | 5.0 | 3.6 | **+1.4 reviews** |
| **Approval rate** | 45.1% | 12.5% | **+32.6 pp** |
| **NACK rate** | (not shown) | (not shown) | - |

**Interpretation**: 
- Merged maintainer PRs get **more reviews** (5.0 vs 3.6) and have **much higher approval rates** (45.1% vs 12.5%)
- This suggests that **approval matters** - merged PRs have approvals, rejected ones don't

### Non-Maintainer PRs

| Metric | Merged | Rejected | Difference |
|--------|--------|----------|------------|
| **Avg reviews** | 6.6 | 2.5 | **+4.1 reviews** |
| **Approval rate** | 40.7% | 7.7% | **+33.0 pp** |
| **NACK rate** | (not shown) | (not shown) | - |

**Interpretation**: 
- Merged non-maintainer PRs get **even more reviews** (6.6 vs 2.5) and have **much higher approval rates** (40.7% vs 7.7%)
- The gap is **larger** for non-maintainers (4.1 reviews vs 1.4 for maintainers)

**Key Insight**: 
- **Approval rate is the strongest predictor** - merged PRs have 33+ percentage point higher approval rates
- **Review count matters more for non-maintainers** - they need 4.1 more reviews on average to get merged
- **Maintainers need fewer reviews** (1.4 difference) but still need approvals

---

## Key Takeaways

### 1. Power Hierarchy is Real
- **laanwj** and **fanquake** are at the top (merge the most maintainer PRs)
- **maflcko** is frequently merged by both (subordinate relationship)
- The hierarchy is **asymmetric** - not all relationships are reciprocal

### 2. Behavioral Clusters Reveal Privilege Levels
- **High self-merge + High authority**: Power users (laanwj, fanquake, maflcko)
- **Low self-merge + High authority**: Gatekeepers (sipa, gmaxwell, achow101)
- **High self-merge + Low authority**: Solo operators (gavinandresen)
- **Low self-merge + Low authority**: Contributors (many others)

### 3. Generational Shift
- **Early 2010s**: 36.9% self-merge, 2.9 reviews
- **Late 2010s**: 1.3% self-merge, 6.8 reviews
- **2020s**: 8.4% self-merge, 19.7 reviews
- Newer maintainers have much lower self-merge rates

### 4. Review Reciprocity is High (88.7%)
- Most maintainer review relationships are reciprocal
- Could indicate mutual respect OR mutual accommodation
- 11.3% one-way relationships suggest power dynamics

### 5. Escalation Driven by Controversy
- High-review PRs have 6x higher NACK rates
- Maintainer status doesn't predict review count
- Controversy triggers escalation, not author status

### 6. Approval Rate is Key Predictor
- Merged PRs have 33+ percentage point higher approval rates
- Review count matters more for non-maintainers (4.1 vs 1.4 difference)
- Maintainers still need approvals, but fewer reviews

---

## Novel Insights

1. **Power is Multi-Dimensional**: Self-merge privilege and merge authority are separate dimensions. Some maintainers have both (power users), some have neither (contributors).

2. **Hierarchy is Asymmetric**: Merge relationships reveal clear subordinate relationships (fanquake → maflcko: 701 times), not just volume differences.

3. **Generational Divide**: Early maintainers (laanwj, gavinandresen) still have high self-merge rates from the old era, while newer maintainers have much lower rates.

4. **Reciprocity Doesn't Mean Equality**: 88.7% reciprocal reviews suggests mutual accommodation, but merge relationships reveal clear hierarchy.

5. **Controversy Drives Escalation**: Review count is driven by controversy (NACKs), not author status. Maintainers don't automatically get fewer reviews.

6. **Approval is the Gate**: Approval rate (33+ pp difference) is the strongest predictor of merge success, more than review count.

---

## Files

- **Analysis script**: `scripts/analysis/novel_interpretations.py`
- **Results**: `data/novel_interpretations.json`
- **This document**: `NOVEL_INTERPRETATIONS.md`
