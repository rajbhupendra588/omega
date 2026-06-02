"""Tests for non-Python heuristic metrics."""

from __future__ import annotations

from omega.metrics_heuristic import analyze_source_text


def test_javascript_cyclomatic_proxy():
    src = """
    function f(x) {
      if (x > 0) {
        for (let i = 0; i < x; i++) {
          if (i % 2) console.log(i);
        }
      }
      return x;
    }
    """
    h = analyze_source_text(src, "javascript")
    assert h["loc"] >= 5
    assert h["cyclomatic"] >= 3
    assert h["nesting_depth"] >= 1


def test_go_import_count():
    src = 'package main\nimport "fmt"\nimport "os"\nfunc main() {}\n'
    h = analyze_source_text(src, "go")
    assert h["import_count"] >= 1


def test_empty_source_zeros():
    h = analyze_source_text("", "java")
    assert h["loc"] == 0
    assert h["cyclomatic"] == 1
