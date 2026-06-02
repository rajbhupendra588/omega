import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { EntityMetric, FileMetric, FullReport } from "../types";
import OmegaGauge from "./OmegaGauge";
import GradeBadge from "./GradeBadge";
import RiskPill from "./RiskPill";
import ImplementationBlocks from "./ImplementationBlocks";
import RerunButton from "./RerunButton";
import QualityDimensions from "./QualityDimensions";
import DeveloperGuidePanel from "./DeveloperGuidePanel";
import AgentOrchestrationPanel from "./AgentOrchestrationPanel";
import MetricSuitePanel from "./MetricSuitePanel";
import SortableHeader from "./SortableHeader";
import { exportUrl } from "../api/client";
import {
  compareNumbers,
  compareStrings,
  matchesQuery,
  toggleSortDir,
  type SortDir,
} from "../lib/tableUtils";
import {
  Briefcase,
  Calculator,
  Download,
  Code2,
  ExternalLink,
  Grid3x3,
  Layers,
  ListChecks,
  Search,
  Sigma,
  Table2,
  X,
} from "lucide-react";

type Tab =
  | "overview"
  | "engineering"
  | "metrics"
  | "dimensions"
  | "developer"
  | "business"
  | "technical"
  | "files"
  | "entities"
  | "improvements";

type EntitySortKey = "symbol" | "omega" | "cyclomatic";
type FileSortKey = "file" | "language" | "omega";
const REPORT_PREFS_KEY = "omega.report.prefs";
const REPORT_TIPS_KEY = "omega.report.tips.dismissed";

