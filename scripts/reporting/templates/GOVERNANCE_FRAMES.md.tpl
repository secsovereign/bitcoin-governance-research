# How to cut this corpus

**Date**: {{generated_date}}  
**Machine-readable**: `analysis/findings/data/governance_frames.json`  
**Use this before quoting all-time rates.**

Four frames. Each one changes what you would cite. Section 5 is the later measurement passes.

---

## 1. Agenda-setting vs decision (by era)

Informal channels put topics on the table. GitHub finalizes. Those are different jobs, and they swapped venues.

| Era | GitHub PRs | IRC mentions | Email | Delving | Bitcointalk | Discussed *before* PR | Flow |
|-----|-----------:|-------------:|------:|--------:|------------:|----------------------:|-----:|
{% for item in eras %}
| {{item.label}} | {{item.github_prs|int}} | {{item.prs_mentioned_in_irc|int}} | {{item.prs_mentioned_in_email|int}} | {{item.prs_mentioned_in_delving|int}} | {{item.prs_mentioned_in_bitcointalk|int}} | {{item.prs_discussed_before_github|int}} | {{item.flow_rate|round3}} |
{% endfor %}

All-time flow is **{{agenda_setting.all_time_flow_rate|round3}}** ({{agenda_setting.prs_discussed_before_github|int}} PRs discussed off-GitHub first). That average is almost entirely **2015–2021 IRC/email**. 2022+ Delving and IRC are loud and almost never first.

**Cite as**: which era, which channel, before or after the PR number existed.  
**Do not cite**: “the community decided on Delving” as if that were SegWit-style agenda-setting.

Detail: `CROSS_PLATFORM_NETWORKS.md`

---

## 2. Funnel / deputy graph as the informal org chart

`MAINTAINERS` is a roster. The merge graph is the org chart.

**2022+** ({{informal_org_chart.n_merged_prs|int}} merged PRs):

| Metric | Value |
|--------|------:|
| Top merger | `{{informal_org_chart.top_merger}}` |
| Top-1 share | {{informal_org_chart.top1_share|pct}} |
| Top-2 | {{informal_org_chart.top2_share|pct}} |
| Top-3 | {{informal_org_chart.top3_share|pct}} |

**Top 5 mergers**
{% for key, value in informal_org_chart.top5_mergers.items %}
- {{key}}: {{value|int}}
{% endfor %}

**Author funnels** (≥40% of an author’s merges through `{{informal_org_chart.top_merger}}`)
{% for item in informal_org_chart.funnels %}
- {{item.author}}: {{item.count|int}} / {{item.author_total|int}} ({{item.pct|round1}}%)
{% endfor %}

**Recurring co-reviewers on those merges** (observational, not formal deputies)
{% for key, value in informal_org_chart.coreviewers.items %}
- {{key}}: {{value|int}}
{% endfor %}

Self-merge among maintainer-authored merges (all-time): {{informal_org_chart.self_merge_rate|pct}}.

**Cite as**: who the current filter is, and which authors funnel through them.  
**Do not cite**: all-time laanwj share as the present picture.  
**Do not cite**: a reviewer’s 0 merges as unused privilege. They cannot merge unless they appear as GitHub `merged_by`.

Detail: `MERGE_CONCENTRATION_DEPUTIES_REPORT.md`, `MERGE_PATTERN_BREAKDOWN.md`

---

## 3. Multiplex identity — power is not portable

The unit is **person-in-channel**, not a login.

| | BIP repo | Bitcoin Core |
|--|----------|--------------|
| Unique mergers | {{multiplex_identity.bip_unique_mergers|int}} | {{multiplex_identity.core_unique_mergers|int}} |
| Top-3 merge share | {{multiplex_identity.bip_top3_share|pct}} | {{multiplex_identity.core_top3_share|pct}} |
| Top-10 overlap | {{multiplex_identity.overlap_count|int}} people ({{multiplex_identity.overlap_rate|pct}}) | |

