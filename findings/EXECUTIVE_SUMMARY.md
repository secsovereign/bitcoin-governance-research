# Bitcoin Core Governance Analysis

**25,122 PRs | 8,890 Issues | 51,062 Emails (2 ML lists) | 430,613 IRC | 4,662 Delving | 158,917 Bitcointalk | 339 Releases | 2010-2026**

**Last Updated**: 2026-10-07 (measurement passes below; informal-channel counts unchanged)
**Methodology**: Quality-weighted review counting (GitHub, ACK, IRC, combined mailing lists, Delving, Bitcointalk), cross-platform integrated, PR importance classification, timeline-aware ACK handling, MAX per reviewer. July 2026 addendum: repaired maintainer tags, fair identity-vs-merits controls, stalled-proposal dossiers (see below).

**External Research**: This analysis extends and quantifies findings from BitMEX Research (2018), Angela Walch (2015-2021), Stanford JBLP (2024), and academic governance studies. See `EXTERNAL_RESEARCH_COMPARISON.md` for detailed comparison. Some analyses apply frameworks from [BCAP (Bitcoin Consensus Analysis Project)](https://github.com/bitcoin-cap/bcap) - see `BCAP_INTEGRATION_REPORT.md` for details.

---

## The Contradiction

**Bitcoin was designed to eliminate trusted third parties. Its reference implementation is controlled by them.**

Bitcoin Core is the reference implementation that most Bitcoin nodes run. Changes to Bitcoin Core can affect the entire Bitcoin network. Yet governance of Bitcoin Core violates Bitcoin's core principles: trust minimization, decentralization, and censorship resistance.

**Historical Context**: Analysis of 549 Satoshi Nakamoto communications (2008-2015) reveals that Satoshi emphasized decentralization and trust minimization, preferred informal consensus mechanisms, and did not establish formal governance structures. Current Bitcoin Core governance diverges from these principles. See `SATOSHI_GOVERNANCE_INSIGHTS.md` for detailed analysis.

---

## How to cut this corpus

All-time rates mix eras and channels. Read `GOVERNANCE_FRAMES.md` before quoting them.

1. **Agenda-setting vs decision, by era.** Informal talk *before* a PR exists is a 2015–2021 IRC/email pattern (flow ~0.55–0.57). 2022+ Delving/IRC volume is mostly commentary on already-opened PRs (flow 0.002).
2. **Funnel / deputy graph is the informal org chart.** `MAINTAINERS` is a roster. 2022+: `fanquake` ~50% of merges; top-3 ~83%.
3. **Power is not portable.** BIP-repo top-10 ∩ Core top-10 is two people (`sipa`, `achow101`). Activity on BIPs/Delving/lists does not imply Core merge keys.
4. **Exit is selection, not collapse.** 90.7% of 7,827 contributors are inactive at 1 year (725 still active, window frozen to last GitHub event in the dump). Participants and one-timers leave; the continuing set is small and already inside the merge graph.

---

## The Numbers: What They Mean

### Power Concentration = Single Points of Failure

**Canonical roster**: 22 GitHub logins (`data/maintainers/canonical_maintainers.json`). That is 21 humans: `TheCharlatan` and `sedited` are the same person after a GitHub rename. Merge stats in this dump use `sedited` (0 `TheCharlatan` merges).  
**Merge keys ≠ roster.** Only 23 GitHub logins appear as `merged_by`. Everyone else **cannot merge** — a zero as merger is lack of keys, not unused privilege. Reviewer/ACK is not merge authority. Non-maintainer “merge rate” is author-success (a key holder merged their PR). See `GLOSSARY_AND_CONTEXT.md` and `data/maintainers/merge_capability.json`.  
**Current merge-key users** (merged since 2023): fanquake, achow101, sedited, glozow, ryanofsky, hebasto, maflcko.  
**Historical**: laanwj, sipa, maflcko, and others with no recent merges. See `MAINTAINER_LIST_SOURCE.md`.  
**Top 3 control 81.1% of all merges** (laanwj 34.8%, fanquake 25.8%, maflcko 20.5%) — all-time.  
**Modern window (2022+):** `fanquake` alone merges **~50.4%**; top-2 **~71%**; top-3 **~83%** (`MERGE_CONCENTRATION_DEPUTIES_REPORT.md`).  
**Top 10 authorship share: 42.7% historical → 47.8% recent** (authorship concentrating). Merge keys stay tight: top-3 merge share ~81% in both periods (`GINI_COEFFICIENT_EXPLANATION.md`).

**Security implication**: If the top 3 are compromised, they could introduce malicious code affecting the entire Bitcoin network. This is a **single point of failure** in a system designed to have none. The modern picture is thinner still: one lead merger handles about half of recent merges.

**Gini (say which one):** authorship 0.851 historical / 0.834 recent; merge-authority 0.623 / 0.667. US income Gini is ~0.49. Do not cite 0.851 as “the” Gini.

**Voting blocs:** high-cohesion pairs exist but **n is tiny** (often 3–7 joint appearances). Conflict-PR cohesion 77.8% (10 pairs) vs non-conflict 100% (38) — treat as suggestive, not a voting machine. See `CONFLICT_RESOLUTION_ANALYSIS.md`.

### Arbitrary Authority = No Accountability

**25.5% self-merge rate** (2,501 of 9,793 maintainer-merged PRs).  
**45.1% of self-merges have zero reviews** (1,129 PRs, 11.6% of all maintainer-merged PRs).  
**Written rule, no numeric minimum.** `CONTRIBUTING.md` puts merge with merge maintainers, who judge contributor consensus and may weigh reviewers by merit. Observed review counts still run from 0 to 14+. Cite 2022+ as the current process bar. Pre-2016 GitHub Review objects are missing from this dump. See `REVEALED_ROUGH_CONSENSUS.md`.

**Security implication**: A merge-key holder can merge their own code with zero GitHub Review objects. The written rule does not set a minimum. What that judgment looked like is in `REVEALED_ROUGH_CONSENSUS.md`.

**PR type breakdown**: Even "trivial" housekeeping PRs have **36.4% zero-review rate** (928 of 2,547). Critical PRs fare better at 23.2%, but the pattern holds: no minimum review requirements regardless of PR importance.

**Variation**: laanwj self-merges 77.1% of his PRs. 7 maintainers self-merge 0%. No standard, just discretion.

### Exclusive Privilege = Structural Inequality

**Maintainers: 25.5% of their merged PRs are self-merged.**  
**Non-maintainers: 0% can self-merge** (not permitted).  
**Maintainer reviews carry 5.5x more weight** than non-maintainer reviews.

**Response time inequality: 1.41x** - Non-maintainers wait 41% longer to merge (145.4h vs 93.3h median). First review times are nearly equal (12.3h vs 12.4h), but merge decisions favor maintainers. **Implication**: No bias in initial review, but maintainer privilege in merge decisions.

**Identity vs merits (fair reading, July 2026 — `MAINTAINER_PREMIUM_REPORT.md`):**
- Raw merge rates (~80% maint / ~55% non) are **mostly self-merge privilege**. Peer-merge (self-merge ≠ success): ~59% / ~54% all-time; gap wider since 2022 (~63% / ~51%).
- **Do not** treat prior author merges as pure “PR merits” — that is reputation/access. Without that control, maintainer authorship multiplies merge odds ~3.6× all-time / ~5× since 2022.
- **Cold start:** first-PR outsiders merge **~29%** all-time → **~16%** since 2022.
- **Established outsiders** (prior ≥5 merges / top-volume authors) merge ~67–71% — ordinary work is not broadly blocked.
- **Large outsider PRs almost never land** (closed ≥2k LOC: ~8% all-time / ~4% since 2022; ≥5k LOC since 2022: ~1%).
- **Author-prep matched (not “quality”):** body + test paths only — mean prep equal/higher for outsiders; high band (≥0.65) still **~76% vs ~59%** all-time (~17 pp) and **~78% vs ~58%** since 2022 (~20 pp). Size-substance and review engagement are **not** quality.
- **Path risk:** on consensus-sensitive paths, outsider merge drops to **~35%** vs maintainer **~73%** (all-time) — sharper than the average gap. Concept/approach ACK received narrows the gap (~11 pp) but does not erase it.
- **High-prep closed outsiders (n=100 sample):** ~45% never received a formal review — non-engagement dominates; CI data unavailable on corpus.

**Structural problem**: There's a **power asymmetry**. Some people have exclusive privileges (self-merge, weighted reviews) that others don't. This creates a **hierarchical structure**: Maintainers with exclusive rights, contributors without them, outsiders with uncertain path forward — especially on first PR and large/novel changes.

**Cross-status reviews**: Only 72% of maintainer PRs receive non-maintainer reviews (recent period). 28% are reviewed only by other maintainers - **segregation**.

### Process vs Structure: The Efficiency Trap

**Process improvements** (2012-2020 → 2021-2025):
- Zero-review merges: 30.3% → 3.3% (89.1% reduction) ✅
- Response time: 30.6 → 8.1 hours (73% faster) ✅
- Cross-status reviews: 50% → 72% (more integration) ✅

**By PR type** (all time):
- Trivial PRs: 36.4% zero-review (housekeeping doesn't excuse lack of review)
- Low importance: 31.5% zero-review
- Critical PRs: 23.2% zero-review (better, but still high)

**Structural persistence**:
- Self-merge rate: 25.5% (still concentrated privilege) ❌
- Top 10 authorship: 42.7% → 47.8% (worse) ❌
- Review weight bias: 5.5:1 (unchanged) ❌
- Authorship Gini: 0.851 → 0.834 (still extreme) ❌
- Top-3 merge share ~81% in both historical and recent windows ❌

**The pattern**: The **workflow got efficient**. The **power structure didn't change**. Concentrated authority got better at processing PRs, but concentration remains.

**Coordination costs**: Average **20.1 messages** per PR (reviews + comments; 15,884 PRs with file data). Load scales **4.3×** from low- to high-complexity (13.6 → 58.3 msgs). See `COORDINATION_COSTS_ANALYSIS.md`.

---

## Security Implications

### 1. Protocol Control Risk

**Bitcoin Core controls Bitcoin's protocol evolution.** Most nodes run Bitcoin Core. Changes to Bitcoin Core can:
- Introduce consensus bugs
- Change economic incentives
- Add surveillance features
- Implement censorship mechanisms
- Create network splits

**11.6% of maintainer-merged PRs are zero-review self-merges** — potential security risk. No review means no detection of malicious code.

**2,671 conflicts** across 20,166 PRs (13.2%). Average resolution 132.2 days. 2026 days are right-censored (year not complete). Pair-level “blocs” have small n. See `CONFLICT_RESOLUTION_ANALYSIS.md`.

### 2. Single Points of Failure

**Top 3 control 81.1% of merges** - if compromised, could affect entire network.  
**No public recourse procedure is in this corpus** if a key holder merges code others oppose.  
**The written rule sets no numeric review minimum.** See `REVEALED_ROUGH_CONSENSUS.md`.

### 3. Trust Minimization Violation

**Bitcoin's principle**: Eliminate trusted third parties.  
**Bitcoin Core's reality**: 23 unique GitHub logins have merge keys; most people in this corpus cannot merge. Top 3 control 81.1% of merges.  
**The contradiction**: Bitcoin removes trust from money, but requires trust in Bitcoin Core governance (concentrated merge authority).

### 4. Economic Capture Risk

**Unknown funding sources**: Who funds the top 3 controlling 81.1% of merges?  
**Data limitation**: Only 1-2% of PRs mention funding. Most is invisible.  
**Risk**: State actors, corporations, or other interests could fund maintainers to influence Bitcoin.

---

## The Long-Term Problem

**Massive Contributor Churn**: 90.7% of 7,827 contributors have no activity in 1 year (window = last GitHub event in the dump). Only 725 remain active. 42.2% contributed once. Even high-quality authors (50%+ merge rate) exit at 83.0%. Read as **selection into a thin continuing set**, not collapse — participants-only exit 95.3%; established authors 58.1%; maintainers among that set 23.8%. See `GOVERNANCE_FRAMES.md` and `CONTRIBUTOR_ANALYSIS.md`.

**Power Calcification**: Top-10 authorship 42.7% → 47.8%. Authorship Gini 0.851 → 0.834 (still extreme). Self-merge 25.5%. Top-3 merge share stays ~81%. Power is **not distributing**. See `GOVERNANCE_FRAMES.md`.

**No path to keys in this corpus**: Non-maintainers: 0% self-merge (not permitted). `CONTRIBUTING.md` governs how a key holder judges consensus. It does not say who receives keys. See `GLOSSARY_AND_CONTEXT.md`.

**Stalled feature-scale work (`STALLED_PROPOSALS_REPORT.md`)**: Dandelion’s Core implementation PR closed unmerged. Full Erlay protocol: **0/7** matched PRs merged (scaffolding/signaling merges ≠ delivery). Package relay shows multi-year lifetimes. Closed-unmerged is often non-engagement (~⅔ of non-maintainer closes have zero reviews) — not interchangeable with “NACK’d” — but the named full-protocol stalls remain.

---

## Later measurements

Fit 2010–2023, confirm 2024–2026. Year is a control. These reports do not refit the rates above.

- **Universal tightening is not supported.** The decided merge-rate slope’s interval covers zero. The newcomer merge slope is negative. `NEWCOMER_BAR.md`
- **In-group is the time-varying top reviewers, not the merge-key set.** Decided in-group pull requests merge higher and go unanswered less often. The fingerprint is mixed. It is not a diagnosis. `INGROUP_REVIEW_TREATMENT.md`
- **What merge looked like** under `CONTRIBUTING.md` is ACK/NACK plus observed discussion. A mention is not an ACK. `REVEALED_ROUGH_CONSENSUS.md`
- **Six attention effects clear on Bitcoin Core.** Comparison dumps lack review objects, so those effects cannot be placed against other repositories’ health. `COMMONS_MECHANISMS.md`
- **The first-year merge gap is not closed by patch content.** Of 1,740 training leavers, 340 match later entrants on patch content and score lower on social legibility. That set is spread across entry years (STRUCTURAL). Newcomer silence is not explained by a shift into subsystems with fewer reviewers. `FIRST_YEAR_TRAJECTORY.md`, `GAP_CLOSURE.md`
- **Conflict-resolution score (P6)** is the only positive lag with later health that clears the joint threshold, on 13 years, low power. Sanctions (P5) and organizing rights (P7) are unscored. `GAP_CLOSURE.md`

---

## The Bottom Line

**Bitcoin Core improved how decisions get made. Not who makes them.**

The oligarchy got more efficient. It's still an oligarchy.

**The question isn't whether the masters do good work.**  
**The question is why masters exist at all.**

Bitcoin was designed to eliminate trusted intermediaries. Its reference implementation is controlled by them. This is the **fundamental contradiction** at the heart of Bitcoin Core governance.

---

## Data Sources

**25,122 PRs** (GitHub) - Formal decisions, review patterns, merge authority  
**8,890 Issues** (GitHub) - Discussions, problem-solving, coordination  
**51,062 Emails** (bitcoin-dev + cryptography ML, deduped) - Consensus-building, rationale  
**430,613 IRC Messages** - Real-time coordination, informal decision-making  
**4,662 Delving posts** - Modern spec/governance forum (2023+)  
**158,917 Bitcointalk posts** (board 6) - Historical public forum discourse  
**339 Releases** - Protocol evolution, release signing authority

**Total**: 1+ million GitHub/informal data points across 16+ years, synthesized to reveal governance patterns.

---

**Core Reports**: See `README.md` for full navigation

**Essential Reading**:
- `GOVERNANCE_FRAMES.md` - How to cut this corpus (era / funnel / identity / exit)
- `MERGE_PATTERN_BREAKDOWN.md` - Detailed merge analysis
- `MAINTAINER_PREMIUM_REPORT.md` - Identity vs merits (fair controls + quality matching)
- `MERGE_CONCENTRATION_DEPUTIES_REPORT.md` - Modern merger share / funnels
- `STALLED_PROPOSALS_REPORT.md` - Dandelion / Erlay / related case dossiers
- `REVEALED_ROUGH_CONSENSUS.md` - what `CONTRIBUTING.md` judgment looked like
- `NEWCOMER_BAR.md` - who the merge slope moved against
- `INGROUP_REVIEW_TREATMENT.md` - top-reviewer treatment gap
- `COMMONS_MECHANISMS.md` - six attention effects and the shared-indicator rank
- `FIRST_YEAR_TRAJECTORY.md` - first-year merge gap and the silence slope
- `GAP_CLOSURE.md` - lagged principle scores, false-negative timeline, subsystem silence
- `TEMPORAL_ANALYSIS_REPORT.md` - Temporal patterns
- `NOVEL_INTERPRETATIONS.md` - Novel insights
- `INTERDISCIPLINARY_ANALYSIS_REPORT.md` - Multi-disciplinary analysis
- `GLOSSARY_AND_CONTEXT.md` - Terminology for non-experts
