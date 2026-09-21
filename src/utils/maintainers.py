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
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Set

_GITHUB_NOREPLY = re.compile(
    r"^(?:\d+\+)?([a-z0-9][a-z0-9-]*)@users\.noreply\.github\.com$"
)

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


def _norm_person_name(name: Optional[str]) -> str:
    if not name:
        return ""
    cleaned = re.sub(r"[._]+", " ", str(name)).strip().lower()
    return re.sub(r"\s+", " ", cleaned)


def canonicalize_actor(
    login: Optional[str] = None,
    email: Optional[str] = None,
    name: Optional[str] = None,
    doc: Optional[Dict[str, Any]] = None,
) -> str:
    """Collapse documented login / email / name variants to one key.

    Priority: GitHub login, then email alias or ``users.noreply.github.com``,
    then display-name alias. Unknown emails stay as the lowercased address so
    unsigned identities are not invented.
    """
    data = doc if doc is not None else load_canonical_maintainers()
    aliases = data.get("aliases") or {}
    email_aliases = {
        str(k).strip().lower(): str(v).strip().lower()
        for k, v in (data.get("email_aliases") or {}).items()
    }
    name_aliases = {
        _norm_person_name(k): str(v).strip().lower()
        for k, v in (data.get("name_aliases") or {}).items()
    }

    if login:
        key = normalize_login(login, aliases)
        if key:
            return key

    if email:
        lowered = str(email).strip().lower()
        if lowered in email_aliases:
            return normalize_login(email_aliases[lowered], aliases)
        noreply = _GITHUB_NOREPLY.match(lowered)
        if noreply:
            return normalize_login(noreply.group(1), aliases)

    if name:
        named = name_aliases.get(_norm_person_name(name))
        if named:
            return normalize_login(named, aliases)

    if email:
        return str(email).strip().lower()
    if name:
        return _norm_person_name(name)
    return ""


def canonicalize_nick(nick: Optional[str], doc: Optional[Dict[str, Any]] = None) -> str:
    """Collapse documented IRC nicks. Does not change the GitHub maintainer login set.

    ``TheCharlatan`` on IRC maps to ``sedited``. ``normalize_login("TheCharlatan")``
    stays ``thecharlatan``.
    """
    if not nick:
        return ""
    data = doc if doc is not None else load_canonical_maintainers()
    aliases = data.get("aliases") or {}
    nicks = {
        str(k).strip().lower(): str(v).strip().lower()
        for k, v in (data.get("nick_aliases") or {}).items()
    }
    lower = re.sub(r"^[@*]\s*", "", str(nick).strip().lower())
    if lower in nicks:
        return normalize_login(nicks[lower], aliases)
    return normalize_login(lower, aliases)


