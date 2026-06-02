"""Single-pass source scans on a capped hotspot set (performance)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_MAX_FILES = 48
_MAX_BYTES = 65_536

_RE_ASYNC = re.compile(
    r"\b(async\s+def|await\s+|asyncio\.|Promise\.|\.then\s*\(|setTimeout|"
    r"threading\.|ThreadPool|concurrent\.futures)\b"
)
_RE_ERROR = re.compile(r"\b(try\s*:|except\s+|finally\s*:|raise\s+)\b")
_RE_PROMPT = re.compile(
    r"\b(openai\.|anthropic\.|ChatCompletion|llm\.|langchain|"
    r"prompt\s*=|system_prompt|user_prompt|\"\"\"[^\"]{200,})\b",
    re.I,
)
_RE_GENERATED = re.compile(
    r"(DO NOT EDIT|auto-?generated|@generated|codegen|swagger-codegen|"
    r"protoc-gen|buf generate)",
    re.I,
)
_RE_OBSERVE = re.compile(
    r"\b(logging\.|logger\.|opentelemetry|prometheus|statsd|sentry\.|"
    r"metrics\.|trace\.|datadog\.)\b",
    re.I,
)
_RE_TYPEDEF = re.compile(r":\s*(int|str|float|bool|list|dict|Optional|Union|Any)\b")
_RE_ML_DL = re.compile(
    r"\b("
    r"torch\.|pytorch|tensorflow|tf\.keras|keras\.|sklearn|scikit-learn|"
    r"jax\.|flax\.|xgboost|lightgbm|catboost|"
    r"nn\.Module|forward\s*\(|backward\s*\(|DataLoader|Dataset|"
    r"mlflow\.|wandb\.|optuna\.|"
    r"\.fit\s*\(|\.predict\s*\(|train_loop|training_step|"
    r"cuda|device\s*=\s*['\"]cuda|gpu"
    r")\b",
    re.I,
)


@dataclass
class FileScanStats:
    path: str
    loc: int
    async_hits: int = 0
    error_hits: int = 0
    prompt_hits: int = 0
    generated: bool = False
    observe_hits: int = 0
    type_hint_hits: int = 0
    ml_dl_hits: int = 0
    is_test_path: bool = False


@dataclass
class SourceScanAggregate:
    files_scanned: int = 0
    per_file: list[FileScanStats] = field(default_factory=list)
    total_async: int = 0
    total_error: int = 0
    total_prompt: int = 0
    generated_files: int = 0
    total_observe: int = 0
    total_type_hints: int = 0
    total_ml_dl: int = 0
    ml_dl_files: int = 0
    test_file_count: int = 0
    prod_omega_sum: float = 0.0
    test_omega_sum: float = 0.0
    prod_file_count: int = 0
    test_loc: int = 0
    prod_loc: int = 0

    @property
    def test_omega_mean(self) -> float:
        return self.test_omega_sum / max(1, self.test_file_count)

    @property
    def prod_omega_mean(self) -> float:
        return self.prod_omega_sum / max(1, self.prod_file_count)


_TEST_SEG = re.compile(
    r"(^|/)(tests?|__tests__|spec|testdata|fixtures)(/|$)|"
    r"test_[^/]+\.py$|[^/]+_test\.go$|\.spec\.|\.test\.",
    re.I,
)


def _is_test_path(rel: str) -> bool:
    return bool(_TEST_SEG.search(rel.replace("\\", "/")))


def scan_sources(
    root: Path,
    file_paths: list[tuple[str, int, float]],
    *,
    entry_paths: list[str] | None = None,
) -> SourceScanAggregate:
    """
    Scan up to _MAX_FILES paths. file_paths: (rel_path, loc, omega_local).
    Prioritizes entry points and highest omega_local.
    """
    root = root.resolve()
    chosen: dict[str, tuple[int, float]] = {}
    for ep in entry_paths or []:
        for rel, loc, omega in file_paths:
            if rel == ep or rel.endswith("/" + ep) or rel.endswith(ep):
                chosen[rel] = (loc, omega)
    ranked = sorted(file_paths, key=lambda x: x[2], reverse=True)
    for rel, loc, omega in ranked:
        if len(chosen) >= _MAX_FILES:
            break
        chosen.setdefault(rel, (loc, omega))

    agg = SourceScanAggregate()
    for rel, (loc, omega) in chosen.items():
        path = root / rel
        if not path.is_file():
            continue
        try:
            raw = path.read_bytes()[:_MAX_BYTES]
            text = raw.decode("utf-8", errors="replace")
        except OSError:
            continue
        is_test = _is_test_path(rel)
        st = FileScanStats(
            path=rel,
            loc=loc,
            async_hits=len(_RE_ASYNC.findall(text)),
            error_hits=len(_RE_ERROR.findall(text)),
            prompt_hits=len(_RE_PROMPT.findall(text)),
            generated=bool(_RE_GENERATED.search(text)),
            observe_hits=len(_RE_OBSERVE.findall(text)),
            type_hint_hits=len(_RE_TYPEDEF.findall(text)),
            ml_dl_hits=len(_RE_ML_DL.findall(text)),
            is_test_path=is_test,
        )
        agg.per_file.append(st)
        agg.files_scanned += 1
        agg.total_async += st.async_hits
        agg.total_error += st.error_hits
        agg.total_prompt += st.prompt_hits
        agg.total_observe += st.observe_hits
        agg.total_type_hints += st.type_hint_hits
        agg.total_ml_dl += st.ml_dl_hits
        if st.ml_dl_hits:
            agg.ml_dl_files += 1
        if st.generated:
            agg.generated_files += 1
        if is_test:
            agg.test_file_count += 1
            agg.test_omega_sum += omega
            agg.test_loc += loc
        else:
            agg.prod_file_count += 1
            agg.prod_omega_sum += omega
            agg.prod_loc += loc

    # Roll up test/prod for ALL files (no read) for split dimension
    for rel, loc, omega in file_paths:
        if rel in chosen:
            continue
        if _is_test_path(rel):
            agg.test_file_count += 1
            agg.test_omega_sum += omega
            agg.test_loc += loc
        else:
            agg.prod_file_count += 1
            agg.prod_omega_sum += omega
            agg.prod_loc += loc

    return agg
