import { diffLines, isInlineDiffFriendly } from "../lib/lineDiff";
import { highlightBlock, highlightLine, languageFromPath } from "../lib/syntaxHighlight";
import "highlight.js/styles/github-dark.css";

export interface ImplementationDiff {
  title: string;
  location: string;
  description: string;
  before: string;
  after: string;
  language: string;
  business_outcome: string;
}

function fileLabel(location: string): string {
  return location.split(":")[0] || location;
}

function DiffFileHeader({ diff, lang }: { diff: ImplementationDiff; lang: string }) {
  return (
    <div className="flex items-center gap-2 border-b border-[#30363d] bg-[#161b22] px-4 py-2">
      <span className="rounded bg-[#21262d] px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide text-[#8b949e]">
        {lang}
      </span>
      <span className="truncate font-mono text-xs text-[#c9d1d9]">{fileLabel(diff.location)}</span>
      <span className="ml-auto font-mono text-[10px] text-[#6e7681]">{diff.location}</span>
    </div>
  );
}

/** Side-by-side: current file code vs suggested change (Cursor-style panels). */
function SideBySideDiff({ diff, lang }: { diff: ImplementationDiff; lang: string }) {
  const before = diff.before || "";
  const after = diff.after || "";

  return (
    <div className="mt-4 overflow-hidden rounded-xl border border-omega-border bg-[#0d1117]">
      <DiffFileHeader diff={diff} lang={lang} />
      <div className="grid md:grid-cols-2">
        <div className="border-b border-[#30363d] md:border-b-0 md:border-r">
          <p className="border-b border-[#30363d] bg-[#67060c]/25 px-4 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-[#ff7b72]">
            Current code in repo
          </p>
          <CodeBlock code={before} lang={lang} variant="removed" />
        </div>
        <div>
          <p className="border-b border-[#30363d] bg-[#033a16]/35 px-4 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-[#3fb950]">
            Suggested change
          </p>
          <CodeBlock code={after} lang={lang} variant="added" />
        </div>
      </div>
    </div>
  );
}

