# Data Sourcing and Reproducibility

**Date**: 2026-09-10  
**Purpose**: Document data sources and enable reproducibility. Raw corpora are gitignored; clones resync with `scripts/collect_all.py`.

---

## Data Sources

### Primary Source: GitHub API

**Repository**: `bitcoin/bitcoin`  
**API**: GitHub REST API v3  
**Authentication**: Personal Access Token (required for higher rate limits)

**Data Collected**:
- Pull Requests (PRs): 25,122 PRs
- Issues: 8,890 issues
- Commits: Full commit history
- Reviews: All PR reviews
- Comments: PR and issue comments
- Merged_by data: Backfilled via separate script

**Collection Script**: `scripts/data_collection/github_collector.py`

### Secondary Sources

**Mailing Lists (bitcoin-dev)**: `scripts/data_collection/gnusha_collector.py`  
**Source**: https://gnusha.org/pi/bitcoindev public-inbox  
**Coverage**: 24,644 emails → `data/mailing_lists/emails.jsonl`

**Mailing Lists (cryptography)**: `scripts/data_collection/cryptography_ml_collector.py`  
**Source**: https://www.metzdowd.com/pipermail/cryptography/  
**Coverage**: 26,420 emails → `data/mailing_lists/cryptography.jsonl`  
**Dedupe**: 2 `message_id` overlaps with bitcoin-dev when analyses combine lists  
**Local cache**: pipermail `.txt.gz` under `data/mailing_lists/cryptography_raw/` is gitignored (re-downloadable). Do not commit `*.bak` (e.g. Bitcointalk pre-reindex backup).

**IRC Channels**: `scripts/data_collection/irc_collector.py` → `430,613` messages in `data/irc/messages.jsonl`

**Delving Bitcoin**: `scripts/data_collection/delving_collector.py` → `4,662` posts

**Bitcointalk (board 6)**: `scripts/data_collection/bitcointalk_collector.py` → `158,917` posts  
**Gap**: topic `n_posts` exceeds stored posts by ~18k. That is a parser ceiling (unrecoverable by refetch), not a missing-download. Do not treat board totals as a completeness check.

**Satoshi Archive**: `scripts/data_collection/satoshi_archive_collector.py` (549 communications, separate from board scrape)

**Orchestration**: `scripts/collect_all.py` (initial) / `scripts/update_all.py` (incremental)


---

## What is in git vs local

**In git:** scripts, findings markdown, analysis JSON (`findings/data/`, `analysis/findings/data/`), samples, manifests, maintainer lists.

**Local only (resync):** every corpus under `data/` except samples/manifests/config. That includes GitHub JSONL, IRC raw HTML + messages, mailing-list dumps, Delving, Bitcointalk, processed JSONL, and Satoshi archive binaries. See `data/README.md`.

Do not run `git clean -fd` / `git clean -fdx` — those delete ignored dumps. `collect_all.py` skips files that already exist.

```bash
python scripts/collect_all.py
python scripts/update_all.py
```

### Analysis Result Files (Included)

**Location**: `findings/data/*.json` and `analysis/findings/data/*.json`
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
   python scripts/collect_all.py          # initial full collect
   # or incremental:
   python scripts/update_all.py
   ```
   **Note**: GitHub collection takes hours (API rate limits). Forum/list collectors are separate long poles.


4. **Run analyses + reports**:
   ```bash
   python scripts/run_all_analyses.py --reports
   ```

Samples (structure only): `data/github/samples/`, `data/irc/messages_sample.jsonl`, `data/mailing_lists/emails_sample.jsonl`.

---

## Files

- This document: `DATA_SOURCING_AND_REPRODUCIBILITY.md`
- Local corpora map: `data/README.md`
- Collectors: `scripts/data_collection/`
- Analyses: `scripts/analysis/`
- Reports: `scripts/reporting/`
- Analysis JSON: `findings/data/`, `analysis/findings/data/`
