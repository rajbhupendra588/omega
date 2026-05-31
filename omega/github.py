"""Clone and resolve GitHub repositories for analysis."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

_GITHUB_RE = re.compile(
    r"^(?:https?://)?(?:www\.)?github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$",
    re.IGNORECASE,
)
_SHORT_RE = re.compile(r"^([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)$")


def parse_github_target(target: str) -> tuple[str, str] | None:
    """Return (owner, repo) from URL or owner/repo shorthand."""
    target = target.strip().rstrip("/")
    m = _GITHUB_RE.match(target)
    if m:
        return m.group(1), m.group(2)
    m = _SHORT_RE.match(target)
    if m:
        return m.group(1), m.group(2)
    if "github.com" in target:
        parsed = urlparse(target if "://" in target else f"https://{target}")
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) >= 2:
            return parts[0], parts[1].replace(".git", "")
    return None


def clone_github_repo(
    owner: str,
    repo: str,
    *,
    depth: int = 1,
    dest: Path | None = None,
) -> Path:
    """Shallow-clone a public GitHub repository into dest or a temp directory."""
    url = f"https://github.com/{owner}/{repo}.git"
    if dest is None:
        dest = Path(tempfile.mkdtemp(prefix=f"omega-{owner}-{repo}-"))
    else:
        dest = Path(dest)
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True, exist_ok=True)

    cmd = [
        "git",
        "clone",
        "--depth",
        str(depth),
        "--single-branch",
        url,
        str(dest),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to clone {url}: {result.stderr.strip() or result.stdout}"
        )
    return dest.resolve()


def is_github_target(target: str) -> bool:
    return parse_github_target(target) is not None
