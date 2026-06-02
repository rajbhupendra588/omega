"""FastAPI server for Omega dashboard."""

from __future__ import annotations

import json
import threading
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from omega.api.repos import decode_repo_key
from omega.api.store import RunStore
from omega.api.targets import can_rerun_target, target_metadata
from omega.dimensions import ensure_report_has_dimensions
from omega.metrics_suite import ensure_report_has_metric_suite
from omega.developer_guide import ensure_report_has_developer_guide
from omega.api.delta import build_run_delta
from omega.api.worker import execute_analysis
from omega.report import refresh_stored_html_report

app = FastAPI(
    title="Omega QFM API",
    description="Code quality analysis — dashboard backend",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = RunStore()


class AnalyzeRequest(BaseModel):
    target: str = Field(..., description="GitHub URL, owner/repo, or local path")


class AnalyzeResponse(BaseModel):
    run_id: str
    status: str
    message: str
    rerun_of: str | None = None


class BulkRerunRequest(BaseModel):
    """Re-queue analysis for one or many repositories."""
    run_ids: list[str] | None = Field(
        None,
        description="Specific run IDs; deduped to one rerun per repo",
    )
    repo_keys: list[str] | None = Field(
        None,
        description="Repo keys; uses latest run for each",
    )
    recent_limit: int = Field(
        20,
        ge=1,
        le=50,
        description="When run_ids/repo_keys empty: unique repos from recent runs",
    )


class BulkRerunItem(BaseModel):
    run_id: str
    repo_display: str
    repo_key: str
    rerun_of: str


class BulkRerunSkipped(BaseModel):
    repo_display: str
    repo_key: str
    reason: str


class BulkRerunResponse(BaseModel):
    queued: list[BulkRerunItem]
    skipped: list[BulkRerunSkipped]
    message: str


def _dashboard_dist() -> Path | None:
    candidates = [
        Path(__file__).resolve().parents[2] / "dashboard" / "dist",
        Path.cwd() / "dashboard" / "dist",
    ]
    for p in candidates:
        if (p / "index.html").exists():
            return p
    return None


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "omega-qfm"}


def _queue_analysis(
    *,
    target: str,
    display: str,
    github_url: str | None,
    background_tasks: BackgroundTasks,
    rerun_of: str | None = None,
) -> AnalyzeResponse:
    record = store.create(target, display, github_url, rerun_of=rerun_of)
    background_tasks.add_task(execute_analysis, store, record.id)
    msg = f"Analysis queued for {display}"
    if rerun_of:
        msg = f"Re-analysis queued for {display}"
    return AnalyzeResponse(
        run_id=record.id,
        status="pending",
        message=msg,
        rerun_of=rerun_of,
    )


@app.post("/api/analyze", response_model=AnalyzeResponse)
def start_analysis(req: AnalyzeRequest, background_tasks: BackgroundTasks):
    try:
        target, display, github_url = target_metadata(req.target)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e

    return _queue_analysis(
        target=target,
        display=display,
        github_url=github_url,
        background_tasks=background_tasks,
    )


@app.post("/api/runs/{run_id}/rerun", response_model=AnalyzeResponse)
def rerun_analysis(run_id: str, background_tasks: BackgroundTasks):
    prior = store.get(run_id)
    if not prior:
        raise HTTPException(404, "Run not found")

    err = can_rerun_target(prior.target)
    if err:
        raise HTTPException(400, err)

    return _queue_analysis(
        target=prior.target,
        display=prior.repo_display,
        github_url=prior.github_url,
        background_tasks=background_tasks,
        rerun_of=run_id,
    )


