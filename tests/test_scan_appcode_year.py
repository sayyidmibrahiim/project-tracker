from pathlib import Path

from core.enums import ProjectState, ProjectType
from infrastructure.filesystem import (
    ensure_appcode_year_structure,
    scan_appcode_year,
)
from infrastructure.metadata_store import MetadataStore


def _make_cr_project(appcode_path, year, state, name):
    project = appcode_path / str(year) / "CR" / state.value / name
    project.mkdir(parents=True)
    (project / "project_data.json").write_text(
        f'{{"$schema":"project_data_v1","project_name":"{name}","project_type":"CR"}}',
        encoding="utf-8",
    )
    (project / "notes.md").touch()
    (project / "_cr-docs").mkdir()
    return project


def _make_non_cr_project(appcode_path, year, name):
    project = appcode_path / str(year) / "Non-CR" / name
    project.mkdir(parents=True)
    (project / "project_data.json").write_text(
        f'{{"$schema":"project_data_v1","project_name":"{name}","project_type":"NON_CR","non_cr_state":"PLANNING"}}',
        encoding="utf-8",
    )
    (project / "notes.md").touch()
    return project


def test_scan_finds_cr_project(tmp_path):
    appcode = tmp_path / "MYAPP"
    appcode.mkdir()
    ensure_appcode_year_structure(appcode, 2026)
    _make_cr_project(appcode, 2026, ProjectState.UAT_PREPARE, "MyCR")
    result = scan_appcode_year(appcode, "2026")
    assert len(result) == 1
    assert result[0].project_type == ProjectType.CR
    assert result[0].project_state == ProjectState.UAT_PREPARE
    assert result[0].appcode == "MYAPP"
    assert result[0].year == "2026"


def test_scan_finds_non_cr_project(tmp_path):
    appcode = tmp_path / "MYAPP"
    appcode.mkdir()
    ensure_appcode_year_structure(appcode, 2026)
    _make_non_cr_project(appcode, 2026, "MyTask")
    result = scan_appcode_year(appcode, "2026")
    assert len(result) == 1
    assert result[0].project_type == ProjectType.NON_CR
    assert result[0].project_state is None
    assert result[0].drone_paths == []


def test_scan_finds_both_types(tmp_path):
    appcode = tmp_path / "MYAPP"
    appcode.mkdir()
    ensure_appcode_year_structure(appcode, 2026)
    _make_cr_project(appcode, 2026, ProjectState.UAT_PREPARE, "CR1")
    _make_non_cr_project(appcode, 2026, "Task1")
    result = scan_appcode_year(appcode, "2026")
    assert len(result) == 2
    types = {p.project_type for p in result}
    assert types == {ProjectType.CR, ProjectType.NON_CR}


def test_scan_empty_year(tmp_path):
    appcode = tmp_path / "MYAPP"
    appcode.mkdir()
    ensure_appcode_year_structure(appcode, 2026)
    result = scan_appcode_year(appcode, "2026")
    assert result == []


def test_scan_drone_paths_excludes_cr_docs(tmp_path):
    appcode = tmp_path / "MYAPP"
    appcode.mkdir()
    ensure_appcode_year_structure(appcode, 2026)
    project = _make_cr_project(appcode, 2026, ProjectState.UAT_PREPARE, "WithDrone")
    drone = project / "api-module"
    drone.mkdir()
    (drone / "UAT").mkdir()
    (drone / "PRD").mkdir()
    result = scan_appcode_year(appcode, "2026")
    assert len(result) == 1
    assert len(result[0].drone_paths) == 1
    assert result[0].drone_paths[0].name == "api-module"
