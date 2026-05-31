export default function RiskPill({ band }: { band: string }) {
  const key = band.toLowerCase();
  const cls =
    {
      low: "risk-low",
      medium: "risk-medium",
      high: "risk-high",
      critical: "risk-critical",
    }[key] || "bg-slate-500/20 text-slate-400";

  return (
    <span className={`rounded-md px-2 py-0.5 text-xs font-semibold ${cls}`}>
      {band}
    </span>
  );
}
