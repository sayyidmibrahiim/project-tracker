from __future__ import annotations

import json
from pathlib import Path

from project_tracker.core.enums import CRState, DroneState, ProjectState
from project_tracker.core.models import DroneTicket, ProjectMetadata
from project_tracker.infrastructure.cache_db import CacheDb, CachedDroneTicketRow, CachedProjectRow, rebuild_year_cache
from project_tracker.infrastructure.metadata_store import METADATA_FILE, MetadataStore


def _cache(tmp_path: Path) -> CacheDb:
    cache = CacheDb(tmp_path / "cache.sqlite3")
    cache.initialize()
    return cache


def _project_path(root_folder: Path, year: str, state: ProjectState, name: str) -> Path:
    return root_folder / year / state.value / name


def _write_metadata(project_path: Path, metadata: ProjectMetadata) -> None:
    MetadataStore().write(project_path, metadata)


def test_rebuild_year_cache_populates_project_rows_from_filesystem_scan(tmp_path: Path) -> None:
    root_folder = tmp_path / "CR"
    project_path = _project_path(root_folder, "2026", ProjectState.PROD_READY, "PAYMENT_MODULE_UPGRADE")
    _write_metadata(project_path, ProjectMetadata(project_name="PAYMENT_MODULE_UPGRADE", cr_state=CRState.APPROVED))
    cache = _cache(tmp_path)

    warnings = rebuild_year_cache(cache, root_folder / "2026")

    assert warnings == []
    rows = cache.list_projects("2026")
    assert len(rows) == 1
    assert rows[0].project_path == project_path
    assert rows[0].year == "2026"
    assert rows[0].project_state == ProjectState.PROD_READY
    assert rows[0].project_name == "PAYMENT_MODULE_UPGRADE"
    assert rows[0].cr_number == ""
    assert rows[0].cr_state == CRState.APPROVED
    assert rows[0].scanned_at is not None


def test_rebuild_year_cache_populates_drone_rows_for_current_projects(tmp_path: Path) -> None:
    root_folder = tmp_path / "CR"
    project_path = _project_path(root_folder, "2026", ProjectState.PROD_READY, "PAYMENT_MODULE_UPGRADE")
    _write_metadata(
        project_path,
        ProjectMetadata(
            project_name="PAYMENT_MODULE_UPGRADE",
            drone_tickets=[
                DroneTicket(
                    subfolder_name="APP_COMPONENT",
                    drone_link="https://drone.example.local/tickets/D-SSIDBI-159",
                    drone_state=DroneState.APPROVED,
                    owner="Alice",
                )
            ],
        ),
    )
    cache = _cache(tmp_path)

    rebuild_year_cache(cache, root_folder / "2026")

    assert cache.list_drone_tickets(project_path) == [
        CachedDroneTicketRow(
            project_path=project_path,
            subfolder_name="APP_COMPONENT",
            drone_ticket="D-SSIDBI-159",
            drone_state=DroneState.APPROVED,
            owner="Alice",
            display="D-SSIDBI-159",
        )
    ]


def test_rebuild_year_cache_removes_stale_project_rows_for_rebuilt_year(tmp_path: Path) -> None:
    root_folder = tmp_path / "CR"
    current_path = _project_path(root_folder, "2026", ProjectState.PROD_READY, "CURRENT")
    stale_path = _project_path(root_folder, "2026", ProjectState.UAT_PREPARE, "STALE")
    _write_metadata(current_path, ProjectMetadata(project_name="CURRENT"))
    cache = _cache(tmp_path)
    cache.upsert_project(CachedProjectRow(stale_path, "2026", ProjectState.UAT_PREPARE, "STALE"))

    rebuild_year_cache(cache, root_folder / "2026")

    assert [row.project_path for row in cache.list_projects("2026")] == [current_path]


def test_rebuild_year_cache_removes_stale_drone_rows_for_removed_projects(tmp_path: Path) -> None:
    root_folder = tmp_path / "CR"
    current_path = _project_path(root_folder, "2026", ProjectState.PROD_READY, "CURRENT")
    stale_path = _project_path(root_folder, "2026", ProjectState.UAT_PREPARE, "STALE")
    _write_metadata(current_path, ProjectMetadata(project_name="CURRENT"))
    cache = _cache(tmp_path)
    cache.upsert_project(CachedProjectRow(stale_path, "2026", ProjectState.UAT_PREPARE, "STALE"))
    cache.replace_drone_tickets_for_project(stale_path, [CachedDroneTicketRow(stale_path, drone_ticket="D-OLD")])

    rebuild_year_cache(cache, root_folder / "2026")

    assert cache.list_drone_tickets(stale_path) == []


