import os

from omega.scan_config import default_max_files


def test_default_max_files(monkeypatch):
    monkeypatch.delenv("OMEGA_MAX_FILES", raising=False)
    assert default_max_files() == 350

    monkeypatch.setenv("OMEGA_MAX_FILES", "unlimited")
    assert default_max_files() is None

    monkeypatch.setenv("OMEGA_MAX_FILES", "120")
    assert default_max_files() == 120
