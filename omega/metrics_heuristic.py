"""Heuristic metrics for non-Python languages (AST-free)."""

from __future__ import annotations

import math
import re
from collections import Counter

_IMPORT_PATTERNS = [
    re.compile(r"^\s*import\s+[\w.]+", re.M),
    re.compile(r"^\s*from\s+[\w.]+\s+import", re.M),
    re.compile(r"^\s*#include\s*[<\"][\w./]+", re.M),
    re.compile(r"^\s*using\s+[\w.]+", re.M),
    re.compile(r"^\s*require\s*\(?['\"][\w./]+", re.M),
    re.compile(r"^\s*require\s+['\"][\w./]+", re.M),
    re.compile(r"import\s+[\w.*]+\s+from\s+['\"]", re.M),
    re.compile(r"^\s*package\s+[\w.]+", re.M),
]

_BRANCH_PATTERNS = [
    re.compile(r"\bif\s*[\(\{]"),
    re.compile(r"\belse\b"),
    re.compile(r"\belif\b"),
    re.compile(r"\bfor\s*[\(\{]"),
    re.compile(r"\bwhile\s*[\(\{]"),
    re.compile(r"\bswitch\s*[\(\{]"),
    re.compile(r"\bcase\s+"),
    re.compile(r"\bcatch\s*[\(\{]"),
    re.compile(r"\?\s*[^:]+\s*:"),  # ternary
]


def _loc(source: str) -> int:
    return sum(
        1
        for line in source.splitlines()
        if line.strip() and not line.strip().startswith(("//", "#", "/*", "*", "--"))
    )


def _textual_entropy(source: str) -> float:
    tokens = re.findall(r"\w+|\S", source)
    if not tokens:
        return 0.0
    counts = Counter(tokens)
    total = len(tokens)
    entropy = 0.0
    for c in counts.values():
        p = c / total
        entropy -= p * math.log2(p)
    return entropy


def _nesting_depth(source: str) -> int:
    depth = 0
    max_d = 0
    in_str = False
    quote = ""
    for ch in source:
        if ch in "\"'`" and not in_str:
            in_str = True
            quote = ch
        elif in_str and ch == quote:
            in_str = False
        elif not in_str:
            if ch in "{(":
                depth += 1
                max_d = max(max_d, depth)
            elif ch in "})":
                depth = max(0, depth - 1)
    return max_d


def _cyclomatic_proxy(source: str) -> int:
    c = 1
    for pat in _BRANCH_PATTERNS:
        c += len(pat.findall(source))
    return c


def _import_count(source: str) -> int:
    n = 0
    for pat in _IMPORT_PATTERNS:
        n += len(pat.findall(source))
    return n


def analyze_source_text(source: str, language: str) -> dict:
    """Return metric dict compatible with FileMetrics assembly."""
    loc = _loc(source)
    cyc = _cyclomatic_proxy(source)
    nest = _nesting_depth(source)
    h_text = _textual_entropy(source)
    # Structural proxy: keyword/type token diversity
    keywords = re.findall(
        r"\b(class|function|def|interface|struct|enum|type|module|namespace|"
        r"public|private|protected|async|await|return|void|int|string)\b",
        source,
        re.I,
    )
    if keywords:
        counts = Counter(k.lower() for k in keywords)
        total = sum(counts.values())
        h_struct = -sum((n / total) * math.log2(n / total) for n in counts.values())
    else:
        h_struct = h_text * 0.7

    raw = source.encode("utf-8", errors="replace")
    import gzip
    import io

    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
        gz.write(raw)
    compress = len(raw) / max(len(buf.getvalue()), 1)

    return {
        "loc": loc,
        "cyclomatic": cyc,
        "nesting_depth": nest,
        "h_struct": round(h_struct, 3),
        "h_text": round(h_text, 3),
        "compression_ratio": round(compress, 2),
        "import_count": _import_count(source),
    }
