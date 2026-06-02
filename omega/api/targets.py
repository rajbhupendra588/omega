"""Validate analysis targets for new runs and reruns."""

from __future__ import annotations

from pathlib import Path

from omega.github import is_github_target, parse_github_target

_UPLOAD_TARGET_PREFIX = "upload://"


def target_metadata(target: str) -> tuple[str, str, str | None]:
    """
    Normalize target and return (target, repo_display, github_url).
    Raises ValueError with a user-facing message when invalid.
    """
    raw = target.strip()
    if not raw:
        raise ValueError("Target is required")

    parsed = parse_github_target(raw)
    if parsed:
        display = f"{parsed[0]}/{parsed[1]}"
        github_url = f"https://github.com/{parsed[0]}/{parsed[1]}"
        return raw, display, github_url

    path = Path(raw).expanduser()
    if path.exists():
        return raw, path.name, None

    if is_github_target(raw):
        raise ValueError("Could not parse GitHub target")

    raise ValueError(
        "Provide a valid GitHub URL (owner/repo) or an existing local directory path"
    )


def can_rerun_target(target: str) -> str | None:
    """Return an error message if rerun is not feasible, else None."""
    if target.strip().startswith(_UPLOAD_TARGET_PREFIX):
        return "Uploaded zip analyses cannot be re-run automatically; upload again."
    try:
        _, _, github_url = target_metadata(target)
    except ValueError as e:
        return str(e)
    if github_url:
        return None
    path = Path(target.strip()).expanduser()
    if not path.exists():
        return f"Local path no longer exists: {path}"
    if not path.is_dir():
        return f"Local path is not a directory: {path}"
    return None
