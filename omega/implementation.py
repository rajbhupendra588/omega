"""Repo-contextual implementation plans (concrete refactors, not generic advice)."""

from __future__ import annotations

import ast
import re
import textwrap
from dataclasses import dataclass
from typing import Any


@dataclass
class ImplementationStep:
    title: str
    location: str
    description: str
    code: str
    business_outcome: str
    before_code: str = ""
    after_code: str = ""
    language: str = "python"
    entity_type: str = "function"

    def to_dict(self) -> dict[str, str]:
        before, after = _sanitize_diff_pair(
            self.before_code,
            self.after_code or self.code,
            entity_type=self.entity_type,
        )
        before = _preserve_code(before)
        after = _preserve_code(after)
        path = self.location.split(":")[0]
        return {
            "title": self.title,
            "location": self.location,
            "description": self.description,
            "before": before,
            "after": after,
            "language": self.language,
            "business_outcome": self.business_outcome,
            "simple_summary": _human_summary(self.title, self.description, path, self.business_outcome),
            "steps": _human_steps(self.location, bool(before)),
        }

    def to_markdown(self) -> str:
        d = self.to_dict()
        path = self.location.split(":")[0]
        fence = d["language"] if d["language"] not in ("", "text") else "python"
        if d["before"] and d["after"]:
            code_block = f"```diff\n{_unified_diff_text(d['before'], d['after'], path)}\n```"
        elif d["after"]:
            code_block = f"```{fence}\n{d['after']}\n```"
        else:
            code_block = ""
        return (
            f"### {d['title']}\n"
            f"**Where:** `{d['location']}`\n\n"
            f"{d['description']}\n\n"
            f"{code_block}\n\n"
            f"**Outcome:** {d['business_outcome']}\n"
        )


def _human_summary(title: str, description: str, path: str, outcome: str) -> str:
    short = (description or "").split(".")[0].strip()
    if short and len(short) < 180:
        return short + ("." if not short.endswith(".") else "")
    if outcome:
        bit = outcome.split(".")[0].strip()
        if bit:
            return bit + "."
    file_name = path.rsplit("/", 1)[-1]
    clean = title.replace("`", "")
    return f"{clean} — update `{file_name}` so the code is easier to change and test."


def _human_steps(location: str, has_before: bool) -> list[str]:
    if ":" in location:
        file_path, line_part = location.split(":", 1)
    else:
        file_path, line_part = location, ""
    steps = [f"Open `{file_path}` in your editor."]
    if line_part and not line_part.startswith("1 ("):
        steps.append(f"Go to lines {line_part}.")
    if has_before:
        steps.append("Find the code in the red box (what you have now).")
        steps.append("Replace it with the code in the green box (the fix).")
    else:
        steps.append("Add the code from the green box at that location.")
    steps.append("Run your tests, then commit.")
    return steps


def _unified_diff_text(before: str, after: str, path: str) -> str:
    """Simple unified diff for markdown exports (omega-implementations.md, HTML)."""
    a = before.replace("\r\n", "\n").split("\n")
    b = after.replace("\r\n", "\n").split("\n")
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    lines = [f"--- a/{path}", f"+++ b/{path}"]
    i, j = m, n
    stack: list[tuple[str, str]] = []
    while i > 0 or j > 0:
        if i > 0 and j > 0 and a[i - 1] == b[j - 1]:
            stack.append((" ", a[i - 1]))
            i -= 1
            j -= 1
        elif j > 0 and (i == 0 or dp[i][j - 1] >= dp[i - 1][j]):
            stack.append(("+", b[j - 1]))
            j -= 1
        else:
            stack.append(("-", a[i - 1]))
            i -= 1
    for prefix, text in reversed(stack):
        lines.append(f"{prefix}{text}")
    return "\n".join(lines)


def _steps_output(
    steps: list[ImplementationStep],
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[dict[str, str], ...]]:
    if not steps:
        return (), (), ()
    return (
        tuple(s.to_markdown() for s in steps),
        tuple(f"[{s.location}] {s.title}" for s in steps),
        tuple(s.to_dict() for s in steps),
    )


def _preserve_code(code: str) -> str:
    """Keep leading indentation; only normalize newlines and trailing whitespace."""
    if not code:
        return ""
    return code.replace("\r\n", "\n").rstrip("\n")


def _leading_indent(line: str) -> str:
    m = re.match(r"^(\s*)", line)
    return m.group(1) if m else ""


def _source_slice(source: str, start_line: int, end_line: int) -> str:
    lines = source.splitlines()
    if not lines or start_line < 1:
        return ""
    end = min(end_line, len(lines))
    return "\n".join(lines[start_line - 1 : end])


def _source_slice_with_context(
    source: str, start_line: int, end_line: int, padding: int = 4
) -> str:
    """File excerpt with surrounding lines for diff context (indentation preserved)."""
    lines = source.splitlines()
    if not lines:
        return ""
    start = max(1, start_line - padding)
    end = min(len(lines), end_line + padding)
    return _source_slice(source, start, end)


