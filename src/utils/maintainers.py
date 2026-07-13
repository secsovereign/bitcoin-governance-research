"""Canonical Bitcoin Core maintainer identity helpers.

Bitcoin Core does not ship a MAINTAINERS file. Analyses historically each
hardcoded slightly different sets, while enrichment expected
``data/processed/maintainer_timeline.json`` — which was empty because
timeline collection incorrectly required ``state == "merged"`` (GitHub
uses ``state=closed`` + ``merged=true``).

This module is the single source of truth for maintainer logins and for
loading the inferred timeline used by enrichment.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Set

from src.utils.paths import get_data_dir, get_project_root


CANONICAL_FILENAME = "canonical_maintainers.json"


def _maintainers_dir() -> Path:
    return get_data_dir() / "maintainers"


def canonical_maintainers_path() -> Path:
    return _maintainers_dir() / CANONICAL_FILENAME


def load_canonical_maintainers() -> Dict[str, Any]:
    """Load canonical maintainer document."""
    path = canonical_maintainers_path()
    if not path.exists():
        # Fallback hardcoded set matching MAINTAINER_LIST_SOURCE.md
        return {
            "github_logins": [
                "laanwj",
                "sipa",
                "maflcko",
                "fanquake",
                "hebasto",
                "jnewbery",
                "ryanofsky",
                "achow101",
                "theuni",
                "jonasschnelli",
                "Sjors",
                "promag",
                "instagibbs",
                "TheBlueMatt",
                "jonatack",
                "gmaxwell",
                "gavinandresen",
                "petertodd",
                "luke-jr",
                "glozow",
                "TheCharlatan",
            ],
            "aliases": {
                "marcofalke": "maflcko",
                "thebluesmatt": "TheBlueMatt",
                "sjors": "Sjors",
            },
        }
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_login(login: Optional[str], aliases: Optional[Dict[str, str]] = None) -> str:
    """Lowercase login and apply known aliases → canonical lowercase key."""
    if not login:
        return ""
    lower = str(login).strip().lower()
    if aliases is None:
        aliases = load_canonical_maintainers().get("aliases") or {}
    # alias keys are lowercase github nicknames → preferred login
    if lower in aliases:
        return str(aliases[lower]).lower()
    return lower


def load_maintainer_login_set() -> Set[str]:
    """Return lowercase GitHub logins for the canonical maintainer set."""
    doc = load_canonical_maintainers()
    aliases = doc.get("aliases") or {}
    logins = {normalize_login(x, aliases) for x in (doc.get("github_logins") or [])}
    logins |= {normalize_login(k, aliases) for k in aliases}
    logins |= {normalize_login(v, aliases) for v in aliases.values()}
    logins.discard("")
    return logins


def load_maintainer_timeline() -> Dict[str, Any]:
    """Load ``maintainer_timeline`` map keyed by lowercase GitHub login."""
    path = get_data_dir() / "processed" / "maintainer_timeline.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    raw = data.get("maintainer_timeline") or {}
    # Normalize keys to lowercase
    out: Dict[str, Any] = {}
    for k, v in raw.items():
        out[str(k).lower()] = v
    return out


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def is_maintainer_at(
    login: Optional[str],
    when: Optional[str] = None,
    timeline: Optional[Dict[str, Any]] = None,
    *,
    require_active_period: bool = False,
) -> bool:
    """Return whether ``login`` is a maintainer.

    Default behavior matches historical analyses: membership in the
    canonical/timeline set (ever-maintainer). If ``require_active_period``
    is True and periods exist, require ``when`` to fall inside a period.
    """
    key = normalize_login(login)
    if not key:
        return False
    timeline = timeline if timeline is not None else load_maintainer_timeline()
    entry = timeline.get(key)
    if entry is None:
        # Fall back to canonical set if timeline not built yet
        return key in load_maintainer_login_set()

    if not require_active_period or not when:
        return True

    periods = entry.get("periods") or []
    if not periods:
        # Documented maintainers with no merge activity: treat as ever
        return bool(entry.get("ever_maintainer", True))

    item_date = _parse_dt(when)
    if item_date is None:
        return True
    if item_date.tzinfo is None:
        item_date = item_date.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    for period in periods:
        start = _parse_dt(period.get("start"))
        end = _parse_dt(period.get("end")) or now
        if start is None:
            continue
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        if start <= item_date <= end:
            return True
    return False
