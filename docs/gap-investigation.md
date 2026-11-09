# Gap investigation

Measured 2026-11-09. Nothing in this file was filled with an estimate. Where a source is missing, the row says so.

## Where the three pieces are

| Piece | Path | Commit at the start of this work | Remote |
| --- | --- | --- | --- |
| Intelligence MCP and the ingest that feeds it | `/mnt/data/bitcoin/btcdecoded-intelligence` | `50d30a34b3c11d49bf7929570253573ede1058d5` | `git@github.com:BTCDecoded/btcdecoded-intel.git` |
| Ingest runtime (not a third repo) | `/home/josh/.local/state/btcdecoded-intel-ingest` | n/a | The worker reads research from `RESEARCH_ROOT` in `ingest/sources.ts`, hardcoded to `/mnt/bulk/bitcoin-governance-research` |
| Governance collection, analysis, findings | `/mnt/bulk/bitcoin-governance-research` | `967c3069cb45e4816acd79e3a5fb337a7e63d387` | `https://github.com/secsovereign/bitcoin-governance-research.git` |

A local Bitcoin Core clone used only to read `contrib/verify-commits/trusted-keys` is `/mnt/data/bitcoin/core` at `f0de87f040` (2026-10-26). It is not one of the three pieces.

Both working trees were already dirty. Those edits were left unstaged. Intelligence's prior edits were stashed as `wip before gap-closure 2026-11-09` and are not part of this branch.

## Assumptions

- S0910, S0920, S0923, S1012, and S1031 are date labels (10 Sep, 20 Sep, 23 Sep, 12 Oct, 31 Oct 2026). No file in either repo uses those strings. S0920 matches the date on `findings/MAINTAINER_LIST_SOURCE.md` and that file has no corpus counts. S0923 was not found.
- "Published banners" means the count lines in `README.md`, `findings/EXECUTIVE_SUMMARY.md`, and `findings/README.md`.
- The outside rebuild's 25,508 / 9,242 / 196,053 / 450,047 are not adopted. They are not the line counts of the files on this machine.
- `get_snapshot` keeps its old job. A 64-character id still replays one stored tool result. A corpus id such as `S1109` returns the collection manifest.

---

## 1. Counts and snapshots

**Confirmed as a freshness problem. Not a single counter bug.**

Commands and what they showed:

- Line counts of the jsonl files, streaming, on 2026-11-09.
  - `data/github/prs_raw.jsonl`: 25,506 lines, 25,494 unique numbers, 12 numbers repeated. Closed 25,076, open 430. Max number 36505.
  - `data/processed/enriched_prs.jsonl` and `cleaned_prs.jsonl`: 25,122 lines, 25,110 unique. 384 raw numbers are absent from the cleaned file. All 384 have an author. They are the high numbers, about 36060 through 36505. `_clean_pr` in `scripts/data_processing/clean_data.py` drops a row only when number or author is missing. This is a clean that was not re-run, not a bot filter and not a null-author filter.
  - `data/github/issues_raw.jsonl`: 9,240 lines. Enriched and cleaned issues: 8,890. 350 raw issues were not cleaned. The ones inspected have authors. Same staleness.
  - `data/irc/messages.jsonl`: 447,349. Every row is `#bitcoin-core-dev`, source `irc_html`. File mtime is 2026-10-12.
  - `data/bitcointalk/posts.jsonl`: 159,092, all ISO dates, none null, 2009-12-09 through 2026-10-01. Topics 14,147. Sum of topic `n_posts` is 177,036.
- The banners before this change said 25,122 PRs, 8,890 issues, 430,613 IRC, 158,917 Bitcointalk. 25,122 and 8,890 still match the enriched files. 430,613 and 158,917 do not match the current files and cannot be recomputed from them. They stay under S0910 as cited figures.
- The outside figures are +2 against the local raw GitHub line counts and are not the IRC or Bitcointalk files. Not reproduced.
- `src/lib/snapshot.ts` `get_snapshot` stored a tool-call blob under a 64-character hash. It did not return a collection manifest. Findings cite JSON artifacts through `findings/CLAIMS_LEDGER.md`. They did not carry a collection snapshot id.

**Spec.** One JSON manifest per snapshot that this tree can actually document: `findings/snapshots/S0906.json`, `S0910.json`, `S1012.json`, `S1031.json`, `S1109.json`. Each has `measured_at`, `script_commit` where one is known, filters, and counts. S0910 has `script_commit: null` because that commit was not recovered. There is no S0920 or S0923 manifest. Inventing one would invent a collection.

The newest recomputed file counts are S1109 (measured 2026-11-09, not a new network collect). S1031 keeps the 25,506 raw PR lines. S1012 keeps the October 12 mail and Delving file counts. S0906 keeps the committed September Delving count of 4,662. S0910 keeps 25,122, 8,890, the cited 430,613 IRC, the cited 158,917 Bitcointalk posts, and the cited 51,062 deduped emails. The deduped email total was not recomputed and is marked `cited_not_recomputed`.

