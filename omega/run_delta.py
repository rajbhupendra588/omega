"""Compare two analysis runs for the same repository."""

from __future__ import annotations

from typing import Any


def _grade_rank(grade: str | None) -> int | None:
    order = {"A": 0, "B": 1, "C": 2, "D": 3, "F": 4, "N/A": 5}
    if not grade:
        return None
    return order.get(grade.upper(), None)


def _delta(a: float | int | None, b: float | int | None) -> float | None:
    if a is None or b is None:
        return None
    return round(float(a) - float(b), 2)


def _file_map(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {f["path"]: f for f in report.get("files", []) if f.get("path")}


def compare_reports(
    current: dict[str, Any],
    baseline: dict[str, Any],
    *,
    current_run_id: str,
    baseline_run_id: str,
    baseline_created_at: str | None = None,
) -> dict[str, Any]:
    """Build delta summary: current minus baseline (positive Ω = regression)."""
    cur_omega = float(current.get("omega_index", 0))
    base_omega = float(baseline.get("omega_index", 0))
    omega_delta = round(cur_omega - base_omega, 2)

    cur_grade = current.get("quality_grade")
    base_grade = baseline.get("quality_grade")
    cur_rank = _grade_rank(str(cur_grade) if cur_grade else None)
    base_rank = _grade_rank(str(base_grade) if base_grade else None)
    grade_improved: bool | None = None
    if cur_rank is not None and base_rank is not None:
        grade_improved = cur_rank < base_rank

    pillars_cur = current.get("pillars") or {}
    pillars_base = baseline.get("pillars") or {}
    pillar_deltas: dict[str, float] = {}
    for key in set(pillars_cur) | set(pillars_base):
        d = _delta(pillars_cur.get(key), pillars_base.get(key))
        if d is not None:
            pillar_deltas[key] = d

    dim_deltas: list[dict[str, Any]] = []
    base_dims = {d["id"]: d for d in baseline.get("dimensions", []) if d.get("id")}
    for d in current.get("dimensions", []):
        did = d.get("id")
        if not did or did not in base_dims:
            continue
        ds = _delta(d.get("score"), base_dims[did].get("score"))
        if ds is not None:
            dim_deltas.append(
                {
                    "id": did,
                    "name": d.get("name", did),
                    "score_delta": ds,
                    "current_score": d.get("score"),
                    "baseline_score": base_dims[did].get("score"),
                }
            )
    dim_deltas.sort(key=lambda x: abs(x["score_delta"]), reverse=True)

    cur_files = _file_map(current)
    base_files = _file_map(baseline)
    improved: list[dict[str, Any]] = []
    regressed: list[dict[str, Any]] = []
    for path, cf in cur_files.items():
        bf = base_files.get(path)
        if not bf:
            continue
        d = round(float(cf["omega_local"]) - float(bf["omega_local"]), 2)
        row = {
            "path": path,
            "omega_delta": d,
            "current_omega": cf["omega_local"],
            "baseline_omega": bf["omega_local"],
            "current_band": cf.get("risk_band"),
            "baseline_band": bf.get("risk_band"),
        }
        if d <= -2.0:
            improved.append(row)
        elif d >= 2.0:
            regressed.append(row)

    improved.sort(key=lambda x: x["omega_delta"])
    regressed.sort(key=lambda x: x["omega_delta"], reverse=True)

    es_cur = current.get("entity_summary") or {}
    es_base = baseline.get("entity_summary") or {}

    summary = _narrative_summary(omega_delta, grade_improved, len(improved), len(regressed))

    return {
        "current_run_id": current_run_id,
        "baseline_run_id": baseline_run_id,
        "baseline_analyzed_at": baseline.get("analyzed_at"),
        "baseline_created_at": baseline_created_at,
        "omega_index": {
            "current": cur_omega,
            "baseline": base_omega,
            "delta": omega_delta,
            "improved": omega_delta < 0,
        },
        "quality_grade": {
            "current": cur_grade,
            "baseline": base_grade,
            "improved": grade_improved,
        },
        "file_count": {
            "current": current.get("file_count"),
            "baseline": baseline.get("file_count"),
            "delta": _delta(current.get("file_count"), baseline.get("file_count")),
        },
        "total_loc": {
            "current": current.get("total_loc"),
            "baseline": baseline.get("total_loc"),
            "delta": _delta(current.get("total_loc"), baseline.get("total_loc")),
        },
        "bayesian_quality": {
            "current": current.get("bayesian_quality"),
            "baseline": baseline.get("bayesian_quality"),
            "delta": _delta(current.get("bayesian_quality"), baseline.get("bayesian_quality")),
        },
        "epistemic_uncertainty": {
            "current": current.get("epistemic_uncertainty"),
            "baseline": baseline.get("epistemic_uncertainty"),
            "delta": _delta(
                current.get("epistemic_uncertainty"),
                baseline.get("epistemic_uncertainty"),
            ),
        },
        "pillar_deltas": pillar_deltas,
        "dimension_deltas": dim_deltas[:10],
        "files_improved": improved[:15],
        "files_regressed": regressed[:15],
        "entity_high_risk": {
            "current": es_cur.get("high_risk"),
            "baseline": es_base.get("high_risk"),
            "delta": _delta(es_cur.get("high_risk"), es_base.get("high_risk")),
        },
        "summary": summary,
    }


def _narrative_summary(
    omega_delta: float,
    grade_improved: bool | None,
    n_improved: int,
    n_regressed: int,
) -> str:
    parts: list[str] = []
    if omega_delta < -0.5:
        parts.append(
            f"Ω index improved by {abs(omega_delta):.2f} points (lower is healthier)."
        )
    elif omega_delta > 0.5:
        parts.append(
            f"Ω index worsened by {omega_delta:.2f} points — review regressions below."
        )
    else:
        parts.append("Ω index is essentially unchanged since the previous run.")

    if grade_improved is True:
        parts.append("Letter grade improved.")
    elif grade_improved is False:
        parts.append("Letter grade declined.")

    if n_improved:
        parts.append(f"{n_improved} file(s) show meaningful Ω reduction (≥2 points).")
    if n_regressed:
        parts.append(f"{n_regressed} file(s) regressed (Ω up ≥2 points).")
    return " ".join(parts)
