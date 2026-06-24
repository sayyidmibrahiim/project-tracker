from __future__ import annotations

import json
from pathlib import Path

from core.enums import CRState, ProjectState
from core.models import ProjectMetadata
from infrastructure.cache_db import CacheDb, CachedProjectRow
from infrastructure.metadata_store import METADATA_FILE, MetadataStore
from services.scanner_service import ScannerService, ScanYearResult


def _cache(tmp_path: Path) -> CacheDb:
    cache = CacheDb(tmp_path / "cache.sqlite3")
    cache.initialize()
    return cache


def _project_path(root_folder: Path, year: str, state: ProjectState, name: str) -> Path:
    return root_folder / year / state.value / name


def _write_metadata(project_path: Path, metadata: ProjectMetadata) -> None:
    MetadataStore().write(project_path, metadata)


def test_scanner_service_rebuild_year_populates_cache_from_filesystem_scan(tmp_path: Path) -> None:
    root_folder = tmp_path / "CR"
    project_path = _project_path(root_folder, "2026", ProjectState.PROD_READY, "PAYMENT_MODULE_UPGRADE")
    _write_metadata(project_path, ProjectMetadata(project_name="PAYMENT_MODULE_UPGRADE", cr_state=CRState.APPROVED))
    cache = _cache(tmp_path)

    result = ScannerService(cache).rebuild_year(root_folder / "2026")

    assert result == ScanYearResult(year="2026", project_count=1, warnings=[])
    rows = cache.list_projects("2026")
    assert len(rows) == 1
    assert rows[0].project_path == project_path
    assert rows[0].project_state == ProjectState.PROD_READY
    assert rows[0].project_name == "PAYMENT_MODULE_UPGRADE"
    assert rows[0].cr_state == CRState.APPROVED


def test_scanner_service_rebuild_year_returns_missing_metadata_warning_and_caches_default_row(tmp_path: Path) -> None:
    root_folder = tmp_path / "CR"
    project_path = _project_path(root_folder, "2026", ProjectState.UAT_PREPARE, "MISSING_METADATA")
    project_path.mkdir(parents=True)
    cache = _cache(tmp_path)

    result = ScannerService(cache).rebuild_year(root_folder / "2026")

    assert result == ScanYearResult(
        year="2026",
        project_count=1,
        warnings=[f"Missing project_data.json: {project_path}"],
    )
    rows = cache.list_projects("2026")
    assert len(rows) == 1
    assert rows[0].project_path == project_path
    assert rows[0].project_name == "MISSING_METADATA"


def test_scanner_service_rebuild_year_returns_corrupt_metadata_warning_and_skips_project(tmp_path: Path) -> None:
    root_folder = tmp_path / "CR"
    project_path = _project_path(root_folder, "2026", ProjectState.UAT_PREPARE, "CORRUPT")
    project_path.mkdir(parents=True)
    metadata_path = project_path / METADATA_FILE
    metadata_path.write_text("{not json", encoding="utf-8")
    cache = _cache(tmp_path)

    result = ScannerService(cache).rebuild_year(root_folder / "2026")

    assert result == ScanYearResult(
        year="2026",
        project_count=0,
        warnings=[f"Corrupt JSON: {metadata_path}"],
    )
    assert cache.list_projects("2026") == []


def test_scanner_service_rebuild_year_missing_year_folder_clears_cached_rows(tmp_path: Path) -> None:
    root_folder = tmp_path / "CR"
    stale_path = _project_path(root_folder, "2026", ProjectState.UAT_PREPARE, "STALE")
    cache = _cache(tmp_path)
    cache.upsert_project(CachedProjectRow(stale_path, "2026", ProjectState.UAT_PREPARE, "STALE"))

    result = ScannerService(cache).rebuild_year(root_folder / "2026")

    assert result == ScanYearResult(year="2026", project_count=0, warnings=[])
    assert cache.list_projects("2026") == []


def test_scanner_service_rebuild_year_replaces_stale_cache_rows_for_year(tmp_path: Path) -> None:
    root_folder = tmp_path / "CR"
    current_path = _project_path(root_folder, "2026", ProjectState.PROD_READY, "CURRENT")
    stale_path = _project_path(root_folder, "2026", ProjectState.UAT_PREPARE, "STALE")
    _write_metadata(current_path, ProjectMetadata(project_name="CURRENT"))
    cache = _cache(tmp_path)
    cache.upsert_project(CachedProjectRow(stale_path, "2026", ProjectState.UAT_PREPARE, "STALE"))

    result = ScannerService(cache).rebuild_year(root_folder / "2026")

    assert result == ScanYearResult(year="2026", project_count=1, warnings=[])
    assert [row.project_path for row in cache.list_projects("2026")] == [current_path]


def test_scanner_service_rebuild_year_does_not_affect_other_years(tmp_path: Path) -> None:
    root_folder = tmp_path / "CR"
    current_path = _project_path(root_folder, "2026", ProjectState.PROD_READY, "CURRENT")
    other_path = _project_path(root_folder, "2027", ProjectState.UAT_PREPARE, "OTHER")
    _write_metadata(current_path, ProjectMetadata(project_name="CURRENT"))
    cache = _cache(tmp_path)
    other_row = CachedProjectRow(other_path, "2027", ProjectState.UAT_PREPARE, "OTHER")
    cache.upsert_project(other_row)

    result = ScannerService(cache).rebuild_year(root_folder / "2026")

    assert result == ScanYearResult(year="2026", project_count=1, warnings=[])
    assert cache.list_projects("2027") == [other_row]


def test_scanner_service_rebuild_year_does_not_mutate_project_data_json(tmp_path: Path) -> None:
    root_folder = tmp_path / "CR"
    project_path = _project_path(root_folder, "2026", ProjectState.PROD_READY, "PAYMENT_MODULE_UPGRADE")
    _write_metadata(project_path, ProjectMetadata(project_name="PAYMENT_MODULE_UPGRADE"))
    metadata_path = project_path / METADATA_FILE
    before_json = json.loads(metadata_path.read_text(encoding="utf-8"))
    cache = _cache(tmp_path)

    ScannerService(cache).rebuild_year(root_folder / "2026")

    after_json = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert after_json == before_json


def test_scanner_service_rebuild_year_does_not_create_move_or_delete_project_folders(tmp_path: Path) -> None:
    root_folder = tmp_path / "CR"
    project_path = _project_path(root_folder, "2026", ProjectState.PROD_READY, "PAYMENT_MODULE_UPGRADE")
    _write_metadata(project_path, ProjectMetadata(project_name="PAYMENT_MODULE_UPGRADE"))
    (project_path / "APP_COMPONENT").mkdir()
    before_year_children = sorted(path.relative_to(root_folder / "2026") for path in (root_folder / "2026").rglob("*"))
    cache = _cache(tmp_path)

    ScannerService(cache).rebuild_year(root_folder / "2026")

    after_year_children = sorted(path.relative_to(root_folder / "2026") for path in (root_folder / "2026").rglob("*"))
    assert after_year_children == before_year_children
