"""Python language worker — full AST analysis."""

from __future__ import annotations

import time
from pathlib import Path

from omega.agents.base import LanguageWorkerAgent, WorkerContext
from omega.agents.metadata import WorkerOutput, WorkerResult
from omega.agents.registry import capabilities_for_strategy, worker_id_for
from omega.agents.strategies import STRATEGY_AST_FULL
from omega.discover import SourceFile
from omega.entities import EntityMetrics, analyze_file_entities, analyze_python_entities
from omega.metrics import FileMetrics, _omega_local, _risk_band
from omega.parse_util import parse_python
from omega import metrics as py_metrics


class PythonWorkerAgent(LanguageWorkerAgent):
    worker_id = worker_id_for("python", STRATEGY_AST_FULL)
    language = "python"
    strategy = STRATEGY_AST_FULL
    capabilities = capabilities_for_strategy(STRATEGY_AST_FULL)

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
            for sf in files:
                src = ctx.sources.get(sf.path, "")
                if not src.strip():
                    continue
                cout = ctx.coupling_out.get(sf.path, 0)
                cin = ctx.coupling_in.get(sf.path, 0)
                try:
                    tree = parse_python(src, filename=str(sf.path))
                    m = self._file_metrics_from_tree(
                        sf, ctx.root, src, tree, cout, cin
                    )
                    metrics.append(m)
                    entities.extend(
                        analyze_python_entities(m.path, src, tree)
                    )
                except SyntaxError:
                    from omega.metrics_heuristic import analyze_source_text

                    h = analyze_source_text(src, "python")
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
                            language="python",
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
                    entities.extend(
                        analyze_file_entities(sf.rel_path, src, "python")
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

    def _file_metrics_from_tree(
        self,
        sf: SourceFile,
        root: Path,
        source: str,
        tree,
        coupling_out: int,
        coupling_in: int,
    ) -> FileMetrics:
        cyclomatic, nesting = py_metrics._cyclomatic_and_nesting(tree)
        h_struct = py_metrics._structural_entropy(tree)
        h_text = py_metrics._textual_entropy(source)
        loc = sum(
            1
            for line in source.splitlines()
            if line.strip() and not line.strip().startswith("#")
        )
        compress = py_metrics._compression_ratio(source)
        omega = _omega_local(h_struct, cyclomatic, nesting, coupling_out, compress)
        return FileMetrics(
            path=sf.rel_path,
            language="python",
            loc=loc,
            cyclomatic=cyclomatic,
            nesting_depth=nesting,
            h_struct=round(h_struct, 3),
            h_text=round(h_text, 3),
            compression_ratio=round(compress, 2),
            coupling_out=coupling_out,
            coupling_in=coupling_in,
            omega_local=omega,
            risk_band=_risk_band(omega),
            import_count=coupling_out,
        )
