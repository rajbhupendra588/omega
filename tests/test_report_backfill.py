"""Report backfill must not recompute on every API read."""

from omega.developer_guide import ensure_report_has_developer_guide
from omega.dimensions import ensure_report_has_dimensions


def _minimal_report() -> dict:
    return {
        "repo_display": "org/repo",
        "omega_index": 0.5,
        "quality_grade": "B",
        "files": [],
        "entities": [],
        "improvement_plan": [],
        "pillars": {},
    }


def test_empty_dimensions_not_rebuilt_every_read():
    report = _minimal_report()
    report, updated = ensure_report_has_dimensions(report)
    assert updated is True
    assert report["dimensions"] == []

    report2, updated2 = ensure_report_has_dimensions(dict(report))
    assert updated2 is False
    assert report2["dimensions"] == []


def test_developer_guide_persisted_marker():
    from omega.developer_guide import GUIDE_VERSION

    report = _minimal_report()
    report["dimensions"] = []
    report, updated = ensure_report_has_developer_guide(report)
    assert updated is True
    assert report["developer_guide"]["guide_version"] == GUIDE_VERSION

    report2, updated2 = ensure_report_has_developer_guide(dict(report))
    assert updated2 is False
