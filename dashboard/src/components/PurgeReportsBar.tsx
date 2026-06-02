import { useState } from "react";
import { Loader2, Trash2 } from "lucide-react";
import { deleteRun, purgeAllRuns, purgeRepoRuns } from "../api/client";
import type { RepoSummary } from "../types";

function isInProgressError(e: unknown): boolean {
  const msg = e instanceof Error ? e.message : String(e);
  return msg.includes("in progress") || msg.includes("include_in_progress");
}

function confirmIncludeStuck(): boolean {
  return confirm(
    "Some runs are still marked as running or pending (often stuck).\n\n" +
      "Delete those too? Click OK to force-remove them."
  );
}

export function PurgeAllButton({ onDone }: { onDone: () => void }) {
  const [busy, setBusy] = useState(false);

  const handle = async () => {
    if (
      !confirm(
        "Permanently delete ALL stored analysis runs and reports on this machine?\n\n" +
          "This cannot be undone."
      )
    ) {
      return;
    }
    const force = confirmIncludeStuck();

    setBusy(true);
    try {
      let res = await purgeAllRuns(force);
      if (!force && res.skipped?.length) {
        if (confirmIncludeStuck()) {
          res = await purgeAllRuns(true);
        }
      }
      alert(res.message);
      onDone();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Purge failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <button
      type="button"
      className="btn-ghost text-sm text-red-400/90 hover:text-red-400"
      disabled={busy}
      onClick={handle}
    >
      {busy ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : (
        <Trash2 className="h-4 w-4" />
      )}
      Purge all reports
    </button>
  );
}

export function PurgeRepoButton({
  repo,
  onDone,
}: {
  repo: RepoSummary;
  onDone: () => void;
}) {
  const [busy, setBusy] = useState(false);

  const handle = async () => {
    if (
      !confirm(
        `Permanently delete all ${repo.run_count} analysis run(s) for "${repo.repo_display}"?\n\n` +
          "Reports and clones for this repo will be removed. This cannot be undone."
      )
    ) {
      return;
    }

    const force = confirmIncludeStuck();

    setBusy(true);
    try {
      let res = await purgeRepoRuns(repo.repo_key, force);
      if (!force && res.skipped?.length) {
        if (confirmIncludeStuck()) {
          res = await purgeRepoRuns(repo.repo_key, true);
        }
      }
      alert(res.message);
      onDone();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Purge failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <button
      type="button"
      className="btn-ghost px-2 py-1 text-xs text-red-400/80 hover:text-red-400"
      disabled={busy}
      onClick={handle}
      title={`Purge all runs for ${repo.repo_display}`}
    >
      {busy ? (
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
      ) : (
        <Trash2 className="h-3.5 w-3.5" />
      )}
      Purge repo history
    </button>
  );
}

export function PurgeRunButton({
  runId,
  label,
  onDone,
  className = "btn-ghost text-sm text-red-400/90",
}: {
  runId: string;
  label?: string;
  onDone?: () => void;
  className?: string;
}) {
  const [busy, setBusy] = useState(false);

  const handle = async () => {
    if (
      !confirm(
        "Permanently delete this analysis run and all its report files?\n\n" +
          "This cannot be undone."
      )
    ) {
      return;
    }
    setBusy(true);
    try {
      try {
        const res = await deleteRun(runId);
        if (res.message) alert(res.message);
      } catch (e) {
        if (isInProgressError(e) && confirmIncludeStuck()) {
          const res = await deleteRun(runId, true);
          if (res.message) alert(res.message);
        } else {
          throw e;
        }
      }
      onDone?.();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Purge failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <button
      type="button"
      className={className}
      disabled={busy}
      onClick={handle}
    >
      {busy ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : (
        <Trash2 className="h-4 w-4 shrink-0" />
      )}
      {label ? <span>{label}</span> : null}
    </button>
  );
}
