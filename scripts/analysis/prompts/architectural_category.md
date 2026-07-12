# Cursor Tier 3 — Architectural PR category prompt

Classify each Bitcoin Core PR into the divergence-study taxonomy.

## Categories (pick exactly one primary)

| Category | Meaning |
|----------|---------|
| `debt_compensation` | Perf/lock/cache/IBD/thread-pool patches working around architectural limits |
| `refactor` | Structural cleanup without net-new user capability |
| `new_feature` | Net-new capability |
| `consensus_change` | Consensus / validation / soft-fork / script rules |
| `networking_change` | P2P, peers, addr, transport, relay |
| `rpc_change` | RPC / REST / ZMQ / bitcoin-cli API surface |
| `dependency_maintenance` | secp256k1, depends/, subtree, upstream lib bumps |
| `test_ci_build` | Tests, CI, build system only |
| `documentation` | Docs / typos / comments-only |
| `other` | Wallet, GUI, unclear, or none of the above |

## Rules

1. Choose **primary** = main purpose of the PR.
2. Optional **secondary** (0–2) if clearly dual-purpose (e.g. networking + debt_compensation).
3. Prefer path evidence over vague titles when they conflict.
4. Perf work on `validation.cpp` / `net_processing` / mempool / IBD → lean `debt_compensation` even if titled "refactor".
5. Pure test/CI/doc → those categories even if files touch `src/` slightly.
6. Do **not** invent categories.

## Output

Return one JSON object per PR (JSONL), fields:

```json
{"number": 12345, "primary": "debt_compensation", "secondary": ["networking_change"], "confidence": "high", "rationale": "short reason"}
```

`confidence`: `high` | `medium` | `low`