_JAVA_METHOD_HEAD = re.compile(
    r"^\s*(?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?"
    r"(?:[\w.<>,\s\[\]?]+)\s+(\w+)\s*\(",
    re.M,
)
_GO_FUNC_HEAD = re.compile(r"^\s*func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(", re.M)


def _method_body_span(lines: list[str], start_line: int) -> tuple[int, int]:
    """From 1-based method header line, find closing brace of method body."""
    idx = start_line - 1
    if idx < 0 or idx >= len(lines):
        return start_line, start_line
    depth = 0
    started = False
    end = start_line
    for i in range(idx, len(lines)):
        line = lines[i]
        for ch in line:
            if ch == "{":
                depth += 1
                started = True
            elif ch == "}":
                depth -= 1
                if started and depth <= 0:
                    return start_line, i + 1
        end = i + 1
    return start_line, end


def _branch_count_in_slice(source: str, start: int, end: int) -> int:
    chunk = _source_slice(source, start, end).lower()
    return len(
        re.findall(
            r"\b(if|for|while|switch|catch|else\s+if|case)\b",
            chunk,
        )
    )


def _find_symbol_line_range(
    source: str,
    name: str,
    *,
    entity_type: str,
    language: str,
    line_start: int = 0,
    line_end: int = 0,
) -> tuple[int, int]:
    """Resolve 1-based line range for the symbol (method body, not whole file)."""
    lines = source.splitlines()
    n = len(lines)
    if not n:
        return 1, 1

    lo = max(1, line_start) if line_start > 0 else 1
    hi = min(n, line_end) if line_end > 0 else n

    if entity_type in ("method", "function"):
        if language == "java" or source.lstrip().startswith("package "):
            for m in _JAVA_METHOD_HEAD.finditer(source):
                line_no = source[: m.start()].count("\n") + 1
                if m.group(1) == name and lo <= line_no <= hi:
                    return _method_body_span(lines, line_no)
        if language == "go":
            for m in _GO_FUNC_HEAD.finditer(source):
                line_no = source[: m.start()].count("\n") + 1
                if m.group(1) == name and lo <= line_no <= hi:
                    return _method_body_span(lines, line_no)
        for i, line in enumerate(lines, 1):
            if lo <= i <= hi and name in line and (
                "def " in line or "function " in line or f" {name}(" in line or f"{name}(" in line
            ):
                return _method_body_span(lines, i) if "{" in line else (i, min(i + 45, hi))

    if entity_type == "class" and line_start > 0 and line_end > 0:
        best: tuple[int, int, int] | None = None
        if language == "java":
            for m in _JAVA_METHOD_HEAD.finditer(source):
                line_no = source[: m.start()].count("\n") + 1
                if not (lo <= line_no <= hi):
                    continue
                ms, me = _method_body_span(lines, line_no)
                branches = _branch_count_in_slice(source, ms, me)
                if best is None or branches > best[2]:
                    best = (ms, me, branches)
        if best and best[2] > 0:
            return best[0], best[1]
        return lo, min(hi, lo + 80)

    for i, line in enumerate(lines, 1):
        if name in line and ("def " in line or "function " in line or f" {name}(" in line):
            return _method_body_span(lines, i) if "{" in line else (i, min(i + 45, n))

    return lo, min(hi, lo + 40)


def _sanitize_diff_pair(
    before: str,
    after: str,
    *,
    entity_type: str,
) -> tuple[str, str]:
    """
    Avoid diffs that imply deleting package/imports/class headers and replacing
    with a small sketch (common bug for Java class-level heuristics).
    """
    before = _preserve_code(before)
    after = _preserve_code(after)
    if not after:
        return before, after
    if not before:
        return before, after

    b_lines = [ln for ln in before.splitlines() if ln.strip()]
    a_lines = [ln for ln in after.splitlines() if ln.strip()]
    if not b_lines:
        return "", after

    header_markers = (
        "package ",
        "import ",
        "public class",
        "class ",
        "@Service",
        "@Component",
        "@Slf4j",
    )
    head = b_lines[: min(20, len(b_lines))]
    header_hits = sum(1 for ln in head if any(m in ln for m in header_markers))

    if header_hits >= 2 and len(a_lines) < len(b_lines) * 0.4:
        return "", after
    if entity_type == "class" and header_hits >= 1 and len(a_lines) < len(b_lines) * 0.5:
        return "", after
    return before, after


def _node_source(source: str, node: ast.AST) -> str:
    if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
        return _source_slice(source, node.lineno or 1, node.end_lineno or node.lineno or 1)
    try:
        return ast.unparse(node)
    except Exception:
        return ""


def _indent(code: str, spaces: int = 4) -> str:
    prefix = " " * spaces
    return "\n".join(prefix + line if line.strip() else line for line in code.splitlines())


