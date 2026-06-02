"""N-metric quality suite: field, business context, upstream/downstream, impact."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from omega.discover import RepoInventory
from omega.ecosystem import discover_ecosystem, per_service_stress
from omega.metric_registry import (
    MetricCategory,
    MetricComputeContext,
    MetricDefinition,
    MetricRecord,
    MetricRegistry,
    band_from_score,
    clamp100,
)
from omega.metrics import FileMetrics
from omega.service_context import detect_service_context


def _mean(files: list[Any], attr: str) -> float:
    if not files:
        return 0.0
    return sum(float(getattr(f, attr)) for f in files) / len(files)


def _record(
    defn: MetricDefinition,
    value: float,
    *,
    summary_technical: str,
    summary_business: str,
    evidence: list[str] | None = None,
    related_service: str | None = None,
    edge_kind: str | None = None,
) -> MetricRecord:
    return MetricRecord(
        id=defn.id,
        name=defn.name,
        category=defn.category.value,
        value=clamp100(value),
        unit=defn.unit,
        formula=defn.formula,
        band=band_from_score(clamp100(value)),
        weight=defn.weight,
        summary_technical=summary_technical,
        summary_business=summary_business,
        evidence=evidence or [],
        related_service=related_service,
        edge_kind=edge_kind,
    )


def _build_registry() -> MetricRegistry:
    reg = MetricRegistry()

    # --- FIELD (code manifold) ---
    field_defs = [
        MetricDefinition(
            "omega_repo_index",
            "Repository Ω index",
            MetricCategory.FIELD,
            "Ω (0–100)",
            "Omega_repo = mean(Omega_local)",
            1.0,
        ),
        MetricDefinition(
            "structural_entropy_field",
            "Structural entropy field",
            MetricCategory.FIELD,
            "H_struct (bits)",
            "mean(H_struct)",
            0.28,
        ),
        MetricDefinition(
            "textual_entropy_field",
            "Textual entropy field",
            MetricCategory.FIELD,
            "H_text (bits)",
            "mean(H_text)",
            0.10,
        ),
        MetricDefinition(
            "cyclomatic_pressure_field",
            "Cyclomatic pressure",
            MetricCategory.FIELD,
            "McCabe",
            "mean(C_cyc)",
            0.25,
        ),
        MetricDefinition(
            "nesting_pressure_field",
            "Nesting pressure",
            MetricCategory.FIELD,
            "levels",
            "mean(D_nest)",
            0.18,
        ),
        MetricDefinition(
            "coupling_field_strength",
            "Coupling field",
            MetricCategory.FIELD,
            "edges",
            "mean(K_out + K_in)",
            0.17,
        ),
        MetricDefinition(
            "compression_density_field",
            "Information density",
            MetricCategory.FIELD,
            "R_gzip",
            "mean(R_compress)",
            0.12,
        ),
        MetricDefinition(
            "p95_tail_risk",
            "P95 tail risk",
            MetricCategory.FIELD,
            "Ω",
            "P95(Omega_local)",
            0.22,
        ),
        MetricDefinition(
            "peak_local_field",
            "Peak local field",
            MetricCategory.FIELD,
            "Ω",
            "max(Omega_local)",
            0.20,
        ),
        MetricDefinition(
            "cycle_topology_stress",
            "Cycle topology stress",
            MetricCategory.FIELD,
            "cycles",
            "beta1_proxy count",
            0.15,
        ),
        MetricDefinition(
            "coupling_asymmetry_index",
            "Coupling asymmetry",
            MetricCategory.FIELD,
            "ratio",
            "|mean(K_out) - mean(K_in)| / mean(K)",
            0.12,
        ),
        MetricDefinition(
            "symbol_risk_density",
            "Symbol risk density",
            MetricCategory.FIELD,
            "ratio",
            "high_risk_entities / total_entities",
            0.20,
        ),
        MetricDefinition(
            "language_fragmentation_index",
            "Language fragmentation",
            MetricCategory.FIELD,
            "index",
            "1 - max(lang_share)",
            0.08,
        ),
        MetricDefinition(
            "loc_stress_index",
            "LOC stress index",
            MetricCategory.FIELD,
            "index",
            "mean(log1p(LOC)) scaled",
            0.10,
        ),
        MetricDefinition(
            "bayesian_quality_posterior",
            "Bayesian quality",
            MetricCategory.FIELD,
            "Q (0–10)",
            "E[Q | observables]",
            0.18,
        ),
        MetricDefinition(
            "epistemic_uncertainty_metric",
            "Epistemic uncertainty",
            MetricCategory.FIELD,
            "U",
            "sqrt(variance(signals))",
            0.15,
        ),
    ]

    def calc_omega(ctx: MetricComputeContext) -> MetricRecord:
        d = reg._definitions["omega_repo_index"]
        return _record(
            d,
            ctx.omega_index,
            summary_technical=f"Omega_repo = {ctx.omega_index:.2f} over {ctx.file_count} files.",
            summary_business=f"Overall codebase health index is {ctx.omega_index:.1f} (lower is better).",
        )

    def calc_struct(ctx: MetricComputeContext) -> MetricRecord:
        d = reg._definitions["structural_entropy_field"]
        agg = ctx.pillars.get("structural_entropy", 0)
        return _record(
            d,
            min(100, agg / 6.0 * 100),
            summary_technical=f"mean(H_struct) = {agg:.3f} bits.",
            summary_business="Structural unpredictability across modules.",
            evidence=[f"pillar structural_entropy = {agg:.3f}"],
        )

    def calc_text(ctx: MetricComputeContext) -> MetricRecord:
        d = reg._definitions["textual_entropy_field"]
        agg = ctx.pillars.get("textual_entropy", 0)
        return _record(
            d,
            min(100, agg / 6.0 * 100),
            summary_technical=f"mean(H_text) = {agg:.3f} bits.",
            summary_business="Lexical diversity and naming inconsistency stress.",
        )

    def calc_cyc(ctx: MetricComputeContext) -> MetricRecord:
        d = reg._definitions["cyclomatic_pressure_field"]
        agg = ctx.pillars.get("cyclomatic_pressure", 0)
        return _record(
            d,
            min(100, agg / 15.0 * 100),
            summary_technical=f"mean(C_cyc) = {agg:.2f}.",
            summary_business="Decision-path density increases change cost.",
        )

    def calc_nest(ctx: MetricComputeContext) -> MetricRecord:
        d = reg._definitions["nesting_pressure_field"]
        v = _mean(ctx.files, "nesting_depth")
        return _record(
            d,
            min(100, v / 6.0 * 100),
            summary_technical=f"mean(D_nest) = {v:.2f}.",
            summary_business="Deep nesting slows reviews and onboarding.",
        )

    def calc_couple(ctx: MetricComputeContext) -> MetricRecord:
        d = reg._definitions["coupling_field_strength"]
        agg = ctx.pillars.get("coupling_field", 0)
        return _record(
            d,
            min(100, agg / 5.0 * 100),
            summary_technical=f"mean(K) = {agg:.2f}.",
            summary_business="Cross-module dependencies amplify coordination cost.",
        )

    def calc_compress(ctx: MetricComputeContext) -> MetricRecord:
        d = reg._definitions["compression_density_field"]
        agg = ctx.pillars.get("information_density", 0)
        return _record(
            d,
            min(100, abs(agg - 2.5) * 10),
            summary_technical=f"mean(R_gzip) = {agg:.2f}.",
            summary_business="Information density deviation from expected compressibility.",
        )

    def calc_p95(ctx: MetricComputeContext) -> MetricRecord:
        d = reg._definitions["p95_tail_risk"]
        v = ctx.pillars.get("p95_omega_local", ctx.omega_index)
        return _record(
            d,
            float(v),
            summary_technical=f"P95(Omega_local) = {v:.2f}.",
            summary_business="Worst 5% of modules dominate delivery risk.",
        )

    def calc_peak(ctx: MetricComputeContext) -> MetricRecord:
        d = reg._definitions["peak_local_field"]
        v = ctx.pillars.get("max_omega_local", ctx.omega_index)
        return _record(
            d,
            float(v),
            summary_technical=f"max(Omega_local) = {v:.2f}.",
            summary_business="Single hottest module caps release confidence.",
        )

    def calc_cycles(ctx: MetricComputeContext) -> MetricRecord:
        d = reg._definitions["cycle_topology_stress"]
        c = float(ctx.pillars.get("topological_cycles", 0))
        return _record(
            d,
            min(100, c * 12),
            summary_technical=f"beta1_proxy = {int(c)} bidirectional modules.",
            summary_business=f"{int(c)} circular dependency pattern(s) detected.",
        )

    def calc_asym(ctx: MetricComputeContext) -> MetricRecord:
        d = reg._definitions["coupling_asymmetry_index"]
        out_m = _mean(ctx.files, "coupling_out")
        in_m = _mean(ctx.files, "coupling_in")
        denom = max(0.01, out_m + in_m)
        asym = abs(out_m - in_m) / denom * 100
        return _record(
            d,
            asym,
            summary_technical=f"|K_out - K_in| / (K_out + K_in) scaled = {asym:.2f}.",
            summary_business="Imbalanced fan-out vs fan-in hints architecture drift.",
        )

    def calc_sym(ctx: MetricComputeContext) -> MetricRecord:
        d = reg._definitions["symbol_risk_density"]
        total = max(1, ctx.entity_summary.get("total", 0))
        high = ctx.entity_summary.get("high_risk", 0)
        ratio = high / total * 100
        return _record(
            d,
            ratio,
            summary_technical=f"{high}/{total} symbols at MEDIUM+ risk.",
            summary_business=f"{high} named symbols need attention before release.",
        )

    def calc_lang(ctx: MetricComputeContext) -> MetricRecord:
        d = reg._definitions["language_fragmentation_index"]
        if not ctx.top_by_language:
            return _record(d, 0, summary_technical="monolingual", summary_business="single language stack")
        total = sum(ctx.top_by_language.values())  # file-weighted proxy via count keys
        counts = ctx.ecosystem.get("_lang_counts") or {}
        if counts:
            n = sum(counts.values())
            share = max(counts.values()) / max(1, n)
        else:
            langs = list(ctx.top_by_language.keys())
            share = 1.0 / max(1, len(langs))
        frag = (1.0 - share) * 100
        return _record(
            d,
            frag,
            summary_technical=f"fragmentation = {frag:.1f}%, languages={list(ctx.top_by_language)}",
            summary_business="More languages increase operational surface area.",
        )

    def calc_loc(ctx: MetricComputeContext) -> MetricRecord:
        d = reg._definitions["loc_stress_index"]
        vals = [min(100, math.log1p(max(1, getattr(f, "loc", 1))) * 12) for f in ctx.files]
        v = sum(vals) / len(vals) if vals else 0
        return _record(
            d,
            v,
            summary_technical=f"mean(log-LOC stress) = {v:.2f}.",
            summary_business="Large files increase review and defect cost.",
        )

    def calc_bayes(ctx: MetricComputeContext) -> MetricRecord:
        d = reg._definitions["bayesian_quality_posterior"]
        q = ctx.bayesian_quality
        stress = max(0, 10 - q) * 10
        return _record(
            d,
            stress,
            summary_technical=f"E[Q|o] = {q:.2f}/10.",
            summary_business=f"Estimated product quality {q:.1f}/10 from fused signals.",
        )

    def calc_unc(ctx: MetricComputeContext) -> MetricRecord:
        d = reg._definitions["epistemic_uncertainty_metric"]
        u = ctx.epistemic_uncertainty * 100
        return _record(
            d,
            u,
            summary_technical=f"U_epistemic = {ctx.epistemic_uncertainty:.3f}.",
            summary_business=(
                "High confidence in assessment."
                if ctx.epistemic_uncertainty < 0.35
                else "Signals disagree — treat planning numbers as directional."
            ),
        )

    field_calcs = [
        calc_omega,
        calc_struct,
        calc_text,
        calc_cyc,
        calc_nest,
        calc_couple,
        calc_compress,
        calc_p95,
        calc_peak,
        calc_cycles,
        calc_asym,
        calc_sym,
        calc_lang,
        calc_loc,
        calc_bayes,
        calc_unc,
    ]
    for defn, calc in zip(field_defs, field_calcs):
        reg.register(defn, calc)

    # --- BUSINESS (service context) ---
    biz_defs = [
        MetricDefinition(
            "service_criticality_index",
            "Service criticality",
            MetricCategory.BUSINESS,
            "index",
            "f(role, entry_points, omega)",
            0.25,
        ),
        MetricDefinition(
            "change_cost_index",
            "Change cost index",
            MetricCategory.BUSINESS,
            "index",
            "Omega_repo * log1p(LOC)",
            0.30,
        ),
        MetricDefinition(
            "delivery_velocity_risk",
            "Delivery velocity risk",
            MetricCategory.BUSINESS,
            "index",
            "Omega * U_epistemic",
            0.22,
        ),
        MetricDefinition(
            "api_surface_stress",
            "API surface stress",
            MetricCategory.BUSINESS,
            "index",
            "entry_points * omega",
            0.18,
        ),
        MetricDefinition(
            "domain_modularity_score",
            "Domain modularity",
            MetricCategory.BUSINESS,
            "index",
            "1 - coupling_field normalized",
            0.15,
        ),
    ]

    def calc_crit(ctx: MetricComputeContext) -> MetricRecord:
        d = reg._definitions["service_criticality_index"]
        role = ctx.service_context.get("service_role", "service")
        role_w = {"api": 1.2, "worker": 1.0, "monolith": 1.15, "library": 0.85}.get(role, 1.0)
        ep = len(ctx.service_context.get("entry_points") or [])
        v = min(100, ctx.omega_index * 0.7 * role_w + ep * 4)
        return _record(
            d,
            v,
            summary_technical=f"criticality for role={role}, entries={ep}.",
            summary_business=f"As a **{role}**, quality debt here has elevated business exposure.",
        )

    def calc_change(ctx: MetricComputeContext) -> MetricRecord:
        d = reg._definitions["change_cost_index"]
        v = min(100, ctx.omega_index * math.log1p(max(1, ctx.total_loc)) / 12)
        return _record(
            d,
            v,
            summary_technical=f"Omega*log(LOC) = {v:.2f}.",
            summary_business="Estimated cost of each change in this service.",
        )

    def calc_deliv(ctx: MetricComputeContext) -> MetricRecord:
        d = reg._definitions["delivery_velocity_risk"]
        v = min(100, ctx.omega_index * (0.5 + ctx.epistemic_uncertainty))
        return _record(
            d,
            v,
            summary_technical=f"Omega*U = {v:.2f}.",
            summary_business="Risk that delivery slows due to quality uncertainty.",
        )

    def calc_api(ctx: MetricComputeContext) -> MetricRecord:
        d = reg._definitions["api_surface_stress"]
        ep = len(ctx.service_context.get("entry_points") or [])
        v = min(100, ep * 8 + ctx.omega_index * 0.3)
        return _record(
            d,
            v,
            summary_technical=f"{ep} entry points × field stress.",
            summary_business="Public entry points amplify defect blast radius.",
        )

    def calc_mod(ctx: MetricComputeContext) -> MetricRecord:
        d = reg._definitions["domain_modularity_score"]
        cf = ctx.pillars.get("coupling_field", 0)
        mod = max(0, 100 - min(100, cf / 5 * 100))
        return _record(
            d,
            mod,
            summary_technical=f"modularity = {mod:.2f} (inverse coupling).",
            summary_business="Higher modularity enables parallel team work.",
        )

    for defn, calc in zip(
        biz_defs,
        [calc_crit, calc_change, calc_deliv, calc_api, calc_mod],
    ):
        reg.register(defn, calc)

    # --- IMPACT (composites) ---
    impact_defs = [
        MetricDefinition(
            "upstream_aggregate_stress",
            "Upstream aggregate stress",
            MetricCategory.IMPACT,
            "index",
            "mean(upstream blended stress)",
            0.28,
        ),
        MetricDefinition(
            "downstream_blast_radius",
            "Downstream blast radius",
            MetricCategory.IMPACT,
            "index",
            "f(downstream count, omega, publish patterns)",
            0.30,
        ),
        MetricDefinition(
            "ecosystem_field_stress",
            "Ecosystem field stress",
            MetricCategory.IMPACT,
            "index",
            "mean(upstream, downstream, omega)",
            0.32,
        ),
        MetricDefinition(
            "business_continuity_risk",
            "Business continuity risk",
            MetricCategory.IMPACT,
            "index",
            "criticality * ecosystem_stress",
            0.35,
        ),
        MetricDefinition(
            "cross_service_impact_quotient",
            "Cross-service impact quotient",
            MetricCategory.IMPACT,
            "index",
            "(upstream+downstream)*omega/100",
            0.25,
        ),
    ]

    def calc_up_agg(ctx: MetricComputeContext) -> MetricRecord:
        d = reg._definitions["upstream_aggregate_stress"]
        nodes = ctx.ecosystem.get("upstream") or []
        if not nodes:
            return _record(
                d,
                ctx.omega_index * 0.4,
                summary_technical="no upstream nodes; baseline from local field.",
                summary_business="No external dependencies detected — simpler operational graph.",
            )
        stresses = [
            per_service_stress(ctx.omega_index, node=n, direction="upstream") for n in nodes
        ]
        v = sum(stresses) / len(stresses)
        return _record(
            d,
            v,
            summary_technical=f"mean upstream stress over {len(nodes)} nodes = {v:.2f}.",
            summary_business="Combined risk from services and libraries you depend on.",
            evidence=[n.get("name", "?") for n in nodes[:6]],
        )

    def calc_down_blast(ctx: MetricComputeContext) -> MetricRecord:
        d = reg._definitions["downstream_blast_radius"]
        nodes = ctx.ecosystem.get("downstream") or []
        n = len(nodes)
        v = min(100, ctx.omega_index * 0.5 + n * 6 + (15 if n else 0))
        return _record(
            d,
            v,
            summary_technical=f"downstream nodes={n}, blast={v:.2f}.",
            summary_business="If this service fails, these channels or consumers are affected.",
            evidence=[x.get("name", "?") for x in nodes[:6]],
        )

    def calc_eco(ctx: MetricComputeContext) -> MetricRecord:
        d = reg._definitions["ecosystem_field_stress"]
        up = ctx.ecosystem.get("upstream") or []
        down = ctx.ecosystem.get("downstream") or []
        parts = [ctx.omega_index]
        for n in up[:20]:
            parts.append(per_service_stress(ctx.omega_index, node=n, direction="upstream"))
        for n in down[:15]:
            parts.append(per_service_stress(ctx.omega_index, node=n, direction="downstream"))
        v = sum(parts) / len(parts)
        return _record(
            d,
            v,
            summary_technical=f"ecosystem mean stress = {v:.2f}.",
            summary_business="Holistic stress across this service and its graph.",
        )

    def calc_bcr(ctx: MetricComputeContext) -> MetricRecord:
        d = reg._definitions["business_continuity_risk"]
        role = ctx.service_context.get("service_role", "service")
        role_w = {"api": 1.2, "worker": 1.0, "monolith": 1.15, "library": 0.85}.get(role, 1.0)
        ep = len(ctx.service_context.get("entry_points") or [])
        crit = min(100, ctx.omega_index * 0.7 * role_w + ep * 4)
        parts = [ctx.omega_index]
        for n in (ctx.ecosystem.get("upstream") or [])[:20]:
            parts.append(per_service_stress(ctx.omega_index, node=n, direction="upstream"))
        for n in (ctx.ecosystem.get("downstream") or [])[:15]:
            parts.append(per_service_stress(ctx.omega_index, node=n, direction="downstream"))
        eco = sum(parts) / len(parts)
        v = min(100, (crit * eco) / 100)
        return _record(
            d,
            v,
            summary_technical=f"BCR = criticality×ecosystem/100 = {v:.2f}.",
            summary_business="Executive risk: service importance × ecosystem stress.",
        )

    def calc_csiq(ctx: MetricComputeContext) -> MetricRecord:
        d = reg._definitions["cross_service_impact_quotient"]
        n = (ctx.ecosystem.get("upstream_count") or 0) + (
            ctx.ecosystem.get("downstream_count") or 0
        )
        v = min(100, n * ctx.omega_index / 100 * 8)
        return _record(
            d,
            v,
            summary_technical=f"CSIQ = |E|*Omega/100 scaled = {v:.2f}.",
            summary_business="Breadth of ecosystem exposure weighted by code health.",
        )

    for defn, calc in zip(
        impact_defs,
        [calc_up_agg, calc_down_blast, calc_eco, calc_bcr, calc_csiq],
    ):
        reg.register(defn, calc)

    return reg


_REGISTRY: MetricRegistry | None = None


def get_metric_registry() -> MetricRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _build_registry()
    return _REGISTRY


def _upstream_downstream_metric_records(ctx: MetricComputeContext) -> list[MetricRecord]:
    """Per-node upstream/downstream metrics (N metrics × services)."""
    records: list[MetricRecord] = []
    for node in ctx.ecosystem.get("upstream") or []:
        name = str(node.get("name", "unknown"))
        stress = per_service_stress(ctx.omega_index, node=node, direction="upstream")
        kind = str(node.get("kind", "unknown"))
        records.append(
            MetricRecord(
                id=f"upstream::{name}",
                name=f"Upstream: {name}",
                category=MetricCategory.UPSTREAM.value,
                value=clamp100(stress),
                unit="blended stress",
                formula="Omega_repo * coupling(kind) * evidence_weight",
                band=band_from_score(stress),
                weight=1.0,
                summary_technical=(
                    f"Upstream `{name}` ({kind}) blended stress = {stress:.2f}."
                ),
                summary_business=(
                    f"Dependency on **{name}** adds operational risk if it degrades."
                ),
                evidence=list(node.get("evidence") or [])[:5],
                related_service=name,
                edge_kind=kind,
            )
        )
    for node in ctx.ecosystem.get("downstream") or []:
        name = str(node.get("name", "unknown"))
        stress = per_service_stress(ctx.omega_index, node=node, direction="downstream")
        kind = str(node.get("kind", "unknown"))
        records.append(
            MetricRecord(
                id=f"downstream::{name}",
                name=f"Downstream: {name}",
                category=MetricCategory.DOWNSTREAM.value,
                value=clamp100(stress),
                unit="blast exposure",
                formula="Omega_repo * coupling(kind) * publish_weight",
                band=band_from_score(stress),
                weight=1.0,
                summary_technical=(
                    f"Downstream `{name}` ({kind}) exposure = {stress:.2f}."
                ),
                summary_business=(
                    f"Consumers of **{name}** feel impact when this service quality drops."
                ),
                evidence=list(node.get("evidence") or [])[:5],
                related_service=name,
                edge_kind=kind,
            )
        )
    return records


def build_metrics_suite(
    root: Path,
    outcome: Any,
    *,
    inventory: RepoInventory | None = None,
) -> dict[str, Any]:
    """
    Compute full metric suite for a repository analysis outcome.
    """
    root_path = Path(root).resolve()
    paths = [f.path for f in (outcome.files or [])]
    inv_paths = [sf.rel_path for sf in inventory.files] if inventory else paths
    source_paths = [root_path / p for p in inv_paths[:200]]

    service_context = detect_service_context(
        root_path,
        repo_display=outcome.repo_display,
        inventory_paths=inv_paths,
    )
    ecosystem = discover_ecosystem(root_path, source_file_paths=source_paths)

    lang_counts: dict[str, int] = {}
    for f in outcome.files or []:
        lang = getattr(f, "language", "unknown")
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
    ecosystem["_lang_counts"] = lang_counts  # internal helper for calculators

    ctx = MetricComputeContext(
        root=str(root_path),
        repo_display=outcome.repo_display,
        omega_index=float(outcome.omega_index),
        quality_grade=str(outcome.quality_grade),
        bayesian_quality=float(outcome.bayesian_quality),
        epistemic_uncertainty=float(outcome.epistemic_uncertainty),
        file_count=int(outcome.file_count),
        total_loc=int(outcome.total_loc),
        pillars=dict(outcome.pillars),
        files=list(outcome.files or []),
        entities=list(outcome.entities or []),
        entity_summary=dict(outcome.entity_summary or {}),
        top_by_language=dict(outcome.top_by_language or {}),
        service_context=service_context,
        ecosystem=ecosystem,
    )

    registry = get_metric_registry()
    core_metrics = registry.compute_all(ctx)
    edge_metrics = _upstream_downstream_metric_records(ctx)
    all_metrics = core_metrics + edge_metrics

    eco_out = {k: v for k, v in ecosystem.items() if not k.startswith("_")}

    by_category: dict[str, list[dict[str, Any]]] = {}
    for m in all_metrics:
        by_category.setdefault(m.category, []).append(m.to_dict())

    return {
        "suite_version": 1,
        "metric_count": len(all_metrics),
        "service_context": service_context,
        "ecosystem": eco_out,
        "metrics": [m.to_dict() for m in all_metrics],
        "by_category": by_category,
        "impact_summary": {
            "business_continuity_risk": next(
                (m.value for m in all_metrics if m.id == "business_continuity_risk"),
                None,
            ),
            "ecosystem_field_stress": next(
                (m.value for m in all_metrics if m.id == "ecosystem_field_stress"),
                None,
            ),
            "upstream_aggregate_stress": next(
                (m.value for m in all_metrics if m.id == "upstream_aggregate_stress"),
                None,
            ),
            "downstream_blast_radius": next(
                (m.value for m in all_metrics if m.id == "downstream_blast_radius"),
                None,
            ),
            "cross_service_impact_quotient": next(
                (m.value for m in all_metrics if m.id == "cross_service_impact_quotient"),
                None,
            ),
        },
    }


def ensure_report_has_metric_suite(
    report: dict[str, Any],
    *,
    root: str | Path | None = None,
) -> tuple[dict[str, Any], bool]:
    """Backfill metric_suite on stored reports when missing."""
    if report.get("metric_suite") and report["metric_suite"].get("metrics"):
        return report, False
    from omega.analyzer import RepositoryOutcome
    from omega.discover import RepoInventory

    repo_root = Path(root or report.get("repository") or ".")
    files = report.get("files") or []
    outcome = RepositoryOutcome(
        root=str(repo_root),
        repo_display=str(report.get("repo_display", "repository")),
        github_url=report.get("github_url"),
        analyzed_at=str(report.get("analyzed_at", "")),
        omega_index=float(report.get("omega_index", 0)),
        quality_grade=str(report.get("quality_grade", "N/A")),
        health_summary=str(report.get("health_summary_technical", "")),
        health_summary_business=str(report.get("health_summary_business", "")),
        file_count=int(report.get("file_count", len(files))),
        total_loc=int(report.get("total_loc", 0)),
        pillars=dict(report.get("pillars", {})),
        bayesian_quality=float(report.get("bayesian_quality", 0)),
        epistemic_uncertainty=float(report.get("epistemic_uncertainty", 0)),
        top_by_language=dict(report.get("languages", {})),
        entity_summary=dict(report.get("entity_summary", {})),
    )
    inv_data = report.get("inventory") or {}
    inv = RepoInventory(
        root=repo_root,
        files=[],
        by_language=dict(inv_data.get("by_language", {})),
        total_bytes=int(inv_data.get("total_bytes", 0)),
    )
    suite = build_metrics_suite(repo_root, outcome, inventory=inv)
    report = {**report, "metric_suite": suite}
    return report, True
