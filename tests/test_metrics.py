"""Tests for core Ω metric functions."""

from __future__ import annotations

import ast
import textwrap

import pytest

from omega.metrics import (
    FileMetrics,
    _compression_ratio,
    _cyclomatic_and_nesting,
    _omega_local,
    _risk_band,
    _structural_entropy,
    _textual_entropy,
    compute_file_metrics,
)


def test_cyclomatic_simple_function_is_one():
    tree = ast.parse("def f():\n    return 1\n")
    cyc, nest = _cyclomatic_and_nesting(tree)
    assert cyc == 1
    assert nest == 0


def test_cyclomatic_counts_branches():
    src = textwrap.dedent(
        """
        def f(x):
            if x > 0:
                for i in range(3):
                    if i % 2:
                        return i
            return 0
        """
    )
    tree = ast.parse(src)
    cyc, nest = _cyclomatic_and_nesting(tree)
    assert cyc >= 4
    assert nest >= 2


def test_structural_entropy_positive_for_class():
    tree = ast.parse("class A:\n    def m(self):\n        pass\n")
    h = _structural_entropy(tree)
    assert h > 0


def test_textual_entropy_empty_is_zero():
    assert _textual_entropy("") == 0.0


def test_compression_ratio_at_least_one():
    assert _compression_ratio("print('hello world')\n" * 10) >= 1.0


def test_omega_local_monotonic_with_complexity():
    low = _omega_local(2.0, 2, 1, 0, 2.0)
    high = _omega_local(5.0, 20, 5, 4, 2.0)
    assert high > low


def test_omega_local_bounded_0_100():
    v = _omega_local(10.0, 50, 8, 6, 5.0)
    assert 0 <= v <= 100


def test_risk_band_thresholds():
    assert _risk_band(10) == "LOW"
    assert _risk_band(40) == "MEDIUM"
    assert _risk_band(60) == "HIGH"
    assert _risk_band(80) == "CRITICAL"


def test_compute_file_metrics_on_sample(tmp_path):
    p = tmp_path / "m.py"
    p.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    m = compute_file_metrics(p, tmp_path, p.read_text(), 0, 0)
    assert m.language == "python"
    assert m.cyclomatic == 1
    assert m.risk_band == "LOW"
    assert m.omega_local < 35


def test_file_metrics_frozen_dataclass():
    m = FileMetrics(
        path="x.py",
        loc=1,
        cyclomatic=1,
        nesting_depth=0,
        h_struct=1.0,
        h_text=1.0,
        compression_ratio=2.0,
        coupling_out=0,
        coupling_in=0,
        omega_local=10.0,
        risk_band="LOW",
    )
    with pytest.raises(Exception):
        m.omega_local = 99.0  # type: ignore[misc]
