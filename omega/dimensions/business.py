"""Business family: service context and product-facing quality dimensions."""

from __future__ import annotations

import math

from omega.dimensions.context import DimensionContext
from omega.dimensions.core import RepoDimension, dim, norm_score


def build_business_dimensions(ctx: DimensionContext) -> list[RepoDimension]:
    if not ctx.files:
        return []
    dims: list[RepoDimension] = []
    svc = ctx.service_context
    name = svc.get("service_name") or ctx.display
    role = svc.get("service_role", "service")
    domains = svc.get("business_domains") or ["general"]
    entry = svc.get("entry_points") or []

    role_w = {"api": 1.2, "worker": 1.0, "monolith": 1.15, "library": 0.85}.get(role, 1.0)
    crit = min(100, ctx.omega_index * 0.7 * role_w + len(entry) * 4)
    dims.append(
        dim(
            id="service_criticality",
            name="Service criticality",
            family="business",
            score=crit,
            weight=0.25,
            repo_aggregate=crit,
            unit="criticality index",
            summary_technical=f"Service `{name}` role={role}, entries={len(entry)}, Ω={ctx.omega_index:.2f}.",
            summary_business=f"**{name}** as **{role}** — quality debt has elevated business exposure.",
            evidence=[f"Domains: {', '.join(domains)}"] + [f"Entry: `{e}`" for e in entry[:5]],
            actions_in_repo=[f"Treat `{name}` as tier-1 for quality gates before release."],
        )
    )

    change_cost = min(100, ctx.omega_index * math.log1p(max(1, ctx.total_loc)) / 12)
    dims.append(
        dim(
            id="change_cost_field",
            name="Change cost field",
            family="business",
            score=change_cost,
            weight=0.30,
            repo_aggregate=round(change_cost, 2),
            unit="cost index",
            summary_technical=f"Omega × log(LOC) cost proxy = {change_cost:.2f}.",
            summary_business="Estimated cost of each feature or fix in this service.",
            evidence=[f"{ctx.total_loc:,} LOC across {ctx.file_count} files"],
            actions_in_repo=["Budget refactor sprints proportional to change-cost index."],
        )
    )

    entry_omega: list[tuple[str, float]] = []
    by_path = {f.path: f for f in ctx.files}
    for ep in entry:
        fm = by_path.get(ep)
        if fm:
            entry_omega.append((ep, fm.omega_local))
    if not entry_omega and ctx.sorted_by_omega:
        entry_omega = [(ctx.sorted_by_omega[0].path, ctx.sorted_by_omega[0].omega_local)]
    is_api_like = role in ("api", "monolith", "worker") or bool(entry)
    if is_api_like:
        api_stress = min(100, len(entry) * 8 + ctx.omega_index * 0.35)
        if entry_omega:
            api_stress = min(
                100, max(api_stress, sum(o for _, o in entry_omega) / len(entry_omega))
            )
        dims.append(
            dim(
                id="api_boundary_stress",
                name="API boundary stress",
                family="business",
                score=api_stress,
                weight=0.18,
                repo_aggregate=api_stress,
                unit="boundary Ω",
                summary_technical=f"{len(entry)} entry point(s); boundary stress {api_stress:.1f}.",
                summary_business="Public boundaries amplify defect blast radius to customers.",
                evidence=[f"`{p}` — Ω={o:.1f}" for p, o in entry_omega[:5]],
                qualification="API/worker/monolith role or detected entry points",
                actions_in_repo=["Harden and test entry-point modules listed above."],
            )
        )

    if ctx.dir_rollup:
        spreads = [avg for _, avg, _ in ctx.dir_rollup]
        spread = max(spreads) - min(spreads) if len(spreads) > 1 else 0
        cohesion = max(0, 100 - spread * 1.5)
        worst = ctx.dir_rollup[0][0]
        dims.append(
            dim(
                id="domain_cohesion",
                name="Domain cohesion",
                family="business",
                score=cohesion,
                weight=0.15,
                repo_aggregate=round(spread, 2),
                unit="Ω spread across folders",
                summary_technical=f"Top-folder Ω spread {spread:.2f}; domains={domains}.",
                summary_business=(
                    f"Quality is {'evenly distributed' if spread < 15 else f'concentrated in `{worst}/`'} "
                    f"for {domains[0]} capabilities."
                ),
                evidence=[f"`{n}/` Ω={avg:.2f}" for n, avg, _ in ctx.dir_rollup[:4]],
                actions_in_repo=[f"Stabilize `{worst}/` to improve domain cohesion."],
            )
        )

    release = min(100, ctx.omega_index * (0.45 + ctx.epistemic_uncertainty) + float(ctx.pillars.get("p95_omega_local", 0)) * 0.25)
    dims.append(
        dim(
            id="release_readiness",
            name="Release readiness",
            family="business",
            score=release,
            weight=0.22,
            repo_aggregate=release,
            unit="readiness stress",
            summary_technical=(
                f"Ω={ctx.omega_index:.2f}, U={ctx.epistemic_uncertainty:.3f}, Q={ctx.bayesian_quality:.1f}/10."
            ),
            summary_business=(
                "Ready for release with confidence."
                if release < 45 and ctx.epistemic_uncertainty < 0.35
                else "Validate hotspots before shipping — signals show elevated risk."
            ),
            evidence=[],
            actions_in_repo=["Re-run Ω after sprint-queue fixes before tagging release."],
        )
    )

    if ctx.config_artifact_count > 0:
        cfg_score = min(100, ctx.config_artifact_count * 12)
        dims.append(
            dim(
                id="configuration_surface",
                name="Configuration surface",
                family="business",
                score=cfg_score,
                weight=0.12,
                repo_aggregate=float(ctx.config_artifact_count),
                unit="deploy artifacts",
                summary_technical=f"{ctx.config_artifact_count} deployment/config artifact types detected.",
                summary_business="More deploy paths increase operational and misconfiguration risk.",
                evidence=svc.get("deployment_artifacts") or [],
                qualification="Deployment or infra config artifacts present",
                actions_in_repo=["Document and test all deployment paths in CI."],
            )
        )

    scan = ctx.source_scan
    if scan and (scan.total_observe > 0 or role in ("api", "worker", "monolith")):
        obs = min(100, max(0, 80 - scan.total_observe * 2))
        dims.append(
            dim(
                id="operational_observability",
                name="Operational observability",
                family="business",
                score=obs,
                weight=0.14,
                repo_aggregate=float(scan.total_observe),
                unit="observe hits",
                summary_technical=f"Logging/metrics/trace patterns: {scan.total_observe} in scan sample.",
                summary_business=(
                    "Strong observability signals detected."
                    if scan.total_observe > 15
                    else "Add metrics/tracing on critical paths for production confidence."
                ),
                evidence=[
                    f"`{st.path}` — {st.observe_hits}" for st in scan.per_file if st.observe_hits
                ][:5],
                qualification="Deployable service role or observability patterns in code",
                actions_in_repo=["Instrument top Ω hotspots with structured logging and traces."],
            )
        )

    doc_score = min(100, max(15, 100 - ctx.readme_chars / 200 - ctx.omega_index * 0.3))
    dims.append(
        dim(
            id="documentation_field",
            name="Documentation field",
            family="business",
            score=doc_score,
            weight=0.10,
            repo_aggregate=float(ctx.readme_chars),
            unit="README bytes",
            summary_technical=f"README size {ctx.readme_chars} bytes vs Ω={ctx.omega_index:.2f}.",
            summary_business="Documentation depth supports onboarding and safer changes.",
            evidence=["README.md present"] if ctx.readme_chars else ["No README.md detected"],
            actions_in_repo=["Expand README with architecture and runbooks for this service."],
        )
    )

    cf = ctx.pillars.get("coupling_field", 0)
    mod = max(0, 100 - norm_score(cf, 5.0))
    dims.append(
        dim(
            id="delivery_modularity",
            name="Delivery modularity",
            family="business",
            score=mod,
            weight=0.15,
            repo_aggregate=mod,
            unit="modularity index",
            summary_technical=f"Inverse coupling stress modularity={mod:.1f}.",
            summary_business="Higher modularity enables parallel team delivery.",
            evidence=[],
            actions_in_repo=["Reduce cross-module imports in the hottest packages."],
        )
    )

    return dims
