import { useEffect, useMemo, useState } from "react";
import { Braces, Clock3, Loader2, Play, Trash2 } from "lucide-react";
import { analyzePlaygroundCode } from "../api/client";
import type { FullReport } from "../types";
import ReportTabs from "../components/ReportTabs";

const LANGUAGES = [
  "python",
  "javascript",
  "typescript",
  "java",
  "go",
  "c",
  "cpp",
  "rust",
  "kotlin",
  "csharp",
] as const;
const HISTORY_KEY = "omega.playground.history";
const HISTORY_LIMIT = 10;

const SAMPLE_BINARY_TREE = `class Node:
    def __init__(self, value):
        self.value = value
        self.left = None
        self.right = None

def insert(root, value):
    if root is None:
        return Node(value)
    if value < root.value:
        root.left = insert(root.left, value)
    else:
        root.right = insert(root.right, value)
    return root

def inorder(root):
    if root is None:
        return []
    return inorder(root.left) + [root.value] + inorder(root.right)

root = None
for value in [7, 3, 9, 1, 5]:
    root = insert(root, value)

print(inorder(root))
`;

type PlaygroundHistoryItem = {
  id: string;
  title: string;
  language: (typeof LANGUAGES)[number];
  code: string;
  createdAt: string;
};

export default function PlaygroundPage() {
  const [title, setTitle] = useState("Binary Tree Playground");
  const [language, setLanguage] = useState<(typeof LANGUAGES)[number]>("python");
  const [code, setCode] = useState(SAMPLE_BINARY_TREE);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<FullReport | null>(null);
  const [history, setHistory] = useState<PlaygroundHistoryItem[]>([]);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(HISTORY_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw) as PlaygroundHistoryItem[];
      if (Array.isArray(parsed)) setHistory(parsed.slice(0, HISTORY_LIMIT));
    } catch {
      /* ignore corrupted history */
    }
  }, []);

  useEffect(() => {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, HISTORY_LIMIT)));
  }, [history]);

  const saveCurrentSnippet = () => {
    const trimmedCode = code.trim();
    if (!trimmedCode) return;
    const normalizedTitle = title.trim() || "Untitled snippet";
    const newItem: PlaygroundHistoryItem = {
      id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
      title: normalizedTitle,
      language,
      code: trimmedCode,
      createdAt: new Date().toISOString(),
    };
    setHistory((prev) => [newItem, ...prev].slice(0, HISTORY_LIMIT));
  };

  const sortedHistory = useMemo(
    () =>
      [...history].sort(
        (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
      ),
    [history]
  );

  const run = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const r = await analyzePlaygroundCode({ code, language, title: title.trim() || undefined });
      setReport(r);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Playground analysis failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-bold text-white">Omega Playground</h1>
        <p className="mt-2 text-omega-muted">
          Paste any code snippet (Binary Tree, API handler, data pipeline) and get full Omega
          analysis across business, technical, symbol, and improvement dimensions.
        </p>
      </div>

      <form onSubmit={run} className="glass-card space-y-4 p-5">
        <div className="grid gap-3 md:grid-cols-3">
          <div className="md:col-span-2">
            <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-omega-muted">
              Snippet title
            </label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="input-field"
              placeholder="Binary Tree Insert/Traversal"
              disabled={busy}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-omega-muted">
              Language
            </label>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value as (typeof LANGUAGES)[number])}
              className="input-field"
              disabled={busy}
            >
              {LANGUAGES.map((lang) => (
                <option key={lang} value={lang}>
                  {lang}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label className="mb-1 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-omega-muted">
            <Braces className="h-3.5 w-3.5" />
            Code
          </label>
          <textarea
            value={code}
            onChange={(e) => setCode(e.target.value)}
            className="input-field min-h-[280px] font-mono text-xs leading-relaxed"
            placeholder="Paste your code here..."
            disabled={busy}
            required
          />
        </div>

        {error && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
            {error}
          </div>
        )}

        <div className="flex flex-wrap items-center gap-3">
          <button type="submit" className="btn-primary" disabled={busy || !code.trim()}>
            {busy ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Analyzing
              </>
            ) : (
              <>
                <Play className="h-4 w-4" />
                Analyze snippet
              </>
            )}
          </button>
          <button
            type="button"
            className="btn-ghost"
            disabled={busy}
            onClick={() => {
              setLanguage("python");
              setTitle("Binary Tree Playground");
              setCode(SAMPLE_BINARY_TREE);
            }}
          >
            Load binary tree sample
          </button>
          <button
            type="button"
            className="btn-ghost"
            disabled={busy || !code.trim()}
            onClick={saveCurrentSnippet}
          >
            Save snippet
          </button>
        </div>
      </form>

      <div className="glass-card p-4">
        <div className="mb-3 flex items-center justify-between gap-2">
          <p className="flex items-center gap-2 text-sm font-medium text-white">
            <Clock3 className="h-4 w-4 text-cyan-400" />
            Recent snippets
          </p>
          {history.length > 0 && (
            <button
              type="button"
              className="btn-ghost px-2 py-1 text-xs"
              onClick={() => setHistory([])}
            >
              <Trash2 className="h-3.5 w-3.5" />
              Clear all
            </button>
          )}
        </div>
        {sortedHistory.length === 0 ? (
          <p className="text-xs text-omega-muted">
            No saved snippets yet. Use <span className="font-mono text-cyan-300">Save snippet</span>{" "}
            to keep recent playground experiments.
          </p>
        ) : (
          <ul className="space-y-2">
            {sortedHistory.map((item) => (
              <li
                key={item.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-omega-border bg-omega-bg/40 px-3 py-2"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-white">{item.title}</p>
                  <p className="text-xs text-omega-muted">
                    {item.language} · {new Date(item.createdAt).toLocaleString()}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    className="btn-ghost px-2 py-1 text-xs"
                    onClick={() => {
                      setTitle(item.title);
                      setLanguage(item.language);
                      setCode(item.code);
                    }}
                  >
                    Load
                  </button>
                  <button
                    type="button"
                    className="btn-ghost px-2 py-1 text-xs text-red-300 hover:text-red-200"
                    onClick={() => {
                      setHistory((prev) => prev.filter((h) => h.id !== item.id));
                    }}
                  >
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {report ? <ReportTabs report={report} /> : null}
    </div>
  );
}
