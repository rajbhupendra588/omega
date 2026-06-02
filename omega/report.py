"""Dual-audience detailed reports: technical/mathematical + business."""

from __future__ import annotations

import csv
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from omega.analyzer import RepositoryOutcome
from omega.dimensions import ensure_report_has_dimensions
from omega.metrics_suite import ensure_report_has_metric_suite
from omega.developer_guide import ensure_report_has_developer_guide
from omega.discover import RepoInventory
from omega.entities import EntityMetrics
from omega.metrics import FileMetrics
from omega.narrative import build_business_sections, build_technical_sections, file_business_blurb


def _esc(s: str) -> str:
    return html.escape(str(s))


def _html_prose(s: str) -> str:
    """Escape HTML and render simple **bold** markdown."""
    if not s:
        return ""
    escaped = html.escape(str(s))
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)


def _code_label(s: str) -> str:
    """Strip markdown backticks for use inside <code>."""
    t = str(s).strip()
    if t.startswith("`") and t.endswith("`"):
        return t[1:-1]
    return t


def _action_strings(actions: list) -> list[str]:
    """Flatten actions; tolerate legacy nested single-item lists."""
    out: list[str] = []
    for item in actions:
        if isinstance(item, (list, tuple)):
            out.extend(_action_strings(list(item)))
        else:
            out.append(str(item))
    return out


def _bar(value: float, width: int = 28) -> str:
    filled = int(min(width, max(0, value / 100 * width)))
    return "█" * filled + "░" * (width - filled)


def _dimension_band_color(band: str) -> str:
    return {
        "LOW": "#22c55e",
        "MEDIUM": "#eab308",
        "HIGH": "#f97316",
        "CRITICAL": "#ef4444",
    }.get(band, "#94a3b8")


def _dimensions_markdown(outcome: RepositoryOutcome, *, audience: str) -> list[str]:
    parts: list[str] = []
    for d in outcome.dimensions:
        parts.append(f"### {d['name']} — {d['band']} (stress score {d['score']})")
        parts.append(
            d["summary_business"] if audience == "business" else d["summary_technical"]
        )
        parts.append(f"- Aggregate in this repo: **{d['repo_aggregate']}** {d['unit']}")
        for ev in d.get("evidence", [])[:4]:
            parts.append(f"- {ev}")
        for sym in d.get("evidence_symbols", [])[:3]:
            parts.append(f"- Symbol: `{sym}`")
        for act in _action_strings(d.get("actions_in_repo", []))[:2]:
            parts.append(f"- **Action:** {act}")
        parts.append("")
    return parts


def _dimensions_html(outcome: RepositoryOutcome) -> str:
    if not outcome.dimensions:
        return "<p>No dimension data.</p>"
    cards = []
    for d in outcome.dimensions:
        color = _dimension_band_color(d["band"])
        ev_items = d.get("evidence", [])[:4]
        ev_lis = "".join(f"<li>{_esc(ev)}</li>" for ev in ev_items)
        sym_lis = "".join(
            f"<li><code>{_esc(_code_label(s))}</code></li>"
            for s in d.get("evidence_symbols", [])[:3]
        )
        act_lis = "".join(
            f"<li>{_esc(a)}</li>"
            for a in _action_strings(d.get("actions_in_repo", []))[:3]
        )
        bar = _bar(d["score"], 20)
        cards.append(
            f"""<div class="dim-card" style="border-left:4px solid {color}">
              <div class="dim-head">
                <strong>{_esc(d['name'])}</strong>
                <span class="badge" style="background:{color}33;color:{color}">{d['band']}</span>
                <span class="dim-score">{d['score']}</span>
              </div>
              <div class="dim-bar mono">{bar} {d['score']}/100</div>
              <p class="dim-summary">{_esc(d['summary_technical'])}</p>
              <p class="dim-agg mono">This repo: {d['repo_aggregate']} {d['unit']} · weight {d['weight']} · does not affect letter grade</p>
              {f"<p class='dim-qual' style='font-size:0.85rem;color:var(--muted)'>{_esc(d['qualification'])}</p>" if d.get('qualification') else ""}
              {"<ul class='dim-ev'>" + ev_lis + "</ul>" if ev_lis else ""}
              {"<ul class='dim-sym'>" + sym_lis + "</ul>" if sym_lis else ""}
              {"<p class='dim-act-lbl'>Actions in this codebase:</p><ul class='dim-act'>" + act_lis + "</ul>" if act_lis else ""}
            </div>"""
        )
    return "".join(cards)


