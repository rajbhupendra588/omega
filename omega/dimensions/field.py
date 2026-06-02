"""Field family: code-quality manifold dimensions (Ω observables)."""

from __future__ import annotations

import math

from omega.dimensions.context import DimensionContext, top_entities, top_files
from omega.dimensions.core import RepoDimension, dim, norm_score


def build_field_dimensions(ctx: DimensionContext) -> list[RepoDimension]:
    if not ctx.files:
        return []
    p = ctx.pillars
    display = ctx.display
    dims: list[RepoDimension] = []

    # --- Core manifold (original set, optimized) ---
    top_hs = top_files(ctx, "h_struct")
    agg = p.get("structural_entropy", 0)
    dims.append(
        dim(
            id="structural_entropy",
            name="Structural entropy",
            family="field",
            score=norm_score(agg, 6.0),
            weight=0.28,
            repo_aggregate=agg,
            unit="bits (mean H_struct)",
            summary_technical=(
                f"In `{display}`, mean AST structural entropy is {agg:.3f} bits across "
                f"{ctx.file_count} files (Ω_repo={ctx.omega_index:.2f})."
            ),
            summary_business=(
                "Code structure varies in predictability; hardest modules are listed below."
            ),
            evidence=[f"`{f.path}` — H_struct={v:.3f}, Ω={f.omega_local}" for f, v in top_hs],
            actions_in_repo=[
                f"Refactor `{top_hs[0][0].path}` first (H_struct={top_hs[0][1]:.3f})."
            ]
            if top_hs
            else [],
            top_contributors=[{"path": f.path, "value": v} for f, v in top_hs],
        )
    )

    top_cyc_f = top_files(ctx, "cyclomatic")
    top_cyc_e = top_entities(ctx, "cyclomatic") if ctx.entities else []
    agg = p.get("cyclomatic_pressure", 0)
    dims.append(
        dim(
            id="cyclomatic_pressure",
            name="Control-flow complexity",
            family="field",
            score=norm_score(agg, 15.0),
            weight=0.25,
            repo_aggregate=agg,
            unit="branches (mean McCabe)",
            summary_technical=f"Mean cyclomatic complexity per file is {agg:.2f}.",
            summary_business="More branches mean more test paths and hidden defect surfaces.",
            evidence=[f"`{f.path}` — {int(v)} branches" for f, v in top_cyc_f],
            evidence_symbols=[
                f"`{e.qualified_name}` in `{e.file_path}` — {int(v)} branches"
                for e, v in top_cyc_e
            ],
            actions_in_repo=[
                (
                    f"Split `{top_cyc_e[0][0].qualified_name}` in `{top_cyc_e[0][0].file_path}`."
                )
                if top_cyc_e
                else f"Decompose `{top_cyc_f[0][0].path}`."
            ]
            if top_cyc_f or top_cyc_e
            else [],
            top_contributors=[{"path": f.path, "value": v} for f, v in top_cyc_f],
        )
    )

    top_nest_f = top_files(ctx, "nesting_depth")
    top_nest_e = top_entities(ctx, "nesting_depth") if ctx.entities else []
    mean_nest = sum(f.nesting_depth for f in ctx.files) / len(ctx.files)
    dims.append(
        dim(
            id="nesting_depth",
            name="Nesting depth",
            family="field",
            score=norm_score(mean_nest, 6.0),
            weight=0.18,
            repo_aggregate=mean_nest,
            unit="levels (mean max depth)",
            summary_technical=f"Mean max nesting depth {mean_nest:.2f} levels per file.",
            summary_business="Deep nesting slows reviews and increases change risk.",
            evidence=[f"`{f.path}` — depth {int(v)}" for f, v in top_nest_f],
            evidence_symbols=[f"`{e.qualified_name}` depth {int(v)}" for e, v in top_nest_e],
            actions_in_repo=[
                f"Flatten nesting in `{top_nest_e[0][0].file_path}` around `{top_nest_e[0][0].qualified_name}`."
                if top_nest_e
                else f"Extract helpers from `{top_nest_f[0][0].path}`."
            ]
            if top_nest_f or top_nest_e
            else [],
        )
    )

    top_couple = sorted(
        ctx.files, key=lambda f: f.coupling_out + f.coupling_in, reverse=True
    )[:5]
    agg = p.get("coupling_field", 0)
    cyclic = ctx.cyclic_files
    dims.append(
        dim(
            id="coupling_field",
            name="Module coupling",
            family="field",
            score=norm_score(agg, 5.0),
            weight=0.17,
            repo_aggregate=agg,
            unit="edges (mean in+out)",
            summary_technical=(
                f"Mean coupling {agg:.2f}; {len(cyclic)} file(s) in bidirectional cycles."
            ),
            summary_business="Tightly linked modules amplify cross-team change risk.",
            evidence=[
                f"`{f.path}` — out={f.coupling_out}, in={f.coupling_in}" for f in top_couple
            ],
            actions_in_repo=[
                f"Break cycle through `{cyclic[0].path}`." if cyclic else f"Reduce fan-out from `{top_couple[0].path}`."
            ],
            top_contributors=[
                {"path": f.path, "coupling_out": f.coupling_out, "coupling_in": f.coupling_in}
                for f in top_couple
            ],
        )
    )

    dims.append(
        dim(
            id="topological_cycles",
            name="Dependency cycles",
            family="field",
            score=norm_score(float(len(cyclic)), max(1, len(ctx.files) * 0.15)),
            weight=0.12,
            repo_aggregate=float(len(cyclic)),
            unit="files in cycles",
            summary_technical=f"β₁ proxy: {len(cyclic)} cycle participant file(s).",
            summary_business=f"{len(cyclic)} module(s) sit in circular dependency chains.",
            evidence=[f"`{f.path}` — cycle participant" for f in cyclic[:8]],
            actions_in_repo=(
                [f"Cut cycle via `{cyclic[0].path}`."]
                if cyclic
                else ["No bidirectional import cycles detected."]
            ),
        )
    )

    top_r = top_files(ctx, "compression_ratio")
    agg = p.get("information_density", 0)
    dims.append(
        dim(
            id="information_density",
            name="Information density",
            family="field",
            score=norm_score(agg, 4.0),
            weight=0.12,
            repo_aggregate=agg,
            unit="gzip ratio",
            summary_technical=f"Mean gzip ratio {agg:.2f}.",
            summary_business="Repetitive or boilerplate-heavy text patterns in listed files.",
            evidence=[f"`{f.path}` — R={v:.2f}" for f, v in top_r],
            actions_in_repo=[f"Deduplicate logic in `{top_r[0][0].path}`." if top_r else []],
        )
    )

    top_ht = top_files(ctx, "h_text")
    agg = p.get("textual_entropy", 0)
    dims.append(
        dim(
            id="textual_entropy",
            name="Lexical diversity",
            family="field",
            score=norm_score(agg, 6.0),
            weight=0.10,
            repo_aggregate=agg,
            unit="bits (mean H_text)",
            summary_technical=f"Token entropy mean {agg:.3f} bits.",
            summary_business="Naming and vocabulary inconsistency across modules.",
            evidence=[f"`{f.path}` — H_text={v:.3f}" for f, v in top_ht],
            actions_in_repo=[f"Align vocabulary in `{top_ht[0][0].path}`." if top_ht else []],
        )
    )

    # --- Extended field dimensions ---
    p95 = float(p.get("p95_omega_local", ctx.omega_index))
    dims.append(
        dim(
            id="tail_risk_p95",
            name="P95 tail risk",
            family="field",
            score=p95,
            weight=0.22,
            repo_aggregate=p95,
            unit="Ω P95",
            summary_technical=f"P95(Omega_local) = {p95:.2f} — tail modules dominate risk.",
            summary_business="The worst 5% of files drive most release risk; prioritize them.",
            evidence=[f"`{f.path}` — Ω={f.omega_local}" for f in ctx.sorted_by_omega[:5]],
            actions_in_repo=[f"Remediate tail hotspot `{ctx.sorted_by_omega[0].path}`."]
            if ctx.sorted_by_omega
            else [],
        )
    )

    peak = float(p.get("max_omega_local", ctx.omega_index))
    dims.append(
        dim(
            id="peak_field_hotspot",
            name="Peak field hotspot",
            family="field",
            score=peak,
            weight=0.20,
            repo_aggregate=peak,
            unit="Ω max",
            summary_technical=f"max(Omega_local) = {peak:.2f}.",
            summary_business="Single worst module caps confidence in rapid delivery.",
            evidence=[f"`{ctx.sorted_by_omega[0].path}` — Ω={peak:.2f}"]
            if ctx.sorted_by_omega
            else [],
            actions_in_repo=[f"Schedule refactor for `{ctx.sorted_by_omega[0].path}` first."]
            if ctx.sorted_by_omega
            else [],
        )
    )

    out_m = sum(f.coupling_out for f in ctx.files) / len(ctx.files)
    in_m = sum(f.coupling_in for f in ctx.files) / len(ctx.files)
    asym = abs(out_m - in_m) / max(0.01, out_m + in_m) * 100
    dims.append(
        dim(
            id="coupling_asymmetry",
            name="Coupling asymmetry",
            family="field",
            score=asym,
            weight=0.12,
            repo_aggregate=round(asym, 2),
            unit="imbalance %",
            summary_technical=f"|K_out - K_in|/(K_out+K_in) = {asym:.1f}%.",
            summary_business="Imbalanced dependency direction hints architecture drift.",
            evidence=[],
            actions_in_repo=["Rebalance imports toward clearer layered architecture."],
        )
    )

    locs = sorted(ctx.files, key=lambda f: f.loc, reverse=True)
    total_loc = max(1, sum(f.loc for f in ctx.files))
    top_loc_share = sum(f.loc for f in locs[: max(1, len(locs) // 10)]) / total_loc * 100
    dims.append(
        dim(
            id="loc_mass_concentration",
            name="LOC mass concentration",
            family="field",
            score=min(100, top_loc_share * 1.2),
            weight=0.10,
            repo_aggregate=round(top_loc_share, 1),
            unit="% LOC in top decile",
            summary_technical=f"Top decile files hold {top_loc_share:.1f}% of LOC.",
            summary_business="Few large files concentrate maintenance and review cost.",
            evidence=[f"`{f.path}` — {f.loc} LOC" for f in locs[:5]],
            actions_in_repo=[f"Split `{locs[0].path}` ({locs[0].loc} LOC)." if locs else []],
        )
    )

    if ctx.entities:
        es = ctx.entity_summary
        top_sym = sorted(ctx.entities, key=lambda e: e.omega_local, reverse=True)[:5]
        dims.append(
            dim(
                id="symbol_surface",
                name="Symbol-level stress",
                family="field",
                score=norm_score(float(es.get("high_risk", 0)), max(1, es.get("total", 1) * 0.2)),
                weight=0.20,
                repo_aggregate=float(es.get("high_risk", 0)),
                unit="high-risk symbols",
                summary_technical=f"{es.get('high_risk', 0)} symbols at MEDIUM+ of {es.get('total', 0)}.",
                summary_business=f"{es.get('high_risk', 0)} named symbols need attention before release.",
                evidence=[
                    f"`{e.qualified_name}` ({e.entity_type}) — Ω={e.omega_local}"
                    for e in top_sym
                ],
                evidence_symbols=[e.qualified_name for e in top_sym],
                actions_in_repo=[
                    f"Refactor `{top_sym[0].qualified_name}` in `{top_sym[0].file_path}`."
                ]
                if top_sym
                else [],
            )
        )

        god = sorted(
            ctx.entities,
            key=lambda e: (e.method_count + e.field_count) * 10 + e.loc,
            reverse=True,
        )[:5]
        if god:
            g0 = god[0]
            surface = (g0.method_count + g0.field_count) * 5 + min(50, g0.loc / 10)
            dims.append(
                dim(
                    id="class_surface_area",
                    name="Class surface area",
                    family="field",
                    score=min(100, surface),
                    weight=0.16,
                    repo_aggregate=float(g0.method_count + g0.field_count),
                    unit="methods+fields (peak)",
                    summary_technical=(
                        f"Largest type surface: `{g0.qualified_name}` "
                        f"({g0.method_count} methods, {g0.field_count} fields)."
                    ),
                    summary_business="Oversized types are expensive to change and test.",
                    evidence=[
                        f"`{e.qualified_name}` — methods={e.method_count}, fields={e.field_count}"
                        for e in god
                    ],
                    evidence_symbols=[e.qualified_name for e in god],
                    actions_in_repo=[f"Decompose `{g0.qualified_name}` into focused types."],
                )
            )

        arity = top_entities(ctx, "parameter_count")
        if arity and arity[0][1] > 4:
            dims.append(
                dim(
                    id="parameter_arity",
                    name="Parameter arity pressure",
                    family="field",
                    score=norm_score(float(arity[0][1]), 12.0),
                    weight=0.12,
                    repo_aggregate=float(arity[0][1]),
                    unit="max parameters",
                    summary_technical=f"Widest signature: {int(arity[0][1])} parameters.",
                    summary_business="Wide APIs are harder to use and evolve safely.",
                    evidence=[
                        f"`{e.qualified_name}` — {int(v)} params" for e, v in arity
                    ],
                    evidence_symbols=[e.qualified_name for e, _ in arity],
                    actions_in_repo=[f"Introduce parameter object for `{arity[0][0].qualified_name}`."],
                )
            )

    if ctx.top_by_language:
        lang_rows = sorted(ctx.top_by_language.items(), key=lambda x: x[1], reverse=True)
        dims.append(
            dim(
                id="language_profile",
                name="Language stack",
                family="field",
                score=norm_score(lang_rows[0][1], 60.0),
                weight=0.08,
                repo_aggregate=lang_rows[0][1],
                unit="Ω mean per language",
                summary_technical=", ".join(f"{k}={v:.2f}" for k, v in lang_rows),
                summary_business=f"Primary language stress: {lang_rows[0][0]} (Ω={lang_rows[0][1]:.2f}).",
                evidence=[
                    f"{lang}: {len(ctx.lang_files[lang])} files"
                    for lang in sorted(ctx.lang_files, key=lambda k: -len(ctx.lang_files[k]))
                ],
                actions_in_repo=[f"Prioritize {lang_rows[0][0]} reviews."],
            )
        )

    if ctx.dir_rollup:
        worst = ctx.dir_rollup[0]
        dims.append(
            dim(
                id="module_topology",
                name="Package topology",
                family="field",
                score=norm_score(worst[1], 60.0),
                weight=0.10,
                repo_aggregate=worst[1],
                unit="Ω mean per top folder",
                summary_technical=f"Hottest folder `{worst[0]}/` mean Ω={worst[1]:.2f}.",
                summary_business=f"Quality debt concentrates under `{worst[0]}/`.",
                evidence=[
                    f"`{n}/` — Ω={avg:.2f} ({cnt} files)" for n, avg, cnt in ctx.dir_rollup
                ],
                actions_in_repo=[f"Sprint budget for `{worst[0]}/`."],
            )
        )

    scan = ctx.source_scan
    if scan and scan.files_scanned:
        async_score = min(100, scan.total_async * 2.5)
        dims.append(
            dim(
                id="async_concurrency",
                name="Async & concurrency",
                family="field",
                score=async_score,
                weight=0.14,
                repo_aggregate=float(scan.total_async),
                unit="pattern hits",
                summary_technical=(
                    f"Async/thread patterns: {scan.total_async} hits in {scan.files_scanned} scanned files."
                ),
                summary_business="Concurrency increases testing and failure-mode complexity.",
                evidence=[
                    f"`{st.path}` — {st.async_hits} hits"
                    for st in sorted(scan.per_file, key=lambda s: -s.async_hits)[:5]
                    if st.async_hits
                ],
                actions_in_repo=["Add concurrency tests around top async modules."],
            )
        )
        err_score = min(100, scan.total_error * 1.8)
        dims.append(
            dim(
                id="error_path_complexity",
                name="Error-path complexity",
                family="field",
                score=err_score,
                weight=0.13,
                repo_aggregate=float(scan.total_error),
                unit="try/except hits",
                summary_technical=f"Exception paths: {scan.total_error} constructs scanned.",
                summary_business="Heavy error handling can hide failure modes and debt.",
                evidence=[
                    f"`{st.path}` — {st.error_hits} hits"
                    for st in sorted(scan.per_file, key=lambda s: -s.error_hits)[:5]
                    if st.error_hits
                ],
                actions_in_repo=["Simplify exception ladders in hottest files."],
            )
        )

    if scan and (scan.test_file_count > 0 or scan.prod_file_count > 0):
        gap = max(0, scan.test_omega_mean - scan.prod_omega_mean)
        dims.append(
            dim(
                id="test_debt_split",
                name="Test vs production field",
                family="field",
                score=min(100, gap * 2 + norm_score(scan.test_omega_mean, 60)),
                weight=0.11,
                repo_aggregate=round(gap, 2),
                unit="Ω_test - Ω_prod",
                summary_technical=(
                    f"Prod mean Ω={scan.prod_omega_mean:.2f}, test mean Ω={scan.test_omega_mean:.2f}."
                ),
                summary_business="Test code health diverging from production affects CI trust.",
                evidence=[
                    f"Production files: {scan.prod_file_count}, test paths: {scan.test_file_count}"
                ],
                actions_in_repo=["Align test module complexity with production standards."],
            )
        )

    if scan and scan.files_scanned:
        hint_ratio = scan.total_type_hints / max(1, scan.files_scanned * 20) * 100
        dims.append(
            dim(
                id="type_surface_coverage",
                name="Type surface coverage",
                family="field",
                score=max(0, 100 - min(100, hint_ratio * 3)),
                weight=0.09,
                repo_aggregate=round(hint_ratio, 1),
                unit="hint density",
                summary_technical=f"Type-hint density proxy {hint_ratio:.1f} in scanned files.",
                summary_business="Stronger typing reduces runtime surprises in large codebases.",
                evidence=[],
                actions_in_repo=["Increase annotations on public APIs in hotspot modules."],
            )
        )

    return dims
