#!/usr/bin/env python3
"""
Maintainer Timeline Tracker

Builds ``data/processed/maintainer_timeline.json`` and refreshes
``data/maintainers/maintainers_summary.json`` for enrichment and analyses.

Bitcoin Core has no in-tree MAINTAINERS file. Timeline construction:

1. Seed from ``data/maintainers/canonical_maintainers.json`` (documented set).
2. Infer active periods from ``merged_by`` on cleaned/enriched PRs
   (``merged=True``, not ``state=="merged"`` — that bug emptied the timeline).

Run via ``enrich_data.py`` (builds timeline automatically) or directly before analyses.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger  # noqa: E402
from src.utils.maintainers import (  # noqa: E402
    load_canonical_maintainers,
    normalize_login,
)
from src.utils.paths import get_data_dir  # noqa: E402

logger = setup_logger()


class MaintainerTimelineTracker:
    """Tracks maintainer status from canonical list + merge activity."""

    def __init__(self):
        self.data_dir = get_data_dir()
        self.processed_dir = self.data_dir / "processed"
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.maintainers_dir = self.data_dir / "maintainers"
        self.maintainers_dir.mkdir(parents=True, exist_ok=True)

        self.canonical = load_canonical_maintainers()
        self.aliases = self.canonical.get("aliases") or {}
        self.canonical_logins = [
            normalize_login(x, self.aliases) for x in (self.canonical.get("github_logins") or [])
        ]

        self.user_merges: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
        self.maintainer_timeline: Dict[str, Any] = {}

    def build_timeline(self) -> None:
        logger.info("=" * 60)
        logger.info("Maintainer Timeline Tracking")
        logger.info("=" * 60)

        prs_file = self._resolve_prs_file()
        if prs_file is None:
            logger.error("No PR JSONL found (cleaned_prs / enriched_prs)")
            return

        logger.info("Using PR source: %s", prs_file)
        self._collect_merge_data(prs_file)
        self._seed_canonical()
        self._apply_merge_inference()
        self._save_timeline()
        self._save_summary()
        logger.info("Identified %s maintainers", len(self.maintainer_timeline))
        logger.info("=" * 60)

    def _resolve_prs_file(self) -> Optional[Path]:
        # Prefer cleaned (pipeline order); fall back to enriched which already has merged_by
        for name in ("cleaned_prs.jsonl", "enriched_prs.jsonl"):
            path = self.processed_dir / name
            if path.exists():
                return path
        raw = self.data_dir / "github" / "prs_raw.jsonl"
        return raw if raw.exists() else None

    def _collect_merge_data(self, prs_file: Path) -> None:
        merge_count = 0
        with open(prs_file, encoding="utf-8") as f:
            for line in f:
                try:
                    pr = json.loads(line)
                except json.JSONDecodeError:
                    continue
                # CRITICAL: GitHub PRs are state=closed when merged; use merged flag.
                if not pr.get("merged") or not pr.get("merged_at"):
                    continue
                merged_by = pr.get("merged_by")
                if isinstance(merged_by, dict):
                    merged_by = merged_by.get("login")
                if not merged_by:
                    continue
                login = normalize_login(merged_by, self.aliases)
                if not login:
                    continue
                self.user_merges[login].append((pr["merged_at"], int(pr.get("number") or 0)))
                merge_count += 1
        logger.info(
            "Collected %s merges from %s distinct mergers",
            merge_count,
            len(self.user_merges),
        )

    def _seed_canonical(self) -> None:
        for login in self.canonical_logins:
            self.maintainer_timeline[login] = {
                "github_login": login,
                "ever_maintainer": True,
                "confidence": "documented",
                "evidence": ["canonical_list"],
                "merge_count": 0,
                "periods": [],
                "first_merge": None,
                "last_merge": None,
                "estimated_start": None,
                "estimated_end": None,
            }

    def _apply_merge_inference(self) -> None:
        logger.info("Inferring active periods from merge activity...")
        # Also add high-volume mergers not on canonical list (rare historical access)
        for login, merges in self.user_merges.items():
            merges = sorted(merges, key=lambda x: x[0])
            if login not in self.maintainer_timeline:
                if len(merges) < 10:
                    continue
                self.maintainer_timeline[login] = {
                    "github_login": login,
                    "ever_maintainer": True,
                    "confidence": "inferred_merger",
                    "evidence": ["merge_pattern"],
                    "merge_count": 0,
                    "periods": [],
                    "first_merge": None,
                    "last_merge": None,
                    "estimated_start": None,
                    "estimated_end": None,
                    "note": "Not on canonical list; inferred from ≥10 merges",
                }

            entry = self.maintainer_timeline[login]
            entry["merge_count"] = len(merges)
            entry["first_merge"] = merges[0][0]
            entry["last_merge"] = merges[-1][0]
            if "merge_pattern" not in entry["evidence"]:
                entry["evidence"].append("merge_pattern")
            if entry["confidence"] == "documented" and len(merges) >= 10:
                entry["confidence"] = "high"
            elif entry["confidence"] == "documented" and len(merges) >= 1:
                entry["confidence"] = "medium"

            periods = self._periods_from_merges(merges)
            entry["periods"] = periods
            if periods:
                entry["estimated_start"] = periods[0]["start"]
                entry["estimated_end"] = periods[-1]["end"]

            by_year: Dict[int, int] = defaultdict(int)
            for merge_date, _ in merges:
                try:
                    by_year[datetime.fromisoformat(merge_date.replace("Z", "+00:00")).year] += 1
                except Exception:
                    pass
            entry["merge_count_by_year"] = dict(by_year)

        # Documented maintainers with zero merges: open-ended documented period
        for login, entry in self.maintainer_timeline.items():
            if entry["merge_count"] == 0 and not entry["periods"]:
                entry["periods"] = [
                    {
                        "start": "2009-01-03T00:00:00+00:00",
                        "end": None,
                        "type": "documented",
                    }
                ]
                entry["estimated_start"] = entry["periods"][0]["start"]
                entry["estimated_end"] = None

    def _periods_from_merges(self, merges: List[Tuple[str, int]]) -> List[Dict[str, Any]]:
        periods: List[Dict[str, Any]] = []
        current_start: Optional[datetime] = None
        current_end: Optional[datetime] = None
        for merge_date, _ in merges:
            try:
                merge_dt = datetime.fromisoformat(merge_date.replace("Z", "+00:00"))
            except Exception:
                continue
            if current_start is None:
                current_start = merge_dt
                current_end = merge_dt
                continue
            assert current_end is not None
            if (merge_dt - current_end).days > 180:
                periods.append(
                    {
                        "start": current_start.isoformat(),
                        "end": current_end.isoformat(),
                        "type": "inferred",
                    }
                )
                current_start = merge_dt
                current_end = merge_dt
            else:
                current_end = merge_dt
        if current_start is not None and current_end is not None:
            age_days = (datetime.now(timezone.utc) - current_end).days
            periods.append(
                {
                    "start": current_start.isoformat(),
                    "end": None if age_days < 365 else current_end.isoformat(),
                    "type": "inferred",
                }
            )
        return periods

    def _save_timeline(self) -> None:
        output_file = self.processed_dir / "maintainer_timeline.json"
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": "canonical_maintainers.json + merged_by inference",
            "total_maintainers": len(self.maintainer_timeline),
            "maintainer_timeline": self.maintainer_timeline,
        }
        output_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        logger.info("Wrote %s", output_file)

        high = sum(1 for d in self.maintainer_timeline.values() if d["confidence"] == "high")
        active = sum(1 for d in self.maintainer_timeline.values() if d.get("estimated_end") is None)
        logger.info(
            "Summary: total=%s high=%s active_open_ended=%s total_merges=%s",
            len(self.maintainer_timeline),
            high,
            active,
            sum(d["merge_count"] for d in self.maintainer_timeline.values()),
        )

    def _save_summary(self) -> None:
        """Write maintainers_summary.json in the shape consumers expect."""
        maintainers = []
        for login, entry in sorted(
            self.maintainer_timeline.items(), key=lambda x: -x[1].get("merge_count", 0)
        ):
            maintainers.append(
                {
                    "github": login,
                    "name": login,
                    "merge_count": entry.get("merge_count", 0),
                    "confidence": entry.get("confidence"),
                    "first_merge": entry.get("first_merge"),
                    "last_merge": entry.get("last_merge"),
                    "ever_maintainer": entry.get("ever_maintainer", True),
                    "evidence": entry.get("evidence"),
                }
            )
        summary = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_versions": 1,
            "unique_maintainers": [m["github"] for m in maintainers],
            "maintainer_changes": [],
            "timeline": [],
            "maintainers": maintainers,
            "total_maintainers": len(maintainers),
            "source": "canonical_list + merge inference (no MAINTAINERS file in bitcoin/bitcoin)",
        }
        path = self.maintainers_dir / "maintainers_summary.json"
        path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        logger.info("Wrote %s (%s maintainers)", path, len(maintainers))


def main() -> int:
    MaintainerTimelineTracker().build_timeline()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
