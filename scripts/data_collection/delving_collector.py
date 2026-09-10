#!/usr/bin/env python3
"""
Collect Delving Bitcoin (Discourse) topics and posts via the public JSON API.

Sources:
  - https://delvingbitcoin.org/sitemap_*.xml  (complete topic id list)
  - https://delvingbitcoin.org/t/{id}.json    (topic + first post chunk)
  - https://delvingbitcoin.org/t/{id}/posts.json  (remaining posts)

Output:
  data/delving/topics.jsonl
  data/delving/posts.jsonl
  data/delving/manifest.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.jsonl_merge import load_jsonl_index, write_jsonl
from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir

logger = setup_logger()

BASE = "https://delvingbitcoin.org"
UA = "BitcoinGovernanceResearch/1.0 (academic; +https://bitcoincommons.org)"
SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
TOPIC_URL_RE = re.compile(r"/t/[^/]+/(\d+)(?:/|$)")


class DelvingCollector:
    def __init__(self, delay: float = 0.35) -> None:
        self.delay = delay
        self.data_dir = get_data_dir() / "delving"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.topics_file = self.data_dir / "topics.jsonl"
        self.posts_file = self.data_dir / "posts.jsonl"
        self.manifest_file = self.data_dir / "manifest.json"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": UA,
                "Accept": "application/json, application/xml, text/xml, */*",
            }
        )
        self._last_request = 0.0

    def collect(self, resume: bool = True) -> Dict[str, Any]:
        logger.info("Starting Delving Bitcoin collection")
        topic_ids = self._discover_topic_ids()
        logger.info("Discovered %s topic ids", len(topic_ids))

        done = self._existing_topic_ids() if resume else set()
        if done:
            logger.info("Resuming: %s topics already on disk", len(done))

        pending = [tid for tid in topic_ids if tid not in done]
        errors = 0
        collected = 0
        mode = "a" if done else "w"
        topics_fh = open(self.topics_file, mode, encoding="utf-8")
        posts_fh = open(self.posts_file, mode, encoding="utf-8")
        try:
            for i, tid in enumerate(pending, 1):
                try:
                    topic, posts = self._fetch_topic(tid)
                    if topic is None:
                        errors += 1
                        continue
                    topics_fh.write(json.dumps(topic, ensure_ascii=False) + "\n")
                    for post in posts:
                        posts_fh.write(json.dumps(post, ensure_ascii=False) + "\n")
                    topics_fh.flush()
                    posts_fh.flush()
                    collected += 1
                    if i % 50 == 0 or i == len(pending):
                        logger.info(
                            "Delving topics %s/%s (this run %s, errors %s)",
                            i,
                            len(pending),
                            collected,
                            errors,
                        )
                except Exception as exc:
                    errors += 1
                    logger.warning("Topic %s failed: %s", tid, exc)
        finally:
            topics_fh.close()
            posts_fh.close()

        n_topics = _count_lines(self.topics_file)
        n_posts = _count_lines(self.posts_file)
        manifest = {
            "source": BASE,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "topic_ids_discovered": len(topic_ids),
            "topics": n_topics,
            "posts": n_posts,
            "new_this_run": collected,
            "errors": errors,
        }
        self.manifest_file.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        logger.info("Delving collection complete: %s topics, %s posts", n_topics, n_posts)
        return manifest

    def collect_update(self) -> Dict[str, Any]:
        """Fetch new topics and refresh topics with new replies since last run."""
        logger.info("Starting Delving Bitcoin incremental update")
        topic_ids = self._discover_topic_ids()
        existing_topics = load_jsonl_index(self.topics_file, lambda t: t.get("id"))
        posts_by_id = load_jsonl_index(self.posts_file, lambda p: p.get("post_id"))

        new_topics = refreshed = errors = 0
        for i, tid in enumerate(topic_ids, 1):
            stored = existing_topics.get(tid)
            try:
                if stored is None:
                    topic, posts = self._fetch_topic(tid)
                    if topic is None:
                        errors += 1
                        continue
                    existing_topics[tid] = topic
                    for post in posts:
                        posts_by_id[post["post_id"]] = post
                    new_topics += 1
                    continue

                meta = self._get_json(f"{BASE}/t/{tid}.json", allow_404=True)
                if not meta:
                    errors += 1
                    continue
                api_posts = int(meta.get("posts_count") or 0)
                stored_posts = int(stored.get("posts_count") or 0)
                api_last = meta.get("last_posted_at") or ""
                stored_last = stored.get("last_posted_at") or ""
                if api_posts <= stored_posts and api_last == stored_last:
                    continue

                topic, posts = self._fetch_topic(tid)
                if topic is None:
                    errors += 1
                    continue
                existing_topics[tid] = topic
                added_posts = 0
                for post in posts:
                    pid = post.get("post_id")
                    if pid not in posts_by_id:
                        added_posts += 1
                    posts_by_id[pid] = post
                refreshed += 1
                logger.debug("Refreshed topic %s (+%s posts)", tid, added_posts)
            except Exception as exc:
                errors += 1
                logger.warning("Topic %s update failed: %s", tid, exc)

            if i % 100 == 0 or i == len(topic_ids):
                logger.info(
                    "Delving update %s/%s (new %s, refreshed %s, errors %s)",
                    i,
                    len(topic_ids),
                    new_topics,
                    refreshed,
                    errors,
                )

        write_jsonl(
            self.topics_file,
            existing_topics.values(),
            sort_key=lambda t: t.get("id") or 0,
        )
        write_jsonl(
            self.posts_file,
            posts_by_id.values(),
            sort_key=lambda p: (p.get("topic_id") or 0, p.get("post_number") or 0),
        )
        manifest = {
            "source": BASE,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "topic_ids_discovered": len(topic_ids),
            "topics": len(existing_topics),
            "posts": len(posts_by_id),
            "new_topics": new_topics,
            "refreshed_topics": refreshed,
            "errors": errors,
        }
        self.manifest_file.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        logger.info(
            "Delving update complete: +%s topics, %s refreshed, %s total posts",
            new_topics,
            refreshed,
            len(posts_by_id),
        )
        return manifest

    def _discover_topic_ids(self) -> List[int]:
        ids: Set[int] = set()
        try:
            index = self._get(f"{BASE}/sitemap.xml")
            root = ET.fromstring(index.content)
            sitemap_locs = [
                loc.text
                for loc in root.findall(".//sm:loc", SITEMAP_NS)
                if loc.text
            ]
            if not sitemap_locs:
                sitemap_locs = [el.text for el in root.iter() if el.tag.endswith("loc") and el.text]
            for loc in sitemap_locs:
                sm = self._get(loc)
                ids.update(_topic_ids_from_sitemap(sm.content))
            logger.info("Sitemap yielded %s topic ids", len(ids))
        except Exception as exc:
            logger.warning("Sitemap discovery failed (%s); falling back to category pagination", exc)

        for slug, cat_id in _categories(self):
            page = 0
            while True:
                url = f"{BASE}/c/{slug}/{cat_id}.json?page={page}"
                data = self._get_json(url)
                topics = (data or {}).get("topic_list", {}).get("topics") or []
                if not topics:
                    break
                for topic in topics:
                    if topic.get("id"):
                        ids.add(int(topic["id"]))
                more = (data or {}).get("topic_list", {}).get("more_topics_url")
                page += 1
                if not more:
                    break
                if page > 500:
                    logger.warning("Stopping category %s after 500 pages", slug)
                    break

        return sorted(ids)

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

    def _fetch_topic(self, topic_id: int) -> tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        data = self._get_json(f"{BASE}/t/{topic_id}.json", allow_404=True)
        if not data:
            return None, []
        posts_by_id = {}
        stream = (data.get("post_stream") or {}).get("stream") or []
        for post in (data.get("post_stream") or {}).get("posts") or []:
            parsed = _normalize_post(post, topic_id, data.get("slug") or "")
            posts_by_id[parsed["post_id"]] = parsed

        missing = [pid for pid in stream if pid not in posts_by_id]
        for chunk in _chunks(missing, 50):
            extra = self._get_json(
                f"{BASE}/t/{topic_id}/posts.json",
                params=[("post_ids[]", pid) for pid in chunk],
                allow_404=True,
            )
            for post in _posts_from_payload(extra):
                parsed = _normalize_post(post, topic_id, data.get("slug") or "")
                posts_by_id[parsed["post_id"]] = parsed

        posts = list(posts_by_id.values())
        posts.sort(key=lambda p: (p.get("post_number") or 0, p.get("post_id") or 0))
        details = data.get("details") or {}
        created_by = ((details.get("created_by") or {}).get("username")) or ""
        topic = {
            "id": data.get("id") or topic_id,
            "title": data.get("title") or "",
            "slug": data.get("slug") or "",
            "category_id": data.get("category_id"),
            "created_at": data.get("created_at"),
            "last_posted_at": data.get("last_posted_at"),
            "posts_count": data.get("posts_count"),
            "reply_count": data.get("reply_count"),
            "views": data.get("views"),
            "like_count": data.get("like_count"),
            "tags": data.get("tags") or [],
            "closed": data.get("closed"),
            "archived": data.get("archived"),
            "pinned": data.get("pinned"),
            "created_by": created_by,
            "url": f"{BASE}/t/{data.get('slug') or topic_id}/{topic_id}",
            "source": "delving_bitcoin",
        }
        return topic, posts

    def _get_json(
        self,
        url: str,
        params: Any = None,
        allow_404: bool = False,
    ) -> Optional[Dict[str, Any]]:
        resp = self._get(url, params=params, allow_404=allow_404)
        if resp is None:
            return None
        try:
            return resp.json()
        except ValueError:
            logger.warning("Non-JSON response from %s", url)
            return None

    def _get(
        self,
        url: str,
        params: Any = None,
        allow_404: bool = False,
        retries: int = 5,
    ) -> Optional[requests.Response]:
        for attempt in range(retries):
            wait = self.delay - (time.monotonic() - self._last_request)
            if wait > 0:
                time.sleep(wait)
            try:
                resp = self.session.get(url, params=params, timeout=60)
            except requests.RequestException as exc:
                logger.warning("Request error %s (%s/%s): %s", url, attempt + 1, retries, exc)
                time.sleep(min(30, 2 ** attempt))
                continue
            self._last_request = time.monotonic()
            if resp.status_code == 404 and allow_404:
                return None
            if resp.status_code == 429:
                retry_after = float(resp.headers.get("Retry-After") or min(60, 5 * (attempt + 1)))
                logger.warning("429 from %s; sleeping %.1fs", url, retry_after)
                time.sleep(retry_after)
                continue
            if resp.status_code >= 500:
                time.sleep(min(30, 2 ** attempt))
                continue
            resp.raise_for_status()
            return resp
        logger.warning("Giving up on %s", url)
        return None


def _categories(collector: DelvingCollector) -> List[tuple[str, int]]:
    data = collector._get_json(f"{BASE}/categories.json") or {}
    cats = (data.get("category_list") or {}).get("categories") or []
    out = []
    for cat in cats:
        slug = cat.get("slug")
        cid = cat.get("id")
        if slug and cid:
            out.append((slug, int(cid)))
        for sub in cat.get("subcategory_list") or cat.get("subcategories") or []:
            sslug, sid = sub.get("slug"), sub.get("id")
            if sslug and sid:
                out.append((sslug, int(sid)))
    return out


def _topic_ids_from_sitemap(xml_bytes: bytes) -> Set[int]:
    ids: Set[int] = set()
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return ids
    for loc in root.iter():
        if not loc.tag.endswith("loc") or not loc.text:
            continue
        match = TOPIC_URL_RE.search(loc.text)
        if match:
            ids.add(int(match.group(1)))
    return ids


def _posts_from_payload(payload: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not payload:
        return []
    posts = (payload.get("post_stream") or {}).get("posts")
    if posts is None:
        posts = payload.get("posts")
    return posts or []


def _like_count(post: Dict[str, Any]) -> int:
    for action in post.get("actions_summary") or []:
        if action.get("id") == 2:
            return int(action.get("count") or 0)
    return 0


def _html_to_text(html: str) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "lxml")
    return soup.get_text("\n", strip=True)


def _normalize_post(post: Dict[str, Any], topic_id: int, slug: str) -> Dict[str, Any]:
    cooked = post.get("cooked") or ""
    return {
        "topic_id": topic_id,
        "post_id": post.get("id"),
        "post_number": post.get("post_number"),
        "username": post.get("username") or "",
        "display_name": post.get("name") or post.get("display_username") or "",
        "created_at": post.get("created_at"),
        "updated_at": post.get("updated_at"),
        "reply_to_post_number": post.get("reply_to_post_number"),
        "reply_count": post.get("reply_count"),
        "like_count": _like_count(post),
        "content": _html_to_text(cooked),
        "cooked_html": cooked,
        "url": f"{BASE}/t/{slug}/{topic_id}/{post.get('post_number') or 1}",
        "source": "delving_bitcoin",
    }


def _chunks(items: List[Any], size: int) -> Iterable[List[Any]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


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
    parser = argparse.ArgumentParser(description="Collect Delving Bitcoin Discourse archive")
    parser.add_argument("--delay", type=float, default=0.35, help="Seconds between HTTP requests")
    parser.add_argument("--no-resume", action="store_true", help="Overwrite existing jsonl files")
    parser.add_argument("--update", action="store_true", help="Fetch new topics and refresh topics with new replies")
    args = parser.parse_args()
    collector = DelvingCollector(delay=args.delay)
    if args.update:
        collector.collect_update()
    else:
        collector.collect(resume=not args.no_resume)


if __name__ == "__main__":
    main()
