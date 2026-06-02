import { useCallback, useMemo, useRef, useState } from "react";
import { ArrowUp, Radar as RadarIcon, X } from "lucide-react";
import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import type { RepoDimension } from "../types";
import RiskPill from "./RiskPill";

const FAMILY_LABELS: Record<string, string> = {
  all: "All families",
  field: "Code field",
  business: "Business",
  ecosystem: "Ecosystem",
  temporal: "Temporal",
  ai_era: "AI era",
  ml_dl: "ML & deep learning",
};

const DIM_SECTION_ID = (id: string) => `omega-dim-${id}`;
const RADAR_TOP_ID = "omega-dim-radar-top";

type RadarPoint = {
  id: string;
  shortLabel: string;
  fullName: string;
  score: number;
  band: string;
};

function shortLabel(name: string, max = 11): string {
  if (name.length <= max) return name;
  const words = name.split(/\s+/);
  if (words[0].length <= max) return words[0];
  return `${name.slice(0, max - 1)}…`;
}

function ClickablePolarTick({
  x,
  y,
  payload,
  points,
  onSelect,
  activeId,
}: {
  x: number;
  y: number;
  payload: { value: string };
  points: RadarPoint[];
  onSelect: (id: string) => void;
  activeId: string | null;
}) {
  const item = points.find((p) => p.id === payload.value);
  const label = item?.shortLabel ?? payload.value;
  const isActive = activeId === payload.value;

  return (
    <g transform={`translate(${x},${y})`}>
      <text
        role="button"
        tabIndex={0}
        textAnchor="middle"
        dominantBaseline="central"
        fill={isActive ? "#22d3ee" : "#8b9cb3"}
        fontSize={9}
        fontWeight={isActive ? 600 : 400}
        style={{ cursor: "pointer" }}
        className="select-none transition-colors hover:fill-cyan-300"
        onClick={(e) => {
          e.stopPropagation();
          onSelect(payload.value);
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onSelect(payload.value);
          }
        }}
      >
        {label}
      </text>
    </g>
  );
}

function ScrollNavButtons({
  activeName,
  onBackToRadar,
  onTop,
  onClear,
}: {
  activeName: string;
  onBackToRadar: () => void;
  onTop: () => void;
  onClear: () => void;
}) {
  return (
    <div
      className="fixed bottom-6 right-6 z-50 flex max-w-[min(100vw-2rem,20rem)] flex-col gap-2"
      role="navigation"
      aria-label="Dimension navigation"
    >
      <div className="rounded-lg border border-cyan-500/40 bg-[#0f1629]/95 px-3 py-2 text-xs text-cyan-100 shadow-xl backdrop-blur-sm">
        <p className="font-medium text-cyan-300">Viewing dimension</p>
        <p className="mt-0.5 truncate font-semibold text-white">{activeName}</p>
      </div>
      <button
        type="button"
        onClick={onBackToRadar}
        className="inline-flex items-center justify-center gap-2 rounded-lg border border-cyan-500/50 bg-cyan-600 px-4 py-2.5 text-sm font-medium text-white shadow-lg shadow-cyan-900/40 transition hover:bg-cyan-500"
      >
        <RadarIcon className="h-4 w-4" />
        Back to radar
      </button>
      <button
        type="button"
        onClick={onTop}
        className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-600 bg-slate-800 px-4 py-2.5 text-sm font-medium text-slate-200 shadow-lg transition hover:bg-slate-700"
      >
        <ArrowUp className="h-4 w-4" />
        Top of page
      </button>
      <button
        type="button"
        onClick={onClear}
        className="inline-flex items-center justify-center gap-1 rounded-lg px-2 py-1 text-xs text-slate-500 hover:text-slate-300"
      >
        <X className="h-3 w-3" />
        Clear highlight
      </button>
    </div>
  );
}

