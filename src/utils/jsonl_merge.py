"""Helpers for incremental jsonl collection and merge-by-key updates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Set, TypeVar

from src.utils.logger import setup_logger

logger = setup_logger()

T = TypeVar("T")
KeyFn = Callable[[Dict[str, Any]], Any]


def iter_jsonl(path: Path) -> Iterator[Dict[str, Any]]:
    if not path.exists():
        return
    with open(path, encoding="utf-8") as fh:
        for line_num, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                logger.debug("Skipping invalid JSON at %s:%s", path.name, line_num)


def load_jsonl_index(path: Path, key_fn: KeyFn) -> Dict[Any, Dict[str, Any]]:
    index: Dict[Any, Dict[str, Any]] = {}
    for record in iter_jsonl(path):
        key = key_fn(record)
        if key is None:
            continue
        index[key] = record
    return index


def load_jsonl_keys(path: Path, key_fn: KeyFn) -> Set[Any]:
    return set(load_jsonl_index(path, key_fn).keys())


def write_jsonl(path: Path, records: Iterable[Dict[str, Any]], *, sort_key: Optional[KeyFn] = None) -> int:
    rows = list(records)
    if sort_key is not None:
        rows.sort(key=lambda r: sort_key(r) or "")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        for record in rows:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    tmp.replace(path)
    return len(rows)


def merge_records(
    existing: Dict[Any, Dict[str, Any]],
    updates: Iterable[Dict[str, Any]],
    key_fn: KeyFn,
) -> tuple[Dict[Any, Dict[str, Any]], int]:
    added = 0
    for record in updates:
        key = key_fn(record)
        if key is None:
            continue
        if key not in existing:
            added += 1
        existing[key] = record
    return existing, added


def append_jsonl(path: Path, records: Iterable[Dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(path, "a", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            n += 1
    return n


def count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    n = 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                n += 1
    return n


def email_key(record: Dict[str, Any]) -> Optional[str]:
    msg_id = (record.get("message_id") or "").strip().lower()
    return msg_id or None
