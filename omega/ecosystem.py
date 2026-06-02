"""Discover upstream/downstream services and dependency graph for ecosystem metrics."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from omega.service_context import _load_yaml_simple, _read_text


@dataclass
class ServiceNode:
    name: str
    kind: str  # http | datastore | queue | library | internal | unknown
    direction: str  # upstream | downstream | peer
    evidence: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "direction": self.direction,
            "evidence": self.evidence,
            "metadata": self.metadata,
        }


_HTTP_PAT = re.compile(
    r"""https?://([a-zA-Z0-9][-a-zA-Z0-9.]*[a-zA-Z0-9])""",
    re.I,
)
_ENV_SVC_PAT = re.compile(
    r"(?:DATABASE|REDIS|KAFKA|RABBIT|ELASTIC|POSTGRES|MYSQL|MONGO|AMQP)[_A-Z]*_?(?:URL|HOST|URI|DSN)\s*[=:]\s*['\"]?([^\s'\"#]+)",
    re.I,
)
_GRPC_PAT = re.compile(r"grpc\.(?:insecure_)?channel\s*\(\s*['\"]([^'\"]+)['\"]", re.I)


def _parse_compose_services(root: Path) -> tuple[list[ServiceNode], list[ServiceNode]]:
    upstream: list[ServiceNode] = []
    downstream: list[ServiceNode] = []
    for name in ("docker-compose.yml", "docker-compose.yaml", "compose.yaml"):
        path = root / name
        if not path.exists():
            continue
        data = _load_yaml_simple(path)
        services = data.get("services")
        if not isinstance(services, dict):
            continue
        self_service: str | None = None
        for svc_name, spec in services.items():
            if not isinstance(spec, dict):
                continue
            if spec.get("build") or spec.get("context"):
                self_service = str(svc_name)
        for svc_name, spec in services.items():
            if not isinstance(spec, dict):
                continue
            depends = spec.get("depends_on")
            dep_list: list[str] = []
            if isinstance(depends, list):
                dep_list = [str(x) for x in depends]
            elif isinstance(depends, dict):
                dep_list = list(depends.keys())
            if svc_name == self_service:
                for dep in dep_list:
                    upstream.append(
                        ServiceNode(
                            name=dep,
                            kind="internal",
                            direction="upstream",
                            evidence=[f"{name}: service `{self_service}` depends_on `{dep}`"],
                        )
                    )
            elif self_service and self_service in dep_list:
                downstream.append(
                    ServiceNode(
                        name=str(svc_name),
                        kind="internal",
                        direction="downstream",
                        evidence=[f"{name}: `{svc_name}` depends_on `{self_service}`"],
                    )
                )
        break
    return upstream, downstream


def _package_dependencies(root: Path) -> list[ServiceNode]:
    nodes: list[ServiceNode] = []
    req = root / "requirements.txt"
    if req.exists():
        for line in _read_text(req).splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            pkg = re.split(r"[<>=!~\[]", line)[0].strip()
            if pkg:
                nodes.append(
                    ServiceNode(
                        name=pkg,
                        kind="library",
                        direction="upstream",
                        evidence=[f"requirements.txt: {pkg}"],
                    )
                )
    pj = root / "package.json"
    if pj.exists():
        try:
            data = json.loads(pj.read_text(encoding="utf-8"))
            for section in ("dependencies", "devDependencies", "peerDependencies"):
                deps = data.get(section) or {}
                if isinstance(deps, dict):
                    for pkg in deps:
                        nodes.append(
                            ServiceNode(
                                name=pkg,
                                kind="library",
                                direction="upstream",
                                evidence=[f"package.json {section}: {pkg}"],
                                metadata={"scope": section},
                            )
                        )
        except (json.JSONDecodeError, OSError):
            pass
    return nodes[:80]


def _scan_code_integrations(root: Path, source_paths: list[Path]) -> tuple[list[ServiceNode], list[ServiceNode]]:
    """HTTP/gRPC/env references → upstream calls; publish patterns → downstream exposure."""
    upstream: dict[str, ServiceNode] = {}
    downstream: dict[str, ServiceNode] = {}
    publish_pats = [
        re.compile(r"\.publish\s*\(", re.I),
        re.compile(r"producer\.send", re.I),
        re.compile(r"kafka\.Producer", re.I),
        re.compile(r"send_event|emit\(", re.I),
    ]

    for path in source_paths[:120]:
        text = _read_text(path, limit=48_000)
        if not text:
            continue
        rel = str(path)
        for m in _HTTP_PAT.finditer(text):
            host = m.group(1).split(":")[0].lower()
            if host in ("localhost", "127.0.0.1", "0.0.0.0"):
                continue
            if host not in upstream:
                upstream[host] = ServiceNode(
                    name=host,
                    kind="http",
                    direction="upstream",
                    evidence=[],
                )
            upstream[host].evidence.append(f"{rel}: HTTP → {host}")
        for m in _GRPC_PAT.finditer(text):
            target = m.group(1)
            key = target.split("/")[-1] or target
            if key not in upstream:
                upstream[key] = ServiceNode(
                    name=key,
                    kind="grpc",
                    direction="upstream",
                    evidence=[],
                )
            upstream[key].evidence.append(f"{rel}: gRPC → {target}")
        for m in _ENV_SVC_PAT.finditer(text):
            url = m.group(1)
            key = re.sub(r"^.*://", "", url).split("/")[0].split(":")[0]
            if key and key not in upstream:
                upstream[key] = ServiceNode(
                    name=key,
                    kind="datastore",
                    direction="upstream",
                    evidence=[f"{rel}: env integration → {key}"],
                )
        if any(p.search(text) for p in publish_pats):
            topic_m = re.search(r"['\"]([a-zA-Z0-9_.-]+)['\"]", text)
            topic = topic_m.group(1) if topic_m else "event-bus"
            if topic not in downstream:
                downstream[topic] = ServiceNode(
                    name=topic,
                    kind="queue",
                    direction="downstream",
                    evidence=[],
                )
            downstream[topic].evidence.append(f"{rel}: event publish pattern")

    for n in upstream.values():
        n.evidence = n.evidence[:5]
    for n in downstream.values():
        n.evidence = n.evidence[:5]
    return list(upstream.values())[:40], list(downstream.values())[:25]


