import { useEffect, useRef, useState } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import {
  Activity,
  ChevronLeft,
  Github,
  Keyboard,
  LayoutDashboard,
  Menu,
  FlaskConical,
  X,
  Sparkles,
} from "lucide-react";
import ApiStatusBadge from "./ApiStatusBadge";

export default function Layout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [showShortcutHelp, setShowShortcutHelp] = useState(false);
  const gPendingRef = useRef(false);
  const nav = [
    { to: "/", label: "Dashboard", icon: LayoutDashboard },
    { to: "/analyze", label: "New Analysis", icon: Sparkles },
    { to: "/playground", label: "Playground", icon: FlaskConical },
  ];

  useEffect(() => {
    setMobileNavOpen(false);
    setShowShortcutHelp(false);
  }, [location.pathname]);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const tag = target?.tagName?.toLowerCase();
      const inEditable =
        tag === "input" ||
        tag === "textarea" ||
        target?.isContentEditable;
      if (inEditable || e.metaKey || e.ctrlKey || e.altKey) return;

      const key = e.key.toLowerCase();
      if (key === "g") {
        gPendingRef.current = true;
        window.setTimeout(() => {
          gPendingRef.current = false;
        }, 900);
        return;
      }
      if (!gPendingRef.current) return;
      gPendingRef.current = false;
      if (key === "d") {
        e.preventDefault();
        navigate("/");
      } else if (key === "a") {
        e.preventDefault();
        navigate("/analyze");
      } else if (key === "p") {
        e.preventDefault();
        navigate("/playground");
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [navigate]);

  return (
    <div className="min-h-screen md:flex">
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-omega-border bg-omega-card/95 backdrop-blur-xl transition-transform md:translate-x-0 ${
          mobileNavOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center gap-3 border-b border-omega-border px-6 py-5">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 to-cyan-400 font-display text-lg font-bold text-white shadow-glow">
            Ω
          </div>
          <div>
            <p className="font-display text-lg font-bold tracking-tight text-white">
              Omega
            </p>
            <p className="text-xs text-omega-muted">Quality Intelligence</p>
          </div>
        </div>
        <nav className="flex-1 space-y-1 p-4">
          {nav.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium transition ${
                  isActive
                    ? "bg-blue-600/20 text-white ring-1 ring-blue-500/30"
                    : "text-omega-muted hover:bg-white/5 hover:text-white"
                }`
              }
            >
              <Icon className="h-5 w-5 shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-omega-border p-4">
          <div className="rounded-xl bg-omega-bg/80 p-3 text-xs text-omega-muted">
            <div className="mb-2 flex items-center gap-2 text-white">
              <Activity className="h-4 w-4 text-cyan-400" />
              <span className="font-medium">Ω-QFM Engine</span>
            </div>
            <p>Dual reports: Business + Technical mathematics</p>
          </div>
        </div>
      </aside>
      {mobileNavOpen && (
        <button
          type="button"
          aria-label="Close navigation"
          onClick={() => setMobileNavOpen(false)}
          className="fixed inset-0 z-30 bg-black/50 md:hidden"
        />
      )}
      <main className="flex-1 md:ml-64">
        <header className="sticky top-0 z-30 border-b border-omega-border/80 bg-omega-bg/70 backdrop-blur-md">
          <div className="flex items-center justify-between gap-3 px-4 py-4 md:px-8">
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="btn-ghost px-2 py-2 md:hidden"
                onClick={() => setMobileNavOpen((v) => !v)}
                aria-label="Toggle navigation"
              >
                {mobileNavOpen ? (
                  <ChevronLeft className="h-4 w-4" />
                ) : (
                  <Menu className="h-4 w-4" />
                )}
              </button>
              <p className="text-sm text-omega-muted">
                Code Quality Field Manifold
              </p>
            </div>
            <div className="flex items-center gap-2 md:gap-3">
              <ApiStatusBadge />
              <div className="relative">
                <button
                  type="button"
                  className="btn-ghost px-2 py-2 text-xs"
                  onClick={() => setShowShortcutHelp((v) => !v)}
                  title="Keyboard shortcuts"
                  aria-label="Keyboard shortcuts"
                >
                  <Keyboard className="h-3.5 w-3.5" />
                  <span className="hidden sm:inline">Keys</span>
                </button>
                {showShortcutHelp && (
                  <div className="absolute right-0 z-50 mt-2 w-64 rounded-xl border border-omega-border bg-omega-card p-3 text-xs text-omega-muted shadow-2xl">
                    <div className="mb-2 flex items-center justify-between text-white">
                      <p className="font-medium">Keyboard shortcuts</p>
                      <button
                        type="button"
                        className="text-omega-muted hover:text-white"
                        onClick={() => setShowShortcutHelp(false)}
                        aria-label="Close shortcuts help"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </div>
                    <ul className="space-y-1.5">
                      <li>
                        <span className="font-mono text-cyan-300">/</span> Focus search on current page
                      </li>
                      <li>
                        <span className="font-mono text-cyan-300">g d</span> Go to Dashboard
                      </li>
                      <li>
                        <span className="font-mono text-cyan-300">g a</span> Go to New Analysis
                      </li>
                      <li>
                        <span className="font-mono text-cyan-300">g p</span> Go to Playground
                      </li>
                    </ul>
                  </div>
                )}
              </div>
              <a
                href="https://github.com"
                target="_blank"
                rel="noreferrer"
                className="btn-ghost hidden text-xs sm:inline-flex"
              >
                <Github className="h-4 w-4" />
                Analyze any public repo
              </a>
            </div>
          </div>
        </header>
        <div className="px-4 py-6 md:px-8 md:py-8">{children}</div>
      </main>
    </div>
  );
}
