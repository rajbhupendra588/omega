import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import type { SortDir } from "../lib/tableUtils";

export default function SortableHeader({
  label,
  active,
  dir,
  onClick,
  className = "",
}: {
  label: string;
  active: boolean;
  dir: SortDir;
  onClick: () => void;
  className?: string;
}) {
  const Icon = active ? (dir === "asc" ? ArrowUp : ArrowDown) : ArrowUpDown;
  return (
    <th className={`px-4 py-3 ${className}`}>
      <button
        type="button"
        onClick={onClick}
        className="inline-flex items-center gap-1 text-xs uppercase text-omega-muted transition hover:text-white"
      >
        {label}
        <Icon className={`h-3 w-3 ${active ? "text-cyan-400" : "opacity-40"}`} />
      </button>
    </th>
  );
}
