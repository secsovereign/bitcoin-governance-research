#!/usr/bin/env python3
"""Pass 7 Task 1. E3, self-merge, and merger Gini from merged_by.

The self-merge comparison stays outside the family. E3's Spearman correlation
against the size-adjusted residual is the one new family test, and only when
at least 6 repositories have an estimate. A repository estimate requires 5
distinct mergers in the trailing window. H4 was published from authors. Merger
Gini replaces that cell, and shared health is refit only when the cell changes.
"""

from __future__ import annotations

import json
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from scripts.analysis.commons_dynamics_test import (  # noqa: E402
    SCORING_SPEC,
    SEED,
    TOP_MERGERS,
    WINDOW,
    People,
    SlidingTop,
    gini,
    normalize_values,
    year_of,
)
from scripts.analysis.comparison_effects import (  # noqa: E402
    _core_reference,
    _family,
    _residuals,
    classify_effect,
    correlation_for_effect,
    e3_time,
    same_sign,
    write_joined,
)
from scripts.analysis.first_year_signal_test import N_BOOT, jsonable  # noqa: E402
from scripts.analysis.pass7_rules import (  # noqa: E402
    H4_PUBLISHED_BASIS,
    H4_PUBLISHED_DESCRIPTION,
    SELF_MERGE_CONTROLS,
    e3_correlation_gate,
    e3_repository_gate,
    repositories_below_bar,
    self_merge_design,
)
from scripts.analysis.rsd_ingroup_test import IdentityIndex, is_bot_login, load_identity, parse_ts  # noqa: E402
from scripts.analysis.size_adjusted_health import (  # noqa: E402
    CORE,
    ROLES,
    SHARED_HEALTH,
    SHARED_MAINTAINERS,
    loo_residual,
    repo_scale,
)
from scripts.data_collection.project_repos_collector import seven_year_slugs  # noqa: E402
from src.utils.findings_io import save_analysis_json  # noqa: E402
from src.utils.paths import get_data_dir, get_findings_dir  # noqa: E402

E3_ID = "E3_log_hours_to_next_same_direction_top5_minus_other"
FAMILY_ID = "pass7.E3_spearman_versus_size_adjusted_residual"
H4 = "H4_gini_merges"


def shared_health_means(
    table: Sequence[Dict[str, Any]],
    h4_overrides: Optional[Dict[Tuple[str, int], float]] = None,
) -> Dict[str, float]:
    """Mean of the six shared indicators. Overrides replace raw H4 before scaling."""
    overrides = h4_overrides or {}
    columns: Dict[str, List[Optional[float]]] = {name: [] for name in SHARED_HEALTH}
    repos: List[str] = []
    for row in table:
        indicators = row.get("indicators") or {}
        key = (str(row["repo"]), int(row["year"]))
        repos.append(key[0])
        for name in SHARED_HEALTH:
            value = indicators.get(name)
            if name == H4 and key in overrides and overrides[key] is not None:
                value = overrides[key]
            columns[name].append(value)
    scaled = {
        name: normalize_values(values, SCORING_SPEC[name]["direction"] == "higher_better")
        for name, values in columns.items()
    }
    by_repo: Dict[str, List[float]] = defaultdict(list)
    for index, repo in enumerate(repos):
        present = [scaled[name][index] for name in SHARED_HEALTH if scaled[name][index] is not None]
        if present:
            by_repo[repo].append(float(np.mean(present)))
    return {repo: float(np.mean(values)) for repo, values in by_repo.items() if values}


def prior_pass6_tests(findings: Path) -> List[Dict[str, Any]]:
    """Tests already in the family of 228. Pass 6 stored them on comparison_effects.json."""
    path = findings / "data" / "comparison_effects.json"
    if not path.exists():
        return []
    rows = []
    for test in json.loads(path.read_text()).get("hypothesis_tests") or []:
        if test.get("in_bh_family") and test.get("p") is not None:
            rows.append(dict(test))
    return rows


