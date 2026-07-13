#!/usr/bin/env python3
"""
Maintainer Premium Analysis (fair / complete pass)

Reports identity effects without soft-pedaling *or* overstating:

1. Raw merge rates (includes self-merge privilege)
2. Self-merge-adjusted rates (self-merge ≠ peer-reviewed success)
3. Cold-start vs established outsider splits
4. Size strata (large outsider failure)
5. Logistic OR with and without prior-merge control
   (prior merges = reputation/access, not PR quality)
6. Close-outcome proxies (no-review vs reviewed-then-closed)
7. Ever-maintainer vs active-at-creation sensitivity
8. All-time and 2022+ windows
9. Author-prep matching (body+tests; no reviews) + size-substance (not \"quality\")
"""

from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from scipy import stats

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger  # noqa: E402
from src.utils.maintainers import is_maintainer_at, load_maintainer_timeline  # noqa: E402
from src.utils.paths import get_analysis_dir, get_data_dir, get_findings_dir  # noqa: E402
from src.utils.pr_quality import (  # noqa: E402
    AUTHOR_PREP_HIGH,
    AUTHOR_PREP_MID_HIGH,
    author_prep_band,
    author_prep_score,
    consensus_ack_flags,
    engagement_score,
    has_nontrivial_test_diff,
    path_risk_band,
    size_substance_score,
)

logger = setup_logger()

SIZE_BINS = [
    (0, 50, "tiny_0_49"),
    (50, 500, "small_50_499"),
    (500, 2000, "medium_500_1999"),
    (2000, 10**12, "large_2000_plus"),
]

CLOSE_WIP_RE = re.compile(
    r"do not merge|don't merge|\[wip\]|\bwip\b|\[do not merge\]", re.I
)
CLOSE_SUPERSEDED_RE = re.compile(
    r"superse?ded|replaced by|closed in favor|obsoleted", re.I
)


