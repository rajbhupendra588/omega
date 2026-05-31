import ImplementationBlocks from "./ImplementationBlocks";
import RiskPill from "./RiskPill";
import type { DeveloperGuide as DeveloperGuideType } from "../types";
import { AlertTriangle, Code2, ListOrdered, Wrench } from "lucide-react";

export default function DeveloperGuidePanel({
  guide,
}: {
  guide: DeveloperGuideType | undefined;
}) {
  if (!guide?.actions?.length) {
    return (
      <p className="text-sm text-omega-muted">
        No developer action items yet. Re-run analysis or refresh — the API
        backfills this section from saved metrics when possible.
      </p>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <div className="flex items-center gap-2">
          <Code2 className="h-5 w-5 text-sky-400" />
          <h3 className="font-display text-lg font-semibold text-white">
            Developer action guide
          </h3>
        </div>
        <p className="mt-3 text-sm leading-relaxed text-slate-300">
          {guide.introduction}
        </p>
      </div>

      <div className="rounded-xl border border-sky-500/20 bg-sky-500/5 p-4">
        <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-sky-400">
          <ListOrdered className="h-4 w-4" />
          How to read
        </p>
        <ul className="mt-2 space-y-1 text-sm text-slate-400">
          {guide.how_to_read.map((line, i) => (
            <li key={i}>• {line}</li>
          ))}
        </ul>
      </div>

      <div className="space-y-6">
        {guide.actions.map((act) => (
          <article
            key={`${act.priority}-${act.title}`}
            className="glass-card overflow-hidden border-l-4 border-sky-500/60"
          >
            <div className="flex flex-wrap items-start justify-between gap-3 border-b border-omega-border px-6 py-4">
              <div>
                <span className="font-mono text-xs text-sky-400">
                  Priority #{act.priority}
                </span>
                <h4 className="mt-1 font-display text-base font-semibold text-white">
                  {act.title}
                </h4>
                <p className="mt-1 font-mono text-xs text-omega-muted">
                  {act.location}
                  {act.symbol ? ` · ${act.symbol}` : ""}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span className="rounded-md bg-slate-800 px-2 py-0.5 text-xs capitalize text-omega-muted">
                  {act.category.replace(/_/g, " ")}
                </span>
                <RiskPill band={act.risk_band} />
              </div>
            </div>

            <div className="grid gap-0 md:grid-cols-2">
              <div className="border-b border-omega-border p-6 md:border-b-0 md:border-r">
                <p className="flex items-center gap-2 text-xs font-semibold uppercase text-amber-400/90">
                  <AlertTriangle className="h-4 w-4" />
                  Why this is risky
                </p>
                <p className="mt-3 text-sm leading-relaxed text-slate-300">
                  {act.why_risky}
                </p>
                <dl className="mt-4 grid grid-cols-2 gap-2 text-xs">
                  {Object.entries(act.metrics).map(([k, v]) => (
                    <div key={k} className="rounded-lg bg-black/20 px-2 py-1">
                      <dt className="text-omega-muted">{k.replace(/_/g, " ")}</dt>
                      <dd className="font-mono text-cyan-300">{v}</dd>
                    </div>
                  ))}
                </dl>
              </div>
              <div className="p-6">
                <p className="flex items-center gap-2 text-xs font-semibold uppercase text-emerald-400/90">
                  <Wrench className="h-4 w-4" />
                  What to do in this repo
                </p>
                <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm text-slate-300">
                  {act.what_to_do.map((step, i) => (
                    <li key={i}>{step}</li>
                  ))}
                </ol>
              </div>
            </div>

            {act.implementation_plan?.length > 0 && (
              <div className="border-t border-omega-border px-6 pb-6">
                <ImplementationBlocks blocks={act.implementation_plan} />
              </div>
            )}
          </article>
        ))}
      </div>
    </div>
  );
}