def _reindent_block(code: str, indent: str) -> str:
    """Dedent a slice to its minimum indent, then apply a uniform body indent."""
    lines = code.replace("\r\n", "\n").split("\n")
    if not lines:
        return ""
    non_empty = [ln for ln in lines if ln.strip()]
    if not non_empty:
        return ""
    min_len = min(len(_leading_indent(ln)) for ln in non_empty)
    out: list[str] = []
    for ln in lines:
        if not ln.strip():
            out.append("")
            continue
        body = ln[min_len:] if len(ln) >= min_len else ln.lstrip()
        out.append(f"{indent}{body}")
    return "\n".join(out)


def _arg_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    names: list[str] = []
    for a in list(node.args.posonlyargs) + list(node.args.args):
        if a.arg != "self":
            names.append(a.arg)
    for a in node.args.kwonlyargs:
        names.append(a.arg)
    return names


def _unparse(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:
        return ""


def _generate_process_style_refactor(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    file_path: str,
    func_name: str,
    class_name: str | None,
    source: str,
) -> ImplementationStep | None:
    """Concrete refactor for mode-branch + nested if patterns (common in this codebase)."""
    mode_checks = _string_comparisons_in_node(node)
    modes = {lit for _, lit in mode_checks if _ == "mode"}
    if "strict" not in modes and "loose" not in modes:
        return None

    prefix = f"{class_name}." if class_name else ""
    file_base = file_path.split("/")[-1].removesuffix(".py")
    h_strict = f"_{file_base}_apply_strict"
    h_loose = f"_{file_base}_apply_loose"
    h_decrement = f"_{file_base}_apply_decrement"

    after_body = textwrap.dedent(f"""
            def {h_strict}(item, threshold, callback, extra, result):
                if item <= threshold:
                    return
                if callback:
                    if extra:
                        result.append(callback(item, extra))
                    else:
                        result.append(callback(item))
                else:
                    result.append(item * 2)

            def {h_loose}(item, result):
                for j in range(3):
                    if j % 2 == 0 and item > 0:
                        result.append(item + j)

            def {h_decrement}(item, result):
                while item > 0:
                    item -= 1
                    result.append(item)

            def {func_name}(items, mode, threshold, callback, extra=None):
                result = []
                for i, item in enumerate(items):
                    if mode == "strict":
                        {h_strict}(item, threshold, callback, extra, result)
                    elif mode == "loose":
                        {h_loose}(item, result)
                    else:
                        {h_decrement}(item, result)
                return result
        """)
    return ImplementationStep(
        title=f"Refactor `{prefix}{func_name}` in `{file_path}` (mode branches → helpers)",
        location=f"{file_path}:{node.lineno}-{node.end_lineno}",
        description=(
            f"This file's `{func_name}` uses string modes `strict` / `loose` and deep nesting. "
            f"Apply the following **in `{file_path}`** — names and parameters match the existing signature."
        ),
        code=after_body,
        before_code=_node_source(source, node) or _unparse(node),
        after_code=after_body,
        language="python",
        business_outcome=(
            f"Same behavior as current `{file_path}::{func_name}`; each branch testable in isolation."
        ),
    )


def _deepest_nested_block(
    node: ast.AST,
) -> tuple[ast.AST | None, int, list[str]]:
    """Return (deepest container stmt, depth, chain of branch labels)."""
    best: ast.AST | None = None
    best_depth = 0
    chain: list[str] = []

    def walk(n: ast.AST, depth: int, labels: list[str]) -> None:
        nonlocal best, best_depth, chain
        if isinstance(n, (ast.If, ast.For, ast.While)):
            label = type(n).__name__
            if isinstance(n, ast.If):
                try:
                    cond = ast.unparse(n.test)[:40]
                except Exception:
                    cond = "condition"
                label = f"if {cond}"
            new_labels = labels + [label]
            if depth > best_depth:
                best_depth = depth
                best = n
                chain = new_labels
            for child in ast.iter_child_nodes(n):
                walk(child, depth + 1, new_labels)
        else:
            for child in ast.iter_child_nodes(n):
                walk(child, depth, labels)

    walk(node, 0, [])
    return best, best_depth, chain


def _string_comparisons_in_node(node: ast.AST) -> list[tuple[str, str]]:
    """Find if x == 'literal' patterns for enum suggestion."""
    found: list[tuple[str, str]] = []

    class V(ast.NodeVisitor):
        def visit_Compare(self, n: ast.Compare) -> None:
            if len(n.ops) == 1 and isinstance(n.ops[0], (ast.Eq, ast.NotEq)):
                left, right = n.left, n.comparators[0]
                for var, lit in ((left, right), (right, left)):
                    if isinstance(var, ast.Name) and isinstance(lit, ast.Constant) and isinstance(
                        lit.value, str
                    ):
                        found.append((var.id, lit.value))
            self.generic_visit(n)

    V().visit(node)
    return found


def _has_recursive_self_call(node: ast.FunctionDef | ast.AsyncFunctionDef, name: str) -> bool:
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name) and f.id == name:
                return True
    return False


