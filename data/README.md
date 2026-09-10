# Local data corpora

Raw and processed dumps are **not in git**. They stay on disk. `git rm --cached` only drops them from the index.

**Do not run `git clean -fd` or `git clean -fdx`.** Those delete ignored files and would wipe this directory.

`scripts/collect_all.py` skips a dump when it already exists. Use `scripts/update_all.py` for incremental refresh.

```bash
source venv/bin/activate
# GitHub token recommended: see GITHUB_TOKEN_SETUP.md
python scripts/collect_all.py
# later:
python scripts/update_all.py
```

`--process` on either command runs `clean_data.py` + `enrich_data.py` after GitHub PRs exist.

## What stays in git

- `data/github/samples/` — 10-row structure stubs
- `data/*/manifest.json` — collection fingerprints
- `data/maintainers/` — canonical maintainer list
- `data/classification/*.yaml` — classification config
- `data/reference/` — architecture manifest
- `data/satoshi_archive/nakamoto-archive/doc/` — curated Satoshi posts

## What you regenerate locally

| Path | Collector |
|------|-----------|
| `data/github/{prs,issues,commits}_raw.jsonl` | `github_collector.py`, `github_commits_collector.py` |
| `data/github/merged_by_mapping.jsonl` | `backfill_merged_by_optimized.py` |
| `data/mailing_lists/emails.jsonl` | `gnusha_collector.py` |
| `data/mailing_lists/cryptography.jsonl` | `cryptography_ml_collector.py` |
| `data/irc/messages.jsonl` | `irc_collector.py` |
| `data/delving/{topics,posts}.jsonl` | `delving_collector.py` |
| `data/bitcointalk/{topics,posts}.jsonl` | `bitcointalk_collector.py` |
| `data/bips/*.jsonl` | `bips_collector.py` |
| `data/processed/` | `clean_data.py`, `enrich_data.py` |

Full collection takes hours (GitHub rate limits). Analysis JSON under `findings/data/` and `analysis/findings/data/` **is** in git so reports stay readable without the corpora.
