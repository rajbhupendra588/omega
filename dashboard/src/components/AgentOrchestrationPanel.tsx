import type { AgentManifest } from "../types";
import { Bot, Cpu } from "lucide-react";

export default function AgentOrchestrationPanel({
  manifest,
}: {
  manifest: AgentManifest | undefined;
}) {
  if (!manifest?.workers_planned?.length) return null;

  return (
    <section className="glass-card col-span-full space-y-4 p-6 lg:col-span-2">
      <div className="flex items-center gap-2">
        <Bot className="h-5 w-5 text-cyan-400" />
        <h3 className="font-display font-semibold text-white">
          Master agent & language workers
        </h3>
      </div>
      <p className="text-sm text-omega-muted">
        Primary stack: <span className="text-white">{manifest.primary_language}</span>
        {" · "}
        {manifest.total_files} files · {manifest.tech_stack?.length ?? 0} workers spawned
      </p>
      {manifest.orchestration_plan?.length > 0 && (
        <ul className="space-y-1 text-sm text-slate-400">
          {manifest.orchestration_plan.slice(0, 4).map((line, i) => (
            <li key={i}>{line}</li>
          ))}
        </ul>
      )}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {manifest.tech_stack?.map((entry) => {
          const result = manifest.worker_results?.find(
            (r) => r.worker_id === entry.worker_id
          );
          return (
            <div
              key={entry.worker_id}
              className="rounded-lg border border-white/10 bg-white/5 p-4"
            >
              <div className="flex items-center gap-2 text-sm font-medium text-white">
                <Cpu className="h-4 w-4 text-cyan-400/80" />
                {entry.language}
              </div>
              <p className="mt-1 font-mono text-xs text-omega-muted">{entry.worker_id}</p>
              <p className="mt-2 text-xs text-slate-400">
                {entry.file_count} files ({entry.share_pct}%) · {entry.strategy}
              </p>
              {result && (
                <p className="mt-2 text-xs text-emerald-400/90">
                  {result.status} · {result.entities_found} symbols · {result.duration_ms}ms
                </p>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