def test_rebuild_year_cache_replaces_drone_rows_for_current_projects(tmp_path: Path) -> None:
    root_folder = tmp_path / "CR"
    project_path = _project_path(root_folder, "2026", ProjectState.PROD_READY, "PAYMENT_MODULE_UPGRADE")
    _write_metadata(
        project_path,
        ProjectMetadata(
            project_name="PAYMENT_MODULE_UPGRADE",
            drone_tickets=[DroneTicket(drone_link="https://drone.example.local/tickets/D-NEW")],
        ),
    )
    cache = _cache(tmp_path)
    cache.upsert_project(CachedProjectRow(project_path, "2026", ProjectState.PROD_READY, "PAYMENT_MODULE_UPGRADE"))
    cache.replace_drone_tickets_for_project(project_path, [CachedDroneTicketRow(project_path, drone_ticket="D-OLD")])

    rebuild_year_cache(cache, root_folder / "2026")

    assert [row.drone_ticket for row in cache.list_drone_tickets(project_path)] == ["D-NEW"]


def test_rebuild_year_cache_does_not_affect_other_years(tmp_path: Path) -> None:
    root_folder = tmp_path / "CR"
    current_path = _project_path(root_folder, "2026", ProjectState.PROD_READY, "CURRENT")
    other_path = _project_path(root_folder, "2027", ProjectState.UAT_PREPARE, "OTHER")
    _write_metadata(current_path, ProjectMetadata(project_name="CURRENT"))
    cache = _cache(tmp_path)
    other_row = CachedProjectRow(other_path, "2027", ProjectState.UAT_PREPARE, "OTHER")
    cache.upsert_project(other_row)

    rebuild_year_cache(cache, root_folder / "2026")

    assert cache.list_projects("2027") == [other_row]


def test_rebuild_year_cache_missing_year_folder_clears_cached_rows_for_that_year(tmp_path: Path) -> None:
    root_folder = tmp_path / "CR"
    stale_path = _project_path(root_folder, "2026", ProjectState.UAT_PREPARE, "STALE")
    cache = _cache(tmp_path)
    cache.upsert_project(CachedProjectRow(stale_path, "2026", ProjectState.UAT_PREPARE, "STALE"))
    cache.replace_drone_tickets_for_project(stale_path, [CachedDroneTicketRow(stale_path, drone_ticket="D-OLD")])

    rebuild_year_cache(cache, root_folder / "2026")

    assert cache.list_projects("2026") == []
    assert cache.list_drone_tickets(stale_path) == []


def test_rebuild_year_cache_missing_metadata_returns_warning_and_caches_default_project_row(tmp_path: Path) -> None:
    root_folder = tmp_path / "CR"
    project_path = _project_path(root_folder, "2026", ProjectState.UAT_PREPARE, "MISSING_METADATA")
    project_path.mkdir(parents=True)
    cache = _cache(tmp_path)

    warnings = rebuild_year_cache(cache, root_folder / "2026")

    assert warnings == [f"Missing project_data.json: {project_path}"]
    rows = cache.list_projects("2026")
    assert len(rows) == 1
    assert rows[0].project_path == project_path
    assert rows[0].year == "2026"
    assert rows[0].project_state == ProjectState.UAT_PREPARE
    assert rows[0].project_name == "MISSING_METADATA"
    assert rows[0].cr_number == ""
    assert rows[0].scanned_at is not None


def test_rebuild_year_cache_corrupt_metadata_returns_warning_and_skips_project(tmp_path: Path) -> None:
    root_folder = tmp_path / "CR"
    project_path = _project_path(root_folder, "2026", ProjectState.UAT_PREPARE, "CORRUPT")
    project_path.mkdir(parents=True)
    metadata_path = project_path / METADATA_FILE
    metadata_path.write_text("{not json", encoding="utf-8")
    cache = _cache(tmp_path)

    warnings = rebuild_year_cache(cache, root_folder / "2026")

    assert warnings == [f"Corrupt JSON: {metadata_path}"]
    assert cache.list_projects("2026") == []


def test_rebuild_year_cache_does_not_mutate_project_data_or_project_folder_contents(tmp_path: Path) -> None:
    root_folder = tmp_path / "CR"
    project_path = _project_path(root_folder, "2026", ProjectState.PROD_READY, "PAYMENT_MODULE_UPGRADE")
    _write_metadata(project_path, ProjectMetadata(project_name="PAYMENT_MODULE_UPGRADE"))
    (project_path / "APP_COMPONENT").mkdir()
    metadata_path = project_path / METADATA_FILE
    before_json = json.loads(metadata_path.read_text(encoding="utf-8"))
    before_children = sorted(child.name for child in project_path.iterdir())
    cache = _cache(tmp_path)

    rebuild_year_cache(cache, root_folder / "2026")

    after_json = json.loads(metadata_path.read_text(encoding="utf-8"))
    after_children = sorted(child.name for child in project_path.iterdir())
    assert after_json == before_json
    assert after_children == before_children
