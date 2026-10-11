"""Pass 7 addendum rules. No self-merge rate and no E3 estimate are computed here."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import numpy as np

from scripts.analysis.comparison_effects import MIN_SPEARMAN_REPOS
from scripts.analysis.pass7_rules import (
    H4_PUBLISHED_BASIS,
    MERGED_BY_COMPLETENESS,
    MIN_REPOS_FOR_SPEARMAN,
    MIN_WINDOW_MERGERS,
    SELF_MERGE_CONTROLS,
    coverage_from_rows,
    e3_correlation_gate,
    e3_repository_gate,
    repositories_below_bar,
    self_merge_design,
)

ROOT = Path(__file__).resolve().parents[1]


class Pass7RuleTests(unittest.TestCase):
    def test_self_merge_design_adds_log_distinct_mergers(self) -> None:
        self.assertEqual(
            SELF_MERGE_CONTROLS,
            (
                "log_total_prs",
                "log_mean_annual_authors",
                "years_of_history",
                "log_mean_distinct_mergers_per_year",
            ),
        )
        design = self_merge_design([
            {
                "log_total_prs": 1.0,
                "log_mean_annual_authors": 2.0,
                "years_of_history": 7.0,
                "log_mean_distinct_mergers_per_year": 0.5,
            },
            {
                "log_total_prs": 3.0,
                "log_mean_annual_authors": 4.0,
                "years_of_history": 11.0,
                "log_mean_distinct_mergers_per_year": 1.5,
            },
        ])
        self.assertEqual(design.shape, (2, 5))
        self.assertTrue(np.allclose(design[:, 0], 1))
        self.assertTrue(np.allclose(design[:, 4], [0.5, 1.5]))

    def test_e3_needs_five_mergers_and_six_repositories(self) -> None:
        self.assertEqual(MIN_WINDOW_MERGERS, 5)
        self.assertEqual(MIN_REPOS_FOR_SPEARMAN, 6)
        self.assertEqual(MIN_REPOS_FOR_SPEARMAN, MIN_SPEARMAN_REPOS)
        blocked = e3_repository_gate(n_considered=40, n_window_at_least_5=0)
        self.assertEqual(blocked["status"], "DATA UNAVAILABLE")
        self.assertIsNone(blocked["estimate"])
        self.assertIsNone(blocked["ci95"])
        self.assertIn("5 distinct mergers", blocked["reason"])
        kept = e3_repository_gate(n_considered=40, n_window_at_least_5=10)
        self.assertEqual(kept["status"], "ok")
        self.assertAlmostEqual(kept["share_window_at_least_5"], 0.25)
        correlation = e3_correlation_gate(5)
        self.assertEqual(correlation["status"], "DATA UNAVAILABLE")
        self.assertEqual(correlation["class"], "UNDETERMINED")
        self.assertIsNone(correlation["ci95"])
        self.assertEqual(e3_correlation_gate(6)["status"], "ok")

    def test_completeness_bar_waits_until_the_crawl_ends(self) -> None:
        self.assertEqual(MERGED_BY_COMPLETENESS, 0.95)
        partial = coverage_from_rows(
            [1, 2, 3, 4],
            [{"number": 1, "merged_by": "a", "merged_by_id": 10}],
        )
        self.assertFalse(partial["crawl_ended"])
        self.assertFalse(partial["below_completeness_bar"])
        self.assertEqual(repositories_below_bar([{"slug": "a/b", **partial}]), [])
        thin = coverage_from_rows(
            [1, 2, 3, 4],
            [
                {"number": 1, "merged_by": "a", "merged_by_id": 10},
                {"number": 2, "merged_by": None, "merged_by_id": None},
                {"number": 3, "missing": True},
                {"number": 4, "merged_by": None, "merged_by_id": None},
            ],
        )
        self.assertTrue(thin["crawl_ended"])
        self.assertEqual(thin["with_merged_by"], 1)
        self.assertEqual(thin["with_numeric_user_id"], 1)
        self.assertEqual(thin["no_longer_served"], 1)
        self.assertTrue(thin["below_completeness_bar"])
        self.assertEqual(repositories_below_bar([{"slug": "a/b", **thin}]), ["a/b"])

    def test_published_h4_counts_authors(self) -> None:
        self.assertEqual(H4_PUBLISHED_BASIS, "authors")

    def test_section_c_numbers_match_committed_json(self) -> None:
        findings = ROOT / "findings" / "data"
        divergence = json.loads((findings / "newcomer_divergence.json").read_text())
        effects = json.loads((findings / "comparison_effects.json").read_text())
        stability = json.loads((findings / "interval_stability.json").read_text())
        core = divergence["core"]
        interaction = core["interaction"]
        self.assertEqual(core["driver"], "BOTH")
        self.assertAlmostEqual(interaction["estimate"] * 100, -3.7, places=1)
        self.assertEqual(divergence["negative_points_before_slope_gate"], {"negative": 7, "eligible": 12})
        self.assertEqual(divergence["negative_points_after_slope_gate"], {"negative": 5, "eligible": 9})
        self.assertEqual(divergence["classification"], "AMBIENT")
        self.assertFalse(divergence["in_bh_family"])
        self.assertEqual(
            divergence["driver_counts"],
            {"INCUMBENT GAIN": 1, "BOTH": 1, "INCUMBENT DECLINE": 2, "UNRESOLVED": 5},
        )
        by_slug = {row["slug"]: row for row in divergence["repositories"]}
        self.assertEqual(by_slug["bitcoin-core/secp256k1"]["driver"], "INCUMBENT GAIN")
        self.assertEqual(by_slug["bitcoindevkit/bdk"]["driver"], "BOTH")
        self.assertEqual(by_slug["lightningdevkit/rust-lightning"]["driver"], "INCUMBENT DECLINE")
        self.assertEqual(by_slug["ElementsProject/lightning"]["driver"], "INCUMBENT DECLINE")
        self.assertEqual(by_slug["lightningnetwork/lnd"]["driver"], "UNRESOLVED")
        self.assertEqual(by_slug["ACINQ/eclair"]["driver"], "UNRESOLVED")
        self.assertEqual(by_slug["rust-bitcoin/rust-bitcoin"]["driver"], "UNRESOLVED")
        self.assertEqual(by_slug["rust-bitcoin/rust-miniscript"]["driver"], "UNRESOLVED")
        link = divergence["health_link"]
        self.assertAlmostEqual(link["estimate"], 0.370, places=3)
        self.assertLessEqual(link["ci95"][0], 0)
        self.assertGreaterEqual(link["ci95"][1], 0)
        self.assertTrue(link["exploratory"])
        self.assertFalse(link["in_bh_family"])
        self.assertEqual(divergence["logins_collapsed"], 0)
        e12 = effects["classifications"]["E12_ingroup_on_no_peer_response"]
        self.assertEqual(e12["class"], "AMBIENT")
        self.assertTrue(e12["bound_touches_extreme"])
        self.assertAlmostEqual(e12["degenerate_share"], 0.005)
        fragile = set(stability["fragile"])
        self.assertIn("capacity_S1_irc_linked", fragile)
        self.assertIn("volume_spearman.H6_median_days_to_decision", fragile)
        by_id = {row["id"]: row["status"] for row in stability["estimates"]}
        self.assertEqual(by_id["volume_spearman.H4_gini_merges"], "STABLE")
        self.assertEqual(by_id["newcomer_merge_interaction"], "STABLE")


if __name__ == "__main__":
    unittest.main()