def _developer_html(outcome: RepositoryOutcome) -> str:
    dg = outcome.developer_guide or {}
    if not dg.get("actions"):
        return "<p>No developer actions for this run.</p>"
    blocks = []
    for act in dg.get("actions", []):
        steps = "".join(f"<li>{_esc(s)}</li>" for s in act.get("what_to_do", []))
        color = _dimension_band_color(act.get("risk_band", "LOW"))
        blocks.append(
            f"""<div class="dev-card" style="border-left:4px solid {color}">
              <div class="dim-head">
                <span class="dev-priority">#{act.get('priority', '?')}</span>
                <strong>{_esc(act.get('title', ''))}</strong>
                <span class="badge" style="background:{color}33;color:{color}">{_esc(act.get('risk_band', ''))}</span>
              </div>
              <p class="dim-agg mono">{_esc(act.get('location', ''))} · {_esc(act.get('category', ''))}</p>
              <h4 style="color:var(--tech);margin:0.75rem 0 0.25rem">Why this is risky</h4>
              <p class="dim-summary">{_esc(act.get('why_risky', ''))}</p>
              <h4 style="color:var(--biz);margin:0.75rem 0 0.25rem">What to do in this repo</h4>
              <ul class="dim-act">{steps}</ul>
            </div>"""
        )
    intro = _esc(dg.get("introduction", ""))
    how = "".join(f"<li>{_esc(h)}</li>" for h in dg.get("how_to_read", []))
    return f"""<p>{intro}</p>
      <h3>How to read</h3><ul>{how}</ul>
      <div class="dim-grid">{''.join(blocks)}</div>"""


def _md_bold(text: str) -> str:
    return text.replace("**", "")  # strip for plain txt; keep in md


def format_terminal_report(outcome: RepositoryOutcome) -> str:
    """Short terminal summary; full detail in HTML/MD files."""
    lines = [
        "═" * 76,
        "  Ω-QFM — ANALYSIS COMPLETE",
        "═" * 76,
        f"  Repository : {outcome.repo_display}",
        f"  Ω Index    : {outcome.omega_index}   Grade: {outcome.quality_grade}",
        f"  Files      : {outcome.file_count:,}   LOC: {outcome.total_loc:,}",
        "",
        "  BUSINESS (one line):",
        f"    {outcome.health_summary_business}",
        "",
        "  TECHNICAL (one line):",
        f"    {outcome.health_summary}",
        "",
        "  Full reports written:",
        "    • omega-report.html      (Business + Technical tabs)",
        "    • omega-report-business.md",
        "    • omega-report-technical.md",
        "    • omega-report.json / .csv",
        "═" * 76,
    ]
    return "\n".join(lines)


def build_markdown_business(outcome: RepositoryOutcome) -> str:
    b = outcome.business
    parts = [
        f"# Omega Quality Report — Business Edition",
        f"",
        f"**Repository:** {outcome.repo_display}  ",
        f"**Analyzed:** {outcome.analyzed_at}  ",
        f"**GitHub:** {outcome.github_url or 'Local / custom path'}  ",
        f"",
        f"---",
        f"",
        f"## Executive summary",
        f"",
        b.get("executive_summary", ""),
        f"",
        f"**Grade: {outcome.quality_grade}** · Omega Index **{outcome.omega_index}** (lower is better)  ",
        f"",
        f"## What does this mean for the business?",
        f"",
        b.get("what_omega_means", ""),
        f"",
        f"## Confidence in this assessment",
        f"",
        b.get("confidence", ""),
        f"",
        f"## Business impact",
        f"",
    ]
    for item in b.get("business_impact", []):
        parts.append(f"- {item}")
    parts += ["", "## Priority fixes", ""]
    for item in b.get("priority_fixes", []):
        parts.append(f"- {item}")
    parts += ["", "## Recommended actions", ""]
    for item in b.get("recommendations_business", []):
        parts.append(f"- {item}")
    parts += [
        "",
        "## For stakeholders without a technical background",
        "",
        b.get("for_non_technical_stakeholders", ""),
        "",
        "## Top files to watch (plain language)",
        "",
        "| File | Risk | Why it matters |",
        "|------|------|----------------|",
    ]
    for f in outcome.files[:25]:
        parts.append(
            f"| `{f.path}` | {f.risk_band} | {file_business_blurb(f)} |"
        )
    if len(outcome.files) > 25:
        parts.append(f"| … | … | *{len(outcome.files) - 25} more files in CSV export* |")
    parts += [
        "",
        "## Language breakdown",
        "",
    ]
    for lang, avg in outcome.top_by_language.items():
        parts.append(f"- **{lang}**: average Omega {avg}")
    if outcome.dimensions:
        parts += ["", "## Quality dimensions (this repository)", ""]
        parts.extend(_dimensions_markdown(outcome, audience="business"))
    return "\n".join(parts)


def build_markdown_developer(outcome: RepositoryOutcome) -> str:
    dg = outcome.developer_guide or {}
    parts = [
        "# Omega — Developer Action Guide",
        "",
        f"**Repository:** {outcome.repo_display}  ",
        f"**Analyzed:** {outcome.analyzed_at}  ",
        f"**Ω Index:** {outcome.omega_index} · Grade **{outcome.quality_grade}**",
        "",
        dg.get("introduction", ""),
        "",
        "## How to use this guide",
        "",
    ]
    for line in dg.get("how_to_read", []):
        parts.append(f"- {line}")
    parts += ["", f"## Prioritized actions ({dg.get('action_count', 0)})", ""]
    for act in dg.get("actions", []):
        parts += [
            f"### {act.get('priority', '?')}. {act.get('title', 'Action')}",
            "",
            f"**Location:** `{act.get('location', '')}`  ",
            f"**Risk band:** {act.get('risk_band', '')} · **Category:** {act.get('category', '')}",
            "",
            "#### Why this is risky",
            "",
            act.get("why_risky", ""),
            "",
            "#### What to do (in this repo)",
            "",
        ]
        for step in act.get("what_to_do", []):
            parts.append(f"1. {step}")
        if act.get("implementation_plan"):
            parts += ["", "#### Implementation sketch", ""]
            for block in act["implementation_plan"]:
                parts.append(block)
                parts.append("")
        parts.append("---")
        parts.append("")
    return "\n".join(parts)


