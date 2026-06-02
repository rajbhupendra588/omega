"""Tests for benchmark baseline indices."""

from __future__ import annotations

from omega.baselines import baseline_scores, cyclomatic_only_index, grade_for_baseline_index
from omega.metrics import FileMetrics


def _file(cyclomatic: int, loc: int = 50, h_struct: float = 3.0) -> FileMetrics:
    return FileMetrics(
        path="f.py",
        loc=loc,
        cyclomatic=cyclomatic,
        nesting_depth=1,
        h_struct=h_struct,
        h_text=4.0,
        compression_ratio=2.0,
        coupling_out=0,
        coupling_in=0,
        omega_local=20.0,
        risk_band="LOW",
    )


def test_cyclomatic_only_index_ordering():
    low = cyclomatic_only_index([_file(1), _file(2)])
    high = cyclomatic_only_index([_file(15), _file(20)])
    assert high > low


def test_baseline_scores_keys():
    scores = baseline_scores([_file(5)])
    assert "cyclomatic_index" in scores
    assert scores["cyclomatic_grade"] in ("A", "B", "C", "D", "F")


def test_grade_for_baseline_matches_omega_scale():
    assert grade_for_baseline_index(25) == "A"
    assert grade_for_baseline_index(50) == "C"
