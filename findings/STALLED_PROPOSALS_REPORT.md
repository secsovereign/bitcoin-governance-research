# Stalled Proposals: Case Dossiers (Fair Cite)

**Date:** 2026-07-13  
**Status:** Fair cite v2.1  
**Machine-readable:** `findings/data/stalled_proposal_dossiers.json`  
**Script:** `scripts/analysis/stalled_proposal_dossiers.py`  
**Rolled into:** `EXECUTIVE_SUMMARY.md` (Long-Term Problem)

## Question

Which named “research-complete / delayed” proposals have **GitHub timelines strong enough to cite**, without counting scaffolding as delivery or noisy keywords as proof?

## Fair-cite guidance (from artifact)

| Proposal | Strength | Cite as |
|----------|----------|---------|
| **Dandelion** | Strong | One implementation PR (`#13947`) closed unmerged (~333 days); Core did not ship |
| **Erlay** | Strong | Full-protocol set **0/7 merged**; 4 scaffolding merges ≠ protocol delivery |
| Package relay | Moderate | Multi-year lifetimes + exemplars (e.g. `#27742`); mixed outcomes |
| Private broadcast | Contrast only | Narrower threat model; not a Dandelion substitute |
| AssumeUTXO / UTXO keywords | Lead only | Totals too noisy for agenda accept/reject claims |
| Wallet/node / kernel / IPC | Lead only | Broad match over-counts |

## Erlay detail (corrected matcher)

Word-boundary match; roles:

| Role | N | Merged | Closed unmerged | Open |
|------|--:|-------:|----------------:|-----:|
| Full / core protocol | 7 | **0** | 6 | 1 |
| Named non-scaffold | 2 | 0 | 2 | 0 |
| Scaffolding / signaling / fuzz / prep | 4 | **4** | 0 | 0 |
| Mention-only | 2 | 1 | 1 | 0 |

Full-protocol examples closed or DO-NOT-MERGE: `#18261`, `#21515` (~1186 days), `#28765`, `#30116`, `#30277`, `#35591`.

## Method limits (fairness)

- Keyword dossiers ≠ exhaustive history; BIP / mailing-list paths not included.
- Closed-unmerged includes author withdrawal and staging PRs.
- Wallet/AssumeUTXO rows are **search leads**, not verdicts.

## Reproduce

```bash
cd /home/user/src/bitcoin-governance-research && source venv/bin/activate
python scripts/analysis/stalled_proposal_dossiers.py
```
