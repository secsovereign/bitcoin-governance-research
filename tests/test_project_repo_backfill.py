"""Shape of a comparison-repo detail record. No network."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.data_collection.project_repos_collector import normalize_detail  # noqa: E402


class DetailShapeTest(unittest.TestCase):
    def test_review_state_and_comment_path_match_the_core_schema(self) -> None:
        row = normalize_detail(
            7,
            "example/repo",
            [{"state": "APPROVED", "body": "ACK", "user": {"login": "a"}, "submitted_at": "2020-01-01T00:00:00Z"}],
            [{"body": "hello", "user": {"login": "b"}, "created_at": "2020-01-02T00:00:00Z"}],
            [{"body": "nit", "user": {"login": "c"}, "created_at": "2020-01-03T00:00:00Z", "path": "src/a.rs", "line": 4}],
            [{"filename": "src/a.rs", "additions": 1, "deletions": 0, "changes": 1, "status": "modified"}],
        )
        self.assertEqual(row["reviews"][0]["state"], "APPROVED")
        self.assertEqual(row["reviews"][0]["author"], "a")
        self.assertEqual(row["review_comments"][0]["path"], "src/a.rs")
        self.assertEqual(row["comments"][0]["author"], "b")
        self.assertEqual(row["files"][0]["filename"], "src/a.rs")
        self.assertNotIn("comments_count", row)

    def test_next_page_reads_the_link_header(self) -> None:
        from scripts.data_collection.project_repos_collector import next_page

        header = '<https://api.github.com/repos/a/b/pulls/1/comments?page=2>; rel="next", <https://api.github.com/repos/a/b/pulls/1/comments?page=4>; rel="last"'
        self.assertEqual(next_page(header), "https://api.github.com/repos/a/b/pulls/1/comments?page=2")
        self.assertIsNone(next_page(""))


if __name__ == "__main__":
    unittest.main()
