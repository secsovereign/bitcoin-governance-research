# Code Turnover and Technical Debt Measurement Methodology

**Date**: 2026-01-28  
**Purpose**: Quantify Bitcoin Core's technical debt through code turnover analysis  
**Research Question**: How much of Bitcoin Core's codebase represents accumulated technical debt from 15 years of development?

---

## Executive Summary

This methodology measures **technical debt** - code that represents accumulated shortcuts, patches, and architectural decisions that make the codebase harder to maintain, refactor, or evolve. 

**Key Insight**: Not all old code is technical debt. Not all new code is good. We need to identify:
- **Legacy code that's stable and well-designed** = NOT debt (good architecture)
- **Legacy code that's patched repeatedly** = Technical debt (accumulated shortcuts)
- **Code that's never refactored despite problems** = Technical debt (debt accumulation)
- **Code that's too risky to change** = Technical debt (architectural lock-in)

**Core Research Questions**:

1. **What percentage of Bitcoin Core's codebase is technical debt?**
   - Code that's been patched repeatedly (high modification count, low refactoring)
   - Code that's too risky to change (consensus code, ancient architecture)
   - Code that represents accumulated shortcuts (many small patches, no refactoring)

2. **How has technical debt accumulated over 15 years?**
   - Is debt increasing (more patches, less refactoring)?
   - Which subsystems have the most debt?
   - What's the ratio of refactoring to patching?

3. **What's the cost of technical debt?**
   - How much code is "untouchable" (too risky to change)?
   - How much code requires understanding 15 years of history?
   - What percentage of changes are patches vs. clean implementations?

**Key Metrics**:
1. **Technical Debt Score**: Composite metric combining age, patch frequency, refactoring rate, and criticality
2. **Patch-to-Refactor Ratio**: How often code is patched vs. properly refactored
3. **Untouchable Code Percentage**: Code that hasn't been refactored in 5+ years despite being modified
4. **Cumulative Patch Count**: How many times has code been patched without refactoring?
5. **Architectural Lock-In**: Code that can't be changed due to dependencies/risk

---

## The Right Questions vs. The Wrong Questions

### ❌ Wrong Questions (Misleading Metrics)

1. **"How old is the code?"** 
   - **Problem**: Old code isn't necessarily debt. Stable, well-designed code that's old is GOOD.
   - **Better**: "How much old code represents accumulated patches vs. stable design?"

2. **"What's the code turnover rate?"**
   - **Problem**: High turnover could mean instability (bad) or active refactoring (good). Low turnover could mean stable code (good) or untouchable debt (bad).
   - **Better**: "What's the ratio of refactoring to patching?"

3. **"What percentage of code is legacy?"**
   - **Problem**: "Legacy" is vague. Old code that works well isn't debt.
   - **Better**: "What percentage of code has been patched repeatedly without refactoring?"

### ✅ Right Questions (Actionable Metrics)

1. **"What percentage of code represents technical debt?"**
   - **Why**: Directly quantifies technical debt in the codebase
   - **Metric**: Debt score >50 = high debt
   - **Actionable**: Identifies files that need refactoring

2. **"Is code being patched or refactored?"**
   - **Why**: Patches accumulate debt, refactoring reduces it
   - **Metric**: Patch-to-refactor ratio
   - **Actionable**: Shows if debt is accumulating

3. **"What code is 'untouchable' (too risky to change)?"**
   - **Why**: Untouchable code = architectural lock-in = debt
   - **Metric**: Code modified recently but only small patches, never refactored
   - **Actionable**: Identifies areas that need architectural work

4. **"Is technical debt increasing over time?"**
   - **Why**: Shows if the problem is getting worse
   - **Metric**: Debt score trend over time
   - **Actionable**: Quantifies the "accumulation" claim

5. **"Which subsystems have the most debt?"**
   - **Why**: Prioritizes where to focus refactoring efforts
   - **Metric**: Debt score by subsystem
   - **Actionable**: Consensus code vs. network code vs. wallet code

### Key Insight: Technical Debt ≠ Old Code

**Technical Debt** = Code that makes the codebase harder to maintain/evolve:
- Patched repeatedly without refactoring
- Too risky to change (consensus code)
- Creates architectural lock-in
- Requires understanding 15 years of history

**NOT Technical Debt**:
- Old but stable, well-designed code
- Code that's been properly refactored
- Simple code that doesn't need refactoring

---

## Methodology

### 1. Code Age Analysis

