#!/usr/bin/env python3
"""
Bitcoin Talk collector for board 6 (Development & Technical Discussion).

Lists every topic on https://bitcointalk.org/index.php?board=6.0 then fetches
each thread via SMF printpage (one request per topic, full post set).

Polite by default: identifiable UA, ~1.2s between requests, backoff on 429/503.
Resume-safe: existing topic ids in topics.jsonl are skipped.
Use --update to scan recent board pages and fetch only new/changed topics.

Output:
  data/bitcointalk/topics.jsonl
  data/bitcointalk/posts.jsonl
  data/bitcointalk/manifest.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import requests
from bs4 import BeautifulSoup

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.jsonl_merge import load_jsonl_index, write_jsonl
from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir

logger = setup_logger()

BOARD_ID = 6
BOARD_NAME = "Development & Technical Discussion"
BASE = "https://bitcointalk.org/index.php"
UA = "BitcoinGovernanceResearch/1.0 (academic archive of board 6; +https://bitcoincommons.org)"
TOPIC_ID_RE = re.compile(r"[?&]topic=(\d+)")
MSG_ID_RE = re.compile(r"\.msg(\d+)")
BOARD_OFFSET_RE = re.compile(r"[?&]board=6\.(\d+)")
DATE_FORMATS = (
    "%B %d, %Y, %I:%M:%S %p",
    "%B %d, %Y, %I:%M %p",
    "%b %d, %Y, %I:%M:%S %p",
)


def _post_key(post: Dict[str, Any]) -> tuple:
    """Stable post key; avoids msg_id/post_index collisions within a topic."""
    topic_id = post.get("topic_id")
    msg_id = post.get("msg_id")
    if msg_id is not None:
        return (topic_id, "m", msg_id)
    return (topic_id, "i", post.get("post_index"))


def _drop_topic_posts(posts_by_key: Dict[tuple, Dict[str, Any]], topic_id: int) -> None:
    for key in list(posts_by_key.keys()):
        if key[0] == topic_id:
            del posts_by_key[key]


class BitcoinTalkCollector:
    def __init__(self, delay: float = 1.2, board_id: int = BOARD_ID) -> None:
        self.delay = delay
        self.board_id = board_id
        self.data_dir = get_data_dir() / "bitcointalk"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.topics_file = self.data_dir / "topics.jsonl"
        self.posts_file = self.data_dir / "posts.jsonl"
        self.manifest_file = self.data_dir / "manifest.json"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
        )
        self._last_request = 0.0
        self._consecutive_blocks = 0

    def collect(
        self,
        resume: bool = True,
        max_topics: Optional[int] = None,
        list_only: bool = False,
    ) -> Dict[str, Any]:
        logger.info("Starting Bitcointalk board %s collection", self.board_id)
        listing = self._list_topics()
        topic_ids = [t["id"] for t in listing]
        logger.info("Board listing: %s topics", len(topic_ids))
        listing_path = self.data_dir / "topic_index.jsonl"
        with open(listing_path, "w", encoding="utf-8") as fh:
            for rec in listing:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

        if list_only:
            return {"topics_listed": len(topic_ids), "list_only": True}

        done = self._existing_topic_ids() if resume else set()
        if done:
            logger.info("Resuming: %s topics already collected", len(done))
        pending = [t for t in listing if t["id"] not in done]
        if max_topics is not None:
            pending = pending[:max_topics]

        mode = "a" if done and resume else "w"
        if mode == "w":
            done = set()
        topics_fh = open(self.topics_file, mode, encoding="utf-8")
        posts_fh = open(self.posts_file, mode, encoding="utf-8")
        collected = 0
        errors = 0
        posts_written = 0
        try:
            for i, meta in enumerate(pending, 1):
                if self._consecutive_blocks >= 8:
                    logger.error("Too many consecutive blocks/403s; stopping. Re-run later to resume.")
                    break
                try:
                    topic, posts = self._fetch_topic(meta["id"], listing_title=meta.get("title") or "")
                    if topic is None:
                        errors += 1
                        continue
                    topics_fh.write(json.dumps(topic, ensure_ascii=False) + "\n")
                    for post in posts:
                        posts_fh.write(json.dumps(post, ensure_ascii=False) + "\n")
                    topics_fh.flush()
                    posts_fh.flush()
                    collected += 1
                    posts_written += len(posts)
                    if i % 25 == 0 or i == len(pending):
                        logger.info(
                            "Bitcointalk topics %s/%s this run (ok %s, posts %s, errors %s)",
                            i,
                            len(pending),
                            collected,
                            posts_written,
                            errors,
                        )
                except Exception as exc:
                    errors += 1
                    logger.warning("Topic %s failed: %s", meta["id"], exc)
        finally:
            topics_fh.close()
            posts_fh.close()

        n_topics = _count_lines(self.topics_file)
        n_posts = _count_lines(self.posts_file)
        manifest = {
            "source": f"{BASE}?board={self.board_id}.0",
            "board_id": self.board_id,
            "board_name": BOARD_NAME,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "topics_listed": len(topic_ids),
            "topics": n_topics,
            "posts": n_posts,
            "new_this_run": collected,
            "errors": errors,
        }
        self.manifest_file.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        logger.info("Bitcointalk collection: %s topics, %s posts", n_topics, n_posts)
        return manifest

    def collect_update(self, idle_pages: int = 5) -> Dict[str, Any]:
        """Scan recent board pages; fetch new topics, retries, and threads with new replies."""
        logger.info("Starting Bitcointalk incremental update (board %s)", self.board_id)
        existing_topics = load_jsonl_index(self.topics_file, lambda t: t.get("id"))
        posts_by_key = self._load_posts_index()
        indexed_ids = self._indexed_topic_ids()

        offset = 0
        pages = 0
        idle = 0
        new_topics = refreshed = retried = errors = 0

        while idle < idle_pages:
            url = f"{BASE}?board={self.board_id}.{offset}"
            html = self._get_html(url)
            if html is None:
                break
            page_topics = _topics_from_board_page(html)
            if not page_topics:
                idle += 1
                offset += 40
                pages += 1
                continue

            page_work = 0
            for meta in page_topics:
                tid = meta["id"]
                stored = existing_topics.get(tid)
                replies = meta.get("replies")
                needs_fetch = stored is None
                if stored is None and tid in indexed_ids:
                    needs_fetch = True
                    retried += 1
                elif stored is not None and replies is not None:
                    stored_replies = max(int(stored.get("n_posts") or 1) - 1, 0)
                    if replies > stored_replies:
                        needs_fetch = True
                if not needs_fetch:
                    continue

                page_work += 1
                try:
                    topic, posts = self._fetch_topic(tid, listing_title=meta.get("title") or "")
                    if topic is None:
                        errors += 1
                        continue
                    is_new = tid not in existing_topics
                    _drop_topic_posts(posts_by_key, tid)
                    existing_topics[tid] = topic
                    for post in posts:
                        posts_by_key[_post_key(post)] = post
                    if is_new:
                        new_topics += 1
                    else:
                        refreshed += 1
                except Exception as exc:
                    errors += 1
                    logger.warning("Topic %s update failed: %s", tid, exc)

            if page_work:
                idle = 0
                logger.info(
                    "Board offset %s: fetched %s topics (new %s, refreshed %s, retried %s)",
                    offset,
                    page_work,
                    new_topics,
                    refreshed,
                    retried,
                )
            else:
                idle += 1

            offset += 40
            pages += 1
            if pages > 500:
                logger.warning("Stopping update scan after 500 pages")
                break

        write_jsonl(
            self.topics_file,
            existing_topics.values(),
            sort_key=lambda t: t.get("id") or 0,
        )
        write_jsonl(
            self.posts_file,
            posts_by_key.values(),
            sort_key=lambda p: (p.get("topic_id") or 0, p.get("msg_id") or p.get("post_index") or 0),
        )
        manifest = {
            "source": f"{BASE}?board={self.board_id}.0",
            "board_id": self.board_id,
            "board_name": BOARD_NAME,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "topics": len(existing_topics),
            "posts": len(posts_by_key),
            "new_topics": new_topics,
            "refreshed_topics": refreshed,
            "retried_topics": retried,
            "errors": errors,
            "pages_scanned": pages,
        }
        self.manifest_file.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        logger.info(
            "Bitcointalk update: +%s new, %s refreshed, %s total topics",
            new_topics,
            refreshed,
            len(existing_topics),
        )
        return manifest

    def rebuild_posts(self) -> Dict[str, Any]:
        """Re-fetch every known topic and rebuild posts.jsonl (recovery after key-collision bug)."""
        logger.info("Rebuilding Bitcointalk posts from topics.jsonl")
        existing_topics = load_jsonl_index(self.topics_file, lambda t: t.get("id"))
        if not existing_topics:
            raise FileNotFoundError(f"No topics at {self.topics_file}")
        posts_by_key: Dict[tuple, Dict[str, Any]] = {}
        errors = 0
        for i, (tid, meta) in enumerate(sorted(existing_topics.items()), 1):
            try:
                topic, posts = self._fetch_topic(tid, listing_title=meta.get("title") or "")
                if topic is None:
                    errors += 1
                    continue
                existing_topics[tid] = topic
                for post in posts:
                    posts_by_key[_post_key(post)] = post
                if i % 25 == 0 or i == len(existing_topics):
                    logger.info("Rebuild %s/%s topics (%s posts, %s errors)", i, len(existing_topics), len(posts_by_key), errors)
            except Exception as exc:
                errors += 1
                logger.warning("Rebuild topic %s failed: %s", tid, exc)
        write_jsonl(self.topics_file, existing_topics.values(), sort_key=lambda t: t.get("id") or 0)
        write_jsonl(
            self.posts_file,
            posts_by_key.values(),
            sort_key=lambda p: (p.get("topic_id") or 0, p.get("msg_id") or p.get("post_index") or 0),
        )
        manifest = {
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "topics": len(existing_topics),
            "posts": len(posts_by_key),
            "errors": errors,
            "rebuild": True,
        }
        self.manifest_file.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        logger.info("Rebuild complete: %s topics, %s posts", len(existing_topics), len(posts_by_key))
        return manifest

    def _load_posts_index(self) -> Dict[tuple, Dict[str, Any]]:
        index: Dict[tuple, Dict[str, Any]] = {}
        if not self.posts_file.exists():
            return index
        with open(self.posts_file, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    post = json.loads(line)
                except json.JSONDecodeError:
                    continue
                key = _post_key(post)
                index[key] = post
        return index

    def _indexed_topic_ids(self) -> Set[int]:
        index_path = self.data_dir / "topic_index.jsonl"
        ids: Set[int] = set()
        if not index_path.exists():
            return ids
        with open(index_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("id") is not None:
                    ids.add(int(rec["id"]))
        return ids

    def _list_topics(self) -> List[Dict[str, Any]]:
        offset = 0
        seen: Set[int] = set()
        topics: List[Dict[str, Any]] = []
        max_offset = None
        pages = 0
        while True:
            url = f"{BASE}?board={self.board_id}.{offset}"
            html = self._get_html(url)
            if html is None:
                break
            if max_offset is None:
                max_offset = _max_board_offset(html)
                logger.info("Board last offset appears to be %s", max_offset)
            page_topics = _topics_from_board_page(html)
            new = 0
            for rec in page_topics:
                if rec["id"] in seen:
                    continue
                seen.add(rec["id"])
                topics.append(rec)
                new += 1
            pages += 1
            logger.info("Board page offset %s: %s new topics (total %s)", offset, new, len(topics))
            if not page_topics and offset > 0:
                break
            offset += 40
            if max_offset is not None and offset > max_offset:
                break
            if pages > 2000:
                logger.warning("Stopping board listing after 2000 pages")
                break
        topics.sort(key=lambda t: t["id"])
        return topics

    def _existing_topic_ids(self) -> Set[int]:
        ids: Set[int] = set()
        if not self.topics_file.exists():
            return ids
        with open(self.topics_file, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("id") is not None:
                    ids.add(int(rec["id"]))
        return ids

    def _fetch_topic(
        self, topic_id: int, listing_title: str = ""
    ) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        url = f"{BASE}?action=printpage;topic={topic_id}"
        html = self._get_html(url)
        if html is None:
            return None, []
        soup = BeautifulSoup(html, "lxml")
        title_tag = soup.title.string if soup.title else ""
        if title_tag and "login" in title_tag.lower():
            logger.debug("Topic %s requires login", topic_id)
            return None, []
        posts, topic_title = _parse_printpage(html, topic_id)
        title = topic_title or listing_title
        topic = {
            "id": topic_id,
            "title": title,
            "board_id": self.board_id,
            "board": BOARD_NAME,
            "n_posts": len(posts),
            "url": f"{BASE}?topic={topic_id}.0",
            "print_url": url,
            "source": "bitcointalk",
        }
        return topic, posts

    def _get_html(self, url: str, retries: int = 6) -> Optional[str]:
        for attempt in range(retries):
            wait = self.delay - (time.monotonic() - self._last_request)
            if wait > 0:
                time.sleep(wait)
            try:
                resp = self.session.get(url, timeout=90)
            except requests.RequestException as exc:
                logger.warning("Request error %s (%s/%s): %s", url, attempt + 1, retries, exc)
                time.sleep(min(60, 3 * (attempt + 1)))
                continue
            self._last_request = time.monotonic()
            if resp.status_code in (403, 429) or resp.status_code >= 500:
                self._consecutive_blocks += 1
                sleep_s = min(120, 8 * (attempt + 1))
                logger.warning(
                    "%s from %s; sleeping %ss (blocks=%s)",
                    resp.status_code,
                    url,
                    sleep_s,
                    self._consecutive_blocks,
                )
                time.sleep(sleep_s)
                continue
            self._consecutive_blocks = 0
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or resp.encoding or "utf-8"
            return resp.text
        return None


def _topics_from_board_page(html: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    topics: List[Dict[str, Any]] = []
    seen: Set[int] = set()

    for row in soup.select("tr"):
        if "Moderators:" in row.get_text(" ", strip=True):
            continue
        tds = row.find_all("td")
        if len(tds) < 7:
            continue
        link = tds[2].find("a", href=TOPIC_ID_RE) if len(tds) > 2 else None
        if link is None:
            link = row.find("a", href=TOPIC_ID_RE)
        if not link:
            continue
        match = TOPIC_ID_RE.search(link.get("href", ""))
        if not match:
            continue
        topic_id = int(match.group(1))
        if topic_id in seen:
            continue
        title = link.get_text(" ", strip=True)
        if not title or title.lower() in {"new", "last post"} or title.isdigit():
            continue
        replies = _replies_from_cells(tds)
        seen.add(topic_id)
        topics.append(
            {
                "id": topic_id,
                "title": title,
                "url": f"{BASE}?topic={topic_id}.0",
                "replies": replies,
            }
        )

    if topics:
        return topics

    for span in soup.select('span[id^="msg_"]'):
        link = span.find("a", href=True)
        if not link:
            continue
        match = TOPIC_ID_RE.search(link["href"])
        if not match:
            continue
        topic_id = int(match.group(1))
        if topic_id in seen:
            continue
        title = link.get_text(" ", strip=True)
        if not title:
            continue
        seen.add(topic_id)
        topics.append(
            {
                "id": topic_id,
                "title": title,
                "url": f"{BASE}?topic={topic_id}.0",
            }
        )
    if topics:
        return topics
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if "topic=" not in href or link.get("class") == ["navPages"]:
            continue
        match = TOPIC_ID_RE.search(href)
        if not match:
            continue
        topic_id = int(match.group(1))
        title = link.get_text(" ", strip=True)
        if not title or title.lower() in {"new", "last post", "re:"} or title.isdigit():
            continue
        if topic_id in seen:
            continue
        seen.add(topic_id)
        topics.append({"id": topic_id, "title": title, "url": f"{BASE}?topic={topic_id}.0"})
    return topics


def _replies_from_cells(tds: List[Any]) -> Optional[int]:
    """SMF board layout: td[4] = reply count, td[5] = view count."""
    if len(tds) < 5:
        return None
    text = tds[4].get_text(" ", strip=True)
    if text.isdigit():
        return int(text)
    return None


def _max_board_offset(html: str) -> int:
    offsets = [int(x) for x in BOARD_OFFSET_RE.findall(html)]
    return max(offsets) if offsets else 0


def _parse_printpage(html: str, topic_id: int) -> Tuple[List[Dict[str, Any]], str]:
    soup = BeautifulSoup(html, "lxml")
    page_title = ""
    if soup.title and soup.title.string:
        page_title = re.sub(r"^Print Page\s*-\s*", "", soup.title.string.strip())
    chunks = re.split(r'<hr\s+size="2"[^>]*>', html, flags=re.I)
    posts: List[Dict[str, Any]] = []
    for idx, chunk in enumerate(chunks[1:], start=1):
        section = BeautifulSoup(chunk, "lxml")
        author = ""
        date_raw = ""
        title = ""
        bold = section.find_all("b")
        # Title: <b>..., Post by: <b>author</b> on <b>date</b>
        text_head = section.get_text(" ", strip=True)[:400]
        title_m = re.search(r"Title:\s*(.*?)\s*Post by:", text_head, re.I)
        if title_m:
            title = title_m.group(1).strip()
        if len(bold) >= 3:
            title = title or bold[0].get_text(" ", strip=True)
            author = bold[1].get_text(" ", strip=True)
            date_raw = bold[2].get_text(" ", strip=True)
        elif len(bold) >= 2:
            author = bold[0].get_text(" ", strip=True)
            date_raw = bold[1].get_text(" ", strip=True)
        content_div = section.find("div", style=re.compile(r"margin", re.I))
        content = content_div.get_text("\n", strip=True) if content_div else ""
        if not author and not content:
            continue
        msg_ids = MSG_ID_RE.findall(chunk)
        msg_id = int(msg_ids[0]) if msg_ids else None
        posts.append(
            {
                "forum": "bitcointalk",
                "board": BOARD_NAME,
                "board_id": BOARD_ID,
                "topic_id": topic_id,
                "msg_id": msg_id,
                "post_index": idx,
                "title": title,
                "author": author,
                "date": _parse_forum_date(date_raw),
                "date_raw": date_raw,
                "content": content,
                "url": f"{BASE}?topic={topic_id}.msg{msg_id}#msg{msg_id}"
                if msg_id
                else f"{BASE}?topic={topic_id}.0",
                "source": "bitcointalk",
            }
        )
    return posts, page_title


def _parse_forum_date(value: str) -> Optional[str]:
    value = (value or "").strip()
    if not value:
        return None
    for fmt in DATE_FORMATS:
        try:
            dt = datetime.strptime(value, fmt)
            return dt.replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            continue
    return value


def _count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    n = 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                n += 1
    return n


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect Bitcointalk board 6 via printpage")
    parser.add_argument("--delay", type=float, default=1.2, help="Seconds between HTTP requests")
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--max-topics", type=int, default=None, help="Cap topics this run (testing)")
    parser.add_argument("--list-only", action="store_true", help="Write topic index only")
    parser.add_argument(
        "--update",
        action="store_true",
        help="Scan recent board pages; fetch new/changed topics only",
    )
    parser.add_argument(
        "--rebuild-posts",
        action="store_true",
        help="Re-fetch all topics from topics.jsonl and rebuild posts.jsonl",
    )
    args = parser.parse_args()
    collector = BitcoinTalkCollector(delay=args.delay)
    if args.rebuild_posts:
        collector.rebuild_posts()
    elif args.update:
        collector.collect_update()
    else:
        collector.collect(resume=not args.no_resume, max_topics=args.max_topics, list_only=args.list_only)


if __name__ == "__main__":
    main()
