"""Base contract for language-specific worker agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omega.agents.metadata import WorkerOutput
    from omega.discover import SourceFile


@dataclass(frozen=True)
class WorkerContext:
    """Shared context passed from master to each language worker."""

    root: Path
    sources: dict[Path, str]
    coupling_out: dict[Path, int]
    coupling_in: dict[Path, int]


class LanguageWorkerAgent(ABC):
    """Analyzes all files for one language in a repository."""

    worker_id: str
    language: str
    strategy: str
    capabilities: tuple[str, ...]

    @abstractmethod
    def analyze(
        self,
        files: list[SourceFile],
        ctx: WorkerContext,
    ) -> WorkerOutput:
        """Process assigned files and return metrics + entities."""