def _parse_ecosystem_list_block(text: str, section: str) -> list[dict[str, str]]:
    """Parse `upstream:` / `downstream:` list-of-maps from ecosystem YAML."""
    lines = text.splitlines()
    in_section = False
    items: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"{section}:"):
            in_section = True
            current = None
            continue
        if not in_section:
            continue
        if stripped and not stripped.startswith("-") and not line.startswith(" "):
            break
        if stripped.startswith("- "):
            if current:
                items.append(current)
            rest = stripped[2:].strip()
            if ":" in rest:
                k, _, v = rest.partition(":")
                current = {k.strip(): v.strip().strip("'\"")}
            else:
                current = {"name": rest.strip("'\""), "kind": "unknown"}
        elif current is not None and ":" in stripped:
            k, _, v = stripped.partition(":")
            current[k.strip()] = v.strip().strip("'\"")
    if current:
        items.append(current)
    return items


def _config_graph(root: Path) -> tuple[list[ServiceNode], list[ServiceNode]]:
    for rel in (".omega/ecosystem.yaml", ".omega/ecosystem.yml", "omega.ecosystem.yaml"):
        p = root / rel
        if not p.exists():
            continue
        text = _read_text(p)
        up: list[ServiceNode] = []
        down: list[ServiceNode] = []
        for item in _parse_ecosystem_list_block(text, "upstream"):
            name = str(item.get("name", "unknown"))
            up.append(
                ServiceNode(
                    name=name,
                    kind=str(item.get("kind", "unknown")),
                    direction="upstream",
                    evidence=[f"{rel}: upstream `{name}`"],
                    metadata=dict(item),
                )
            )
        for item in _parse_ecosystem_list_block(text, "downstream"):
            name = str(item.get("name", "unknown"))
            down.append(
                ServiceNode(
                    name=name,
                    kind=str(item.get("kind", "unknown")),
                    direction="downstream",
                    evidence=[f"{rel}: downstream `{name}`"],
                    metadata=dict(item),
                )
            )
        if up or down:
            return up, down
    return [], []


def _dedupe_nodes(nodes: list[ServiceNode]) -> list[ServiceNode]:
    by_name: dict[str, ServiceNode] = {}
    for n in nodes:
        key = n.name.lower()
        if key in by_name:
            existing = by_name[key]
            existing.evidence.extend(n.evidence)
            existing.evidence = existing.evidence[:8]
            if n.metadata:
                existing.metadata.update(n.metadata)
        else:
            by_name[key] = n
    return list(by_name.values())


def discover_ecosystem(
    root: Path,
    *,
    source_file_paths: list[Path] | None = None,
) -> dict[str, Any]:
    """
  Build upstream/downstream service graph for ecosystem metrics.
  """
    root = root.resolve()
    paths = source_file_paths or []
    cfg_up, cfg_down = _config_graph(root)
    compose_up, compose_down = _parse_compose_services(root)
    libs = _package_dependencies(root)
    code_up, code_down = _scan_code_integrations(root, paths)

    upstream = _dedupe_nodes(cfg_up + compose_up + libs + code_up)
    downstream = _dedupe_nodes(cfg_down + compose_down + code_down)

    return {
        "upstream": [n.to_dict() for n in upstream],
        "downstream": [n.to_dict() for n in downstream],
        "upstream_count": len(upstream),
        "downstream_count": len(downstream),
        "graph_summary_technical": (
            f"Ecosystem: {len(upstream)} upstream nodes, {len(downstream)} downstream nodes."
        ),
        "graph_summary_business": (
            f"This service depends on {len(upstream)} external or internal providers "
            f"and exposes impact to {len(downstream)} downstream consumers or channels."
        ),
    }


def per_service_stress(
    omega_index: float,
    *,
    node: dict[str, Any],
    direction: str,
) -> float:
    """
    Blended stress for an ecosystem edge: local field × coupling weight × kind factor.
    """
    kind = str(node.get("kind", "unknown")).lower()
    kind_weight = {
        "datastore": 1.25,
        "http": 1.15,
        "grpc": 1.15,
        "queue": 1.1,
        "library": 0.85,
        "internal": 1.0,
        "unknown": 1.0,
    }.get(kind, 1.0)
    evidence_n = len(node.get("evidence") or [])
    coupling = min(1.0, 0.35 + 0.1 * evidence_n)
    direction_factor = 1.05 if direction == "upstream" else 1.12
    return round(min(100.0, omega_index * coupling * kind_weight * direction_factor), 2)
