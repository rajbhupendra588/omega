"""Safe Python parsing for third-party repositories."""

from __future__ import annotations

import ast
import warnings
from contextlib import contextmanager


@contextmanager
def suppress_syntax_warnings():
    """Ignore SyntaxWarning from invalid escape sequences in vendor/test fixtures."""
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=SyntaxWarning)
        yield


def parse_python(source: str, filename: str = "<unknown>") -> ast.AST:
    """Parse Python source without flooding stderr on test-fixture escape sequences."""
    with suppress_syntax_warnings():
        return ast.parse(source, filename=filename)
