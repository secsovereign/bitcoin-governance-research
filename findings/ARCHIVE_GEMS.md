# Archive gems

**Date**: 2026-09-12  
**Method**: The four frames in `GOVERNANCE_FRAMES.md` pick *where* to look. This pass reads the primary text at those places — GitHub threads, bitcoin-dev, Satoshi’s archive — and keeps only quotes that change how you read the numbers.  
**Machine pack**: `findings/data/archive_gems.json`  
**Local LLM**: `OPENAI_BASE_URL` was down this run. Re-run `venv/bin/python scripts/analysis/archive_gems.py --llm` when the endpoint is up.

Seventeen years is not a prompt. It is a mine. The quantitative work is the map.

Quote pack, not episode anatomy. Counts vs anatomy: `STALLED_PROPOSALS_REPORT.md`, `REJECTION_ANATOMY.md`, `STALLED_AGREEMENT_LEDGER.md`.

---

## How this integrates

| Frame | What the numbers say | What the archives add |
|-------|----------------------|------------------------|
| Agenda vs decision | 2015–21 flow ~0.55; 2022+ **0.002** | The list still *designs* policy (package RBF). GitHub then spends years on approach, not whether to have the meeting. |
| Funnel | 2022+ top-3 ~82% of merges | “[NO MERGE]” and “Concept NACK to deferring tests” are the filter talking. |
| Power is not portable | BIP top-10 ∩ Core top-10 = 2 | A BIP can be “research-complete” and still die on DOS/wallet edge cases. |
| Exit as selection | 90.7% inactive; established 58% | Multi-year PRs are a retention machine for the people already inside the graph. |

---

## Gems

### 1. The design was declared finished in 0.1

> The nature of Bitcoin is such that once version 0.1 was released, the core design was set in stone for the rest of its lifetime.

Satoshi, archive. This is why later “we discussed it on Delving” is the wrong unit. The stone is consensus. Everything else is how a thin continuing set *approaches* the stone.

### 2. Persuasion was never the job

> If you don't believe me or don't get it, I don't have time to try to convince you, sorry.

Satoshi, Bitcointalk, snack-machine thread. Same voice as today’s review culture: show the work or drop it. Not a town hall.

### 3. Dandelion did not lose a vote. It lost a threat model.

PR [#13947](https://github.com/bitcoin/bitcoin/pull/13947) — BIP 156, closed unmerged.

> I closed this for now because it is non-trivial to allow for all wallet behavior (e.g. cpfp and rbf) while not opening DOS vectors. I think a simpler first step would be to go for "Dandelion Light" or "Dandelion one-hop."

The dossier claim (“research-complete; Core did not ship”) is true. The thread says *why*: stem routing vs the wallet’s own RBF/CPFP. Privacy that breaks the mempool policy you already shipped is not a merge.

### 4. Erlay is still an argument about measurement

PR [#21515](https://github.com/bitcoin/bitcoin/pull/21515) — full protocol, unmerged.

> Therefore it is better NOT to use this patch. Therefore, NACK, for now, perhaps premature.

> I was slightly tuning implementation/configurations and observing savings of 20-50% of overall bandwidth.

Same PR. Opposite empirics. The stall is not “nobody cares about bandwidth.” It is that a bandwidth BIP does not close until two nodes agree what the graphs mean. Scaffolding can merge. The protocol waits.

### 5. Package relay announced the rule on the list, then spent years on GitHub

bitcoin-dev, Gloria Zhao, taproot-era:

> I'm writing to propose a set of mempool policy changes to enable package validation (in preparation for package relay) in Bitcoin Core. These would not be consensus or P2P protocol changes.

Then the implementation PR is titled **`[NO MERGE]`** ([#27742](https://github.com/bitcoin/bitcoin/pull/27742)):

> I'd like to get rough consensus on approach before we start looking at code details and merging PRs.

That is the 2022+ flow number in prose: the list sets the *topic*; GitHub refuses to treat the first large PR as a decision.

### 6. “We won’t merge it if it doesn’t compile” is the early process, unromantic

PR [#980](https://github.com/bitcoin/bitcoin/pull/980), 2012:

> Don't worry, we won't merge it if it doesn't compile cleanly.

The later ritual (ACK / NACK / DrahtBot coverage / approach NACK) is this sentence with more ceremony.

### 7. Outside libraries are treated as a sovereignty problem

PR [#10102](https://github.com/bitcoin/bitcoin/pull/10102) (multiprocess):

> NACK This is using a library produced by an outside entity that addresses a specific use case of bitcoin. Good intentions and all, bait-and-switch is a thing.

And on Erlay’s minisketch subtree ([#23114](https://github.com/bitcoin/bitcoin/pull/23114)):

> Concept NACK to using a subtree for non-consensus-critical libraries. At the very least, there should be a way to use a system install.

Portability again: a good idea with a foreign dependency is a different object than a good idea.

### 8. Two years of refactor is a governance fact

AssumeUTXO, [#15606](https://github.com/bitcoin/bitcoin/pull/15606):

> …a slight dread at the prospect of introducing more prerequisite refactoring (given this project has been ongoing for two years already)…

The premium numbers (cold-start ~16% since 2022; large outsider closed ~5%) are this, counted. Time is the filter.

---

## What we did *not* do

- Dump 430k IRC lines into a model. That is a bill, not a method.
- Treat DrahtBot review tables as speech.
- Re-quote all-time merge share as if it were 2022+.

When the local OpenAI-compatible server is up:

```bash
venv/bin/python scripts/analysis/archive_gems.py --llm
venv/bin/python scripts/reporting/generate_findings_reports.py
```

**Cite the quote and the PR.** The frames tell you which shelf. The gem is on the shelf.
