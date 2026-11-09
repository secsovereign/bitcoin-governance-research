"""Path-based layer for a pull request.

The older ``pr_type`` label treats the word "policy" and ``src/policy/`` as
consensus. This classifier does not. It reads filenames only.

Precedence, after test and doc paths are set aside:

1. consensus: ``src/consensus/``, ``src/primitives/``, ``src/script/``
2. relay_policy: ``src/policy/``, mempool argument files, or ``src/init.cpp``
   / ``src/validation.cpp`` when a touched test path mentions datacarrier
   or mempool and no consensus path is present
3. wallet: ``src/wallet/``
4. gui: ``src/qt/``
5. build: build, CI, and dependency files
6. tests, if nothing else remains
7. other

A pull request can touch several layers. ``primary`` is the highest one.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Sequence, Set

LAYERS = (
    "consensus",
    "relay_policy",
    "wallet",
    "gui",
    "build",
    "tests",
    "other",
)

_PRECEDENCE = {name: i for i, name in enumerate(LAYERS)}


def _norm(path: str) -> str:
    return str(path or "").replace("\\", "/").lstrip("./")


def _is_test(path: str) -> bool:
    return (
        path.startswith("src/test/")
        or path.startswith("test/")
        or path.startswith("src/fuzz")
        or "/fuzz/" in path
        or path.startswith("src/wallet/test/")
        or path.startswith("src/qt/test/")
    )


def _is_doc(path: str) -> bool:
    return path.startswith("doc/") or path.endswith((".md", ".rst"))


def _is_build(path: str) -> bool:
    base = path.rsplit("/", 1)[-1]
    return (
        path.startswith(("depends/", "ci/", "cmake/", ".github/", "build-aux/"))
        or base in {"CMakeLists.txt", "Makefile", "Makefile.am", "configure.ac", "autogen.sh"}
        or base.endswith(".cmake")
    )


def _is_consensus(path: str) -> bool:
    return path.startswith(("src/consensus/", "src/primitives/", "src/script/"))


def _is_relay(path: str) -> bool:
    return (
        path.startswith("src/policy/")
        or path in {"src/node/mempool_args.cpp", "src/kernel/mempool_options.h"}
    )


def _is_wallet(path: str) -> bool:
    return path.startswith("src/wallet/")


def _is_gui(path: str) -> bool:
    return path.startswith("src/qt/")


def classify_filenames(files: Sequence[str]) -> Dict[str, object]:
    """Return layers touched and the primary layer."""
    names = [_norm(path) for path in files if _norm(path)]
    layers: Set[str] = set()
    production: List[str] = []
    for path in names:
        if _is_test(path):
            layers.add("tests")
            continue
        if _is_doc(path):
            layers.add("other")
            continue
        production.append(path)
        if _is_consensus(path):
            layers.add("consensus")
        elif _is_relay(path):
            layers.add("relay_policy")
        elif _is_wallet(path):
            layers.add("wallet")
        elif _is_gui(path):
            layers.add("gui")
        elif _is_build(path):
            layers.add("build")
        else:
            layers.add("other")

    policy_test = any(
        _is_test(path) and ("datacarrier" in path or "mempool" in path) for path in names
    )
    startup = {path for path in production if path in {"src/init.cpp", "src/validation.cpp"}}
    if policy_test and startup and "consensus" not in layers and "relay_policy" not in layers:
        layers.add("relay_policy")
        other_production = [
            path
            for path in production
            if path not in startup
            and not _is_build(path)
            and not _is_wallet(path)
            and not _is_gui(path)
            and not _is_consensus(path)
            and not _is_relay(path)
        ]
        if not other_production:
            layers.discard("other")

    if not layers:
        layers.add("other")
    primary = sorted(layers, key=lambda name: _PRECEDENCE[name])[0]
    ordered = [name for name in LAYERS if name in layers]
    return {"primary": primary, "layers": ordered, "rule": "filenames-v1"}


def filenames_of(pr: Dict[str, object]) -> List[str]:
    files = pr.get("files") or []
    if not isinstance(files, Iterable) or isinstance(files, (str, bytes)):
        return []
    out: List[str] = []
    for item in files:
        if isinstance(item, dict):
            name = item.get("filename") or item.get("path") or ""
        else:
            name = item
        if name:
            out.append(str(name))
    return out
