# Architectural Divergence: Bitcoin Core vs Bitcoin Commons

## Single final report

**Status:** FINAL  
**Date:** 2026-07-12  
**Corpus:** 16,653 merged Bitcoin Core PRs · Bitcoin Commons at `/home/user/src/btc-commons`  
**Plan:** `/home/user/src/btc-commons/docs/ARCHITECTURAL_DIVERGENCE_PLAN.md`  
**Machine-readable audit:** `findings/data/validation_recompute_audit.json`

This document is the **sole narrative deliverable**. It merges findings, methodology, validation, citation checks, exemplars, limitations, and reproducibility.

**Corrections incorporated (still FINAL):** (1) tightened `debt_compensation` / `test_ci_build` rules + round-2 stratified validation; (2) Quarkslab primary-source characterization; (3) consensus rule count resolved at **159**.

---

# Part I — Bottom line

Bitcoin Core’s 16-year merged-PR history is **maintenance-heavy**, with a smaller **architectural debt-tax** slice that is real but classifier-sensitive. Bitcoin Commons encodes a **different design strategy**—formal rule register, spec-lock, layered crates, process-isolated modules—measured statically, not by PR velocity.

| Keep these separate | Value |
|---------------------|------:|
| Architectural debt tax (`debt_compensation`) | **1.70%** of merged PRs |
| Total maintenance (debt + deps + test/CI/build) | **39.79%** |
| Net-new capability (feature + consensus + net + RPC) | **16.23%** |
| Structural (`refactor`) | **8.82%** |
| Other (wallet / GUI / policy / backports …) | **22.87%** |
| Documentation | **12.29%** |

| Trust ranking for peer review | |
|-------------------------------|--|
| **Strong** | Maintenance % (~40%), net-new %, RPC file-debt hotspot, Commons posture counts, round-2 `test_ci_build` agreement |
| **Directional** | Debt tax 1.70% (improved precision vs prior 6.14%; round-2 debt agreement 75%) |
| **Reject** | “Commons has lower `debt_score` than Core”; “Commons is N× faster to ship”; freezing a Knots % without a date |

**Material headline shift vs pre-tighten FINAL numbers:** debt tax **6.14% → 1.70%** (−4.44 pp); total maintenance **44.33% → 39.79%** (−4.54 pp). Net-new stayed stable (**16.07% → 16.23%**, +0.16 pp). The maintenance drop is almost entirely false-positive debt reclassified into refactor/docs/other/test—not a change in Core’s test/CI volume.

**RPC hotspot (chrono-sorted turnover, same 16,653 PRs):** avg debt **52.62** · high-debt files **62.13%** · patch:refactor **3.737**.

**Commons posture:** **159** consensus rules · **251** production `#[spec_locked]` · **8** `module.toml` · transports Iroh / TCP / Dandelion / Erlay.

**Net-new is robust:** only 80 merged PRs carry GitHub `Feature`; forcing them into net-new moves 16.23% by at most **+0.21 pp**.

---

# Part II — How to read this (hostile-reviewer frame)

This is **not** a head-to-head velocity contest. Two questions, two instruments:

| Question | Instrument | Unit |
|----------|------------|------|
| What did Core’s merged work consist of over ~16 years? | PR architectural classification + file turnover debt scores | Share of merged PRs; debt score 0–100; patch:refactor |
| What design posture does Commons encode in-tree *today*? | Static codebase / manifest metrics | Rule counts; `#[spec_locked]`; LOC; module manifests; transport presence |

**Defensible claim:** Core’s long-run merged bandwidth and file-churn show heavy maintenance and a high-debt RPC surface; Commons’ tree encodes formal rules, spec-lock, and process-isolated extension—a different *architectural strategy* for consensus-critical monetary software.

**Indefensible claim:** “Commons has lower technical debt than Core” via applying Core’s patch-frequency formula to Commons LOC. This study **never** computes Commons `debt_score`.

---

# Part III — Findings

## 1. PR classification

### 1.1 Category distribution (recomputed from `pr_architectural_classification.jsonl`)

| Primary | Count | % |
|---------|------:|--:|
| test_ci_build | 5,782 | 34.72 |
| other | 3,809 | 22.87 |
| documentation | 2,047 | 12.29 |
| refactor | 1,469 | 8.82 |
| networking_change | 1,008 | 6.05 |
| rpc_change | 964 | 5.79 |
| consensus_change | 619 | 3.72 |
| dependency_maintenance | 561 | 3.37 |
| debt_compensation | 283 | 1.70 |
| new_feature | 111 | 0.67 |
| **Total** | **16,653** | **100** |

