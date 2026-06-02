"""Entity-level AST analysis for Java and Go via tree-sitter."""

from __future__ import annotations

from omega.ast_tree_sitter import _cyclomatic, _max_nesting, _walk, parse_tree
from omega.entities import EntityMetrics, _improvements, _risk_band, _score_entity


def _node_text(source: str, node) -> str:
    return source.encode("utf-8")[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _line_range(node) -> tuple[int, int]:
    return node.start_point[0] + 1, node.end_point[0] + 1


def _loc_lines(node) -> int:
    return max(1, node.end_point[0] - node.start_point[0] + 1)


def _entity_block(
    *,
    entity_type: str,
    file_path: str,
    language: str,
    source: str,
    qualified_name: str,
    node,
    parent_class: str | None = None,
    parameter_count: int = 0,
    method_count: int = 0,
    field_count: int = 0,
) -> EntityMetrics:
    snippet = _node_text(source, node)
    cyc = _cyclomatic(node, language)
    nest = _max_nesting(node)
    loc = _loc_lines(node)
    line_start, line_end = _line_range(node)
    name = qualified_name.split(".")[-1]
    tech, biz = _improvements(
        entity_type,
        cyclomatic=cyc,
        nesting=nest,
        loc=loc,
        params=parameter_count,
        method_count=method_count,
        field_count=field_count,
        name=name,
    )
    omega = _score_entity(
        entity_type,
        cyc,
        nest,
        loc,
        source_snippet=snippet,
    )
    band = _risk_band(omega)
    return EntityMetrics(
        entity_type=entity_type,
        qualified_name=qualified_name,
        file_path=file_path,
        line_start=line_start,
        line_end=line_end,
        loc=loc,
        cyclomatic=cyc,
        nesting_depth=nest,
        omega_local=omega,
        risk_band=band,
        improvement_areas=tech,
        improvement_areas_business=biz,
        parent_class=parent_class,
        parameter_count=parameter_count,
        method_count=method_count,
        field_count=field_count,
    )


def _param_count_java(node) -> int:
    params = node.child_by_field_name("parameters")
    if params is None:
        return 0
    return sum(1 for c in params.children if c.type == "formal_parameter")


def _param_count_go(node) -> int:
    params = node.child_by_field_name("parameters")
    if params is None:
        return 0
    n = 0
    for c in params.children:
        if c.type in ("parameter_declaration", "variadic_parameter_declaration"):
            n += 1
    return n


def analyze_java_entities(file_path: str, source: str, tree) -> list[EntityMetrics]:
    entities: list[EntityMetrics] = []
    pkg = ""
    for n in tree.root_node.children:
        if n.type == "package_declaration":
            for c in n.children:
                if c.type == "identifier" and c.text:
                    pkg = c.text.decode("utf-8", errors="replace")
                    break

    for node in _walk(tree.root_node):
        if node.type != "class_declaration":
            continue
        name_node = node.child_by_field_name("name")
        if name_node is None or not name_node.text:
            continue
        cname = name_node.text.decode("utf-8", errors="replace")
        qname = f"{pkg}.{cname}" if pkg else f"{file_path}.{cname}"
        body = node.child_by_field_name("body")
        methods = 0
        fields = 0
        if body:
            for ch in body.children:
                if ch.type == "method_declaration":
                    methods += 1
                elif ch.type == "field_declaration":
                    fields += 1

        entities.append(
            _entity_block(
                entity_type="class",
                file_path=file_path,
                language="java",
                source=source,
                qualified_name=qname,
                node=node,
                method_count=methods,
                field_count=fields,
            )
        )

        if body:
            for ch in body.children:
                if ch.type == "method_declaration":
                    mname = ch.child_by_field_name("name")
                    if mname is None or not mname.text:
                        continue
                    mn = mname.text.decode("utf-8", errors="replace")
                    entities.append(
                        _entity_block(
                            entity_type="method",
                            file_path=file_path,
                            language="java",
                            source=source,
                            qualified_name=f"{qname}.{mn}",
                            node=ch,
                            parent_class=cname,
                            parameter_count=_param_count_java(ch),
                        )
                    )
                elif ch.type == "field_declaration":
                    for v in ch.children:
                        if v.type == "variable_declarator":
                            vn = v.child_by_field_name("name")
                            if vn and vn.text:
                                fn = vn.text.decode("utf-8", errors="replace")
                                entities.append(
                                    _entity_block(
                                        entity_type="field",
                                        file_path=file_path,
                                        language="java",
                                        source=source,
                                        qualified_name=f"{qname}.{fn}",
                                        node=v,
                                        parent_class=cname,
                                    )
                                )

    return entities


def analyze_go_entities(file_path: str, source: str, tree) -> list[EntityMetrics]:
    entities: list[EntityMetrics] = []
    pkg = ""
    for n in tree.root_node.children:
        if n.type == "package_clause":
            for c in n.children:
                if c.type == "package_identifier" and c.text:
                    pkg = c.text.decode("utf-8", errors="replace")
                    break

    for node in _walk(tree.root_node):
        if node.type == "type_declaration":
            for spec in node.children:
                if spec.type != "type_spec":
                    continue
                name_node = spec.child_by_field_name("name")
                if name_node is None or not name_node.text:
                    continue
                tname = name_node.text.decode("utf-8", errors="replace")
                if not any(c.type == "struct_type" for c in spec.children):
                    continue
                qname = f"{pkg}.{tname}" if pkg else f"{file_path}.{tname}"
                methods = sum(
                    1
                    for m in _walk(tree.root_node)
                    if m.type == "method_declaration"
                    and m.child_by_field_name("receiver")
                    and _go_method_type_name(m) == tname
                )
                entities.append(
                    _entity_block(
                        entity_type="class",
                        file_path=file_path,
                        language="go",
                        source=source,
                        qualified_name=qname,
                        node=spec,
                        method_count=methods,
                    )
                )

        elif node.type == "function_declaration":
            name_node = node.child_by_field_name("name")
            if name_node is None or not name_node.text:
                continue
            fname = name_node.text.decode("utf-8", errors="replace")
            qname = f"{pkg}.{fname}" if pkg else f"{file_path}.{fname}"
            entities.append(
                _entity_block(
                    entity_type="function",
                    file_path=file_path,
                    language="go",
                    source=source,
                    qualified_name=qname,
                    node=node,
                    parameter_count=_param_count_go(node),
                )
            )

        elif node.type == "method_declaration":
            recv = node.child_by_field_name("receiver")
            name_node = node.child_by_field_name("name")
            if name_node is None or not name_node.text:
                continue
            mn = name_node.text.decode("utf-8", errors="replace")
            tname = _go_method_type_name(node) if recv else ""
            qname = f"{pkg}.{tname}.{mn}" if pkg and tname else f"{file_path}.{mn}"
            entities.append(
                _entity_block(
                    entity_type="method",
                    file_path=file_path,
                    language="go",
                    source=source,
                    qualified_name=qname,
                    node=node,
                    parent_class=tname or None,
                    parameter_count=_param_count_go(node),
                )
            )

    return entities


def _go_method_type_name(method_node) -> str:
    recv = method_node.child_by_field_name("receiver")
    if recv is None:
        return ""
    for c in recv.children:
        if c.type == "parameter_declaration":
            for t in c.children:
                if t.type == "type_identifier" and t.text:
                    return t.text.decode("utf-8", errors="replace")
                if t.type == "pointer_type":
                    for inner in t.children:
                        if inner.type == "type_identifier" and inner.text:
                            return inner.text.decode("utf-8", errors="replace")
    return ""


def analyze_ts_entities(file_path: str, source: str, language: str, tree) -> list[EntityMetrics]:
    if language == "java":
        return analyze_java_entities(file_path, source, tree)
    if language == "go":
        return analyze_go_entities(file_path, source, tree)
    return []


def analyze_ts_entities_from_source(
    file_path: str, source: str, language: str
) -> list[EntityMetrics]:
    tree = parse_tree(language, source)
    if tree is None:
        return []
    try:
        return analyze_ts_entities(file_path, source, language, tree)
    except ValueError:
        return []
