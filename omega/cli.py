"""CLI entry point — local paths and GitHub repositories."""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

from omega.analyzer import analyze_repository
from omega.api.store import RunStore
from omega.api.targets import can_rerun_target
from omega.github import clone_github_repo, is_github_target, parse_github_target
from omega.report import build_report, format_terminal_report


def _cli_rerun(args: argparse.Namespace) -> None:
    store = RunStore()
    record = store.get(args.rerun.strip())
    if not record:
        print(f"Error: run not found: {args.rerun}", file=sys.stderr)
        sys.exit(1)
    err = can_rerun_target(record.target)
    if err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)

    temp_root: Path | None = None
    try:
        cache = Path(args.cache_dir).expanduser() if args.cache_dir else None
        root, github_url, display, is_temp = _resolve_target(
            record.target,
            keep_clone=args.keep_clone,
            cache_dir=cache,
        )
        if is_temp:
            temp_root = root
        if github_url is None and record.github_url:
            github_url = record.github_url
        if display != record.repo_display:
            display = record.repo_display

        print(f"Re-analyzing {display} (from run {record.id}) …", file=sys.stderr)
        outcome = analyze_repository(
            root,
            github_url=github_url,
            repo_display=display,
        )
        out_dir = Path(args.out)
        if not out_dir.is_absolute():
            out_dir = Path.cwd() / out_dir
        paths = build_report(outcome, out_dir)
        print(format_terminal_report(outcome))
        print(f"\nRe-run complete → {out_dir.resolve()}/\n")
        for label, key in [
            ("HTML (Business + Technical tabs)", "html"),
            ("Business Markdown", "md_business"),
            ("Technical Markdown", "md_technical"),
            ("JSON (full data)", "json"),
            ("CSV (all files)", "csv"),
            ("Summary", "txt"),
        ]:
            if key in paths:
                print(f"  {label:<36} {paths[key].name}")
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if temp_root and temp_root.exists() and not args.keep_clone:
            shutil.rmtree(temp_root, ignore_errors=True)


def _resolve_target(target: str, *, keep_clone: bool, cache_dir: Path | None) -> tuple[Path, str | None, str, bool]:
    """
    Returns (root_path, github_url, display_name, is_temp_clone).
    """
    parsed = parse_github_target(target)
    if parsed:
        owner, repo = parsed
        github_url = f"https://github.com/{owner}/{repo}"
        display = f"{owner}/{repo}"
        if cache_dir:
            dest = cache_dir / f"{owner}-{repo}"
            if dest.exists():
                root = dest.resolve()
                return root, github_url, display, False
            root = clone_github_repo(owner, repo, dest=dest)
            return root, github_url, display, False
        root = clone_github_repo(owner, repo)
        return root, github_url, display, not keep_clone

    root = Path(target).resolve()
    if not root.exists():
        raise FileNotFoundError(f"Path does not exist: {root}")
    return root, None, root.name, False


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="omega",
        description=(
            "Ω-QFM: Analyze any GitHub repo or local path. "
            "Produces detailed Business + Technical reports."
        ),
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=".",
        help=(
            "GitHub URL (https://github.com/owner/repo), owner/repo shorthand, "
            "or local directory path"
        ),
    )
    parser.add_argument(
        "--out",
        type=str,
        default="omega-output",
        help="Output directory for reports (default: omega-output)",
    )
    parser.add_argument(
        "--keep-clone",
        action="store_true",
        help="Keep temporary git clone (only for GitHub without --cache-dir)",
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        default=None,
        help="Reuse clones under this directory (e.g. ~/.omega/repos)",
    )
    parser.add_argument(
        "--rerun",
        metavar="RUN_ID",
        default=None,
        help="Re-run analysis using target from a stored dashboard run (~/.omega/data/runs/)",
    )
    args = parser.parse_args()

    if args.rerun:
        _cli_rerun(args)
        return

    temp_root: Path | None = None
    try:
        cache = Path(args.cache_dir).expanduser() if args.cache_dir else None
        root, github_url, display, is_temp = _resolve_target(
            args.target,
            keep_clone=args.keep_clone,
            cache_dir=cache,
        )
        if is_temp:
            temp_root = root

        print(f"Analyzing {display} …", file=sys.stderr)
        outcome = analyze_repository(
            root,
            github_url=github_url,
            repo_display=display,
        )
        out_dir = Path(args.out)
        if not out_dir.is_absolute():
            out_dir = Path.cwd() / out_dir

        paths = build_report(outcome, out_dir)
        print(format_terminal_report(outcome))
        print(f"\nDetailed reports → {out_dir.resolve()}/\n")
        for label, key in [
            ("HTML (Business + Technical tabs)", "html"),
            ("Business Markdown", "md_business"),
            ("Technical Markdown", "md_technical"),
            ("JSON (full data)", "json"),
            ("CSV (all files)", "csv"),
            ("Summary", "txt"),
        ]:
            if key in paths:
                print(f"  {label:<36} {paths[key].name}")
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if temp_root and temp_root.exists() and not args.keep_clone:
            shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    main()
