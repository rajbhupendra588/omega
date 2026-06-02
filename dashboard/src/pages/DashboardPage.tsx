import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { getRunHistory, listRepos } from "../api/client";
import type { RepoSummary, RunRecord } from "../types";
import GradeBadge from "../components/GradeBadge";
import GradeDistribution from "../components/GradeDistribution";
import RerunButton from "../components/RerunButton";
import BulkRerunBar from "../components/BulkRerunBar";
import { PurgeAllButton, PurgeRepoButton, PurgeRunButton } from "../components/PurgeReportsBar";
import {
  ArrowRight,
  ChevronDown,
  ChevronRight,
  Clock,
  History,
  Loader2,
  Plus,
  AlertCircle,
  CheckCircle2,
  Search,
  ArrowUpDown,
  Info,
  X,
} from "lucide-react";

type SortKey = "name" | "date" | "omega" | "grade" | "runs";
type SortDir = "asc" | "desc";

const GRADE_RANK: Record<string, number> = { A: 1, B: 2, C: 3, D: 4, F: 5 };
const DASHBOARD_PREFS_KEY = "omega.dashboard.prefs";
const DASHBOARD_TIPS_KEY = "omega.dashboard.tips.dismissed";

export default function DashboardPage() {
  const [repos, setRepos] = useState<RepoSummary[]>([]);
  const [expanded, setExpanded] = useState<Record<string, RunRecord[]>>({});
  const [openRepo, setOpenRepo] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const searchRef = useRef<HTMLInputElement | null>(null);
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("date");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [showTips, setShowTips] = useState(true);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(DASHBOARD_PREFS_KEY);
      if (!raw) return;
      const prefs = JSON.parse(raw) as {
        search?: string;
        sortKey?: SortKey;
        sortDir?: SortDir;
      };
      if (prefs.search) setSearch(prefs.search);
      if (prefs.sortKey) setSortKey(prefs.sortKey);
      if (prefs.sortDir) setSortDir(prefs.sortDir);
    } catch {
      /* ignore corrupted prefs */
    }
  }, []);

  useEffect(() => {
    localStorage.setItem(
      DASHBOARD_PREFS_KEY,
      JSON.stringify({ search, sortKey, sortDir })
    );
  }, [search, sortKey, sortDir]);

  useEffect(() => {
    const dismissed = localStorage.getItem(DASHBOARD_TIPS_KEY) === "1";
    if (dismissed) setShowTips(false);
  }, []);

  const load = async () => {
    try {
      setRepos(await listRepos());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    const onShortcut = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const tag = target?.tagName?.toLowerCase();
      const inEditable =
        tag === "input" || tag === "textarea" || target?.isContentEditable;
      if (inEditable || e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === "/") {
        e.preventDefault();
        searchRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onShortcut);
    return () => window.removeEventListener("keydown", onShortcut);
  }, []);

  const toggleHistory = async (repo: RepoSummary) => {
    if (openRepo === repo.repo_key) {
      setOpenRepo(null);
      return;
    }
    setOpenRepo(repo.repo_key);
    if (expanded[repo.repo_key]) return;
    try {
      const h = await getRunHistory(repo.latest_run_id);
      setExpanded((prev) => ({ ...prev, [repo.repo_key]: h.runs }));
    } catch {
      /* ignore */
    }
  };

  const totalRuns = repos.reduce((n, r) => n + r.run_count, 0);
  const inProgress = repos.filter(
    (r) => r.latest_status === "running" || r.latest_status === "pending"
  ).length;
  const avgOmega =
    repos.filter((r) => r.latest_omega_index != null).length > 0
      ? repos
          .filter((r) => r.latest_omega_index != null)
          .reduce((s, r) => s + (r.latest_omega_index ?? 0), 0) /
        repos.filter((r) => r.latest_omega_index != null).length
      : null;

  const filteredRepos = useMemo(() => {
    const q = search.trim().toLowerCase();
    let list = q
      ? repos.filter(
          (r) =>
            r.repo_display.toLowerCase().includes(q) ||
            r.target.toLowerCase().includes(q)
        )
      : [...repos];

    list.sort((a, b) => {
      let cmp = 0;
      switch (sortKey) {
        case "name":
          cmp = a.repo_display.localeCompare(b.repo_display);
          break;
        case "date":
          cmp =
            new Date(a.latest_created_at).getTime() -
            new Date(b.latest_created_at).getTime();
          break;
        case "omega":
          cmp = (a.latest_omega_index ?? 999) - (b.latest_omega_index ?? 999);
          break;
        case "grade":
          cmp =
            (GRADE_RANK[a.latest_quality_grade ?? "F"] ?? 9) -
            (GRADE_RANK[b.latest_quality_grade ?? "F"] ?? 9);
          break;
        case "runs":
          cmp = a.run_count - b.run_count;
          break;
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
    return list;
  }, [repos, search, sortKey, sortDir]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "name" ? "asc" : "desc");
    }
  };

  const statusIcon = (s: string) => {
    if (s === "completed")
      return <CheckCircle2 className="h-4 w-4 text-emerald-400" />;
    if (s === "failed") return <AlertCircle className="h-4 w-4 text-red-400" />;
    return <Loader2 className="h-4 w-4 animate-spin text-cyan-400" />;
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold tracking-tight text-white">
            Quality Dashboard
          </h1>
          <p className="mt-2 max-w-xl text-omega-muted">
            Each repository keeps a full run history — re-analyses append as new
            runs without losing prior reports.
          </p>
        </div>
        <Link to="/analyze" className="btn-primary">
          <Plus className="h-5 w-5" />
          New Analysis
        </Link>
      </div>

      {showTips && (
        <div className="glass-card flex flex-wrap items-start justify-between gap-3 p-4">
          <div className="min-w-0">
            <p className="flex items-center gap-2 text-sm font-medium text-white">
              <Info className="h-4 w-4 text-cyan-400" />
              Quick tips
            </p>
            <p className="mt-1 text-xs text-omega-muted">
              Press <span className="font-mono text-cyan-300">/</span> to focus search. Use
              <span className="ml-1 font-mono text-cyan-300">g d</span> for Dashboard and
              <span className="ml-1 font-mono text-cyan-300">g a</span> for New Analysis.
            </p>
          </div>
          <button
            type="button"
            className="btn-ghost px-2 py-1.5 text-xs"
            onClick={() => {
              setShowTips(false);
              localStorage.setItem(DASHBOARD_TIPS_KEY, "1");
            }}
          >
            <X className="h-3.5 w-3.5" />
            Dismiss
          </button>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Repositories"
          value={String(repos.length)}
          sub="Grouped by target"
        />
        <StatCard
          label="Total runs"
          value={String(totalRuns)}
          sub="All analyses stored"
        />
        <StatCard
          label="In progress"
          value={String(inProgress)}
          sub="Latest run per repo"
        />
        <StatCard
          label="Avg Ω index"
          value={avgOmega != null ? avgOmega.toFixed(1) : "—"}
          sub="Across graded repos"
        />
      </div>

      {!loading && repos.length > 0 && <GradeDistribution repos={repos} />}

      {!loading && repos.length > 0 && (
        <div className="flex flex-col items-stretch gap-3 lg:flex-row">
          <div className="min-w-0 flex-1">
            <BulkRerunBar repos={repos} recentLimit={10} onDone={load} />
          </div>
          <div className="flex items-center rounded-xl border border-red-500/20 bg-red-500/5 px-4">
            <PurgeAllButton
              onDone={() => {
                setExpanded({});
                setOpenRepo(null);
                load();
              }}
            />
          </div>
        </div>
      )}

      <div className="glass-card overflow-hidden">
        <div className="border-b border-omega-border px-6 py-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="font-display text-lg font-semibold text-white">
                Repositories & run history
              </h2>
              <p className="mt-1 text-xs text-omega-muted">
                Expand a repo to re-run a specific past analysis, or use bulk re-run above.
              </p>
            </div>
            {!loading && repos.length > 0 && (
              <div className="flex flex-wrap items-center gap-2">
                <div className="relative">
                  <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-omega-muted" />
                  <input
                    ref={searchRef}
                    type="search"
                    placeholder="Search repos…"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="input-field w-56 pl-9 py-2 text-sm"
                  />
                </div>
                {(
                  [
                    ["name", "Name"],
                    ["date", "Date"],
                    ["omega", "Ω"],
                    ["grade", "Grade"],
                    ["runs", "Runs"],
                  ] as const
                ).map(([key, label]) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => toggleSort(key)}
                    className={`flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-medium transition ${
                      sortKey === key
                        ? "bg-blue-600/25 text-white ring-1 ring-blue-500/40"
                        : "text-omega-muted hover:text-white"
                    }`}
                  >
                    {label}
                    {sortKey === key && (
                      <ArrowUpDown className="h-3 w-3 text-cyan-400" />
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
        {loading && (
          <div className="flex items-center justify-center gap-2 py-16 text-omega-muted">
            <Loader2 className="h-5 w-5 animate-spin" />
            Loading…
          </div>
        )}
        {error && (
          <div className="px-6 py-8 text-red-400">
            {error}. Is the API running?{" "}
            <code className="text-sm">omega-ui</code>
          </div>
        )}
        {!loading && !error && repos.length === 0 && (
          <div className="px-6 py-16 text-center text-omega-muted">
            <p>No analyses yet.</p>
            <Link to="/analyze" className="btn-primary mt-4 inline-flex">
              Analyze your first repo
            </Link>
          </div>
        )}
        {!loading && repos.length > 0 && filteredRepos.length === 0 && (
          <div className="px-6 py-10 text-center text-omega-muted">
            No repositories match your search.
          </div>
        )}
        {!loading && repos.length > 0 && filteredRepos.length > 0 && (
          <ul className="divide-y divide-omega-border">
            {filteredRepos.map((repo) => {
              const isOpen = openRepo === repo.repo_key;
              const runs = expanded[repo.repo_key];
              return (
                <li key={repo.repo_key} className="px-4 py-4 sm:px-6">
                  <div className="flex flex-wrap items-center gap-3 sm:gap-4">
                    <button
                      type="button"
                      onClick={() => toggleHistory(repo)}
                      className="btn-ghost p-1"
                      aria-label="Toggle history"
                    >
                      {isOpen ? (
                        <ChevronDown className="h-4 w-4" />
                      ) : (
                        <ChevronRight className="h-4 w-4" />
                      )}
                    </button>
                    {statusIcon(repo.latest_status)}
                    <div className="min-w-0 flex-1 basis-full sm:basis-auto">
                      <p className="font-semibold text-white">{repo.repo_display}</p>
                      <p className="truncate text-xs text-omega-muted">
                        {repo.target}
                      </p>
                    </div>
                    <span className="flex items-center gap-1 rounded-full bg-cyan-500/10 px-2.5 py-1 text-xs text-cyan-300">
                      <History className="h-3.5 w-3.5" />
                      {repo.run_count} run{repo.run_count === 1 ? "" : "s"}
                    </span>
                    {repo.latest_quality_grade && (
                      <GradeBadge grade={repo.latest_quality_grade} />
                    )}
                    {repo.latest_omega_index != null && (
                      <div className="text-right">
                        <p className="font-mono text-sm font-semibold text-cyan-400">
                          Ω {repo.latest_omega_index}
                        </p>
                        <p className="text-xs text-omega-muted">Latest</p>
                      </div>
                    )}
                    <div className="flex items-center gap-2 text-xs text-omega-muted">
                      <Clock className="h-3.5 w-3.5" />
                      {new Date(repo.latest_created_at).toLocaleString()}
                    </div>
                    {(repo.latest_status === "completed" ||
                      repo.latest_status === "failed") && (
                      <RerunButton
                        runId={repo.latest_run_id}
                        label="Re-run repo"
                        className="btn-ghost py-2 text-sm"
                        waitForCompletion={false}
                        onComplete={load}
                      />
                    )}
                    {repo.latest_status === "completed" && (
                      <Link
                        to={`/reports/${repo.latest_run_id}`}
                        className="btn-primary py-2 text-sm"
                      >
                        Latest report
                        <ArrowRight className="h-4 w-4" />
                      </Link>
                    )}
                  </div>
                  {isOpen && runs && (
                    <div className="mt-4 ml-8 flex flex-wrap items-center gap-2 border-l border-omega-border pl-4">
                      <PurgeRepoButton
                        repo={repo}
                        onDone={() => {
                          setExpanded({});
                          setOpenRepo(null);
                          load();
                        }}
                      />
                    </div>
                  )}
                  {isOpen && runs && (
                    <ul className="mt-2 ml-8 space-y-2 border-l border-omega-border pl-4">
                      {runs.map((run) => (
                        <li
                          key={run.id}
                          className="flex flex-wrap items-center gap-3 rounded-lg bg-slate-900/40 px-3 py-2 text-sm"
                        >
                          <span className="font-mono text-xs text-omega-muted">
                            Run #{run.run_number}
                          </span>
                          <span className="text-xs text-omega-muted">
                            {new Date(run.created_at).toLocaleString()}
                          </span>
                          {run.omega_index != null && (
                            <span className="font-mono text-cyan-400">
                              Ω {run.omega_index}
                            </span>
                          )}
                          {run.status === "completed" && (
                            <Link
                              to={`/reports/${run.id}`}
                              className="text-xs text-cyan-400 hover:underline"
                            >
                              View
                            </Link>
                          )}
                          {(run.status === "completed" ||
                            run.status === "failed") && (
                            <RerunButton
                              runId={run.id}
                              label="Re-run"
                              className="btn-ghost px-2 py-1 text-xs"
                              waitForCompletion={false}
                              onComplete={() => {
                                setExpanded({});
                                load();
                              }}
                            />
                          )}
                          <PurgeRunButton
                            runId={run.id}
                            label=""
                            className="btn-ghost p-1 text-red-400/80"
                            onDone={() => {
                              setExpanded((prev) => {
                                const next = { ...prev };
                                if (next[repo.repo_key]) {
                                  next[repo.repo_key] = next[repo.repo_key].filter(
                                    (r) => r.id !== run.id
                                  );
                                }
                                return next;
                              });
                              load();
                            }}
                          />
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub: string;
}) {
  return (
    <div className="glass-card p-5">
      <p className="text-xs font-medium uppercase tracking-wider text-omega-muted">
        {label}
      </p>
      <p className="mt-2 font-display text-3xl font-bold text-white">{value}</p>
      <p className="mt-1 text-xs text-omega-muted">{sub}</p>
    </div>
  );
}
