"""Java / Go language workers — full tree-sitter AST analysis."""

from __future__ import annotations

import time

from omega.agents.base import LanguageWorkerAgent, WorkerContext
from omega.agents.metadata import WorkerOutput, WorkerResult
from omega.agents.registry import capabilities_for_strategy, worker_id_for
from omega.agents.strategies import STRATEGY_AST_FULL
from omega.ast_tree_sitter import (
    AST_LANGUAGES,
    file_metrics_from_tree,
    parse_tree,
)
from omega.discover import SourceFile
from omega.entities import analyze_file_entities
from omega.entities_ts import analyze_ts_entities
from omega.metrics import FileMetrics, _omega_local, _risk_band
from omega.metrics_heuristic import analyze_source_text


class TreeSitterAstWorker(LanguageWorkerAgent):
    """Full AST via tree-sitter (Java, Go)."""

    def __init__(self, language: str) -> None:
        if language not in AST_LANGUAGES:
            raise ValueError(f"Unsupported AST language: {language}")
        self.language = language
        self.strategy = STRATEGY_AST_FULL
        self.worker_id = worker_id_for(language, STRATEGY_AST_FULL)
        self.capabilities = capabilities_for_strategy(STRATEGY_AST_FULL)

    def _fallback_metrics(
        self, sf: SourceFile, src: str, cout: int, cin: int
    ) -> FileMetrics:
        h = analyze_source_text(src, self.language)
        omega = _omega_local(
            h["h_struct"],
            h["cyclomatic"],
            h["nesting_depth"],
            cout,
            h["compression_ratio"],
        )
        return FileMetrics(
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

    def analyze(
        self,
        files: list[SourceFile],
        ctx: WorkerContext,
    ) -> WorkerOutput:
        t0 = time.perf_counter()
        metrics: list[FileMetrics] = []
        entities = []
        error: str | None = None

        try:
            for sf in files:
                src = ctx.sources.get(sf.path, "")
                if not src.strip():
                    continue
                cout = ctx.coupling_out.get(sf.path, 0)
                cin = ctx.coupling_in.get(sf.path, 0)
                tree = parse_tree(self.language, src)
                if tree is None:
                    metrics.append(self._fallback_metrics(sf, src, cout, cin))
                    entities.extend(
                        analyze_file_entities(sf.rel_path, src, self.language)
                    )
                    continue
                try:
                    metrics.append(
                        file_metrics_from_tree(
                            rel_path=sf.rel_path,
                            language=self.language,
                            source=src,
                            tree=tree,
                            coupling_out=cout,
                            coupling_in=cin,
                        )
                    )
                    entities.extend(
                        analyze_ts_entities(sf.rel_path, src, self.language, tree)
                    )
                except ValueError:
                    metrics.append(self._fallback_metrics(sf, src, cout, cin))
                    entities.extend(
                        analyze_file_entities(sf.rel_path, src, self.language)
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
            entities_found=len(entities),
            duration_ms=round(elapsed, 2),
            error=error,
            capabilities=list(self.capabilities),
        )
        return WorkerOutput(result=result, files=metrics, entities=entities)
