"""Rewrite GitHub dump jsonl by issue/PR number. No GitHub API."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def aware_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_iso_datetime(raw: str) -> datetime:
    text = raw.strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(text)
    got = aware_utc(dt)
    if got is None:
        raise ValueError(f"invalid --updated-since {raw}")
    return got


def default_updated_since(dump: Path, now: Optional[datetime] = None) -> datetime:
    """Stale dump → mtime (catch-up). Fresh dump → 48h overlap."""
    now_utc = aware_utc(now) or datetime.now(timezone.utc)
    overlap = now_utc - timedelta(hours=48)
    if not dump.exists():
        return overlap
    mtime = datetime.fromtimestamp(dump.stat().st_mtime, tz=timezone.utc)
    return min(mtime, overlap)


def rewrite_jsonl_by_number(path: Path, updates: Dict[int, Dict[str, Any]]) -> int:
    """Replace records by `number`, append new numbers. Atomic rename in the same dir."""
    pending = dict(updates)
    out_lines: list[str] = []
    if path.exists():
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                raw = line.rstrip("\n")
                if not raw.strip():
                    continue
                try:
                    rec = json.loads(raw)
                except json.JSONDecodeError:
                    out_lines.append(raw)
                    continue
                num = rec.get("number")
                if isinstance(num, int) and num in pending:
                    out_lines.append(json.dumps(pending.pop(num), separators=(",", ":")))
                else:
                    out_lines.append(raw)
    for rec in pending.values():
        out_lines.append(json.dumps(rec, separators=(",", ":")))
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        if out_lines:
            fh.write("\n".join(out_lines))
            fh.write("\n")
    os.replace(tmp, path)
    return len(out_lines)
