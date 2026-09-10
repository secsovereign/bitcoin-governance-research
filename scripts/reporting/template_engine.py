#!/usr/bin/env python3
"""Minimal markdown template renderer.

Placeholders: ``{{path.to.value|filter}}``
Loops:
  ``{% for item in path %} ... {{item.0}} / {{item.key}} ... {% endfor %}``
  ``{% for key, value in path.items %} ... {% endfor %}``
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


FILTERS = {
    "int": lambda v: f"{int(round(float(v))):,}" if v is not None and v != "" else "—",
    "comma": lambda v: f"{int(v):,}" if isinstance(v, (int, float)) else str(v),
    "pct": lambda v: f"{float(v) * 100:.1f}%" if v is not None and v != "" else "—",
    "pct0": lambda v: f"{float(v) * 100:.0f}%" if v is not None and v != "" else "—",
    "pp": lambda v: f"{float(v):.1f} pp" if v is not None and v != "" else "—",
    "round1": lambda v: f"{float(v):.1f}" if v is not None and v != "" else "—",
    "round2": lambda v: f"{float(v):.2f}" if v is not None and v != "" else "—",
    "round3": lambda v: f"{float(v):.3f}" if v is not None and v != "" else "—",
    "str": lambda v: "" if v is None else str(v),
}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve(data: Any, path: str) -> Any:
    if path in ("generated_date",):
        return date.today().isoformat()
    if isinstance(data, dict) and path in data:
        return data[path]
    current = data
    for part in path.split("."):
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, (list, tuple)):
            if part.isdigit():
                idx = int(part)
                current = current[idx] if 0 <= idx < len(current) else None
            else:
                return None
        else:
            return None
    return current


def apply_filter(value: Any, name: str) -> str:
    if not name:
        if value is None:
            return "—"
        if isinstance(value, float):
            return f"{value:.4g}"
        return str(value)
    fn = FILTERS.get(name)
    if not fn:
        return str(value)
    try:
        return fn(value)
    except (TypeError, ValueError):
        return "—"


_PLACEHOLDER = re.compile(r"\{\{\s*([^}|]+?)(?:\|([a-z0-9]+))?\s*\}\}")
_FOR = re.compile(
    r"\{%\s*for\s+(.+?)\s+in\s+([^\s%]+)\s*%\}(.*?)\{\%\s*endfor\s*%\}",
    re.DOTALL,
)


def _render_placeholders(text: str, scope: Dict[str, Any]) -> str:
    def repl(match: re.Match) -> str:
        path = match.group(1).strip()
        filt = match.group(2) or ""
        return apply_filter(resolve(scope, path), filt)

    return _PLACEHOLDER.sub(repl, text)


def _iter_items(value: Any, items_mode: bool) -> Iterable[Tuple[Any, Any]]:
    if items_mode:
        if isinstance(value, dict):
            return value.items()
        return []
    if isinstance(value, dict):
        return enumerate(value.values())
    if isinstance(value, list):
        return enumerate(value)
    return []


def render(template: str, context: Dict[str, Any]) -> str:
    def expand_for(match: re.Match) -> str:
        vars_part = match.group(1).strip()
        path = match.group(2).strip()
        body = match.group(3)
        if body.startswith("\n"):
            body = body[1:]
        items_mode = path.endswith(".items")
        if items_mode:
            path = path[: -len(".items")]
        source = resolve(context, path)
        names = [n.strip() for n in vars_part.split(",")]
        chunks: List[str] = []
        for key, value in _iter_items(source, items_mode):
            local = dict(context)
            if items_mode and len(names) == 2:
                local[names[0]] = key
                local[names[1]] = value
            elif len(names) == 1:
                item = value
                local[names[0]] = item
                if isinstance(item, dict):
                    local.update({f"{names[0]}.{k}": v for k, v in item.items()})
                elif isinstance(item, (list, tuple)):
                    for i, v in enumerate(item):
                        local[f"{names[0]}.{i}"] = v
            chunks.append(_render_placeholders(body, local))
        return "".join(chunks)

    expanded = _FOR.sub(expand_for, template)
    return _render_placeholders(expanded, context)


def render_file(template_path: Path, context: Dict[str, Any]) -> str:
    return render(template_path.read_text(encoding="utf-8"), context)
