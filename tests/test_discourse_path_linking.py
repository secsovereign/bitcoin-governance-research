"""Known true and false path links. No corpus scan."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.analysis.discourse_path_linking import (  # noqa: E402
    DAY,
    PullWindow,
    index_pulls,
    link_message,
    path_only_hits,
)


def _pulls():
    opened = 1_600_000_000.0
    pulls = [
        PullWindow(1, opened, opened + 10 * DAY, {"src/wallet/fees.cpp", "fees.cpp"}, {"RefreshFee"}, "fee refresh"),
        PullWindow(2, opened, opened + 10 * DAY, {"src/net.cpp"}, {"OtherName"}, "net tweak"),
    ]
    return pulls, index_pulls(pulls), {s for p in pulls for s in p.symbols}


class PathLinkerTest(unittest.TestCase):
    def test_true_path_and_false_path(self) -> None:
        pulls, index, symbols = _pulls()
        opened = pulls[0].opened
        _nums, hits = link_message("please see src/wallet/fees.cpp", opened + DAY, pulls, index, symbols)
        self.assertEqual(hits, {1})
        _nums, hits = link_message("please see src/net.cpp", opened + DAY, pulls, index, symbols)
        self.assertEqual(hits, {2})

    def test_censor_after_close_plus_14_days(self) -> None:
        pulls, index, symbols = _pulls()
        late = pulls[0].closed + 15 * DAY
        _nums, hits = link_message("src/wallet/fees.cpp", late, pulls, index, symbols)
        self.assertEqual(hits, set())

    def test_symbol_true_and_false(self) -> None:
        pulls, index, symbols = _pulls()
        opened = pulls[0].opened
        _nums, hits = link_message("RefreshFee is too high", opened + 2 * DAY, pulls, index, symbols)
        self.assertEqual(hits, {1})
        _nums, hits = link_message("OtherName only", opened + 2 * DAY, pulls, index, symbols)
        self.assertEqual(hits, {2})

    def test_number_match_is_not_counted_as_a_new_path_link(self) -> None:
        pulls, index, symbols = _pulls()
        opened = pulls[0].opened
        nums, hits = link_message("see #1001 and src/wallet/fees.cpp", opened + DAY, pulls, index, symbols)
        self.assertIn(1001, nums)
        self.assertEqual(path_only_hits(nums, hits), {1})


if __name__ == "__main__":
    unittest.main()
