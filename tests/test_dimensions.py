"""Multi-family dimension builders."""

from __future__ import annotations

from pathlib import Path

from omega.analyzer import analyze_repository
from omega.dimensions import build_repo_dimensions


def test_sample_repo_has_all_families():
    root = Path(__file__).resolve().parent.parent / "sample_repo"
    outcome = analyze_repository(root, repo_display="sample_repo")
    dims = build_repo_dimensions(outcome, root=str(root))
    families = {d.family for d in dims}
    assert "field" in families
    assert "business" in families
    assert "ecosystem" in families
    assert len(dims) >= 20


def test_temporal_with_baseline():
    root = Path(__file__).resolve().parent.parent / "sample_repo"
    outcome = analyze_repository(root)
    baseline = {
        "omega_index": outcome.omega_index + 10,
        "quality_grade": "D",
        "analyzed_at": "2020-01-01",
        "dimensions": [
            {"id": "structural_entropy", "score": 10.0},
        ],
    }
    dims = build_repo_dimensions(outcome, root=str(root), baseline_report=baseline)
    temporal = [d for d in dims if d.family == "temporal"]
    assert any(d.id == "field_drift" for d in temporal)
