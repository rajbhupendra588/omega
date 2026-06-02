"""Persist analysis runs and report metadata."""

from __future__ import annotations

import dataclasses
import json
import shutil
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from omega.api.repos import repo_key_for_run

_DEFAULT_DATA = Path.cwd() / "omega-data"


def data_root() -> Path:
    env = Path.home() / ".omega" / "data"
    if env.exists() or not (_DEFAULT_DATA.exists()):
        root = env
    else:
        root = _DEFAULT_DATA
    root.mkdir(parents=True, exist_ok=True)
    return root


@dataclass
class RunRecord:
    id: str
    target: str
    repo_display: str
    github_url: str | None
    status: str  # pending | running | completed | failed
    created_at: str
    repo_key: str = ""
    run_number: int = 0
    rerun_of: str | None = None
    completed_at: str | None = None
    error: str | None = None
    omega_index: float | None = None
    quality_grade: str | None = None
    file_count: int | None = None
    total_loc: int | None = None
    output_dir: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_RUN_RECORD_FIELDS = {f.name for f in dataclasses.fields(RunRecord)}


def _record_from_dict(data: dict[str, Any]) -> RunRecord:
    """Load meta.json; ignore unknown keys and apply defaults for missing fields."""
    kwargs: dict[str, Any] = {
        k: v for k, v in data.items() if k in _RUN_RECORD_FIELDS
    }
    for f in dataclasses.fields(RunRecord):
        if f.name in kwargs:
            continue
        if f.default is not dataclasses.MISSING:
            kwargs[f.name] = f.default
        elif f.default_factory is not dataclasses.MISSING:
            kwargs[f.name] = f.default_factory()
    return RunRecord(**kwargs)


