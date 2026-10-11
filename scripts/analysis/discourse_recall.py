#!/usr/bin/env python3
"""Recall from path links, then the silence, discussion, and E12 sensitivity reruns.

Symbol matches need patch text. The enriched pull requests store filenames only,
so symbols are DATA UNAVAILABLE on the bulk scan. The linker still accepts
symbols when a caller supplies them.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import numpy as np

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from scripts.analysis.commons_dynamics_test import (  # noqa: E402
    DAY,
    TOP_N,
    WINDOW,
    SlidingTop,
    fit_split,
)
from scripts.analysis.comparison_effects import _family  # noqa: E402
from scripts.analysis.discourse_path_linking import (  # noqa: E402
    PullWindow,
    index_pulls,
    link_message,
    path_only_hits,
    pr_path_tokens,
)
from scripts.analysis.first_year_signal_test import (  # noqa: E402
    N_BOOT,
    SEED,
    capacity_test,
    load_analysis_frame,
    parse_ts,
)
from src.utils.findings_io import save_analysis_json  # noqa: E402
from src.utils.paths import get_data_dir, get_findings_dir  # noqa: E402

PRECISION_HEADLINE = 0.7
SAMPLE_N = 200


def load_pull_windows(path: Path) -> Tuple[List[PullWindow], float]:
    rows = []
    data_end = 0.0
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip():
                continue
            pr = json.loads(line)
            opened = parse_ts(pr.get("created_at"))
            if opened is None:
                continue
            closed = parse_ts(pr.get("closed_at")) or parse_ts(pr.get("merged_at"))
            data_end = max(data_end, opened, closed or 0.0)
            files = []
            for item in pr.get("files") or []:
                if isinstance(item, dict) and item.get("filename"):
                    files.append(item["filename"])
            try:
                number = int(pr.get("number") or 0)
            except (TypeError, ValueError):
                continue
            if number <= 0:
                continue
            rows.append((number, opened, closed, pr_path_tokens(files), str(pr.get("title") or "")[:180]))
    pulls = []
    for number, opened, closed, paths, title in rows:
        end = closed if closed is not None else data_end
        pulls.append(PullWindow(number, opened, end, paths, set(), title))
    return pulls, data_end


def _iter_messages(data_dir: Path) -> Iterable[Tuple[str, str, float]]:
    specs = [
        ("irc", data_dir / "irc" / "messages.jsonl", ("message",), ("timestamp", "time")),
        ("mail", data_dir / "mailing_lists" / "emails.jsonl", ("subject", "body"), ("date",)),
        ("delving", data_dir / "delving" / "posts.jsonl", ("content",), ("created_at",)),
        ("bitcointalk", data_dir / "bitcointalk" / "posts.jsonl", ("title", "content"), ("date",)),
    ]
    for channel, path, text_keys, ts_keys in specs:
        if not path.exists():
            continue
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = None
                for key in ts_keys:
                    ts = parse_ts(row.get(key))
                    if ts is not None:
                        break
                if ts is None:
                    continue
                text = "\n".join(str(row.get(key) or "") for key in text_keys)
                if text.strip():
                    yield channel, text, ts


class Reservoir:
    def __init__(self, k: int, rng: np.random.Generator) -> None:
        self.k = k
        self.rng = rng
        self.seen = 0
        self.rows: List[Dict[str, Any]] = []

    def add(self, row: Dict[str, Any]) -> None:
        self.seen += 1
        if len(self.rows) < self.k:
            self.rows.append(row)
            return
        j = int(self.rng.integers(0, self.seen))
        if j < self.k:
            self.rows[j] = row


def scan(data_dir: Path, rng: np.random.Generator, sample_n: int = SAMPLE_N) -> Dict[str, Any]:
    enriched = data_dir / "processed" / "enriched_prs.jsonl"
    if not enriched.exists():
        return {"status": "DATA UNAVAILABLE", "reason": "enriched_prs.jsonl is missing, so file paths are unknown"}
    pulls, data_end = load_pull_windows(enriched)
    by_token = index_pulls(pulls)
    by_number = {pull.number: pull for pull in pulls}
    number_prs: Set[int] = set()
    path_prs: Set[int] = set()
    s1_path: Set[int] = set()
    reservoir = Reservoir(sample_n, rng)
    n_messages = 0
    n_path_hits = 0
    for channel, text, ts in _iter_messages(data_dir):
        n_messages += 1
        numbered, hits = link_message(text, ts, pulls, by_token, set())
        for num in numbered:
            if num in by_number:
                number_prs.add(num)
        fresh = path_only_hits(numbered, hits)
        if not fresh:
            continue
        n_path_hits += len(fresh)
        snippet = " ".join(text.split())[:280]
        for num in sorted(fresh):
            path_prs.add(num)
            pull = by_number[num]
            if pull.opened <= ts <= pull.opened + 7 * DAY:
                s1_path.add(num)
            reservoir.add({
                "channel": channel,
                "pr": num,
                "title": pull.title,
                "text": snippet,
                "label": None,
            })
    gained = path_prs - number_prs
    n_prs = len(pulls)
    return {
        "status": "ok",
        "n_prs": n_prs,
        "n_messages": n_messages,
        "n_path_hit_pairs": n_path_hits,
        "n_number_prs": len(number_prs),
        "n_path_prs": len(path_prs),
        "n_gained_prs": len(gained),
        "recall_gain_share": (len(gained) / n_prs) if n_prs else None,
        "number_prs": number_prs,
        "path_prs": path_prs,
        "s1_path_prs": s1_path,
        "sample": reservoir.rows,
        "sample_population": reservoir.seen,
        "data_end": data_end,
        "symbols": "DATA UNAVAILABLE: enriched pull requests store filenames, not patch text, so symbols the pull request touches are not in the bulk scan.",
    }


def precision_from_labels(sample: List[Dict[str, Any]]) -> Dict[str, Any]:
    labeled = [row for row in sample if row.get("label") in ("true", "false")]
    if len(labeled) < SAMPLE_N:
        return {
            "status": "DATA UNAVAILABLE",
            "reason": f"{len(labeled)} of {SAMPLE_N} candidate links are labeled",
            "n": len(labeled),
            "precision": None,
        }
    n_true = sum(1 for row in labeled if row["label"] == "true")
    return {
        "status": "ok",
        "n": len(labeled),
        "n_true": n_true,
        "precision": n_true / len(labeled),
        "headline": "number_match" if (n_true / len(labeled)) < PRECISION_HEADLINE else "combined",
    }


def _mentions_from_prs(prs: Set[int], created_by_number: Dict[int, float]) -> Dict[int, List[float]]:
    """A timestamp inside the seven-day S1 window, only so the existing S1 test can see the link."""
    return {num: [created_by_number[num]] for num in prs if num in created_by_number}


def rerun_s1(frame: Dict[str, Any], extra_prs: Set[int], rng: np.random.Generator, n_boot: int) -> Dict[str, Any]:
    from scripts.analysis.first_year_signal_test import irc_mentions

    prs = frame["prs"]
    wanted = {int(n) for n in prs["number"].tolist() if int(n) > 0}
    irc_path = get_data_dir() / "irc" / "messages.jsonl"
    base_mentions = irc_mentions(irc_path, wanted) if irc_path.exists() else {}
    created_by_number = {int(n): float(t) for n, t in zip(prs["number"].tolist(), prs["created"].tolist())}
    extra = _mentions_from_prs(extra_prs, created_by_number)
    combined: Dict[int, List[float]] = defaultdict(list)
    for num, times in base_mentions.items():
        combined[num].extend(times)
    for num, times in extra.items():
        combined[num].extend(times)
    missing: List[Dict[str, str]] = []
    tests: List[Dict[str, Any]] = []
    number_only = capacity_test(prs, frame["features"], None, base_mentions, rng, n_boot, missing, tests)
    tests_combined: List[Dict[str, Any]] = []
    both = capacity_test(prs, frame["features"], None, combined, np.random.default_rng(SEED), n_boot, missing, tests_combined)
    return {
        "number_only": (number_only.get("predictors") or {}).get("S1_irc_linked"),
        "combined": (both.get("predictors") or {}).get("S1_irc_linked"),
        "s3_reviews_before_first": (number_only.get("predictors") or {}).get("S3_reviews_before_first"),
        "s3_note": (
            "S3_reviews_before_first counts reviews given before the first pull request. "
            "It does not read discourse links, so the path linker leaves it unchanged."
        ),
        "missing": missing,
    }


def rerun_e12(frame: Dict[str, Any], discourse_prs: Set[int], seed: int, n_boot: int) -> Dict[str, Any]:
    """Published E12 is GitHub peer silence. The combined outcome also treats a discourse link as a response."""
    from bisect import bisect_left

    prs = frame["prs"]
    n = prs["created"].size
    created = prs["created"]
    order = np.argsort(created, kind="mergesort")
    numbers = [int(x) for x in prs["number"].tolist()]
    merged_at = _merged_at_by_number(get_data_dir() / "processed" / "enriched_prs.jsonl", set(numbers))
    first: Dict[str, float] = {}
    tenure = np.zeros(n)
    for i in order:
        author = str(prs["author"][i])
        if author not in first:
            first[author] = float(created[i])
        tenure[i] = (float(created[i]) - first[author]) / (365.25 * DAY)
    prior = np.zeros(n)
    by_author: Dict[str, List[int]] = defaultdict(list)
    for i in order:
        by_author[str(prs["author"][i])].append(int(i))
    for idxs in by_author.values():
        times = sorted(
            merged_at[numbers[i]]
            for i in idxs
            if prs["merged"][i] and numbers[i] in merged_at and merged_at[numbers[i]] is not None
        )
        for i in idxs:
            prior[i] = bisect_left(times, float(created[i]))
    people: Dict[str, int] = {}

    def pid(name: str) -> int:
        if name not in people:
            people[name] = len(people)
        return people[name]

    raw_events = [(float(ts), pid(str(reviewer))) for ts, reviewer in prs["review_events"]]
    slider = SlidingTop(raw_events, WINDOW, TOP_N)
    ingroup = np.full(n, np.nan)
    unidentified = np.zeros(n)
    authors = [pid(str(a)) for a in prs["author"].tolist()]
    for i in order:
        slider.advance(float(created[i]))
        flag = slider.contains(authors[int(i)])
        if flag is None:
            unidentified[i] = 1.0
            ingroup[i] = 0.0
        else:
            ingroup[i] = 1.0 if flag else 0.0
    linked = np.asarray([1.0 if num in discourse_prs else 0.0 for num in numbers])
    y_base = prs["no_response"].astype(float)
    y_plus = np.where((y_base == 1.0) & (linked == 0.0), 1.0, 0.0)
    log_lines = np.log1p(prs["lines"].astype(float))
    files = prs["files"].astype(float)
    years = prs["year"].astype(float)
    cov = [log_lines, files, tenure, prior, unidentified]
    base_train, base_hold = fit_split(y_base, ingroup, cov, years, np.random.default_rng(seed), n_boot, True)
    plus_train, plus_hold = fit_split(y_plus, ingroup, cov, years, np.random.default_rng(seed), n_boot, True)

    def pack(train, hold):
        if train is None:
            return {"status": "DATA UNAVAILABLE", "estimate": None, "ci95": None, "p": None, "n": None}
        hold_est = None if hold is None else hold.get("estimate")
        estimate = train.get("estimate")
        return {
            "status": "ok",
            "estimate": estimate,
            "ci95": train.get("ci95"),
            "p": train.get("p"),
            "n": train.get("n"),
            "holdout_estimate": hold_est,
            "holdout_same_sign": None if hold_est is None or estimate is None else bool(np.sign(hold_est) == np.sign(estimate)),
        }

    return {"number_only_github_silence": pack(base_train, base_hold), "combined_linker": pack(plus_train, plus_hold)}


def discussion_shift(enriched: Path, number_any: Set[int], path_prs: Set[int]) -> Dict[str, Any]:
    """discussion_observed with the published number set, then with path links added."""
    from scripts.analysis.revealed_rough_consensus import pr_consensus_vector

    counts = {
        "before_2016": {"n": 0, "number": 0, "combined": 0},
        "from_2016": {"n": 0, "number": 0, "combined": 0},
    }
    with enriched.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip():
                continue
            pr = json.loads(line)
            opened = parse_ts(pr.get("created_at"))
            if opened is None:
                continue
            try:
                number = int(pr.get("number") or 0)
            except (TypeError, ValueError):
                continue
            vec = pr_consensus_vector(pr, set(), set())
            github_or_peer = bool(vec.get("discussion_observed"))
            number_obs = github_or_peer or number in number_any
            combined_obs = number_obs or number in path_prs
            era = "before_2016" if opened < 1451606400 else "from_2016"  # 2016-01-01 UTC
            counts[era]["n"] += 1
            counts[era]["number"] += int(number_obs)
            counts[era]["combined"] += int(combined_obs)
    out = {}
    for era, row in counts.items():
        n = row["n"]
        out[era] = {
            "n": n,
            "number_only_share": None if n == 0 else row["number"] / n,
            "combined_share": None if n == 0 else row["combined"] / n,
            "gain": None if n == 0 else (row["combined"] - row["number"]) / n,
        }
    return out


def _public_scan(raw: Dict[str, Any]) -> Dict[str, Any]:
    keep = {k: v for k, v in raw.items() if k not in {"number_prs", "path_prs", "s1_path_prs", "sample"}}
    return keep


def _published_test(path: Path, test_id: str) -> Dict[str, Any]:
    if not path.exists():
        return {"status": "DATA UNAVAILABLE", "reason": f"{path.name} is missing"}
    payload = json.loads(path.read_text())
    rows = payload.get("hypothesis_tests") or []
    for row in rows:
        if row.get("id") == test_id:
            return {
                "status": "ok",
                "id": test_id,
                "estimate": row.get("estimate"),
                "ci95": row.get("ci95"),
                "p": row.get("p"),
                "n": row.get("n"),
            }
    return {"status": "DATA UNAVAILABLE", "reason": f"{test_id} is not in {path.name}"}


def _published_comparison(findings: Path, s1: Dict[str, Any], e12: Dict[str, Any]) -> Dict[str, Any]:
    published_s1 = _published_test(findings / "data" / "first_year_signal_analysis.json", "capacity_S1_irc_linked")
    published_e12 = _published_test(findings / "data" / "commons_dynamics_analysis.json", "E12_ingroup_on_no_peer_response")
    number_s1 = (s1.get("number_only") or {}).get("estimate")
    number_e12 = (e12.get("number_only_github_silence") or {}).get("estimate")

    def same_point(left, right) -> Optional[bool]:
        if left is None or right is None:
            return None
        return abs(float(left) - float(right)) < 1e-9

    return {
        "s1": published_s1,
        "s1_number_only_point_matches_published": same_point(number_s1, published_s1.get("estimate")),
        "e12": published_e12,
        "e12_number_only_point_matches_published": same_point(number_e12, published_e12.get("estimate")),
        "note": (
            "The number-only S1 point estimate is the published capacity fit. "
            "Its interval in this file is a fresh seed-7 bootstrap, not the draws already consumed by the pass-4 script. "
            "The published interval remains the headline. "
            "The number-only E12 column is a refit on the first-year frame. The published E12 estimate stays in the pass-3 file."
        ),
    }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Path-link discourse recall and the sensitivity reruns")
    parser.add_argument("--bootstrap", type=int, default=N_BOOT)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--scan-only", action="store_true")
    args = parser.parse_args()
    findings = get_findings_dir()
    data_dir = get_data_dir()
    rng = np.random.default_rng(args.seed)
    print("scanning discourse", flush=True)
    raw = scan(data_dir, rng)
    if raw.get("status") != "ok":
        print(raw, flush=True)
        return 2
    sample_path = findings / "data" / "discourse_path_sample.json"
    sample_path.parent.mkdir(parents=True, exist_ok=True)
    labels_path = findings / "data" / "discourse_path_labels.json"
    sample = raw["sample"]
    labeled_rows = [{**row, "i": i} for i, row in enumerate(sample)]
    if labels_path.exists():
        saved = json.loads(labels_path.read_text())
        by_key = {
            (row.get("channel"), int(row.get("pr") or 0), row.get("text")): row.get("label")
            for row in saved
        }
        for row in labeled_rows:
            row["label"] = by_key.get((row["channel"], int(row["pr"]), row["text"]))
        for i, row in enumerate(sample):
            row["label"] = labeled_rows[i]["label"]
    sample_path.write_text(json.dumps(labeled_rows, indent=2))
    judged = precision_from_labels(sample)
    print(f"path prs {raw['n_path_prs']} gained {raw['n_gained_prs']} precision {judged.get('precision')}", flush=True)
    if args.scan_only or judged.get("status") != "ok":
        payload = {
            "status": "LABELS_REQUIRED" if judged.get("status") != "ok" else "scan",
            "scan": _public_scan(raw),
            "precision": judged,
            "symbols": raw.get("symbols"),
        }
        save_analysis_json("discourse_recall.json", payload)
        return 0 if args.scan_only else 2
    print("loading first-year frame", flush=True)
    missing: List[Dict[str, str]] = []
    frame = load_analysis_frame(missing)
    from scripts.analysis.revealed_rough_consensus import load_informal_pr_sets
    number_any = load_informal_pr_sets().get("any") or set()
    print("discussion rates", flush=True)
    rates = discussion_shift(data_dir / "processed" / "enriched_prs.jsonl", number_any, raw["path_prs"])
    print("S1 rerun", flush=True)
    s1 = rerun_s1(frame, raw["s1_path_prs"], np.random.default_rng(args.seed), args.bootstrap)
    print("E12 rerun", flush=True)
    e12 = rerun_e12(frame, raw["path_prs"], args.seed, args.bootstrap)
    headline = judged["headline"]
    tests = []
    for name, block in (
        ("pass6.discourse_s1_combined", s1.get("combined") or {}),
        ("pass6.discourse_e12_combined", e12.get("combined_linker") or {}),
    ):
        if block.get("p") is None or headline == "number_match":
            continue
        tests.append({
            "id": name,
            "estimate": block.get("estimate"),
            "ci95": block.get("ci95"),
            "p": block.get("p"),
            "n": block.get("n"),
            "source": "pass6",
            "in_bh_family": True,
            "low_power": (block.get("n") or 0) < 20,
            "holdout_same_sign": block.get("holdout_same_sign"),
        })
    prior_pass6 = []
    comp_path = findings / "data" / "comparison_effects.json"
    if comp_path.exists():
        for test in json.loads(comp_path.read_text()).get("hypothesis_tests") or []:
            if test.get("in_bh_family") and test.get("p") is not None:
                prior_pass6.append(test)
    family, crossed = _family(findings, missing, prior_pass6 + tests)
    for test in tests:
        match = next((row for row in family if row.get("id") == test["id"]), None)
        if match is not None:
            test["q"] = match.get("q")
    payload = {
        "version": "6.0",
        "task": 5,
        "status": "ok",
        "headline": headline,
        "precision_rule": (
            "A sampled path link is true when the message is about that pull request's change. "
            "It is false when the path is only a file that several open pull requests share, or the message is about a different change."
        ),
        "scan": _public_scan(raw),
        "precision": judged,
        "s1": {k: v for k, v in s1.items() if k != "missing"},
        "discussion_observed": rates,
        "e12": e12,
        "hypothesis_tests": tests,
        "bh_family_size": len(family),
        "bh_crossed_0_05": crossed,
        "symbols": raw.get("symbols"),
        "find_discourse": (
            "find_discourse is available. Its hits mix GitHub pull-request text with IRC lines that are already in messages.jsonl. "
            "GitHub file lists are not discourse, so the scan uses the local IRC, mail, Delving, and Bitcointalk archives."
        ),
        "published_comparison": _published_comparison(findings, s1, e12),
        "label_method": (
            "The 200 labels are one reading of the first 280 characters of each message against the stated rule. "
            "They are not a second independent coder. A sentence after those 280 characters can name the change and still be marked false."
        ),
        "precision_bar_scope": (
            "The 0.7 precision bar is the pass 6 task rule. It is not a row in pass6_preregistration.json, "
            "which records the durability signs, the size residual, and the comparison-repository correlations."
        ),
        "what_this_cannot_prove": [
            "A path mention is not proof the speaker had this pull request in mind.",
            "The 200 labels are one reading of a 280-character snippet, not a second independent coder.",
            "Symbols in the patch are not in the enriched file, so symbol linking was not applied to the bulk scan.",
            "Precision below 0.7 keeps number matching as the headline. The path linker is then a sensitivity check.",
            "Linking discussion does not show that the discussion changed the decision.",
        ],
    }
    save_analysis_json("discourse_recall.json", payload)
    print(json.dumps({"headline": headline, "precision": judged.get("precision"), "gain": raw.get("recall_gain_share"), "family": len(family), "crossed": crossed}, indent=2))
    return 0


def _merged_at_by_number(path: Path, wanted: Set[int]) -> Dict[int, Optional[float]]:
    found: Dict[int, Optional[float]] = {}
    if not path.exists():
        return found
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip():
                continue
            pr = json.loads(line)
            try:
                number = int(pr.get("number") or 0)
            except (TypeError, ValueError):
                continue
            if number not in wanted or not pr.get("merged"):
                continue
            found[number] = parse_ts(pr.get("merged_at"))
    return found


if __name__ == "__main__":
    raise SystemExit(main())
