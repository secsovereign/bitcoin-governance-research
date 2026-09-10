#!/usr/bin/env python3
"""
Collect the datasets the analysis package needs.

Order:
  1. Mailing lists (gnusha bitcoin-dev + metzdowd cryptography)
  2. IRC (parse existing data/irc/raw, or download)
  3. GitHub PRs and issues
  4. GitHub commits
  5. Delving Bitcoin + Bitcointalk board 6
  6. Satoshi archive
  7. Current MAINTAINERS file
  8. BIPs
  9. Clean + enrich (after GitHub PRs exist)

GitHub PR collection is the long pole (hours, rate-limited). Run it and leave it going.
For incremental updates prefer: python scripts/update_all.py
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.mailing_lists import has_canonical_dump
from src.utils.paths import get_data_dir


def _present(path: Path, min_bytes: int = 1000) -> bool:
    return path.exists() and path.stat().st_size > min_bytes


def run(script: str, *args: str) -> int:
    cmd = [sys.executable, str(project_root / script), *args]
    print(f"\n>>> {' '.join(cmd)}")
    return subprocess.call(cmd, cwd=str(project_root))


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect datasets for the analysis package")
    parser.add_argument("--skip-github", action="store_true", help="Skip GitHub API collection")
    parser.add_argument("--skip-mail", action="store_true", help="Skip gnusha + cryptography lists")
    parser.add_argument("--skip-forums", action="store_true", help="Skip Delving + Bitcointalk")
    parser.add_argument("--skip-irc-download", action="store_true", help="Only parse existing IRC raw files")
    parser.add_argument("--prs-only", action="store_true", help="GitHub: PRs only")
    parser.add_argument("--issues-only", action="store_true", help="GitHub: issues only")
    parser.add_argument("--process", action="store_true", help="Run clean_data + enrich_data after collection")
    args = parser.parse_args()

    data = get_data_dir()
    failed = []

    if not args.skip_mail:
        if has_canonical_dump():
            print("Mailing lists: gnusha dump already present (run gnusha_collector.py to refresh)")
        else:
            if run("scripts/data_collection/gnusha_collector.py") != 0:
                failed.append("gnusha")

        crypto_file = data / "mailing_lists" / "cryptography.jsonl"
        if _present(crypto_file, 10_000):
            print("Cryptography ML: dump already present (run cryptography_ml_collector.py to refresh)")
        else:
            if run("scripts/data_collection/cryptography_ml_collector.py") != 0:
                failed.append("cryptography")

    irc_messages = data / "irc" / "messages.jsonl"
    irc_raw = data / "irc" / "raw"
    if _present(irc_messages, 10_000):
        print("IRC: dump already present (run irc_collector.py to refresh)")
    elif irc_raw.exists() and any(irc_raw.iterdir()):
        if run("scripts/data_collection/irc_collector.py", "--from-raw") != 0:
            failed.append("irc-from-raw")
    elif not args.skip_irc_download:
        if run("scripts/data_collection/irc_collector.py") != 0:
            failed.append("irc-download")

    if not args.skip_github:
        prs = data / "github" / "prs_raw.jsonl"
        issues = data / "github" / "issues_raw.jsonl"
        commits = data / "github" / "commits_raw.jsonl"
        merged = data / "github" / "merged_by_mapping.jsonl"
        if _present(prs, 10_000) and (args.issues_only or _present(issues, 1000)):
            print("GitHub PRs/issues: dump already present (run update_all.py to refresh)")
        else:
            github_args = []
            if args.prs_only:
                github_args.append("--prs-only")
            if args.issues_only:
                github_args.append("--issues-only")
            if run("scripts/data_collection/github_collector.py", *github_args) != 0:
                failed.append("github")
        if not args.issues_only:
            if _present(commits, 10_000):
                print("GitHub commits: dump already present (run github_commits_collector.py to refresh)")
            else:
                if run("scripts/data_collection/github_commits_collector.py") != 0:
                    failed.append("commits")
        if _present(prs, 10_000) and not _present(merged, 100):
            if run("scripts/data_collection/backfill_merged_by_optimized.py") != 0:
                failed.append("merged_by")
        elif _present(merged, 100):
            print("merged_by mapping: already present (run backfill_merged_by_optimized.py to refresh)")

    if not args.skip_forums:
        delving_posts = data / "delving" / "posts.jsonl"
        if _present(delving_posts):
            print("Delving: dump already present (run delving_collector.py --update to refresh)")
        else:
            if run("scripts/data_collection/delving_collector.py") != 0:
                failed.append("delving")

        bitcointalk_posts = data / "bitcointalk" / "posts.jsonl"
        if _present(bitcointalk_posts):
            print("Bitcointalk: dump already present (run bitcointalk_collector.py --update to refresh)")
        else:
            if run("scripts/data_collection/bitcointalk_collector.py") != 0:
                failed.append("bitcointalk")

    satoshi = data / "satoshi_archive" / "satoshi_communications.jsonl"
    if _present(satoshi):
        print("Satoshi archive: dump already present (run satoshi_archive_collector.py to refresh)")
    else:
        if run("scripts/data_collection/satoshi_archive_collector.py") != 0:
            failed.append("satoshi")

    maintainers = data / "maintainers" / "canonical_maintainers.json"
    if _present(maintainers, 100):
        print("Maintainers: already present (run fetch_maintainers.py to refresh)")
    else:
        if run("scripts/data_collection/fetch_maintainers.py") != 0:
            failed.append("maintainers")

    bips = data / "bips" / "bips.jsonl"
    if _present(bips, 10_000):
        print("BIPs: dump already present (run bips_collector.py to refresh)")
    else:
        if run("scripts/data_collection/bips_collector.py", "--skip-discussions") != 0:
            failed.append("bips")

    if args.process and (data / "github" / "prs_raw.jsonl").exists():
        if run("scripts/data_processing/clean_data.py") != 0:
            failed.append("clean")
        if run("scripts/data_processing/enrich_data.py") != 0:
            failed.append("enrich")

    if failed:
        print(f"\nFailed steps: {', '.join(failed)}")
        return 1
    print("\nCollection steps finished.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
