#!/usr/bin/env python3
"""Blinded audit sample of first pull requests.

The committed csv has an opaque id, the repository, the pull request number,
and the entry year. The key that maps an id to a person is gitignored.
This script does not score the patches.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

import numpy as np

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from scripts.analysis.first_year_signal_test import (  # noqa: E402
    CONTENT_KEYS,
    N_BOOT,
    SEED,
    g1_top_quartile_rows,
    load_analysis_frame,
)
from src.utils.paths import get_findings_dir  # noqa: E402

REPO = "bitcoin/bitcoin"
SAMPLE_N = 100


def stratified_sample(people: Sequence[Dict[str, Any]], n: int, rng: np.random.Generator) -> List[Dict[str, Any]]:
    """Without replacement, counts proportional to entry year. A year cannot give more people than it has."""
    by_year: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for person in people:
        by_year[int(person["year"])].append(person)
    if not by_year or n <= 0:
        return []
    n = min(n, sum(len(rows) for rows in by_year.values()))
    years = sorted(by_year)
    raw = {year: n * len(by_year[year]) / sum(len(rows) for rows in by_year.values()) for year in years}
    alloc = {year: min(len(by_year[year]), int(raw[year])) for year in years}
    left = n - sum(alloc.values())
    remainder = sorted(years, key=lambda year: (raw[year] - alloc[year], -year), reverse=True)
    while left > 0:
        moved = False
        for year in remainder:
            if alloc[year] < len(by_year[year]):
                alloc[year] += 1
                left -= 1
                moved = True
                if left == 0:
                    break
        if not moved:
            break
    chosen: List[Dict[str, Any]] = []
    for year in years:
        pool = list(by_year[year])
        order = rng.permutation(len(pool))
        chosen.extend(pool[int(i)] for i in order[: alloc[year]])
    return chosen


def redact_text(text: str, names: Iterable[str]) -> str:
    """Remove person tokens from a description. Patch hunks are not passed through this for outcome words."""
    cleaned = text or ""
    for name in sorted({str(name) for name in names if name and len(str(name)) >= 3}, key=len, reverse=True):
        cleaned = re.sub(re.escape(name), "[person]", cleaned, flags=re.I)
    return cleaned


def coder_bundle(description: str, files: Sequence[Dict[str, Any]], names: Iterable[str]) -> Dict[str, Any]:
    """Patch plus description. No author, reviewer, merged flag, or login."""
    safe_files = []
    for item in files:
        safe_files.append({
            "filename": item.get("filename") or "",
            "patch": redact_text(item.get("patch") or "", names),
        })
    return {
        "description": redact_text(description, names),
        "files": safe_files,
    }


def _first_pr(prs, authors: Sequence[str]) -> Dict[str, int]:
    first: Dict[str, tuple] = {}
    for i, author in enumerate(prs["author"].tolist()):
        if author not in authors and author not in first:
            continue
        created = float(prs["created"][i])
        number = int(prs["number"][i])
        current = first.get(str(author))
        if current is None or created < current[0]:
            first[str(author)] = (created, number)
    return {author: pair[1] for author, pair in first.items()}


def draw_sample(seed: int = SEED) -> Dict[str, Any]:
    missing: List[Dict[str, str]] = []
    frame = load_analysis_frame(missing)
    picked = g1_top_quartile_rows(frame["train_rows"], CONTENT_KEYS)
    fn_rows = picked.get("rows") or []
    g1_rows = [row for row in frame["train_rows"] if row["group"] == 1]
    wanted = {row["author"] for row in fn_rows} | {row["author"] for row in g1_rows}
    numbers = _first_pr(frame["prs"], list(wanted))
    rng = np.random.default_rng(seed)
    fn_draw = stratified_sample(fn_rows, SAMPLE_N, rng)
    g1_draw = stratified_sample(g1_rows, SAMPLE_N, rng)
    shortfall = []
    if len(g1_rows) < SAMPLE_N:
        shortfall.append({
            "metric": "g1_audit_sample",
            "status": "DATA UNAVAILABLE",
            "reason": (
                f"G1 has {len(g1_rows)} people, so a sample of {SAMPLE_N} first pull requests "
                "cannot be drawn without replacement. The arm uses every G1 first pull request."
            ),
        })
    records = []
    for group, draw in (("false_negative", fn_draw), ("g1", g1_draw)):
        for person in draw:
            records.append({
                "group": group,
                "author": person["author"],
                "year": int(person["year"]),
                "pr": numbers.get(person["author"]),
                "repo": REPO,
            })
    rng.shuffle(records)
    for i, row in enumerate(records, start=1):
        row["opaque_id"] = f"S{i:03d}"
    return {"records": records, "shortfall": shortfall, "n_false_negative": len(fn_rows), "n_g1": len(g1_rows)}


def write_sample(payload: Dict[str, Any], findings: Path) -> None:
    findings.mkdir(parents=True, exist_ok=True)
    public = findings / "audit_sample.csv"
    key = findings / "audit_sample_key.csv"
    with public.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["opaque_id", "repo", "pr_number", "year"])
        writer.writeheader()
        for row in payload["records"]:
            writer.writerow({
                "opaque_id": row["opaque_id"],
                "repo": row["repo"],
                "pr_number": row["pr"],
                "year": row["year"],
            })
    with key.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["opaque_id", "group", "author", "pr_number", "year"])
        writer.writeheader()
        for row in payload["records"]:
            writer.writerow({
                "opaque_id": row["opaque_id"],
                "group": row["group"],
                "author": row["author"],
                "pr_number": row["pr"],
                "year": row["year"],
            })


def _github_json(path: str) -> Any:
    env = os.environ.copy()
    # A stale token in the environment overrides gh's own login and returns 401.
    env.pop("GITHUB_TOKEN", None)
    env.pop("GH_TOKEN", None)
    proc = subprocess.run(["gh", "api", path], capture_output=True, text=True, check=False, env=env)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip()[:300] or f"gh api failed for {path}")
    return json.loads(proc.stdout)


def fetch_bundle(repo: str, number: int, names: Iterable[str]) -> Dict[str, Any]:
    owner, name = repo.split("/", 1)
    pr = _github_json(f"repos/{owner}/{name}/pulls/{number}")
    files = _github_json(f"repos/{owner}/{name}/pulls/{number}/files?per_page=100")
    description = f"{pr.get('title') or ''}\n\n{pr.get('body') or ''}"
    extra = set(names)
    user = (pr.get("user") or {}).get("login")
    if user:
        extra.add(user)
    return coder_bundle(description, files if isinstance(files, list) else [], extra)


def score_coded(coded_path: Path, key_path: Path) -> Dict[str, Any]:
    """G1 minus false-negative mean on each rubric item, once a coded csv exists."""
    if not coded_path.exists() or not key_path.exists():
        return {
            "status": "DATA UNAVAILABLE",
            "reason": "The coded csv or the gitignored key is missing, so group differences cannot be scored.",
        }
    key = {row["opaque_id"]: row for row in csv.DictReader(key_path.open())}
    coded = list(csv.DictReader(coded_path.open()))
    items = ["correctness", "scope_discipline", "test_coverage", "clarity"]
    coders = {row.get("coder") for row in coded if row.get("coder")}
    out: Dict[str, Any] = {"status": "ok", "n_coders": len(coders), "items": {}}
    for item in items:
        groups: Dict[str, List[float]] = defaultdict(list)
        for row in coded:
            ident = key.get(row.get("opaque_id") or "")
            if ident is None or row.get(item) in (None, ""):
                continue
            groups[ident["group"]].append(float(row[item]))
        g1 = np.asarray(groups.get("g1") or [], dtype=float)
        fn = np.asarray(groups.get("false_negative") or [], dtype=float)
        if g1.size == 0 or fn.size == 0:
            out["items"][item] = {"status": "DATA UNAVAILABLE", "reason": "one arm has no scores"}
            continue
        diff = float(g1.mean() - fn.mean())
        rng = np.random.default_rng(SEED)
        draws = np.empty(N_BOOT)
        for i in range(N_BOOT):
            draws[i] = float(g1[rng.integers(0, g1.size, g1.size)].mean() - fn[rng.integers(0, fn.size, fn.size)].mean())
        lo, hi = np.quantile(draws, [0.025, 0.975])
        out["items"][item] = {"difference_g1_minus_fn": diff, "ci95": [float(lo), float(hi)], "n_g1": int(g1.size), "n_fn": int(fn.size)}
    if len(coders) >= 2:
        out["inter_rater"] = "two coders are present; pair their scores on opaque_id before citing agreement"
    else:
        out["inter_rater"] = "DATA UNAVAILABLE. One coder, so agreement is not computed."
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--fetch", action="store_true")
    args = parser.parse_args()
    findings = get_findings_dir() / "data"
    payload = draw_sample(args.seed)
    write_sample(payload, findings)
    note = {
        "n_false_negative_population": payload["n_false_negative"],
        "n_g1_population": payload["n_g1"],
        "n_drawn": len(payload["records"]),
        "shortfall": payload["shortfall"],
        "bundle_source": (
            "GitHub pull request files. analyze_pr in this session returned a review scaffold "
            "with names and a judgment, not a patch pack, so it is not the coder bundle."
        ),
    }
    (findings / "audit_sample_note.json").write_text(json.dumps(note, indent=2), encoding="utf-8")
    print(json.dumps(note))
    if args.fetch:
        bundle_dir = findings / "audit_bundles"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        key_rows = list(csv.DictReader((findings / "audit_sample_key.csv").open()))
        public = {row["opaque_id"]: row for row in csv.DictReader((findings / "audit_sample.csv").open())}
        for row in key_rows:
            dest = bundle_dir / f"{row['opaque_id']}.json"
            if dest.exists():
                continue
            repo = public[row["opaque_id"]]["repo"]
            bundle = fetch_bundle(repo, int(row["pr_number"]), [row["author"]])
            dest.write_text(json.dumps(bundle), encoding="utf-8")
            print(row["opaque_id"], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