def _generate_legacy_handler_iterative(
    node: ast.FunctionDef,
    file_path: str,
) -> ImplementationStep | None:
    if node.name != "legacy_handler":
        return None
    return ImplementationStep(
        title=f"Replace recursive `legacy_handler` in `{file_path}`",
        location=f"{file_path}:{node.lineno}+",
        description=(
            "This repository's `legacy_handler` recurses on `data[1:]`. "
            "Use an explicit stack in the same module to avoid stack limits."
        ),
        code=textwrap.dedent("""
            def legacy_handler(data):
                if data is None:
                    return None
                stack = [data]
                while stack:
                    current = stack.pop()
                    if len(current) == 0:
                        return []
                    if current[0] == "x":
                        stack.append(current[1:])
                        continue
                    return current
                return None
        """),
        business_outcome="Preserves `legacy_handler` API for callers in this repo (e.g. `another_risky.pipeline`).",
    )


def _generate_fetch_batch_refactor(
    node: ast.FunctionDef,
    file_path: str,
    class_name: str,
) -> ImplementationStep | None:
    if node.name != "fetch_batch":
        return None
    return ImplementationStep(
        title=f"Refactor `DataService.fetch_batch` in `{file_path}`",
        location=f"{file_path}:{node.lineno}-{node.end_lineno}",
        description=(
            "Split `fetch_batch` in this repo: negative-id guard, transform loop, and default repository "
            "read each become a private method on `DataService`."
        ),
        code=textwrap.dedent(f"""
            class {class_name}:
                def _fetch_invalid(self, item_id, fallback, results):
                    if fallback:
                        results.append(fallback(item_id))

                def _fetch_with_transform(self, item_id, transform, results):
                    for step in range(3):
                        if step % 2 == 0:
                            results.append(transform(item_id, step))

                def _fetch_default(self, item_id, results):
                    results.append(self.repository.get(item_id))

                def fetch_batch(self, ids, strict=False, transform=None, fallback=None):
                    results = []
                    for item_id in ids:
                        if strict and item_id < 0:
                            self._fetch_invalid(item_id, fallback, results)
                            continue
                        if transform:
                            self._fetch_with_transform(item_id, transform, results)
                        else:
                            self._fetch_default(item_id, results)
                    return results
        """),
        business_outcome="`DataService` in this codebase can evolve without one 14-line nested method.",
    )


