/** Line-level diff rows for Cursor/GitHub-style inline view. */
export type DiffLineKind = "same" | "add" | "del";

export interface DiffLine {
  kind: DiffLineKind;
  text: string;
  oldLine?: number;
  newLine?: number;
}

function lcsTable(a: string[], b: string[]): number[][] {
  const m = a.length;
  const n = b.length;
  const dp: number[][] = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0));
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (a[i - 1] === b[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1;
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
      }
    }
  }
  return dp;
}

export function diffLines(before: string, after: string): DiffLine[] {
  const a = before ? before.replace(/\r\n/g, "\n").split("\n") : [];
  const b = after ? after.replace(/\r\n/g, "\n").split("\n") : [];
  if (a.length === 0 && b.length === 0) return [];
  if (a.length === 0) {
    return b.map((text, i) => ({ kind: "add" as const, text, newLine: i + 1 }));
  }
  if (b.length === 0) {
    return a.map((text, i) => ({ kind: "del" as const, text, oldLine: i + 1 }));
  }

  const dp = lcsTable(a, b);
  const raw: Array<{ kind: DiffLineKind; text: string; ai?: number; bi?: number }> = [];
  let i = a.length;
  let j = b.length;
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && a[i - 1] === b[j - 1]) {
      raw.push({ kind: "same", text: a[i - 1], ai: i, bi: j });
      i--;
      j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      raw.push({ kind: "add", text: b[j - 1], bi: j });
      j--;
    } else {
      raw.push({ kind: "del", text: a[i - 1], ai: i });
      i--;
    }
  }
  raw.reverse();

  return raw.map((row) => ({
    kind: row.kind,
    text: row.text,
    oldLine: row.ai,
    newLine: row.bi,
  }));
}

/** True when before/after are similar enough for inline red/green line diff. */
export function isInlineDiffFriendly(before: string, after: string): boolean {
  const a = before.replace(/\r\n/g, "\n").split("\n");
  const b = after.replace(/\r\n/g, "\n").split("\n");
  if (!a.length || !b.length) return false;
  const rows = diffLines(before, after);
  const same = rows.filter((r) => r.kind === "same").length;
  const ratio = same / Math.max(a.length, b.length);
  return ratio >= 0.12;
}
