import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getRunHistory } from "../api/client";
import type { RunHistoryResponse } from "../types";
import GradeBadge from "./GradeBadge";
import RerunButton from "./RerunButton";
import { History, Loader2 } from "lucide-react";

export default function RepoRunHistory({
  runId,
  currentOmega,
  onRerunQueued,
}: {
  runId: string;
  currentOmega?: number;
  onRerunQueued?: () => void;
}) {
  const [history, setHistory] = useState<RunHistoryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(true);

  const reload = () => {
    getRunHistory(runId).then(setHistory).catch(() => setHistory(null));
  };

  useEffect(() => {
    let cancelled = false;
    getRunHistory(runId)
      .then((h) => {
        if (!cancelled) setHistory(h);
      })
      .catch(() => {
        if (!cancelled) setHistory(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [runId]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-omega-muted">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading history…
      </div>
    );
  }

  if (!history) return null;

  const runs = history.runs;
  const prior = runs.find((r) => r.id !== runId && r.status === "completed");
  const delta =
    prior?.omega_index != null && currentOmega != null
      ? currentOmega - prior.omega_index
      : null;

  return (
    <div className="glass-card overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-omega-border px-5 py-4">
        <button
          type="button"
          className="flex flex-1 items-center gap-2 text-left hover:opacity-90"
          onClick={() => setExpanded((e) => !e)}
        >
          <History className="h-5 w-5 text-cyan-400" />
          <span className="font-display font-semibold text-white">
            Repository history
          </span>
          <span className="rounded-full bg-cyan-500/15 px-2 py-0.5 text-xs text-cyan-300">
            {history.run_count} run{history.run_count === 1 ? "" : "s"}
          </span>
          {delta != null && (
            <span
              className={`text-xs font-mono ${
                delta <= 0 ? "text-emerald-400" : "text-amber-400"
              }`}
            >
              Ω {delta > 0 ? "+" : ""}
              {delta.toFixed(2)} vs previous
            </span>
          )}
        </button>
        <RerunButton
          runId={runId}
          label="Re-run this repo"
          className="btn-ghost py-2 text-sm"
        />
      </div>
      {history.run_count <= 1 && (
        <p className="px-5 py-3 text-xs text-omega-muted">
          First analysis for this repository (run #
          {history.runs[0]?.run_number ?? 1}). Use Re-run to start run #2.
        </p>
      )}
      {expanded && history.run_count > 0 && (
        <ul className="divide-y divide-omega-border">
          {runs.map((r) => {
            const isCurrent = r.id === runId;
            const canRerun =
              r.status === "completed" || r.status === "failed";
            return (
              <li
                key={r.id}
                className={`flex flex-wrap items-center gap-3 px-5 py-3 text-sm ${
                  isCurrent ? "bg-cyan-500/10" : ""
                }`}
              >
                <span className="font-mono text-xs text-omega-muted">
                  Run #{r.run_number}
                </span>
                <span className="text-xs text-omega-muted">
                  {new Date(r.created_at).toLocaleString()}
                </span>
                {r.status === "completed" && r.quality_grade && (
                  <GradeBadge grade={r.quality_grade} />
                )}
                {r.omega_index != null && (
                  <span className="font-mono text-cyan-400">Ω {r.omega_index}</span>
                )}
                <span
                  className={`rounded px-1.5 py-0.5 text-xs capitalize ${
                    r.status === "completed"
                      ? "bg-emerald-500/15 text-emerald-300"
                      : r.status === "failed"
                        ? "bg-red-500/15 text-red-300"
                        : "bg-slate-500/20 text-slate-400"
                  }`}
                >
                  {r.status}
                </span>
                {isCurrent ? (
                  <span className="text-xs font-medium text-cyan-300">Viewing</span>
                ) : r.status === "completed" ? (
                  <Link
                    to={`/reports/${r.id}`}
                    className="text-xs text-cyan-400 hover:underline"
                  >
                    View report
                  </Link>
                ) : null}
                {canRerun && (
                  <RerunButton
                    runId={r.id}
                    label="Re-run"
                    className="btn-ghost ml-auto px-2 py-1 text-xs"
                    navigateOnComplete={!isCurrent}
                    onQueued={() => {
                      reload();
                      onRerunQueued?.();
                    }}
                  />
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
