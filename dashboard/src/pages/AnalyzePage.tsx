import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import JSZip from "jszip";
import {
  startAnalysis,
  startAnalysisFromZip,
  waitForRunCompletion,
} from "../api/client";
import {
  Github,
  Loader2,
  Sparkles,
  FolderOpen,
  Zap,
  Upload,
} from "lucide-react";

const EXAMPLES = [
  "psf/requests",
  "pallets/flask",
  "django/django",
  "fastapi/fastapi",
];
const ANALYZE_PREFS_KEY = "omega.analyze.prefs";

export default function AnalyzePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [target, setTarget] = useState("");
  const [zipFile, setZipFile] = useState<File | null>(null);
  const [folderFiles, setFolderFiles] = useState<File[]>([]);
  const [folderName, setFolderName] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [background, setBackground] = useState(false);
  const [progress, setProgress] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const prefill = searchParams.get("target");
    if (prefill) setTarget(prefill);
  }, [searchParams]);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(ANALYZE_PREFS_KEY);
      if (!raw) return;
      const prefs = JSON.parse(raw) as { background?: boolean };
      setBackground(Boolean(prefs.background));
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    localStorage.setItem(
      ANALYZE_PREFS_KEY,
      JSON.stringify({ background })
    );
  }, [background]);

  const run = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    setProgress("Starting analysis…");
    try {
      const hasTarget = target.trim().length > 0;
      const hasZip = Boolean(zipFile);
      const hasFolder = folderFiles.length > 0;
      if (!hasTarget && !hasZip && !hasFolder) {
        throw new Error(
          "Provide a repository target, upload a .zip archive, or choose a local project folder"
        );
      }
      const selectedCount = [hasTarget, hasZip, hasFolder].filter(Boolean).length;
      if (selectedCount > 1) {
        throw new Error(
          "Choose only one source: repository target, zip upload, or local project folder"
        );
      }

      let run_id: string;
      if (hasFolder) {
        setProgress("Preparing project folder for upload…");
        const zip = new JSZip();
        for (const f of folderFiles) {
          const rel = f.webkitRelativePath || f.name;
          zip.file(rel, f);
        }
        const blob = await zip.generateAsync({ type: "blob" });
        const uploadName = `${folderName || "local-project"}.zip`;
        const zipFromFolder = new File([blob], uploadName, {
          type: "application/zip",
        });
        ({ run_id } = await startAnalysisFromZip(zipFromFolder));
      } else if (hasZip) {
        ({ run_id } = await startAnalysisFromZip(zipFile as File));
      } else {
        ({ run_id } = await startAnalysis(target.trim()));
      }
      if (background) {
        navigate("/");
        return;
      }
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
        <div>
          <label className="mb-2 flex items-center gap-2 text-sm font-medium text-white">
            <FolderOpen className="h-4 w-4 text-cyan-400" />
            Choose complete local project folder
          </label>
          <input
            type="file"
            multiple
            {...({ webkitdirectory: "", directory: "" } as Record<string, string>)}
            className="input-field cursor-pointer file:mr-3 file:rounded-md file:border file:border-omega-border file:bg-omega-bg file:px-3 file:py-1 file:text-sm file:text-white"
            onChange={(e) => {
              const files = Array.from(e.target.files || []);
              setFolderFiles(files);
              const firstRel = files[0]?.webkitRelativePath || "";
              setFolderName(firstRel.split("/")[0] || "local-project");
            }}
            disabled={busy}
          />
          <p className="mt-2 text-xs text-omega-muted">
            Select a local project folder to upload all files recursively.
            {folderFiles.length > 0
              ? ` Selected ${folderFiles.length} files from ${folderName || "folder"}.`
              : ""}
          </p>
        </div>
        <div>
          <label className="mb-2 flex items-center gap-2 text-sm font-medium text-white">
            <Upload className="h-4 w-4 text-cyan-400" />
            Upload app zip (local)
          </label>
          <input
            type="file"
            accept=".zip,application/zip,application/x-zip-compressed"
            className="input-field cursor-pointer file:mr-3 file:rounded-md file:border file:border-omega-border file:bg-omega-bg file:px-3 file:py-1 file:text-sm file:text-white"
            onChange={(e) => setZipFile(e.target.files?.[0] ?? null)}
            disabled={busy}
          />
          <p className="mt-2 text-xs text-omega-muted">
            Upload a single project archive. Use this instead of repository target.
          </p>
        </div>

        {error && (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        )}

        <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-omega-border bg-omega-bg/40 px-4 py-3">
          <input
            type="checkbox"
            checked={background}
            onChange={(e) => setBackground(e.target.checked)}
            disabled={busy}
            className="mt-0.5 h-4 w-4 rounded border-omega-border accent-cyan-500"
          />
          <div>
            <p className="text-sm font-medium text-white">Run in background</p>
            <p className="text-xs text-omega-muted">
              Queue the analysis and return to the dashboard — watch progress there.
            </p>
          </div>
        </label>

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
          icon={Upload}
          title="Zip upload"
          text="Upload a local .zip archive when the server cannot access your path."
        />
        <Tip
          icon={FolderOpen}
          title="Complete folder upload"
          text="Pick a local project folder; it is packaged and analyzed as one upload."
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
