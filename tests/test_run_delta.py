"""Tests for run-to-run delta reporting."""

from __future__ import annotations

from omega.run_delta import compare_reports


def _mini_report(omega: float, grade: str, files: list[dict]) -> dict:
    return {
        "omega_index": omega,
        "quality_grade": grade,
        "analyzed_at": "2026-01-01",
        "file_count": len(files),
        "total_loc": sum(f.get("loc", 10) for f in files),
        "bayesian_quality": 8.0,
        "epistemic_uncertainty": 0.2,
        "pillars": {"cyclomatic_pressure": 5.0, "structural_entropy": 3.0},
        "dimensions": [
            {"id": "cyclomatic_pressure", "name": "Control-flow", "score": 40.0},
        ],
        "entity_summary": {"high_risk": 1},
        "files": files,
    }


def test_compare_reports_improvement():
    base_files = [{"path": "a.py", "omega_local": 50, "risk_band": "MEDIUM", "loc": 20}]
    cur_files = [{"path": "a.py", "omega_local": 40, "risk_band": "MEDIUM", "loc": 20}]
    baseline = _mini_report(30.0, "A", base_files)
    current = _mini_report(25.0, "A", cur_files)
    delta = compare_reports(
        current,
        baseline,
        current_run_id="cur",
        baseline_run_id="base",
    )
    assert delta["omega_index"]["delta"] == -5.0
    assert delta["omega_index"]["improved"] is True
    assert len(delta["files_improved"]) == 1


def test_compare_reports_regression():
    baseline = _mini_report(20.0, "A", [{"path": "x.py", "omega_local": 30, "risk_band": "LOW", "loc": 5}])
    current = _mini_report(35.0, "B", [{"path": "x.py", "omega_local": 45, "risk_band": "MEDIUM", "loc": 5}])
    delta = compare_reports(current, baseline, current_run_id="c", baseline_run_id="b")
    assert delta["omega_index"]["improved"] is False
    assert len(delta["files_regressed"]) == 1
