"""Tree-sitter AST metrics for Java and Go (cyclomatic, nesting, entropy, imports)."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from omega.metrics import FileMetrics, _compression_ratio, _omega_local, _risk_band, _textual_entropy

if TYPE_CHECKING:
    from tree_sitter import Node, Parser, Tree

AST_LANGUAGES = frozenset({"java", "go"})

_JAVA_BRANCH = frozenset(
    {
        "if_statement",
        "for_statement",
        "enhanced_for_statement",
        "while_statement",
        "do_statement",
        "switch_expression",
        "synchronized_statement",
        "catch_clause",
        "conditional_expression",
    }
)
_GO_BRANCH = frozenset(
    {
        "if_statement",
        "for_statement",
        "expression_switch_statement",
        "type_switch_statement",
        "select_statement",
    }
)
_NEST_CONTAINERS = frozenset(
    {
        "block",
        "class_body",
        "method_declaration",
        "constructor_declaration",
        "static_initializer",
        "statement_block",
        "switch_block",
        "switch_block_statement_group",
        "function_declaration",
        "method_declaration",
        "func_literal",
    }
)


@dataclass(frozen=True)
class TsFileAnalysis:
    cyclomatic: int
    nesting_depth: int
    h_struct: float
    import_stems: frozenset[str]


def _optional_tree_sitter():
    try:
        from tree_sitter import Language, Parser  # noqa: F401

        return True
    except ImportError:
        return False


@lru_cache(maxsize=2)
def _parser(language: str) -> Parser:
    from tree_sitter import Language, Parser

    if language == "java":
        import tree_sitter_java as lang_mod
    elif language == "go":
        import tree_sitter_go as lang_mod
    else:
        raise ValueError(f"No tree-sitter grammar for {language}")
    return Parser(Language(lang_mod.language()))


def parse_tree(language: str, source: str) -> Tree | None:
    if not _optional_tree_sitter() or language not in AST_LANGUAGES:
        return None
    try:
        return _parser(language).parse(source.encode("utf-8"))
    except Exception:
        return None


def _walk(node: Node) -> list[Node]:
    out: list[Node] = [node]
    for i in range(node.child_count):
        out.extend(_walk(node.child(i)))
    return out


def _structural_entropy(nodes: list[Node]) -> float:
    types = [n.type for n in nodes]
    if not types:
        return 0.0
    counts = Counter(types)
    total = sum(counts.values())
    entropy = 0.0
    for c in counts.values():
        p = c / total
        entropy -= p * math.log2(p)
    return entropy


def _max_nesting(node: Node, depth: int = 0) -> int:
    max_d = depth
    child_depth = depth + 1 if node.type in _NEST_CONTAINERS else depth
    for i in range(node.child_count):
        max_d = max(max_d, _max_nesting(node.child(i), child_depth))
    return max_d


def _cyclomatic(node: Node, language: str) -> int:
    branch = _JAVA_BRANCH if language == "java" else _GO_BRANCH
    return 1 + sum(1 for n in _walk(node) if n.type in branch)


def _java_import_stems(root: Node) -> set[str]:
    stems: set[str] = set()
    for n in _walk(root):
        if n.type != "import_declaration":
            continue
        for child in n.children:
            if child.type == "scoped_identifier":
                text = child.text.decode("utf-8", errors="replace")
                stems.add(text.split(".")[-1].lower())
            elif child.type == "identifier" and child.text:
                stems.add(child.text.decode("utf-8", errors="replace").lower())
    return stems


def _go_import_path_from_spec(spec: Node) -> str | None:
    path_node = spec.child_by_field_name("path")
    if path_node is None:
        for c in spec.children:
            if c.type == "interpreted_string_literal":
                path_node = c
                break
    if path_node is None or not path_node.text:
        return None
    raw = path_node.text.decode("utf-8", errors="replace").strip('"')
    return raw.strip() or None


def _go_import_stems(root: Node) -> set[str]:
    stems: set[str] = set()
    for n in _walk(root):
        if n.type == "import_spec":
            raw = _go_import_path_from_spec(n)
            if raw:
                stems.add(raw.split("/")[-1].lower())
    return stems


def analyze_tree(language: str, source: str, tree: Tree) -> TsFileAnalysis:
    root = tree.root_node
    if root.type == "ERROR" or root.has_error:
        raise ValueError("parse tree has errors")
    stems = _java_import_stems(root) if language == "java" else _go_import_stems(root)
    nodes = _walk(root)
    return TsFileAnalysis(
        cyclomatic=_cyclomatic(root, language),
        nesting_depth=_max_nesting(root),
        h_struct=_structural_entropy(nodes),
        import_stems=frozenset(stems),
    )


def _loc(source: str, language: str) -> int:
    comment_prefix = ("//", "#") if language != "java" else ("//",)
    return sum(
        1
        for line in source.splitlines()
        if line.strip()
        and not any(line.strip().startswith(p) for p in comment_prefix)
        and not line.strip().startswith("/*")
        and not line.strip().startswith("*")
    )


def file_metrics_from_tree(
    *,
    rel_path: str,
    language: str,
    source: str,
    tree: Tree,
    coupling_out: int,
    coupling_in: int,
) -> FileMetrics:
    a = analyze_tree(language, source, tree)
    h_text = _textual_entropy(source)
    loc = _loc(source, language)
    compress = _compression_ratio(source)
    omega = _omega_local(a.h_struct, a.cyclomatic, a.nesting_depth, coupling_out, compress)
    return FileMetrics(
        path=rel_path,
        language=language,
        loc=loc,
        cyclomatic=a.cyclomatic,
        nesting_depth=a.nesting_depth,
        h_struct=round(a.h_struct, 3),
        h_text=round(h_text, 3),
        compression_ratio=round(compress, 2),
        coupling_out=coupling_out,
        coupling_in=coupling_in,
        omega_local=omega,
        risk_band=_risk_band(omega),
        import_count=max(coupling_out, len(a.import_stems)),
    )


def ts_coupling_maps(
    language: str,
    paths: list[Path],
    sources: dict[Path, str],
    stem_to_path: dict[str, Path],
) -> tuple[dict[Path, int], dict[Path, int]]:
    """AST import graph for Java/Go files (internal module stems)."""
    out_c: dict[Path, int] = {p: 0 for p in paths}
    # Inbound edges may target any repo file (e.g. Java → TS module stem), not only Java/Go paths.
    in_c: dict[Path, int] = {p: 0 for p in set(stem_to_path.values())}
    if language not in AST_LANGUAGES:
        return out_c, in_c

    for path in paths:
        src = sources.get(path, "")
        if not src.strip():
            continue
        tree = parse_tree(language, src)
        if tree is None:
            continue
        try:
            stems = analyze_tree(language, src, tree).import_stems
        except ValueError:
            continue
        self_stem = path.stem.lower()
        deps: set[str] = set()
        for stem in stems:
            if stem in stem_to_path and stem != self_stem:
                deps.add(stem)
        out_c[path] = len(deps)
        for dep in deps:
            target = stem_to_path.get(dep)
            if target is not None and target in in_c:
                in_c[target] += 1
    return out_c, in_c
