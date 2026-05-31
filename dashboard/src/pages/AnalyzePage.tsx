import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { startAnalysis, waitForRunCompletion } from "../api/client";
import {
  Github,
  Loader2,
  Sparkles,
  FolderOpen,
  Zap,
} from "lucide-react";

const EXAMPLES = [
  "psf/requests",
  "pallets/flask",
  "django/django",
  "fastapi/fastapi",
];

export default function AnalyzePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [target, setTarget] = useState("");
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const prefill = searchParams.get("target");
    if (prefill) setTarget(prefill);
  }, [searchParams]);

  const run = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    setProgress("Starting analysis…");
    try {
      const { run_id } = await startAnalysis(target.trim());
      setProgress("Cloning & scanning repository…");
      await waitForRunCompletion(run_id, (msg) => setProgress(msg));
      navigate(`/reports/${run_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <div>
        <h1 className="font-display text-3xl font-bold text-white">
          New Code Quality Analysis
        </h1>
        <p className="mt-2 text-omega-muted">
          Enter a public GitHub repository or a local folder path on this machine.
        </p>
      </div>

      <form onSubmit={run} className="glass-card space-y-6 p-8">
        <div>
          <label className="mb-2 flex items-center gap-2 text-sm font-medium text-white">
            <Github className="h-4 w-4 text-cyan-400" />
            Repository target
          </label>
          <input
            className="input-field"
            placeholder="https://github.com/owner/repo  or  owner/repo  or  /path/to/project"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            required
            disabled={busy}
          />
          <div className="mt-3 flex flex-wrap gap-2">
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                type="button"
                className="rounded-lg border border-omega-border px-3 py-1 text-xs text-omega-muted transition hover:border-blue-500/50 hover:text-white"
                onClick={() => setTarget(ex)}
                disabled={busy}
              >
                {ex}
              </button>
            ))}
          </div>
        </div>

        {error && (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        )}

        {busy && (
          <div className="flex items-center gap-3 rounded-xl bg-blue-500/10 px-4 py-3 text-sm text-cyan-200">
            <Loader2 className="h-5 w-5 shrink-0 animate-spin" />
            {progress}
          </div>
        )}

        <button type="submit" className="btn-primary w-full py-3" disabled={busy}>
          {busy ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              Analyzing…
            </>
          ) : (
            <>
              <Sparkles className="h-5 w-5" />
              Run Ω-QFM Analysis
            </>
          )}
        </button>
      </form>

      <div className="grid gap-4 sm:grid-cols-2">
        <Tip
          icon={Github}
          title="GitHub"
          text="Public repos are cloned automatically. Use owner/repo or full URL."
        />
        <Tip
          icon={FolderOpen}
          title="Local path"
          text="Server must have filesystem access, e.g. /Users/you/projects/app"
        />
        <Tip
          icon={Zap}
          title="Dual reports"
          text="Business summary for stakeholders + full mathematical technical report."
        />
      </div>
    </div>
  );
}

function Tip({
  icon: Icon,
  title,
  text,
}: {
  icon: typeof Github;
  title: string;
  text: string;
}) {
  return (
    <div className="glass-card p-4">
      <Icon className="mb-2 h-5 w-5 text-blue-400" />
      <p className="font-medium text-white">{title}</p>
      <p className="mt-1 text-xs text-omega-muted">{text}</p>
    </div>
  );
}
