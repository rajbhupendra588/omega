"""Extensible registry for Ω-QFM mathematical and ecosystem metrics."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Callable


class MetricCategory(str, Enum):
    """Metric families — extend by registering new calculators."""

    FIELD = "field"  # code quality field observables
    BUSINESS = "business"  # service / product context
    UPSTREAM = "upstream"  # dependencies this service relies on
    DOWNSTREAM = "downstream"  # consumers / outbound blast radius
    IMPACT = "impact"  # cross-service composite


@dataclass(frozen=True)
class MetricDefinition:
    """Static definition of one measurable quantity."""

    id: str
    name: str
    category: MetricCategory
    unit: str
    formula: str
    weight: float = 1.0


@dataclass
class MetricRecord:
    """Computed metric instance with dual-audience narrative."""

    id: str
    name: str
    category: str
    value: float
    unit: str
    formula: str
    band: str
    weight: float
    summary_technical: str
    summary_business: str
    evidence: list[str] = field(default_factory=list)
    related_service: str | None = None
    edge_kind: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


MetricCalculator = Callable[["MetricComputeContext"], MetricRecord | list[MetricRecord]]


@dataclass
class MetricComputeContext:
    """Inputs available to every registered metric calculator."""

    root: str
    repo_display: str
    omega_index: float
    quality_grade: str
    bayesian_quality: float
    epistemic_uncertainty: float
    file_count: int
    total_loc: int
    pillars: dict[str, float]
    files: list[Any]
    entities: list[Any]
    entity_summary: dict[str, int]
    top_by_language: dict[str, float]
    service_context: dict[str, Any]
    ecosystem: dict[str, Any]


def band_from_score(score: float) -> str:
    """Shared risk band for 0–100 stress scores (higher = worse)."""
    if score < 35:
        return "LOW"
    if score < 55:
        return "MEDIUM"
    if score < 75:
        return "HIGH"
    return "CRITICAL"


def clamp100(value: float) -> float:
    return round(min(100.0, max(0.0, value)), 2)


class MetricRegistry:
    """Register N metric calculators; run against a shared context."""

    def __init__(self) -> None:
        self._definitions: dict[str, MetricDefinition] = {}
        self._calculators: dict[str, MetricCalculator] = {}

    def register(
        self,
        definition: MetricDefinition,
        calculator: MetricCalculator,
    ) -> None:
        self._definitions[definition.id] = definition
        self._calculators[definition.id] = calculator

    @property
    def definitions(self) -> list[MetricDefinition]:
        return list(self._definitions.values())

    def compute_all(self, ctx: MetricComputeContext) -> list[MetricRecord]:
        records: list[MetricRecord] = []
        for mid in self._definitions:
            calc = self._calculators[mid]
            result = calc(ctx)
            if isinstance(result, list):
                records.extend(result)
            else:
                records.append(result)
        return records
