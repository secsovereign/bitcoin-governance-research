# Newcomer divergence outside Core

**Date:** 2026-10-11
**Machine-readable:** `findings/data/newcomer_divergence.json`
**Problem:** Does the Core newcomer-versus-incumbent merge divergence appear in the other seven-year repositories?

The estimator is the pass 2 linear probability model on decided merge rate. Newcomer means the pull request falls within 12 months of that author's first pull request. Incumbent means the first pull request was at least 3 years earlier. Authors between those ages are in neither series. Open pull requests are excluded. A calendar year is dropped when more than 20 percent of its pull requests are still open. The interaction is newcomer times years since 2010. Comparison authors are keyed on the numeric GitHub user id. Core authors use the existing identity index. A slope needs 3 years. If either group has fewer, the interaction is DATA UNAVAILABLE and that repository is left out of the classification. `comments_count` is not used.

## Core check

The Core interaction is -3.7 percentage points per year (fresh interval -4.0 to -3.3). n=18956. This point matches the published pass 2 estimate of -3.7 percentage points. The published interval remains the Core headline. The interval here is a fresh seed 7 bootstrap so the repositories can be compared with each other. The newcomer slope is -2.7 percentage points per year. The incumbent slope is 0.9 percentage points per year. The Core driver is BOTH.

## Identity

Numeric GitHub user ids collapsed 0 extra logins (0 people had more than one stored login). Core stays on the existing identity index. Author ids are DATA UNAVAILABLE for foundation-devices/passport-firmware, stratum-mining/stratum, stratum-mining/sv2-spec.

## Classification

The classification is AMBIENT. 9 seven-year repositories have a usable interaction. Intervals that exclude zero on the negative side are bitcoin-core/secp256k1, bitcoindevkit/bdk, lightningnetwork/lnd, ACINQ/eclair. Intervals that exclude zero on the positive side are rust-bitcoin/rust-bitcoin, rust-bitcoin/rust-miniscript. Dropping the shared-maintainer repositories leaves the classification AMBIENT.

Before the slope gate, 7 of 12 eligible interactions were negative. After it, 5 of 9 were negative.

A repository shows the divergence when the newcomer-by-year interaction on decided merge rate is negative and its interval excludes zero. A slope needs 3 years. If either group has fewer than 3 years, the interaction is DATA UNAVAILABLE and the repository is left out of the classification. CORE-SPECIFIC when Core's interval excludes zero on the negative side and no seven-year comparison repository has an interval that excludes zero on the negative side. AMBIENT when Core's interval excludes zero on the negative side, at least half of those repositories have a negative point, and at least one of those intervals excludes zero on the negative side. UNDETERMINED otherwise. The seven-year minimum is the one already used for the cross-repository table.

Among eligible repositories, the interaction is NEWCOMER DECLINE in 0, INCUMBENT GAIN in 1, BOTH in 1, INCUMBENT DECLINE in 2, and UNRESOLVED in 5.

