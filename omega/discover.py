"""Discover analyzable source files in any repository."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Extensions → language id
_LANG_MAP: dict[str, str] = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".kt": "kotlin",
    ".swift": "swift",
    ".scala": "scala",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".c": "c",
    ".h": "c",
    ".hpp": "cpp",
    ".m": "objc",
    ".mm": "objc",
    ".vue": "vue",
    ".sql": "sql",
    ".sh": "shell",
    ".bash": "shell",
}

_SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "target",
    "out",
    ".venv",
    "venv",
    "env",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    "coverage",
    "htmlcov",
    ".next",
    ".nuxt",
    "bower_components",
    "Pods",
    "DerivedData",
    ".gradle",
    "gradle",
    ".idea",
    ".vscode",
    "site-packages",
    "egg-info",
    ".eggs",
    "omega-output",
    ".omega-cache",
}

_SKIP_EXTENSIONS = {
    ".min.js",
    ".bundle.js",
    ".map",
    ".lock",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".svg",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".jar",
    ".war",
    ".class",
    ".o",
    ".so",
    ".dll",
    ".exe",
    ".pyc",
    ".pyo",
    ".whl",
}


@dataclass(frozen=True)
class SourceFile:
    path: Path
    rel_path: str
    language: str
    size_bytes: int


@dataclass
class RepoInventory:
    root: Path
    files: list[SourceFile]
    by_language: dict[str, int]
    total_bytes: int


def discover_source_files(root: Path) -> RepoInventory:
    root = root.resolve()
    found: list[SourceFile] = []

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        name_lower = path.name.lower()
        if any(name_lower.endswith(ext) for ext in _SKIP_EXTENSIONS):
            continue
        ext = path.suffix.lower()
        if ext not in _LANG_MAP:
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > 512_000:  # skip huge single files
            continue
        rel = str(path.relative_to(root))
        found.append(
            SourceFile(
                path=path,
                rel_path=rel,
                language=_LANG_MAP[ext],
                size_bytes=size,
            )
        )

    by_lang: dict[str, int] = {}
    for f in found:
        by_lang[f.language] = by_lang.get(f.language, 0) + 1

    return RepoInventory(
        root=root,
        files=found,
        by_language=dict(sorted(by_lang.items(), key=lambda x: -x[1])),
        total_bytes=sum(f.size_bytes for f in found),
    )
