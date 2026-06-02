/** End-user friendly refactor guide (not raw diff markdown). */
import { SimpleRefactorCard } from "./SimpleRefactorGuide";
import type { ImplementationDiff } from "../types";
import { normalizeImplementationDiffs } from "../lib/parseImplementationMarkdown";

export default function ImplementationBlocks({
  blocks,
  diffs,
}: {
  blocks?: string[];
  diffs?: ImplementationDiff[];
}) {
  const items = normalizeImplementationDiffs(diffs, blocks);
  if (!items.length) return null;

  return (
    <div className="mt-6 space-y-5 border-t border-omega-border pt-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wider text-cyan-400">
          How to fix it
        </p>
        <p className="mt-1 text-sm text-slate-400">
          Follow the steps below — in each fix, red lines are removed and green lines are added in the
          same file (like Cursor).
        </p>
      </div>
      <div className="space-y-6">
        {items.map((diff, i) => (
          <SimpleRefactorCard key={`${diff.location}-${i}`} diff={diff} />
        ))}
      </div>
    </div>
  );
}
