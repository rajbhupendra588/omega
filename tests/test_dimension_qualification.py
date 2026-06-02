"""Dimensions are qualified per repo; grade comes from Ω only."""

from __future__ import annotations

from pathlib import Path

from omega.analyzer import analyze_repository
from omega.dimensions import build_repo_dimensions


def test_minimal_repo_no_ecosystem_synthetic_dims(tmp_path: Path):
    (tmp_path / "lib.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    outcome = analyze_repository(tmp_path)
    dims = build_repo_dimensions(outcome, root=str(tmp_path))
    eco_ids = {d.id for d in dims if d.family == "ecosystem"}
    assert "upstream_aggregate_stress" not in eco_ids
    assert "cross_service_impact" not in eco_ids
    assert all(not d.contributes_to_grade for d in dims)
    assert all(d.applicable for d in dims)


def test_sample_repo_has_ecosystem_when_graph_configured():
    root = Path(__file__).resolve().parent.parent / "sample_repo"
    outcome = analyze_repository(root, repo_display="sample_repo")
    dims = build_repo_dimensions(outcome, root=str(root))
    eco = [d for d in dims if d.family == "ecosystem"]
    assert eco, "sample_repo has .omega/ecosystem.yaml upstream nodes"
    assert eco[0].qualification
