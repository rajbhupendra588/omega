export type SortDir = "asc" | "desc";

export function toggleSortDir(current: SortDir): SortDir {
  return current === "asc" ? "desc" : "asc";
}

export function compareStrings(a: string, b: string, dir: SortDir): number {
  const cmp = a.localeCompare(b, undefined, { sensitivity: "base" });
  return dir === "asc" ? cmp : -cmp;
}

export function compareNumbers(a: number, b: number, dir: SortDir): number {
  const cmp = a - b;
  return dir === "asc" ? cmp : -cmp;
}

export function matchesQuery(text: string, query: string): boolean {
  if (!query.trim()) return true;
  return text.toLowerCase().includes(query.trim().toLowerCase());
}
