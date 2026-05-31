"""Tight coupling to risky_module."""

from risky_module import process, legacy_handler


def pipeline(values):
    mid = process(values, "strict", 10, lambda x, e: x + e, extra=1)
    return legacy_handler(mid)