function CodeBlock({
  code,
  lang,
  variant,
}: {
  code: string;
  lang: string;
  variant: "removed" | "added" | "neutral";
}) {
  const lines = code.replace(/\r\n/g, "\n").split("\n");
  const tint =
    variant === "removed"
      ? "bg-[#ff818266]/10"
      : variant === "added"
        ? "bg-[#3fb95066]/12"
        : "";

  return (
    <div className={`overflow-x-auto ${tint}`}>
      <table className="w-full border-collapse font-mono text-[12px] leading-[1.45]">
        <tbody>
          {lines.map((line, i) => (
            <tr key={i} className="hover:bg-white/[0.02]">
              <td className="w-11 select-none border-r border-[#21262d] px-2 text-right align-top text-[#6e7681]">
                {i + 1}
              </td>
              <td
                className="whitespace-pre px-3 py-0 align-top text-[#e6edf3] hljs"
                dangerouslySetInnerHTML={{ __html: highlightLine(line, lang) }}
              />
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Inline diff: one block — context, red removals, green additions (Cursor-style). */
export function InlineUnifiedDiff({
  diff,
  lang,
  className = "mt-4",
}: {
  diff: ImplementationDiff;
  lang: string;
  className?: string;
}) {
  const before = diff.before || "";
  const after = diff.after || "";
  const rows = diffLines(before, after);

  if (!rows.length && !after) return null;

  return (
    <div
      className={`overflow-hidden rounded-xl border border-[#30363d] bg-[#0d1117] shadow-inner ${className}`}
    >
      <DiffFileHeader diff={diff} lang={lang} />
      <p className="border-b border-[#30363d] bg-[#161b22] px-4 py-1.5 text-[11px] text-[#8b949e]">
        <span className="text-[#ff7b72]">− removed</span>
        <span className="mx-2 text-[#484f58]">·</span>
        <span className="text-[#3fb950]">+ added</span>
        <span className="mx-2 text-[#484f58]">·</span>
        unchanged lines shown for context
      </p>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse font-mono text-[12px] leading-[1.5]">
          <tbody>
            {rows.map((row, idx) => {
              const isAdd = row.kind === "add";
              const isDel = row.kind === "del";
              const rowClass = isAdd
                ? "bg-[#3fb95026]"
                : isDel
                  ? "bg-[#f8514926]"
                  : "bg-transparent";
              const signClass = isAdd
                ? "text-[#3fb950] bg-[#3fb950]/15"
                : isDel
                  ? "text-[#ff7b72] bg-[#f85149]/15"
                  : "text-[#484f58]";
              const textClass = isAdd
                ? "text-[#7ee787]"
                : isDel
                  ? "text-[#ffa198]"
                  : "text-[#e6edf3]";

              return (
                <tr key={idx} className={rowClass}>
                  <td
                    className={`w-7 select-none border-r border-[#21262d] px-1.5 text-center align-top font-bold ${signClass}`}
                  >
                    {isAdd ? "+" : isDel ? "−" : ""}
                  </td>
                  <td className="w-10 select-none border-r border-[#21262d] px-2 text-right align-top text-[#6e7681]">
                    {row.oldLine ?? ""}
                  </td>
                  <td className="w-10 select-none border-r border-[#21262d] px-2 text-right align-top text-[#6e7681]">
                    {row.newLine ?? ""}
                  </td>
                  <td
                    className={`whitespace-pre px-3 py-0 align-top hljs ${textClass}`}
                    style={{ tabSize: 4 }}
                    dangerouslySetInnerHTML={{
                      __html: highlightLine(row.text || " ", lang),
                    }}
                  />
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/** New code only (no before snippet in report). */
function AddedOnlyDiff({ diff, lang }: { diff: ImplementationDiff; lang: string }) {
  const after = diff.after || "";
  if (!after.trim()) return null;

  return (
    <div className="mt-4 overflow-hidden rounded-xl border border-omega-border bg-[#0d1117]">
      <DiffFileHeader diff={diff} lang={lang} />
      <p className="border-b border-[#30363d] bg-[#033a16]/35 px-4 py-1.5 text-xs text-[#3fb950]">
        New code to add in this file
      </p>
      <div
        className="overflow-x-auto p-0 font-mono text-[12px] leading-[1.45] hljs"
        style={{ tabSize: 4 }}
        dangerouslySetInnerHTML={{ __html: highlightBlock(after, lang) }}
      />
    </div>
  );
}

export default function CodeDiffView({
  diff,
  preferInline = false,
}: {
  diff: ImplementationDiff;
  /** One block with red/green lines (Cursor-style), even for larger edits */
  preferInline?: boolean;
}) {
  const path = fileLabel(diff.location);
  const lang = languageFromPath(path, diff.language || "python");
  const hasBefore = Boolean(diff.before?.trim());
  const hasAfter = Boolean((diff.after || "").trim());

  if (!hasBefore && hasAfter) {
    return <AddedOnlyDiff diff={diff} lang={lang} />;
  }
  if (
    hasBefore &&
    hasAfter &&
    (preferInline || isInlineDiffFriendly(diff.before, diff.after))
  ) {
    return <InlineUnifiedDiff diff={diff} lang={lang} />;
  }
  if (hasBefore && hasAfter) {
    return <SideBySideDiff diff={diff} lang={lang} />;
  }
  return null;
}

export function ImplementationDiffCard({ diff }: { diff: ImplementationDiff }) {
  return (
    <article className="space-y-3">
      <div>
        <h4 className="font-display text-sm font-semibold text-white">{diff.title}</h4>
        <p className="mt-1 font-mono text-xs text-omega-muted">{diff.location}</p>
      </div>
      {diff.description ? (
        <p className="text-sm leading-relaxed text-slate-400">{diff.description}</p>
      ) : null}
      <CodeDiffView diff={diff} />
      {diff.business_outcome ? (
        <p className="text-sm text-slate-500">
          <span className="font-medium text-cyan-400/90">Outcome:</span> {diff.business_outcome}
        </p>
      ) : null}
    </article>
  );
}
