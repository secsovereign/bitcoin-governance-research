# Rejection anatomy

**Date:** 2026-09-23  
**Status:** Schema seed (empty objection cells)  
**Machine-readable:** `findings/data/governance_episode_ledger.json`

Do not infer objections. technical_objections, process_objections, nack_exists (beyond unknown), nack_source, stated_reason_for_stall, episode_roles, and corpus_cites come only from BTCDecoded Intelligence search / find_discourse / find_incident / get_passage returns, with source pinned to github | irc | mail | delving | bips. GitHub matcher counts in stalled_proposal_dossiers.json and quotes in archive_gems.json are anchors (existing_findings / github_anchors), not corpus_cites and not substitutes for NACK or objection cells. This file is not an identity store: contributors[].canonical_key joins canonical_maintainers.json; do not copy aliases, emails, or merge keys here. person_role() is merge-capability, not episode role.

This is **episode anatomy**, not GitHub matcher counts. Counts: `STALLED_PROPOSALS_REPORT.md`. Quotes: `ARCHIVE_GEMS.md`.

---

## Block size increase / blocksize wars

- **episode_id:** `blocksize-2015`
- **parent:** —
- **venue:** bitcoin-dev
- **github_anchors:** —
- **existing_findings:** governance_timeline.json
- **technical_objections:** having miners -- or any group -- vote on block size is not an intrinsically good thing., The trouble is this requires maintaining a hash tree commitment over validator state, which turns out to be insanely expensive. … if you also want this commitment scheme for fraud proofs, then you should be arguing for a block size limit decrease (to 500kB), not increase.
- **process_objections:** —
- **outcome:** —
- **corpus_cites:** 7bb2fa3257fb3233839f824429337941611e2820340a7eaf6ae5f9dac04a6217, 6f6f7d58549247ea96a42ed22c5156367d6590ee67f0aa028639caada3f2f9bd

## Taproot activation method

- **episode_id:** `taproot-activation`
- **parent:** —
- **venue:** bitcoin-dev
- **github_anchors:** bitcoin/bitcoin#21701
- **existing_findings:** —
- **technical_objections:** —
- **process_objections:** Some participants expressed concern of having "Bitcoin Core" in the name e.g. "Bitcoin Core + Taproot" as it would be confusing to users and give them the mistaken impression that it had been signed off by Bitcoin Core maintainers., The activation mechanism(s) for this alternative release is Speedy Trial (BIP 8, consistent use of block height) followed by BIP 8 (1 year, LOT=true).
- **outcome:** —
- **corpus_cites:** 5ee0fe7bc0814af2d1f5d5d062b2220e11fad8ca623e41eef3914157c66b2433, 0414138197d4a84afb02af3ee3e075d4a5b94e1c8a146c0be524093a0af442c9, 50c0284c0b1fcc3b6ebdb397da9e00ac1c53159f1e28dbe5e0d3812c5f705962

## OP_RETURN / datacarrier policy

- **episode_id:** `op-return-2024`
- **parent:** —
- **venue:** GitHub PR
- **github_anchors:** bitcoin/bitcoin#32381
- **existing_findings:** ARCHIVE_GEMS.md
- **technical_objections:** Approach NACK for me -- there's no point having a limit that's trivially avoided by just having many OP_RETURNs, and forcing people to waste blockspace by encoding redundant nValue and `OP_RETURN OP_PUSH` instructions
- **process_objections:** —
- **outcome:** —
- **corpus_cites:** 73521ece63aba5a118cf4a4af585e46d9b16a184299534f2666d7a51b3c7a45b

## Dandelion / BIP156 transaction origin privacy

- **episode_id:** `dandelion-pr13947`
- **parent:** —
- **venue:** GitHub PR
- **github_anchors:** bitcoin/bitcoin#13947, bitcoin/bitcoin#20203
- **existing_findings:** STALLED_PROPOSALS_REPORT.md, ARCHIVE_GEMS.md
- **technical_objections:** we still need to figure out what the right behavior is for transaction chains and replacement transactions … and generally how to prevent DoS attacks during stem routing, If we use a stempool … I'm not sure I understand how we could share a stempool across multiple inbound peers without leaking dandelion routing information to an adversary, Neither `dandeliontx` or `dandelionacc` are mentioned and/or specified in the BIP.
- **process_objections:** Needs functional tests.
- **outcome:** —
- **corpus_cites:** 3dd0ecf40408cdce77c772976af0d3f3d7ce99d314d22bc3faffed041c7e0f7e, ee24474a93a3a82c72028970ab5b9cda8b76c37da670170fbd24b8b703750066, d7c99966b47748e485ba9efb5c569b9d37e8393c7871f181a8cc673cc92d32ff, 0f5a668721b4ce773a44632f0b0b984c504a555469def512b0a19d11008a632b, e3fe29cd1c91a2990382da92a104ccf56babaeaab120b74f2fe9f2f1b7c64a07