@dataclass
class RepoSummary:
    repo_key: str
    repo_display: str
    target: str
    github_url: str | None
    run_count: int
    latest_run_id: str
    latest_status: str
    latest_created_at: str
    latest_omega_index: float | None
    latest_quality_grade: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RunStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or data_root()
        self.runs_dir = self.root / "runs"
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self.root / "index.json"
        self._repos_index_path = self.root / "repos-index.json"
        self._load_index()
        self._load_repos_index()
        self._migrate_and_sync_repos_index()

    def _load_index(self) -> None:
        if self._index_path.exists():
            self._index: list[str] = json.loads(self._index_path.read_text(encoding="utf-8"))
        else:
            self._index = []

    def _save_index(self) -> None:
        self._index_path.write_text(json.dumps(self._index, indent=2), encoding="utf-8")

    def _load_repos_index(self) -> None:
        if self._repos_index_path.exists():
            raw = json.loads(self._repos_index_path.read_text(encoding="utf-8"))
            self._repos_index: dict[str, list[str]] = {
                k: list(v) for k, v in raw.items() if isinstance(v, list)
            }
        else:
            self._repos_index = {}

    def _save_repos_index(self) -> None:
        self._repos_index_path.write_text(
            json.dumps(self._repos_index, indent=2), encoding="utf-8"
        )

    def _meta_path(self, run_id: str) -> Path:
        return self.runs_dir / run_id / "meta.json"

    def _ensure_repo_key(self, record: RunRecord) -> str:
        key = repo_key_for_run(
            record.target,
            record.github_url,
            record.repo_display,
            record.repo_key,
        )
        changed = key != record.repo_key or record.run_number < 1
        if changed:
            record.repo_key = key
            if record.run_number < 1:
                record.run_number = len(self._repos_index.get(key, [])) or 1
            self._write(record)
        return key

    def _migrate_and_sync_repos_index(self) -> None:
        rebuilt: dict[str, list[str]] = {}
        for run_id in self._index:
            r = self._read_raw(run_id)
            if not r:
                continue
            key = self._ensure_repo_key(r)
            if run_id not in rebuilt.get(key, []):
                rebuilt.setdefault(key, []).append(run_id)

        for key, ids in rebuilt.items():
            n = len(ids)
            for i, run_id in enumerate(ids):
                r = self.get(run_id)
                if not r:
                    continue
                num = n - i
                if r.run_number != num:
                    r.run_number = num
                    self._write(r)

        if rebuilt != self._repos_index:
            self._repos_index = rebuilt
            self._save_repos_index()

    def _read_raw(self, run_id: str) -> RunRecord | None:
        p = self._meta_path(run_id)
        if not p.exists():
            return None
        data = json.loads(p.read_text(encoding="utf-8"))
        return _record_from_dict(data)

    def create(
        self,
        target: str,
        repo_display: str,
        github_url: str | None,
        *,
        rerun_of: str | None = None,
    ) -> RunRecord:
        run_id = uuid.uuid4().hex[:12]
        run_dir = self.runs_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        repo_key = repo_key_for_run(target, github_url, repo_display)
        prior = self._repos_index.get(repo_key, [])
        run_number = len(prior) + 1
        record = RunRecord(
            id=run_id,
            target=target,
            repo_display=repo_display,
            github_url=github_url,
            status="pending",
            created_at=datetime.now(timezone.utc).isoformat(),
            output_dir=str(run_dir / "output"),
            repo_key=repo_key,
            run_number=run_number,
            rerun_of=rerun_of,
        )
        self._write(record)
        self._index.insert(0, run_id)
        self._save_index()
        self._repos_index.setdefault(repo_key, []).insert(0, run_id)
        self._save_repos_index()
        return record

    def _write(self, record: RunRecord) -> None:
        self._meta_path(record.id).write_text(
            json.dumps(record.to_dict(), indent=2), encoding="utf-8"
        )

    def get(self, run_id: str) -> RunRecord | None:
        r = self._read_raw(run_id)
        if not r:
            return None
        self._ensure_repo_key(r)
        return r

    def update(self, record: RunRecord) -> None:
        self._write(record)

    def runs_for_bulk_rerun(
        self,
        *,
        run_ids: list[str] | None = None,
        repo_keys: list[str] | None = None,
        recent_limit: int = 20,
    ) -> list[RunRecord]:
        """One source run per repository (for bulk re-analysis)."""
        out: list[RunRecord] = []
        seen: set[str] = set()

        if run_ids:
            for rid in run_ids:
                r = self.get(rid)
                if r and r.repo_key not in seen:
                    seen.add(r.repo_key)
                    out.append(r)
            return out

        if repo_keys:
            for key in repo_keys:
                ids = self._repos_index.get(key, [])
                if not ids:
                    continue
                r = self.get(ids[0])
                if r and r.repo_key not in seen:
                    seen.add(r.repo_key)
                    out.append(r)
            return out

        for run_id in self._index:
            r = self.get(run_id)
            if not r or r.repo_key in seen:
                continue
            seen.add(r.repo_key)
            out.append(r)
            if len(out) >= recent_limit:
                break
        return out

    def list_runs(self, limit: int = 50) -> list[RunRecord]:
        out: list[RunRecord] = []
        for run_id in self._index[:limit]:
            r = self.get(run_id)
            if r:
                out.append(r)
        return out

    def list_runs_for_repo(self, repo_key: str, limit: int = 50) -> list[RunRecord]:
        ids = self._repos_index.get(repo_key, [])
        out: list[RunRecord] = []
        for run_id in ids[:limit]:
            r = self.get(run_id)
            if r:
                out.append(r)
        return out

    def history_for_run(self, run_id: str, limit: int = 50) -> tuple[RunRecord | None, list[RunRecord]]:
        current = self.get(run_id)
        if not current:
            return None, []
        runs = self.list_runs_for_repo(current.repo_key, limit=limit)
        return current, runs

    def list_repo_summaries(self, limit_repos: int = 100) -> list[RepoSummary]:
        summaries: list[RepoSummary] = []
        for repo_key, run_ids in self._repos_index.items():
            if not run_ids:
                continue
            latest = self.get(run_ids[0])
            if not latest:
                continue
            summaries.append(
                RepoSummary(
                    repo_key=repo_key,
                    repo_display=latest.repo_display,
                    target=latest.target,
                    github_url=latest.github_url,
                    run_count=len(run_ids),
                    latest_run_id=latest.id,
                    latest_status=latest.status,
                    latest_created_at=latest.created_at,
                    latest_omega_index=latest.omega_index,
                    latest_quality_grade=latest.quality_grade,
                )
            )
        summaries.sort(key=lambda s: s.latest_created_at, reverse=True)
        return summaries[:limit_repos]

    def report_json_path(self, run_id: str) -> Path | None:
        r = self.get(run_id)
        if not r or not r.output_dir:
            return None
        p = Path(r.output_dir) / "omega-report.json"
        return p if p.exists() else None

    def delete(self, run_id: str) -> bool:
        r = self.get(run_id)
        if not r:
            return False
        self._remove_run_record(run_id, r.repo_key)
        return True

    def _remove_run_record(self, run_id: str, repo_key: str) -> None:
        run_dir = self.runs_dir / run_id
        if run_dir.exists():
            shutil.rmtree(run_dir)
        if run_id in self._index:
            self._index.remove(run_id)
            self._save_index()
        if repo_key in self._repos_index and run_id in self._repos_index[repo_key]:
            self._repos_index[repo_key].remove(run_id)
            if not self._repos_index[repo_key]:
                del self._repos_index[repo_key]
            else:
                ids = self._repos_index[repo_key]
                n = len(ids)
                for i, rid in enumerate(ids):
                    rec = self.get(rid)
                    if rec and rec.run_number != n - i:
                        rec.run_number = n - i
                        self._write(rec)
            self._save_repos_index()

    def delete_runs_for_repo(
        self, repo_key: str, *, include_in_progress: bool = False
    ) -> tuple[list[str], list[str]]:
        """Returns (deleted_run_ids, skipped_run_ids)."""
        ids = list(self._repos_index.get(repo_key, []))
        deleted: list[str] = []
        skipped: list[str] = []
        for run_id in ids:
            r = self.get(run_id)
            if not r:
                continue
            if not include_in_progress and r.status in ("pending", "running"):
                skipped.append(run_id)
                continue
            self._remove_run_record(run_id, repo_key)
            deleted.append(run_id)
        return deleted, skipped

    def delete_all_runs(self, *, include_in_progress: bool = False) -> tuple[list[str], list[str]]:
        """Purge every stored run. Returns (deleted_run_ids, skipped_run_ids)."""
        deleted: list[str] = []
        skipped: list[str] = []
        for run_id in list(self._index):
            r = self.get(run_id)
            if not r:
                continue
            if not include_in_progress and r.status in ("pending", "running"):
                skipped.append(run_id)
                continue
            self._remove_run_record(run_id, r.repo_key)
            deleted.append(run_id)
        return deleted, skipped