**Question**: When was each line of code last modified?

**Method**:
- For each file in current codebase, trace git history
- Find last modification date for each line (using `git blame`)
- Calculate age distribution:
  - **0-1 years**: Recent code
  - **1-3 years**: Modern code
  - **3-5 years**: Mature code
  - **5-10 years**: Legacy code
  - **10+ years**: Ancient code (Satoshi era)

**Data Source**: Git repository (`git blame` for each file)

**Output Metrics**:
- Percentage of code by age category
- Average code age
- Median code age
- Oldest code still in use

### 2. File-Level Turnover

**Question**: What percentage of files have been significantly modified or replaced?

**Method**:
- Track file changes across all PRs (2009-2025)
- For each file currently in codebase:
  - Count total modifications (PRs that touched the file)
  - Calculate cumulative changes (total additions + deletions)
  - Classify files:
    - **Stable**: <10% of lines changed over lifetime
    - **Active**: 10-50% of lines changed
    - **Refactored**: >50% of lines changed (high turnover)
    - **Replaced**: File deleted and recreated (100% turnover)

**Data Source**: PR file change data (`prs_raw.jsonl` - `files` array)

**Output Metrics**:
- Percentage of files by stability category
- Average file modification count
- Files with highest/lowest turnover

### 3. Line-Level Turnover (Code Churn)

**Question**: What percentage of code has been rewritten?

**Method**:
- Track all line additions and deletions across PRs
- Calculate cumulative churn:
  - **Total lines ever written**: Sum of all additions
  - **Current codebase size**: Lines in current codebase
  - **Churn ratio**: (Total additions) / (Current size)
  - **Turnover rate**: If churn ratio = 3.0, codebase has been rewritten 3x

**Data Source**: PR statistics (`total_additions`, `total_deletions`)

**Output Metrics**:
- Cumulative code churn ratio
- Annual churn rate
- Net growth vs. gross additions

### 4. Technical Debt Indicators

**Question**: What code represents actual technical debt (not just old code)?

**Method**:
- Identify **debt indicators**:
  1. **High patch count, low refactoring**: File modified 20+ times but never refactored (>50% change)
  2. **Untouchable code**: Code modified recently but only small patches, never refactored
  3. **Ancient critical code**: Consensus/validation code >10 years old, rarely changed
  4. **Accumulated complexity**: Files with high modification count relative to size
- Calculate debt score per file:
  - Patch frequency (modifications per year)
  - Refactoring rate (significant changes vs. patches)
  - Age (years since last refactor)
  - Criticality (consensus code = higher debt weight)

**Data Source**: PR file change data + git history

**Output Metrics**:
- Technical debt percentage (files with high debt score)
- Debt by subsystem (which areas have most debt)
- Debt accumulation rate (is debt increasing?)
- Untouchable code percentage (code too risky to refactor)

### 5. Refactoring vs. Patching Analysis

**Question**: Is code being properly refactored, or just accumulating patches?

**Method**:
- Classify file changes by type:
  - **Patch**: Small incremental change (<20% of file, <100 lines)
  - **Feature Addition**: New code added, minimal changes to existing code
  - **Bug Fix**: Targeted fix, small scope
  - **Refactor**: Significant restructuring (>30% of file changed, or >200 lines)
  - **Replacement**: File deleted and recreated (100% turnover)
- Track patterns:
  - Files with many patches but no refactoring = debt accumulation
  - Files that get refactored regularly = healthy
  - Files that are never refactored despite many changes = debt
- Calculate metrics:
  - **Patch-to-Refactor Ratio**: Patches / Refactors per file
  - **Debt Accumulation Rate**: Files with increasing patch count, no refactoring
  - **Refactoring Frequency**: How often are files properly refactored?

**Data Source**: PR file change data

**Output Metrics**:
- Refactoring frequency (by subsystem, over time)
- Patch-to-refactor ratio (higher = more debt accumulation)
- Files with debt accumulation pattern (many patches, no refactoring)
- Technical debt accumulation rate (is debt increasing over time?)

---

## Data Requirements

### Available Data ✅

1. **PR File Changes**: `prs_raw.jsonl` contains:
   - `files` array with `filename`, `additions`, `deletions`, `changes`
   - `merged_at` date for timing
   - 23,478 PRs with file-level data

2. **Commit Data**: `commits_raw.jsonl` contains:
   - Commit SHA, date, author
   - File statistics
   - ~5,025 commits

