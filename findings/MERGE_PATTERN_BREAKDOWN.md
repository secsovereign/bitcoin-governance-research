# Detailed Merge Pattern Breakdown

**Analysis Date**: 2026-01-07  
**Last Updated**: 2026-01-07 (cross-platform integration, PR importance analysis, consistency fixes)  
**Data Source**: 9,235 maintainer merged PRs with merged_by data (99.9% coverage)  
**Methodology**: Quality-weighted review counting (GitHub, ACK, IRC, email), cross-platform integrated, PR importance classification, timeline-aware ACK handling, MAX per reviewer

**Methodological Note**: Analysis based on publicly available GitHub data. "Friend patterns" and "high-volume merger patterns" are descriptive terms for observable merge relationships. These patterns may reflect normal collaboration, informal coordination, or governance structures. This analysis does not account for private coordination or internal decision-making processes not visible in public data.

---

## 1. Self-Merge Rate Breakdown

### Overall Rate

- **Total maintainer merged PRs**: 9,235
- **Self-merged**: 2,446 (26.5%)
- **Other-merged**: 6,789 (73.5%)

### Self-Merge by Review Count

| Review Count | Count | % of Self-Merges | % of All Maintainer PRs |
|-------------|-------|------------------|------------------------|
| **Zero reviews** | 1,127 | 46.1% | 12.2% |
| **One review** | 409 | 16.7% | 4.4% |
| **Two+ reviews** | 910 | 37.2% | 9.9% |

**Key Finding**: Nearly half (46.1%) of self-merged PRs have **zero reviews** before merge. This represents 12.2% of all maintainer PRs merging without any review.

**By PR importance**: Even trivial/housekeeping PRs have high zero-review rates (36.4% trivial, 31.5% low importance). Critical PRs fare better (23.2%) but still problematic. See `PR_IMPORTANCE_ANALYSIS.md` for full breakdown.

---

## 2. Merge Relationships: "Friend" Patterns

**Definition**: A "friend" pattern is when one maintainer consistently merges another maintainer's PRs (20%+ of that person's PRs).

### Top Friend Patterns

| Rank | Merger | Author | Merges | % of Author's PRs |
|------|--------|--------|--------|-------------------|
| 1 | fanquake | maflcko | 701 | 32.4% |
| 2 | fanquake | hebasto | 494 | 56.9% |
| 3 | laanwj | maflcko | 490 | 22.7% |
| 4 | laanwj | sipa | 309 | 41.1% |
| 5 | laanwj | fanquake | 303 | 24.2% |
| 6 | laanwj | theuni | 201 | 68.4% |
| 7 | laanwj | jonasschnelli | 186 | 71.5% |
| 8 | maflcko | jnewbery | 160 | 51.0% |
| 9 | laanwj | luke-jr | 136 | 48.2% |
| 10 | laanwj | thebluematt | 132 | 45.5% |

### Key Observations

1. **fanquake** is the primary merger for:
   - **hebasto**: 56.9% of PRs
   - **maflcko**: 32.4% of PRs
   - **achow101**: 31.6% of PRs

2. **laanwj** is the primary merger for:
   - **jonasschnelli**: 71.5% of PRs
   - **theuni**: 68.4% of PRs
   - **sipa**: 41.1% of PRs
   - **promag**: 52.0% of PRs
   - **gmaxwell**: 51.9% of PRs

3. **maflcko** is the primary merger for:
   - **jnewbery**: 51.0% of PRs
   - **jonatack**: 42.3% of PRs

**Implication**: Strong relationship patterns may indicate informal authority structures. While some collaboration is expected, patterns where one person merges 50%+ of another's PRs suggest potential gatekeeping roles. This analysis is based on publicly available merge data and does not account for private coordination or normal collaborative workflows.

---

## 3. High-Volume Merger Patterns

**Definition**: A "high-volume merger" is a maintainer who merges PRs from many different authors (10+ unique authors). This pattern may indicate centralized merge authority or active maintenance work.

