"""Repository-level Ω-QFM analysis."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from omega.discover import RepoInventory
from omega.entities import EntityMetrics
from omega.metrics import FileMetrics
from omega.developer_guide import build_developer_guide
from omega.dimensions import build_repo_dimensions
from omega.narrative import build_business_sections, build_technical_sections
from omega.scan import scan_repository


@dataclass
class RepositoryOutcome:
    """Final outcome of a complete code analysis run."""

    root: str
    repo_display: str
    github_url: str | None
    analyzed_at: str
    omega_index: float
    quality_grade: str
    health_summary: str
    health_summary_business: str
    file_count: int
    total_loc: int
    pillars: dict[str, float]
    files: list[FileMetrics] = field(default_factory=list)
    hotspots: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    recommendations_business: list[str] = field(default_factory=list)
    bayesian_quality: float = 0.0
    epistemic_uncertainty: float = 0.0
    inventory: RepoInventory | None = None
    business: dict = field(default_factory=dict)
    technical: dict = field(default_factory=dict)
    top_by_language: dict[str, float] = field(default_factory=dict)
    entities: list[EntityMetrics] = field(default_factory=list)
    entity_summary: dict[str, int] = field(default_factory=dict)
    entity_hotspots: list[str] = field(default_factory=list)
    improvement_plan: list[dict] = field(default_factory=list)
    developer_guide: dict = field(default_factory=dict)
    dimensions: list[dict] = field(default_factory=list)


def _grade(omega: float) -> str:
    if omega < 30:
        return "A"
    if omega < 45:
        return "B"
    if omega < 60:
        return "C"
    if omega < 75:
        return "D"
    return "F"


def _health_summary_technical(omega: float, grade: str) -> str:
    if grade == "A":
        return "Repository field is stable; entropy and coupling are well bounded."
    if grade == "B":
        return "Acceptable quality with localized stress; monitor hotspots on next change."
    if grade == "C":
        return "Elevated structural disorder; refactor high-Ω modules before scaling features."
    if grade == "D":
        return "Significant quality debt; architecture drift and complexity dominate."
    return "Critical quality field; immediate remediation required on top hotspots."


def _health_summary_business(grade: str) -> str:
    return {
        "A": "Your software is in strong shape for growth and fast delivery.",
        "B": "Good overall health — fix highlighted files before they slow the team.",
        "C": "Quality debt is building — budget time for cleanup alongside features.",
        "D": "High maintenance burden — expect slower releases and more bugs until refactored.",
        "F": "Urgent attention needed — treat quality work as a top business priority.",
    }.get(grade, "Review the detailed sections below.")


def _repo_pillars(files: list[FileMetrics]) -> dict[str, float]:
    if not files:
        return {
            "structural_entropy": 0.0,
            "cyclomatic_pressure": 0.0,
            "coupling_field": 0.0,
            "topological_cycles": 0.0,
            "information_density": 0.0,
            "textual_entropy": 0.0,
            "max_omega_local": 0.0,
            "p95_omega_local": 0.0,
        }
    omegas = sorted(f.omega_local for f in files)
    p95_idx = min(len(omegas) - 1, int(len(omegas) * 0.95))
    return {
        "structural_entropy": round(sum(f.h_struct for f in files) / len(files), 3),
        "textual_entropy": round(sum(f.h_text for f in files) / len(files), 3),
        "cyclomatic_pressure": round(sum(f.cyclomatic for f in files) / len(files), 2),
        "coupling_field": round(
            sum(f.coupling_out + f.coupling_in for f in files) / len(files), 2
        ),
        "topological_cycles": float(
            sum(1 for f in files if f.coupling_out > 0 and f.coupling_in > 0)
        ),
        "information_density": round(
            sum(f.compression_ratio for f in files) / len(files), 2
        ),
        "max_omega_local": round(max(omegas), 2),
        "p95_omega_local": round(omegas[p95_idx], 2),
    }


def _bayesian_posterior(pillars: dict[str, float], omega: float) -> tuple[float, float]:
    expected_q = max(0.0, min(10.0, 10.0 - omega / 10.0))
    signals = [
        pillars["structural_entropy"] / 6.0,
        pillars["cyclomatic_pressure"] / 15.0,
        pillars["coupling_field"] / 5.0,
        omega / 100.0,
        pillars.get("p95_omega_local", omega) / 100.0,
    ]
    variance = sum(s**2 for s in signals) / len(signals)
    uncertainty = round(min(1.0, math.sqrt(variance)), 3)
    return round(expected_q, 2), uncertainty


def _entity_summary(entities: list[EntityMetrics]) -> dict[str, int]:
    summary = {"class": 0, "method": 0, "function": 0, "field": 0, "total": len(entities)}
    for e in entities:
        if e.entity_type in summary:
            summary[e.entity_type] += 1
    summary["high_risk"] = sum(
        1 for e in entities if e.risk_band in ("HIGH", "CRITICAL")
    )
    return summary


def _improvement_plan(entities: list[EntityMetrics], limit: int = 40) -> list[dict]:
    plan: list[dict] = []
    for e in entities:
        if e.risk_band not in ("MEDIUM", "HIGH", "CRITICAL"):
            if not e.implementation_plan:
                continue
        if (
            not e.implementation_plan
            and e.improvement_areas
            and e.improvement_areas[0].startswith("Metrics within")
        ):
            continue
        plan.append(
            {
                "entity_type": e.entity_type,
                "qualified_name": e.qualified_name,
                "file_path": e.file_path,
                "lines": f"{e.line_start}-{e.line_end}",
                "omega_local": e.omega_local,
                "risk_band": e.risk_band,
                "cyclomatic": e.cyclomatic,
                "nesting_depth": e.nesting_depth,
                "improvement_areas": list(e.improvement_areas),
                "improvement_areas_business": list(e.improvement_areas_business),
                "implementation_plan": list(e.implementation_plan),
                "implementation_summary": list(e.implementation_summary),
            }
        )
        if len(plan) >= limit:
            break
    return plan


def _entity_hotspots(entities: list[EntityMetrics], limit: int = 20) -> list[str]:
    return [
        f"{e.qualified_name} ({e.entity_type}, Ω={e.omega_local}, {e.file_path}:{e.line_start})"
        for e in entities
        if e.risk_band in ("HIGH", "CRITICAL", "MEDIUM")
    ][:limit]


def _recommendations(
    files: list[FileMetrics],
    pillars: dict[str, float],
    entities: list[EntityMetrics],
) -> tuple[list[str], list[str]]:
    tech: list[str] = []
    biz: list[str] = []
    for f in files:
        if f.risk_band in ("HIGH", "CRITICAL"):
            tech.append(
                f"Refactor `{f.path}` (Ω_local={f.omega_local}): "
                f"reduce cyclomatic={f.cyclomatic}, nesting={f.nesting_depth}, "
                f"language={f.language}."
            )
            biz.append(
                f"Assign engineering time to simplify `{f.path}` — "
                f"it is a top risk for bugs and slow delivery (score {f.omega_local}/100)."
            )
        elif f.risk_band == "MEDIUM" and len(tech) < 8:
            biz.append(
                f"Review `{f.path}` in the next sprint — complexity is above team average."
            )
    if pillars["coupling_field"] > 1.5:
        tech.append(
            "Decouple modules: coupling field strength "
            f"{pillars['coupling_field']:.2f} exceeds comfort threshold 1.5."
        )
        biz.append(
            "Reduce cross-team dependencies between modules to speed up parallel work."
        )
    if pillars["topological_cycles"] > 0:
        tech.append(
            f"Resolve {int(pillars['topological_cycles'])} dependency cycle(s) "
            "(β₁ proxy > 0): bidirectional module coupling increases fixpoint analysis cost."
        )
        biz.append(
            "Break circular dependencies — they cause unpredictable side effects when changing code."
        )
    if pillars.get("p95_omega_local", 0) > 55:
        tech.append(
            f"95th-percentile Ω_local is {pillars['p95_omega_local']:.1f} — "
            "tail modules dominate risk; prioritize P95 hotspot remediation."
        )
    for e in entities[:8]:
        if e.risk_band in ("HIGH", "CRITICAL"):
            tech.append(
                f"[{e.entity_type}] `{e.qualified_name}` @ {e.file_path}:{e.line_start} — "
                f"Ω={e.omega_local}: {e.improvement_areas[0]}"
            )
            biz.append(
                f"Fix {e.entity_type} '{e.qualified_name.split('.')[-1]}' in {e.file_path} — "
                f"{e.improvement_areas_business[0]}"
            )
    if not tech:
        tech.append("Maintain current structure; re-run Ω analysis on each significant PR.")
        biz.append("No urgent hotspots — continue quality checks before major releases.")
    return tech, biz


def _top_by_language(files: list[FileMetrics]) -> dict[str, float]:
    by_lang: dict[str, list[float]] = {}
    for f in files:
        by_lang.setdefault(f.language, []).append(f.omega_local)
    return {lang: round(sum(v) / len(v), 2) for lang, v in sorted(by_lang.items())}


def analyze_repository(
    root: str | Path,
    *,
    github_url: str | None = None,
    repo_display: str | None = None,
) -> RepositoryOutcome:
    root_path = Path(root).resolve()
    files, entities, inventory = scan_repository(root_path)

    display = repo_display or root_path.name
    analyzed_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    if not files:
        empty_inv = inventory
        outcome = RepositoryOutcome(
            root=str(root_path),
            repo_display=display,
            github_url=github_url,
            analyzed_at=analyzed_at,
            omega_index=0.0,
            quality_grade="N/A",
            health_summary="No analyzable source files found.",
            health_summary_business="No source code files matched supported languages.",
            file_count=0,
            total_loc=0,
            pillars=_repo_pillars([]),
            files=[],
            hotspots=[],
            recommendations=["Add supported source files or check path / clone URL."],
            recommendations_business=["Verify repository contains code in supported languages."],
            inventory=empty_inv,
        )
        outcome.business = build_business_sections(outcome)
        outcome.technical = build_technical_sections(outcome)
        outcome.dimensions = [d.to_dict() for d in build_repo_dimensions(outcome)]
        outcome.developer_guide = build_developer_guide(outcome)
        return outcome

    omega_index = round(sum(f.omega_local for f in files) / len(files), 2)
    grade = _grade(omega_index)
    pillars = _repo_pillars(files)
    bayesian_q, uncertainty = _bayesian_posterior(pillars, omega_index)
    hotspots = [
        f.path
        for f in files
        if f.risk_band in ("HIGH", "CRITICAL", "MEDIUM")
    ][:15]
    tech_recs, biz_recs = _recommendations(files, pillars, entities)
    ent_summary = _entity_summary(entities)
    ent_plan = _improvement_plan(entities)
    ent_hot = _entity_hotspots(entities)

    outcome = RepositoryOutcome(
        root=str(root_path),
        repo_display=display,
        github_url=github_url,
        analyzed_at=analyzed_at,
        omega_index=omega_index,
        quality_grade=grade,
        health_summary=_health_summary_technical(omega_index, grade),
        health_summary_business=_health_summary_business(grade),
        file_count=len(files),
        total_loc=sum(f.loc for f in files),
        pillars=pillars,
        files=files,
        hotspots=hotspots,
        recommendations=tech_recs,
        recommendations_business=biz_recs,
        bayesian_quality=bayesian_q,
        epistemic_uncertainty=uncertainty,
        inventory=inventory,
        top_by_language=_top_by_language(files),
        entities=entities,
        entity_summary=ent_summary,
        entity_hotspots=ent_hot,
        improvement_plan=ent_plan,
        dimensions=[],
    )
    outcome.dimensions = [d.to_dict() for d in build_repo_dimensions(outcome)]
    outcome.developer_guide = build_developer_guide(outcome)
    outcome.business = build_business_sections(outcome)
    outcome.technical = build_technical_sections(outcome)
    return outcome
