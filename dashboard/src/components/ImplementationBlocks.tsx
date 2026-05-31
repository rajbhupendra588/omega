/** Render implementation_plan markdown blocks with code fences. */
import type { ReactNode } from "react";

export default function ImplementationBlocks({ blocks }: { blocks: string[] }) {
  if (!blocks?.length) return null;

  return (
    <div className="mt-6 space-y-6 border-t border-omega-border pt-6">
      <p className="text-xs font-semibold uppercase tracking-wider text-cyan-400">
        Implementation in this repo (copy-paste ready)
      </p>
      {blocks.map((block, i) => (
        <ImplementationBlock key={i} text={block} />
      ))}
    </div>
  );
}

function ImplementationBlock({ text }: { text: string }) {
  const parts = text.split(/```(?:python|javascript|java|typescript)?\n?/);
  const elements: ReactNode[] = [];

  parts.forEach((part, idx) => {
    if (idx % 2 === 1) {
      const codeEnd = part.indexOf("```");
      const code = codeEnd >= 0 ? part.slice(0, codeEnd) : part;
      const rest = codeEnd >= 0 ? part.slice(codeEnd + 3) : "";
      elements.push(
        <pre
          key={`c-${idx}`}
          className="mt-3 overflow-x-auto rounded-xl border border-omega-border bg-[#0a0f1a] p-4 font-mono text-xs leading-relaxed text-emerald-100/90"
        >
          {code.trimEnd()}
        </pre>
      );
      if (rest.trim()) {
        elements.push(
          <p key={`r-${idx}`} className="mt-2 text-sm text-slate-400 whitespace-pre-wrap">
            {rest.trim()}
          </p>
        );
      }
    } else if (part.trim()) {
      elements.push(
        <div
          key={`t-${idx}`}
          className="prose prose-invert max-w-none text-sm text-slate-300 [&_h3]:mt-0 [&_h3]:font-display [&_h3]:text-base [&_h3]:text-white [&_strong]:text-cyan-300"
          dangerouslySetInnerHTML={{ __html: simpleMd(part) }}
        />
      );
    }
  });

  return <div>{elements}</div>;
}

function simpleMd(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/### (.+)/g, "<h3>$1</h3>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code class='text-cyan-300 bg-black/30 px-1 rounded'>$1</code>")
    .replace(/\n\n/g, "</p><p>")
    .replace(/^/, "<p>")
    .concat("</p>");
}