export default function ReportTabs({
  report,
  runId,
}: {
  report: FullReport;
  runId?: string;
}) {
  const [searchParams, setSearchParams] = useSearchParams();
  const entitySearchRef = useRef<HTMLInputElement | null>(null);
  const fileSearchRef = useRef<HTMLInputElement | null>(null);
  const tabFromUrl = searchParams.get("tab") as Tab | null;
  const [tab, setTab] = useState<Tab>(tabFromUrl ?? "overview");
  const [entityFilter, setEntityFilter] = useState<string>("all");
  const [entitySearch, setEntitySearch] = useState("");
  const [entitySortKey, setEntitySortKey] = useState<EntitySortKey>("omega");
  const [entitySortDir, setEntitySortDir] = useState<SortDir>("desc");
  const [fileSearch, setFileSearch] = useState("");
  const [fileSortKey, setFileSortKey] = useState<FileSortKey>("omega");
  const [fileSortDir, setFileSortDir] = useState<SortDir>("desc");
  const [improvementRiskFilter, setImprovementRiskFilter] = useState<string>("all");
  const [showTips, setShowTips] = useState(true);
  const biz = report.business_report || {};
  const tech = report.technical_report || {};
  const summary = report.entity_summary || {};
  const entities = report.entities || [];
  const plan = report.improvement_plan || [];
  const scorecard = report.scorecard;
  const refactorSuggestions = report.suggested_refactorings || [];

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

  useEffect(() => {
    if (
      tabFromUrl &&
      [
        "overview",
        "engineering",
        "metrics",
        "dimensions",
        "developer",
        "business",
        "technical",
        "files",
        "entities",
        "improvements",
      ].includes(tabFromUrl)
    ) {
      setTab(tabFromUrl);
    }
  }, [tabFromUrl]);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(REPORT_PREFS_KEY);
      if (!raw) return;
      const prefs = JSON.parse(raw) as {
        entityFilter?: string;
        entitySearch?: string;
        entitySortKey?: EntitySortKey;
        entitySortDir?: SortDir;
        fileSearch?: string;
        fileSortKey?: FileSortKey;
        fileSortDir?: SortDir;
        improvementRiskFilter?: string;
      };
      if (prefs.entityFilter) setEntityFilter(prefs.entityFilter);
      if (prefs.entitySearch) setEntitySearch(prefs.entitySearch);
      if (prefs.entitySortKey) setEntitySortKey(prefs.entitySortKey);
      if (prefs.entitySortDir) setEntitySortDir(prefs.entitySortDir);
      if (prefs.fileSearch) setFileSearch(prefs.fileSearch);
      if (prefs.fileSortKey) setFileSortKey(prefs.fileSortKey);
      if (prefs.fileSortDir) setFileSortDir(prefs.fileSortDir);
      if (prefs.improvementRiskFilter) {
        setImprovementRiskFilter(prefs.improvementRiskFilter);
      }
    } catch {
      /* ignore corrupted prefs */
    }
  }, []);

  useEffect(() => {
    const dismissed = localStorage.getItem(REPORT_TIPS_KEY) === "1";
    if (dismissed) setShowTips(false);
  }, []);

  useEffect(() => {
    localStorage.setItem(
      REPORT_PREFS_KEY,
      JSON.stringify({
        entityFilter,
        entitySearch,
        entitySortKey,
        entitySortDir,
        fileSearch,
        fileSortKey,
        fileSortDir,
        improvementRiskFilter,
      })
    );
  }, [
    entityFilter,
    entitySearch,
    entitySortKey,
    entitySortDir,
    fileSearch,
    fileSortKey,
    fileSortDir,
    improvementRiskFilter,
  ]);

  useEffect(() => {
    const onShortcut = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const tag = target?.tagName?.toLowerCase();
      const inEditable =
        tag === "input" || tag === "textarea" || target?.isContentEditable;
      if (inEditable || e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key !== "/") return;
      e.preventDefault();
      if (tab === "files") {
        fileSearchRef.current?.focus();
      } else {
        entitySearchRef.current?.focus();
        if (tab !== "entities") setActiveTab("entities");
      }
    };
    window.addEventListener("keydown", onShortcut);
    return () => window.removeEventListener("keydown", onShortcut);
  }, [tab]);

  const setActiveTab = (next: Tab) => {
    setTab(next);
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set("tab", next);
    setSearchParams(nextParams, { replace: true });
  };

  const filteredEntities = useMemo(() => {
    const base =
      entityFilter === "all"
        ? [...entities]
        : entities.filter((e) => e.entity_type === entityFilter);
    const searched = base.filter((e) =>
      matchesQuery(
        `${e.qualified_name} ${e.file_path} ${e.improvement_areas.join(" ")} ${e.improvement_areas_business.join(" ")}`,
        entitySearch
      )
    );
    searched.sort((a, b) => compareEntityRows(a, b, entitySortKey, entitySortDir));
    return searched;
  }, [entities, entityFilter, entitySearch, entitySortDir, entitySortKey]);

  const filteredFiles = useMemo(() => {
    const searched = report.files.filter((f) =>
      matchesQuery(`${f.path} ${f.language} ${f.business_note}`, fileSearch)
    );
    searched.sort((a, b) => compareFileRows(a, b, fileSortKey, fileSortDir));
    return searched;
  }, [fileSearch, fileSortDir, fileSortKey, report.files]);

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
    { id: "engineering", label: "Engineering Report", icon: Code2 },
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
      <div className="glass-card flex flex-wrap items-center justify-between gap-6 p-4 sm:p-6">
        <div className="flex items-center gap-4 sm:gap-6">
          <OmegaGauge value={report.omega_index} />
          <div>
            <h2 className="font-display text-2xl font-bold text-white">
              {report.repo_display}
            </h2>
            <p className="mt-1 text-sm text-omega-muted">{report.analyzed_at}</p>
            <div className="mt-3 flex items-center gap-3">
              <GradeBadge grade={report.quality_grade} />
              <p className="hidden max-w-xs text-xs text-omega-muted sm:block">
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
        {runId ? (
          <div className="flex flex-wrap items-center gap-2">
            <RerunButton
              runId={runId}
              label="Re-run analysis"
              className="btn-primary py-2 text-sm"
            />
            {(["html", "pdf", "json", "csv", "entities", "implementations", "developer", "business", "technical"] as const).map((k) => (
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
        ) : (
          <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/5 px-3 py-2 text-xs text-cyan-300">
            Playground mode: in-memory analysis, no export files.
          </div>
        )}
      </div>

      <div className="flex flex-wrap gap-2 border-b border-omega-border pb-2">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => setActiveTab(id)}
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

      {showTips && (
        <div className="glass-card flex flex-wrap items-start justify-between gap-3 p-3">
          <p className="text-xs text-omega-muted">
            Tip: press <span className="font-mono text-cyan-300">/</span> to jump to search
            (symbols/files), and use the sortable table headers to prioritize review quickly.
          </p>
          <button
            type="button"
            className="btn-ghost px-2 py-1 text-xs"
            onClick={() => {
              setShowTips(false);
              localStorage.setItem(REPORT_TIPS_KEY, "1");
            }}
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {tab === "engineering" && (
        <div className="space-y-6">
          <div className="glass-card p-6">
            <h3 className="font-display text-xl font-semibold text-white">
              Engineering Report
            </h3>
            <p className="mt-2 text-sm text-omega-muted">
              Clean engineering snapshot with required outputs first, details second.
            </p>
          </div>

          <div className="glass-card p-6">
            <h4 className="font-display text-lg font-semibold text-white">
              Required Engineering Outputs
            </h4>
            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
              {scorecard ? (
                [
                  ["1. Code Quality Score", scorecard.code_quality],
                  ["2. Security Score", scorecard.security],
                  ["3. Performance Score", scorecard.performance],
                  ["4. Architecture Score", scorecard.architecture],
                  ["5. Technical Debt Score", scorecard.technical_debt],
                ].map(([label, value]) => (
                  <div key={String(label)} className="rounded-xl border border-omega-border bg-omega-bg/60 p-3">
                    <p className="text-xs text-omega-muted">{label}</p>
                    <p className="font-display text-xl font-bold text-white">{value}</p>
                  </div>
                ))
              ) : (
                <div className="rounded-xl border border-omega-border bg-omega-bg/60 p-3 text-sm text-omega-muted">
                  Scores unavailable for this report.
                </div>
              )}
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-3 text-sm">
              <span className="text-omega-muted">6. PDF Report:</span>
              {runId ? (
                <a
                  href={exportUrl(runId, "pdf")}
                  target="_blank"
                  rel="noreferrer"
                  className="btn-primary px-3 py-1.5 text-xs"
                >
                  <Download className="h-3.5 w-3.5" />
                  Open PDF Report
                </a>
              ) : (
                <span className="text-xs text-omega-muted">Not available in playground mode</span>
              )}
              <span className="text-omega-muted">
                7. Suggested Refactoring: {refactorSuggestions.length} item(s)
              </span>
            </div>
          </div>

          {refactorSuggestions.length > 0 && (
            <div className="glass-card p-6">
              <h4 className="font-display text-lg font-semibold text-white">
                Suggested Refactoring for Omega
              </h4>
              <ul className="mt-3 space-y-2 text-sm text-slate-300">
                {refactorSuggestions.slice(0, 12).map((item, idx) => (
                  <li key={`${idx}-${item}`} className="flex gap-2">
                    <span className="text-cyan-500">{idx + 1}.</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {plan.length > 0 && (
            <div className="glass-card p-6">
              <h4 className="font-display text-lg font-semibold text-white">
                Refactoring Code Format (from Improvements)
              </h4>
              <p className="mt-2 text-sm text-omega-muted">
                Same implementation-style code blocks as the Improvements tab, shown here for engineering execution.
              </p>
              <div className="mt-4 space-y-6">
                {plan.slice(0, 3).map((item) => (
                  <div
                    key={`eng-plan-${item.qualified_name}-${item.lines}`}
                    className="rounded-xl border border-omega-border bg-omega-bg/40 p-4"
                  >
                    <div className="mb-3">
                      <p className="font-mono text-xs text-white">{item.qualified_name}</p>
                      <p className="text-xs text-omega-muted">
                        {item.file_path} · lines {item.lines} · Ω {item.omega_local}
                      </p>
                    </div>
                    <ImplementationBlocks
                      diffs={item.implementation_diffs}
                      blocks={item.implementation_plan || []}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          <details className="glass-card p-6">
            <summary className="cursor-pointer font-display text-lg font-semibold text-white">
              Engineering Details (expand)
            </summary>
            <div className="mt-4 grid gap-6 lg:grid-cols-2">
              <div>
                <h5 className="text-sm font-semibold text-white">Top Risk Files</h5>
                <ul className="mt-2 space-y-2 text-sm text-slate-300">
                  {report.files.slice(0, 10).map((f) => (
                    <li key={f.path} className="flex items-start justify-between gap-2">
                      <span className="min-w-0 truncate font-mono text-xs">{f.path}</span>
                      <span className="shrink-0 font-semibold text-cyan-300">Ω {f.omega_local}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h5 className="text-sm font-semibold text-white">High-Risk Symbols</h5>
                <ul className="mt-2 space-y-2 text-sm text-slate-300">
                  {entities
                    .filter((e) => e.risk_band === "CRITICAL" || e.risk_band === "HIGH")
                    .slice(0, 10)
                    .map((e) => (
                      <li key={`${e.qualified_name}-${e.line_start}`} className="space-y-1">
                        <p className="font-mono text-xs text-white">{e.qualified_name}</p>
                        <p className="text-xs text-omega-muted">
                          {e.file_path}:{e.line_start} · Ω {e.omega_local} · {e.risk_band}
                        </p>
                      </li>
                    ))}
                </ul>
              </div>
            </div>
            <div className="mt-6">
              <h5 className="text-sm font-semibold text-white">Engineering Recommendations</h5>
              <ul className="mt-2 space-y-2 text-sm text-slate-300">
                {(report.recommendations_technical || []).slice(0, 12).map((item, idx) => (
                  <li key={`${idx}-${item}`} className="flex gap-2">
                    <span className="text-cyan-500">•</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </details>
        </div>
      )}

      {tab === "overview" && (
        <div className="grid gap-6 lg:grid-cols-2">
          {scorecard && (
            <div className="glass-card col-span-full p-4 sm:p-6 lg:col-span-2">
              <h3 className="font-display font-semibold text-white">
                Omega Output Scores
              </h3>
              <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
                {[
                  ["Code Quality", scorecard.code_quality],
                  ["Security", scorecard.security],
                  ["Performance", scorecard.performance],
                  ["Architecture", scorecard.architecture],
                  ["Technical Debt", scorecard.technical_debt],
                ].map(([label, value]) => (
                  <div key={String(label)} className="rounded-xl bg-omega-bg/60 p-3">
                    <p className="text-xs text-omega-muted">{label} Score</p>
                    <p className="font-display text-xl font-bold text-white">{value}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
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
          <div className="glass-card col-span-full p-4 sm:p-6 lg:col-span-2">
            <h3 className="font-display font-semibold text-white">
              Top modules by Ω (risk)
            </h3>
            <div className="mt-4 h-56 sm:h-64">
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
          <div className="glass-card grid grid-cols-2 gap-4 p-4 sm:grid-cols-3 sm:p-6">
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
                onClick={() => setActiveTab("dimensions")}
                className="text-sm font-medium text-cyan-400 hover:underline"
              >
                View full {dims.length}-dimension repo profile →
              </button>
            </div>
          )}
          {summary.total > 0 && (
            <div className="glass-card col-span-full p-4 sm:p-6 lg:col-span-2">
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
          {refactorSuggestions.length > 0 && (
            <div className="glass-card col-span-full p-4 sm:p-6 lg:col-span-2">
              <h3 className="font-display font-semibold text-white">
                Suggested Refactoring for Omega
              </h3>
              <ul className="mt-3 space-y-2 text-sm text-slate-300">
                {refactorSuggestions.map((item, idx) => (
                  <li key={`${idx}-${item}`} className="flex gap-2">
                    <span className="text-cyan-500">•</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
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
            <div className="flex items-center gap-3">
              <div className="relative">
                <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-omega-muted" />
                <input
                  ref={entitySearchRef}
                  type="search"
                  placeholder="Search symbols"
                  value={entitySearch}
                  onChange={(e) => setEntitySearch(e.target.value)}
                  className="input-field w-52 py-1.5 pl-8 text-xs"
                />
              </div>
              <p className="text-xs text-omega-muted">
                Showing {filteredEntities.length} symbols
              </p>
            </div>
          </div>
          <div className="glass-card h-44 p-3 sm:h-48 sm:p-4">
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
              <div className="overflow-x-auto">
                <table className="min-w-[760px] w-full text-left text-sm">
                <thead className="sticky top-0 bg-omega-card text-xs uppercase text-omega-muted">
                  <tr>
                    <th className="px-4 py-3">Type</th>
                    <SortableHeader
                      label="Symbol"
                      active={entitySortKey === "symbol"}
                      dir={entitySortDir}
                      onClick={() => {
                        if (entitySortKey === "symbol") {
                          setEntitySortDir((d) => toggleSortDir(d));
                        } else {
                          setEntitySortKey("symbol");
                          setEntitySortDir("asc");
                        }
                      }}
                    />
                    <th className="px-4 py-3">Location</th>
                    <SortableHeader
                      label="Ω"
                      active={entitySortKey === "omega"}
                      dir={entitySortDir}
                      onClick={() => {
                        if (entitySortKey === "omega") {
                          setEntitySortDir((d) => toggleSortDir(d));
                        } else {
                          setEntitySortKey("omega");
                          setEntitySortDir("desc");
                        }
                      }}
                    />
                    <SortableHeader
                      label="Cyc"
                      active={entitySortKey === "cyclomatic"}
                      dir={entitySortDir}
                      onClick={() => {
                        if (entitySortKey === "cyclomatic") {
                          setEntitySortDir((d) => toggleSortDir(d));
                        } else {
                          setEntitySortKey("cyclomatic");
                          setEntitySortDir("desc");
                        }
                      }}
                    />
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
        </div>
      )}

      {tab === "business" && (
        <div className="glass-card space-y-8 p-8">
          {scorecard && (
            <div>
              <h3 className="font-display text-lg font-semibold text-white">
                Omega Output Scores
              </h3>
              <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
                {[
                  ["Code Quality", scorecard.code_quality],
                  ["Security", scorecard.security],
                  ["Performance", scorecard.performance],
                  ["Architecture", scorecard.architecture],
                  ["Technical Debt", scorecard.technical_debt],
                ].map(([label, value]) => (
                  <div key={String(label)} className="rounded-xl bg-omega-bg/60 p-3">
                    <p className="text-xs text-omega-muted">{label} Score</p>
                    <p className="font-display text-xl font-bold text-white">{value}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
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
          {refactorSuggestions.length > 0 && (
            <div>
              <h3 className="font-display text-lg font-semibold text-white">
                Suggested Refactoring for Omega
              </h3>
              <ul className="mt-3 space-y-2 text-sm text-slate-300">
                {refactorSuggestions.map((item, idx) => (
                  <li key={`${idx}-${item}`} className="flex gap-2">
                    <span className="text-cyan-500">•</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {tab === "technical" && (
        <div className="glass-card space-y-8 p-8">
          {scorecard && (
            <div>
              <h3 className="font-display text-lg font-semibold text-white">
                Omega Output Scores
              </h3>
              <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
                {[
                  ["Code Quality", scorecard.code_quality],
                  ["Security", scorecard.security],
                  ["Performance", scorecard.performance],
                  ["Architecture", scorecard.architecture],
                  ["Technical Debt", scorecard.technical_debt],
                ].map(([label, value]) => (
                  <div key={String(label)} className="rounded-xl bg-omega-bg/60 p-3">
                    <p className="text-xs text-omega-muted">{label} Score</p>
                    <p className="font-display text-xl font-bold text-white">{value}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
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
          {refactorSuggestions.length > 0 && (
            <div>
              <h3 className="font-display text-lg font-semibold text-white">
                Suggested Refactoring for Omega
              </h3>
              <ul className="mt-3 space-y-2 text-sm text-slate-300">
                {refactorSuggestions.map((item, idx) => (
                  <li key={`${idx}-${item}`} className="flex gap-2">
                    <span className="text-cyan-500">•</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {tab === "files" && (
        <div className="space-y-4">
          <div className="glass-card flex flex-wrap items-center justify-between gap-3 p-4">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-omega-muted" />
              <input
                ref={fileSearchRef}
                type="search"
                placeholder="Search files"
                value={fileSearch}
                onChange={(e) => setFileSearch(e.target.value)}
                className="input-field w-64 py-2 pl-9 text-sm"
              />
            </div>
            <p className="text-xs text-omega-muted">Showing {filteredFiles.length} files</p>
          </div>
          <div className="glass-card overflow-hidden">
            <div className="max-h-[600px] overflow-auto">
              <div className="overflow-x-auto">
                <table className="min-w-[760px] w-full text-left text-sm">
                <thead className="sticky top-0 bg-omega-card text-xs uppercase text-omega-muted">
                  <tr>
                    <SortableHeader
                      label="File"
                      active={fileSortKey === "file"}
                      dir={fileSortDir}
                      onClick={() => {
                        if (fileSortKey === "file") {
                          setFileSortDir((d) => toggleSortDir(d));
                        } else {
                          setFileSortKey("file");
                          setFileSortDir("asc");
                        }
                      }}
                    />
                    <SortableHeader
                      label="Lang"
                      active={fileSortKey === "language"}
                      dir={fileSortDir}
                      onClick={() => {
                        if (fileSortKey === "language") {
                          setFileSortDir((d) => toggleSortDir(d));
                        } else {
                          setFileSortKey("language");
                          setFileSortDir("asc");
                        }
                      }}
                    />
                    <SortableHeader
                      label="Ω"
                      active={fileSortKey === "omega"}
                      dir={fileSortDir}
                      onClick={() => {
                        if (fileSortKey === "omega") {
                          setFileSortDir((d) => toggleSortDir(d));
                        } else {
                          setFileSortKey("omega");
                          setFileSortDir("desc");
                        }
                      }}
                    />
                    <th className="px-4 py-3">Risk</th>
                    <th className="px-4 py-3 hidden lg:table-cell">Business note</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredFiles.map((f) => (
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

function compareEntityRows(
  a: EntityMetric,
  b: EntityMetric,
  key: EntitySortKey,
  dir: SortDir
): number {
  if (key === "symbol") return compareStrings(a.qualified_name, b.qualified_name, dir);
  if (key === "omega") return compareNumbers(a.omega_local, b.omega_local, dir);
  return compareNumbers(a.cyclomatic, b.cyclomatic, dir);
}

function compareFileRows(
  a: FileMetric,
  b: FileMetric,
  key: FileSortKey,
  dir: SortDir
): number {
  if (key === "file") return compareStrings(a.path, b.path, dir);
  if (key === "language") return compareStrings(a.language, b.language, dir);
  return compareNumbers(a.omega_local, b.omega_local, dir);
}
