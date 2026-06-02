"""Full AST analysis for Java and Go via tree-sitter."""

from __future__ import annotations

from pathlib import Path

import pytest

from omega.ast_tree_sitter import (
    analyze_tree,
    file_metrics_from_tree,
    parse_tree,
    ts_coupling_maps,
)
from omega.entities_ts import analyze_java_entities, analyze_go_entities
from omega.agents.registry import strategy_for_language, create_worker


JAVA_SAMPLE = """
package com.example.app;
import java.util.List;
import com.example.util.Helper;

public class Service {
    private int count;

    public int compute(int x) {
        if (x > 0) {
            for (int i = 0; i < x; i++) {
                if (i % 2 == 0) count++;
            }
            return count;
        }
        return -1;
    }
}
"""

GO_SAMPLE = """package main

import (
    "fmt"
    "strings"
)

type Server struct {
    Name string
}

func (s *Server) Handle() {
    if s.Name != "" {
        fmt.Println(strings.ToUpper(s.Name))
    }
}

func Add(a, b int) int {
    if a > b {
        return a
    }
    return b
}
"""


@pytest.fixture
def java_tree():
    tree = parse_tree("java", JAVA_SAMPLE)
    assert tree is not None
    return tree


@pytest.fixture
def go_tree():
    tree = parse_tree("go", GO_SAMPLE)
    assert tree is not None
    return tree


def test_strategy_java_go_ast_full():
    assert strategy_for_language("java") == "ast_full"
    assert strategy_for_language("go") == "ast_full"


def test_java_metrics_from_ast(java_tree):
    a = analyze_tree("java", JAVA_SAMPLE, java_tree)
    assert a.cyclomatic >= 4
    assert a.nesting_depth >= 2
    assert a.h_struct > 0
    assert "list" in a.import_stems or "helper" in a.import_stems

    fm = file_metrics_from_tree(
        rel_path="com/example/Service.java",
        language="java",
        source=JAVA_SAMPLE,
        tree=java_tree,
        coupling_out=2,
        coupling_in=0,
    )
    assert fm.language == "java"
    assert fm.cyclomatic == a.cyclomatic
    assert fm.omega_local > 0


def test_go_metrics_from_ast(go_tree):
    a = analyze_tree("go", GO_SAMPLE, go_tree)
    assert a.cyclomatic >= 3
    assert a.nesting_depth >= 1
    assert "fmt" in a.import_stems and "strings" in a.import_stems

    ents = analyze_go_entities("server.go", GO_SAMPLE, go_tree)
    types = {e.entity_type for e in ents}
    assert "class" in types or "function" in types
    assert "method" in types


def test_java_entities(java_tree):
    ents = analyze_java_entities("Service.java", JAVA_SAMPLE, java_tree)
    names = [e.qualified_name for e in ents]
    assert any("Service" in n for n in names)
    assert any(e.entity_type == "method" for e in ents)


def test_ts_coupling_inbound_non_java_target(tmp_path: Path):
    """Java import stem may resolve to a .ts file in the same repo (monorepo)."""
    java_dir = tmp_path / "backend"
    ts_dir = tmp_path / "frontend" / "src" / "api"
    java_dir.mkdir(parents=True)
    ts_dir.mkdir(parents=True)
    java_file = java_dir / "App.java"
    ts_file = ts_dir / "fileService.ts"
    java_file.write_text(
        "package app; import fileService;\npublic class App { }\n",
        encoding="utf-8",
    )
    ts_file.write_text("export const x = 1;\n", encoding="utf-8")
    sources = {
        java_file: java_file.read_text(encoding="utf-8"),
        ts_file: ts_file.read_text(encoding="utf-8"),
    }
    stem_to_path = {p.stem.lower(): p for p in (java_file, ts_file)}
    out_c, in_c = ts_coupling_maps("java", [java_file], sources, stem_to_path)
    assert out_c[java_file] >= 0
    assert ts_file in in_c


def test_worker_java(tmp_path: Path):
    jf = tmp_path / "App.java"
    jf.write_text(JAVA_SAMPLE, encoding="utf-8")
    worker = create_worker("java")
    assert worker.strategy == "ast_full"
