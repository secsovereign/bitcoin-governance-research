"""Write analysis JSON to both analysis/findings/data and findings/data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from src.utils.paths import get_analysis_dir, get_findings_dir


def analysis_json_paths(name: str) -> List[Path]:
    if not name.endswith(".json"):
        name = f"{name}.json"
    return [
        get_analysis_dir() / "findings" / "data" / name,
        get_findings_dir() / "data" / name,
    ]


def save_analysis_json(name: str, data: Dict[str, Any]) -> List[Path]:
    written: List[Path] = []
    payload = json.dumps(data, indent=2, default=str)
    for path in analysis_json_paths(name):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")
        written.append(path)
    return written


def mirror_analysis_json() -> List[str]:
    """Copy JSON that exists on only one of the two findings data dirs."""
    analysis = get_analysis_dir() / "findings" / "data"
    findings = get_findings_dir() / "data"
    analysis.mkdir(parents=True, exist_ok=True)
    findings.mkdir(parents=True, exist_ok=True)
    names = {p.name for p in analysis.glob("*.json")} | {p.name for p in findings.glob("*.json")}
    copied: List[str] = []
    for name in sorted(names):
        left, right = analysis / name, findings / name
        if left.exists() and not right.exists():
            right.write_text(left.read_text(encoding="utf-8"), encoding="utf-8")
            copied.append(f"{name} → findings/data")
        elif right.exists() and not left.exists():
            left.write_text(right.read_text(encoding="utf-8"), encoding="utf-8")
            copied.append(f"{name} → analysis/findings/data")
    return copied


def extract_nested_json(source_name: str, key: str, dest_name: str, overwrite: bool = False) -> List[Path]:
    """Write a nested object from one analysis JSON as its own dual-written file."""
    dests = analysis_json_paths(dest_name)
    if not overwrite and any(p.exists() for p in dests):
        return []
    for path in analysis_json_paths(source_name):
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        nested: Any = data
        for part in key.split("."):
            nested = nested.get(part) if isinstance(nested, dict) else None
        if isinstance(nested, dict) and nested:
            return save_analysis_json(dest_name, nested)
    return []
