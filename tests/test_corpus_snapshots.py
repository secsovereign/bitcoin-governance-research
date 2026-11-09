"""Banner citations, coverage, layers, and consequence records.

These checks read committed JSON. They do not load the gitignored corpora,
except the cryptography raw directory when it happens to be present.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.validation.snapshot_manifests import check_citations
from src.utils.coverage import month_names, prehistory_coverage
from src.utils.pr_layer import classify_filenames

ROOT = Path(__file__).resolve().parents[1]


class CorpusSnapshotTests(unittest.TestCase):
    def test_banner_citations_match_manifests(self) -> None:
        self.assertEqual(check_citations(), [])

    def test_a_disagreement_fails(self) -> None:
        from scripts.validation import snapshot_manifests as mod

        original = mod.load_snapshot

        def broken(snapshot_id: str):
            data = original(snapshot_id)
            if snapshot_id == "S1109":
                data = json.loads(json.dumps(data))
                data["counts"]["irc_messages"] = 1
            return data

        mod.load_snapshot = broken
        try:
            failures = check_citations()
        finally:
            mod.load_snapshot = original
        self.assertTrue(any("irc_messages" in item for item in failures))

    def test_cryptography_window_is_32_of_48(self) -> None:
        report = json.loads((ROOT / "findings/data/coverage_report.json").read_text(encoding="utf-8"))
        crypto = report["sources"]["cryptography"]
        self.assertEqual(crypto["expected"], 48)
        self.assertEqual(crypto["ingested"], 32)
        self.assertEqual(len(crypto["missing"]), 16)
        expected = month_names((2008, 1), (2011, 12))
        present = [name for name in expected if name not in crypto["missing"]]
        self.assertEqual(prehistory_coverage(present)["ingested"], 32)
        raw = ROOT / "data/mailing_lists/cryptography_raw"
        if raw.exists():
            names = [path.name for path in raw.iterdir()]
            self.assertEqual(prehistory_coverage(names)["missing"], crypto["missing"])

    def test_op_return_prs_are_relay_policy(self) -> None:
        summary = json.loads((ROOT / "findings/data/pr_layer_summary.json").read_text(encoding="utf-8"))
        for number in ("32359", "32381", "32406", "32714", "33224", "33453"):
            self.assertEqual(summary["examples"][number]["primary"], "relay_policy")
            again = classify_filenames(summary["examples"][number]["files"])
            self.assertEqual(again["primary"], "relay_policy")
            self.assertNotIn("consensus", again["layers"])

    def test_policy_path_is_not_consensus(self) -> None:
        got = classify_filenames(["src/policy/policy.cpp", "src/policy/policy.h"])
        self.assertEqual(got["primary"], "relay_policy")

    def test_consensus_path_stays_consensus(self) -> None:
        got = classify_filenames(["src/consensus/params.h", "src/test/sanity_tests.cpp"])
        self.assertEqual(got["primary"], "consensus")

    def test_key_list_is_not_the_23_logins(self) -> None:
        events = json.loads((ROOT / "findings/data/trusted_keys_events.json").read_text(encoding="utf-8"))
        self.assertIn("not this gpg list", events["not_the_23_logins"].lower())
        removals = [row for row in events["events"] if row["action"] == "remove"]
        self.assertGreaterEqual(len(removals), 1)
        subjects = " ".join(row["subject"].lower() for row in events["events"])
        self.assertIn("laanwj", subjects)
        self.assertIn("glozow", subjects)

    def test_consequences_keep_allegation_thin(self) -> None:
        data = json.loads((ROOT / "findings/data/applied_consequences.json").read_text(encoding="utf-8"))
        mechanic = data["allegations"][0]
        self.assertEqual(mechanic["evidence_tier"], "allegation")
        self.assertTrue(mechanic["thin"])
        self.assertIsNone(mechanic["actor"])
        kinds = {row["kind"] for row in data["applied"]}
        self.assertEqual(kinds, {"key_removal"})

    def test_closed_unmerged_is_not_split_into_rejected(self) -> None:
        metrics = json.loads((ROOT / "findings/data/metric_kinds.json").read_text(encoding="utf-8"))
        closed = metrics["closed_unmerged"]
        self.assertIsNone(closed["rejected"])
        self.assertIsNone(closed["withdrawn"])
        self.assertEqual(closed["draft"] + closed["not_draft"], closed["n"])
        self.assertTrue(metrics["funding_mentions"]["floor"])
        self.assertTrue(metrics["resolution_times_2026"]["right_censored"])
        text = (ROOT / "findings/ENHANCED_FUNDING_ANALYSIS_REPORT.md").read_text(encoding="utf-8")
        self.assertIn("floor", text)
        method = (ROOT / "findings/RESEARCH_METHODOLOGY.md").read_text(encoding="utf-8")
        self.assertIn("right-censored", method)

    def test_publication_batches_list_files_and_invent_no_counts(self) -> None:
        from scripts.validation.snapshot_manifests import check_publication_ids

        self.assertEqual(check_publication_ids(), [])
        ledger = (ROOT / "findings/CLAIMS_LEDGER.md").read_text(encoding="utf-8")
        self.assertIn("| S0920 |", ledger)
        self.assertIn("| S0923 |", ledger)

    def test_recomputed_email_total_keeps_the_old_formula(self) -> None:
        old = json.loads((ROOT / "findings/snapshots/S0910.json").read_text(encoding="utf-8"))
        new = json.loads((ROOT / "findings/snapshots/S1109.json").read_text(encoding="utf-8"))
        self.assertEqual(old["counts"]["emails_deduped_cited"], 51062)
        self.assertEqual(old["emails_deduped_formula"], "24644 + 26420 - 2 = 51062")
        self.assertEqual(new["counts"]["emails_deduped"], 51078)

    def test_outside_rebuild_is_not_adopted(self) -> None:
        data = json.loads((ROOT / "findings/data/outside_rebuild_comparison.json").read_text(encoding="utf-8"))
        self.assertFalse(data["matched"])
        self.assertEqual(data["deltas"]["prs_lines"]["delta"], 2)

    def test_dossier_sample_records_misses_without_changing_erlay(self) -> None:
        data = json.loads((ROOT / "findings/data/dossier_label_sample.json").read_text(encoding="utf-8"))
        self.assertEqual(data["stored_rows"], 160)
        self.assertEqual(data["hits"] + data["misses"], 160)
        erlay = [row for row in data["rows"] if row["number"] == 30233][0]
        self.assertEqual(erlay["label"], "miss")
        self.assertIn("not recomputed", data["published_figures_unchanged"])

    def test_mechanic_stays_a_thin_allegation(self) -> None:
        data = json.loads((ROOT / "findings/data/applied_consequences.json").read_text(encoding="utf-8"))
        mechanic = data["allegations"][0]
        self.assertTrue(mechanic["thin"])
        self.assertEqual(mechanic["evidence_tier"], "allegation")
        self.assertIn("argument-map", mechanic["source"])
        self.assertFalse(mechanic["dossier_in_corpus"])

    def test_external_references_are_not_filled(self) -> None:
        data = json.loads((ROOT / "data/reference/external_records.json").read_text(encoding="utf-8"))
        self.assertTrue(all(row["ingested"] is False for row in data["records"]))
