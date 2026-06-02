"""Heuristic language worker — regex symbols + implementation sketches."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from omega.agents.base import LanguageWorkerAgent, WorkerContext
from omega.agents.metadata import WorkerOutput, WorkerResult
from omega.agents.registry import capabilities_for_strategy, strategy_for_language, worker_id_for
from omega.agents.strategies import STRATEGY_HEURISTIC_SYMBOLS
from omega.discover import SourceFile
from omega.entities import EntityMetrics, analyze_file_entities
from omega.metrics import FileMetrics, _omega_local, _risk_band
from omega.metrics_heuristic import analyze_source_text
from omega.scan_config import file_worker_threads


class HeuristicLanguageWorker(LanguageWorkerAgent):
    """One worker instance per non-Python language (JS, Go, Java, …)."""

    def __init__(self, language: str) -> None:
        self.language = language
        self.strategy = strategy_for_language(language)
        self.worker_id = worker_id_for(language, self.strategy)
        self.capabilities = capabilities_for_strategy(self.strategy)

    def _analyze_one(
        self, sf: SourceFile, ctx: WorkerContext
    ) -> tuple[FileMetrics | None, list[EntityMetrics]]:
        src = ctx.sources.get(sf.path, "")
        if not src.strip():
            return None, []
        cout = ctx.coupling_out.get(sf.path, 0)
        cin = ctx.coupling_in.get(sf.path, 0)
        try:
            h = analyze_source_text(src, self.language)
            omega = _omega_local(
                h["h_struct"],
                h["cyclomatic"],
                h["nesting_depth"],
                cout,
                h["compression_ratio"],
            )
            fm = FileMetrics(
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
            ents = analyze_file_entities(sf.rel_path, src, self.language)
            return fm, ents
        except SyntaxError:
            h = analyze_source_text(src, self.language)
            omega = _omega_local(
                h["h_struct"],
                h["cyclomatic"],
                h["nesting_depth"],
                cout,
                h["compression_ratio"],
            )
            fm = FileMetrics(
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
            ents = analyze_file_entities(sf.rel_path, src, self.language)
            return fm, ents

    def analyze(
        self,
        files: list[SourceFile],
        ctx: WorkerContext,
    ) -> WorkerOutput:
        t0 = time.perf_counter()
        metrics: list[FileMetrics] = []
        entities: list[EntityMetrics] = []
        error: str | None = None

        try:
            workers = min(file_worker_threads(), max(1, len(files)))
            if workers <= 1 or len(files) < 4:
                for sf in files:
                    fm, ents = self._analyze_one(sf, ctx)
                    if fm:
                        metrics.append(fm)
                    entities.extend(ents)
            else:
                with ThreadPoolExecutor(max_workers=workers) as pool:
                    futures = {
                        pool.submit(self._analyze_one, sf, ctx): sf for sf in files
                    }
                    for fut in as_completed(futures):
                        fm, ents = fut.result()
                        if fm:
                            metrics.append(fm)
                        entities.extend(ents)
        except Exception as e:
            error = str(e)

        elapsed = (time.perf_counter() - t0) * 1000
        result = WorkerResult(
            worker_id=self.worker_id,
            language=self.language,
            strategy=self.strategy,
            status="error" if error else "completed",
            files_analyzed=len(metrics),
            entities_found=len(entities),
            duration_ms=round(elapsed, 2),
            error=error,
            capabilities=list(self.capabilities),
        )
        return WorkerOutput(result=result, files=metrics, entities=entities)
