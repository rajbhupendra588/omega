"""Metric suite: service context, ecosystem, N metrics."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from omega.analyzer import analyze_repository
from omega.ecosystem import discover_ecosystem, per_service_stress
from omega.metrics_suite import (
    build_metrics_suite,
    ensure_report_has_metric_suite,
    get_metric_registry,
)
from omega.service_context import detect_service_context


def test_registry_has_core_field_and_business_metrics():
    reg = get_metric_registry()
    ids = {d.id for d in reg.definitions}
    assert "omega_repo_index" in ids
    assert "business_continuity_risk" in ids
    assert "service_criticality_index" in ids
    assert len(ids) >= 26


def test_analyze_sample_repo_includes_metric_suite():
    root = Path(__file__).resolve().parent.parent / "sample_repo"
    outcome = analyze_repository(root, repo_display="sample_repo")
    suite = outcome.metric_suite
    assert suite["metric_count"] >= 26
    assert suite["service_context"]["service_name"]
    assert "metrics" in suite
    categories = {m["category"] for m in suite["metrics"]}
    assert "field" in categories
    assert "business" in categories
    assert "impact" in categories


def test_ecosystem_yaml_upstream_metrics(tmp_path: Path):
    cfg = tmp_path / ".omega" / "ecosystem.yaml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(
        """
service:
  name: billing-api
  role: api
  business_domains: payments
upstream:
  - name: postgres
    kind: datastore
  - name: auth-service
    kind: http
downstream:
  - name: analytics-pipeline
    kind: queue
""",
        encoding="utf-8",
    )
    (tmp_path / "main.py").write_text(
        "import requests\nrequests.get('https://auth.internal/health')\n",
        encoding="utf-8",
    )
    ctx = detect_service_context(tmp_path, repo_display="billing-api")
    assert ctx["service_name"] == "billing-api"
    eco = discover_ecosystem(tmp_path, source_file_paths=[tmp_path / "main.py"])
    assert eco["upstream_count"] >= 2
    assert eco["downstream_count"] >= 1

    from omega.analyzer import RepositoryOutcome

    outcome = RepositoryOutcome(
        root=str(tmp_path),
        repo_display="billing-api",
        github_url=None,
        analyzed_at="2026-01-01",
        omega_index=42.0,
        quality_grade="C",
        health_summary="",
        health_summary_business="",
        file_count=1,
        total_loc=10,
        pillars={
            "structural_entropy": 3.0,
            "cyclomatic_pressure": 5.0,
            "coupling_field": 1.0,
            "topological_cycles": 0,
            "p95_omega_local": 42,
            "max_omega_local": 42,
            "textual_entropy": 2.0,
            "information_density": 2.5,
        },
    )
    suite = build_metrics_suite(tmp_path, outcome)
    upstream_metrics = [m for m in suite["metrics"] if m["category"] == "upstream"]
    assert any(m["related_service"] == "postgres" for m in upstream_metrics)
    assert any(m["related_service"] == "auth-service" for m in upstream_metrics)
    assert suite["impact_summary"]["business_continuity_risk"] is not None


def test_per_service_stress_scales_with_kind():
    node = {"name": "db", "kind": "datastore", "evidence": ["a", "b"]}
    v = per_service_stress(50.0, node=node, direction="upstream")
    assert 0 < v <= 100


def test_ensure_report_backfill():
    report = {
        "repository": str(Path(__file__).parent.parent / "sample_repo"),
        "repo_display": "sample_repo",
        "omega_index": 40.0,
        "quality_grade": "C",
        "file_count": 3,
        "total_loc": 100,
        "pillars": {
            "structural_entropy": 3.0,
            "cyclomatic_pressure": 5.0,
            "coupling_field": 1.0,
            "topological_cycles": 0,
            "p95_omega_local": 40,
            "max_omega_local": 45,
            "textual_entropy": 2.0,
            "information_density": 2.5,
        },
        "languages": {"python": 40.0},
        "entity_summary": {"total": 5, "high_risk": 1},
        "bayesian_quality": 6.0,
        "epistemic_uncertainty": 0.2,
    }
    updated, changed = ensure_report_has_metric_suite(report)
    assert changed
    assert updated["metric_suite"]["metric_count"] >= 26
