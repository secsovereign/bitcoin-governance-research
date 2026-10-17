"""The ledger check fails on a mismatched number, a retracted claim, and a fragile interval."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from scripts.validation.claims_consistency import check_text

ROOT = Path(__file__).resolve().parents[1]


CLAIMS = [
    {
        "id": "roster",
        "sentence": "2,501 self-merges",
        "status": "CONFIRMED",
        "conflicts": ["1,127 of 2,501"],
        "fragile_markers": [],
    },
    {
        "id": "practice",
        "sentence": "rust-bitcoin and rust-miniscript show a practice that serves newcomers",
        "status": "RETRACTED",
        "conflicts": [],
        "fragile_markers": [],
    },
    {
        "id": "s1",
        "sentence": "S1 is fragile",
        "status": "FRAGILE",
        "conflicts": [],
        "fragile_markers": ["S1"],
    },
]


class ClaimsConsistencyTests(unittest.TestCase):
    def test_fixture_flags_mismatch_retraction_and_fragile_exclusion(self) -> None:
        text = "\n\n".join([
            "The file has 1,127 of 2,501 self-merges.",
            "rust-bitcoin and rust-miniscript show a practice that serves newcomers.",
            "S1 excludes zero on the fresh interval.",
        ])
        failures = check_text(text, CLAIMS, "fixture.md")
        joined = "\n".join(failures)
        self.assertIn("1,127 of 2,501", joined)
        self.assertIn("retracted", joined)
        self.assertIn("excluding zero", joined)

    def test_negation_and_retracted_label_are_allowed(self) -> None:
        text = "\n\n".join([
            "RETRACTED. rust-bitcoin and rust-miniscript show a practice that serves newcomers.",
            "S1 must not be described as excluding zero.",
        ])
        self.assertEqual(check_text(text, CLAIMS, "fixture.md"), [])

    def test_retraction_cites_the_refit_and_self_merge_names_the_control(self) -> None:
        from scripts.validation.claims_consistency import build_claims

        by_id = {claim["id"]: claim for claim in build_claims()}
        replacement = by_id["retract_last_place"]["replacement"]
        self.assertIn("-0.070", replacement)
        self.assertIn("rank 3 of 17", replacement)
        self.assertNotIn("rank 10 of 17", replacement)
        self.assertIn(
            "distinct-mergers control",
            by_id["self_merge_residual"]["sentence"],
        )

    def test_methodology_cites_the_committed_snapshot(self) -> None:
        from scripts.validation.claims_consistency import build_claims

        text = (ROOT / "findings" / "RESEARCH_METHODOLOGY.md").read_text(encoding="utf-8")
        by_id = {claim["id"]: claim["sentence"] for claim in build_claims()}
        for key in (
            "roster_self_merge",
            "revealed_self_merge",
            "e3_spearman",
            "satoshi_file",
            "identity_collapse",
        ):
            # The methodology states the same snapshot figures the ledger sentence states.
            for token in re.findall(r"\d[\d,]*(?:\.\d+)?", by_id[key]):
                token = token.rstrip(",")
                if token in {"0", "1"}:
                    continue
                self.assertIn(token, text, token)


if __name__ == "__main__":
    unittest.main()
