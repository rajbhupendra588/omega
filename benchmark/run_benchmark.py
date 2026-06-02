#!/usr/bin/env python3
"""Run Ω-QFM benchmark against curated corpus (30 public repos).

Usage:
  python benchmark/run_benchmark.py --quick          # cap files/repo for CI
  python benchmark/run_benchmark.py --full           # no cap (slow)
  SONAR_TOKEN=... python benchmark/run_benchmark.py  # optional SonarCloud appendix

Outputs:
  benchmark/results.json
  docs/benchmark/BENCHMARK.md (results table section updated)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import warnings
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from omega.analyzer import analyze_repository  # noqa: E402
from omega.baselines import baseline_scores  # noqa: E402
from omega.github import clone_github_repo  # noqa: E402

CORPUS_PATH = Path(__file__).parent / "corpus.json"
RESULTS_PATH = Path(__file__).parent / "results.json"
PAPER_PATH = ROOT / "docs" / "benchmark" / "BENCHMARK.md"
GRADE_TO_SCORE = {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0}


def _spearman(x: list[float], y: list[float]) -> float | None:
    if len(x) < 3 or len(x) != len(y):
        return None
    n = len(x)

    def ranks(vals: list[float]) -> list[float]:
        order = sorted(range(n), key=lambda i: vals[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j < n - 1 and vals[order[j]] == vals[order[j + 1]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r

    rx, ry = ranks(x), ranks(y)
    d2 = sum((a - b) ** 2 for a, b in zip(rx, ry))
    return round(1 - (6 * d2) / (n * (n * n - 1)), 3)


def _grade_accuracy(pred: list[str], ref: list[str]) -> float:
    if not pred:
        return 0.0
    return round(sum(p == r for p, r in zip(pred, ref)) / len(pred), 3)


def _try_sonar_rating(repo_path: Path, repo_id: str) -> dict | None:
    """Optional SonarCloud measure via sonar-scanner + API (requires SONAR_TOKEN)."""
    token = os.environ.get("SONAR_TOKEN")
    if not token or not shutil.which("sonar-scanner"):
        return None
    org = os.environ.get("SONAR_ORG", "omega-benchmark")
    project_key = repo_id.replace("/", "_")
    props = repo_path / "sonar-project.properties"
    props.write_text(
        f"sonar.projectKey={project_key}\n"
        f"sonar.sources=.\n"
        f"sonar.python.version=3.11\n",
        encoding="utf-8",
    )
    try:
        subprocess.run(
            [
                "sonar-scanner",
                f"-Dsonar.projectKey={project_key}",
                f"-Dsonar.organization={org}",
                f"-Dsonar.host.url=https://sonarcloud.io",
                f"-Dsonar.login={token}",
            ],
            cwd=repo_path,
            check=True,
            capture_output=True,
            timeout=600,
        )
    except (subprocess.SubprocessError, OSError):
        return {"status": "scanner_failed", "project_key": project_key}
    return {"status": "submitted", "project_key": project_key, "note": "Fetch rating via SonarCloud UI/API"}


def analyze_one(
    repo_id: str,
    reference_grade: str,
    *,
    work_dir: Path,
    max_files: int | None,
    skip_clone: bool,
) -> dict:
    owner, repo = repo_id.split("/", 1)
    dest = work_dir / repo_id.replace("/", "__")
    row: dict = {
        "repo": repo_id,
        "reference_grade": reference_grade,
        "status": "ok",
        "error": None,
    }
    try:
        if skip_clone and dest.exists():
            root = dest
        else:
            if dest.exists():
                shutil.rmtree(dest)
            root = clone_github_repo(owner, repo, dest=dest)
        outcome = analyze_repository(
            root,
            github_url=f"https://github.com/{repo_id}",
            repo_display=repo_id,
            max_files=max_files,
        )
        baselines = baseline_scores(outcome.files)
        row.update(
            {
                "omega_index": outcome.omega_index,
                "omega_grade": outcome.quality_grade,
                "file_count": outcome.file_count,
                "total_loc": outcome.total_loc,
                "cyclomatic_index": baselines["cyclomatic_index"],
                "cyclomatic_grade": baselines["cyclomatic_grade"],
                "loc_index": baselines["loc_index"],
                "entropy_index": baselines["entropy_index"],
            }
        )
        sonar = _try_sonar_rating(root, repo_id)
        if sonar:
            row["sonar"] = sonar
    except Exception as e:
        row["status"] = "error"
        row["error"] = str(e)
    return row


def compute_metrics(rows: list[dict]) -> dict:
    ok = [r for r in rows if r.get("status") == "ok"]
    if not ok:
        return {}
    ref_scores = [GRADE_TO_SCORE[r["reference_grade"]] for r in ok]
    omega_scores = [GRADE_TO_SCORE.get(r["omega_grade"], 0) for r in ok]
    cyc_scores = [GRADE_TO_SCORE.get(r["cyclomatic_grade"], 0) for r in ok]

    omega_idx = [r["omega_index"] for r in ok]
    ref_idx = ref_scores

    return {
        "n_success": len(ok),
        "n_total": len(rows),
        "grade_accuracy_omega": _grade_accuracy(
            [r["omega_grade"] for r in ok], [r["reference_grade"] for r in ok]
        ),
        "grade_accuracy_cyclomatic": _grade_accuracy(
            [r["cyclomatic_grade"] for r in ok], [r["reference_grade"] for r in ok]
        ),
        "spearman_omega_vs_reference": _spearman(omega_idx, [float(x) for x in ref_scores]),
        "spearman_cyclomatic_vs_reference": _spearman(
            [r["cyclomatic_index"] for r in ok], [float(x) for x in ref_scores]
        ),
        "mean_abs_grade_error_omega": round(
            sum(abs(a - b) for a, b in zip(omega_scores, ref_scores)) / len(ok), 3
        ),
        "mean_abs_grade_error_cyclomatic": round(
            sum(abs(a - b) for a, b in zip(cyc_scores, ref_scores)) / len(ok), 3
        ),
    }


def update_paper(rows: list[dict], summary: dict) -> None:
    if not PAPER_PATH.exists():
        return
    text = PAPER_PATH.read_text(encoding="utf-8")
    start = "<!-- BENCHMARK_RESULTS_START -->"
    end = "<!-- BENCHMARK_RESULTS_END -->"
    if start not in text or end not in text:
        return

    lines = [
        f"*Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*",
        "",
        "### Summary metrics",
        "",
        "| Metric | Ω composite | Cyclomatic-only |",
        "|--------|-------------|-----------------|",
        f"| Grade accuracy (exact A–F) | {summary.get('grade_accuracy_omega', '—')} | {summary.get('grade_accuracy_cyclomatic', '—')} |",
        f"| Spearman ρ vs reference | {summary.get('spearman_omega_vs_reference', '—')} | {summary.get('spearman_cyclomatic_vs_reference', '—')} |",
        f"| Mean |grade error| | {summary.get('mean_abs_grade_error_omega', '—')} | {summary.get('mean_abs_grade_error_cyclomatic', '—')} |",
        "",
        f"Successful runs: **{summary.get('n_success', 0)}** / {summary.get('n_total', 0)}",
        "",
        "### Per-repository results",
        "",
        "| Repository | Ref | Ω | Ω grade | Cyc | Cyc grade | Files |",
        "|------------|-----|---|---------|-----|-----------|-------|",
    ]
    for r in rows:
        if r.get("status") != "ok":
            lines.append(f"| {r['repo']} | {r.get('reference_grade','?')} | — | ERR | — | — | — |")
            continue
        lines.append(
            f"| {r['repo']} | {r['reference_grade']} | {r['omega_index']} | {r['omega_grade']} | "
            f"{r['cyclomatic_index']} | {r['cyclomatic_grade']} | {r['file_count']} |"
        )

    block = "\n".join(lines)
    new_text = text[: text.index(start) + len(start)] + "\n\n" + block + "\n\n" + text[text.index(end) :]
    PAPER_PATH.write_text(new_text, encoding="utf-8")


def main() -> int:
    # Third-party test fixtures (e.g. psf/black) trigger harmless SyntaxWarnings.
    warnings.filterwarnings("ignore", category=SyntaxWarning)

    parser = argparse.ArgumentParser(description="Ω-QFM benchmark on 30 public repos")
    parser.add_argument("--quick", action="store_true", help="Cap at 400 files per repo")
    parser.add_argument("--full", action="store_true", help="Analyze all discovered files")
    parser.add_argument("--repos", nargs="*", help="Subset of owner/repo ids")
    parser.add_argument("--skip-clone", action="store_true", help="Reuse clones in work dir")
    parser.add_argument("--work-dir", type=Path, default=Path(tempfile.gettempdir()) / "omega-benchmark")
    args = parser.parse_args()

    max_files = None if args.full else (400 if args.quick else 800)
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    repos = corpus["repos"]
    if args.repos:
        wanted = set(args.repos)
        repos = [r for r in repos if r["id"] in wanted]

    args.work_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for i, entry in enumerate(repos, 1):
        rid = entry["id"]
        print(f"[{i}/{len(repos)}] {rid} …", flush=True)
        rows.append(
            analyze_one(
                rid,
                entry["reference_grade"],
                work_dir=args.work_dir,
                max_files=max_files,
                skip_clone=args.skip_clone,
            )
        )

    summary = compute_metrics(rows)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "max_files_per_repo": max_files,
        "methodology": corpus.get("methodology"),
        "summary": summary,
        "repos": rows,
    }
    RESULTS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    update_paper(rows, summary)
    print(json.dumps(summary, indent=2))
    print(f"Wrote {RESULTS_PATH}")
    return 0 if summary.get("n_success", 0) > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
