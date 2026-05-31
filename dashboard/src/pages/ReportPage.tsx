import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getReport, getRun } from "../api/client";
import RerunButton from "../components/RerunButton";
import type { FullReport, RunRecord } from "../types";
import ReportTabs from "../components/ReportTabs";
import RepoRunHistory from "../components/RepoRunHistory";
import { ArrowLeft, Loader2 } from "lucide-react";

export default function ReportPage() {
  const { runId } = useParams<{ runId: string }>();
  const [run, setRun] = useState<RunRecord | null>(null);
  const [report, setReport] = useState<FullReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId) return;
    let cancelled = false;

    const load = async () => {
      try {
        const r = await getRun(runId);
        if (cancelled) return;
        setRun(r);
        if (r.status !== "completed") {
          setError(
            r.status === "failed"
              ? r.error || "Analysis failed"
              : "Analysis still in progress"
          );
          setLoading(false);
          return;
        }
        const rep = await getReport(runId);
        if (!cancelled) {
          setReport(rep);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load report");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, [runId]);

  useEffect(() => {
    if (!runId || !run) return;
    if (run.status !== "pending" && run.status !== "running") return;

    const poll = setInterval(async () => {
      try {
        const r = await getRun(runId);
        setRun(r);
        if (r.status === "completed") {
          const rep = await getReport(runId);
          setReport(rep);
          setError(null);
          setLoading(false);
        } else if (r.status === "failed") {
          setError(r.error || "Analysis failed");
          setLoading(false);
        }
      } catch {
        /* keep polling */
      }
    }, 2000);

    return () => clearInterval(poll);
  }, [runId, run?.status]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-omega-muted">
        <Loader2 className="h-10 w-10 animate-spin text-cyan-400" />
        <p className="mt-4">Loading report…</p>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="space-y-4">
        <Link to="/" className="btn-ghost inline-flex">
          <ArrowLeft className="h-4 w-4" />
          Dashboard
        </Link>
        <div className="glass-card px-6 py-8 text-red-300">{error}</div>
        {run?.status === "running" || run?.status === "pending" ? (
          <p className="text-sm text-omega-muted">
            Analysis in progress — this page will refresh automatically.
          </p>
        ) : null}
        {runId && run?.status === "failed" && (
          <RerunButton runId={runId} className="btn-primary" />
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Link to="/" className="btn-ghost inline-flex">
        <ArrowLeft className="h-4 w-4" />
        Back to Dashboard
      </Link>
      <RepoRunHistory
        runId={runId!}
        currentOmega={report.omega_index}
        onRerunQueued={() => {
          getRun(runId!).then(setRun).catch(() => undefined);
        }}
      />
      <ReportTabs report={report} runId={runId!} />
    </div>
  );
}
