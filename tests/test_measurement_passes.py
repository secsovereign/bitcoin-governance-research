"""The measurement runner stays in pass order and does not call generate_all."""

from __future__ import annotations

import unittest

from scripts.run_measurement_passes import PASSES, commands


class MeasurementPassTests(unittest.TestCase):
    def test_passes_run_from_1_through_7_without_generate_all(self) -> None:
        numbers = [block["pass"] for block in PASSES]
        self.assertEqual(numbers, [1, 3, 4, 5, 6, 7])
        self.assertEqual(PASSES[0]["also_writes_pass"], 2)
        flat = commands()
        self.assertGreaterEqual(len(flat), 10)
        self.assertTrue(flat[0][1].endswith("rsd_ingroup_test.py"))
        self.assertTrue(flat[-1][1].endswith("pass7_merged_by.py"))
        joined = " ".join(" ".join(cmd) for cmd in flat)
        self.assertNotIn("generate_all", joined)
        self.assertNotIn("generate_from_templates", joined)


if __name__ == "__main__":
    unittest.main()