@app.post("/api/reruns/bulk", response_model=BulkRerunResponse)
def bulk_rerun(req: BulkRerunRequest, background_tasks: BackgroundTasks):
    sources = store.runs_for_bulk_rerun(
        run_ids=req.run_ids,
        repo_keys=req.repo_keys,
        recent_limit=req.recent_limit,
    )
    if not sources:
        raise HTTPException(404, "No runs matched for bulk re-analysis")

    queued: list[BulkRerunItem] = []
    skipped: list[BulkRerunSkipped] = []

    for prior in sources:
        err = can_rerun_target(prior.target)
        if err:
            skipped.append(
                BulkRerunSkipped(
                    repo_display=prior.repo_display,
                    repo_key=prior.repo_key,
                    reason=err,
                )
            )
            continue
        record = store.create(
            prior.target,
            prior.repo_display,
            prior.github_url,
            rerun_of=prior.id,
        )
        background_tasks.add_task(execute_analysis, store, record.id)
        queued.append(
            BulkRerunItem(
                run_id=record.id,
                repo_display=prior.repo_display,
                repo_key=prior.repo_key,
                rerun_of=prior.id,
            )
        )

    if not queued:
        raise HTTPException(
            400,
            "No repositories could be re-queued. See skipped for reasons.",
        )

    return BulkRerunResponse(
        queued=queued,
        skipped=skipped,
        message=f"Queued {len(queued)} re-analysis job(s)",
    )


@app.get("/api/runs")
def list_runs(limit: int = 50):
    runs = store.list_runs(limit=limit)
    return {"runs": [r.to_dict() for r in runs]}


@app.get("/api/repos")
def list_repos(limit: int = 100):
    repos = store.list_repo_summaries(limit_repos=limit)
    return {"repos": [r.to_dict() for r in repos]}


@app.get("/api/repos/{repo_key_enc}/runs")
def list_repo_runs(repo_key_enc: str, limit: int = 50):
    repo_key = decode_repo_key(repo_key_enc)
    runs = store.list_runs_for_repo(repo_key, limit=limit)
    if not runs:
        raise HTTPException(404, "No runs for this repository")
    return {
        "repo_key": repo_key,
        "repo_display": runs[0].repo_display,
        "runs": [r.to_dict() for r in runs],
    }


@app.get("/api/runs/{run_id}/history")
def run_history(run_id: str, limit: int = 50):
    current, runs = store.history_for_run(run_id, limit=limit)
    if not current:
        raise HTTPException(404, "Run not found")
    return {
        "repo_key": current.repo_key,
        "repo_display": current.repo_display,
        "target": current.target,
        "github_url": current.github_url,
        "current_run_id": run_id,
        "run_count": len(runs),
        "runs": [r.to_dict() for r in runs],
    }


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    record = store.get(run_id)
    if not record:
        raise HTTPException(404, "Run not found")
    return record.to_dict()


@app.get("/api/runs/{run_id}/delta")
def get_run_delta(run_id: str, baseline_run_id: str | None = None):
    """Compare this run to a prior completed run (default: previous run for same repo)."""
    record = store.get(run_id)
    if not record:
        raise HTTPException(404, "Run not found")
    if record.status != "completed":
        raise HTTPException(409, f"Run status is {record.status}")
    delta = build_run_delta(store, run_id, baseline_run_id=baseline_run_id)
    if delta is None:
        return {
            "has_baseline": False,
            "message": "No prior completed run for this repository to compare against.",
        }
    return {"has_baseline": True, "delta": delta}


def _persist_report_json(path: Path, report: dict) -> None:
    path.write_text(json.dumps(report), encoding="utf-8")


@app.get("/api/runs/{run_id}/report")
def get_report(run_id: str, background_tasks: BackgroundTasks):
    record = store.get(run_id)
    if not record:
        raise HTTPException(404, "Run not found")
    if record.status != "completed":
        raise HTTPException(409, f"Run status is {record.status}")
    path = store.report_json_path(run_id)
    if not path:
        raise HTTPException(404, "Report not generated")
    report = json.loads(path.read_text(encoding="utf-8"))
    updated = False
    report, u = ensure_report_has_dimensions(report)
    updated = updated or u
    report, u = ensure_report_has_developer_guide(report)
    updated = updated or u
    report, u = ensure_report_has_metric_suite(
        report, root=record.output_dir and str(Path(record.output_dir) / "repo") or report.get("repository")
    )
    updated = updated or u
    if updated:
        snapshot = json.loads(json.dumps(report))
        background_tasks.add_task(_persist_report_json, path, snapshot)
    return report


