import type { ImplementationDiff } from "../types";

/** Turn legacy markdown plans into structured diffs for the simple UI. */
export function diffsFromMarkdownBlocks(blocks: string[]): ImplementationDiff[] {
  return blocks.map(parseBlock).filter((d): d is ImplementationDiff => d !== null);
}

export function normalizeImplementationDiffs(
  diffs?: ImplementationDiff[],
  blocks?: string[]
): ImplementationDiff[] {
  if (diffs?.length) return diffs;
  if (!blocks?.length) return [];
  return diffsFromMarkdownBlocks(blocks);
}

function parseBlock(text: string): ImplementationDiff | null {
  const title = text.match(/### (.+)/)?.[1]?.trim();
  const where = text.match(/\*\*Where:\*\*\s*`([^`]+)`/)?.[1]?.trim();
  if (!title || !where) return null;

  const descMatch = text.split(/\*\*Where:\*\*/)[1];
  const description = descMatch
    ?.split(/```/)[0]
    ?.replace(/^`[^`]+`\s*\n?\n?/, "")
    ?.trim() ?? "";

  const outcome =
    text.match(/\*\*Outcome:\*\*\s*(.+?)(?:\n\n|$)/s)?.[1]?.trim() ?? "";

  const fence = text.match(/```(\w+)\n/)?.[1] ?? "text";
  const codeBody = text.match(/```\w*\n([\s\S]*?)```/)?.[1] ?? "";

  let before = "";
  let after = "";
  if (fence === "diff") {
    const parsed = parseUnifiedDiff(codeBody);
    before = parsed.before;
    after = parsed.after;
  } else if (codeBody.trim()) {
    after = codeBody.trimEnd();
  }

  const path = where.split(":")[0];
  const lang = fence === "diff" ? guessLang(path) : fence;

  return {
    title,
    location: where,
    description,
    before,
    after,
    language: lang,
    business_outcome: outcome,
    simple_summary: humanSummary(title, description, path, outcome),
    steps: humanSteps(where, Boolean(before)),
  };
}

function parseUnifiedDiff(body: string): { before: string; after: string } {
  const before: string[] = [];
  const after: string[] = [];
  for (const line of body.replace(/\r\n/g, "\n").split("\n")) {
    if (line.startsWith("--- ") || line.startsWith("+++ ")) continue;
    if (line.startsWith("-")) before.push(line.slice(1));
    else if (line.startsWith("+")) after.push(line.slice(1));
    else if (line.startsWith(" ")) {
      const t = line.slice(1);
      before.push(t);
      after.push(t);
    } else if (line) {
      before.push(line);
      after.push(line);
    }
  }
  return { before: before.join("\n"), after: after.join("\n") };
}

function guessLang(path: string): string {
  const p = path.toLowerCase();
  if (p.endsWith(".java")) return "java";
  if (p.endsWith(".py")) return "python";
  if (p.endsWith(".go")) return "go";
  if (p.endsWith(".ts") || p.endsWith(".tsx")) return "typescript";
  if (p.endsWith(".js")) return "javascript";
  if (p.endsWith(".kt")) return "kotlin";
  if (p.endsWith(".rs")) return "rust";
  return "java";
}

function humanSummary(
  title: string,
  description: string,
  path: string,
  outcome: string
): string {
  const short = description.split(".")[0]?.trim();
  if (short && short.length < 160) return short + ".";
  if (outcome) return outcome.split(".")[0] + ".";
  const file = path.split("/").pop() ?? path;
  return `${title.replace(/`/g, "")} — apply this change in ${file} to make the code easier to maintain.`;
}

function humanSteps(location: string, hasBefore: boolean): string[] {
  const [file, lines] = location.includes(":")
    ? [location.split(":")[0], location.split(":").slice(1).join(":")]
    : [location, ""];
  const steps = [`Open \`${file}\` in your IDE.`];
  if (lines) steps.push(`Jump to lines ${lines}.`);
  if (hasBefore) {
    steps.push("Find the code in the red box (what you have now).");
    steps.push("Replace it with the code in the green box (the fix).");
  } else {
    steps.push("Add or paste the code from the green box at that location.");
  }
  steps.push("Run your usual tests and commit.");
  return steps;
}