`findings/snapshots/banner_citations.json` lists each banner string, the snapshot, and the field. `scripts/validation/snapshot_manifests.py` fails when the string is missing or the number disagrees. This pass tags the corpus-size banners only. Tagging every number in every finding is larger than the symptom and was not done.

`get_snapshot` on an `S####` id returns that manifest. A 64-character id is unchanged.

Old values that the banners used to print alone, and the values that replace them as the current citation:

| Measure | Old banner | Current citation | Older id that still holds the old value |
| --- | --- | --- | --- |
| IRC messages | 430,613 | 447,349 | S0910 |
| Bitcointalk stored posts | 158,917 | 159,092 | S0910 |
| Delving posts | 4,662 | both are cited | 4,662 is S0906; 4,817 is S1012 |
| Raw PR lines | not on the banner | 25,506 | S1031 and S1109 |
| Raw issue lines | not on the banner | 9,240 | S1109 |

Enriched 25,122 and 8,890 did not change.

## 2. Coverage gaps

**Confirmed, and more specific than the four-line table.**

Cryptography pre-history. `scripts/data_collection/cryptography_ml_collector.py` documents 2008-01 through 2011-12, which is 48 months. The raw directory has 32 of those 48 gzip files. The 16 missing names are in `findings/data/coverage_report.json`. HTTP HEAD on 2026-11-09 returned 404 for 2009-December, 2010-January, 2010-November, 2011-January, 2011-June, and 2011-July. The gap is upstream. The missing months are listed and not imputed. The incremental manifest writer was dropping the full-window fields on update. It now stores `prehistory` from the files on disk.

IRC. The HTML corpus is `#bitcoin-core-dev` only, 447,349 messages, timestamps ending in `Z` or `+00:00`. The archive page says timestamps are UTC, so the HTML conversion is verified for this file. The plain-text parser stamps `+00:00` with no source. The current file does not use that parser. `#bitcoin-dev` and `#bitcoin-core` are 6,495 days each, and 6,494 of each contain "There are no messages recorded". That is an upstream empty archive, not a parse failure. One day on each was not that sentence and was not parsed into `messages.jsonl`. Those two days are unnamed in this report. The channels were not filled with estimated messages.

Bitcointalk. Months from 2010-01 through 2026-10 are present. Dates parse. The unresolved part is that `_parse_forum_date` labels a naive forum time as UTC. Stored posts (159,092) are fewer than the topic `n_posts` sum (177,036). The difference is the parser ceiling already described by the repair manifest. It is recorded as a gap and not filled.

BIP discussions. `scripts/collect_all.py` called `bips_collector.py --skip-discussions` when `bips.jsonl` was missing, and skipped the whole BIP step when the dump already existed. A clean machine therefore never collected discussions. This machine has `bips_prs.jsonl` (max updated 2026-07-11) and `bips_issues.jsonl` (max updated 2025-12-08). Those files were not refreshed. The flag is removed so the next clean collect fetches discussions. A refresh needs a GitHub token and was not run.

**Spec.** `findings/data/coverage_report.json` is expected against ingested, per source, with `fixable: false` where the upstream object does not exist. Search text in Intelligence appends a coverage line when a cite's source is mail, irc, or bitcointalk. `get_snapshot` of a corpus id returns the manifest, whose note points at the gaps. No missing month, post, or IRC day is invented.

## 3. Merge-key events

**Confirmed that the events were prose, and that the 23 logins are not the GPG list.**

`data/maintainers/merge_capability.json` holds 23 observed `merged_by` logins, generated from cleaned pull requests. `scripts/data_collection/maintainers_history_collector.py` already says `bitcoin/bitcoin` has no MAINTAINERS file. `git log` of `contrib/verify-commits/trusted-keys` at `f0de87f040` returns 20 commits. That history can generate fingerprint additions and removals. It cannot generate the 23 GitHub logins. Early mergers predate the file.

The named pulls are in the enriched file: 23798, 25524, 27604, 27054, and 34517 merged; 25560, 25871, 26868, and 17094 did not. 34517's "Concept NACK" from Sjors is a farewell joke plus a key check, so it is not stored as a rejection. Excerpts are stored as excerpts.

**Spec.** `findings/data/trusted_keys_events.json` is those 20 commits: hash, date, author, subject, fingerprints added, fingerprints removed, action, commit URL, `evidence_tier: first_party`, `rule_cited: false`, `thin: true` because the subject does not cite a written rule or the objections. The file says in `not_the_23_logins` that the login list is a different set. `findings/MERGE_KEY_EVENTS.md` points at it. Intelligence loads the same JSON and, on a search query that mentions trusted-keys, merge keys, or maintainer nomination, appends the counts and that sentence. Production Vectorize was not re-embedded.