Ambiguous after Tier 3: **1,459 / 16,653 = 8.76%** (gate &lt;10%).

`new_feature` as primary is rare by design: capability often lands in `rpc_change` / `networking_change` / wallet→`other`. Use the **net-new aggregate (16.23%)**, not the 0.67% primary alone.

### 1.2 Headline aggregates

```
architectural_debt_tax   = debt_compensation
total_maintenance_burden = debt_compensation + dependency_maintenance + test_ci_build
structural_work          = refactor
net_new_capability       = new_feature + consensus_change + networking_change + rpc_change
```

`debt_compensation` and `dependency_maintenance` stay separate: subtree bumps are maintenance, not architecture workarounds.

### 1.3 Ambiguity audit

| Among ambiguous (n=1,459) | Share |
|---------------------------|------:|
| Machine primary = `other` | **43.80%** |
| Net-new aggregate | 33.17% |
| Maintenance aggregate | 12.95% |
| Machine primary = `debt_compensation` | **2.67%** |

**Bias finding (post-tighten):** ambiguous cases are no longer debt-enriched (was 29% debt pre-tighten). Residual ambiguity concentrates in `other` and net-new border cases. Main remaining risk for debt tax is **recall** (true debt missed), not false-positive inflation.

### 1.4 Feature-label sensitivity

| Destination of `Feature`-labeled merged PRs (n=80) | Count |
|----------------------------------------------------|------:|
| other | 22 |
| rpc_change | 14 |
| new_feature | 14 |
| networking_change | 13 |
| test_ci_build | 8 |
| consensus_change | 4 |
| dependency_maintenance | 2 |
| debt_compensation | 2 |
| refactor | 1 |

| Sensitivity | Net-new % | Δ |
|-------------|----------:|--:|
| Baseline | 16.23 | — |
| A: force all Feature outside net-new into net-new | 16.44 | +0.21 pp |

### 1.5 Stratified human validation

#### Round 1 (pre-tighten; seed 42)

| Metric | Value |
|--------|------:|
| Sample | 50 (5×10 categories) |
| Agreement with machine primary | **68%** (34/50) |
| Strong | refactor, networking, dependency_maintenance, other (5/5) |
| Weak | debt_compensation (**1/5**), test_ci_build (**1/5**), consensus_change (2/5) |

Round-1 debt false positives included copyright bumps, blocksdir XOR (feature), 32-bit large-file portability, and appveyor clcache (CI). Round-1 test_ci false positives included USE_SSL cleanup, multiprocess IPC feature, HexStr optimize, and policy TX_MAX.

Artifact: `findings/data/stratified_validation_sample.json`.

#### Round 2 (post-tighten; seed 99; focus categories)

| Metric | Value |
|--------|------:|
| Sample | **40** (20 `debt_compensation` + 20 `test_ci_build`) |
| `debt_compensation` agreement | **75%** (15/20) — was 20% |
| `test_ci_build` agreement | **95%** (19/20) — was 20% |
| Combined focus agreement | **85%** (34/40) |

**Rule tighten (summary):** Block storage / UTXO labels no longer auto-map to debt; copyright → docs; CI tooling → test_ci; no soft debt-join without a debt signal; strong vs weak debt keywords (bare `cs_main` / body-only `ibd` / enrich `performance` alone do not gate debt_join); `refactor:` title wins unless strong debt; `qa:` / benchmark / makefile / build-parallel overrides; Docs “Document …” → documentation; Tests+test title → test_ci.

**Headline impact:** maintenance **−4.54 pp** (material). Report uses post-tighten figures throughout Part I–III.

Artifact: `findings/data/stratified_validation_sample_round2.json`.

### 1.6 Temporal trends (Core only)

| Era | Years | N | Debt tax % | Maintenance % | Net-new % | Structural % |
|-----|-------|--:|----------:|--------------:|----------:|-------------:|
| early | 2010–2013 | 1,595 | 3.57 | 17.55 | 25.71 | 4.14 |
| growth | 2014–2017 | 4,026 | 2.73 | 29.73 | 19.70 | 9.61 |
| professionalization | 2018–2021 | 5,482 | 0.88 | 41.99 | 14.90 | 9.83 |
| recent | 2022– | 5,550 | 1.23 | 51.30 | 12.29 | 8.59 |

