"""Infer business service context from repository artifacts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "payments": ["payment", "billing", "invoice", "stripe", "checkout"],
    "identity": ["auth", "login", "oauth", "jwt", "session", "identity"],
    "data": ["warehouse", "etl", "pipeline", "analytics", "metrics"],
    "messaging": ["kafka", "rabbitmq", "sqs", "pubsub", "queue", "event"],
    "api": ["graphql", "rest", "openapi", "swagger", "grpc"],
    "ml": ["machine learning", "mlflow", "feature store", "sklearn", "scikit"],
    "deep_learning": [
        "deep learning",
        "pytorch",
        "tensorflow",
        "keras",
        "neural",
        "transformer",
        "cnn",
        "lstm",
        "gpu training",
    ],
    "platform": ["kubernetes", "deploy", "infra", "terraform"],
}

_ROLE_PATTERNS: list[tuple[str, list[str]]] = [
    ("api", ["api/", "/api/", "routes/", "controllers/", "handlers/", "graphql"]),
    ("worker", ["worker", "consumer", "celery", "jobs/", "tasks/"]),
    ("library", ["lib/", "sdk/", "client/", "pkg/"]),
    ("frontend", ["frontend/", "ui/", "dashboard/", "components/"]),
    ("monolith", ["app/", "main.py", "server.py"]),
]


def _read_text(path: Path, limit: int = 64_000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return ""


def _load_yaml_simple(path: Path) -> dict[str, Any]:
    """Minimal YAML subset parser (key: value, lists) — no PyYAML required."""
    text = _read_text(path)
    if not text.strip():
        return {}
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(0, root)]
    list_key: str | None = None
    list_indent = 0

    for line in text.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        while stack and indent < stack[-1][0]:
            stack.pop()
        container = stack[-1][1]

        if stripped.startswith("- "):
            item = stripped[2:].strip().strip("'\"")
            if list_key and list_key in container:
                cast = container[list_key]
                if isinstance(cast, list):
                    cast.append(item)
            continue

        if ":" not in stripped:
            continue
        key, _, rest = stripped.partition(":")
        key = key.strip()
        val = rest.strip().strip("'\"")
        if not val:
            if list_key:
                container[key] = []
            else:
                container[key] = {}
            stack.append((indent, container[key] if isinstance(container.get(key), dict) else container))
            list_key = key
            list_indent = indent
            continue
        container[key] = val
        list_key = None

    return root


def _package_name(root: Path) -> str | None:
    pj = root / "package.json"
    if pj.exists():
        try:
            data = json.loads(pj.read_text(encoding="utf-8"))
            return data.get("name")
        except (json.JSONDecodeError, OSError):
            pass
    pyproj = root / "pyproject.toml"
    if pyproj.exists():
        text = _read_text(pyproj)
        m = re.search(r'name\s*=\s*["\']([^"\']+)["\']', text)
        if m:
            return m.group(1)
    go_mod = root / "go.mod"
    if go_mod.exists():
        for line in _read_text(go_mod).splitlines():
            if line.startswith("module "):
                return line.split()[-1].split("/")[-1]
    return None


def _infer_role(root: Path, inventory_paths: list[str]) -> str:
    joined = " ".join(inventory_paths[:200]).lower()
    scores: dict[str, int] = {role: 0 for role, _ in _ROLE_PATTERNS}
    for role, patterns in _ROLE_PATTERNS:
        for pat in patterns:
            if pat in joined:
                scores[role] += 1
    if root.joinpath("Dockerfile").exists() and scores.get("api", 0) == 0:
        scores["api"] = scores.get("api", 0) + 1
    best = max(scores.items(), key=lambda x: x[1])
    return best[0] if best[1] > 0 else "service"


def _infer_domain(root: Path, display: str) -> list[str]:
    blob = display.lower()
    readme = _read_text(root / "README.md", limit=12_000).lower()
    blob += " " + readme
    for path in list(root.glob("**/*"))[:80]:
        if path.is_file() and path.suffix in {".py", ".go", ".java", ".ts", ".js"}:
            blob += " " + path.name.lower()
            break
    domains: list[str] = []
    for domain, keys in _DOMAIN_KEYWORDS.items():
        if any(k in blob for k in keys):
            domains.append(domain)
    return domains[:5] or ["general"]


def _parse_service_block(text: str) -> dict[str, Any]:
    svc: dict[str, Any] = {}
    in_svc = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("service:"):
            in_svc = True
            continue
        if in_svc:
            if stripped and not line.startswith(" ") and not stripped.startswith("service:"):
                if stripped.endswith(":") and "name" not in stripped:
                    break
            if stripped.startswith("- "):
                continue
            if ":" in stripped and not stripped.startswith("-"):
                k, _, v = stripped.partition(":")
                key = k.strip()
                val = v.strip().strip("'\"")
                if key == "business_domains":
                    svc.setdefault("business_domains", []).append(val)
                else:
                    svc[key] = val
    return svc


def _load_omega_config(root: Path) -> dict[str, Any]:
    for rel in (".omega/ecosystem.yaml", ".omega/ecosystem.yml", "omega.ecosystem.yaml"):
        p = root / rel
        if p.exists():
            text = _read_text(p)
            data = _load_yaml_simple(p)
            svc = _parse_service_block(text)
            if svc:
                data["service"] = {**data.get("service", {}), **svc} if isinstance(data.get("service"), dict) else svc
            return data
    return {}


def detect_service_context(
    root: Path,
    *,
    repo_display: str,
    inventory_paths: list[str] | None = None,
) -> dict[str, Any]:
    """
    Business-facing identity of this repository as a deployable service or product module.
    """
    root = root.resolve()
    paths = inventory_paths or []
    cfg = _load_omega_config(root)
    svc_cfg = cfg.get("service") if isinstance(cfg.get("service"), dict) else {}

    name = (
        svc_cfg.get("name")
        or _package_name(root)
        or repo_display
    )
    role = str(svc_cfg.get("role") or _infer_role(root, paths))
    domains = svc_cfg.get("business_domains") or svc_cfg.get("domain")
    if isinstance(domains, str):
        domains = [domains]
    if not domains:
        domains = _infer_domain(root, str(name))

    deployment_hints: list[str] = []
    for marker in (
        "Dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
        "compose.yaml",
        "kubernetes",
        "k8s",
        "helm",
        "terraform",
        ".github/workflows",
    ):
        if (root / marker).exists() or any(root.glob(f"**/{marker}")):
            deployment_hints.append(marker)

    entry_points: list[str] = []
    for rel in paths:
        low = rel.lower()
        if low.endswith(("main.py", "app.py", "server.py", "index.ts", "main.go")):
            entry_points.append(rel)
    entry_points = entry_points[:8]

    return {
        "service_name": str(name),
        "service_role": role,
        "business_domains": list(domains) if isinstance(domains, list) else [str(domains)],
        "deployment_artifacts": deployment_hints[:12],
        "entry_points": entry_points,
        "config_source": "omega.ecosystem" if cfg else "inferred",
        "description_technical": (
            f"Service `{name}` classified as `{role}` with domains "
            f"{', '.join(domains if isinstance(domains, list) else [str(domains)])}."
        ),
        "description_business": (
            f"This codebase implements **{name}** — a **{role}** component "
            f"in the **{domains[0] if domains else 'general'}** business area."
        ),
    }
