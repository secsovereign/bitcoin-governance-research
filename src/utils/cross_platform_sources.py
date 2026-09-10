"""Load informal communication sources for cross-platform analysis.

Mailing lists are kept separate by ``list_name``; when combined for aggregate
email metrics, records are deduplicated by normalized ``message_id`` (currently
~2 cross-list duplicates between bitcoin-dev and cryptography).

Delving and Bitcointalk are distinct from GitHub PR data — they may *mention*
PRs but do not duplicate PR records.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir

logger = setup_logger()

BCAP_SOM_KEYWORDS = {
    "som1": [
        "excellent", "great", "strongly support", "essential", "critical", "important",
        "strongly advocate", "fantastic", "amazing", "perfect",
    ],
    "som2": ["support", "good", "helpful", "agree", "ack", "approve", "yes", "sounds good"],
    "som3": ["maybe", "perhaps", "uncertain", "not sure", "neutral", "?", "unclear", "unsure"],
    "som5": ["concern", "worried", "skeptical", "hesitant", "nack", "oppose", "not ideal"],
    "som6": [
        "strongly oppose", "dangerous", "harmful", "bad idea", "against", "veto",
        "reject", "terrible", "wrong", "horrible",
    ],
}

MAILING_LIST_FILES = {
    "bitcoin-dev": "emails.jsonl",
    "cryptography": "cryptography.jsonl",
}

PR_PATTERN = re.compile(
    r"(?:github\.com/bitcoin/bitcoin/pull/|(?:PR|pull[/\s#]*|#))(\d{4,6})\b",
    re.IGNORECASE,
)


def normalize_message_id(message_id: str) -> str:
    return (message_id or "").strip().lower()


def _mailing_dir() -> Path:
    return get_data_dir() / "mailing_lists"


def _emails_cleaned_path() -> Path:
    return get_data_dir() / "processed" / "cleaned_emails.jsonl"


def _emails_raw_path() -> Path:
    return _mailing_dir() / "emails.jsonl"


def iter_mailing_list(list_name: str, *, prefer_cleaned_bitcoin_dev: bool = True) -> Iterator[Dict]:
    """Yield records for a single mailing list."""
    if list_name == "bitcoin-dev":
        if prefer_cleaned_bitcoin_dev:
            cleaned = _emails_cleaned_path()
            if cleaned.exists() and cleaned.stat().st_size > 0:
                path = cleaned
            else:
                path = _emails_raw_path()
        else:
            path = _emails_raw_path()
    else:
        filename = MAILING_LIST_FILES.get(list_name)
        if not filename:
            return
        path = _mailing_dir() / filename

    if not path.exists() or path.stat().st_size == 0:
        return

    with open(path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                logger.debug("Skipping invalid JSON at %s:%s", path.name, line_num)
                continue
            record.setdefault("list_name", list_name)
            yield record


def load_mailing_lists(
    *,
    lists: Optional[List[str]] = None,
    dedupe: bool = True,
    prefer_cleaned_bitcoin_dev: bool = True,
) -> Tuple[List[Dict], Dict[str, Any]]:
    """Load mailing-list records with per-list counts and optional dedupe."""
    list_names = lists or list(MAILING_LIST_FILES.keys())
    meta: Dict[str, Any] = {
        "lists_requested": list_names,
        "per_list_counts": {},
        "dedupe_enabled": dedupe,
        "duplicates_removed": 0,
        "duplicate_message_ids": [],
    }
    records: List[Dict] = []
    seen_ids: Set[str] = set()

    for list_name in list_names:
        list_records = list(
            iter_mailing_list(list_name, prefer_cleaned_bitcoin_dev=prefer_cleaned_bitcoin_dev)
        )
        meta["per_list_counts"][list_name] = len(list_records)

        for record in list_records:
            mid = normalize_message_id(record.get("message_id", ""))
            if dedupe and mid:
                if mid in seen_ids:
                    meta["duplicates_removed"] += 1
                    if len(meta["duplicate_message_ids"]) < 20:
                        meta["duplicate_message_ids"].append(mid)
                    continue
                seen_ids.add(mid)
            records.append(record)

    meta["total_loaded"] = len(records)
    return records, meta


def load_emails(*, prefer_cleaned: bool = True) -> List[Dict]:
    """Backward-compatible loader: bitcoin-dev list only."""
    records, meta = load_mailing_lists(
        lists=["bitcoin-dev"],
        dedupe=False,
        prefer_cleaned_bitcoin_dev=prefer_cleaned,
    )
    if records:
        path = _emails_cleaned_path() if prefer_cleaned and _emails_cleaned_path().exists() else _emails_raw_path()
        logger.info("Loaded %s bitcoin-dev emails from %s", f"{len(records):,}", path.name)
    return records


def _load_jsonl(path: Path) -> List[Dict]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    records: List[Dict] = []
    with open(path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                logger.debug("Skipping invalid JSON at %s:%s", path.name, line_num)
    return records


def load_delving_posts() -> Tuple[List[Dict], Dict[str, Any]]:
    path = get_data_dir() / "delving" / "posts.jsonl"
    records = _load_jsonl(path)
    meta = {"source": "delving_bitcoin", "path": str(path), "count": len(records)}
    if records:
        logger.info("Loaded %s Delving posts", f"{len(records):,}")
    return records, meta


def load_bitcointalk_posts() -> Tuple[List[Dict], Dict[str, Any]]:
    path = get_data_dir() / "bitcointalk" / "posts.jsonl"
    records = _load_jsonl(path)
    meta = {"source": "bitcointalk_board_6", "path": str(path), "count": len(records)}
    if records:
        logger.info("Loaded %s Bitcointalk posts", f"{len(records):,}")
    return records, meta


def audit_source_overlap() -> Dict[str, Any]:
    """Report cross-source duplication (for logging / methodology)."""
    gnusha_ids: Set[str] = set()
    crypto_ids: Set[str] = set()

    for record in iter_mailing_list("bitcoin-dev"):
        mid = normalize_message_id(record.get("message_id", ""))
        if mid:
            gnusha_ids.add(mid)

    for record in iter_mailing_list("cryptography"):
        mid = normalize_message_id(record.get("message_id", ""))
        if mid:
            crypto_ids.add(mid)

    overlap = gnusha_ids & crypto_ids
    delving_posts, _ = load_delving_posts()
    bitcointalk_posts, _ = load_bitcointalk_posts()

    delving_pr_refs = sum(
        1 for p in delving_posts if PR_PATTERN.search((p.get("content") or "") + (p.get("cooked_html") or ""))
    )

    return {
        "mailing_lists": {
            "bitcoin_dev_count": len(gnusha_ids),
            "cryptography_count": len(crypto_ids),
            "message_id_overlap": len(overlap),
            "overlap_note": "Dedupe by message_id when combining mailing lists for aggregate email metrics.",
        },
        "forums": {
            "delving_posts": len(delving_posts),
            "delving_posts_mentioning_core_prs": delving_pr_refs,
            "bitcointalk_posts": len(bitcointalk_posts),
            "note": "Forums are separate channels; PR mentions are links, not duplicate PR records.",
        },
        "satoshi_bitcointalk_overlap": "Not merged — Satoshi archive uses separate curated export.",
    }


def extract_pr_numbers(text: str) -> Set[str]:
    if not text:
        return set()
    return {m for m in PR_PATTERN.findall(text)}


def extract_text_author_timestamp(record: Dict, channel: str) -> Tuple[str, str, Optional[str]]:
    """Normalize author/text/timestamp for a channel type."""
    if channel == "irc":
        return (
            (record.get("message") or ""),
            (record.get("nickname") or "").lower(),
            record.get("timestamp"),
        )
    if channel in ("email", "bitcoin-dev", "cryptography"):
        text = f"{record.get('subject', '')} {record.get('body', '')}"
        from_field = record.get("from", "")
        author = _extract_email_author(from_field).lower()
        return text, author, record.get("date")
    if channel == "delving":
        return (
            (record.get("content") or ""),
            (record.get("username") or "").lower(),
            record.get("created_at"),
        )
    if channel == "bitcointalk":
        return (
            (record.get("content") or ""),
            (record.get("author") or "").lower(),
            record.get("date"),
        )
    return "", "", None


def _extract_email_author(from_field: str) -> str:
    if not from_field:
        return ""
    email_match = re.search(r"[\w.+-]+@[\w.-]+\.\w+", from_field)
    if email_match:
        return email_match.group(0).split("@")[0]
    name_match = re.search(r"^([^<]+)", from_field)
    if name_match:
        return name_match.group(1).strip()
    return from_field.strip()


def split_mailing_lists_by_name(records: List[Dict]) -> Dict[str, List[Dict]]:
    grouped: Dict[str, List[Dict]] = {}
    for record in records:
        list_name = record.get("list_name") or "unknown"
        grouped.setdefault(list_name, []).append(record)
    return grouped


def load_irc_messages() -> Tuple[List[Dict], Dict[str, Any]]:
    path = get_data_dir() / "irc" / "messages.jsonl"
    records = _load_jsonl(path)
    meta = {"source": "irc", "path": str(path), "count": len(records)}
    if records:
        logger.info("Loaded %s IRC messages", f"{len(records):,}")
    return records, meta


def load_all_informal_sources() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Load all informal channels used by cross-platform analyses."""
    emails, email_meta = load_mailing_lists(dedupe=True)
    irc, irc_meta = load_irc_messages()
    delving, delving_meta = load_delving_posts()
    bitcointalk, bitcointalk_meta = load_bitcointalk_posts()
    sources = {
        "emails": emails,
        "emails_by_list": split_mailing_lists_by_name(emails),
        "irc": irc,
        "delving": delving,
        "bitcointalk": bitcointalk,
    }
    meta = {
        "source_audit": audit_source_overlap(),
        "email_load_meta": email_meta,
        "irc_meta": irc_meta,
        "delving_meta": delving_meta,
        "bitcointalk_meta": bitcointalk_meta,
    }
    return sources, meta