Debt tax remains low after tighten; maintenance **rose** across eras (mostly test/CI/build). That is a process-volume story, not proof hot files healed—RPC/validation debt scores remain high. Growth-era net-new was **19.70%**; early-era net-new peaked at **25.71%** under the tightened classifier.

Yearly series: `findings/data/velocity_differential.json`.

---

## 2. Architectural comparison

### 2.1 What each column measures

| Column | Measures | Does not measure |
|--------|----------|------------------|
| Commons evidence | Present-day design artifacts | Historical maintenance cost; future debt; throughput |
| Core PR proxy % | Share of merged PRs matching dimension queries | Whether Commons “eliminates” that PR mass |

Proxies are **attention shares**, not feature-parity proofs.

### 2.2 Dimension table

| Dimension | Commons evidence (static) | Core PR proxy |
|-----------|---------------------------|---------------|
| Formal spec | `CONSENSUS_SPEC.md` — **159** rules | **4.01%** (668 PRs) |
| Spec lock / Z3 | **251** production locked fns | **No Core equivalent** |
| Pure Rust secp256k1 | `blvm-secp256k1/` (~25.6k LOC) | **3.37%** (561) |
| UTXO commitments | protocol utxo_commitments (~2.8k LOC) | **2.18%** (363) |
| Parallel IBD | `parallel_ibd/` — **12,850** LOC | **4.60%** (766) |
| Multi-transport P2P | Iroh / TCP / Dandelion / Erlay | **6.76%** (1,125) |
| Module extension | process + WASM; **8** `module.toml`; **7** satellites | **8.14%** (1,355) |
| Selective sync | `blvm-selective-sync/` | **No Core equivalent** |
| Differential testing | `blvm-bench/` (~32.8k LOC) | **41.65%** (6,936) |
| Layered crates | Six-tier stack | Cross-cutting ≥3 subsystems **12.24%** (2,038) |

### 2.3 Why side-by-side is still meaningful

1. Object of study = **architectural strategy**, not one scalar debt index.  
2. Core’s only long-history instrument = PR/file churn; Commons’ honest instrument today = static posture.  
3. Rows pair **problem class → response type**.  
4. We refuse computing Commons `debt_score` from LOC or age.

For a paper figure: qualitative presence/absence (e.g. spec-lock yes/no) plus **separate** Core-only quantitative panels—not a blended index.

---

## 3. Subsystem debt vs Commons layers

### 3.1 Core turnover (chrono-sorted; 16,653 merged PRs)

| Subsystem | Files | Avg debt | High-debt % | Patch:refactor |
|-----------|------:|---------:|------------:|---------------:|
| rpc | 235 | **52.62** | **62.13** | **3.737** |
| script | 82 | 47.22 | 45.12 | 3.171 |
| consensus | 39 | 43.53 | 38.46 | 1.012 |
| wallet | 271 | 42.55 | 33.58 | **5.885** |
| network | 165 | 39.20 | 28.48 | 4.359 |
| test | 1,143 | 37.72 | 24.15 | 2.575 |

Corpus-wide: high-debt files **27.88%**; overall patch:refactor **3.015**.

Wallet has the worst patch:refactor among listed subsystems but sits outside primary divergence axes (`other`). Consensus is nearly balanced (1.012), unlike RPC.

### 3.2 Commons static layers

| Layer | src LOC | Notes |
|-------|--------:|-------|
| consensus (+ primitives) | 50,099 | Manifest **240** locked in `blvm-consensus`; test density 1.086 |
| protocol | 17,453 | UTXO commitments 2,754 |
| node network | 23,051 | iroh, tcp, dandelion, erlay |
| node RPC | 20,453 | Separate from module IPC |
| node storage | 23,593 | database, ibd_engine |
| modules | 18,831 | 8 `module.toml`; 7 satellites; process isolation |
| parallel IBD | 12,850 | First-class engine |
| spec-lock crate | 16,237 | Z3-linked verification |
| secp256k1 | 25,578 | Pure Rust |
| bench | 32,763 | Differential / operator harness |

---

## 4. Exemplars (illustrative, not a sample)

