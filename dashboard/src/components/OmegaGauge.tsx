export default function OmegaGauge({
  value,
  label = "Ω Index",
}: {
  value: number;
  label?: string;
}) {
  const pct = Math.min(100, Math.max(0, value));
  const color =
    pct < 30
      ? "#22c55e"
      : pct < 45
        ? "#84cc16"
        : pct < 60
          ? "#eab308"
          : pct < 75
            ? "#f97316"
            : "#ef4444";

  const circumference = 2 * Math.PI * 54;
  const offset = circumference - (pct / 100) * circumference;

  return (
    <div className="relative flex flex-col items-center">
      <svg width="140" height="140" className="-rotate-90">
        <circle
          cx="70"
          cy="70"
          r="54"
          fill="none"
          stroke="#1e2d4a"
          strokeWidth="10"
        />
        <circle
          cx="70"
          cy="70"
          r="54"
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-700"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-display text-3xl font-bold text-white">
          {value.toFixed(1)}
        </span>
        <span className="text-xs text-omega-muted">{label}</span>
        <span className="mt-0.5 text-[10px] text-omega-muted/80">
          lower is better
        </span>
      </div>
    </div>
  );
}
