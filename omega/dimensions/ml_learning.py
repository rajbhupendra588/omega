"""Machine learning & deep learning family: stack, training, inference, experiment hygiene."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from omega.dimensions.context import DimensionContext
from omega.dimensions.core import RepoDimension, dim

_DEP_FRAMEWORKS: list[tuple[str, str]] = [
    ("pytorch", r"\b(torch|pytorch)\b"),
    ("tensorflow", r"\b(tensorflow|tf\.)\b"),
    ("keras", r"\bkeras\b"),
    ("scikit-learn", r"\b(sklearn|scikit-learn)\b"),
    ("jax", r"\b(jax|flax)\b"),
    ("xgboost", r"\bxgboost\b"),
    ("lightgbm", r"\blightgbm\b"),
    ("catboost", r"\bcatboost\b"),
    ("huggingface", r"\b(transformers|huggingface|datasets)\b"),
    ("onnx", r"\bonnx\b"),
    ("mlflow", r"\bmlflow\b"),
    ("wandb", r"\b(wandb|weights\s*&\s*biases)\b"),
]

_ML_DIR_NAMES = frozenset(
    {
        "models",
        "model",
        "training",
        "train",
        "inference",
        "notebooks",
        "notebook",
        "experiments",
        "experiment",
        "ml",
        "deep_learning",
        "deeplearning",
        "features",
        "pipelines",
    }
)

_MODEL_ARTIFACT_SUFFIXES = frozenset(
    {".pt", ".pth", ".onnx", ".h5", ".hdf5", ".pkl", ".pickle", ".joblib", ".safetensors"}
)


@dataclass
class MLRepoSignals:
    frameworks: list[str] = field(default_factory=list)
    notebook_count: int = 0
    model_artifact_count: int = 0
    ml_dir_hits: list[str] = field(default_factory=list)
    source_ml_hits: int = 0
    source_ml_files: int = 0

    @property
    def is_ml_repo(self) -> bool:
        return bool(
            self.frameworks
            or self.notebook_count
            or self.model_artifact_count
            or self.ml_dir_hits
            or self.source_ml_hits
        )


def _read_dep_blob(root: Path) -> str:
    parts: list[str] = []
    for name in (
        "requirements.txt",
        "requirements-dev.txt",
        "pyproject.toml",
        "Pipfile",
        "environment.yml",
        "conda.yml",
        "setup.cfg",
    ):
        p = root / name
        if p.is_file():
            try:
                parts.append(p.read_text(encoding="utf-8", errors="replace")[:24_000])
            except OSError:
                pass
    return "\n".join(parts).lower()


def _frameworks_from_blob(blob: str) -> list[str]:
    found: list[str] = []
    for label, pattern in _DEP_FRAMEWORKS:
        if re.search(pattern, blob, re.I):
            found.append(label)
    return found


def discover_ml_signals(ctx: DimensionContext) -> MLRepoSignals:
    signals = MLRepoSignals()
    scan = ctx.source_scan
    if scan:
        signals.source_ml_hits = scan.total_ml_dl
        signals.source_ml_files = scan.ml_dl_files

    domains = [str(d).lower() for d in (ctx.service_context.get("business_domains") or [])]
    if "ml" in domains or "deep_learning" in domains:
        if "ml" not in signals.frameworks:
            signals.frameworks.append("inferred-domain")

    for f in ctx.files:
        rel = f.path.replace("\\", "/")
        suffix = Path(rel).suffix.lower()
        if suffix == ".ipynb":
            signals.notebook_count += 1
        elif suffix in _MODEL_ARTIFACT_SUFFIXES:
            signals.model_artifact_count += 1
        parts = {p.lower() for p in rel.split("/")}
        if parts & _ML_DIR_NAMES and rel not in signals.ml_dir_hits:
            signals.ml_dir_hits.append(rel)

    if ctx.root and ctx.root.is_dir():
        dep_blob = _read_dep_blob(ctx.root)
        for fw in _frameworks_from_blob(dep_blob):
            if fw not in signals.frameworks:
                signals.frameworks.append(fw)

    signals.ml_dir_hits = signals.ml_dir_hits[:12]
    return signals


def build_ml_learning_dimensions(ctx: DimensionContext) -> list[RepoDimension]:
    if not ctx.files:
        return []
    signals = discover_ml_signals(ctx)
    if not signals.is_ml_repo:
        return []

    dims: list[RepoDimension] = []
    scan = ctx.source_scan
    fw_count = len(signals.frameworks)
    diversity = min(100, fw_count * 22 + max(0, fw_count - 2) * 15)
    dims.append(
        dim(
            id="ml_framework_surface",
            name="ML framework surface",
            family="ml_dl",
            score=diversity,
            weight=0.14,
            repo_aggregate=float(fw_count),
            unit="frameworks",
            summary_technical=(
                f"Detected {fw_count} ML/DL stack signal(s): "
                f"{', '.join(signals.frameworks) or 'path/source only'}."
            ),
            summary_business=(
                "Multiple ML frameworks increase operational and hiring complexity — "
                "consolidate where possible."
            ),
            evidence=[f"Framework: `{f}`" for f in signals.frameworks[:8]],
            actions_in_repo=["Document canonical training/inference stack in README or ADR."],
        )
    )

    train_score = min(
        100,
        (scan.total_ml_dl if scan else 0) * 4
        + signals.notebook_count * 6
        + len(signals.ml_dir_hits) * 5,
    )
    if train_score > 8 or signals.notebook_count or "training" in " ".join(signals.ml_dir_hits).lower():
        dims.append(
            dim(
                id="training_pipeline_surface",
                name="Training pipeline surface",
                family="ml_dl",
                score=train_score,
                weight=0.16,
                repo_aggregate=float(train_score),
                unit="training exposure",
                summary_technical=(
                    f"Training markers in scan: {scan.total_ml_dl if scan else 0}; "
                    f"notebooks={signals.notebook_count}; ml_dirs={len(signals.ml_dir_hits)}."
                ),
                summary_business=(
                    "Training code paths need reproducibility, data versioning, and CI gates."
                ),
                evidence=(
                    [f"Notebook count: {signals.notebook_count}"]
                    + [f"`{p}`" for p in signals.ml_dir_hits[:5]]
                    + (
                        [
                            f"`{st.path}` — {st.ml_dl_hits} hits"
                            for st in (scan.per_file if scan else [])
                            if st.ml_dl_hits
                        ][:5]
                    )
                ),
                actions_in_repo=[
                    "Pin datasets, seeds, and hyperparameters; add training smoke tests."
                ],
            )
        )

    ml_files = {st.path for st in (scan.per_file if scan else []) if st.ml_dl_hits}
    inf_omega: list[float] = []
    for f in ctx.files:
        low = f.path.lower()
        if f.path in ml_files or any(
            seg in low for seg in ("inference", "predict", "serve", "model")
        ):
            inf_omega.append(f.omega_local)
    mean_inf = sum(inf_omega) / len(inf_omega) if inf_omega else ctx.omega_index
    inference_score = min(
        100,
        mean_inf * 0.85
        + (scan.total_ml_dl if scan else 0) * 2
        + signals.model_artifact_count * 8,
    )
    dims.append(
        dim(
            id="inference_operational_risk",
            name="Inference operational risk",
            family="ml_dl",
            score=inference_score,
            weight=0.18,
            repo_aggregate=round(mean_inf, 2),
            unit="Ω on ML paths",
            summary_technical=(
                f"Mean Ω on inference/ML-touched files: {mean_inf:.2f}; "
                f"model artifacts in tree: {signals.model_artifact_count}."
            ),
            summary_business=(
                "Serving paths with high complexity debt raise latency, incident, and rollback risk."
            ),
            evidence=[
                f"`{f.path}` Ω={f.omega_local:.1f}"
                for f in sorted(
                    [x for x in ctx.files if x.path in ml_files],
                    key=lambda x: x.omega_local,
                    reverse=True,
                )[:5]
            ],
            actions_in_repo=[
                "Add inference contract tests and monitor p95 latency on model endpoints."
            ],
        )
    )

    tracking = {"mlflow", "wandb"} & set(signals.frameworks)
    gov_score = min(
        100,
        signals.notebook_count * 10
        + max(0, 40 - len(tracking) * 20)
        + signals.model_artifact_count * 5,
    )
    if signals.notebook_count or signals.model_artifact_count or not tracking:
        dims.append(
            dim(
                id="experiment_reproducibility",
                name="Experiment reproducibility",
                family="ml_dl",
                score=gov_score,
                weight=0.12,
                repo_aggregate=float(signals.notebook_count),
                unit="governance gap",
                summary_technical=(
                    f"Notebooks={signals.notebook_count}, artifacts={signals.model_artifact_count}, "
                    f"experiment tracking detected: {bool(tracking)}."
                ),
                summary_business=(
                    "Notebooks and binary checkpoints without experiment tracking hinder audit and rollback."
                ),
                evidence=[
                    f"Notebooks: {signals.notebook_count}",
                    f"Model artifacts: {signals.model_artifact_count}",
                ]
                + ([f"Tracking: {', '.join(sorted(tracking))}"] if tracking else []),
                actions_in_repo=[
                    "Adopt MLflow/W&B or equivalent; version datasets and export notebooks to modules."
                ],
            )
        )

    composite = min(
        100,
        ctx.omega_index * 0.4
        + diversity * 0.25
        + inference_score * 0.2
        + (scan.total_ml_dl if scan else 0) * 3,
    )
    dims.append(
        dim(
            id="ml_change_risk",
            name="ML/DL change risk",
            family="ml_dl",
            score=composite,
            weight=0.15,
            repo_aggregate=composite,
            unit="composite",
            summary_technical=(
                f"Composite ML/DL risk: Ω={ctx.omega_index:.2f}, "
                f"frameworks={fw_count}, inference stress={inference_score:.1f}."
            ),
            summary_business=(
                "ML systems need Ω scans on every training or serving change — "
                "field debt compounds silently in notebooks and scripts."
            ),
            evidence=[],
            actions_in_repo=["Run Ω on PRs that touch `models/`, training, or inference paths."],
        )
    )

    return dims
