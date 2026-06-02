import { useState } from "react";
import { CheckCircle2, ChevronDown, ChevronUp, FileCode2, Sparkles } from "lucide-react";
import type { ImplementationDiff } from "../types";
import CodeDiffView, { InlineUnifiedDiff } from "./CodeDiffView";
import { languageFromPath } from "../lib/syntaxHighlight";
import { highlightBlock } from "../lib/syntaxHighlight";
import "highlight.js/styles/github-dark.css";

export function SimpleRefactorCard({ diff }: { diff: ImplementationDiff }) {
  const [showDetails, setShowDetails] = useState(false);
  const path = diff.location.split(":")[0];
  const lineHint = diff.location.includes(":") ? diff.location.split(":").slice(1).join(":") : "";
  const lang = languageFromPath(path, diff.language || "java");
  const summary =
    diff.simple_summary ??
    (diff.description
      ? `${diff.description.split(".")[0].trim()}.`
      : diff.title);
  const steps =
    diff.steps ||
    [
      `Open \`${path}\` in your editor.`,
      lineHint ? `Go to line ${lineHint}.` : "Find the symbol named in the title.",
      diff.before
        ? "Apply the change below: remove red lines and use green lines in the same file."
        : "Add the green lines where indicated.",
      "Run tests and commit.",
    ];

  const hasBefore = Boolean(diff.before?.trim());
  const hasAfter = Boolean(diff.after?.trim());

  return (
    <article className="rounded-2xl border border-cyan-500/20 bg-gradient-to-b from-cyan-500/5 to-transparent p-5">
      <div className="flex items-start gap-3">
        <div className="rounded-lg bg-cyan-500/20 p-2">
          <Sparkles className="h-5 w-5 text-cyan-400" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-cyan-400">
            Recommended fix
          </p>
          <h4 className="mt-1 font-display text-base font-semibold text-white">{diff.title}</h4>
          <p className="mt-2 text-sm leading-relaxed text-slate-300">{summary}</p>
        </div>
      </div>

      <ol className="mt-5 space-y-2">
        {steps.map((step, i) => (
          <li
            key={i}
            className="flex gap-3 rounded-lg bg-black/25 px-3 py-2 text-sm text-slate-300"
          >
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-cyan-600/30 font-mono text-xs font-bold text-cyan-300">
              {i + 1}
            </span>
            <span className="pt-0.5">{step.replace(/`([^`]+)`/g, "$1")}</span>
          </li>
        ))}
      </ol>

      <div className="mt-4 flex flex-wrap items-center gap-2 rounded-lg border border-[#30363d] bg-[#0d1117] px-4 py-3">
        <FileCode2 className="h-4 w-4 shrink-0 text-slate-400" />
        <span className="truncate font-mono text-sm text-white">{path}</span>
        {lineHint ? (
          <span className="rounded bg-slate-800 px-2 py-0.5 font-mono text-xs text-slate-400">
            lines {lineHint}
          </span>
        ) : null}
        <span className="ml-auto rounded bg-slate-800 px-2 py-0.5 text-[10px] uppercase text-slate-500">
          {lang}
        </span>
      </div>

      {/* Single code block: red removals + green additions (Cursor-style) */}
      {hasBefore && hasAfter ? (
        <InlineUnifiedDiff diff={diff} lang={lang} className="mt-4" />
      ) : (
        <CodeDiffView diff={diff} preferInline />
      )}

      {diff.business_outcome ? (
        <div className="mt-4 flex gap-2 rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-4 py-3 text-sm text-emerald-100/90">
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
          <p>
            <span className="font-medium text-emerald-400">Why this helps: </span>
            {diff.business_outcome}
          </p>
        </div>
      ) : null}

      {diff.description && diff.description !== summary ? (
        <button
          type="button"
          onClick={() => setShowDetails(!showDetails)}
          className="mt-4 flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300"
        >
          {showDetails ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          {showDetails ? "Hide technical details" : "Technical details for engineers"}
        </button>
      ) : null}
      {showDetails && diff.description ? (
        <p className="mt-2 text-xs leading-relaxed text-slate-500">{diff.description}</p>
      ) : null}
    </article>
  );
}

/** Single block when only after exists and is one chunk */
export function SimpleRefactorCardCompact({ diff }: { diff: ImplementationDiff }) {
  const path = diff.location.split(":")[0];
  const lang = languageFromPath(path, diff.language || "text");
  const after = diff.after || "";
  if (!after.trim()) return null;

  return (
    <div
      className="overflow-hidden rounded-xl border border-[#3fb950]/30 bg-[#0d1117]"
      dangerouslySetInnerHTML={{
        __html: `<pre class="p-4 hljs" style="tab-size:4">${highlightBlock(after, lang)}</pre>`,
      }}
    />
  );
}