export default function QualityDimensions({
  dimensions,
  repoDisplay,
}: {
  dimensions: RepoDimension[];
  repoDisplay: string;
}) {
  const [family, setFamily] = useState<string>("all");
  const [activeDimId, setActiveDimId] = useState<string | null>(null);
  const radarRef = useRef<HTMLDivElement>(null);
  const headerRef = useRef<HTMLDivElement>(null);

  const filtered = useMemo(() => {
    if (family === "all") return dimensions;
    return dimensions.filter((d) => (d.family || "field") === family);
  }, [dimensions, family]);

  const activeDimension = useMemo(
    () => filtered.find((d) => d.id === activeDimId) ?? dimensions.find((d) => d.id === activeDimId),
    [filtered, dimensions, activeDimId],
  );

  const families = useMemo(() => {
    const set = new Set(dimensions.map((d) => d.family || "field"));
    return ["all", ...Array.from(set).sort()];
  }, [dimensions]);

  const radarData: RadarPoint[] = useMemo(
    () =>
      filtered.map((d) => ({
        id: d.id,
        shortLabel: shortLabel(d.name),
        fullName: d.name,
        score: d.score,
        band: d.band,
      })),
    [filtered],
  );

  const scrollToRadar = useCallback(() => {
    const el = radarRef.current ?? document.getElementById(RADAR_TOP_ID);
    el?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  const scrollToPageTop = useCallback(() => {
    headerRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  const clearHighlight = useCallback(() => {
    setActiveDimId(null);
  }, []);

  const scrollToDimension = useCallback((id: string) => {
    setActiveDimId(id);
    requestAnimationFrame(() => {
      const el = document.getElementById(DIM_SECTION_ID(id));
      el?.scrollIntoView({ behavior: "smooth", block: "center" });
    });
  }, []);

  const handleRadarClick = useCallback(
    (state: { activePayload?: Array<{ payload?: RadarPoint }> } | null) => {
      const id = state?.activePayload?.[0]?.payload?.id;
      if (id) scrollToDimension(id);
    },
    [scrollToDimension],
  );

  if (!dimensions?.length) {
    return (
      <div className="space-y-3 text-sm text-omega-muted">
        <p>No dimension profile for this run yet.</p>
        <p>
          This usually means the report was saved before dimensions were enabled, or
          the analysis found no source files. Try <strong>Re-run analysis</strong> on
          this repository, or refresh the page (the API will backfill dimensions from
          saved file metrics when possible).
        </p>
      </div>
    );
  }

  return (
    <div className="relative space-y-8">
      {activeDimId && activeDimension ? (
        <ScrollNavButtons
          activeName={activeDimension.name}
          onBackToRadar={scrollToRadar}
          onTop={scrollToPageTop}
          onClear={clearHighlight}
        />
      ) : null}

      <div ref={headerRef} className="scroll-mt-20">
        <h3 className="font-display text-lg font-semibold text-white">
          Multi-dimensional profile — {repoDisplay}
        </h3>
        <p className="mt-2 text-sm text-omega-muted">
          {dimensions.length} applicable dimensions for this repository (contextual lenses only).
          Letter grade <strong className="text-slate-300">A–F</strong> comes from the{" "}
          <strong className="text-slate-300">Ω index</strong> on source files — not from dimension
          scores. Families such as ecosystem, AI-era, ML/DL, and temporal appear only when this
          service qualifies.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          {families.map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => {
                setFamily(f);
                setActiveDimId(null);
              }}
              className={`rounded px-2 py-1 text-xs ${
                family === f ? "bg-cyan-600 text-white" : "bg-slate-800 text-slate-400"
              }`}
            >
              {FAMILY_LABELS[f] ?? f}
              {f !== "all"
                ? ` (${dimensions.filter((d) => (d.family || "field") === f).length})`
                : ` (${dimensions.length})`}
            </button>
          ))}
        </div>
      </div>

      <div
        id={RADAR_TOP_ID}
        ref={radarRef}
        className="glass-card scroll-mt-24 p-6"
      >
        <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
          <div>
            <h4 className="text-sm font-medium text-omega-muted">
              Stress radar (higher = more pressure in this repo)
            </h4>
            <p className="mt-1 text-xs text-cyan-400/90">
              Click a label or point — the matching section below will be highlighted
            </p>
          </div>
          <button
            type="button"
            onClick={scrollToPageTop}
            className="inline-flex items-center gap-1 rounded-md border border-slate-700 bg-slate-800/80 px-2.5 py-1.5 text-xs text-slate-300 hover:border-slate-600 hover:text-white"
          >
            <ArrowUp className="h-3.5 w-3.5" />
            Top
          </button>
        </div>
        <div className="h-[min(28rem,70vh)] min-h-[20rem]">
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart
              data={radarData}
              cx="50%"
              cy="50%"
              outerRadius="72%"
              onClick={handleRadarClick}
              style={{ cursor: "pointer" }}
            >
              <PolarGrid stroke="#1e2d4a" />
              <PolarAngleAxis
                dataKey="id"
                tick={(props) => (
                  <ClickablePolarTick
                    {...props}
                    points={radarData}
                    onSelect={scrollToDimension}
                    activeId={activeDimId}
                  />
                )}
              />
              <PolarRadiusAxis domain={[0, 100]} tick={{ fill: "#8b9cb3", fontSize: 9 }} />
              <Radar
                name="Stress"
                dataKey="score"
                stroke="#3b82f6"
                fill="#3b82f6"
                fillOpacity={0.35}
                activeDot={{
                  r: 6,
                  fill: "#22d3ee",
                  stroke: "#0e7490",
                  strokeWidth: 2,
                  cursor: "pointer",
                }}
                dot={{ r: 3, fill: "#3b82f6", cursor: "pointer" }}
              />
              <Tooltip
                contentStyle={{
                  background: "#0f1629",
                  border: "1px solid #1e2d4a",
                  borderRadius: 8,
                }}
                formatter={(v: number) => [`${v}`, "Score"]}
                labelFormatter={(_, p) => {
                  const row = p?.[0]?.payload as RadarPoint | undefined;
                  return row?.fullName ?? "";
                }}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>
        <div className="mt-4 flex flex-wrap gap-2 border-t border-omega-border pt-4">
          {radarData.map((r) => (
            <button
              key={r.id}
              type="button"
              onClick={() => scrollToDimension(r.id)}
              className={`rounded-full border px-2.5 py-1 text-[11px] transition-colors ${
                activeDimId === r.id
                  ? "border-cyan-400 bg-cyan-500/25 text-cyan-100 ring-1 ring-cyan-400/60"
                  : "border-slate-700 bg-slate-800/80 text-slate-400 hover:border-cyan-600/50 hover:text-cyan-300"
              }`}
              title={`${r.fullName} — score ${r.score}`}
            >
              {r.shortLabel}
              <span className="ml-1 font-mono text-[10px] opacity-70">{r.score}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="grid min-w-0 gap-4 lg:grid-cols-2">
        {filtered.map((d) => {
          const isSelected = activeDimId === d.id;
          return (
            <div
              key={d.id}
              id={DIM_SECTION_ID(d.id)}
              className={`glass-card min-w-0 max-w-full scroll-mt-28 overflow-hidden border-l-4 p-5 transition-all duration-300 ${
                isSelected
                  ? "z-[1] scale-[1.01] border-l-cyan-400 bg-cyan-500/[0.08] shadow-[0_0_0_2px_rgba(34,211,238,0.55),0_12px_40px_rgba(34,211,238,0.18)] ring-2 ring-cyan-400/70"
                  : activeDimId
                    ? "opacity-55 hover:opacity-80"
                    : ""
              }`}
              style={
                isSelected
                  ? undefined
                  : {
                      borderLeftColor:
                        d.band === "LOW"
                          ? "#22c55e"
                          : d.band === "MEDIUM"
                            ? "#eab308"
                            : d.band === "HIGH"
                              ? "#f97316"
                              : "#ef4444",
                    }
              }
            >
              {isSelected ? (
                <div className="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-cyan-500/40 bg-cyan-500/15 px-3 py-2.5">
                  <div className="flex items-center gap-2 text-sm">
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-cyan-500 text-xs font-bold text-[#0a0f1a]">
                      ✓
                    </span>
                    <span className="font-medium text-cyan-200">
                      Selected — review this dimension
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={scrollToRadar}
                      className="inline-flex items-center gap-1 rounded-md bg-cyan-600/90 px-2.5 py-1 text-xs font-medium text-white hover:bg-cyan-500"
                    >
                      <RadarIcon className="h-3 w-3" />
                      Radar
                    </button>
                    <button
                      type="button"
                      onClick={scrollToPageTop}
                      className="inline-flex items-center gap-1 rounded-md border border-slate-600 bg-slate-800 px-2.5 py-1 text-xs text-slate-200 hover:bg-slate-700"
                    >
                      <ArrowUp className="h-3 w-3" />
                      Top
                    </button>
                  </div>
                </div>
              ) : null}

              <div className="flex flex-wrap items-center gap-2">
                <h4
                  className={`font-display font-semibold ${isSelected ? "text-cyan-50" : "text-white"}`}
                >
                  {d.name}
                </h4>
                {d.family && (
                  <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] uppercase text-slate-400">
                    {d.family}
                  </span>
                )}
                <RiskPill band={d.band} />
                <span
                  className={`ml-auto font-mono text-lg font-bold ${isSelected ? "text-cyan-300" : "text-cyan-400"}`}
                >
                  {d.score}
                </span>
              </div>
              <p className="mt-2 text-xs text-omega-muted">
                This repo: {d.repo_aggregate} {d.unit} · Ω-QFM weight {d.weight}
              </p>
              <p className="mt-3 text-sm text-slate-300">{d.summary_technical}</p>
              <p className="mt-2 text-sm text-slate-400">{d.summary_business}</p>

              {d.evidence.length > 0 && (
                <div className="mt-4">
                  <p className="text-xs font-semibold uppercase tracking-wider text-cyan-400/80">
                    Evidence in this codebase
                  </p>
                  <ul className="mt-2 space-y-1 text-xs text-slate-400">
                    {d.evidence.map((ev, i) => (
                      <li key={i} className="break-all font-mono">
                        {ev}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {d.evidence_symbols && d.evidence_symbols.length > 0 && (
                <div className="mt-3">
                  <p className="text-xs font-semibold uppercase tracking-wider text-violet-400/80">
                    Symbols
                  </p>
                  <ul className="mt-1 space-y-1 break-all text-xs font-mono text-violet-200/80">
                    {d.evidence_symbols.map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ul>
                </div>
              )}

              {d.actions_in_repo.length > 0 && (
                <div className="mt-4 border-t border-omega-border pt-3">
                  <p className="text-xs font-semibold uppercase tracking-wider text-emerald-400/80">
                    Actions in this repo
                  </p>
                  <ul className="mt-2 space-y-1 break-words text-sm text-slate-300">
                    {d.actions_in_repo.map((a, i) => (
                      <li key={i} className="flex min-w-0 gap-2">
                        <span className="text-emerald-500">→</span>
                        {a}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
