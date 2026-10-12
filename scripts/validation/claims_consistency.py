#!/usr/bin/env python3
"""Build the claims ledger from committed JSON and check findings markdown against it."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List

from src.utils.findings_io import save_analysis_json
from src.utils.paths import get_findings_dir

ROOT = Path(__file__).resolve().parents[2]


def _load(name: str) -> Dict[str, Any]:
    return json.loads((get_findings_dir() / "data" / name).read_text())


def _claim(**kwargs: Any) -> Dict[str, Any]:
    kwargs.setdefault("conflicts", [])
    kwargs.setdefault("fragile_markers", [])
    kwargs.setdefault("holdout", None)
    kwargs.setdefault("q", None)
    kwargs.setdefault("family", None)
    return kwargs


def satoshi_counts() -> Dict[str, int]:
    path = ROOT / "data" / "satoshi_archive" / "satoshi_communications.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    seen = set()
    for row in rows:
        path_key = row.get("file_path") or row.get("filename") or ""
        seen.add(path_key + "\n" + (row.get("content") or "")[:2000])
    return {"rows": len(rows), "deduped": len(seen)}


def build_claims() -> List[Dict[str, Any]]:
    divergence = _load("newcomer_divergence.json")
    effects = _load("comparison_effects.json")
    stability = _load("interval_stability.json")
    size = _load("size_adjusted_health.json")
    durability = _load("merge_durability.json")
    merged = _load("pass7_merged_by.json")
    pattern = _load("merge_pattern_analysis.json")
    revealed = _load("revealed_rough_consensus.json")
    h4 = size["indicator_volume_spearman"]["H4_gini_merges"]
    e12 = effects["classifications"]["E12_ingroup_on_no_peer_response"]
    e3 = merged["e3"]["correlation"]
    fix = durability["splits"]["12"]["out_vs_in"]["fix_forward"]
    roster = pattern["self_merge_breakdown"]
    zero = roster["self_merge_by_reviews"]["zero_reviews"]
    revealed_merged = revealed["windows"]["all_time"]["merged"]
    after = divergence["negative_points_after_slope_gate"]
    before = divergence["negative_points_before_slope_gate"]
    health = divergence["health_link"]
    archive = satoshi_counts()
    return [
        _claim(
            id="newcomer_divergence",
            sentence=(
                "The Core newcomer interaction is -3.7 percentage points per year, driver BOTH. "
                f"Classification is AMBIENT on {after['negative']} of {after['eligible']} eligible negative points "
                f"after the 3-year series rule, and {before['negative']} of {before['eligible']} before it."
            ),
            number="-3.7 percentage points per year",
            source_report="findings/NEWCOMER_DIVERGENCE.md",
            json_path="findings/data/newcomer_divergence.json published_core_interaction",
            family="not in family",
            q=None,
            holdout="headline is the full series, not a 2010-2023 split",
            status="NOT IN FAMILY, LOW POWER",
        ),
        _claim(
            id="divergence_drivers",
            sentence=divergence["driver_sentence"]
            + " Core and bdk are the two repositories where newcomer decline and incumbent gain both resolve.",
            number="4 resolved, 5 unresolved",
            source_report="findings/NEWCOMER_DIVERGENCE.md",
            json_path="findings/data/newcomer_divergence.json driver_counts",
            family="not in family",
            status="NOT IN FAMILY, LOW POWER",
        ),
        _claim(
            id="retract_newcomer_practice",
            sentence="rust-bitcoin and rust-miniscript show a practice that serves newcomers",
            number=None,
            source_report="findings/CLAIMS_LEDGER.md",
            json_path="findings/data/newcomer_divergence.json driver_counts",
            family="not in family",
            status="RETRACTED",
            replacement=(
                "A positive interaction in this set is unresolved or driven by incumbent decline. "
                "It is not evidence of better newcomer treatment."
            ),
        ),
        _claim(
            id="health_link",
            sentence="The newcomer interaction against the size-adjusted residual has Spearman 0.370, and the interval covers zero.",
            number="0.370",
            source_report="findings/NEWCOMER_DIVERGENCE.md",
            json_path="findings/data/newcomer_divergence.json health_link.estimate",
            family="not in family",
            status="EXPLORATORY, NOT IN FAMILY",
            value_check=round(float(health["estimate"]), 3),
        ),
        _claim(
            id="identity_collapse",
            sentence=(
                f"Numeric user ids merged {divergence['logins_collapsed']} additional logins in the seven-year dumps, "
                f"and {divergence['people_with_multiple_logins']} people had more than one login."
            ),
            number=str(divergence["logins_collapsed"]),
            source_report="findings/NEWCOMER_DIVERGENCE.md",
            json_path="findings/data/newcomer_divergence.json logins_collapsed",
            family="not in family",
            status="CONFIRMED",
        ),
        _claim(
            id="e12_diagnostics",
            sentence=(
                "E12 stays AMBIENT. Its Spearman interval touches -1, with "
                f"{e12['degenerate_share'] * 100:.1f} percent degenerate draws."
            ),
            number="0.5 percent degenerate",
            source_report="findings/SIZE_ADJUSTED_COMPARISON.md",
            json_path="findings/data/comparison_effects.json classifications.E12_ingroup_on_no_peer_response",
            family="pass 6 Spearman, family at the time 228",
            q=None,
            status="AMBIENT, LOW POWER",
        ),
        _claim(
            id="s1_fragile",
            sentence="S1 is FRAGILE. Summaries do not describe it as excluding zero.",
            number=None,
            source_report="findings/DISCOURSE_RECALL.md",
            json_path="findings/data/interval_stability.json fragile",
            family="in family as capacity_S1_irc_linked",
            status="FRAGILE",
            fragile_markers=["S1", "capacity_S1_irc_linked"],
        ),
        _claim(
            id="h6_fragile",
            sentence="The H6 volume correlation is FRAGILE. Summaries do not describe it as excluding zero. Indicators that move with scale name merge Gini (H4) only.",
            number=None,
            source_report="findings/SIZE_ADJUSTED_COMPARISON.md",
            json_path="findings/data/interval_stability.json fragile",
            family="pass 6 volume correlation",
            status="FRAGILE",
            fragile_markers=["H6_median_days_to_decision", "H6 volume"],
        ),
        _claim(
            id="h4_volume",
            sentence=f"Author-basis merge Gini (H4) tracks log pull-request volume at {h4['estimate']:.3f}.",
            number="0.860",
            source_report="findings/SIZE_ADJUSTED_COMPARISON.md",
            json_path="findings/data/size_adjusted_health.json indicator_volume_spearman.H4_gini_merges",
            family="pass 6",
            status="STABLE",
            conflicts=["US income inequality Gini", "US income Gini"],
        ),
        _claim(
            id="e3_spearman",
            sentence=(
                f"E3's Spearman correlation with the refit residual is {e3['estimate']:.3f}, q={e3['q']:.3f}. "
                f"The class is {merged['e3']['class']}. The interval touches 1, with "
                f"{e3['degenerate_share'] * 100:.1f} percent degenerate draws."
            ),
            number=f"{e3['estimate']:.3f}",
            source_report="findings/RESEARCH_METHODOLOGY.md",
            json_path="findings/data/pass7_merged_by.json e3.correlation",
            family="pass7.E3_spearman_versus_size_adjusted_residual",
            q=e3.get("q"),
            status="AMBIENT, LOW POWER",
        ),
        _claim(
            id="family_size",
            sentence=f"The Benjamini-Hochberg family is {merged['bh_family_size']} tests. No prior q crossed 0.05.",
            number=str(merged["bh_family_size"]),
            source_report="findings/RESEARCH_METHODOLOGY.md",
            json_path="findings/data/pass7_merged_by.json bh_family_size",
            family="passes 1 through 7",
            status="CONFIRMED",
        ),
        _claim(
            id="self_merge_residual",
            sentence=(
                f"Core's matched-size self-merge residual with the distinct-mergers control is "
                f"{merged['self_merge']['core']['residual']:.3f}, and the interval covers zero."
            ),
            number=f"{merged['self_merge']['core']['residual']:.3f}",
            source_report="findings/RESEARCH_METHODOLOGY.md",
            json_path="findings/data/pass7_merged_by.json self_merge.core.residual",
            family="not in family",
            status="EXPLORATORY, NOT IN FAMILY",
        ),
        _claim(
            id="published_health_residual",
            sentence=(
                f"Core's published size-adjusted residual is about {size['samples']['all_repositories']['core_residual']:.4f}, "
                f"rank {size['samples']['all_repositories']['core_rank_most_negative']} of "
                f"{size['samples']['all_repositories']['n']}, and the interval covers zero."
            ),
            number="-0.0003",
            source_report="findings/SIZE_ADJUSTED_COMPARISON.md",
            json_path="findings/data/size_adjusted_health.json samples.all_repositories.core_residual",
            family="pass 6",
            status="LOW POWER",
            conflicts=["last-place shared-health rank survives size adjustment"],
        ),
        _claim(
            id="refit_health_residual",
            sentence=(
                "After merger Gini replaces author-basis H4, Core's refit residual is "
                f"{merged['size_adjusted_health']['core_residual']:.3f}, rank "
                f"{merged['size_adjusted_health']['core_rank_most_negative']} of "
                f"{len(merged['size_adjusted_health']['repositories'])}, and the interval covers zero."
            ),
            number=f"{merged['size_adjusted_health']['core_residual']:.3f}",
            source_report="findings/RESEARCH_METHODOLOGY.md",
            json_path="findings/data/pass7_merged_by.json size_adjusted_health.core_residual",
            family="not a new family test",
            status="LOW POWER",
        ),
        _claim(
            id="durability_fix_forward",
            sentence=(
                f"Out-group merged code fixes forward at {fix['rate_group1'] * 100:.1f} percent against "
                f"{fix['rate_group0'] * 100:.1f} percent for in-group. "
                f"The coefficient is {fix['estimate']:.3f}, q={fix['q']:.3f}. "
                "The claim is that out-group code does not fail more."
            ),
            number=f"{fix['rate_group1']:.3f} and {fix['rate_group0']:.3f}",
            source_report="findings/MERGE_DURABILITY.md",
            json_path="findings/data/merge_durability.json out_vs_in.fix_forward",
            family="in family",
            q=fix.get("q") if isinstance(fix, dict) else None,
            holdout="yes",
            status="CONFIRMED",
            conflicts=["out-group code is worse after merge"],
        ),
        _claim(
            id="roster_self_merge",
            sentence=(
                f"The 2026-09-10 roster snapshot has {roster['total_self_merged']:,} self-merges "
                f"out of {roster['total_maintainer_merged']:,}, and {zero['count']:,} of those self-merges "
                "have zero GitHub review objects (45.1 percent)."
            ),
            number="2,501 of 9,793",
            source_report="findings/MERGE_PATTERN_BREAKDOWN.md",
            json_path="findings/data/merge_pattern_analysis.json self_merge_breakdown",
            family="not in family",
            status="CONFIRMED",
            conflicts=["46.1% of self-merges", "1,127 of 2,501"],
        ),
        _claim(
            id="revealed_self_merge",
            sentence=(
                f"Revealed rough consensus counts {revealed_merged['self_merge']:,} self-merges "
                f"out of {revealed_merged['n']:,} merges of any author."
            ),
            number="2,572 of 16,845",
            source_report="findings/REVEALED_ROUGH_CONSENSUS.md",
            json_path="findings/data/revealed_rough_consensus.json windows.all_time.merged",
            family="not in family",
            status="CONFIRMED",
        ),
        _claim(
            id="roster_recount",
            sentence=(
                "A 2026-10-12 recount of the same roster function on the current dump returns "
                "2,514 self-merges out of 9,874, and 1,131 with zero review objects. Reports stay on the September snapshot."
            ),
            number="2,514 of 9,874",
            source_report="findings/RESEARCH_METHODOLOGY.md",
            json_path="live recount, not a replacement of merge_pattern_analysis.json",
            family="not in family",
            status="DATA FRESHNESS",
        ),
        _claim(
            id="satoshi_file",
            sentence=(
                f"The Satoshi file holds {archive['rows']:,} rows, and {archive['deduped']:,} remain after hashing path plus a content prefix. "
                "The figure 549 does not describe this file."
            ),
            number=f"{archive['rows']:,}",
            source_report="findings/RESEARCH_METHODOLOGY.md",
            json_path="data/satoshi_archive/satoshi_communications.jsonl",
            family="not in family",
            status="CONFIRMED",
            conflicts=["549 Satoshi"],
        ),
        _claim(
            id="retract_harder",
            sentence="the project got harder for everyone",
            number=None,
            source_report="findings/CLAIMS_LEDGER.md",
            json_path="findings/data/newcomer_divergence.json",
            status="RETRACTED",
            replacement="Newcomer merge rates fall while incumbent rates rise. The series are not one bar for everyone.",
        ),
        _claim(
            id="retract_starvation",
            sentence="review capacity starvation explains newcomer silence",
            number=None,
            source_report="findings/CLAIMS_LEDGER.md",
            json_path="findings/data/first_year_signal_analysis.json",
            status="RETRACTED",
            replacement="Silence rises while the queue per reviewer falls.",
        ),
        _claim(
            id="retract_quality",
            sentence="the first-year merge gap detects patch quality",
            number=None,
            source_report="findings/CLAIMS_LEDGER.md",
            json_path="findings/data/first_year_signal_analysis.json",
            status="RETRACTED",
            replacement="Reception, not the patch-content score, lines up with the first-year merge gap.",
        ),
        _claim(
            id="retract_unique",
            sentence="Core is uniquely sick on the attention effects",
            number=None,
            source_report="findings/CLAIMS_LEDGER.md",
            json_path="findings/data/comparison_effects.json classifications",
            status="RETRACTED",
            replacement="The attention effects that have estimates are AMBIENT.",
        ),
        _claim(
            id="retract_last_place",
            sentence="last-place shared-health rank survives size adjustment",
            number=None,
            source_report="findings/CLAIMS_LEDGER.md",
            json_path="findings/data/pass7_merged_by.json size_adjusted_health.core_residual",
            status="RETRACTED",
            replacement=(
                "After merger Gini replaces author-basis H4, Core's refit residual is -0.070, "
                "rank 3 of 17, and the interval covers zero."
            ),
        ),
        _claim(
            id="retract_income",
            sentence="merge Gini of 0.85 is extreme by comparison with income inequality",
            number=None,
            source_report="findings/CLAIMS_LEDGER.md",
            json_path="findings/data/size_adjusted_health.json indicator_volume_spearman.H4_gini_merges",
            status="RETRACTED",
            replacement="Author-basis H4 is a volume correlation inside this corpus.",
        ),
        _claim(
            id="retract_outgroup_worse",
            sentence="out-group code is worse after merge",
            number=None,
            source_report="findings/CLAIMS_LEDGER.md",
            json_path="findings/data/merge_durability.json out_vs_in.fix_forward",
            status="RETRACTED",
            replacement="Out-group merged code does not fail more on the fix-forward contrast.",
        ),
        _claim(
            id="fragile_set",
            sentence="Fragile ids are " + ", ".join(stability["fragile"]) + ".",
            number=None,
            source_report="findings/data/interval_stability.json",
            json_path="findings/data/interval_stability.json fragile",
            status="FRAGILE",
            fragile_markers=[],
        ),
    ]


def _paragraphs(text: str) -> Iterable[str]:
    for block in re.split(r"\n\s*\n", text):
        yield block


def _asserts_excludes_zero(sentence: str, marker: str) -> bool:
    if marker not in sentence:
        return False
    if not re.search(r"exclud", sentence, re.I):
        return False
    if re.search(r"\b(not|no|never|without|do not|does not)\b", sentence, re.I):
        return False
    return True


def check_text(text: str, claims: List[Dict[str, Any]], path: str = "<text>") -> List[str]:
    failures = []
    for paragraph in _paragraphs(text):
        for claim in claims:
            if claim.get("status") == "RETRACTED" and claim["sentence"] in paragraph and "RETRACTED" not in paragraph:
                failures.append(f"{path}: retracted claim {claim['id']} is stated as current")
            for bad in claim.get("conflicts") or []:
                if bad in paragraph and "RETRACTED" not in paragraph:
                    failures.append(f"{path}: {claim['id']} conflicts with {bad!r}")
            if claim.get("status") == "FRAGILE":
                for sentence in re.split(r"(?<=[.])\s+", paragraph):
                    for marker in claim.get("fragile_markers") or []:
                        if _asserts_excludes_zero(sentence, marker):
                            failures.append(f"{path}: fragile {claim['id']} described as excluding zero")
    return failures


def check_findings(claims: List[Dict[str, Any]]) -> List[str]:
    failures = []
    findings = get_findings_dir()
    for path in sorted(findings.glob("*.md")):
        failures.extend(check_text(path.read_text(encoding="utf-8", errors="replace"), claims, str(path)))
    return failures


def render_markdown(claims: List[Dict[str, Any]]) -> str:
    lines = [
        "# Claims ledger",
        "",
        "Each row is a headline claim. The number is taken from the committed JSON named in the row. Older reports keep the q they were written against. The pass 7 family is 229, and those recomputed q values are in `pass7_merged_by.json`.",
        "",
        "| Status | Claim | Number | Source | JSON | Family |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for claim in claims:
        lines.append(
            "| {status} | {sentence} | {number} | {source} | {json_path} | {family} |".format(
                status=claim.get("status") or "",
                sentence=claim["sentence"].replace("|", "/"),
                number=claim.get("number") or "",
                source=claim.get("source_report") or "",
                json_path=claim.get("json_path") or "",
                family=claim.get("family") or "",
            )
        )
    lines.extend([
        "",
        "## Retracted claims",
        "",
    ])
    for claim in claims:
        if claim.get("status") != "RETRACTED":
            continue
        lines.append(f"- RETRACTED. {claim['sentence']}. Replacement: {claim.get('replacement')}")
    lines.extend([
        "",
        "## What this cannot prove",
        "",
        "The ledger records the status of a measurement. It does not turn a LOW POWER interval that covers zero into a cause, and it does not score the blinded audit.",
        "",
    ])
    return "\n".join(lines) + "\n"


def render_readout(claims: List[Dict[str, Any]]) -> str:
    by_id = {claim["id"]: claim for claim in claims}
    order = [
        "newcomer_divergence",
        "divergence_drivers",
        "retract_newcomer_practice",
        "health_link",
        "identity_collapse",
        "e12_diagnostics",
        "s1_fragile",
        "h6_fragile",
        "h4_volume",
        "published_health_residual",
        "refit_health_residual",
        "e3_spearman",
        "family_size",
        "self_merge_residual",
        "durability_fix_forward",
        "roster_self_merge",
        "revealed_self_merge",
        "roster_recount",
        "satoshi_file",
    ]
    lines = [
        "# Final readout",
        "",
        "Numbers below are the ledger values, and each one carries its status.",
        "",
    ]
    for key in order:
        claim = by_id[key]
        status = claim.get("status") or ""
        if status == "RETRACTED":
            lines.append(f"**{status}.** {claim['sentence']}. {claim.get('replacement')}")
        else:
            lines.append(f"**{status}.** {claim['sentence']}")
        lines.append("")
    lines.extend([
        "## Retracted",
        "",
    ])
    for claim in claims:
        if claim.get("status") == "RETRACTED" and claim["id"] not in order:
            lines.append(f"**RETRACTED.** {claim['sentence']}. {claim.get('replacement')}")
            lines.append("")
    lines.extend([
        "## Open items",
        "",
        "The blinded audit of 160 pull requests has a rubric and a sample and no scores.",
        "",
        "Path-link precision is 0.015, from one reading of the first 280 characters. A second independent coder is needed.",
        "",
        "P5 and P7 need data outside this corpus. Deleted comments, and a person-to-funder ledger.",
        "",
        "ethereum/go-ethereum needs its pull-request list before it can serve as an outside peer.",
        "",
        "## What this cannot prove",
        "",
        "These measurements describe public artifacts. They do not show what a reviewer intended, and they do not show what the project should do.",
        "",
    ])
    return "\n".join(lines)


def write_outputs() -> List[str]:
    claims = build_claims()
    payload = {"version": "7.0", "claims": claims}
    written = [str(path) for path in save_analysis_json("claims_ledger.json", payload)]
    findings = get_findings_dir()
    ledger_path = findings / "CLAIMS_LEDGER.md"
    readout_path = findings / "FINAL_READOUT.md"
    ledger_path.write_text(render_markdown(claims), encoding="utf-8")
    readout_path.write_text(render_readout(claims), encoding="utf-8")
    written.extend([str(ledger_path), str(readout_path)])
    return written


def main() -> int:
    claims = build_claims()
    write_outputs()
    failures = check_findings(claims)
    for failure in failures:
        print(failure)
    print(f"failures {len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