def build_markdown_technical(outcome: RepositoryOutcome) -> str:
    t = outcome.technical
    p = outcome.pillars
    parts = [
        "# Omega Quality Report — Technical & Mathematical Edition",
        "",
        f"**Repository:** `{outcome.root}`  ",
        f"**Analyzed:** {outcome.analyzed_at}  ",
        "",
        "## Abstract",
        "",
        t.get("abstract", ""),
        "",
        "## Aggregate results",
        "",
        f"| Quantity | Value |",
        f"|----------|-------|",
        f"| $\\Omega_{{repo}}$ | {outcome.omega_index} |",
        f"| Grade | {outcome.quality_grade} |",
        f"| $\\mathbb{{E}}[Q \\mid \\mathbf{{o}}]$ | {outcome.bayesian_quality} |",
        f"| Epistemic uncertainty | {outcome.epistemic_uncertainty} |",
        f"| $\\bar{{H}}_{{struct}}$ | {p['structural_entropy']} |",
        f"| $\\bar{{H}}_{{text}}$ | {p.get('textual_entropy', 'N/A')} |",
        f"| $\\bar{{C}}_{{cyc}}$ | {p['cyclomatic_pressure']} |",
        f"| $\\bar{{K}}_{{couple}}$ | {p['coupling_field']} |",
        f"| $\\beta_1$ proxy | {int(p['topological_cycles'])} |",
        f"| $\\Omega_{{95}}$ | {p.get('p95_omega_local', 'N/A')} |",
        f"| $\\Omega_{{max}}$ | {p.get('max_omega_local', 'N/A')} |",
        "",
        "## Formal definitions",
        "",
    ]
    for line in t.get("aggregate_formulas", []):
        parts.append(line)
        parts.append("")
    parts += ["## Scan inventory", ""]
    for line in t.get("inventory_technical", []):
        parts.append(f"- {line}")
    parts += ["", "## Methodology", ""]
    for line in t.get("methodology", []):
        parts.append(f"- {line}")
    parts += ["", "## Per-module field (top 50 by Ω)", ""]
    parts += [
        "| Path | Lang | Ω_local | Band | H_s | H_t | M_c | D_nest | K_out | K_in |",
        "|------|------|---------|------|-----|-----|-----|--------|-------|------|",
    ]
    for f in outcome.files[:50]:
        parts.append(
            f"| `{f.path}` | {f.language} | {f.omega_local} | {f.risk_band} | "
            f"{f.h_struct} | {f.h_text} | {f.cyclomatic} | {f.nesting_depth} | "
            f"{f.coupling_out} | {f.coupling_in} |"
        )
    parts += ["", "## Engineering recommendations", ""]
    for r in t.get("recommendations_technical", []):
        parts.append(f"1. {r}")
    if outcome.dimensions:
        parts += ["", "## Multi-dimensional profile (repository-specific)", ""]
        parts.extend(_dimensions_markdown(outcome, audience="technical"))
    parts += ["", "## Limitations", ""]
    for line in t.get("limitations", []):
        parts.append(f"- {line}")
    return "\n".join(parts)