def documented_identities(doc: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    """Unified-id → github / email / irc / real_name lists from the canonical file."""
    data = doc if doc is not None else load_canonical_maintainers()
    aliases = data.get("aliases") or {}
    out: Dict[str, Dict[str, Any]] = {}

    def bucket(key: str) -> Dict[str, Any]:
        key = normalize_login(key, aliases)
        if key not in out:
            out[key] = {"github": [], "email": [], "irc": [], "real_name": ""}
        return out[key]

    for login in data.get("github_logins") or []:
        key = normalize_login(login, aliases)
        b = bucket(key)
        low = str(login).strip().lower()
        if low not in b["github"]:
            b["github"].append(low)
        if key not in b["irc"]:
            b["irc"].append(key)

    for src, dst in (data.get("aliases") or {}).items():
        b = bucket(str(dst))
        low = str(src).strip().lower()
        if low not in b["github"]:
            b["github"].append(low)

    for src, dst in (data.get("email_aliases") or {}).items():
        b = bucket(str(dst))
        low = str(src).strip().lower()
        if low not in b["email"]:
            b["email"].append(low)

    for src, dst in (data.get("nick_aliases") or {}).items():
        b = bucket(str(dst))
        low = str(src).strip().lower()
        if low not in b["irc"]:
            b["irc"].append(low)

    for key, name in (data.get("display_names") or {}).items():
        b = bucket(str(key))
        b["real_name"] = str(name)

    return out


def display_name_for(key: Optional[str], doc: Optional[Dict[str, Any]] = None) -> str:
    """Preferred public name for a canonical actor key."""
    if not key:
        return ""
    data = doc if doc is not None else load_canonical_maintainers()
    names = {str(k).lower(): v for k, v in (data.get("display_names") or {}).items()}
    return str(names.get(str(key).lower()) or key)


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


ROLE_MERGE_KEYS = "merge_keys"
ROLE_ROSTER_WITHOUT_KEYS = "roster_without_keys"
ROLE_CANNOT_MERGE = "cannot_merge"

PERSON_ROLE_PIN = (
    "Only observed GitHub merged_by logins have merge keys. "
    "Everyone else cannot merge: a zero as merger is lack of keys, not unused privilege. "
    "Non-maintainer 'merge rate' is author-success (a key holder merged their PR). "
    "Reviewer/ACK is not merge authority. Roster membership is not the same set as merge keys."
)


def is_maintainer_at(
    login: Optional[str],
    when: Optional[str] = None,
    timeline: Optional[Dict[str, Any]] = None,
    *,
    require_active_period: bool = False,
) -> bool:
    """Return whether ``login`` is on the maintainer roster (ever-maintainer).

    This is the identity label used by published maintainer-vs-outsider splits.
    It is **not** proof of merge keys. Use ``person_role`` / ``has_merge_keys``.

    Default: membership in the canonical/timeline set. If
    ``require_active_period`` is True and periods exist, require ``when``
    to fall inside a period.
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


_capability_cache: Optional[Dict[str, Any]] = None


def merge_capability_path() -> Path:
    return _maintainers_dir() / "merge_capability.json"


def load_merge_capability() -> Dict[str, Any]:
    """Observed merge-key holders vs roster vs cannot-merge."""
    global _capability_cache
    if _capability_cache is not None:
        return _capability_cache
    path = merge_capability_path()
    if not path.exists():
        _capability_cache = {
            "pin": PERSON_ROLE_PIN,
            "observed_mergers": {},
            "merge_key_holders": [],
            "roster_without_keys": [],
            "historical_keys_not_on_roster": [],
        }
        return _capability_cache
    _capability_cache = json.loads(path.read_text(encoding="utf-8"))
    return _capability_cache


def load_observed_merger_set() -> Set[str]:
    data = load_merge_capability()
    holders = data.get("merge_key_holders") or []
    if holders:
        return {str(x).strip().lower() for x in holders if x}
    observed = data.get("observed_mergers") or {}
    return {str(k).strip().lower() for k, n in observed.items() if n}


def has_merge_keys(login: Optional[str]) -> bool:
    """True only if this login appears as GitHub ``merged_by`` in the dump."""
    key = normalize_login(login)
    return bool(key) and key in load_observed_merger_set()


def person_role(login: Optional[str]) -> str:
    """Classify a GitHub login into merge_keys / roster_without_keys / cannot_merge."""
    key = normalize_login(login)
    if not key:
        return ROLE_CANNOT_MERGE
    if has_merge_keys(key):
        return ROLE_MERGE_KEYS
    if key in load_maintainer_login_set():
        return ROLE_ROSTER_WITHOUT_KEYS
    return ROLE_CANNOT_MERGE


def cannot_merge(login: Optional[str]) -> bool:
    """True for people who have not merged because they cannot (no observed keys)."""
    return person_role(login) == ROLE_CANNOT_MERGE


def write_merge_capability(
    counts: Dict[str, int],
    generated_from: str = "",
) -> Dict[str, Any]:
    """Write ``merge_capability.json`` from login → merge-count."""
    global _capability_cache
    roster = load_maintainer_login_set()
    holders = sorted(k for k, n in counts.items() if n)
    roster_without = sorted(roster - set(holders))
    historical = sorted(set(holders) - roster)
    payload = {
        "generated_from": generated_from,
        "pin": PERSON_ROLE_PIN,
        "roles": {
            ROLE_MERGE_KEYS: (
                "Login appears as GitHub merged_by. Technical ability to land "
                "code on bitcoin/bitcoin. The only people who can merge."
            ),
            ROLE_ROSTER_WITHOUT_KEYS: (
                "On the canonical maintainer roster but never appears as "
                "merged_by in this dump. Do not cite as unused privilege."
            ),
            ROLE_CANNOT_MERGE: (
                "Not in observed merged_by. They have not merged because they "
                "cannot. Reviewer/author/commenter status does not grant keys."
            ),
        },
        "observed_mergers": dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))),
        "merge_key_holders": holders,
        "roster_without_keys": roster_without,
        "historical_keys_not_on_roster": historical,
        "counts": {
            "unique_mergers": len(holders),
            "roster_logins": len(roster),
            "roster_with_keys": len(roster & set(holders)),
            "roster_without_keys": len(roster_without),
            "historical_keys_not_on_roster": len(historical),
        },
    }
    out = merge_capability_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    _capability_cache = payload
    return payload


def rebuild_merge_capability(prs_file: Optional[Path] = None) -> Dict[str, Any]:
    """Scan PR JSONL ``merged_by`` and write ``merge_capability.json``."""
    from collections import Counter

    path = prs_file
    if path is None:
        for candidate in (
            get_data_dir() / "processed" / "cleaned_prs.jsonl",
            get_data_dir() / "processed" / "enriched_prs.jsonl",
            get_data_dir() / "github" / "prs_raw.jsonl",
        ):
            if candidate.exists():
                path = candidate
                break
    if path is None or not path.exists():
        raise FileNotFoundError("No PR JSONL found to count merged_by")

    aliases = load_canonical_maintainers().get("aliases") or {}
    counts: Counter[str] = Counter()
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                pr = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not pr.get("merged"):
                continue
            merged_by = pr.get("merged_by")
            if isinstance(merged_by, dict):
                merged_by = merged_by.get("login")
            key = normalize_login(merged_by, aliases)
            if key:
                counts[key] += 1
    return write_merge_capability(dict(counts), generated_from=str(path))
