"""Core types and helpers for Ω-QFM repository dimensions."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class RepoDimension:
    """One measurable quality dimension with repo-local evidence.

    Repo letter grade (A–F) and Ω index come from per-file field metrics only.
    Dimensions are contextual lenses; ``applicable`` gates whether this repo/service
    qualifies for a given lens. ``contributes_to_grade`` is always false today.
    """

    id: str
    name: str
    score: float
    band: str
    weight: float
    repo_aggregate: float
    unit: str
    summary_technical: str
    summary_business: str
    family: str = "field"
    applicable: bool = True
    contributes_to_grade: bool = False
    qualification: str = ""
    evidence: list[str] = field(default_factory=list)
    evidence_symbols: list[str] = field(default_factory=list)
    actions_in_repo: list[str] = field(default_factory=list)
    top_contributors: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def band(score: float) -> str:
    if score < 35:
        return "LOW"
    if score < 55:
        return "MEDIUM"
    if score < 75:
        return "HIGH"
    return "CRITICAL"


def norm_score(value: float, scale: float) -> float:
    if scale <= 0:
        return 0.0
    return round(min(100.0, max(0.0, (value / scale) * 100.0)), 1)


def dim(
    *,
    id: str,
    name: str,
    family: str,
    score: float,
    weight: float,
    repo_aggregate: float,
    unit: str,
    summary_technical: str,
    summary_business: str,
    evidence: list[str] | None = None,
    evidence_symbols: list[str] | None = None,
    actions_in_repo: list[str] | None = None,
    top_contributors: list[dict[str, Any]] | None = None,
    applicable: bool = True,
    contributes_to_grade: bool = False,
    qualification: str = "",
) -> RepoDimension:
    s = norm_score(score, 100.0) if score > 100 else round(min(100.0, max(0.0, score)), 1)
    return RepoDimension(
        id=id,
        name=name,
        score=s,
        band=band(s),
        weight=weight,
        repo_aggregate=round(float(repo_aggregate), 4)
        if isinstance(repo_aggregate, float)
        else float(repo_aggregate),
        unit=unit,
        family=family,
        applicable=applicable,
        contributes_to_grade=contributes_to_grade,
        qualification=qualification,
        summary_technical=summary_technical,
        summary_business=summary_business,
        evidence=evidence or [],
        evidence_symbols=evidence_symbols or [],
        actions_in_repo=actions_in_repo or [],
        top_contributors=top_contributors or [],
    )


def applicable_dimensions(dims: list[RepoDimension]) -> list[RepoDimension]:
    """Dimensions this repository/service qualifies for (excludes gated families)."""
    return [d for d in dims if d.applicable]
