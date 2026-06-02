import { useState } from "react";
import ImplementationBlocks from "./ImplementationBlocks";
import RiskPill from "./RiskPill";
import type { DeveloperAction, DeveloperGuide as DeveloperGuideType } from "../types";
import { AlertTriangle, ChevronDown, ChevronUp, Code2, Layers, ListOrdered, Wrench } from "lucide-react";

function tierLabel(tier?: string): string | null {
  if (tier === "sprint") return "Sprint queue";
  if (tier === "summary") return "Module batch";
  if (tier === "backlog") return "Backlog";
  return null;
}

function ActionCard({ act }: { act: DeveloperAction }) {
  const [expandFiles, setExpandFiles] = useState(false);
  const tier = tierLabel(act.action_tier);
  const isGroup = act.category === "module_health_group";

  return (
    <article
      className={`glass-card overflow-hidden border-l-4 ${
        isGroup ? "border-amber-500/60" : "border-sky-500/60"
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-omega-border px-6 py-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-xs text-sky-400">Priority #{act.priority}</span>
            {tier ? (
              <span
                className={`rounded-md px-2 py-0.5 text-[10px] font-semibold uppercase ${
                  act.action_tier === "sprint"
                    ? "bg-emerald-500/20 text-emerald-300"
                    : act.action_tier === "summary"
                      ? "bg-amber-500/20 text-amber-300"
                      : "bg-slate-700 text-slate-400"
                }`}
              >
                {tier}
              </span>
            ) : null}
          </div>
          <h4 className="mt-1 font-display text-base font-semibold text-white">{act.title}</h4>
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
          <p className="mt-3 text-sm leading-relaxed text-slate-300">{act.why_risky}</p>
          {!isGroup ? (
            <dl className="mt-4 grid grid-cols-2 gap-2 text-xs">
              {Object.entries(act.metrics).map(([k, v]) => (
                <div key={k} className="rounded-lg bg-black/20 px-2 py-1">
                  <dt className="text-omega-muted">{k.replace(/_/g, " ")}</dt>
                  <dd className="font-mono text-cyan-300">{v}</dd>
                </div>
              ))}
            </dl>
          ) : null}
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

      {isGroup && act.grouped_files && act.grouped_files.length > 0 ? (
        <div className="border-t border-omega-border px-6 py-4">
          <button
            type="button"
            className="flex items-center gap-2 text-xs font-medium text-slate-400 hover:text-white"
            onClick={() => setExpandFiles(!expandFiles)}
          >
            <Layers className="h-4 w-4" />
            {expandFiles ? "Hide" : "Show"} all {act.grouped_files.length} modules
            {expandFiles ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          </button>
          {expandFiles ? (
            <ul className="mt-3 max-h-64 space-y-1 overflow-y-auto font-mono text-xs text-slate-400">
              {act.grouped_files.map((f) => (
                <li key={f.path} className="rounded bg-black/20 px-2 py-1">
                  {f.path}{" "}
                  <span className="text-cyan-400/80">Ω {f.omega_local}</span>{" "}
                  <span className="text-omega-muted">cc {f.cyclomatic}</span>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      {act.implementation_diffs?.length || act.implementation_plan?.length ? (
        <div className="border-t border-omega-border px-6 pb-6">
          <ImplementationBlocks
            diffs={act.implementation_diffs}
            blocks={act.implementation_plan}
          />
        </div>
      ) : null}
    </article>
  );
}

export default function DeveloperGuidePanel({
  guide,
}: {
  guide: DeveloperGuideType | undefined;
}) {
  const [showBacklog, setShowBacklog] = useState(false);

  if (!guide?.actions?.length) {
    return (
      <p className="text-sm text-omega-muted">
        No developer action items yet. Re-run analysis or refresh — the API backfills this
        section from saved metrics when possible.
      </p>
    );
  }

  const sprint = guide.actions.filter((a) => a.action_tier === "sprint" || !a.action_tier);
  const summary = guide.actions.filter((a) => a.action_tier === "summary");
  const backlog = guide.actions.filter((a) => a.action_tier === "backlog");

  return (
    <div className="space-y-8">
      <div>
        <div className="flex items-center gap-2">
          <Code2 className="h-5 w-5 text-sky-400" />
          <h3 className="font-display text-lg font-semibold text-white">Developer action guide</h3>
        </div>
        <p className="mt-3 text-sm leading-relaxed text-slate-300">{guide.introduction}</p>
        {guide.sprint_count != null ? (
          <p className="mt-2 text-xs text-slate-500">
            {guide.sprint_count} symbol fixes
            {guide.module_group_count
              ? ` · ${guide.module_group_count} modules in batch summary`
              : ""}
            {backlog.length ? ` · ${backlog.length} backlog items` : ""}
          </p>
        ) : null}
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

      {sprint.length > 0 ? (
        <section className="space-y-4">
          <h4 className="text-sm font-semibold uppercase tracking-wide text-emerald-400/90">
            Sprint queue — fix these first
          </h4>
          <div className="space-y-6">
            {sprint.map((act) => (
              <ActionCard key={`${act.priority}-${act.title}`} act={act} />
            ))}
          </div>
        </section>
      ) : null}

      {summary.length > 0 ? (
        <section className="space-y-4">
          <h4 className="text-sm font-semibold uppercase tracking-wide text-amber-400/90">
            Module batch — same playbook, many files
          </h4>
          <div className="space-y-6">
            {summary.map((act) => (
              <ActionCard key={`${act.priority}-${act.title}`} act={act} />
            ))}
          </div>
        </section>
      ) : null}

      {backlog.length > 0 ? (
        <section className="space-y-4">
          <button
            type="button"
            className="flex items-center gap-2 text-sm font-semibold text-slate-400 hover:text-white"
            onClick={() => setShowBacklog(!showBacklog)}
          >
            Backlog ({backlog.length} items)
            {showBacklog ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
          {showBacklog ? (
            <div className="space-y-6">
              {backlog.map((act) => (
                <ActionCard key={`${act.priority}-${act.title}`} act={act} />
              ))}
            </div>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
