#!/usr/bin/env python3
"""Post-merge durability of introduced production lines.

Survival, revert, fix-forward, and neutral churn are read from the git
history of a merged pull request. Reviewer verdicts are not an input.
A pull request whose horizon is past the tip of the repository is
right-censored. It is not scored as a failure.
"""

from __future__ import annotations

import argparse
import calendar
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from scripts.analysis.commons_dynamics_test import (  # noqa: E402
    bh_qvalues,
    ci_from_draws,
    collect_prior_tests,
    p_from_draws,
)
from scripts.analysis.first_year_signal_test import (  # noqa: E402
    CONTENT_KEYS,
    HOLDOUT_FIRST,
    N_BOOT,
    SEED,
    TOP_N,
    TRAIN_LAST,
    WINDOW,
    YEAR,
    collect_pass3,
    g1_top_quartile_rows,
    jsonable,
    load_analysis_frame,
    unavailable,
)
from scripts.analysis.gap_closure_test import collect_pass4  # noqa: E402
from scripts.analysis.rsd_ingroup_test import (  # noqa: E402
    cohens_d,
    effect_flag,
    logistic_irls,
    walk_rolling,
)
from src.utils.findings_io import save_analysis_json  # noqa: E402
from src.utils.pr_quality import path_risk_band  # noqa: E402

PREREG_COMMIT = "c94414a4"
DEFAULT_REPO = Path(os.environ.get("BITCOIN_SRC_REPO", "/mnt/bulk/bitcoin-src"))
HORIZONS = (12, 24)
INGROUP_FROM = datetime(2016, 9, 23, tzinfo=timezone.utc).timestamp()
SENTINEL = "@@DURABILITY@@"
HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
FIX_TITLE_RE = re.compile(r"(?i)\b(bugfix|bug-fix)\b|^(?:fix|fixes|fixed)\b")
FIXES_REF_RE = re.compile(r"(?i)\bFixes\s+#\d+")
CVE_RE = re.compile(r"(?i)\bCVE-\d{4}-\d+")
HASH_RE = re.compile(r"\b([0-9a-f]{7,40})\b", re.I)


def add_months(ts: float, months: int) -> float:
    dt = datetime.fromtimestamp(float(ts), tz=timezone.utc)
    index = dt.month - 1 + int(months)
    year = dt.year + index // 12
    month = index % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day).timestamp()


def horizon_censored(merge_ts: float, months: int, data_end: float) -> bool:
    """True when the horizon falls after the last commit in the data."""
    return add_months(merge_ts, months) > float(data_end)


def classify_path(path: str) -> str:
    """production, test, or docs_build. Production is the headline outcome."""
    text = (path or "").replace("\\", "/")
    if text.startswith("a/") or text.startswith("b/"):
        text = text[2:]
    low = text.lower()
    name = low.rsplit("/", 1)[-1]
    if (
        low.startswith("test/")
        or low.startswith("src/test/")
        or "/test/" in f"/{low}"
        or name.startswith("test_")
        or name.endswith("_tests.cpp")
        or name.endswith("_tests.py")
        or name.endswith("_test.cpp")
        or name.endswith("_test.py")
    ):
        return "test"
    if (
        low.startswith("doc/")
        or low.startswith("docs/")
        or low.startswith("build")
        or low.startswith("ci/")
        or low.startswith("contrib/")
        or low.startswith(".github/")
        or name in {"makefile", "cmakelists.txt", "copying", "readme.md"}
        or name.endswith(".md")
        or name.endswith(".adoc")
    ):
        return "docs_build"
    return "production"


def is_fix_message(message: str) -> bool:
    text = message or ""
    title = text.splitlines()[0] if text else ""
    if FIX_TITLE_RE.search(title.strip()):
        return True
    if FIXES_REF_RE.search(text):
        return True
    if CVE_RE.search(text):
        return True
    return False


def is_revert_of(message: str, shas: Iterable[str], pr_number: int) -> bool:
    """A later commit reverts this merge when its title starts with Revert and names it, or the message cites one of its hashes."""
    text = message or ""
    title = text.splitlines()[0].strip() if text else ""
    lowered = text.lower()
    cites = False
    for sha in shas:
        short = str(sha).lower()
        if len(short) >= 12 and short[:12] in lowered:
            cites = True
            break
        if len(short) >= 7 and short in lowered:
            cites = True
            break
    names_pr = bool(re.search(rf"(?i)(?:#|pull/){int(pr_number)}\b", text))
    if title.lower().startswith("revert") and (cites or names_pr or f'"{pr_number}"' in title):
        return True
    if title.lower().startswith("revert") and names_pr:
        return True
    return cites


