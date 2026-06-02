"""Ecosystem family: upstream/downstream and cross-service impact (qualified repos only)."""

from __future__ import annotations

from omega.dimensions.context import DimensionContext
from omega.dimensions.core import RepoDimension, dim
from omega.ecosystem import per_service_stress


def _has_ecosystem_graph(ctx: DimensionContext) -> bool:
    eco = ctx.ecosystem
    upstream = eco.get("upstream") or []
    downstream = eco.get("downstream") or []
    if upstream or downstream:
        return True
    return ctx.service_context.get("config_source") == "omega.ecosystem"


def build_ecosystem_dimensions(ctx: DimensionContext) -> list[RepoDimension]:
    if not ctx.files:
        return []
    if not _has_ecosystem_graph(ctx):
        return []

    dims: list[RepoDimension] = []
    eco = ctx.ecosystem
    impact = ctx.impact_summary
    upstream = eco.get("upstream") or []
    downstream = eco.get("downstream") or []

    if upstream:
        up_stress = impact.get("upstream_aggregate_stress")
        if up_stress is None:
            stresses = [
                per_service_stress(ctx.omega_index, node=n, direction="upstream")
                for n in upstream
            ]
            up_stress = sum(stresses) / len(stresses)
        dims.append(
            dim(
                id="upstream_aggregate_stress",
                name="Upstream aggregate stress",
                family="ecosystem",
                score=float(up_stress),
                weight=0.28,
                repo_aggregate=float(up_stress),
                unit="blended stress",
                summary_technical=f"Mean upstream blended stress over {len(upstream)} node(s).",
                summary_business="Combined risk from libraries and services this codebase depends on.",
                evidence=[f"`{n.get('name')}` ({n.get('kind')})" for n in upstream[:8]],
                qualification="Declared or discovered upstream dependencies",
                actions_in_repo=[
                    f"Harden integration with `{upstream[0].get('name')}` first."
                ],
            )
        )

    if downstream:
        down_blast = impact.get("downstream_blast_radius")
        if down_blast is None:
            n = len(downstream)
            down_blast = min(100, ctx.omega_index * 0.5 + n * 6)
        dims.append(
            dim(
                id="downstream_blast_exposure",
                name="Downstream blast exposure",
                family="ecosystem",
                score=float(down_blast),
                weight=0.30,
                repo_aggregate=float(down_blast),
                unit="blast index",
                summary_technical=f"{len(downstream)} downstream consumer/channel node(s).",
                summary_business="If this service degrades, listed consumers are affected.",
                evidence=[f"`{n.get('name')}` ({n.get('kind')})" for n in downstream[:8]],
                qualification="Declared or discovered downstream consumers",
                actions_in_repo=["Add contract tests for downstream consumers."],
            )
        )

    data_nodes = [n for n in upstream if str(n.get("kind", "")).lower() == "datastore"]
    if data_nodes:
        stresses = [
            per_service_stress(ctx.omega_index, node=n, direction="upstream") for n in data_nodes
        ]
        ds = sum(stresses) / len(stresses)
        dims.append(
            dim(
                id="datastore_coupling",
                name="Datastore coupling",
                family="ecosystem",
                score=ds,
                weight=0.24,
                repo_aggregate=ds,
                unit="datastore stress",
                summary_technical=f"{len(data_nodes)} datastore upstream node(s).",
                summary_business="Data dependencies are continuity-critical — prioritize resilience.",
                evidence=[n.get("name", "?") for n in data_nodes],
                qualification="Datastore upstream in service graph",
                actions_in_repo=["Review migrations, pooling, and timeout policy for data stores."],
            )
        )

    http_nodes = [
        n
        for n in upstream
        if str(n.get("kind", "")).lower() in ("http", "grpc", "internal")
    ]
    if http_nodes:
        fan = len(http_nodes)
        mean_s = sum(
            per_service_stress(ctx.omega_index, node=n, direction="upstream") for n in http_nodes
        ) / fan
        dims.append(
            dim(
                id="sync_http_fanout",
                name="Sync HTTP fan-out",
                family="ecosystem",
                score=min(100, mean_s + fan * 2),
                weight=0.20,
                repo_aggregate=float(fan),
                unit="sync deps",
                summary_technical=f"{fan} synchronous remote dependency(ies).",
                summary_business="Each remote call adds latency and failure modes to customer journeys.",
                evidence=[n.get("name", "?") for n in http_nodes[:8]],
                qualification="HTTP/gRPC upstream dependencies",
                actions_in_repo=["Reduce chatty sync calls; add circuit breakers on top fan-out deps."],
            )
        )

    queue_down = [
        n
        for n in downstream
        if str(n.get("kind", "")).lower() in ("queue", "internal", "unknown")
    ]
    if queue_down or any(
        "publish" in str(e).lower() for n in downstream for e in (n.get("evidence") or [])
    ):
        pub_score = min(100, len(queue_down) * 10 + ctx.omega_index * 0.4)
        dims.append(
            dim(
                id="event_publish_surface",
                name="Event publish surface",
                family="ecosystem",
                score=pub_score,
                weight=0.18,
                repo_aggregate=float(len(queue_down)),
                unit="publish channels",
                summary_technical=f"{len(queue_down)} event/downstream channel(s).",
                summary_business="Published events multiply blast radius beyond HTTP callers.",
                evidence=[n.get("name", "?") for n in queue_down[:6]],
                qualification="Event or queue downstream channels",
                actions_in_repo=["Version event schemas and monitor consumer lag."],
            )
        )

    lib_nodes = [n for n in upstream if str(n.get("kind", "")).lower() == "library"]
    if lib_nodes:
        lib_score = min(100, len(lib_nodes) * 1.2 + ctx.omega_index * 0.25)
        dims.append(
            dim(
                id="library_supply_chain",
                name="Library supply chain",
                family="ecosystem",
                score=lib_score,
                weight=0.16,
                repo_aggregate=float(len(lib_nodes)),
                unit="packages",
                summary_technical=f"{len(lib_nodes)} declared library upstream dependencies.",
                summary_business="Third-party packages expand security and upgrade obligations.",
                evidence=[n.get("name", "?") for n in lib_nodes[:10]],
                qualification="Package manifest dependencies in graph",
                actions_in_repo=["Pin and audit top dependency fan-in packages quarterly."],
            )
        )

    n_edges = len(upstream) + len(downstream)
    if n_edges:
        csiq = impact.get("cross_service_impact_quotient")
        if csiq is None:
            csiq = min(100, n_edges * ctx.omega_index / 100 * 8)
        dims.append(
            dim(
                id="cross_service_impact",
                name="Cross-service impact",
                family="ecosystem",
                score=float(csiq),
                weight=0.25,
                repo_aggregate=float(csiq),
                unit="impact quotient",
                summary_technical=eco.get("graph_summary_technical", "Ecosystem graph stress."),
                summary_business=eco.get(
                    "graph_summary_business",
                    "Breadth of ecosystem exposure weighted by code health.",
                ),
                evidence=[],
                qualification="Non-empty service dependency graph",
                actions_in_repo=["Keep `.omega/ecosystem.yaml` aligned with production topology."],
            )
        )

    bcr = impact.get("business_continuity_risk")
    if bcr is not None and n_edges:
        dims.append(
            dim(
                id="business_continuity_risk",
                name="Business continuity risk",
                family="ecosystem",
                score=float(bcr),
                weight=0.35,
                repo_aggregate=float(bcr),
                unit="BCR index",
                summary_technical=f"BCR composite = {bcr:.2f} (criticality × ecosystem stress).",
                summary_business="Executive risk score for service continuity planning.",
                evidence=[],
                qualification="Ecosystem graph with continuity composite",
                actions_in_repo=["Address top upstream and Ω hotspots before peak traffic."],
            )
        )

    return dims
