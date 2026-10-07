#!/usr/bin/env python3
"""First-year technical signal versus social legibility.

The within-cohort gap between people who later enter the rolling top 20 and
people who leave by 24 months is already measured. This pass asks which
first-year signals carry that gap. It does not observe ability or intent.
"""

from __future__ import annotations

import argparse
import heapq
import json
import re
import sys
from bisect import bisect_left, bisect_right
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
    stance_flags,
)
from scripts.analysis.rsd_ingroup_test import (  # noqa: E402
    DAY,
    ERA_2016,
    HORIZON_DAYS,
    cohens_d,
    effect_flag,
    is_bot_login,
    keyword_tone,
    load_identity,
    logistic_irls,
    parse_ts,
    review_tone,
    walk_rolling,
)
from src.utils.findings_io import save_analysis_json  # noqa: E402
from src.utils.logger import setup_logger  # noqa: E402
from src.utils.paths import get_data_dir, get_findings_dir  # noqa: E402

logger = setup_logger("first_year_signal")

YEAR = HORIZON_DAYS[12] * DAY
HORIZON_24 = HORIZON_DAYS[24] * DAY
WINDOW = HORIZON_DAYS[24] * DAY
TRAIN_LAST = 2023
HOLDOUT_FIRST = 2024
TOP_N = 20
TOP_REVIEWERS = 5
N_BOOT = 1000
SEED = 7
PASS2_REFERENCE_D = 0.7338842495815344

JARGON_RE = re.compile(
    r"\b(concept\s+acks?|approach\s+acks?|utacks?|tacks?|acks?|nits?)\b",
    re.I,
)
BUG_RE = re.compile(r"\b(fixes|fixed|fix|bugs|bug|crash|asserts|assert|errors|error)\b", re.I)
PULL_URL_RE = re.compile(r"bitcoin/bitcoin/(?:pull|issues)/(\d+)", re.I)
HASH_RE = re.compile(r"(?<![A-Za-z0-9])#(\d{4,6})\b")
TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9-]{2,}")
MAIL_DATE_RE = re.compile(br'"date": "([^"]+)"')

# Predictors in the joint model. T2c is the merge-rate gap itself, so the
# decomposition of that gap omits it. The logistic of group membership keeps it.
T_PREDICTORS = [
    "T1a_median_lines",
    "T1b_median_files",
    "T1c_consensus_share",
    "T1d_test_only_share",
    "T1e_bugfix_share",
    "T2a_mean_tone",
    "T2b_ack_top5_share",
    "T2d_mean_review_cycles",
    "T3a_n_directories",
    "T3b_n_active_areas",
]
T_GAP_BLOCK = T_PREDICTORS  # excludes T2c
S_PREDICTORS = [
    "S1_irc_linked",
    "S2_jargon_share",
    "S3_reviews_before_first",
    "S4_early_reciprocity",
    "S5_named_by_top20",
]
SIZE_CONTROLS = ["log_lines", "T1b_median_files", "prior_pr_count"]
# Raw median lines are skewed. Models use log1p(median lines) as the T1a term.
T_MODEL_KEYS = ["log_lines" if key == "T1a_median_lines" else key for key in T_GAP_BLOCK]
RECEPTION_KEYS = ["T2a_mean_tone", "T2b_ack_top5_share", "T2d_mean_review_cycles"]
CONTENT_KEYS = [key for key in T_MODEL_KEYS if key not in RECEPTION_KEYS]


def unavailable(bucket: List[Dict[str, str]], metric: str, reason: str) -> None:
    bucket.append({"metric": metric, "reason": reason, "status": "DATA UNAVAILABLE"})


def jsonable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jsonable(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.floating):
        value = float(obj)
        return value if np.isfinite(value) else None
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, float):
        return obj if np.isfinite(obj) else None
    if isinstance(obj, np.bool_):
        return bool(obj)
    return obj


def year_of(ts: float) -> int:
    return datetime.fromtimestamp(ts, tz=timezone.utc).year


def login_of(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("login") or value.get("name") or "")
    if value is None:
        return ""
    return str(value)


def jargon_hit(text: str) -> bool:
    return bool(JARGON_RE.search(text or ""))


def is_bugfix(title: str, labels: Sequence[Any]) -> bool:
    blob = title or ""
    for lab in labels or []:
        name = lab.get("name") if isinstance(lab, dict) else str(lab)
        blob += " " + str(name)
    return bool(BUG_RE.search(blob))


def is_consensus_path(path: str) -> bool:
    p = (path or "").lower()
    return (
        p.startswith("consensus/")
        or "/consensus/" in p
        or p == "src/validation.cpp"
        or p.endswith("/src/validation.cpp")
        or p.startswith("src/script/")
        or "/src/script/" in p
        or p.startswith("src/primitives/")
        or "/src/primitives/" in p
    )


def is_test_path(path: str) -> bool:
    p = (path or "").lower()
    return p.startswith(("src/test/", "test/", "src/qt/test/")) or "/test/" in p


def source_dir(path: str) -> Optional[str]:
    parts = [p for p in (path or "").split("/") if p]
    if not parts:
        return None
    if parts[0] == "src" and len(parts) > 1:
        return "src/" + parts[1]
    return parts[0]


def subsystem_of(path: str) -> str:
    """Primary-subsystem label from a file path. More specific prefixes win over src/."""
    text = (path or "").replace("\\", "/")
    if text.startswith("./"):
        text = text[2:]
    low = text.lower()
    if low.startswith("src/consensus/") or "/src/consensus/" in "/" + low or low.startswith("consensus/"):
        return "consensus"
    if low.startswith("src/validation") or "/src/validation" in "/" + low:
        return "consensus"
    if low.startswith("src/script/") or "/src/script/" in "/" + low or low.startswith("script/"):
        return "consensus"
    if low.startswith("src/wallet/") or "/src/wallet/" in "/" + low or low.startswith("wallet/"):
        return "wallet"
    if low.startswith("src/net"):
        return "p2p"
    if low.startswith("src/rpc/") or "/src/rpc/" in "/" + low or low.startswith("rpc/"):
        return "rpc"
    if low.startswith("src/qt/") or "/src/qt/" in "/" + low or low.startswith("qt/"):
        return "gui"
    if low.startswith("test/") or "/test/" in "/" + low:
        return "test"
    if low.startswith("doc/") or low.startswith("docs/") or "/doc/" in "/" + low:
        return "docs"
    if low.startswith("build") or "/build" in "/" + low:
        return "build"
    if low.startswith("src/") or low == "src":
        return "core"
    return "other"


def primary_subsystem(paths: Sequence[str]) -> str:
    """Subsystem with the most changed files. Ties break on the label, alphabetically."""
    counts: Dict[str, int] = defaultdict(int)
    for path in paths:
        if path:
            counts[subsystem_of(path)] += 1
    if not counts:
        return "other"
    return sorted(counts, key=lambda name: (-counts[name], name))[0]


def explicit_ack(text: str, state: str = "") -> bool:
    ack, _nack, concept = stance_flags(text or "", state or "")
    if str(state or "").upper() == "APPROVED":
        return True
    return bool(ack and not concept)


def pooled_cohens_d(values: np.ndarray, group: np.ndarray, cohort: np.ndarray) -> Optional[float]:
    """Within-cohort Cohen's d, weighted by n1*n0/n. Cells with under 2 per side are omitted."""
    num = 0.0
    den = 0.0
    for year in np.unique(cohort):
        m = cohort == year
        a = values[m & (group == 1)]
        b = values[m & (group == 0)]
        a = a[np.isfinite(a)]
        b = b[np.isfinite(b)]
        if a.size < 2 or b.size < 2:
            continue
        d = cohens_d(a, b)
        if d is None or not np.isfinite(d):
            continue
        w = (a.size * b.size) / (a.size + b.size)
        num += w * float(d)
        den += w
    if den <= 0:
        return None
    return num / den


def classify_decomposition(d_raw: float, d_t: float, d_s: float, d_both: float) -> Dict[str, Any]:
    """Apply the four decision rules to residual within-cohort d values."""
    t_reduction = d_raw - d_t
    s_reduction = d_raw - d_s
    s_after_t = d_t - d_both
    t_after_s = d_s - d_both
    t_rule = t_reduction > 0.5 * d_raw and s_after_t < 0.1
    s_rule = s_reduction > 0.5 * d_raw and t_after_s < 0.1
    if t_rule and s_rule:
        verdict = "redundant"
        text = (
            "Each block alone closes more than half the gap, and neither adds as much as 0.1 d once the other is controlled. "
            "The blocks are redundant on the merge-rate gap. The ordered technical rule also matches, "
            "but the technical block contains review reception (tone, a top-5 ACK, review cycles), which is a community response. "
            "Use the content-versus-reception split before reading the gap as detection of technical quality."
        )
    elif t_rule:
        verdict = "technical"
        text = (
            "The technical block alone closes more than half the gap, and the social block "
            "adds less than 0.1 d after technical signal is controlled. "
            "On these proxies, the community is primarily detecting technical quality."
        )
    elif s_rule:
        verdict = "social"
        text = (
            "The social block alone closes more than half the gap, and the technical block "
            "adds less than 0.1 d after social signal is controlled. "
            "On these proxies, the community is primarily detecting social legibility."
        )
    elif t_reduction > 0.1 and s_reduction > 0.1 and abs(d_both) < 0.2:
        verdict = "both"
        text = (
            "Both blocks reduce the gap, and the residual is below d=0.2. "
            "The signals are separable and both matter."
        )
    elif t_reduction > 0.1 and s_reduction > 0.1 and abs(d_both) >= 0.2:
        verdict = "unexplained"
        text = (
            "UNEXPLAINED VARIANCE. Both blocks contribute and the residual stays at or above d=0.2. "
            "Plausible missing pieces are prior reputation outside the repo, an in-person network, "
            "and a direct referral from an existing contributor."
        )
    else:
        verdict = "neither"
        text = (
            "Neither block closes half the gap on its own, and the two-block pattern does not "
            "meet the separable or unexplained rule. Read the residual d values directly."
        )
    return {
        "verdict": verdict,
        "text": text,
        "t_reduction": t_reduction,
        "s_reduction": s_reduction,
        "s_added_after_t": s_after_t,
        "t_added_after_s": t_after_s,
        "residual_d": d_both,
        "technical_rule_matches": t_rule,
        "social_rule_matches": s_rule,
    }


