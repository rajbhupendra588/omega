"""Generate technical and business narratives for reports."""

from __future__ import annotations

from typing import TYPE_CHECKING

from omega.metrics import FileMetrics

if TYPE_CHECKING:
    from omega.analyzer import RepositoryOutcome


def _business_risk_label(grade: str) -> str:
    return {
        "A": "Low operational risk",
        "B": "Moderate risk — watch key modules",
        "C": "Elevated risk — plan remediation",
        "D": "High risk — delays likely on changes",
        "F": "Critical risk — immediate action required",
    }.get(grade, "Unknown")


def _business_grade_explanation_plain(grade: str, omega: float) -> str:
    explanations = {
        "A": (
            f"Your codebase scores {omega:.1f} on the Omega Index (lower is healthier). "
            "This is like a building inspection rating of Excellent: the structure is sound, "
            "changes are unlikely to cause surprise failures, and your team can ship with confidence."
        ),
        "B": (
            f"Omega Index {omega:.1f} indicates Good health with a few stress points. "
            "Think of it as a car that runs well but needs scheduled maintenance on specific parts."
        ),
        "C": (
            f"Omega Index {omega:.1f} means Fair quality — technical debt is accumulating. "
            "New features will cost more time and money until problem areas are simplified."
        ),
        "D": (
            f"Omega Index {omega:.1f} signals Poor health. "
            "Every change has a higher chance of breaking something else — similar to renovating a house with hidden wiring issues."
        ),
        "F": (
            f"Omega Index {omega:.1f} is Critical. "
            "The cost of change is very high; defects and delays are likely without focused refactoring."
        ),
    }
    return explanations.get(grade, f"Omega Index is {omega:.1f}.")


def build_business_sections(outcome: "RepositoryOutcome") -> dict[str, str | list[str]]:
    """Plain-language sections for executives and product owners."""
    p = outcome.pillars
    sections: dict[str, str | list[str]] = {}

    n_langs = len(outcome.top_by_language) or (
        len(outcome.inventory.by_language) if outcome.inventory else 0
    )
    es = outcome.entity_summary
    entity_line = ""
    if es.get("total", 0) > 0:
        entity_line = (
            f" Granular scan: {es['total']} symbols measured "
            f"({es.get('class', 0)} classes, {es.get('method', 0)} methods, "
            f"{es.get('function', 0)} functions, {es.get('field', 0)} fields), "
            f"{es.get('high_risk', 0)} high-risk symbols."
        )
    sections["executive_summary"] = (
        f"{outcome.repo_display} was analyzed across {outcome.file_count:,} source files "
        f"({outcome.total_loc:,} lines of active code) in {n_langs} languages.{entity_line} "
        f"Overall quality grade: {outcome.quality_grade} ({_business_risk_label(outcome.quality_grade)}). "
        f"{_business_grade_explanation_plain(outcome.quality_grade, outcome.omega_index)}"
    )

    sections["what_omega_means"] = (
        "The Omega Index is a single health score for your entire repository (0–100). "
        "Lower is better. It combines how complicated the code is, how tangled modules are, "
        "and how unpredictable the structure is — not just how many lines you have."
    )

    sections["confidence"] = (
        f"We estimate overall product quality at {outcome.bayesian_quality:.1f} out of 10 "
        f"with {outcome.epistemic_uncertainty * 100:.0f}% uncertainty. "
        + (
            "The signals are consistent — you can trust this assessment for planning."
            if outcome.epistemic_uncertainty < 0.35
            else "Several signals disagree — treat this as directional and validate with your team."
        )
    )

    cost_map = {"A": "low", "B": "moderate", "C": "rising", "D": "high", "F": "very high"}
    sections["business_impact"] = [
        f"Cost of change: {cost_map.get(outcome.quality_grade, 'unknown')} — "
        "how expensive each new feature or bugfix becomes.",
        f"Structural complexity: entropy average {p['structural_entropy']:.2f} — "
        "higher means the code has more varied, harder-to-follow patterns.",
        f"Decision paths: average {p['cyclomatic_pressure']:.1f} branches per file — "
        "more branches mean more test cases needed and more ways bugs hide.",
        f"Team coupling: {p['coupling_field']:.2f} — "
        "high values mean teams step on each other's files more often.",
        f"Architecture loops: {int(p['topological_cycles'])} circular dependencies detected — "
        "these slow refactors and increase regression risk.",
    ]

    if outcome.hotspots:
        sections["priority_fixes"] = [
            f"{h} — this file stresses the quality field; prioritize review or refactor."
            for h in outcome.hotspots[:10]
        ]
    else:
        sections["priority_fixes"] = [
            "No critical hotspots in the top tier. Continue monitoring on each release."
        ]

    sections["recommendations_business"] = [
        _business_rec(r) for r in outcome.recommendations
    ] + outcome.recommendations_business

    sections["entity_improvement_plan"] = [
        f"{item['qualified_name']} ({item['entity_type']}, lines {item['lines']}): "
        f"{item['improvement_areas_business'][0]}"
        for item in outcome.improvement_plan[:25]
    ] or ["No class/method/field required urgent changes at symbol level."]

    sections["for_non_technical_stakeholders"] = (
        "You do **not** need to read cyclomatic complexity or entropy formulas. "
        "Focus on: (1) Letter grade A–F, (2) Multi-dimensional profile (repo-specific), "
        "(3) Entity improvement plan, (4) Hotspot file list."
    )

    if outcome.dimensions:
        sections["quality_dimensions_business"] = [
            f"**{d['name']}** ({d['band']}): {d['summary_business']}"
            + (
                f" — e.g. {d['evidence'][0]}"
                if d.get("evidence")
                else ""
            )
            for d in outcome.dimensions
        ]
        sections["dimension_actions_business"] = [
            act
            for d in outcome.dimensions
            for act in d.get("actions_in_repo", [])[:2]
        ][:12]

    return sections