def _safe_div(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None or b == 0:
        return None
    return a / b


def _close_proxy(row: Dict[str, Any]) -> Optional[str]:
    if row.get("merged") or not row.get("closed_unmerged"):
        return None
    blob = f"{row.get('title') or ''} {row.get('body_head') or ''}"
    reviews = int(row.get("total_reviews") or 0)
    nacks = int(row.get("nack_count") or 0)
    if CLOSE_WIP_RE.search(blob):
        return "staging_or_wip"
    if CLOSE_SUPERSEDED_RE.search(blob):
        return "superseded_keyword"
    if nacks >= 1:
        return "had_nack"
    if reviews == 0:
        return "no_reviews"
    return "reviewed_then_closed"


class MaintainerPremiumAnalyzer:
    def __init__(self) -> None:
        self.data_dir = get_data_dir()
        self.analysis_dir = get_analysis_dir() / "maintainer_premium"
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
        self.findings_dir = get_findings_dir() / "data"
        self.findings_dir.mkdir(parents=True, exist_ok=True)
        self.timeline = load_maintainer_timeline()

    def run_analysis(self) -> Dict[str, Any]:
        logger.info("Starting maintainer premium analysis (fair/complete v7 + phase2 signals)")
        df = self._load_frame()
        logger.info(
            "Loaded %s PRs (ever-maintainer=%s, active-at-creation=%s)",
            len(df),
            int(df["is_maintainer"].sum()),
            int(df["is_active_maintainer"].sum()),
        )

        windows = {
            "all_time": df,
            "from_2022": df[df["year"] >= 2022].copy(),
        }

        by_window: Dict[str, Any] = {}
        for name, sub in windows.items():
            if len(sub) < 200:
                continue
            by_window[name] = self._analyze_window(sub)

        all_time = by_window["all_time"]
        results = {
            "analysis_name": "maintainer_premium",
            "version": "7.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "fairness_framework": {
                "identity_definition_primary": "ever_maintainer",
                "identity_definition_sensitivity": "active_at_creation_via_timeline_periods",
                "self_merge_rule": "self_merge counted in raw rates; excluded from adjusted success",
                "prior_merges_rule": "reputation/access — report OR with and without this control",
                "closed_unmerged_rule": "not equated to Core rejection; split by close proxies",
                "quality_rule": (
                    "author_prep_score = body + test paths only (no reviews/LOC/merge). "
                    "size_substance_score is size-heavy — not quality. "
                    "engagement_score = reviews received — process only. "
                    "Canonical high author-prep band: score >= 0.65 (also report >= 0.5). "
                    "Phase 2: path_risk_band, concept/approach ACK text flags, nontrivial test diff — "
                    "ACK flags are received signals (not author prep). CI still unavailable."
                ),
                "primary_claims": [
                    "large_outsider_merge_failure",
                    "cold_start_first_pr",
                    "self_merge_privilege",
                    "reputation_channel_via_prior_merges",
                    "author_prep_matched_outsider_gap",
                    "merge_concentration_see_sister_report",
                ],
                "not_claimed_from_raw_bivariate_alone": [
                    "level_playing_field_80_vs_55",
                ],
                "not_claimed_as_true_quality": [
                    "size_substance_score",
                    "engagement_score",
                    "importance_bands",
                    "concept_ack_received",
                ],
            },
            "n_prs": all_time["n_prs"],
            "n_maintainer_authored": all_time["n_maintainer_authored"],
            # Back-compat + primary all_time slices
            "bivariate": all_time["bivariate_raw"],
            "bivariate_fair": all_time["bivariate_fair"],
            "controlled_logistic_merge": all_time["controlled_logistic_merge_with_prior"],
            "controlled_logistic_merge_without_prior": all_time[
                "controlled_logistic_merge_without_prior"
            ],
            "size_strata": all_time["size_strata"],
            "outsider_segments": all_time["outsider_segments"],
            "quality_matched": all_time["quality_matched"],
            "author_prep_matched": all_time["quality_matched"],
            "close_proxies": all_time["close_proxies"],
            "active_maintainer_sensitivity": all_time["active_maintainer_sensitivity"],
            "stratified_by_pr_type": all_time["stratified_by_pr_type"],
            "stall_metrics": all_time["stall_metrics"],
            "windows": by_window,
            "interpretation": self._interpret(by_window),
            "claim_summary": self._claim_summary(by_window),
        }

        payload = json.dumps(results, indent=2, default=str) + "\n"
        # Canonical cite path for reports; analysis/ keeps a thin compat file for older reporters.
        findings_path = self.findings_dir / "maintainer_premium.json"
        findings_path.write_text(payload, encoding="utf-8")

        # Backward compat: synthesize_timeline / generate_executive_summary expect statistics.json
        stats_compat = {
            "metrics": {
                "maintainer_merge_rate": (results.get("bivariate") or {}).get(
                    "maintainer_merge_rate"
                ),
                "non_maintainer_merge_rate": (results.get("bivariate") or {}).get(
                    "non_maintainer_merge_rate"
                ),
                "maintainer_median_time_to_merge": (results.get("bivariate") or {}).get(
                    "maintainer_median_days_to_merge"
                ),
                "non_maintainer_median_time_to_merge": (results.get("bivariate") or {}).get(
                    "non_maintainer_median_days_to_merge"
                ),
            },
            "statistical_tests": {
                "chi_square": (results.get("bivariate") or {}).get("chi_square_merge"),
            },
            "fair_claim_summary": results.get("claim_summary"),
            "version": results.get("version"),
            "canonical_findings_path": "findings/data/maintainer_premium.json",
        }
        (self.analysis_dir / "statistics.json").write_text(
            json.dumps(stats_compat, indent=2, default=str) + "\n", encoding="utf-8"
        )
        # Remove prior accidental full-JSON duplicate if present
        legacy_dup = self.analysis_dir / "maintainer_premium.json"
        if legacy_dup.exists():
            legacy_dup.unlink()
        logger.info("Wrote %s and %s", findings_path, self.analysis_dir / "statistics.json")
        return results

    def _analyze_window(self, df: pd.DataFrame) -> Dict[str, Any]:
        return {
            "n_prs": int(len(df)),
            "n_maintainer_authored": int(df["is_maintainer"].sum()),
            "bivariate_raw": self._bivariate_raw(df),
            "bivariate_fair": self._bivariate_fair(df),
            "controlled_logistic_merge_with_prior": self._controlled_logistic(
                df, include_prior=True
            ),
            "controlled_logistic_merge_without_prior": self._controlled_logistic(
                df, include_prior=False
            ),
            "size_strata": self._size_strata(df),
            "outsider_segments": self._outsider_segments(df),
            "quality_matched": self._quality_matched(df),
            "close_proxies": self._close_proxies(df),
            "active_maintainer_sensitivity": self._active_sensitivity(df),
            "first_pr_outsiders": self._first_pr_outsiders(df),
            "stratified_by_pr_type": self._stratified_by_type(df),
            "stall_metrics": self._stall_metrics(df),
        }

    def _load_frame(self) -> pd.DataFrame:
        path = self.data_dir / "processed" / "enriched_prs.jsonl"
        rows: List[Dict[str, Any]] = []
        author_merged_before: Dict[str, int] = defaultdict(int)
        records = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                records.append(json.loads(line))
        records.sort(key=lambda r: r.get("created_at") or "")

        for pr in records:
            author = (pr.get("author") or "").lower()
            merged_by = (pr.get("merged_by") or "").lower()
            created = pr.get("created_at") or ""
            tags = pr.get("maintainer_tags") or {}
            inv = pr.get("maintainer_involvement") or {}
            is_maint = bool(tags.get("author_is_maintainer") or inv.get("author_is_maintainer"))
            is_active = is_maintainer_at(
                author, created, self.timeline, require_active_period=True
            )
            cx = pr.get("complexity") or {}
            rm = pr.get("review_metrics") or {}
            pt = pr.get("pr_type") or {}
            td = pr.get("time_to_decision") or {}
            days = td.get("days_to_decision")
            if days is None and pr.get("time_to_merge_days") is not None:
                days = pr.get("time_to_merge_days")
            prior = author_merged_before[author]
            merged = bool(pr.get("merged"))
            if merged:
                author_merged_before[author] += 1
            self_merge = bool(merged and merged_by and author and merged_by == author)
            year = int(created[:4]) if len(created) >= 4 and created[:4].isdigit() else 0
            closed_unmerged = (not merged) and pr.get("state") == "closed"
            # Author-prep (no reviews/LOC); size-substance; engagement; Phase 2 flags
            prep = author_prep_score(pr)
            substance = size_substance_score(pr)
            engage = engagement_score(pr)
            ack = consensus_ack_flags(pr)
            row = {
                "number": pr.get("number"),
                "author": author,
                "is_maintainer": is_maint,
                "is_active_maintainer": is_active,
                "merged": merged,
                "self_merge": self_merge,
                "peer_merge": bool(merged and not self_merge),
                "open": (pr.get("state") == "open")
                or bool((pr.get("decision_outcome") or {}).get("open")),
                "closed_unmerged": closed_unmerged,
                "days_to_decision": days,
                "total_changes": int(cx.get("total_changes") or 0),
                "files_changed": int(cx.get("files_changed") or 0),
                "log_changes": math.log1p(int(cx.get("total_changes") or 0)),
                "total_reviews": int(rm.get("total_reviews") or 0),
                "approvals": int(rm.get("approvals") or 0),
                "nack_count": int(rm.get("nack_count") or 0),
                "primary_type": pt.get("primary_type") or "unknown",
                "consensus_related": bool(pt.get("consensus_related")),
                "prior_author_merges": prior,
                "log_prior_merges": math.log1p(prior),
                "is_first_pr": prior == 0,
                "is_established_outsider": (not is_maint) and prior >= 5,
                "author_prep_score": prep,
                "author_prep_band": author_prep_band(prep),
                "size_substance_score": substance,
                "engagement_score": engage,
                "has_nontrivial_test_diff": has_nontrivial_test_diff(pr),
                "has_concept_or_approach_ack": ack["has_concept_or_approach_ack"],
                "has_nack_text": ack["has_nack_text"],
                "path_risk": path_risk_band(pr),
                "created_at": created,
                "year": year,
                "title": pr.get("title") or "",
                "body_head": (pr.get("body") or "")[:500],
            }
            row["close_proxy"] = _close_proxy(row)
            rows.append(row)
        return pd.DataFrame(rows)

    def _merge_stats(self, x: pd.DataFrame) -> Dict[str, Any]:
        if len(x) == 0:
            return {
                "n": 0,
                "raw_merge_rate": None,
                "peer_merge_rate": None,
                "self_merge_rate": None,
                "closed_unmerged_rate": None,
            }
        return {
            "n": int(len(x)),
            "raw_merge_rate": float(x["merged"].mean()),
            "peer_merge_rate": float(x["peer_merge"].mean()),
            "self_merge_rate": float(x["self_merge"].mean()),
            "closed_unmerged_rate": float(x["closed_unmerged"].mean()),
        }

    def _bivariate_raw(self, df: pd.DataFrame) -> Dict[str, Any]:
        m = df[df["is_maintainer"]]
        n = df[~df["is_maintainer"]]
        mm, nn = float(m["merged"].mean()), float(n["merged"].mean())

        def median_days(x: pd.DataFrame) -> Optional[float]:
            s = x.loc[x["merged"] & x["days_to_decision"].notna(), "days_to_decision"]
            return float(s.median()) if len(s) else None

        md, nd = median_days(m), median_days(n)
        contingency = pd.crosstab(df["is_maintainer"], df["merged"])
        chi2, p_chi, dof, _ = stats.chi2_contingency(contingency)
        return {
            "maintainer_merge_rate": mm,
            "non_maintainer_merge_rate": nn,
            "merge_rate_ratio_maint_over_non": _safe_div(mm, nn),
            "maintainer_closed_unmerged_rate": float(m["closed_unmerged"].mean()),
            "non_maintainer_closed_unmerged_rate": float(n["closed_unmerged"].mean()),
            "maintainer_median_days_to_merge": md,
            "non_maintainer_median_days_to_merge": nd,
            "time_ratio_non_over_maint": _safe_div(nd, md) if md and nd else None,
            "chi_square_merge": {"chi2": float(chi2), "p_value": float(p_chi), "dof": int(dof)},
            "n_maintainer": int(len(m)),
            "n_non_maintainer": int(len(n)),
            "note": "Raw rates include self-merges as successes — use bivariate_fair for peer-reviewed comparison.",
        }

    def _bivariate_fair(self, df: pd.DataFrame) -> Dict[str, Any]:
        m = df[df["is_maintainer"]]
        n = df[~df["is_maintainer"]]
        ms, ns = self._merge_stats(m), self._merge_stats(n)
        return {
            "maintainer": ms,
            "non_maintainer": ns,
            "raw_merge_rate_ratio": _safe_div(ms["raw_merge_rate"], ns["raw_merge_rate"]),
            "peer_merge_rate_ratio": _safe_div(ms["peer_merge_rate"], ns["peer_merge_rate"]),
            "self_merge_share_of_maintainer_prs": ms["self_merge_rate"],
            "self_merge_share_of_maintainer_merges": (
                float(m.loc[m["merged"], "self_merge"].mean()) if m["merged"].any() else None
            ),
            "reading": (
                "If peer_merge rates converge, the raw maintainer premium is largely "
                "self-merge privilege rather than outsider rejection on typical PRs."
            ),
        }

    def _controlled_logistic(self, df: pd.DataFrame, include_prior: bool = True) -> Dict[str, Any]:
        try:
            from sklearn.linear_model import LogisticRegression
            from sklearn.preprocessing import StandardScaler
        except ImportError:
            return {"error": "sklearn not available"}

        sub = df[~df["open"]].copy()
        if len(sub) < 500:
            return {"error": "insufficient rows"}

        top_types = sub["primary_type"].value_counts().head(8).index.tolist()
        for t in top_types:
            sub[f"type_{t}"] = (sub["primary_type"] == t).astype(int)

        feature_cols = [
            "is_maintainer",
            "log_changes",
            "files_changed",
            "total_reviews",
            "nack_count",
            "consensus_related",
            "author_prep_score",
        ]
        if include_prior:
            feature_cols.insert(5, "log_prior_merges")
        feature_cols = feature_cols + [f"type_{t}" for t in top_types]

        X = sub[feature_cols].astype(float).fillna(0)
        y = sub["merged"].astype(int)
        scaler = StandardScaler()
        scale_cols = [
            c
            for c in feature_cols
            if c
            in {
                "log_changes",
                "files_changed",
                "total_reviews",
                "nack_count",
                "log_prior_merges",
                "author_prep_score",
            }
        ]
        X_scaled = X.copy()
        X_scaled[scale_cols] = scaler.fit_transform(X[scale_cols])

        model = LogisticRegression(max_iter=1000, solver="lbfgs")
        model.fit(X_scaled, y)
        coefs = dict(zip(feature_cols, [float(c) for c in model.coef_[0]]))
        odds = {k: float(math.exp(v)) for k, v in coefs.items()}

        merits_cols = [c for c in feature_cols if c != "is_maintainer"]
        m0 = LogisticRegression(max_iter=1000, solver="lbfgs")
        m1 = LogisticRegression(max_iter=1000, solver="lbfgs")
        m0.fit(X_scaled[merits_cols], y)
        m1.fit(X_scaled[feature_cols], y)

        def loglik(model_, X_, y_):
            p = model_.predict_proba(X_)[:, 1]
            p = np.clip(p, 1e-9, 1 - 1e-9)
            return float(np.sum(y_ * np.log(p) + (1 - y_) * np.log(1 - p)))

        ll0 = loglik(m0, X_scaled[merits_cols], y)
        ll1 = loglik(m1, X_scaled[feature_cols], y)
        lr_stat = 2 * (ll1 - ll0)
        lr_p = float(stats.chi2.sf(lr_stat, df=1))

        # Secondary: peer-merge outcome (self-merge counts as failure for identity test)
        y_peer = sub["peer_merge"].astype(int)
        model_p = LogisticRegression(max_iter=1000, solver="lbfgs")
        model_p.fit(X_scaled, y_peer)
        odds_peer = {
            k: float(math.exp(v)) for k, v in zip(feature_cols, model_p.coef_[0])
        }

        return {
            "n": int(len(sub)),
            "include_prior_merges_control": include_prior,
            "outcome": "merged_including_self_merge",
            "coefficients": coefs,
            "odds_ratios": odds,
            "maintainer_odds_ratio": odds.get("is_maintainer"),
            "prior_merges_odds_ratio": odds.get("log_prior_merges"),
            "author_prep_odds_ratio": odds.get("author_prep_score"),
            "likelihood_ratio_test_add_maintainer": {
                "lr_stat": lr_stat,
                "p_value": lr_p,
                "df": 1,
            },
            "peer_merge_outcome": {
                "maintainer_odds_ratio": odds_peer.get("is_maintainer"),
                "note": "Dependent variable = merged AND not self-merged",
            },
            "features": feature_cols,
        }

    def _quality_matched(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Author-prep matched contrasts (primary) + size-substance descriptive only."""
        work = df.copy()

        def contrast(mask: pd.Series) -> Dict[str, Any]:
            g = work[mask]
            m = g[g["is_maintainer"]]
            n = g[~g["is_maintainer"]]
            return {
                "n": int(len(g)),
                "mean_author_prep": float(g["author_prep_score"].mean()) if len(g) else None,
                "maintainer": self._merge_stats(m),
                "non_maintainer": self._merge_stats(n),
                "raw_merge_gap_pp": (
                    (float(m["merged"].mean()) - float(n["merged"].mean())) * 100
                    if len(m) and len(n)
                    else None
                ),
            }

        by_band = {}
        for band, g in work.groupby("author_prep_band"):
            m = g[g["is_maintainer"]]
            n = g[~g["is_maintainer"]]
            by_band[str(band)] = {
                "n": int(len(g)),
                "mean_author_prep": float(g["author_prep_score"].mean()),
                "maintainer": self._merge_stats(m),
                "non_maintainer": self._merge_stats(n),
            }

        m_all = work[work["is_maintainer"]]
        n_all = work[~work["is_maintainer"]]
        high = work["author_prep_score"] >= AUTHOR_PREP_HIGH
        mid_high = work["author_prep_score"] >= AUTHOR_PREP_MID_HIGH

        # Size-substance high = top third by score (descriptive; size-heavy)
        sub_cut = float(work["size_substance_score"].quantile(2 / 3))
        high_sub = work["size_substance_score"] >= sub_cut

        out: Dict[str, Any] = {
            "score_definitions": {
                "author_prep_score": (
                    "Body length bands + test-path touch only. No reviews/LOC/merge. "
                    f"High band >= {AUTHOR_PREP_HIGH}; also report >= {AUTHOR_PREP_MID_HIGH}."
                ),
                "size_substance_score": (
                    "Ex-outcome size/files substance — NOT quality. Descriptive only."
                ),
                "engagement_score": "Reviews received — process only; not used for matching.",
                "importance": "Excluded from claims (keyword classifier over-tags critical).",
                "path_risk": "Path-based risk band (consensus/security/net/other).",
                "concept_ack": "Received concept/approach ACK text — process signal, not author prep.",
            },
            "thresholds": {
                "author_prep_high": AUTHOR_PREP_HIGH,
                "author_prep_mid_high": AUTHOR_PREP_MID_HIGH,
                "size_substance_high_quantile_cut": sub_cut,
            },
            "mean_scores": {
                "maintainer_author_prep": float(m_all["author_prep_score"].mean())
                if len(m_all)
                else None,
                "non_maintainer_author_prep": float(n_all["author_prep_score"].mean())
                if len(n_all)
                else None,
                "maintainer_engagement": float(m_all["engagement_score"].mean())
                if len(m_all)
                else None,
                "non_maintainer_engagement": float(n_all["engagement_score"].mean())
                if len(n_all)
                else None,
            },
            "by_author_prep_band": by_band,
            "high_author_prep_ge_065": contrast(high),
            "author_prep_ge_050": contrast(mid_high),
            "high_size_substance_contrast": {
                **contrast(high_sub),
                "note": (
                    "High substance ≈ larger PRs; outsider merge rates here often look "
                    "worse — size exclusion, not 'low quality'."
                ),
            },
            "phase2": {
                "by_path_risk": {},
                "concept_ack_received": contrast(work["has_concept_or_approach_ack"]),
                "high_prep_and_nontrivial_tests": contrast(
                    high & work["has_nontrivial_test_diff"]
                ),
                "ci_status": "unavailable_on_enriched_corpus",
            },
            "high_readiness_contrast": contrast(high),
            "high_substance_contrast": {
                **contrast(high_sub),
                "note": "Alias of high_size_substance_contrast",
            },
        }
        for band, g in work.groupby("path_risk"):
            m = g[g["is_maintainer"]]
            n = g[~g["is_maintainer"]]
            out["phase2"]["by_path_risk"][str(band)] = {
                "n": int(len(g)),
                "maintainer": self._merge_stats(m),
                "non_maintainer": self._merge_stats(n),
            }
        return out

    def _size_strata(self, df: pd.DataFrame) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for lo, hi, name in SIZE_BINS:
            g = df[(df["total_changes"] >= lo) & (df["total_changes"] < hi)]
            if len(g) < 30:
                continue
            m = g[g["is_maintainer"]]
            n = g[~g["is_maintainer"]]
            out[name] = {
                "loc_range": [lo, None if hi > 10**11 else hi],
                "n": int(len(g)),
                "maintainer": self._merge_stats(m),
                "non_maintainer": self._merge_stats(n),
                "raw_merge_rate_ratio": _safe_div(
                    float(m["merged"].mean()) if len(m) else None,
                    float(n["merged"].mean()) if len(n) else None,
                ),
                "peer_merge_rate_ratio": _safe_div(
                    float(m["peer_merge"].mean()) if len(m) else None,
                    float(n["peer_merge"].mean()) if len(n) else None,
                ),
            }
        for thr in (2000, 5000):
            g = df[df["total_changes"] >= thr]
            if len(g) < 20:
                continue
            m = g[g["is_maintainer"]]
            n = g[~g["is_maintainer"]]
            # Prefer closed-only for large-PR outcome clarity
            gc = g[~g["open"]]
            mc, nc = gc[gc["is_maintainer"]], gc[~gc["is_maintainer"]]
            out[f"ge_{thr}_loc"] = {
                "n": int(len(g)),
                "maintainer": self._merge_stats(m),
                "non_maintainer": self._merge_stats(n),
                "closed_only": {
                    "n": int(len(gc)),
                    "maint_raw_merge": float(mc["merged"].mean()) if len(mc) else None,
                    "non_raw_merge": float(nc["merged"].mean()) if len(nc) else None,
                    "ratio": _safe_div(
                        float(mc["merged"].mean()) if len(mc) else None,
                        float(nc["merged"].mean()) if len(nc) else None,
                    ),
                },
            }
        return out

    def _outsider_segments(self, df: pd.DataFrame) -> Dict[str, Any]:
        non = df[~df["is_maintainer"]]
        cold = non[non["is_first_pr"]]
        established = non[non["prior_author_merges"] >= 5]
        mid = non[(non["prior_author_merges"] >= 1) & (non["prior_author_merges"] < 5)]
        # Top-20 volume non-maintainer authors in this window
        top_authors = (
            non.groupby("author").size().sort_values(ascending=False).head(20).index
        )
        top = non[non["author"].isin(top_authors)]
        maint = df[df["is_maintainer"]]
        return {
            "cold_start_first_pr": self._merge_stats(cold),
            "mid_1_to_4_prior_merges": self._merge_stats(mid),
            "established_ge_5_prior_merges": self._merge_stats(established),
            "top_20_volume_non_maintainer_authors": {
                **self._merge_stats(top),
                "n_authors": int(len(top_authors)),
            },
            "maintainer_reference": self._merge_stats(maint),
            "reading": (
                "Established and high-volume outsiders often approach maintainer raw merge "
                "rates on typical work; cold-start and large-LOC remain the exclusion zones."
            ),
        }

    def _first_pr_outsiders(self, df: pd.DataFrame) -> Dict[str, Any]:
        first = df[df["is_first_pr"] & ~df["is_maintainer"]]
        first_m = df[df["is_first_pr"] & df["is_maintainer"]]
        return {
            "n_first_pr_non_maintainer": int(len(first)),
            "first_pr_non_maintainer_merge_rate": float(first["merged"].mean())
            if len(first)
            else None,
            "first_pr_non_maintainer_peer_merge_rate": float(first["peer_merge"].mean())
            if len(first)
            else None,
            "n_first_pr_maintainer": int(len(first_m)),
            "first_pr_maintainer_merge_rate": float(first_m["merged"].mean())
            if len(first_m)
            else None,
            "closed_unmerged_rate_first_pr_non": float(first["closed_unmerged"].mean())
            if len(first)
            else None,
        }

    def _close_proxies(self, df: pd.DataFrame) -> Dict[str, Any]:
        cu = df[df["closed_unmerged"]]
        if len(cu) == 0:
            return {"n": 0}

        def pack(x: pd.DataFrame) -> Dict[str, Any]:
            counts = Counter(x["close_proxy"].dropna().tolist())
            n = int(len(x))
            return {
                "n": n,
                "counts": dict(counts),
                "shares": {k: v / n for k, v in counts.items()},
            }

        return {
            "all_closed_unmerged": pack(cu),
            "maintainer_authored": pack(cu[cu["is_maintainer"]]),
            "non_maintainer_authored": pack(cu[~cu["is_maintainer"]]),
            "note": (
                "no_reviews ≈ abandoned / never engaged / ignored — not proven Core rejection. "
                "reviewed_then_closed is closer to contested non-merge. "
                "Explicit NACK and superseded keywords are rare in text."
            ),
        }

    def _active_sensitivity(self, df: pd.DataFrame) -> Dict[str, Any]:
        ever_m = df[df["is_maintainer"]]
        ever_n = df[~df["is_maintainer"]]
        act_m = df[df["is_active_maintainer"]]
        act_n = df[~df["is_active_maintainer"]]
        disagree = int((df["is_maintainer"] != df["is_active_maintainer"]).sum())
        return {
            "ever_maintainer": {
                "maintainer": self._merge_stats(ever_m),
                "non_maintainer": self._merge_stats(ever_n),
            },
            "active_at_creation": {
                "maintainer": self._merge_stats(act_m),
                "non_maintainer": self._merge_stats(act_n),
            },
            "n_label_disagreement": disagree,
            "note": (
                "Active-at-creation uses timeline merge periods; people outside their "
                "estimated active window move to the non-maintainer side."
            ),
        }

    def _stratified_by_type(self, df: pd.DataFrame) -> Dict[str, Any]:
        out = {}
        for t, g in df.groupby("primary_type"):
            if len(g) < 50:
                continue
            m = g[g["is_maintainer"]]
            n = g[~g["is_maintainer"]]
            out[str(t)] = {
                "n": int(len(g)),
                "maint_raw_merge": float(m["merged"].mean()) if len(m) else None,
                "non_raw_merge": float(n["merged"].mean()) if len(n) else None,
                "maint_peer_merge": float(m["peer_merge"].mean()) if len(m) else None,
                "non_peer_merge": float(n["peer_merge"].mean()) if len(n) else None,
            }
        return out

    def _stall_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        open_df = df[df["open"]]
        closed_u = df[df["closed_unmerged"]]
        return {
            "open_n": int(len(open_df)),
            "open_maint_share": float(open_df["is_maintainer"].mean()) if len(open_df) else None,
            "closed_unmerged_n": int(len(closed_u)),
            "closed_unmerged_maint_share": float(closed_u["is_maintainer"].mean())
            if len(closed_u)
            else None,
            "closed_unmerged_maint_rate": float(
                closed_u[closed_u["is_maintainer"]].shape[0]
                / max(df["is_maintainer"].sum(), 1)
            ),
            "closed_unmerged_non_rate": float(
                closed_u[~closed_u["is_maintainer"]].shape[0]
                / max((~df["is_maintainer"]).sum(), 1)
            ),
        }

    def _claim_summary(self, by_window: Dict[str, Any]) -> Dict[str, Any]:
        """Machine-readable fair claims for the synthesis report."""
        claims = {}
        for name, w in by_window.items():
            fair = w["bivariate_fair"]
            segs = w["outsider_segments"]
            large = (w.get("size_strata") or {}).get("ge_2000_loc") or {}
            large5 = (w.get("size_strata") or {}).get("ge_5000_loc") or {}
            close = w.get("close_proxies") or {}
            claims[name] = {
                "raw_maint_vs_non_merge": [
                    fair["maintainer"]["raw_merge_rate"],
                    fair["non_maintainer"]["raw_merge_rate"],
                ],
                "peer_maint_vs_non_merge": [
                    fair["maintainer"]["peer_merge_rate"],
                    fair["non_maintainer"]["peer_merge_rate"],
                ],
                "self_merge_share_of_maintainer_merges": fair.get(
                    "self_merge_share_of_maintainer_merges"
                ),
                "cold_start_merge": segs["cold_start_first_pr"]["raw_merge_rate"],
                "established_outsider_merge": segs["established_ge_5_prior_merges"][
                    "raw_merge_rate"
                ],
                "top20_outsider_merge": segs["top_20_volume_non_maintainer_authors"][
                    "raw_merge_rate"
                ],
                "large_2k_closed_non_merge": (large.get("closed_only") or {}).get(
                    "non_raw_merge"
                ),
                "large_2k_closed_ratio": (large.get("closed_only") or {}).get("ratio"),
                "large_5k_closed_non_merge": (large5.get("closed_only") or {}).get(
                    "non_raw_merge"
                ),
                "or_without_prior": (
                    w.get("controlled_logistic_merge_without_prior") or {}
                ).get("maintainer_odds_ratio"),
                "or_with_prior": (w.get("controlled_logistic_merge_with_prior") or {}).get(
                    "maintainer_odds_ratio"
                ),
                "author_prep_or": (
                    w.get("controlled_logistic_merge_without_prior") or {}
                ).get("author_prep_odds_ratio"),
                "closed_unmerged_no_review_share_non": (
                    ((close.get("non_maintainer_authored") or {}).get("shares") or {}).get(
                        "no_reviews"
                    )
                ),
                "closed_unmerged_reviewed_share_non": (
                    ((close.get("non_maintainer_authored") or {}).get("shares") or {}).get(
                        "reviewed_then_closed"
                    )
                ),
                "high_author_prep_maint_merge": (
                    ((w.get("quality_matched") or {}).get("high_author_prep_ge_065") or {})
                    .get("maintainer")
                    or {}
                ).get("raw_merge_rate"),
                "high_author_prep_non_merge": (
                    ((w.get("quality_matched") or {}).get("high_author_prep_ge_065") or {})
                    .get("non_maintainer")
                    or {}
                ).get("raw_merge_rate"),
                "high_author_prep_gap_pp": (
                    (w.get("quality_matched") or {}).get("high_author_prep_ge_065") or {}
                ).get("raw_merge_gap_pp"),
                "author_prep_ge_050_gap_pp": (
                    (w.get("quality_matched") or {}).get("author_prep_ge_050") or {}
                ).get("raw_merge_gap_pp"),
                "mean_author_prep_maint_vs_non": [
                    ((w.get("quality_matched") or {}).get("mean_scores") or {}).get(
                        "maintainer_author_prep"
                    ),
                    ((w.get("quality_matched") or {}).get("mean_scores") or {}).get(
                        "non_maintainer_author_prep"
                    ),
                ],
                "phase2_concept_ack_gap_pp": (
                    ((w.get("quality_matched") or {}).get("phase2") or {})
                    .get("concept_ack_received")
                    or {}
                ).get("raw_merge_gap_pp"),
                "phase2_high_prep_test_diff_gap_pp": (
                    ((w.get("quality_matched") or {}).get("phase2") or {})
                    .get("high_prep_and_nontrivial_tests")
                    or {}
                ).get("raw_merge_gap_pp"),
                "phase2_ci": (
                    ((w.get("quality_matched") or {}).get("phase2") or {}).get("ci_status")
                ),
            }
        return claims

    def _interpret(self, by_window: Dict[str, Any]) -> str:
        parts = []
        for name, w in by_window.items():
            fair = w["bivariate_fair"]
            segs = w["outsider_segments"]
            large = (w.get("size_strata") or {}).get("ge_2000_loc") or {}
            qm = w.get("quality_matched") or {}
            hp = qm.get("high_author_prep_ge_065") or {}
            parts.append(
                f"[{name}] raw maint/non="
                f"{fair['maintainer']['raw_merge_rate']:.3f}/"
                f"{fair['non_maintainer']['raw_merge_rate']:.3f}; "
                f"peer maint/non="
                f"{fair['maintainer']['peer_merge_rate']:.3f}/"
                f"{fair['non_maintainer']['peer_merge_rate']:.3f}; "
                f"cold={segs['cold_start_first_pr']['raw_merge_rate']:.3f}; "
                f"established={segs['established_ge_5_prior_merges']['raw_merge_rate']:.3f}; "
                f"large≥2k closed non="
                f"{(large.get('closed_only') or {}).get('non_raw_merge')}; "
                f"author-prep≥0.65 maint/non="
                f"{(hp.get('maintainer') or {}).get('raw_merge_rate')}/"
                f"{(hp.get('non_maintainer') or {}).get('raw_merge_rate')} "
                f"(gap_pp={hp.get('raw_merge_gap_pp')})."
            )
        parts.append(
            "Fair reading: self-merge drives most of the average-case raw gap; "
            "cold-start and large outsider PRs remain strongly disadvantaged; "
            "established outsiders do comparatively well on ordinary work; "
            "prior-merge controls absorb reputation and must not be the sole headline; "
            "author-prep matching (body+tests, no reviews) still shows an identity gap — "
            "size_substance is size-heavy and must not be read as quality."
        )
        return " ".join(parts)


def main() -> int:
    results = MaintainerPremiumAnalyzer().run_analysis()
    print(json.dumps({
        "version": results.get("version"),
        "claim_summary": results.get("claim_summary"),
        "interpretation": results.get("interpretation"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