| # | Theme | Core | Commons |
|---|-------|------|---------|
| 1 | Formal spec | #32998 bump SCRIPT_VERIFY flags to 64-bit | Numbered `CONSENSUS_SPEC` rules |
| 2 | Spec lock | *(none)* | `blvm-spec-lock` + `#[spec_locked]` |
| 3 | secp | #35564 secp256k1 subtree update | `blvm-secp256k1/` pure Rust |
| 4 | UTXO / IBD | #1677 Ultraprune | utxo_commitments + parallel_ibd |
| 5 | Locks | #35652 reindex deadlock | parallel_ibd as designed concurrency |
| 6 | Transport | #30043 replace libnatpmp | Iroh/TCP/Dandelion/Erlay |
| 7 | Modules vs RPC | #22751 simulaterawtransaction RPC | process modules + `module.toml` |
| 8 | DoS bounds | #31829 TxOrphanage DoS | dos_protection / bandwidth_protection |
| 9 | Layers | #25290 decouple mempool from ArgsManager | crate boundaries from day one |
| 10 | Selective sync | *(none)* | `blvm-selective-sync/` |

JSON twin: `findings/data/divergence_exemplars.json`.

---

## 5. Relation to governance / concentration risk

This study measures **what merged work is about** and **how Commons is structured**. Gini / self-merge / review-quality studies measure **who decides**. A paper on **implementation concentration risk** needs both legs cited separately—architecture mix alone does not prove merge concentration.

---

# Part IV — Methodology

## 6. Research question

How much of Bitcoin Core’s long-run merged-PR bandwidth is consumed by architectural debt compensation and related maintenance, and how does that compare—**asymmetrically**—to Bitcoin Commons’ spec-first layered design posture?

No Commons PR-velocity parity claim.

## 7. Data sources

| Source | Path | Role |
|--------|------|------|
| Enriched Core PRs | `data/processed/enriched_prs.jsonl` | Titles, bodies, labels, files, `merged_at` |
| Classifications | `data/processed/pr_architectural_classification.jsonl` | Per-PR primary/secondary |
| File debt scores | `findings/data/code_turnover_analysis.json` | Tier 2b + subsystem debt (chrono-sorted, 16,653 PRs) |
| BLVM manifest | `data/reference/blvm_architecture_manifest.json` | Rules, locks, crate presence |
| Commons checkout | `/home/user/src/btc-commons` | Static layer scans |
| Jan validated turnover (audit) | `findings/data/code_turnover_analysis_20260128_validated.json` | Prior snapshot |
| Broken newest-first run (discard) | `findings/data/code_turnover_analysis_20260712_regen.json` | Audit only |

## 8. Taxonomy

| Category | Meaning |
|----------|---------|
| `debt_compensation` | Perf/lock/cache/IBD/thread-pool workarounds |
| `refactor` | Structural cleanup without net-new capability |
| `new_feature` | Net-new capability (rare as primary) |
| `consensus_change` | Consensus / validation / soft-fork / script |
| `networking_change` | P2P / peers / transport / relay |
| `rpc_change` | RPC / REST / ZMQ / bitcoin-cli |
| `dependency_maintenance` | secp / depends / subtree / upstream |
| `test_ci_build` | Tests, CI, build system |
| `documentation` | Docs / typos / comments-oriented |
| `other` | Wallet, GUI, policy/mempool, backports, unclear |

## 9. Classification tiers

**Tier 1 — labels:** `data/classification/label_map.yaml`. Only **Resource usage** auto-boosts debt; Block storage / UTXO Db map to `other` unless keywords fire.

**Tier 2a — paths + keywords:** `core_path_map.yaml` (capped path scores), `keyword_rules.yaml`, title-prefix overrides (`refactor:`, `doc:`, `qa:`, `rpc:`, `net:`, …), dependency/subtree title override.

**Tier 2b — file-debt join:** `debt_score ≥ 50` amplifies `debt_compensation` **only with** a **strong** debt signal (strong lock/memory/IBD keywords, weak keywords *in the title*, or Resource usage label). Enrich `performance` subtype alone and bare body mentions of `cs_main`/`ibd` do **not** gate the join. Hot-file touch alone is insufficient; there is no soft hint without a signal.

**Tier 3 — Cursor batches:** export → `scripts/analysis/prompts/architectural_category.md` → import. Results under `data/classification/cursor_results/`. Re-apply after rule changes via `reclassify_with_cursor_overrides.py`.

Gate: ambiguous &lt; 10% → **8.76%**.

## 10. Core debt formula

File/subsystem debt scores follow existing turnover methodology (`CODE_TURNOVER_AND_TECHNICAL_DEBT_METHODOLOGY.md`). **Not applied to Commons.**

