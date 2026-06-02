"""Register and resolve language worker agents by tech stack."""

from __future__ import annotations

from omega.agents.base import LanguageWorkerAgent
from omega.agents.strategies import (
    STRATEGY_AST_FULL,
    STRATEGY_FILE_METRICS,
    STRATEGY_HEURISTIC_SYMBOLS,
)
from omega.ast_tree_sitter import AST_LANGUAGES
from omega.entities import HEURISTIC_ENTITY_LANGUAGES


def strategy_for_language(language: str) -> str:
    if language == "python" or language in AST_LANGUAGES:
        return STRATEGY_AST_FULL
    if language in HEURISTIC_ENTITY_LANGUAGES:
        return STRATEGY_HEURISTIC_SYMBOLS
    return STRATEGY_FILE_METRICS


def capabilities_for_strategy(strategy: str) -> tuple[str, ...]:
    if strategy == STRATEGY_AST_FULL:
        return (
            "file_metrics",
            "ast_entities",
            "implementation_plans",
            "business_recommendations",
        )
    if strategy == STRATEGY_HEURISTIC_SYMBOLS:
        return (
            "file_metrics",
            "heuristic_entities",
            "implementation_sketches",
            "business_recommendations",
        )
    return ("file_metrics", "business_recommendations")


def worker_id_for(language: str, strategy: str) -> str:
    return f"{language}-{strategy}"


def create_worker(language: str) -> LanguageWorkerAgent:
    """Instantiate the worker agent appropriate for this language (lazy import)."""
    strategy = strategy_for_language(language)
    if strategy == STRATEGY_AST_FULL:
        if language == "python":
            from omega.agents.workers.python_worker import PythonWorkerAgent

            return PythonWorkerAgent()
        from omega.agents.workers.ast_ts_worker import TreeSitterAstWorker

        return TreeSitterAstWorker(language)
    if strategy == STRATEGY_HEURISTIC_SYMBOLS:
        from omega.agents.workers.heuristic_worker import HeuristicLanguageWorker

        return HeuristicLanguageWorker(language)
    from omega.agents.workers.file_metrics_worker import FileMetricsWorker

    return FileMetricsWorker(language)


def workers_for_tech_stack(languages: list[str]) -> list[LanguageWorkerAgent]:
    seen: set[str] = set()
    workers: list[LanguageWorkerAgent] = []
    for lang in languages:
        if lang in seen:
            continue
        seen.add(lang)
        workers.append(create_worker(lang))
    return workers
