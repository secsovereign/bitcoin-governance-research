# Data Samples

**Purpose**: Sample files showing data structure without including full datasets

---

## Files

- `prs_raw_sample.jsonl` - Sample of 10 PRs (full file: 230M, 23,478 PRs)
- `issues_raw_sample.jsonl` - Sample of 10 issues (full file: 50M, 8,890 issues)
- `commits_raw_sample.jsonl` - Sample of 10 commits (full file: 5.8M)
- `merged_by_mapping_sample.jsonl` - Sample of 20 mappings (full file: 625K, 9,235 mappings)

---

## To Get Full Data

1. **Install dependencies**: `pip install PyGithub`
2. **Get GitHub token**: https://github.com/settings/tokens
3. **Set environment**: `export GITHUB_TOKEN=your_token`
4. **Run collector**: `python scripts/data_collection/github_collector.py`
5. **Backfill merged_by**: `python scripts/data_collection/backfill_merged_by_optimized.py`

**Note**: Full data collection takes hours due to GitHub API rate limits (5,000 requests/hour).

---

## Data Structure

Each `.jsonl` file contains one JSON object per line. See sample files for structure.

---

**Created**: 2025-12-14
