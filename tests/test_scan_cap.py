"""Tests for optional file cap during scan."""

from __future__ import annotations

from pathlib import Path

from omega.scan import scan_repository


def test_max_files_caps_inventory(tmp_path: Path):
    for i in range(10):
        (tmp_path / f"m{i}.py").write_text(f"def f{i}():\n    return {i}\n", encoding="utf-8")
    files, _, inv, manifest = scan_repository(tmp_path, max_files=3)
    assert len(inv.files) == 3
    assert len(files) == 3
    assert manifest.total_files == 3
    assert len(manifest.workers_planned) >= 1
