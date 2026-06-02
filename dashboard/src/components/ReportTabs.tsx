import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { FullReport } from "../types";
import OmegaGauge from "./OmegaGauge";
import GradeBadge from "./GradeBadge";
import RiskPill from "./RiskPill";
import ImplementationBlocks from "./ImplementationBlocks";
import RerunButton from "./RerunButton";
import QualityDimensions from "./QualityDimensions";
import DeveloperGuidePanel from "./DeveloperGuidePanel";
import AgentOrchestrationPanel from "./AgentOrchestrationPanel";
import MetricSuitePanel from "./MetricSuitePanel";
import { exportUrl } from "../api/client";
import {
  Briefcase,
  Calculator,
  Download,
  Code2,
  ExternalLink,
  Grid3x3,
  Layers,
  ListChecks,
  Sigma,
  Table2,
} from "lucide-react";

type Tab =
  | "overview"
  | "metrics"
  | "dimensions"
  | "developer"
  | "business"
  | "technical"
  | "files"
  | "entities"
  | "improvements";

export default function ReportTabs({
  report,
  runId,
}: {
  report: FullReport;
  runId: string;
}) {
  const [tab, setTab] = useState<Tab>("overview");
  const [entityFilter, setEntityFilter] = useState<string>("all");
  const [improvementRiskFilter, setImprovementRiskFilter] = useState<string>("all");
  const biz = report.business_report || {};
  const tech = report.technical_report || {};
  const summary = report.entity_summary || {};
  const entities = report.entities || [];
  const plan = report.improvement_plan || [];

  const filteredPlan =
    improvementRiskFilter === "all"
      ? plan
      : plan.filter((item) => item.risk_band === improvementRiskFilter);

  const planByRisk = {
    CRITICAL: plan.filter((p) => p.risk_band === "CRITICAL").length,
    HIGH: plan.filter((p) => p.risk_band === "HIGH").length,
    MEDIUM: plan.filter((p) => p.risk_band === "MEDIUM").length,
    LOW: plan.filter((p) => p.risk_band === "LOW").length,
  };

  const filteredEntities =
    entityFilter === "all"
      ? entities
      : entities.filter((e) => e.entity_type === entityFilter);

  const chartData = report.files.slice(0, 12).map((f) => ({
    name: f.path.split("/").pop()?.slice(0, 14) || f.path,
    omega: f.omega_local,
  }));

  const entityChart = ["class", "method", "function", "field"].map((t) => ({
    type: t,
    count: entities.filter((e) => e.entity_type === t).length,
    avgOmega:
      entities.filter((e) => e.entity_type === t).length > 0
        ? entities
            .filter((e) => e.entity_type === t)
            .reduce((s, e) => s + e.omega_local, 0) /
          entities.filter((e) => e.entity_type === t).length
        : 0,
  }));

  const dims = report.dimensions || [];
  const metricCount = report.metric_suite?.metric_count ?? 0;

  const devGuide = report.developer_guide;
  const devCount = devGuide?.action_count ?? devGuide?.actions?.length ?? 0;

  const tabs: { id: Tab; label: string; icon: typeof Briefcase }[] = [
    { id: "overview", label: "Overview", icon: Table2 },
    { id: "metrics", label: `Metrics (${metricCount})`, icon: Sigma },
    { id: "developer", label: `Developer (${devCount})`, icon: Code2 },
    { id: "dimensions", label: `Dimensions (${dims.length})`, icon: Grid3x3 },
    { id: "improvements", label: `Improvements (${plan.length})`, icon: ListChecks },
    { id: "entities", label: `Symbols (${summary.total ?? entities.length})`, icon: Layers },
    { id: "business", label: "Business Report", icon: Briefcase },
    { id: "technical", label: "Technical / Math", icon: Calculator },
    { id: "files", label: `Files (${report.file_count})`, icon: Table2 },
  ];

  const listSection = (items: string | string[] | undefined) => {
    if (!items) return null;
    const arr = Array.isArray(items) ? items : [items];
    return (
      <ul className="mt-3 space-y-2 text-sm text-slate-300">
        {arr.map((item, i) => (
          <li key={i} className="flex gap-2">
            <span className="text-cyan-500">•</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    );
  };

  return (
    <div className="space-y-6">
      <div className="glass-card flex flex-wrap items-center justify-between gap-6 p-6">
        <div className="flex items-center gap-6">
          <OmegaGauge value={report.omega_index} />
          <div>
            <h2 className="font-display text-2xl font-bold text-white">
              {report.repo_display}
            </h2>
            <p className="mt-1 text-sm text-omega-muted">{report.analyzed_at}</p>
            <div className="mt-3 flex items-center gap-3">
              <GradeBadge grade={report.quality_grade} />
              <p className="max-w-xs text-xs text-omega-muted">
                Grade from Ω index on source files only — dimension scores are contextual and
                not every lens applies to every repo.
              </p>
              <div className="text-sm">
                <p>
                  Bayesian Q{" "}
                  <span className="font-mono text-cyan-400">
                    {report.bayesian_quality}/10
                  </span>
                </p>
                <p className="text-omega-muted">
                  Uncertainty {report.epistemic_uncertainty}
                </p>
              </div>
            </div>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <RerunButton
            runId={runId}
            label="Re-run analysis"
            className="btn-primary py-2 text-sm"
          />
          {(["html", "json", "csv", "entities", "implementations", "developer", "business", "technical"] as const).map((k) => (
              <a
                key={k}
                href={exportUrl(runId, k)}
                target="_blank"
                rel="noreferrer"
                className="btn-ghost text-xs"
              >
                <Download className="h-3.5 w-3.5" />
                {k.toUpperCase()}
              </a>
            )
          )}
          <a
            href={exportUrl(runId, "html")}
            target="_blank"
            rel="noreferrer"
            className="btn-primary text-sm"
          >
            <ExternalLink className="h-4 w-4" />
            Full HTML Report
          </a>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 border-b border-omega-border pb-2">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={`flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium transition ${
              tab === id
                ? "bg-blue-600/25 text-white ring-1 ring-blue-500/40"
                : "text-omega-muted hover:text-white"
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="glass-card p-6">
            <p className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
              Business
            </p>
            <p className="mt-3 text-slate-200">{report.health_summary_business}</p>
          </div>
          <div className="glass-card p-6">
            <p className="text-xs font-semibold uppercase tracking-wider text-violet-400">
              Technical
            </p>
            <p className="mt-3 text-slate-200">{report.health_summary_technical}</p>
          </div>
          <AgentOrchestrationPanel manifest={report.agent_manifest} />
          <div className="glass-card col-span-full p-6 lg:col-span-2">
            <h3 className="font-display font-semibold text-white">
              Top modules by Ω (risk)
            </h3>
            <div className="mt-4 h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} layout="vertical" margin={{ left: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e2d4a" />
                  <XAxis type="number" stroke="#8b9cb3" fontSize={11} />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={100}
                    stroke="#8b9cb3"
                    fontSize={10}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#0f1629",
                      border: "1px solid #1e2d4a",
                      borderRadius: 8,
                    }}
                  />
                  <Bar dataKey="omega" fill="#3b82f6" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="glass-card grid grid-cols-2 gap-4 p-6 sm:grid-cols-3">
            {Object.entries(report.pillars).map(([k, v]) => (
              <div key={k} className="rounded-xl bg-omega-bg/60 p-3">
                <p className="text-xs text-omega-muted">{k.replace(/_/g, " ")}</p>
                <p className="font-mono text-lg font-semibold text-white">{v}</p>
              </div>
            ))}
          </div>
          {dims.length > 0 && (
            <div className="glass-card col-span-full p-4 lg:col-span-2">
              <button
                type="button"
                onClick={() => setTab("dimensions")}
                className="text-sm font-medium text-cyan-400 hover:underline"
              >
                View full {dims.length}-dimension repo profile →
              </button>
            </div>
          )}
          {summary.total > 0 && (
            <div className="glass-card col-span-full p-6 lg:col-span-2">
              <h3 className="font-display font-semibold text-white">
                Symbol-level coverage
              </h3>
              <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-5">
                {[
                  ["Classes", summary.class],
                  ["Methods", summary.method],
                  ["Functions", summary.function],
                  ["Fields", summary.field],
                  ["High risk", summary.high_risk],
                ].map(([label, val]) => (
                  <div
                    key={String(label)}
                    className="rounded-xl bg-omega-bg/60 p-3 text-center"
                  >
                    <p className="text-xs text-omega-muted">{label}</p>
                    <p className="font-display text-xl font-bold text-white">
                      {val ?? 0}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {tab === "developer" && (
        <div className="glass-card p-6">
          <DeveloperGuidePanel guide={devGuide} />
        </div>
      )}

      {tab === "metrics" && (
        <div className="glass-card p-6">
          <MetricSuitePanel suite={report.metric_suite} />
        </div>
      )}

      {tab === "dimensions" && (
        <div className="glass-card p-6">
          <QualityDimensions
            dimensions={dims}
            repoDisplay={report.repo_display}
          />
        </div>
      )}

      {tab === "improvements" && (
        <div className="space-y-4">
          <div className="glass-card p-6">
            <h3 className="font-display text-lg font-semibold text-white">
              All symbol improvement areas
            </h3>
            <p className="mt-2 text-sm text-omega-muted">
              Every measured class, method, function, and field — ordered
              CRITICAL → HIGH → MEDIUM → LOW. Includes maintenance notes for
              healthy (LOW) symbols.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              {(
                [
                  ["all", `All (${plan.length})`],
                  ["CRITICAL", `Critical (${planByRisk.CRITICAL})`],
                  ["HIGH", `High (${planByRisk.HIGH})`],
                  ["MEDIUM", `Medium (${planByRisk.MEDIUM})`],
                  ["LOW", `Low (${planByRisk.LOW})`],
                ] as const
              ).map(([id, label]) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => setImprovementRiskFilter(id)}
                  className={`rounded-lg px-3 py-1.5 text-xs font-medium ${
                    improvementRiskFilter === id
                      ? "bg-blue-600/30 text-white ring-1 ring-blue-500/50"
                      : "bg-slate-800/80 text-omega-muted hover:text-white"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          {filteredPlan.length === 0 ? (
            <div className="glass-card p-8 text-center text-omega-muted">
              No symbols match this risk filter.
            </div>
          ) : (
            filteredPlan.map((item) => (
              <div
                key={`${item.qualified_name}-${item.lines}`}
                className="glass-card p-6"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <span className="rounded-md bg-blue-500/20 px-2 py-0.5 text-xs font-semibold uppercase text-blue-300">
                      {item.entity_type}
                    </span>
                    <h4 className="mt-2 font-mono text-sm font-semibold text-white">
                      {item.qualified_name}
                    </h4>
                    <p className="text-xs text-omega-muted">
                      {item.file_path} · lines {item.lines} · Ω {item.omega_local}
                    </p>
                  </div>
                  <RiskPill band={item.risk_band} />
                </div>
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <div className="rounded-xl border border-violet-500/20 bg-violet-500/5 p-4">
                    <p className="text-xs font-semibold uppercase text-violet-400">
                      Technical
                    </p>
                    <ul className="mt-2 space-y-1 text-sm text-slate-300">
                      {item.improvement_areas.map((a, i) => (
                        <li key={i}>• {a}</li>
                      ))}
                    </ul>
                  </div>
                  <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4">
                    <p className="text-xs font-semibold uppercase text-emerald-400">
                      Business
                    </p>
                    <ul className="mt-2 space-y-1 text-sm text-slate-300">
                      {item.improvement_areas_business.map((a, i) => (
                        <li key={i}>• {a}</li>
                      ))}
                    </ul>
                  </div>
                </div>
                <ImplementationBlocks
                  diffs={item.implementation_diffs}
                  blocks={item.implementation_plan || []}
                />
              </div>
            ))
          )}
        </div>
      )}

      {tab === "entities" && (
        <div className="space-y-4">
          <div className="glass-card flex flex-wrap items-center justify-between gap-4 p-4">
            <div className="flex flex-wrap gap-2">
              {["all", "class", "method", "function", "field"].map((f) => (
                <button
                  key={f}
                  type="button"
                  onClick={() => setEntityFilter(f)}
                  className={`rounded-lg px-3 py-1.5 text-xs font-medium capitalize ${
                    entityFilter === f
                      ? "bg-blue-600/30 text-white ring-1 ring-blue-500/50"
                      : "text-omega-muted hover:text-white"
                  }`}
                >
                  {f === "all" ? "All" : `${f}s`}
                </button>
              ))}
            </div>
            <p className="text-xs text-omega-muted">
              Showing {filteredEntities.length} symbols
            </p>
          </div>
          <div className="glass-card h-48 p-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={entityChart}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2d4a" />
                <XAxis dataKey="type" stroke="#8b9cb3" fontSize={11} />
                <YAxis stroke="#8b9cb3" fontSize={11} />
                <Tooltip
                  contentStyle={{
                    background: "#0f1629",
                    border: "1px solid #1e2d4a",
                  }}
                />
                <Bar dataKey="count" fill="#22d3ee" name="Count" />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="glass-card overflow-hidden">
            <div className="max-h-[560px] overflow-auto">
              <table className="w-full text-left text-sm">
                <thead className="sticky top-0 bg-omega-card text-xs uppercase text-omega-muted">
                  <tr>
                    <th className="px-4 py-3">Type</th>
                    <th className="px-4 py-3">Symbol</th>
                    <th className="px-4 py-3">Location</th>
                    <th className="px-4 py-3">Ω</th>
                    <th className="px-4 py-3">Cyc</th>
                    <th className="px-4 py-3">Risk</th>
                    <th className="px-4 py-3">Improvement</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredEntities.map((e) => (
                    <tr
                      key={`${e.qualified_name}-${e.line_start}`}
                      className="border-t border-omega-border/60 hover:bg-white/5"
                    >
                      <td className="px-4 py-2 capitalize text-omega-muted">
                        {e.entity_type}
                      </td>
                      <td className="max-w-[180px] truncate px-4 py-2 font-mono text-xs">
                        {e.qualified_name}
                      </td>
                      <td className="px-4 py-2 text-xs text-omega-muted">
                        {e.file_path}:{e.line_start}
                      </td>
                      <td className="px-4 py-2 font-semibold">{e.omega_local}</td>
                      <td className="px-4 py-2">{e.cyclomatic}</td>
                      <td className="px-4 py-2">
                        <RiskPill band={e.risk_band} />
                      </td>
                      <td className="max-w-xs px-4 py-2 text-xs text-omega-muted">
                        {e.improvement_areas_business[0] || e.improvement_areas[0]}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {tab === "business" && (
        <div className="glass-card space-y-8 p-8">
          <Section title="Executive summary" body={biz.executive_summary as string} />
          <Section title="What is the Omega Index?" body={biz.what_omega_means as string} />
          <Section title="Confidence" body={biz.confidence as string} />
          <div>
            <h3 className="font-display text-lg font-semibold text-white">
              Business impact
            </h3>
            {listSection(biz.business_impact)}
          </div>
          <div>
            <h3 className="font-display text-lg font-semibold text-white">
              Priority fixes
            </h3>
            {listSection(biz.priority_fixes)}
          </div>
          <div>
            <h3 className="font-display text-lg font-semibold text-white">
              Recommended actions
            </h3>
            {listSection(report.recommendations_business)}
          </div>
          <div>
            <h3 className="font-display text-lg font-semibold text-white">
              Symbol-level improvement plan
            </h3>
            {listSection(biz.entity_improvement_plan as string[])}
          </div>
          <Section
            title="For non-technical readers"
            body={biz.for_non_technical_stakeholders as string}
          />
        </div>
      )}

      {tab === "technical" && (
        <div className="glass-card space-y-8 p-8">
          <Section title="Abstract" body={tech.abstract as string} />
          <div>
            <h3 className="font-display text-lg font-semibold text-white">
              Formal definitions
            </h3>
            {listSection(tech.aggregate_formulas as string[])}
          </div>
          <div>
            <h3 className="font-display text-lg font-semibold text-white">
              Methodology
            </h3>
            {listSection(tech.methodology as string[])}
          </div>
          <div>
            <h3 className="font-display text-lg font-semibold text-white">
              Engineering recommendations
            </h3>
            {listSection(report.recommendations_technical)}
          </div>
          <div>
            <h3 className="font-display text-lg font-semibold text-white">
              Per-entity measurements (sample)
            </h3>
            {listSection(tech.per_entity_technical as string[])}
          </div>
          <div>
            <h3 className="font-display text-lg font-semibold text-white">
              Limitations
            </h3>
            {listSection(tech.limitations as string[])}
          </div>
        </div>
      )}

      {tab === "files" && (
        <div className="glass-card overflow-hidden">
          <div className="max-h-[600px] overflow-auto">
            <table className="w-full text-left text-sm">
              <thead className="sticky top-0 bg-omega-card text-xs uppercase text-omega-muted">
                <tr>
                  <th className="px-4 py-3">File</th>
                  <th className="px-4 py-3">Lang</th>
                  <th className="px-4 py-3">Ω</th>
                  <th className="px-4 py-3">Risk</th>
                  <th className="px-4 py-3 hidden lg:table-cell">Business note</th>
                </tr>
              </thead>
              <tbody>
                {report.files.map((f) => (
                  <tr
                    key={f.path}
                    className="border-t border-omega-border/60 hover:bg-white/5"
                  >
                    <td className="max-w-[200px] truncate px-4 py-2 font-mono text-xs">
                      {f.path}
                    </td>
                    <td className="px-4 py-2 text-omega-muted">{f.language}</td>
                    <td className="px-4 py-2 font-semibold">{f.omega_local}</td>
                    <td className="px-4 py-2">
                      <RiskPill band={f.risk_band} />
                    </td>
                    <td className="hidden max-w-md px-4 py-2 text-xs text-omega-muted lg:table-cell">
                      {f.business_note}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function Section({ title, body }: { title: string; body?: string }) {
  if (!body) return null;
  return (
    <div>
      <h3 className="font-display text-lg font-semibold text-white">{title}</h3>
      <p className="mt-3 leading-relaxed text-slate-300">{body}</p>
    </div>
  );
}
