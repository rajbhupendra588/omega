"""Developer-facing action guide: why each item is risky and what to do in this repo."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from omega.entities import EntityMetrics
from omega.metrics import FileMetrics


@dataclass
class DeveloperAction:
    priority: int
    category: str
    title: str
    location: str
    risk_band: str
    symbol: str | None
    metrics: dict[str, float | int]
    why_risky: str
    what_to_do: list[str] = field(default_factory=list)
    implementation_plan: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _priority_for_band(band: str) -> int:
    return {"CRITICAL": 1, "HIGH": 2, "MEDIUM": 3, "LOW": 4}.get(band, 5)


def _why_file_risky(f: FileMetrics) -> str:
    parts = [
        f"`{f.path}` scores Ω_local={f.omega_local} ({f.risk_band} band; threshold MEDIUM≥35, HIGH≥55).",
        f"McCabe cyclomatic complexity is {f.cyclomatic} — each branch doubles paths a tester must reason about.",
        f"Max nesting depth is {f.nesting_depth}; beyond depth 4, reviewers miss edge cases in code review.",
    ]
    if f.coupling_out + f.coupling_in > 0:
        parts.append(
            f"Internal coupling: {f.coupling_out} outbound imports, {f.coupling_in} inbound — "
            "changes here trigger compile/test failures in dependent modules."
        )
    if f.h_struct > 3.5:
        parts.append(
            f"Structural entropy H_struct={f.h_struct:.2f} — AST shape varies heavily in this file, "
            "so patterns are inconsistent and refactors are error-prone."
        )
    return " ".join(parts)


def _what_to_do_file(f: FileMetrics) -> list[str]:
    steps = [
        f"Open `{f.path}` and list every `if`/`for`/`while` block; target cyclomatic {f.cyclomatic} → ≤8.",
        f"Extract the deepest nested block (depth {f.nesting_depth}) into a private helper in the same file.",
    ]
    if f.coupling_out >= 3:
        steps.append(
            f"Reduce imports from `{f.path}`: introduce an interface module or move shared types to a leaf package."
        )
    if f.coupling_in >= 2 and f.coupling_out > 0:
        steps.append(
            f"Break the import cycle involving `{f.path}` (in={f.coupling_in}, out={f.coupling_out}) "
            "by moving shared code to a third module both sides import."
        )
    steps.append(f"Add focused unit tests around the refactored helpers before merging.")
    return steps


def _why_entity_risky(e: EntityMetrics) -> str:
    base = (
        f"`{e.qualified_name}` ({e.entity_type}) in `{e.file_path}` L{e.line_start}–{e.line_end} "
        f"has Ω={e.omega_local} ({e.risk_band}). "
    )
    reasons: list[str] = [base]
    if e.cyclomatic >= 10:
        reasons.append(
            f"Cyclomatic {e.cyclomatic} means {e.cyclomatic} independent paths — "
            "one-line fixes often break an untested branch."
        )
    elif e.cyclomatic >= 6:
        reasons.append(
            f"Cyclomatic {e.cyclomatic} exceeds the ~5 guideline for a single function/method body."
        )
    if e.nesting_depth >= 4:
        reasons.append(
            f"Nesting depth {e.nesting_depth} hides null/edge handling; stack traces become hard to follow in production."
        )
    if e.loc >= 45:
        reasons.append(
            f"{e.loc} LOC in one {e.entity_type} violates single-responsibility — diffs touch unrelated logic."
        )
    if e.parameter_count >= 5:
        reasons.append(
            f"{e.parameter_count} parameters increase call-site mistakes and mock setup cost in tests."
        )
    if e.improvement_areas:
        reasons.append(e.improvement_areas[0])
    return " ".join(reasons)


def _what_to_do_entity(e: EntityMetrics, plan_item: dict | None) -> list[str]:
    steps: list[str] = []
    if plan_item and plan_item.get("implementation_plan"):
        steps.append(
            f"Follow the implementation sketch for `{e.qualified_name}` in `{e.file_path}` "
            "(see Implementation blocks below or `omega-implementations.md`)."
        )
    for area in e.improvement_areas[:3]:
        if not area.startswith("Metrics within"):
            steps.append(area)
    if e.cyclomatic >= 8:
        steps.append(
            f"Split `{e.qualified_name}` into orchestrator + helpers; keep each helper cyclomatic ≤6."
        )
    if e.nesting_depth >= 4:
        steps.append(
            f"Replace nested conditionals in `{e.qualified_name}` with guard clauses at the top of the function."
        )
    if not steps:
        steps.append(f"Review `{e.qualified_name}` on next change; keep Ω below 35.")
    return steps


def _action_from_entity(e: EntityMetrics, plan_item: dict | None, priority: int) -> DeveloperAction:
    category = "control_flow"
    if e.cyclomatic >= 10:
        category = "control_flow"
    elif e.nesting_depth >= 4:
        category = "nesting"
    elif e.parameter_count >= 5:
        category = "api_surface"
    elif e.entity_type == "class":
        category = "class_design"

    impl = list(plan_item.get("implementation_plan", [])) if plan_item else list(e.implementation_plan)

    return DeveloperAction(
        priority=priority,
        category=category,
        title=f"Fix {e.entity_type} `{e.qualified_name}`",
        location=f"{e.file_path}:{e.line_start}-{e.line_end}",
        risk_band=e.risk_band,
        symbol=e.qualified_name,
        metrics={
            "omega_local": e.omega_local,
            "cyclomatic": e.cyclomatic,
            "nesting_depth": e.nesting_depth,
            "loc": e.loc,
            "parameter_count": e.parameter_count,
        },
        why_risky=_why_entity_risky(e),
        what_to_do=_what_to_do_entity(e, plan_item),
        implementation_plan=impl,
    )


def _action_from_file(f: FileMetrics, priority: int) -> DeveloperAction:
    return DeveloperAction(
        priority=priority,
        category="module_health",
        title=f"Stabilize module `{f.path}`",
        location=f.path,
        risk_band=f.risk_band,
        symbol=None,
        metrics={
            "omega_local": f.omega_local,
            "cyclomatic": f.cyclomatic,
            "nesting_depth": f.nesting_depth,
            "coupling_out": f.coupling_out,
            "coupling_in": f.coupling_in,
            "h_struct": f.h_struct,
        },
        why_risky=_why_file_risky(f),
        what_to_do=_what_to_do_file(f),
    )


def _action_from_dimension(d: dict[str, Any], priority: int) -> DeveloperAction | None:
    if not d.get("actions_in_repo"):
        return None
    return DeveloperAction(
        priority=priority,
        category="architecture",
        title=d["name"],
        location=d.get("evidence", ["this repository"])[0].split("—")[0].strip("` "),
        risk_band=d["band"],
        symbol=None,
        metrics={"dimension_score": d["score"], "repo_aggregate": d["repo_aggregate"]},
        why_risky=f"{d['summary_technical']} Evidence: {d.get('evidence', [''])[0]}",
        what_to_do=list(d.get("actions_in_repo", [])[:4]),
    )


def build_developer_guide(outcome: Any) -> dict[str, Any]:
    """
    Structured developer section: prioritized actions with risk rationale
    and concrete steps tied to this repository's paths and symbols.
    """
    actions: list[DeveloperAction] = []
    seen_keys: set[str] = set()

    plan_by_symbol = {
        item["qualified_name"]: item for item in getattr(outcome, "improvement_plan", [])
    }

    for e in sorted(
        getattr(outcome, "entities", []),
        key=lambda x: (-_priority_for_band(x.risk_band), -x.omega_local),
    ):
        if e.risk_band not in ("MEDIUM", "HIGH", "CRITICAL"):
            if not e.implementation_plan:
                continue
        key = e.qualified_name
        if key in seen_keys:
            continue
        seen_keys.add(key)
        pri = _priority_for_band(e.risk_band)
        actions.append(_action_from_entity(e, plan_by_symbol.get(key), pri))

    file_symbols = {e.file_path for e in getattr(outcome, "entities", []) if e.risk_band in ("HIGH", "CRITICAL", "MEDIUM")}
    for f in sorted(
        getattr(outcome, "files", []),
        key=lambda x: (-_priority_for_band(x.risk_band), -x.omega_local),
    ):
        if f.risk_band not in ("HIGH", "CRITICAL"):
            continue
        if f.path in file_symbols and f.risk_band != "CRITICAL":
            continue
        key = f"file:{f.path}"
        if key in seen_keys:
            continue
        seen_keys.add(key)
        actions.append(_action_from_file(f, _priority_for_band(f.risk_band)))

    dim_added = 0
    for d in getattr(outcome, "dimensions", []):
        if d.get("band") not in ("HIGH", "CRITICAL", "MEDIUM"):
            continue
        if d.get("id") in ("language_profile", "information_density"):
            continue
        act = _action_from_dimension(d, 10 + dim_added)
        if act and act.title not in seen_keys:
            seen_keys.add(act.title)
            actions.append(act)
            dim_added += 1
            if dim_added >= 4:
                break

    actions.sort(key=lambda a: (a.priority, -float(a.metrics.get("omega_local", 0))))

    for i, a in enumerate(actions, start=1):
        a.priority = i

    intro = (
        f"This section is for engineers working on **{outcome.repo_display}**. "
        f"Each item names a concrete location in this repository, explains **why** it increases "
        f"defect and maintenance risk (using Ω-QFM metrics), and lists **what to change** before "
        f"shipping related features. Repository Ω={outcome.omega_index}, grade {outcome.quality_grade}."
    )

    return {
        "introduction": intro,
        "how_to_read": [
            "Work top-to-bottom by priority (1 = do first).",
            "**Why risky** ties cyclomatic complexity, nesting, coupling, and Ω_local to test/review cost.",
            "**What to do** are file-local steps — not generic best practices.",
            "When **Implementation plan** blocks appear, use them as copy-paste starting points in this repo.",
        ],
        "action_count": len(actions),
        "actions": [a.to_dict() for a in actions[:35]],
    }


def build_developer_guide_from_report(report: dict[str, Any]) -> dict[str, Any]:
    """Rebuild developer guide from saved JSON (backfill)."""
    existing = report.get("developer_guide") or {}
    if existing.get("actions"):
        return existing

    from omega.dimensions import build_dimensions_from_report, entity_from_report_dict, file_from_report_dict

    class _Snap:
        pass

    s = _Snap()
    s.repo_display = report.get("repo_display", "repository")
    s.omega_index = report.get("omega_index", 0)
    s.quality_grade = report.get("quality_grade", "?")
    s.improvement_plan = report.get("improvement_plan", [])
    s.dimensions = report.get("dimensions") or build_dimensions_from_report(report)
    s.files = [file_from_report_dict(f) for f in report.get("files", [])]
    s.entities = [entity_from_report_dict(e) for e in report.get("entities", [])]
    return build_developer_guide(s)


def ensure_report_has_developer_guide(report: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    dg = report.get("developer_guide") or {}
    if dg.get("actions"):
        return report, False
    guide = build_developer_guide_from_report(report)
    if not guide.get("actions"):
        report["developer_guide"] = guide
        return report, False
    report = {**report, "developer_guide": guide}
    return report, True
