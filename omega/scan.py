"""Scan repository — all languages."""

from __future__ import annotations

import ast
from pathlib import Path

from omega.discover import RepoInventory, SourceFile, discover_source_files
from omega.entities import EntityMetrics, analyze_file_entities
from omega.metrics import FileMetrics, _coupling_graph, _omega_local, _risk_band
from omega.metrics_heuristic import analyze_source_text

# Re-use Python helpers from metrics
from omega import metrics as py_metrics


def _analyze_python(path: Path, root: Path, source: str, coupling_out: int, coupling_in: int) -> FileMetrics:
    tree = ast.parse(source, filename=str(path))
    cyclomatic, nesting = py_metrics._cyclomatic_and_nesting(tree)
    h_struct = py_metrics._structural_entropy(tree)
    h_text = py_metrics._textual_entropy(source)
    loc = sum(
        1
        for line in source.splitlines()
        if line.strip() and not line.strip().startswith("#")
    )
    compress = py_metrics._compression_ratio(source)
    omega = _omega_local(h_struct, cyclomatic, nesting, coupling_out, compress)
    return FileMetrics(
        path=str(path.relative_to(root)),
        language="python",
        loc=loc,
        cyclomatic=cyclomatic,
        nesting_depth=nesting,
        h_struct=round(h_struct, 3),
        h_text=round(h_text, 3),
        compression_ratio=round(compress, 2),
        coupling_out=coupling_out,
        coupling_in=coupling_in,
        omega_local=omega,
        risk_band=_risk_band(omega),
        import_count=coupling_out,
    )


def _build_coupling(files: list[SourceFile], sources: dict[Path, str]) -> tuple[dict[Path, int], dict[Path, int]]:
    """Approximate coupling via shared module stem names in import statements."""
    stems = {f.path.stem: f.path for f in files}
    out_c: dict[Path, int] = {f.path: 0 for f in files}
    in_c: dict[Path, int] = {f.path: 0 for f in files}
    import re

    pat = re.compile(
        r"(?:import|from|require|#include|using|package)\s+['\"]?([\w./]+)",
        re.I,
    )
    for sf in files:
        text = sources.get(sf.path, "")
        deps: set[str] = set()
        for m in pat.finditer(text):
            token = m.group(1).split("/")[-1].split(".")[0].lower()
            if token in {s.lower() for s in stems} and token != sf.path.stem.lower():
                deps.add(token)
        out_c[sf.path] = len(deps)
        for dep in deps:
            for f in files:
                if f.path.stem.lower() == dep:
                    in_c[f.path] += 1
    return out_c, in_c


def scan_repository(root: Path) -> tuple[list[FileMetrics], list[EntityMetrics], RepoInventory]:
    inventory = discover_source_files(root)
    sources: dict[Path, str] = {}
    for sf in inventory.files:
        try:
            sources[sf.path] = sf.path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            sources[sf.path] = ""

    py_paths = [sf.path for sf in inventory.files if sf.language == "python"]
    py_out, py_in = {}, {}
    if py_paths:
        py_out_edges, py_in_edges = py_metrics._coupling_graph(py_paths, sources)
        for p in py_paths:
            py_out[p] = len(py_out_edges.get(p, set()))
            py_in[p] = len(py_in_edges.get(p, set()))

    gen_out, gen_in = _build_coupling(inventory.files, sources)

    results: list[FileMetrics] = []
    all_entities: list[EntityMetrics] = []
    for sf in inventory.files:
        src = sources[sf.path]
        if not src.strip():
            continue
        cout = py_out.get(sf.path, gen_out.get(sf.path, 0))
        cin = py_in.get(sf.path, gen_in.get(sf.path, 0))
        try:
            if sf.language == "python":
                m = _analyze_python(sf.path, inventory.root, src, cout, cin)
            else:
                h = analyze_source_text(src, sf.language)
                omega = _omega_local(
                    h["h_struct"],
                    h["cyclomatic"],
                    h["nesting_depth"],
                    cout,
                    h["compression_ratio"],
                )
                m = FileMetrics(
                    path=sf.rel_path,
                    language=sf.language,
                    loc=h["loc"],
                    cyclomatic=h["cyclomatic"],
                    nesting_depth=h["nesting_depth"],
                    h_struct=h["h_struct"],
                    h_text=h["h_text"],
                    compression_ratio=h["compression_ratio"],
                    coupling_out=cout,
                    coupling_in=cin,
                    omega_local=omega,
                    risk_band=_risk_band(omega),
                    import_count=h.get("import_count", cout),
                )
            results.append(m)
            all_entities.extend(
                analyze_file_entities(m.path, sources[sf.path], sf.language)
            )
        except SyntaxError:
            h = analyze_source_text(src, sf.language)
            omega = _omega_local(
                h["h_struct"], h["cyclomatic"], h["nesting_depth"], cout, h["compression_ratio"]
            )
            results.append(
                FileMetrics(
                    path=sf.rel_path,
                    language=sf.language,
                    loc=h["loc"],
                    cyclomatic=h["cyclomatic"],
                    nesting_depth=h["nesting_depth"],
                    h_struct=h["h_struct"],
                    h_text=h["h_text"],
                    compression_ratio=h["compression_ratio"],
                    coupling_out=cout,
                    coupling_in=cin,
                    omega_local=omega,
                    risk_band=_risk_band(omega),
                    import_count=h.get("import_count", cout),
                )
            )
            all_entities.extend(
                analyze_file_entities(sf.rel_path, src, sf.language)
            )

    results.sort(key=lambda x: x.omega_local, reverse=True)
    all_entities.sort(key=lambda x: x.omega_local, reverse=True)
    return results, all_entities, inventory
