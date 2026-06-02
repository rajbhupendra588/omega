"""Background analysis worker."""

from __future__ import annotations

import shutil
import traceback
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from omega.analyzer import analyze_repository
from omega.api.store import RunRecord, RunStore
from omega.github import clone_github_repo, parse_github_target
from omega.report import build_report
from omega.scan_config import default_max_files


_UPLOAD_TARGET_PREFIX = "upload://"
_UPLOAD_ZIP_NAME = "source.zip"


def _safe_extract_zip(zip_path: Path, dest: Path) -> None:
    """Extract zip to destination while preventing zip-slip traversal."""
    dest.mkdir(parents=True, exist_ok=True)
    dest_real = dest.resolve()
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.infolist():
            member_path = (dest / member.filename).resolve()
            if not str(member_path).startswith(str(dest_real)):
                raise ValueError(f"Unsafe zip member path: {member.filename}")
        zf.extractall(dest)


def _resolve_target(target: str, run_dir: Path) -> tuple[Path, str | None, str]:
    if target.startswith(_UPLOAD_TARGET_PREFIX):
        zip_path = run_dir / "input" / _UPLOAD_ZIP_NAME
        if not zip_path.exists():
            raise FileNotFoundError("Uploaded zip file not found for this run")
        repo_dest = run_dir / "repo"
        if repo_dest.exists():
            shutil.rmtree(repo_dest)
        _safe_extract_zip(zip_path, repo_dest)
        display = target.removeprefix(_UPLOAD_TARGET_PREFIX) or "uploaded-project"
        return repo_dest, None, display

    parsed = parse_github_target(target)
    if parsed:
        owner, repo = parsed
        clone_dest = run_dir / "repo"
        if clone_dest.exists():
            shutil.rmtree(clone_dest)
        root = clone_github_repo(owner, repo, dest=clone_dest)
        return root, f"https://github.com/{owner}/{repo}", f"{owner}/{repo}"
    root = Path(target).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Path not found: {root}")
    return root, None, root.name


def execute_analysis(store: RunStore, run_id: str) -> None:
    record = store.get(run_id)
    if not record:
        return
    record.status = "running"
    store.update(record)
    run_dir = store.runs_dir / run_id
    try:
        root, github_url, display = _resolve_target(record.target, run_dir)
        out_dir = Path(record.output_dir or str(run_dir / "output"))
        out_dir.mkdir(parents=True, exist_ok=True)
        outcome = analyze_repository(
            root,
            github_url=github_url or record.github_url,
            repo_display=display,
            max_files=default_max_files(),
        )
        build_report(outcome, out_dir)
        record.status = "completed"
        record.completed_at = datetime.now(timezone.utc).isoformat()
        record.omega_index = outcome.omega_index
        record.quality_grade = outcome.quality_grade
        record.file_count = outcome.file_count
        record.total_loc = outcome.total_loc
        record.repo_display = outcome.repo_display
        record.error = None
    except Exception as e:
        record.status = "failed"
        record.completed_at = datetime.now(timezone.utc).isoformat()
        record.error = str(e)
        err_file = run_dir / "error.log"
        err_file.write_text(traceback.format_exc(), encoding="utf-8")
    store.update(record)
