#!/usr/bin/env python3
"""Collect pull requests and issues for project repositories.

Writes data/github/repos/<owner>/<repo>/prs.jsonl and issues.jsonl.
Does not touch data/github/prs_raw.jsonl or issues_raw.jsonl.

bitcoin/secp256k1 now lives at bitcoin-core/secp256k1.
demand-open-stratum/demand was not a public repository on 2026-10-01.

Resume: each record is appended immediately, and an existing number is skipped.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set

ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = ROOT / "data" / "github" / "repos"

# Discussion record only. Implementation trees stay out of this collector.
REPOS = [
    "bitcoin-core/secp256k1",
    "bitcoindevkit/bdk",
    "lightningdevkit/rust-lightning",
    "lightningnetwork/lnd",
    "sparrowwallet/sparrow",
    "SeedSigner/seedsigner",
    "foundation-devices/passport-firmware",
    "stratum-mining/stratum",
    "bitcoin-core/bitcoin-maintainer-tools",
    "lightning/bolts",
    "ElementsProject/lightning",
    "bitcoin-core/HWI",
    "rust-bitcoin/rust-bitcoin",
    "rust-bitcoin/rust-miniscript",
    "stratum-mining/sv2-spec",
    "ACINQ/eclair",
]


def is_pull(item: Dict[str, Any]) -> bool:
    return item.get("pull_request") is not None


def token() -> str:
    for key in ("GITHUB_TOKEN", "GH_TOKEN"):
        val = os.environ.get(key, "").strip()
        if val:
            return val
    proc = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=False)
    val = proc.stdout.strip()
    if proc.returncode == 0 and val:
        return val
    raise SystemExit("GITHUB_TOKEN or gh auth token required")


class MissingOnGitHub(Exception):
    """The pull request number is in the local list, but GitHub no longer resolves it."""


def github_json(url: str, tok: str, etag: Optional[str] = None, allow_missing: bool = False) -> tuple[Any, Dict[str, str]]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "btcdecoded-project-repos",
        "Authorization": f"Bearer {tok}",
    }
    if etag:
        headers["If-None-Match"] = etag
    req = urllib.request.Request(url, headers=headers)
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=60) as res:
                body = json.loads(res.read().decode())
                return body, {k.lower(): v for k, v in res.headers.items()}
        except urllib.error.HTTPError as err:
            if err.code == 304:
                return None, {k.lower(): v for k, v in err.headers.items()}
            if err.code == 404 and allow_missing:
                raise MissingOnGitHub(url)
            if err.code in (403, 429, 502, 503, 504) and attempt < 5:
                reset = err.headers.get("X-RateLimit-Reset")
                remaining = err.headers.get("X-RateLimit-Remaining")
                wait = 30
                if reset and str(reset).isdigit():
                    wait = max(5, int(reset) - int(time.time()) + 2)
                # A primary limit needs the whole reset window. Capping at 120s
                # burns the retries and then exits while the limit is still closed.
                if remaining == "0":
                    wait = min(wait, 3700)
                else:
                    wait = min(wait, 120)
                print(f"HTTP {err.code} on {url}; sleeping {wait}s", flush=True)
                time.sleep(wait)
                continue
            detail = err.read().decode("utf-8", "replace")[:300]
            raise SystemExit(f"GitHub HTTP {err.code} {url} {detail}") from err
        except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError) as err:
            if attempt >= 5:
                raise SystemExit(f"GitHub failed {url} {err}") from err
            wait = min(60, 5 * (attempt + 1))
            print(f"network error on {url}; sleeping {wait}s", flush=True)
            time.sleep(wait)
    raise SystemExit(f"GitHub failed {url}")


def next_page(link_header: str) -> Optional[str]:
    for part in (link_header or "").split(","):
        if 'rel="next"' in part and "<" in part:
            return part[part.find("<") + 1 : part.find(">")]
    return None


def paginate(url: str, tok: str, params: Dict[str, str]) -> Iterator[Dict[str, Any]]:
    query = urllib.parse.urlencode(params)
    next_url: Optional[str] = f"{url}?{query}"
    while next_url:
        payload, headers = github_json(next_url, tok)
        if not isinstance(payload, list):
            raise SystemExit(f"Unexpected payload from {next_url}")
        yield from payload
        next_url = next_page(headers.get("link", "")) if len(payload) >= 100 else None


LIST_KEYS = ("reviews", "comments", "review_comments", "files")


def list_was_cut(row: Dict[str, Any]) -> bool:
    if row.get("missing") or row.get("pages_complete"):
        return False
    return any(isinstance(row.get(key), list) and len(row[key]) >= 100 for key in LIST_KEYS)


def fetch_all_pages(url: str, tok: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    next_url: Optional[str] = url
    while next_url:
        payload, headers = github_json(next_url, tok, allow_missing=True)
        if not isinstance(payload, list):
            return items
        items.extend(item for item in payload if isinstance(item, dict))
        next_url = next_page(headers.get("link", "")) if len(payload) >= 100 else None
    return items


def load_numbers(path: Path) -> Set[int]:
    found: Set[int] = set()
    if not path.exists():
        return found
    with path.open() as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                number = json.loads(line).get("number")
            except json.JSONDecodeError:
                continue
            if isinstance(number, int):
                found.add(number)
    return found


def comment_rows(slug: str, number: int, tok: str) -> List[Dict[str, str]]:
    url = f"https://api.github.com/repos/{slug}/issues/{number}/comments"
    payload, _headers = github_json(f"{url}?per_page=12", tok)
    if not isinstance(payload, list):
        return []
    rows = []
    for item in payload[:12]:
        if not isinstance(item, dict):
            continue
        body = str(item.get("body") or "").strip()
        if not body:
            continue
        user = item.get("user") if isinstance(item.get("user"), dict) else {}
        rows.append(
            {
                "author": str((user or {}).get("login") or ""),
                "body": body[:500],
                "created_at": str(item.get("created_at") or ""),
            }
        )
    return rows


def record(item: Dict[str, Any], kind: str, slug: str, tok: str, with_comments: bool) -> Dict[str, Any]:
    number = item.get("number")
    user = item.get("user") if isinstance(item.get("user"), dict) else {}
    comments_count = int(item.get("comments") or 0)
    row: Dict[str, Any] = {
        "repo": slug,
        "number": number,
        "title": item.get("title"),
        "body": item.get("body") or "",
        "state": item.get("state"),
        "created_at": item.get("created_at"),
        "closed_at": item.get("closed_at"),
        "author": (user or {}).get("login"),
        "comments_count": comments_count,
        "url": item.get("html_url"),
    }
    if kind == "pull":
        row["merged"] = item.get("merged_at") is not None
        row["merged_at"] = item.get("merged_at")
    else:
        row["labels"] = [
            lab.get("name")
            for lab in (item.get("labels") or [])
            if isinstance(lab, dict) and lab.get("name")
        ]
    if with_comments and comments_count and isinstance(number, int):
        row["comments"] = comment_rows(slug, number, tok)
    return row


def append_jsonl(path: Path, row: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def collect_repo(slug: str, tok: str, with_comments: bool, limit: Optional[int]) -> None:
    owner, repo = slug.split("/", 1)
    dest = OUT_ROOT / owner / repo
    prs_path = dest / "prs.jsonl"
    issues_path = dest / "issues.jsonl"
    have_prs = load_numbers(prs_path)
    have_issues = load_numbers(issues_path)
    print(
        f"{slug} resume prs={len(have_prs)} issues={len(have_issues)}",
        flush=True,
    )
    new_prs = new_issues = 0

    def take(item: Dict[str, Any], kind: str) -> None:
        nonlocal new_prs, new_issues
        number = item.get("number")
        if not isinstance(number, int):
            return
        if kind == "issue" and is_pull(item):
            return
        seen = have_prs if kind == "pull" else have_issues
        if number in seen:
            return
        if limit is not None and new_prs + new_issues >= limit:
            return
        row = record(item, kind, slug, tok, with_comments)
        if kind == "pull":
            append_jsonl(prs_path, row)
            have_prs.add(number)
            new_prs += 1
        else:
            append_jsonl(issues_path, row)
            have_issues.add(number)
            new_issues += 1
        done = new_prs + new_issues
        if done == 1 or done % 50 == 0:
            print(f"{slug} new prs={new_prs} issues={new_issues} last=#{number}", flush=True)

    for item in paginate(
        f"https://api.github.com/repos/{slug}/pulls",
        tok,
        {"state": "all", "per_page": "100", "sort": "created", "direction": "asc"},
    ):
        take(item, "pull")
        if limit is not None and new_prs + new_issues >= limit:
            break
    if limit is None or new_prs + new_issues < limit:
        for item in paginate(
            f"https://api.github.com/repos/{slug}/issues",
            tok,
            {"state": "all", "per_page": "100", "sort": "created", "direction": "asc"},
        ):
            before = new_prs + new_issues
            take(item, "issue")
            if limit is not None and new_prs + new_issues >= limit and new_prs + new_issues != before:
                break
    print(f"{slug} done new prs={new_prs} issues={new_issues}", flush=True)


def normalize_detail(number: int, slug: str, reviews: List[Any], comments: List[Any], review_comments: List[Any], files: List[Any]) -> Dict[str, Any]:
    """Same nested fields the bitcoin/bitcoin pull-request records store."""
    def login(item: Dict[str, Any]) -> Optional[str]:
        user = item.get("user") if isinstance(item.get("user"), dict) else {}
        return (user or {}).get("login")

    return {
        "repo": slug,
        "number": number,
        "reviews": [
            {
                "state": item.get("state"),
                "body": item.get("body") or "",
                "author": login(item),
                "submitted_at": item.get("submitted_at") or item.get("created_at"),
            }
            for item in reviews if isinstance(item, dict)
        ],
        "review_comments": [
            {
                "body": item.get("body") or "",
                "author": login(item),
                "created_at": item.get("created_at"),
                "path": item.get("path"),
                "line": item.get("line"),
            }
            for item in review_comments if isinstance(item, dict)
        ],
        "comments": [
            {
                "body": item.get("body") or "",
                "author": login(item),
                "created_at": item.get("created_at"),
            }
            for item in comments if isinstance(item, dict)
        ],
        "files": [
            {
                "filename": item.get("filename"),
                "additions": item.get("additions"),
                "deletions": item.get("deletions"),
                "changes": item.get("changes"),
                "status": item.get("status"),
            }
            for item in files if isinstance(item, dict)
        ],
    }


def load_repo_config() -> List[str]:
    path = Path(__file__).resolve().parent / "comparison_repos.json"
    if not path.exists():
        return list(REPOS)
    data = json.loads(path.read_text())
    return [row["slug"] for row in data.get("repos") or []]


def backfill_detail(slug: str, tok: str, limit: Optional[int]) -> None:
    owner, repo = slug.split("/", 1)
    dest = OUT_ROOT / owner / repo
    prs_path = dest / "prs.jsonl"
    if not prs_path.exists():
        print(f"{slug} DATA UNAVAILABLE prs.jsonl is missing, so review objects were not requested", flush=True)
        return
    detail_path = dest / "pr_detail.jsonl"
    have = load_numbers(detail_path)
    etag_path = dest / "detail_etags.json"
    etags: Dict[str, str] = json.loads(etag_path.read_text()) if etag_path.exists() else {}
    done = 0
    with prs_path.open() as handle:
        for line in handle:
            if not line.strip():
                continue
            number = json.loads(line).get("number")
            if not isinstance(number, int) or number in have:
                continue
            base = f"https://api.github.com/repos/{slug}"
            key = f"{slug}#{number}"

            def one(kind: str, url: str) -> Any:
                try:
                    payload, headers = github_json(url, tok, etags.get(key + ":" + kind), allow_missing=True)
                except MissingOnGitHub:
                    return "MISSING"
                if payload is None:
                    return []
                if headers.get("etag"):
                    etags[key + ":" + kind] = headers["etag"]
                return payload

            reviews = one("reviews", f"{base}/pulls/{number}/reviews?per_page=100")
            if reviews == "MISSING":
                row = normalize_detail(number, slug, [], [], [], [])
                row["missing"] = True
                append_jsonl(detail_path, row)
                have.add(number)
                done += 1
                print(f"{slug} #{number} DATA UNAVAILABLE GitHub returned 404", flush=True)
                if limit is not None and done >= limit:
                    break
                continue
            comments = one("comments", f"{base}/issues/{number}/comments?per_page=100")
            review_comments = one("review_comments", f"{base}/pulls/{number}/comments?per_page=100")
            files = one("files", f"{base}/pulls/{number}/files?per_page=100")
            if "MISSING" in (comments, review_comments, files):
                row = normalize_detail(number, slug, [], [], [], [])
                row["missing"] = True
                append_jsonl(detail_path, row)
                have.add(number)
                done += 1
                print(f"{slug} #{number} DATA UNAVAILABLE GitHub returned 404", flush=True)
                if limit is not None and done >= limit:
                    break
                continue
            append_jsonl(detail_path, normalize_detail(number, slug, reviews or [], comments or [], review_comments or [], files or []))
            have.add(number)
            done += 1
            if done == 1 or done % 25 == 0:
                etag_path.write_text(json.dumps(etags))
                print(f"{slug} detail {done} last=#{number}", flush=True)
            if limit is not None and done >= limit:
                break
    etag_path.write_text(json.dumps(etags))
    print(f"{slug} detail done {done}", flush=True)


def _write_updates(detail_path: Path, updated: Dict[int, Dict[str, Any]]) -> None:
    if not updated:
        return
    tmp = detail_path.with_suffix(".jsonl.tmp")
    with detail_path.open() as handle, tmp.open("w") as out:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            number = row.get("number")
            if isinstance(number, int) and number in updated:
                row = updated[number]
            out.write(json.dumps(row) + "\n")
    tmp.replace(detail_path)


def extend_truncated(slug: str, tok: str) -> None:
    """Follow later pages for lists that stopped at 100. Completed rows are skipped."""
    owner, repo = slug.split("/", 1)
    dest = OUT_ROOT / owner / repo
    detail_path = dest / "pr_detail.jsonl"
    if not detail_path.exists():
        print(f"{slug} DATA UNAVAILABLE pr_detail.jsonl is missing", flush=True)
        return
    pending: List[Dict[str, Any]] = []
    with detail_path.open() as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if list_was_cut(row) and isinstance(row.get("number"), int):
                pending.append(row)
    if not pending:
        print(f"{slug} pages already complete", flush=True)
        return
    print(f"{slug} extending {len(pending)} pull requests past the first page", flush=True)
    base = f"https://api.github.com/repos/{slug}"
    endpoints = {
        "reviews": "pulls/{number}/reviews?per_page=100",
        "comments": "issues/{number}/comments?per_page=100",
        "review_comments": "pulls/{number}/comments?per_page=100",
        "files": "pulls/{number}/files?per_page=100",
    }
    updated: Dict[int, Dict[str, Any]] = {}
    for i, original in enumerate(pending, start=1):
        number = int(original["number"])
        fetched_raw: Dict[str, List[Any]] = {}
        try:
            for kind, pattern in endpoints.items():
                current = original.get(kind)
                if isinstance(current, list) and len(current) >= 100:
                    fetched_raw[kind] = fetch_all_pages(f"{base}/{pattern.format(number=number)}", tok)
        except MissingOnGitHub:
            print(f"{slug} #{number} DATA UNAVAILABLE GitHub returned 404", flush=True)
            continue
        normalized = normalize_detail(
            number,
            slug,
            fetched_raw.get("reviews", []),
            fetched_raw.get("comments", []),
            fetched_raw.get("review_comments", []),
            fetched_raw.get("files", []),
        )
        row = dict(original)
        for kind in fetched_raw:
            row[kind] = normalized[kind]
        row["pages_complete"] = True
        updated[number] = row
        if i == 1 or i % 10 == 0:
            print(f"{slug} extended {i}/{len(pending)} last=#{number}", flush=True)
            _write_updates(detail_path, updated)
            updated = {}
    _write_updates(detail_path, updated)
    print(f"{slug} pages written", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect project-repo pull requests and issues")
    parser.add_argument("--repo", action="append", help="owner/name. Repeatable. Default is the project list.")
    parser.add_argument("--no-comments", action="store_true", help="Store the opening post only")
    parser.add_argument("--limit", type=int, default=None, help="Stop after this many new records per repo")
    parser.add_argument("--backfill-detail", action="store_true", help="Add review objects, comment authors, and file paths")
    parser.add_argument("--extend-truncated", action="store_true", help="Fetch later pages for lists cut at 100")
    args = parser.parse_args()
    repos = args.repo or load_repo_config()
    for slug in repos:
        if slug.count("/") != 1 or any(part in ("", ".", "..") for part in slug.split("/")):
            raise SystemExit(f"refusing repo slug {slug}")
    tok = token()
    for slug in repos:
        if args.extend_truncated:
            extend_truncated(slug, tok)
        elif args.backfill_detail:
            backfill_detail(slug, tok, args.limit)
        else:
            collect_repo(slug, tok, with_comments=not args.no_comments, limit=args.limit)


if __name__ == "__main__":
    main()