### Top High-Volume Mergers

| Rank | Janitor | Unique Authors | Total Merges | Avg per Author |
|------|---------|----------------|--------------|----------------|
| 1 | laanwj | 20 | 3,208 | 160.4 |
| 2 | fanquake | 18 | 2,378 | 132.1 |
| 3 | maflcko | 19 | 1,891 | 99.5 |
| 4 | gavinandresen | 10 | 392 | 39.2 |
| 5 | achow101 | 14 | 308 | 22.0 |
| 6 | sipa | 18 | 303 | 16.8 |
| 7 | jonasschnelli | 16 | 160 | 10.0 |
| 8 | glozow | 13 | 137 | 10.5 |
| 9 | gmaxwell | 12 | 80 | 6.7 |
| 10 | ryanofsky | 11 | 67 | 6.1 |

### Key Observations

1. **laanwj** is the primary janitor:
   - Merges from **20 different authors**
   - **3,208 total merges** (34.8% of all maintainer merges)
   - Top authors: laanwj (self), maflcko, sipa, fanquake, theuni

2. **fanquake** is the secondary janitor:
   - Merges from **18 different authors**
   - **2,378 total merges** (25.8% of all maintainer merges)
   - Top authors: maflcko, fanquake (self), hebasto, achow101, glozow

3. **maflcko** is the tertiary janitor:
   - Merges from **19 different authors**
   - **1,891 total merges** (20.5% of all maintainer merges)
   - Top authors: maflcko (self), fanquake, hebasto, jnewbery, jonatack

**Implication**: Three maintainers (laanwj, fanquake, maflcko) handle **81.0% of all merges** (7,477 of 9,235, rounded to 81.1% in summary documents), creating extreme concentration of merge authority.

---

## 4. Individual Maintainer Self-Merge Patterns

### Top 15 Maintainers by Total Merges

| Maintainer | Total Merged | Self-Merge Rate | Self-Merge Count | Zero Reviews | One Review | Two+ Reviews |
|------------|--------------|-----------------|-----------------|--------------|------------|--------------|
| **maflcko** | 2,161 | 37.4% | 808 | 258 | 171 | 379 |
| **fanquake** | 1,251 | 51.2% | 641 | 68 | 187 | 386 |
| **hebasto** | 868 | 2.0% | 17 | 2 | 4 | 11 |
| **laanwj** | 828 | 77.1% | 638 | 522 | 34 | 82 |
| **sipa** | 752 | 19.0% | 143 | 123 | 3 | 17 |
| **achow101** | 361 | 3.3% | 12 | 0 | 1 | 11 |
| **jnewbery** | 314 | 0.0% | 0 | 0 | 0 | 0 |
| **theuni** | 294 | 0.0% | 0 | 0 | 0 | 0 |
| **thebluematt** | 292 | 0.7% | 2 | 2 | 0 | 0 |
| **luke-jr** | 282 | 0.4% | 1 | 1 | 0 | 0 |
| **ryanofsky** | 273 | 0.4% | 1 | 0 | 0 | 1 |
| **jonasschnelli** | 260 | 15.4% | 40 | 20 | 5 | 15 |
| **jonatack** | 253 | 0.0% | 0 | 0 | 0 | 0 |
| **promag** | 204 | 0.0% | 0 | 0 | 0 | 0 |
| **gavinandresen** | 180 | 68.3% | 123 | 122 | 0 | 1 |

**Key Findings**:
- **Average self-merge rate**: 14.5% (lower than overall 26.5% because some maintainers rarely self-merge)
- **Average zero-review self-merge rate**: 33.6% (of self-merges)
- **Extreme variation**: 
  - **laanwj**: 77.1% self-merge (522 with zero reviews!)
  - **gavinandresen**: 68.3% self-merge (122 with zero reviews)
  - **fanquake**: 51.2% self-merge
  - **maflcko**: 37.4% self-merge
  - **7 maintainers**: 0% self-merge (never self-merge)