def parse_record_timestamp(record: Dict, channel: str) -> Optional[datetime]:
    _, _, timestamp = extract_text_author_timestamp(record, channel)
    if not timestamp:
        return None
    try:
        if isinstance(timestamp, datetime):
            dt = timestamp
        else:
            dt = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (TypeError, ValueError):
        return None


def record_in_period(
    record: Dict,
    channel: str,
    start: datetime,
    end: datetime,
    *,
    keywords: Optional[List[str]] = None,
) -> bool:
    dt = parse_record_timestamp(record, channel)
    if dt is None or not (start <= dt <= end):
        return False
    if not keywords:
        return True
    text, _, _ = extract_text_author_timestamp(record, channel)
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


def filter_records_by_period(
    records: List[Dict],
    channel: str,
    start: datetime,
    end: datetime,
    *,
    keywords: Optional[List[str]] = None,
) -> List[Dict]:
    return [
        record
        for record in records
        if record_in_period(record, channel, start, end, keywords=keywords)
    ]


def classify_som_from_text(
    text: str,
    som_keywords: Optional[Dict[str, List[str]]] = None,
) -> Optional[str]:
    if not text:
        return None
    keywords = som_keywords or BCAP_SOM_KEYWORDS
    text_lower = text.lower()
    som_scores = {
        som: sum(1 for kw in kws if kw in text_lower)
        for som, kws in keywords.items()
    }
    som_scores = {som: score for som, score in som_scores.items() if score > 0}
    if not som_scores:
        return None
    return max(som_scores.items(), key=lambda item: item[1])[0]


