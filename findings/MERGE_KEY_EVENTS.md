# Trusted-keys history

The structured record is `findings/data/trusted_keys_events.json`. It is the git history of `bitcoin/bitcoin` `contrib/verify-commits/trusted-keys`, read at commit `f0de87f040` on 2026-11-09. Each row is a commit: date, author, subject, fingerprints added, fingerprints removed, and the commit URL.

The 23 merge-key logins in `data/maintainers/merge_capability.json` are observed `merged_by` values. They are not this GPG list, and this history cannot generate them.

Nominations that were not merged stay pull requests: 25560, 25871, 26868, and 17094. Objections stored with those rows are excerpts from the thread, not a new paraphrase.

Applied consequences are `findings/data/applied_consequences.json`. A key removal is a first-party git event. The commit subjects do not cite a written rule, so `rule_cited` is false and the reason is marked thin. Pull requests 7243 and 26890 and issue 29507 are proposals, not applied sanctions. The ban attributed to Mechanic is an allegation: the tweet is not in the corpus, the actor is empty, and the row is thin. A moderation dossier dated 2024-08-14 was not found in the corpus.
