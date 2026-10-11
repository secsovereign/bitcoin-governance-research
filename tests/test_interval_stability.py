"""FRAGILE means the published interval and a fresh bootstrap do not agree, or the bound is close to zero."""

from __future__ import annotations

import unittest

from scripts.validation.interval_stability import stability


class IntervalStabilityTests(unittest.TestCase):
    def test_disagreement_on_zero_is_fragile(self) -> None:
        self.assertEqual(stability([-0.369, -0.009], [-0.385, 0.006], "coefficient"), "FRAGILE")

    def test_correlation_bound_within_0_02_is_fragile(self) -> None:
        self.assertEqual(stability([-0.743, -0.002], [-0.80, -0.05], "correlation"), "FRAGILE")

    def test_a_clear_interval_that_still_excludes_zero_is_stable(self) -> None:
        self.assertEqual(stability([-0.040, -0.033], [-0.041, -0.032], "coefficient"), "STABLE")


if __name__ == "__main__":
    unittest.main()