@app.get("/api/runs/{run_id}/export/{kind}")
def export_file(run_id: str, kind: str):
    record = store.get(run_id)
    if not record or not record.output_dir:
        raise HTTPException(404, "Run not found")
    out = Path(record.output_dir)
    mapping = {
        "html": "omega-report.html",
        "json": "omega-report.json",
        "csv": "omega-files.csv",
        "entities": "omega-entities.csv",
        "implementations": "omega-implementations.md",
        "developer": "omega-report-developer.md",
        "business": "omega-report-business.md",
        "technical": "omega-report-technical.md",
    }
    if kind not in mapping:
        raise HTTPException(400, f"Unknown export kind: {kind}")
    if kind == "html":
        try:
            path = refresh_stored_html_report(out)
        except FileNotFoundError:
            raise HTTPException(404, "Report not generated") from None
    else:
        path = out / mapping[kind]
        if not path.exists():
            raise HTTPException(404, "File not found")
    media = {
        "html": "text/html",
        "json": "application/json",
        "csv": "text/csv",
        "entities": "text/csv",
        "implementations": "text/markdown",
        "developer": "text/markdown",
        "business": "text/markdown",
        "technical": "text/markdown",
    }
    return FileResponse(path, media_type=media.get(kind, "application/octet-stream"))


class PurgeResponse(BaseModel):
    deleted: list[str]
    skipped: list[str]
    message: str


@app.delete("/api/runs/{run_id}")
def delete_run(run_id: str, include_in_progress: bool = False):
    record = store.get(run_id)
    if not record:
        raise HTTPException(404, "Run not found")
    if record.status in ("pending", "running") and not include_in_progress:
        raise HTTPException(
            409,
            "Cannot purge a run that is still in progress. "
            "Retry with ?include_in_progress=true to force-delete a stuck run.",
        )
    if not store.delete(run_id):
        raise HTTPException(404, "Run not found")
    return {
        "deleted": run_id,
        "message": f"Purged analysis run {run_id} for {record.repo_display}",
    }


@app.delete("/api/runs", response_model=PurgeResponse)
def purge_all_runs(include_in_progress: bool = False):
    deleted, skipped = store.delete_all_runs(include_in_progress=include_in_progress)
    if not deleted and not skipped:
        return PurgeResponse(
            deleted=[],
            skipped=[],
            message="No analysis runs to purge",
        )
    msg = f"Purged {len(deleted)} analysis run(s)"
    if skipped:
        msg += f"; skipped {len(skipped)} in-progress run(s)"
    return PurgeResponse(deleted=deleted, skipped=skipped, message=msg)


@app.delete("/api/repos/{repo_key_enc}/runs", response_model=PurgeResponse)
def purge_repo_runs(repo_key_enc: str, include_in_progress: bool = False):
    repo_key = decode_repo_key(repo_key_enc)
    if not store.list_runs_for_repo(repo_key, limit=1):
        raise HTTPException(404, "No runs for this repository")
    deleted, skipped = store.delete_runs_for_repo(
        repo_key, include_in_progress=include_in_progress
    )
    msg = f"Purged {len(deleted)} run(s) for this repository"
    if skipped:
        msg += f"; skipped {len(skipped)} in-progress run(s)"
    return PurgeResponse(deleted=deleted, skipped=skipped, message=msg)


def _mount_frontend():
    dist = _dashboard_dist()
    if dist:
        assets = dist / "assets"
        if assets.is_dir():
            app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

        @app.get("/{full_path:path}")
        def spa_fallback(full_path: str):
            if full_path.startswith("api"):
                raise HTTPException(404)
            index = dist / "index.html"
            if index.exists():
                return FileResponse(index)
            raise HTTPException(404)


_mount_frontend()


def main():
    import os

    import uvicorn

    reload = os.environ.get("OMEGA_RELOAD", "").lower() in ("1", "true", "yes")
    root = Path(__file__).resolve().parents[2]
    kwargs: dict = {
        "app": "omega.api.server:app",
        "host": "0.0.0.0",
        "port": 8765,
        "reload": reload,
    }
    if reload:
        kwargs["reload_dirs"] = [str(root / "omega")]
    uvicorn.run(**kwargs)


if __name__ == "__main__":
    main()