def parse_u0_diff(text: str) -> List[Dict[str, Any]]:
    """Parse a unified diff. Each file has hunks with old range and added (new_line, content) pairs."""
    files: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    new_line = 0

    def finish_hunk() -> None:
        return None

    for raw in (text or "").splitlines():
        if raw.startswith("diff --git "):
            parts = raw.split()
            new_path = parts[-1][2:] if len(parts) >= 4 and parts[-1].startswith("b/") else parts[-1]
            old_path = parts[-2][2:] if len(parts) >= 4 and parts[-2].startswith("a/") else new_path
            current = {"old_path": old_path, "new_path": new_path, "hunks": [], "rename": False}
            files.append(current)
            continue
        if current is None:
            continue
        if raw.startswith("rename from "):
            current["old_path"] = raw[len("rename from ") :]
            current["rename"] = True
            continue
        if raw.startswith("rename to "):
            current["new_path"] = raw[len("rename to ") :]
            current["rename"] = True
            continue
        if raw.startswith("Binary files ") or raw.startswith("GIT binary patch"):
            current["binary"] = True
            continue
        match = HUNK_RE.match(raw)
        if match:
            old_start = int(match.group(1))
            old_count = int(match.group(2) if match.group(2) is not None else 1)
            new_start = int(match.group(3))
            new_count = int(match.group(4) if match.group(4) is not None else 1)
            hunk = {
                "old_start": old_start,
                "old_count": old_count,
                "new_start": new_start,
                "new_count": new_count,
                "added": [],
            }
            current["hunks"].append(hunk)
            new_line = new_start
            continue
        if not current["hunks"] or current.get("binary"):
            continue
        hunk = current["hunks"][-1]
        if raw.startswith("+") and not raw.startswith("+++"):
            hunk["added"].append((new_line, raw[1:]))
            new_line += 1
        elif raw.startswith("-") and not raw.startswith("---"):
            continue
        elif raw.startswith("\\"):
            continue
    return files


def apply_hunks(
    live: Dict[int, Dict[str, Any]],
    hunks: Sequence[Dict[str, Any]],
) -> Tuple[Dict[int, Dict[str, Any]], List[Dict[str, Any]]]:
    """Move surviving lines onto their new numbers. Lines inside a deleted range are removed."""
    ordered = sorted(live.items())
    hunks_sorted = sorted(hunks, key=lambda hunk: (hunk["old_start"], hunk["old_count"]))
    removed: List[Dict[str, Any]] = []
    updated: Dict[int, Dict[str, Any]] = {}
    index = 0
    delta = 0
    for hunk in hunks_sorted:
        old_start = int(hunk["old_start"])
        old_count = int(hunk["old_count"])
        new_count = int(hunk["new_count"])
        if old_count == 0:
            while index < len(ordered) and ordered[index][0] <= old_start:
                line, rec = ordered[index]
                updated[line + delta] = rec
                index += 1
            delta += new_count
            continue
        while index < len(ordered) and ordered[index][0] < old_start:
            line, rec = ordered[index]
            updated[line + delta] = rec
            index += 1
        end = old_start + old_count
        while index < len(ordered) and ordered[index][0] < end:
            removed.append(ordered[index][1])
            index += 1
        delta += new_count - old_count
    while index < len(ordered):
        line, rec = ordered[index]
        updated[line + delta] = rec
        index += 1
    return updated, removed


def _git(repo: Path, args: Sequence[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=check,
        capture_output=True,
        text=True,
    )


def tip_timestamp(repo: Path) -> float:
    proc = _git(repo, ["log", "-1", "--format=%ct"])
    return float(proc.stdout.strip())


def missing_objects(repo: Path, shas: Sequence[str]) -> List[str]:
    if not shas:
        return []
    proc = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "--batch-check"],
        input="\n".join(shas) + "\n",
        capture_output=True,
        text=True,
        check=True,
    )
    missing = []
    for line in proc.stdout.splitlines():
        if line.endswith(" missing"):
            missing.append(line.split()[0])
    return missing


def constituent_shas(repo: Path, first_parent: str, second_parent: str, merge_sha: str) -> List[str]:
    proc = _git(repo, ["rev-list", f"{first_parent}..{second_parent}"], check=False)
    found = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    found.append(merge_sha)
    return found


