"""Architectural PR classification for Core vs Commons divergence study.

Tiered pipeline:
  1. GitHub labels (label_map.yaml)
  2a. Keywords + explicit path prefixes
  2b. File-debt join (code_turnover_analysis.json)
  3. Cursor batches for ambiguous cases (export/import scripts)

Does not replace src.utils.pr_classification (governance importance).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

CATEGORIES = [
    "debt_compensation",
    "refactor",
    "new_feature",
    "consensus_change",
    "networking_change",
    "rpc_change",
    "dependency_maintenance",
    "test_ci_build",
    "documentation",
    "other",
]

# Headline metric groupings (plan decisions)
ARCHITECTURAL_DEBT_TAX = {"debt_compensation"}
TOTAL_MAINTENANCE = {"debt_compensation", "dependency_maintenance", "test_ci_build"}
STRUCTURAL = {"refactor"}
NET_NEW = {"new_feature", "consensus_change", "networking_change", "rpc_change"}


@dataclass
class ClassificationResult:
    number: int
    primary: str
    secondary: List[str] = field(default_factory=list)
    confidence: str = "low"  # low | medium | high
    tier_used: str = "none"
    evidence: List[str] = field(default_factory=list)
    scores: Dict[str, float] = field(default_factory=dict)
    ambiguous: bool = False
    title: str = ""
    merged_at: Optional[str] = None
    labels: List[str] = field(default_factory=list)
    files_sample: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _normalize_labels(raw: Any) -> List[str]:
    labels: List[str] = []
    for item in raw or []:
        if isinstance(item, dict):
            name = item.get("name") or ""
        else:
            name = str(item)
        if name:
            labels.append(name)
    return labels


def _load_yaml(path: Path) -> Dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML required: pip install pyyaml")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class ArchitecturalClassifier:
    """Classify merged Core PRs into architectural categories."""

    def __init__(
        self,
        classification_dir: Path,
        debt_json_path: Optional[Path] = None,
        debt_score_threshold: float = 50.0,
    ):
        self.classification_dir = Path(classification_dir)
        self.label_cfg = _load_yaml(self.classification_dir / "label_map.yaml")
        self.path_cfg = _load_yaml(self.classification_dir / "core_path_map.yaml")
        self.keyword_cfg = _load_yaml(self.classification_dir / "keyword_rules.yaml")

        self.label_map = {
            k.lower(): v for k, v in (self.label_cfg.get("label_map") or {}).items()
        }
        self.debt_boost_labels = {
            x.lower() for x in (self.label_cfg.get("debt_compensation_boost_labels") or [])
        }

        path_entries = self.path_cfg.get("path_map") or []
        self.path_map: List[Tuple[str, str]] = sorted(
            [(e["prefix"], e["category"]) for e in path_entries],
            key=lambda x: len(x[0]),
            reverse=True,
        )
        self.debt_hotspots = set(self.path_cfg.get("debt_hotspot_files") or [])

        self.keyword_rules = self.keyword_cfg.get("keyword_rules") or {}
        self.enrich_map = self.keyword_cfg.get("enrich_pr_type_map") or {}

        self.debt_scores: Dict[str, float] = {}
        self.debt_score_threshold = debt_score_threshold
        if debt_json_path and Path(debt_json_path).exists():
            data = json.loads(Path(debt_json_path).read_text(encoding="utf-8"))
            for path, metrics in (data.get("file_metrics") or {}).items():
                score = metrics.get("debt_score")
                if score is not None:
                    self.debt_scores[path] = float(score)

    def classify(self, pr: Dict[str, Any]) -> ClassificationResult:
        number = int(pr.get("number") or 0)
        title = pr.get("title") or ""
        body = pr.get("body") or ""
        text = f"{title}\n{body}".lower()
        labels = _normalize_labels(pr.get("labels"))
        files = [f.get("filename") for f in (pr.get("files") or []) if f.get("filename")]

        scores: Dict[str, float] = {c: 0.0 for c in CATEGORIES}
        evidence: List[str] = []
        tiers_hit: List[str] = []

        # Tier 1: labels
        domain_other = {
            "wallet",
            "gui",
            "qt",
            "mempool",
            "tx fees and policy",
            "mining",
            "macos",
            "windows",
            "linux/unix",
        }
        buildish = {"build system", "tests", "ci", "ci failed", "scripts and tools"}
        has_domain_other = False
        has_buildish = False
        for lab in labels:
            cat = self.label_map.get(lab.lower())
            if cat and cat in scores:
                scores[cat] += 4.0
                evidence.append(f"label:{lab}->{cat}")
                tiers_hit.append("1")
            if lab.lower() in self.debt_boost_labels:
                scores["debt_compensation"] += 2.0
                evidence.append(f"label_boost:{lab}->debt_compensation")
                tiers_hit.append("1")
            if lab.lower() in domain_other:
                has_domain_other = True
            if lab.lower() in buildish:
                has_buildish = True
        # Build/Tests labels must not drown wallet/policy/GUI primaries (Tier 3 lesson)
        if has_domain_other and has_buildish:
            scores["other"] += 6.0
            scores["test_ci_build"] = max(0.0, scores["test_ci_build"] - 4.0)
            evidence.append("override:domain_over_buildish")
            tiers_hit.append("1")

        # --- Tier 2a: paths ---
        # Cap per-category path contribution so mega subtree PRs (hundreds of
        # files) cannot drown title/label signals via raw file count.
        path_votes: Dict[str, int] = {}
        for fn in files:
            cat = self._path_category(fn)
            if cat:
                path_votes[cat] = path_votes.get(cat, 0) + 1
        if path_votes:
            for cat, n in path_votes.items():
                # 1.5 each for first 8 files, then diminishing
                capped = min(n, 8) * 1.5 + min(max(n - 8, 0), 20) * 0.25
                scores[cat] += capped
            top_path = max(path_votes.items(), key=lambda x: x[1])
            evidence.append(f"paths:{dict(path_votes)}")
            tiers_hit.append("2a")
            scores[top_path[0]] += 2.0

        hotspot_hits = [f for f in files if f in self.debt_hotspots]
        # Hotspot files alone are not debt_compensation; they only amplify when
        # a performance / lock / IBD signal is also present (checked after keywords).

        # --- Tier 2a: keywords ---
        # Strong debt keywords gate debt_join / refactor-skip. Weak ones
        # (cs_main, ibd, bare "performance"/"optimiz") often appear in
        # refactor/docs bodies and caused round-1/2 false positives.
        strong_debt_kws = {
            "lock contention",
            "deadlock",
            "race condition",
            "thread pool",
            "paralleliz",
            "reduce memory",
            "oom",
            "memory usage",
            "cpu usage",
            "hot path",
            "avoid lock",
            "release lock",
            "prefetch",
            "sync improvement",
            "initial block download",
            "latency",
            "throughput",
            "cache miss",
            "caching",
            "perf:",
        }
        weak_debt_kws = {
            "cs_main",
            "cs_wallet",
            "ibd",
            "performance",
            "optimiz",
            "speed up",
            "faster",
        }
        debt_kw_matched: List[str] = []
        strong_debt_matched: List[str] = []
        weak_debt_in_title: List[str] = []
        title_l_early = title.lower()
        for cat, rule in self.keyword_rules.items():
            weight = float(rule.get("weight") or 1)
            matched = [kw for kw in (rule.get("any") or []) if kw.lower() in text]
            if matched:
                scores[cat] += weight * min(len(matched), 3)
                evidence.append(f"kw:{cat}:{matched[:3]}")
                tiers_hit.append("2a")
                if cat == "debt_compensation":
                    debt_kw_matched = matched
                    strong_debt_matched = [m for m in matched if m.lower() in strong_debt_kws]
                    weak_debt_in_title = [
                        m
                        for m in matched
                        if m.lower() in weak_debt_kws and m.lower() in title_l_early
                    ]

        # Weak enrich_data signal
        enrich_perf = False
        pr_type = pr.get("pr_type") or {}
        if isinstance(pr_type, dict):
            primary_type = pr_type.get("primary_type")
            mapped = self.enrich_map.get(primary_type)
            if mapped and mapped in scores:
                # enrich over-assigns consensus — keep weak
                boost = 0.5 if mapped != "consensus_change" else 0.25
                if pr_type.get("confidence") == "high":
                    boost *= 1.5
                scores[mapped] += boost
                evidence.append(f"enrich:{primary_type}->{mapped}")
            if "performance" in (pr_type.get("subtypes") or []):
                enrich_perf = True
                scores["debt_compensation"] += 1.0
                evidence.append("enrich_subtype:performance->debt_compensation")

        label_debt_boost = any(lab.lower() in self.debt_boost_labels for lab in labels)
        # Gate debt_join on strong evidence — enrich_perf alone is too noisy
        has_debt_signal = bool(strong_debt_matched) or bool(weak_debt_in_title) or label_debt_boost
        if enrich_perf and (strong_debt_matched or weak_debt_in_title or label_debt_boost):
            has_debt_signal = True
        # Keep a soft flag for util:/title helpers that previously used enrich_perf
        debt_signal_soft = has_debt_signal or enrich_perf or bool(debt_kw_matched)

        if hotspot_hits and has_debt_signal:
            scores["debt_compensation"] += 1.5 * min(len(hotspot_hits), 5)
            evidence.append(f"hotspots:{hotspot_hits[:5]}")
            tiers_hit.append("2a")

        # --- Tier 2b: file-debt join (requires debt signal; else soft hint only) ---
        high_debt_files = []
        for fn in files:
            score = self.debt_scores.get(fn)
            if score is not None and score >= self.debt_score_threshold:
                high_debt_files.append((fn, score))
        if high_debt_files:
            evidence.append(
                "debt_join:"
                + ",".join(f"{p}={s:.0f}" for p, s in sorted(high_debt_files, key=lambda x: -x[1])[:5])
            )
            tiers_hit.append("2b")
            if has_debt_signal:
                boost = 2.0 + 0.5 * min(len(high_debt_files), 6)
                if hotspot_hits:
                    boost += 2.0
                scores["debt_compensation"] += boost
            # No soft hint without debt signal — file churn alone ≠ debt_compensation.

        title_l = title.lower()

        # Refactoring label without *strong* debt signal → prefer refactor
        if any(lab.lower() == "refactoring" for lab in labels) and not has_debt_signal:
            scores["refactor"] += 8.0
            scores["debt_compensation"] = max(0.0, scores["debt_compensation"] - 5.0)
            evidence.append("override:refactoring_label_no_debt_signal")
            tiers_hit.append("1")

        # Typo/comment cleanups beat debt noise even when body mentions "optimiz"
        if any(
            s in title_l
            for s in ("typo", "fix typo", "spelling", "written as proper noun")
        ) or (
            any(s in title_l for s in (" comment", "comments"))
            and any(lab.lower() in {"docs", "documentation"} for lab in labels)
        ):
            scores["documentation"] += 22.0
            scores["debt_compensation"] = max(0.0, scores["debt_compensation"] - 10.0)
            evidence.append("override:comment_typo->documentation")
            tiers_hit.append("2a")

        # Benchmarks are test infrastructure, not debt_compensation
        if any(s in title_l for s in ("benchmark", "bench:", "add bench")):
            scores["test_ci_build"] += 18.0
            scores["debt_compensation"] = max(0.0, scores["debt_compensation"] - 8.0)
            evidence.append("override:benchmark->test_ci_build")
            tiers_hit.append("2a")

        # Test flakiness / race-in-tests is test_ci, not architectural debt.
        # Keep narrow — matching any touched *_tests file over-fires (round-2).
        if any(lab.lower() == "tests" for lab in labels) and any(
            s in title_l for s in ("intermittent", "flaky", "race", "scheduler_tests")
        ):
            scores["test_ci_build"] += 14.0
            scores["debt_compensation"] = max(0.0, scores["debt_compensation"] - 10.0)
            evidence.append("override:test_flakiness_not_debt")
            tiers_hit.append("2a")

        # Build parallelization ≠ architectural debt (e.g. "guix: parallelize LIEF")
        if any(s in title_l for s in ("guix:", "depends:", "makefile", "build:", "ci:")) and (
            "parallel" in title_l or "paralleliz" in title_l
        ):
            scores["test_ci_build"] += 16.0
            scores["debt_compensation"] = max(0.0, scores["debt_compensation"] - 12.0)
            evidence.append("override:build_parallel_not_debt")
            tiers_hit.append("2a")

        # makefile / mingw / msbuild titles are build system
        if any(s in title_l for s in ("makefile", "mingw", "msvc", "autotools", "cmake:")):
            scores["test_ci_build"] += 14.0
            scores["debt_compensation"] = max(0.0, scores["debt_compensation"] - 8.0)
            evidence.append("override:makefile_build->test_ci_build")
            tiers_hit.append("2a")

        # Docs-labeled documentation of deadlocks/etc. is documentation, not debt
        if any(lab.lower() in {"docs", "documentation"} for lab in labels) and (
            title_l.startswith(("doc:", "docs:", "document "))
            or "document " in title_l[:40]
        ):
            scores["documentation"] += 20.0
            scores["debt_compensation"] = max(0.0, scores["debt_compensation"] - 12.0)
            evidence.append("override:docs_document->documentation")
            tiers_hit.append("2a")

        # Tests-labeled "fix … test" is test_ci even if lockorder/race keywords fire
        if any(lab.lower() == "tests" for lab in labels) and (
            "test" in title_l or title_l.startswith(("qa:", "fuzz:", "bench:"))
        ):
            scores["test_ci_build"] += 16.0
            scores["debt_compensation"] = max(0.0, scores["debt_compensation"] - 12.0)
            evidence.append("override:tests_label_title->test_ci_build")
            tiers_hit.append("2a")

        # UI / autoprune / eBPF / getheaders-style networking should not be debt
        if any(s in title_l for s in ("(ui)", "ui:", "gui:")) and not label_debt_boost:
            scores["other"] += 14.0
            scores["debt_compensation"] = max(0.0, scores["debt_compensation"] - 8.0)
            evidence.append("override:ui->other")
            tiers_hit.append("2a")
        if "ebpf" in title_l or "tracepoint" in title_l:
            scores["other"] += 14.0
            scores["debt_compensation"] = max(0.0, scores["debt_compensation"] - 8.0)
            evidence.append("override:tracepoint->other")
            tiers_hit.append("2a")
        if "autoprune" in title_l or title_l.startswith("add ") and "prune" in title_l:
            if not label_debt_boost and not strong_debt_matched:
                scores["other"] += 12.0
                scores["debt_compensation"] = max(0.0, scores["debt_compensation"] - 8.0)
                evidence.append("override:autoprune_feature->other")
                tiers_hit.append("2a")

        # Decisive overrides for clear dependency/subtree updates (Tier 3 lesson:
        # mega file lists were routing these to "other" / test_ci_build).
        dep_title = any(
            s in title_l
            for s in (
                "subtree",
                "libsecp",
                "secp256k1",
                "leveldb",
                "univalue",
                "libmultiprocess",
                "zeromq",
                "depends:",
                "update lib",
                "bump leveldb",
                "bump secp",
            )
        )
        if dep_title and (
            scores["dependency_maintenance"] >= 3
            or any("secp256k1/" in f or "leveldb/" in f or "univalue/" in f or "depends/" in f for f in files)
        ):
            scores["dependency_maintenance"] += 40.0
            evidence.append("override:dependency_title")
            tiers_hit.append("2a")

        # Title-prefix overrides (Tier 3 lesson: many ambiguous PRs already
        # declare intent in conventional Core title prefixes).
        prefix_map = (
            ("doc:", "documentation", 25.0),
            ("docs:", "documentation", 25.0),
            ("test:", "test_ci_build", 20.0),
            ("tests:", "test_ci_build", 20.0),
            ("ci:", "test_ci_build", 20.0),
            ("fuzz:", "test_ci_build", 20.0),
            ("qa:", "test_ci_build", 20.0),
            ("bench:", "test_ci_build", 15.0),
            ("build:", "test_ci_build", 18.0),
            ("policy:", "other", 20.0),
            ("mempool:", "other", 18.0),
            ("rpc:", "rpc_change", 20.0),
            ("rest:", "rpc_change", 18.0),
            ("net:", "networking_change", 20.0),
            ("p2p:", "networking_change", 20.0),
            ("wallet:", "other", 20.0),
            ("gui:", "other", 20.0),
            ("qt:", "other", 20.0),
            ("util:", "other", 12.0),  # weak; debt keywords may still win
            ("scripted-diff:", "refactor", 22.0),
            ("refactor:", "refactor", 18.0),
        )
        for prefix, cat, boost in prefix_map:
            if title_l.startswith(prefix) or f" {prefix}" in title_l[:40]:
                # Copyright scripted-diffs are documentation, not refactor
                if prefix == "scripted-diff:" and "copyright" in title_l:
                    scores["documentation"] += 25.0
                    evidence.append("override:title_prefix:scripted-diff:copyright->documentation")
                    tiers_hit.append("2a")
                    break
                # refactor: title wins unless *strong* debt signal (not enrich_perf /
                # bare cs_main mention). Round-2: "refactor: add kernel/cs_main.h"
                # was wrongly skipped into debt_compensation.
                if cat == "refactor" and has_debt_signal and label_debt_boost:
                    evidence.append(f"override_skip:{prefix}strong_debt_signal")
                    break
                if cat == "refactor" and has_debt_signal and strong_debt_matched:
                    # Still apply a reduced refactor boost; strong debt may win
                    scores["refactor"] += 8.0
                    evidence.append(f"override:title_prefix:{prefix}->refactor_reduced")
                    tiers_hit.append("2a")
                    break
                # util: + soft debt → debt, not other — unless title is a refactor
                if prefix == "util:" and debt_signal_soft and "refactor" not in title_l:
                    scores["debt_compensation"] += 18.0
                    evidence.append("override:title_prefix:util:+debt_signal->debt_compensation")
                    tiers_hit.append("2a")
                    break
                if prefix == "util:" and "refactor" in title_l:
                    scores["refactor"] += 18.0
                    evidence.append("override:title_prefix:util:refactor->refactor")
                    tiers_hit.append("2a")
                    break
                scores[cat] += boost
                evidence.append(f"override:title_prefix:{prefix}->{cat}")
                tiers_hit.append("2a")
                break

        # Broaden copyright → documentation (Tier 3 lesson: "update copyright year")
        if "copyright" in title_l:
            scores["documentation"] += 25.0
            evidence.append("override:copyright->documentation")
            tiers_hit.append("2a")

        # CI speedups must not become debt_compensation via "speed up"/"faster"
        ci_tooling = any(
            s in title_l
            for s in (
                "appveyor",
                "travis",
                "cirrus",
                "clcache",
                "ccache",
                "github actions",
                "ci: ",
                "speed up build",
                "faster build",
                "faster compile",
            )
        )
        if ci_tooling:
            scores["test_ci_build"] += 22.0
            scores["debt_compensation"] = max(0.0, scores["debt_compensation"] - 6.0)
            evidence.append("override:ci_tooling->test_ci_build")
            tiers_hit.append("2a")

        if "backport" in title_l and not title_l.startswith(("rpc:", "net:", "p2p:", "doc:")):
            scores["other"] += 15.0
            evidence.append("override:backport->other")
            tiers_hit.append("2a")

        primary, secondary, confidence, ambiguous = self._resolve(scores, evidence)

        # Prefer dependency_maintenance over other when override fired and scores close
        if "override:dependency_title" in evidence and primary == "other":
            if scores["dependency_maintenance"] >= scores.get("other", 0) * 0.5:
                primary = "dependency_maintenance"
                ambiguous = False
                confidence = "high"
                evidence.append("override:force_dependency")

        # Strong title-prefix wins: clear ambiguity when boost was decisive
        if any(e.startswith("override:title_prefix:") for e in evidence):
            for e in evidence:
                if e.startswith("override:title_prefix:"):
                    forced = e.split("->")[-1]
                    if scores.get(forced, 0) >= max(scores.values()) - 0.01:
                        primary = forced
                        # Keep ambiguous only if a close rival still within 75%
                        rivals = sorted(
                            ((c, s) for c, s in scores.items() if c != forced),
                            key=lambda x: -x[1],
                        )
                        if rivals and rivals[0][1] >= scores[forced] * 0.75 and rivals[0][0] != "other":
                            ambiguous = True
                            confidence = "medium"
                        else:
                            ambiguous = False
                            confidence = "high"
                    break

        tier_used = "+".join(sorted(set(tiers_hit))) if tiers_hit else "fallback"
        if not tiers_hit or (primary == "other" and max(scores.values()) < 1):
            primary = "other"
            confidence = "low"
            ambiguous = True
            evidence.append("fallback:other")

        return ClassificationResult(
            number=number,
            primary=primary,
            secondary=secondary,
            confidence=confidence,
            tier_used=tier_used,
            evidence=evidence[:20],
            scores={k: round(v, 2) for k, v in scores.items() if v > 0},
            ambiguous=ambiguous,
            title=title,
            merged_at=pr.get("merged_at"),
            labels=labels,
            files_sample=files[:12],
        )

    def _path_category(self, filename: str) -> Optional[str]:
        for prefix, cat in self.path_map:
            if filename.startswith(prefix) or filename == prefix:
                return cat
        return None

    def _resolve(
        self, scores: Dict[str, float], evidence: List[str]
    ) -> Tuple[str, List[str], str, bool]:
        ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
        best_cat, best_score = ranked[0]
        second_cat, second_score = ranked[1]

        if best_score <= 0:
            return "other", [], "low", True

        secondary = [c for c, s in ranked[1:] if s >= max(2.0, best_score * 0.45) and c != best_cat]
        secondary = secondary[:3]

        # Ambiguous if top two are close and both meaningful
        ambiguous = False
        if second_score > 0 and best_score > 0:
            # Accompanying tests/docs are common on domain PRs — require near-tie
            soft_seconds = {"test_ci_build", "documentation"}
            threshold = 0.9 if second_cat in soft_seconds else 0.75
            if second_score >= best_score * threshold and second_cat != "other":
                ambiguous = True
        if best_score < 3.0:
            ambiguous = True
            conf = "low"
        elif best_score < 6.0 or ambiguous:
            conf = "medium"
        else:
            conf = "high"

        # Pure docs/tests with strong score are not ambiguous
        if best_cat in {"documentation", "test_ci_build"} and best_score >= 4 and second_score < best_score * 0.5:
            ambiguous = False
            conf = "high" if best_score >= 6 else "medium"

        # Domain primary with only soft seconds and medium+ score → accept
        if (
            best_cat not in {"other", "test_ci_build", "documentation"}
            and best_score >= 5.0
            and second_cat in {"test_ci_build", "documentation", "other"}
        ):
            ambiguous = False
            conf = "high" if best_score >= 6 else "medium"

        return best_cat, secondary, conf, ambiguous


def aggregate_results(results: Sequence[ClassificationResult]) -> Dict[str, Any]:
    from collections import Counter

    primary = Counter(r.primary for r in results)
    total = len(results) or 1
    ambiguous = sum(1 for r in results if r.ambiguous)
    by_conf = Counter(r.confidence for r in results)

    def pct(n: int) -> float:
        return round(100.0 * n / total, 2)

    debt_tax = sum(primary[c] for c in ARCHITECTURAL_DEBT_TAX)
    maintenance = sum(primary[c] for c in TOTAL_MAINTENANCE)
    structural = sum(primary[c] for c in STRUCTURAL)
    net_new = sum(primary[c] for c in NET_NEW)

    return {
        "total_classified": len(results),
        "ambiguous_count": ambiguous,
        "ambiguous_pct": pct(ambiguous),
        "confidence": dict(by_conf),
        "primary_counts": dict(primary),
        "primary_pct": {k: pct(v) for k, v in primary.items()},
        "headline_metrics": {
            "architectural_debt_tax_pct": pct(debt_tax),
            "total_maintenance_burden_pct": pct(maintenance),
            "structural_work_pct": pct(structural),
            "net_new_capability_pct": pct(net_new),
            "other_pct": pct(primary.get("other", 0)),
        },
    }
