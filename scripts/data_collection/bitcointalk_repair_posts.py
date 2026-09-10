#!/usr/bin/env python3
"""
Repair Bitcointalk posts.jsonl without a full re-collect.

Modes:
  --reindex     Local only. Rewrite posts.jsonl using stable _post_key() dedupe,
                fix msg_id from URL when missing, report gaps vs topics.jsonl.
                Does NOT restore posts deleted by the old key-collision bug.

  --fetch-gaps  Network. Re-fetch only topics where post count < topics.n_posts
                (~5k topics vs ~14k for --rebuild-posts). Merges with correct keys.

  --audit       Print gap statistics only (no writes).

The 2025 key-collision bug used (topic_id, msg_id or post_index), so msg_id=5 and
post_index=5 collided. ~18k posts were overwritten during --update. Those rows are
not recoverable from the current file alone; use --fetch-gaps or --rebuild-posts.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from scripts.data_collection.bitcointalk_collector import (  # noqa: E402
    BitcoinTalkCollector,
    _drop_topic_posts,
    _post_key,
)
from src.utils.jsonl_merge import load_jsonl_index, write_jsonl
from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir

logger = setup_logger()

MSG_ID_FROM_URL = re.compile(r"[?&]topic=\d+\.msg(\d+)")


def _data_dir() -> Path:
    return get_data_dir() / "bitcointalk"


def _old_buggy_key(post: Dict[str, Any]) -> tuple:
    return (post.get("topic_id"), post.get("msg_id") or post.get("post_index"))


def _fix_msg_id_from_url(post: Dict[str, Any]) -> Dict[str, Any]:
    if post.get("msg_id") is not None:
        return post
    url = post.get("url") or ""
    match = MSG_ID_FROM_URL.search(url)
    if not match:
        return post
    fixed = dict(post)
    fixed["msg_id"] = int(match.group(1))
    fixed["url"] = (
        f"https://bitcointalk.org/index.php?"
        f"topic={post.get('topic_id')}.msg{fixed['msg_id']}#msg{fixed['msg_id']}"
    )
    return fixed


def _load_topics() -> Dict[int, Dict[str, Any]]:
    topics_file = _data_dir() / "topics.jsonl"
    return load_jsonl_index(topics_file, lambda t: t.get("id"))


def audit_gaps(posts_by_key: Dict[tuple, Dict[str, Any]], topics: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
    actual = Counter(p.get("topic_id") for p in posts_by_key.values())
    deficient: List[Dict[str, Any]] = []
    missing_total = 0
    for tid, topic in topics.items():
        expected = int(topic.get("n_posts") or 0)
        got = actual.get(tid, 0)
        if got < expected:
            gap = expected - got
            missing_total += gap
            deficient.append(
                {
                    "topic_id": tid,
                    "title": (topic.get("title") or "")[:80],
                    "expected": expected,
                    "got": got,
                    "missing": gap,
                }
            )
    deficient.sort(key=lambda x: x["missing"], reverse=True)
    return {
        "topics_total": len(topics),
        "posts_indexed": len(posts_by_key),
        "expected_posts_sum": sum(int(t.get("n_posts") or 0) for t in topics.values()),
        "topics_deficient": len(deficient),
        "missing_posts_estimate": missing_total,
        "top_gaps": deficient[:20],
    }


def reindex_posts(*, backup: bool = True, dry_run: bool = False) -> Dict[str, Any]:
    """Local repair: stable keys, optional msg_id fix, rewrite sorted posts.jsonl."""
    data_dir = _data_dir()
    posts_file = data_dir / "posts.jsonl"
    if not posts_file.exists():
        raise FileNotFoundError(posts_file)

    lines_read = 0
    old_key_dupes = 0
    new_key_dupes = 0
    msg_ids_fixed = 0
    posts_by_key: Dict[tuple, Dict[str, Any]] = {}
    old_keys_seen: set = set()

    with open(posts_file, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            lines_read += 1
            post = json.loads(line)
            old_k = _old_buggy_key(post)
            if old_k in old_keys_seen:
                old_key_dupes += 1
            old_keys_seen.add(old_k)

            fixed = _fix_msg_id_from_url(post)
            if fixed.get("msg_id") != post.get("msg_id"):
                msg_ids_fixed += 1
                post = fixed

            key = _post_key(post)
            if key in posts_by_key:
                new_key_dupes += 1
            posts_by_key[key] = post

    topics = _load_topics()
    gap_report = audit_gaps(posts_by_key, topics)

    result = {
        "mode": "reindex",
        "dry_run": dry_run,
        "lines_read": lines_read,
        "unique_new_keys": len(posts_by_key),
        "lines_lost_vs_input": lines_read - len(posts_by_key),
        "old_buggy_key_dupes_in_file": old_key_dupes,
        "new_key_dupes_in_file": new_key_dupes,
        "msg_ids_fixed_from_url": msg_ids_fixed,
        **gap_report,
        "note": (
            "lines_lost_vs_input > 0 means duplicate keys in the source file; "
            "missing_posts_estimate vs topics.jsonl means content must be re-fetched."
        ),
    }

    if dry_run:
        logger.info("Dry run — no files written")
        return result

    if backup:
        backup_path = posts_file.with_suffix(".jsonl.pre-reindex.bak")
        shutil.copy2(posts_file, backup_path)
        result["backup"] = str(backup_path)

    write_jsonl(
        posts_file,
        posts_by_key.values(),
        sort_key=lambda p: (p.get("topic_id") or 0, p.get("msg_id") or p.get("post_index") or 0),
    )

    manifest = {
        "repaired_at": datetime.now(timezone.utc).isoformat(),
        "repair_mode": "reindex",
        **{k: v for k, v in result.items() if k != "top_gaps"},
        "top_gaps": result["top_gaps"][:10],
    }
    manifest_path = data_dir / "repair_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    result["manifest"] = str(manifest_path)
    return result


def fetch_gaps(*, delay: float = 1.2, max_topics: int | None = None, dry_run: bool = False) -> Dict[str, Any]:
    """Re-fetch only topics that are short on posts vs topics.jsonl n_posts."""
    collector = BitcoinTalkCollector(delay=delay)
    topics = _load_topics()
    posts_by_key = collector._load_posts_index()
    gap_report = audit_gaps(posts_by_key, topics)

    actual = Counter(p.get("topic_id") for p in posts_by_key.values())
    to_fetch: List[Tuple[int, Dict[str, Any]]] = []
    for tid, topic in sorted(topics.items()):
        expected = int(topic.get("n_posts") or 0)
        got = actual.get(tid, 0)
        if got < expected:
            to_fetch.append((tid, topic))

    if max_topics is not None:
        to_fetch = to_fetch[:max_topics]

    result = {
        "mode": "fetch-gaps",
        "dry_run": dry_run,
        "topics_to_fetch": len(to_fetch),
        "before_posts": len(posts_by_key),
        **gap_report,
    }

    if dry_run:
        result["sample_topic_ids"] = [t[0] for t in to_fetch[:20]]
        return result

    errors = 0
    repaired_topics = 0
    for i, (tid, meta) in enumerate(to_fetch, 1):
        try:
            topic, posts = collector._fetch_topic(tid, listing_title=meta.get("title") or "")
            if topic is None:
                errors += 1
                continue
            _drop_topic_posts(posts_by_key, tid)
            topics[tid] = topic
            for post in posts:
                posts_by_key[_post_key(post)] = post
            repaired_topics += 1
            if i % 25 == 0 or i == len(to_fetch):
                logger.info("Gap repair %s/%s topics (%s posts, %s errors)", i, len(to_fetch), len(posts_by_key), errors)
        except Exception as exc:
            errors += 1
            logger.warning("Gap fetch topic %s failed: %s", tid, exc)

    write_jsonl(
        collector.topics_file,
        topics.values(),
        sort_key=lambda t: t.get("id") or 0,
    )
    write_jsonl(
        collector.posts_file,
        posts_by_key.values(),
        sort_key=lambda p: (p.get("topic_id") or 0, p.get("msg_id") or p.get("post_index") or 0),
    )

    after_gap = audit_gaps(posts_by_key, topics)
    result.update(
        {
            "after_posts": len(posts_by_key),
            "topics_repaired": repaired_topics,
            "errors": errors,
            "after_missing_posts_estimate": after_gap["missing_posts_estimate"],
            "after_topics_deficient": after_gap["topics_deficient"],
        }
    )
    return result


def _print_report(result: Dict[str, Any]) -> None:
    print(json.dumps({k: v for k, v in result.items() if k != "top_gaps"}, indent=2))
    gaps = result.get("top_gaps") or []
    if gaps:
        print("\nTop gaps (topic_id, missing, got/expected, title):")
        for g in gaps[:10]:
            print(
                f"  {g['topic_id']}: -{g['missing']} "
                f"({g['got']}/{g['expected']}) {g['title']}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair Bitcointalk posts.jsonl (local or targeted fetch)")
    parser.add_argument(
        "--reindex",
        action="store_true",
        help="Local: rewrite posts with stable keys (no HTTP)",
    )
    parser.add_argument(
        "--fetch-gaps",
        action="store_true",
        help="Network: re-fetch topics short on posts vs topics.jsonl",
    )
    parser.add_argument("--audit", action="store_true", help="Print gap stats only")
    parser.add_argument("--dry-run", action="store_true", help="Report only, no writes/fetches")
    parser.add_argument("--no-backup", action="store_true", help="Skip backup on --reindex")
    parser.add_argument("--delay", type=float, default=1.2, help="HTTP delay for --fetch-gaps")
    parser.add_argument("--max-topics", type=int, default=None, help="Cap gap fetches (testing)")
    args = parser.parse_args()

    if args.audit:
        collector = BitcoinTalkCollector()
        topics = _load_topics()
        posts_by_key = collector._load_posts_index()
        _print_report({"mode": "audit", **audit_gaps(posts_by_key, topics)})
        return

    if args.reindex:
        _print_report(reindex_posts(backup=not args.no_backup, dry_run=args.dry_run))
        return

    if args.fetch_gaps:
        _print_report(fetch_gaps(delay=args.delay, max_topics=args.max_topics, dry_run=args.dry_run))
        return

    parser.error("Specify --audit, --reindex, or --fetch-gaps")


if __name__ == "__main__":
    main()
