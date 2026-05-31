import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2, RefreshCw } from "lucide-react";
import { rerunAnalysis, waitForRunCompletion } from "../api/client";

export default function RerunButton({
  runId,
  label = "Re-run",
  className = "btn-ghost text-sm",
  waitForCompletion = true,
  navigateOnComplete = true,
  onQueued,
  onComplete,
}: {
  runId: string;
  label?: string;
  className?: string;
  /** Wait for scan to finish before calling onComplete / navigating */
  waitForCompletion?: boolean;
  navigateOnComplete?: boolean;
  onQueued?: (newRunId: string) => void;
  onComplete?: (newRunId: string) => void;
}) {
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState("");

  const handleRerun = async () => {
    setBusy(true);
    setProgress("Starting…");
    try {
      const { run_id } = await rerunAnalysis(runId);
      onQueued?.(run_id);
      if (!waitForCompletion) {
        onComplete?.(run_id);
        return;
      }
      setProgress("Scanning repository…");
      await waitForRunCompletion(run_id, (msg) => setProgress(msg));
      onComplete?.(run_id);
      if (navigateOnComplete) {
        navigate(`/reports/${run_id}`);
      }
    } catch (e) {
      alert(e instanceof Error ? e.message : "Re-run failed");
    } finally {
      setBusy(false);
      setProgress("");
    }
  };

  return (
    <button
      type="button"
      className={className}
      onClick={handleRerun}
      disabled={busy}
      title="Run a fresh Ω analysis on the same repository"
    >
      {busy ? (
        <>
          <Loader2 className="h-4 w-4 animate-spin" />
          <span className="max-w-[8rem] truncate">
            {progress || "Re-running…"}
          </span>
        </>
      ) : (
        <>
          <RefreshCw className="h-4 w-4 shrink-0" />
          {label}
        </>
      )}
    </button>
  );
}