## UTXO commitments vs AssumeUTXO

- **episode_id:** `utxo-commitments`
- **parent:** —
- **venue:** bitcoin-dev
- **github_anchors:** bitcoin/bitcoin#3977, bitcoin/bitcoin#15605
- **existing_findings:** STALLED_PROPOSALS_REPORT.md
- **technical_objections:** A soft-fork to make (U)TXO commitments always required is problematic, because we can't change the format of those commitments in the future in another soft-fork - the exact form is baked in stone., The trouble is this requires maintaining a hash tree commitment over validator state, which turns out to be insanely expensive. … that ends up requiring 15 - 22x more I/O during block validation., My objection is that `assumeUTXO` makes the most critical part of the codebase harder to read and reason about, and this PR extends that model further.
- **process_objections:** —
- **outcome:** —
- **corpus_cites:** 3ec77c6ca322a8075b81313746314f3dbb4b668a9dafccebbc97c7741a033855, 6f6f7d58549247ea96a42ed22c5156367d6590ee67f0aa028639caada3f2f9bd, 22d2d6a9d60b08b979efbeb5a9c0a8c3b41cf3f0b9fb78494ffd617de2b3f492, 5074841b738fea4e44bd8331bfcc281a2cc78dcbcfe001a745d2debe9842f431

## Erlay set-reconciliation relay

- **episode_id:** `erlay`
- **parent:** —
- **venue:** GitHub PR
- **github_anchors:** bitcoin/bitcoin#21515, bitcoin/bitcoin#18261, bitcoin/bitcoin#30277
- **existing_findings:** STALLED_PROPOSALS_REPORT.md, ARCHIVE_GEMS.md
- **technical_objections:** —
- **process_objections:** This is not to be merged. Functionality will be spread across multiple smaller PRs to ease the review process.
- **outcome:** —
- **corpus_cites:** 98e4c756dd91f5b9397f6ac25051d5630c26c33376846165459329fbc91598b5, f42f37ccaed32ae73f5a7df1b8d120f36bd7fd2720dd15f493c4308a3893a5df, 80f98485057ba50a2e480ee0cec38e669baa9b838ec2d98c3123c6c4885dd15a, 0a2983f841556e06a375607e308725eafd8dfc96c7e7d5ffab055d4ecb05c3ab

## BIP editor process / Luke Dashjr

- **episode_id:** `bip-editor-dashjr`
- **parent:** —
- **venue:** bitcoin-dev
- **github_anchors:** bitcoin/bips#271
- **existing_findings:** —
- **technical_objections:** —
- **process_objections:** Off-list BIP-related correspondence should be sent (or CC'd) to the BIP editors., admissions from Luke that he has not had the time to actively work on the BIPs repo … I think it is prudent for us to look at adding more BIPs editors.
- **outcome:** —
- **corpus_cites:** 58498aa8c91f23f12944bba7a5bbd51a651dd8b8805d74a07df036b0a2652b09, 401eaf732dbd29fc3116749541cc5d22a93d8a73c924b82abfccc81e2c7a7911, 37a7e8163339d67892cf45776b823d69e8b6d0712c61cad8f2f8806088140871, f3caacf5b89f926b3bcfc03e5be9596f31708d9935bb252666e5d465be1e50f7, 437704059ef5defe4baac183c59bf2650181648c4d8d6aabab58aea54d960709

## libbitcoinkernel extraction

- **episode_id:** `kernel-extraction`
- **parent:** wallet-node-split
- **venue:** GitHub PR
- **github_anchors:** bitcoin/bitcoin#24322, bitcoin/bitcoin#27285
- **existing_findings:** STALLED_PROPOSALS_REPORT.md
- **technical_objections:** NACK. This is pretty literally the opposite of what we want to be doing with the kernel. … Hiding this away into `libbitcoin_util` only makes this harder/impossible to do
- **process_objections:** —
- **outcome:** —
- **corpus_cites:** 6760b0bf63931b62aad281510bd179efed6d82809436d63ae098c7db221e4c61, 6e6ebfdecf884e548dbb64a734e036e1f4d0bfb5d080463c7106569b33d001aa



**Generated by:** `scripts/reporting/generate_from_templates.py`
