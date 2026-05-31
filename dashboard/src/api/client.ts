import type { FullReport, RepoSummary, RunHistoryResponse, RunRecord } from "../types";

const API = import.meta.env.DEV ? "" : "";

export async function healthCheck(): Promise<boolean> {
  try {
    const r = await fetch(`${API}/api/health`);
    return r.ok;
  } catch {
    return false;
  }
}

export type AnalyzeStartResult = {
  run_id: string;
  status: string;
  message: string;
  rerun_of?: string | null;
};

export async function startAnalysis(target: string): Promise<AnalyzeStartResult> {
  const r = await fetch(`${API}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ target }),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }));
    const d = err.detail;
    const msg = Array.isArray(d) ? d.map((x: { msg?: string }) => x.msg).join(", ") : d;
    throw new Error(msg || "Analysis failed to start");
  }
  return r.json();
}

export async function listRuns(limit = 50): Promise<RunRecord[]> {
  const r = await fetch(`${API}/api/runs?limit=${limit}`);
  if (!r.ok) throw new Error("Failed to load runs");
  const data = await r.json();
  return data.runs;
}

export async function listRepos(limit = 100): Promise<RepoSummary[]> {
  const r = await fetch(`${API}/api/repos?limit=${limit}`);
  if (!r.ok) throw new Error("Failed to load repositories");
  const data = await r.json();
  return data.repos;
}

export async function getRunHistory(runId: string): Promise<RunHistoryResponse> {
  const r = await fetch(`${API}/api/runs/${runId}/history`);
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to load run history");
  }
  return r.json();
}

export function encodeRepoKey(repoKey: string): string {
  return encodeURIComponent(repoKey);
}

export async function getRun(id: string): Promise<RunRecord> {
  const r = await fetch(`${API}/api/runs/${id}`);
  if (!r.ok) throw new Error("Run not found");
  return r.json();
}

export async function getReport(id: string): Promise<FullReport> {
  const r = await fetch(`${API}/api/runs/${id}/report`);
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail || "Report not ready");
  }
  return r.json();
}

export async function deleteRun(id: string): Promise<void> {
  const r = await fetch(`${API}/api/runs/${id}`, { method: "DELETE" });
  if (!r.ok) throw new Error("Delete failed");
}

export function exportUrl(runId: string, kind: string): string {
  return `${API}/api/runs/${runId}/export/${kind}`;
}

export interface BulkRerunResult {
  queued: {
    run_id: string;
    repo_display: string;
    repo_key: string;
    rerun_of: string;
  }[];
  skipped: { repo_display: string; repo_key: string; reason: string }[];
  message: string;
}

export async function bulkRerun(options: {
  runIds?: string[];
  repoKeys?: string[];
  recentLimit?: number;
}): Promise<BulkRerunResult> {
  const r = await fetch(`${API}/api/reruns/bulk`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      run_ids: options.runIds,
      repo_keys: options.repoKeys,
      recent_limit: options.recentLimit ?? 20,
    }),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }));
    const d = err.detail;
    const msg = Array.isArray(d) ? d.map((x: { msg?: string }) => x.msg).join(", ") : d;
    throw new Error(msg || "Bulk re-run failed");
  }
  return r.json();
}

export async function rerunAnalysis(runId: string): Promise<AnalyzeStartResult> {
  const r = await fetch(`${API}/api/runs/${runId}/rerun`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }));
    const d = err.detail;
    const msg = Array.isArray(d) ? d.map((x: { msg?: string }) => x.msg).join(", ") : d;
    throw new Error(msg || "Re-run failed to start");
  }
  return r.json();
}

const POLL_MS = 1500;
const POLL_MAX = 600;

export async function waitForRunCompletion(
  runId: string,
  onProgress?: (status: string) => void
): Promise<RunRecord> {
  for (let i = 0; i < POLL_MAX; i++) {
    await new Promise((resolve) => setTimeout(resolve, POLL_MS));
    const run = await getRun(runId);
    if (run.status === "completed") return run;
    if (run.status === "failed") {
      throw new Error(run.error || "Analysis failed");
    }
    onProgress?.(
      run.status === "running"
        ? "Computing Ω quality field…"
        : "Queued…"
    );
  }
  throw new Error("Analysis timed out — check Dashboard for status");
}
