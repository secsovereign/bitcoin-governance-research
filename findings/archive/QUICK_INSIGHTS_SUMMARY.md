# Quick Insights: Low-Effort, High-Impact Findings

**Analysis Date**: 2025-12-14  
**Purpose**: Extract valuable insights from existing data with minimal computation

---

## Key Findings

### 1. Self-Merge Correlations

**Self-merged PRs vs Other-merged PRs:**

| Metric | Self-Merge | Other-Merge | Difference |
|--------|-----------|-------------|------------|
| **Zero-review rate** | 46.1% | 36.6% | +9.5 percentage points |
| **Average review count** | 2.5 | 5.8 | -3.3 reviews |
| **Time to merge** | 15.3 days | 31.2 days | -15.9 days (2x faster) |

**Key Insight**: Self-merged PRs have **higher zero-review rate**, **fewer reviews**, but **merge 2x faster**. This suggests self-merge is used to bypass review requirements and speed up merges.

---

### 2. Maintainer Outliers

**Highest Self-Merge Rates:**
1. **laanwj**: 77.1% (638/828 PRs)
2. **gavinandresen**: 68.3% (123/180 PRs)
3. **fanquake**: 51.2% (641/1,251 PRs)
4. **maflcko**: 37.4% (808/2,161 PRs)
5. **sipa**: 19.0% (143/752 PRs)

**Lowest Self-Merge Rates (Never Self-Merge):**
- **petertodd**: 0.0% (0/61)
- **theuni**: 0.0% (0/294)
- **promag**: 0.0% (0/204)
- **instagibbs**: 0.0% (0/167)
- **jnewbery**: 0.0% (0/314)

**Highest Zero-Review Self-Merge Rates:**
1. **thebluematt**: 100.0% (2/2 self-merges)
2. **luke-jr**: 100.0% (1/1 self-merges)
3. **gmaxwell**: 100.0% (9/9 self-merges)
4. **gavinandresen**: 99.2% (122/123 self-merges)
5. **sipa**: 86.0% (123/143 self-merges)

**Key Insight**: Extreme variation in self-merge behavior. Some maintainers never self-merge, while others (laanwj, gavinandresen) self-merge 68-77% of the time, often with zero reviews.

---

### 3. PR Success Factors

**Maintainer PRs:**
- **Merge rate**: 79.9%
- **Avg reviews (merged)**: 5.0
- **Avg reviews (not merged)**: 3.9

**Non-Maintainer PRs:**
- **Merge rate**: 55.4%
- **Avg reviews (merged)**: 6.6
- **Avg reviews (not merged)**: 3.1

**Key Insight**: 
- Maintainers have 24.5 percentage point higher merge rate
- Merged PRs get more reviews than not-merged (for both groups)
- Non-maintainer merged PRs get **more reviews** (6.6 vs 5.0), suggesting they need more scrutiny to be accepted

---

### 4. Temporal Anomalies

**Notable Years:**
- **Highest self-merge year**: 2012 (43.5%)
- **Lowest zero-review year**: 2024 (3.7%)

**Key Insight**: Early years had higher self-merge rates, recent years have dramatically reduced zero-review merges.

---

### 5. Response Time Bias

**Finding**: **No significant bias** in response times.

- **Maintainer PRs**: 21.6 hours average
- **Non-maintainer PRs**: 21.6 hours average
- **Ratio**: 1.00x (no difference)

**Key Insight**: Response times are equal, but merge rates and speeds differ significantly. The bias is in **outcomes**, not **responsiveness**.

---

## Additional Low-Hanging Fruit Analyses

### Already Identified (Can Implement Quickly)

1. **Network Visualization Data**
   - Export merge relationships as graph data (who merges whom)
   - Export review relationships (who reviews whom)
   - **Effort**: Low (just format existing data)
   - **Impact**: High (visual representation of power structures)

2. **Maintainer Lifecycle Analysis**
   - Track path from first PR to maintainer status
   - Time to become maintainer
   - PR count before maintainer status
   - **Effort**: Low (track first PR date vs maintainer timeline)
   - **Impact**: Medium (shows barriers to entry)

3. **Domain/File Type Analysis**
   - Do certain file types have different patterns?
   - Security-related files vs documentation
   - **Effort**: Medium (need to categorize files)
   - **Impact**: Medium (shows if critical code gets more scrutiny)

4. **Conflict Analysis**
   - NACK patterns by maintainer
   - Most contentious PRs (most NACKs, most comments)
   - **Effort**: Low (already have NACK data)
   - **Impact**: Medium (shows where conflicts occur)

5. **Review Effectiveness**
   - Do reviews with questions lead to changes?
   - Do reviews with suggestions get addressed?
   - **Effort**: Medium (need to track PR changes after reviews)
   - **Impact**: High (shows if reviews matter)

6. **Funding Correlation**
   - Do PRs with funding mentions have higher merge rates?
   - Do funded contributors get faster merges?
   - **Effort**: Low (already have funding data)
   - **Impact**: High (shows potential influence of funding)

7. **Individual Maintainer Profiles**
   - Complete profiles: self-merge rate, review style, merge patterns
   - **Effort**: Low (aggregate existing data)
   - **Impact**: Medium (shows individual variation)

---

## Most Valuable Quick Wins

### 1. Funding Correlation Analysis ⭐⭐⭐
**Why**: Already have funding mention data, just need to correlate with merge outcomes.
**Effort**: Very Low
**Impact**: Very High (shows potential funding influence)

### 2. Network Visualization Data ⭐⭐⭐
**Why**: Have all the relationship data, just need to format for visualization.
**Effort**: Very Low
**Impact**: Very High (visual representation is powerful)

### 3. Review Effectiveness ⭐⭐
**Why**: Have review data, can check if questions/suggestions lead to changes.
**Effort**: Medium
**Impact**: High (shows if reviews actually matter)

### 4. Maintainer Lifecycle ⭐⭐
**Why**: Can track first PR to maintainer status from existing data.
**Effort**: Low
**Impact**: Medium (shows barriers to entry)

---

## Recommended Next Steps

1. **Run funding correlation** (5 minutes)
2. **Export network data** (10 minutes)
3. **Create maintainer profiles** (15 minutes)
4. **Analyze review effectiveness** (30 minutes)

---

## Files

- **Analysis script**: `scripts/analysis/quick_insights.py`
- **Results**: `findings/quick_insights.json`
- **This summary**: `findings/QUICK_INSIGHTS_SUMMARY.md`
