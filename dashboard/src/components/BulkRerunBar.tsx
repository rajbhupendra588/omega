import { useState } from "react";
import { Loader2, RefreshCw } from "lucide-react";
import { bulkRerun } from "../api/client";
import type { RepoSummary } from "../types";

export default function BulkRerunBar({
  repos,
  recentLimit = 10,
  onDone,
}: {
  repos: RepoSummary[];
  recentLimit?: number;
  onDone: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const repoCount = repos.length;
  const recentN = Math.min(recentLimit, repoCount);

  const runBulk = async (mode: "recent" | "all") => {
    const label =
      mode === "all"
        ? `all ${repoCount} repositories`
        : `the ${recentN} most recent unique repositories`;
    if (!confirm(`Queue a new Ω analysis for ${label}? Jobs run in the background.`)) {
      return;
    }

    setBusy(true);
    setMessage(null);
    try {
      const res = await bulkRerun(
        mode === "all"
          ? { repoKeys: repos.map((r) => r.repo_key) }
          : { recentLimit: recentN }
      );
      const skipped =
        res.skipped.length > 0
          ? ` · ${res.skipped.length} skipped (e.g. missing local paths)`
          : "";
      setMessage(`${res.message}${skipped}`);
      onDone();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Bulk re-run failed");
    } finally {
      setBusy(false);
    }
  };

  if (repoCount === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-omega-border bg-slate-900/40 px-4 py-3">
      <RefreshCw className="h-4 w-4 shrink-0 text-cyan-400" />
      <span className="text-sm text-omega-muted">Bulk re-run:</span>
      <button
        type="button"
        className="btn-ghost text-sm"
        disabled={busy || repoCount < 1}
        onClick={() => runBulk("recent")}
      >
        {busy ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <RefreshCw className="h-4 w-4" />
        )}
        Recent ({recentN})
      </button>
      {repoCount > 1 && (
        <button
          type="button"
          className="btn-ghost text-sm"
          disabled={busy}
          onClick={() => runBulk("all")}
        >
          All repos ({repoCount})
        </button>
      )}
      {message && <span className="text-xs text-cyan-300">{message}</span>}
    </div>
  );
}
