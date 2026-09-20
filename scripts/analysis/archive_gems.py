#!/usr/bin/env python3
"""Mine 17 years of archives for cited gems, then optionally ask an LLM.

The quantitative frames pick *where* to look. This script pulls short primary
quotes from those places. It does not dump IRC into a model.

  venv/bin/python scripts/analysis/archive_gems.py
  venv/bin/python scripts/analysis/archive_gems.py --llm   # needs OPENAI_BASE_URL
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.utils.findings_io import save_analysis_json
from src.utils.paths import get_analysis_dir, get_data_dir, get_findings_dir

SKIP_AUTHORS = {"drahtbot", "bitcoin-core-ai", "github-actions[bot]"}
SKIP_QUOTE = re.compile(
    r"the following sections might be updated|corecheck\.dev|show signature and timestamp",
    re.I,
)
UTACK_ONLY = re.compile(r"^\s*u?tACK\s+[0-9a-f]{6,}", re.I)

QUOTE_RE = re.compile(
    r"\b(nack|utack|concept nack|approach nack|do not merge|don't merge|"
    r"won't merge|will not merge|precedent|slippery|consensus|"
    r"soft fork|hard fork|political|process|maintainer|nak\b|"
    r"not mergeable|cannot merge)\b",
    re.I,
)
SATOSHI_RE = re.compile(
    r"\b(I('m| am) better staying|the nature of Bitcoin|"
    r"if you don't believe me or don't get it|"
    r"we are all in control|no one person|"
    r"I will not be the|I've moved on|"
    r"design was set in stone|version 0\.1)\b",
    re.I,
)
HTML_RE = re.compile(r"<[^>]+>")


def _clean(text: Optional[str], n: int = 420) -> str:
    if not text:
        return ""
    t = HTML_RE.sub(" ", str(text))
    t = re.sub(r"\s+", " ", t).strip()
    return t[:n]


def _era(iso: Optional[str]) -> str:
    if not iso:
        return "unknown"
    year = int(str(iso)[:4])
    if year <= 2014:
        return "early"
    if year <= 2017:
        return "segwit"
    if year <= 2021:
        return "taproot"
    return "2022+"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _wanted_pr_numbers() -> Dict[int, str]:
    """PR numbers the existing analyses already flagged as high-signal."""
    wanted: Dict[int, str] = {}
    analysis = get_analysis_dir() / "findings" / "data"
    findings = get_findings_dir() / "data"

    stalled = _load_json(analysis / "stalled_proposal_dossiers.json") or _load_json(
        findings / "stalled_proposal_dossiers.json"
    )
    for prop in stalled.get("proposals") or []:
        pid = prop.get("id") or "stalled"
        for key in ("first_pr", "longest_lived_unmerged"):
            item = prop.get(key) or {}
            num = item.get("number")
            if num:
                wanted[int(num)] = f"stalled:{pid}"
        for pr in (prop.get("prs") or [])[:8]:
            num = pr.get("number")
            if num:
                wanted.setdefault(int(num), f"stalled:{pid}")

    sample = _load_json(findings / "high_prep_outsider_closed_sample.json") or _load_json(
        analysis / "high_prep_outsider_closed_sample.json"
    )
    for item in sample.get("items") or []:
        if "nack" in " ".join(item.get("codes") or []) or item.get("primary_code") == "nack_signal":
            num = item.get("number")
            if num:
                wanted.setdefault(int(num), "high_prep_nack")

    return wanted


def _snippets_from_pr(pr: Dict[str, Any], limit: int = 4) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    blobs = []
    for r in pr.get("reviews") or []:
        body = _clean(r.get("body"), 500)
        author = (r.get("author") or "").lower()
        if author in SKIP_AUTHORS or SKIP_QUOTE.search(body) or UTACK_ONLY.match(body):
            continue
        if not body or not QUOTE_RE.search(body):
            continue
        blobs.append(
            {
                "kind": "review",
                "author": r.get("author") or "",
                "date": r.get("submitted_at") or "",
                "quote": body,
            }
        )
    for c in pr.get("comments") or []:
        body = _clean(c.get("body"), 500)
        author = (c.get("author") or "").lower()
        if author in SKIP_AUTHORS or SKIP_QUOTE.search(body) or UTACK_ONLY.match(body):
            continue
        if not body or not QUOTE_RE.search(body):
            continue
        blobs.append(
            {
                "kind": "comment",
                "author": c.get("author") or "",
                "date": c.get("created_at") or "",
                "quote": body,
            }
        )
    # Prefer longer, more specific quotes
    blobs.sort(key=lambda x: len(x["quote"]), reverse=True)
    return blobs[:limit]


def mine_prs() -> List[Dict[str, Any]]:
    wanted = _wanted_pr_numbers()
    scored: List[Dict[str, Any]] = []
    extras: List[Dict[str, Any]] = []

    path = get_data_dir() / "github" / "prs_raw.jsonl"
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            pr = json.loads(line)
            num = pr.get("number")
            if not num:
                continue
            nacks = 0
            for r in pr.get("reviews") or []:
                blob = f"{r.get('state') or ''} {r.get('body') or ''}".lower()
                if "nack" in blob and "utack" not in blob.replace("concept nack", "nack"):
                    nacks += 1
            for c in pr.get("comments") or []:
                if re.search(r"\bnack\b", (c.get("body") or ""), re.I):
                    nacks += 1

            days = pr.get("time_to_merge_days")
            if days is None and pr.get("created_at") and (pr.get("closed_at") or pr.get("merged_at")):
                try:
                    a = datetime.fromisoformat(str(pr["created_at"]).replace("Z", "+00:00"))
                    b = datetime.fromisoformat(
                        str(pr.get("merged_at") or pr.get("closed_at")).replace("Z", "+00:00")
                    )
                    days = (b - a).days
                except Exception:
                    days = None

            labels = [str(x).lower() if not isinstance(x, dict) else str(x.get("name") or "").lower()
                      for x in (pr.get("labels") or [])]
            consensusish = any("consensus" in x or "validation" in x for x in labels)
            flagged = int(num) in wanted
            if not flagged and nacks < 3 and not (consensusish and (days or 0) > 180):
                continue

            snippets = _snippets_from_pr(pr)
            if not snippets and not flagged:
                continue
            rec = {
                "source": "github",
                "pr": int(num),
                "title": pr.get("title") or "",
                "url": f"https://github.com/bitcoin/bitcoin/pull/{num}",
                "author": pr.get("author") or "",
                "merged": bool(pr.get("merged")),
                "era": _era(pr.get("created_at")),
                "created_at": pr.get("created_at"),
                "nacks_proxy": nacks,
                "days": days,
                "why": wanted.get(int(num), "high_nack_or_long_consensus"),
                "snippets": snippets,
                "frame": "funnel" if flagged or nacks else "decision",
            }
            if flagged:
                scored.append(rec)
            else:
                extras.append(rec)

    extras.sort(key=lambda r: (r.get("nacks_proxy") or 0, r.get("days") or 0), reverse=True)
    return scored + extras[:18]


def mine_satoshi(limit: int = 12) -> List[Dict[str, Any]]:
    path = get_data_dir() / "satoshi_archive" / "satoshi_communications.jsonl"
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            rec = json.loads(line)
            content = rec.get("content") or ""
            if "<html" in content[:200].lower() or "<!DOCTYPE" in content[:80]:
                continue
            if re.search(r"task manager|Set Priority|wallet\.dat|CPU hog", content):
                continue
            if not SATOSHI_RE.search(content):
                continue
            # Pull the matching paragraph
            quote = ""
            for para in re.split(r"\n\s*\n", content):
                if SATOSHI_RE.search(para) or QUOTE_RE.search(para):
                    quote = _clean(para, 480)
                    if len(quote) > 80:
                        break
            if len(quote) < 80:
                continue
            out.append(
                {
                    "source": "satoshi",
                    "pr": None,
                    "title": rec.get("subject") or rec.get("filename") or "",
                    "url": "",
                    "author": rec.get("from") or "Satoshi Nakamoto",
                    "merged": None,
                    "era": "early",
                    "created_at": rec.get("date"),
                    "nacks_proxy": 0,
                    "days": None,
                    "why": "satoshi_governance_voice",
                    "snippets": [{"kind": "archive", "author": rec.get("from") or "", "date": rec.get("date") or "", "quote": quote}],
                    "frame": "agenda",
                }
            )
            if len(out) >= limit:
                break
    return out


def mine_mail_for_prs(pr_nums: List[int], limit: int = 10) -> List[Dict[str, Any]]:
    """Pull bitcoin-dev lines that mention a flagged PR number."""
    if not pr_nums:
        return []
    needles = {str(n) for n in pr_nums}
    path = get_data_dir() / "mailing_lists" / "emails.jsonl"
    if not path.exists():
        return []
    pat = re.compile(r"(?:pull/|#)(\d{4,6})\b")
    out: List[Dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            rec = json.loads(line)
            body = rec.get("body") or rec.get("text") or rec.get("content") or ""
            if not body:
                continue
            found = [m for m in pat.findall(body) if m in needles]
            if not found:
                continue
            if not QUOTE_RE.search(body):
                continue
            quote = ""
            for para in re.split(r"\n\s*\n", body):
                if QUOTE_RE.search(para) and any(n in para for n in found):
                    quote = _clean(para, 480)
                    if len(quote) > 70:
                        break
            if len(quote) < 70:
                quote = _clean(body, 400)
            out.append(
                {
                    "source": "bitcoin-dev",
                    "pr": int(found[0]),
                    "title": rec.get("subject") or "",
                    "url": "",
                    "author": rec.get("from") or rec.get("author") or "",
                    "merged": None,
                    "era": _era(rec.get("date") or rec.get("created_at")),
                    "created_at": rec.get("date") or rec.get("created_at"),
                    "nacks_proxy": 1,
                    "days": None,
                    "why": "list_mentions_flagged_pr",
                    "snippets": [{"kind": "email", "author": rec.get("from") or "", "date": rec.get("date") or "", "quote": quote}],
                    "frame": "agenda",
                }
            )
            if len(out) >= limit:
                break
    return out


def interpret_extractive(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """No-model gem lines: the quote is the gem; tag the frame."""
    gems: List[Dict[str, Any]] = []
    for item in items:
        snips = item.get("snippets") or []
        if not snips:
            continue
        top = snips[0]
        gems.append(
            {
                "headline": item.get("title") or item.get("why"),
                "quote": top.get("quote"),
                "speaker": top.get("author"),
                "when": top.get("date") or item.get("created_at"),
                "source": item.get("source"),
                "pr": item.get("pr"),
                "url": item.get("url"),
                "era": item.get("era"),
                "frame": item.get("frame"),
                "why_look_here": item.get("why"),
                "llm": False,
            }
        )
    return gems


def call_llm(items: List[Dict[str, Any]], model: str) -> Optional[List[Dict[str, Any]]]:
    base = (os.environ.get("OPENAI_BASE_URL") or "").rstrip("/")
    if not base:
        return None
    key = os.environ.get("OPENAI_API_KEY") or "local"
    payload_items = []
    for item in items[:24]:
        payload_items.append(
            {
                "pr": item.get("pr"),
                "title": item.get("title"),
                "era": item.get("era"),
                "why": item.get("why"),
                "url": item.get("url"),
                "snippets": item.get("snippets"),
            }
        )
    prompt = (
        "You are reading cited excerpts from Bitcoin Core's public archives "
        "(GitHub, bitcoin-dev, Satoshi). Return JSON {\"gems\": [...]} only.\n"
        "Each gem: headline, quote (verbatim substring of a provided snippet), "
        "speaker, frame (agenda|funnel|portable|exit), why_it_matters (one sentence), "
        "pr, url, era. Do not invent quotes. Do not name-shame; talk about the process.\n\n"
        + json.dumps(payload_items, ensure_ascii=False)[:24000]
    )
    body = json.dumps(
        {
            "model": model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": "Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        base + "/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None
    text = (((data.get("choices") or [{}])[0].get("message") or {}).get("content")) or ""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    gems = parsed.get("gems") if isinstance(parsed, dict) else parsed
    if not isinstance(gems, list):
        return None
    for g in gems:
        g["llm"] = True
    return gems


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract archive gems for the frames")
    parser.add_argument("--llm", action="store_true", help="Call OPENAI_BASE_URL if set")
    parser.add_argument("--model", default=os.environ.get("OPENAI_MODEL") or "local")
    args = parser.parse_args()

    pr_items = mine_prs()
    satoshi = mine_satoshi()
    mail = mine_mail_for_prs([i["pr"] for i in pr_items if i.get("pr")][:40])
    items = pr_items + satoshi + mail

    gems = interpret_extractive(items)
    llm_gems: Optional[List[Dict[str, Any]]] = None
    llm_note = "extractive only (no live LLM endpoint this run)"
    if args.llm:
        llm_gems = call_llm(items, args.model)
        if llm_gems:
            gems = llm_gems
            llm_note = f"llm via OPENAI_BASE_URL model={args.model}"
        else:
            llm_note = "llm requested but endpoint failed; extractive fallback"

    results = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": llm_note,
        "n_candidates": len(items),
        "n_gems": len(gems),
        "frames_used": ["agenda", "funnel", "portable", "exit"],
        "candidates": items,
        "gems": gems,
    }
    written = save_analysis_json("archive_gems.json", results)
    print(f"Candidates {len(items)} | gems {len(gems)} | {llm_note}")
    print("Wrote", ", ".join(str(p) for p in written))
    return 0


if __name__ == "__main__":
    sys.exit(main())