def analyze_informal_som(
    messages: List[Dict[str, Any]],
    channel_type: str,
    *,
    som_keywords: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Any]:
    """BCAP SOM distribution for an informal channel."""
    author_som: Dict[str, Counter] = defaultdict(Counter)
    som_counts: Counter = Counter()

    for msg in messages:
        text, author, _ = extract_text_author_timestamp(msg, channel_type)
        if not text or not author:
            continue
        som = classify_som_from_text(text, som_keywords=som_keywords)
        if not som:
            continue
        author_som[author][som] += 1
        som_counts[som] += 1

    total = sum(som_counts.values())
    return {
        "channel": channel_type,
        "classified_messages": total,
        "som_counts": dict(som_counts),
        "som_distribution": {
            som: (count / total if total else 0.0)
            for som, count in som_counts.items()
        },
        "unique_authors": len(author_som),
        "top_authors": sorted(
            ((author, sum(counts.values())) for author, counts in author_som.items()),
            key=lambda item: item[1],
            reverse=True,
        )[:20],
    }


def summarize_informal_activity(
    sources: Dict[str, Any],
    start: datetime,
    end: datetime,
    *,
    keywords: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Message/author counts per informal channel for a date window."""
    channel_specs = [
        ("email", sources.get("emails") or [], "email"),
        ("irc", sources.get("irc") or [], "irc"),
        ("delving", sources.get("delving") or [], "delving"),
        ("bitcointalk", sources.get("bitcointalk") or [], "bitcointalk"),
    ]
    summary: Dict[str, Any] = {}
    for name, records, channel_type in channel_specs:
        filtered = filter_records_by_period(records, channel_type, start, end, keywords=keywords)
        authors = {
            extract_text_author_timestamp(record, channel_type)[1]
            for record in filtered
            if extract_text_author_timestamp(record, channel_type)[1]
        }
        summary[name] = {
            "messages": len(filtered),
            "unique_authors": len(authors),
            "som": analyze_informal_som(filtered, channel_type),
        }
    emails_by_list = sources.get("emails_by_list") or {}
    for list_name, list_records in emails_by_list.items():
        filtered = filter_records_by_period(list_records, "email", start, end, keywords=keywords)
        summary[f"mailing_list_{list_name}"] = {
            "messages": len(filtered),
            "unique_authors": len(
                {
                    extract_text_author_timestamp(record, "email")[1]
                    for record in filtered
                    if extract_text_author_timestamp(record, "email")[1]
                }
            ),
        }
    return summary
