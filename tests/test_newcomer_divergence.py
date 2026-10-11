"""Newcomer divergence estimator. The interaction sign is fixed before any repository is scored."""

from __future__ import annotations

import unittest

import numpy as np

from scripts.analysis.newcomer_divergence import classify, score_frame


def _rows():
    created = []
    outcome = []
    authors = []
    # Incumbents start in 2010 and stay. Their merge rate rises.
    for author in range(40):
        for year in range(2010, 2021):
            created.append(float(np.datetime64(f"{year}-06-01", "s").astype(np.int64)))
            rate = 0.40 + 0.03 * (year - 2010)
            outcome.append(1 if (author + year) % 100 < rate * 100 else 0)
            authors.append(f"old-{author}")
    # A new cohort each year, one pull request, merge rate falls.
    for year in range(2010, 2021):
        rate = 0.70 - 0.04 * (year - 2010)
        for author in range(40):
            created.append(float(np.datetime64(f"{year}-07-01", "s").astype(np.int64)))
            outcome.append(1 if author < rate * 40 else 0)
            authors.append(f"new-{year}-{author}")
    return np.asarray(created), np.asarray(outcome), authors


class NewcomerDivergenceTests(unittest.TestCase):
    def test_interaction_is_negative_when_newcomers_fall_and_incumbents_rise(self) -> None:
        scored = score_frame(*_rows(), np.random.default_rng(7), 200)
        block = scored["interaction"]
        self.assertLess(block["estimate"], 0)
        self.assertLess(block["ci95"][1], 0)
        self.assertGreater(scored["incumbent_slope"]["estimate"], 0)
        self.assertLess(scored["newcomer_slope"]["estimate"], 0)

    def test_classification_follows_the_written_rule(self) -> None:
        core = {"interaction": {"estimate": -0.03, "ci95": [-0.04, -0.02]}}
        quiet = {"interaction": {"estimate": -0.01, "ci95": [-0.05, 0.02]}}
        opposite = {"interaction": {"estimate": 0.02, "ci95": [0.01, 0.03]}}
        confirmed = {"interaction": {"estimate": -0.02, "ci95": [-0.03, -0.01]}}
        self.assertEqual(classify(core, [quiet, opposite]), "CORE-SPECIFIC")
        self.assertEqual(classify(core, [confirmed, quiet]), "AMBIENT")
        self.assertEqual(classify({"interaction": {"estimate": -0.01, "ci95": [-0.03, 0.01]}}, [confirmed]), "UNDETERMINED")


if __name__ == "__main__":
    unittest.main()
