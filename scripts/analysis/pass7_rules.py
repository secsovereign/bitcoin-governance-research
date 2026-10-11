"""Pass 7 rules that were written before any comparison merged_by estimate.

Self-merge stays descriptive. E3 needs 5 distinct mergers in the trailing window
and 6 repositories before a correlation is reported. Neither minimum is lowered.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import numpy as np

MIN_WINDOW_MERGERS = 5
MIN_REPOS_FOR_SPEARMAN = 6
MERGED_BY_COMPLETENESS = 0.95

SELF_MERGE_CONTROLS = (
    "log_total_prs",
    "log_mean_annual_authors",
    "years_of_history",
    "log_mean_distinct_mergers_per_year",
)

# Published H4 in commons_dynamics_test.SCORING_SPEC. It counts merged pull
# requests across people who opened a pull request that year, not merged_by.
H4_PUBLISHED_BASIS = "authors"
H4_PUBLISHED_DESCRIPTION = "Gini of merged-PR counts across people who opened a PR that year."

E3_WINDOW_REASON = (
    "Fewer than 5 distinct mergers appear in the trailing window for the pull requests being scored."
)
E3_REPO_REASON = (
    "Fewer than 6 repositories have an E3 estimate, so the Spearman correlation is DATA UNAVAILABLE "
    "and the class stays UNDETERMINED."
)


def self_merge_design(rows: Sequence[Dict[str, float]]) -> np.ndarray:
    """Design matrix only. This does not fit a self-merge rate."""
    if not rows:
        raise ValueError("self-merge design needs at least one repository")
    columns = [np.ones(len(rows), dtype=float)]
    for name in SELF_MERGE_CONTROLS:
        columns.append(np.asarray([float(row[name]) for row in rows], dtype=float))
    return np.column_stack(columns)


def e3_repository_gate(n_considered: int, n_window_at_least_5: int) -> Dict[str, Any]:
    """A repository is scored only when some scored window contains at least 5 mergers."""
    share = None if n_considered <= 0 else n_window_at_least_5 / n_considered
    if n_window_at_least_5 <= 0:
        return {
            "status": "DATA UNAVAILABLE",
            "reason": E3_WINDOW_REASON,
            "estimate": None,
            "ci95": None,
            "n_considered": n_considered,
            "n_window_at_least_5": n_window_at_least_5,
            "share_window_at_least_5": share,
        }
    return {
        "status": "ok",
        "reason": None,
        "n_considered": n_considered,
        "n_window_at_least_5": n_window_at_least_5,
        "share_window_at_least_5": share,
    }


def e3_correlation_gate(n_repositories_with_estimate: int) -> Dict[str, Any]:
    """Task 3 minimum. Do not report an interval below 6 repositories."""
    if n_repositories_with_estimate < MIN_REPOS_FOR_SPEARMAN:
        return {
            "status": "DATA UNAVAILABLE",
            "class": "UNDETERMINED",
            "reason": E3_REPO_REASON,
            "estimate": None,
            "ci95": None,
            "n_repositories": n_repositories_with_estimate,
        }
    return {
        "status": "ok",
        "class": None,
        "reason": None,
        "n_repositories": n_repositories_with_estimate,
    }


def coverage_from_rows(merged_numbers: Sequence[int], stored: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Counts only. No rate, residual, or E3 estimate."""
    by_number = {int(row["number"]): row for row in stored if isinstance(row.get("number"), int)}
    merged = len(merged_numbers)
    with_merged_by = 0
    with_numeric_id = 0
    no_longer_served = 0
    pending = 0
    for number in merged_numbers:
        row = by_number.get(int(number))
        if row is None:
            pending += 1
            continue
        if row.get("missing"):
            no_longer_served += 1
            continue
        if row.get("merged_by"):
            with_merged_by += 1
        if isinstance(row.get("merged_by_id"), int):
            with_numeric_id += 1
    share = None if merged == 0 else with_merged_by / merged
    ended = pending == 0 and merged > 0
    below_bar = bool(ended and share is not None and share < MERGED_BY_COMPLETENESS)
    return {
        "merged_prs": merged,
        "with_merged_by": with_merged_by,
        "with_numeric_user_id": with_numeric_id,
        "no_longer_served": no_longer_served,
        "pending": pending,
        "merged_by_share": share,
        "crawl_ended": ended,
        "below_completeness_bar": below_bar,
    }


def repositories_below_bar(rows: Sequence[Dict[str, Any]]) -> List[str]:
    """Stop list. An unfinished crawl is not a failure of the 95 percent bar."""
    if any(not row.get("crawl_ended") for row in rows):
        return []
    return [str(row.get("slug")) for row in rows if row.get("below_completeness_bar")]
