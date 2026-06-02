"""Machine learning & deep learning dimension family."""

from __future__ import annotations

from pathlib import Path

from omega.analyzer import analyze_repository
from omega.dimensions import build_repo_dimensions
from omega.dimensions.ml_learning import discover_ml_signals
from omega.dimensions.context import DimensionContext


def test_ml_dimensions_on_synthetic_repo(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text(
        "torch>=2.0\nmlflow\n", encoding="utf-8"
    )
    (tmp_path / "train.py").write_text(
        """
import torch
from torch.utils.data import DataLoader

class Net(torch.nn.Module):
    def forward(self, x):
        return x

def train_loop(model, loader):
    for batch in loader:
        model(batch)
""",
        encoding="utf-8",
    )
    outcome = analyze_repository(tmp_path, repo_display="ml_sample")
    dims = build_repo_dimensions(outcome, root=str(tmp_path))
    families = {d.family for d in dims}
    assert "ml_dl" in families
    ml_ids = {d.id for d in dims if d.family == "ml_dl"}
    assert "ml_framework_surface" in ml_ids
    assert "inference_operational_risk" in ml_ids
    assert "ml_change_risk" in ml_ids


def test_non_ml_repo_has_no_ml_dl_family(tmp_path: Path):
    (tmp_path / "app.py").write_text("def main():\n    print('ok')\n", encoding="utf-8")
    outcome = analyze_repository(tmp_path)
    dims = build_repo_dimensions(outcome, root=str(tmp_path))
    assert "ml_dl" not in {d.family for d in dims}


def test_discover_ml_signals_from_deps(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\ndependencies = ["tensorflow>=2.16"]\n',
        encoding="utf-8",
    )
    ctx = DimensionContext(
        display="x",
        root=tmp_path.resolve(),
        omega_index=50.0,
        quality_grade="C",
        pillars={},
        files=[],
        entities=[],
        entity_summary={},
        top_by_language={},
        bayesian_quality=50.0,
        epistemic_uncertainty=0.1,
        total_loc=0,
        file_count=0,
        metric_suite={},
        baseline_report=None,
    )
    sig = discover_ml_signals(ctx)
    assert "tensorflow" in sig.frameworks
