#!/usr/bin/env python3
"""
Stalled proposal dossiers — timelines for named governance-critique proposals.

Builds case files for Dandelion, Erlay, AssumeUTXO, wallet/node separation,
package relay, private broadcast, etc. from enriched PRs + issues.

Matching rules are proposal-specific to avoid false positives (e.g. Erlay
vs "overlay") and to separate scaffolding merges from full-implementation stalls.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger  # noqa: E402
from src.utils.paths import get_data_dir, get_findings_dir  # noqa: E402

logger = setup_logger()

# Role labels for Erlay PRs — used in dossier narrative, not as merge excuses.
ERLAY_SCAFFOLDING_RE = re.compile(
    r"(signaling|sendtxrcncl|fuzz|refactor.*erlay|preparation for erlay)",
    re.I,
)
ERLAY_FULL_IMPL_RE = re.compile(
    r"(bandwidth-efficient transaction relay|fill reconciliation|implementation of\s*\[?erlay|"
    r"^erlay:|erlay:\s*bandwidth)",
    re.I,
)


PROPOSALS = [
    {
        "id": "dandelion",
        "title": "Dandelion / BIP156 transaction origin privacy",
        "match_mode": "substring",
        "title_any": ["dandelion", "bip 156", "bip156"],
        "issue_numbers": [],
        "claim": "Research-complete since ~2017; Monero shipped Dandelion++; Core did not.",
    },
    {
        "id": "erlay",
        "title": "Erlay set-reconciliation relay",
        "match_mode": "erlay_word",
        "title_any": ["erlay"],
        "issue_numbers": [],
        "claim": "Technically uncontroversial bandwidth reduction; full protocol still unmerged after years.",
    },
    {
        "id": "utxo_commitments_vs_assumeutxo",
        "title": "UTXO commitments vs AssumeUTXO",
        "match_mode": "substring",
        "title_any": ["assumeutxo", "utxo commitment", "utxo commitments", "utreexo"],
        "issue_numbers": [],
        "claim": "Cryptographic UTXO commitment research vs hardcoded-hash AssumeUTXO that shipped.",
    },
    {
        "id": "wallet_node_separation",
        "title": "Wallet / node separation (issue 7525)",
        "match_mode": "substring",
        "title_any": ["disablewallet", "libbitcoinkernel", "multiprocess", "ipc"],
        "issue_numbers": [7525],
        "claim": "Universal agreement since 2016; -disablewallet / kernel franchise ≠ product split.",
    },
    {
        "id": "package_relay",
        "title": "Package relay / BIP331",
        "match_mode": "substring",
        "title_any": ["package relay", "bip331", "bip 331", "submitpackage", "1p1c"],
        "issue_numbers": [],
        "claim": "Long-running P2P policy/capability work with multi-year PR lifetimes.",
    },
    {
        "id": "private_broadcast",
        "title": "Private broadcast (partial Dandelion substitute)",
        "match_mode": "substring",
        "title_any": ["private broadcast"],
        "issue_numbers": [],
        "claim": "Narrower threat model than Dandelion; landed years later.",
    },
]


def _norm(s: Optional[str]) -> str:
    return (s or "").lower()


def _matches_substring(text: str, needles: List[str]) -> bool:
    return any(n in text for n in needles)


def _matches_erlay(title: str, body: str) -> bool:
    """Word-boundary Erlay; exclude 'overlay' / 'interlay' style false positives."""
    blob = f"{title} {body}"
    if not re.search(r"(?<![a-z])erlay(?![a-z])", blob, re.I):
        return False
    # Guard: 'overlay' contains 'erlay' as substring without word boundary — already excluded.
    return True


def _erlay_role(title: str, body: str) -> str:
    t = f"{title}\n{body[:800]}"
    if ERLAY_FULL_IMPL_RE.search(t) or re.search(
        r"\berlay\b.*bandwidth-efficient|implementation of \[?erlay", t, re.I
    ):
        return "full_or_core_protocol"
    if ERLAY_SCAFFOLDING_RE.search(t):
        return "scaffolding_or_signaling"
    if re.search(r"fill reconciliation|reconciliation set", t, re.I):
        return "full_or_core_protocol"
    if re.search(r"\berlay\b", title, re.I):
        return "named_erlay_work"
    return "mention_only"


def _pr_summary(pr: Dict[str, Any], extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    tags = pr.get("maintainer_tags") or {}
    td = pr.get("time_to_decision") or {}
    rm = pr.get("review_metrics") or {}
    out = {
        "number": pr.get("number"),
        "title": pr.get("title"),
        "state": pr.get("state"),
        "merged": bool(pr.get("merged")),
        "author": pr.get("author"),
        "author_is_maintainer": bool(tags.get("author_is_maintainer")),
        "created_at": pr.get("created_at"),
        "closed_at": pr.get("closed_at"),
        "merged_at": pr.get("merged_at"),
        "days_to_decision": td.get("days_to_decision") or pr.get("time_to_merge_days"),
        "total_reviews": (rm.get("total_reviews") or 0),
        "nack_count": (rm.get("nack_count") or 0),
        "labels": pr.get("labels"),
    }
    if extra:
        out.update(extra)
    return out


def _issue_summary(issue: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "number": issue.get("number"),
        "title": issue.get("title"),
        "state": issue.get("state"),
        "created_at": issue.get("created_at"),
        "closed_at": issue.get("closed_at"),
        "author": issue.get("author"),
        "comments": len(issue.get("comments") or []),
    }


def _age_days(start: Optional[str], end: Optional[str] = None) -> Optional[float]:
    if not start:
        return None
    try:
        s = datetime.fromisoformat(start.replace("Z", "+00:00"))
        e = (
            datetime.fromisoformat(end.replace("Z", "+00:00"))
            if end
            else datetime.now(timezone.utc)
        )
        return (e - s).total_seconds() / 86400.0
    except Exception:
        return None


def _match_pr(pr: Dict[str, Any], spec: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    title = _norm(pr.get("title"))
    body = _norm(pr.get("body"))[:800]
    mode = spec.get("match_mode") or "substring"
    if mode == "erlay_word":
        ok = _matches_erlay(title, body)
        extra = {"erlay_role": _erlay_role(pr.get("title") or "", pr.get("body") or "")} if ok else {}
        return ok, extra
    blob = f"{title} {body[:500]}"
    return _matches_substring(blob, spec["title_any"]), {}


def build_dossiers() -> Dict[str, Any]:
    data_dir = get_data_dir()
    prs_path = data_dir / "processed" / "enriched_prs.jsonl"
    issues_path = data_dir / "processed" / "enriched_issues.jsonl"

    prs: List[Dict[str, Any]] = []
    with open(prs_path, encoding="utf-8") as f:
        for line in f:
            prs.append(json.loads(line))
    issues: List[Dict[str, Any]] = []
    if issues_path.exists():
        with open(issues_path, encoding="utf-8") as f:
            for line in f:
                issues.append(json.loads(line))

    dossiers = []
    for spec in PROPOSALS:
        matched_prs = []
        for pr in prs:
            ok, extra = _match_pr(pr, spec)
            if ok:
                matched_prs.append(_pr_summary(pr, extra or None))
        matched_prs.sort(key=lambda x: x.get("created_at") or "")

        matched_issues = []
        for issue in issues:
            if issue.get("number") in (spec.get("issue_numbers") or []):
                matched_issues.append(_issue_summary(issue))
                continue
            blob = f"{_norm(issue.get('title'))} {_norm(issue.get('body'))[:300]}"
            if spec.get("match_mode") == "erlay_word":
                if _matches_erlay(_norm(issue.get("title")), _norm(issue.get("body"))[:300]):
                    matched_issues.append(_issue_summary(issue))
            elif _matches_substring(blob, spec["title_any"]):
                matched_issues.append(_issue_summary(issue))

        lifetimes = [
            p["days_to_decision"]
            for p in matched_prs
            if p.get("days_to_decision") is not None
        ]
        open_prs = [p for p in matched_prs if p.get("state") == "open"]
        merged_prs = [p for p in matched_prs if p.get("merged")]
        closed_unmerged = [p for p in matched_prs if (not p.get("merged")) and p.get("state") == "closed"]

        first = matched_prs[0] if matched_prs else None
        last = matched_prs[-1] if matched_prs else None
        span = None
        if first and last:
            span = _age_days(
                first.get("created_at"),
                last.get("merged_at") or last.get("closed_at") or last.get("created_at"),
            )

        dossier: Dict[str, Any] = {
            "id": spec["id"],
            "title": spec["title"],
            "claim": spec["claim"],
            "match_mode": spec.get("match_mode"),
            "n_prs": len(matched_prs),
            "n_merged": len(merged_prs),
            "n_closed_unmerged": len(closed_unmerged),
            "n_open": len(open_prs),
            "n_issues": len(matched_issues),
            "median_days_to_decision": (
                float(sorted(lifetimes)[len(lifetimes) // 2]) if lifetimes else None
            ),
            "max_days_to_decision": float(max(lifetimes)) if lifetimes else None,
            "first_pr": first,
            "longest_lived_unmerged": max(
                closed_unmerged + open_prs,
                key=lambda p: p.get("days_to_decision") or _age_days(p.get("created_at")) or 0,
                default=None,
            ),
            "activity_span_days": span,
            "maintainer_authored_share": (
                sum(1 for p in matched_prs if p.get("author_is_maintainer")) / len(matched_prs)
                if matched_prs
                else None
            ),
            "issues": matched_issues[:10],
            "prs": matched_prs[:40],
        }

        if spec["id"] == "erlay":
            by_role: Dict[str, List[Dict[str, Any]]] = {}
            for p in matched_prs:
                role = p.get("erlay_role") or "unknown"
                by_role.setdefault(role, []).append(p)
            role_stats = {}
            for role, plist in by_role.items():
                role_stats[role] = {
                    "n": len(plist),
                    "n_merged": sum(1 for p in plist if p.get("merged")),
                    "n_closed_unmerged": sum(
                        1 for p in plist if (not p.get("merged")) and p.get("state") == "closed"
                    ),
                    "n_open": sum(1 for p in plist if p.get("state") == "open"),
                    "numbers": [p["number"] for p in plist],
                }
            dossier["erlay_by_role"] = role_stats
            full = by_role.get("full_or_core_protocol") or []
            dossier["erlay_full_protocol_outcome"] = {
                "n": len(full),
                "n_merged": sum(1 for p in full if p.get("merged")),
                "n_closed_unmerged": sum(
                    1 for p in full if (not p.get("merged")) and p.get("state") == "closed"
                ),
                "n_open": sum(1 for p in full if p.get("state") == "open"),
                "note": (
                    "Scaffolding/signaling merges are not full Erlay. "
                    "Full-protocol attempts have repeatedly closed unmerged or remain DO-NOT-MERGE."
                ),
            }

        dossiers.append(dossier)

    # Fair-cite set: cases where keyword noise is low enough for primary claims
    fair_cite = []
    for d in dossiers:
        if d["id"] == "dandelion" and d["n_prs"] == 1 and d["n_merged"] == 0:
            fair_cite.append(
                {
                    "id": "dandelion",
                    "claim_strength": "strong",
                    "statement": "Single Core implementation PR closed unmerged; no ship.",
                }
            )
        if d["id"] == "erlay":
            fo = d.get("erlay_full_protocol_outcome") or {}
            if fo.get("n_merged") == 0 and (fo.get("n") or 0) >= 3:
                fair_cite.append(
                    {
                        "id": "erlay",
                        "claim_strength": "strong",
                        "statement": (
                            "Full-protocol Erlay PRs: zero merges; scaffolding merges are not delivery."
                        ),
                    }
                )
        if d["id"] == "private_broadcast":
            fair_cite.append(
                {
                    "id": "private_broadcast",
                    "claim_strength": "contrast_only",
                    "statement": "Narrower threat model; not evidence Dandelion was unnecessary.",
                }
            )
        if d["id"] in ("utxo_commitments_vs_assumeutxo", "wallet_node_separation"):
            fair_cite.append(
                {
                    "id": d["id"],
                    "claim_strength": "lead_only",
                    "statement": "Keyword totals too noisy for acceptance/rejection claims.",
                }
            )
        if d["id"] == "package_relay":
            fair_cite.append(
                {
                    "id": "package_relay",
                    "claim_strength": "moderate",
                    "statement": "Multi-year PR lifetimes with mixed merge outcomes; cite max days + exemplars.",
                }
            )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "enriched_prs.jsonl + enriched_issues.jsonl",
        "version": "2.1",
        "matching_notes": {
            "erlay": "Word-boundary match; roles split scaffolding vs full protocol",
            "wallet_node_separation": "Broad keywords; over-counts — curate before citing totals",
        },
        "fair_cite_guidance": fair_cite,
        "proposals": dossiers,
    }


def main() -> int:
    logger.info("Building stalled proposal dossiers")
    payload = build_dossiers()
    out_dir = get_findings_dir() / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "stalled_proposal_dossiers.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    logger.info("Wrote %s", path)
    for d in payload["proposals"]:
        extra = ""
        if d["id"] == "erlay":
            fo = d.get("erlay_full_protocol_outcome") or {}
            extra = f" full_protocol_merged={fo.get('n_merged')}/{fo.get('n')}"
        print(
            f"{d['id']}: prs={d['n_prs']} merged={d['n_merged']} "
            f"closed_unmerged={d['n_closed_unmerged']} open={d['n_open']} "
            f"max_days={d['max_days_to_decision']} "
            f"longest={((d.get('longest_lived_unmerged') or {}).get('number'))}"
            f"{extra}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
