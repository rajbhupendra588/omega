"""Coupling graph helpers shared by master and workers."""

from __future__ import annotations

import re
from pathlib import Path

from omega import metrics as py_metrics
from omega.discover import SourceFile


def build_coupling_maps(
    files: list[SourceFile],
    sources: dict[Path, str],
) -> tuple[dict[Path, int], dict[Path, int]]:
    """Approximate in/out coupling via import/require/include stems."""
    stem_to_path: dict[str, Path] = {f.path.stem.lower(): f.path for f in files}
    out_c: dict[Path, int] = {f.path: 0 for f in files}
    in_c: dict[Path, int] = {f.path: 0 for f in files}

    pat = re.compile(
        r"(?:import|from|require|#include|using|package)\s+['\"]?([\w./]+)",
        re.I,
    )
    for sf in files:
        text = sources.get(sf.path, "")
        deps: set[str] = set()
        self_stem = sf.path.stem.lower()
        for m in pat.finditer(text):
            token = m.group(1).split("/")[-1].split(".")[0].lower()
            if token in stem_to_path and token != self_stem:
                deps.add(token)
        out_c[sf.path] = len(deps)
        for dep in deps:
            target = stem_to_path.get(dep)
            if target is not None:
                in_c[target] += 1
    return out_c, in_c


def python_coupling_maps(
    py_paths: list[Path],
    sources: dict[Path, str],
) -> tuple[dict[Path, int], dict[Path, int]]:
    """AST-based coupling for Python modules."""
    if not py_paths:
        return {}, {}
    out_edges, in_edges = py_metrics._coupling_graph(py_paths, sources)
    return (
        {p: len(out_edges.get(p, set())) for p in py_paths},
        {p: len(in_edges.get(p, set())) for p in py_paths},
    )
