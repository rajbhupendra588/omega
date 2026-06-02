"""Baseline quality indices for benchmark comparison (no Ω composite)."""

from __future__ import annotations

from omega.metrics import FileMetrics


def _grade_from_index(index: float) -> str:
    if index < 30:
        return "A"
    if index < 45:
        return "B"
    if index < 60:
        return "C"
    if index < 75:
        return "D"
    return "F"


def cyclomatic_only_index(files: list[FileMetrics]) -> float:
    """Mean per-file McCabe complexity scaled 0–100 (higher = worse)."""
    if not files:
        return 0.0
    vals = [min(100.0, float(f.cyclomatic) * 6.0) for f in files]
    return round(sum(vals) / len(vals), 2)


def loc_only_index(files: list[FileMetrics]) -> float:
    """Mean log-scaled LOC stress 0–100 (higher = worse)."""
    if not files:
        return 0.0
    import math

    vals = [min(100.0, math.log1p(max(1, f.loc)) * 12.0) for f in files]
    return round(sum(vals) / len(vals), 2)


def entropy_only_index(files: list[FileMetrics]) -> float:
    """Mean structural entropy scaled 0–100 (higher = worse)."""
    if not files:
        return 0.0
    vals = [min(100.0, f.h_struct * 8.0) for f in files]
    return round(sum(vals) / len(vals), 2)


def grade_for_baseline_index(index: float) -> str:
    return _grade_from_index(index)


def baseline_scores(files: list[FileMetrics]) -> dict[str, float | str]:
    cyc = cyclomatic_only_index(files)
    loc = loc_only_index(files)
    ent = entropy_only_index(files)
    return {
        "cyclomatic_index": cyc,
        "cyclomatic_grade": grade_for_baseline_index(cyc),
        "loc_index": loc,
        "loc_grade": grade_for_baseline_index(loc),
        "entropy_index": ent,
        "entropy_grade": grade_for_baseline_index(ent),
    }
