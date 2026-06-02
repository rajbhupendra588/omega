"""Developer-facing action guide: why each item is risky and what to do in this repo."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from omega.entities import EntityMetrics
from omega.metrics import FileMetrics

# Bump when guide shape/logic changes (triggers backfill on report read).
GUIDE_VERSION = 2

SPRINT_SYMBOL_CAP = 22
FILE_GROUP_MIN = 2
FILE_GROUP_TOP_DETAIL = 5
MIN_ENTITY_RISK = frozenset({"CRITICAL", "HIGH", "MEDIUM"})
MIN_FILE_RISK = frozenset({"CRITICAL", "HIGH", "MEDIUM"})


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
    implementation_diffs: list[dict] = field(default_factory=list)
    action_tier: str = "sprint"  # sprint | backlog | summary
    grouped_files: list[dict[str, Any]] = field(default_factory=list)

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
    steps.append("Add focused unit tests around the refactored helpers before merging.")
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
    has_diffs = bool(
        (plan_item or {}).get("implementation_diffs")
        or (plan_item or {}).get("implementation_plan")
        or e.implementation_diffs
        or e.implementation_plan
    )
    if has_diffs:
        steps.append(
            f"Use **How to fix it** below for `{e.qualified_name}` in `{e.file_path}` "
            "(red = current code, green = suggested change)."
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
    diffs = (
        list(plan_item.get("implementation_diffs", []))
        if plan_item
        else list(e.implementation_diffs)
    )

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
        implementation_diffs=diffs,
        action_tier="sprint",
    )


def _action_from_file_group(files: list[FileMetrics], priority: int) -> DeveloperAction:
    files = sorted(files, key=lambda f: (-f.omega_local, f.path))
    top = files[:FILE_GROUP_TOP_DETAIL]
    rest = len(files) - len(top)
    avg_omega = sum(f.omega_local for f in files) / len(files)
    worst = files[0]

    file_rows = [
        {
            "path": f.path,
            "omega_local": f.omega_local,
            "risk_band": f.risk_band,
            "cyclomatic": f.cyclomatic,
            "nesting_depth": f.nesting_depth,
        }
        for f in files
    ]

    steps = [
        "These modules have no single worst function identified yet — apply the same cleanup pattern to each.",
        "For each file: reduce cyclomatic complexity to ≤8, extract the deepest nested block into a helper, add tests.",
    ]
    for f in top:
        steps.append(
            f"• `{f.path}` — Ω={f.omega_local}, cyclomatic {f.cyclomatic}, nesting {f.nesting_depth}"
        )
    if rest > 0:
        steps.append(f"• …and {rest} more module(s) with similar metrics (expand list below).")

    return DeveloperAction(
        priority=priority,
        category="module_health_group",
        title=f"{len(files)} modules need stabilization",
        location=worst.path,
        risk_band=worst.risk_band,
        symbol=None,
        metrics={
            "omega_local": round(avg_omega, 2),
            "module_count": len(files),
            "worst_omega": worst.omega_local,
        },
        why_risky=(
            f"{len(files)} files score {worst.risk_band} or higher on Ω_local without a dedicated symbol fix yet. "
            f"Worst: `{worst.path}` (Ω={worst.omega_local}, cyclomatic {worst.cyclomatic}). "
            "Tackle the top files in the list first; the same refactor playbook applies to each."
        ),
        what_to_do=steps,
        action_tier="summary",
        grouped_files=file_rows,
    )


def _action_from_dimension(d: dict[str, Any], priority: int) -> DeveloperAction | None:
    if not d.get("actions_in_repo"):
        return None
    evidence = d.get("evidence") or []
    loc = "this repository"
    if evidence:
        loc = evidence[0].split("—")[0].strip("` ")
    return DeveloperAction(
        priority=priority,
        category="architecture",
        title=d["name"],
        location=loc,
        risk_band=d["band"],
        symbol=None,
        metrics={"dimension_score": d["score"], "repo_aggregate": d["repo_aggregate"]},
        why_risky=(
            f"{d['summary_technical']}"
            + (f" Evidence: {evidence[0]}" if evidence else "")
        ),
        what_to_do=list(d.get("actions_in_repo", [])),
        action_tier="backlog",
    )


def _collect_symbol_actions(
    outcome: Any,
    entities_by_name: dict[str, EntityMetrics],
    plan_items: list[dict],
) -> list[DeveloperAction]:
    actions: list[DeveloperAction] = []
    seen: set[str] = set()

    for item in plan_items:
        qn = item["qualified_name"]
        if qn in seen:
            continue
        e = entities_by_name.get(qn)
        if not e or e.risk_band not in MIN_ENTITY_RISK:
            continue
        seen.add(qn)
        actions.append(_action_from_entity(e, item, _priority_for_band(e.risk_band)))

    if len(actions) < SPRINT_SYMBOL_CAP:
        for e in sorted(
            getattr(outcome, "entities", []),
            key=lambda x: (_priority_for_band(x.risk_band), -x.omega_local),
        ):
            if e.qualified_name in seen or e.risk_band not in MIN_ENTITY_RISK:
                continue
            if not (e.implementation_diffs or e.implementation_plan or e.improvement_areas):
                continue
            seen.add(e.qualified_name)
            actions.append(_action_from_entity(e, None, _priority_for_band(e.risk_band)))
            if len(actions) >= SPRINT_SYMBOL_CAP:
                break

    return actions


def _files_with_symbol_coverage(entities: list[EntityMetrics]) -> set[str]:
    return {
        e.file_path
        for e in entities
        if e.risk_band in MIN_ENTITY_RISK
    }


def build_developer_guide(outcome: Any) -> dict[str, Any]:
    """
  Sprint queue: symbol-level fixes first (with code when available).
  Summary: grouped orphan modules without symbol coverage.
  Backlog: remaining symbols + architecture dimensions.
    """
    entities: list[EntityMetrics] = list(getattr(outcome, "entities", []))
    entities_by_name = {e.qualified_name: e for e in entities}
    plan_items: list[dict] = list(getattr(outcome, "improvement_plan", []))

    symbol_actions = _collect_symbol_actions(outcome, entities_by_name, plan_items)
    covered_files = _files_with_symbol_coverage(entities)

    orphan_files: list[FileMetrics] = []
    for f in sorted(
        getattr(outcome, "files", []),
        key=lambda x: (_priority_for_band(x.risk_band), -x.omega_local),
    ):
        if f.risk_band not in MIN_FILE_RISK:
            continue
        if f.path in covered_files:
            continue
        orphan_files.append(f)

    actions: list[DeveloperAction] = list(symbol_actions)

    if len(orphan_files) >= FILE_GROUP_MIN:
        actions.append(
            _action_from_file_group(orphan_files, priority=3)
        )
    elif len(orphan_files) == 1:
        f = orphan_files[0]
        actions.append(
            DeveloperAction(
                priority=_priority_for_band(f.risk_band),
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
                },
                why_risky=_why_file_risky(f),
                what_to_do=_what_to_do_file(f),
                action_tier="backlog",
            )
        )

    seen_titles: set[str] = {a.title for a in actions}
    for d in getattr(outcome, "dimensions", []):
        if d.get("id") in ("language_profile", "information_density"):
            continue
        if not d.get("applicable", True) or d.get("contributes_to_grade"):
            continue
        act = _action_from_dimension(d, 10)
        if act and act.title not in seen_titles:
            seen_titles.add(act.title)
            actions.append(act)

    symbol_only = [a for a in actions if a.symbol]
    symbol_only.sort(
        key=lambda a: (
            _priority_for_band(a.risk_band),
            -float(a.metrics.get("omega_local", 0)),
        )
    )
    for i, a in enumerate(symbol_only):
        a.action_tier = "sprint" if i < SPRINT_SYMBOL_CAP else "backlog"

    non_symbol = [a for a in actions if not a.symbol]
    actions = symbol_only + non_symbol

    ordered: list[DeveloperAction] = []
    for tier in ("sprint", "summary", "backlog"):
        ordered.extend(a for a in actions if a.action_tier == tier)

    for i, a in enumerate(ordered, start=1):
        a.priority = i

    sprint_n = sum(1 for a in ordered if a.action_tier == "sprint")
    group_n = sum(1 for a in ordered if a.category == "module_health_group")
    orphan_n = len(orphan_files)

    intro = (
        f"This section is for engineers working on **{outcome.repo_display}**. "
        f"**{sprint_n} symbol-level fixes** are prioritized first (with code diffs when available). "
    )
    if group_n:
        intro += (
            f"**{orphan_n} modules** without a single worst function are grouped into one summary card. "
        )
    intro += (
        f"Repository Ω={outcome.omega_index}, grade {outcome.quality_grade}."
    )

    return {
        "guide_version": GUIDE_VERSION,
        "introduction": intro,
        "how_to_read": [
            "**Sprint queue** (priorities 1–N): fix named functions/classes — use red/green code when shown.",
            "**Module summary**: batch of similar hot files — same playbook, start with the highest Ω listed.",
            "**Backlog**: architecture items and lower-priority symbols for later.",
        ],
        "sprint_count": sprint_n,
        "module_group_count": orphan_n if group_n else 0,
        "action_count": len(ordered),
        "actions": [a.to_dict() for a in ordered],
    }


def build_developer_guide_from_report(report: dict[str, Any]) -> dict[str, Any]:
    """Rebuild developer guide from saved JSON."""
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
    if dg.get("guide_version") == GUIDE_VERSION and "actions" in dg:
        return report, False
    guide = build_developer_guide_from_report(report)
    return {**report, "developer_guide": guide}, True
