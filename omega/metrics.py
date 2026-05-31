"""Mathematical metrics for Ω-QFM (Phase 1 MVP)."""

from __future__ import annotations

import ast
import gzip
import io
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FileMetrics:
    path: str
    loc: int
    cyclomatic: int
    nesting_depth: int
    h_struct: float
    h_text: float
    compression_ratio: float
    coupling_out: int
    coupling_in: int
    omega_local: float
    risk_band: str
    language: str = "python"
    import_count: int = 0


def _python_files(root: Path) -> list[Path]:
    skip = {"__pycache__", ".git", ".venv", "venv", "node_modules"}
    files: list[Path] = []
    for p in root.rglob("*.py"):
        if any(part in skip for part in p.parts):
            continue
        files.append(p)
    return sorted(files)


def _cyclomatic_and_nesting(tree: ast.AST) -> tuple[int, int]:
    """McCabe-style complexity + max nesting depth."""
    complexity = 1
    max_depth = 0

    def walk(node: ast.AST, depth: int) -> None:
        nonlocal complexity, max_depth
        max_depth = max(max_depth, depth)
        if isinstance(
            node,
            (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.ExceptHandler),
        ):
            complexity += 1
        if isinstance(node, (ast.BoolOp, ast.IfExp)):
            complexity += max(0, len(getattr(node, "values", [])) - 1)
        for child in ast.iter_child_nodes(node):
            child_depth = depth + 1 if isinstance(child, (ast.If, ast.For, ast.While, ast.Try)) else depth
            walk(child, child_depth)

    walk(tree, 0)
    return complexity, max_depth


def _structural_entropy(tree: ast.AST) -> float:
    types: list[str] = []
    for node in ast.walk(tree):
        types.append(type(node).__name__)
    if not types:
        return 0.0
    counts = Counter(types)
    total = sum(counts.values())
    entropy = 0.0
    for c in counts.values():
        p = c / total
        entropy -= p * math.log2(p)
    return entropy


def _textual_entropy(source: str) -> float:
    tokens = re.findall(r"\w+|\S", source)
    if not tokens:
        return 0.0
    counts = Counter(tokens)
    total = len(tokens)
    entropy = 0.0
    for c in counts.values():
        p = c / total
        entropy -= p * math.log2(p)
    return entropy


def _compression_ratio(source: str) -> float:
    raw = source.encode("utf-8")
    if not raw:
        return 1.0
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
        gz.write(raw)
    compressed = len(buf.getvalue())
    return len(raw) / max(compressed, 1)


def _imports(path: Path, tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def _coupling_graph(files: list[Path], sources: dict[Path, str]) -> tuple[dict[Path, set[str]], dict[Path, set[str]]]:
    module_names = {p.stem for p in files}
    out_edges: dict[Path, set[str]] = {p: set() for p in files}
    in_edges: dict[Path, set[str]] = {p: set() for p in files}
    for path in files:
        try:
            tree = ast.parse(sources[path], filename=str(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                mod = node.module.split(".")[-1]
                if mod in module_names and mod != path.stem:
                    out_edges[path].add(mod)
                    for target in files:
                        if target.stem == mod:
                            in_edges[target].add(path.stem)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    mod = alias.name.split(".")[-1]
                    if mod in module_names and mod != path.stem:
                        out_edges[path].add(mod)
                        for target in files:
                            if target.stem == mod:
                                in_edges[target].add(path.stem)
    return out_edges, in_edges


def _risk_band(omega: float) -> str:
    if omega < 35:
        return "LOW"
    if omega < 55:
        return "MEDIUM"
    if omega < 75:
        return "HIGH"
    return "CRITICAL"


def _omega_local(
    h_struct: float,
    cyclomatic: int,
    nesting: int,
    coupling_out: int,
    compression_ratio: float,
) -> float:
    """Composite Ω_local (0–100, higher = worse quality field)."""
    norm_struct = min(100, h_struct * 8)
    norm_cyc = min(100, cyclomatic * 6)
    norm_nest = min(100, nesting * 12)
    norm_coupling = min(100, coupling_out * 15)
    norm_compress = min(100, abs(compression_ratio - 2.5) * 10)
    return round(
        0.28 * norm_struct
        + 0.25 * norm_cyc
        + 0.18 * norm_nest
        + 0.17 * norm_coupling
        + 0.12 * norm_compress,
        2,
    )


def compute_file_metrics(
    path: Path,
    root: Path,
    source: str,
    coupling_out: int,
    coupling_in: int,
) -> FileMetrics:
    tree = ast.parse(source, filename=str(path))
    cyclomatic, nesting = _cyclomatic_and_nesting(tree)
    h_struct = _structural_entropy(tree)
    h_text = _textual_entropy(source)
    loc = sum(1 for line in source.splitlines() if line.strip() and not line.strip().startswith("#"))
    omega = _omega_local(h_struct, cyclomatic, nesting, coupling_out, _compression_ratio(source))
    rel = str(path.relative_to(root))
    return FileMetrics(
        path=rel,
        language="python",
        loc=loc,
        cyclomatic=cyclomatic,
        nesting_depth=nesting,
        h_struct=round(h_struct, 3),
        h_text=round(h_text, 3),
        compression_ratio=round(_compression_ratio(source), 2),
        coupling_out=coupling_out,
        coupling_in=coupling_in,
        omega_local=omega,
        risk_band=_risk_band(omega),
        import_count=coupling_out,
    )


def analyze_files(root: Path) -> list[FileMetrics]:
    files = _python_files(root)
    sources = {p: p.read_text(encoding="utf-8", errors="replace") for p in files}
    out_edges, in_edges = _coupling_graph(files, sources)
    metrics: list[FileMetrics] = []
    for path in files:
        out_count = len(out_edges.get(path, set()))
        in_count = len(in_edges.get(path, set()))
        metrics.append(
            compute_file_metrics(path, root, sources[path], out_count, in_count)
        )
    return sorted(metrics, key=lambda m: m.omega_local, reverse=True)
