"""Integration tests for repository analysis."""

from __future__ import annotations

from pathlib import Path

from omega.analyzer import analyze_repository
from omega.baselines import cyclomatic_only_index


def test_sample_repo_produces_outcome(sample_repo: Path):
    outcome = analyze_repository(sample_repo, repo_display="sample_repo")
    assert outcome.file_count > 0
    assert outcome.total_loc > 0
    assert outcome.quality_grade in ("A", "B", "C", "D", "F")
    assert 0 <= outcome.omega_index <= 100
    assert outcome.entities
    assert outcome.dimensions


def test_risky_module_higher_omega_than_good(sample_repo: Path):
    outcome = analyze_repository(sample_repo)
    by_path = {f.path: f.omega_local for f in outcome.files}
    risky = max(
        by_path.get("risky_module.py", 0),
        by_path.get("another_risky.py", 0),
    )
    good = by_path.get("good_module.py", 0)
    assert risky > good


def test_baseline_cyclomatic_index(sample_repo: Path):
    outcome = analyze_repository(sample_repo)
    cyc_idx = cyclomatic_only_index(outcome.files)
    assert cyc_idx >= 0
    assert outcome.omega_index >= 0