def topk_history(events: Sequence[Tuple[float, str]], window: float, k: int) -> List[Tuple[float, Optional[Tuple[str, ...]]]]:
    """Membership changes of the trailing-window top-k. State at t uses events strictly before t."""
    ordered = sorted(events, key=lambda row: row[0])
    counts: Dict[str, int] = {}
    left = 0
    history: List[Tuple[float, Optional[Tuple[str, ...]]]] = []
    prev: Optional[Tuple[str, ...]] = None
    for right, (ts, who) in enumerate(ordered):
        counts[who] = counts.get(who, 0) + 1
        cutoff = ts - window
        while left <= right and ordered[left][0] < cutoff:
            old = ordered[left][1]
            counts[old] = counts.get(old, 0) - 1
            if counts[old] <= 0:
                counts.pop(old, None)
            left += 1
        if len(counts) >= k:
            top: Optional[Tuple[str, ...]] = tuple(heapq.nlargest(k, counts, key=lambda name: (counts[name], name)))
        else:
            top = None
        if top != prev:
            history.append((float(ts), top))
            prev = top
    return history


def in_topk(history: Sequence[Tuple[float, Optional[Tuple[str, ...]]]], times: np.ndarray, ts: float, who: str) -> Optional[bool]:
    idx = bisect_left(times, ts) - 1
    if idx < 0:
        return None
    members = history[idx][1]
    if members is None:
        return None
    return who in members


def _finite_mask(*cols: np.ndarray) -> np.ndarray:
    mask = np.ones(cols[0].size, dtype=bool)
    for col in cols:
        mask &= np.isfinite(col)
    return mask


def design_matrix(
    cohort: np.ndarray,
    columns: Sequence[np.ndarray],
    include_group: Optional[np.ndarray] = None,
) -> np.ndarray:
    blocks: List[np.ndarray] = [np.ones(cohort.size)]
    if include_group is not None:
        blocks.append(include_group.astype(float))
    levels = np.unique(cohort.astype(int))
    for lev in levels[1:]:
        blocks.append((cohort.astype(int) == int(lev)).astype(float))
    for col in columns:
        sd = float(np.std(col))
        if sd < 1e-12:
            continue
        blocks.append((col - float(np.mean(col))) / sd)
    return np.column_stack(blocks)


def ols_resid(y: np.ndarray, x_mat: np.ndarray) -> Optional[np.ndarray]:
    beta = np.linalg.lstsq(x_mat, y, rcond=1e-8)[0]
    if beta.size != x_mat.shape[1] or not np.all(np.isfinite(beta)):
        return None
    return y - x_mat @ beta