**Critical implementation note:** merged PRs must be processed **oldest → newest**. Newest-first JSONL inverted first-touch classification and collapsed patch:refactor (~0.9) and high-debt (~4%). Chrono fix restored ~3.0 / ~28% alignment with the Jan validated snapshot.

## 11. Commons static metrics

`blvm_codebase_metrics.py` scans layer paths for LOC, test density, transports, module.toml counts, posture from the BLVM manifest.

## 12. Dimension matching

`dimension_queries.yaml` + `architectural_comparison.py`:

- If `primary_categories` set: primary match **or** (path ∧ title) when both lists non-empty  
- Else: interpretive / special heuristic (`layered_crates` = ≥3 coarse subsystems)

Precision over recall for noisy keywords.

## 13. Velocity eras

| Era | Years |
|-----|-------|
| early | 2010–2013 |
| growth | 2014–2017 |
| professionalization | 2018–2021 |
| recent | 2022– |

Narrative buckets, not causal periods. Commons = posture only.

---

# Part V — Validation log

All headline statistics regenerated from primary JSONL/JSON on 2026-07-12 after round-2 rule tighten.

| Statistic | Pre-tighten FINAL | Post-tighten FINAL | Δ |
|-----------|------------------:|-------------------:|--:|
| Merged PRs | 16,653 | 16,653 | 0 |
| Debt tax % | 6.14 | **1.70** | **−4.44** |
| Maintenance % | 44.33 | **39.79** | **−4.54** |
| Structural % | 5.96 | 8.82 | +2.86 |
| Net-new % | 16.07 | 16.23 | +0.16 |
| Other % | 22.03 | 22.87 | +0.84 |
| Ambiguous % | 9.94 | 8.76 | −1.18 |
| RPC avg debt | 52.62 | 52.62 | 0 |
| RPC high-debt % | 62.13 | 62.13 | 0 |
| Consensus rules | 159 | **159** | 0 |
| Spec-locked fns | 251 | 251 | 0 |

**Material correction:** maintenance and debt-tax headlines **did** shift after debt/test_ci rule tighten; numbers above are canonical. RPC turnover hotspot unchanged (independent of PR category rules).

Full audit JSON: `findings/data/validation_recompute_audit.json`.

---

# Part VI — External citations (not inputs to Core↔Commons tables)

### Brink “56% of 2025 merges”

