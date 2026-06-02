"""Class, method, and field-level quality measurement."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, replace

from omega.implementation import build_implementation_plan
from omega.scan_config import impl_plan_max_entities, max_entities_per_file
from omega.metrics import _compression_ratio, _omega_local, _risk_band, _structural_entropy, _textual_entropy
from omega.parse_util import parse_python


@dataclass(frozen=True)
class EntityMetrics:
    entity_type: str  # class | method | field | function
    qualified_name: str
    file_path: str
    line_start: int
    line_end: int
    loc: int
    cyclomatic: int
    nesting_depth: int
    omega_local: float
    risk_band: str
    improvement_areas: tuple[str, ...] = ()
    improvement_areas_business: tuple[str, ...] = ()
    implementation_plan: tuple[str, ...] = ()
    implementation_summary: tuple[str, ...] = ()
    implementation_diffs: tuple[dict, ...] = ()
    parent_class: str | None = None
    parameter_count: int = 0
    method_count: int = 0
    field_count: int = 0


def _cyclomatic_nesting_node(node: ast.AST) -> tuple[int, int]:
    complexity = 1
    max_depth = 0

    def walk(n: ast.AST, depth: int) -> None:
        nonlocal complexity, max_depth
        max_depth = max(max_depth, depth)
        if isinstance(n, (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.ExceptHandler)):
            complexity += 1
        if isinstance(n, ast.BoolOp):
            complexity += max(0, len(n.values) - 1)
        if isinstance(n, ast.IfExp):
            complexity += 1
        for child in ast.iter_child_nodes(n):
            d = depth + 1 if isinstance(child, (ast.If, ast.For, ast.While, ast.Try)) else depth
            walk(child, d)

    walk(node, 0)
    return complexity, max_depth


def _loc_lines(node: ast.AST) -> int:
    if not hasattr(node, "lineno") or not hasattr(node, "end_lineno"):
        return 1
    end = node.end_lineno or node.lineno
    return max(1, end - node.lineno + 1)


def _source_slice(source: str, node: ast.AST) -> str:
    lines = source.splitlines()
    start = (node.lineno or 1) - 1
    end = node.end_lineno or node.lineno or start + 1
    return "\n".join(lines[start:end])


def _improvements(
    entity_type: str,
    *,
    cyclomatic: int,
    nesting: int,
    loc: int,
    params: int = 0,
    method_count: int = 0,
    field_count: int = 0,
    name: str = "",
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    tech: list[str] = []
    biz: list[str] = []

    if cyclomatic >= 15:
        tech.append(f"Critical cyclomatic complexity ({cyclomatic}): decompose into smaller units with single responsibility.")
        biz.append(f"'{name}' has too many decision paths — bugs hide here; simplify or split.")
    elif cyclomatic >= 8:
        tech.append(f"Elevated cyclomatic complexity ({cyclomatic}): extract guard clauses or helper methods.")
        biz.append(f"Reduce branching in '{name}' to make testing and reviews faster.")

    if nesting >= 5:
        tech.append(f"Deep nesting (depth {nesting}): flatten with early returns or strategy extraction.")
        biz.append(f"Nested logic in '{name}' is hard to follow — refactor for readability.")
    elif nesting >= 3 and entity_type in ("method", "function"):
        tech.append(f"Nesting depth {nesting}: consider extracting inner blocks to named functions.")

    if entity_type in ("method", "function") and loc >= 80:
        tech.append(f"Long {entity_type} ({loc} LOC): apply extract-method; target < 40 lines.")
        biz.append(f"'{name}' is too long — split so each piece does one job.")
    elif entity_type in ("method", "function") and loc >= 45:
        tech.append(f"{entity_type.capitalize()} length {loc} lines exceeds guideline (~30–40).")

    if params >= 7:
        tech.append(f"High arity ({params} parameters): introduce parameter object or builder.")
        biz.append(f"'{name}' takes too many inputs — bundle into a config/data object.")
    elif params >= 5:
        tech.append(f"{params} parameters: review if all are necessary.")

    if entity_type == "class":
        if method_count >= 20:
            tech.append(f"God class signal ({method_count} methods): split by bounded context or feature area.")
            biz.append(f"Class '{name}' does too much — divide into focused classes for team ownership.")
        elif method_count >= 12:
            tech.append(f"Large class ({method_count} methods): group related methods into mixins or sub-modules.")

        if field_count >= 25:
            tech.append(f"Excessive state ({field_count} fields): apply decomposition or value objects.")
            biz.append(f"'{name}' holds too much data — split to reduce change risk.")
        elif field_count >= 15:
            tech.append(f"High field count ({field_count}): audit which fields belong together.")

    if entity_type == "field" and loc > 3:
        tech.append("Field initializer is complex; move logic to factory or __post_init__.")

    if not tech:
        tech.append("Metrics within healthy range; maintain on change.")
        biz.append("No urgent structural issues detected.")

    return tuple(tech), tuple(biz)


def _attach_implementation(
    *,
    entity_type: str,
    file_path: str,
    language: str,
    source: str,
    qualified_name: str,
    risk_band: str,
    cyclomatic: int,
    nesting: int,
    loc: int,
    params: int = 0,
    method_count: int = 0,
    field_count: int = 0,
    node: ast.AST | None = None,
    class_node: ast.ClassDef | None = None,
    methods: list[ast.FunctionDef | ast.AsyncFunctionDef] | None = None,
    field_names: list[str] | None = None,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[dict, ...]]:
    return build_implementation_plan(
        entity_type=entity_type,
        file_path=file_path,
        language=language,
        source=source,
        qualified_name=qualified_name,
        node=node,
        class_node=class_node,
        methods=methods,
        field_names=field_names,
        cyclomatic=cyclomatic,
        nesting=nesting,
        loc=loc,
        params=params,
        method_count=method_count,
        field_count=field_count,
        risk_band=risk_band,
    )


def _score_entity(
    entity_type: str,
    cyclomatic: int,
    nesting: int,
    loc: int,
    coupling_bonus: int = 0,
    *,
    node: ast.AST | None = None,
    source_snippet: str = "",
) -> float:
    h = 0.0
    if node is not None:
        h = _structural_entropy(node)
    elif source_snippet:
        try:
            h = _structural_entropy(parse_python(source_snippet))
        except SyntaxError:
            h = _textual_entropy(source_snippet) * 0.7
    compress = _compression_ratio(source_snippet) if source_snippet else 2.0
    base = _omega_local(h, cyclomatic, nesting, coupling_bonus, compress)
    if entity_type == "class":
        base = min(100, base * 0.95)
    elif entity_type == "field":
        base = min(100, base * 0.7 + loc * 0.5)
    return round(base, 2)


def analyze_python_entities(
    file_path: str, source: str, tree: ast.AST | None = None
) -> list[EntityMetrics]:
    if tree is None:
        tree = parse_python(source, filename=file_path)
    entities: list[EntityMetrics] = []
    module_name = file_path.replace("/", ".").replace("\\", ".").removesuffix(".py")

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            methods: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
            fields = 0
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append(item)

            field_names_list: list[str] = []
            for m in methods:
                if m.name.startswith("__") and m.name.endswith("__") and m.name != "__init__":
                    continue
                entities.append(_method_entity(file_path, module_name, node.name, m, source))

            fields = _extract_class_fields(
                node, file_path, module_name, source, entities, field_names_list
            )

            cyc, nest = _cyclomatic_nesting_node(node)
            loc = _loc_lines(node)
            qname = f"{module_name}.{node.name}"
            tech, biz = _improvements(
                "class",
                cyclomatic=cyc,
                nesting=nest,
                loc=loc,
                method_count=len(methods),
                field_count=fields,
                name=node.name,
            )
            omega = _score_entity(
                "class",
                cyc,
                nest,
                loc,
                node=node,
                source_snippet=_source_slice(source, node),
            )
            band = _risk_band(omega)
            impl_md, impl_sum, impl_diffs = _attach_implementation(
                entity_type="class",
                file_path=file_path,
                language="python",
                source=source,
                qualified_name=qname,
                risk_band=band,
                cyclomatic=cyc,
                nesting=nest,
                loc=loc,
                method_count=len(methods),
                field_count=fields,
                class_node=node,
                methods=methods,
                field_names=field_names_list,
            )
            entities.append(
                EntityMetrics(
                    entity_type="class",
                    qualified_name=qname,
                    file_path=file_path,
                    line_start=node.lineno or 0,
                    line_end=node.end_lineno or node.lineno or 0,
                    loc=loc,
                    cyclomatic=cyc,
                    nesting_depth=nest,
                    omega_local=omega,
                    risk_band=band,
                    improvement_areas=tech,
                    improvement_areas_business=biz,
                    implementation_plan=impl_md,
                    implementation_summary=impl_sum,
                    implementation_diffs=tuple(impl_diffs),
                    method_count=len(methods),
                    field_count=fields,
                )
            )

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            entities.append(_method_entity(file_path, module_name, None, node, source, is_module_level=True))

    entities.sort(key=lambda e: e.omega_local, reverse=True)
    return entities


def _method_entity(
    file_path: str,
    module: str,
    class_name: str | None,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    source: str,
    *,
    is_module_level: bool = False,
) -> EntityMetrics:
    cyc, nest = _cyclomatic_nesting_node(node)
    loc = _loc_lines(node)
    params = len(node.args.args) + len(node.args.posonlyargs) + len(node.args.kwonlyargs)
    if class_name and not is_module_level:
        qname = f"{module}.{class_name}.{node.name}"
        parent = class_name
        etype = "method"
    else:
        qname = f"{module}.{node.name}"
        parent = None
        etype = "function"
    tech, biz = _improvements(
        etype,
        cyclomatic=cyc,
        nesting=nest,
        loc=loc,
        params=params,
        name=node.name,
    )
    snippet = _source_slice(source, node)
    omega = _score_entity(etype, cyc, nest, loc, node=node, source_snippet=snippet)
    band = _risk_band(omega)
    impl_md, impl_sum, impl_diffs = _attach_implementation(
        entity_type=etype,
        file_path=file_path,
        language="python",
        source=source,
        qualified_name=qname,
        risk_band=band,
        cyclomatic=cyc,
        nesting=nest,
        loc=loc,
        params=params,
        node=node,
    )
    return EntityMetrics(
        entity_type=etype,
        qualified_name=qname,
        file_path=file_path,
        line_start=node.lineno or 0,
        line_end=node.end_lineno or node.lineno or 0,
        loc=loc,
        cyclomatic=cyc,
        nesting_depth=nest,
        omega_local=omega,
        risk_band=band,
        improvement_areas=tech,
        improvement_areas_business=biz,
        implementation_plan=impl_md,
        implementation_summary=impl_sum,
        implementation_diffs=tuple(impl_diffs),
        parent_class=parent,
        parameter_count=params,
    )


def _extract_class_fields(
    class_node: ast.ClassDef,
    file_path: str,
    module: str,
    source: str,
    entities: list[EntityMetrics],
    field_names_out: list[str],
) -> int:
    """Class-level and __init__ self.* fields."""
    seen: set[str] = set()
    count = 0

    def add_field(name: str, node: ast.AST) -> None:
        nonlocal count
        if name in seen or name.startswith("__"):
            return
        seen.add(name)
        field_names_out.append(name)
        count += 1
        entities.append(_field_entity(file_path, module, class_node.name, name, node, source))

    for item in class_node.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            add_field(item.target.id, item)
        elif isinstance(item, ast.Assign):
            for t in item.targets:
                if isinstance(t, ast.Name):
                    add_field(t.id, item)
        elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == "__init__":
            for stmt in ast.walk(item):
                if isinstance(stmt, ast.Assign):
                    for t in stmt.targets:
                        if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name):
                            if t.value.id == "self":
                                add_field(t.attr, stmt)
                elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Attribute):
                    if isinstance(stmt.target.value, ast.Name) and stmt.target.value.id == "self":
                        add_field(stmt.target.attr, stmt)
    return count


def _field_entity(
    file_path: str,
    module: str,
    class_name: str,
    field_name: str,
    node: ast.AST,
    source: str,
) -> EntityMetrics:
    cyc, nest = _cyclomatic_nesting_node(node) if hasattr(node, "body") else (1, 0)
    loc = _loc_lines(node)
    qname = f"{module}.{class_name}.{field_name}"
    tech, biz = _improvements("field", cyclomatic=cyc, nesting=nest, loc=loc, name=field_name)
    snippet = _source_slice(source, node)
    omega = _score_entity("field", cyc, nest, loc, node=node, source_snippet=snippet)
    band = _risk_band(omega)
    impl_md, impl_sum, impl_diffs = _attach_implementation(
        entity_type="field",
        file_path=file_path,
        language="python",
        source=source,
        qualified_name=qname,
        risk_band=band,
        cyclomatic=cyc,
        nesting=nest,
        loc=loc,
        node=node,
    )
    return EntityMetrics(
        entity_type="field",
        qualified_name=qname,
        file_path=file_path,
        line_start=getattr(node, "lineno", 0) or 0,
        line_end=getattr(node, "end_lineno", getattr(node, "lineno", 0)) or 0,
        loc=loc,
        cyclomatic=cyc,
        nesting_depth=nest,
        omega_local=omega,
        risk_band=band,
        improvement_areas=tech,
        improvement_areas_business=biz,
        implementation_plan=impl_md,
        implementation_summary=impl_sum,
        implementation_diffs=tuple(impl_diffs),
        parent_class=class_name,
    )


# --- Heuristic entity extraction (JS, TS, Java, Go, etc.) ---

_CLASS_RE = re.compile(
    r"^\s*(?:export\s+)?(?:abstract\s+)?class\s+(\w+)",
    re.M,
)
_METHOD_RE = re.compile(
    r"^\s*(?:export\s+)?(?:async\s+)?(?:function\s*(\w+)|(\w+)\s*\([^)]*\)\s*\{)",
    re.M,
)
_JAVA_METHOD_RE = re.compile(
    r"^\s*(?:public|private|protected|static|\s)+[\w<>\[\],\s]+\s+(\w+)\s*\([^)]*\)\s*\{",
    re.M,
)
_GO_TYPE_RE = re.compile(r"^\s*type\s+(\w+)\s+struct\b", re.M)
_GO_FUNC_RE = re.compile(r"^\s*func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(", re.M)
_RUST_FN_RE = re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+(\w+)\s*\(", re.M)
_RUST_STRUCT_RE = re.compile(r"^\s*(?:pub\s+)?struct\s+(\w+)\b", re.M)

# Languages with regex symbol extraction + implementation sketches (not full AST).
HEURISTIC_ENTITY_LANGUAGES = frozenset(
    {
        "javascript",
        "typescript",
        "kotlin",
        "csharp",
        "rust",
        "ruby",
        "php",
        "scala",
        "cpp",
        "c",
        "objc",
        "vue",
    }
)


def _line_range(source: str, start_line: int, approx_lines: int) -> tuple[int, int]:
    end = min(len(source.splitlines()), start_line + approx_lines - 1)
    return start_line, end


def _heuristic_entity(
    *,
    entity_type: str,
    file_path: str,
    language: str,
    source: str,
    chunk: str,
    qualified_name: str,
    line_start: int,
    line_end: int,
    loc: int,
    cyclomatic: int,
    nesting: int,
    omega: float,
    tech: tuple[str, ...],
    biz: tuple[str, ...],
    parent_class: str | None = None,
    parameter_count: int = 0,
    method_count: int = 0,
    field_count: int = 0,
) -> EntityMetrics:
    """Build heuristic symbol metrics with repo-context implementation + business text."""
    band = _risk_band(omega)
    return EntityMetrics(
        entity_type=entity_type,
        qualified_name=qualified_name,
        file_path=file_path,
        line_start=line_start,
        line_end=line_end,
        loc=loc,
        cyclomatic=cyclomatic,
        nesting_depth=nesting,
        omega_local=omega,
        risk_band=band,
        improvement_areas=tech,
        improvement_areas_business=biz,
        parent_class=parent_class,
        parameter_count=parameter_count,
        method_count=method_count,
        field_count=field_count,
    )


def analyze_heuristic_entities(file_path: str, source: str, language: str) -> list[EntityMetrics]:
    entities: list[EntityMetrics] = []
    lines = source.splitlines()
    module = file_path

    class_spans: list[tuple[str, int, int]] = []
    for m in _CLASS_RE.finditer(source):
        start = source[: m.start()].count("\n") + 1
        brace_depth = 0
        end_line = start
        for i, line in enumerate(lines[start - 1 :], start=start):
            brace_depth += line.count("{") - line.count("}")
            end_line = i
            if brace_depth <= 0 and "{" in line:
                break
        if end_line <= start:
            end_line = min(start + 30, len(lines))
        class_spans.append((m.group(1), start, end_line))

    for cname, start, end in class_spans:
        chunk = "\n".join(lines[start - 1 : end])
        cyc = len(re.findall(r"\b(if|for|while|switch|case|catch|\?)\b", chunk))
        nest = max((line.count("{") for line in lines[start - 1 : end]), default=0)
        loc = end - start + 1
        methods = len(re.findall(r"\b(function\s+\w+|\w+\s*\([^)]*\)\s*\{)", chunk))
        fields = len(re.findall(r"^\s+\w+\s*[=:]", chunk, re.M))
        tech, biz = _improvements(
            "class", cyclomatic=cyc + 1, nesting=nest, loc=loc,
            method_count=methods, field_count=fields, name=cname,
        )
        omega = _score_entity("class", cyc + 1, nest, loc, source_snippet=chunk)
        entities.append(
            _heuristic_entity(
                entity_type="class",
                file_path=file_path,
                language=language,
                source=source,
                chunk=chunk,
                qualified_name=f"{module}.{cname}",
                line_start=start,
                line_end=end,
                loc=loc,
                cyclomatic=cyc + 1,
                nesting=nest,
                omega=omega,
                tech=tech,
                biz=biz,
                method_count=methods,
                field_count=fields,
            )
        )

    seen_funcs: set[str] = set()

    def _add_function(fname: str, start_line: int, chunk: str, end_line: int) -> None:
        if fname in seen_funcs or fname in ("if", "for", "while", "switch", "catch"):
            return
        seen_funcs.add(fname)
        cyc = len(re.findall(r"\b(if|for|while|else|case|catch)\b", chunk)) + 1
        loc = end_line - start_line + 1
        tech, biz = _improvements("function", cyclomatic=cyc, nesting=2, loc=loc, name=fname)
        omega = _score_entity("function", cyc, 2, loc, source_snippet=chunk)
        entities.append(
            _heuristic_entity(
                entity_type="function",
                file_path=file_path,
                language=language,
                source=source,
                chunk=chunk,
                qualified_name=f"{module}.{fname}",
                line_start=start_line,
                line_end=end_line,
                loc=loc,
                cyclomatic=cyc,
                nesting=2,
                omega=omega,
                tech=tech,
                biz=biz,
            )
        )

    for i, line in enumerate(lines, start=1):
        patterns = [
            r"^\s*(?:(?:export\s+)?(?:default\s+)?)?(?:async\s+)?function\s+(\w+)",
            r"^\s*(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>",
            r"^\s*(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?function\s*\(",
        ]
        fname: str | None = None
        for pat in patterns:
            m = re.match(pat, line)
            if m:
                fname = m.group(1)
                break
        if not fname:
            if re.match(
                r"^\s*(?:(?:export|default)\s+)?(?:async\s+)?function\s+\w+|\w+\s*\([^)]*\)\s*\{",
                line,
            ):
                name_m = re.search(r"(?:function\s+)?(\w+)\s*\(", line)
                if name_m:
                    fname = name_m.group(1)
        if not fname:
            continue
        end = min(i + 80, len(lines))
        chunk = "\n".join(lines[i - 1 : end])
        _add_function(fname, i, chunk, end)

    if language == "go":
        for m in _GO_TYPE_RE.finditer(source):
            start = source[: m.start()].count("\n") + 1
            tname = m.group(1)
            end = min(start + 40, len(lines))
            chunk = "\n".join(lines[start - 1 : end])
            cyc = len(re.findall(r"\b(if|for|range|switch|case)\b", chunk)) + 1
            loc = end - start + 1
            tech, biz = _improvements(
                "class", cyclomatic=cyc, nesting=2, loc=loc, name=tname, method_count=3
            )
            omega = _score_entity("class", cyc, 2, loc, source_snippet=chunk)
            entities.append(
                _heuristic_entity(
                    entity_type="class",
                    file_path=file_path,
                    language=language,
                    source=source,
                    chunk=chunk,
                    qualified_name=f"{module}.{tname}",
                    line_start=start,
                    line_end=end,
                    loc=loc,
                    cyclomatic=cyc,
                    nesting=2,
                    omega=omega,
                    tech=tech,
                    biz=biz,
                )
            )
        for m in _GO_FUNC_RE.finditer(source):
            start = source[: m.start()].count("\n") + 1
            fname = m.group(1)
            if fname in ("if", "for", "switch"):
                continue
            end = min(start + 45, len(lines))
            chunk = "\n".join(lines[start - 1 : end])
            cyc = len(re.findall(r"\b(if|for|range|switch|case)\b", chunk)) + 1
            loc = end - start + 1
            tech, biz = _improvements("function", cyclomatic=cyc, nesting=2, loc=loc, name=fname)
            omega = _score_entity("function", cyc, 2, loc, source_snippet=chunk)
            entities.append(
                _heuristic_entity(
                    entity_type="function",
                    file_path=file_path,
                    language=language,
                    source=source,
                    chunk=chunk,
                    qualified_name=f"{module}.{fname}",
                    line_start=start,
                    line_end=end,
                    loc=loc,
                    cyclomatic=cyc,
                    nesting=2,
                    omega=omega,
                    tech=tech,
                    biz=biz,
                )
            )

    if language == "rust":
        for m in _RUST_STRUCT_RE.finditer(source):
            start = source[: m.start()].count("\n") + 1
            sname = m.group(1)
            end = min(start + 40, len(lines))
            chunk = "\n".join(lines[start - 1 : end])
            cyc = len(re.findall(r"\b(if|for|while|match|loop)\b", chunk)) + 1
            loc = end - start + 1
            tech, biz = _improvements("class", cyclomatic=cyc, nesting=2, loc=loc, name=sname)
            omega = _score_entity("class", cyc, 2, loc, source_snippet=chunk)
            entities.append(
                _heuristic_entity(
                    entity_type="class",
                    file_path=file_path,
                    language=language,
                    source=source,
                    chunk=chunk,
                    qualified_name=f"{module}.{sname}",
                    line_start=start,
                    line_end=end,
                    loc=loc,
                    cyclomatic=cyc,
                    nesting=2,
                    omega=omega,
                    tech=tech,
                    biz=biz,
                )
            )
        for m in _RUST_FN_RE.finditer(source):
            start = source[: m.start()].count("\n") + 1
            fname = m.group(1)
            end = min(start + 45, len(lines))
            chunk = "\n".join(lines[start - 1 : end])
            cyc = len(re.findall(r"\b(if|for|while|match|loop)\b", chunk)) + 1
            loc = end - start + 1
            tech, biz = _improvements("function", cyclomatic=cyc, nesting=2, loc=loc, name=fname)
            omega = _score_entity("function", cyc, 2, loc, source_snippet=chunk)
            entities.append(
                _heuristic_entity(
                    entity_type="function",
                    file_path=file_path,
                    language=language,
                    source=source,
                    chunk=chunk,
                    qualified_name=f"{module}.{fname}",
                    line_start=start,
                    line_end=end,
                    loc=loc,
                    cyclomatic=cyc,
                    nesting=2,
                    omega=omega,
                    tech=tech,
                    biz=biz,
                )
            )

    if language in ("java", "kotlin", "csharp"):
        seen_methods: set[str] = set()
        for m in _JAVA_METHOD_RE.finditer(source):
            start = source[: m.start()].count("\n") + 1
            fname = m.group(1)
            if fname in ("if", "for", "while", "class", "interface") or fname in seen_methods:
                continue
            seen_methods.add(fname)
            end = min(start + 35, len(lines))
            chunk = "\n".join(lines[start - 1 : end])
            cyc = len(re.findall(r"\b(if|for|while|catch|switch)\b", chunk)) + 1
            loc = end - start + 1
            tech, biz = _improvements("method", cyclomatic=cyc, nesting=2, loc=loc, name=fname)
            omega = _score_entity("method", cyc, 2, loc, source_snippet=chunk)
            entities.append(
                _heuristic_entity(
                    entity_type="method",
                    file_path=file_path,
                    language=language,
                    source=source,
                    chunk=chunk,
                    qualified_name=f"{module}.{fname}",
                    line_start=start,
                    line_end=end,
                    loc=loc,
                    cyclomatic=cyc,
                    nesting=2,
                    omega=omega,
                    tech=tech,
                    biz=biz,
                )
            )

    cap = max_entities_per_file()
    if len(entities) > cap:
        entities.sort(key=lambda e: e.omega_local, reverse=True)
        entities = entities[:cap]
    return entities


def enrich_implementation_plans(
    entities: list[EntityMetrics],
    source_by_path: dict[str, str],
    *,
    max_entities: int | None = None,
) -> list[EntityMetrics]:
    """
    Attach implementation plans only to the top-N riskiest symbols (deferred for speed).
    Symbols that already have plans (e.g. Python AST) are left unchanged.
    """
    limit = impl_plan_max_entities() if max_entities is None else max_entities
    if limit <= 0:
        return entities

    candidates = [
        e
        for e in entities
        if not e.implementation_plan
        and e.risk_band in ("CRITICAL", "HIGH", "MEDIUM")
    ]
    candidates.sort(key=lambda e: (-e.omega_local, e.qualified_name))
    enrich_names = {e.qualified_name for e in candidates[:limit]}

    out: list[EntityMetrics] = []
    for e in entities:
        if e.qualified_name not in enrich_names:
            out.append(e)
            continue
        src = source_by_path.get(e.file_path, "")
        impl_md, impl_sum, impl_diffs = build_implementation_plan(
            entity_type=e.entity_type,
            file_path=e.file_path,
            language=_language_for_path(e.file_path),
            source=src,
            qualified_name=e.qualified_name,
            cyclomatic=e.cyclomatic,
            nesting=e.nesting_depth,
            loc=e.loc,
            params=e.parameter_count,
            method_count=e.method_count,
            field_count=e.field_count,
            risk_band=e.risk_band,
            line_start=e.line_start,
            line_end=e.line_end,
        )
        out.append(
            replace(
                e,
                implementation_plan=impl_md,
                implementation_summary=impl_sum,
                implementation_diffs=tuple(impl_diffs),
            )
        )
    return out


def _language_for_path(file_path: str) -> str:
    low = file_path.lower()
    if low.endswith(".java"):
        return "java"
    if low.endswith(".py"):
        return "python"
    if low.endswith(".go"):
        return "go"
    if low.endswith((".ts", ".tsx")):
        return "typescript"
    if low.endswith((".js", ".jsx")):
        return "javascript"
    if low.endswith(".kt"):
        return "kotlin"
    if low.endswith(".rs"):
        return "rust"
    if low.endswith(".cs"):
        return "csharp"
    return "unknown"


def analyze_file_entities(file_path: str, source: str, language: str) -> list[EntityMetrics]:
    if language == "python":
        try:
            return analyze_python_entities(file_path, source)
        except SyntaxError:
            return analyze_heuristic_entities(file_path, source, language)
    if language in ("java", "go"):
        from omega.ast_tree_sitter import parse_tree
        from omega.entities_ts import analyze_ts_entities

        tree = parse_tree(language, source)
        if tree is not None:
            try:
                return analyze_ts_entities(file_path, source, language, tree)
            except ValueError:
                pass
        return analyze_heuristic_entities(file_path, source, language)
    if language in HEURISTIC_ENTITY_LANGUAGES:
        return analyze_heuristic_entities(file_path, source, language)
    return []