def e3_family_test(spearman: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The one family entry. Per-repository E3 fits do not enter."""
    if spearman.get("status") != "ok" or spearman.get("p") is None:
        return None
    return {
        "id": FAMILY_ID,
        "estimate": spearman.get("estimate"),
        "ci95": spearman.get("ci95"),
        "p": spearman.get("p"),
        "n": spearman.get("n"),
        "source": "pass7",
        "in_bh_family": True,
        "low_power": True,
        "predicted_sign": "positive",
    }


def _person_key(login: Any, uid: Any, ident: Optional[IdentityIndex]) -> str:
    text = str(login or "").strip()
    if is_bot_login(text):
        return ""
    if ident is not None:
        return ident.ident(text, irc=False)
    if isinstance(uid, int) and not isinstance(uid, bool):
        return f"id:{uid}"
    lowered = text.lower()
    return f"gh:{lowered}" if lowered else ""


def _rate(rows: Sequence[Tuple[str, str]]) -> Dict[str, Any]:
    merged = len(rows)
    if merged == 0:
        return {"status": "DATA UNAVAILABLE", "reason": "no merged pull requests", "estimate": None, "n": 0}
    known = [(author, merger) for author, merger in rows if author and merger]
    self_n = sum(1 for author, merger in known if author == merger)
    mergers = {merger for _author, merger in known}
    authored = [(author, merger) for author, merger in known if author in mergers]
    authored_self = sum(1 for author, merger in authored if author == merger)
    return {
        "status": "ok",
        "estimate": self_n / merged,
        "n": merged,
        "n_with_known_merger": len(known),
        "n_self": self_n,
        "among_merger_authored": None if not authored else authored_self / len(authored),
        "n_merger_authored": len(authored),
    }


def _yearly_counts(pairs: Iterable[Tuple[int, str]]) -> Dict[int, Dict[str, int]]:
    counts: Dict[int, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for year, key in pairs:
        if key:
            counts[year][key] += 1
    return counts


def describe_merges(records: Sequence[Dict[str, Any]], ident: Optional[IdentityIndex]) -> Dict[str, Any]:
    """Self-merge rates, merger Gini by pull-request year, and distinct mergers by merge year."""
    rate_rows: List[Tuple[str, str]] = []
    created_pairs: List[Tuple[int, str]] = []
    merge_year_people: Dict[int, set] = defaultdict(set)
    for row in records:
        if not row.get("merged"):
            continue
        author = _person_key(row.get("author"), row.get("author_id"), ident)
        merger = _person_key(row.get("merged_by"), row.get("merged_by_id"), ident)
        rate_rows.append((author, merger))
        created = parse_ts(row.get("created_at"))
        if merger and created is not None:
            created_pairs.append((year_of(created), merger))
        merged_at = parse_ts(row.get("merged_at"))
        if merger and merged_at is not None:
            merge_year_people[year_of(merged_at)].add(merger)
    yearly = _yearly_counts(created_pairs)
    gini_by_year = {}
    for year, counts in sorted(yearly.items()):
        value = gini(np.asarray(list(counts.values()), dtype=float))
        if value is not None:
            gini_by_year[str(year)] = value
    distinct = {str(year): len(people) for year, people in sorted(merge_year_people.items())}
    annual = list(distinct.values())
    mean_distinct = float(np.mean(annual)) if annual else None
    packed = _rate(rate_rows)
    packed["merge_gini_by_created_year"] = gini_by_year
    packed["distinct_mergers_per_year"] = distinct
    packed["mean_distinct_mergers_per_year"] = mean_distinct
    packed["log_mean_distinct_mergers_per_year"] = None if not mean_distinct else float(np.log(mean_distinct))
    return packed


def _core_records(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if not row.get("merged"):
                continue
            rows.append({
                "merged": True,
                "author": row.get("author"),
                "author_id": row.get("author_id"),
                "merged_by": row.get("merged_by"),
                "merged_by_id": row.get("merged_by_id"),
                "created_at": row.get("created_at"),
                "merged_at": row.get("merged_at"),
            })
    return rows


def _comparison_records(slug: str) -> List[Dict[str, Any]]:
    owner, repo = slug.split("/", 1)
    root = get_data_dir() / "github" / "repos" / owner / repo
    sidecar: Dict[int, Dict[str, Any]] = {}
    side_path = root / "merged_by.jsonl"
    if side_path.exists():
        with side_path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if not line.strip():
                    continue
                item = json.loads(line)
                number = item.get("number")
                if isinstance(number, int):
                    sidecar[number] = item
    rows = []
    with (root / "prs.jsonl").open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip():
                continue
            pr = json.loads(line)
            if pr.get("merged") is not True:
                continue
            side = sidecar.get(pr.get("number")) or {}
            rows.append({
                "merged": True,
                "author": side.get("author") or pr.get("author"),
                "author_id": side.get("author_id"),
                "merged_by": side.get("merged_by"),
                "merged_by_id": side.get("merged_by_id"),
                "created_at": pr.get("created_at"),
                "merged_at": pr.get("merged_at"),
            })
    return rows


def window_record(core: Dict[str, Any]) -> Dict[str, Any]:
    """Share of scored pull requests whose trailing window has at least 5 mergers."""
    n = int(core["created"].size)
    merge_events = [
        (float(core["merged_at"][i]), int(core["merger"][i]))
        for i in range(n)
        if core["merged"][i] and np.isfinite(core["merged_at"][i]) and int(core["merger"][i]) >= 0
    ]
    signal = np.isfinite(core["signal_ts"]) & (core["signal_dir"] != 0)
    slider = SlidingTop(merge_events, WINDOW, TOP_MERGERS)
    n_scored = 0
    n_window = 0
    order = np.argsort(np.where(signal, core["signal_ts"], np.inf), kind="mergesort")
    for index in order:
        if not signal[index]:
            break
        n_scored += 1
        slider.advance(float(core["signal_ts"][index]))
        if slider.topset() is not None:
            n_window += 1
    gate = e3_repository_gate(n_scored, n_window)
    return gate


def _load_comparison_core(slug: str) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    with tempfile.TemporaryDirectory(prefix="pass7-e3-") as tmp:
        scratch = Path(tmp)
        joined = scratch / "joined.jsonl"
        built = write_joined(slug, joined)
        if built.get("status") != "ok":
            return None, built
        owner, repo = slug.split("/", 1)
        side_path = get_data_dir() / "github" / "repos" / owner / repo / "merged_by.jsonl"
        mergers: Dict[int, str] = {}
        if side_path.exists():
            with side_path.open(encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    item = json.loads(line)
                    number = item.get("number")
                    login = item.get("merged_by")
                    if isinstance(number, int) and login:
                        mergers[number] = str(login)
        enriched = scratch / "enriched.jsonl"
        with joined.open(encoding="utf-8") as source, enriched.open("w", encoding="utf-8") as out:
            for line in source:
                row = json.loads(line)
                login = mergers.get(row.get("number"))
                if login:
                    row["merged_by"] = login
                out.write(json.dumps(row) + "\n")
        core = load_core_quiet(enriched)
        return core, built


def load_core_quiet(path: Path) -> Dict[str, Any]:
    from scripts.analysis.commons_dynamics_test import load_core

    return load_core(path, IdentityIndex(), People())


def _h4_overrides(descriptions: Dict[str, Dict[str, Any]]) -> Dict[Tuple[str, int], float]:
    overrides = {}
    for repo, described in descriptions.items():
        for year, value in (described.get("merge_gini_by_created_year") or {}).items():
            if value is not None:
                overrides[(repo, int(year))] = float(value)
    return overrides


def _h4_changed(table: Sequence[Dict[str, Any]], overrides: Dict[Tuple[str, int], float]) -> bool:
    for row in table:
        key = (str(row["repo"]), int(row["year"]))
        if key not in overrides:
            continue
        published = (row.get("indicators") or {}).get(H4)
        if published is None or abs(float(published) - overrides[key]) > 1e-8:
            return True
    return False


def _fit_health(means: Dict[str, float], rng: np.random.Generator, n_boot: int) -> Dict[str, Any]:
    data_dir = get_data_dir()
    rows = []
    for repo, score in sorted(means.items()):
        dump = data_dir / "github" / "repos" / repo / "prs.jsonl"
        if repo == CORE:
            dump = data_dir / "github" / "prs_raw.jsonl"
        scale = repo_scale(dump)
        if scale.get("status") != "ok":
            continue
        rows.append({
            "repo": repo,
            "role": ROLES.get(repo, "other"),
            "shared_maintainers": repo in SHARED_MAINTAINERS,
            "health": float(score),
            "n_prs": scale["n_prs"],
            "log_total_prs": scale["log_total_prs"],
            "log_mean_annual_authors": scale["log_mean_annual_authors"],
            "years_of_history": scale["years_of_history"],
        })
    fitted = []
    for index, row in enumerate(rows):
        fitted.append({**row, **loo_residual(rows, index, rng, n_boot)})
    core = next((row for row in fitted if row["repo"] == CORE), None)
    ordered = sorted((row for row in fitted if row.get("residual") is not None), key=lambda item: item["residual"])
    rank = next((i for i, row in enumerate(ordered, start=1) if row["repo"] == CORE), None)
    return {
        "n": len(rows),
        "low_power": len(rows) < 20,
        "core_residual": None if core is None else core.get("residual"),
        "core_ci95": None if core is None else core.get("ci95"),
        "core_rank_most_negative": rank,
        "repositories": [
            {
                "repo": row["repo"],
                "health": row["health"],
                "residual": row.get("residual"),
                "ci95": row.get("ci95"),
            }
            for row in fitted
        ],
    }


def _self_merge_rows(descriptions: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    data_dir = get_data_dir()
    rows = []
    for repo, described in descriptions.items():
        if described.get("status") != "ok" or described.get("log_mean_distinct_mergers_per_year") is None:
            continue
        dump = data_dir / "github" / "repos" / repo / "prs.jsonl"
        if repo == CORE:
            dump = data_dir / "github" / "prs_raw.jsonl"
        scale = repo_scale(dump)
        if scale.get("status") != "ok":
            continue
        rows.append({
            "repo": repo,
            "self_merge_rate": float(described["estimate"]),
            "log_total_prs": scale["log_total_prs"],
            "log_mean_annual_authors": scale["log_mean_annual_authors"],
            "years_of_history": float(scale["years_of_history"]),
            "log_mean_distinct_mergers_per_year": float(described["log_mean_distinct_mergers_per_year"]),
        })
    return rows


def self_merge_residual(rows: Sequence[Dict[str, Any]], index: int, rng: np.random.Generator, n_boot: int) -> Dict[str, Any]:
    """Leave-one-out residual. Descriptive, and not a family test."""
    held = rows[index]
    train = [row for i, row in enumerate(rows) if i != index]
    if len(train) < 5:
        return {"status": "DATA UNAVAILABLE", "reason": "leave-one-out fit has fewer than 5 repositories"}
    y = np.asarray([row["self_merge_rate"] for row in train], dtype=float)
    beta, *_ = np.linalg.lstsq(self_merge_design(train), y, rcond=None)
    predicted = float(self_merge_design([held])[0] @ beta)
    residual = float(held["self_merge_rate"] - predicted)
    draws = np.full(n_boot, np.nan)
    pool = np.arange(len(train))
    for i in range(n_boot):
        take = pool[rng.integers(0, pool.size, pool.size)]
        sample = [train[int(j)] for j in take]
        fitted, *_ = np.linalg.lstsq(
            self_merge_design(sample),
            np.asarray([row["self_merge_rate"] for row in sample], dtype=float),
            rcond=None,
        )
        draws[i] = float(held["self_merge_rate"] - float(self_merge_design([held])[0] @ fitted))
    from scripts.analysis.commons_dynamics_test import ci_from_draws, p_from_draws

    return {
        "status": "ok",
        "residual": residual,
        "ci95": ci_from_draws(draws),
        "p": p_from_draws(draws),
        "n": len(rows),
        "low_power": len(rows) < 20,
        "in_bh_family": False,
        "controls": list(SELF_MERGE_CONTROLS),
    }


def _score_e3(slug: str, rng: np.random.Generator, n_boot: int) -> Dict[str, Any]:
    core, built = _load_comparison_core(slug)
    if core is None:
        gate = e3_repository_gate(0, 0)
        gate["reason"] = built.get("reason") or gate["reason"]
        return gate
    record = window_record(core)
    if record.get("status") != "ok":
        record["estimate"] = None
        record["ci95"] = None
        return record
    from scripts.analysis.commons_dynamics_test import events_frame

    fit = e3_time(core, events_frame(core["events"]), rng, n_boot)
    record.update(fit)
    record["in_bh_family"] = False
    if fit.get("cohens_d") is not None and abs(float(fit["cohens_d"])) > 2:
        record["large_effect_cite_gap"] = True
        record["log_hour_gap"] = fit.get("estimate")
    return record


def analyze(n_boot: int = N_BOOT, seed: int = SEED) -> Dict[str, Any]:
    findings = get_findings_dir()
    coverage_path = findings / "data" / "merged_by_crawl_coverage.json"
    coverage = json.loads(coverage_path.read_text()) if coverage_path.exists() else {"repositories": []}
    below = repositories_below_bar(coverage.get("repositories") or [])
    if below:
        payload = {
            "status": "STOPPED",
            "reason": "merged_by coverage is under 95 percent",
            "repositories_below_bar": below,
        }
        save_analysis_json("pass7_merged_by.json", payload)
        return payload
    commons = json.loads((findings / "data" / "commons_dynamics_analysis.json").read_text())
    table = commons.get("repo_year_table") or []
    published_means = {
        row["repo"]: row.get("mean_health")
        for row in commons.get("cross_repo_ranking") or []
    }
    ident = load_identity()
    descriptions: Dict[str, Dict[str, Any]] = {
        CORE: describe_merges(_core_records(get_data_dir() / "github" / "prs_raw.jsonl"), ident),
    }
    for slug in seven_year_slugs():
        print(f"describing {slug}", flush=True)
        descriptions[slug] = describe_merges(_comparison_records(slug), None)
    descriptions["ethereum/go-ethereum"] = {
        "status": "DATA UNAVAILABLE",
        "reason": "prs.jsonl is missing, so merged_by was not requested",
        "estimate": None,
    }
    overrides = _h4_overrides({repo: row for repo, row in descriptions.items() if repo != "ethereum/go-ethereum"})
    changed = _h4_changed(table, overrides)
    published_residuals = _residuals(findings)
    if changed:
        print("H4 changed, refitting shared health", flush=True)
        means = shared_health_means(table, overrides)
        health = _fit_health(means, np.random.default_rng(seed), n_boot)
        residuals = {
            row["repo"]: row["residual"]
            for row in health["repositories"]
            if row.get("residual") is not None
        }
    else:
        means = published_means
        health = {"status": "unchanged", "core_residual": published_residuals.get(CORE)}
        residuals = published_residuals
    e3_rows = []
    e3_rng = np.random.default_rng(seed)
    for slug in seven_year_slugs():
        print(f"scoring E3 {slug}", flush=True)
        scored = _score_e3(slug, e3_rng, n_boot)
        scored["repo"] = slug
        e3_rows.append(scored)
        print(
            f"scored {slug} status={scored.get('status')} "
            f"window_share={scored.get('share_window_at_least_5')}",
            flush=True,
        )
    reference = _core_reference(findings).get(E3_ID) or {}
    pairs_x: List[float] = []
    pairs_y: List[float] = []
    core_estimate = reference.get("estimate")
    if core_estimate is not None and CORE in residuals:
        pairs_x.append(float(core_estimate))
        pairs_y.append(float(residuals[CORE]))
    outside = []
    for row in e3_rows:
        if row.get("status") != "ok" or row.get("estimate") is None:
            continue
        outside.append(row)
        residual = residuals.get(row["repo"])
        if residual is None:
            continue
        pairs_x.append(float(row["estimate"]))
        pairs_y.append(float(residual))
    gate = e3_correlation_gate(len(pairs_x))
    if gate.get("status") != "ok":
        spearman = {
            **gate,
            "predicted_sign": "positive",
            "low_power": True,
            "point_matches_prediction": None,
            "interval_excludes_zero": False,
            "in_bh_family": False,
        }
        label = "UNDETERMINED"
    else:
        spearman = correlation_for_effect(
            np.asarray(pairs_x, dtype=float),
            np.asarray(pairs_y, dtype=float),
            np.random.default_rng(seed),
            n_boot,
        )
        spearman["predicted_sign"] = "positive"
        spearman["low_power"] = True
        spearman["n_repositories"] = len(pairs_x)
        spearman["point_matches_prediction"] = same_sign(spearman.get("estimate"), 1.0)
        spearman["in_bh_family"] = spearman.get("status") == "ok" and spearman.get("p") is not None
        if spearman.get("status") != "ok":
            label = "UNDETERMINED"
        else:
            label = classify_effect(core_estimate, reference.get("ci95"), outside, spearman.get("ci95"))
    test = e3_family_test(spearman)
    family_size = 228
    crossed: List[Dict[str, Any]] = []
    recomputed_q: List[Dict[str, Any]] = []
    if test is not None:
        from scripts.analysis.commons_dynamics_test import collect_prior_tests
        from scripts.analysis.first_year_signal_test import collect_pass3
        from scripts.analysis.gap_closure_test import collect_pass4
        from scripts.analysis.merge_durability import _collect_pass5

        stored_for_q: List[Dict[str, Any]] = []
        missing_q: List[Dict[str, str]] = []
        stored_for_q.extend(collect_prior_tests(findings, missing_q))
        stored_for_q.extend(collect_pass3(findings, missing_q))
        stored_for_q.extend(collect_pass4(findings, missing_q))
        stored_for_q.extend(_collect_pass5(findings, missing_q))
        durability_path = findings / "data" / "merge_durability.json"
        if durability_path.exists():
            for row in json.loads(durability_path.read_text()).get("hypothesis_tests") or []:
                if row.get("in_bh_family") and row.get("p") is not None:
                    stored_for_q.append(row)
        pass6 = prior_pass6_tests(findings)
        previous_q = {
            str(row.get("id")): row.get("q")
            for row in stored_for_q + pass6
            if row.get("q") is not None
        }
        family, crossed = _family(findings, [], pass6 + [test])
        ids = [str(row.get("id")) for row in family]
        if len(ids) != len(set(ids)):
            raise RuntimeError("BH family has a duplicate test id")
        family_size = len(family)
        for row in family:
            before = previous_q.get(str(row.get("id")))
            recomputed_q.append({"id": row.get("id"), "q_before": before, "q": row.get("q")})
            if before is None:
                continue
            was = float(before) < 0.05
            now = float(row["q"]) < 0.05
            if was != now and not any(item.get("id") == row.get("id") for item in crossed):
                crossed.append({
                    "id": row.get("id"),
                    "q_before": float(before),
                    "q_after": float(row["q"]),
                    "crossed": "above 0.05" if was and not now else "below 0.05",
                })
        match = next((row for row in family if row.get("id") == FAMILY_ID), None)
        if match is not None:
            test["q"] = match.get("q")
            spearman["q"] = match.get("q")
    else:
        spearman["q"] = None
    merge_rows = _self_merge_rows({repo: row for repo, row in descriptions.items() if row.get("status") == "ok"})
    self_rng = np.random.default_rng(seed)
    self_fitted = []
    for index, row in enumerate(merge_rows):
        self_fitted.append({**row, **self_merge_residual(merge_rows, index, self_rng, n_boot)})
    core_self = next((row for row in self_fitted if row["repo"] == CORE), None)
    payload = {
        "version": "7.0",
        "task": 1,
        "status": "ok",
        "h4_published_basis": H4_PUBLISHED_BASIS,
        "h4_published_description": H4_PUBLISHED_DESCRIPTION,
        "h4_replaced_with_merged_by": bool(changed),
        "shared_health_rerun": bool(changed),
        "published_core_health_residual": published_residuals.get(CORE),
        "size_adjusted_health": health,
        "self_merge": {
            "in_bh_family": False,
            "descriptive": True,
            "controls": list(SELF_MERGE_CONTROLS),
            "core": None if core_self is None else {
                "rate": core_self["self_merge_rate"],
                "residual": core_self.get("residual"),
                "ci95": core_self.get("ci95"),
                "p": core_self.get("p"),
                "n": core_self.get("n"),
                "low_power": True,
            },
            "repositories": [
                {
                    "repo": row["repo"],
                    "rate": row["self_merge_rate"],
                    "residual": row.get("residual"),
                    "ci95": row.get("ci95"),
                }
                for row in self_fitted
            ],
        },
        "e3": {
            "family_id": FAMILY_ID,
            "core_estimate": core_estimate,
            "core_ci95": reference.get("ci95"),
            "class": label,
            "correlation": spearman,
            "repositories": e3_rows,
            "n_with_estimate": len(outside) + (1 if core_estimate is not None else 0),
        },
        "descriptions": descriptions,
        "hypothesis_tests": [] if test is None else [test],
        "bh_family_size": family_size,
        "bh_recomputed_q": recomputed_q,
        "bh_crossed_0_05": crossed,
        "what_this_cannot_prove": [
            "A size-adjusted residual is not a cause of the merger cascade.",
            "Fewer than 20 repositories make the correlation LOW POWER.",
            "Self-merge falls as the number of mergers rises, so the residual is descriptive and is not in the family.",
            "A repository with fewer than 5 mergers in the trailing window has no E3 estimate. That absence is not evidence the cascade is missing.",
            "ethereum/go-ethereum has no pull-request list, so it is not an outside peer here.",
        ],
    }
    save_analysis_json("pass7_merged_by.json", jsonable(payload))
    return payload


def main() -> int:
    result = analyze()
    e3 = result.get("e3") or {}
    correlation = e3.get("correlation") or {}
    print(json.dumps({
        "status": result.get("status"),
        "h4_replaced": result.get("h4_replaced_with_merged_by"),
        "family": result.get("bh_family_size"),
        "crossed": result.get("bh_crossed_0_05"),
        "e3_class": e3.get("class"),
        "e3_n": correlation.get("n_repositories"),
        "e3_r": correlation.get("estimate"),
        "e3_status": correlation.get("status"),
        "self_merge_residual": (result.get("self_merge") or {}).get("core"),
    }, default=str))
    return 0 if result.get("status") == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
