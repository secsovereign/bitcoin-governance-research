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

from scripts.analysis.gap_closure_test import MIN_REPO_YEARS  # noqa: E402
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

DIVERGENCE_RULE = (
    "A repository shows the divergence when the newcomer-by-year interaction on decided merge rate "
    "is negative and its interval excludes zero. "
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


def load_repo_rows(path: Path) -> List[Tuple[str, float, int]]:
    rows = []
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
            rows.append((str(author), float(ts), code))
    return rows


def _years_span(created: np.ndarray) -> int:
    if created.size == 0:
        return 0
    years = {datetime.fromtimestamp(float(t), tz=timezone.utc).year for t in created}
    return len(years)


def analyze(n_boot: int = N_BOOT, seed: int = SEED) -> Dict[str, Any]:
    core_rows = load_core_rows()
    core = score_frame(*_frame_from_rows(core_rows), np.random.default_rng(seed), n_boot)
    published_point = (core.get("interaction") or {}).get("estimate")
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
        loaded = load_repo_rows(path)
        created, outcome, authors = _frame_from_rows(loaded)
        scored = score_frame(created, outcome, authors, np.random.default_rng(seed), n_boot)
        n_years = _years_span(created)
        interaction_ok = (scored.get("interaction") or {}).get("estimate") is not None
        scored.update({
            "slug": slug,
            "role": row.get("role"),
            "shared_maintainers": bool(row.get("shared_maintainers")),
            "n_years": n_years,
            "eligible": n_years >= MIN_REPO_YEARS and interaction_ok,
        })
        repos.append(scored)
    eligible = [row for row in repos if row.get("eligible")]
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
    counterexample = (
        "Repositories whose interval excludes zero on the positive side are "
        + ", ".join(positive_names)
        + ". The pattern is not universal in this set."
        if positive_names
        else "No eligible repository has an interval that excludes zero on the positive side."
    )
    payload = {
        "version": "6.1",
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
        "negative_excluding_zero": negative_names,
        "positive_excluding_zero": positive_names,
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
