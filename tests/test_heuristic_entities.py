"""Heuristic (non-Python) symbol improvements and implementation plans."""

from __future__ import annotations

from omega.entities import analyze_file_entities


def test_javascript_entity_gets_implementation_plan():
    src = """
    export function processItems(items, mode, threshold, callback, extra, flag) {
      for (const item of items) {
        if (mode === "strict") {
          if (item > threshold) {
            if (callback) {
              if (extra) {
                callback(item, extra);
              }
            }
          }
        } else if (mode === "loose") {
          for (let j = 0; j < 3; j++) {
            if (j % 2 === 0 && item > 0) console.log(item);
          }
        }
      }
    }
    """
    entities = analyze_file_entities("lib/process.js", src, "javascript")
    assert entities
    top = entities[0]
    assert top.improvement_areas
    assert top.improvement_areas_business
    assert top.implementation_plan or top.risk_band == "LOW"


def test_go_entity_gets_business_and_impl():
    src = """
    package main

    func process(items []int, mode string) {
        for _, item := range items {
            if mode == "strict" {
                if item > 10 {
                    if item%2 == 0 {
                        println(item)
                    }
                }
            }
        }
    }
    """
    entities = analyze_file_entities("main.go", src, "go")
    names = [e.qualified_name for e in entities]
    assert any("process" in n for n in names)
    proc = next(e for e in entities if e.qualified_name.endswith(".process"))
    assert proc.improvement_areas_business
    assert proc.file_path == "main.go"