### Notable Patterns

1. **High self-merge maintainers**: Some maintainers self-merge 40-50%+ of their PRs
2. **Low self-merge maintainers**: Some maintainers rarely or never self-merge
3. **Zero-review self-merge**: Many maintainers self-merge with zero reviews

---

## 5. Structural Analysis

### Concentration of Merge Authority

**Top 3 mergers handle 81.1% of all merges** (rounded):
- laanwj: 3,208 merges (34.8%)
- fanquake: 2,378 merges (25.8%)
- maflcko: 1,891 merges (20.5%)
- **Total**: 7,477 merges (81.0% of 9,235, rounded to 81.1%)

**Top 10 mergers handle 95%+ of all merges**

### Relationship Patterns

1. **Friend patterns**: 24 significant relationships where one maintainer merges 20%+ of another's PRs
2. **Janitor patterns**: 10 maintainers merge from 10+ different authors
3. **Self-merge patterns**: 26.5% overall, but 46.1% of those have zero reviews

### Governance Implications

1. **Extreme concentration**: 3 people control 81.1% of merges
2. **Informal authority**: Friend patterns suggest informal gatekeeping
3. **Unaccountable self-merge**: 12.2% of all maintainer PRs merge with zero reviews
4. **No formal, publicly documented rules**: Wide variation in self-merge rates and review requirements

---

## 6. Comparison: Self-Merge vs Other-Merge

### Review Requirements

**Self-merged PRs**:
- Zero reviews: 46.1%
- One review: 16.7%
- Two+ reviews: 37.2%

**Other-merged PRs**:
- Zero reviews: ~35-40% (estimated)
- One review: ~15-20% (estimated)
- Two+ reviews: ~40-45% (estimated)

**Finding**: Self-merged PRs have slightly higher zero-review rate, but both groups show wide variation.

### Time-to-Merge (Speed Hack)

**All-time aggregate**:
- Self-merged PRs: 15.3 days average
- Other-merged PRs: 31.2 days average
- **Speed ratio**: 2.04x faster

**Temporal analysis**: See `TEMPORAL_ANALYSIS_REPORT.md` for breakdown by historical vs recent period.

---

## 7. Key Statistics

| Metric | Value |
|--------|-------|
| **Total maintainer merged PRs** | 9,235 |
| **Self-merge rate** | 26.5% (2,446 PRs) |
| **Zero-review self-merge** | 12.2% of all PRs (1,127 PRs) |
| **Unique mergers** | 15 people |
| **Top 3 merger concentration** | 81.1% of all merges |
| **Friend patterns** | 24 significant relationships |
| **Janitor patterns** | 10 maintainers merge 10+ authors |
| **Average self-merge rate** | 14.5% (by maintainer) |
| **Zero-review self-merge rate** | 33.6% (of self-merges) |

---

## 8. Implications for Governance

### Structural Problems

1. **Extreme concentration**: 3 people control 81.1% of merges
2. **Informal gatekeeping**: Friend patterns create informal authority structures
3. **Unaccountable self-merge**: 12.2% of PRs merge with zero reviews
4. **No formal, publicly documented rules**: Wide variation suggests discretionary, not rule-based governance

### Commons Model Comparison

**Bitcoin Core** (based on analysis of 9,235 maintainer merged PRs):
- 3 people control 81.1% of merges
- 26.5% self-merge (46.1% with zero reviews)
- Informal relationship patterns
- Discretionary standards (no formal, publicly documented rules)

**Commons Governance Principles** (theoretical):
- Would distribute merge authority
- Would require 0% self-merge (all follow same rules)
- Would use transparent, rule-based processes
- Would include community accountability mechanisms

---

## Data Files

- **Analysis script**: `scripts/analysis/merge_pattern_analysis.py`
- **Results JSON**: `data/merge_pattern_analysis.json`
- **This report**: `MERGE_PATTERN_BREAKDOWN.md`