Only {{overlap_joined}} sit in both top 10s.

BIP top 10: {{bip_top10_joined}}  
Core top 10: {{core_top10_joined}}

Cross-platform exact username overlap is a lower bound: GitHub–Delving {{multiplex_identity.github_delving_overlap|int}}, GitHub–Bitcointalk {{multiplex_identity.github_bitcointalk_overlap|int}}, verified aliases {{multiplex_identity.verified_aliases|int}}. High informal activity without Core merge keys is common (Delving-only names include people who *are* Core-adjacent on GitHub under a different handle — treat the “only” lists as unmatched strings, not proof of absence).

**Cite as**: activity on BIPs / Delving / lists does not imply Core merge authority.  
**Do not cite**: a BIP champion as a Core decision-maker without the merge graph.

Detail: `CROSS_REPO_COMPARISON.md`, `BIP_PROCESS_ANALYSIS.md`

---

## 4. Exit as selection, not collapse

**{{exit_as_selection.exit_rate_1yr|pct}}** of {{exit_as_selection.total_contributors|int}} contributors have no activity in 365 days ({{exit_as_selection.active_1yr|int}} still active). That headline is true and misleading until split:

| Segment | n | 1-year exit |
|---------|--:|------------:|
| All contributors | {{exit_as_selection.total_contributors|int}} | {{exit_as_selection.exit_rate_1yr|pct}} |
| Participants only (never authored a PR) | {{exit_as_selection.participants_total|int}} | {{exit_as_selection.participants_exit|pct}} |
| One-time (exactly 1 activity) | — | {{exit_as_selection.one_time_exit|pct}} ({{exit_as_selection.one_time_share|pct}} of all) |
| PR authors | {{exit_as_selection.authors_total|int}} | {{exit_as_selection.authors_exit|pct}} |
| High-quality authors (50%+ merge) | {{exit_as_selection.high_quality_authors|int}} | {{exit_as_selection.high_quality_exit|pct}} |
| Established authors (5+ authored PRs a key holder merged) | {{exit_as_selection.established_total|int}} | {{exit_as_selection.established_exit|pct}} |
| … of whom maintainers | — | {{exit_as_selection.established_maint_exit|pct}} |
| … of whom non-maintainers | — | {{exit_as_selection.established_non_exit|pct}} |

The process keeps a small continuing set. High merge-rate authors still leave at {{exit_as_selection.high_quality_exit|pct}} — quality does not retain. Maintainers among the established set leave much less.

**Cite as**: selection into a thin continuing core.  
**Do not cite**: 91% exit as “the project is dying.”

Detail: `CONTRIBUTOR_ANALYSIS.md`

---

## 5. Later measurements

These sit beside the four frames. Year is a control in the models. Do not read a year slope as evidence the whole project tightened.

- Cite 2022+ for the current merge bar. Compare before 2016 and 2016+ on observed discussion. Pre-2016 GitHub Review objects are missing. `REVEALED_ROUGH_CONSENSUS.md`
- The decided merge-rate slope’s interval covers zero. The newcomer slope is negative. `NEWCOMER_BAR.md`
- In-group is the time-varying top reviewers, not the merge-key set. `INGROUP_REVIEW_TREATMENT.md`
- Six attention effects clear on Bitcoin Core. Comparison dumps cannot host them. `COMMONS_MECHANISMS.md`
- Patch content does not close the first-year merge gap. The 340 content-matched leavers are spread across entry years. Newcomer silence is not a shift into quieter subsystems. `FIRST_YEAR_TRAJECTORY.md`, `GAP_CLOSURE.md`

---

## Reproduce

```bash
venv/bin/python scripts/analysis/governance_frames.py
venv/bin/python scripts/reporting/generate_from_templates.py
```

**Generated by**: `scripts/reporting/generate_from_templates.py`
