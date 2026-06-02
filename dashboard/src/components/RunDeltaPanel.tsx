import { useEffect, useState } from "react";
import { getRunDelta, type RunDeltaResponse } from "../api/client";
import { ArrowDown, ArrowUp, Minus, TrendingDown, TrendingUp } from "lucide-react";

type Props = {
  runId: string;
};

function DeltaChip({
  label,
  delta,
  invert = false,
}: {
  label: string;
  delta: number | null | undefined;
  invert?: boolean;
}) {
  if (delta == null) return null;
  const improved = invert ? delta < 0 : delta > 0;
  const worse = invert ? delta > 0 : delta < 0;
  const Icon = delta === 0 ? Minus : improved ? TrendingDown : worse ? TrendingUp : Minus;
  const color =
    delta === 0
      ? "text-omega-muted"
      : improved
        ? "text-emerald-400"
        : worse
          ? "text-amber-400"
          : "text-omega-muted";
  return (
    <div className="rounded-lg border border-white/10 bg-white/5 px-3 py-2">
      <div className="text-xs text-omega-muted">{label}</div>
      <div className={`mt-1 flex items-center gap-1 text-sm font-semibold ${color}`}>
        <Icon className="h-4 w-4" />
        {delta > 0 ? "+" : ""}
        {delta}
      </div>
    </div>
  );
}

export default function RunDeltaPanel({ runId }: Props) {
  const [data, setData] = useState<RunDeltaResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getRunDelta(runId)
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch(() => {
        if (!cancelled) setData({ has_baseline: false, message: "Could not load comparison." });
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [runId]);

  if (loading) {
    return (
      <div className="glass-card px-5 py-4 text-sm text-omega-muted">
        Loading comparison to previous run…
      </div>
    );
  }

  if (!data?.has_baseline || !data.delta) {
    return (
      <div className="glass-card border-dashed px-5 py-4 text-sm text-omega-muted">
        {data && !data.has_baseline
          ? data.message
          : "First run for this repository — re-run later to see deltas."}
      </div>
    );
  }

  const d = data.delta;
  const omegaImproved = d.omega_index.improved;

  return (
    <section className="glass-card space-y-4 px-5 py-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-white">Change since last run</h2>
          <p className="mt-1 text-sm text-omega-muted">
            Compared to run <span className="font-mono text-cyan-300/90">{d.baseline_run_id}</span>
            {d.baseline_analyzed_at ? ` (${d.baseline_analyzed_at})` : ""}
          </p>
        </div>
        <div
          className={`flex items-center gap-2 rounded-full px-3 py-1 text-sm font-medium ${
            omegaImproved
              ? "bg-emerald-500/15 text-emerald-300"
              : d.omega_index.delta > 0.5
                ? "bg-amber-500/15 text-amber-300"
                : "bg-white/10 text-omega-muted"
          }`}
        >
          {omegaImproved ? (
            <ArrowDown className="h-4 w-4" />
          ) : d.omega_index.delta > 0 ? (
            <ArrowUp className="h-4 w-4" />
          ) : (
            <Minus className="h-4 w-4" />
          )}
          Ω {d.omega_index.current} → was {d.omega_index.baseline}
        </div>
      </div>

      <p className="text-sm leading-relaxed text-slate-300">{d.summary}</p>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <DeltaChip label="Ω index Δ" delta={d.omega_index.delta} invert />
        <DeltaChip label="Files analyzed Δ" delta={d.file_count.delta ?? undefined} invert />
        <DeltaChip label="LOC Δ" delta={d.total_loc.delta ?? undefined} invert />
        <DeltaChip
          label="High-risk symbols Δ"
          delta={d.entity_high_risk.delta ?? undefined}
          invert
        />
      </div>

      {(d.quality_grade.current || d.quality_grade.baseline) && (
        <p className="text-sm text-omega-muted">
          Grade:{" "}
          <span className="font-semibold text-white">{d.quality_grade.baseline}</span>
          {" → "}
          <span className="font-semibold text-white">{d.quality_grade.current}</span>
          {d.quality_grade.improved === true && (
            <span className="ml-2 text-emerald-400">(improved)</span>
          )}
          {d.quality_grade.improved === false && (
            <span className="ml-2 text-amber-400">(declined)</span>
          )}
        </p>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        {d.files_improved.length > 0 && (
          <div>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-emerald-400/90">
              Files improved
            </h3>
            <ul className="space-y-1 text-sm">
              {d.files_improved.slice(0, 8).map((f) => (
                <li key={f.path} className="font-mono text-slate-300">
                  {f.path}{" "}
                  <span className="text-emerald-400">({f.omega_delta})</span>
                </li>
              ))}
            </ul>
          </div>
        )}
        {d.files_regressed.length > 0 && (
          <div>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-amber-400/90">
              Files regressed
            </h3>
            <ul className="space-y-1 text-sm">
              {d.files_regressed.slice(0, 8).map((f) => (
                <li key={f.path} className="font-mono text-slate-300">
                  {f.path}{" "}
                  <span className="text-amber-400">(+{f.omega_delta})</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  );
}
