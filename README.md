# Bitcoin Core Governance Research

Quantitative analysis of Bitcoin Core governance from public communications (2010–2026).

**Start here:** [`findings/EXECUTIVE_SUMMARY.md`](findings/EXECUTIVE_SUMMARY.md) then [`findings/GOVERNANCE_FRAMES.md`](findings/GOVERNANCE_FRAMES.md). Navigation: [`findings/README.md`](findings/README.md).

## What this measures

1. Who holds merge keys, and whether that concentrates over time
2. Review and merge decision patterns (including self-merge)
3. Informal channels vs GitHub (agenda-setting vs decision, by era)
4. Whether activity on BIPs / lists / forums predicts Core authority
5. Later passes: who the bar moved against, what `CONTRIBUTING.md` judgment looked like, and which attention patterns the corpus can actually score (`findings/EXECUTIVE_SUMMARY.md`, section “Later measurements”)

## Layout

```
collect  →  analyze  →  report
```

| Path | Role |
|------|------|
| `scripts/collect_all.py` / `update_all.py` | Collect or refresh corpora |
| `scripts/run_all_analyses.py` | Analysis JSON |
| `scripts/reporting/` | Templates → `findings/*.md` |
| `data/` | Local corpora (gitignored) + samples/manifests |
| `findings/` | Reports + `findings/data/*.json` |
| `analysis/findings/data/` | Same analysis JSON (machine path) |
| `src/` | Shared loaders (`findings_io`, `cross_platform_sources`, paths) |

See [`scripts/README.md`](scripts/README.md) and [`scripts/reporting/README.md`](scripts/reporting/README.md).

## Setup

```bash
./setup.sh
source venv/bin/activate
# GitHub token recommended — see GITHUB_TOKEN_SETUP.md
python scripts/check_token.py
```

Optional extras: `pip install -e '.[stats,nlp,network]'` (`stats` is scikit-learn for the maintainer-premium logistic).

## Collect data (not in git)

Corpora are local. Samples and manifests stay in the repo.

**Do not `git clean -fdx`** — that deletes ignored dumps. `collect_all.py` skips files that already exist.

```bash
python scripts/collect_all.py            # first time (hours)
python scripts/update_all.py             # later
python scripts/collect_all.py --process  # also clean + enrich
```

Details: [`data/README.md`](data/README.md), [`DATA_SOURCING_AND_REPRODUCIBILITY.md`](DATA_SOURCING_AND_REPRODUCIBILITY.md).

Onboarding checks: `python scripts/validate_setup.py`, `python scripts/workflow.py`.

## Analyze and report

```bash
python scripts/run_all_analyses.py              # all analyses
python scripts/run_all_analyses.py --reports    # + regenerate findings markdown
python scripts/reporting/generate_findings_reports.py   # reports only
```

`--github-only` and `--cross-platform-only` limit the analysis set.

## Data sources (public)

| Channel | Approx. size |
|---------|-------------:|
| GitHub `bitcoin/bitcoin` PRs / issues | 25,122 / 8,890 |
| bitcoin-dev + cryptography ML (deduped) | 51,062 emails |
| IRC `#bitcoin-core-dev` and related | 430,613 messages |
| Delving Bitcoin | 4,662 posts |
| Bitcointalk board 6 | 158,917 posts |

## Related

Some analyses use frameworks from [BCAP](https://github.com/bitcoin-cap/bcap). See [`findings/BCAP_INTEGRATION_REPORT.md`](findings/BCAP_INTEGRATION_REPORT.md).

## License

MIT — see LICENSE.
