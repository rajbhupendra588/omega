"""Repository-specific quality dimensions (evidence from this codebase, not generic advice)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any

from omega.entities import EntityMetrics
from omega.metrics import FileMetrics


@dataclass
class RepoDimension:
    """One measurable quality dimension with repo-local evidence."""

    id: str
    name: str
    score: float
    band: str
    weight: float
    repo_aggregate: float
    unit: str
    summary_technical: str
    summary_business: str
    evidence: list[str] = field(default_factory=list)
    evidence_symbols: list[str] = field(default_factory=list)
    actions_in_repo: list[str] = field(default_factory=list)
    top_contributors: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _band(score: float) -> str:
    if score < 35:
        return "LOW"
    if score < 55:
        return "MEDIUM"
    if score < 75:
        return "HIGH"
    return "CRITICAL"


def _top_files(
    files: list[FileMetrics],
    key: str,
    *,
    n: int = 5,
    reverse: bool = True,
) -> list[tuple[FileMetrics, float]]:
    scored = [(f, float(getattr(f, key))) for f in files]
    scored.sort(key=lambda x: x[1], reverse=reverse)
    return scored[:n]


def _top_entities(
    entities: list[EntityMetrics],
    key: str,
    *,
    n: int = 5,
) -> list[tuple[EntityMetrics, float]]:
    scored = [(e, float(getattr(e, key))) for e in entities]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:n]


def _dir_rollup(files: list[FileMetrics]) -> list[tuple[str, float, int]]:
    buckets: dict[str, list[float]] = defaultdict(list)
    for f in files:
        parts = f.path.replace("\\", "/").split("/")
        prefix = parts[0] if len(parts) > 1 else "(root)"
        buckets[prefix].append(f.omega_local)
    rows = [
        (name, sum(v) / len(v), len(v))
        for name, v in buckets.items()
    ]
    rows.sort(key=lambda x: x[1], reverse=True)
    return rows[:8]


def _norm_score(value: float, scale: float) -> float:
    return round(min(100.0, max(0.0, (value / scale) * 100.0)), 1)


def file_from_report_dict(data: dict[str, Any]) -> FileMetrics:
    return FileMetrics(
        path=data["path"],
        loc=int(data.get("loc", 1)),
        cyclomatic=int(data["cyclomatic"]),
        nesting_depth=int(data["nesting_depth"]),
        h_struct=float(data["h_struct"]),
        h_text=float(data["h_text"]),
        compression_ratio=float(data["compression_ratio"]),
        coupling_out=int(data["coupling_out"]),
        coupling_in=int(data["coupling_in"]),
        omega_local=float(data["omega_local"]),
        risk_band=data["risk_band"],
        language=data.get("language", "unknown"),
    )


def entity_from_report_dict(data: dict[str, Any]) -> EntityMetrics:
    return EntityMetrics(
        entity_type=data["entity_type"],
        qualified_name=data["qualified_name"],
        file_path=data["file_path"],
        line_start=int(data["line_start"]),
        line_end=int(data["line_end"]),
        loc=int(data["loc"]),
        cyclomatic=int(data["cyclomatic"]),
        nesting_depth=int(data["nesting_depth"]),
        omega_local=float(data["omega_local"]),
        risk_band=data["risk_band"],
        improvement_areas=tuple(data.get("improvement_areas", [])),
        improvement_areas_business=tuple(data.get("improvement_areas_business", [])),
        implementation_plan=tuple(data.get("implementation_plan", [])),
        implementation_summary=tuple(data.get("implementation_summary", [])),
        parent_class=data.get("parent_class"),
        parameter_count=int(data.get("parameter_count", 0)),
        method_count=int(data.get("method_count", 0)),
        field_count=int(data.get("field_count", 0)),
    )


def build_dimensions_from_report(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Rebuild dimensions from saved report JSON (for runs analyzed before this feature)."""
    existing = report.get("dimensions")
    if existing:
        return list(existing)
    if not report.get("files"):
        return []

    class _Snapshot:
        pass

    snap = _Snapshot()
    snap.repo_display = report.get("repo_display", "repository")
    snap.omega_index = float(report.get("omega_index", 0))
    snap.files = [file_from_report_dict(f) for f in report["files"]]
    snap.entities = [entity_from_report_dict(e) for e in report.get("entities", [])]
    snap.pillars = dict(report.get("pillars", {}))
    snap.top_by_language = dict(report.get("languages", report.get("top_by_language", {})))
    snap.entity_summary = dict(report.get("entity_summary", {}))

    return [d.to_dict() for d in build_repo_dimensions(snap)]


