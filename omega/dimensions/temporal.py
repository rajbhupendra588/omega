"""Temporal family: run-over-run field drift (when baseline report available)."""

from __future__ import annotations

from omega.dimensions.context import DimensionContext
from omega.dimensions.core import RepoDimension, dim


def build_temporal_dimensions(
    ctx: DimensionContext,
    current_dims: list[RepoDimension],
) -> list[RepoDimension]:
    if not ctx.files:
        return []
    baseline = ctx.baseline_report
    if not baseline:
        return []

    dims: list[RepoDimension] = []
    base_omega = float(baseline.get("omega_index", 0))
    delta = round(ctx.omega_index - base_omega, 2)
    drift_score = min(100, abs(delta) * 2.5)

    dims.append(
        dim(
            id="field_drift",
            name="Field drift (ΔΩ)",
            family="temporal",
            score=drift_score,
            weight=0.30,
            repo_aggregate=delta,
            unit="ΔΩ vs baseline",
            summary_technical=(
                f"Omega_repo {ctx.omega_index:.2f} vs baseline {base_omega:.2f} (Δ={delta:+.2f})."
            ),
            summary_business=(
                "Quality field improved since last run."
                if delta < -2
                else (
                    "Quality field regressed — investigate before release."
                    if delta > 2
                    else "Stable vs last analysis."
                )
            ),
            evidence=[
                f"Baseline grade {baseline.get('quality_grade')} → current {ctx.quality_grade}"
            ],
            actions_in_repo=[
                "Review changed files if ΔΩ > 2." if delta > 2 else "Maintain current trajectory."
            ],
        )
    )

    base_dims = {d["id"]: d for d in baseline.get("dimensions", []) if d.get("id")}
    regressions: list[str] = []
    for cur in current_dims:
        if cur.id not in base_dims:
            continue
        base_row = base_dims[cur.id]
        if not base_row.get("applicable", True):
            continue
        old = float(base_row.get("score", 0))
        if cur.score - old > 8:
            regressions.append(f"{cur.id}: {old:.1f} → {cur.score:.1f}")

    reg_score = min(100, len(regressions) * 18)
    dims.append(
        dim(
            id="dimension_regression",
            name="Dimension regression",
            family="temporal",
            score=reg_score,
            weight=0.22,
            repo_aggregate=float(len(regressions)),
            unit="regressed dims",
            summary_technical=f"{len(regressions)} dimension(s) worsened vs baseline.",
            summary_business="Multiple quality axes moved in the wrong direction since last scan.",
            evidence=regressions[:8],
            actions_in_repo=["Target regressed dimensions in the next sprint."],
        )
    )

    if baseline.get("analyzed_at"):
        dims.append(
            dim(
                id="debt_velocity",
                name="Debt velocity",
                family="temporal",
                score=drift_score,
                weight=0.18,
                repo_aggregate=delta,
                unit="Ω per run",
                summary_technical=f"Signed drift {delta:+.2f} between consecutive runs.",
                summary_business="Tracks whether quality debt is accumulating or burning down.",
                evidence=[f"Prior run: {baseline.get('analyzed_at')}"],
                actions_in_repo=["Schedule weekly Ω scans to monitor velocity."],
            )
        )

    return dims
