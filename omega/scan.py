"""Scan repository — master agent orchestrates per-language workers."""

from __future__ import annotations

from pathlib import Path

from omega.agents.master import MasterAgent
from omega.agents.metadata import MasterManifest
from omega.discover import RepoInventory
from omega.entities import EntityMetrics
from omega.metrics import FileMetrics


def scan_repository(
    root: Path,
    *,
    max_files: int | None = None,
    parallel_workers: bool = True,
) -> tuple[list[FileMetrics], list[EntityMetrics], RepoInventory, MasterManifest]:
    """
    Discover tech stack, spawn language workers dynamically, merge metrics.
    Returns (files, entities, inventory, master_manifest).
    """
    master = MasterAgent(
        root,
        max_files=max_files,
        parallel_workers=parallel_workers,
    )
    return master.run()
