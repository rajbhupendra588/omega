"""Developer guide: symbol-first sprint queue and grouped module batch."""

from omega.developer_guide import GUIDE_VERSION, build_developer_guide
from omega.entities import EntityMetrics
from omega.metrics import FileMetrics


def _snap(*, entities=None, files=None, plan=None):
    class S:
        pass

    s = S()
    s.repo_display = "org/app"
    s.omega_index = 40.0
    s.quality_grade = "C"
    s.improvement_plan = plan or []
    s.dimensions = []
    s.entities = entities or []
    s.files = files or []
    return s


def test_groups_orphan_files_instead_of_many_stabilize_cards():
    entities = [
        EntityMetrics(
            entity_type="function",
            qualified_name="lib/a.ts.process",
            file_path="lib/a.ts",
            line_start=1,
            line_end=20,
            loc=20,
            cyclomatic=12,
            nesting_depth=3,
            omega_local=60.0,
            risk_band="HIGH",
            improvement_areas=("High complexity",),
            improvement_areas_business=("Risky",),
        ),
    ]
    files = [
        FileMetrics(
            path="ui/Tab1.tsx",
            language="typescript",
            loc=200,
            cyclomatic=30,
            nesting_depth=8,
            h_struct=2.0,
            h_text=1.0,
            coupling_out=5,
            coupling_in=2,
            compression_ratio=1.0,
            omega_local=70.0,
            risk_band="HIGH",
        ),
        FileMetrics(
            path="ui/Tab2.tsx",
            language="typescript",
            loc=180,
            cyclomatic=25,
            nesting_depth=7,
            h_struct=2.0,
            h_text=1.0,
            coupling_out=4,
            coupling_in=1,
            compression_ratio=1.0,
            omega_local=65.0,
            risk_band="HIGH",
        ),
    ]
    guide = build_developer_guide(_snap(entities=entities, files=files))
    assert guide["guide_version"] == GUIDE_VERSION
    titles = [a["title"] for a in guide["actions"]]
    assert any("modules need stabilization" in t for t in titles)
    assert sum(1 for t in titles if t.startswith("Stabilize module")) == 0
    group = next(a for a in guide["actions"] if a["category"] == "module_health_group")
    assert len(group["grouped_files"]) == 2


def test_no_file_card_when_symbol_covers_file():
    entities = [
        EntityMetrics(
            entity_type="function",
            qualified_name="ui/Tab1.tsx.ReceiverTab",
            file_path="ui/Tab1.tsx",
            line_start=1,
            line_end=50,
            loc=50,
            cyclomatic=15,
            nesting_depth=5,
            omega_local=55.0,
            risk_band="HIGH",
            improvement_areas=("Complex",),
            improvement_areas_business=("Risk",),
        ),
    ]
    files = [
        FileMetrics(
            path="ui/Tab1.tsx",
            language="typescript",
            loc=200,
            cyclomatic=30,
            nesting_depth=8,
            h_struct=2.0,
            h_text=1.0,
            coupling_out=5,
            coupling_in=2,
            compression_ratio=1.0,
            omega_local=70.0,
            risk_band="HIGH",
        ),
    ]
    guide = build_developer_guide(_snap(entities=entities, files=files))
    assert not any(a["category"] == "module_health_group" for a in guide["actions"])
    assert not any("Stabilize module" in a["title"] for a in guide["actions"])
