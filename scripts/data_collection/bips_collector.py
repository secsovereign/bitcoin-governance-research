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

    def __init__(self, skip_files: bool = False, fresh: bool = False, with_comments: bool = False, skip_discussions: bool = False):
        self.token = config.get("data_collection.github.token") or os.getenv("GITHUB_TOKEN")
        self.repo_owner = "bitcoin"
        self.repo_name = "bips"
        self.data_dir = get_data_dir() / "bips"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.skip_files = skip_files
        self.skip_discussions = skip_discussions
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
        if not self.skip_discussions:
            self._collect_bip_discussions()
        else:
            logger.info("Skipping BIP issues/PRs (--skip-discussions)")
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

    def _comment_sidecar(self) -> Path:
        return self.data_dir / "bips_pr_comments.jsonl"

    def _load_issue_comment_counts(self) -> Dict[int, int]:
        counts: Dict[int, int] = {}
        if not self.issues_file.exists():
            return counts
        with open(self.issues_file, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                number = obj.get("number")
                comments = obj.get("comments")
                if isinstance(number, int):
                    counts[number] = len(comments) if isinstance(comments, list) else 0
        return counts

    def _load_sidecar_numbers(self) -> Set[int]:
        return self._load_existing_numbers(self._comment_sidecar())

    def _get_json(self, url: str) -> Any:
        """One GitHub JSON body. None on 404. Does not follow every page."""
        self.rate_limiter.wait_if_needed()
        resp = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self.session.get(url, timeout=60)
                if resp.status_code in (403, 429, 502, 503, 504) and attempt < self.max_retries:
                    reset = resp.headers.get("X-RateLimit-Reset")
                    wait = 30
                    if reset and str(reset).isdigit():
                        wait = max(5, int(reset) - int(time.time()) + 2)
                    logger.warning("HTTP %s on %s; sleeping %ss", resp.status_code, url, min(wait, 120))
                    time.sleep(min(wait, 120))
                    continue
                if resp.status_code == 404:
                    return None
                resp.raise_for_status()
                return resp.json()
            except Exception as exc:
                if attempt >= self.max_retries:
                    raise
                wait = min(60, 5 * attempt)
                logger.warning("REST error (attempt %s/%s): %s; sleep %ss", attempt, self.max_retries, exc, wait)
                time.sleep(wait)
        raise RuntimeError(f"Failed to fetch {url}")

    def _map_comment(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        body = str(item.get("body") or "").strip()
        if not body:
            return None
        user = item.get("user") if isinstance(item.get("user"), dict) else {}
        row: Dict[str, Any] = {
            "author": (user or {}).get("login") or "",
            "body": body[:500],
            "created_at": item.get("created_at") or "",
        }
        path = item.get("path")
        if isinstance(path, str) and path.strip():
            row["path"] = path.strip()
        line = item.get("line")
        if not isinstance(line, int) or line <= 0:
            line = item.get("original_line")
        if isinstance(line, int) and line > 0:
            row["line"] = line
        return row

    def _capped_comments(self, url: str, total: int) -> List[Dict[str, Any]]:
        """At most 12 bodies: the whole thread, or the first 6 and last 6."""

        def page(n: int) -> List[Dict[str, Any]]:
            payload = self._get_json(f"{url}?per_page=100&page={n}")
            if payload is None:
                return []
            if not isinstance(payload, list):
                raise RuntimeError(f"Unexpected payload from {url}")
            return [item for item in payload if isinstance(item, dict)]

        first = page(1)
        if total <= 12:
            chosen = first[:12]
        elif total <= 100:
            chosen = first[:6] + first[-6:]
        else:
            last_page = max(1, (total + 99) // 100)
            last = page(last_page)
            chosen = first[:6] + last[-6:]
        seen: Set[int] = set()
        rows: List[Dict[str, Any]] = []
        for item in chosen:
            item_id = item.get("id")
            if isinstance(item_id, int):
                if item_id in seen:
                    continue
                seen.add(item_id)
            mapped = self._map_comment(item)
            if mapped:
                rows.append(mapped)
        return rows

    def backfill_comments(self) -> None:
        """Write missing conversation and review-line bodies. Does not rewrite the PR or issue dumps."""
        if not self.token:
            proc = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=False)
            tok = proc.stdout.strip()
            if proc.returncode == 0 and tok:
                self.token = tok
                self.session.headers.update(self._github_headers())
                self.rate_limiter = RateLimiter(max_calls=4500, time_window=3600)
        issue_counts = self._load_issue_comment_counts()
        done = self._load_sidecar_numbers()
        sidecar = self._comment_sidecar()
        want: List[Dict[str, Any]] = []
        seen: Set[int] = set()
        for obj in self._read_jsonl(self.prs_file):
            number = obj.get("number")
            if not isinstance(number, int) or number in seen or number in done:
                continue
            seen.add(number)
            comments_count = int(obj.get("comments_count") or 0)
            review_count = int(obj.get("review_comments_count") or 0)
            need_comments = comments_count > 0 and issue_counts.get(number, 0) < comments_count
            need_reviews = review_count > 0
            if need_comments or need_reviews:
                obj["_need_comments"] = need_comments
                obj["_need_reviews"] = need_reviews
                obj["_comments_count"] = comments_count
                obj["_review_count"] = review_count
                want.append(obj)
        logger.info("BIP comment backfill: %s pull requests, sidecar %s", len(want), sidecar)
        wrote = 0
        for obj in want:
            number = int(obj["number"])
            row: Dict[str, Any] = {"number": number}
            missing = False
            if obj["_need_comments"]:
                comments = self._capped_comments(
                    f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/issues/{number}/comments",
                    int(obj["_comments_count"]),
                )
                if comments is None:
                    missing = True
                else:
                    row["comments"] = comments
            if obj["_need_reviews"]:
                reviews = self._capped_comments(
                    f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/pulls/{number}/comments",
                    int(obj["_review_count"]),
                )
                if reviews is None:
                    missing = True
                else:
                    row["review_comments"] = reviews
            if missing and "comments" not in row and "review_comments" not in row:
                row["comments"] = []
                row["review_comments"] = []
            self._append_jsonl(sidecar, row)
            wrote += 1
            if wrote == 1 or wrote % 25 == 0:
                logger.info("BIP comment backfill wrote %s/%s last=#%s", wrote, len(want), number)
        logger.info("BIP comment backfill complete: %s -> %s", wrote, sidecar)

    def backfill_reviews(self) -> None:
        """Append pull-review bodies. Does not rewrite the PR dump or the comment sidecar."""
        if not self.token:
            proc = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=False)
            tok = proc.stdout.strip()
            if proc.returncode == 0 and tok:
                self.token = tok
                self.session.headers.update(self._github_headers())
                self.rate_limiter = RateLimiter(max_calls=4500, time_window=3600)
        sidecar = self.data_dir / "bips_pr_reviews.jsonl"
        done = self._load_existing_numbers(sidecar)
        want: List[int] = []
        seen: Set[int] = set()
        for obj in self._read_jsonl(self.prs_file):
            number = obj.get("number")
            if not isinstance(number, int) or number in seen or number in done:
                continue
            seen.add(number)
            want.append(number)
        logger.info("BIP review backfill: %s pull requests, sidecar %s", len(want), sidecar)
        wrote = 0
        for number in want:
            first = self._get_json(
                f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/pulls/{number}/reviews?per_page=100&page=1"
            )
            items: List[Dict[str, Any]] = []
            if isinstance(first, list):
                items = [item for item in first if isinstance(item, dict)]
            if len(items) >= 100:
                second = self._get_json(
                    f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/pulls/{number}/reviews?per_page=100&page=2"
                )
                if isinstance(second, list):
                    items.extend(item for item in second if isinstance(item, dict))
            if len(items) > 12:
                items = items[:6] + items[-6:]
            seen_ids: Set[int] = set()
            rows: List[Dict[str, Any]] = []
            for item in items:
                item_id = item.get("id")
                if isinstance(item_id, int):
                    if item_id in seen_ids:
                        continue
                    seen_ids.add(item_id)
                if not item.get("created_at") and item.get("submitted_at"):
                    item = dict(item)
                    item["created_at"] = item.get("submitted_at")
                mapped = self._map_comment(item)
                if not mapped:
                    continue
                state = item.get("state")
                if isinstance(state, str) and state:
                    mapped["state"] = state
                rows.append(mapped)
            self._append_jsonl(sidecar, {"number": number, "reviews": rows})
            wrote += 1
            if wrote == 1 or wrote % 25 == 0:
                logger.info("BIP review backfill wrote %s/%s last=#%s", wrote, len(want), number)
        logger.info("BIP review backfill complete: %s -> %s", wrote, sidecar)

    def _read_jsonl(self, path: Path) -> Iterator[Dict[str, Any]]:
        if not path.exists():
            return
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict):
                    yield obj


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect BIPs data from bitcoin/bips")
    parser.add_argument("--skip-files", action="store_true", help="Skip BIP mediawiki clone/parse")
    parser.add_argument("--skip-discussions", action="store_true", help="Skip BIP repo issues/PRs (GitHub API)")
    parser.add_argument("--fresh", action="store_true", help="Backup and rewrite issues/PRs from scratch")
    parser.add_argument("--with-comments", action="store_true", help="Fetch issue comment bodies (slow)")
    parser.add_argument(
        "--comments-only",
        action="store_true",
        help="Append missing PR conversation and review comments to bips_pr_comments.jsonl",
    )
    parser.add_argument(
        "--reviews-only",
        action="store_true",
        help="Append pull-review bodies to bips_pr_reviews.jsonl",
    )
    args = parser.parse_args()
    collector = BIPsCollector(
        skip_files=args.skip_files,
        skip_discussions=args.skip_discussions,
        fresh=args.fresh,
        with_comments=args.with_comments,
    )
    if args.comments_only:
        collector.backfill_comments()
    elif args.reviews_only:
        collector.backfill_reviews()
    else:
        collector.collect()


if __name__ == "__main__":
    main()
