"""Task 1 helpers. The full merged_by estimate is not computed here."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.analysis.pass7_merged_by import (
    FAMILY_ID,
    e3_family_test,
    prior_pass6_tests,
    shared_health_means,
)
from src.utils.paths import get_findings_dir

ROOT = Path(__file__).resolve().parents[1]


class Pass7Task1Tests(unittest.TestCase):
    def test_shared_health_matches_published_means_when_h4_is_unchanged(self) -> None:
        commons = json.loads((ROOT / "findings" / "data" / "commons_dynamics_analysis.json").read_text())
        got = shared_health_means(commons["repo_year_table"])
        for row in commons["cross_repo_ranking"]:
            published = row.get("mean_health")
            if published is None:
                continue
            self.assertAlmostEqual(got[row["repo"]], published, places=9)

    def test_family_entry_is_only_the_spearman_test(self) -> None:
        self.assertIsNone(e3_family_test({"status": "DATA UNAVAILABLE", "p": None}))
        test = e3_family_test({"status": "ok", "estimate": 0.2, "ci95": [-0.1, 0.4], "p": 0.2, "n": 8})
        self.assertEqual(test["id"], FAMILY_ID)
        self.assertTrue(test["in_bh_family"])
        self.assertEqual(test["predicted_sign"], "positive")
        self.assertNotIn("repo", test)

    def test_pass6_tests_are_the_ones_already_in_the_family(self) -> None:
        rows = prior_pass6_tests(get_findings_dir())
        self.assertGreaterEqual(len(rows), 50)
        self.assertTrue(all(row.get("in_bh_family") and row.get("p") is not None for row in rows))
        self.assertTrue(all(str(row.get("id", "")).startswith("pass6.") for row in rows))


if __name__ == "__main__":
    unittest.main()
