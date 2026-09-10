# Scripts

```
collect  →  analyze  →  report
```

| Command | What |
|---------|------|
| `python scripts/collect_all.py` | First-time corpora (hours). Skips dumps that already exist. |
| `python scripts/update_all.py` | Incremental refresh (does not wipe existing files) |
| `python scripts/run_all_analyses.py` | Analysis JSON |
| `python scripts/run_all_analyses.py --reports` | Analyses + findings markdown |
| `python scripts/reporting/generate_findings_reports.py` | Reports only (JSON already exists) |

Flags on the analysis runner: `--github-only`, `--cross-platform-only`.

## Layout

| Dir | Role |
|-----|------|
| `data_collection/` | Collectors invoked by collect/update |
| `data_processing/` | `clean_data.py`, `enrich_data.py`, `maintainer_timeline.py` |
| `analysis/` | One script per analysis JSON |
| `reporting/` | Templates + report orchestrator — see `reporting/README.md` |
| `validation/` | Dataset / methodology checks |

Onboarding helpers at this level: `workflow.py`, `validate_setup.py`, `check_token.py`, `test_minimal_collection.py`.