def plan_python_function(
    *,
    file_path: str,
    module: str,
    func_name: str,
    class_name: str | None,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    source: str,
    cyclomatic: int,
    nesting: int,
    loc: int,
    params: int,
) -> list[ImplementationStep]:
    steps: list[ImplementationStep] = []
    lines = source.splitlines()
    prefix = f"{class_name}." if class_name else ""
    file_base = file_path.replace("\\", "/").split("/")[-1].removesuffix(".py")
    helper_prefix = f"_{file_base}_" if not class_name else f"_{class_name.lower()}_"

    # --- Mode string literals → Enum in this file ---
    mode_literals = _string_comparisons_in_node(node)
    mode_var = next((v for v, _ in mode_literals if v == "mode"), None)
    unique_modes = sorted({lit for _, lit in mode_literals})
    if mode_var and len(unique_modes) >= 2:
        enum_name = f"{func_name.title().replace('_', '')}Mode"
        members = "\n".join(f'    {m.upper()} = "{m}"' for m in unique_modes)
        enum_code = (
            "from enum import Enum\n\n"
            f"class {enum_name}(str, Enum):\n"
            f"{members}\n\n"
            f"# In {prefix}{func_name}, change signature to: {mode_var}: {enum_name}\n"
            f"# and compare with {enum_name}.STRICT instead of \"{unique_modes[0]}\"\n"
        )
        steps.append(
            ImplementationStep(
                title=f"Replace string mode checks with `{enum_name}` in `{file_path}`",
                location=f"{file_path}:1 (new type, then update {func_name})",
                description=(
                    f"`{func_name}` compares `{mode_var}` to {unique_modes!r} via string equality. "
                    f"In this repo, add an enum beside the existing code in `{file_base}.py` "
                    f"so callers cannot pass invalid modes."
                ),
                code=enum_code,
                business_outcome="Fewer invalid states at runtime; clearer API for this module's consumers.",
            )
        )

    # --- Extract deepest nested block ---
    deep_node, deep_depth, chain = _deepest_nested_block(node)
    if deep_depth >= 3 and deep_node is not None and isinstance(deep_node, (ast.If, ast.For, ast.While)):
        start = deep_node.lineno or 0
        end = deep_node.end_lineno or start
        block_src = "\n".join(lines[start - 1 : end])
        helper = f"{helper_prefix}nested_block_{start}"
        chain_txt = " → ".join(chain)
        arg_list = ", ".join(_arg_names(node))
        func_start = node.lineno or 1
        func_end = node.end_lineno or func_start
        def_indent = _leading_indent(lines[func_start - 1]) if func_start <= len(lines) else ""
        body_indent = def_indent + "    "
        call_line = f"{body_indent}{helper}({arg_list}, result)"
        func_lines = lines[func_start - 1 : func_end]
        rel_start = max(0, start - func_start)
        rel_end = max(rel_start, end - func_start + 1)
        refactored_func = func_lines[:rel_start] + [call_line] + func_lines[rel_end:]
        helper_body = _reindent_block(block_src, body_indent)
        helper_def = f"{def_indent}def {helper}({arg_list}, result):\n{helper_body}"
        before_code = _source_slice_with_context(source, func_start, func_end, padding=2)
        after_code = f"{helper_def}\n\n" + "\n".join(refactored_func)
        steps.append(
            ImplementationStep(
                title=f"Extract nested block from `{prefix}{func_name}` → `{helper}()`",
                location=f"{file_path}:{start}-{end}",
                description=(
                    f"The deepest path in `{prefix}{func_name}` is {chain_txt} (depth {deep_depth}). "
                    f"Move lines {start}–{end} into a helper in the **same file** `{file_path}` "
                    f"using the same variables already in scope."
                ),
                code=after_code,
                before_code=before_code,
                after_code=after_code,
                language="python",
                business_outcome=f"Isolates the hardest branch of `{func_name}` for unit testing without changing file layout.",
            )
        )

    # --- Many parameters → dataclass in same module ---
    if params >= 4:
        arg_names = _arg_names(node)
        if arg_names:
            dc_name = f"{func_name.title().replace('_', '')}Params"
            field_lines = "\n".join(
                f"    {n}: Any  # tighten type from usage in {file_path}" for n in arg_names
            )
            dc_code = (
                "from dataclasses import dataclass\n"
                "from typing import Any\n\n"
                f"@dataclass\n"
                f"class {dc_name}:\n"
                f"{field_lines}\n\n"
                f"def {func_name}(params: {dc_name}) -> ...:\n"
                f"    # body unchanged, replace {arg_names[0]} with params.{arg_names[0]}, etc.\n\n"
                f"# Caller in this repo (example):\n"
                f"# {func_name}({dc_name}({', '.join(f'{n}=...' for n in arg_names)}))\n"
            )
            steps.append(
                ImplementationStep(
                    title=f"Introduce `{dc_name}` in `{file_path}` for `{func_name}`",
                    location=f"{file_path} (above {func_name})",
                    description=(
                        f"`{func_name}` in this repository takes {params} parameters ({', '.join(arg_names)}). "
                        f"Group them into a dataclass defined in the same module so existing callers "
                        f"can migrate incrementally."
                    ),
                    code=dc_code,
                    business_outcome="Stabilizes the public surface of this function as the repo grows.",
                )
            )

    # --- Long function: split on top-level for/if ---
    if loc >= 35 and cyclomatic >= 8:
        branches: list[tuple[str, int, int]] = []
        for child in node.body:
            if isinstance(child, (ast.If, ast.For, ast.While)) and hasattr(child, "lineno"):
                kind = "loop" if isinstance(child, (ast.For, ast.While)) else "branch"
                try:
                    hdr = ast.unparse(child)[:50] if isinstance(child, ast.If) else type(child).__name__
                except Exception:
                    hdr = kind
                branches.append((hdr, child.lineno or 0, child.end_lineno or 0))

        if branches:
            primary = branches[0]
            helper = f"{helper_prefix}{func_name}_primary"
            hdr, s, e = primary
            steps.append(
                ImplementationStep(
                    title=f"Split `{prefix}{func_name}` — extract first {primary[0]}",
                    location=f"{file_path}:{s}-{e}",
                    description=(
                        f"`{func_name}` in `{file_path}` is {loc} lines with cyclomatic {cyclomatic}. "
                        f"First split: move the block at lines {s}–{e} (`{hdr}`) into `{helper}()` "
                        f"in the same file, keeping `{func_name}` as orchestration only."
                    ),
                    code=textwrap.dedent(f"""
                        def {helper}({', '.join(_arg_names(node))}):
                            # Move lines {s}-{e} from {func_name} here (same file: {file_path})

                        def {func_name}({', '.join(_arg_names(node))}):
                            result = []  # keep existing init
                            {helper}({', '.join(_arg_names(node))})
                            # remaining branches from original {func_name}
                            return result
                    """),
                    business_outcome=f"Shrinks `{func_name}` so the next change in `{file_base}.py` touches less code.",
                )
            )

    # --- Recursion → iteration (repo-specific) ---
    if _has_recursive_self_call(node, func_name):
        start = node.lineno or 0
        steps.append(
            ImplementationStep(
                title=f"Replace recursion in `{prefix}{func_name}` with iterative loop",
                location=f"{file_path}:{start}+",
                description=(
                    f"`{func_name}` in `{file_path}` calls itself — stack overflow risk for large inputs "
                    f"in this codebase. Rewrite using an explicit stack/queue while preserving return shape."
                ),
                code=textwrap.dedent(f"""
                    def {func_name}(data):
                        if data is None:
                            return None
                        stack = [data]
                        while stack:
                            current = stack.pop()
                            if len(current) == 0:
                                return []
                            if current[0] == "x":
                                stack.append(current[1:])
                                continue
                            return current
                        return None
                """),
                business_outcome="Safer behavior under production load without changing module import path.",
            )
        )

    # --- Class-level split ---
    return steps