def _business_rec(tech: str) -> str:
    if "Refactor" in tech and "`" in tech:
        return tech.replace("Ω_local=", "health score ").replace("cyclomatic=", "branch count ")
    if "Decouple" in tech:
        return "Split tightly linked modules so teams can work independently without breaking each other's code."
    if "dependency cycles" in tech:
        return "Remove circular dependencies between modules — they create deadlock-style maintenance problems."
    if "Maintain current" in tech:
        return "Keep current practices; run Omega again before major releases."
    return tech


def build_technical_sections(outcome: "RepositoryOutcome") -> dict[str, str | list[str]]:
    """Mathematical and engineering sections."""
    p = outcome.pillars
    inv = outcome.inventory

    sections: dict[str, str | list[str]] = {}

    sections["abstract"] = (
        "This report applies the Omega Quality Field Manifold (Ω-QFM) framework: a multi-scale "
        "composition of information-theoretic entropy, control-flow complexity, coupling graph topology, "
        "and Bayesian fusion over observables. Repository treated as a weighted field "
        "Phi: M -> R>=0 over module manifold M."
    )

    sections["aggregate_formulas"] = [
        "Repository Omega Index (arithmetic mean of local fields):",
        f"  Omega_repo = (1/|F|) * sum(Omega_local(f)) = {outcome.omega_index}",
        "Shannon structural entropy per file (AST or keyword proxy):",
        "  H_struct(F) = -sum_n p(n) log2 p(n)",
        "Textual entropy over token stream:",
        "  H_text(F) = -sum_t p(t) log2 p(t)",
        "Local quality field per file/class/method/field (weighted normalization, higher = worse):",
        "  Omega_local = 0.28*H_s + 0.25*C + 0.18*N + 0.17*K_out + 0.12*R",
        "  Entity-level: same formula applied to AST subtrees for each symbol.",
        f"  Entities measured: {outcome.entity_summary.get('total', 0)} "
        f"(classes={outcome.entity_summary.get('class', 0)}, "
        f"methods={outcome.entity_summary.get('method', 0)}, "
        f"functions={outcome.entity_summary.get('function', 0)}, "
        f"fields={outcome.entity_summary.get('field', 0)})",
        "Bayesian quality posterior (simplified map):",
        f"  E[Q | o] = {outcome.bayesian_quality},  U_epistemic = {outcome.epistemic_uncertainty}",
        "Pillar aggregates (repository means):",
        f"  mean(H_struct) = {p['structural_entropy']}",
        f"  mean(C_cyc) = {p['cyclomatic_pressure']}",
        f"  mean(K_couple) = {p['coupling_field']}",
        f"  beta1_proxy = {int(p['topological_cycles'])}",
        f"  mean(R_compress) = {p['information_density']}",
    ]

    sections["inventory_technical"] = [
        f"Root path: `{outcome.root}`",
        f"GitHub: {outcome.github_url or 'N/A (local path)'}",
        f"Files analyzed: {outcome.file_count}",
        f"Languages: {', '.join(f'{k} ({v})' for k, v in inv.by_language.items())}",
        f"Total source bytes: {inv.total_bytes:,}",
        "Scan scope: full repository (all discoverable source files)",
    ]

    sections["methodology"] = [
        "Python: full AST — every ClassDef, FunctionDef/AsyncFunctionDef, class fields and __init__ self.* assignments.",
        "Per-entity cyclomatic and nesting computed on the symbol subtree only.",
        "Improvement areas: rule engine on complexity, length, arity, class method/field counts.",
        "Other languages: heuristic class/method/field extraction with regex blocks.",
        "Coupling graph: directed edges from import/require/include statements to internal module stems.",
        "β₁ proxy: count of files with both inbound and outbound internal edges (cycle indicator).",
        "Risk bands: LOW < 35 ≤ MEDIUM < 55 ≤ HIGH < 75 ≤ CRITICAL.",
    ]

    sections["per_file_technical"] = []
    for f in outcome.files[:50]:  # cap narrative for huge repos
        sections["per_file_technical"].append(
            f"{f.path} [{f.language}] — "
            f"Omega_local={f.omega_local}, H_s={f.h_struct}, H_t={f.h_text}, "
            f"M_c={f.cyclomatic}, D_nest={f.nesting_depth}, "
            f"K_out/in={f.coupling_out}/{f.coupling_in}, "
            f"R_gzip={f.compression_ratio}, band={f.risk_band}"
        )
    if len(outcome.files) > 50:
        sections["per_file_technical"].append(
            f"*… and {len(outcome.files) - 50} additional modules in JSON/CSV export.*"
        )

    sections["recommendations_technical"] = outcome.recommendations

    sections["per_entity_technical"] = []
    for e in outcome.entities[:60]:
        areas = "; ".join(e.improvement_areas[:2])
        sections["per_entity_technical"].append(
            f"{e.qualified_name} [{e.entity_type}] L{e.line_start}-{e.line_end} "
            f"Omega={e.omega_local} M_c={e.cyclomatic} D={e.nesting_depth} — {areas}"
        )
    if len(outcome.entities) > 60:
        sections["per_entity_technical"].append(
            f"*… {len(outcome.entities) - 60} more entities in omega-entities.csv*"
        )

    if outcome.dimensions:
        sections["quality_dimensions_technical"] = []
        for d in outcome.dimensions:
            sections["quality_dimensions_technical"].append(
                f"### {d['name']} (`{d['id']}`) — score {d['score']}, band {d['band']}, "
                f"weight {d['weight']}, aggregate {d['repo_aggregate']} {d['unit']}"
            )
            sections["quality_dimensions_technical"].append(d["summary_technical"])
            for ev in d.get("evidence", [])[:5]:
                sections["quality_dimensions_technical"].append(f"  - {ev}")
            for sym in d.get("evidence_symbols", [])[:3]:
                sections["quality_dimensions_technical"].append(f"  - symbol: {sym}")
            for act in d.get("actions_in_repo", [])[:2]:
                sections["quality_dimensions_technical"].append(f"  - action: {act}")

    sections["limitations"] = [
        "Heuristic metrics for non-Python languages underestimate semantic coupling.",
        "No mutation-test Boltzmann entropy \\(S = k \\ln \\Omega(T)\\) in this release.",
        "No persistent Laplacian spectra on full CPG (future Phase 2).",
        "Private GitHub repos require local clone with credentials.",
    ]

    return sections


def file_business_blurb(f: FileMetrics) -> str:
    if f.risk_band == "LOW":
        return "Healthy module — low change risk."
    if f.risk_band == "MEDIUM":
        return (
            f"Moderate concern: {f.cyclomatic} decision paths and nesting depth {f.nesting_depth}. "
            "Schedule simplification when touching this file."
        )
    if f.risk_band == "HIGH":
        return (
            f"High maintenance cost: complex logic ({f.cyclomatic} branches) "
            f"and coupling to {f.coupling_out + f.coupling_in} other modules."
        )
    return (
        f"Critical hotspot: refactor before adding features. "
        f"Omega local score {f.omega_local}."
    )
