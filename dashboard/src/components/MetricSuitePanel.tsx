import { useMemo, useState } from "react";
import type { MetricRecord, MetricSuite } from "../types";
import RiskPill from "./RiskPill";
import { Activity, ArrowDownLeft, ArrowUpRight, Globe2, Sigma } from "lucide-react";

const CATEGORY_LABELS: Record<string, string> = {
  field: "Code field",
  business: "Business context",
  upstream: "Upstream services",
  downstream: "Downstream impact",
  impact: "Ecosystem impact",
};

function MetricRow({ m }: { m: MetricRecord }) {
  return (
    <div className="metric-row border border-slate-700/60 rounded-lg p-3 bg-slate-900/40">
      <div className="flex flex-wrap items-center gap-2 justify-between">
        <div>
          <span className="font-medium text-slate-100">{m.name}</span>
          {m.related_service && (
            <span className="ml-2 text-xs text-cyan-400">{m.related_service}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-lg font-mono text-amber-300">{m.value.toFixed(1)}</span>
          <span className="text-xs text-slate-500">{m.unit}</span>
          <RiskPill band={m.band} />
        </div>
      </div>
      <p className="text-sm text-slate-400 mt-2">{m.summary_business}</p>
      <details className="mt-2 text-xs text-slate-500">
        <summary className="cursor-pointer hover:text-slate-300">Formula & technical</summary>
        <p className="mt-1 font-mono">{m.formula}</p>
        <p className="mt-1">{m.summary_technical}</p>
        {m.evidence.length > 0 && (
          <ul className="mt-1 list-disc pl-4">
            {m.evidence.slice(0, 4).map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        )}
      </details>
    </div>
  );
}

export default function MetricSuitePanel({ suite }: { suite: MetricSuite | undefined }) {
  const [filter, setFilter] = useState<string>("all");

  const metrics = suite?.metrics ?? [];
  const byCat = suite?.by_category ?? {};

  const filtered = useMemo(() => {
    if (filter === "all") return metrics;
    return metrics.filter((m) => m.category === filter);
  }, [metrics, filter]);

  if (!suite || metrics.length === 0) {
    return (
      <div className="card p-6 text-slate-400">
        <p>No metric suite on this report. Re-run analysis to compute the full Ω metric field.</p>
      </div>
    );
  }

  const ctx = suite.service_context;
  const impact = suite.impact_summary;
  const eco = suite.ecosystem;

  return (
    <div className="space-y-6">
      <div className="grid md:grid-cols-2 gap-4">
        <div className="card p-4 border-l-4 border-cyan-500">
          <div className="flex items-center gap-2 text-cyan-400 mb-2">
            <Globe2 size={18} />
            <h3 className="font-semibold">Service context</h3>
          </div>
          <p className="text-lg font-medium">{ctx.service_name}</p>
          <p className="text-sm text-slate-400">
            Role: <span className="text-slate-200">{ctx.service_role}</span>
            {" · "}
            Domains: {(ctx.business_domains || []).join(", ")}
          </p>
          <p className="text-sm text-slate-400 mt-2">{ctx.description_business}</p>
        </div>
        <div className="card p-4 border-l-4 border-amber-500">
          <div className="flex items-center gap-2 text-amber-400 mb-2">
            <Activity size={18} />
            <h3 className="font-semibold">Ecosystem impact</h3>
          </div>
          <p className="text-sm text-slate-400">{eco.graph_summary_business}</p>
          <dl className="grid grid-cols-2 gap-2 mt-3 text-sm">
            <div>
              <dt className="text-slate-500">Business continuity</dt>
              <dd className="font-mono text-amber-300">
                {impact.business_continuity_risk?.toFixed(1) ?? "—"}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Ecosystem stress</dt>
              <dd className="font-mono text-amber-300">
                {impact.ecosystem_field_stress?.toFixed(1) ?? "—"}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Upstream aggregate</dt>
              <dd className="font-mono">{impact.upstream_aggregate_stress?.toFixed(1) ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Downstream blast</dt>
              <dd className="font-mono">{impact.downstream_blast_radius?.toFixed(1) ?? "—"}</dd>
            </div>
          </dl>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 items-center">
        <Sigma size={16} className="text-violet-400" />
        <span className="text-sm text-slate-400">
          {suite.metric_count} mathematical metrics
        </span>
        {(["all", "field", "business", "upstream", "downstream", "impact"] as const).map((c) => (
          <button
            key={c}
            type="button"
            className={`px-2 py-1 rounded text-xs ${
              filter === c ? "bg-violet-600 text-white" : "bg-slate-800 text-slate-400"
            }`}
            onClick={() => setFilter(c)}
          >
            {c === "all" ? "All" : CATEGORY_LABELS[c] ?? c}
            {c !== "all" && byCat[c] ? ` (${byCat[c].length})` : ""}
          </button>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-3">
        {filtered.map((m) => (
          <MetricRow key={m.id} m={m} />
        ))}
      </div>

      {(eco.upstream?.length > 0 || eco.downstream?.length > 0) && (
        <div className="grid md:grid-cols-2 gap-4">
          <div className="card p-4">
            <h4 className="flex items-center gap-2 text-sm font-semibold text-slate-300 mb-2">
              <ArrowUpRight size={16} /> Upstream ({eco.upstream_count})
            </h4>
            <ul className="text-sm space-y-1 text-slate-400">
              {eco.upstream.slice(0, 12).map((n) => (
                <li key={n.name}>
                  <span className="text-slate-200">{n.name}</span>
                  <span className="text-xs ml-1">({n.kind})</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="card p-4">
            <h4 className="flex items-center gap-2 text-sm font-semibold text-slate-300 mb-2">
              <ArrowDownLeft size={16} /> Downstream ({eco.downstream_count})
            </h4>
            <ul className="text-sm space-y-1 text-slate-400">
              {eco.downstream.slice(0, 12).map((n) => (
                <li key={n.name}>
                  <span className="text-slate-200">{n.name}</span>
                  <span className="text-xs ml-1">({n.kind})</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
