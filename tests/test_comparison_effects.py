"""Comparison-repo effect wiring. Uses the commons estimators on a tiny dump."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.analysis.comparison_effects import classify_effect, score_repo  # noqa: E402


def _pr(number: int, author: str, created: str, reviews: list) -> dict:
    return {
        "number": number,
        "author": author,
        "title": "change parser",
        "body": "",
        "state": "closed",
        "created_at": created,
        "closed_at": "2020-02-01T00:00:00Z",
        "merged": True,
        "merged_at": "2020-02-01T00:00:00Z",
        "reviews": reviews,
        "comments": [],
        "review_comments": [],
        "files": [{"filename": "src/a.c", "additions": 3, "deletions": 1, "changes": 4, "status": "modified"}],
        "total_additions": 3,
        "total_deletions": 1,
        "total_files_changed": 1,
    }


class ComparisonEffectTest(unittest.TestCase):
    def test_classification_rule(self) -> None:
        outside = [{"estimate": 0.2, "ci95": [-0.1, 0.4]}]
        self.assertEqual(classify_effect(0.4, [0.1, 0.7], outside, [-0.2, 0.3]), "CORE-SPECIFIC")
        tracking = [{"estimate": 0.2, "ci95": [0.05, 0.4]}]
        self.assertEqual(classify_effect(0.4, [0.1, 0.7], tracking, [-0.8, -0.1]), "TRACKS HEALTH")
        ambient = [
            {"estimate": 0.2, "ci95": [0.05, 0.5]},
            {"estimate": 0.1, "ci95": [-0.2, 0.4]},
        ]
        self.assertEqual(classify_effect(0.4, [0.1, 0.7], ambient, [-0.2, 0.3]), "AMBIENT")

    def test_e3_stays_unavailable_without_merged_by(self) -> None:
        rows = [
            _pr(1, "ada", "2020-01-01T00:00:00Z", [
                {"author": "bea", "state": "APPROVED", "body": "ACK", "submitted_at": "2020-01-02T00:00:00Z"},
            ]),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prs.jsonl"
            path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
            scored = score_repo(path, np.random.default_rng(7), n_boot=20, n_perm=10)
        effect = scored["effects"]["E3_log_hours_to_next_same_direction_top5_minus_other"]
        self.assertEqual(effect["status"], "DATA UNAVAILABLE")
        self.assertIn("merged_by", effect["reason"])
        self.assertIsNone(effect["estimate"])

    def test_unidentified_ingroup_is_not_coded_as_a_scored_out_group(self) -> None:
        reviews = [
            {"author": f"r{i}", "state": "COMMENTED", "body": "looks fine", "submitted_at": "2019-06-01T00:00:00Z"}
            for i in range(5)
        ]
        rows = [_pr(1, "ada", "2020-01-01T00:00:00Z", reviews)]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prs.jsonl"
            path.write_text(json.dumps(rows[0]) + "\n")
            scored = score_repo(path, np.random.default_rng(7), n_boot=20, n_perm=10)
        self.assertGreater(scored["n_unidentified"], 0)
        e12 = scored["effects"]["E12_ingroup_on_no_peer_response"]
        self.assertNotEqual(e12.get("estimate"), 1)

    def test_fewer_than_six_repositories_has_no_interval(self) -> None:
        from scripts.analysis.comparison_effects import correlation_for_effect

        fit = correlation_for_effect(
            np.asarray([0.1, 0.2, 0.3, 0.4, 0.5]),
            np.asarray([1.0, 2.0, 3.0, 4.0, 5.0]),
            np.random.default_rng(7),
            20,
        )
        self.assertEqual(fit["status"], "DATA UNAVAILABLE")
        self.assertIsNone(fit["ci95"])
        self.assertIsNone(fit["estimate"])

    def test_degenerate_draws_are_counted(self) -> None:
        from scripts.analysis.comparison_effects import correlation_for_effect, degenerate_draw

        self.assertTrue(degenerate_draw(np.asarray([1.0, 1.0, 2.0, 3.0]), np.asarray([1.0, 2.0, 3.0, 4.0])))
        x = np.asarray([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        y = np.asarray([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        fit = correlation_for_effect(x, y, np.random.default_rng(7), 50)
        self.assertEqual(fit["status"], "ok")
        self.assertGreaterEqual(fit["n_degenerate"], 0)
        self.assertLessEqual(fit["degenerate_share"], 1)


if __name__ == "__main__":
    unittest.main()