def build_html_report(outcome: RepositoryOutcome) -> str:
    grade_color = {
        "A": "#22c55e",
        "B": "#84cc16",
        "C": "#eab308",
        "D": "#f97316",
        "F": "#ef4444",
    }.get(outcome.quality_grade, "#94a3b8")

    b = outcome.business
    t = outcome.technical
    p = outcome.pillars

    file_rows = ""
    for f in outcome.files:
        rc = {"LOW": "#22c55e", "MEDIUM": "#eab308", "HIGH": "#f97316", "CRITICAL": "#ef4444"}.get(
            f.risk_band, "#94a3b8"
        )
        file_rows += f"""<tr>
          <td><code>{_esc(f.path)}</code></td>
          <td>{_esc(f.language)}</td>
          <td><strong>{f.omega_local}</strong></td>
          <td style="color:{rc}">{f.risk_band}</td>
          <td>{f.h_struct}</td>
          <td>{f.h_text}</td>
          <td>{f.cyclomatic}</td>
          <td>{f.nesting_depth}</td>
          <td>{f.coupling_out}/{f.coupling_in}</td>
          <td class="biz-cell">{_esc(file_business_blurb(f))}</td>
        </tr>"""

    lang_cards = "".join(
        f'<div class="pillar"><span class="lbl">{_esc(lang)}</span><span>{avg}</span></div>'
        for lang, avg in outcome.top_by_language.items()
    )

    biz_impact = "".join(f"<li>{_esc(str(x))}</li>" for x in b.get("business_impact", []))
    biz_fixes = "".join(f"<li>{_esc(str(x))}</li>" for x in b.get("priority_fixes", []))
    biz_recs = "".join(f"<li>{_esc(str(x))}</li>" for x in b.get("recommendations_business", []))
    tech_formulas = "".join(
        f'<p class="formula">{_esc(str(line))}</p>' for line in t.get("aggregate_formulas", [])
    )
    tech_method = "".join(f"<li>{_esc(str(x))}</li>" for x in t.get("methodology", []))
    tech_recs = "".join(f"<li>{_esc(str(x))}</li>" for x in t.get("recommendations_technical", []))
    tech_limits = "".join(f"<li>{_esc(str(x))}</li>" for x in t.get("limitations", []))
    tech_inv = "".join(f"<li>{_esc(str(x))}</li>" for x in t.get("inventory_technical", []))
    dim_html = _dimensions_html(outcome)
    dev_html = _developer_html(outcome)

    inv = outcome.inventory

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Omega Report — {_esc(outcome.repo_display)} — Grade {outcome.quality_grade}</title>
  <style>
    :root {{
      --bg: #0b1220; --card: #151d2e; --border: #2a3548;
      --text: #e8eef7; --muted: #8b9cb3; --accent: #60a5fa;
      --biz: #34d399; --tech: #a78bfa;
    }}
    * {{ box-sizing: border-box; }}
    body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: var(--bg); color: var(--text);
      margin: 0; line-height: 1.55; }}
    .wrap {{ max-width: 1200px; margin: 0 auto; padding: 1.5rem; }}
    header {{ border-bottom: 1px solid var(--border); padding-bottom: 1rem; margin-bottom: 1rem; }}
    h1 {{ font-size: 1.6rem; margin: 0 0 0.25rem; }}
    .meta {{ color: var(--muted); font-size: 0.9rem; }}
    .tabs {{ display: flex; gap: 0.5rem; flex-wrap: wrap; margin: 1rem 0; }}
    .tab {{
      padding: 0.6rem 1.2rem; border: 1px solid var(--border); background: var(--card);
      color: var(--text); border-radius: 8px; cursor: pointer; font-weight: 600;
    }}
    .tab.active {{ border-color: var(--accent); background: #1e3a5f; }}
    .tab.biz.active {{ border-color: var(--biz); background: #064e3b; }}
    .tab.tech.active {{ border-color: var(--tech); background: #3b2667; }}
    .tab.dev.active {{ border-color: #38bdf8; background: #0c4a6e; }}
    .panel {{ display: none; }}
    .panel.active {{ display: block; }}
    .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px;
      padding: 1.25rem; margin: 1rem 0; }}
    .score {{ font-size: 3.5rem; font-weight: 800; color: {grade_color}; text-align: center; }}
    .pillars {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 0.75rem; }}
    .pillar {{ background: #1a2332; padding: 0.75rem; border-radius: 8px; text-align: center; }}
    .pillar .lbl {{ display: block; font-size: 0.7rem; color: var(--muted); text-transform: uppercase; }}
    .pillar span:last-child {{ font-size: 1.2rem; font-weight: 700; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; }}
    th, td {{ padding: 0.45rem 0.5rem; border-bottom: 1px solid var(--border); text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); font-size: 0.68rem; text-transform: uppercase; }}
    .biz-cell {{ max-width: 220px; color: var(--muted); font-size: 0.78rem; }}
    .formula {{ font-family: ui-monospace, monospace; font-size: 0.85rem; color: #c4b5fd;
      background: #1a1528; padding: 0.5rem; border-radius: 6px; margin: 0.35rem 0; white-space: pre-wrap; }}
    .badge {{ display: inline-block; padding: 0.2rem 0.6rem; border-radius: 4px; font-size: 0.75rem;
      font-weight: 700; background: {grade_color}33; color: {grade_color}; }}
    .section-tag {{ font-size: 0.75rem; font-weight: 700; letter-spacing: 0.05em; }}
    .section-tag.biz {{ color: var(--biz); }}
    .section-tag.tech {{ color: var(--tech); }}
    .warn {{ color: #fbbf24; }}
    ul {{ padding-left: 1.2rem; }}
    .dim-grid {{
      display: grid; gap: 1rem;
      grid-template-columns: repeat(auto-fill, minmax(min(100%, 320px), 1fr));
    }}
    .dim-grid > * {{ min-width: 0; }}
    .dim-card {{
      background: #1a2332; border-radius: 10px; padding: 1rem;
      min-width: 0; max-width: 100%; overflow: hidden;
      overflow-wrap: anywhere; word-break: break-word;
    }}
    .dim-card code {{
      display: inline-block; max-width: 100%;
      word-break: break-all; overflow-wrap: anywhere;
    }}
    .dim-ev li, .dim-sym li, .dim-act li {{
      max-width: 100%; overflow-wrap: anywhere; word-break: break-word;
    }}
    .dim-head {{ display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; }}
    .dim-score {{ margin-left: auto; font-weight: 800; font-size: 1.1rem; }}
    .dim-bar {{ font-size: 0.75rem; color: var(--muted); margin: 0.35rem 0; overflow-x: auto; }}
    .dim-summary {{ font-size: 0.88rem; color: var(--muted); margin: 0.5rem 0; }}
    .dim-agg {{ font-size: 0.78rem; color: #94a3b8; }}
    .dim-ev, .dim-sym, .dim-act {{
      font-size: 0.8rem; margin: 0.35rem 0; padding-left: 1rem;
      overflow-wrap: anywhere; word-break: break-word;
    }}
    .dim-act-lbl {{ font-size: 0.72rem; color: var(--biz); margin: 0.5rem 0 0; font-weight: 600; }}
    .dev-card {{ background: #1a2332; border-radius: 10px; padding: 1rem; margin-bottom: 0.75rem; }}
    .dev-priority {{ font-family: ui-monospace, monospace; color: var(--accent); margin-right: 0.5rem; }}
    .mono {{ font-family: ui-monospace, monospace; }}
    @media print {{ .tabs {{ display: none; }} .panel {{ display: block !important; page-break-before: always; }} }}
  </style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>Ω-QFM Quality Report</h1>
    <p class="meta">
      <strong>{_esc(outcome.repo_display)}</strong> · {_esc(outcome.analyzed_at)}<br/>
      Path: <code>{_esc(outcome.root)}</code><br/>
      GitHub: {_esc(outcome.github_url or '—')} · {outcome.file_count:,} files · {outcome.total_loc:,} LOC
    </p>
  </header>

  <div class="card" style="text-align:center">
    <div class="score">{outcome.omega_index}</div>
    <p>Omega Index <span style="color:var(--muted)">(0–100, lower is healthier)</span></p>
    <p>Grade <span class="badge">{outcome.quality_grade}</span>
       · Bayesian Q {_esc(str(outcome.bayesian_quality))}/10
       · Uncertainty {_esc(str(outcome.epistemic_uncertainty))}</p>
  </div>

  <nav class="tabs">
    <button class="tab active" data-panel="overview">Overview</button>
    <button class="tab dev" data-panel="developer">Developer Guide</button>
    <button class="tab biz" data-panel="business">Business Report</button>
    <button class="tab tech" data-panel="technical">Technical / Math Report</button>
    <button class="tab" data-panel="files">All Files ({outcome.file_count})</button>
  </nav>

  <div id="developer" class="panel">
    <div class="card">
      <p class="section-tag" style="color:#38bdf8">FOR DEVELOPERS — WHAT TO FIX &amp; WHY</p>
      {dev_html}
    </div>
  </div>

  <div id="overview" class="panel active">
    <div class="card">
      <p class="section-tag biz">FOR LEADERS & PRODUCT</p>
      <p>{_esc(outcome.health_summary_business)}</p>
      <p style="margin-top:1rem;color:var(--muted)">{_html_prose(b.get('executive_summary', ''))}</p>
    </div>
    <div class="card">
      <p class="section-tag tech">FOR ENGINEERS & ARCHITECTS</p>
      <p>{_esc(outcome.health_summary)}</p>
      <p style="margin-top:1rem;color:var(--muted)">{_esc(t.get('abstract', ''))}</p>
    </div>
    <div class="card">
      <h2>Key metrics at a glance</h2>
      <div class="pillars">
        <div class="pillar"><span class="lbl">H_struct</span><span>{p['structural_entropy']}</span></div>
        <div class="pillar"><span class="lbl">Cyclomatic</span><span>{p['cyclomatic_pressure']}</span></div>
        <div class="pillar"><span class="lbl">Coupling</span><span>{p['coupling_field']}</span></div>
        <div class="pillar"><span class="lbl">β₁ proxy</span><span>{int(p['topological_cycles'])}</span></div>
        <div class="pillar"><span class="lbl">Ω p95</span><span>{p.get('p95_omega_local', '—')}</span></div>
        <div class="pillar"><span class="lbl">Ω max</span><span>{p.get('max_omega_local', '—')}</span></div>
      </div>
    </div>
    <div class="card"><h2>Languages</h2><div class="pillars">{lang_cards or '<p>No data</p>'}</div></div>
    <div class="card">
      <h2>Quality dimensions — {_esc(outcome.repo_display)}</h2>
      <p style="color:var(--muted);font-size:0.9rem">Each dimension cites real files and symbols from this repository (not generic advice).</p>
      <div class="dim-grid">{dim_html}</div>
    </div>
  </div>

  <div id="business" class="panel">
    <div class="card">
      <p class="section-tag biz">BUSINESS REPORT — DETAILED</p>
      <h2>Executive summary</h2>
      <p>{_html_prose(b.get('executive_summary', ''))}</p>
      <h2>What is the Omega Index?</h2>
      <p>{_html_prose(b.get('what_omega_means', ''))}</p>
      <h2>How confident is this report?</h2>
      <p>{_html_prose(b.get('confidence', ''))}</p>
      <h2>Business impact</h2>
      <ul>{biz_impact}</ul>
      <h2>Priority fixes</h2>
      <ul>{biz_fixes}</ul>
      <h2>Recommended actions</h2>
      <ul>{biz_recs}</ul>
      <h2>Guidance for non-technical readers</h2>
      <p>{_html_prose(b.get('for_non_technical_stakeholders', ''))}</p>
      <h2>Quality dimensions (this repo)</h2>
      <div class="dim-grid">{dim_html}</div>
    </div>
  </div>

  <div id="technical" class="panel">
    <div class="card">
      <p class="section-tag tech">TECHNICAL / MATHEMATICAL REPORT — DETAILED</p>
      <h2>Abstract</h2>
      <p>{_esc(t.get('abstract', ''))}</p>
      <h2>Formal definitions &amp; computed values</h2>
      {tech_formulas}
      <h2>Repository inventory</h2>
      <ul>{tech_inv}</ul>
      <h2>Methodology</h2>
      <ul>{tech_method}</ul>
      <h2>Engineering recommendations</h2>
      <ul>{tech_recs}</ul>
      <h2>Multi-dimensional profile (repository-specific)</h2>
      <div class="dim-grid">{dim_html}</div>
      <h2>Known limitations</h2>
      <ul>{tech_limits}</ul>
    </div>
  </div>

  <div id="files" class="panel">
    <div class="card">
      <h2>Complete module table</h2>
      <p style="color:var(--muted)">Sorted by Ω_local (highest risk first). Business column explains each row in plain language.</p>
      <div style="overflow-x:auto">
      <table>
        <thead>
          <tr>
            <th>File</th><th>Lang</th><th>Ω</th><th>Risk</th>
            <th>H_struct</th><th>H_text</th><th>Cyc</th><th>Nest</th><th>Coupling</th><th>Business note</th>
          </tr>
        </thead>
        <tbody>{file_rows}</tbody>
      </table>
      </div>
    </div>
  </div>
</div>
<script>
document.querySelectorAll('.tab').forEach(btn => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(btn.dataset.panel).classList.add('active');
  }});
}});
</script>
</body>
</html>"""


def _report_needs_html_refresh(data: dict, html_text: str | None = None) -> bool:
    if html_text and "Scan capped at" in html_text:
        return True
    inv = data.get("inventory") or {}
    if inv.get("truncated"):
        return True
    tech = data.get("technical_report") or {}
    for line in tech.get("inventory_technical", []):
        if "Scan truncated: yes" in str(line) or "increase --max-files" in str(line):
            return True
    if html_text and "overflow-wrap: anywhere" not in html_text:
        return True
    return False


def outcome_from_report_dict(data: dict) -> RepositoryOutcome:
    """Rebuild a RepositoryOutcome from saved omega-report.json."""
    inv_data = data.get("inventory") or {}
    root = data.get("repository", "")
    inv = RepoInventory(
        root=Path(root),
        files=[],
        by_language=dict(inv_data.get("by_language", {})),
        total_bytes=int(inv_data.get("total_bytes", 0)),
    )
    files = [
        FileMetrics(
            path=f["path"],
            loc=int(f.get("loc", 0)),
            cyclomatic=int(f.get("cyclomatic", 0)),
            nesting_depth=int(f.get("nesting_depth", 0)),
            h_struct=float(f.get("h_struct", 0)),
            h_text=float(f.get("h_text", 0)),
            compression_ratio=float(f.get("compression_ratio", 0)),
            coupling_out=int(f.get("coupling_out", 0)),
            coupling_in=int(f.get("coupling_in", 0)),
            omega_local=float(f["omega_local"]),
            risk_band=str(f.get("risk_band", "LOW")),
            language=str(f.get("language", "unknown")),
        )
        for f in data.get("files", [])
    ]
    entities = [
        EntityMetrics(
            entity_type=str(e.get("entity_type", "")),
            qualified_name=str(e.get("qualified_name", "")),
            file_path=str(e.get("file_path", "")),
            line_start=int(e.get("line_start", 0)),
            line_end=int(e.get("line_end", 0)),
            loc=int(e.get("loc", 0)),
            cyclomatic=int(e.get("cyclomatic", 0)),
            nesting_depth=int(e.get("nesting_depth", 0)),
            omega_local=float(e.get("omega_local", 0)),
            risk_band=str(e.get("risk_band", "LOW")),
            improvement_areas=tuple(e.get("improvement_areas", [])),
            improvement_areas_business=tuple(e.get("improvement_areas_business", [])),
            implementation_plan=tuple(e.get("implementation_plan", [])),
            implementation_summary=tuple(e.get("implementation_summary", [])),
            implementation_diffs=tuple(e.get("implementation_diffs", [])),
            parent_class=e.get("parent_class"),
            parameter_count=int(e.get("parameter_count", 0)),
            method_count=int(e.get("method_count", 0)),
            field_count=int(e.get("field_count", 0)),
        )
        for e in data.get("entities", [])
    ]
    outcome = RepositoryOutcome(
        root=root,
        repo_display=str(data.get("repo_display", "")),
        github_url=data.get("github_url"),
        analyzed_at=str(data.get("analyzed_at", "")),
        omega_index=float(data.get("omega_index", 0)),
        quality_grade=str(data.get("quality_grade", "F")),
        health_summary=str(data.get("health_summary_technical", "")),
        health_summary_business=str(data.get("health_summary_business", "")),
        file_count=int(data.get("file_count", len(files))),
        total_loc=int(data.get("total_loc", 0)),
        pillars=dict(data.get("pillars", {})),
        files=files,
        hotspots=list(data.get("hotspots", [])),
        recommendations=list(data.get("recommendations_technical", [])),
        recommendations_business=list(data.get("recommendations_business", [])),
        bayesian_quality=float(data.get("bayesian_quality", 0)),
        epistemic_uncertainty=float(data.get("epistemic_uncertainty", 0)),
        inventory=inv,
        business=dict(data.get("business_report", {})),
        technical=dict(data.get("technical_report", {})),
        top_by_language=dict(data.get("languages", {})),
        entities=entities,
        entity_summary=dict(data.get("entity_summary", {})),
        entity_hotspots=list(data.get("entity_hotspots", [])),
        improvement_plan=list(data.get("improvement_plan", [])),
        developer_guide=dict(data.get("developer_guide", {})),
        dimensions=list(data.get("dimensions", [])),
        metric_suite=dict(data.get("metric_suite", {})),
    )
    if _report_needs_html_refresh(data):
        outcome.business = build_business_sections(outcome)
        outcome.technical = build_technical_sections(outcome)
    return outcome


def refresh_stored_html_report(output_dir: Path) -> Path:
    """Regenerate omega-report.html from JSON using the current template."""
    output_dir = Path(output_dir)
    json_path = output_dir / "omega-report.json"
    html_path = output_dir / "omega-report.html"
    if not json_path.exists():
        raise FileNotFoundError(json_path)
    data = json.loads(json_path.read_text(encoding="utf-8"))
    data, _ = ensure_report_has_dimensions(data)
    data, _ = ensure_report_has_developer_guide(data)
    html_existing = html_path.read_text(encoding="utf-8") if html_path.exists() else None
    if not _report_needs_html_refresh(data, html_existing) and html_path.exists():
        return html_path
    outcome = outcome_from_report_dict(data)
    html_path.write_text(build_html_report(outcome), encoding="utf-8")
    tech_path = output_dir / "omega-report-technical.md"
    biz_path = output_dir / "omega-report-business.md"
    tech_path.write_text(build_markdown_technical(outcome), encoding="utf-8")
    biz_path.write_text(build_markdown_business(outcome), encoding="utf-8")
    inv = data.get("inventory") or {}
    inv.pop("truncated", None)
    inv.pop("max_files", None)
    data["inventory"] = inv
    data["business_report"] = outcome.business
    data["technical_report"] = outcome.technical
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return html_path


def _outcome_to_dict(outcome: RepositoryOutcome) -> dict:
    inv = outcome.inventory
    return {
        "repository": outcome.root,
        "repo_display": outcome.repo_display,
        "github_url": outcome.github_url,
        "analyzed_at": outcome.analyzed_at,
        "omega_index": outcome.omega_index,
        "quality_grade": outcome.quality_grade,
        "bayesian_quality": outcome.bayesian_quality,
        "epistemic_uncertainty": outcome.epistemic_uncertainty,
        "health_summary_technical": outcome.health_summary,
        "health_summary_business": outcome.health_summary_business,
        "file_count": outcome.file_count,
        "total_loc": outcome.total_loc,
        "pillars": outcome.pillars,
        "dimensions": outcome.dimensions,
        "metric_suite": outcome.metric_suite,
        "developer_guide": outcome.developer_guide,
        "hotspots": outcome.hotspots,
        "languages": outcome.top_by_language,
        "inventory": {
            "by_language": inv.by_language if inv else {},
            "total_bytes": inv.total_bytes if inv else 0,
        },
        "recommendations_technical": outcome.recommendations,
        "recommendations_business": outcome.recommendations_business,
        "business_report": outcome.business,
        "technical_report": outcome.technical,
        "files": [
            {
                "path": f.path,
                "language": f.language,
                "omega_local": f.omega_local,
                "risk_band": f.risk_band,
                "business_note": file_business_blurb(f),
                "loc": f.loc,
                "cyclomatic": f.cyclomatic,
                "nesting_depth": f.nesting_depth,
                "h_struct": f.h_struct,
                "h_text": f.h_text,
                "coupling_out": f.coupling_out,
                "coupling_in": f.coupling_in,
                "compression_ratio": f.compression_ratio,
            }
            for f in outcome.files
        ],
        "agent_manifest": outcome.agent_manifest,
        "entity_summary": outcome.entity_summary,
        "entity_hotspots": outcome.entity_hotspots,
        "improvement_plan": outcome.improvement_plan,
        "entities": [
            {
                "entity_type": e.entity_type,
                "qualified_name": e.qualified_name,
                "file_path": e.file_path,
                "line_start": e.line_start,
                "line_end": e.line_end,
                "loc": e.loc,
                "cyclomatic": e.cyclomatic,
                "nesting_depth": e.nesting_depth,
                "omega_local": e.omega_local,
                "risk_band": e.risk_band,
                "parent_class": e.parent_class,
                "parameter_count": e.parameter_count,
                "method_count": e.method_count,
                "field_count": e.field_count,
                "improvement_areas": list(e.improvement_areas),
                "improvement_areas_business": list(e.improvement_areas_business),
                "implementation_plan": list(e.implementation_plan),
                "implementation_summary": list(e.implementation_summary),
                "implementation_diffs": [dict(d) for d in e.implementation_diffs],
            }
            for e in outcome.entities
        ],
    }


def _write_csv(outcome: RepositoryOutcome, path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "path",
                "language",
                "omega_local",
                "risk_band",
                "loc",
                "cyclomatic",
                "nesting_depth",
                "h_struct",
                "h_text",
                "coupling_out",
                "coupling_in",
                "compression_ratio",
                "business_note",
            ]
        )
        for fm in outcome.files:
            w.writerow(
                [
                    fm.path,
                    fm.language,
                    fm.omega_local,
                    fm.risk_band,
                    fm.loc,
                    fm.cyclomatic,
                    fm.nesting_depth,
                    fm.h_struct,
                    fm.h_text,
                    fm.coupling_out,
                    fm.coupling_in,
                    fm.compression_ratio,
                    file_business_blurb(fm),
                ]
            )


def build_report(outcome: RepositoryOutcome, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    paths["txt"] = output_dir / "omega-summary.txt"
    paths["txt"].write_text(format_terminal_report(outcome), encoding="utf-8")

    paths["html"] = output_dir / "omega-report.html"
    paths["html"].write_text(build_html_report(outcome), encoding="utf-8")

    paths["json"] = output_dir / "omega-report.json"
    payload = _outcome_to_dict(outcome)
    if "dimensions" not in payload:
        payload, _ = ensure_report_has_dimensions(payload)
    if "developer_guide" not in payload:
        payload, _ = ensure_report_has_developer_guide(payload)
    paths["json"].write_text(json.dumps(payload, indent=2), encoding="utf-8")

    paths["md_business"] = output_dir / "omega-report-business.md"
    paths["md_business"].write_text(build_markdown_business(outcome), encoding="utf-8")

    paths["md_technical"] = output_dir / "omega-report-technical.md"
    paths["md_technical"].write_text(build_markdown_technical(outcome), encoding="utf-8")

    paths["md_developer"] = output_dir / "omega-report-developer.md"
    paths["md_developer"].write_text(build_markdown_developer(outcome), encoding="utf-8")

    paths["csv"] = output_dir / "omega-files.csv"
    _write_csv(outcome, paths["csv"])

    paths["csv_entities"] = output_dir / "omega-entities.csv"
    _write_entities_csv(outcome, paths["csv_entities"])

    paths["md_implementations"] = output_dir / "omega-implementations.md"
    paths["md_implementations"].write_text(
        _build_implementations_markdown(outcome), encoding="utf-8"
    )

    return paths


def _build_implementations_markdown(outcome: RepositoryOutcome) -> str:
    lines = [
        "# Omega — Repo-Contextual Implementation Guide",
        "",
        f"**Repository:** {outcome.repo_display}  ",
        f"**Path:** `{outcome.root}`  ",
        "",
        "Each section below is a **concrete change in your codebase** (file paths, line ranges, "
        "and copy-pasteable code sketches using your actual symbol names).",
        "",
    ]
    count = 0
    for e in outcome.entities:
        if not e.implementation_plan:
            continue
        count += 1
        lines.append(f"## {count}. `{e.qualified_name}` ({e.entity_type})")
        lines.append(
            f"**File:** `{e.file_path}` · **Lines:** {e.line_start}–{e.line_end} · "
            f"**Ω:** {e.omega_local} · **Risk:** {e.risk_band}"
        )
        lines.append("")
        for block in e.implementation_plan:
            lines.append(block)
            lines.append("")
    if count == 0:
        lines.append("_No implementation refactors required at symbol level._")
    return "\n".join(lines)


def _write_entities_csv(outcome: RepositoryOutcome, path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "entity_type",
                "qualified_name",
                "file_path",
                "line_start",
                "line_end",
                "omega_local",
                "risk_band",
                "loc",
                "cyclomatic",
                "nesting_depth",
                "parameter_count",
                "parent_class",
                "improvement_areas",
                "improvement_areas_business",
                "has_implementation_plan",
            ]
        )
        for e in outcome.entities:
            w.writerow(
                [
                    e.entity_type,
                    e.qualified_name,
                    e.file_path,
                    e.line_start,
                    e.line_end,
                    e.omega_local,
                    e.risk_band,
                    e.loc,
                    e.cyclomatic,
                    e.nesting_depth,
                    e.parameter_count,
                    e.parent_class or "",
                    " | ".join(e.improvement_areas),
                    " | ".join(e.improvement_areas_business),
                    "yes" if e.implementation_plan else "no",
                ]
            )
