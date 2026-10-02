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


def github_json(url: str, tok: str) -> tuple[Any, Dict[str, str]]:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "btcdecoded-project-repos",
            "Authorization": f"Bearer {tok}",
        },
    )
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=60) as res:
                body = json.loads(res.read().decode())
                return body, {k.lower(): v for k, v in res.headers.items()}
        except urllib.error.HTTPError as err:
            if err.code in (403, 429, 502, 503, 504) and attempt < 5:
                reset = err.headers.get("X-RateLimit-Reset")
                wait = 30
                if reset and reset.isdigit():
                    wait = max(5, int(reset) - int(time.time()) + 2)
                print(f"HTTP {err.code} on {url}; sleeping {wait}s", flush=True)
                time.sleep(min(wait, 120))
                continue
            detail = err.read().decode("utf-8", "replace")[:300]
            raise SystemExit(f"GitHub HTTP {err.code} {url} {detail}") from err
    raise SystemExit(f"GitHub failed {url}")


def paginate(url: str, tok: str, params: Dict[str, str]) -> Iterator[Dict[str, Any]]:
    query = urllib.parse.urlencode(params)
    next_url: Optional[str] = f"{url}?{query}"
    while next_url:
        payload, headers = github_json(next_url, tok)
        if not isinstance(payload, list):
            raise SystemExit(f"Unexpected payload from {next_url}")
        yield from payload
        next_url = None
        for part in headers.get("link", "").split(","):
            if 'rel="next"' in part:
                next_url = part[part.find("<") + 1 : part.find(">")]
                break


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect project-repo pull requests and issues")
    parser.add_argument("--repo", action="append", help="owner/name. Repeatable. Default is the project list.")
    parser.add_argument("--no-comments", action="store_true", help="Store the opening post only")
    parser.add_argument("--limit", type=int, default=None, help="Stop after this many new records per repo")
    args = parser.parse_args()
    repos = args.repo or REPOS
    for slug in repos:
        if slug.count("/") != 1 or any(part in ("", ".", "..") for part in slug.split("/")):
            raise SystemExit(f"refusing repo slug {slug}")
    tok = token()
    for slug in repos:
        collect_repo(slug, tok, with_comments=not args.no_comments, limit=args.limit)


if __name__ == "__main__":
    main()