### Missing Data ⚠️

1. **Git Blame Data**: Need to run `git blame` on current codebase
   - Requires cloning Bitcoin Core repository
   - Line-level modification dates

2. **File History**: Need complete file lifecycle tracking
   - When files were created
   - When files were deleted
   - File rename tracking

3. **Current Codebase Snapshot**: Need current file list and sizes
   - Total lines of code per file
   - File structure (directories, subsystems)

---

## Implementation Plan

### Phase 1: File-Level Analysis (Using Existing PR Data)

**Script**: `scripts/analysis/code_turnover_analysis.py`

**Steps**:
1. Load all PRs from `prs_raw.jsonl`
2. Extract file changes for merged PRs only
3. Build file change history:
   - For each file: list of all PRs that modified it
   - Cumulative additions/deletions per file
   - First modification date, last modification date
4. Calculate metrics:
   - File modification count
   - File churn ratio (total changes / current size estimate)
   - File age (time since last modification)
5. Generate report:
   - File-level turnover statistics
   - Most/least modified files
   - Files by modification frequency

**Output**: `findings/data/code_turnover_analysis.json`

### Phase 2: Code Age Analysis (Requires Git Repository)

**Script**: `scripts/analysis/code_age_analysis.py`

**Steps**:
1. Clone Bitcoin Core repository (or use existing clone)
2. For each file in current codebase:
   - Run `git blame` to get line-level modification dates
   - Calculate age distribution
3. Aggregate by:
   - File age categories
   - Subsystem (consensus, network, wallet, etc.)
   - Code age percentiles
4. Generate report:
   - Code age distribution
   - Legacy code percentage
   - Oldest code identification

**Output**: `findings/data/code_age_analysis.json`

### Phase 3: Cumulative Churn Analysis

**Script**: `scripts/analysis/code_churn_analysis.py`

**Steps**:
1. Sum all additions across all merged PRs
2. Sum all deletions across all merged PRs
3. Estimate current codebase size (from file change data)
4. Calculate:
   - Cumulative churn ratio
   - Annual churn rates
   - Net growth vs. gross additions
5. Generate report:
   - Churn metrics over time
   - Growth patterns
   - Turnover rate

**Output**: `findings/data/code_churn_analysis.json`

### Phase 4: Refactoring Analysis

**Script**: `scripts/analysis/refactoring_analysis.py`

**Steps**:
1. Classify PRs by change type (using file change percentages)
2. Identify refactoring PRs (>50% of file changed)
3. Calculate refactoring frequency over time
4. Analyze refactoring patterns:
   - Which subsystems get refactored?
   - Refactoring vs. patching trends
5. Generate report:
   - Refactoring statistics
   - Technical debt indicators

**Output**: `findings/data/refactoring_analysis.json`

---

## Expected Findings

### Hypotheses

1. **High Technical Debt Percentage**: Significant portion of codebase is debt
   - Evidence: Maintainers mention legacy code, accumulated patches over time
   - Prediction: 30-50% of codebase has high debt score (>50)
   - **Key Question**: What percentage represents actual debt vs. stable old code?

2. **High Patch-to-Refactor Ratio**: Code is patched, not refactored
   - Evidence: Maintainers mention "legacy code" frequently, IRC discussions
   - Prediction: <5% of file modifications are refactoring (>30% change)
   - **Key Question**: Are patches accumulating without refactoring?

3. **Consensus Code is Untouchable**: Core consensus code has highest debt
   - Evidence: Consensus changes are rare and risky, maintainers avoid touching it
   - Prediction: Consensus code has highest debt score (old + critical + never refactored)
   - **Key Question**: Is consensus code "locked in" due to risk?

4. **Debt Accumulation Over Time**: Debt increases, not decreases
   - Evidence: Codebase grows, refactoring is rare, patches accumulate
   - Prediction: Debt score increases over time (more patches, less refactoring)
   - **Key Question**: Is technical debt accumulating faster than it's being addressed?

