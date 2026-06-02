"""Structured implementation diffs for dashboard GitHub-style view."""

from omega.implementation import (
    ImplementationStep,
    _find_symbol_line_range,
    _preserve_code,
    _reindent_block,
    _sanitize_diff_pair,
    _plan_heuristic_impl,
    _steps_output,
)


def test_preserve_code_keeps_leading_indent():
    assert _preserve_code("    def foo():\n        pass") == "    def foo():\n        pass"


def test_reindent_block_normalizes_nested_slice():
    nested = "            if x:\n                return y"
    out = _reindent_block(nested, "        ")
    assert out == "        if x:\n            return y"


def test_steps_output_includes_before_after():
    step = ImplementationStep(
        title="Extract helper",
        location="pkg/mod.py:10-20",
        description="Move nested block.",
        code="def helper():\n    pass",
        before_code="if x:\n    pass",
        after_code="def helper():\n    pass",
        language="python",
        business_outcome="Easier tests.",
    )
    md, plain, diffs = _steps_output([step])
    assert len(md) == 1
    assert len(plain) == 1
    assert len(diffs) == 1
    d = diffs[0]
    assert d["before"] == "if x:\n    pass"  # indentation preserved (no strip)
    assert d["after"] == "def helper():\n    pass"
    assert d["language"] == "python"
    assert d["title"] == "Extract helper"


def test_sanitize_strips_misleading_java_class_header_diff():
    before = "package com.example;\nimport java.util.List;\npublic class Foo {\n  private int x;\n}\n"
    after = "private void _refactor_core() {\n}\n"
    b, a = _sanitize_diff_pair(before, after, entity_type="class")
    assert b == ""
    assert "private void" in a


def test_java_class_heuristic_uses_method_body_not_whole_file():
    java = """\
package com.example;

import org.springframework.stereotype.Service;

@Service
public class LocalStorageService {
    private String basePath;

    public void save(String path, byte[] data) {
        if (path == null) {
            throw new IllegalArgumentException();
        }
        for (int i = 0; i < data.length; i++) {
            if (data[i] < 0) {
                continue;
            }
        }
    }
}
"""
    _, _, diffs = _plan_heuristic_impl(
        entity_type="class",
        file_path="LocalStorageService.java",
        source=java,
        qualified_name="com.example.LocalStorageService",
        cyclomatic=12,
        nesting=2,
        loc=40,
        params=0,
        language="java",
        line_start=8,
        line_end=22,
    )
    assert diffs
    d = diffs[0]
    before = d.get("before") or ""
    assert not before.lstrip().startswith("package ")
    assert before == "" or "public void save" in before
    assert "_refactor_save_core" in d["after"]


def test_find_symbol_line_range_picks_branchiest_method_in_class():
    java = """\
public class C {
    public void easy() { return; }
    public void hard() {
        if (a) {
            for (int i = 0; i < n; i++) {
                if (b) { }
            }
        }
    }
}
"""
    start, end = _find_symbol_line_range(
        java,
        "C",
        entity_type="class",
        language="java",
        line_start=1,
        line_end=12,
    )
    chunk = "\n".join(java.splitlines()[start - 1 : end])
    assert "hard" in chunk
    assert "easy" not in chunk or start > 2