Log order follows `git log --reverse`. The sedited addition is dated 2026-01-08 and the glozow removal is dated 2025-09-18, and the log does not put those two in calendar order. The dates are the ones git printed. They were not reordered.

## 4. Applied consequences

**Confirmed that no such field existed. The named moderation records are not applied sanctions.**

PR 7243 and PR 26890 are closed, unmerged code-of-conduct proposals. Issue 29507, "Consideration of a Code of Conduct and/or written rules for moderation", author achow101, opened 2024-02-28, is a proposal. A moderation dossier dated 2024-08-14 was not found in the corpus. The Mechanic ban is not in the corpus. The only basis named in the request is his own tweet, which was not ingested.

The first-party acts already on disk are the trusted-keys removals.

**Spec.** `findings/data/applied_consequences.json` has three lists. `applied` is the key-removal commits: actor (commit author), target (the subject, which names the key), trigger (the same subject), `rule_cited: false`, `evidence_tier: first_party`, `thin: true`. `not_applied` is PR 7243, PR 26890, and issue 29507. `allegations` is the Mechanic row: actor null, trigger null, `evidence_tier: allegation`, `thin: true`, source "not in this corpus". A search query that mentions Mechanic, sanction, code of conduct, or applied consequence returns that distinction. Nothing was backfilled as a ban that the corpus does not record.

## 5. Layer of a pull request

**Confirmed for `analyze_pr`. File lists are already ingested. The existing `pr_type` label is the wrong tool.**

Enriched rows store GitHub `filename` lists, not patch text. A hunk-level claim that PR 32359 changes no consensus rule cannot be recomputed, because it touches `src/validation.cpp` and the patch is not stored. `src/utils/pr_classification.py` treats the word "policy" and a policy path as consensus-related, so 32359, 32381, and 32406 come out consensus-related, and 32714, 33224, and 33453 come out documentation. That label was left in place.

`analyze_pr` already computes `consensus_paths` from a prefix list that includes `src/validation`. That gate was left in place. It is not the new layer. `surface_class` is an LLM choice and was left in place.

**Spec.** Rule id `filenames-v1`, in `src/utils/pr_layer.py` and `src/lib/pr-layer.ts`. Tests and docs are set aside. Precedence of what remains:

1. consensus: `src/consensus/`, `src/primitives/`, `src/script/`
2. relay_policy: `src/policy/`, `src/node/mempool_args.cpp`, `src/kernel/mempool_options.h`, or `src/init.cpp` / `src/validation.cpp` only when a touched test path contains `datacarrier` or `mempool` and no consensus path is present
3. wallet: `src/wallet/`
4. gui: `src/qt/`
5. build: `depends/`, `ci/`, `cmake/`, `.github/`, `build-aux/`, `CMakeLists.txt`, `Makefile`, `Makefile.am`, `configure.ac`, `autogen.sh`, `*.cmake`
6. tests, if nothing else remains
7. other

`src/validation.cpp` alone is other. `src/init.cpp` alone is other. `primary` is the highest layer. `analyze_pr` returns `files_touched`, `layer`, and `layers`. A local run wrote `findings/data/pr_layers.jsonl` (25,122 rows). `*.jsonl` is gitignored, so the committed artifact is `findings/data/pr_layer_summary.json`, which holds the primary counts and the six examples with their filenames. The classifier test recomputes those six from the filenames.

Recomputed primary counts: other 9,547, tests 5,813, build 2,953, wallet 2,548, gui 2,214, consensus 1,544, relay_policy 503. The six named pulls are all `relay_policy`, and none of them is in the consensus layer under this rule. 32359's files include `src/validation.cpp`, `src/policy/`, `src/init.cpp`, `src/kernel/mempool_options.h`, and `src/node/mempool_args.cpp`.

## 6. Keyword methods

**Partly confirmed. A precision rate is not published.**

Conflict. `stance_flags` in `scripts/analysis/commons_dynamics_test.py` treats a body as a NACK when it matches `\bNACK\b` and is not a hedged "not a nack", or when the GitHub review state is `CHANGES_REQUESTED`. A convenience walk of the first 10 hits from the start of `enriched_prs.jsonl` among recent numbers: 3 are DrahtBot templates quoting someone else's NACK, 6 are `CHANGES_REQUESTED` notes that do not say NACK, 1 quotes another person's NACK, and 0 are an unquoted NACK by the commenter. n=10 and the walk is not random, so `findings/data/metric_kinds.json` stores the sample and sets `published_precision` to null.

Right-censoring. Some analysis scripts already censor open work at the end of the dump. The methodology did not say that a 2026 resolution time is right-censored. It does now.

