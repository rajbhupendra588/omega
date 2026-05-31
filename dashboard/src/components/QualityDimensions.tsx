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

export default function QualityDimensions({
  dimensions,
  repoDisplay,
}: {
  dimensions: RepoDimension[];
  repoDisplay: string;
}) {
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

  const radarData = dimensions.map((d) => ({
    dimension: d.name.split(" ")[0],
    fullName: d.name,
    score: d.score,
    band: d.band,
  }));

  return (
    <div className="space-y-8">
      <div>
        <h3 className="font-display text-lg font-semibold text-white">
          Multi-dimensional profile — {repoDisplay}
        </h3>
        <p className="mt-2 text-sm text-omega-muted">
          Each dimension is computed from this repository&apos;s files and symbols.
          Evidence lists real paths and qualified names — not generic guidance.
        </p>
      </div>

      <div className="glass-card p-6">
        <h4 className="mb-4 text-sm font-medium text-omega-muted">
          Stress radar (higher = more pressure in this repo)
        </h4>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart data={radarData}>
              <PolarGrid stroke="#1e2d4a" />
              <PolarAngleAxis dataKey="dimension" tick={{ fill: "#8b9cb3", fontSize: 10 }} />
              <PolarRadiusAxis domain={[0, 100]} tick={{ fill: "#8b9cb3", fontSize: 9 }} />
              <Radar
                name="Stress"
                dataKey="score"
                stroke="#3b82f6"
                fill="#3b82f6"
                fillOpacity={0.35}
              />
              <Tooltip
                contentStyle={{
                  background: "#0f1629",
                  border: "1px solid #1e2d4a",
                  borderRadius: 8,
                }}
                formatter={(v: number) => [`${v}`, "Score"]}
                labelFormatter={(_, p) =>
                  (p?.[0]?.payload as { fullName?: string })?.fullName ?? ""
                }
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid min-w-0 gap-4 lg:grid-cols-2">
        {dimensions.map((d) => (
          <div
            key={d.id}
            className="glass-card min-w-0 max-w-full overflow-hidden border-l-4 p-5"
            style={{
              borderLeftColor:
                d.band === "LOW"
                  ? "#22c55e"
                  : d.band === "MEDIUM"
                    ? "#eab308"
                    : d.band === "HIGH"
                      ? "#f97316"
                      : "#ef4444",
            }}
          >
            <div className="flex flex-wrap items-center gap-2">
              <h4 className="font-display font-semibold text-white">{d.name}</h4>
              <RiskPill band={d.band} />
              <span className="ml-auto font-mono text-lg font-bold text-cyan-400">
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
        ))}
      </div>
    </div>
  );
}
