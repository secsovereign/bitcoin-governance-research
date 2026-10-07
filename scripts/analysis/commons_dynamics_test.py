#!/usr/bin/env python3
"""Commons dynamics: behavioral effects, Ostrom design principles, health.

The common-pool resource is reviewer attention and merge authority. The code
is non-rival and is not the resource. Part A is candidate mechanisms, Part B
is institutional conditions, and Part C is outcomes. The three measurement
sets use different indicators. This file does not observe psychological state
and does not diagnose any person.

Pass 2 found time-structured newcomer and in-group gaps, not a single
project-wide rise in the bar. Year fixed effects are still on every model
so those paths are not pooled together.
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
from scipy import stats

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from scripts.analysis.rsd_ingroup_test import (  # noqa: E402
    cohens_d,
    effect_flag,
    is_bot_login,
    keyword_tone,
    load_identity,
    logistic_irls,
    parse_ts,
)
from src.utils.findings_io import save_analysis_json  # noqa: E402
from src.utils.logger import setup_logger  # noqa: E402
from src.utils.paths import get_data_dir, get_findings_dir  # noqa: E402

logger = setup_logger("commons_dynamics")

DAY = 86400.0
YEAR = 365.25 * DAY
WINDOW = 730.5 * DAY
TRAIN_LAST_YEAR = 2023
HOLDOUT_FIRST_YEAR = 2024
TOP_N = 20
TOP_MERGERS = 5
N_BOOT_DEFAULT = 1000
N_PERM_DEFAULT = 500
SEED = 7

# Danescu-Niculescu-Mizil style function-word classes. Inline on purpose.
FUNCTION_WORDS: Dict[str, set] = {
    "article": {"a", "an", "the"},
    "pronoun": {
        "i", "you", "he", "she", "we", "they", "me", "him", "her", "us", "them",
        "my", "your", "his", "our", "their", "it", "its", "myself", "yourself",
    },
    "preposition": {
        "of", "to", "in", "for", "on", "with", "at", "by", "from", "as", "into",
        "about", "over", "after", "before", "between", "under", "through", "without",
    },
    "auxiliary": {
        "is", "are", "was", "were", "be", "been", "being", "do", "does", "did",
        "have", "has", "had", "can", "could", "will", "would", "should", "may", "might", "must",
    },
    "conjunction": {"and", "or", "but", "if", "because", "so", "while", "although", "though", "than", "then"},
    "quantifier": {"all", "some", "any", "many", "much", "few", "more", "most", "no", "every", "each"},
}
FW_NAMES = list(FUNCTION_WORDS)
FW_SETS = [FUNCTION_WORDS[name] for name in FW_NAMES]

JARGON_RE = re.compile(
    r"\b(concept\s+acks?|approach\s+acks?|utacks?|tacks?|acks?|nits?|rebase[ds]?|squash(?:ed|es)?)\b",
    re.I,
)
HARSH_RE = re.compile(
    r"\b(idiot|idiots|stupid|useless|garbage|nonsense|ridiculous|clueless|incompetent|"
    r"dumb|pathetic|terrible|shut up|waste of time)\b",
    re.I,
)
SCOPE_RE = re.compile(r"out of scope|not for this repo|belongs in|should be a bip", re.I)
RULE_FILE_RE = re.compile(
    r"contributing\.md|developer-notes|productivity\.md|release-process|"
    r"maintainer|github/workflows|/ci/|ci/|bip[-_ ]?process",
    re.I,
)
RULE_TITLE_RE = re.compile(r"\b(contributing\.md|developer notes|release process|bip process|ci policy)\b", re.I)
SANCTION_RE = re.compile(
    r"\b(permanently banned|banned|conversation (is )?locked|this thread (is|has been) locked|"
    r"access removed|removed as maintainer|moderation notice)\b",
    re.I,
)
ALT_RE = re.compile(
    r"bitcoin\s*knots|\bknots\b|\bbtcd\b|libbitcoin|\bbcoin\b|floresta|\bblvm\b",
    re.I,
)
TOPIC_RES: Dict[str, re.Pattern] = {
    "block size": re.compile(r"block ?size|blocksize", re.I),
    "mempool policy": re.compile(r"mempool polic", re.I),
    "OP_RETURN": re.compile(r"op_return|opreturn", re.I),
    "datacarrier": re.compile(r"datacarrier|data carrier", re.I),
    "activation": re.compile(r"\bactivation\b|soft[- ]?fork activ", re.I),
    "RBF": re.compile(r"\brbf\b|replace[- ]by[- ]fee", re.I),
    "covenants": re.compile(r"\bcovenants?\b", re.I),
}
TOPIC_NAMES = list(TOPIC_RES)
PULL_URL_RE = re.compile(r"bitcoin/bitcoin/(?:pull|issues)/(\d+)", re.I)
HASH_RE = re.compile(r"(?<![A-Za-z0-9])#(\d{3,6})\b")
PRIORITY_TOPIC_RE = re.compile(
    r"#topic\b.*high[- ]priority.*(?:review|\bprs?\b)|#topic\b.*\bprs?\b.*high[- ]priority",
    re.I,
)
ANY_TOPIC_RE = re.compile(r"#topic\b", re.I)
TOKEN_RE = re.compile(r"[a-z']+")
SUBSYSTEMS = ("wallet", "p2p", "gui", "consensus", "mempool", "build", "test", "docs")

# Direction is fixed here, before any fit, score, or normalization.
SCORING_SPEC: Dict[str, Dict[str, Any]] = {
    "E1": {
        "part": "A", "principle": None, "maps": ["P1", "P2"], "scored": False,
        "direction": "higher_means_stronger_cumulative_advantage",
        "description": "Standardized coefficient of prior merges on getting a peer response within 14 days.",
    },
    "E2": {
        "part": "A", "principle": None, "maps": ["P2", "P4"], "scored": False,
        "direction": "higher_means_stronger_reciprocity",
        "description": "Reciprocity index minus the within-year shuffle null.",
    },
    "E3": {
        "part": "A", "principle": None, "maps": ["P3", "P4"], "scored": False,
        "direction": "higher_means_stronger_agreement_cascade",
        "description": "Agreement-share gap after a top-5 merger's first ACK or NACK, minus everyone else.",
    },
    "E4": {
        "part": "A", "principle": None, "maps": ["P1"], "scored": False,
        "direction": "higher_means_stronger_jargon_merge_link",
        "description": "Standardized coefficient of first-year house-term use on first-year merge rate.",
    },
    "E5": {
        "part": "A", "principle": None, "maps": ["P4"], "scored": False,
        "direction": "higher_means_slower_decisions_as_participation_rises",
        "description": "Standardized coefficient of log participant count on log days to decision.",
    },
    "E6": {
        "part": "A", "principle": None, "maps": ["P7", "P4"], "scored": False,
        "direction": "higher_means_stronger_funder_homophily",
        "description": "Within-funder review rate minus a within-year shuffle. Requires a person-to-funder ledger.",
    },
    "E7": {
        "part": "A", "principle": None, "maps": ["P6"], "scored": False,
        "direction": "higher_means_first_tone_predicts_merge_given_later_tone",
        "description": "Standardized coefficient of first-comment tone on merge, controlling for later tone.",
    },
    "E8": {
        "part": "A", "principle": None, "maps": ["P2"], "scored": False,
        "direction": "higher_means_more_relative_souring_before_exit",
        "description": "How much more leavers' tone falls in the last six months than matched active contributors.",
    },
    "E9": {
        "part": "A", "principle": None, "maps": ["P3", "P1"], "scored": False,
        "direction": "higher_means_listed_prs_merge_more",
        "description": "Merge-rate gap, meeting high-priority list minus unlisted, in the meeting era.",
    },
    "E10": {
        "part": "A", "principle": None, "maps": ["P3", "P6"], "scored": False,
        "direction": "higher_means_more_participation_after_a_nack_that_lost",
        "description": "Next-year participation after NACK-then-merged minus NACK-then-closed. Negative favors a suppression reading.",
    },
    "E11": {
        "part": "A", "principle": None, "maps": ["P5"], "scored": False,
        "direction": "higher_means_more_followup_after_harsh_comments",
        "description": "Follow-up correction rate. LOW OBSERVABILITY: deleted comments are absent.",
    },
    "E12": {
        "part": "A", "principle": None, "maps": [], "scored": False,
        "direction": "higher_means_ingroup_predicts_the_outcome",
        "description": "In-group coefficient on 90-day return and on no-peer-response, with shared controls. Unmapped to a principle.",
    },
    "P1a_grant_discussion_share": {
        "part": "B", "principle": "P1", "direction": "higher_better", "scored": True,
        "description": "Share of inferred merge-right starts with IRC or mailing-list discussion in the prior 30 days.",
    },
    "P1b_entry_wait_cv": {
        "part": "B", "principle": "P1", "direction": "lower_better", "scored": True,
        "description": "Coefficient of variation of days from first PR to first merge, by entry cohort.",
    },
    "P1c_scope_disputes_per_100": {
        "part": "B", "principle": "P1", "direction": "lower_better", "scored": True,
        "description": "Scope-boundary phrases per 100 PRs.",
    },
    "P2a_gini_provision_ratio": {
        "part": "B", "principle": "P2", "direction": "lower_better", "scored": True,
        "description": "Gini of attention given divided by attention received.",
    },
    "P2a_share_ratio_near_one": {
        "part": "B", "principle": "P2", "direction": "higher_better", "scored": True,
        "description": "Share of contributors whose given/received ratio is between 0.5 and 2.",
    },
    "P2a_share_ratio_above_one": {
        "part": "B", "principle": "P2", "direction": "unscored", "scored": False,
        "description": "Share with ratio above 1. Reported only: above 1 is not a signed principle.",
    },
    "P2b_merge_review_correlation": {
        "part": "B", "principle": "P2", "direction": "higher_better", "scored": True,
        "description": "Correlation between merges received and attention given.",
    },
    "P2c_top5_review_share": {
        "part": "B", "principle": "P2", "direction": "lower_better", "scored": True,
        "description": "Share of attention events produced by the top 5 people that year.",
    },
    "P3a_rule_pr_count": {
        "part": "B", "principle": "P3", "direction": "unscored", "scored": False,
        "description": "Count of rule-changing PRs. Identifies the set; it is not a quality score.",
    },
    "P3b_rule_participant_share": {
        "part": "B", "principle": "P3", "direction": "higher_better", "scored": True,
        "description": "Unique participants on rule-changing PRs divided by active contributors.",
    },
    "P3c_nonmerger_rule_merge_rate": {
        "part": "B", "principle": "P3", "direction": "higher_better", "scored": True,
        "description": "Merge rate of rule-changing PRs whose author had not merged code before.",
    },
    "P4a_self_merge_rate": {
        "part": "B", "principle": "P4", "direction": "lower_better", "scored": True,
        "description": "Share of merges in which the author and the merger are the same person.",
    },
    "P4b_zero_independent_attention_share": {
        "part": "B", "principle": "P4", "direction": "lower_better", "scored": True,
        "description": "Share of merges with no attention from anyone except the author and the merger.",
    },
    "P4c_nonmaintainer_review_share": {
        "part": "B", "principle": "P4", "direction": "higher_better", "scored": True,
        "description": "Share of canonical-maintainer PRs that received attention from a non-maintainer.",
    },
    "P4c_median_independent_reviews": {
        "part": "B", "principle": "P4", "direction": "higher_better", "scored": True,
        "description": "Median count of non-maintainer attention events on canonical-maintainer PRs.",
    },
    "P5a_sanction_events": {
        "part": "B", "principle": "P5", "direction": "unscored", "scored": False,
        "description": "Lock, ban, moderation, or access-removal traces. Counts only.",
    },
    "P5b_graduated_share": {
        "part": "B", "principle": "P5", "direction": "higher_better", "scored": True,
        "description": "Share of severe traces preceded by a lesser recorded action. Entered only when at least 10 events exist.",
    },
    "P6a_explicit_resolution_share": {
        "part": "B", "principle": "P6", "direction": "higher_better", "scored": True,
        "description": "Share of contested PRs that end by merge or by activity within 30 days of closure.",
    },
    "P6a_median_days_contested": {
        "part": "B", "principle": "P6", "direction": "lower_better", "scored": True,
        "description": "Median days to a final state on contested PRs.",
    },
    "P6b_recurring_topics": {
        "part": "B", "principle": "P6", "direction": "lower_better", "scored": True,
        "description": "Dispute topics present this year that also appear in three or more separate years.",
    },
    "P6c_exit_channels": {
        "part": "B", "principle": "P6", "direction": "unscored", "scored": False,
        "description": "Dated forks and alternative-implementation launches. Not the H7 departure rate.",
    },
    "P7a_funder_hhi": {
        "part": "B", "principle": "P7", "direction": "lower_better", "scored": True,
        "description": "Herfindahl index of funders across active contributors.",
    },
    "P7b_alt_impl_mentions": {
        "part": "B", "principle": "P7", "direction": "unscored", "scored": False,
        "description": "Mentions of other implementations and keyword sentiment. Descriptive and sentiment-model dependent.",
    },
    "P8a_subsystem_local_share": {
        "part": "B", "principle": "P8", "direction": "higher_better", "scored": False,
        "description": "Per-subsystem local-merge share. Reported in detail. P8c is that mean and is the scored index.",
    },
    "P8b_venue_count": {
        "part": "B", "principle": "P8", "direction": "higher_better", "scored": True,
        "description": "Distinct decision venues with activity that year.",
    },
    "P8c_decision_locality": {
        "part": "B", "principle": "P8", "direction": "higher_better", "scored": True,
        "description": "Mean across subsystems of merges by that subsystem's frequent reviewers rather than top-level mergers.",
    },
    "H1_active_reviewers_per_pr": {
        "part": "C", "principle": None, "direction": "higher_better", "scored": True,
        "description": "Distinct reviewers that year per PR opened.",
    },
    "H2_open_stock_per_pr_opened": {
        "part": "C", "principle": None, "direction": "lower_better", "scored": True,
        "description": "PRs still open at year end, per PR opened that year.",
    },
    "H2_stale_open_per_pr_opened": {
        "part": "C", "principle": None, "direction": "lower_better", "scored": True,
        "description": "Year-end open PRs older than one year, per PR opened that year.",
    },
    "H3_cohort_active_24m": {
        "part": "C", "principle": None, "direction": "higher_better", "scored": True,
        "description": "Share of an entry cohort with activity on or after the 24-month mark.",
    },
    "H4_gini_merges": {
        "part": "C", "principle": None, "direction": "lower_better", "scored": True,
        "description": "Gini of merged-PR counts across people who opened a PR that year.",
    },
    "H4_gini_reviews": {
        "part": "C", "principle": None, "direction": "lower_better", "scored": True,
        "description": "Gini of attention given across people who authored or reviewed that year.",
    },
    "H5_bus_factor": {
        "part": "C", "principle": None, "direction": "higher_better", "scored": True,
        "description": "Fewest people accounting for half of that year's merges.",
    },
    "H6_median_days_to_decision": {
        "part": "C", "principle": None, "direction": "lower_better", "scored": True,
        "description": "Median days from open to merge or close among decided PRs.",
    },
    "H7_exit_rate": {
        "part": "C", "principle": None, "direction": "lower_better", "scored": True,
        "description": "Attrition-timeline departures that year divided by timeline members active that year.",
    },
}


def metric_ids(part: str) -> set:
    return {key for key, spec in SCORING_SPEC.items() if spec["part"] == part}


def assert_measurement_sets_disjoint() -> None:
    """Health indicators must not be Part A or Part B indicators."""
    health = metric_ids("C")
    principles = metric_ids("B")
    effects = metric_ids("A")
    overlap = (health & principles) | (health & effects) | (principles & effects)
    if overlap:
        raise RuntimeError(
            "measurement sets overlap: " + ", ".join(sorted(overlap))
        )
    for key, spec in SCORING_SPEC.items():
        if spec["part"] == "C" and spec.get("principle"):
            raise RuntimeError(f"health metric {key} is tied to a principle")
        if spec["part"] == "B" and not spec.get("principle"):
            raise RuntimeError(f"principle metric {key} has no principle id")


assert_measurement_sets_disjoint()


def unavailable(bucket: List[Dict[str, str]], metric: str, reason: str) -> None:
    bucket.append({"metric": metric, "reason": reason, "status": "DATA UNAVAILABLE"})


def gini(values: np.ndarray) -> Optional[float]:
    x = np.sort(np.asarray(values, dtype=float))
    x = x[np.isfinite(x) & (x >= 0)]
    if x.size == 0:
        return None
    total = float(x.sum())
    if total <= 0:
        return 0.0
    n = x.size
    idx = np.arange(1, n + 1, dtype=float)
    return float((2.0 * np.sum(idx * x)) / (n * total) - (n + 1) / n)


def bus_factor(counts: np.ndarray) -> Optional[int]:
    x = np.asarray(counts, dtype=float)
    x = x[np.isfinite(x) & (x > 0)]
    if x.size == 0:
        return None
    ordered = np.sort(x)[::-1]
    half = ordered.sum() * 0.5
    running = 0.0
    for i, value in enumerate(ordered, start=1):
        running += value
        if running + 1e-9 >= half:
            return int(i)
    return int(ordered.size)


def normalize_values(values: Sequence[Optional[float]], higher_better: bool) -> List[Optional[float]]:
    usable = [float(v) for v in values if v is not None and np.isfinite(v)]
    if not usable:
        return [None for _ in values]
    lo = min(usable)
    hi = max(usable)
    out: List[Optional[float]] = []
    for value in values:
        if value is None or not np.isfinite(value):
            out.append(None)
        elif hi == lo:
            out.append(0.5)
        else:
            scaled = (float(value) - lo) / (hi - lo)
            out.append(scaled if higher_better else 1.0 - scaled)
    return out


def bh_qvalues(pvals: Sequence[float]) -> np.ndarray:
    """Benjamini-Hochberg q-values, clipped to [0, 1]."""
    p = np.asarray(pvals, dtype=float)
    m = int(p.size)
    q = np.ones(m, dtype=float)
    if m == 0:
        return q
    order = np.argsort(p)
    running = 1.0
    for rank_from_end, idx in enumerate(order[::-1]):
        rank = m - rank_from_end
        running = min(running, float(p[idx]) * m / rank)
        q[idx] = running
    return np.clip(q, 0.0, 1.0)


def p_from_ci(estimate: Optional[float], ci: Optional[Sequence[float]]) -> Optional[float]:
    """Two-sided normal p from a percentile interval. Used for passes 1 and 2, which stored intervals."""
    if estimate is None or ci is None or len(ci) != 2:
        return None
    lo, hi = ci
    if lo is None or hi is None or not np.isfinite(estimate) or not np.isfinite(lo) or not np.isfinite(hi):
        return None
    se = (float(hi) - float(lo)) / (2.0 * 1.959963984540054)
    if se <= 1e-15:
        return 0.0 if abs(float(estimate)) > 0 else 1.0
    z = abs(float(estimate)) / se
    return float(min(1.0, 2.0 * (1.0 - stats.norm.cdf(z))))


def p_from_draws(draws: np.ndarray) -> float:
    ok = draws[np.isfinite(draws)]
    if ok.size == 0:
        return 1.0
    tail = min(float(np.mean(ok <= 0)), float(np.mean(ok >= 0)))
    return float(min(1.0, max(2.0 * tail, 1.0 / ok.size)))


def ci_from_draws(draws: np.ndarray) -> Optional[List[float]]:
    ok = draws[np.isfinite(draws)]
    if ok.size < 20:
        return None
    lo, hi = np.percentile(ok, [2.5, 97.5])
    return [float(lo), float(hi)]


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
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    return obj


def year_of(ts: float) -> int:
    return datetime.fromtimestamp(ts, tz=timezone.utc).year


def tokenize(text: str) -> List[str]:
    return TOKEN_RE.findall((text or "").lower()[:4000])


def fw_mask(tokens: Sequence[str]) -> int:
    if not tokens:
        return 0
    present = set(tokens)
    mask = 0
    for i, vocab in enumerate(FW_SETS):
        if present & vocab:
            mask |= 1 << i
    return mask


def jargon_hit(text: str) -> bool:
    return bool(JARGON_RE.search(text or ""))


def stance_flags(text: str, state: str = "") -> Tuple[bool, bool, bool]:
    raw = text or ""
    hedged = bool(re.search(r"not a nack|not nack", raw, re.I))
    state_u = (state or "").upper()
    nack = ((not hedged) and bool(re.search(r"\bNACK\b", raw))) or state_u == "CHANGES_REQUESTED"
    concept = bool(re.search(r"\b(concept|approach)\s+acks?\b", raw, re.I))
    ack = bool(re.search(r"\b(utacks?|tacks?|acks?)\b", raw, re.I)) or state_u == "APPROVED" or concept
    if nack:
        ack = False
    return ack, nack, concept


def subsystem_bit(path: str) -> int:
    p = (path or "").lower()
    if "src/wallet" in p or "/wallet/" in p:
        return 1 << 0
    if "src/net" in p or "net_processing" in p:
        return 1 << 1
    if "src/qt" in p:
        return 1 << 2
    if any(bit in p for bit in ("src/consensus", "src/script", "src/validation", "src/primitives", "src/coins")):
        return 1 << 3
    if "mempool" in p or "src/policy" in p:
        return 1 << 4
    if p.startswith(("build", "cmake", "ci/", ".github")) or "makefile" in p or "/ci/" in p:
        return 1 << 5
    if p.startswith(("src/test", "test/")) or "/test/" in p:
        return 1 << 6
    if p.startswith("doc/") or p.endswith(".md"):
        return 1 << 7
    return 0


def is_rule_path(path: str, title: str) -> bool:
    return bool(RULE_FILE_RE.search(path or "") or RULE_TITLE_RE.search(title or ""))


def topic_mask(text: str) -> int:
    mask = 0
    for i, name in enumerate(TOPIC_NAMES):
        if TOPIC_RES[name].search(text or ""):
            mask |= 1 << i
    return mask


def login_of(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("login") or value.get("name") or "")
    if value is None:
        return ""
    return str(value)


def irc_bot(nick: str) -> bool:
    n = (nick or "").lower().lstrip("@+")
    return (not n) or n.startswith("github") or n in {"gribble"} or is_bot_login(n)


class People:
    def __init__(self) -> None:
        self.ids: Dict[str, int] = {}
        self.labels: List[str] = []

    def add(self, ident: str, label: str = "") -> int:
        if not ident:
            return -1
        idx = self.ids.get(ident)
        if idx is None:
            idx = len(self.labels)
            self.ids[ident] = idx
            self.labels.append(label or ident)
        return idx


def reciprocity_index(reviewer: np.ndarray, author: np.ndarray, ts: np.ndarray, window: float = 30 * DAY) -> float:
    """Share of attention events reciprocated the other way within `window` seconds."""
    hits, opps = reciprocity_counts(reviewer, author, ts, window=window)
    total_h = sum(hits.values())
    total_o = sum(opps.values())
    if total_o == 0:
        return float("nan")
    return total_h / total_o


def reciprocity_counts(
    reviewer: np.ndarray,
    author: np.ndarray,
    ts: np.ndarray,
    years: Optional[np.ndarray] = None,
    window: float = 30 * DAY,
) -> Tuple[Dict[int, int], Dict[int, int]]:
    """Hits and opportunities by year. Year 0 means the caller did not pass years."""
    idx: Dict[Tuple[int, int], List[float]] = defaultdict(list)
    rev = reviewer.tolist()
    aut = author.tolist()
    times = ts.tolist()
    year_list = [0] * len(times) if years is None else years.tolist()
    for r, a, t in zip(rev, aut, times):
        if r == a or r < 0 or a < 0:
            continue
        idx[(int(r), int(a))].append(float(t))
    hits: Dict[int, int] = defaultdict(int)
    opps: Dict[int, int] = defaultdict(int)
    for r, a, t, y in zip(rev, aut, times, year_list):
        if r == a or r < 0 or a < 0:
            continue
        year = int(y)
        opps[year] += 1
        lst = idx.get((int(a), int(r)))
        if not lst:
            continue
        lo = bisect_right(lst, float(t))
        hi = bisect_right(lst, float(t) + window)
        if hi > lo:
            hits[year] += 1
    return hits, opps


def _pool_rate(hits: Dict[int, int], opps: Dict[int, int], pred) -> float:
    h = o = 0
    for year, opportunities in opps.items():
        if pred(year):
            h += hits.get(year, 0)
            o += opportunities
    if o == 0:
        return float("nan")
    return h / o


def dnm_accommodation(partner: np.ndarray, speaker: np.ndarray) -> Optional[float]:
    """Mean over categories of P(speaker|partner) minus P(speaker|not partner)."""
    if partner.size == 0:
        return None
    acc: List[float] = []
    for k in range(partner.shape[1]):
        p = partner[:, k].astype(bool)
        s = speaker[:, k].astype(bool)
        if not p.any() or not (~p).any():
            continue
        acc.append(float(s[p].mean() - s[~p].mean()))
    if not acc:
        return None
    return float(np.mean(acc))


def _fit_beta(x_mat: np.ndarray, y: np.ndarray, binary: bool) -> Optional[np.ndarray]:
    if binary:
        return logistic_irls(x_mat, y)
    beta = np.linalg.lstsq(x_mat, y, rcond=1e-8)[0]
    if beta.size != x_mat.shape[1] or not np.all(np.isfinite(beta)):
        return None
    return beta


def regress(
    y: np.ndarray,
    focals: Sequence[np.ndarray],
    covariates: Sequence[np.ndarray],
    years: np.ndarray,
    rng: np.random.Generator,
    n_boot: int,
    binary: bool,
    focal_index: int = 0,
) -> Optional[Dict[str, Any]]:
    """Year fixed effects plus covariates. Focal columns are standardized inside the sample."""
    mask = np.isfinite(y) & np.isfinite(years)
    for focal in focals:
        mask &= np.isfinite(focal)
    for cov in covariates:
        mask &= np.isfinite(cov)
    if int(mask.sum()) < 40:
        return None
    y_m = y[mask].astype(float)
    if binary:
        y_m = (y_m > 0).astype(float)
        if np.unique(y_m).size < 2:
            return None
    elif np.nanstd(y_m) < 1e-12:
        return None
    blocks: List[np.ndarray] = [np.ones(y_m.size)]
    for focal in focals:
        col = focal[mask].astype(float)
        sd = float(np.std(col))
        if sd < 1e-12:
            return None
        blocks.append((col - float(np.mean(col))) / sd)
    for cov in covariates:
        col = cov[mask].astype(float)
        sd = float(np.std(col))
        if sd < 1e-12:
            continue
        blocks.append((col - float(np.mean(col))) / sd)
    year_m = years[mask].astype(int)
    levels = np.unique(year_m)
    if levels.size >= 2:
        for lev in levels[1:]:
            blocks.append((year_m == lev).astype(float))
    x_mat = np.column_stack(blocks)
    if focal_index + 1 >= x_mat.shape[1]:
        return None
    point = _fit_beta(x_mat, y_m, binary)
    if point is None:
        return None
    draws = np.empty(n_boot, dtype=float)
    fails = 0
    n = y_m.size
    col = focal_index + 1
    for i in range(n_boot):
        ix = rng.integers(0, n, size=n)
        beta = _fit_beta(x_mat[ix], y_m[ix], binary)
        if beta is None or not np.isfinite(beta[col]):
            draws[i] = np.nan
            fails += 1
        else:
            draws[i] = beta[col]
    if fails > 0.2 * n_boot:
        return None
    estimate = float(point[col])
    return {
        "estimate": estimate,
        "ci95": ci_from_draws(draws),
        "p": p_from_draws(draws),
        "n": int(n),
        "n_bootstrap_failed": int(fails),
        "model": "logistic" if binary else "ols",
        "standardized_focal": True,
        "year_fixed_effects": bool(levels.size >= 2),
    }


def group_diff(
    a: np.ndarray,
    b: np.ndarray,
    rng: np.random.Generator,
    n_boot: int,
) -> Optional[Dict[str, Any]]:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    a = a[np.isfinite(a)]
    b = b[np.isfinite(b)]
    if a.size < 5 or b.size < 5:
        return None
    point = float(a.mean() - b.mean())
    draws = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        draws[i] = float(a[rng.integers(0, a.size, a.size)].mean() - b[rng.integers(0, b.size, b.size)].mean())
    d = cohens_d(a, b)
    return {
        "estimate": point,
        "ci95": ci_from_draws(draws),
        "p": p_from_draws(draws),
        "n_a": int(a.size),
        "n_b": int(b.size),
        "n": int(a.size + b.size),
        "cohens_d": d,
        "effect_size_flag": effect_flag(d),
        "model": "difference_of_means",
    }


class SlidingTop:
    """Top-k identities in a trailing window. Queries must be nondecreasing in time."""

    def __init__(self, events: Sequence[Tuple[float, int]], window: float, k: int) -> None:
        self.events = sorted(events, key=lambda item: item[0])
        self.window = window
        self.k = k
        self.i = 0
        self.j = 0
        self.counts: Dict[int, int] = defaultdict(int)

    def advance(self, t: float) -> None:
        ev = self.events
        while self.i < len(ev) and ev[self.i][0] < t:
            self.counts[ev[self.i][1]] += 1
            self.i += 1
        cutoff = t - self.window
        while self.j < self.i and ev[self.j][0] < cutoff:
            person = ev[self.j][1]
            self.counts[person] -= 1
            if self.counts[person] <= 0:
                del self.counts[person]
            self.j += 1

    def topset(self) -> Optional[set]:
        if len(self.counts) < self.k:
            return None
        picked = heapq.nlargest(self.k, self.counts.items(), key=lambda kv: (kv[1], kv[0]))
        return {person for person, _count in picked}

    def contains(self, person: int) -> Optional[bool]:
        top = self.topset()
        if top is None:
            return None
        return person in top


def put_metric(
    store: Dict[Tuple[str, int, str], Optional[float]],
    seen: Dict[str, str],
    metric: str,
    repo: str,
    year: int,
    value: Optional[float],
) -> None:
    spec = SCORING_SPEC[metric]
    prev = seen.get(metric)
    if prev is not None and prev != spec["part"]:
        raise RuntimeError(f"{metric} registered as {prev} and {spec['part']}")
    if spec["part"] == "C" and metric in metric_ids("B"):
        raise RuntimeError(f"health metric reuses a principle indicator: {metric}")
    if spec["part"] == "C" and metric in metric_ids("A"):
        raise RuntimeError(f"health metric reuses an effect indicator: {metric}")
    seen[metric] = spec["part"]
    if value is None or not np.isfinite(value):
        store[(repo, year, metric)] = None
    else:
        store[(repo, year, metric)] = float(value)


def load_core(path: Path, ident: Any, people: People) -> Dict[str, Any]:
    numbers: List[int] = []
    author: List[int] = []
    created: List[float] = []
    years: List[int] = []
    merged: List[int] = []
    merged_at: List[float] = []
    closed_at: List[float] = []
    decided: List[int] = []
    lines: List[float] = []
    files_n: List[float] = []
    merger: List[int] = []
    rule: List[int] = []
    scope: List[int] = []
    topics: List[int] = []
    subsys: List[int] = []
    concept: List[int] = []
    full: List[int] = []
    first_concept: List[float] = []
    first_peer: List[float] = []
    first_tone: List[float] = []
    later_sum: List[float] = []
    later_n: List[int] = []
    signal_ts: List[float] = []
    signal_person: List[int] = []
    signal_dir: List[int] = []
    participants: List[int] = []
    sanction: List[int] = []
    maintainer_author: List[int] = []
    events: List[Tuple[int, int, float, float, int, int, int, int, int, int]] = []
    review_objects: List[Tuple[float, int]] = []
    activity: Dict[int, List[float]] = defaultdict(list)
    alt_rows: List[Tuple[int, float]] = []
    dropped_bots = 0
    n_read = 0

    with path.open() as handle:
        for line in handle:
            n_read += 1
            pr = json.loads(line)
            login = login_of(pr.get("author"))
            who = ident.ident(login, irc=False)
            if not who:
                dropped_bots += 1
                continue
            ts = parse_ts(pr.get("created_at"))
            if ts is None:
                continue
            pr_i = len(numbers)
            author_i = people.add(who, login.lower())
            numbers.append(int(pr.get("number") or 0))
            author.append(author_i)
            created.append(ts)
            years.append(year_of(ts))
            activity[author_i].append(ts)
            is_merged = bool(pr.get("merged"))
            m_at = parse_ts(pr.get("merged_at")) if is_merged else None
            c_at = parse_ts(pr.get("closed_at"))
            merged.append(1 if is_merged else 0)
            merged_at.append(m_at if m_at is not None else np.nan)
            closed_at.append(c_at if c_at is not None else np.nan)
            state = str(pr.get("state") or "").lower()
            is_decided = is_merged or state == "closed" or c_at is not None
            decided.append(1 if is_decided else 0)
            adds = pr.get("total_additions")
            dels = pr.get("total_deletions")
            if adds is None or dels is None:
                comp = pr.get("complexity") or {}
                adds = comp.get("additions") or comp.get("total_changes") or 0
                dels = comp.get("deletions") or 0
            lines.append(float(adds or 0) + float(dels or 0))
            files_n.append(float(pr.get("total_files_changed") or (pr.get("complexity") or {}).get("files_changed") or 0))
            merger_login = login_of(pr.get("merged_by"))
            merger_id = people.add(ident.ident(merger_login, irc=False), merger_login.lower()) if is_merged else -1
            merger.append(merger_id)
            title = pr.get("title") or ""
            body = pr.get("body") or ""
            header = f"{title}\n{body}"
            bits = 0
            rule_flag = is_rule_path("", title)
            for fobj in pr.get("files") or []:
                fname = fobj.get("filename") if isinstance(fobj, dict) else str(fobj)
                bits |= subsystem_bit(fname or "")
                if is_rule_path(fname or "", title):
                    rule_flag = True
            subsys.append(bits)
            rule.append(1 if rule_flag else 0)
            scope_flag = 1 if SCOPE_RE.search(header) else 0
            tmask = topic_mask(header)
            if ALT_RE.search(header):
                alt_rows.append((year_of(ts), keyword_tone(header[:2000])))
            labels = pr.get("labels") or []
            sanctioned = False
            for lab in labels:
                name = lab.get("name") if isinstance(lab, dict) else str(lab)
                if re.search(r"lock|ban|moderat", str(name), re.I):
                    sanctioned = True
            if SANCTION_RE.search(header):
                sanctioned = True

            # person-day collapse of attention on this PR
            bucket: Dict[Tuple[int, int], Dict[str, Any]] = {}
            review_people: set = set()
            concept_ts = np.inf
            has_concept = False
            has_full = False
            peer_ts = np.inf
            tone0 = np.nan
            tone0_ts = np.inf
            lsum = 0.0
            ln = 0
            sig_ts = np.inf
            sig_person = -1
            sig_dir = 0

            def absorb(person: int, when: float, text: str, state: str, source: str) -> None:
                nonlocal concept_ts, has_concept, has_full, peer_ts, tone0, tone0_ts, lsum, ln
                nonlocal sig_ts, sig_person, sig_dir, scope_flag, tmask, sanctioned
                if person < 0 or when is None:
                    return
                activity[person].append(when)
                ack, nack, conc = stance_flags(text, state)
                tone = keyword_tone(text)
                if source == "review_object" and person != author_i:
                    review_objects.append((when, person))
                if person == author_i:
                    if SANCTION_RE.search(text):
                        sanctioned = True
                    return
                if when < peer_ts:
                    peer_ts = when
                if when < tone0_ts:
                    if np.isfinite(tone0):
                        lsum += tone0
                        ln += 1
                    tone0 = tone
                    tone0_ts = when
                else:
                    lsum += tone
                    ln += 1
                if conc:
                    has_concept = True
                    if when < concept_ts:
                        concept_ts = when
                if source == "review_object" and ((ack and not conc) or state.upper() == "APPROVED"):
                    has_full = True
                if (ack or nack) and when < sig_ts:
                    sig_ts = when
                    sig_person = person
                    sig_dir = -1 if nack else 1
                if SCOPE_RE.search(text):
                    scope_flag = 1
                tmask |= topic_mask(text)
                if ALT_RE.search(text):
                    alt_rows.append((year_of(when), tone))
                if SANCTION_RE.search(text):
                    sanctioned = True
                tokens = tokenize(text)
                harsh = 1 if (HARSH_RE.search(text) and tone < 0) else 0
                day = int(when // DAY)
                key = (person, day)
                slot = bucket.get(key)
                if slot is None:
                    bucket[key] = {
                        "ts": when, "tone": tone, "words": len(tokens), "harsh": harsh,
                        "jargon": 1 if jargon_hit(text) else 0, "fw": fw_mask(tokens),
                        "ack": 1 if ack else 0, "nack": 1 if nack else 0,
                    }
                else:
                    if when < slot["ts"]:
                        slot["ts"] = when
                    slot["tone"] = tone
                    slot["words"] += len(tokens)
                    slot["harsh"] = max(slot["harsh"], harsh)
                    slot["jargon"] = max(slot["jargon"], 1 if jargon_hit(text) else 0)
                    slot["fw"] |= fw_mask(tokens)
                    slot["ack"] = max(slot["ack"], 1 if ack else 0)
                    slot["nack"] = max(slot["nack"], 1 if nack else 0)
                review_people.add(person)

            for rev in pr.get("reviews") or []:
                rlogin = login_of(rev.get("author") or rev.get("user"))
                rid = people.add(ident.ident(rlogin, irc=False), rlogin.lower())
                when = parse_ts(rev.get("submitted_at") or rev.get("created_at"))
                if when is None:
                    continue
                absorb(rid, when, rev.get("body") or "", str(rev.get("state") or ""), "review_object")
            for com in pr.get("comments") or []:
                clogin = login_of(com.get("author") or com.get("user"))
                cid = people.add(ident.ident(clogin, irc=False), clogin.lower())
                when = parse_ts(com.get("created_at"))
                if when is None:
                    continue
                absorb(cid, when, com.get("body") or "", "", "comment")
            for com in pr.get("review_comments") or []:
                clogin = login_of(com.get("author") or com.get("user"))
                cid = people.add(ident.ident(clogin, irc=False), clogin.lower())
                when = parse_ts(com.get("created_at"))
                if when is None:
                    continue
                absorb(cid, when, com.get("body") or "", "", "line")

            for (person, _day), slot in bucket.items():
                events.append((
                    pr_i, person, float(slot["ts"]), float(slot["tone"]), int(slot["words"]),
                    int(slot["harsh"]), int(slot["jargon"]), int(slot["fw"]), int(slot["ack"]), int(slot["nack"]),
                ))
            scope.append(scope_flag)
            topics.append(tmask)
            concept.append(1 if has_concept else 0)
            full.append(1 if has_full else 0)
            first_concept.append(concept_ts if np.isfinite(concept_ts) else np.nan)
            first_peer.append(peer_ts if np.isfinite(peer_ts) else np.nan)
            first_tone.append(tone0)
            later_sum.append(lsum)
            later_n.append(ln)
            signal_ts.append(sig_ts if np.isfinite(sig_ts) else np.nan)
            signal_person.append(sig_person)
            signal_dir.append(sig_dir)
            participants.append(len(review_people))
            sanction.append(1 if sanctioned else 0)
            maintainer_author.append(0)

    for rows in activity.values():
        rows.sort()
    return {
        "n_read": n_read,
        "dropped_bot_authors": dropped_bots,
        "number": np.asarray(numbers, dtype=np.int32),
        "author": np.asarray(author, dtype=np.int32),
        "created": np.asarray(created, dtype=float),
        "year": np.asarray(years, dtype=np.int16),
        "merged": np.asarray(merged, dtype=np.int8),
        "merged_at": np.asarray(merged_at, dtype=float),
        "closed_at": np.asarray(closed_at, dtype=float),
        "decided": np.asarray(decided, dtype=np.int8),
        "lines": np.asarray(lines, dtype=float),
        "files": np.asarray(files_n, dtype=float),
        "merger": np.asarray(merger, dtype=np.int32),
        "rule": np.asarray(rule, dtype=np.int8),
        "scope": np.asarray(scope, dtype=np.int8),
        "topics": np.asarray(topics, dtype=np.int16),
        "subsys": np.asarray(subsys, dtype=np.int16),
        "concept": np.asarray(concept, dtype=np.int8),
        "full": np.asarray(full, dtype=np.int8),
        "first_concept": np.asarray(first_concept, dtype=float),
        "first_peer": np.asarray(first_peer, dtype=float),
        "first_tone": np.asarray(first_tone, dtype=float),
        "later_sum": np.asarray(later_sum, dtype=float),
        "later_n": np.asarray(later_n, dtype=np.int32),
        "signal_ts": np.asarray(signal_ts, dtype=float),
        "signal_person": np.asarray(signal_person, dtype=np.int32),
        "signal_dir": np.asarray(signal_dir, dtype=np.int8),
        "participants": np.asarray(participants, dtype=np.int32),
        "sanction": np.asarray(sanction, dtype=np.int8),
        "maintainer_author": np.asarray(maintainer_author, dtype=np.int8),
        "events": events,
        "review_objects": review_objects,
        "activity": activity,
        "alt_rows": alt_rows,
        "people": people,
    }


def load_thin(path: Path) -> Dict[str, Any]:
    author: List[str] = []
    created: List[float] = []
    years: List[int] = []
    merged: List[int] = []
    merged_at: List[float] = []
    closed_at: List[float] = []
    decided: List[int] = []
    rule: List[int] = []
    scope: List[int] = []
    topics: List[int] = []
    sanction: List[int] = []
    alt: List[Tuple[int, float]] = []
    with path.open() as handle:
        for line in handle:
            pr = json.loads(line)
            login = login_of(pr.get("author")).lower()
            if not login or is_bot_login(login):
                continue
            ts = parse_ts(pr.get("created_at"))
            if ts is None:
                continue
            author.append(login)
            created.append(ts)
            years.append(year_of(ts))
            is_merged = bool(pr.get("merged"))
            m_at = parse_ts(pr.get("merged_at")) if is_merged else None
            c_at = parse_ts(pr.get("closed_at"))
            merged.append(1 if is_merged else 0)
            merged_at.append(m_at if m_at is not None else np.nan)
            closed_at.append(c_at if c_at is not None else np.nan)
            state = str(pr.get("state") or "").lower()
            decided.append(1 if is_merged or state == "closed" or c_at is not None else 0)
            text = f"{pr.get('title') or ''}\n{pr.get('body') or ''}"
            rule.append(1 if is_rule_path("", pr.get("title") or "") or RULE_FILE_RE.search(text) else 0)
            scope.append(1 if SCOPE_RE.search(text) else 0)
            topics.append(topic_mask(text))
            sanction.append(1 if SANCTION_RE.search(text) else 0)
            if ALT_RE.search(text):
                alt.append((year_of(ts), keyword_tone(text[:2000])))
    return {
        "author": author,
        "created": np.asarray(created, dtype=float),
        "year": np.asarray(years, dtype=np.int16),
        "merged": np.asarray(merged, dtype=np.int8),
        "merged_at": np.asarray(merged_at, dtype=float),
        "closed_at": np.asarray(closed_at, dtype=float),
        "decided": np.asarray(decided, dtype=np.int8),
        "rule": np.asarray(rule, dtype=np.int8),
        "scope": np.asarray(scope, dtype=np.int8),
        "topics": np.asarray(topics, dtype=np.int16),
        "sanction": np.asarray(sanction, dtype=np.int8),
        "alt": alt,
    }


def discover_repos(data_dir: Path) -> List[Tuple[str, Path]]:
    root = data_dir / "github" / "repos"
    found = []
    if not root.exists():
        return found
    for prs in sorted(root.glob("*/*/prs.jsonl")):
        found.append((f"{prs.parts[-3]}/{prs.parts[-2]}", prs))
    return found


def venue_years_from_regex(path: Path, pattern: re.Pattern, missing: List[Dict[str, str]], metric: str) -> set:
    years: set = set()
    if not path.exists():
        unavailable(missing, metric, f"{path} is not in the dataset")
        return years
    with path.open("rb") as handle:
        for line in handle:
            match = pattern.search(line)
            if match:
                years.add(int(match.group(1)))
    return years


def scan_irc_and_mail(
    data_dir: Path,
    ident: Any,
    people: People,
    number_to_index: Dict[int, int],
    grant_windows: List[Dict[str, Any]],
    missing: List[Dict[str, str]],
) -> Dict[str, Any]:
    irc_path = data_dir / "irc" / "messages.jsonl"
    listed: Dict[int, float] = {}
    listed_by: Dict[int, str] = {}
    request_types: Dict[str, int] = defaultdict(int)
    irc_years: set = set()
    grant_hits = [0 for _ in grant_windows]
    n_topics = 0
    if not irc_path.exists():
        unavailable(missing, "E9", "data/irc/messages.jsonl is not in the dataset")
        unavailable(missing, "P1a_grant_discussion_share", "IRC archive is missing, so grant discussion cannot be checked")
    else:
        in_window = False
        window_end = 0.0
        with irc_path.open() as handle:
            for line in handle:
                msg = json.loads(line)
                ts = parse_ts(msg.get("timestamp") or msg.get("time"))
                if ts is None:
                    continue
                irc_years.add(year_of(ts))
                text = msg.get("message") or msg.get("content") or ""
                nick = msg.get("nickname") or msg.get("author") or ""
                low_nick = nick.lower().lstrip("@+")
                blob = f"{low_nick} {text.lower()}"
                for i, window in enumerate(grant_windows):
                    if window["start"] - 30 * DAY <= ts <= window["start"] and any(term in blob for term in window["terms"]):
                        grant_hits[i] = 1
                if ANY_TOPIC_RE.search(text):
                    in_window = bool(PRIORITY_TOPIC_RE.search(text))
                    window_end = ts + 40 * 60
                    if in_window:
                        n_topics += 1
                elif in_window and ts > window_end:
                    in_window = False
                if not in_window:
                    continue
                nums = {int(n) for n in PULL_URL_RE.findall(text)}
                nums.update(int(n) for n in HASH_RE.findall(text))
                if not nums or irc_bot(nick):
                    continue
                who = ident.ident(nick, irc=True)
                for num in nums:
                    if num not in number_to_index:
                        continue
                    prev = listed.get(num)
                    if prev is None or ts < prev:
                        listed[num] = ts
                        listed_by[num] = who or ""
                    request_types[who or "unresolved"] += 1
    mail_path = data_dir / "mailing_lists" / "emails.jsonl"
    mail_years: set = set()
    if not mail_path.exists():
        unavailable(missing, "P8b_venue_count", "mailing list archive is missing; venue count will omit it")
    else:
        with mail_path.open() as handle:
            for line in handle:
                mail = json.loads(line)
                ts = parse_ts(mail.get("date"))
                if ts is None:
                    continue
                mail_years.add(year_of(ts))
                if not grant_windows:
                    continue
                # Cheap reject before building a search blob.
                if not any(w["start"] - 30 * DAY <= ts <= w["start"] for w in grant_windows):
                    continue
                blob = f"{mail.get('from') or ''} {mail.get('subject') or ''} {(mail.get('body') or '')[:500]}".lower()
                for i, window in enumerate(grant_windows):
                    if window["start"] - 30 * DAY <= ts <= window["start"] and any(term in blob for term in window["terms"]):
                        grant_hits[i] = 1
    return {
        "listed": listed,
        "listed_by": listed_by,
        "request_counts_by_ident": dict(request_types),
        "n_priority_topics": n_topics,
        "irc_years": irc_years,
        "mail_years": mail_years,
        "grant_hits": grant_hits,
    }


def controls_for_core(core: Dict[str, Any], maintainer_ids: set) -> Dict[str, np.ndarray]:
    n = core["created"].size
    author = core["author"]
    created = core["created"]
    order = np.argsort(created, kind="mergesort")
    first_ts = np.empty(n, dtype=float)
    seen: Dict[int, float] = {}
    for i in order:
        person = int(author[i])
        if person not in seen:
            seen[person] = float(created[i])
        first_ts[i] = seen[person]
    prior = np.zeros(n, dtype=float)
    by_author: Dict[int, List[int]] = defaultdict(list)
    for i in order:
        by_author[int(author[i])].append(int(i))
    for idxs in by_author.values():
        mtimes = sorted(
            float(core["merged_at"][i])
            for i in idxs
            if core["merged"][i] and np.isfinite(core["merged_at"][i])
        )
        for i in idxs:
            prior[i] = bisect_left(mtimes, float(created[i]))
    tenure = (created - first_ts) / YEAR
    # Rolling in-group from review objects only, matching pass 2's instrument.
    slider = SlidingTop([(float(t), int(p)) for t, p in core["review_objects"] if p >= 0], WINDOW, TOP_N)
    ingroup = np.full(n, np.nan)
    unidentified = np.zeros(n, dtype=float)
    for i in order:
        slider.advance(float(created[i]))
        flag = slider.contains(int(author[i]))
        if flag is None:
            unidentified[i] = 1.0
            ingroup[i] = 0.0
        else:
            ingroup[i] = 1.0 if flag else 0.0
    merger_first: Dict[int, float] = {}
    for i in range(n):
        m = int(core["merger"][i])
        if m < 0 or not np.isfinite(core["merged_at"][i]):
            continue
        merger_first[m] = min(merger_first.get(m, np.inf), float(core["merged_at"][i]))
    core["maintainer_author"][:] = np.array([1 if int(a) in maintainer_ids else 0 for a in author], dtype=np.int8)
    log_lines = np.log1p(np.clip(core["lines"], 0, None))
    return {
        "tenure": tenure,
        "prior": prior,
        "ingroup": ingroup,
        "unidentified": unidentified,
        "log_lines": log_lines,
        "files": core["files"].astype(float),
        "first_ts": first_ts,
        "merger_first": merger_first,
    }


def shared_covariates(
    ctrl: Dict[str, np.ndarray],
    idx: np.ndarray,
    *,
    include_prior: bool = True,
) -> List[np.ndarray]:
    """Shared controls. Omit prior merges when that variable is already the focal, so it is not entered twice."""
    cols = [
        ctrl["log_lines"][idx],
        ctrl["files"][idx],
        ctrl["tenure"][idx],
    ]
    if include_prior:
        cols.append(ctrl["prior"][idx])
    cols.extend([ctrl["ingroup"][idx], ctrl["unidentified"][idx]])
    return cols


def add_test(
    tests: List[Dict[str, Any]],
    *,
    test_id: str,
    effect: Optional[str],
    estimate: Optional[float],
    ci: Optional[Sequence[float]],
    p: Optional[float],
    n: Optional[int],
    kind: str,
    effect_size: Optional[float] = None,
    effect_size_flag: Optional[str] = None,
    holdout: Optional[Dict[str, Any]] = None,
    principles: Optional[Sequence[str]] = None,
    note: str = "",
    family: bool = True,
    low_observability: bool = False,
) -> None:
    same = None
    if holdout and holdout.get("estimate") is not None and estimate is not None:
        if holdout["estimate"] == 0 or estimate == 0:
            same = bool(np.sign(holdout["estimate"]) == np.sign(estimate))
        else:
            same = bool(np.sign(holdout["estimate"]) == np.sign(estimate))
    elif holdout and holdout.get("status") == "DATA UNAVAILABLE":
        same = None
    tests.append({
        "id": test_id,
        "effect": effect,
        "mapped_principles": list(principles if principles is not None else SCORING_SPEC.get(effect or "", {}).get("maps", [])),
        "estimate": estimate,
        "ci95": list(ci) if ci else None,
        "p": p,
        "q": None,
        "n": n,
        "effect_size": effect_size if effect_size is not None else estimate,
        "effect_size_kind": kind,
        "effect_size_flag": effect_size_flag,
        "holdout_estimate": None if not holdout else holdout.get("estimate"),
        "holdout_ci95": None if not holdout else holdout.get("ci95"),
        "holdout_n": None if not holdout else holdout.get("n"),
        "holdout_same_sign": same,
        "holdout_status": None if not holdout else holdout.get("status"),
        "sample": "2010-2023",
        "in_bh_family": family,
        "low_observability": low_observability,
        "note": note,
        "source": "pass3",
    })


def fit_split(
    y: np.ndarray,
    focal: np.ndarray,
    cov: Sequence[np.ndarray],
    years: np.ndarray,
    rng: np.random.Generator,
    n_boot: int,
    binary: bool,
    extra_focal: Optional[np.ndarray] = None,
    focal_index: int = 0,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    train = years <= TRAIN_LAST_YEAR
    hold = years >= HOLDOUT_FIRST_YEAR
    focals = [focal] if extra_focal is None else [focal, extra_focal]
    cov_t = [c[train] for c in cov]
    cov_h = [c[hold] for c in cov]
    train_fit = regress(y[train], [f[train] for f in focals], cov_t, years[train], rng, n_boot, binary, focal_index)
    hold_fit = regress(y[hold], [f[hold] for f in focals], cov_h, years[hold], rng, n_boot, binary, focal_index)
    return train_fit, hold_fit


def hold_pack(fit: Optional[Dict[str, Any]], reason: str) -> Dict[str, Any]:
    if fit is None:
        return {"status": "DATA UNAVAILABLE", "reason": reason, "estimate": None, "ci95": None, "n": None}
    return {"status": "ok", "estimate": fit["estimate"], "ci95": fit["ci95"], "n": fit["n"]}


def record_regression(
    tests: List[Dict[str, Any]],
    test_id: str,
    effect: str,
    train_fit: Optional[Dict[str, Any]],
    hold_fit: Optional[Dict[str, Any]],
    missing: List[Dict[str, str]],
    note: str,
    low_observability: bool = False,
    kind: str = "standardized_coefficient",
) -> None:
    if train_fit is None:
        unavailable(missing, test_id, "the training model did not fit (too few rows, no outcome variation, or singular design)")
        add_test(
            tests, test_id=test_id, effect=effect, estimate=None, ci=None, p=None, n=None,
            kind=kind, family=False, note=note, low_observability=low_observability,
            holdout={"status": "DATA UNAVAILABLE", "estimate": None},
        )
        return
    hold = hold_pack(hold_fit, "the 2024-2026 model did not fit")
    if hold_fit is None:
        unavailable(missing, test_id + "_holdout", hold["reason"])
    flag = None
    if kind == "cohens_d":
        flag = effect_flag(train_fit["estimate"])
    add_test(
        tests, test_id=test_id, effect=effect, estimate=train_fit["estimate"], ci=train_fit["ci95"],
        p=train_fit["p"], n=train_fit["n"], kind=kind, effect_size_flag=flag, holdout=hold,
        note=note, low_observability=low_observability,
    )


def yearly_coef(
    y: np.ndarray,
    focal: np.ndarray,
    cov: Sequence[np.ndarray],
    years: np.ndarray,
    binary: bool,
) -> Dict[int, float]:
    out: Dict[int, float] = {}
    for year in sorted(set(int(v) for v in years if np.isfinite(v))):
        m = years == year
        if int(m.sum()) < 40:
            continue
        fit = regress(y[m], [focal[m]], [c[m] for c in cov], years[m], np.random.default_rng(SEED), n_boot=1, binary=binary)
        # n_boot=1 still runs one fit; use the point estimate only.
        if fit is None:
            # regress with n_boot=1 still bootstraps once and can fail the 20% rule only if that one fails.
            point = _point_only(y[m], focal[m], [c[m] for c in cov], binary)
            if point is None:
                continue
            out[year] = point
        else:
            out[year] = float(fit["estimate"])
    return out


def _point_only(y: np.ndarray, focal: np.ndarray, cov: Sequence[np.ndarray], binary: bool) -> Optional[float]:
    mask = np.isfinite(y) & np.isfinite(focal)
    for c in cov:
        mask &= np.isfinite(c)
    if int(mask.sum()) < 40:
        return None
    y_m = y[mask].astype(float)
    col = focal[mask].astype(float)
    sd = float(np.std(col))
    if sd < 1e-12:
        return None
    blocks = [np.ones(y_m.size), (col - float(np.mean(col))) / sd]
    for c in cov:
        v = c[mask].astype(float)
        s = float(np.std(v))
        if s >= 1e-12:
            blocks.append((v - float(np.mean(v))) / s)
    x_mat = np.column_stack(blocks)
    beta = _fit_beta(x_mat, (y_m > 0).astype(float) if binary else y_m, binary)
    if beta is None:
        return None
    return float(beta[1])


def events_frame(events: List[Tuple]) -> Dict[str, np.ndarray]:
    if not events:
        z = np.zeros(0, dtype=np.int32)
        return {k: z for k in ("pr", "person", "words", "harsh", "jargon", "fw", "ack", "nack")} | {
            "ts": np.zeros(0), "tone": np.zeros(0),
        }
    arr = list(zip(*events))
    return {
        "pr": np.asarray(arr[0], dtype=np.int32),
        "person": np.asarray(arr[1], dtype=np.int32),
        "ts": np.asarray(arr[2], dtype=float),
        "tone": np.asarray(arr[3], dtype=float),
        "words": np.asarray(arr[4], dtype=np.int32),
        "harsh": np.asarray(arr[5], dtype=np.int8),
        "jargon": np.asarray(arr[6], dtype=np.int8),
        "fw": np.asarray(arr[7], dtype=np.int16),
        "ack": np.asarray(arr[8], dtype=np.int8),
        "nack": np.asarray(arr[9], dtype=np.int8),
    }


def comment_gaps(ev: Dict[str, np.ndarray]) -> np.ndarray:
    gap = np.full(ev["ts"].size, np.nan)
    order = np.lexsort((ev["ts"], ev["pr"]))
    prev_ts: Dict[int, float] = {}
    prev_person: Dict[int, int] = {}
    for k in order:
        pr = int(ev["pr"][k])
        person = int(ev["person"][k])
        if pr in prev_ts and prev_person[pr] != person:
            gap[k] = float(ev["ts"][k] - prev_ts[pr])
        prev_ts[pr] = float(ev["ts"][k])
        prev_person[pr] = person
    return gap


def window_stats(rows: List[Tuple[float, float, float, float]], t0: float, t1: float) -> Optional[Tuple[float, float, float]]:
    """Mean words, tone, gap on [t0, t1). rows are (ts, words, tone, gap)."""
    lo = bisect_left(rows, (t0,))
    hi = bisect_left(rows, (t1,))
    if hi - lo < 5:
        return None
    words = tone = gaps = 0.0
    ng = 0
    for i in range(lo, hi):
        _ts, w, tn, g = rows[i]
        words += w
        tone += tn
        if np.isfinite(g):
            gaps += g
            ng += 1
    n = hi - lo
    return words / n, tone / n, (gaps / ng if ng else np.nan)


def analyze(n_boot: int = N_BOOT_DEFAULT, n_perm: int = N_PERM_DEFAULT, seed: int = SEED) -> Dict[str, Any]:
    assert_measurement_sets_disjoint()
    rng = np.random.default_rng(seed)
    data_dir = get_data_dir()
    findings = get_findings_dir()
    missing: List[Dict[str, str]] = []
    tests: List[Dict[str, Any]] = []
    seen: Dict[str, str] = {}
    store: Dict[Tuple[str, int, str], Optional[float]] = {}
    detail: Dict[str, Any] = {}
    yearly_strength: Dict[str, Dict[int, float]] = {key: {} for key in metric_ids("A")}

    pr_path = data_dir / "processed" / "enriched_prs.jsonl"
    if not pr_path.exists():
        unavailable(missing, "ALL", f"{pr_path} is not in the dataset")
        raise RuntimeError("enriched PR file is required")
    ident = load_identity()
    people = People()
    logger.info("loading core PRs")
    core = load_core(pr_path, ident, people)
    logger.info("core PRs %s", core["created"].size)

    canon_path = data_dir / "maintainers" / "canonical_maintainers.json"
    canon = json.loads(canon_path.read_text()) if canon_path.exists() else {"github_logins": [], "aliases": {}}
    maintainer_ids = set()
    for login in canon.get("github_logins") or []:
        who = ident.ident(str(login), irc=False)
        if who and who in people.ids:
            maintainer_ids.add(people.ids[who])
    ctrl = controls_for_core(core, maintainer_ids)
    ev = events_frame(core["events"])
    gaps = comment_gaps(ev)
    n = core["created"].size
    dataset_end = float(np.nanmax(np.concatenate([
        core["created"],
        core["merged_at"][np.isfinite(core["merged_at"])],
        core["closed_at"][np.isfinite(core["closed_at"])],
        ev["ts"] if ev["ts"].size else core["created"],
    ])))
    number_to_index = {int(num): i for i, num in enumerate(core["number"].tolist()) if int(num) > 0}

    # Grant windows from the maintainer timeline. Starts are inferred from first observed merge.
    timeline_path = data_dir / "processed" / "maintainer_timeline.json"
    grant_windows: List[Dict[str, Any]] = []
    if not timeline_path.exists():
        unavailable(missing, "P1a_grant_discussion_share", "maintainer_timeline.json is missing, so merge-right starts are unknown")
    else:
        doc = json.loads(timeline_path.read_text())
        aliases = {str(k).lower(): str(v).lower() for k, v in (canon.get("aliases") or {}).items()}
        for _login, row in (doc.get("maintainer_timeline") or {}).items():
            start = parse_ts(row.get("estimated_start") or row.get("first_merge"))
            login = str(row.get("github_login") or _login).lower()
            if start is None:
                continue
            terms = {login, aliases.get(login, login)}
            for alias, target in aliases.items():
                if target == login:
                    terms.add(alias)
            grant_windows.append({"login": login, "start": start, "year": year_of(start), "terms": terms})

    logger.info("scanning IRC, mail, and venues")
    irc = scan_irc_and_mail(data_dir, ident, people, number_to_index, grant_windows, missing)
    bt_years = venue_years_from_regex(
        data_dir / "bitcointalk" / "posts.jsonl",
        re.compile(br'"date": "(\d{4})-'),
        missing, "P8b_venue_count_bitcointalk",
    )
    delving_years = venue_years_from_regex(
        data_dir / "delving" / "posts.jsonl",
        re.compile(br'"created_at": "(\d{4})-'),
        missing, "P8b_venue_count_delving",
    )
    if not (data_dir / "github" / "repos" / "bitcoin-core" / "gui" / "prs.jsonl").exists():
        unavailable(missing, "bitcoin-core/gui", "no PR dump for bitcoin-core/gui is under data/github/repos")

    # ----- Part A -----
    logger.info("part A effects")
    y_fast = (np.isfinite(core["first_peer"]) & ((core["first_peer"] - core["created"]) <= 14 * DAY)).astype(float)
    # Prior merges are the focal here, so they are not also entered as a control.
    e1_cov = shared_covariates(ctrl, np.arange(n), include_prior=False)
    train_fit, hold_fit = fit_split(
        y_fast, ctrl["prior"], e1_cov, core["year"].astype(float),
        rng, n_boot, True,
    )
    record_regression(
        tests, "E1_prior_merges_response_14d", "E1", train_fit, hold_fit, missing,
        "P(peer response within 14 days). Peer response is a review object, issue comment, or line comment. "
        "Linear probability is not used; this is logistic. Focal is prior merge count.",
    )
    sq = ctrl["prior"] ** 2
    train_sq, hold_sq = fit_split(
        y_fast, ctrl["prior"], e1_cov, core["year"].astype(float),
        rng, n_boot, True, extra_focal=sq, focal_index=1,
    )
    record_regression(
        tests, "E1_convexity_prior_squared", "E1", train_sq, hold_sq, missing,
        "Coefficient on prior-merges squared in the same logistic model. Positive means each added merge buys more attention than the last.",
    )
    responded = np.isfinite(core["first_peer"])
    log_hours = np.full(n, np.nan)
    lag_sec = core["first_peer"][responded] - core["created"][responded]
    log_hours[responded] = np.log1p(np.clip(lag_sec, 0, None) / 3600.0)
    train_t, hold_t = fit_split(
        log_hours, ctrl["prior"], e1_cov, core["year"].astype(float),
        rng, n_boot, False,
    )
    record_regression(
        tests, "E1_prior_merges_log_hours_to_response", "E1", train_t, hold_t, missing,
        "Log hours to first peer response, among PRs that received one. PRs with no response are in the 14-day model as failures and out of this timing model.",
    )
    cov_all = shared_covariates(ctrl, np.arange(n))
    yearly_strength["E1"] = {
        int(k): float(v) for k, v in yearly_coef(y_fast, ctrl["prior"], e1_cov, core["year"].astype(float), True).items()
    }

    # E2 reciprocity
    if ev["ts"].size == 0:
        unavailable(missing, "E2", "no peer attention events were loaded")
    else:
        author_of_event = core["author"][ev["pr"]]
        ev_year = np.array([year_of(t) for t in ev["ts"].tolist()], dtype=np.int16)
        obs_hits, obs_opps = reciprocity_counts(ev["person"], author_of_event, ev["ts"], ev_year)
        obs = _pool_rate(obs_hits, obs_opps, lambda _y: True)
        obs_train = _pool_rate(obs_hits, obs_opps, lambda y: y <= TRAIN_LAST_YEAR)
        obs_hold = _pool_rate(obs_hits, obs_opps, lambda y: y >= HOLDOUT_FIRST_YEAR)
        null_train = np.empty(n_perm)
        null_hold = np.empty(n_perm)
        year_levels = sorted(obs_opps)
        null_year = {y: [] for y in year_levels}
        obs_year = {
            y: (obs_hits.get(y, 0) / obs_opps[y]) if obs_opps[y] else float("nan")
            for y in year_levels
        }
        for i in range(n_perm):
            shuffled = ev["person"].copy()
            for y in year_levels:
                ix = np.flatnonzero(ev_year == y)
                if ix.size:
                    shuffled[ix] = rng.permutation(shuffled[ix])
            hits_i, opps_i = reciprocity_counts(shuffled, author_of_event, ev["ts"], ev_year)
            null_train[i] = _pool_rate(hits_i, opps_i, lambda y: y <= TRAIN_LAST_YEAR)
            null_hold[i] = _pool_rate(hits_i, opps_i, lambda y: y >= HOLDOUT_FIRST_YEAR)
            for y in year_levels:
                null_year[y].append(_pool_rate(hits_i, opps_i, lambda year, y=y: year == y))
        def excess_pack(obs_v: float, null_v: np.ndarray, n_events: int) -> Dict[str, Any]:
            if not np.isfinite(obs_v) or null_v.size == 0 or not np.isfinite(null_v).any():
                return {"estimate": None, "ci95": None, "p": None, "n": n_events, "status": "DATA UNAVAILABLE"}
            center = float(np.nanmean(null_v))
            estimate = float(obs_v - center)
            draws = obs_v - null_v
            p = float((np.sum(np.abs(null_v - center) >= abs(obs_v - center)) + 1) / (null_v.size + 1))
            return {
                "estimate": estimate,
                "ci95": ci_from_draws(draws),
                "p": p,
                "n": n_events,
                "status": "ok",
                "observed": float(obs_v),
                "null_mean": center,
            }
        n_train_events = int(sum(v for y, v in obs_opps.items() if y <= TRAIN_LAST_YEAR))
        n_hold_events = int(sum(v for y, v in obs_opps.items() if y >= HOLDOUT_FIRST_YEAR))
        pack = excess_pack(obs_train, null_train, n_train_events)
        hold_pack_e2 = excess_pack(obs_hold, null_hold, n_hold_events)
        if pack["estimate"] is None:
            unavailable(missing, "E2", "reciprocity could not be computed on 2010-2023 events")
        if hold_pack_e2["estimate"] is None:
            unavailable(missing, "E2_holdout", "reciprocity could not be computed on 2024-2026 events")
        add_test(
            tests, test_id="E2_reciprocity_excess", effect="E2", estimate=pack["estimate"], ci=pack["ci95"],
            p=pack["p"], n=pack.get("n"), kind="excess_over_null", holdout=hold_pack_e2,
            note="Attention events are one per reviewer per PR per day. The null shuffles reviewer labels within calendar year,  "
            f"{n_perm} times. Index is the share of events matched by the reverse pair within 30 days.",
        )
        for y, series in null_year.items():
            if obs_year[y] is None or not np.isfinite(obs_year[y]):
                continue
            yearly_strength["E2"][y] = float(obs_year[y] - float(np.nanmean(series)))
        detail["E2"] = {
            "observed_all_years": obs,
            "observed_train": obs_train,
            "null_mean_train": pack.get("null_mean"),
            "permutations": n_perm,
        }

    # E3 status cascades
    sig = np.isfinite(core["signal_ts"]) & (core["signal_dir"] != 0)
    merge_events = [
        (float(core["merged_at"][i]), int(core["merger"][i]))
        for i in range(n)
        if core["merged"][i] and np.isfinite(core["merged_at"][i]) and int(core["merger"][i]) >= 0
    ]
    slider_m = SlidingTop(merge_events, WINDOW, TOP_MERGERS)
    top5_first = np.zeros(n, dtype=np.int8)
    top5_known = np.zeros(n, dtype=np.int8)
    order_sig = np.argsort(np.where(sig, core["signal_ts"], np.inf), kind="mergesort")
    for i in order_sig:
        if not sig[i]:
            break
        slider_m.advance(float(core["signal_ts"][i]))
        flag = slider_m.contains(int(core["signal_person"][i]))
        if flag is None:
            continue
        top5_known[i] = 1
        top5_first[i] = 1 if flag else 0
    # later agreement and time to next same-direction attention
    later_agree = np.full(n, np.nan)
    later_hours = np.full(n, np.nan)
    by_pr: Dict[int, List[int]] = defaultdict(list)
    for k in np.argsort(ev["ts"], kind="mergesort"):
        by_pr[int(ev["pr"][k])].append(int(k))
    for i in np.flatnonzero(sig & top5_known.astype(bool)):
        direction_ack = int(core["signal_dir"][i]) == 1
        start = float(core["signal_ts"][i])
        same_time = None
        agree = 0
        later = 0
        for k in by_pr.get(int(i), []):
            if float(ev["ts"][k]) <= start:
                continue
            if int(ev["person"][k]) == int(core["signal_person"][i]):
                continue
            is_ack = bool(ev["ack"][k])
            is_nack = bool(ev["nack"][k])
            if not is_ack and not is_nack:
                continue
            later += 1
            matches = is_ack if direction_ack else is_nack
            if matches:
                agree += 1
                if same_time is None:
                    same_time = float(ev["ts"][k])
        if later:
            later_agree[i] = agree / later
        if same_time is not None:
            later_hours[i] = (same_time - start) / 3600.0
    known = top5_known.astype(bool) & sig
    train_known = known & (core["year"] <= TRAIN_LAST_YEAR)
    hold_known = known & (core["year"] >= HOLDOUT_FIRST_YEAR)
    def cascade_pack(mask: np.ndarray) -> Dict[str, Any]:
        a = later_agree[mask & (top5_first == 1)]
        b = later_agree[mask & (top5_first == 0)]
        return group_diff(a, b, rng, n_boot) or {"estimate": None, "status": "DATA UNAVAILABLE"}
    c_train = cascade_pack(train_known)
    c_hold = cascade_pack(hold_known)
    if c_train.get("estimate") is None:
        unavailable(missing, "E3_agreement", "not enough contested-direction PRs with a defined top-5 merger window")
        c_train = {"estimate": None, "ci95": None, "p": None, "n": None, "cohens_d": None, "effect_size_flag": None, "status": "DATA UNAVAILABLE"}
    if c_hold.get("estimate") is None:
        unavailable(missing, "E3_agreement_holdout", "2024-2026 did not have enough top-5-first and other-first PRs")
        c_hold = {"estimate": None, "status": "DATA UNAVAILABLE"}
    add_test(
        tests, test_id="E3_agreement_share_top5_minus_other", effect="E3",
        estimate=c_train.get("estimate"), ci=c_train.get("ci95"), p=c_train.get("p"), n=c_train.get("n"),
        kind="cohens_d", effect_size=c_train.get("cohens_d"), effect_size_flag=c_train.get("effect_size_flag"),
        holdout=c_hold,
        note="Top-5 mergers are the trailing 24-month merge-key holders. First ACK or NACK can come from a comment or a review object. "
        "Agreement is the share of later ACK/NACK attention in the same direction. PRs with no later stance are excluded.",
    )
    def time_pack(mask: np.ndarray) -> Dict[str, Any]:
        a = np.log1p(later_hours[mask & (top5_first == 1)])
        b = np.log1p(later_hours[mask & (top5_first == 0)])
        return group_diff(a, b, rng, n_boot) or {"estimate": None, "status": "DATA UNAVAILABLE"}
    t_train = time_pack(train_known)
    t_hold = time_pack(hold_known)
    if t_train.get("estimate") is None:
        unavailable(missing, "E3_time", "not enough PRs with a later same-direction review")
        t_train = {"estimate": None, "ci95": None, "p": None, "n": None, "cohens_d": None, "effect_size_flag": None}
    if t_hold.get("estimate") is None:
        unavailable(missing, "E3_time_holdout", "2024-2026 lacked later same-direction reviews in both groups")
        t_hold = {"estimate": None, "status": "DATA UNAVAILABLE"}
    add_test(
        tests, test_id="E3_log_hours_to_next_same_direction_top5_minus_other", effect="E3",
        estimate=t_train.get("estimate"), ci=t_train.get("ci95"), p=t_train.get("p"), n=t_train.get("n"),
        kind="cohens_d", effect_size=t_train.get("cohens_d"), effect_size_flag=t_train.get("effect_size_flag"),
        holdout=t_hold,
        note="Negative means the next same-direction review arrives sooner after a top-5 merger speaks first. Cohen's d uses the same sign.",
    )
    for year in sorted(set(int(y) for y in core["year"][known].tolist())):
        m = known & (core["year"] == year)
        a = later_agree[m & (top5_first == 1)]
        b = later_agree[m & (top5_first == 0)]
        a = a[np.isfinite(a)]
        b = b[np.isfinite(b)]
        if a.size >= 5 and b.size >= 5:
            yearly_strength["E3"][year] = float(a.mean() - b.mean())

    # E4a jargon
    person_rows: Dict[int, List[int]] = defaultdict(list)
    for i in range(n):
        person_rows[int(core["author"][i])].append(i)
    # comments by person
    comments_by_person: Dict[int, List[Tuple[float, float, float, float, int]]] = defaultdict(list)
    for k in range(ev["ts"].size):
        comments_by_person[int(ev["person"][k])].append((
            float(ev["ts"][k]), float(ev["words"][k]), float(ev["tone"][k]), float(gaps[k]), int(ev["jargon"][k]),
        ))
    for rows in comments_by_person.values():
        rows.sort()
    jargon_share = []
    merge_rate = []
    retained = []
    entry_year = []
    mean_log_lines = []
    sizes_ok = []
    for person, idxs in person_rows.items():
        first = float(ctrl["first_ts"][idxs[0]])
        # first_ts was stored per PR; recover from min created
        first = float(np.min(core["created"][idxs]))
        ey = year_of(first)
        rows = comments_by_person.get(person, [])
        in_year = [r for r in rows if first <= r[0] < first + YEAR]
        if len(in_year) < 3:
            continue
        share = float(np.mean([r[4] for r in in_year]))
        decided_idx = [i for i in idxs if core["created"][i] < first + YEAR and core["decided"][i]]
        if len(decided_idx) < 1:
            continue
        mr = float(np.mean(core["merged"][decided_idx]))
        observable = first + 2 * YEAR <= dataset_end
        later_act = any(r[0] >= first + 2 * YEAR for r in rows) or any(
            float(core["created"][i]) >= first + 2 * YEAR for i in idxs
        )
        jargon_share.append(share)
        merge_rate.append(mr)
        retained.append(1.0 if (observable and later_act) else (np.nan if not observable else 0.0))
        entry_year.append(ey)
        mean_log_lines.append(float(np.mean(np.log1p(core["lines"][decided_idx]))))
        sizes_ok.append(float(np.mean(core["files"][decided_idx])))
    if len(jargon_share) < 40:
        unavailable(missing, "E4a", "fewer than 40 newcomers had at least 3 first-year comments and a decided PR")
    else:
        js = np.asarray(jargon_share)
        mr = np.asarray(merge_rate)
        ret = np.asarray(retained)
        ey = np.asarray(entry_year, dtype=float)
        ml = np.asarray(mean_log_lines)
        fl = np.asarray(sizes_ok)
        # tenure and prior merges are ~0 for a first-year cohort; they are included and dropped if constant.
        zeros = np.zeros(js.size)
        train_j, hold_j = fit_split(mr, js, [ml, fl, zeros, zeros, zeros, zeros], ey, rng, n_boot, False)
        record_regression(
            tests, "E4a_jargon_share_on_first_year_merge_rate", "E4", train_j, hold_j, missing,
            "Person-level. House terms: ACK, concept ACK, approach ACK, nit, tACK, utACK, rebase, squash. "
            "Entry-year fixed effects stand in for calendar year. Prior merges and in-group are constant for newcomers and drop out.",
        )
        ret_obs = np.isfinite(ret)
        if int(ret_obs.sum()) < 40:
            unavailable(missing, "E4a_retention", "fewer than 40 newcomers are observable at 24 months")
        else:
            train_r, hold_r = fit_split(
                np.where(ret_obs, ret, np.nan), js, [ml, fl, zeros, zeros, zeros, zeros], ey, rng, n_boot, True,
            )
            record_regression(
                tests, "E4a_jargon_share_on_24m_retention", "E4", train_r, hold_r, missing,
                "Retention means any PR or attention event on or after 24 months from the first PR. Right-censored people are excluded.",
            )
        for year in sorted(set(int(v) for v in ey if np.isfinite(v))):
            m = ey == year
            if int(m.sum()) < 15 or np.std(js[m]) < 1e-8:
                continue
            # simple standardized slope
            x = (js[m] - js[m].mean()) / js[m].std()
            yv = mr[m]
            varx = float(np.dot(x, x))
            if varx <= 0:
                continue
            yearly_strength["E4"][year] = float(np.dot(x, yv - yv.mean()) / varx)

    # E4b accommodation. Reply = next different author within 14 days on the same PR.
    partner_bits = []
    speaker_bits = []
    partner_merger = []
    reply_year = []
    pair_score_m = []
    pair_score_o = []
    if ev["ts"].size:
        order = np.lexsort((ev["ts"], ev["pr"]))
        last: Dict[int, Tuple[float, int, int]] = {}
        for k in order:
            pr = int(ev["pr"][k])
            prev = last.get(pr)
            person = int(ev["person"][k])
            ts = float(ev["ts"][k])
            if prev is not None and prev[1] != person and 0 < ts - prev[0] <= 14 * DAY:
                p_mask = [(prev[2] >> b) & 1 for b in range(len(FW_NAMES))]
                s_mask = [(int(ev["fw"][k]) >> b) & 1 for b in range(len(FW_NAMES))]
                became_merger = ctrl["merger_first"].get(prev[1], np.inf) < ts
                partner_bits.append(p_mask)
                speaker_bits.append(s_mask)
                partner_merger.append(1 if became_merger else 0)
                reply_year.append(year_of(ts))
                used = [i for i, bit in enumerate(p_mask) if bit]
                score = float(np.mean([s_mask[i] for i in used])) if used else np.nan
                if became_merger:
                    pair_score_m.append(score)
                else:
                    pair_score_o.append(score)
            last[pr] = (ts, person, int(ev["fw"][k]))
    if len(partner_bits) < 50:
        unavailable(missing, "E4b", "fewer than 50 reply pairs with function-word masks")
        yearly_note = None
    else:
        P = np.asarray(partner_bits, dtype=bool)
        S = np.asarray(speaker_bits, dtype=bool)
        g = np.asarray(partner_merger, dtype=bool)
        ry = np.asarray(reply_year)
        def acc_gap(mask: np.ndarray) -> Optional[float]:
            if int(mask.sum()) < 30 or not g[mask].any() or not (~g[mask]).any():
                return None
            a = dnm_accommodation(P[mask & g], S[mask & g])
            b = dnm_accommodation(P[mask & ~g], S[mask & ~g])
            if a is None or b is None:
                return None
            return float(a - b)
        # year-stratified: mean of within-year gaps, weighted by pairs
        weights = []
        gaps_y = []
        for year in sorted(set(int(v) for v in ry)):
            gap_y = acc_gap(ry == year)
            if gap_y is None:
                continue
            # E4's yearly strength stays the jargon coefficient. Accommodation is stored beside it.
            detail.setdefault("E4b_by_year", {})[str(year)] = gap_y
            weights.append(int((ry == year).sum()))
            gaps_y.append(gap_y)
        train_gap = acc_gap(ry <= TRAIN_LAST_YEAR)
        hold_gap = acc_gap(ry >= HOLDOUT_FIRST_YEAR)
        if weights:
            w = np.asarray(weights, dtype=float)
            stratified = float(np.dot(w, gaps_y) / w.sum())
        else:
            stratified = train_gap
        dpack = group_diff(np.asarray(pair_score_m, dtype=float), np.asarray(pair_score_o, dtype=float), rng, n_boot)
        # bootstrap the stratified gap by resampling years that have a gap
        if gaps_y:
            draws = np.empty(n_boot)
            for i in range(n_boot):
                ix = rng.integers(0, len(gaps_y), len(gaps_y))
                ww = w[ix]
                draws[i] = float(np.dot(ww, np.asarray(gaps_y)[ix]) / ww.sum())
            ci = ci_from_draws(draws)
            p = p_from_draws(draws)
        else:
            ci, p = None, None
        if stratified is None:
            unavailable(missing, "E4b", "function-word accommodation was undefined in the training years")
        if hold_gap is None:
            unavailable(missing, "E4b_holdout", "function-word accommodation was undefined in 2024-2026")
        add_test(
            tests, test_id="E4b_accommodation_toward_mergers_minus_others", effect="E4",
            estimate=stratified, ci=ci, p=p, n=int((ry <= TRAIN_LAST_YEAR).sum()),
            kind="cohens_d",
            effect_size=None if not dpack else dpack.get("cohens_d"),
            effect_size_flag=None if not dpack else dpack.get("effect_size_flag"),
            holdout={"estimate": hold_gap, "ci95": None, "n": int((ry >= HOLDOUT_FIRST_YEAR).sum()),
                     "status": "ok" if hold_gap is not None else "DATA UNAVAILABLE"},
            note="Danescu-Niculescu-Mizil accommodation on inline function-word classes. "
            "Estimate is the pair-weighted mean of within-year gaps, which is the year control. "
            "Cohen's d is the pair-level match rate toward people who had already merged code versus everyone else. "
            "Method-dependent: the category lists are an instrument.",
            low_observability=True,
        )
        detail["E4b"] = {"train_gap": train_gap, "hold_gap": hold_gap, "n_pairs": len(partner_bits)}

    # E5 diffusion
    decided_m = core["decided"].astype(bool)
    end_ts = np.where(core["merged"].astype(bool), core["merged_at"], core["closed_at"])
    days = (end_ts - core["created"]) / DAY
    log_days = np.where(decided_m & np.isfinite(days) & (days >= 0), np.log1p(days), np.nan)
    log_part = np.log1p(core["participants"].astype(float))
    train_d, hold_d = fit_split(log_days, log_part, cov_all, core["year"].astype(float), rng, n_boot, False)
    record_regression(
        tests, "E5_log_participants_on_log_days", "E5", train_d, hold_d, missing,
        "Decided PRs only. Open PRs are right-censored and excluded. Positive means more participants, slower decisions. "
        "This is not identified as diffusion of responsibility: a harder PR can draw both more people and a longer wait.",
    )
    yearly_strength["E5"] = yearly_coef(log_days, log_part, cov_all, core["year"].astype(float), False)
    concept_only = (core["concept"] == 1) & (core["full"] == 0)
    stall = concept_only & (
        (decided_m & np.isfinite(days) & (days > 180))
        | ((~decided_m) & ((dataset_end - core["created"]) > 180 * DAY))
    )
    def rate_ci(mask_num: np.ndarray, mask_den: np.ndarray) -> Dict[str, Any]:
        den = int(mask_den.sum())
        if den < 10:
            return {"estimate": None}
        num = int((mask_num & mask_den).sum())
        point = num / den
        draws = np.empty(n_boot)
        idx = np.flatnonzero(mask_den)
        flags = mask_num[idx].astype(float)
        for i in range(n_boot):
            take = flags[rng.integers(0, flags.size, flags.size)]
            draws[i] = float(take.mean())
        return {"estimate": point, "ci95": ci_from_draws(draws), "n": den, "p": None}
    stall_train = rate_ci(stall, concept_only & (core["year"] <= TRAIN_LAST_YEAR))
    stall_hold = rate_ci(stall, concept_only & (core["year"] >= HOLDOUT_FIRST_YEAR))
    if stall_train.get("estimate") is None:
        unavailable(missing, "E5_concept_ack_stall", "fewer than 10 concept-ACK PRs without a full review in 2010-2023")
    add_test(
        tests, test_id="E5_concept_ack_without_full_review_stall_share", effect="E5",
        estimate=stall_train.get("estimate"), ci=stall_train.get("ci95"), p=None, n=stall_train.get("n"),
        kind="rate", family=False, holdout=stall_hold if stall_hold.get("estimate") is not None else {"estimate": None, "status": "DATA UNAVAILABLE"},
        note="Descriptive rate, not a hypothesis test, so it is outside the BH family. Stall means more than 180 days to a decision, or still open after 180 days. Full review means an APPROVED review or an ACK that is not only a concept or approach ACK.",
    )

    # E6 funder homophily
    unavailable(
        missing, "E6",
        "The funding files record keyword mentions on PRs, not a ledger of which person is paid by which funder, so within-funder review cannot be computed.",
    )
    add_test(
        tests, test_id="E6_funder_homophily", effect="E6", estimate=None, ci=None, p=None, n=None,
        kind="excess_over_null", family=False,
        holdout={"estimate": None, "status": "DATA UNAVAILABLE"},
        note="DATA UNAVAILABLE. No person-to-funder assignment.",
    )

    # E7 anchoring
    later_mean = np.where(core["later_n"] > 0, core["later_sum"] / np.maximum(core["later_n"], 1), np.nan)
    y_merge = np.where(decided_m, core["merged"].astype(float), np.nan)
    train_a, hold_a = fit_split(
        y_merge, core["first_tone"], cov_all + [later_mean], core["year"].astype(float), rng, n_boot, True,
    )
    record_regression(
        tests, "E7_first_tone_on_merge_given_later_tone", "E7", train_a, hold_a, missing,
        "Decided PRs with a first peer tone and at least one later peer tone. Logistic. Later mean tone is an added control on top of the shared set.",
    )
    yearly_strength["E7"] = yearly_coef(
        y_merge, core["first_tone"], cov_all + [later_mean], core["year"].astype(float), True,
    )

    # E8 burnout signatures from the attrition timeline
    attr_path = findings / "data" / "contributor_timeline_analysis.json"
    tone_delta_d = []
    tone_delta_a = []
    word_delta_d = []
    word_delta_a = []
    gap_delta_d = []
    gap_delta_a = []
    if not attr_path.exists():
        unavailable(missing, "E8", "findings/data/contributor_timeline_analysis.json is missing")
    else:
        attr = json.loads(attr_path.read_text())
        departed_T = []
        active_people = []
        for login, row in (attr.get("timeline") or {}).items():
            who = ident.ident(str(login), irc=False)
            if not who or who not in people.ids:
                continue
            pid = people.ids[who]
            last = parse_ts(row.get("last_activity") or row.get("last_contribution_date"))
            if last is None or pid not in comments_by_person:
                continue
            if row.get("is_active"):
                active_people.append(pid)
            elif last <= dataset_end - 180 * DAY:
                departed_T.append((pid, last))
        def deltas(pid: int, t_end: float) -> Optional[Tuple[float, float, float]]:
            rows = [(r[0], r[1], r[2], r[3]) for r in comments_by_person.get(pid, [])]
            final = window_stats(rows, t_end - 180 * DAY, t_end + 1)
            base = window_stats(rows, t_end - 3 * YEAR, t_end - 180 * DAY)
            if final is None or base is None:
                return None
            return final[0] - base[0], final[1] - base[1], (
                final[2] - base[2] if np.isfinite(final[2]) and np.isfinite(base[2]) else np.nan
            )
        # Match each leaver to active contributors on the same end date.
        for pid, t_end in departed_T:
            dlt = deltas(pid, t_end)
            if dlt is None:
                continue
            control_vals = []
            for ap in active_people:
                cd = deltas(ap, t_end)
                if cd is not None:
                    control_vals.append(cd)
            if len(control_vals) < 5:
                continue
            cmean = np.nanmean(control_vals, axis=0)
            word_delta_d.append(dlt[0])
            word_delta_a.append(float(cmean[0]))
            tone_delta_d.append(dlt[1])
            tone_delta_a.append(float(cmean[1]))
            if np.isfinite(dlt[2]) and np.isfinite(cmean[2]):
                gap_delta_d.append(dlt[2])
                gap_delta_a.append(float(cmean[2]))
        unavailable(
            missing, "E8_off_hours",
            "Comment timestamps are UTC and no per-contributor timezone is stored, so the share of activity outside 08:00-22:00 local time cannot be computed.",
        )
        for name, left, right, strength_sign in (
            ("E8_reply_length_words", word_delta_d, word_delta_a, 1),
            ("E8_tone", tone_delta_d, tone_delta_a, -1),
            ("E8_response_gap_seconds", gap_delta_d, gap_delta_a, 1),
        ):
            pack = group_diff(np.asarray(left, dtype=float), np.asarray(right, dtype=float), rng, n_boot)
            if pack is None:
                unavailable(missing, name, "fewer than 5 leavers and 5 matched active windows had at least 5 comments in both the last 180 days and the prior baseline")
                add_test(
                    tests, test_id=name, effect="E8", estimate=None, ci=None, p=None, n=None,
                    kind="cohens_d", family=False, holdout={"estimate": None, "status": "DATA UNAVAILABLE"},
                    note="DATA UNAVAILABLE",
                )
                continue
            # Holdout: leavers whose end date is in 2024-2026 versus the rest. If too few, say so.
            add_test(
                tests, test_id=name + "_leaver_minus_matched_active", effect="E8",
                estimate=pack["estimate"], ci=pack["ci95"], p=pack["p"], n=pack["n"],
                kind="cohens_d", effect_size=pack["cohens_d"], effect_size_flag=pack["effect_size_flag"],
                holdout={"estimate": None, "status": "DATA UNAVAILABLE"},
                note="Difference of (last 180 days minus prior baseline). Active contributors are matched on the leaver's end date and need the same two windows. "
                "The timeline is the filtered 301-person attrition file, not every GitHub author. "
                "A separate 2024-2026 refit is not identified: each leaver is already one window.",
            )
            unavailable(missing, name + "_holdout", "E8 matches each leaver to one window, so there is no second sample of the same people in 2024-2026")
        if tone_delta_d and tone_delta_a:
            # yearly strength: mean leaver tone delta minus matched active, by year of exit. Recompute lightly from pairs stored only as pooled.
            # The matched pairs were not stored by year. Strength uses the pooled adverse tone gap only in the summary, yearly left empty if we didn't keep years.
            pass
        detail["E8"] = {
            "n_leavers_length": len(word_delta_d),
            "n_leavers_tone": len(tone_delta_d),
            "n_leavers_gap": len(gap_delta_d),
            "definition": "Last 180 days versus the preceding period back to three years, matched to active timeline members on the same end timestamp.",
        }

    # E9 meeting list
    listed_flag = np.zeros(n, dtype=np.int8)
    list_ts = np.full(n, np.nan)
    for num, ts in irc["listed"].items():
        i = number_to_index.get(int(num))
        if i is None:
            continue
        # listing counts if it happens before a decision, or while still open
        end = core["merged_at"][i] if core["merged"][i] and np.isfinite(core["merged_at"][i]) else core["closed_at"][i]
        if np.isfinite(end) and ts > end:
            continue
        if ts + DAY < core["created"][i]:
            continue
        listed_flag[i] = 1
        list_ts[i] = ts
    if irc["n_priority_topics"] == 0:
        unavailable(missing, "E9", "no IRC #topic lines matched the high-priority review pattern")
    first_list_year = min((year_of(t) for t in irc["listed"].values()), default=None)
    if first_list_year is None:
        unavailable(missing, "E9", "priority topics were seen but no resolvable bitcoin/bitcoin PR numbers were on them")
        era = np.zeros(n, dtype=bool)
    else:
        era = core["year"] >= first_list_year
    y_list = np.where(decided_m, core["merged"].astype(float), np.nan)
    train_l, hold_l = fit_split(
        np.where(era, y_list, np.nan),
        listed_flag.astype(float),
        cov_all,
        core["year"].astype(float),
        rng, n_boot, True,
    )
    record_regression(
        tests, "E9_listed_on_merge", "E9", train_l, hold_l, missing,
        "Listed means a PR number appeared in an IRC #topic high-priority review window (until the next #topic or 40 minutes) "
        "before the PR was decided. Comparison is restricted to PRs opened on or after the first such topic. "
        f"Priority topics found: {irc['n_priority_topics']}. PRs listed before decision: {int(listed_flag.sum())}.",
    )
    log_merge_days = np.where(
        core["merged"].astype(bool) & np.isfinite(core["merged_at"]) & era,
        np.log1p((core["merged_at"] - core["created"]) / DAY),
        np.nan,
    )
    train_lt, hold_lt = fit_split(log_merge_days, listed_flag.astype(float), cov_all, core["year"].astype(float), rng, n_boot, False)
    record_regression(
        tests, "E9_listed_on_log_days_to_merge", "E9", train_lt, hold_lt, missing,
        "Among merged PRs in the meeting era. Negative means listed PRs merge faster.",
    )
    d_list = group_diff(
        y_list[(listed_flag == 1) & decided_m & era & (core["year"] <= TRAIN_LAST_YEAR)],
        y_list[(listed_flag == 0) & decided_m & era & (core["year"] <= TRAIN_LAST_YEAR)],
        rng, n_boot,
    )
    detail["E9"] = {
        "n_priority_topics": irc["n_priority_topics"],
        "n_listed_before_decision": int(listed_flag.sum()),
        "first_list_year": first_list_year,
        "merge_rate_d": None if not d_list else d_list.get("cohens_d"),
        "merge_rate_d_flag": None if not d_list else d_list.get("effect_size_flag"),
    }
    # requester types
    type_counts = {"merger": 0, "regular": 0, "newcomer": 0, "unresolved": 0}
    for ident_s, count in irc["request_counts_by_ident"].items():
        if ident_s == "unresolved" or ident_s not in people.ids:
            type_counts["unresolved"] += count
            continue
        pid = people.ids[ident_s]
        # classify at dataset median: merger if they ever merged before their requests. Use ever-merger vs newcomer-at-first-PR.
        if pid in ctrl["merger_first"]:
            type_counts["merger"] += count
        else:
            type_counts["newcomer"] += count  # refined below if they have tenure; requests aren't all first-year
    # Better classification using the listing timestamp when we stored the ident on the PR.
    type_counts = {"merger": 0, "regular": 0, "newcomer": 0, "unresolved": 0}
    for num, ts in irc["listed"].items():
        i = number_to_index.get(int(num))
        who = irc["listed_by"].get(num) or ""
        if i is None or not who or who not in people.ids:
            type_counts["unresolved"] += 1
            continue
        pid = people.ids[who]
        if ctrl["merger_first"].get(pid, np.inf) < ts:
            type_counts["merger"] += 1
        elif pid in person_rows and ts - float(np.min(core["created"][person_rows[pid]])) <= YEAR:
            type_counts["newcomer"] += 1
        elif pid not in person_rows and pid not in comments_by_person:
            type_counts["unresolved"] += 1
        else:
            type_counts["regular"] += 1
    detail["E9"]["listing_requests_by_author_type"] = type_counts
    detail["E9"]["unresolved_note"] = (
        "Unresolved means the IRC nick did not join to a GitHub identity. "
        "PR matching itself does not use nicks."
    )
    for year in sorted(set(int(y) for y in core["year"][era].tolist())):
        m = era & decided_m & (core["year"] == year)
        a = y_list[m & (listed_flag == 1)]
        b = y_list[m & (listed_flag == 0)]
        a = a[np.isfinite(a)]
        b = b[np.isfinite(b)]
        if a.size >= 5 and b.size >= 20:
            yearly_strength["E9"][year] = float(a.mean() - b.mean())

    # E10 dissent
    nack_rows = []
    seen_pair = set()
    for k in np.argsort(ev["ts"], kind="mergesort"):
        if not ev["nack"][k]:
            continue
        pr = int(ev["pr"][k])
        person = int(ev["person"][k])
        if person == int(core["author"][pr]):
            continue
        if (person, pr) in seen_pair:
            continue
        seen_pair.add((person, pr))
        if not core["decided"][pr]:
            continue
        ts = float(ev["ts"][k])
        if ts + YEAR > dataset_end:
            continue
        nack_rows.append((person, pr, ts, int(core["merged"][pr]), int(core["year"][pr])))
    if len(nack_rows) < 30:
        unavailable(missing, "E10", f"only {len(nack_rows)} observable NACK events; need at least 30")
    else:
        part_y = []
        merge_y = []
        focal = []
        years_e = []
        tenure_e = []
        logl = []
        files_e = []
        prior_e = []
        ing = []
        unid = []
        for person, pr, ts, did_merge, _year in nack_rows:
            rows = comments_by_person.get(person, [])
            lo = bisect_left(rows, (ts,))
            hi = bisect_left(rows, (ts + YEAR,))
            part_y.append(float(hi - lo))
            # own PRs in the next year
            own = [i for i in person_rows.get(person, []) if ts < float(core["created"][i]) <= ts + YEAR and core["decided"][i]]
            merge_y.append(float(np.mean(core["merged"][own])) if own else np.nan)
            focal.append(float(did_merge))
            years_e.append(float(year_of(ts)))
            tenure_e.append((ts - float(np.min(core["created"][person_rows[person]]))) / YEAR if person in person_rows else 0.0)
            logl.append(float(ctrl["log_lines"][pr]))
            files_e.append(float(core["files"][pr]))
            prior_e.append(float(ctrl["prior"][pr]))
            ing.append(float(ctrl["ingroup"][pr]))
            unid.append(float(ctrl["unidentified"][pr]))
        fy = np.asarray(focal)
        yy = np.asarray(years_e)
        cov_e = [np.asarray(logl), np.asarray(files_e), np.asarray(tenure_e), np.asarray(prior_e), np.asarray(ing), np.asarray(unid)]
        tr, ho = fit_split(np.asarray(part_y), fy, cov_e, yy, rng, n_boot, False)
        record_regression(
            tests, "E10_participation_after_nack_merged_vs_closed", "E10", tr, ho, missing,
            "Focal is 1 when the NACKed PR later merged and 0 when it closed without merging. "
            "Outcome is the reviewer's attention events in the next 365 days. Negative means less participation after a NACK that lost.",
        )
        trm, hom = fit_split(np.asarray(merge_y), fy, cov_e, yy, rng, n_boot, False)
        record_regression(
            tests, "E10_own_merge_rate_after_nack", "E10", trm, hom, missing,
            "Outcome is the reviewer's own decided-PR merge rate in the next year. Events with no decided PR of their own are excluded.",
        )
        # yearly: mean participation gap
        py = np.asarray(part_y)
        for year in sorted(set(int(v) for v in yy)):
            m = yy == year
            if (fy[m] == 1).sum() >= 5 and (fy[m] == 0).sum() >= 5:
                yearly_strength["E10"][year] = float(py[m & (fy == 1)].mean() - py[m & (fy == 0)].mean())

    # E11 harsh comments. LOW OBSERVABILITY.
    harsh_idx = np.flatnonzero(ev["harsh"] == 1) if ev["ts"].size else np.array([], dtype=int)
    follow = []
    atype = []
    hyear = []
    hten = []
    hlines = []
    hfiles = []
    hprior = []
    hing = []
    hunid = []
    # index events by pr for follow-up search
    for k in harsh_idx.tolist():
        pr = int(ev["pr"][k])
        person = int(ev["person"][k])
        ts = float(ev["ts"][k])
        corrected = 0
        for j in by_pr.get(pr, []):
            if float(ev["ts"][j]) <= ts or float(ev["ts"][j]) > ts + 7 * DAY:
                continue
            if int(ev["person"][j]) == person:
                continue
            if float(ev["tone"][j]) >= 0:
                corrected = 1
                break
        if core["sanction"][pr]:
            corrected = 1
        follow.append(corrected)
        if ctrl["merger_first"].get(person, np.inf) < ts:
            atype.append(2)  # merger
        elif person in person_rows and ts - float(np.min(core["created"][person_rows[person]])) <= YEAR:
            atype.append(0)  # newcomer
        else:
            atype.append(1)  # regular
        hyear.append(float(year_of(ts)))
        hten.append((ts - float(np.min(core["created"][person_rows[person]]))) / YEAR if person in person_rows else 0.0)
        hlines.append(float(ctrl["log_lines"][pr]))
        hfiles.append(float(core["files"][pr]))
        hprior.append(float(ctrl["prior"][pr]))
        hing.append(float(ctrl["ingroup"][pr]))
        hunid.append(float(ctrl["unidentified"][pr]))
    follow_a = np.asarray(follow, dtype=float)
    type_a = np.asarray(atype, dtype=float) if atype else np.zeros(0)
    if follow_a.size < 10:
        unavailable(
            missing, "E11",
            f"{int(follow_a.size)} harsh comments (lexicon and negative tone). Deleted comments are not in the dataset. LOW OBSERVABILITY.",
        )
    else:
        merger_f = (type_a == 2).astype(float)
        train_h, hold_h = fit_split(
            follow_a, merger_f,
            [np.asarray(hlines), np.asarray(hfiles), np.asarray(hten), np.asarray(hprior), np.asarray(hing), np.asarray(hunid)],
            np.asarray(hyear), rng, n_boot, True,
        )
        record_regression(
            tests, "E11_followup_on_harsh_comment_by_merger", "E11", train_h, hold_h, missing,
            "Harsh means a lexicon hit and negative keyword tone. Follow-up means a non-author-of-the-harsh-comment replies within 7 days at tone >= 0, or the PR carries a lock/ban trace. "
            "LOW OBSERVABILITY: deleted and redacted comments are absent, so both the harsh set and the correction set are lower bounds.",
            low_observability=True,
        )
        d_h = group_diff(follow_a[type_a == 2], follow_a[type_a == 0], rng, n_boot)
        detail["E11"] = {
            "n_harsh": int(follow_a.size),
            "rate_merger": float(follow_a[type_a == 2].mean()) if (type_a == 2).any() else None,
            "rate_regular": float(follow_a[type_a == 1].mean()) if (type_a == 1).any() else None,
            "rate_newcomer": float(follow_a[type_a == 0].mean()) if (type_a == 0).any() else None,
            "cohens_d_merger_minus_newcomer": None if not d_h else d_h.get("cohens_d"),
            "effect_size_flag": None if not d_h else d_h.get("effect_size_flag"),
            "low_observability": True,
        }
        for year in sorted(set(int(v) for v in hyear)):
            m = np.asarray(hyear) == year
            if (type_a[m] == 2).sum() >= 3 and (type_a[m] == 0).sum() >= 3:
                yearly_strength["E11"][year] = float(follow_a[m & (type_a == 2)].mean() - follow_a[m & (type_a == 0)].mean())

    # E12 carried metrics with shared controls
    no_resp = np.where(np.isfinite(core["first_peer"]), 0.0, 1.0)
    train_nr, hold_nr = fit_split(no_resp, ctrl["ingroup"], [
        ctrl["log_lines"], ctrl["files"], ctrl["tenure"], ctrl["prior"], ctrl["unidentified"],
    ], core["year"].astype(float), rng, n_boot, True)
    record_regression(
        tests, "E12_ingroup_on_no_peer_response", "E12", train_nr, hold_nr, missing,
        "No peer response means no review object, issue comment, or line comment by someone other than the author. "
        "In-group is the trailing-24-month top 20 by review-object volume, unidentified when fewer than 20 reviewers exist. "
        "Unidentified is a control, not coded as out-group.",
    )
    # 90-day return
    returned = np.full(n, np.nan)
    for i in range(n):
        if not np.isfinite(core["first_peer"][i]):
            continue
        t0 = float(core["first_peer"][i])
        if t0 + 90 * DAY > dataset_end:
            continue
        pid = int(core["author"][i])
        rows = core["activity"].get(pid, [])
        lo = bisect_right(rows, t0)
        hi = bisect_right(rows, t0 + 90 * DAY)
        returned[i] = 1.0 if hi > lo else 0.0
    train_ret, hold_ret = fit_split(returned, ctrl["ingroup"], [
        ctrl["log_lines"], ctrl["files"], ctrl["tenure"], ctrl["prior"], ctrl["unidentified"],
    ], core["year"].astype(float), rng, n_boot, True)
    record_regression(
        tests, "E12_ingroup_on_90d_return", "E12", train_ret, hold_ret, missing,
        "Return means the author has any later PR or attention event within 90 days after the first peer response. "
        "Events after the dataset end minus 90 days are excluded. E12 is not mapped to an Ostrom principle.",
    )
    yearly_strength["E12"] = yearly_coef(no_resp, ctrl["ingroup"], [
        ctrl["log_lines"], ctrl["files"], ctrl["tenure"], ctrl["prior"], ctrl["unidentified"],
    ], core["year"].astype(float), True)

    # ----- Part B and C for core, then thin repos -----
    logger.info("part B and C")
    repo = "bitcoin/bitcoin"
    score_core_repo(
        repo, core, ctrl, ev, maintainer_ids, irc, grant_windows, bt_years, delving_years,
        dataset_end, attr_path, ident, people, store, seen, missing, detail,
    )
    # P7a explicitly unavailable
    unavailable(
        missing, "P7a_funder_hhi",
        "Funding files contain keyword mentions, not a person-to-funder ledger, so a funder HHI across contributors cannot be computed.",
    )
    unavailable(
        missing, "P6c_exit_channels",
        "No dated ledger of forks or alternative-implementation launches is in the dataset. Contributor departures are H7 and are not copied here.",
    )
    unavailable(
        missing, "E8_yearly",
        "E8 is a matched-window contrast of leavers and does not produce a stable yearly strength series.",
    )

    thin_notes = []
    for repo_name, path in discover_repos(data_dir):
        if repo_name in {"bitcoin/bitcoin"}:
            continue
        thin = load_thin(path)
        if thin["created"].size == 0:
            unavailable(missing, repo_name, "PR file had no usable rows")
            continue
        score_thin_repo(repo_name, thin, dataset_end, store, seen, missing, detail)
        thin_notes.append(repo_name)
        unavailable(
            missing, f"{repo_name} Part A",
            "This PR dump has author, title, body, and timestamps only. It has no review text, file paths, or merged_by, so effects E1-E12 and review-based principles are not computed.",
        )
    if "bitcoin-core/gui" not in thin_notes:
        unavailable(missing, "bitcoin-core/gui", "repository not present under data/github/repos")

    # normalize
    logger.info("normalizing and linking")
    keys = sorted({(r, y) for (r, y, _m) in store})
    metrics = sorted({m for (_r, _y, m) in store})
    normalized: Dict[Tuple[str, int, str], Optional[float]] = {}
    for metric in metrics:
        spec = SCORING_SPEC[metric]
        raw_vals = [store.get((r, y, metric)) for r, y in keys]
        if spec.get("scored") and spec["direction"] in {"higher_better", "lower_better"}:
            scaled = normalize_values(raw_vals, spec["direction"] == "higher_better")
        else:
            scaled = [None for _ in raw_vals]
        for (r, y), value in zip(keys, scaled):
            normalized[(r, y, metric)] = value

    # P5b: if the underlying event count is under 10, drop the normalized value even if a number was stored.
    for r, y in keys:
        count = store.get((r, y, "P5a_sanction_events"))
        if count is None or count < 10:
            normalized[(r, y, "P5b_graduated_share")] = None
            store[(r, y, "P5b_graduated_share")] = None

    principles = ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"]
    by_principle: Dict[str, List[str]] = {p: [] for p in principles}
    for metric, spec in SCORING_SPEC.items():
        if spec["part"] == "B" and spec.get("principle"):
            by_principle[spec["principle"]].append(metric)
    health_ids = [m for m, spec in SCORING_SPEC.items() if spec["part"] == "C" and spec.get("scored")]

    def mean_or_none(vals: Iterable[Optional[float]]) -> Optional[float]:
        usable = [float(v) for v in vals if v is not None and np.isfinite(v)]
        if not usable:
            return None
        return float(np.mean(usable))

    repo_rows = []
    principle_scores: Dict[Tuple[str, int], Dict[str, Optional[float]]] = {}
    health_scores: Dict[Tuple[str, int], Optional[float]] = {}
    for r, y in keys:
        scores = {}
        for p in principles:
            scored_metrics = [m for m in by_principle[p] if SCORING_SPEC[m].get("scored")]
            scores[p] = mean_or_none(normalized.get((r, y, m)) for m in scored_metrics)
        principle_scores[(r, y)] = scores
        h = mean_or_none(normalized.get((r, y, m)) for m in health_ids)
        health_scores[(r, y)] = h
        present_h = [m for m in health_ids if store.get((r, y, m)) is not None]
        present_p = [m for m in metrics if SCORING_SPEC[m]["part"] == "B" and store.get((r, y, m)) is not None]
        row = {
            "repo": r,
            "year": y,
            "principles": scores,
            "health": h,
            "health_indicators_present": present_h,
            "health_partial": len(present_h) < len(health_ids),
            "indicators": {m: store.get((r, y, m)) for m in metrics if store.get((r, y, m)) is not None},
        }
        repo_rows.append(row)
        if set(present_h) & set(present_p):
            raise RuntimeError("a health indicator was stored as a principle indicator")

    # alias check: no health series object is a principle series object
    for hid in health_ids:
        for pid in by_principle["P2"] + by_principle["P4"]:
            if hid == pid:
                raise RuntimeError(f"overlap {hid}")

    # T1-T3 on bitcoin/bitcoin
    core_years = sorted(y for (r, y) in principle_scores if r == repo)
    linkage = []

    def series_for(effect: str) -> Tuple[np.ndarray, np.ndarray]:
        ys = []
        vs = []
        for y, v in sorted(yearly_strength.get(effect, {}).items()):
            if np.isfinite(v):
                ys.append(y)
                vs.append(v)
        return np.asarray(ys, dtype=float), np.asarray(vs, dtype=float)

    def spearman_pack(x: np.ndarray, y: np.ndarray) -> Optional[Dict[str, Any]]:
        if x.size < 6 or y.size < 6:
            return None
        res = stats.spearmanr(x, y)
        r = float(res.statistic if hasattr(res, "statistic") else res[0])
        p = float(res.pvalue if hasattr(res, "pvalue") else res[1])
        if not np.isfinite(r):
            return None
        draws = np.empty(n_boot)
        m = x.size
        for i in range(n_boot):
            ix = rng.integers(0, m, m)
            if np.unique(x[ix]).size < 2 or np.unique(y[ix]).size < 2:
                draws[i] = np.nan
                continue
            rr = stats.spearmanr(x[ix], y[ix])
            draws[i] = float(rr.statistic if hasattr(rr, "statistic") else rr[0])
        return {"estimate": r, "p": p, "ci95": ci_from_draws(draws), "n": int(m)}

    for effect, spec in SCORING_SPEC.items():
        if spec["part"] != "A":
            continue
        years_e, vals_e = series_for(effect)
        for principle in spec["maps"]:
            xs = []
            ys = []
            xs_train = []
            ys_train = []
            for y, v in zip(years_e.tolist(), vals_e.tolist()):
                score = principle_scores.get((repo, int(y)), {}).get(principle)
                if score is None:
                    continue
                xs.append(v)
                ys.append(score)
                if int(y) <= TRAIN_LAST_YEAR:
                    xs_train.append(v)
                    ys_train.append(score)
            primary = spearman_pack(np.asarray(xs_train), np.asarray(ys_train))
            full = spearman_pack(np.asarray(xs), np.asarray(ys))
            if primary is None:
                unavailable(missing, f"T1_{effect}_{principle}", "fewer than 6 years with both an effect strength and a principle score")
                add_test(
                    tests, test_id=f"T1_{effect}_{principle}", effect=effect, estimate=None, ci=None, p=None,
                    n=None, kind="spearman", family=False, principles=[principle],
                    holdout={"estimate": None, "status": "DATA UNAVAILABLE"},
                    note="DATA UNAVAILABLE. LOW POWER would apply even with a full series of about 16 years.",
                )
                continue
            hold_est = None if full is None else full["estimate"]
            same = None if hold_est is None else bool(np.sign(hold_est) == np.sign(primary["estimate"]))
            add_test(
                tests, test_id=f"T1_{effect}_{principle}", effect=effect, estimate=primary["estimate"],
                ci=primary["ci95"], p=primary["p"], n=primary["n"], kind="spearman", principles=[principle],
                holdout={"estimate": hold_est, "ci95": None if not full else full["ci95"], "n": None if not full else full["n"],
                         "status": "ok" if hold_est is not None else "DATA UNAVAILABLE"},
                note="Spearman of yearly effect strength with the principle score. Negative means the effect is stronger in years the principle scores lower. "
                "Primary sample is years through 2023. Full-sample sign is the holdout check. LOW POWER: about 16 years.",
            )
            linkage.append({
                "test": "T1", "effect": effect, "principle": principle,
                "spearman": primary["estimate"], "p": primary["p"], "n_years": primary["n"],
                "stronger_when_principle_weaker": bool(primary["estimate"] < 0),
                "low_power": True,
            })

    def health_at(year: int) -> Optional[float]:
        return health_scores.get((repo, year))

    for principle in principles:
        for lag in (1, 2):
            xs, ys, xs_tr, ys_tr = [], [], [], []
            for y in core_years:
                s = principle_scores[(repo, y)].get(principle)
                h = health_at(y + lag)
                if s is None or h is None:
                    continue
                xs.append(s)
                ys.append(h)
                if y + lag <= TRAIN_LAST_YEAR:
                    xs_tr.append(s)
                    ys_tr.append(h)
            primary = spearman_pack(np.asarray(xs_tr, dtype=float), np.asarray(ys_tr, dtype=float))
            full = spearman_pack(np.asarray(xs, dtype=float), np.asarray(ys, dtype=float))
            test_id = f"T2_{principle}_lag{lag}"
            if primary is None:
                unavailable(missing, test_id, f"fewer than 6 year-pairs for {principle} and health at t+{lag} inside 2010-2023")
                add_test(
                    tests, test_id=test_id, effect=None, estimate=None, ci=None, p=None, n=None,
                    kind="spearman", family=False, principles=[principle],
                    holdout={"estimate": None, "status": "DATA UNAVAILABLE"},
                    note="LOW POWER. DATA UNAVAILABLE for this lag.",
                )
                continue
            hold_est = None if full is None else full["estimate"]
            add_test(
                tests, test_id=test_id, effect=None, estimate=primary["estimate"], ci=primary["ci95"],
                p=primary["p"], n=primary["n"], kind="spearman", principles=[principle],
                holdout={"estimate": hold_est, "status": "ok" if hold_est is not None else "DATA UNAVAILABLE",
                         "ci95": None if not full else full["ci95"], "n": None if not full else full["n"]},
                note=f"Principle score in t versus health in t+{lag}. LOW POWER: the series is about 16 years.",
            )
            linkage.append({
                "test": "T2", "principle": principle, "lag": lag,
                "spearman": primary["estimate"], "p": primary["p"], "n_years": primary["n"], "low_power": True,
            })

    for effect in metric_ids("A"):
        years_e, vals_e = series_for(effect)
        for lag in (1, 2):
            xs, ys, xs_tr, ys_tr = [], [], [], []
            for y, v in zip(years_e.tolist(), vals_e.tolist()):
                h = health_at(int(y) + lag)
                if h is None:
                    continue
                xs.append(v)
                ys.append(h)
                if int(y) + lag <= TRAIN_LAST_YEAR:
                    xs_tr.append(v)
                    ys_tr.append(h)
            primary = spearman_pack(np.asarray(xs_tr, dtype=float), np.asarray(ys_tr, dtype=float))
            full = spearman_pack(np.asarray(xs, dtype=float), np.asarray(ys, dtype=float))
            test_id = f"T3_{effect}_lag{lag}"
            if primary is None:
                unavailable(missing, test_id, f"fewer than 6 year-pairs for {effect} and health at t+{lag}")
                add_test(
                    tests, test_id=test_id, effect=effect, estimate=None, ci=None, p=None, n=None,
                    kind="spearman", family=False,
                    holdout={"estimate": None, "status": "DATA UNAVAILABLE"},
                    note="LOW POWER. DATA UNAVAILABLE for this lag.",
                )
                continue
            hold_est = None if full is None else full["estimate"]
            add_test(
                tests, test_id=test_id, effect=effect, estimate=primary["estimate"], ci=primary["ci95"],
                p=primary["p"], n=primary["n"], kind="spearman",
                holdout={"estimate": hold_est, "status": "ok" if hold_est is not None else "DATA UNAVAILABLE",
                         "ci95": None if not full else full["ci95"], "n": None if not full else full["n"]},
                note=f"Effect strength in t versus health in t+{lag}. LOW POWER: about 16 years.",
            )
            linkage.append({
                "test": "T3", "effect": effect, "lag": lag,
                "spearman": primary["estimate"], "p": primary["p"], "n_years": primary["n"], "low_power": True,
            })

    # T5 change points
    change_points = []
    for principle in principles:
        series = [(y, principle_scores[(repo, y)][principle]) for y in core_years if principle_scores[(repo, y)][principle] is not None]
        change_points.append(change_point(principle, series, health_scores, repo))
    for effect, mapping in yearly_strength.items():
        series = sorted((y, v) for y, v in mapping.items() if np.isfinite(v))
        change_points.append(change_point(effect, series, health_scores, repo))

    # prior-pass tests
    logger.info("collecting pass 1 and pass 2 tests for BH")
    prior = collect_prior_tests(findings, missing)
    tests.extend(prior)

    family = [t for t in tests if t.get("in_bh_family") and t.get("p") is not None]
    qvals = bh_qvalues([t["p"] for t in family])
    for t, q in zip(family, qvals):
        t["q"] = float(q)
    for t in tests:
        if t.get("q") is None and t.get("in_bh_family"):
            t["q_status"] = "no p-value, not adjusted"

    # cross-repo ranking
    # Cross-repo rank uses only indicators the thin dumps can support.
    # Bitcoin-only indicators (review labor, sanctions, exits) stay in the
    # per-repo table and are not allowed to make a partial profile look healthier.
    shared_principles = ["P1b_entry_wait_cv", "P1c_scope_disputes_per_100", "P6b_recurring_topics"]
    shared_health = [
        "H2_open_stock_per_pr_opened", "H2_stale_open_per_pr_opened", "H3_cohort_active_24m",
        "H4_gini_merges", "H5_bus_factor", "H6_median_days_to_decision",
    ]
    ranking = []
    repos = sorted({r for (r, _y) in principle_scores})
    for r in repos:
        ys = [y for (rr, y) in principle_scores if rr == r]
        pmean = []
        hmean = []
        full_p = []
        full_h = []
        for y in ys:
            pvals = [normalized.get((r, y, m)) for m in shared_principles]
            pvals = [v for v in pvals if v is not None]
            if pvals:
                pmean.append(float(np.mean(pvals)))
            hvals = [normalized.get((r, y, m)) for m in shared_health]
            hvals = [v for v in hvals if v is not None]
            if hvals:
                hmean.append(float(np.mean(hvals)))
            fp = [principle_scores[(r, y)][p] for p in principles if principle_scores[(r, y)][p] is not None]
            if fp:
                full_p.append(float(np.mean(fp)))
            if health_scores[(r, y)] is not None:
                full_h.append(health_scores[(r, y)])
        ranking.append({
            "repo": r,
            "mean_principle_score": float(np.mean(pmean)) if pmean else None,
            "mean_health": float(np.mean(hmean)) if hmean else None,
            "full_profile_principle_score": float(np.mean(full_p)) if full_p else None,
            "full_profile_health": float(np.mean(full_h)) if full_h else None,
            "n_years": len(ys),
            "ranked": len(ys) >= 7,
            "principles_ever_scored": sorted({
                p for y in ys for p, v in principle_scores[(r, y)].items() if v is not None
            }),
            "shared_indicators": shared_principles + shared_health,
            "note": (
                "Ranking uses the indicators every dump can support: entry-wait variation, "
                "scope disputes, recurring dispute topics, open backlog, 24-month retention, "
                "merge Gini, bus factor, and median time to decision. "
                "Review labor, monitoring, and exit rates exist for bitcoin/bitcoin only and are not in this rank."
            ),
        })
    ranking.sort(key=lambda row: (
        0 if row["ranked"] else 1,
        -(row["mean_health"] if row["mean_health"] is not None else -1),
        -(row["mean_principle_score"] if row["mean_principle_score"] is not None else -1),
    ))

    summary = render_summary(tests, repo_rows, linkage, ranking, change_points, missing, repo)
    payload = {
        "pin": (
            "Part A effects are behavioral signatures, not psychological states. "
            "Part B scores institutional conditions. Part C is health and does not reuse A or B indicators. "
            "Year fixed effects are included because pass 2 found time-structured gaps, not because the bar rose for everyone."
        ),
        "version": "3.0",
        "parameters": {
            "bootstrap": n_boot,
            "permutations": n_perm,
            "seed": seed,
            "train_years": "2010-2023",
            "holdout_years": "2024-2026",
            "rolling_ingroup": "top 20 by peer review-object volume in the trailing 24 months; unidentified below 20",
            "attention_event": "one per person per PR per day, from review objects, issue comments, and line comments, excluding the author and bots",
        },
        "scoring_spec": SCORING_SPEC,
        "effects_table": [t for t in tests if str(t.get("id") or "").startswith("E")],
        "hypothesis_tests": tests,
        "repo_year_table": repo_rows,
        "linkage_table": linkage,
        "change_points": change_points,
        "cross_repo_ranking": ranking,
        "yearly_effect_strength": {k: {str(y): v for y, v in sorted(m.items())} for k, m in yearly_strength.items()},
        "detail": detail,
        "data_unavailable": missing,
        "plain_text_summary": summary,
        "what_this_cannot_prove": CANNOT_PROVE,
    }
    return jsonable(payload)


def change_point(name: str, series: Sequence[Tuple[int, Optional[float]]], health: Dict, repo: str) -> Dict[str, Any]:
    clean = [(int(y), float(v)) for y, v in series if v is not None and np.isfinite(v)]
    if len(clean) < 3:
        return {"name": name, "status": "DATA UNAVAILABLE", "reason": "fewer than 3 yearly points"}
    best = None
    for (y0, v0), (y1, v1) in zip(clean, clean[1:]):
        delta = abs(v1 - v0)
        if best is None or delta > best[0]:
            best = (delta, y1, v0, v1)
    _delta, year, before_v, after_v = best
    values = [v for _y, v in clean]
    scale = float(np.std(values))
    relative = float(abs(after_v - before_v) / scale) if scale > 1e-8 else None
    def health_mean(years: Iterable[int]) -> Optional[float]:
        vals = [health.get((repo, y)) for y in years]
        vals = [v for v in vals if v is not None]
        return float(np.mean(vals)) if vals else None
    return {
        "name": name,
        "year": year,
        "abs_change": float(abs(after_v - before_v)),
        "change_in_within_series_sd": relative,
        "value_before": before_v,
        "value_after": after_v,
        "health_mean_two_years_before": health_mean([year - 2, year - 1]),
        "health_mean_two_years_after": health_mean([year + 1, year + 2]),
    }


def score_core_repo(
    repo, core, ctrl, ev, maintainer_ids, irc, grant_windows, bt_years, delving_years,
    dataset_end, attr_path, ident, people, store, seen, missing, detail,
) -> None:
    years = sorted(set(int(y) for y in core["year"].tolist()))
    # grant discussion by year
    hits = irc["grant_hits"]
    by_year_grants: Dict[int, List[int]] = defaultdict(list)
    for window, hit in zip(grant_windows, hits):
        by_year_grants[window["year"]].append(hit)
    # attention indexes
    ev_year = np.array([year_of(t) for t in ev["ts"].tolist()], dtype=np.int16) if ev["ts"].size else np.zeros(0, dtype=np.int16)
    # author activity years for cohorts
    first_year = {}
    for i, person in enumerate(core["author"].tolist()):
        y = int(core["year"][i])
        first_year[person] = min(first_year.get(person, y), y)
    # timeline exits
    exits_by_year: Dict[int, int] = defaultdict(int)
    timeline_active: Dict[int, int] = defaultdict(int)
    if attr_path.exists():
        attr = json.loads(attr_path.read_text())
        for login, row in (attr.get("timeline") or {}).items():
            first = parse_ts(row.get("first_activity") or row.get("join_date"))
            last = parse_ts(row.get("last_activity") or row.get("last_contribution_date"))
            if first is None or last is None:
                continue
            for y in range(year_of(first), year_of(last) + 1):
                timeline_active[y] += 1
            if not row.get("is_active"):
                exits_by_year[year_of(last)] += 1
    else:
        unavailable(missing, "H7_exit_rate", "contributor timeline is missing")

    topic_years: Dict[str, set] = {name: set() for name in TOPIC_NAMES}
    for i, mask in enumerate(core["topics"].tolist()):
        y = int(core["year"][i])
        for b, name in enumerate(TOPIC_NAMES):
            if mask & (1 << b):
                topic_years[name].add(y)
    chronic = {name for name, ys in topic_years.items() if len(ys) >= 3}
    detail["P6b_topics"] = {name: sorted(ys) for name, ys in topic_years.items() if len(ys) >= 3}
    detail["P7b_alt_impl"] = _alt_summary(core["alt_rows"])
    detail["P7b_note"] = "Keyword sentiment is model-dependent. The pattern \\bknots\\b can match unrelated uses, so counts are an upper bound. Descriptive only."
    detail.setdefault("P8a", {})

    last_att = core["created"].astype(float).copy()
    has_ack = np.zeros(core["created"].size, dtype=bool)
    has_nack = np.zeros(core["created"].size, dtype=bool)
    if ev["ts"].size:
        for pr, ts, ack, nack in zip(ev["pr"].tolist(), ev["ts"].tolist(), ev["ack"].tolist(), ev["nack"].tolist()):
            i = int(pr)
            if ts > last_att[i]:
                last_att[i] = ts
            if ack:
                has_ack[i] = True
            if nack:
                has_nack[i] = True
    person_last = {p: rows[-1] for p, rows in core["activity"].items() if rows}
    first_pr_ts: Dict[int, float] = {}
    for person, ts in zip(core["author"].tolist(), core["created"].tolist()):
        if person not in first_pr_ts or ts < first_pr_ts[person]:
            first_pr_ts[person] = float(ts)
    sanction_total = int(core["sanction"].sum())
    if sanction_total < 10:
        unavailable(
            missing, "P5",
            f"{sanction_total} sanction traces (locks, bans, moderation phrases, access-removal phrases). "
            "LOW OBSERVABILITY. Counts only, no principle score.",
        )

    for y in years:
        m = core["year"] == y
        opened = int(m.sum())
        if opened == 0:
            continue
        # P1a
        grants = by_year_grants.get(y, [])
        if grants:
            put_metric(store, seen, "P1a_grant_discussion_share", repo, y, float(np.mean(grants)))
        else:
            put_metric(store, seen, "P1a_grant_discussion_share", repo, y, None)
        # P1b entry cohort CV
        entrants = [p for p, fy in first_year.items() if fy == y]
        waits = []
        for p in entrants:
            idxs = np.flatnonzero(core["author"] == p)
            first = float(np.min(core["created"][idxs]))
            merged_times = [
                float(core["merged_at"][i]) for i in idxs
                if core["merged"][i] and np.isfinite(core["merged_at"][i])
            ]
            if merged_times:
                waits.append((min(merged_times) - first) / DAY)
        if len(waits) >= 5 and float(np.mean(waits)) > 0:
            put_metric(store, seen, "P1b_entry_wait_cv", repo, y, float(np.std(waits) / np.mean(waits)))
        else:
            put_metric(store, seen, "P1b_entry_wait_cv", repo, y, None)
        put_metric(store, seen, "P1c_scope_disputes_per_100", repo, y, 100.0 * float(core["scope"][m].mean()))
        # attention this year
        em = ev_year == y
        given: Dict[int, int] = defaultdict(int)
        received: Dict[int, int] = defaultdict(int)
        if em.any():
            for person, pr in zip(ev["person"][em].tolist(), ev["pr"][em].tolist()):
                given[int(person)] += 1
                received[int(core["author"][pr])] += 1
        ratios = []
        for person, got in received.items():
            if got <= 0:
                continue
            ratios.append(given.get(person, 0) / got)
        if len(ratios) >= 5:
            arr = np.asarray(ratios, dtype=float)
            put_metric(store, seen, "P2a_gini_provision_ratio", repo, y, gini(arr))
            put_metric(store, seen, "P2a_share_ratio_near_one", repo, y, float(np.mean((arr >= 0.5) & (arr <= 2))))
            put_metric(store, seen, "P2a_share_ratio_above_one", repo, y, float(np.mean(arr > 1)))
        else:
            for metric in ("P2a_gini_provision_ratio", "P2a_share_ratio_near_one", "P2a_share_ratio_above_one"):
                put_metric(store, seen, metric, repo, y, None)
        authors_y = set(int(a) for a in core["author"][m].tolist())
        merges_received: Dict[int, int] = defaultdict(int)
        for i in np.flatnonzero(m & core["merged"].astype(bool)):
            merges_received[int(core["author"][i])] += 1
        people_y = authors_y | set(given)
        if len(people_y) >= 5:
            mv = np.array([merges_received.get(p, 0) for p in people_y], dtype=float)
            rv = np.array([given.get(p, 0) for p in people_y], dtype=float)
            if np.std(mv) > 0 and np.std(rv) > 0:
                put_metric(store, seen, "P2b_merge_review_correlation", repo, y, float(np.corrcoef(mv, rv)[0, 1]))
            else:
                put_metric(store, seen, "P2b_merge_review_correlation", repo, y, None)
            total_att = sum(given.values())
            if total_att > 0:
                top = sorted(given.values(), reverse=True)[:5]
                put_metric(store, seen, "P2c_top5_review_share", repo, y, float(sum(top) / total_att))
            else:
                put_metric(store, seen, "P2c_top5_review_share", repo, y, None)
        else:
            put_metric(store, seen, "P2b_merge_review_correlation", repo, y, None)
            put_metric(store, seen, "P2c_top5_review_share", repo, y, None)
        # P3
        rule_m = m & core["rule"].astype(bool)
        put_metric(store, seen, "P3a_rule_pr_count", repo, y, float(rule_m.sum()))
        parts = set()
        if ev["ts"].size and rule_m.any():
            rule_idx = set(int(i) for i in np.flatnonzero(rule_m).tolist())
            for pr, person in zip(ev["pr"].tolist(), ev["person"].tolist()):
                if pr in rule_idx:
                    parts.add(int(person))
            for i in np.flatnonzero(rule_m):
                parts.add(int(core["author"][i]))
        active = authors_y | set(given)
        if rule_m.any() and active:
            put_metric(store, seen, "P3b_rule_participant_share", repo, y, len(parts) / len(active))
        else:
            put_metric(store, seen, "P3b_rule_participant_share", repo, y, None)
        if rule_m.any():
            nonmerger = []
            for i in np.flatnonzero(rule_m & core["decided"].astype(bool)):
                author = int(core["author"][i])
                had_merged = ctrl["merger_first"].get(author, np.inf) < float(core["created"][i])
                if not had_merged:
                    nonmerger.append(int(core["merged"][i]))
            if nonmerger:
                put_metric(store, seen, "P3c_nonmerger_rule_merge_rate", repo, y, float(np.mean(nonmerger)))
            else:
                put_metric(store, seen, "P3c_nonmerger_rule_merge_rate", repo, y, None)
        else:
            put_metric(store, seen, "P3c_nonmerger_rule_merge_rate", repo, y, None)
        # P4
        merged_m = m & core["merged"].astype(bool)
        if merged_m.any():
            self_m = (core["merger"] == core["author"]) & merged_m
            put_metric(store, seen, "P4a_self_merge_rate", repo, y, float(self_m.sum() / merged_m.sum()))
            indep = set()
            if ev["ts"].size:
                merged_idx = set(int(i) for i in np.flatnonzero(merged_m).tolist())
                for pr, person in zip(ev["pr"][em].tolist(), ev["person"][em].tolist()):
                    if int(pr) not in merged_idx:
                        continue
                    if int(person) == int(core["author"][pr]) or int(person) == int(core["merger"][pr]):
                        continue
                    indep.add(int(pr))
            put_metric(
                store, seen, "P4b_zero_independent_attention_share", repo, y,
                float(1.0 - (len(indep) / int(merged_m.sum()))),
            )
        else:
            put_metric(store, seen, "P4a_self_merge_rate", repo, y, None)
            put_metric(store, seen, "P4b_zero_independent_attention_share", repo, y, None)
        maint_m = m & (core["maintainer_author"] == 1)
        if maint_m.any() and ev["ts"].size:
            counts = defaultdict(int)
            maint_idx = set(int(i) for i in np.flatnonzero(maint_m).tolist())
            for pr, person in zip(ev["pr"].tolist(), ev["person"].tolist()):
                if int(pr) in maint_idx and int(person) not in maintainer_ids:
                    counts[int(pr)] += 1
            share = len(counts) / len(maint_idx)
            med = float(np.median([counts.get(i, 0) for i in maint_idx]))
            put_metric(store, seen, "P4c_nonmaintainer_review_share", repo, y, share)
            put_metric(store, seen, "P4c_median_independent_reviews", repo, y, med)
        else:
            put_metric(store, seen, "P4c_nonmaintainer_review_share", repo, y, None)
            put_metric(store, seen, "P4c_median_independent_reviews", repo, y, None)
        put_metric(store, seen, "P5a_sanction_events", repo, y, float(core["sanction"][m].sum()))
        # no sequence of lesser-then-greater actions is recorded
        put_metric(store, seen, "P5b_graduated_share", repo, y, None)
        # P6 contested
        contested = []
        for i in np.flatnonzero(m & core["decided"].astype(bool)):
            if not (has_ack[i] and has_nack[i]):
                continue
            end = float(core["merged_at"][i] if core["merged"][i] and np.isfinite(core["merged_at"][i]) else core["closed_at"][i])
            if not np.isfinite(end):
                continue
            explicit = bool(core["merged"][i]) or (end - float(last_att[i])) <= 30 * DAY
            contested.append(((end - float(core["created"][i])) / DAY, explicit))
        if len(contested) >= 5:
            put_metric(store, seen, "P6a_explicit_resolution_share", repo, y, float(np.mean([c[1] for c in contested])))
            put_metric(store, seen, "P6a_median_days_contested", repo, y, float(np.median([c[0] for c in contested])))
        else:
            put_metric(store, seen, "P6a_explicit_resolution_share", repo, y, None)
            put_metric(store, seen, "P6a_median_days_contested", repo, y, None)
        present_chronic = sum(1 for name in chronic if y in topic_years[name])
        put_metric(store, seen, "P6b_recurring_topics", repo, y, float(present_chronic))
        put_metric(store, seen, "P6c_exit_channels", repo, y, None)
        put_metric(store, seen, "P7a_funder_hhi", repo, y, None)
        put_metric(store, seen, "P7b_alt_impl_mentions", repo, y, None)
        # P8
        venues = 1  # github, because this repo-year has PRs
        if y in irc["irc_years"]:
            venues += 1
        if y in irc["mail_years"]:
            venues += 1
        if y in bt_years:
            venues += 1
        if y in delving_years:
            venues += 1
        put_metric(store, seen, "P8b_venue_count", repo, y, float(venues))
        local_shares = []
        year_mergers = defaultdict(int)
        for i in np.flatnonzero(merged_m):
            if int(core["merger"][i]) >= 0:
                year_mergers[int(core["merger"][i])] += 1
        top_level = {p for p, _c in sorted(year_mergers.items(), key=lambda kv: (-kv[1], kv[0]))[:5]}
        sub_detail = {}
        for bit, name in enumerate(SUBSYSTEMS):
            mask_bit = 1 << bit
            touched = [int(i) for i in np.flatnonzero(merged_m) if int(core["subsys"][i]) & mask_bit]
            if len(touched) < 5:
                continue
            reviewers = defaultdict(int)
            if em.any():
                touched_set = set(touched)
                for pr, person in zip(ev["pr"][em].tolist(), ev["person"][em].tolist()):
                    if int(pr) in touched_set:
                        reviewers[int(person)] += 1
            frequent = {p for p, c in reviewers.items() if c >= 5 and p not in top_level}
            local = sum(1 for i in touched if int(core["merger"][i]) in frequent)
            share = local / len(touched)
            local_shares.append(share)
            sub_detail[name] = {"merges": len(touched), "local_share": share}
        detail["P8a"][str(y)] = sub_detail
        put_metric(store, seen, "P8a_subsystem_local_share", repo, y, float(np.mean(local_shares)) if local_shares else None)
        put_metric(store, seen, "P8c_decision_locality", repo, y, float(np.mean(local_shares)) if local_shares else None)
        # Health. Computed from raw PR fields, not from principle scores.
        reviewers_y = set(given)
        put_metric(store, seen, "H1_active_reviewers_per_pr", repo, y, len(reviewers_y) / opened)
        year_end = datetime(y, 12, 31, 23, 59, tzinfo=timezone.utc).timestamp()
        if year_end > dataset_end:
            year_end = dataset_end
        open_end = 0
        stale = 0
        for i in np.flatnonzero(core["created"] <= year_end):
            end = core["merged_at"][i] if core["merged"][i] and np.isfinite(core["merged_at"][i]) else core["closed_at"][i]
            if not np.isfinite(end) or end > year_end:
                open_end += 1
                if float(core["created"][i]) <= year_end - YEAR:
                    stale += 1
        put_metric(store, seen, "H2_open_stock_per_pr_opened", repo, y, open_end / opened)
        put_metric(store, seen, "H2_stale_open_per_pr_opened", repo, y, stale / opened)
        # H3
        cohort = [p for p, fy in first_year.items() if fy == y]
        observable = []
        for p in cohort:
            first = first_pr_ts.get(p)
            if first is None or first + 2 * YEAR > dataset_end:
                continue
            observable.append(1.0 if person_last.get(p, 0.0) >= first + 2 * YEAR else 0.0)
        if len(observable) >= 10 and len(observable) >= 0.5 * max(len(cohort), 1):
            put_metric(store, seen, "H3_cohort_active_24m", repo, y, float(np.mean(observable)))
        else:
            put_metric(store, seen, "H3_cohort_active_24m", repo, y, None)
            if cohort:
                unavailable(
                    missing, f"H3_cohort_active_24m:{y}",
                    "entry cohort is not yet observable at 24 months for enough members, or has fewer than 10 observable people",
                )
        merge_counts = np.array([merges_received.get(p, 0) for p in authors_y], dtype=float)
        put_metric(store, seen, "H4_gini_merges", repo, y, gini(merge_counts))
        review_counts = np.array([given.get(p, 0) for p in (authors_y | set(given))], dtype=float)
        put_metric(store, seen, "H4_gini_reviews", repo, y, gini(review_counts) if review_counts.size else None)
        bf = bus_factor(np.array(list(year_mergers.values()), dtype=float) if year_mergers else merge_counts)
        # bus factor is among mergers' merge counts, not authors. Recompute from merger side.
        put_metric(store, seen, "H5_bus_factor", repo, y, None if bf is None else float(bf))
        decided = m & core["decided"].astype(bool)
        end = np.where(core["merged"].astype(bool), core["merged_at"], core["closed_at"])
        dd = (end[decided] - core["created"][decided]) / DAY
        dd = dd[np.isfinite(dd) & (dd >= 0)]
        put_metric(store, seen, "H6_median_days_to_decision", repo, y, float(np.median(dd)) if dd.size else None)
        if timeline_active.get(y, 0) > 0:
            put_metric(store, seen, "H7_exit_rate", repo, y, exits_by_year.get(y, 0) / timeline_active[y])
        else:
            put_metric(store, seen, "H7_exit_rate", repo, y, None)
    if sanction_total < 10:
        detail["P5"] = {"events": sanction_total, "low_observability": True, "scored": False}
    detail["P1a"] = {
        "n_inferred_grants": len(grant_windows),
        "n_with_discussion_30d": int(sum(hits)) if hits else 0,
        "note": "A grant is the estimated start of merge activity in the maintainer timeline, not a recorded vote.",
    }


def score_thin_repo(repo, thin, dataset_end, store, seen, missing, detail) -> None:
    years = sorted(set(int(y) for y in thin["year"].tolist()))
    first_year: Dict[str, int] = {}
    for login, y in zip(thin["author"], thin["year"].tolist()):
        first_year[login] = min(first_year.get(login, int(y)), int(y))
    topic_years: Dict[str, set] = {name: set() for name in TOPIC_NAMES}
    for mask, y in zip(thin["topics"].tolist(), thin["year"].tolist()):
        for b, name in enumerate(TOPIC_NAMES):
            if mask & (1 << b):
                topic_years[name].add(int(y))
    chronic = {name for name, ys in topic_years.items() if len(ys) >= 3}
    review_metrics = [
        "P2a_gini_provision_ratio", "P2a_share_ratio_near_one", "P2b_merge_review_correlation",
        "P2c_top5_review_share", "P3b_rule_participant_share", "P4a_self_merge_rate",
        "P4b_zero_independent_attention_share", "P4c_nonmaintainer_review_share",
        "P4c_median_independent_reviews", "P6a_explicit_resolution_share", "P6a_median_days_contested",
        "P8c_decision_locality", "H1_active_reviewers_per_pr", "H4_gini_reviews", "H7_exit_rate",
        "P1a_grant_discussion_share", "P3c_nonmerger_rule_merge_rate", "P7a_funder_hhi", "P8b_venue_count",
    ]
    unavailable(
        missing, repo,
        "PR dump lacks reviews, comments, file paths, merged_by, maintainer timeline, and an attrition timeline. "
        "Those indicators are omitted rather than filled with zeros.",
    )
    for y in years:
        m = thin["year"] == y
        opened = int(m.sum())
        if opened == 0:
            continue
        for metric in review_metrics:
            put_metric(store, seen, metric, repo, y, None)
        entrants = [p for p, fy in first_year.items() if fy == y]
        waits = []
        for p in entrants:
            idxs = [i for i, a in enumerate(thin["author"]) if a == p]
            first = min(float(thin["created"][i]) for i in idxs)
            mtimes = [float(thin["merged_at"][i]) for i in idxs if thin["merged"][i] and np.isfinite(thin["merged_at"][i])]
            if mtimes:
                waits.append((min(mtimes) - first) / DAY)
        if len(waits) >= 5 and float(np.mean(waits)) > 0:
            put_metric(store, seen, "P1b_entry_wait_cv", repo, y, float(np.std(waits) / np.mean(waits)))
        else:
            put_metric(store, seen, "P1b_entry_wait_cv", repo, y, None)
        put_metric(store, seen, "P1c_scope_disputes_per_100", repo, y, 100.0 * float(thin["scope"][m].mean()) if opened else None)
        put_metric(store, seen, "P3a_rule_pr_count", repo, y, float(thin["rule"][m].sum()))
        put_metric(store, seen, "P5a_sanction_events", repo, y, float(thin["sanction"][m].sum()))
        put_metric(store, seen, "P5b_graduated_share", repo, y, None)
        put_metric(store, seen, "P6b_recurring_topics", repo, y, float(sum(1 for name in chronic if y in topic_years[name])))
        put_metric(store, seen, "P6c_exit_channels", repo, y, None)
        put_metric(store, seen, "P7b_alt_impl_mentions", repo, y, None)
        put_metric(store, seen, "P8a_subsystem_local_share", repo, y, None)
        put_metric(store, seen, "P2a_share_ratio_above_one", repo, y, None)
        # health from timestamps only
        year_end = datetime(y, 12, 31, 23, 59, tzinfo=timezone.utc).timestamp()
        if year_end > dataset_end:
            year_end = dataset_end
        open_end = stale = 0
        for i in range(thin["created"].size):
            if float(thin["created"][i]) > year_end:
                continue
            end = float(thin["merged_at"][i] if thin["merged"][i] and np.isfinite(thin["merged_at"][i]) else thin["closed_at"][i])
            if not np.isfinite(end) or end > year_end:
                open_end += 1
                if float(thin["created"][i]) <= year_end - YEAR:
                    stale += 1
        put_metric(store, seen, "H2_open_stock_per_pr_opened", repo, y, open_end / opened)
        put_metric(store, seen, "H2_stale_open_per_pr_opened", repo, y, stale / opened)
        cohort = [p for p, fy in first_year.items() if fy == y]
        observable = []
        created_by = defaultdict(list)
        for i, login in enumerate(thin["author"]):
            created_by[login].append(float(thin["created"][i]))
        for p in cohort:
            times = created_by[p]
            first = min(times)
            if first + 2 * YEAR > dataset_end:
                continue
            observable.append(1.0 if any(t >= first + 2 * YEAR for t in times) else 0.0)
        if len(observable) >= 10 and len(observable) >= 0.5 * max(len(cohort), 1):
            put_metric(store, seen, "H3_cohort_active_24m", repo, y, float(np.mean(observable)))
        else:
            put_metric(store, seen, "H3_cohort_active_24m", repo, y, None)
        authors = set(a for a, yy in zip(thin["author"], thin["year"].tolist()) if int(yy) == y)
        counts = []
        for p in authors:
            counts.append(sum(1 for i, a in enumerate(thin["author"]) if a == p and int(thin["year"][i]) == y and thin["merged"][i]))
        put_metric(store, seen, "H4_gini_merges", repo, y, gini(np.asarray(counts, dtype=float)))
        bf = bus_factor(np.asarray([c for c in counts if c > 0], dtype=float))
        put_metric(store, seen, "H5_bus_factor", repo, y, None if bf is None else float(bf))
        dd = []
        for i in np.flatnonzero(m & thin["decided"].astype(bool)):
            end = float(thin["merged_at"][i] if thin["merged"][i] and np.isfinite(thin["merged_at"][i]) else thin["closed_at"][i])
            if np.isfinite(end):
                dd.append((end - float(thin["created"][i])) / DAY)
        dd = [v for v in dd if v >= 0]
        put_metric(store, seen, "H6_median_days_to_decision", repo, y, float(np.median(dd)) if dd else None)
    detail.setdefault("thin_alt", {})[repo] = _alt_summary(thin["alt"])


def _alt_summary(rows: List[Tuple[int, float]]) -> Dict[str, Any]:
    if not rows:
        return {"n": 0, "mean_sentiment": None, "sentiment_model_dependent": True}
    tones = [t for _y, t in rows]
    return {
        "n": len(rows),
        "mean_sentiment": float(np.mean(tones)),
        "sentiment_model_dependent": True,
        "by_year": {
            str(y): int(sum(1 for yy, _t in rows if yy == y))
            for y in sorted({yy for yy, _t in rows})
        },
    }


def collect_prior_tests(findings: Path, missing: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """Primary contrasts from passes 1 and 2. Year cells and stratum replications are not a second family."""
    out: List[Dict[str, Any]] = []
    specs = [
        (findings / "data" / "rsd_ingroup_analysis.json", "pass1"),
        (findings / "data" / "rsd_ingroup_analysis_v2.json", "pass2"),
    ]
    skip_keys = {
        "years", "by_entry_year", "one_year_cohorts", "two_year_cohorts", "plain_text_summary",
        "per_term_per_pr", "stratification", "entry_by_year",
    }

    def walk(obj: Any, path: str, source: str) -> None:
        if isinstance(obj, dict):
            if path.endswith("difference_in_minus_out") and "estimate" in obj and "ci95" in obj:
                _add_prior(out, source, path, obj["estimate"], obj["ci95"])
            if "interaction_per_year" in obj and isinstance(obj.get("ci95"), list):
                _add_prior(out, source, path + ".interaction_per_year", obj["interaction_per_year"], obj["ci95"])
            if "pearson_r" in obj and isinstance(obj.get("ci95"), list):
                _add_prior(out, source, path + ".pearson_r", obj["pearson_r"], obj["ci95"])
            if "in_group_log_odds" in obj and isinstance(obj.get("ci95_log_odds"), list):
                _add_prior(out, source, path + ".in_group_log_odds", obj["in_group_log_odds"], obj["ci95_log_odds"])
            if path.endswith("merge_rate_slope_per_year") and "estimate" in obj and "ci95" in obj:
                _add_prior(out, source, path, obj["estimate"], obj["ci95"])
            if path.endswith("cohort_fe_merge_rate_two_year") and "estimate" in obj and "ci95" in obj:
                _add_prior(out, source, path, obj["estimate"], obj["ci95"])
            if "slope_merge_rate_per_year" in obj and isinstance(obj.get("ci"), dict) and "ci95" in obj["ci"]:
                _add_prior(out, source, path + ".slope_merge_rate_per_year", obj["slope_merge_rate_per_year"], obj["ci"]["ci95"])
            for key, value in obj.items():
                if key in skip_keys or key in {"ci", "ci95"}:
                    continue
                walk(value, path + "." + key, source)
        elif isinstance(obj, list) and len(obj) <= 8:
            for i, value in enumerate(obj):
                walk(value, f"{path}[{i}]", source)

    for path, source in specs:
        if not path.exists():
            unavailable(missing, source, f"{path.name} is missing, so its tests cannot enter the BH family")
            continue
        walk(json.loads(path.read_text()), source, source)
    # de-duplicate ids
    seen = set()
    unique = []
    for row in out:
        if row["id"] in seen:
            continue
        seen.add(row["id"])
        unique.append(row)
    return unique


def _add_prior(out: List[Dict[str, Any]], source: str, path: str, estimate: Any, ci: Sequence[float]) -> None:
    if not isinstance(estimate, (int, float)) or not isinstance(ci, list) or len(ci) != 2:
        return
    p = p_from_ci(float(estimate), ci)
    out.append({
        "id": path,
        "effect": None,
        "mapped_principles": [],
        "estimate": float(estimate),
        "ci95": [float(ci[0]), float(ci[1])] if ci[0] is not None and ci[1] is not None else None,
        "p": p,
        "q": None,
        "n": None,
        "effect_size": float(estimate),
        "effect_size_kind": "pass_estimate",
        "effect_size_flag": None,
        "holdout_estimate": None,
        "holdout_ci95": None,
        "holdout_n": None,
        "holdout_same_sign": None,
        "holdout_status": "not_applicable",
        "sample": "as published in " + source,
        "in_bh_family": p is not None,
        "low_observability": False,
        "note": "p-value is a normal approximation from the published bootstrap interval, not a new fit.",
        "source": source,
    })


CANNOT_PROVE = [
    "Psychological states are not observable. The effects are behavioral signatures only.",
    "Ostrom's principles are correlates of durable commons, not proven causes of these outcomes.",
    "A series of about 16 years cannot establish causation. Lagged correlations are low power.",
    "P5, P7, E4b, and E11 rely on thin or model-dependent data. P5 and E11 are low observability because deleted and off-platform sanctions are missing. P7 has no person-to-funder ledger, and its sentiment is a keyword model. E4b depends on the function-word lists.",
    "Results that fail the 2024-2026 holdout or the Benjamini-Hochberg correction are exploratory.",
    "A commons can score poorly and still survive for a time on funding or reputation before the health metrics show it.",
]


def render_summary(tests, repo_rows, linkage, ranking, change_points, missing, core_repo: str) -> str:
    lines = []
    lines.append("Commons dynamics, pass 3.")
    lines.append("The resource is reviewer attention and merge authority. Effects, principles, and health are separate measurements.")
    lines.append("Year fixed effects are on every model because newcomer and in-group outcomes moved differently over time. Pass 2 did not show one bar rising for everyone.")
    lines.append("")
    confirmed = []
    for t in tests:
        if t.get("source") != "pass3" or not t.get("in_bh_family"):
            continue
        if not str(t.get("id") or "").startswith("E"):
            continue
        if t.get("estimate") is None or t.get("q") is None:
            continue
        if t["q"] >= 0.05 or not t.get("holdout_same_sign"):
            continue
        flag = t.get("effect_size_flag") or ""
        if str(flag).startswith("negligible"):
            continue
        size = t.get("effect_size")
        if t.get("effect_size_kind") == "standardized_coefficient" and size is not None and abs(size) < 0.2:
            continue
        confirmed.append(t)
    confirmed.sort(
        key=lambda t: abs(t["effect_size"] if t.get("effect_size") is not None else t["estimate"]),
        reverse=True,
    )
    lines.append("STRONGEST CONFIRMED EFFECTS")
    lines.append("Confirmed means: training estimate, q below 0.05 after BH across passes 1-3, same sign in 2024-2026, and not a negligible Cohen's d or a standardized coefficient under 0.2.")
    if not confirmed:
        lines.append("None cleared that bar.")
    else:
        for t in confirmed[:8]:
            lines.append(
                f"  {t['id']}: {t['estimate']:.4f} (95% CI {_fmt_ci(t.get('ci95'))}), "
                f"q={t['q']:.4f}, holdout {t.get('holdout_estimate')}, maps {', '.join(t.get('mapped_principles') or []) or 'none'}"
            )
    lines.append("")
    lines.append("WEAKEST PRINCIPLE BY PERIOD (bitcoin/bitcoin)")
    periods = [("2010-2015", range(2010, 2016)), ("2016-2021", range(2016, 2022)), ("2022-2026", range(2022, 2027))]
    core_rows = {(row["year"]): row for row in repo_rows if row["repo"] == core_repo}
    for label, years in periods:
        means = {}
        for p in ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"]:
            vals = [core_rows[y]["principles"][p] for y in years if y in core_rows and core_rows[y]["principles"][p] is not None]
            if vals:
                means[p] = float(np.mean(vals))
        if not means:
            lines.append(f"  {label}: DATA UNAVAILABLE")
            continue
        weakest = min(means, key=means.get)
        rendered = ", ".join(f"{p}={means[p]:.2f}" for p in sorted(means))
        lines.append(f"  {label}: weakest {weakest} ({means[weakest]:.2f}). {rendered}")
    lines.append("  P5 and P7 are unscored in every period: sanction traces are below 10 and there is no person-to-funder ledger.")
    lines.append("")
    lines.append("ASSOCIATED WITH LATER HEALTH (low power, about 16 years)")
    t2 = [row for row in linkage if row["test"] == "T2" and row.get("lag") == 1 and row.get("spearman") is not None]
    t3 = [row for row in linkage if row["test"] == "T3" and row.get("lag") == 1 and row.get("spearman") is not None]
    if t2:
        best = max(t2, key=lambda row: abs(row["spearman"]))
        lines.append(f"  Principle: {best['principle']} spearman {best['spearman']:.3f} with health at t+1 (n={best['n_years']}, p={best['p']:.3f}).")
    else:
        lines.append("  Principle: DATA UNAVAILABLE")
    if t3:
        best = max(t3, key=lambda row: abs(row["spearman"]))
        lines.append(f"  Effect: {best['effect']} spearman {best['spearman']:.3f} with health at t+1 (n={best['n_years']}, p={best['p']:.3f}).")
    else:
        lines.append("  Effect: DATA UNAVAILABLE")
    lines.append("These lagged tests are descriptive. The cross-repo comparison below is the sturdier contrast.")
    lines.append("")
    lines.append("CROSS-REPO RANKING")
    lines.append(
        "Ordered by shared-indicator health, then shared-indicator principles. "
        "Shared means entry-wait variation, scope disputes, recurring topics, backlog, "
        "24-month retention, merge Gini, bus factor, and median time to decision. "
        "Repos with fewer than 7 years are listed after the ranking and are not treated as leaders. "
        "bitcoin/bitcoin is the only full Ostrom profile; its review, monitoring, and exit indicators are not in this rank."
    )
    for row in ranking:
        if not row.get("ranked"):
            continue
        hp = "n/a" if row["mean_health"] is None else f"{row['mean_health']:.2f}"
        pp = "n/a" if row["mean_principle_score"] is None else f"{row['mean_principle_score']:.2f}"
        extra = ""
        if row["repo"] == "bitcoin/bitcoin":
            fh = row.get("full_profile_health")
            fp = row.get("full_profile_principle_score")
            extra = f" full profile health {fh if fh is None else round(fh, 2)}, principles {fp if fp is None else round(fp, 2)}"
        lines.append(f"  {row['repo']}: shared health {hp}, shared principles {pp}, years {row['n_years']}{extra}")
    short = [row for row in ranking if not row.get("ranked")]
    if short:
        lines.append("  Shorter series, not ranked:")
        for row in short:
            hp = "n/a" if row["mean_health"] is None else f"{row['mean_health']:.2f}"
            lines.append(f"    {row['repo']}: shared health {hp}, years {row['n_years']}")
    lines.append("")
    lines.append("LARGEST YEAR-TO-YEAR MOVES")
    moves = [c for c in change_points if c.get("year") and c.get("change_in_within_series_sd") is not None]
    moves.sort(key=lambda c: c.get("change_in_within_series_sd") or 0, reverse=True)
    for c in moves[:8]:
        lines.append(
            f"  {c['name']} in {c['year']}: {c['value_before']:.3f} -> {c['value_after']:.3f} "
            f"({c['change_in_within_series_sd']:.2f} within-series SD); "
            f"health before {c.get('health_mean_two_years_before')}, after {c.get('health_mean_two_years_after')}"
        )
    lines.append("")
    lines.append("WHAT THIS CANNOT PROVE")
    for i, text in enumerate(CANNOT_PROVE, start=1):
        lines.append(f"  ({i}) {text}")
    lines.append("")
    lines.append(f"DATA UNAVAILABLE entries: {len(missing)}. See data_unavailable in the JSON. Nothing in that list was filled with a zero.")
    return "\n".join(lines)


def _fmt_ci(ci: Optional[Sequence[float]]) -> str:
    if not ci or ci[0] is None or ci[1] is None:
        return "n/a"
    return f"{ci[0]:.4f} to {ci[1]:.4f}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Commons dynamics: effects, Ostrom principles, health")
    parser.add_argument("--bootstrap", type=int, default=N_BOOT_DEFAULT)
    parser.add_argument("--permutations", type=int, default=N_PERM_DEFAULT)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    payload = analyze(n_boot=args.bootstrap, n_perm=args.permutations, seed=args.seed)
    paths = save_analysis_json("commons_dynamics_analysis.json", payload)
    print(payload["plain_text_summary"])
    for path in paths:
        logger.info("wrote %s", path)


if __name__ == "__main__":
    main()
