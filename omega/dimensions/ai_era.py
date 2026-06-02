"""AI-era family: generated code, prompts (repos with AI/codegen signals only)."""

from __future__ import annotations

from omega.dimensions.context import DimensionContext
from omega.dimensions.core import RepoDimension, dim, norm_score


def _ai_era_qualifies(ctx: DimensionContext) -> bool:
    scan = ctx.source_scan
    if scan and (scan.generated_files or scan.total_prompt):
        return True
    if ctx.root and (ctx.root / "README.md").is_file():
        try:
            blob = (ctx.root / "README.md").read_text(encoding="utf-8", errors="replace")[:12_000].lower()
        except OSError:
            blob = ""
        if any(
            k in blob
            for k in (
                "openai",
                "langchain",
                "llm",
                "anthropic",
                "copilot",
                "codegen",
                "prompt engineering",
            )
        ):
            return True
    return False


def build_ai_era_dimensions(ctx: DimensionContext) -> list[RepoDimension]:
    if not ctx.files or not _ai_era_qualifies(ctx):
        return []

    scan = ctx.source_scan
    dims: list[RepoDimension] = []

    if scan and scan.generated_files:
        gen_score = min(100, scan.generated_files * 25 + scan.total_prompt * 3)
        dims.append(
            dim(
                id="generated_code_stress",
                name="Generated code stress",
                family="ai_era",
                score=gen_score,
                weight=0.14,
                repo_aggregate=float(scan.generated_files),
                unit="generated files",
                summary_technical=f"{scan.generated_files} file(s) with codegen markers in scan sample.",
                summary_business="Generated layers need separate review and regeneration discipline.",
                evidence=[f"`{st.path}`" for st in scan.per_file if st.generated][:6],
                qualification="Codegen / auto-generated markers in source",
                actions_in_repo=["Exclude or gate generated paths in Ω budgets; regenerate from schema."],
            )
        )

    if scan and scan.total_prompt:
        prompt_score = min(100, scan.total_prompt * 8)
        dims.append(
            dim(
                id="prompt_surface",
                name="LLM prompt surface",
                family="ai_era",
                score=prompt_score,
                weight=0.12,
                repo_aggregate=float(scan.total_prompt),
                unit="prompt hits",
                summary_technical=f"LLM/prompt patterns: {scan.total_prompt} in scanned files.",
                summary_business="AI call sites need versioning, evals, and cost/latency controls.",
                evidence=[
                    f"`{st.path}` — {st.prompt_hits}" for st in scan.per_file if st.prompt_hits
                ][:5],
                qualification="LLM / prompt call sites in source",
                actions_in_repo=["Add prompt regression tests and redact secrets in templates."],
            )
        )

    ai_velocity = min(
        100,
        ctx.omega_index * 0.35
        + (scan.total_prompt if scan else 0) * 5
        + norm_score(ctx.pillars.get("textual_entropy", 0), 6.0) * 0.2,
    )
    dims.append(
        dim(
            id="ai_change_risk",
            name="AI-era change risk",
            family="ai_era",
            score=ai_velocity,
            weight=0.16,
            repo_aggregate=ai_velocity,
            unit="composite",
            summary_technical=(
                f"Composite: Ω, prompt surface, lexical entropy (Ω={ctx.omega_index:.2f})."
            ),
            summary_business="Risk profile when AI tooling accelerates change without field discipline.",
            evidence=[],
            qualification="Repository uses AI/codegen signals",
            actions_in_repo=["Pair AI-assisted edits with Ω scan on every significant PR."],
        )
    )

    return dims
