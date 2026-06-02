"""Tests for quiet Python parsing."""

from __future__ import annotations

import warnings

from omega.parse_util import parse_python


def test_parse_invalid_escape_no_syntax_warning():
    src = 'x = "\\ "\n'
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", SyntaxWarning)
        tree = parse_python(src, filename="fixture.py")
    syntax = [w for w in caught if issubclass(w.category, SyntaxWarning)]
    assert syntax == []
    assert tree is not None