5. **Architectural Lock-In**: Monolithic structure prevents refactoring
   - Evidence: 300k+ lines, tightly coupled, hard to split
   - Prediction: High dependency count = high debt (can't refactor without breaking everything)
   - **Key Question**: Does architecture prevent refactoring?

### Metrics to Report

**Primary Metrics**:
- **Technical Debt Percentage**: X% of codebase has debt score >50
- **Patch-to-Refactor Ratio**: Y patches per refactor (higher = more debt)
- **Untouchable Code**: Z% of code hasn't been refactored in 5+ years despite modifications
- **Debt by Subsystem**: Which areas have most debt (consensus, network, etc.)
- **Debt Accumulation Rate**: Is debt increasing over time?

**Supporting Metrics**:
- **Code Age Distribution**: X% of code is 10+ years old (context, not debt itself)
- **Cumulative Churn**: Codebase has been rewritten Z times (shows activity)
- **Refactoring Frequency**: Only V% of file changes are refactoring
- **Most Patched Files**: Top 20 files with highest patch count (debt candidates)

---

## Technical Debt Quantification

### Definition

**Technical Debt** = Code that represents accumulated shortcuts, patches, and architectural decisions that:
1. **Make maintenance harder**: Code that's been patched repeatedly without refactoring
2. **Increase risk**: Code that's too critical/risky to refactor (consensus code)
3. **Lock in architecture**: Code that prevents evolution (monolithic dependencies)
4. **Accumulate complexity**: Many small patches instead of proper refactoring

**NOT Technical Debt**:
- Old but stable, well-designed code (if it works, don't fix it)
- Code that's been properly refactored over time
- Simple code that doesn't need refactoring

### Debt Score Formula

For each file, calculate a composite debt score:

```
Debt Score = 
  (Patch Frequency × 0.3) +           # High patch count = debt
  (Refactoring Deficit × 0.3) +       # Never refactored = debt
  (Age Risk × 0.2) +                  # Old critical code = debt
  (Complexity × 0.2)                  # High complexity = debt
```

Where:
- **Patch Frequency**: Modifications per year (higher = more patches = debt)
- **Refactoring Deficit**: Years since last refactor (if >3 years and modified = debt)
- **Age Risk**: Age × Criticality (old consensus code = high risk)
- **Complexity**: Modification count / file size (many patches on small file = debt)

### Debt Categories

1. **Low Debt (0-25)**: 
   - Recent code OR regularly refactored
   - Low patch frequency
   - Non-critical subsystems

2. **Medium Debt (25-50)**:
   - Mature code with some patches
   - Occasional refactoring
   - Moderate complexity

3. **High Debt (50-75)**:
   - Many patches, no refactoring
   - Old code that's been patched repeatedly
   - High complexity relative to size

4. **Critical Debt (75-100)**:
   - Ancient consensus code, never refactored
   - Very high patch count, zero refactoring
   - Too risky to change (architectural lock-in)

### Key Insight: The "Untouchable Code" Problem

**The real technical debt** isn't just old code - it's code that:
- Has been patched many times (accumulated shortcuts)
- Can't be refactored due to risk (consensus code)
- Creates architectural lock-in (monolithic dependencies)
- Requires understanding 15 years of history to change

This is what technical debt means: not just old code, but **accumulated decisions that make the codebase harder to evolve**.

---

## Limitations

1. **File Renames**: Git may not track renames perfectly
   - Solution: Use similarity heuristics

2. **Current Codebase Size**: Need accurate line counts
   - Solution: Clone repo and count lines

3. **Git Blame Accuracy**: `git blame` shows last modification, not creation
   - Solution: Use `git log --follow` for file history

4. **PR Data Completeness**: Some early PRs may be missing
   - Solution: Acknowledge limitation, focus on recent data

5. **Subsystem Classification**: Need to categorize files
   - Solution: Use directory structure (src/consensus/, src/net/, etc.)

---

## Deliverables

1. **Analysis Scripts**: 4 Python scripts for each phase
2. **Data Files**: JSON outputs with metrics
3. **Findings Report**: `findings/CODE_TURNOVER_ANALYSIS.md`
4. **Visualizations**: Code age distribution charts, turnover trends
5. **Technical Debt Score**: Quantified debt metric

---

## Next Steps

1. ✅ Create methodology document (this file)
2. ⏳ Implement Phase 1: File-level analysis (using existing PR data)
3. ⏳ Implement Phase 2: Code age analysis (requires git clone)
4. ⏳ Implement Phase 3: Cumulative churn analysis
5. ⏳ Implement Phase 4: Refactoring analysis
6. ⏳ Generate findings report
7. ⏳ Create visualizations

---

## References

- **Code Churn Metrics**: Software engineering best practices
- **Technical Debt**: Martin Fowler's definition
- **Git Blame**: Git documentation
- **Bitcoin Core Repository**: https://github.com/bitcoin/bitcoin