def ensure_report_has_dimensions(report: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Return report with dimensions populated; bool = whether JSON should be rewritten."""
    if report.get("dimensions"):
        return report, False
    dims = build_dimensions_from_report(report)
    if not dims:
        report["dimensions"] = []
        return report, False
    report = {**report, "dimensions": dims}
    return report, True


def build_repo_dimensions(outcome: Any) -> list[RepoDimension]:
    """Build multi-dimensional profile grounded in this repository's files and symbols."""
    files = outcome.files
    entities = outcome.entities
    p = outcome.pillars
    display = outcome.repo_display
    dims: list[RepoDimension] = []

    if not files:
        return dims

    mean_omega = outcome.omega_index

    # --- 1. Structural entropy ---
    top_hs = _top_files(files, "h_struct")
    agg = p["structural_entropy"]
    score = _norm_score(agg, 6.0)
    dim = RepoDimension(
        id="structural_entropy",
        name="Structural entropy",
        score=score,
        band=_band(score),
        weight=0.28,
        repo_aggregate=agg,
        unit="bits (mean H_struct)",
        summary_technical=(
            f"In `{display}`, mean AST structural entropy is {agg:.3f} bits across "
            f"{len(files)} files (Ω_repo={mean_omega:.2f})."
        ),
        summary_business=(
            f"Code in this project varies in how predictable its structure is; "
            f"the hardest-to-read modules are listed below by file name."
        ),
        evidence=[
            f"`{f.path}` — H_struct={val:.3f}, Ω_local={f.omega_local}, {f.language}"
            for f, val in top_hs
        ],
        actions_in_repo=[
            f"Refactor `{top_hs[0][0].path}` first: highest structural entropy ({top_hs[0][1]:.3f}) in this repo.",
            *(
                f"Next: simplify control-flow variety in `{f.path}` (H_struct={val:.3f})."
                for f, val in top_hs[1:3]
            ),
        ],
        top_contributors=[
            {"path": f.path, "value": val, "omega_local": f.omega_local}
            for f, val in top_hs
        ],
    )
    dims.append(dim)

    # --- 2. Cyclomatic / control flow ---
    top_cyc_f = _top_files(files, "cyclomatic")
    top_cyc_e = _top_entities(entities, "cyclomatic") if entities else []
    agg = p["cyclomatic_pressure"]
    score = _norm_score(agg, 15.0)
    dim = RepoDimension(
        id="cyclomatic_pressure",
        name="Control-flow complexity",
        score=score,
        band=_band(score),
        weight=0.25,
        repo_aggregate=agg,
        unit="branches (mean McCabe)",
        summary_technical=(
            f"Mean cyclomatic complexity per file in `{display}` is {agg:.2f}; "
            f"p95 Ω_local={p.get('p95_omega_local', 0):.2f}."
        ),
        summary_business=(
            "More branches per file means more test cases and more places bugs can hide — "
            "these are the specific files and functions driving that cost here."
        ),
        evidence=[f"`{f.path}` — {int(val)} branches, nesting={f.nesting_depth}" for f, val in top_cyc_f],
        evidence_symbols=[
            f"`{e.qualified_name}` in `{e.file_path}` L{e.line_start}–{e.line_end} — {int(val)} branches"
            for e, val in top_cyc_e
        ],
        actions_in_repo=[
            (
                f"Split decision logic in `{top_cyc_e[0][0].file_path}` → "
                f"`{top_cyc_e[0][0].qualified_name}` ({int(top_cyc_e[0][1])} branches)."
            )
            if top_cyc_e
            else (
                f"Decompose `{top_cyc_f[0][0].path}` ({int(top_cyc_f[0][1])} branches) into smaller functions in the same module."
            ),
        ],
        top_contributors=[
            {"path": f.path, "value": val, "qualified_name": None}
            for f, val in top_cyc_f
        ],
    )
    dims.append(dim)

    # --- 3. Nesting depth ---
    top_nest_f = _top_files(files, "nesting_depth")
    top_nest_e = _top_entities(entities, "nesting_depth") if entities else []
    mean_nest = sum(f.nesting_depth for f in files) / len(files)
    score = _norm_score(mean_nest, 6.0)
    dim = RepoDimension(
        id="nesting_depth",
        name="Nesting depth",
        score=score,
        band=_band(score),
        weight=0.18,
        repo_aggregate=round(mean_nest, 2),
        unit="levels (mean max depth)",
        summary_technical=(
            f"Maximum nesting depth averages {mean_nest:.2f} levels per file in this tree."
        ),
        summary_business=(
            "Deeply nested code in this repository is harder to review and modify — "
            "these locations are where reviewers spend the most time."
        ),
        evidence=[f"`{f.path}` — depth {int(val)}, Ω={f.omega_local}" for f, val in top_nest_f],
        evidence_symbols=[
            f"`{e.qualified_name}` (`{e.file_path}:{e.line_start}`) — depth {int(val)}"
            for e, val in top_nest_e
        ],
        actions_in_repo=[
            (
                f"Flatten nested if/for chains in `{top_nest_e[0][0].file_path}` around "
                f"`{top_nest_e[0][0].qualified_name}` (depth {int(top_nest_e[0][1])})."
            )
            if top_nest_e
            else f"Extract inner blocks from `{top_nest_f[0][0].path}` into named helpers.",
        ],
        top_contributors=[{"path": f.path, "value": val} for f, val in top_nest_f],
    )
    dims.append(dim)

    # --- 4. Coupling field ---
    top_couple = sorted(
        files,
        key=lambda f: f.coupling_out + f.coupling_in,
        reverse=True,
    )[:5]
    agg = p["coupling_field"]
    score = _norm_score(agg, 5.0)
    cyclic = [f for f in files if f.coupling_out > 0 and f.coupling_in > 0]
    dim = RepoDimension(
        id="coupling_field",
        name="Module coupling",
        score=score,
        band=_band(score),
        weight=0.17,
        repo_aggregate=agg,
        unit="edges (mean in+out)",
        summary_technical=(
            f"Mean internal coupling per file is {agg:.2f}; "
            f"{len(cyclic)} file(s) participate in bidirectional import cycles in `{display}`."
        ),
        summary_business=(
            "Tightly linked files in this codebase mean teams cannot change one module "
            "without risking breakage in another — listed below."
        ),
        evidence=[
            f"`{f.path}` — imports {f.coupling_out} internal module(s), imported by {f.coupling_in}"
            for f in top_couple
        ],
        actions_in_repo=[
            f"Break the import cycle involving `{cyclic[0].path}` ↔ peers (out={cyclic[0].coupling_out}, in={cyclic[0].coupling_in})."
            if cyclic
            else f"Reduce fan-out from `{top_couple[0].path}` ({top_couple[0].coupling_out} outbound internal imports).",
            *[
                f"Introduce a facade or interface at `{f.path}` to hide {f.coupling_in} inbound dependencies."
                for f in top_couple[1:3]
                if f.coupling_in >= 2
            ],
        ],
        top_contributors=[
            {
                "path": f.path,
                "coupling_out": f.coupling_out,
                "coupling_in": f.coupling_in,
            }
            for f in top_couple
        ],
    )
    dims.append(dim)

    # --- 5. Topological cycles (repo-specific list) ---
    score = _norm_score(float(len(cyclic)), max(1, len(files) * 0.15))
    dim = RepoDimension(
        id="topological_cycles",
        name="Dependency cycles",
        score=score,
        band=_band(score),
        weight=0.12,
        repo_aggregate=float(len(cyclic)),
        unit="files in cycles",
        summary_technical=(
            f"β₁ proxy: {len(cyclic)} file(s) with both inbound and outbound internal edges."
        ),
        summary_business=(
            f"{len(cyclic)} module(s) in this repo sit in circular dependency chains — "
            "refactors there are the slowest and riskiest."
        ),
        evidence=[f"`{f.path}` — cycle participant (in={f.coupling_in}, out={f.coupling_out})" for f in cyclic[:8]],
        actions_in_repo=[
            f"Cut the cycle through `{cyclic[0].path}` by extracting shared types/protocols to a leaf module."
            for _ in [0]
            if cyclic
        ]
        or ["No bidirectional internal import cycles detected in this repository."],
        top_contributors=[{"path": f.path} for f in cyclic[:5]],
    )
    dims.append(dim)

    # --- 6. Information density / compressibility ---
    top_r = _top_files(files, "compression_ratio")
    agg = p["information_density"]
    score = _norm_score(agg, 4.0)
    dim = RepoDimension(
        id="information_density",
        name="Information density",
        score=score,
        band=_band(score),
        weight=0.12,
        repo_aggregate=agg,
        unit="gzip ratio",
        summary_technical=f"Mean gzip compression ratio {agg:.2f} (higher ⇒ more repetitive text).",
        summary_business=(
            "Files with repetitive patterns may indicate copy-paste or generated boilerplate in this project."
        ),
        evidence=[f"`{f.path}` — R_gzip={val:.2f}" for f, val in top_r],
        actions_in_repo=[
            f"Review `{top_r[0][0].path}` for duplicated logic (R={top_r[0][1]:.2f}) and deduplicate in-place."
        ],
        top_contributors=[{"path": f.path, "value": val} for f, val in top_r],
    )
    dims.append(dim)

    # --- 7. Textual entropy ---
    top_ht = _top_files(files, "h_text")
    agg = p["textual_entropy"]
    score = _norm_score(agg, 6.0)
    dim = RepoDimension(
        id="textual_entropy",
        name="Lexical diversity",
        score=score,
        band=_band(score),
        weight=0.10,
        repo_aggregate=agg,
        unit="bits (mean H_text)",
        summary_technical=f"Token-level entropy mean {agg:.3f} bits across `{display}`.",
        summary_business="High lexical diversity can mean inconsistent naming across this codebase.",
        evidence=[f"`{f.path}` — H_text={val:.3f}" for f, val in top_ht],
        actions_in_repo=[
            f"Align naming and vocabulary in `{top_ht[0][0].path}` with the dominant terms used in sibling modules."
        ],
        top_contributors=[{"path": f.path, "value": val} for f, val in top_ht],
    )
    dims.append(dim)

    # --- 8. Symbol surface (entity-level, this repo) ---
    if entities:
        high = [e for e in entities if e.risk_band in ("HIGH", "CRITICAL", "MEDIUM")]
        top_sym = sorted(entities, key=lambda e: e.omega_local, reverse=True)[:5]
        es = outcome.entity_summary
        score = _norm_score(float(es.get("high_risk", 0)), max(1, es.get("total", 1) * 0.2))
        dim = RepoDimension(
            id="symbol_surface",
            name="Symbol-level stress",
            score=score,
            band=_band(score),
            weight=0.20,
            repo_aggregate=float(es.get("high_risk", 0)),
            unit="high-risk symbols",
            summary_technical=(
                f"Measured {es.get('total', 0)} symbols: "
                f"{es.get('class', 0)} classes, {es.get('method', 0)} methods, "
                f"{es.get('function', 0)} functions, {es.get('field', 0)} fields; "
                f"{es.get('high_risk', 0)} at MEDIUM+ risk."
            ),
            summary_business=(
                f"This scan named {es.get('high_risk', 0)} classes/methods/fields in your repo "
                "that need attention before the next release."
            ),
            evidence=[
                f"`{e.qualified_name}` ({e.entity_type}) — `{e.file_path}`, Ω={e.omega_local}"
                for e in top_sym
            ],
            evidence_symbols=[e.qualified_name for e in top_sym],
            actions_in_repo=[
                f"Apply the implementation guide for `{e.qualified_name}` in `{e.file_path}` (Ω={e.omega_local})."
                for e in top_sym[:3]
                if e.implementation_plan or e.improvement_areas
            ]
            or [f"Refactor `{top_sym[0].qualified_name}` in `{top_sym[0].file_path}` first."],
            top_contributors=[
                {
                    "qualified_name": e.qualified_name,
                    "file_path": e.file_path,
                    "omega_local": e.omega_local,
                }
                for e in top_sym
            ],
        )
        dims.append(dim)

    # --- 9. Language / stack profile (this repo's languages) ---
    if outcome.top_by_language:
        lang_rows = sorted(outcome.top_by_language.items(), key=lambda x: x[1], reverse=True)
        lang_files: dict[str, list[FileMetrics]] = defaultdict(list)
        for f in files:
            lang_files[f.language].append(f)
        score = _norm_score(lang_rows[0][1] if lang_rows else 0, 60.0)
        dim = RepoDimension(
            id="language_profile",
            name="Language stack",
            score=score,
            band=_band(score),
            weight=0.08,
            repo_aggregate=lang_rows[0][1] if lang_rows else 0,
            unit="Ω mean per language",
            summary_technical=(
                "Per-language mean Ω_local in this repository: "
                + ", ".join(f"{k}={v:.2f}" for k, v in lang_rows)
            ),
            summary_business=(
                f"This codebase is primarily "
                f"{lang_rows[0][0]} (highest mean stress Ω={lang_rows[0][1]:.2f})."
            ),
            evidence=[
                f"{lang}: {len(lang_files[lang])} file(s), mean Ω={sum(x.omega_local for x in lf) / len(lf):.2f}"
                for lang, lf in sorted(lang_files.items(), key=lambda x: -len(x[1]))
            ],
            actions_in_repo=[
                f"Focus reviews on {lang_rows[0][0]} modules ({lang_rows[0][1]:.1f} mean Ω) before other languages."
            ],
            top_contributors=[
                {"language": k, "mean_omega": v, "file_count": len(lang_files[k])}
                for k, v in lang_rows
            ],
        )
        dims.append(dim)

    # --- 10. Module / directory topology ---
    dirs = _dir_rollup(files)
    if dirs:
        worst = dirs[0]
        score = _norm_score(worst[1], 60.0)
        dim = RepoDimension(
            id="module_topology",
            name="Package topology",
            score=score,
            band=_band(score),
            weight=0.10,
            repo_aggregate=worst[1],
            unit="Ω mean per top folder",
            summary_technical=(
                f"Top-level folders in `{display}` ranked by mean Ω_local; "
                f"hottest: `{worst[0]}/` ({worst[1]:.2f} over {worst[2]} files)."
            ),
            summary_business=(
                f"The `{worst[0]}/` area of this project carries the most quality debt — "
                "plan sprints around that folder."
            ),
            evidence=[
                f"`{name}/` — mean Ω={avg:.2f} across {cnt} file(s)"
                for name, avg, cnt in dirs
            ],
            actions_in_repo=[
                f"Allocate refactor budget to `{worst[0]}/` (mean Ω={worst[1]:.2f}, {worst[2]} files) before expanding features there.",
                *[
                    f"Stabilize `{name}/` (Ω={avg:.2f}) after `{worst[0]}/`."
                    for name, avg, cnt in dirs[1:3]
                ],
            ],
            top_contributors=[
                {"folder": name, "mean_omega": avg, "file_count": cnt}
                for name, avg, cnt in dirs
            ],
        )
        dims.append(dim)

    return dims
