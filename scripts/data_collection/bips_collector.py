#!/usr/bin/env python3
"""
BIPs (Bitcoin Improvement Proposals) collector.

Collects BIPs, their discussions, and status from the bitcoin/bips repository.

Supports incremental JSONL writes and resume: each issue/PR is flushed to disk
immediately, and already-collected numbers are skipped on restart.

Issues/PRs use GitHub REST pagination directly (requests) — PyGithub listing was
hanging and burning rate-limit tickets on comment/attribute access.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set

socket.setdefaulttimeout(30)

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import config
from src.utils.logger import setup_logger
from src.utils.rate_limiter import RateLimiter
from src.utils.paths import get_data_dir

try:
    import requests
except ImportError:
    print("Error: requests package not installed.")
    print("Run: pip install requests")
    sys.exit(1)

logger = setup_logger()


class BIPsCollector:
    """Collector for Bitcoin Improvement Proposals."""

    def __init__(self, skip_files: bool = False, fresh: bool = False, with_comments: bool = False):
        self.token = config.get("data_collection.github.token") or os.getenv("GITHUB_TOKEN")
        self.repo_owner = "bitcoin"
        self.repo_name = "bips"
        self.data_dir = get_data_dir() / "bips"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.skip_files = skip_files
        self.fresh = fresh
        self.with_comments = with_comments
        self.max_retries = 5

        if self.token:
            self.rate_limiter = RateLimiter(max_calls=4500, time_window=3600)
        else:
            logger.warning("No GitHub token provided. Rate limits will be stricter.")
            self.rate_limiter = RateLimiter(max_calls=60, time_window=3600)

        self.issues_file = self.data_dir / "bips_issues.jsonl"
        self.prs_file = self.data_dir / "bips_prs.jsonl"
        self.bips_file = self.data_dir / "bips.jsonl"
        self.session = requests.Session()
        self.session.headers.update(self._github_headers())

    def _github_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "bitcoin-governance-research-bips-collector",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def collect(self) -> None:
        logger.info("Starting BIPs collection")
        if not self.skip_files:
            self._collect_bip_files()
        else:
            logger.info("Skipping BIP file collection (--skip-files)")
        self._collect_bip_discussions()
        logger.info("BIPs collection complete")

    def _load_existing_numbers(self, path: Path) -> Set[int]:
        numbers: Set[int] = set()
        if not path.exists() or self.fresh:
            return numbers
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    number = obj.get("number")
                    if number is not None:
                        numbers.add(int(number))
                except (json.JSONDecodeError, TypeError, ValueError):
                    continue
        return numbers

    def _backup_if_fresh(self, path: Path) -> None:
        if not self.fresh or not path.exists():
            return
        stamp = time.strftime("%Y%m%d_%H%M%S")
        backup = path.with_name(f"{path.stem}_BACKUP_{stamp}{path.suffix}")
        shutil.copy2(path, backup)
        path.unlink()
        logger.info("Fresh mode: backed up %s -> %s", path.name, backup.name)

    def _append_jsonl(self, path: Path, record: Dict[str, Any]) -> None:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())

    def _paginate_rest(self, url: str, params: Optional[Dict[str, Any]] = None) -> Iterator[Dict[str, Any]]:
        params = dict(params or {})
        params.setdefault("per_page", 100)
        next_url: Optional[str] = url
        page = 0
        while next_url:
            self.rate_limiter.wait_if_needed()
            resp = None
            for attempt in range(1, self.max_retries + 1):
                try:
                    resp = self.session.get(
                        next_url,
                        params=params if page == 0 else None,
                        timeout=30,
                    )
                    if resp.status_code == 403 and "rate limit" in resp.text.lower():
                        reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
                        wait = max(5, reset - int(time.time()) + 2)
                        logger.warning("REST rate limited, sleeping %ss", wait)
                        time.sleep(wait)
                        continue
                    resp.raise_for_status()
                    break
                except Exception as e:
                    if attempt >= self.max_retries:
                        raise
                    wait = min(60, 5 * attempt)
                    logger.warning("REST error (attempt %s/%s): %s; sleep %ss", attempt, self.max_retries, e, wait)
                    time.sleep(wait)
            if resp is None:
                raise RuntimeError(f"Failed to fetch {next_url}")

            page += 1
            items = resp.json()
            if not isinstance(items, list):
                raise RuntimeError(f"Unexpected payload from {next_url}")
            remaining = resp.headers.get("X-RateLimit-Remaining", "?")
            logger.info("REST page %s (%s items, remaining=%s)", page, len(items), remaining)
            yield from items

            next_url = None
            for part in resp.headers.get("Link", "").split(","):
                if 'rel="next"' in part:
                    next_url = part[part.find("<") + 1 : part.find(">")]
                    break
            params = None

    def _collect_bip_files(self) -> None:
        logger.info("Collecting BIP files from repository")
        try:
            temp_dir = tempfile.mkdtemp(prefix="bitcoin_bips_")
            logger.info("Cloning BIPs repository to %s", temp_dir)
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--depth=1",
                    f"https://github.com/{self.repo_owner}/{self.repo_name}.git",
                    temp_dir,
                ],
                check=True,
                capture_output=True,
            )
            bip_dir = Path(temp_dir)
            bip_files = list(bip_dir.rglob("bip-*.mediawiki")) + list(bip_dir.rglob("bip-*.md"))
            logger.info("Found %s BIP files", len(bip_files))

            bips = []
            for bip_file in bip_files:
                try:
                    bip_data = self._parse_bip_file(bip_file)
                    if bip_data:
                        bips.append(bip_data)
                except Exception as e:
                    logger.warning("Error parsing BIP file %s: %s", bip_file, e)

            with open(self.bips_file, "w", encoding="utf-8") as f:
                for bip in bips:
                    f.write(json.dumps(bip, ensure_ascii=False) + "\n")
            logger.info("Saved %s BIPs to %s", len(bips), self.bips_file)
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception as e:
            logger.error("Error collecting BIP files: %s", e)

    def _parse_bip_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            bip_match = re.search(r"bip-(\d+)", file_path.name, re.I)
            bip_number = int(bip_match.group(1)) if bip_match else None
            metadata: Dict[str, Any] = {
                "bip_number": bip_number,
                "filename": file_path.name,
                "content": content,
                "content_length": len(content),
            }
            for key, pattern in (
                ("title", r"^Title:\s*(.+)$"),
                ("author", r"^Author:\s*(.+)$"),
                ("status", r"^Status:\s*(.+)$"),
                ("type", r"^Type:\s*(.+)$"),
                ("created", r"^Created:\s*(.+)$"),
            ):
                match = re.search(pattern, content, re.M | re.I)
                if match:
                    metadata[key] = match.group(1).strip()
            return metadata
        except Exception as e:
            logger.debug("Error parsing BIP file %s: %s", file_path, e)
            return None

    def _fetch_issue_comments(self, number: int) -> List[Dict[str, Any]]:
        comments: List[Dict[str, Any]] = []
        url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/issues/{number}/comments"
        for item in self._paginate_rest(url, {"per_page": 100}):
            comments.append(
                {
                    "author": (item.get("user") or {}).get("login"),
                    "body": item.get("body"),
                    "created_at": item.get("created_at"),
                }
            )
        return comments

    def _collect_issues(self) -> None:
        self._backup_if_fresh(self.issues_file)
        existing = self._load_existing_numbers(self.issues_file)
        if existing:
            logger.info("Resuming issues: %s already collected, skipping duplicates", len(existing))
        else:
            logger.info("Starting issues collection from scratch (incremental writes)")

        collected = skipped = skipped_prs = errors = 0
        url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/issues"

        for item in self._paginate_rest(url, {"state": "all", "per_page": 100}):
            number = item.get("number")
            if item.get("pull_request") is not None:
                skipped_prs += 1
                continue
            if number in existing:
                skipped += 1
                continue
            try:
                issue_data = {
                    "number": number,
                    "title": item.get("title"),
                    "body": item.get("body"),
                    "state": item.get("state"),
                    "created_at": item.get("created_at"),
                    "closed_at": item.get("closed_at"),
                    "author": (item.get("user") or {}).get("login"),
                    "labels": [l.get("name") for l in (item.get("labels") or []) if isinstance(l, dict)],
                    "comments_count": item.get("comments", 0),
                    "comments": [],
                }
                if self.with_comments and issue_data["comments_count"]:
                    issue_data["comments"] = self._fetch_issue_comments(number)
                self._append_jsonl(self.issues_file, issue_data)
                existing.add(number)
                collected += 1
                if collected == 1 or collected % 25 == 0:
                    logger.info(
                        "Collected %s new issues (skipped %s, filtered_prs %s, file ~%s) last=#%s",
                        collected,
                        skipped,
                        skipped_prs,
                        len(existing),
                        number,
                    )
            except Exception as e:
                errors += 1
                logger.error("Error collecting issue #%s: %s", number, e)

        logger.info(
            "Issues complete: %s new, %s skipped, %s filtered_prs, %s errors -> %s",
            collected,
            skipped,
            skipped_prs,
            errors,
            self.issues_file,
        )

    def _collect_prs(self) -> None:
        self._backup_if_fresh(self.prs_file)
        existing = self._load_existing_numbers(self.prs_file)
        if existing:
            logger.info("Resuming PRs: %s already collected, skipping duplicates", len(existing))
        else:
            logger.info("Starting PRs collection from scratch (incremental writes)")

        collected = skipped = errors = 0
        url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/pulls"

        for item in self._paginate_rest(url, {"state": "all", "per_page": 100}):
            number = item.get("number")
            if number in existing:
                skipped += 1
                continue
            try:
                pr_data = {
                    "number": number,
                    "title": item.get("title"),
                    "body": item.get("body"),
                    "state": item.get("state"),
                    "created_at": item.get("created_at"),
                    "merged_at": item.get("merged_at"),
                    "closed_at": item.get("closed_at"),
                    "author": (item.get("user") or {}).get("login"),
                    "merged": item.get("merged_at") is not None,
                    "mergeable": item.get("mergeable"),
                    "comments_count": item.get("comments"),
                    "review_comments_count": item.get("review_comments"),
                }
                self._append_jsonl(self.prs_file, pr_data)
                existing.add(number)
                collected += 1
                if collected == 1 or collected % 25 == 0:
                    logger.info(
                        "Collected %s new PRs (skipped %s, file ~%s) last=#%s",
                        collected,
                        skipped,
                        len(existing),
                        number,
                    )
            except Exception as e:
                errors += 1
                logger.error("Error collecting PR #%s: %s", number, e)

        logger.info(
            "PRs complete: %s new, %s skipped, %s errors -> %s",
            collected,
            skipped,
            errors,
            self.prs_file,
        )

    def _collect_bip_discussions(self) -> None:
        logger.info("Collecting BIP repository issues and PRs (REST incremental)")
        self._collect_issues()
        self._collect_prs()


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect BIPs data from bitcoin/bips")
    parser.add_argument("--skip-files", action="store_true", help="Skip BIP mediawiki clone/parse")
    parser.add_argument("--fresh", action="store_true", help="Backup and rewrite issues/PRs from scratch")
    parser.add_argument("--with-comments", action="store_true", help="Fetch issue comment bodies (slow)")
    args = parser.parse_args()
    BIPsCollector(
        skip_files=args.skip_files,
        fresh=args.fresh,
        with_comments=args.with_comments,
    ).collect()


if __name__ == "__main__":
    main()
