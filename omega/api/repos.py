"""Stable repository identity for run history grouping."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote, unquote

from omega.github import parse_github_target


def compute_repo_key(
    target: str,
    *,
    github_url: str | None = None,
    repo_display: str | "",
) -> str:
    """
    Canonical key for grouping runs of the same repository.
    GitHub: github:owner/repo (lowercase owner/repo).
    Local: local:<resolved absolute path>.
    """
    parsed = parse_github_target(target)
    if parsed:
        owner, repo = parsed
        return f"github:{owner.lower()}/{repo.lower()}"

    if github_url:
        tail = github_url.rstrip("/").split("/")[-2:]
        if len(tail) == 2:
            return f"github:{tail[0].lower()}/{tail[1].lower()}"

    if repo_display and "/" in repo_display and not repo_display.startswith("/"):
        parts = repo_display.split("/", 1)
        if len(parts) == 2 and parts[0] and parts[1]:
            return f"github:{parts[0].lower()}/{parts[1].lower()}"

    path = Path(target.strip()).expanduser()
    try:
        resolved = str(path.resolve())
    except OSError:
        resolved = str(path)
    return f"local:{resolved}"


def repo_key_for_run(
    target: str,
    github_url: str | None,
    repo_display: str,
    existing_key: str = "",
) -> str:
    if existing_key:
        return existing_key
    return compute_repo_key(target, github_url=github_url, repo_display=repo_display)


def encode_repo_key(repo_key: str) -> str:
    return quote(repo_key, safe="")


def decode_repo_key(encoded: str) -> str:
    return unquote(encoded)