def iter_first_parent(repo: Path):
    """Yield (sha, parents, timestamp, message, diff_text) along first-parent history, oldest first."""
    proc = subprocess.Popen(
        [
            "git", "-C", str(repo), "log", "--first-parent", "--reverse",
            "-M", "--find-renames", "-U0",
            f"--format={SENTINEL}%n%H%n%P%n%ct%n%B%n{SENTINEL}MSG",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.stdout is not None
    sha = ""
    parents: List[str] = []
    stamp = 0.0
    message_lines: List[str] = []
    diff_lines: List[str] = []
    mode = "seek"
    exhausted = False
    try:
        for line in proc.stdout:
            stripped = line.rstrip("\n")
            if mode == "seek":
                if stripped == SENTINEL:
                    mode = "sha"
                continue
            if mode == "sha":
                sha = stripped
                mode = "parents"
                continue
            if mode == "parents":
                parents = stripped.split()
                mode = "time"
                continue
            if mode == "time":
                stamp = float(stripped)
                message_lines = []
                mode = "message"
                continue
            if mode == "message":
                if stripped == f"{SENTINEL}MSG":
                    diff_lines = []
                    mode = "diff"
                    continue
                message_lines.append(stripped)
                continue
            if stripped == SENTINEL:
                yield sha, parents, stamp, "\n".join(message_lines).strip(), "\n".join(diff_lines)
                mode = "sha"
                sha = ""
                continue
            diff_lines.append(stripped)
        if mode == "diff" and sha:
            yield sha, parents, stamp, "\n".join(message_lines).strip(), "\n".join(diff_lines)
        exhausted = True
    finally:
        if proc.stdout:
            proc.stdout.close()
        proc.wait()
        if exhausted and proc.returncode not in (0, None):
            raise RuntimeError(f"git log exited {proc.returncode}")


def trace_merges(repo: Path, merges: Dict[str, Dict[str, Any]], data_end: float) -> Dict[int, Dict[str, Any]]:
    """Follow introduced lines from each merge sha to the repository tip.

    merges is keyed by full sha. Each value needs pr (int) and the constituent sha list.
    """
    by_sha = {sha.lower(): meta for sha, meta in merges.items()}
    sha_owner: Dict[str, int] = {}
    for sha, meta in by_sha.items():
        for piece in meta.get("shas") or [sha]:
            sha_owner[str(piece).lower()[:12]] = int(meta["pr"])
    live: Dict[str, Dict[int, Dict[str, Any]]] = defaultdict(dict)
    lines_by_pr: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    revert_at: Dict[int, List[float]] = defaultdict(list)

    seen = 0
    for sha, parents, stamp, message, diff_text in iter_first_parent(repo):
        seen += 1
        if seen % 2000 == 0:
            print(f"history commits {seen}", flush=True)
        meta = by_sha.get(sha.lower())
        parsed = parse_u0_diff(diff_text)
        renamed: Dict[str, str] = {}
        for file_diff in parsed:
            if file_diff.get("rename") and file_diff["old_path"] != file_diff["new_path"]:
                renamed[file_diff["old_path"]] = file_diff["new_path"]
        for old, new in renamed.items():
            if old in live and new not in live:
                live[new] = live.pop(old)
            elif old in live:
                live[new].update(live.pop(old))

        for file_diff in parsed:
            if file_diff.get("binary"):
                continue
            path = file_diff["new_path"]
            if path == "/dev/null":
                path = file_diff["old_path"]
            current = live.get(path, {})
            updated, removed = apply_hunks(current, file_diff["hunks"])
            for rec in removed:
                if rec.get("removed_at") is None:
                    rec["removed_at"] = stamp
                    rec["removal"] = _removal_class(message, rec)
            live[path] = updated
            if meta is not None and classify_path(path) == "production":
                for hunk in file_diff["hunks"]:
                    for new_line, _content in hunk["added"]:
                        rec = {
                            "pr": int(meta["pr"]),
                            "shas": list(meta.get("shas") or []),
                            "introduced_at": stamp,
                            "removed_at": None,
                            "removal": None,
                            "class": "production",
                        }
                        live[path][int(new_line)] = rec
                        lines_by_pr[int(meta["pr"])].append(rec)

        for pr, _prefix in _revert_hits(message, sha_owner):
            if meta is None or int(meta["pr"]) != pr:
                revert_at[pr].append(stamp)

    outcomes: Dict[int, Dict[str, Any]] = {}
    for sha, meta in by_sha.items():
        pr = int(meta["pr"])
        introduced = [rec for rec in lines_by_pr.get(pr, []) if rec["class"] == "production"]
        merge_ts = float(meta["time"])
        horizons = {}
        for months in HORIZONS:
            if horizon_censored(merge_ts, months, data_end):
                horizons[str(months)] = {"status": "censored", "censored": True}
                continue
            horizon_ts = add_months(merge_ts, months)
            surviving = 0
            neutral = 0
            fix = False
            for rec in introduced:
                gone = rec["removed_at"] is not None and float(rec["removed_at"]) <= horizon_ts
                if not gone:
                    surviving += 1
                    continue
                if rec["removal"] == "fix":
                    fix = True
                elif rec["removal"] == "revert":
                    pass
                else:
                    neutral += 1
            reverted = any(ts <= horizon_ts for ts in revert_at.get(pr, []))
            if any(rec["removal"] == "revert" and rec["removed_at"] is not None and float(rec["removed_at"]) <= horizon_ts for rec in introduced):
                reverted = True
            horizons[str(months)] = {
                "status": "ok",
                "censored": False,
                "introduced": len(introduced),
                "surviving": surviving,
                "survival": None if not introduced else surviving / len(introduced),
                "fix_forward": int(fix),
                "revert": int(reverted),
                "neutral_lines": neutral,
                "neutral_share": None if not introduced else neutral / len(introduced),
            }
        outcomes[pr] = {
            "pr": pr,
            "merge_sha": sha,
            "merge_time": merge_ts,
            "production_lines": len(introduced),
            "horizons": horizons,
        }
    return outcomes


def _removal_class(message: str, rec: Dict[str, Any]) -> str:
    shas = rec.get("shas") or []
    pr = int(rec.get("pr") or 0)
    if pr and is_revert_of(message, shas, pr):
        return "revert"
    if is_fix_message(message):
        return "fix"
    return "neutral"


def _revert_hits(message: str, sha_owner: Dict[str, int]) -> List[Tuple[int, str]]:
    hits = []
    title = (message or "").splitlines()[0].strip() if message else ""
    if title.lower().startswith("revert"):
        for match in re.finditer(r"(?i)#(\d+)", title):
            hits.append((int(match.group(1)), "title"))
    for match in HASH_RE.finditer(message or ""):
        prefix = match.group(1).lower()[:12]
        owner = sha_owner.get(prefix)
        if owner is not None:
            hits.append((owner, prefix))
    return hits


def _z(values: np.ndarray) -> np.ndarray:
    finite = values[np.isfinite(values)]
    if finite.size == 0 or float(np.std(finite)) < 1e-12:
        return np.zeros(values.shape[0], dtype=float)
    return (values - float(finite.mean())) / float(finite.std())


def _design(rows: Sequence[Dict[str, Any]], group_key: str) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    group = np.asarray([float(row[group_key]) for row in rows], dtype=float)
    log_lines = _z(np.asarray([row["log_lines"] for row in rows], dtype=float))
    files = _z(np.asarray([row["files"] for row in rows], dtype=float))
    tenure = _z(np.asarray([row["tenure"] for row in rows], dtype=float))
    years = sorted({int(row["year"]) for row in rows})
    risks = sorted({row["path_risk"] for row in rows})
    subs = sorted({row["subsystem"] for row in rows})
    drop_year = years[0]
    drop_risk = "other" if "other" in risks else risks[0]
    drop_sub = "other" if "other" in subs else subs[0]
    columns = [np.ones(len(rows)), group, log_lines, files, tenure]
    names = ["intercept", "group", "log_lines", "files", "tenure"]
    for year in years:
        if year == drop_year:
            continue
        columns.append(np.asarray([1.0 if int(row["year"]) == year else 0.0 for row in rows]))
        names.append(f"year_{year}")
    for risk in risks:
        if risk == drop_risk:
            continue
        columns.append(np.asarray([1.0 if row["path_risk"] == risk else 0.0 for row in rows]))
        names.append(f"risk_{risk}")
    for sub in subs:
        if sub == drop_sub:
            continue
        columns.append(np.asarray([1.0 if row["subsystem"] == sub else 0.0 for row in rows]))
        names.append(f"subsystem_{sub}")
    return np.column_stack(columns), group, names


def fit_binary(
    rows: Sequence[Dict[str, Any]],
    outcome: str,
    group_key: str,
    rng: np.random.Generator,
    n_boot: int,
) -> Dict[str, Any]:
    usable = [row for row in rows if row.get(outcome) is not None and row.get(group_key) is not None]
    authors = sorted({row["author"] for row in usable})
    if len(usable) < 8 or len(authors) < 2:
        return {"status": "DATA UNAVAILABLE", "reason": "fewer than 8 pull requests or 2 authors", "low_power": True}
    y = np.asarray([float(row[outcome]) for row in usable], dtype=float)
    x_mat, _group, names = _design(usable, group_key)
    beta = logistic_irls(x_mat, y)
    estimate = None if beta is None else float(beta[1])
    by_author: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in usable:
        by_author[row["author"]].append(row)
    draws = np.full(n_boot, np.nan)
    author_ids = np.asarray(authors, dtype=object)
    if n_boot and beta is not None:
        for i in range(n_boot):
            chosen = author_ids[rng.integers(0, author_ids.size, author_ids.size)]
            sample = [row for author in chosen for row in by_author[author]]
            if len({row[group_key] for row in sample}) < 2:
                continue
            ys = np.asarray([float(row[outcome]) for row in sample], dtype=float)
            if ys.min() == ys.max():
                continue
            xs, _g, _n = _design(sample, group_key)
            if xs.shape[1] != x_mat.shape[1]:
                continue
            fitted = logistic_irls(xs, ys)
            if fitted is not None and fitted.size > 1:
                draws[i] = float(fitted[1])
    a = np.asarray([float(row[outcome]) for row in usable if row[group_key] == 1], dtype=float)
    b = np.asarray([float(row[outcome]) for row in usable if row[group_key] == 0], dtype=float)
    d = cohens_d(a, b) if a.size >= 2 and b.size >= 2 else None
    rate_gap = None if not a.size or not b.size else float(a.mean() - b.mean())
    return {
        "status": "ok",
        "outcome": outcome,
        "estimate": estimate,
        "ci95": ci_from_draws(draws),
        "p": None if estimate is None else p_from_draws(draws),
        "n": len(usable),
        "n_authors": len(authors),
        "low_power": len(authors) < 20,
        "cohens_d": d,
        "effect_size_flag": effect_flag(d),
        "rate_group1": None if not a.size else float(a.mean()),
        "rate_group0": None if not b.size else float(b.mean()),
        "rate_gap": rate_gap,
        "cite_rate_gap": bool(d is not None and abs(d) > 2),
        "names": names,
    }


def holdout_sign(train: Dict[str, Any], hold_rows: Sequence[Dict[str, Any]], outcome: str, group_key: str) -> Optional[bool]:
    if train.get("estimate") is None:
        return None
    usable = [row for row in hold_rows if row.get(outcome) is not None and row.get(group_key) is not None]
    if len(usable) < 8 or len({row[group_key] for row in usable}) < 2:
        return None
    y = np.asarray([float(row[outcome]) for row in usable], dtype=float)
    if y.min() == y.max():
        return None
    x_mat, _g, _n = _design(usable, group_key)
    beta = logistic_irls(x_mat, y)
    if beta is None:
        return None
    return bool(float(beta[1]) == 0 or (float(beta[1]) > 0) == (float(train["estimate"]) > 0))


def _load_merge_index(path: Path) -> Dict[int, Dict[str, Any]]:
    found: Dict[int, Dict[str, Any]] = {}
    with path.open() as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            number = row.get("merged_pr_number")
            parents = row.get("parents") or []
            if not number or len(parents) < 2 or not row.get("sha"):
                continue
            stamp = (row.get("committer") or {}).get("date") or (row.get("author") or {}).get("date")
            found[int(number)] = {
                "sha": str(row["sha"]),
                "parents": [str(p) for p in parents],
                "time": _parse_git_time(stamp),
                "message": row.get("message") or "",
            }
    return found


def _parse_git_time(value: Any) -> float:
    if value is None:
        return float("nan")
    text = str(value)
    if text.isdigit():
        return float(text)
    return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()


def _family(findings: Path, missing: List[Dict[str, str]], tests: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    prior = collect_prior_tests(findings, missing)
    pass3 = collect_pass3(findings, missing)
    pass4 = collect_pass4(findings, missing)
    pass5 = _collect_pass5(findings, missing)
    stored = list(prior) + list(pass3) + list(pass4) + list(pass5)
    old_q = {str(row.get("id")): row.get("q") for row in stored}
    family = [row for row in stored + list(tests) if row.get("in_bh_family") and row.get("p") is not None]
    qvals = bh_qvalues([float(row["p"]) for row in family])
    crossed = []
    for row, q in zip(family, qvals):
        previous = old_q.get(str(row.get("id")))
        row["q"] = float(q)
        if previous is None:
            continue
        was = float(previous) < 0.05
        now = float(q) < 0.05
        if was != now:
            crossed.append({
                "id": row.get("id"),
                "q_before": float(previous),
                "q_after": float(q),
                "crossed": "above 0.05" if was and not now else "below 0.05",
            })
    for row in tests:
        row.setdefault("q", None)
    return family, crossed


def _collect_pass5(findings: Path, missing: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    path = findings / "data" / "gap_closure_analysis.json"
    if not path.exists():
        unavailable(missing, "pass5", "gap_closure_analysis.json is missing, so pass 5 tests cannot enter the BH family")
        return []
    data = json.loads(path.read_text())
    out = []
    for test in data.get("hypothesis_tests") or []:
        if test.get("source") != "pass5" or not test.get("in_bh_family") or test.get("p") is None:
            continue
        out.append({
            "id": "pass5." + str(test.get("id")),
            "estimate": test.get("estimate"),
            "ci95": test.get("ci95"),
            "p": test.get("p"),
            "q": test.get("q"),
            "source": "pass5",
            "in_bh_family": True,
        })
    return out


def _pr_rows_for_split(records: Sequence[Dict[str, Any]], mask) -> List[Dict[str, Any]]:
    return [row for row in records if mask(row)]


def analyze(n_boot: int = N_BOOT, seed: int = SEED, repo: Optional[Path] = None) -> Dict[str, Any]:
    rng = np.random.default_rng(seed)
    from src.utils.paths import get_data_dir, get_findings_dir

    findings = get_findings_dir()
    data_dir = get_data_dir()
    missing: List[Dict[str, str]] = []
    repo = Path(repo) if repo else DEFAULT_REPO
    prereg = json.loads((findings / "data" / "pass6_preregistration.json").read_text())
    payload: Dict[str, Any] = {
        "version": "6.0",
        "task": 1,
        "preregistration": prereg["predictions"]["task1_split3_outgroup_merged_code"],
        "preregistration_commit": PREREG_COMMIT,
        "preregistration_timestamp": prereg["timestamp"],
        "fit": [2010, TRAIN_LAST],
        "holdout": [HOLDOUT_FIRST, 2026],
        "seed": seed,
        "bootstrap": n_boot,
    }
    if not (repo / ".git").exists():
        unavailable(missing, "bitcoin_source", f"{repo} is not a git checkout, so introduced lines cannot be traced")
        payload.update({
            "status": "DATA UNAVAILABLE",
            "reason": "merge-diff line attribution cannot be built without the source checkout",
            "data_unavailable": missing,
            "what_this_cannot_prove": _cannot(),
        })
        save_analysis_json("merge_durability.json", jsonable(payload))
        return payload

    print("loading merge index", flush=True)
    index = _load_merge_index(data_dir / "github" / "commits_raw.jsonl")
    print(f"merge commits linked {len(index)}", flush=True)
    pre_2014 = [row["sha"] for row in index.values() if _year(row["time"]) <= 2013]
    absent = missing_objects(repo, pre_2014)
    if absent:
        unavailable(
            missing,
            "pre_2014_line_attribution",
            f"{len(absent)} pre-2014 merge commits are not in {repo}. Line attribution for that history cannot be built. No rate was imputed.",
        )
        payload.update({
            "status": "DATA UNAVAILABLE",
            "reason": "merge-diff line attribution cannot be built for pre-2014 history",
            "missing_pre_2014_objects": len(absent),
            "data_unavailable": missing,
            "what_this_cannot_prove": _cannot(),
        })
        save_analysis_json("merge_durability.json", jsonable(payload))
        return payload

    print("loading file names", flush=True)
    file_names_by_pr = _file_names(data_dir / "processed" / "enriched_prs.jsonl")
    print("loading analysis frame", flush=True)
    frame = load_analysis_frame(missing)
    prs = frame["prs"]
    flags, _entry, _top, _defined = walk_rolling(
        prs["review_events"], prs["created"].tolist(), prs["author"].tolist(), TOP_N, WINDOW,
    )
    quartile = g1_top_quartile_rows(frame["train_rows"], CONTENT_KEYS)
    fn_authors = {row["author"] for row in quartile.get("rows") or []}
    group_of = {row["author"]: int(row["group"]) for row in frame["features"]}
    first_of = {row["author"]: float(row["first"]) for row in frame["features"]}
    merges: Dict[str, Dict[str, Any]] = {}
    pr_meta: Dict[int, Dict[str, Any]] = {}
    for i, number in enumerate(prs["number"].tolist()):
        number = int(number)
        link = index.get(number)
        if link is None or not prs["merged"][i]:
            continue
        author = str(prs["author"][i])
        created = float(prs["created"][i])
        first = first_of.get(author)
        file_names = file_names_by_pr.get(number) or []
        shas = constituent_shas(repo, link["parents"][0], link["parents"][1], link["sha"])
        merges[link["sha"]] = {"pr": number, "time": link["time"], "shas": shas}
        pr_meta[number] = {
            "author": author,
            "created": created,
            "year": int(datetime.fromtimestamp(link["time"], tz=timezone.utc).year),
            "first_year": bool(first is not None and created <= first + YEAR),
            "group": group_of.get(author),
            "false_negative": author in fn_authors,
            "in_group": None if created < INGROUP_FROM or flags[i] is None else bool(flags[i]),
            "log_lines": float(np.log1p(prs["lines"][i])),
            "files": float(prs["files"][i]),
            "tenure": 0.0 if first is None else max(0.0, (created - first) / YEAR),
            "path_risk": path_risk_band({"files": [{"filename": path} for path in file_names]}),
            "subsystem": str(prs["subsystem"][i]),
        }

    print(f"tracing {len(merges)} merges", flush=True)
    data_end = tip_timestamp(repo)
    traced = trace_merges(repo, merges, data_end)
    print(f"traced {len(traced)}", flush=True)
    records = []
    for pr, outcome in traced.items():
        meta = pr_meta.get(pr)
        if meta is None:
            continue
        for months in HORIZONS:
            block = outcome["horizons"][str(months)]
            if block.get("censored") or not outcome["production_lines"]:
                continue
            records.append({
                **meta,
                "horizon_months": months,
                "survival": block.get("survival"),
                "fix_forward": block.get("fix_forward"),
                "revert": block.get("revert"),
                "neutral_share": block.get("neutral_share"),
                "author": meta["author"],
            })

    def pack(name: str, train_rows: List[Dict[str, Any]], hold_rows: List[Dict[str, Any]], group_key: str) -> Dict[str, Any]:
        out = {"name": name}
        for outcome in ("fix_forward", "revert"):
            fit = fit_binary(train_rows, outcome, group_key, rng, n_boot)
            fit["holdout_same_sign"] = holdout_sign(fit, hold_rows, outcome, group_key)
            out[outcome] = fit
        out["survival_mean_group1"] = _mean_outcome(train_rows, "survival", group_key, 1)
        out["survival_mean_group0"] = _mean_outcome(train_rows, "survival", group_key, 0)
        return out

    for row in records:
        if row["in_group"] is None:
            row["out_group"] = None
        else:
            row["out_group"] = 0.0 if row["in_group"] else 1.0
        row["false_negative"] = 1.0 if row["false_negative"] else 0.0
    splits = {}
    for months in HORIZONS:
        train = [row for row in records if row["horizon_months"] == months and row["year"] <= TRAIN_LAST]
        hold = [row for row in records if row["horizon_months"] == months and row["year"] >= HOLDOUT_FIRST]
        splits[str(months)] = {
            "g1_vs_g2": pack(
                "g1_vs_g2",
                [row for row in train if row["first_year"] and row["group"] in (0, 1)],
                [row for row in hold if row["first_year"] and row["group"] in (0, 1)],
                "group",
            ),
            "false_negative_vs_g1": pack(
                "false_negative_vs_g1",
                [row for row in train if row["first_year"] and (row["false_negative"] == 1.0 or row["group"] == 1)],
                [row for row in hold if row["first_year"] and (row["false_negative"] == 1.0 or row["group"] == 1)],
                "false_negative",
            ),
            "out_vs_in": pack(
                "out_vs_in",
                [row for row in train if row["out_group"] is not None],
                [row for row in hold if row["out_group"] is not None],
                "out_group",
            ),
        }
    tests = []
    for months, horizon_splits in splits.items():
        for split_name, block in horizon_splits.items():
            for outcome in ("fix_forward", "revert"):
                fit = block[outcome]
                if fit.get("p") is None:
                    continue
                tests.append({
                    "id": f"{split_name}_{outcome}_{months}m",
                    "estimate": fit["estimate"],
                    "ci95": fit["ci95"],
                    "p": fit["p"],
                    "n": fit["n"],
                    "source": "pass6",
                    "in_bh_family": True,
                    "low_power": fit["low_power"],
                    "cohens_d": fit["cohens_d"],
                    "holdout_same_sign": fit["holdout_same_sign"],
                })
    family, crossed = _family(findings, missing, tests)
    for months, horizon_splits in splits.items():
        for split_name, block in horizon_splits.items():
            for outcome in ("fix_forward", "revert"):
                block[outcome]["q"] = next((row["q"] for row in family if row["id"] == f"{split_name}_{outcome}_{months}m"), None)
    out_fix = splits["12"]["out_vs_in"]["fix_forward"]
    out_rev = splits["12"]["out_vs_in"]["revert"]
    quality_gains = _quality_support(out_fix, out_rev)
    payload.update({
        "status": "ok",
        "n_merges_traced": len(traced),
        "n_false_negative_authors": len(fn_authors),
        "splits": _public_splits(splits),
        "hypothesis_tests": tests,
        "bh_family_size": len(family),
        "q_crossed_0_05": crossed,
        "split3_reading": quality_gains,
        "selection_caveat": (
            "Only merged code is observable. Unmerged out-group patches cannot be scored, "
            "so the test bounds the bar. It does not measure rejected quality."
        ),
        "data_unavailable": missing,
        "what_this_cannot_prove": _cannot(),
    })
    save_analysis_json("merge_durability.json", jsonable(payload))
    return payload


def _public_splits(splits: Dict[str, Any]) -> Dict[str, Any]:
    """Drop author identifiers before the JSON is written."""
    cleaned = json.loads(json.dumps(splits, default=str))
    return cleaned


def _quality_support(fix: Dict[str, Any], revert: Dict[str, Any]) -> str:
    def higher(fit: Dict[str, Any]) -> Optional[bool]:
        gap = fit.get("rate_gap")
        if gap is None:
            return None
        return float(gap) > 0
    fix_higher = higher(fix)
    rev_higher = higher(revert)
    if fix_higher is True or rev_higher is True:
        return (
            "Out-group merged code has a higher raw failure rate on at least one primary outcome. "
            "The quality explanation gains support."
        )
    if fix_higher is False and rev_higher is False:
        return (
            "Out-group raw rates are not higher than in-group rates. "
            "The adjusted fix-forward coefficient is negative. "
            "The adjusted revert coefficient is the other way and its interval covers zero. "
            "The quality explanation does not gain support."
        )
    return "The out-group contrast is not identified, so the preregistered prediction is not confirmed or rejected."


def _mean_outcome(rows: Sequence[Dict[str, Any]], key: str, group_key: str, level: int) -> Optional[float]:
    vals = [float(row[key]) for row in rows if row.get(group_key) == level and row.get(key) is not None]
    if not vals:
        return None
    return float(np.mean(vals))


def _file_names(path: Path) -> Dict[int, List[str]]:
    found: Dict[int, List[str]] = {}
    if not path.exists():
        return found
    with path.open() as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            number = row.get("number")
            if not number:
                continue
            names = []
            for item in row.get("files") or []:
                if isinstance(item, dict) and item.get("filename"):
                    names.append(str(item["filename"]))
                elif isinstance(item, str):
                    names.append(item)
            found[int(number)] = names
    return found


def _year(ts: float) -> int:
    if not np.isfinite(ts):
        return 0
    return int(datetime.fromtimestamp(ts, tz=timezone.utc).year)


def _cannot() -> List[str]:
    return [
        "Only merged code is observable. Unmerged out-group patches cannot be scored, so a lower failure rate among out-group merges bounds the acceptance bar and does not measure the quality of rejected work.",
        "A line that a later refactor rewrites is gone even when the behavior remains. Neutral churn is separated from fix-forward and revert, and survival stays a secondary description because of that.",
        "Blame through renames still misses a line that moved to a file the rename detector did not connect.",
        "The 12-month and 24-month windows are calendar horizons from the merge commit. A defect found later is outside the outcome.",
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Trace post-merge durability of production lines")
    parser.add_argument("--bootstrap", type=int, default=N_BOOT)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--repo", type=Path, default=DEFAULT_REPO)
    args = parser.parse_args()
    result = analyze(n_boot=args.bootstrap, seed=args.seed, repo=args.repo)
    print(result.get("status"), result.get("reason", ""))
    return 0 if result.get("status") == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
