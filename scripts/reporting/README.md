# Reporting

One entry point. Templates first. String-built reports only where the JSON is still awkward to template.

```bash
python scripts/reporting/generate_findings_reports.py
# same as: python scripts/run_all_analyses.py --reports
```

## Pipeline

1. `../analysis/governance_frames.py` — compose `governance_frames.json` from existing analysis JSON
2. `generate_cross_platform_reports.py` — four informal-channel reports + header patches
3. `generate_from_templates.py` — render `templates/*.md.tpl` → `findings/*.md`
4. `patch_project_docs.py` — canonical counts / methodology strings on README and methodology docs

## Templates

| Template | Output |
|----------|--------|
| `GOVERNANCE_FRAMES.md.tpl` | `findings/GOVERNANCE_FRAMES.md` |
| `BIP_PROCESS_ANALYSIS.md.tpl` | `findings/BIP_PROCESS_ANALYSIS.md` |
| `CONTRIBUTOR_ANALYSIS.md.tpl` | `findings/CONTRIBUTOR_ANALYSIS.md` |
| `CROSS_REPO_COMPARISON.md.tpl` | `findings/CROSS_REPO_COMPARISON.md` |
| `MERGE_CONCENTRATION_DEPUTIES_REPORT.md.tpl` | `findings/MERGE_CONCENTRATION_DEPUTIES_REPORT.md` |
| `MERGE_PATTERN_BREAKDOWN.md.tpl` | `findings/MERGE_PATTERN_BREAKDOWN.md` |
| `MAINTAINER_PREMIUM_REPORT.md.tpl` | `findings/MAINTAINER_PREMIUM_REPORT.md` |
| `STALLED_PROPOSALS_REPORT.md.tpl` | `findings/STALLED_PROPOSALS_REPORT.md` |
| `TEMPORAL_ANALYSIS_REPORT.md.tpl` | `findings/TEMPORAL_ANALYSIS_REPORT.md` |
| `REVIEW_QUALITY_ENHANCED_ANALYSIS.md.tpl` | `findings/REVIEW_QUALITY_ENHANCED_ANALYSIS.md` |
| `CONFLICT_RESOLUTION_ANALYSIS.md.tpl` | `findings/CONFLICT_RESOLUTION_ANALYSIS.md` |
| `COORDINATION_COSTS_ANALYSIS.md.tpl` | `findings/COORDINATION_COSTS_ANALYSIS.md` |
| `PR_IMPORTANCE_ANALYSIS.md.tpl` | `findings/PR_IMPORTANCE_ANALYSIS.md` |
| `RELEASE_SIGNING_ANALYSIS.md.tpl` | `findings/RELEASE_SIGNING_ANALYSIS.md` |
| `LANGUAGE_EVOLUTION.md.tpl` | `findings/LANGUAGE_EVOLUTION.md` |
| `REJECTION_ANATOMY.md.tpl` | `findings/REJECTION_ANATOMY.md` |
| `STALLED_AGREEMENT_LEDGER.md.tpl` | `findings/STALLED_AGREEMENT_LEDGER.md` |
| `VOCABULARY_AUDIT.md.tpl` | `findings/VOCABULARY_AUDIT.md` |
| `CONTRIBUTOR_CROSS_REF.md.tpl` | `findings/CONTRIBUTOR_CROSS_REF.md` |
| `REVEALED_ROUGH_CONSENSUS.md.tpl` | `findings/REVEALED_ROUGH_CONSENSUS.md` |
| `INGROUP_REVIEW_TREATMENT.md.tpl` | `findings/INGROUP_REVIEW_TREATMENT.md` |
| `NEWCOMER_BAR.md.tpl` | `findings/NEWCOMER_BAR.md` |
| `COMMONS_MECHANISMS.md.tpl` | `findings/COMMONS_MECHANISMS.md` |
| `FIRST_YEAR_TRAJECTORY.md.tpl` | `findings/FIRST_YEAR_TRAJECTORY.md` |
| `GAP_CLOSURE.md.tpl` | `findings/GAP_CLOSURE.md` |
| `INTERDISCIPLINARY_ANALYSIS_REPORT.md.tpl` | `findings/INTERDISCIPLINARY_ANALYSIS_REPORT.md` |
| `NOVEL_INTERPRETATIONS.md.tpl` | `findings/NOVEL_INTERPRETATIONS.md` |
| `GINI_COEFFICIENT_EXPLANATION.md.tpl` | `findings/GINI_COEFFICIENT_EXPLANATION.md` |

Engine: `template_engine.py` — `{{path.to.value|pct}}`, `{% for item in path %}`, `{% for key, value in path.items %}`.

Context builders live in `generate_from_templates.py` (`ctx_*`). Add a new report by: write JSON from an analysis script → add `ctx_*` + `.tpl` → append a job in `generate_all()`.

## Still string-built (not templates)

`generate_cross_platform_reports.py` writes:

- `CROSS_PLATFORM_NETWORKS.md`
- `INFORMAL_SENTIMENT_ANALYSIS.md`
- `ENHANCED_FUNDING_ANALYSIS_REPORT.md`
- `BCAP_INTEGRATION_REPORT.md`

Hand-edited (patched, not regenerated): `EXECUTIVE_SUMMARY.md`, Satoshi reports, methodology, glossary. `GOVERNANCE_FRAMES.md.tpl` section 5 is static text; the four frames above it are filled from JSON.

## JSON locations

Analyses write via `src/utils/findings_io.py` to both:

- `analysis/findings/data/` — machine output
- `findings/data/` — same payload, next to the markdown
