"""Multi-family Ω-QFM repository dimensions (field, business, ecosystem, temporal, AI-era, ML/DL)."""

from __future__ import annotations

from typing import Any

from omega.dimensions.ai_era import build_ai_era_dimensions
from omega.dimensions.business import build_business_dimensions
from omega.dimensions.context import DimensionContext
from omega.dimensions.core import RepoDimension, applicable_dimensions
from omega.dimensions.ecosystem import build_ecosystem_dimensions
from omega.dimensions.field import build_field_dimensions
from omega.dimensions.ml_learning import build_ml_learning_dimensions
from omega.dimensions.temporal import build_temporal_dimensions
from omega.entities import EntityMetrics
from omega.metrics import FileMetrics

__all__ = [
    "RepoDimension",
    "applicable_dimensions",
    "build_repo_dimensions",
    "build_dimensions_from_report",
    "ensure_report_has_dimensions",
    "file_from_report_dict",
    "entity_from_report_dict",
]


def file_from_report_dict(data: dict[str, Any]) -> FileMetrics:
    return FileMetrics(
        path=data["path"],
        loc=int(data.get("loc", 1)),
        cyclomatic=int(data["cyclomatic"]),
        nesting_depth=int(data["nesting_depth"]),
        h_struct=float(data["h_struct"]),
        h_text=float(data["h_text"]),
        compression_ratio=float(data["compression_ratio"]),
        coupling_out=int(data["coupling_out"]),
        coupling_in=int(data["coupling_in"]),
        omega_local=float(data["omega_local"]),
        risk_band=data["risk_band"],
        language=data.get("language", "unknown"),
    )


def entity_from_report_dict(data: dict[str, Any]) -> EntityMetrics:
    return EntityMetrics(
        entity_type=data["entity_type"],
        qualified_name=data["qualified_name"],
        file_path=data["file_path"],
        line_start=int(data["line_start"]),
        line_end=int(data["line_end"]),
        loc=int(data["loc"]),
        cyclomatic=int(data["cyclomatic"]),
        nesting_depth=int(data["nesting_depth"]),
        omega_local=float(data["omega_local"]),
        risk_band=data["risk_band"],
        improvement_areas=tuple(data.get("improvement_areas", [])),
        improvement_areas_business=tuple(data.get("improvement_areas_business", [])),
        implementation_plan=tuple(data.get("implementation_plan", [])),
        implementation_summary=tuple(data.get("implementation_summary", [])),
        implementation_diffs=tuple(data.get("implementation_diffs", [])),
        parent_class=data.get("parent_class"),
        parameter_count=int(data.get("parameter_count", 0)),
        method_count=int(data.get("method_count", 0)),
        field_count=int(data.get("field_count", 0)),
    )


def build_repo_dimensions(
    outcome: Any,
    *,
    root: str | None = None,
    baseline_report: dict[str, Any] | None = None,
) -> list[RepoDimension]:
    """Build all dimension families from one precomputed context."""
    ctx = DimensionContext.from_outcome(
        outcome,
        root=root or getattr(outcome, "root", None),
        baseline_report=baseline_report,
    )
    dims: list[RepoDimension] = []
    dims.extend(build_field_dimensions(ctx))
    dims.extend(build_business_dimensions(ctx))
    dims.extend(build_ecosystem_dimensions(ctx))
    dims.extend(build_ai_era_dimensions(ctx))
    dims.extend(build_ml_learning_dimensions(ctx))
    dims.extend(build_temporal_dimensions(ctx, dims))
    return applicable_dimensions(dims)


def build_dimensions_from_report(report: dict[str, Any]) -> list[dict[str, Any]]:
    existing = report.get("dimensions")
    if existing:
        return list(existing)
    if not report.get("files"):
        return []

    class _Snapshot:
        pass

    snap = _Snapshot()
    snap.repo_display = report.get("repo_display", "repository")
    snap.omega_index = float(report.get("omega_index", 0))
    snap.quality_grade = report.get("quality_grade", "N/A")
    snap.files = [file_from_report_dict(f) for f in report["files"]]
    snap.entities = [entity_from_report_dict(e) for e in report.get("entities", [])]
    snap.pillars = dict(report.get("pillars", {}))
    snap.top_by_language = dict(report.get("languages", report.get("top_by_language", {})))
    snap.entity_summary = dict(report.get("entity_summary", {}))
    snap.total_loc = int(report.get("total_loc", 0))
    snap.file_count = int(report.get("file_count", len(snap.files)))
    snap.bayesian_quality = float(report.get("bayesian_quality", 0))
    snap.epistemic_uncertainty = float(report.get("epistemic_uncertainty", 0))
    snap.root = report.get("repository")
    snap.metric_suite = dict(report.get("metric_suite") or {})

    return [
        d.to_dict()
        for d in build_repo_dimensions(
            snap,
            root=snap.root,
        )
    ]


def ensure_report_has_dimensions(report: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    if "dimensions" in report:
        return report, False
    dims = build_dimensions_from_report(report)
    if not dims:
        report["dimensions"] = []
        return report, True
    report = {**report, "dimensions": dims}
    return report, True
