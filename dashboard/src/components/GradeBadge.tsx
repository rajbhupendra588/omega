export default function GradeBadge({ grade }: { grade: string }) {
  const g = (grade || "—").toUpperCase();
  const cls =
    {
      A: "grade-a border-emerald-500/30 bg-emerald-500/10",
      B: "grade-b border-lime-500/30 bg-lime-500/10",
      C: "grade-c border-amber-500/30 bg-amber-500/10",
      D: "grade-d border-orange-500/30 bg-orange-500/10",
      F: "grade-f border-red-500/30 bg-red-500/10",
    }[g] || "border-omega-border bg-omega-bg text-omega-muted";

  return (
    <span
      className={`inline-flex h-14 w-14 items-center justify-center rounded-2xl border-2 font-display text-2xl font-bold ${cls}`}
    >
      {g}
    </span>
  );
}