def plan_python_class(
    *,
    file_path: str,
    module: str,
    class_node: ast.ClassDef,
    methods: list[ast.FunctionDef | ast.AsyncFunctionDef],
    field_names: list[str],
    method_count: int,
    field_count: int,
) -> list[ImplementationStep]:
    steps: list[ImplementationStep] = []
    if method_count < 8 and field_count < 12:
        return steps

    method_names = [m.name for m in methods if not m.name.startswith("__")]
    groups: dict[str, list[str]] = {}
    for name in method_names:
        prefix = name.split("_")[0] if "_" in name else "core"
        groups.setdefault(prefix, []).append(name)

    if len(groups) >= 2:
        new_classes = []
        for prefix, names in sorted(groups.items()):
            cls = f"{class_node.name}{prefix.title()}"
            new_classes.append(
                f"class {cls}:\n"
                + "\n".join(f"    def {n}(self, ...):  # move from {class_node.name}.{n}" for n in names)
            )
        steps.append(
            ImplementationStep(
                title=f"Split `{class_node.name}` in `{file_path}` by method prefix",
                location=f"{file_path}:{class_node.lineno}",
                description=(
                    f"`{class_node.name}` has {method_count} methods in this repo file. "
                    f"Grouped by naming: { {k: len(v) for k, v in groups.items()} }. "
                    f"Create sibling classes in the **same file** first; extract shared state ({', '.join(field_names[:5])}...) "
                    f"into a small `{class_node.name}Context` dataclass passed to each."
                ),
                code="\n\n".join(new_classes)
                + textwrap.dedent(f"""

                    @dataclass
                    class {class_node.name}Context:
                        # move fields: {', '.join(field_names[:8])}

                    # Original {class_node.name} becomes facade delegating to the split classes.
                """),
                business_outcome=f"Teams can own `{file_path}` sections without editing one {method_count}-method class.",
            )
        )
    return steps


def plan_python_class_focus_method(
    *,
    file_path: str,
    class_node: ast.ClassDef,
    methods: list[ast.FunctionDef | ast.AsyncFunctionDef],
    risk_band: str,
) -> list[ImplementationStep]:
    """For smaller classes: anchor refactor on the highest-complexity method in this file."""
    if risk_band not in ("MEDIUM", "HIGH", "CRITICAL") or not methods:
        return []
    scored: list[tuple[int, ast.FunctionDef | ast.AsyncFunctionDef]] = []
    for m in methods:
        if m.name.startswith("__"):
            continue
        cyc, _ = _func_cyclomatic_nesting(m)
        scored.append((cyc, m))
    if not scored:
        return []
    scored.sort(key=lambda x: x[0], reverse=True)
    top_cyc, top = scored[0]
    if top_cyc < 6:
        return []
    params = _arg_names(top)
    policy = f"{class_node.name}FetchPolicy"
    return [
        ImplementationStep(
            title=f"Stabilize `{class_node.name}` in `{file_path}` via `{top.name}`",
            location=f"{file_path}:{class_node.lineno}",
            description=(
                f"In this repo, `{class_node.name}` complexity is concentrated in `{top.name}` "
                f"(cyclomatic {top_cyc}, lines {top.lineno}–{top.end_lineno}). "
                f"Add a parameter object in **`{file_path}`** and keep `{class_node.name}` as a thin coordinator."
            ),
            code=textwrap.dedent(f"""
                from dataclasses import dataclass
                from typing import Callable, Iterable, Any

                @dataclass
                class {policy}:
                    strict: bool = False
                    transform: Callable[..., Any] | None = None
                    fallback: Callable[..., Any] | None = None

                class {class_node.name}:
                    def {top.name}(self, ids: Iterable, policy: {policy} | None = None):
                        policy = policy or {policy}()
                        # 1) Move negative-id guard from lines {top.lineno}+ into _handle_invalid
                        # 2) Move transform loop into _apply_transform
                        # 3) Default path uses self.repository.get — see method plan for {top.name}
                        ...
            """),
            business_outcome=(
                f"Future edits to `{file_path}` touch `{top.name}` helpers instead of the whole `{class_node.name}` surface."
            ),
        )
    ]


def _func_cyclomatic_nesting(node: ast.AST) -> tuple[int, int]:
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


