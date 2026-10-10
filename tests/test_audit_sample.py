"""Redaction and stratified draw. The corpus is not loaded."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.analysis.audit_sample import coder_bundle, redact_text, stratified_sample  # noqa: E402


class AuditSampleTest(unittest.TestCase):
    def test_redaction_strips_the_author_and_keeps_outcome_out_of_the_bundle(self) -> None:
        self.assertNotIn("fanquake", redact_text("Reviewed by fanquake", ["fanquake"]).lower())
        bundle = coder_bundle(
            "fanquake opened this and it merged",
            [{"filename": "src/a.cpp", "patch": "fanquake\n+int merged = 1;\n"}],
            ["fanquake"],
        )
        self.assertNotIn("author", bundle)
        self.assertNotIn("merged_by", bundle)
        self.assertNotIn("fanquake", json_blob := __import__("json").dumps(bundle).lower())
        self.assertIn("src/a.cpp", json_blob)

    def test_stratified_draw_does_not_exceed_a_year(self) -> None:
        people = [{"year": 2018, "author": f"a{i}"} for i in range(3)]
        people += [{"year": 2020, "author": f"b{i}"} for i in range(10)]
        drawn = stratified_sample(people, 5, np.random.default_rng(7))
        self.assertEqual(len(drawn), 5)
        self.assertLessEqual(sum(1 for row in drawn if row["year"] == 2018), 3)


if __name__ == "__main__":
    unittest.main()
