from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from project_tracker.core.enums import CRState, DroneState, ProjectState
from project_tracker.infrastructure.cache_db import CacheDb, CachedDroneTicketRow, CachedProjectRow


def _project_row(
    project_path: Path,
    *,
    year: str = "2026",
    project_state: ProjectState = ProjectState.UAT_PREPARE,
    project_name: str = "PAYMENT_MODULE_UPGRADE",
    cr_state: CRState = CRState.APPROVED,
) -> CachedProjectRow:
    return CachedProjectRow(
        project_path=project_path,
        year=year,
        project_state=project_state,
        project_name=project_name,
        start_datetime=datetime(2026, 6, 3, 10, 0, tzinfo=timezone.utc),
        end_datetime=datetime(2026, 6, 3, 11, 0, tzinfo=timezone.utc),
        cr_number="CR202604209900114",
        cr_state=cr_state,
        updated_at=datetime(2026, 6, 3, 9, 0, tzinfo=timezone.utc),
    )


def _drone_row(
    project_path: Path,
    *,
    drone_ticket: str = "D-SSIDBI-159",
    owner: str = "Alice",
    display: str = "D-SSIDBI-159 ↗",
    drone_state: DroneState = DroneState.APPROVED,
) -> CachedDroneTicketRow:
    return CachedDroneTicketRow(
        project_path=project_path,
        subfolder_name="APP_COMPONENT",
        drone_ticket=drone_ticket,
        drone_state=drone_state,
        owner=owner,
        display=display,
        updated_at=datetime(2026, 6, 3, 9, 30, tzinfo=timezone.utc),
    )


def _table_names(db_path: Path) -> set[str]:
    import sqlite3

    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    return {row[0] for row in rows}


def test_initialize_creates_db_file(tmp_path: Path) -> None:
    db_path = tmp_path / "cache.sqlite3"

    CacheDb(db_path).initialize()

    assert db_path.is_file()


def test_initialize_creates_expected_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "cache.sqlite3"

    CacheDb(db_path).initialize()

    assert _table_names(db_path) == {"projects", "drone_tickets", "scan_warnings"}


def test_health_check_returns_true_for_initialized_db(tmp_path: Path) -> None:
    db_path = tmp_path / "cache.sqlite3"
    cache = CacheDb(db_path)
    cache.initialize()

    assert cache.health_check() is True


def test_health_check_returns_false_for_corrupt_non_sqlite_file(tmp_path: Path) -> None:
    db_path = tmp_path / "cache.sqlite3"
    db_path.write_text("not sqlite", encoding="utf-8")

    assert CacheDb(db_path).health_check() is False


def test_reset_recreates_corrupt_db(tmp_path: Path) -> None:
    db_path = tmp_path / "cache.sqlite3"
    db_path.write_text("not sqlite", encoding="utf-8")
    cache = CacheDb(db_path)

    cache.reset()

    assert cache.health_check() is True
    assert _table_names(db_path) == {"projects", "drone_tickets", "scan_warnings"}


def test_upsert_project_and_list_projects_round_trip_cache_fields(tmp_path: Path) -> None:
    db_path = tmp_path / "cache.sqlite3"
    project_path = tmp_path / "CR" / "2026" / ProjectState.UAT_PREPARE.value / "PAYMENT_MODULE_UPGRADE"
    row = _project_row(project_path)
    cache = CacheDb(db_path)
    cache.initialize()

    cache.upsert_project(row)

    assert cache.list_projects() == [row]


def test_list_projects_filters_by_year(tmp_path: Path) -> None:
    db_path = tmp_path / "cache.sqlite3"
    cache = CacheDb(db_path)
    cache.initialize()
    row_2026 = _project_row(tmp_path / "CR" / "2026" / "UAT_PREPARE" / "A", year="2026", project_name="A")
    row_2027 = _project_row(tmp_path / "CR" / "2027" / "UAT_PREPARE" / "B", year="2027", project_name="B")
    cache.upsert_project(row_2026)
    cache.upsert_project(row_2027)

    assert cache.list_projects(year="2026") == [row_2026]


def test_replace_projects_for_year_removes_stale_rows_for_that_year_only(tmp_path: Path) -> None:
    db_path = tmp_path / "cache.sqlite3"
    cache = CacheDb(db_path)
    cache.initialize()
    stale = _project_row(tmp_path / "CR" / "2026" / "UAT_PREPARE" / "STALE", year="2026", project_name="STALE")
    current = _project_row(tmp_path / "CR" / "2026" / "UAT_PREPARE" / "CURRENT", year="2026", project_name="CURRENT")
    cache.upsert_project(stale)

    cache.replace_projects_for_year("2026", [current])

    assert cache.list_projects(year="2026") == [current]


def test_replace_projects_for_year_does_not_remove_other_years(tmp_path: Path) -> None:
    db_path = tmp_path / "cache.sqlite3"
    cache = CacheDb(db_path)
    cache.initialize()
    other_year = _project_row(tmp_path / "CR" / "2027" / "UAT_PREPARE" / "OTHER", year="2027", project_name="OTHER")
    replacement = _project_row(tmp_path / "CR" / "2026" / "UAT_PREPARE" / "CURRENT", year="2026", project_name="CURRENT")
    cache.upsert_project(other_year)

    cache.replace_projects_for_year("2026", [replacement])

    assert cache.list_projects(year="2027") == [other_year]


def test_replace_drone_tickets_for_project_and_list_round_trip_fields(tmp_path: Path) -> None:
    db_path = tmp_path / "cache.sqlite3"
    project_path = tmp_path / "CR" / "2026" / "UAT_PREPARE" / "PAYMENT_MODULE_UPGRADE"
    row = _drone_row(project_path)
    cache = CacheDb(db_path)
    cache.initialize()

    cache.replace_drone_tickets_for_project(project_path, [row])

    assert cache.list_drone_tickets(project_path) == [row]


def test_replacing_drone_tickets_for_one_project_does_not_affect_another_project(tmp_path: Path) -> None:
    db_path = tmp_path / "cache.sqlite3"
    project_a = tmp_path / "CR" / "2026" / "UAT_PREPARE" / "A"
    project_b = tmp_path / "CR" / "2026" / "UAT_PREPARE" / "B"
    row_b = _drone_row(project_b, drone_ticket="D-SSIDBI-160", owner="Bob", display="D-SSIDBI-160 ↗")
    cache = CacheDb(db_path)
    cache.initialize()
    cache.replace_drone_tickets_for_project(project_a, [_drone_row(project_a)])
    cache.replace_drone_tickets_for_project(project_b, [row_b])

    cache.replace_drone_tickets_for_project(project_a, [])

    assert cache.list_drone_tickets(project_b) == [row_b]


def test_replace_projects_for_year_removes_stale_drone_rows_for_removed_projects(tmp_path: Path) -> None:
    db_path = tmp_path / "cache.sqlite3"
    cache = CacheDb(db_path)
    cache.initialize()
    stale_project = tmp_path / "CR" / "2026" / "UAT_PREPARE" / "STALE"
    current_project = tmp_path / "CR" / "2026" / "UAT_PREPARE" / "CURRENT"
    cache.upsert_project(_project_row(stale_project, year="2026", project_name="STALE"))
    cache.replace_drone_tickets_for_project(stale_project, [_drone_row(stale_project)])

    cache.replace_projects_for_year(
        "2026",
        [_project_row(current_project, year="2026", project_name="CURRENT")],
    )

    assert cache.list_drone_tickets(stale_project) == []