| Repository | Years | Eligible | Interaction, percentage points per year | Interval | Newcomer slope | Incumbent slope | Driver |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bitcoin-core/secp256k1 | 13 | yes | -5.7 | -7.9 to -3.5 | -1.6 | 3.8 | INCUMBENT GAIN |
| bitcoindevkit/bdk | 7 | yes | -14.7 | -25.9 to -1.2 | -8.1 | 6.5 | BOTH |
| lightningdevkit/rust-lightning | 9 | yes | 0.3 | -1.0 to 1.8 | -1.8 | -2.1 | INCUMBENT DECLINE |
| lightningnetwork/lnd | 11 | yes | -3.1 | -4.4 to -1.8 | -1.2 | 1.9 | UNRESOLVED |
| sparrowwallet/sparrow | 7 | no | DATA UNAVAILABLE | not defined | missing | missing | UNRESOLVED |
| SeedSigner/seedsigner | 7 | no | DATA UNAVAILABLE | not defined | -7.7 | missing | UNRESOLVED |
| foundation-devices/passport-firmware | 3 | no | DATA UNAVAILABLE | not defined | missing | missing | UNRESOLVED |
| stratum-mining/stratum | 6 | no | DATA UNAVAILABLE | not defined | -0.9 | missing | UNRESOLVED |
| bitcoin-core/bitcoin-maintainer-tools | 11 | no | DATA UNAVAILABLE | not defined | missing | missing | UNRESOLVED |
| lightning/bolts | 11 | yes | -3.4 | -8.9 to 1.9 | -2.4 | 4.9 | UNRESOLVED |
| ElementsProject/lightning | 12 | yes | 0.3 | -0.7 to 1.3 | -1.1 | -1.3 | INCUMBENT DECLINE |
| bitcoin-core/HWI | 9 | no | DATA UNAVAILABLE | not defined | -7.2 | missing | UNRESOLVED |
| rust-bitcoin/rust-bitcoin | 13 | yes | 4.6 | 2.2 to 7.0 | 1.4 | -3.6 | UNRESOLVED |
| rust-bitcoin/rust-miniscript | 9 | yes | 4.8 | 0.2 to 9.2 | 0.5 | -2.8 | UNRESOLVED |
| stratum-mining/sv2-spec | 5 | no | DATA UNAVAILABLE | not defined | missing | missing | UNRESOLVED |
| ACINQ/eclair | 11 | yes | -2.9 | -4.9 to -0.9 | -1.9 | 1.0 | UNRESOLVED |
| ethereum/go-ethereum | missing | no | DATA UNAVAILABLE | not defined | missing | missing | UNRESOLVED |

sparrowwallet/sparrow. The interaction is the pass 2 linear probability model on decided newcomer and incumbent rows. The newcomer slope uses 1 year and the incumbent slope uses 0 years. A slope needs 3 years, so the interaction is not used. SeedSigner/seedsigner. The interaction is the pass 2 linear probability model on decided newcomer and incumbent rows. The newcomer slope uses 5 years and the incumbent slope uses 2 years. A slope needs 3 years, so the interaction is not used. foundation-devices/passport-firmware. The interaction is the pass 2 linear probability model on decided newcomer and incumbent rows. The newcomer slope uses 1 year and the incumbent slope uses 0 years. A slope needs 3 years, so the interaction is not used. stratum-mining/stratum. The interaction is the pass 2 linear probability model on decided newcomer and incumbent rows. The newcomer slope uses 6 years and the incumbent slope uses 1 year. A slope needs 3 years, so the interaction is not used. bitcoin-core/bitcoin-maintainer-tools. The interaction is the pass 2 linear probability model on decided newcomer and incumbent rows. The newcomer slope uses 1 year and the incumbent slope uses 0 years. A slope needs 3 years, so the interaction is not used. bitcoin-core/HWI. The interaction is the pass 2 linear probability model on decided newcomer and incumbent rows. The newcomer slope uses 5 years and the incumbent slope uses 1 year. A slope needs 3 years, so the interaction is not used. stratum-mining/sv2-spec. The interaction is the pass 2 linear probability model on decided newcomer and incumbent rows. The newcomer slope uses 2 years and the incumbent slope uses 0 years. A slope needs 3 years, so the interaction is not used.

Short-history repositories are scored in the table and left out of the classification. ethereum/go-ethereum stays DATA UNAVAILABLE because `prs.jsonl` is missing.

## Health link

The Spearman correlation of the interaction with the size-adjusted residual is 0.370 (interval -0.397 to 0.961). n=10.

## What this cannot prove

- A Core-specific divergence is not proof that implementation diversity would remove it.
- An ambient divergence is not proof that every reference implementation must treat newcomers this way.
- The cross-repository count is below 20.
- A positive interaction is not evidence that a repository's practice serves newcomers. The driver column is the description that replaces that reading.


**Generated by:** `scripts/reporting/generate_from_templates.py`
