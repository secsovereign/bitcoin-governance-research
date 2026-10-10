"""Leave-one-out residual on a synthetic size line. Does not read the corpora."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.analysis.size_adjusted_health import loo_residual  # noqa: E402


class LeaveOneOutTest(unittest.TestCase):
    def test_low_health_large_repo_has_a_negative_residual(self) -> None:
        rows = []
        for i in range(8):
            rows.append({
                "repo": f"r{i}",
                "health": 0.5 + 0.02 * i,
                "log_total_prs": float(i + 1),
                "log_mean_annual_authors": 1.0,
                "years_of_history": 8,
            })
        rows.append({
            "repo": "bitcoin/bitcoin",
            "health": 0.2,
            "log_total_prs": 9.0,
            "log_mean_annual_authors": 1.0,
            "years_of_history": 8,
        })
        fit = loo_residual(rows, len(rows) - 1, np.random.default_rng(7), n_boot=50)
        self.assertEqual(fit["status"], "ok")
        self.assertLess(fit["residual"], 0)
        self.assertTrue(fit["low_power"])


if __name__ == "__main__":
    unittest.main()
