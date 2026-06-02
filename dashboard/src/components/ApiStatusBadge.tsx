import { useEffect, useState } from "react";
import { healthCheck } from "../api/client";
import { Circle, Loader2 } from "lucide-react";

export default function ApiStatusBadge() {
  const [status, setStatus] = useState<"checking" | "online" | "offline">("checking");

  useEffect(() => {
    let cancelled = false;

    const check = async () => {
      const ok = await healthCheck();
      if (!cancelled) setStatus(ok ? "online" : "offline");
    };

    check();
    const t = setInterval(check, 15000);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, []);

  if (status === "checking") {
    return (
      <span className="flex items-center gap-1.5 text-xs text-omega-muted">
        <Loader2 className="h-3 w-3 animate-spin" />
        API
      </span>
    );
  }

  return (
    <span
      className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${
        status === "online"
          ? "bg-emerald-500/10 text-emerald-400"
          : "bg-red-500/10 text-red-400"
      }`}
      title={status === "online" ? "API is reachable" : "API unreachable — start omega-ui"}
    >
      <Circle
        className={`h-2 w-2 fill-current ${status === "online" ? "text-emerald-400" : "text-red-400"}`}
      />
      API {status === "online" ? "online" : "offline"}
    </span>
  );
}
