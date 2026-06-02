"""File-only worker for languages without symbol extraction (SQL, shell, …)."""

from __future__ import annotations

import time

from omega.agents.base import LanguageWorkerAgent, WorkerContext
from omega.agents.metadata import WorkerOutput, WorkerResult
from omega.agents.registry import capabilities_for_strategy, worker_id_for
from omega.agents.strategies import STRATEGY_FILE_METRICS
from omega.discover import SourceFile
from omega.metrics import FileMetrics, _omega_local, _risk_band
from omega.metrics_heuristic import analyze_source_text


class FileMetricsWorker(LanguageWorkerAgent):
    def __init__(self, language: str) -> None:
        self.language = language
        self.strategy = STRATEGY_FILE_METRICS
        self.worker_id = worker_id_for(language, self.strategy)
        self.capabilities = capabilities_for_strategy(self.strategy)

    def analyze(
        self,
        files: list[SourceFile],
        ctx: WorkerContext,
    ) -> WorkerOutput:
        t0 = time.perf_counter()
        metrics: list[FileMetrics] = []
        error: str | None = None

        try:
            for sf in files:
                src = ctx.sources.get(sf.path, "")
                if not src.strip():
                    continue
                cout = ctx.coupling_out.get(sf.path, 0)
                cin = ctx.coupling_in.get(sf.path, 0)
                h = analyze_source_text(src, self.language)
                omega = _omega_local(
                    h["h_struct"],
                    h["cyclomatic"],
                    h["nesting_depth"],
                    cout,
                    h["compression_ratio"],
                )
                metrics.append(
                    FileMetrics(
                        path=sf.rel_path,
                        language=self.language,
                        loc=h["loc"],
                        cyclomatic=h["cyclomatic"],
                        nesting_depth=h["nesting_depth"],
                        h_struct=h["h_struct"],
                        h_text=h["h_text"],
                        compression_ratio=h["compression_ratio"],
                        coupling_out=cout,
                        coupling_in=cin,
                        omega_local=omega,
                        risk_band=_risk_band(omega),
                        import_count=h.get("import_count", cout),
                    )
                )
        except Exception as e:
            error = str(e)

        elapsed = (time.perf_counter() - t0) * 1000
        result = WorkerResult(
            worker_id=self.worker_id,
            language=self.language,
            strategy=self.strategy,
            status="error" if error else "completed",
            files_analyzed=len(metrics),
            entities_found=0,
            duration_ms=round(elapsed, 2),
            error=error,
            capabilities=list(self.capabilities),
        )
        return WorkerOutput(result=result, files=metrics, entities=[])
