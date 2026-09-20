"""Jsonl rewrite helpers for --updated-since. No GitHub API."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.github_jsonl import default_updated_since, parse_iso_datetime, rewrite_jsonl_by_number


def test_rewrite_replaces_by_number_and_appends(tmp_path: Path) -> None:
    path = tmp_path / "prs_raw.jsonl"
    path.write_text(
        json.dumps({"number": 1, "body": "old"})
        + "\n"
        + json.dumps({"number": 2, "body": "keep"})
        + "\n",
        encoding="utf-8",
    )
    n = rewrite_jsonl_by_number(
        path,
        {
            1: {"number": 1, "body": "new-review"},
            3: {"number": 3, "body": "fresh"},
        },
    )
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert n == 3
    recs = [json.loads(x) for x in lines]
    assert recs[0] == {"number": 1, "body": "new-review"}
    assert recs[1] == {"number": 2, "body": "keep"}
    assert recs[2] == {"number": 3, "body": "fresh"}


def test_rewrite_does_not_copy_full_dump_sidecar(tmp_path: Path) -> None:
    path = tmp_path / "prs_raw.jsonl"
    path.write_text(json.dumps({"number": 9, "body": "a"}) + "\n", encoding="utf-8")
    rewrite_jsonl_by_number(path, {9: {"number": 9, "body": "b"}})
    extras = [p.name for p in tmp_path.iterdir() if p.name != "prs_raw.jsonl"]
    assert extras == []


def test_stale_dump_cutoff_is_mtime_not_48h(tmp_path: Path) -> None:
    path = tmp_path / "prs_raw.jsonl"
    path.write_text("{}\n", encoding="utf-8")
    old = datetime(2026, 8, 25, tzinfo=timezone.utc).timestamp()
    os.utime(path, (old, old))
    now = datetime(2026, 9, 20, 18, 0, tzinfo=timezone.utc)
    got = default_updated_since(path, now=now)
    assert got == datetime(2026, 8, 25, tzinfo=timezone.utc)


def test_fresh_dump_uses_48h_overlap(tmp_path: Path) -> None:
    path = tmp_path / "prs_raw.jsonl"
    path.write_text("{}\n", encoding="utf-8")
    now = datetime(2026, 9, 20, 18, 0, tzinfo=timezone.utc)
    recent = (now - timedelta(hours=2)).timestamp()
    os.utime(path, (recent, recent))
    got = default_updated_since(path, now=now)
    assert got == now - timedelta(hours=48)


def test_parse_iso() -> None:
    dt = parse_iso_datetime("2026-08-25T00:00:00Z")
    assert dt == datetime(2026, 8, 25, tzinfo=timezone.utc)
