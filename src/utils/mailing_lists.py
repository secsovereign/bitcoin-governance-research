"""Canonical mailing-list data access.

bitcoin-dev: gnusha.org public-inbox (`gnusha_collector.py` → emails.jsonl).
cryptography: metzdowd pipermail (`cryptography_ml_collector.py`).

Cross-list loaders and dedupe live in ``cross_platform_sources``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterator, List, Optional

from src.utils.cross_platform_sources import (
    iter_mailing_list,
    load_emails as _load_bitcoin_dev_emails,
    load_mailing_lists,
)
from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir

logger = setup_logger()

COLLECT_HINT = (
    "Mailing list dump missing. Collect it with: "
    "python scripts/data_collection/gnusha_collector.py"
)


def emails_raw_path() -> Path:
    return get_data_dir() / "mailing_lists" / "emails.jsonl"


def emails_cleaned_path() -> Path:
    return get_data_dir() / "processed" / "cleaned_emails.jsonl"


def gnusha_manifest_path() -> Path:
    return get_data_dir() / "mailing_lists" / "gnusha_manifest.json"


def has_canonical_dump() -> bool:
    """True when the gnusha-produced emails.jsonl is present and non-trivial."""
    path = emails_raw_path()
    return path.exists() and path.stat().st_size > 10_000


def resolve_emails_path(*, prefer_cleaned: bool = True) -> Optional[Path]:
    """Return cleaned emails if present, otherwise the raw gnusha dump."""
    cleaned = emails_cleaned_path()
    raw = emails_raw_path()
    if prefer_cleaned and cleaned.exists() and cleaned.stat().st_size > 0:
        return cleaned
    if raw.exists() and raw.stat().st_size > 0:
        return raw
    return None


def iter_emails(*, prefer_cleaned: bool = True) -> Iterator[Dict]:
    """Yield bitcoin-dev records (backward compatible)."""
    yield from iter_mailing_list("bitcoin-dev", prefer_cleaned_bitcoin_dev=prefer_cleaned)


def load_emails(*, prefer_cleaned: bool = True) -> List[Dict]:
    """Load bitcoin-dev mailing list into memory."""
    return _load_bitcoin_dev_emails(prefer_cleaned=prefer_cleaned)
