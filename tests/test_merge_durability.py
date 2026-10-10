"""Durability tracing on a synthetic repository. No Bitcoin Core checkout required."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.analysis.merge_durability import (  # noqa: E402
    apply_hunks,
    classify_path,
    horizon_censored,
    trace_merges,
)


def _git(repo: Path, *args: str, date: str = "") -> str:
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "Tester"
    env["GIT_AUTHOR_EMAIL"] = "tester@example.com"
    env["GIT_COMMITTER_NAME"] = "Tester"
    env["GIT_COMMITTER_EMAIL"] = "tester@example.com"
    if date:
        env["GIT_AUTHOR_DATE"] = date
        env["GIT_COMMITTER_DATE"] = date
    proc = subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True, env=env)
    return proc.stdout.strip()


def _init(repo: Path) -> None:
    _git(repo, "init", "-b", "master")
    _git(repo, "config", "user.email", "tester@example.com")
    _git(repo, "config", "user.name", "Tester")


def _write(repo: Path, path: str, text: str) -> None:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)


class DurabilityRulesTest(unittest.TestCase):
    def test_censor_when_horizon_passes_the_tip(self) -> None:
        merge = 1_600_000_000.0
        self.assertTrue(horizon_censored(merge, 12, merge + 86400 * 30))
        self.assertFalse(horizon_censored(merge, 12, merge + 86400 * 400))

    def test_path_classes(self) -> None:
        self.assertEqual(classify_path("src/validation.cpp"), "production")
        self.assertEqual(classify_path("src/test/util_tests.cpp"), "test")
        self.assertEqual(classify_path("doc/release-notes.md"), "docs_build")

    def test_hunks_shift_surviving_lines(self) -> None:
        live = {1: {"id": "a"}, 2: {"id": "b"}, 3: {"id": "c"}}
        updated, removed = apply_hunks(live, [{"old_start": 1, "old_count": 0, "new_count": 1}])
        self.assertEqual(removed, [])
        self.assertEqual(updated[1]["id"], "a")
        self.assertEqual(updated[3]["id"], "b")
        deleted, gone = apply_hunks({1: {"id": "a"}, 2: {"id": "b"}, 3: {"id": "c"}}, [{"old_start": 2, "old_count": 1, "new_count": 0}])
        self.assertEqual([row["id"] for row in gone], ["b"])
        self.assertEqual(deleted[2]["id"], "c")


class SyntheticRepoTest(unittest.TestCase):
    def test_survival_revert_fix_refactor_and_censor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _init(repo)
            _write(repo, "src/main.cpp", "alpha\n")
            _git(repo, "add", "src/main.cpp")
            _git(repo, "commit", "-m", "base", date="2018-01-01T00:00:00")

            def merge_line(branch: str, path: str, line: str, message: str, date: str) -> str:
                _git(repo, "checkout", "-b", branch)
                current = (repo / path).read_text() if (repo / path).exists() else ""
                _write(repo, path, current + line + "\n")
                _git(repo, "add", path)
                _git(repo, "commit", "-m", message, date=date)
                _git(repo, "checkout", "master")
                _git(repo, "merge", "--no-ff", branch, "-m", f"Merge {message}", date=date)
                return _git(repo, "rev-parse", "HEAD")

            survive = merge_line("s", "src/main.cpp", "beta", "add beta", "2018-01-02T00:00:00")
            parent = _git(repo, "rev-parse", "HEAD^1")
            second = _git(repo, "rev-parse", "HEAD^2")
            revert_sha = merge_line("r", "src/other.cpp", "gamma", "add gamma", "2018-02-01T00:00:00")
            _write(repo, "src/other.cpp", "")
            _git(repo, "add", "src/other.cpp")
            _git(
                repo, "commit", "-m",
                f"Revert \"add gamma\"\n\nThis reverts commit {revert_sha}.",
                date="2018-03-01T00:00:00",
            )
            fix_sha = merge_line("f", "src/fix.cpp", "delta", "add delta", "2018-04-01T00:00:00")
            _write(repo, "src/fix.cpp", "delta-fixed\n")
            _git(repo, "add", "src/fix.cpp")
            _git(repo, "commit", "-m", "fix crash in parser", date="2018-05-01T00:00:00")
            refactor_sha = merge_line("c", "src/churn.cpp", "epsilon", "add epsilon", "2018-06-01T00:00:00")
            _write(repo, "src/churn.cpp", "")
            _git(repo, "add", "src/churn.cpp")
            _git(repo, "commit", "-m", "move helper out of the file", date="2018-07-01T00:00:00")
            _write(repo, "src/test_only.cpp", "")
            late = merge_line("late", "src/late.cpp", "zeta", "add zeta", "2020-03-01T00:00:00")
            _write(repo, "doc/notes.md", "done\n")
            _git(repo, "add", "doc/notes.md")
            _git(repo, "commit", "-m", "notes", date="2020-06-01T00:00:00")
            tip = float(_git(repo, "log", "-1", "--format=%ct"))

            def meta(sha: str, pr: int) -> dict:
                first = _git(repo, "rev-parse", f"{sha}^1")
                second_parent = _git(repo, "rev-parse", f"{sha}^2")
                when = float(_git(repo, "log", "-1", "--format=%ct", sha))
                return {"pr": pr, "time": when, "shas": [sha, second_parent, first]}

            traced = trace_merges(repo, {
                survive: meta(survive, 10),
                revert_sha: meta(revert_sha, 11),
                fix_sha: meta(fix_sha, 12),
                refactor_sha: meta(refactor_sha, 13),
                late: meta(late, 14),
            }, tip)

            self.assertEqual(traced[10]["horizons"]["12"]["survival"], 1.0)
            self.assertEqual(traced[10]["horizons"]["12"]["fix_forward"], 0)
            self.assertEqual(traced[10]["horizons"]["12"]["revert"], 0)
            self.assertEqual(traced[11]["horizons"]["12"]["revert"], 1)
            self.assertEqual(traced[11]["horizons"]["12"]["survival"], 0.0)
            self.assertEqual(traced[12]["horizons"]["12"]["fix_forward"], 1)
            self.assertEqual(traced[12]["horizons"]["12"]["neutral_lines"], 0)
            self.assertEqual(traced[13]["horizons"]["12"]["fix_forward"], 0)
            self.assertEqual(traced[13]["horizons"]["12"]["revert"], 0)
            self.assertGreater(traced[13]["horizons"]["12"]["neutral_lines"], 0)
            self.assertEqual(traced[13]["horizons"]["12"]["survival"], 0.0)
            self.assertTrue(traced[14]["horizons"]["12"]["censored"])
            self.assertNotIn("survival", traced[14]["horizons"]["12"])
            self.assertIsNotNone(parent)
            self.assertIsNotNone(second)


if __name__ == "__main__":
    unittest.main()
