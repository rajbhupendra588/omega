import { NavLink } from "react-router-dom";
import {
  Activity,
  Github,
  LayoutDashboard,
  Sparkles,
} from "lucide-react";

export default function Layout({ children }: { children: React.ReactNode }) {
  const nav = [
    { to: "/", label: "Dashboard", icon: LayoutDashboard },
    { to: "/analyze", label: "New Analysis", icon: Sparkles },
  ];

  return (
    <div className="flex min-h-screen">
      <aside className="fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-omega-border bg-omega-card/50 backdrop-blur-xl">
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
      <main className="ml-64 flex-1">
        <header className="sticky top-0 z-30 border-b border-omega-border/80 bg-omega-bg/70 backdrop-blur-md">
          <div className="flex items-center justify-between px-8 py-4">
            <p className="text-sm text-omega-muted">
              Code Quality Field Manifold
            </p>
            <a
              href="https://github.com"
              target="_blank"
              rel="noreferrer"
              className="btn-ghost text-xs"
            >
              <Github className="h-4 w-4" />
              Analyze any public repo
            </a>
          </div>
        </header>
        <div className="px-8 py-8">{children}</div>
      </main>
    </div>
  );
}