def prepare_predictor(values: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Z-score observed values. Missing stays NaN here; the caller imputes."""
    observed = values[np.isfinite(values)]
    if observed.size < 5 or float(np.std(observed)) < 1e-12:
        return np.full(values.size, np.nan), np.zeros(values.size)
    mu = float(observed.mean())
    sd = float(observed.std())
    z = (values - mu) / sd
    missing = ~np.isfinite(values)
    return z, missing.astype(float)


def impute_train(z: np.ndarray, missing: np.ndarray) -> np.ndarray:
    out = z.copy()
    out[missing.astype(bool)] = 0.0
    out[~np.isfinite(out)] = 0.0
    return out


def load_prs(path: Path, ident: Any) -> Dict[str, Any]:
    authors: List[str] = []
    logins: Dict[str, set] = defaultdict(set)
    created: List[float] = []
    numbers: List[int] = []
    years: List[int] = []
    merged: List[int] = []
    decided: List[int] = []
    lines: List[float] = []
    files_n: List[float] = []
    consensus: List[int] = []
    test_only: List[int] = []
    bugfix: List[int] = []
    dirs: List[Tuple[str, ...]] = []
    tone_sum: List[float] = []
    tone_n: List[int] = []
    cycles: List[int] = []
    no_response: List[int] = []
    review_events: List[Tuple[float, str]] = []
    review_subsystem_events: List[Tuple[int, str, str]] = []
    subsystems: List[str] = []
    ack_events: List[Tuple[float, str, int]] = []
    given_reviews: List[Tuple[float, str, str]] = []
    authored_comments: List[Tuple[str, float, int]] = []
    n_read = 0

    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            pr = json.loads(line)
            n_read += 1
            login = login_of(pr.get("author"))
            author = ident.ident(login, irc=False)
            ts = parse_ts(pr.get("created_at"))
            if not author or ts is None:
                continue
            logins[author].add(login.lower())
            pr_i = len(authors)
            authors.append(author)
            created.append(ts)
            numbers.append(int(pr.get("number") or 0))
            years.append(year_of(ts))
            is_merged = bool(pr.get("merged"))
            state = str(pr.get("state") or "").lower()
            merged.append(1 if is_merged else 0)
            decided.append(1 if is_merged or state == "closed" or pr.get("closed_at") else 0)
            comp = pr.get("complexity") or {}
            n_lines = comp.get("total_changes")
            if n_lines is None:
                n_lines = (pr.get("total_additions") or 0) + (pr.get("total_deletions") or 0)
            lines.append(float(n_lines or 0))
            files_n.append(float(comp.get("files_changed") or pr.get("total_files_changed") or len(pr.get("files") or []) or 0))
            file_paths = []
            for fobj in pr.get("files") or []:
                file_paths.append(fobj.get("filename") if isinstance(fobj, dict) else str(fobj))
            consensus.append(1 if any(is_consensus_path(p) for p in file_paths) else 0)
            test_only.append(1 if file_paths and all(is_test_path(p) for p in file_paths) else 0)
            bugfix.append(1 if is_bugfix(pr.get("title") or "", pr.get("labels") or []) else 0)
            dirs.append(tuple(sorted({d for d in (source_dir(p) for p in file_paths) if d})))
            sub = primary_subsystem(file_paths)
            subsystems.append(sub)
            scores: List[float] = []
            n_cycles = 0
            peer = False

            def absorb_peer(who: str, when: Optional[float], text: str, state: str, is_review_object: bool) -> None:
                nonlocal peer, n_cycles
                if not who or who == author or when is None:
                    return
                peer = True
                tone = review_tone({"body": text, "state": state}) if is_review_object else keyword_tone(text)
                scores.append(tone)
                if is_review_object:
                    review_events.append((when, who))
                    review_subsystem_events.append((int(year_of(when)), sub, who))
                    n_cycles += 1
                    given_reviews.append((when, who, author))
                if explicit_ack(text, state):
                    ack_events.append((when, who, pr_i))

            for rev in pr.get("reviews") or []:
                if not isinstance(rev, dict):
                    continue
                who = ident.ident(login_of(rev.get("author") or rev.get("user")), irc=False)
                when = parse_ts(rev.get("submitted_at") or rev.get("created_at"))
                absorb_peer(who, when, rev.get("body") or "", str(rev.get("state") or ""), True)
                if who and who != author and when is not None and jargon_hit(rev.get("body") or ""):
                    authored_comments.append((who, when, 1))
                elif who and who != author and when is not None:
                    authored_comments.append((who, when, 0))
            for com in list(pr.get("comments") or []) + list(pr.get("review_comments") or []):
                if not isinstance(com, dict):
                    continue
                who = ident.ident(login_of(com.get("author") or com.get("user")), irc=False)
                when = parse_ts(com.get("created_at"))
                text = com.get("body") or ""
                absorb_peer(who, when, text, "", False)
                if who and when is not None:
                    authored_comments.append((who, when, 1 if jargon_hit(text) else 0))
            tone_sum.append(float(np.sum(scores)) if scores else 0.0)
            tone_n.append(len(scores))
            cycles.append(n_cycles)
            no_response.append(0 if peer else 1)

    return {
        "n_read": n_read,
        "author": np.asarray(authors, dtype=object),
        "login_aliases": logins,
        "created": np.asarray(created, dtype=float),
        "number": np.asarray(numbers, dtype=np.int32),
        "year": np.asarray(years, dtype=np.int16),
        "merged": np.asarray(merged, dtype=np.int8),
        "decided": np.asarray(decided, dtype=np.int8),
        "lines": np.asarray(lines, dtype=float),
        "files": np.asarray(files_n, dtype=float),
        "consensus": np.asarray(consensus, dtype=np.int8),
        "test_only": np.asarray(test_only, dtype=np.int8),
        "bugfix": np.asarray(bugfix, dtype=np.int8),
        "dirs": dirs,
        "tone_sum": np.asarray(tone_sum, dtype=float),
        "tone_n": np.asarray(tone_n, dtype=np.int32),
        "cycles": np.asarray(cycles, dtype=np.int32),
        "no_response": np.asarray(no_response, dtype=np.int8),
        "subsystem": np.asarray(subsystems, dtype=object),
        "review_events": review_events,
        "review_subsystem_events": review_subsystem_events,
        "ack_events": ack_events,
        "given_reviews": given_reviews,
        "authored_comments": authored_comments,
    }


def irc_mentions(path: Path, wanted: set) -> Dict[int, List[float]]:
    found: Dict[int, List[float]] = defaultdict(list)
    if not path.exists():
        return found
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            msg = json.loads(line)
            ts = parse_ts(msg.get("timestamp") or msg.get("time"))
            if ts is None:
                continue
            text = msg.get("message") or msg.get("content") or ""
            nums = {int(n) for n in PULL_URL_RE.findall(text)}
            nums.update(int(n) for n in HASH_RE.findall(text))
            for num in nums:
                if num in wanted:
                    found[num].append(ts)
    for num in found:
        found[num].sort()
    return found


def build_people(prs: Dict[str, Any], entry: Dict[str, float], dataset_end: float) -> List[Dict[str, Any]]:
    by_author: Dict[str, List[int]] = defaultdict(list)
    for i, author in enumerate(prs["author"].tolist()):
        by_author[author].append(i)
    people = []
    for author, idxs in by_author.items():
        idxs.sort(key=lambda i: float(prs["created"][i]))
        first = float(prs["created"][idxs[0]])
        end = first + YEAR
        window = [i for i in idxs if float(prs["created"][i]) <= end]
        if not window:
            continue
        horizon = first + HORIZON_24
        observable = dataset_end >= horizon
        active = any(float(prs["created"][i]) >= horizon for i in idxs) if observable else False
        entered = entry.get(author)
        later = entered is not None and entered > first + 1
        people.append({
            "author": author,
            "first": first,
            "year": year_of(first),
            "window": window,
            "all_idxs": idxs,
            "observable24": observable,
            "active24": active,
            "entered_ts": entered,
            "later_entered": later,
            "ever_entered": entered is not None,
        })
    return people


def person_features(
    people: List[Dict[str, Any]],
    prs: Dict[str, Any],
    ack_hit: np.ndarray,
    ack_defined: np.ndarray,
    mentions: Dict[int, List[float]],
    reviews_before: Dict[str, int],
    reciprocity: Dict[str, int],
    named: Dict[str, int],
    active_dirs_by_year: Dict[int, set],
    review_era_start: float,
) -> List[Dict[str, Any]]:
    comments_by: Dict[str, List[Tuple[float, int]]] = defaultdict(list)
    for author, ts, hit in prs["authored_comments"]:
        comments_by[author].append((ts, hit))
    for rows in comments_by.values():
        rows.sort()
    rows_out = []
    for person in people:
        window = person["window"]
        lines = prs["lines"][window]
        files = prs["files"][window]
        decided = prs["decided"][window].astype(bool)
        merged = prs["merged"][window].astype(bool)
        first = person["first"]
        end = first + YEAR
        pre_review_era = end < review_era_start
        tone_n = int(prs["tone_n"][window].sum())
        tone = float(prs["tone_sum"][window].sum() / tone_n) if tone_n else np.nan
        if pre_review_era:
            cycles = np.nan
            ack_share = np.nan
        else:
            # Review objects before 2016 are absent. Do not average those zeros in.
            post = [
                window[i] for i, flag in enumerate(merged)
                if flag and float(prs["created"][window[i]]) >= review_era_start
            ]
            cycles = float(np.mean(prs["cycles"][post])) if post else np.nan
            defined_idx = [i for i in window if ack_defined[i]]
            ack_share = float(np.mean(ack_hit[defined_idx])) if defined_idx else np.nan
        dirs: set = set()
        for i in window:
            dirs.update(prs["dirs"][i])
        active_hit = set()
        for i in window:
            year = int(prs["year"][i])
            active = active_dirs_by_year.get(year) or set()
            active_hit.update(set(prs["dirs"][i]) & active)
        irc = 0
        for i in window:
            num = int(prs["number"][i])
            times = mentions.get(num) or []
            created = float(prs["created"][i])
            if any(ts <= created + 7 * DAY for ts in times):
                irc = 1
                break
        own_comments = [row for row in comments_by.get(person["author"], []) if first <= row[0] <= end]
        jargon = float(np.mean([row[1] for row in own_comments])) if own_comments else np.nan
        priors = []
        earlier = 0
        for i in person["all_idxs"]:
            if float(prs["created"][i]) > end:
                break
            priors.append(earlier)
            earlier += 1
        reviews_observable = person["first"] >= review_era_start
        rec = {
            "author": person["author"],
            "first": first,
            "year": person["year"],
            "group": person["group"],
            "T1a_median_lines": float(np.median(lines)),
            "T1b_median_files": float(np.median(files)),
            "T1c_consensus_share": float(np.mean(prs["consensus"][window])),
            "T1d_test_only_share": float(np.mean(prs["test_only"][window])),
            "T1e_bugfix_share": float(np.mean(prs["bugfix"][window])),
            "T2a_mean_tone": tone,
            "T2b_ack_top5_share": ack_share,
            "T2c_merge_rate": float(np.mean(prs["merged"][window][decided])) if decided.any() else np.nan,
            "T2d_mean_review_cycles": cycles,
            "T3a_n_directories": float(len(dirs)),
            "T3b_n_active_areas": float(len(active_hit)),
            "S1_irc_linked": float(irc),
            "S2_jargon_share": jargon,
            "S3_reviews_before_first": float(reviews_before.get(person["author"], 0)) if reviews_observable else np.nan,
            "S3_any_review_before": float(reviews_before.get(person["author"], 0) > 0) if reviews_observable else np.nan,
            "S4_early_reciprocity": np.nan if pre_review_era else float(reciprocity.get(person["author"], 0)),
            "S5_named_by_top20": float(named.get(person["author"], 0)),
            "prior_pr_count": float(np.mean(priors)) if priors else 0.0,
            "log_lines": float(np.log1p(np.median(lines))),
        }
        rows_out.append(rec)
    return rows_out


def reported_ci(draws: np.ndarray, n_boot: int) -> Optional[List[float]]:
    """Percentile interval. If more than 20% of resamples failed, do not invent one."""
    ok = int(np.isfinite(draws).sum()) if draws.size else 0
    if n_boot <= 0 or ok < 0.8 * n_boot:
        return None
    return ci_from_draws(draws)


def column(rows: Sequence[Dict[str, Any]], key: str) -> np.ndarray:
    return np.asarray([row.get(key, np.nan) for row in rows], dtype=float)


def matched_comparison(
    rows: Sequence[Dict[str, Any]],
    key: str,
    rng: np.random.Generator,
    n_boot: int,
    train: bool,
) -> Optional[Dict[str, Any]]:
    use = [row for row in rows if (row["year"] <= TRAIN_LAST) == train]
    if len(use) < 8:
        return None
    y = column(use, key)
    group = column(use, "group")
    cohort = column(use, "year")
    mask = np.isfinite(y) & np.isfinite(group)
    if int(mask.sum()) < 8 or np.unique(group[mask]).size < 2:
        return None
    y, group, cohort = y[mask], group[mask], cohort[mask]
    kept = [use[i] for i in np.flatnonzero(mask)]
    extras = []
    for control in ("log_lines", "T1b_median_files", "prior_pr_count"):
        if key in {"T1a_median_lines", "log_lines"} and control == "log_lines":
            continue
        if key == "T1b_median_files" and control == "T1b_median_files":
            continue
        if key == "prior_pr_count" and control == "prior_pr_count":
            continue
        vals = column(kept, control)
        if np.isfinite(vals).sum() < 8 or np.nanstd(vals) < 1e-12:
            continue
        vals = np.where(np.isfinite(vals), vals, np.nanmean(vals))
        extras.append(vals)
    g1 = y[group == 1]
    g2 = y[group == 0]
    d = pooled_cohens_d(y, group, cohort)
    if d is None:
        d = cohens_d(g1, g2)
    x_mat = design_matrix(cohort, extras, include_group=group)
    beta = np.linalg.lstsq(x_mat, y, rcond=1e-8)[0]
    if beta.size < 2 or not np.isfinite(beta[1]):
        return None
    diff = float(beta[1])
    scale = float(np.std(y))
    smd = diff / scale if scale > 1e-12 else np.nan
    draws = np.empty(n_boot)
    d_draws = np.empty(n_boot)
    # Stratify the resample by cohort so the match stays intact.
    cohorts = np.unique(cohort.astype(int))
    buckets = {int(c): np.flatnonzero(cohort.astype(int) == int(c)) for c in cohorts}
    for i in range(n_boot):
        take = []
        for ix in buckets.values():
            take.append(ix[rng.integers(0, ix.size, ix.size)])
        ix = np.concatenate(take)
        yy = y[ix]
        gg = group[ix]
        cc = cohort[ix]
        if np.unique(gg).size < 2 or np.unique(cc.astype(int)).size < 1:
            draws[i] = np.nan
            d_draws[i] = np.nan
            continue
        xx = [col[ix] for col in extras]
        try:
            b = np.linalg.lstsq(design_matrix(cc, xx, include_group=gg), yy, rcond=1e-8)[0]
            sd = float(np.std(yy))
            draws[i] = float(b[1] / sd) if sd > 1e-12 and np.isfinite(b[1]) else np.nan
        except Exception:
            draws[i] = np.nan
        dd = pooled_cohens_d(yy, gg, cc)
        d_draws[i] = np.nan if dd is None else dd
    return {
        "g1_mean": float(np.mean(g1)) if g1.size else None,
        "g2_mean": float(np.mean(g2)) if g2.size else None,
        "g1_median": float(np.median(g1)) if g1.size else None,
        "g2_median": float(np.median(g2)) if g2.size else None,
        "n_g1": int(g1.size),
        "n_g2": int(g2.size),
        "standardized_difference": float(smd) if np.isfinite(smd) else None,
        "ci95": reported_ci(draws, n_boot),
        "p": p_from_draws(draws),
        "cohens_d": None if d is None else float(d),
        "cohens_d_ci95": reported_ci(d_draws, n_boot),
        "effect_size_flag": effect_flag(None if d is None else float(d)),
        "n": int(y.size),
        "estimate": float(smd) if np.isfinite(smd) else None,
    }


def block_matrix(rows: Sequence[Dict[str, Any]], keys: Sequence[str], extra: Sequence[str] = ()) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """Intercept, cohort dummies, then z-scored predictors. Names align with the predictor columns."""
    cohort = column(rows, "year")
    levels = np.unique(cohort.astype(int))
    blocks: List[np.ndarray] = [np.ones(len(rows))]
    for lev in levels[1:]:
        blocks.append((cohort.astype(int) == int(lev)).astype(float))
    names: List[str] = []
    for key in list(keys) + list(extra):
        z, missing_col = prepare_predictor(column(rows, key))
        if not np.isfinite(z).any():
            continue
        filled = impute_train(z, missing_col)
        if float(np.std(filled)) < 1e-12:
            continue
        blocks.append(filled)
        names.append(key)
        if missing_col.any() and not missing_col.all() and float(np.std(missing_col)) > 1e-12:
            blocks.append(missing_col)
            names.append(key + "_missing")
    return np.column_stack(blocks), cohort, names


def residual_gap(y: np.ndarray, group: np.ndarray, cohort: np.ndarray, x_mat: np.ndarray) -> Optional[float]:
    resid = ols_resid(y, x_mat)
    if resid is None:
        return None
    d = pooled_cohens_d(resid, group, cohort)
    if d is None:
        d = cohens_d(resid[group == 1], resid[group == 0])
    return None if d is None else float(d)


def fit_logistic(
    rows: Sequence[Dict[str, Any]],
    keys: Sequence[str],
    rng: np.random.Generator,
    n_boot: int,
) -> Optional[Dict[str, Any]]:
    y = column(rows, "group")
    x_mat, _cohort, names = block_matrix(rows, keys)
    if np.unique(y).size < 2 or x_mat.shape[0] < 30:
        return None
    beta = logistic_irls(x_mat, y)
    if beta is None:
        return None
    # Column 0 is the intercept. Predictor columns follow cohort dummies.
    n_cohort = max(int(np.unique(column(rows, "year")).size) - 1, 0)
    start = 1 + n_cohort
    coefs = {}
    draws = {name: np.empty(n_boot) for name in names}
    n = y.size
    for i in range(n_boot):
        ix = rng.integers(0, n, n)
        if np.unique(y[ix]).size < 2:
            for name in names:
                draws[name][i] = np.nan
            continue
        b = logistic_irls(x_mat[ix], y[ix])
        if b is None or b.size != beta.size:
            for name in names:
                draws[name][i] = np.nan
            continue
        for j, name in enumerate(names):
            draws[name][i] = float(b[start + j]) if start + j < b.size else np.nan
    for j, name in enumerate(names):
        if start + j >= beta.size:
            continue
        est = float(beta[start + j])
        coefs[name] = {
            "estimate": est,
            "ci95": None if n_boot <= 0 else reported_ci(draws[name], n_boot),
            "p": None if n_boot <= 0 else p_from_draws(draws[name]),
            "n": int(n),
        }
    return {"coefficients": coefs, "n": int(n), "n_g1": int(y.sum()), "names": names}


def scan_named(
    data_dir: Path,
    ident: Any,
    people: Sequence[Dict[str, Any]],
    login_aliases: Dict[str, set],
    history: Sequence[Tuple[float, Optional[Tuple[str, ...]]]],
    times: np.ndarray,
    missing: List[Dict[str, str]],
) -> Dict[str, int]:
    """Top-20 speaker mentions a future contributor in the 30 days before their first PR."""
    hits = {person["author"]: 0 for person in people}
    windows: Dict[int, List[Tuple[str, set]]] = defaultdict(list)
    for person in people:
        tokens = {tok for tok in login_aliases.get(person["author"], set()) if len(tok) >= 3}
        if not tokens:
            continue
        start = person["first"] - 30 * DAY
        day0 = int(start // DAY)
        day1 = int(person["first"] // DAY)
        for day in range(day0, day1 + 1):
            windows[day].append((person["author"], tokens))
    if not windows:
        unavailable(missing, "S5_named_by_top20", "no contributor windows were available for the pre-PR mention search")
        return hits
    irc_path = data_dir / "irc" / "messages.jsonl"
    mail_path = data_dir / "mailing_lists" / "emails.jsonl"
    unresolved_speakers = 0
    checked = 0

    def consider(ts: float, speaker_raw: str, text: str, irc: bool) -> None:
        nonlocal unresolved_speakers, checked
        day = int(ts // DAY)
        slot = windows.get(day)
        if not slot:
            return
        checked += 1
        speaker = ident.ident(speaker_raw, irc=irc)
        if not speaker:
            unresolved_speakers += 1
            return
        top = in_topk(history, times, ts, speaker)
        if top is not True:
            return
        tokens = set(TOKEN_RE.findall((text or "").lower()))
        for author, names in slot:
            if author == speaker:
                continue
            if tokens & names:
                hits[author] = 1

    if not irc_path.exists():
        unavailable(missing, "S5_irc", "data/irc/messages.jsonl is missing")
    else:
        with irc_path.open(encoding="utf-8") as handle:
            for line in handle:
                msg = json.loads(line)
                ts = parse_ts(msg.get("timestamp") or msg.get("time"))
                if ts is None:
                    continue
                nick = str(msg.get("nickname") or msg.get("author") or "").lstrip("@+")
                consider(ts, nick, msg.get("message") or "", True)
    if not mail_path.exists():
        unavailable(missing, "S5_mail", "mailing list archive is missing")
    else:
        with mail_path.open("rb") as handle:
            for raw in handle:
                stamp = MAIL_DATE_RE.search(raw)
                if stamp is None:
                    continue
                ts = parse_ts(stamp.group(1).decode("utf-8", "ignore"))
                if ts is None or int(ts // DAY) not in windows:
                    continue
                try:
                    mail = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                sender = str(mail.get("from") or "")
                blob = f"{sender} {mail.get('subject') or ''} {(mail.get('body') or '')[:800]}"
                local = sender.split("<")[-1].split("@")[0].strip().lower()
                consider(ts, local, blob, False)
    missing.append({
        "metric": "S5_named_by_top20",
        "status": "LOW OBSERVABILITY",
        "reason": (
            "IRC nick resolution is limited, so a speaker who is in the rolling top 20 but did not resolve "
            "is not counted. Mentions by unresolved speakers are missed, not treated as absence. "
            f"Candidate messages in the pre-PR windows: {checked}. Unresolved speakers among them: {unresolved_speakers}."
        ),
    })
    return hits


def load_analysis_frame(missing: List[Dict[str, str]]) -> Dict[str, Any]:
    """Grouped first-year features used by pass 4. Years only; no person list is returned to callers that do not ask."""
    data_dir = get_data_dir()
    pr_path = data_dir / "processed" / "enriched_prs.jsonl"
    if not pr_path.exists():
        raise RuntimeError(f"DATA UNAVAILABLE: {pr_path} is not in the dataset")
    ident = load_identity()
    logger.info("loading PRs")
    prs = load_prs(pr_path, ident)
    created = prs["created"]
    dataset_end = float(np.nanmax(created))
    logger.info("rolling top %s", TOP_N)
    _flags, entry, _final, _defined = walk_rolling(
        prs["review_events"], created.tolist(), prs["author"].tolist(), TOP_N, WINDOW,
    )
    people = build_people(prs, entry, dataset_end)
    n_ever = len(entry)
    n_ever_authored = sum(1 for p in people if p["ever_entered"])
    for person in people:
        if person["later_entered"] or person["ever_entered"]:
            person["group"] = 1
        elif person["observable24"] and not person["active24"] and not person["ever_entered"]:
            person["group"] = 0
        else:
            person["group"] = -1
    grouped = [p for p in people if p["group"] in (0, 1)]
    logger.info("groups G1 %s G2 %s ever %s", sum(p["group"] == 1 for p in grouped), sum(p["group"] == 0 for p in grouped), n_ever)

    logger.info("top-k histories and ACK flags")
    hist20 = topk_history(prs["review_events"], WINDOW, TOP_N)
    hist5 = topk_history(prs["review_events"], WINDOW, TOP_REVIEWERS)
    times20 = np.asarray([row[0] for row in hist20], dtype=float)
    times5 = np.asarray([row[0] for row in hist5], dtype=float)
    ack_hit = np.zeros(created.size, dtype=np.int8)
    ack_defined = np.zeros(created.size, dtype=np.int8)
    for i, ts in enumerate(created.tolist()):
        idx = bisect_left(times5, float(ts)) - 1 if times5.size else -1
        if idx >= 0 and hist5[idx][1] is not None:
            ack_defined[i] = 1
    for ts, who, pr_i in prs["ack_events"]:
        flag = in_topk(hist5, times5, ts, who)
        if flag is True:
            ack_hit[pr_i] = 1
    reviews_before: Dict[str, int] = defaultdict(int)
    first_of = {p["author"]: p["first"] for p in grouped}
    for ts, reviewer, _author in prs["given_reviews"]:
        first = first_of.get(reviewer)
        if first is not None and ts < first:
            reviews_before[reviewer] += 1
    by_reviewer: Dict[str, List[Tuple[float, str]]] = defaultdict(list)
    for ts, reviewer, author in prs["given_reviews"]:
        by_reviewer[reviewer].append((ts, author))
    for rows in by_reviewer.values():
        rows.sort()
    reciprocity = {p["author"]: 0 for p in grouped}
    for person in grouped:
        if person["first"] + YEAR < ERA_2016:
            continue
        start, end = person["first"], person["first"] + YEAR
        for ts, author in by_reviewer.get(person["author"], []):
            if ts < start or ts > end:
                continue
            if in_topk(hist20, times20, ts, author) is not True:
                continue
            later = by_reviewer.get(author, [])
            lo = bisect_right(later, (ts, "\uffff"))
            for ts2, author2 in later[lo:]:
                if ts2 > end:
                    break
                if author2 == person["author"]:
                    reciprocity[person["author"]] = 1
                    break
            if reciprocity[person["author"]]:
                break

    logger.info("IRC mention index")
    wanted = set(int(n) for n in prs["number"].tolist() if int(n) > 0)
    irc_path = data_dir / "irc" / "messages.jsonl"
    if not irc_path.exists():
        unavailable(missing, "S1_irc_linked", "data/irc/messages.jsonl is missing, so IRC-linked PRs cannot be matched")
        mentions: Dict[int, List[float]] = {}
    else:
        mentions = irc_mentions(irc_path, wanted)
    logger.info("pre-PR name mentions")
    named = scan_named(data_dir, ident, grouped, prs["login_aliases"], hist20, times20, missing)

    # Active directories: 10 or more PRs in that calendar year.
    dir_counts: Dict[int, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for i, year in enumerate(prs["year"].tolist()):
        for directory in prs["dirs"][i]:
            dir_counts[int(year)][directory] += 1
    active_dirs = {year: {d for d, c in counts.items() if c >= 10} for year, counts in dir_counts.items()}
    review_era = float(ERA_2016)
    features = person_features(
        grouped, prs, ack_hit, ack_defined, mentions, reviews_before, reciprocity, named, active_dirs, review_era,
    )
    n_review_missing = sum(1 for row in features if not np.isfinite(row["S3_reviews_before_first"]))
    if n_review_missing:
        unavailable(
            missing,
            "S3_pre_review_objects",
            f"{n_review_missing} grouped contributors opened their first PR before 2016-01-01. "
            "Reviews given before that PR are missing, not zero, because GitHub review objects are not in the corpus yet.",
        )
    train_rows = [row for row in features if row["year"] <= TRAIN_LAST]
    hold_rows = [row for row in features if row["year"] >= HOLDOUT_FIRST]
    if sum(r["group"] == 1 for r in hold_rows) < 5 or sum(r["group"] == 0 for r in hold_rows) < 5:
        unavailable(
            missing,
            "holdout_groups",
            "2024-2026 does not have at least 5 later top-20 entrants and 5 leavers observable on the same definition. Holdout confirmation is unavailable.",
        )
    return {
        "prs": prs,
        "features": features,
        "train_rows": train_rows,
        "hold_rows": hold_rows,
        "grouped": grouped,
        "n_ever": n_ever,
        "n_ever_authored": n_ever_authored,
    }


def analyze(n_boot: int = N_BOOT, seed: int = SEED) -> Dict[str, Any]:
    rng = np.random.default_rng(seed)
    findings = get_findings_dir()
    missing: List[Dict[str, str]] = []
    frame = load_analysis_frame(missing)
    prs = frame["prs"]
    features = frame["features"]
    train_rows = frame["train_rows"]
    hold_rows = frame["hold_rows"]
    grouped = frame["grouped"]
    n_ever = frame["n_ever"]
    n_ever_authored = frame["n_ever_authored"]

    logger.info("matched comparisons")
    comparisons = []
    tests: List[Dict[str, Any]] = []
    predictor_keys = [
        ("T1a", "T1a_median_lines", "T"),
        ("T1b", "T1b_median_files", "T"),
        ("T1c", "T1c_consensus_share", "T"),
        ("T1d", "T1d_test_only_share", "T"),
        ("T1e", "T1e_bugfix_share", "T"),
        ("T2a", "T2a_mean_tone", "T"),
        ("T2b", "T2b_ack_top5_share", "T"),
        ("T2c", "T2c_merge_rate", "T"),
        ("T2d", "T2d_mean_review_cycles", "T"),
        ("T3a", "T3a_n_directories", "T"),
        ("T3b", "T3b_n_active_areas", "T"),
        ("S1", "S1_irc_linked", "S"),
        ("S2", "S2_jargon_share", "S"),
        ("S3_count", "S3_reviews_before_first", "S"),
        ("S3_any", "S3_any_review_before", "S"),
        ("S4", "S4_early_reciprocity", "S"),
        ("S5", "S5_named_by_top20", "S"),
    ]
    for short, key, block in predictor_keys:
        fit = matched_comparison(features, key, rng, n_boot, train=True)
        hold = matched_comparison(features, key, rng, n_boot, train=False)
        if fit is None:
            unavailable(missing, key, "fewer than 8 grouped contributors with this measure in 2010-2023, or the measure does not vary")
            tests.append(_test(short, key, block, None, hold, family=False))
            comparisons.append({"id": short, "predictor": key, "block": block, "status": "DATA UNAVAILABLE"})
            continue
        if hold is None:
            unavailable(missing, key + "_holdout", "the 2024-2026 matched comparison did not have both groups")
        same = None
        if hold and hold.get("estimate") is not None and fit.get("estimate") is not None:
            same = bool(np.sign(hold["estimate"]) == np.sign(fit["estimate"]))
        row = {"id": short, "predictor": key, "block": block, **fit, "holdout_estimate": None if not hold else hold.get("estimate"),
               "holdout_same_sign": same}
        comparisons.append(row)
        tests.append(_test(short, key, block, fit, hold, family=True, low=(key == "S5_named_by_top20")))

    logger.info("decomposition")
    y = column(train_rows, "T2c_merge_rate")
    group = column(train_rows, "group")
    cohort = column(train_rows, "year")
    usable = np.isfinite(y)
    y_u, g_u, c_u = y[usable], group[usable], cohort[usable]
    base_rows = [train_rows[i] for i in np.flatnonzero(usable)]
    d_raw = pooled_cohens_d(y_u, g_u, c_u)
    if d_raw is None:
        d_raw = cohens_d(y_u[g_u == 1], y_u[g_u == 0])
    if d_raw is None:
        unavailable(missing, "decomposition", "the within-cohort merge-rate gap could not be computed")
        d_raw = float("nan")
    x_t, _, _ = block_matrix(base_rows, T_MODEL_KEYS, extra=["prior_pr_count"])
    x_s, _, _ = block_matrix(base_rows, S_PREDICTORS, extra=SIZE_CONTROLS)
    x_b, _, _ = block_matrix(base_rows, T_MODEL_KEYS + S_PREDICTORS, extra=["prior_pr_count"])
    x_size, _, _ = block_matrix(base_rows, [], extra=SIZE_CONTROLS)
    d_t = residual_gap(y_u, g_u, c_u, x_t)
    d_s = residual_gap(y_u, g_u, c_u, x_s)
    d_both = residual_gap(y_u, g_u, c_u, x_b)
    d_size = residual_gap(y_u, g_u, c_u, x_size)
    x_content, _, _ = block_matrix(base_rows, CONTENT_KEYS, extra=["prior_pr_count"])
    x_reception, _, _ = block_matrix(base_rows, RECEPTION_KEYS, extra=SIZE_CONTROLS)
    d_content = residual_gap(y_u, g_u, c_u, x_content)
    d_reception = residual_gap(y_u, g_u, c_u, x_reception)
    decomp_rule = None
    if all(v is not None and np.isfinite(v) for v in (d_raw, d_t, d_s, d_both)):
        decomp_rule = classify_decomposition(float(d_raw), float(d_t), float(d_s), float(d_both))
    else:
        unavailable(missing, "decomposition_rule", "one of the block residual gaps was undefined")

    # Bootstrap the residual ds by resampling rows.
    boot_raw = np.empty(n_boot)
    boot_t = np.empty(n_boot)
    boot_s = np.empty(n_boot)
    boot_both = np.empty(n_boot)
    boot_content = np.empty(n_boot)
    boot_reception = np.empty(n_boot)
    n = y_u.size
    for i in range(n_boot):
        ix = rng.integers(0, n, n)
        if np.unique(g_u[ix]).size < 2:
            boot_raw[i] = boot_t[i] = boot_s[i] = boot_both[i] = np.nan
            boot_content[i] = boot_reception[i] = np.nan
            continue
        raw_d = pooled_cohens_d(y_u[ix], g_u[ix], c_u[ix])
        t_d = residual_gap(y_u[ix], g_u[ix], c_u[ix], x_t[ix])
        s_d = residual_gap(y_u[ix], g_u[ix], c_u[ix], x_s[ix])
        both_d = residual_gap(y_u[ix], g_u[ix], c_u[ix], x_b[ix])
        content_d = residual_gap(y_u[ix], g_u[ix], c_u[ix], x_content[ix])
        reception_d = residual_gap(y_u[ix], g_u[ix], c_u[ix], x_reception[ix])
        boot_raw[i] = np.nan if raw_d is None else raw_d
        boot_t[i] = np.nan if t_d is None else t_d
        boot_s[i] = np.nan if s_d is None else s_d
        boot_both[i] = np.nan if both_d is None else both_d
        boot_content[i] = np.nan if content_d is None else content_d
        boot_reception[i] = np.nan if reception_d is None else reception_d
    for name, point, draws in (
        ("gap_raw", d_raw, boot_raw),
        ("gap_after_T", d_t, boot_t),
        ("gap_after_S", d_s, boot_s),
        ("gap_after_both", d_both, boot_both),
    ):
        tests.append({
            "id": name,
            "block": "decomposition",
            "estimate": point,
            "ci95": reported_ci(draws, n_boot),
            "p": None if point is None else p_from_draws(draws - (0 if name == "gap_raw" else (d_raw or 0))),
            "n": int(n),
            "effect_size": point,
            "effect_size_kind": "cohens_d",
            "effect_size_flag": effect_flag(None if point is None else float(point)),
            "in_bh_family": point is not None and name != "gap_raw",
            "source": "pass4",
            "holdout_same_sign": None,
            "note": "Residual within-cohort d of first-year merge rate. The raw gap is the reference, not a second hypothesis.",
        })
    # p above for residual tests is awkward (draws - d_raw). Recompute p as whether residual d differs from 0,
    # and report the reduction separately. A residual of 0 would mean the block closed the gap.
    for t, draws in zip(tests[-4:], (boot_raw, boot_t, boot_s, boot_both)):
        if t["id"] == "gap_raw":
            t["in_bh_family"] = False
            t["p"] = None
        else:
            t["p"] = p_from_draws(draws)
            t["in_bh_family"] = t["estimate"] is not None

    logger.info("logistic")
    joint_keys = ["T2c_merge_rate", "prior_pr_count"] + T_MODEL_KEYS + S_PREDICTORS
    logistic = fit_logistic(train_rows, joint_keys, rng, n_boot)
    logistic_hold = fit_logistic(hold_rows, joint_keys, rng, 0) if len(hold_rows) >= 30 else None
    if logistic is None:
        unavailable(missing, "logistic_g1", "the joint logistic did not fit on 2010-2023")
    else:
        if logistic_hold is None:
            unavailable(missing, "logistic_holdout", "the 2024-2026 joint logistic did not fit, so coefficient signs were not confirmed")
        for name, coef in logistic["coefficients"].items():
            if name.endswith("_missing"):
                continue
            hold_est = None
            if logistic_hold and name in logistic_hold["coefficients"]:
                hold_est = logistic_hold["coefficients"][name]["estimate"]
            same = None if hold_est is None or coef["estimate"] is None else bool(np.sign(hold_est) == np.sign(coef["estimate"]))
            family = coef["p"] is not None and name != "prior_pr_count"
            tests.append({
                "id": "logit_" + name,
                "block": "S" if name.startswith("S") else "T",
                "estimate": coef["estimate"],
                "ci95": coef["ci95"],
                "p": coef["p"],
                "n": coef["n"],
                "effect_size": coef["estimate"],
                "effect_size_kind": "standardized_log_odds",
                "effect_size_flag": None,
                "in_bh_family": family,
                "source": "pass4",
                "holdout_estimate": hold_est,
                "holdout_same_sign": same,
                "low_observability": name.startswith("S5"),
                "note": "Logistic of later top-20 entry. Predictors are standardized. Cohort fixed effects are included. Missing review-object measures use a missingness indicator and are not filled with zero as if they were real zeros.",
            })

    logger.info("false negatives")
    fn = false_negatives(train_rows, rng, n_boot)
    fn_content = false_negatives(train_rows, rng, n_boot, keys=CONTENT_KEYS)
    fn["content_only"] = {
        "n_false_negative": fn_content.get("n_false_negative"),
        "n_g2": fn_content.get("n_g2"),
        "s_difference": fn_content.get("s_difference"),
        "cohens_d": fn_content.get("cohens_d"),
        "effect_size_flag": fn_content.get("effect_size_flag"),
        "q": None,
        "reading": fn_content.get("reading"),
        "note": "Same quartile rule, using patch-content measures only. Excludes review tone, top-5 ACKs, review cycles, and the merge rate, so a leaver is not counted as technically strong for having already been received well.",
    }
    if fn.get("n_g2_in_g1_top_quartile") and fn.get("s_difference") is not None:
        tests.append({
            "id": "false_negative_S_vs_G1",
            "block": "S",
            "estimate": fn["s_difference"],
            "ci95": fn.get("s_difference_ci"),
            "p": fn.get("p"),
            "n": fn["n_false_negative"],
            "effect_size": fn.get("cohens_d"),
            "effect_size_kind": "cohens_d",
            "effect_size_flag": fn.get("effect_size_flag"),
            "in_bh_family": fn.get("p") is not None,
            "source": "pass4",
            "holdout_same_sign": None,
            "note": "S-block composite of technically strong leavers minus the G1 S composite. Negative means those leavers were less socially legible than the people who later entered.",
        })

    logger.info("capacity interaction")
    capacity = capacity_test(prs, features, ack_hit, mentions, rng, n_boot, missing, tests)

    logger.info("BH family")
    prior = collect_prior_tests(findings, missing)
    prior3 = collect_pass3(findings, missing)
    all_family = apply_family_q(prior, prior3, tests)
    q_by_id = {t["id"]: t.get("q") for t in tests}
    for row in comparisons:
        row["q"] = q_by_id.get(row["id"])
    if logistic:
        for t in tests:
            ident_name = str(t["id"])
            if ident_name.startswith("logit_"):
                slot = logistic["coefficients"].get(ident_name[len("logit_"):])
                if slot is not None:
                    slot["q"] = t.get("q")
    fn["q"] = q_by_id.get("false_negative_S_vs_G1")
    if capacity.get("predictors"):
        confirmed = []
        for name, pred in capacity["predictors"].items():
            if not isinstance(pred, dict):
                continue
            pred["q"] = q_by_id.get("capacity_" + name)
            if pred.get("lower_S_when_unanswered") and pred.get("q") is not None and pred["q"] < 0.05:
                confirmed.append(name)
        capacity["predictors_with_q_below_05"] = confirmed
        capacity["silence_tracks_lower_S"] = bool(confirmed)
        shrinkage = (capacity.get("year_coefficient") or {}).get("shrinkage")
        year_shrinks = shrinkage is not None and shrinkage > 0
        if confirmed and year_shrinks:
            capacity["reading"] = (
                "Unanswered newcomer PRs are lower on " + ", ".join(confirmed)
                + " after technical controls (q<0.05), and the year slope of silence shrinks once those indicators are included. "
                "The rising silence lines up with social legibility."
            )
        elif confirmed:
            capacity["reading"] = (
                "Unanswered newcomer PRs are lower on " + ", ".join(confirmed)
                + " after technical controls (q<0.05). That is a cross-sectional social-legibility gap. "
                "The year slope of newcomer silence does not shrink when the social indicators are added, "
                "so this pass does not show that the rise in silence over time operates through social legibility."
            )
        else:
            capacity["reading"] = (
                "After technical controls and the joint q-value correction, unanswered newcomer PRs are not lower on the social indicators. "
                "This pass does not show that the rising silence operates through social legibility."
            )

    summary = render_summary(
        comparisons, decomp_rule, d_raw, d_t, d_s, d_both, d_size, d_content, d_reception,
        logistic, fn, capacity, n_ever, n_ever_authored, grouped, missing,
    )
    payload = {
        "pin": (
            "G1 later entered the rolling 24-month top 20. G2 never entered and authored no PR at or after 24 months. "
            "The pass-2 d=0.73 used the cumulative top 20. This pass recomputes the within-cohort merge gap on the rolling groups and decomposes that gap. "
            "T2c, the merge rate, is not used as a predictor of itself."
        ),
        "version": "4.0",
        "parameters": {
            "bootstrap": n_boot,
            "seed": seed,
            "train_years": "2010-2023",
            "holdout_years": "2024-2026",
            "rolling_window_days": HORIZON_DAYS[24],
            "pass2_reference_d": PASS2_REFERENCE_D,
            "pass2_reference_definition": "cumulative top 20, two-year cohorts, first-year merge rate",
        },
        "groups": {
            "n_ever_in_rolling_top20": n_ever,
            "n_ever_with_a_pr": n_ever_authored,
            "n_g1": int(sum(p["group"] == 1 for p in grouped)),
            "n_g2": int(sum(p["group"] == 0 for p in grouped)),
            "n_train": len(train_rows),
            "n_holdout": len(hold_rows),
        },
        "comparison_table": comparisons,
        "decomposition": {
            "outcome": "first-year decided-PR merge rate",
            "d_raw": d_raw,
            "d_after_size_controls": d_size,
            "d_after_T": d_t,
            "d_after_S": d_s,
            "d_after_both": d_both,
            "d_after_patch_content": d_content,
            "d_after_review_reception": d_reception,
            "share_of_raw_gap_closed_by_T": None if not d_raw else (d_raw - d_t) / d_raw if d_t is not None else None,
            "share_of_raw_gap_closed_by_S": None if not d_raw else (d_raw - d_s) / d_raw if d_s is not None else None,
            "share_of_raw_gap_closed_by_both": None if not d_raw else (d_raw - d_both) / d_raw if d_both is not None else None,
            "rule": decomp_rule,
            "t_block_excludes": ["T2c_merge_rate"],
            "s_model_controls": SIZE_CONTROLS,
            "ci95": {
                "d_raw": reported_ci(boot_raw, n_boot),
                "d_after_T": reported_ci(boot_t, n_boot),
                "d_after_S": reported_ci(boot_s, n_boot),
                "d_after_both": reported_ci(boot_both, n_boot),
                "d_after_patch_content": reported_ci(boot_content, n_boot),
                "d_after_review_reception": reported_ci(boot_reception, n_boot),
            },
        },
        "logistic": logistic,
        "logistic_holdout": logistic_hold,
        "false_negatives": fn,
        "capacity": capacity,
        "hypothesis_tests": tests,
        "prior_tests_in_family": [{"id": t["id"], "source": t["source"], "p": t["p"], "q": t.get("q")} for t in prior + prior3],
        "data_unavailable": missing,
        "plain_text_summary": summary,
        "what_this_cannot_prove": CANNOT,
    }
    return jsonable(payload)


def apply_family_q(
    prior: Sequence[Dict[str, Any]],
    pass3: Sequence[Dict[str, Any]],
    tests: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Benjamini-Hochberg across passes 1-4. Pass-4 holdout re-fits are not a second family member."""
    family = [t for t in list(prior) + list(pass3) + list(tests) if t.get("in_bh_family") and t.get("p") is not None]
    qvals = bh_qvalues([float(t["p"]) for t in family])
    for test, q in zip(family, qvals):
        test["q"] = float(q)
    for test in tests:
        test.setdefault("q", None)
    return family


def false_negatives(
    rows: Sequence[Dict[str, Any]],
    rng: np.random.Generator,
    n_boot: int,
    keys: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    g1 = [r for r in rows if r["group"] == 1]
    g2 = [r for r in rows if r["group"] == 0]
    if len(g1) < 8 or len(g2) < 8:
        return {"status": "DATA UNAVAILABLE", "reason": "fewer than 8 people in a group", "n_false_negative": 0}
    wanted = list(keys) if keys is not None else T_GAP_BLOCK + ["T2c_merge_rate"]
    keys = [k for k in wanted if np.isfinite(column(g1, k)).sum() >= 5]
    def composite(sample: Sequence[Dict[str, Any]], orient_from: Sequence[Dict[str, Any]], variables: Sequence[str]) -> np.ndarray:
        parts = []
        for key in variables:
            base = column(orient_from, key)
            base = base[np.isfinite(base)]
            if base.size < 5 or float(np.std(base)) < 1e-12:
                continue
            direction = 1.0 if float(np.nanmean(column(g1, key))) >= float(np.nanmean(column(g2, key))) else -1.0
            vals = column(sample, key)
            z = direction * (vals - float(base.mean())) / float(base.std())
            parts.append(z)
        if not parts:
            return np.full(len(sample), np.nan)
        stacked = np.vstack(parts)
        with np.errstate(all="ignore"):
            return np.nanmean(stacked, axis=0)
    t_g1 = composite(g1, g1, keys)
    t_g2 = composite(g2, g1, keys)
    finite = t_g1[np.isfinite(t_g1)]
    if finite.size < 8:
        return {"status": "DATA UNAVAILABLE", "reason": "T composite was undefined", "n_false_negative": 0}
    cutoff = float(np.quantile(finite, 0.75))
    fn_mask = np.isfinite(t_g2) & (t_g2 >= cutoff)
    fn_rows = [g2[i] for i in np.flatnonzero(fn_mask)]
    s_keys = S_PREDICTORS
    s_g1 = composite(g1, g1, s_keys)
    s_fn = composite(fn_rows, g1, s_keys) if fn_rows else np.array([])
    d = cohens_d(s_fn, s_g1) if s_fn.size >= 2 else None
    fn_ok = s_fn[np.isfinite(s_fn)] if s_fn.size else np.array([])
    g1_ok = s_g1[np.isfinite(s_g1)]
    draws = np.full(n_boot, np.nan)
    if fn_ok.size >= 2 and g1_ok.size >= 2:
        for i in range(n_boot):
            a = fn_ok[rng.integers(0, fn_ok.size, fn_ok.size)]
            b = g1_ok[rng.integers(0, g1_ok.size, g1_ok.size)]
            draws[i] = float(np.mean(a) - np.mean(b))
    diff = float(np.mean(fn_ok) - np.mean(g1_ok)) if fn_ok.size and g1_ok.size else None
    flag = effect_flag(d)
    if diff is not None and diff < 0 and not str(flag).startswith("negligible"):
        reading = (
            "Technically strong leavers score lower on the social composite than later top-20 entrants. "
            "That is the high false-negative pattern: first-year technical signal in the top quarter of the entrant distribution, without the social signal, and gone by 24 months."
        )
    elif diff is not None and diff < 0:
        reading = (
            "Technically strong leavers score lower on the social composite, but the difference is negligible in size."
        )
    else:
        reading = (
            "Technically strong leavers do not score lower on the social composite than later entrants, so the false-negative pattern is not supported."
        )
    return {
        "status": "ok",
        "t_cutoff_g1_top_quartile": cutoff,
        "n_g1": len(g1),
        "n_g2": len(g2),
        "n_false_negative": int(fn_mask.sum()),
        "n_g2_in_g1_top_quartile": int(fn_mask.sum()),
        "false_negative_entry_years": [int(row["year"]) for row in fn_rows],
        "leaver_entry_years": [int(row["year"]) for row in g2],
        "false_negative_share_of_g2": float(fn_mask.sum() / len(g2)),
        "s_mean_false_negative": None if not fn_ok.size else float(np.mean(fn_ok)),
        "s_mean_g1": float(np.mean(g1_ok)) if g1_ok.size else None,
        "s_difference": diff,
        "s_difference_ci": reported_ci(draws, n_boot),
        "cohens_d": d,
        "effect_size_flag": flag,
        "p": None if fn_ok.size < 2 else p_from_draws(draws),
        "low_s_relative_to_g1": bool(diff is not None and diff < 0),
        "reading": reading,
    }


def capacity_test(prs, features, ack_hit, mentions, rng, n_boot, missing, tests) -> Dict[str, Any]:
    del ack_hit  # ACK receipt is a consequence of getting a response, so it is not a silence control.
    author_row = {row["author"]: row for row in features}
    records = []
    for i, author in enumerate(prs["author"].tolist()):
        row = author_row.get(str(author))
        if row is None:
            continue
        if float(prs["created"][i]) > float(row["first"]) + YEAR:
            continue
        records.append(i)
    if len(records) < 50:
        unavailable(missing, "capacity", "fewer than 50 newcomer PRs from grouped contributors")
        return {"status": "DATA UNAVAILABLE", "reading": "DATA UNAVAILABLE"}
    idx = np.asarray(records, dtype=int)
    train = prs["year"][idx] <= TRAIN_LAST
    idx_t = idx[train]
    y = prs["no_response"][idx_t].astype(float)
    authors = prs["author"][idx_t]
    s1 = np.asarray([
        1.0 if any(ts <= float(prs["created"][i]) + 7 * DAY for ts in mentions.get(int(prs["number"][i]), [])) else 0.0
        for i in idx_t
    ])
    def person_col(key: str) -> np.ndarray:
        return np.asarray([author_row[str(a)][key] if str(a) in author_row else np.nan for a in authors], dtype=float)
    predictors = {
        "S1_irc_linked": s1,
        "S2_jargon_share": person_col("S2_jargon_share"),
        "S3_reviews_before_first": person_col("S3_reviews_before_first"),
        "S4_early_reciprocity": person_col("S4_early_reciprocity"),
        "S5_named_by_top20": person_col("S5_named_by_top20"),
    }
    t_cols = {
        "consensus": prs["consensus"][idx_t].astype(float),
        "test_only": prs["test_only"][idx_t].astype(float),
        "bugfix": prs["bugfix"][idx_t].astype(float),
        "log_lines": np.log1p(prs["lines"][idx_t]),
        "files": prs["files"][idx_t].astype(float),
        "prior": _prior_at(prs, idx_t),
    }
    years = prs["year"][idx_t].astype(float)
    results = {}
    for name, values in predictors.items():
        cols = [values, t_cols["consensus"], t_cols["test_only"], t_cols["bugfix"], t_cols["log_lines"], t_cols["files"], t_cols["prior"]]
        mask = np.isfinite(y) & np.isfinite(years)
        for col in cols:
            mask &= np.isfinite(col)
        if int(mask.sum()) < 40 or np.unique(y[mask]).size < 2:
            unavailable(missing, "capacity_" + name, "the newcomer silence model did not have enough complete rows")
            results[name] = {"status": "DATA UNAVAILABLE"}
            continue
        x_mat = design_matrix(years[mask], [c[mask] for c in cols])
        beta = logistic_irls(x_mat, y[mask])
        # The S predictor is the first standardized column after the intercept and year dummies.
        n_cohort = max(int(np.unique(years[mask].astype(int)).size) - 1, 0)
        col_i = 1 + n_cohort
        if beta is None or beta.size <= col_i:
            unavailable(missing, "capacity_" + name, "logistic fit failed")
            results[name] = {"status": "DATA UNAVAILABLE"}
            continue
        yy = y[mask]
        authors_m = authors[mask]
        draws = _cluster_logit_draws(yy, x_mat, authors_m, col_i, rng, n_boot)
        est = float(beta[col_i])
        hold_est = _holdout_silence_coef(prs, author_row, mentions, name, idx)
        results[name] = {
            "estimate": est,
            "ci95": reported_ci(draws, n_boot),
            "p": p_from_draws(draws),
            "n": int(yy.size),
            "n_authors": int(len(set(authors_m.tolist()))),
            "lower_S_when_unanswered": bool(est < 0),
            "holdout_estimate": hold_est,
            "holdout_same_sign": None if hold_est is None else bool(np.sign(hold_est) == np.sign(est)),
        }
        tests.append({
            "id": "capacity_" + name,
            "block": "capacity",
            "estimate": est,
            "ci95": results[name]["ci95"],
            "p": results[name]["p"],
            "n": int(yy.size),
            "effect_size": est,
            "effect_size_kind": "standardized_log_odds",
            "effect_size_flag": None,
            "in_bh_family": True,
            "source": "pass4",
            "holdout_estimate": results[name]["holdout_estimate"],
            "holdout_same_sign": results[name]["holdout_same_sign"],
            "low_observability": name.startswith("S5"),
            "note": "Logistic of no peer response on newcomer PRs. Negative means unanswered PRs are lower on this social indicator after consensus/test/bugfix and the shared size and prior-PR controls. Year fixed effects are included.",
        })
    answered_lower = [k for k, v in results.items() if isinstance(v, dict) and v.get("lower_S_when_unanswered") and v.get("p") is not None and v["p"] < 0.05]
    year_model = _year_mediation(y, years, t_cols, predictors)
    return {
        "status": "ok",
        "predictors": results,
        "silence_tracks_lower_S": bool(answered_lower),
        "predictors_with_uncorrected_p_below_05": answered_lower,
        "year_coefficient": year_model,
        "reading": (
            "Unanswered newcomer PRs are lower on at least one social indicator after technical controls. "
            "Selectivity lines up with social legibility, not with the technical file and size measures in the model."
            if answered_lower
            else "After technical controls, unanswered newcomer PRs are not reliably lower on the social indicators. "
            "This pass does not show that the rising silence operates through social legibility."
        ),
    }


def _cluster_logit_draws(y, x_mat, authors, col_i, rng, n_boot):
    buckets: Dict[str, List[int]] = defaultdict(list)
    for i, author in enumerate(authors.tolist()):
        buckets[str(author)].append(i)
    groups = [np.asarray(ix, dtype=int) for ix in buckets.values()]
    draws = np.full(n_boot, np.nan)
    if len(groups) < 8:
        return draws
    for b in range(n_boot):
        chosen = rng.integers(0, len(groups), len(groups))
        take = np.concatenate([groups[j] for j in chosen])
        if np.unique(y[take]).size < 2:
            continue
        beta = logistic_irls(x_mat[take], y[take])
        if beta is not None and beta.size > col_i:
            draws[b] = float(beta[col_i])
    return draws


def _holdout_silence_coef(prs, author_row, mentions, name, idx):
    hold = idx[prs["year"][idx] >= HOLDOUT_FIRST]
    if hold.size < 40:
        return None
    y = prs["no_response"][hold].astype(float)
    if np.unique(y).size < 2:
        return None
    authors = prs["author"][hold]
    if name == "S1_irc_linked":
        social = np.asarray([
            1.0 if any(ts <= float(prs["created"][i]) + 7 * DAY for ts in mentions.get(int(prs["number"][i]), [])) else 0.0
            for i in hold
        ])
    else:
        social = np.asarray([author_row[str(a)].get(name, np.nan) for a in authors], dtype=float)
    cols = [
        social,
        prs["consensus"][hold].astype(float),
        prs["test_only"][hold].astype(float),
        prs["bugfix"][hold].astype(float),
        np.log1p(prs["lines"][hold]),
        prs["files"][hold].astype(float),
        _prior_at(prs, hold),
    ]
    years = prs["year"][hold].astype(float)
    mask = np.isfinite(y) & np.isfinite(years)
    for col in cols:
        mask &= np.isfinite(col)
    if int(mask.sum()) < 30 or np.unique(y[mask]).size < 2 or float(np.std(social[mask])) < 1e-12:
        return None
    x_mat = design_matrix(years[mask], [c[mask] for c in cols])
    beta = logistic_irls(x_mat, y[mask])
    col_i = 1 + max(int(np.unique(years[mask].astype(int)).size) - 1, 0)
    if beta is None or beta.size <= col_i:
        return None
    return float(beta[col_i])


def _year_mediation(y, years, t_cols, predictors):
    """Does the newcomer-silence year slope shrink once social indicators are in the model?"""
    pieces = [
        years.astype(float) - 2010.0,
        t_cols["log_lines"], t_cols["files"], t_cols["prior"],
        t_cols["consensus"], t_cols["test_only"], t_cols["bugfix"],
    ]
    mask = np.isfinite(y)
    for col in pieces:
        mask &= np.isfinite(col)
    social = []
    for values in predictors.values():
        observed = values[np.isfinite(values)]
        if observed.size < 8 or float(np.std(observed)) < 1e-12:
            continue
        z = (values - float(observed.mean())) / float(observed.std())
        social.append(np.where(np.isfinite(z), z, 0.0))
    if int(mask.sum()) < 40 or not social:
        return None

    def pack(extra):
        cols = [np.ones(int(mask.sum()))]
        for col in pieces:
            c = col[mask].astype(float)
            sd = float(np.std(c))
            cols.append((c - float(np.mean(c))) / sd if sd > 1e-12 else np.zeros(c.size))
        for col in extra:
            cols.append(col[mask])
        return np.column_stack(cols)

    without = np.linalg.lstsq(pack([]), y[mask], rcond=1e-8)[0]
    with_s = np.linalg.lstsq(pack(social), y[mask], rcond=1e-8)[0]
    if without.size < 2 or with_s.size < 2 or not np.isfinite(without[1]) or not np.isfinite(with_s[1]):
        return None
    return {
        "standardized_year_without_S": float(without[1]),
        "standardized_year_with_S": float(with_s[1]),
        "shrinkage": float(without[1] - with_s[1]),
        "note": "Linear probability of no peer response. Year is standardized the same way in both fits. A smaller coefficient after S is consistent with social legibility carrying part of the time trend. It is not a causal mediation claim.",
    }


def _prior_at(prs, idx: np.ndarray) -> np.ndarray:
    prior = np.zeros(idx.size, dtype=float)
    counts: Dict[str, int] = defaultdict(int)
    order = np.argsort(prs["created"], kind="mergesort")
    rank = np.empty(prs["created"].size, dtype=int)
    for position, i in enumerate(order):
        author = str(prs["author"][i])
        rank[i] = counts[author]
        counts[author] += 1
    return rank[idx].astype(float)


def _test(short, key, block, fit, hold, family: bool, low: bool = False) -> Dict[str, Any]:
    if fit is None:
        return {
            "id": short, "predictor": key, "block": block, "estimate": None, "ci95": None, "p": None,
            "n": None, "effect_size": None, "effect_size_kind": "cohens_d", "effect_size_flag": None,
            "in_bh_family": False, "source": "pass4", "holdout_same_sign": None, "low_observability": low,
            "note": "DATA UNAVAILABLE",
        }
    same = None
    if hold and hold.get("estimate") is not None and fit.get("estimate") is not None:
        same = bool(np.sign(hold["estimate"]) == np.sign(fit["estimate"]))
    return {
        "id": short,
        "predictor": key,
        "block": block,
        "estimate": fit.get("estimate"),
        "ci95": fit.get("ci95"),
        "p": fit.get("p"),
        "n": fit.get("n"),
        "effect_size": fit.get("cohens_d"),
        "effect_size_kind": "cohens_d",
        "effect_size_flag": fit.get("effect_size_flag"),
        "in_bh_family": family and fit.get("p") is not None,
        "source": "pass4",
        "holdout_estimate": None if not hold else hold.get("estimate"),
        "holdout_same_sign": same,
        "low_observability": low,
        "g1_mean": fit.get("g1_mean"),
        "g2_mean": fit.get("g2_mean"),
        "note": "Cohort-year matched. Standardized difference is the cohort-FE group coefficient divided by the outcome SD, with size and prior-PR controls when those are not the outcome.",
    }


def collect_pass3(findings: Path, missing: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    path = findings / "data" / "commons_dynamics_analysis.json"
    if not path.exists():
        unavailable(missing, "pass3", "commons_dynamics_analysis.json is missing, so pass 3 tests cannot enter the BH family")
        return []
    data = json.loads(path.read_text())
    out = []
    for t in data.get("hypothesis_tests") or []:
        if t.get("source") != "pass3" or not t.get("in_bh_family") or t.get("p") is None:
            continue
        out.append({
            "id": "pass3." + str(t.get("id")),
            "estimate": t.get("estimate"),
            "ci95": t.get("ci95"),
            "p": t.get("p"),
            "q": None,
            "source": "pass3",
            "in_bh_family": True,
            "note": "p-value carried from pass 3. q is recomputed on the passes 1-4 family.",
        })
    return out


CANNOT = [
    "T and S proxies are imperfect measures of technical quality and social legibility.",
    "IRC-linked PRs are identified by number matching and miss discussions that never name the PR.",
    "G1 has on the order of 65 members and matched cohort cells are small. Treat the results as exploratory until they are replicated on comparison repositories.",
    "Social legibility and technical quality are partly correlated in any expert community. Separating them from observational data is inherently limited.",
]


def render_summary(comparisons, rule, d_raw, d_t, d_s, d_both, d_size, d_content, d_reception, logistic, fn, capacity, n_ever, n_authored, grouped, missing) -> str:
    lines = []
    lines.append("First-year signal, pass 4.")
    lines.append(
        f"Rolling top 20 ever entered: {n_ever}. Of those, {n_authored} authored a PR. "
        f"G1 (ever entered): {sum(p['group']==1 for p in grouped)}. "
        f"G2 (never entered, no PR at or after 24 months): {sum(p['group']==0 for p in grouped)}."
    )
    lines.append(
        f"Pass 2's d={PASS2_REFERENCE_D:.2f} was the cumulative top-20 merge gap. "
        f"This pass recomputes the within-cohort merge gap on the rolling groups: d={_fmt(d_raw)}."
    )
    lines.append("")
    lines.append("MATCHED PREDICTORS (G1 minus G2, 2010-2023)")
    for row in comparisons:
        if row.get("status") == "DATA UNAVAILABLE":
            lines.append(f"  {row['id']}: DATA UNAVAILABLE")
            continue
        lines.append(
            f"  {row['id']}: G1 mean {_fmt(row.get('g1_mean'))} (median {_fmt(row.get('g1_median'))}) "
            f"G2 mean {_fmt(row.get('g2_mean'))} (median {_fmt(row.get('g2_median'))}) "
            f"smd {_fmt(row.get('standardized_difference'))} d={_fmt(row.get('cohens_d'))} "
            f"({row.get('effect_size_flag')}) q={_fmt(row.get('q'))} "
            f"holdout_same_sign={row.get('holdout_same_sign')}"
        )
    lines.append("")
    lines.append("DECOMPOSITION OF THE MERGE-RATE GAP")
    lines.append(
        f"  raw d={_fmt(d_raw)}; after size and prior controls d={_fmt(d_size)}; "
        f"after T d={_fmt(d_t)}; after S d={_fmt(d_s)}; after both d={_fmt(d_both)}. "
        f"Patch content only (no review reception) leaves d={_fmt(d_content)}. "
        f"Review reception only, with size controls, leaves d={_fmt(d_reception)}."
    )
    if rule:
        lines.append("  " + rule["text"])
    else:
        lines.append("  DATA UNAVAILABLE: the decision rule did not have all four d values.")
    lines.append("")
    lines.append("FALSE NEGATIVES")
    if fn.get("status") == "DATA UNAVAILABLE":
        lines.append("  DATA UNAVAILABLE: " + str(fn.get("reason")))
    else:
        lines.append(
            f"  {fn.get('n_false_negative')} of {fn.get('n_g2')} leavers sit in the top quartile of G1's technical composite. "
            f"Their social composite minus G1 is {_fmt(fn.get('s_difference'))} (d={_fmt(fn.get('cohens_d'))}, {fn.get('effect_size_flag')})."
        )
        lines.append("  " + str(fn.get("reading")))
        content_fn = fn.get("content_only") or {}
        if content_fn.get("n_false_negative") is not None:
            lines.append(
                "  Patch-content quartile only, excluding ACKs, tone, review cycles, and the merge rate: "
                f"{content_fn.get('n_false_negative')} of {content_fn.get('n_g2')} leavers. "
                f"Their social composite minus G1 is {_fmt(content_fn.get('s_difference'))} "
                f"(d={_fmt(content_fn.get('cohens_d'))}, {content_fn.get('effect_size_flag')})."
            )
    lines.append("")
    lines.append("CAPACITY")
    lines.append("  " + str(capacity.get("reading")))
    year_model = capacity.get("year_coefficient") or {}
    if year_model:
        lines.append(
            "  Newcomer silence year slope, technical controls only: "
            f"{_fmt(year_model.get('standardized_year_without_S'))}. "
            f"After social indicators: {_fmt(year_model.get('standardized_year_with_S'))} "
            f"(shrinkage {_fmt(year_model.get('shrinkage'))})."
        )
    lines.append("")
    if logistic and logistic.get("coefficients"):
        lines.append("JOINT LOGISTIC COEFFICIENTS WITH q<0.05")
        coefs = [
            (k, v) for k, v in logistic["coefficients"].items()
            if not k.endswith("_missing") and v.get("q") is not None and v["q"] < 0.05 and v.get("estimate") is not None
        ]
        coefs.sort(key=lambda kv: abs(kv[1]["estimate"]), reverse=True)
        if not coefs:
            lines.append("  None. Individual coefficients are collinear; use the block residuals.")
        for name, coef in coefs:
            lines.append(f"  {name}: {coef['estimate']:.3f} (q={_fmt(coef.get('q'))})")
        lines.append("  T3a and T3b count nearly the same directories, so their separate logistic coefficients are not identified.")
        lines.append("")
    lines.append("WHAT THIS CANNOT PROVE")
    for i, text in enumerate(CANNOT, start=1):
        lines.append(f"  ({i}) {text}")
    lines.append("")
    n_unavail = sum(1 for item in missing if item.get("status") == "DATA UNAVAILABLE")
    lines.append(f"DATA UNAVAILABLE entries: {n_unavail}.")
    return "\n".join(lines)


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        if not np.isfinite(float(value)):
            return "n/a"
    except (TypeError, ValueError):
        return "n/a"
    return f"{float(value):.3f}"


def main() -> None:
    parser = argparse.ArgumentParser(description="First-year technical versus social signal")
    parser.add_argument("--bootstrap", type=int, default=N_BOOT)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    payload = analyze(n_boot=args.bootstrap, seed=args.seed)
    paths = save_analysis_json("first_year_signal_analysis.json", payload)
    print(payload["plain_text_summary"])
    for path in paths:
        logger.info("wrote %s", path)


if __name__ == "__main__":
    main()
