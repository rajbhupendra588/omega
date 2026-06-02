"""Metadata models for master / language worker orchestration."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class LanguageStackEntry:
    """One language detected in the repository tech stack."""

    language: str
    file_count: int
    share_pct: float
    worker_id: str
    strategy: str
    capabilities: tuple[str, ...]


@dataclass
class WorkerSpec:
    """A language worker the master agent plans to spawn."""

    worker_id: str
    language: str
    strategy: str
    file_count: int
    capabilities: list[str] = field(default_factory=list)


@dataclass
class WorkerResult:
    """Outcome from a single language worker run."""

    worker_id: str
    language: str
    strategy: str
    status: str
    files_analyzed: int
    entities_found: int
    duration_ms: float
    error: str | None = None
    capabilities: list[str] = field(default_factory=list)


@dataclass
class WorkerOutput:
    """Full payload returned by a language worker to the master agent."""

    result: WorkerResult
    files: list[Any] = field(default_factory=list)
    entities: list[Any] = field(default_factory=list)


@dataclass
class MasterManifest:
    """Complete orchestration metadata owned by the master agent."""

    root: str
    total_files: int
    total_bytes: int
    primary_language: str
    tech_stack: list[LanguageStackEntry]
    workers_planned: list[WorkerSpec]
    worker_results: list[WorkerResult] = field(default_factory=list)
    orchestration_plan: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": self.root,
            "total_files": self.total_files,
            "total_bytes": self.total_bytes,
            "primary_language": self.primary_language,
            "tech_stack": [asdict(e) for e in self.tech_stack],
            "workers_planned": [asdict(w) for w in self.workers_planned],
            "worker_results": [asdict(r) for r in self.worker_results],
            "orchestration_plan": list(self.orchestration_plan),
        }
