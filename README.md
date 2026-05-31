# Omega (Ω-QFM)

Analyze **any GitHub repository** or local project. Get a **detailed dual report**:

1. **Business report** — plain language for leaders, PMs, and non-technical stakeholders  
2. **Technical report** — formulas, methodology, and per-module mathematical metrics  

## Quick start

```bash
cd /Users/bhupendra/omega
pip install -e .

# Local folder
omega sample_repo

# Any public GitHub repo
omega https://github.com/psf/requests
omega psf/requests

# Save reports
omega psf/requests --out ./my-reports
```

## Open the final outcome

| File | Audience |
|------|----------|
| **`omega-report.html`** | Everyone — tabs: Overview, **Business**, **Technical**, All Files |
| `omega-report-business.md` | Executives, product, business |
| `omega-report-technical.md` | Engineers, architects, researchers |
| `omega-files.csv` | Spreadsheets, BI tools |
| `omega-report.json` | CI/CD, custom dashboards |

## Options

```bash
omega owner/repo --cache-dir ~/.omega/repos   # reuse clones
omega . --out reports
```

Scans include **all** discoverable source files in the repository (no file-count cap).

## Supported languages

Python (full AST), plus heuristic analysis for JavaScript, TypeScript, Java, Go, Rust, C/C++, C#, Ruby, PHP, Kotlin, Swift, Scala, and more.

## Web dashboard (world-class UI)

Run analysis and view **Business + Technical** reports in the browser.

```bash
cd /Users/bhupendra/omega
chmod +x scripts/start-ui.sh
./scripts/start-ui.sh
```

Open **http://127.0.0.1:8765**

- **Dashboard** — history of all analyses  
- **New Analysis** — paste any public `owner/repo` or GitHub URL  
- **Report view** — Overview, **Improvements** (per class/method/field), **Symbols** table, Business, Technical, Files, exports
- **Granular analysis** — every class, method, and field measured with specific improvement areas  

Development (hot reload frontend):

```bash
# Terminal 1
pip install -e ".[ui]"
omega-ui

# Terminal 2
cd dashboard && npm install && npm run dev
# Open http://127.0.0.1:5173
```

## Requirements

- Python 3.10+
- `git` on PATH (for GitHub URLs)
- Node.js 18+ (to build dashboard, or use `scripts/start-ui.sh` which builds once)
