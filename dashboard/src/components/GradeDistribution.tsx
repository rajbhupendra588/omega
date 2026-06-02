import type { RepoSummary } from "../types";

const GRADE_ORDER = ["A", "B", "C", "D", "F"] as const;
const GRADE_COLORS: Record<string, string> = {
  A: "bg-emerald-500",
  B: "bg-lime-500",
  C: "bg-yellow-500",
  D: "bg-orange-500",
  F: "bg-red-500",
};

export default function GradeDistribution({ repos }: { repos: RepoSummary[] }) {
  const graded = repos.filter((r) => r.latest_quality_grade);
  if (graded.length === 0) return null;

  const counts = GRADE_ORDER.map((g) => ({
    grade: g,
    count: graded.filter((r) => r.latest_quality_grade === g).length,
  }));
  const max = Math.max(...counts.map((c) => c.count), 1);

  return (
    <div className="glass-card p-5">
      <p className="text-xs font-medium uppercase tracking-wider text-omega-muted">
        Grade distribution
      </p>
      <p className="mt-1 text-xs text-omega-muted">
        Latest run per repository ({graded.length} graded)
      </p>
      <div className="mt-4 flex items-end gap-3">
        {counts.map(({ grade, count }) => (
          <div key={grade} className="flex flex-1 flex-col items-center gap-1">
            <span className="text-xs font-mono text-omega-muted">{count}</span>
            <div
              className={`w-full rounded-t-md transition-all ${GRADE_COLORS[grade]}`}
              style={{ height: `${Math.max(8, (count / max) * 64)}px`, opacity: count ? 1 : 0.2 }}
            />
            <span className="font-display text-sm font-bold text-white">{grade}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
