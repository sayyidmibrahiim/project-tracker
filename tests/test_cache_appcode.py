"""Tests for new cache columns: appcode, project_type, non_cr_state."""
from pathlib import Path

from core.enums import ProjectState, ProjectType, NonCrState
from infrastructure.cache_db import CacheDb, CachedProjectRow


def test_cached_project_row_has_appcode_and_type():
    row = CachedProjectRow(
        project_path=Path("D:/WORK/MYAPP/2026/CR/UAT_PREPARE/Test"),
        year="2026",
        project_state=ProjectState.UAT_PREPARE,
        project_name="Test",
        appcode="MYAPP",
        project_type=ProjectType.CR,
        non_cr_state=None,
    )
    assert row.appcode == "MYAPP"
    assert row.project_type == ProjectType.CR


def test_list_projects_filters_by_appcode(tmp_path):
    cache = CacheDb(tmp_path / "test.db")
    cache.initialize()
    row1 = CachedProjectRow(
        project_path=Path(str(tmp_path / "APP1" / "2026" / "CR" / "UAT_PREPARE" / "P1")),
        year="2026", project_state=ProjectState.UAT_PREPARE, project_name="P1",
        appcode="APP1", project_type=ProjectType.CR, non_cr_state=None,
    )
    row2 = CachedProjectRow(
        project_path=Path(str(tmp_path / "APP2" / "2026" / "CR" / "UAT_PREPARE" / "P2")),
        year="2026", project_state=ProjectState.UAT_PREPARE, project_name="P2",
        appcode="APP2", project_type=ProjectType.CR, non_cr_state=None,
    )
    cache.upsert_project(row1)
    cache.upsert_project(row2)
    result = cache.list_projects("2026", appcode="APP1")
    assert len(result) == 1
    assert result[0].appcode == "APP1"


def test_upsert_and_read_non_cr_project(tmp_path):
    cache = CacheDb(tmp_path / "test.db")
    cache.initialize()
    row = CachedProjectRow(
        project_path=Path(str(tmp_path / "MYAPP" / "2026" / "Non-CR" / "Task1")),
        year="2026", project_state=ProjectState.UAT_PREPARE, project_name="Task1",
        appcode="MYAPP", project_type=ProjectType.NON_CR,
        non_cr_state=NonCrState.PLANNING,
    )
    cache.upsert_project(row)
    result = cache.list_projects("2026", appcode="MYAPP")
    assert len(result) == 1
    assert result[0].project_type == ProjectType.NON_CR
    assert result[0].non_cr_state == NonCrState.PLANNING
