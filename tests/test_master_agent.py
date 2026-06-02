"""Master agent orchestration tests."""

from __future__ import annotations

from pathlib import Path

from omega.agents.master import MasterAgent
from omega.agents.strategies import STRATEGY_AST_FULL, STRATEGY_HEURISTIC_SYMBOLS


def test_master_spawns_workers_per_language(tmp_path: Path):
    (tmp_path / "app.py").write_text("def a():\n    return 1\n", encoding="utf-8")
    (tmp_path / "app.js").write_text(
        "export function b(x) {\n  if (x) return x;\n  return 0;\n}\n",
        encoding="utf-8",
    )
    master = MasterAgent(tmp_path, parallel_workers=False)
    assert len(master.manifest.workers_planned) == 2
    langs = {w.language for w in master.manifest.workers_planned}
    assert langs == {"python", "javascript"}

    files, entities, inv, manifest = master.run()
    assert len(files) == 2
    assert manifest.worker_results
    assert all(r.status == "completed" for r in manifest.worker_results)
    strategies = {r.strategy for r in manifest.worker_results}
    assert STRATEGY_AST_FULL in strategies
    assert STRATEGY_HEURISTIC_SYMBOLS in strategies
    assert entities
