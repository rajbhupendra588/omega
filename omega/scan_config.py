"""Scan limits — tune via environment without code changes."""

from __future__ import annotations

import os


def default_max_files() -> int | None:
    """
    Cap analyzable source files per run (largest production files kept).
    Set OMEGA_MAX_FILES=0 or unlimited for no cap.
    """
    raw = os.environ.get("OMEGA_MAX_FILES", "350").strip().lower()
    if raw in ("", "none", "0", "unlimited", "off"):
        return None
    return max(1, int(raw))


def skip_test_paths() -> bool:
    """Skip test/support trees (guava-tests, __tests__, etc.) — major speedup on library repos."""
    return os.environ.get("OMEGA_SKIP_TEST_PATHS", "1").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


def max_entities_per_file() -> int:
    """Cap symbols extracted per file (heuristic languages)."""
    return max(1, int(os.environ.get("OMEGA_MAX_ENTITIES_PER_FILE", "10")))


def impl_plan_max_entities() -> int:
    """Generate copy-paste implementation plans only for the top-N riskiest symbols."""
    return max(0, int(os.environ.get("OMEGA_IMPL_MAX_ENTITIES", "80")))


def file_worker_threads() -> int:
    """Parallel file analysis threads per language worker."""
    return max(1, int(os.environ.get("OMEGA_FILE_WORKERS", "8")))