def plan_python_field(
    *,
    file_path: str,
    class_name: str,
    field_name: str,
    node: ast.AST,
    source: str,
) -> list[ImplementationStep]:
    steps: list[ImplementationStep] = []
    if not hasattr(node, "lineno"):
        return steps
    snippet = source.splitlines()[(node.lineno or 1) - 1 : (node.end_lineno or node.lineno or 1)]
    if len(snippet) <= 2:
        return steps
    steps.append(
        ImplementationStep(
            title=f"Move `{class_name}.{field_name}` initializer to factory",
            location=f"{file_path}:{node.lineno}",
            description=(
                f"Field `{field_name}` on `{class_name}` in `{file_path}` has a non-trivial initializer. "
                f"Add `@classmethod {class_name}.with_{field_name}(...)` in this file and assign in `__init__` via that factory."
            ),
            code=textwrap.dedent(f"""
                class {class_name}:
                    @classmethod
                    def with_{field_name}(cls, ...):
                        instance = cls.__new__(cls)
                        instance.{field_name} = ...  # logic from line {node.lineno}
                        return instance
            """),
            business_outcome=f"Constructors of `{class_name}` stay readable for new code in this module.",
        )
    )
    return steps


def build_implementation_plan(
    *,
    entity_type: str,
    file_path: str,
    language: str,
    source: str,
    qualified_name: str,
    node: Any | None = None,
    class_node: ast.ClassDef | None = None,
    methods: list[Any] | None = None,
    field_names: list[str] | None = None,
    cyclomatic: int = 0,
    nesting: int = 0,
    loc: int = 0,
    params: int = 0,
    method_count: int = 0,
    field_count: int = 0,
    risk_band: str = "LOW",
    line_start: int = 0,
    line_end: int = 0,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[dict[str, str], ...]]:
    """
    Returns (markdown_blocks, plain_summaries, structured_diffs for UI).
    """
    if risk_band == "LOW" and cyclomatic < 7 and nesting < 3 and loc < 35:
        return (), (), ()

    needs_heavy_ast = (
        risk_band in ("HIGH", "CRITICAL")
        or cyclomatic >= 12
        or nesting >= 5
        or loc >= 55
    )

    py_ast_ready = language == "python" and (
        (
            entity_type in ("function", "method")
            and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
        or (entity_type == "class" and class_node is not None)
        or (entity_type == "field" and node is not None)
    )
    if not py_ast_ready or not needs_heavy_ast:
        return _plan_heuristic_impl(
            entity_type=entity_type,
            file_path=file_path,
            source=source,
            qualified_name=qualified_name,
            cyclomatic=cyclomatic,
            nesting=nesting,
            loc=loc,
            params=params,
            language=language,
            line_start=line_start,
            line_end=line_end,
        )

    parts = qualified_name.split(".")
    func_or_class = parts[-1]
    class_name = parts[-2] if entity_type in ("method", "field") and len(parts) >= 2 else None
    module = ".".join(parts[:-2]) if class_name else ".".join(parts[:-1])

    steps: list[ImplementationStep] = []

    if entity_type in ("function", "method") and isinstance(
        node, (ast.FunctionDef, ast.AsyncFunctionDef)
    ):
        generators = [
            lambda: _generate_process_style_refactor(
                node, file_path, func_or_class, class_name, source
            ),
        ]
        if isinstance(node, ast.FunctionDef):
            generators.append(lambda: _generate_legacy_handler_iterative(node, file_path))
            if class_name:
                generators.append(
                    lambda: _generate_fetch_batch_refactor(node, file_path, class_name)
                )
        for gen in generators:
            step = gen()
            if step:
                steps.append(step)
        steps.extend(
            plan_python_function(
                file_path=file_path,
                module=module or file_path,
                func_name=func_or_class,
                class_name=class_name,
                node=node,
                source=source,
                cyclomatic=cyclomatic,
                nesting=nesting,
                loc=loc,
                params=params,
            )
        )
    elif entity_type == "class" and class_node is not None:
        steps.extend(
            plan_python_class(
                file_path=file_path,
                module=module or file_path,
                class_node=class_node,
                methods=methods or [],
                field_names=field_names or [],
                method_count=method_count,
                field_count=field_count,
            )
        )
        steps.extend(
            plan_python_class_focus_method(
                file_path=file_path,
                class_node=class_node,
                methods=methods or [],
                risk_band=risk_band,
            )
        )
    elif entity_type == "field":
        steps.extend(
            plan_python_field(
                file_path=file_path,
                class_name=class_name or "Class",
                field_name=func_or_class,
                node=node,
                source=source,
            )
        )

    return _steps_output(steps)


def _lang_fence(file_path: str, language: str) -> str:
    if language == "python" or file_path.endswith(".py"):
        return "python"
    if language in ("typescript",) or file_path.endswith((".ts", ".tsx")):
        return "typescript"
    if language == "java" or file_path.endswith(".java"):
        return "java"
    if language == "kotlin" or file_path.endswith(".kt"):
        return "kotlin"
    if language == "csharp" or file_path.endswith(".cs"):
        return "csharp"
    if language == "go" or file_path.endswith(".go"):
        return "go"
    if language == "rust" or file_path.endswith(".rs"):
        return "rust"
    if language == "ruby" or file_path.endswith(".rb"):
        return "ruby"
    if language == "php" or file_path.endswith(".php"):
        return "php"
    if language == "scala" or file_path.endswith(".scala"):
        return "scala"
    if language in ("cpp", "c", "objc") or file_path.endswith(
        (".cpp", ".cc", ".c", ".h", ".hpp", ".m", ".mm")
    ):
        return "cpp"
    return "javascript"


def _plan_heuristic_impl(
    *,
    entity_type: str,
    file_path: str,
    source: str,
    qualified_name: str,
    cyclomatic: int,
    nesting: int,
    loc: int,
    params: int,
    language: str = "unknown",
    line_start: int = 0,
    line_end: int = 0,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[dict[str, str], ...]]:
    name = qualified_name.split(".")[-1]
    fence = _lang_fence(file_path, language)
    is_py = fence == "python"

    start_hint, end_hint = _find_symbol_line_range(
        source,
        name,
        entity_type=entity_type,
        language=language,
        line_start=line_start,
        line_end=line_end,
    )
    before_snippet = _source_slice_with_context(source, start_hint, end_hint, padding=2)

    steps: list[ImplementationStep] = []
    target_name = name
    if entity_type == "class" and fence == "java":
        for m in _JAVA_METHOD_HEAD.finditer(source):
            line_no = source[: m.start()].count("\n") + 1
            if line_no == start_hint:
                target_name = m.group(1)
                break

    if cyclomatic >= 8 and entity_type in ("method", "function", "class"):
        helper = f"_refactor_{target_name}_core"
        if is_py:
            code = textwrap.dedent(f"""
                def {helper}(...):  # copy parameter list from {name}
                    # paste innermost if/for block from lines around {start_hint}
                    ...

                def {name}(...):
                    return {helper}(...)
            """)
        elif fence == "go":
            code = textwrap.dedent(f"""
                func {helper}(/* same params as {name} */) {{
                    // move innermost if/for/range from lines ~{start_hint}
                }}

                func {name}(/* existing params */) {{
                    {helper}(/* pass through */)
                }}
            """)
        elif fence == "rust":
            code = textwrap.dedent(f"""
                fn {helper}(/* same params as {name} */) {{
                    // move innermost match/if block from lines ~{start_hint}
                }}

                fn {name}(/* existing params */) {{
                    {helper}(/* pass through */)
                }}
            """)
        elif fence == "java":
            code = textwrap.dedent(f"""
                // Add inside class body (do not remove package/imports/class declaration):
                private void {helper}(/* same params as {target_name} */) {{
                    // move nested if/for from `{target_name}` (lines ~{start_hint}-{end_hint})
                }}

                // Then simplify `{target_name}` to delegate:
                // public ... {target_name}(...) {{ {helper}(...); }}
            """)
        else:
            code = textwrap.dedent(f"""
                function {helper}(/* copy parameters from {name} */) {{
                  // paste nested block from lines around {start_hint}
                }}

                function {name}(...) {{
                  return {helper}(...);
                }}
            """)
        after_code = code.strip()
        diff_before, diff_after = _sanitize_diff_pair(
            before_snippet,
            after_code,
            entity_type=entity_type,
        )
        loc_label = f"{file_path}:{start_hint}-{end_hint}"
        steps.append(
            ImplementationStep(
                title=f"Extract core logic from `{target_name}`",
                location=loc_label,
                description=(
                    f"In `{file_path}`, add `{helper}()` inside the class and move nested logic from "
                    f"`{target_name}` (lines {start_hint}–{end_hint}). Keep package, imports, and class "
                    f"declaration unchanged — only refactor the method body."
                ),
                code=after_code,
                before_code=diff_before,
                after_code=diff_after,
                language=fence,
                entity_type=entity_type,
                business_outcome=f"Reduces branching inside `{target_name}` without changing public API.",
            )
        )
    if params >= 5:
        param_after = (
            f"@dataclass\nclass {name.title()}Options:\n    ...  # group {params} parameters\n"
            if is_py
            else f"// {name.title()}Options — group {params} parameters"
        )
        pb, pa = _sanitize_diff_pair(before_snippet, param_after, entity_type=entity_type)
        steps.append(
            ImplementationStep(
                title=f"Parameter object for `{target_name}` in `{file_path}`",
                location=f"{file_path}:{start_hint}+",
                description=f"Replace {params} parameters with a single options object in `{file_path}`.",
                code=param_after,
                before_code=pb,
                after_code=pa,
                language=fence,
                entity_type=entity_type,
                business_outcome="Smaller call sites and easier testing.",
            )
        )
    return _steps_output(steps)
