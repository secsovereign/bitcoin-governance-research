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

    def test_external_references_are_not_filled(self) -> None:
        data = json.loads((ROOT / "data/reference/external_records.json").read_text(encoding="utf-8"))
        self.assertTrue(all(row["ingested"] is False for row in data["records"]))
