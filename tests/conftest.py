"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_REPO = ROOT / "sample_repo"


@pytest.fixture
def sample_repo() -> Path:
    assert SAMPLE_REPO.is_dir()
    return SAMPLE_REPO
