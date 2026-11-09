"""Expected-versus-ingested coverage. Missing months are listed, not estimated."""

from __future__ import annotations

import calendar
from typing import Iterable, List, Sequence, Tuple


def month_names(start: Tuple[int, int], end: Tuple[int, int]) -> List[str]:
    """Inclusive year-month pairs as pipermail filenames."""
    year, month = start
    out: List[str] = []
    while (year, month) <= end:
        out.append(f"{year}-{calendar.month_name[month]}.txt.gz")
        month += 1
        if month == 13:
            year += 1
            month = 1
    return out


def prehistory_coverage(filenames: Iterable[str]) -> dict:
    """2008-01 through 2011-12 is the 48-month window the collector documents."""
    expected = month_names((2008, 1), (2011, 12))
    present = set(filenames)
    missing = [name for name in expected if name not in present]
    return {
        "window": "2008-01/2011-12",
        "expected": len(expected),
        "ingested": len(expected) - len(missing),
        "missing": missing,
        "upstream": "Months checked on 2026-11-09 returned HTTP 404 from metzdowd pipermail.",
    }
