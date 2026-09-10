# Data Samples

**Purpose**: Sample files showing data structure without including full datasets

---

## Files

- `prs_raw_sample.jsonl` - Sample of 10 PRs (full file: ~230M, 25,122 PRs)
- `issues_raw_sample.jsonl` - Sample of 10 issues (full file: 50M, 8,890 issues)
- `commits_raw_sample.jsonl` - Sample of 10 commits (full file: 5.8M)
- `merged_by_mapping_sample.jsonl` - Sample of 20 mappings (full file: 625K, 9,235 mappings)

---

## To Get Full Data

```bash
# token: see GITHUB_TOKEN_SETUP.md
python scripts/collect_all.py
# or GitHub only:
python scripts/data_collection/github_collector.py
python scripts/data_collection/backfill_merged_by_optimized.py
```

Full collection takes hours (GitHub: 5,000 requests/hour with a token).

---

## Data Structure

Each `.jsonl` file contains one JSON object per line. See sample files for structure.

---

**Created**: 2025-12-14
