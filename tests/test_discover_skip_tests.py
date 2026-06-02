from pathlib import Path

from omega.discover import discover_source_files


def test_skips_guava_test_modules_by_default(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("OMEGA_SKIP_TEST_PATHS", raising=False)
    root = tmp_path / "repo"
    (root / "guava" / "src").mkdir(parents=True)
    (root / "guava-tests").mkdir(parents=True)
    (root / "guava" / "src" / "Main.java").write_text("class Main {}")
    (root / "guava-tests" / "HugeTest.java").write_text("class HugeTest {}" * 1000)

    inv = discover_source_files(root)
    paths = {f.rel_path for f in inv.files}
    assert "guava/src/Main.java" in paths
    assert not any("guava-tests" in p for p in paths)