- **Claim:** Michael Ford (fanquake) merged 56% of Bitcoin Core PRs in 2025.  
- **Primary:** [Brink 2025 Engineering Impact Report](https://brink.dev/blog/2026/03/26/engineering-impact-report-2025/) · [PDF](https://brink.dev/assets/files/brink-engineering-report-2025.pdf).  
- **Status:** **Verified as Brink’s published figure** (self-reported). Independent `merged_by` replication recommended before treating as hard peer-review fact.

### Bitcoin Knots network share

- **Often summarized:** ~20–25% of nodes.  
- **Status:** **Time-varying**; Coin Dance / Clark Moody / Bitnodes differ; 2025 sybil disputes reported.  
- **Rule:** Cite a **dated snapshot + URL**, or omit.

### Quarkslab audit (2025) — primary-source characterization

**Primary sources reviewed:** [Quarkslab blog](https://blog.quarkslab.com/bitcoin-core-audit.html) · [OSTIF summary](https://ostif.org/bitcoin-core-audit-complete/) · [Brink note](https://brink.dev/blog/2025/11/19/bitcoin-core-security-audit/).

**Paper-ready paragraph:**

> Quarkslab’s 2025 engagement—funded by Brink and coordinated by OSTIF—was the first public third-party security assessment of Bitcoin Core. Scope focused on the P2P attack surface and related mempool, peer/chain management, and consensus/policy validation logic (~100 person-days). The auditors reported no critical, high, or medium findings (two low-severity issues and informational recommendations). Deliverables emphasized testing infrastructure: new block-connect/reorg fuzz harnesses, structured fuzzing (including libprotobuf-mutator harnesses), ensemble fuzzing (PASTIS), and two differential harnesses (chacha20_poly1305 and SHA256 SIMD variants). In conclusion, Quarkslab stated that alternative approaches such as ensemble and differential testing “can certainly add value,” while identifying Brink’s snapshot-fuzzing work (**Fuzzamoto**) as “likely the most valuable path” for triggering deeper bugs—not differential testing alone as *the* path forward. The audit did not claim that Core “lacks property testing,” nor did it prescribe formal verification as a required next step.

**Overstatement flags (do not use in the paper):**

| Overstatement | Why it fails against the primary source |
|---------------|-----------------------------------------|
| “Quarkslab identified differential testing as *the* path forward” | Conclusion elevates **Fuzzamoto / snapshot fuzzing**; differential is one explored alternative that “can add value.” |
| “Quarkslab said Core lacks property testing” | Not stated; scope was P2P-focused assessment + fuzzing experiments. |
| “Audit concluded formal verification is required” | Not concluded; formal verification was not the headline recommendation. |

---

# Part VII — Argument gaps

### Claims that outrun this dataset

| Pattern | Gap |
|---------|-----|
| Merge-authority concentration | Not measured here—cite Gini/self-merge reports |
| “Commons eliminates debt tax” | Unsupported; design response ≠ measured future maintenance |
| “~900k differential blocks” | Operator claim; not re-verified in metrics scripts |

### Resolved in this correction pass

1. ~~Second stratified sample after tightening debt rules~~ → round-2: debt **75%**, test_ci **95%**; maintenance updated.  
2. ~~Reconcile rule_count 159 vs plan 161~~ → canonical **159** (see Part V / rule-count note below).  
3. ~~Quarkslab differential-testing overclaim~~ → accurate paragraph + overstatement table above.

### Rule-count resolution (159 vs 161)

| Source | Count | Notes |
|--------|------:|-------|
| `CONSENSUS_SPEC.md` headings `### PREFIX-N` | **159** | No sequence gaps in the register |
| BLVM manifest / extractor | **159** | Matches headings |
| Plan text / stale Document Statistics footer | 161 | **Wrong** — footer previously claimed 161; corrected to 159 in-spec; plan synced to 159 |

The two “missing” rules were never absent from the register: the **161 figure was a stale footer/plan typo**, not two deleted rules. Canonical number for the paper and this report: **159**.

### Still open (optional)

1. Replicate Brink 56% from raw 2025 `merged_by`.  
2. Residual round-2 miss: BIP350 landed in `test_ci_build` once (1/20)—monitor consensus-keyword vs Tests-label conflicts.

---

# Part VIII — Limitations

1. Asymmetric instruments by necessity—do not blend into one debt index.  
2. Debt-tax point estimate improved in precision (round-2 75%) but remains directional; prefer maintenance % and RPC hotspot for hard claims.  
3. Dimension proxies are interpretive attention shares.  
4. Turnover requires chronological PR order.  
5. Era buckets are narrative, not causal IDs.  
6. Commons youth ≠ permanent maintenance advantage.  
7. External concentration / Knots / audit claims need their own citations—not this corpus.

---

# Part IX — Reproducibility

```bash
cd /home/user/src/bitcoin-governance-research && source venv/bin/activate

python scripts/analysis/code_turnover_analysis.py           # chronological sort required
python scripts/analysis/reclassify_with_cursor_overrides.py
python scripts/analysis/blvm_codebase_metrics.py
python scripts/analysis/subsystem_debt_comparison.py
python scripts/analysis/architectural_comparison.py
python scripts/analysis/velocity_differential.py
python scripts/analysis/export_stratified_validation_sample.py --seed 99 --per-category 20
```

| Artifact | Path |
|----------|------|
| **This report** | `findings/ARCHITECTURAL_DIVERGENCE_FINAL_REPORT.md` |
| Classifications | `data/processed/pr_architectural_classification.jsonl` |
| Phase 1 aggregate | `findings/data/pr_architectural_classification.json` |
| Turnover debt | `findings/data/code_turnover_analysis.json` |
| Commons metrics | `findings/data/blvm_codebase_metrics.json` |
| Dimension table | `findings/data/architectural_comparison.json` |
| Subsystem debt | `findings/data/subsystem_debt_comparison.json` |
| Velocity | `findings/data/velocity_differential.json` |
| Exemplars | `findings/data/divergence_exemplars.json` |
| Recompute / bias audit | `findings/data/validation_recompute_audit.json` |
| Stratified validation (R1) | `findings/data/stratified_validation_sample.json` |
| Stratified validation (R2) | `findings/data/stratified_validation_sample_round2.json` |
| Cursor Tier 3 batches | `data/classification/cursor_results/` |
| Classification YAML | `data/classification/*.yaml` |

---

*End of single final report.*
