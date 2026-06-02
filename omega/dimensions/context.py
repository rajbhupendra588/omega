"""Precomputed aggregates — one pass over files/entities for all dimension families."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from omega.dimensions.source_scan import SourceScanAggregate, scan_sources
from omega.entities import EntityMetrics
from omega.metrics import FileMetrics


@dataclass
class DimensionContext:
    display: str
    root: Path | None
    omega_index: float
    quality_grade: str
    pillars: dict[str, float]
    files: list[FileMetrics]
    entities: list[EntityMetrics]
    entity_summary: dict[str, int]
    top_by_language: dict[str, float]
    bayesian_quality: float
    epistemic_uncertainty: float
    total_loc: int
    file_count: int
    metric_suite: dict[str, Any]
    baseline_report: dict[str, Any] | None
    cyclic_files: list[FileMetrics] = field(default_factory=list)
    dir_rollup: list[tuple[str, float, int]] = field(default_factory=list)
    lang_files: dict[str, list[FileMetrics]] = field(default_factory=dict)
    sorted_by_omega: list[FileMetrics] = field(default_factory=list)
    service_context: dict[str, Any] = field(default_factory=dict)
    ecosystem: dict[str, Any] = field(default_factory=dict)
    impact_summary: dict[str, Any] = field(default_factory=dict)
    source_scan: SourceScanAggregate | None = None
    config_artifact_count: int = 0
    readme_chars: int = 0

    @classmethod
    def from_outcome(
        cls,
        outcome: Any,
        *,
        root: str | Path | None = None,
        baseline_report: dict[str, Any] | None = None,
    ) -> DimensionContext:
        files = list(outcome.files or [])
        entities = list(outcome.entities or [])
        pillars = dict(outcome.pillars or {})
        suite = dict(getattr(outcome, "metric_suite", None) or {})

        root_path: Path | None = None
        if root is not None:
            root_path = Path(root).resolve()
        elif getattr(outcome, "root", None):
            root_path = Path(outcome.root).resolve()

        cyclic = [f for f in files if f.coupling_out > 0 and f.coupling_in > 0]
        sorted_omega = sorted(files, key=lambda f: f.omega_local, reverse=True)

        lang_files: dict[str, list[FileMetrics]] = defaultdict(list)
        for f in files:
            lang_files[f.language].append(f)

        dir_buckets: dict[str, list[float]] = defaultdict(list)
        for f in files:
            parts = f.path.replace("\\", "/").split("/")
            prefix = parts[0] if len(parts) > 1 else "(root)"
            dir_buckets[prefix].append(f.omega_local)
        dir_rollup = sorted(
            [
                (name, sum(v) / len(v), len(v))
                for name, v in dir_buckets.items()
            ],
            key=lambda x: x[1],
            reverse=True,
        )[:8]

        svc = suite.get("service_context") or {}
        eco = suite.get("ecosystem") or {}
        impact = suite.get("impact_summary") or {}

        ctx = cls(
            display=outcome.repo_display,
            root=root_path,
            omega_index=float(outcome.omega_index),
            quality_grade=str(outcome.quality_grade),
            pillars=pillars,
            files=files,
            entities=entities,
            entity_summary=dict(outcome.entity_summary or {}),
            top_by_language=dict(outcome.top_by_language or {}),
            bayesian_quality=float(getattr(outcome, "bayesian_quality", 0)),
            epistemic_uncertainty=float(getattr(outcome, "epistemic_uncertainty", 0)),
            total_loc=int(outcome.total_loc),
            file_count=int(outcome.file_count),
            metric_suite=suite,
            baseline_report=baseline_report,
            cyclic_files=cyclic,
            dir_rollup=dir_rollup,
            lang_files=dict(lang_files),
            sorted_by_omega=sorted_omega,
            service_context=svc,
            ecosystem=eco,
            impact_summary=impact,
        )

        if root_path and root_path.is_dir() and files:
            file_triples = [(f.path, f.loc, f.omega_local) for f in files]
            entry = list(svc.get("entry_points") or [])
            ctx.source_scan = scan_sources(
                root_path, file_triples, entry_paths=entry
            )
            ctx.config_artifact_count = _count_config_artifacts(root_path)
            readme = root_path / "README.md"
            if readme.is_file():
                try:
                    ctx.readme_chars = min(32_000, readme.stat().st_size)
                except OSError:
                    pass

        return ctx


_CONFIG_MARKERS = (
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yaml",
    "Dockerfile",
    "kubernetes",
    "k8s",
    "helm",
    "terraform",
    ".github/workflows",
    "pyproject.toml",
    "package.json",
)


def _count_config_artifacts(root: Path) -> int:
    n = 0
    for name in _CONFIG_MARKERS:
        if (root / name).exists():
            n += 1
        elif name in ("kubernetes", "k8s", "helm", "terraform", ".github/workflows"):
            if any(root.glob(f"**/{name}")):
                n += 1
    return n


def top_files(
    ctx: DimensionContext,
    key: str,
    *,
    n: int = 5,
    reverse: bool = True,
) -> list[tuple[FileMetrics, float]]:
    scored = [(f, float(getattr(f, key))) for f in ctx.files]
    scored.sort(key=lambda x: x[1], reverse=reverse)
    return scored[:n]


def top_entities(
    ctx: DimensionContext,
    key: str,
    *,
    n: int = 5,
) -> list[tuple[EntityMetrics, float]]:
    scored = [(e, float(getattr(e, key))) for e in ctx.entities]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:n]
