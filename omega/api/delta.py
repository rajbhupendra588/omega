"""API helpers for run-to-run deltas."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from omega.api.store import RunRecord, RunStore
from omega.run_delta import compare_reports


def find_baseline_run(
    store: RunStore,
    current: RunRecord,
    *,
    baseline_run_id: str | None = None,
) -> RunRecord | None:
    if baseline_run_id:
        base = store.get(baseline_run_id)
        if base and base.repo_key == current.repo_key and base.status == "completed":
            return base
        return None

    _, runs = store.history_for_run(current.id)
    for r in runs:
        if r.id == current.id:
            continue
        if r.status == "completed" and r.omega_index is not None:
            return r
    return None


def load_report_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_run_delta(
    store: RunStore,
    run_id: str,
    *,
    baseline_run_id: str | None = None,
) -> dict[str, Any] | None:
    current_record = store.get(run_id)
    if not current_record or current_record.status != "completed":
        return None

    baseline_record = find_baseline_run(
        store, current_record, baseline_run_id=baseline_run_id
    )
    if not baseline_record:
        return None

    cur_path = store.report_json_path(run_id)
    base_path = store.report_json_path(baseline_record.id)
    if not cur_path or not base_path:
        return None

    current = load_report_json(cur_path)
    baseline = load_report_json(base_path)
    return compare_reports(
        current,
        baseline,
        current_run_id=run_id,
        baseline_run_id=baseline_record.id,
        baseline_created_at=baseline_record.created_at,
    )
