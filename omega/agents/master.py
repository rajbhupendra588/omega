"""Master agent: owns repo metadata and dispatches language worker agents."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from omega.agents.base import WorkerContext
from omega.agents.coupling import build_coupling_maps, python_coupling_maps
from omega.ast_tree_sitter import AST_LANGUAGES, ts_coupling_maps
from omega.agents.metadata import (
    LanguageStackEntry,
    MasterManifest,
    WorkerSpec,
)
from omega.agents.registry import (
    capabilities_for_strategy,
    create_worker,
    strategy_for_language,
    worker_id_for,
)
from omega.discover import RepoInventory, SourceFile, discover_source_files
from omega.scan_config import default_max_files
from omega.entities import EntityMetrics, enrich_implementation_plans
from omega.metrics import FileMetrics


def _cap_inventory(inventory: RepoInventory, max_files: int | None) -> RepoInventory:
    if max_files is None or len(inventory.files) <= max_files:
        return inventory
    capped = sorted(inventory.files, key=lambda sf: sf.size_bytes, reverse=True)[:max_files]
    by_lang: dict[str, int] = {}
    for f in capped:
        by_lang[f.language] = by_lang.get(f.language, 0) + 1
    return RepoInventory(
        root=inventory.root,
        files=capped,
        by_language=dict(sorted(by_lang.items(), key=lambda x: -x[1])),
        total_bytes=sum(f.size_bytes for f in capped),
    )


def _load_sources(files: list[SourceFile]) -> dict[Path, str]:
    sources: dict[Path, str] = {}
    for sf in files:
        try:
            sources[sf.path] = sf.path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            sources[sf.path] = ""
    return sources


def _group_by_language(files: list[SourceFile]) -> dict[str, list[SourceFile]]:
    groups: dict[str, list[SourceFile]] = {}
    for sf in files:
        groups.setdefault(sf.language, []).append(sf)
    return groups


class MasterAgent:
    """
    Central orchestrator:
    1. Discovers repository inventory and builds tech-stack metadata
    2. Spawns one worker agent per language present
    3. Merges file metrics and entities for downstream Ω aggregation
    """

    def __init__(
        self,
        root: Path,
        *,
        max_files: int | None = None,
        parallel_workers: bool = True,
    ) -> None:
        self.root = root.resolve()
        self.max_files = max_files if max_files is not None else default_max_files()
        self.parallel_workers = parallel_workers
        self.inventory = _cap_inventory(
            discover_source_files(self.root), self.max_files
        )
        self.sources = _load_sources(self.inventory.files)
        gen_out, gen_in = build_coupling_maps(self.inventory.files, self.sources)
        stem_to_path = {sf.path.stem.lower(): sf.path for sf in self.inventory.files}
        py_paths = [sf.path for sf in self.inventory.files if sf.language == "python"]
        py_out, py_in = python_coupling_maps(py_paths, self.sources)
        self.coupling_out = {**gen_out, **py_out}
        self.coupling_in = {**gen_in, **py_in}
        for lang in AST_LANGUAGES:
            lang_paths = [sf.path for sf in self.inventory.files if sf.language == lang]
            if not lang_paths:
                continue
            lo, li = ts_coupling_maps(lang, lang_paths, self.sources, stem_to_path)
            self.coupling_out.update(lo)
            self.coupling_in.update(li)
        self.manifest = self._build_manifest()

    def _build_manifest(self) -> MasterManifest:
        total = len(self.inventory.files) or 1
        stack: list[LanguageStackEntry] = []
        planned: list[WorkerSpec] = []
        plan_lines: list[str] = [
            f"Master agent discovered {len(self.inventory.files)} source files "
            f"across {len(self.inventory.by_language)} languages.",
        ]

        for lang, count in self.inventory.by_language.items():
            strategy = strategy_for_language(lang)
            caps = capabilities_for_strategy(strategy)
            wid = worker_id_for(lang, strategy)
            share = round(100.0 * count / total, 1)
            stack.append(
                LanguageStackEntry(
                    language=lang,
                    file_count=count,
                    share_pct=share,
                    worker_id=wid,
                    strategy=strategy,
                    capabilities=caps,
                )
            )
            planned.append(
                WorkerSpec(
                    worker_id=wid,
                    language=lang,
                    strategy=strategy,
                    file_count=count,
                    capabilities=list(caps),
                )
            )
            plan_lines.append(
                f"Spawn worker `{wid}` ({strategy}) for {count} {lang} file(s) "
                f"— {', '.join(caps)}."
            )

        primary = (
            max(self.inventory.by_language.items(), key=lambda x: x[1])[0]
            if self.inventory.by_language
            else "unknown"
        )
        plan_lines.append(
            f"Primary language: {primary}. Workers execute "
            + ("in parallel." if self.parallel_workers else "sequentially.")
        )

        return MasterManifest(
            root=str(self.root),
            total_files=len(self.inventory.files),
            total_bytes=self.inventory.total_bytes,
            primary_language=primary,
            tech_stack=stack,
            workers_planned=planned,
            orchestration_plan=plan_lines,
        )

    def _run_one_worker(self, language: str, batch: list[SourceFile]) -> tuple:
        worker = create_worker(language)
        ctx = WorkerContext(
            root=self.root,
            sources=self.sources,
            coupling_out=self.coupling_out,
            coupling_in=self.coupling_in,
        )
        output = worker.analyze(batch, ctx)
        return output

    def run(
        self,
    ) -> tuple[list[FileMetrics], list[EntityMetrics], RepoInventory, MasterManifest]:
        """Dispatch language workers and merge results."""
        by_lang = _group_by_language(self.inventory.files)
        if not by_lang:
            return [], [], self.inventory, self.manifest

        all_files: list[FileMetrics] = []
        all_entities: list[EntityMetrics] = []
        results = []

        languages = list(by_lang.keys())
        max_parallel = int(os.environ.get("OMEGA_MAX_WORKER_AGENTS", "8"))
        use_pool = self.parallel_workers and len(languages) > 1

        if use_pool:
            with ThreadPoolExecutor(max_workers=min(len(languages), max_parallel)) as pool:
                futures = {
                    pool.submit(self._run_one_worker, lang, by_lang[lang]): lang
                    for lang in languages
                }
                for fut in as_completed(futures):
                    output = fut.result()
                    results.append(output.result)
                    all_files.extend(output.files)
                    all_entities.extend(output.entities)
        else:
            for lang in languages:
                output = self._run_one_worker(lang, by_lang[lang])
                results.append(output.result)
                all_files.extend(output.files)
                all_entities.extend(output.entities)

        self.manifest.worker_results = results
        sources_by_rel = {
            sf.rel_path: self.sources.get(sf.path, "")
            for sf in self.inventory.files
        }
        all_entities = enrich_implementation_plans(all_entities, sources_by_rel)
        all_files.sort(key=lambda x: x.omega_local, reverse=True)
        all_entities.sort(key=lambda x: x.omega_local, reverse=True)
        return all_files, all_entities, self.inventory, self.manifest