Contributor dossiers. The method is keyword match. A separate hand label of dossiers was not done. The metric file says a hit is a keyword match, not a reviewed identity.

Closed-unmerged. The revealed-rough-consensus figure is 16,845 merged, 7,907 closed unmerged, 370 open. Of the 7,907, 683 have `draft: true` and 7,224 do not. Enriched rows have no `state_reason`. Withdrawn and rejected are null. The 7,224 are not labeled rejected.

Funding. `findings/ENHANCED_FUNDING_ANALYSIS_REPORT.md` already said most funding is never mentioned. It now says the mentions are a floor. Counts were not recomputed.

Review. Methodology section 3 already says review counts are GitHub review objects and that pre-2016 absence is not coded as zero. The metric file repeats that comments, IRC, and offline review are missed.

## 7. Documents

Checked with the live search tool on 2026-11-09, and against the local files.

| Document | Result |
| --- | --- |
| June 6, 2025 "Bitcoin Core development and transaction relay policy" | Missing. Page is `https://bitcoincore.org/en/2025/06/06/relay-statement/`. Text retrieved that day and stored as an article. |
| Feb–Apr 2024 bitcoin-dev thread on adding BIP editors | Present. Ava Chow, "Adding New BIP Editors", through the April 22, 2024 addition note. |
| Jeff Garzik, Feb 24, 2014, OP_RETURN in the 0.9 release, and PR 3737 | Both present. The mail cites PR 2738 and PR 3737. PR 3737 is in `prs_raw.jsonl`. |
| bitcoin-dev thread opened April 17, 2025 | Present. Antoine Poinsot, "Relax OP_RETURN standardness restrictions". |
| Jason Hughes, April 28, 2025, on taking comments to the list | Present in the mail index. |
| Delving, May 1, May 12, and May 14, 2025 | Present. Topics 1645, 1689, and 1697. |
| ETF prospectus governance disclosures | No document type, and no specific filing was named. Not ingested. |
| Tulip Trading [2023] EWCA Civ 83 | No document type. The judgment was not copied. |

**Spec.** The statement is `ingest/static/articles/bitcoin-core-relay-policy-2025-06-06.md` and a copy at `data/reference/bitcoin-core-relay-policy-2025-06-06.md`. The next article ingest will embed it. Production was not re-embedded in this pass. ETF and Tulip records are `data/reference/external_records.json` with `document_type: external_reference` and `ingested: false`. No URL was invented for a filing that was not named.

## 8. Node share

**Not verified. No figure was changed.**

`https://coin.dance/nodes` returned HTTP 200 on 2026-11-09 (228,702 bytes). The body does not contain `25.45` or `4.7`. The historical chart is `https://coin.dance/nodes/image/knots.png`, which was not OCR'd. `findings/data/node_share_retrieval.json` records that retrieval. PR 33453's `merged_at` in the enriched file is 2025-09-30T22:23:33Z. That is a merge timestamp, not a share. The articles that cite 4.7% and 25.45% were left as they are.

## 9. Reproduction

A clean machine can read the committed findings and the snapshot manifests. It cannot regenerate the banner counts by running the collectors, because the raw corpora are gitignored and a fresh collect will not match a frozen snapshot.

Shortest path to the figures in the banners for snapshot S1109, from a checkout of this branch:

```bash
git checkout gap-closure
python3 -c 'import json; print(json.load(open("findings/snapshots/S1109.json"))["counts"])'
python3 -m unittest tests.test_corpus_snapshots
python3 tests/test_gap_closure.py
```

Steps that are not in the repo:

- The gitignored dumps under `data/` (`prs_raw.jsonl`, `enriched_prs.jsonl`, IRC, Bitcointalk, mail). Rebuilding them needs a network, `GITHUB_TOKEN`, and hours, and the result will not equal S0910.
- The Bitcoin Core clone, if the trusted-keys history is regenerated instead of read from `findings/data/trusted_keys_events.json`.
- Cloudflare credentials, if the article and the findings markdown are to be embedded into the live index.
- A `.env` exists in the governance checkout. It was not read and is not required for the commands above.

---

## Also found

- 12 duplicate PR numbers in `prs_raw.jsonl`.
- 384 pull requests and 350 issues sit in the raw files and were never cleaned. They have authors.
- The working-tree Delving and mail manifests are newer than git HEAD and were not committed.
- `pr_type` still marks policy paths, and the word "policy", as consensus. PR 26890 is an example. The new field does not replace it.
- `analyze_pr.consensus_paths` still flags `src/validation`. `layer` does not, under `filenames-v1`.
- Intelligence `test/snapshot.test.ts` returns HTTP 402 on `assess_argument` because a minted key with a zero sat balance is blocked. That gate is on commit `50d30a34` and was not changed here.
- One non-empty day each on `#bitcoin-dev` and `#bitcoin-core` was not identified.
