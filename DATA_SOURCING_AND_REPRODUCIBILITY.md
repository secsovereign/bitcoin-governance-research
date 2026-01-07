# Data Sourcing and Reproducibility

**Date**: 2026-01-07  
**Purpose**: Document data sources and enable reproducibility

---

## Data Sources

### Primary Source: GitHub API

**Repository**: `bitcoin/bitcoin`  
**API**: GitHub REST API v3  
**Authentication**: Personal Access Token (required for higher rate limits)

**Data Collected**:
- Pull Requests (PRs): 23,478 PRs
- Issues: 8,890 issues
- Commits: Full commit history
- Reviews: All PR reviews
- Comments: PR and issue comments
- Merged_by data: Backfilled via separate script

**Collection Script**: `scripts/data_collection/github_collector.py`

### Secondary Sources

**Mailing Lists**: Collected via `scripts/data_collection/mailing_list_collector.py`  
**IRC Channels**: Collected via `scripts/data_collection/irc_collector.py`  
**Satoshi Archive**: Collected via `scripts/data_collection/satoshi_archive_collector.py`
  - Source: GitHub archive `lugaxker/nakamoto-archive` repository
  - Contains 549 Satoshi Nakamoto communications (2008-2015)
  - Includes emails, forum posts, code releases, documents
  - Used for historical governance context analysis
**Other**: Various collectors in `scripts/data_collection/`

---

## Raw Data Files

### Large Files (Not Included in ZIP)

**Location**: `data/github/`

| File | Size | Description | Included? |
|------|------|-------------|------------|
| `prs_raw.jsonl` | 230M | All PRs (23,478) | ❌ No (too large) |
| `issues_raw.jsonl` | 50M | All issues (8,890) | ❌ No (too large) |
| `commits_raw.jsonl` | 5.8M | Commit history | ❌ No (too large) |
| `merged_by_mapping.jsonl` | 625K | Merged_by backfill data | ✅ Yes (critical) |

**Why Not Included**: Raw data files are too large (285M+ total). Scripts can regenerate them.

### Analysis Result Files (Included)

**Location**: `findings/*.json`

| File | Size | Description | Included? |
|------|------|-------------|-----------|
| `merge_pattern_analysis.json` | ~100K | Merge pattern results | ✅ Yes |
| `quick_insights.json` | ~50K | Quick insights results | ✅ Yes |
| `temporal_analysis.json` | 28K | Temporal analysis results | ✅ Yes |
| `novel_interpretations.json` | 28K | Novel interpretations | ✅ Yes |
| `interdisciplinary_analysis.json` | ~50K | Interdisciplinary results | ✅ Yes |
| `network_data.json` | 96K | Network data for visualization | ✅ Yes |
| `validation_results.json` | 68K | Validation results | ✅ Yes |
| `enhanced_funding_analysis.json` | ~50K | Enhanced funding results | ✅ Yes |
| `funding_correlation.json` | ~10K | Funding correlation | ✅ Yes |
| `review_quality_enhanced.json` | 148K | Review quality results | ✅ Yes |
| `funding_analysis.json` | 4.4M | Large funding analysis | ⚠️ Consider excluding |

**Total Analysis Results**: ~5M (mostly from funding_analysis.json)

---

## Reproducibility

### To Reproduce Analysis

1. **Install Dependencies**:
   ```bash
   pip install PyGithub
   ```

2. **Get GitHub Token**:
   - Create personal access token at https://github.com/settings/tokens
   - Set environment variable: `export GITHUB_TOKEN=your_token`

3. **Collect Raw Data** (if needed):
   ```bash
   python scripts/data_collection/github_collector.py
   python scripts/data_collection/backfill_merged_by_optimized.py
   python scripts/data_collection/mailing_list_collector.py
   python scripts/data_collection/irc_collector.py
   python scripts/data_collection/satoshi_archive_collector.py
   ```
   **Note**: This takes hours due to API rate limits (5,000 requests/hour for GitHub)
   **Note**: Satoshi archive collection clones a GitHub repository (no API limits)

4. **Run Analyses**:
   ```bash
   python scripts/analysis/merge_pattern_analysis.py
   python scripts/analysis/temporal_analysis.py
   python scripts/analysis/interdisciplinary_analysis.py
   # ... etc
   ```

### Data Stubs/Samples

**For Large Files**: Create sample files showing structure

**Example**: `data/github/prs_raw_sample.jsonl`
- First 10 PRs from full dataset
- Shows data structure
- Enables understanding without full download

---

## What's Included in ZIP

### ✅ Included

1. **All Scripts**:
   - `scripts/analysis/*.py` - All analysis scripts
   - `scripts/data_collection/*.py` - All collection scripts
   - `scripts/validation/*.py` - Validation scripts
   - `scripts/utils/*.py` - Utility scripts

2. **Analysis Results** (JSON):
   - All `findings/*.json` files (analysis results)
   - `merged_by_mapping.jsonl` (critical for self-merge analysis)

3. **All Reports**:
   - All `findings/*.md` files
   - Documentation

### ❌ Not Included (Too Large)

1. **Raw Data Files**:
   - `prs_raw.jsonl` (230M)
   - `issues_raw.jsonl` (50M)
   - `commits_raw.jsonl` (5.8M)

**Reason**: Can be regenerated using included scripts

### ⚠️ Consider Excluding

1. **Large Analysis Results**:
   - `funding_analysis.json` (4.4M)

**Reason**: Very large, may not be essential

---

## Recommendations

### Option 1: Include Analysis Results Only (Current)

**Pros**: 
- All analysis results available
- Can verify calculations
- No need to regenerate

**Cons**: 
- ZIP file larger (~5M from funding_analysis.json)
- Still missing raw data

### Option 2: Create Data Stubs

**Action**: Create sample files for large datasets

**Example**:
- `data/github/prs_raw_sample.jsonl` (first 10 PRs)
- `data/github/issues_raw_sample.jsonl` (first 10 issues)
- Document structure in README

**Pros**: 
- Shows data structure
- Enables understanding
- Keeps ZIP small

**Cons**: 
- Can't run full analysis without full data

### Option 3: Exclude Large Analysis Results

**Action**: Exclude `funding_analysis.json` (4.4M)

**Pros**: 
- Smaller ZIP
- Can regenerate if needed

**Cons**: 
- Missing some analysis results

---

## Current ZIP Contents

**Included**:
- ✅ All scripts (can regenerate data)
- ✅ All analysis result JSONs (including large ones)
- ✅ All reports
- ✅ `merged_by_mapping.jsonl` (critical)

**Not Included**:
- ❌ Raw data files (230M+)
- ❌ Archive directory

**Size**: 544K (without raw data)

---

## Recommendation

**Current approach is good**:
1. ✅ Scripts included (can regenerate)
2. ✅ Analysis results included (can verify)
3. ✅ Critical data included (`merged_by_mapping.jsonl`)
4. ❌ Raw data excluded (too large, can regenerate)

**Optional Enhancement**: Create data stubs/samples for documentation purposes.

---

## Files

- **This document**: `DATA_SOURCING_AND_REPRODUCIBILITY.md`
- **Collection scripts**: `scripts/data_collection/`
- **Analysis scripts**: `scripts/analysis/`
- **Raw data**: `data/github/` (not in ZIP)
- **Analysis results**: `findings/*.json` (in ZIP)
