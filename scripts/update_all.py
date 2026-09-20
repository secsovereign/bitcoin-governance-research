#!/usr/bin/env python3
"""
Incremental update: collect only new/changed records since the last run.

Each collector implements delta logic (git fetch + diff, skip-existing IDs,
recent-board scan, etc.). Re-run safely anytime.

Usage:
    python scripts/update_all.py                 # all sources
    python scripts/update_all.py --github-only   # GitHub PRs/issues/commits only
    python scripts/update_all.py --process       # also clean/enrich new GitHub rows
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.paths import get_data_dir


def run(script: str, *args: str) -> int:
    cmd = [sys.executable, str(project_root / script), *args]
    print(f"\n>>> {' '.join(cmd)}")
    return subprocess.call(cmd, cwd=str(project_root))


def main() -> int:
    parser = argparse.ArgumentParser(description="Incrementally update collected datasets")
    parser.add_argument("--github-only", action="store_true")
    parser.add_argument("--skip-github", action="store_true")
    parser.add_argument("--skip-forums", action="store_true", help="Skip Delving + Bitcointalk")
    parser.add_argument("--skip-mail", action="store_true", help="Skip gnusha + cryptography lists")
    parser.add_argument("--skip-irc", action="store_true")
    parser.add_argument("--process", action="store_true", help="Clean/enrich only new GitHub rows")
    args = parser.parse_args()

    failed: list[str] = []
    data = get_data_dir()

    if not args.skip_mail and not args.github_only:
        if run("scripts/data_collection/gnusha_collector.py", "--update") != 0:
            failed.append("gnusha")
        if run("scripts/data_collection/cryptography_ml_collector.py", "--update") != 0:
            failed.append("cryptography")

    if not args.skip_irc and not args.github_only:
        if run("scripts/data_collection/irc_collector.py") != 0:
            failed.append("irc")

    if not args.skip_github:
        gh_since = ["--updated-since"] if args.github_only else []
        if run("scripts/data_collection/github_collector.py", "--prs-only", *gh_since) != 0:
            failed.append("github-prs")
        if run("scripts/data_collection/github_collector.py", "--issues-only", *gh_since) != 0:
            failed.append("github-issues")
        if run("scripts/data_collection/github_commits_collector.py") != 0:
            failed.append("github-commits")
        if (data / "github" / "prs_raw.jsonl").exists():
            if run("scripts/data_collection/backfill_merged_by_optimized.py") != 0:
                failed.append("merged_by")

    if not args.skip_forums and not args.github_only:
        if run("scripts/data_collection/delving_collector.py", "--update") != 0:
            failed.append("delving")
        if run("scripts/data_collection/bitcointalk_collector.py", "--update") != 0:
            failed.append("bitcointalk")

    if not args.github_only:
        if run("scripts/data_collection/satoshi_archive_collector.py") != 0:
            failed.append("satoshi")
        if run("scripts/data_collection/fetch_maintainers.py") != 0:
            failed.append("maintainers")
        if run("scripts/data_collection/bips_collector.py", "--skip-discussions") != 0:
            failed.append("bips")

    if args.process and (data / "github" / "prs_raw.jsonl").exists():
        if run("scripts/data_processing/clean_data.py", "--append-new") != 0:
            failed.append("clean")
        if run("scripts/data_processing/enrich_data.py", "--append-new") != 0:
            failed.append("enrich")
        if run("scripts/data_processing/clean_data.py", "--emails-only") != 0:
            failed.append("clean-emails")

    if failed:
        print(f"\nUpdate finished with failures: {', '.join(failed)}")
        return 1
    print("\nIncremental update finished.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
