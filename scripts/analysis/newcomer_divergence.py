#!/usr/bin/env python3
"""Newcomer-versus-incumbent merge slope on the comparison repositories.

The estimator is the pass-2 linear probability model. It was specified after
the pass 6 results were known, so it is not in the preregistration file and
it is not in the Benjamini-Hochberg family.

Newcomer means this pull request is within 12 months of the author's first
pull request. Incumbent means the author's first pull request was at least
3 years earlier. Authors in between are in neither series. A year is
right-censored when more than 20 percent of its pull requests are still open.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from scripts.analysis.gap_closure_test import MIN_REPO_YEARS, spearman_with_ci  # noqa: E402
from scripts.analysis.rsd_ingroup_test import (  # noqa: E402
    DAY,
    _actor,
    _weighted_slope,
    _years_of,
    is_bot_login,
    load_identity,
    load_prs,
    parse_ts,
    resolve_pr_path,
)
from src.utils.findings_io import save_analysis_json  # noqa: E402
from src.utils.paths import get_data_dir, get_findings_dir  # noqa: E402

SEED = 7
N_BOOT = 1000
PUBLISHED_CORE_INTERACTION = -0.036617537534312336
def _year_phrase(count: int) -> str:
    return f"{count} year" if count == 1 else f"{count} years"


MIN_SLOPE_YEARS = 3

DIVERGENCE_RULE = (
    "A repository shows the divergence when the newcomer-by-year interaction on decided merge rate "
    "is negative and its interval excludes zero. "
    "A slope needs 3 years. If either group has fewer than 3 years, the interaction is DATA UNAVAILABLE "
    "and the repository is left out of the classification. "
    "CORE-SPECIFIC when Core's interval excludes zero on the negative side and no seven-year comparison "
    "repository has an interval that excludes zero on the negative side. "
    "AMBIENT when Core's interval excludes zero on the negative side, at least half of those repositories "
    "have a negative point, and at least one of those intervals excludes zero on the negative side. "
    "UNDETERMINED otherwise. "
    "The seven-year minimum is the one already used for the cross-repository table. "
    "This test was specified after the pass 6 results were known. It is not in pass6_preregistration.json "
    "and it is not in the Benjamini-Hochberg family."
)


def score_frame(
    created: np.ndarray,
    outcome: np.ndarray,
    authors: Sequence[str],
    rng: np.random.Generator,
    n_boot: int,
) -> Dict[str, Any]:
    """Pass-2 merge interaction and the two group slopes. outcome is 1, 0, or -1 for open."""
    n = created.size
    if n == 0:
        return {"status": "DATA UNAVAILABLE", "reason": "no pull requests"}
    years = _years_of(created)
    by_author: Dict[str, List[int]] = defaultdict(list)
    for i, author in enumerate(authors):
        by_author[author].append(i)
    first = np.empty(n, dtype=float)
    for idxs in by_author.values():
        earliest = min(float(created[i]) for i in idxs)
        for i in idxs:
            first[i] = earliest
    age_days = (created - first) / DAY
    newcomer = age_days <= 365.25
    incumbent = age_days >= (3 * 365.25)
    merge = np.full(n, np.nan)
    merge[outcome == 1] = 1.0
    merge[outcome == 0] = 0.0
    censored = set()
    for year in range(2010, 2027):
        m = years == year
        if int(m.sum()) == 0:
            continue
        if float((outcome[m] < 0).mean()) > 0.20:
            censored.add(year)

    def yearly(mask_g: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        xs, ys, ws = [], [], []
        for year in range(2010, 2027):
            if year in censored:
                continue
            mm = (years == year) & mask_g & np.isfinite(merge)
            count = int(mm.sum())
            if count < 20:
                continue
            xs.append(year)
            ys.append(float(merge[mm].mean()))
            ws.append(count)
        return np.asarray(xs, float), np.asarray(ys, float), np.asarray(ws, float)

    def slope(mask_g: np.ndarray) -> Dict[str, Any]:
        xa, ya, wa = yearly(mask_g)
        point = _weighted_slope(xa, ya, wa)
        draws = []
        if xa.size >= 3:
            for _ in range(n_boot):
                take = rng.integers(0, xa.size, size=xa.size)
                draws.append(_weighted_slope(xa[take], ya[take], wa[take]))
        clean = np.asarray([d for d in draws if d is not None and np.isfinite(d)], dtype=float)
        ci = None
        if clean.size:
            lo, hi = np.quantile(clean, [0.025, 0.975])
            ci = [float(lo), float(hi)]
        return {"estimate": point, "ci95": ci, "n_years": int(xa.size)}

    both = newcomer | incumbent
    keep = both & np.isfinite(merge) & np.array([int(y) not in censored for y in years])
    if int(keep.sum()) < 50 or np.unique(newcomer[keep]).size < 2:
        interaction = {"status": "DATA UNAVAILABLE", "reason": "fewer than 50 newcomer or incumbent decided pull requests, or only one group", "estimate": None, "ci95": None, "n": int(keep.sum())}
    else:
        y = merge[keep]
        new = newcomer[keep].astype(float)
        yr = years[keep].astype(float) - 2010.0
        x_full = np.column_stack([np.ones(y.size), new, yr, new * yr])

        def coef(idx: np.ndarray) -> Optional[float]:
            if np.unique(new[idx]).size < 2:
                return None
            fitted, *_rest = np.linalg.lstsq(x_full[idx], y[idx], rcond=None)
            return float(fitted[3])

        point = coef(np.arange(y.size))
        draws = [coef(rng.integers(0, y.size, size=y.size)) for _ in range(n_boot)]
        clean = np.asarray([d for d in draws if d is not None and np.isfinite(d)], dtype=float)
        ci = None
        if clean.size:
            lo, hi = np.quantile(clean, [0.025, 0.975])
            ci = [float(lo), float(hi)]
        interaction = {"status": "ok", "estimate": point, "ci95": ci, "n": int(y.size)}
    return {
        "status": "ok",
        "n_prs": int(n),
        "n_authors": len(by_author),
        "years_right_censored": sorted(censored),
        "interaction": interaction,
        "newcomer_slope": slope(newcomer),
        "incumbent_slope": slope(incumbent),
    }


def collapse_logins(pairs: Sequence[Tuple[str, Optional[int]]]) -> Dict[str, Any]:
    """Map each login onto a numeric GitHub user id when one is known."""
    names_for: Dict[int, set] = defaultdict(set)
    for login, uid in pairs:
        if not login or uid is None:
            continue
        names_for[int(uid)].add(str(login))
    mapping: Dict[str, str] = {}
    people = 0
    extras = 0
    for uid, names in names_for.items():
        if len(names) > 1:
            people += 1
            extras += len(names) - 1
        for name in names:
            mapping[name] = f"id:{uid}"
    return {
        "login_to_key": mapping,
        "people_with_multiple_logins": people,
        "logins_collapsed": extras,
    }


def _side(block: Dict[str, Any], side: str) -> bool:
    ci = block.get("ci95")
    estimate = block.get("estimate")
    if not isinstance(ci, (list, tuple)) or len(ci) < 2 or estimate is None:
        return False
    if side == "below":
        return ci[1] < 0 and estimate < 0
    if side == "above":
        return ci[0] > 0 and estimate > 0
    return ci[0] <= 0 <= ci[1]


def classify_driver(newcomer: Dict[str, Any], incumbent: Dict[str, Any]) -> str:
    """Which slope carries the interaction. The order is the pass 7 rule."""
    new_below = _side(newcomer, "below")
    old_below = _side(incumbent, "below")
    old_above = _side(incumbent, "above")
    if new_below and old_above:
        return "BOTH"
    if old_below:
        return "INCUMBENT DECLINE"
    if new_below and (_side(incumbent, "covers") or old_above):
        return "NEWCOMER DECLINE"
    if old_above and _side(newcomer, "covers"):
        return "INCUMBENT GAIN"
    return "UNRESOLVED"


def gate_interaction(
    interaction: Dict[str, Any],
    newcomer_slope: Dict[str, Any],
    incumbent_slope: Dict[str, Any],
) -> Dict[str, Any]:
    """Drop an interaction when either slope has fewer than MIN_SLOPE_YEARS years."""
    new_years = int((newcomer_slope or {}).get("n_years") or 0)
    old_years = int((incumbent_slope or {}).get("n_years") or 0)
    estimation = (
        "The interaction is the pass 2 linear probability model on decided newcomer and incumbent rows. "
        f"The newcomer slope uses {_year_phrase(new_years)} and the incumbent slope uses {_year_phrase(old_years)}."
    )
    if (
        new_years >= MIN_SLOPE_YEARS
        and old_years >= MIN_SLOPE_YEARS
        and interaction.get("estimate") is not None
    ):
        kept = dict(interaction)
        kept["slope_gate"] = "kept"
        kept["estimation"] = estimation + " Both slopes meet the 3-year minimum, so the interaction is used."
        return kept
    return {
        "status": "DATA UNAVAILABLE",
        "reason": estimation + f" A slope needs {MIN_SLOPE_YEARS} years, so the interaction is not used.",
        "estimate": None,
        "ci95": None,
        "n": interaction.get("n"),
        "withheld_estimate": interaction.get("estimate"),
        "slope_gate": "withheld",
        "estimation": estimation + f" A slope needs {MIN_SLOPE_YEARS} years, so the interaction is not used.",
    }


def _negative_count(rows: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    negative = 0
    for row in rows:
        estimate = (row.get("interaction") or {}).get("estimate")
        if estimate is None:
            estimate = (row.get("interaction") or {}).get("withheld_estimate")
        if estimate is not None and estimate < 0:
            negative += 1
    return {"negative": negative, "eligible": len(rows)}
    ci = block.get("ci95")
    est = block.get("estimate")
    return bool(ci and est is not None and ci[1] < 0 and est < 0)


def _excludes_negative(block: Dict[str, Any]) -> bool:
    ci = block.get("ci95")
    est = block.get("estimate")
    return bool(ci and est is not None and ci[1] < 0 and est < 0)


def classify(core: Dict[str, Any], eligible: List[Dict[str, Any]]) -> str:
    """DIVERGENCE_RULE. eligible rows are the seven-year comparison repositories."""
    core_block = core.get("interaction") or {}
    if not _excludes_negative(core_block):
        return "UNDETERMINED"
    signed = []
    excluding = []
    for row in eligible:
        block = row.get("interaction") or {}
        est = block.get("estimate")
        if est is None:
            continue
        signed.append(est < 0)
        excluding.append(_excludes_negative(block))
    if not signed:
        return "UNDETERMINED"
    if any(excluding):
        if sum(signed) >= (len(signed) / 2):
            return "AMBIENT"
        return "UNDETERMINED"
    return "CORE-SPECIFIC"


def _frame_from_rows(rows: List[Tuple[str, float, int]]) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    authors = [a for a, _t, _o in rows]
    created = np.asarray([t for _a, t, _o in rows], dtype=float)
    outcome = np.asarray([o for _a, _t, o in rows], dtype=np.int8)
    return created, outcome, authors


def load_core_rows() -> List[Tuple[str, float, int]]:
    data_dir = get_data_dir()
    path, _source = resolve_pr_path(data_dir)
    prs = load_prs(path, load_identity())
    rows = []
    for author, ts, code in zip(prs["authors"], prs["created"].tolist(), prs["outcome"].tolist()):
        rows.append((str(author), float(ts), int(code)))
    return rows


def load_repo_rows(path: Path, id_map: Optional[Dict[int, Optional[int]]] = None) -> Tuple[List[Tuple[str, float, int]], Dict[str, Any]]:
    id_map = id_map or {}
    rows = []
    pairs: List[Tuple[str, Optional[int]]] = []
    missing_ids = 0
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip():
                continue
            pr = json.loads(line)
            author = pr.get("author")
            if not author or is_bot_login(str(author)):
                continue
            ts = parse_ts(pr.get("created_at"))
            if ts is None:
                continue
            state = str(pr.get("state") or "").lower()
            if pr.get("merged"):
                code = 1
            elif state == "open":
                code = -1
            else:
                code = 0
            uid = id_map.get(pr.get("number")) if isinstance(pr.get("number"), int) else None
            if not isinstance(uid, int):
                missing_ids += 1
                uid = None
            pairs.append((str(author), uid))
            rows.append((str(author), float(ts), code))
    collapsed = collapse_logins(pairs)
    collapsed["prs_without_author_id"] = missing_ids
    if not id_map:
        collapsed["identity_status"] = "DATA UNAVAILABLE"
        collapsed["reason"] = "author_ids.jsonl is missing, so logins were not merged"
        return rows, collapsed
    collapsed["identity_status"] = "ok"
    keyed = []
    for login, ts, code in rows:
        keyed.append((collapsed["login_to_key"].get(login, login), ts, code))
    return keyed, collapsed


def _size_residuals() -> Dict[str, float]:
    path = get_findings_dir() / "data" / "size_adjusted_health.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text())
    sample = ((payload.get("samples") or {}).get("all_repositories") or {}).get("repositories") or []
    found = {}
    for row in sample:
        if row.get("repo") is not None and row.get("residual") is not None:
            found[row["repo"]] = float(row["residual"])
    return found


def _author_ids(path: Path) -> Dict[int, Optional[int]]:
    found: Dict[int, Optional[int]] = {}
    if not path.exists():
        return found
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            number = row.get("number")
            if isinstance(number, int):
                uid = row.get("author_id")
                found[number] = int(uid) if isinstance(uid, int) else None
    return found


def _years_span(created: np.ndarray) -> int:
    if created.size == 0:
        return 0
    years = {datetime.fromtimestamp(float(t), tz=timezone.utc).year for t in created}
    return len(years)


def analyze(n_boot: int = N_BOOT, seed: int = SEED) -> Dict[str, Any]:
    core_rows = load_core_rows()
    core = score_frame(*_frame_from_rows(core_rows), np.random.default_rng(seed), n_boot)
    core_ungated = core.get("interaction") or {}
    core["interaction_ungated"] = core_ungated
    core["interaction"] = gate_interaction(core_ungated, core.get("newcomer_slope") or {}, core.get("incumbent_slope") or {})
    core["driver"] = classify_driver(core.get("newcomer_slope") or {}, core.get("incumbent_slope") or {})
    published_point = core_ungated.get("estimate")
    reproduces = published_point is not None and abs(float(published_point) - PUBLISHED_CORE_INTERACTION) < 1e-9
    repos = []
    data_dir = get_data_dir() / "github" / "repos"
    config = json.loads((project_root / "scripts" / "data_collection" / "comparison_repos.json").read_text())
    for row in config.get("repos") or []:
        slug = row["slug"]
        owner, repo = slug.split("/", 1)
        path = data_dir / owner / repo / "prs.jsonl"
        if not path.exists():
            repos.append({"slug": slug, "role": row.get("role"), "status": "DATA UNAVAILABLE", "reason": "prs.jsonl is missing", "eligible": False})
            continue
        loaded, identity = load_repo_rows(path, _author_ids(data_dir / owner / repo / "author_ids.jsonl"))
        created, outcome, authors = _frame_from_rows(loaded)
        scored = score_frame(created, outcome, authors, np.random.default_rng(seed), n_boot)
        ungated = scored.get("interaction") or {}
        gated = gate_interaction(ungated, scored.get("newcomer_slope") or {}, scored.get("incumbent_slope") or {})
        scored["interaction_ungated"] = ungated
        scored["interaction"] = gated
        scored["driver"] = classify_driver(scored.get("newcomer_slope") or {}, scored.get("incumbent_slope") or {})
        n_years = _years_span(created)
        before_ok = n_years >= MIN_REPO_YEARS and ungated.get("estimate") is not None
        after_ok = n_years >= MIN_REPO_YEARS and gated.get("estimate") is not None
        scored.update({
            "slug": slug,
            "role": row.get("role"),
            "shared_maintainers": bool(row.get("shared_maintainers")),
            "n_years": n_years,
            "eligible_before_slope_gate": before_ok,
            "eligible": after_ok,
            "identity": {key: value for key, value in identity.items() if key != "login_to_key"},
        })
        repos.append(scored)
    before_rows = [row for row in repos if row.get("eligible_before_slope_gate")]
    before_count = _negative_count([
        {"interaction": row.get("interaction_ungated") or {}} for row in before_rows
    ])
    eligible = [row for row in repos if row.get("eligible")]
    after_count = _negative_count(eligible)
    classification = classify(core, eligible) if reproduces else "UNDETERMINED"
    without_shared = [row for row in eligible if not row.get("shared_maintainers")]
    sensitivity = classify(core, without_shared) if reproduces else "UNDETERMINED"

    def _named(rows: List[Dict[str, Any]], negative: bool) -> List[str]:
        names = []
        for row in rows:
            block = row.get("interaction") or {}
            est = block.get("estimate")
            ci = block.get("ci95")
            if est is None or not ci:
                continue
            if negative and ci[1] < 0 and est < 0:
                names.append(row["slug"])
            if not negative and ci[0] > 0 and est > 0:
                names.append(row["slug"])
        return names

    negative_names = _named(eligible, True)
    positive_names = _named(eligible, False)
    drivers: Dict[str, int] = defaultdict(int)
    for row in eligible:
        drivers[row.get("driver") or "UNRESOLVED"] += 1
    driver_sentence = (
        "Among eligible repositories, the interaction is NEWCOMER DECLINE in "
        f"{drivers.get('NEWCOMER DECLINE', 0)}, INCUMBENT GAIN in {drivers.get('INCUMBENT GAIN', 0)}, "
        f"BOTH in {drivers.get('BOTH', 0)}, INCUMBENT DECLINE in {drivers.get('INCUMBENT DECLINE', 0)}, "
        f"and UNRESOLVED in {drivers.get('UNRESOLVED', 0)}."
    )
    logins_collapsed = sum(int((row.get("identity") or {}).get("logins_collapsed") or 0) for row in repos)
    people_merged = sum(int((row.get("identity") or {}).get("people_with_multiple_logins") or 0) for row in repos)
    identity_missing = [
        row["slug"] for row in repos
        if (row.get("identity") or {}).get("identity_status") == "DATA UNAVAILABLE"
    ]
    residuals = _size_residuals()
    link_x = []
    link_y = []
    core_est = (core.get("interaction") or {}).get("estimate")
    if core_est is not None and "bitcoin/bitcoin" in residuals:
        link_x.append(float(core_est))
        link_y.append(residuals["bitcoin/bitcoin"])
    for row in eligible:
        estimate = (row.get("interaction") or {}).get("estimate")
        residual = residuals.get(row.get("slug"))
        if estimate is None or residual is None:
            continue
        link_x.append(float(estimate))
        link_y.append(float(residual))
    health_link = spearman_with_ci(
        np.asarray(link_x, dtype=float),
        np.asarray(link_y, dtype=float),
        np.random.default_rng(seed),
        n_boot,
    )
    health_link["exploratory"] = True
    health_link["in_bh_family"] = False
    health_link["label"] = "Spearman correlation of the newcomer interaction with the size-adjusted residual. Exploratory. Not in the family."
    counterexample = (
        "A positive interaction is not evidence that a repository's practice serves newcomers. "
        "The driver column is the description that replaces that reading."
    )
    payload = {
        "version": "7.0",
        "status": "ok" if reproduces else "ESTIMATOR_MISMATCH",
        "specified_after_pass6": True,
        "in_bh_family": False,
        "rule": DIVERGENCE_RULE,
        "core_reproduces_published_point": reproduces,
        "published_core_interaction": PUBLISHED_CORE_INTERACTION,
        "published_core_note": (
            "The published pass-2 interval remains the Core headline. "
            "The interval in this file is a fresh seed-7 bootstrap of the same point, so it can be compared with the other repositories."
        ),
        "classification": classification,
        "classification_without_shared_maintainers": sensitivity,
        "negative_points_before_slope_gate": before_count,
        "negative_points_after_slope_gate": after_count,
        "negative_excluding_zero": negative_names,
        "positive_excluding_zero": positive_names,
        "driver_counts": dict(drivers),
        "driver_sentence": driver_sentence,
        "logins_collapsed": logins_collapsed,
        "people_with_multiple_logins": people_merged,
        "identity_unavailable": identity_missing,
        "health_link": health_link,
        "low_power": True,
        "low_power_reason": "Fewer than 20 repositories. Each repository's own interval can still be informative.",
        "core": core,
        "repositories": repos,
        "n_eligible": len(eligible),
        "what_this_cannot_prove": [
            "A Core-specific divergence is not proof that implementation diversity would remove it.",
            "An ambient divergence is not proof that every reference implementation must treat newcomers this way.",
            "The cross-repository count is below 20, so the classification is LOW POWER.",
            counterexample,
            "This test was chosen after pass 6 was known. It is a follow-up, not a preregistered result.",
        ],
    }
    save_analysis_json("newcomer_divergence.json", payload)
    return payload


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Newcomer merge divergence on comparison repositories")
    parser.add_argument("--bootstrap", type=int, default=N_BOOT)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    payload = analyze(args.bootstrap, args.seed)
    core = (payload.get("core") or {}).get("interaction") or {}
    print(json.dumps({
        "status": payload.get("status"),
        "classification": payload.get("classification"),
        "core": core.get("estimate"),
        "reproduces": payload.get("core_reproduces_published_point"),
        "eligible": payload.get("n_eligible"),
    }, indent=2))
    return 0 if payload.get("core_reproduces_published_point") else 2


if __name__ == "__main__":
    raise SystemExit(main())
