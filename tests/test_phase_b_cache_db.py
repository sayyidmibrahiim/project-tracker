from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from core.enums import CRState, DroneState, ProjectState
from infrastructure.cache_db import CacheDb, CachedDroneTicketRow, CachedProjectRow


def _project_row(
    project_path: Path,
    *,
    year: str = "2026",
    project_state: ProjectState = ProjectState.UAT_PREPARE,
    project_name: str = "PAYMENT_MODULE_UPGRADE",
    cr_state: CRState = CRState.APPROVED,
    drone_paths_json: str = "[]",
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
        drone_paths_json=drone_paths_json,
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

    assert _table_names(db_path) == {
        "project_index",
        "drone_tickets",
        "scan_warnings",
        "notifications",
        "automation_rule_logs",
        "approval_polling_jobs",
        "automation_logs",
        "second_brain_activity",
    }


def test_initialize_creates_notifications_and_rule_logs_with_documented_columns(tmp_path: Path) -> None:
    import sqlite3

    db_path = tmp_path / "cache.sqlite3"

    CacheDb(db_path).initialize()

    with sqlite3.connect(db_path) as connection:
        notification_columns = [
            row[1] for row in connection.execute("PRAGMA table_info(notifications)").fetchall()
        ]
        rule_log_columns = [
            row[1] for row in connection.execute("PRAGMA table_info(automation_rule_logs)").fetchall()
        ]

    assert notification_columns == [
        "id",
        "type",
        "title",
        "message",
        "timestamp",
        "project_path",
        "dismissed",
        "created_at",
    ]
    assert rule_log_columns == [
        "id",
        "rule_id",
        "rule_name",
        "trigger_type",
        "conditions_passed",
        "actions_executed",
        "success",
        "error_message",
        "timestamp",
    ]


def test_notifications_and_rule_logs_tables_are_queryable_after_init(tmp_path: Path) -> None:
    import sqlite3

    db_path = tmp_path / "cache.sqlite3"

    CacheDb(db_path).initialize()

    with sqlite3.connect(db_path) as connection:
        notifications = connection.execute("SELECT * FROM notifications").fetchall()
        rule_logs = connection.execute("SELECT * FROM automation_rule_logs").fetchall()

    assert notifications == []
    assert rule_logs == []


def test_project_index_schema_matches_prd_cache_columns(tmp_path: Path) -> None:
    import sqlite3

    db_path = tmp_path / "cache.sqlite3"

    CacheDb(db_path).initialize()

    with sqlite3.connect(db_path) as connection:
        columns = [row[1] for row in connection.execute("PRAGMA table_info(project_index)").fetchall()]

    assert columns == [
        "path",
        "name",
        "year",
        "folder_state",
        "cr_link",
        "cr_number",
        "cr_state",
        "cr_pending_approval_at",
        "start_datetime",
        "end_datetime",
        "drone_tickets_json",
        "drone_paths_json",
        "t10_status",
        "appcode",
        "project_type",
        "non_cr_state",
        "created_at",
        "updated_at",
        "scanned_at",
    ]


def test_initialize_migrates_existing_project_index_with_drone_paths_json(tmp_path: Path) -> None:
    import sqlite3

    db_path = tmp_path / "cache.sqlite3"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE project_index (
                path TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                year TEXT NOT NULL,
                folder_state TEXT NOT NULL,
                cr_link TEXT,
                cr_number TEXT,
                cr_state TEXT,
                cr_pending_approval_at TEXT,
                start_datetime TEXT,
                end_datetime TEXT,
                drone_tickets_json TEXT,
                t10_status TEXT,
                updated_at TEXT,
                scanned_at TEXT DEFAULT (datetime('now'))
            )
            """
        )

    CacheDb(db_path).initialize()

    with sqlite3.connect(db_path) as connection:
        columns = [row[1] for row in connection.execute("PRAGMA table_info(project_index)").fetchall()]
        drone_default = connection.execute(
            "SELECT dflt_value FROM pragma_table_info('project_index') WHERE name = 'drone_paths_json'"
        ).fetchone()[0]
        appcode_default = connection.execute(
            "SELECT dflt_value FROM pragma_table_info('project_index') WHERE name = 'appcode'"
        ).fetchone()[0]
        project_type_default = connection.execute(
            "SELECT dflt_value FROM pragma_table_info('project_index') WHERE name = 'project_type'"
        ).fetchone()[0]

    assert "drone_paths_json" in columns
    assert "appcode" in columns
    assert "project_type" in columns
    assert "non_cr_state" in columns
    assert drone_default == "'[]'"
    assert appcode_default == "''"
    assert project_type_default == "'CR'"


def test_health_check_returns_true_for_initialized_db(tmp_path: Path) -> None:
    db_path = tmp_path / "cache.sqlite3"
    cache = CacheDb(db_path)
    cache.initialize()

    assert cache.health_check() is True


def test_health_check_returns_false_when_project_index_has_null_cr_state(tmp_path: Path) -> None:
    import sqlite3

    db_path = tmp_path / "cache.sqlite3"
    cache = CacheDb(db_path)
    cache.initialize()

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO project_index (path, name, year, folder_state, cr_state)
            VALUES (?, ?, ?, ?, NULL)
            """,
            (str(tmp_path / "PROJECT"), "PROJECT", "2026", ProjectState.UAT_PREPARE.value),
        )

    assert cache.health_check() is False


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
    assert _table_names(db_path) == {
        "project_index",
        "drone_tickets",
        "scan_warnings",
        "notifications",
        "automation_rule_logs",
        "approval_polling_jobs",
        "automation_logs",
        "second_brain_activity",
    }


def test_reset_recreates_notifications_and_rule_logs_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "cache.sqlite3"
    cache = CacheDb(db_path)
    cache.initialize()

    cache.reset()

    table_names = _table_names(db_path)
    assert "notifications" in table_names
    assert "automation_rule_logs" in table_names


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


def test_notification_insert_and_list_round_trip_preserves_dismissed(tmp_path: Path) -> None:
    from core.models import Notification, local_now

    cache = CacheDb(tmp_path / "cache.sqlite3")
    cache.initialize()

    created = Notification(
        id="n-1",
        type="WARNING",
        title="T-10 violation",
        message="Move blocked",
        timestamp=local_now(),
        project_path=tmp_path / "2026" / "UAT_PREPARE" / "PROJECT_A",
        dismissed=False,
    )
    cache.insert_notification(created)

    loaded = cache.list_notifications()
    assert len(loaded) == 1
    assert loaded[0].id == "n-1"
    assert loaded[0].type == "WARNING"
    assert loaded[0].dismissed is False
    assert loaded[0].project_path == created.project_path


def test_notification_set_dismissed_persists(tmp_path: Path) -> None:
    from core.models import Notification, local_now

    cache = CacheDb(tmp_path / "cache.sqlite3")
    cache.initialize()
    cache.insert_notification(
        Notification(
            id="n-1",
            type="INFO",
            title="Title",
            message="Message",
            timestamp=local_now(),
            project_path=None,
            dismissed=False,
        )
    )

    cache.set_notification_dismissed("n-1", True)

    loaded = cache.list_notifications()
    assert loaded[0].dismissed is True
    assert loaded[0].project_path is None


def test_notification_service_persists_and_reloads_dismissed_state(tmp_path: Path) -> None:
    from services.notification_service import NotificationService

    db_path = tmp_path / "cache.sqlite3"
    cache = CacheDb(db_path)
    cache.initialize()

    service = NotificationService(event_publisher=None, cache=cache)
    created = service.add("WARNING", "Heads up", "Check project")
    service.dismiss(created.id)

    # Simulate a restart: a fresh service over the same cache loads prior state.
    reloaded = NotificationService(event_publisher=None, cache=CacheDb(db_path))
    reloaded.load_persisted()

    all_notifications = reloaded.get_all()
    assert len(all_notifications) == 1
    assert all_notifications[0].id == created.id
    assert all_notifications[0].dismissed is True


def test_approval_polling_jobs_persist_and_resume(tmp_path):
    from infrastructure.cache_db import CacheDb

    cache = CacheDb(tmp_path / "cache.db")
    cache.initialize()
    assert cache.health_check() is True

    row = {
        "job_id": "j-1",
        "project_path": "C:/root/APP/2026/CR/UAT_PREPARE/CR-2026-001",
        "request_type": "uat",
        "cr_number": "CR-2026-001",
        "email_subject": "Request UAT Approval CR-2026-001",
        "sent_at": "2026-07-06T10:00:00",
        "status": "polling",
        "reply_received_at": None,
    }
    cache.upsert_approval_job(row)
    assert [j["job_id"] for j in cache.list_polling_approval_jobs()] == ["j-1"]

    latest = cache.latest_approval_job(row["project_path"], "uat")
    assert latest is not None and latest["status"] == "polling"

    cache.update_approval_job("j-1", status="completed", reply_received_at="2026-07-06T11:00:00")
    assert cache.list_polling_approval_jobs() == []
    latest = cache.latest_approval_job(row["project_path"], "uat")
    assert latest["status"] == "completed"
    assert latest["reply_received_at"] == "2026-07-06T11:00:00"


# ── Task 5: second_brain_activity (capped recent-activity ledger) ──────────

from infrastructure.cache_db import SECOND_BRAIN_ACTIVITY_CAP, SecondBrainActivityRow  # noqa: E402


def _activity_row(
    *,
    item_id: str,
    action: str,
    ts: datetime,
    path: str = "notes/a.md",
    title: str = "A",
    source: str = "personal",
) -> SecondBrainActivityRow:
    return SecondBrainActivityRow(
        item_id=item_id,
        path=Path(path),
        title=title,
        source=source,
        action=action,
        timestamp=ts,
    )


def test_append_second_brain_activity_round_trips_fields(tmp_path: Path) -> None:
    cache = CacheDb(tmp_path / "cache.sqlite3")
    cache.initialize()
    ts = datetime(2026, 7, 12, 9, 0, tzinfo=timezone.utc)

    persisted = cache.append_second_brain_activity(
        _activity_row(item_id="note-1", action="opened", ts=ts)
    )

    assert persisted.id > 0
    listed = cache.list_second_brain_activity()
    assert len(listed) == 1
    assert listed[0].item_id == "note-1"
    assert listed[0].action == "opened"
    assert listed[0].path == Path("notes/a.md")
    assert listed[0].title == "A"
    assert listed[0].source == "personal"
    assert listed[0].timestamp == ts


def test_list_second_brain_activity_orders_newest_first_by_timestamp_then_id(tmp_path: Path) -> None:
    cache = CacheDb(tmp_path / "cache.sqlite3")
    cache.initialize()
    cache.append_second_brain_activity(
        _activity_row(item_id="note-1", action="created", ts=datetime(2026, 7, 10, tzinfo=timezone.utc))
    )
    cache.append_second_brain_activity(
        _activity_row(item_id="note-2", action="created", ts=datetime(2026, 7, 12, tzinfo=timezone.utc))
    )
    cache.append_second_brain_activity(
        _activity_row(item_id="note-3", action="created", ts=datetime(2026, 7, 11, tzinfo=timezone.utc))
    )

    ordered = [row.item_id for row in cache.list_second_brain_activity()]

    assert ordered == ["note-2", "note-3", "note-1"]


@pytest.mark.parametrize("action", ["opened", "opened_externally"])
def test_append_second_brain_activity_dedupes_repeated_opens_and_moves_to_newest(
    tmp_path: Path,
    action: str,
) -> None:
    cache = CacheDb(tmp_path / "cache.sqlite3")
    cache.initialize()
    cache.append_second_brain_activity(
        _activity_row(item_id="note-1", action=action, ts=datetime(2026, 7, 1, tzinfo=timezone.utc))
    )
    cache.append_second_brain_activity(
        _activity_row(item_id="note-2", action=action, ts=datetime(2026, 7, 2, tzinfo=timezone.utc))
    )

    # note-1 opened again, later than note-2 — should update in place, not duplicate.
    cache.append_second_brain_activity(
        _activity_row(
            item_id="note-1", action=action, ts=datetime(2026, 7, 3, tzinfo=timezone.utc), title="A renamed"
        )
    )

    rows = cache.list_second_brain_activity()
    assert [row.item_id for row in rows] == ["note-1", "note-2"]
    assert len(rows) == 2
    assert rows[0].title == "A renamed"


def test_append_second_brain_activity_keeps_distinct_actions_for_same_item(tmp_path: Path) -> None:
    cache = CacheDb(tmp_path / "cache.sqlite3")
    cache.initialize()
    cache.append_second_brain_activity(
        _activity_row(item_id="note-1", action="created", ts=datetime(2026, 7, 1, tzinfo=timezone.utc))
    )
    cache.append_second_brain_activity(
        _activity_row(item_id="note-1", action="opened", ts=datetime(2026, 7, 2, tzinfo=timezone.utc))
    )

    rows = cache.list_second_brain_activity(item_id="note-1")

    assert {row.action for row in rows} == {"created", "opened"}
    assert len(rows) == 2


@pytest.mark.parametrize("action", ["edited", "renamed"])
def test_append_second_brain_activity_preserves_repeated_mutations(
    tmp_path: Path, action: str
) -> None:
    cache = CacheDb(tmp_path / "cache.sqlite3")
    cache.initialize()
    cache.append_second_brain_activity(
        _activity_row(item_id="note-1", action=action, ts=datetime(2026, 7, 1, tzinfo=timezone.utc))
    )
    cache.append_second_brain_activity(
        _activity_row(item_id="note-1", action=action, ts=datetime(2026, 7, 2, tzinfo=timezone.utc))
    )

    rows = cache.list_second_brain_activity(item_id="note-1")

    assert [row.action for row in rows] == [action, action]


def test_append_second_brain_activity_caps_at_200_newest_rows(tmp_path: Path) -> None:
    cache = CacheDb(tmp_path / "cache.sqlite3")
    cache.initialize()
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for i in range(SECOND_BRAIN_ACTIVITY_CAP + 10):
        cache.append_second_brain_activity(
            _activity_row(item_id=f"note-{i}", action="opened", ts=base + timedelta(minutes=i))
        )

    rows = cache.list_second_brain_activity(limit=SECOND_BRAIN_ACTIVITY_CAP + 50)

    assert len(rows) == SECOND_BRAIN_ACTIVITY_CAP
    # Oldest 10 (note-0..note-9) trimmed; newest kept.
    assert rows[0].item_id == f"note-{SECOND_BRAIN_ACTIVITY_CAP + 9}"
    assert "note-0" not in {row.item_id for row in rows}
    assert "note-9" not in {row.item_id for row in rows}
    assert "note-10" in {row.item_id for row in rows}


def test_list_second_brain_activity_filters_by_item_id(tmp_path: Path) -> None:
    cache = CacheDb(tmp_path / "cache.sqlite3")
    cache.initialize()
    cache.append_second_brain_activity(
        _activity_row(item_id="note-1", action="opened", ts=datetime(2026, 7, 1, tzinfo=timezone.utc))
    )
    cache.append_second_brain_activity(
        _activity_row(item_id="note-2", action="opened", ts=datetime(2026, 7, 2, tzinfo=timezone.utc))
    )

    rows = cache.list_second_brain_activity(item_id="note-1")

    assert [row.item_id for row in rows] == ["note-1"]


def test_clear_second_brain_activity_deletes_all_rows(tmp_path: Path) -> None:
    cache = CacheDb(tmp_path / "cache.sqlite3")
    cache.initialize()
    cache.append_second_brain_activity(
        _activity_row(item_id="note-1", action="opened", ts=datetime(2026, 7, 1, tzinfo=timezone.utc))
    )

    deleted = cache.clear_second_brain_activity()

    assert deleted == 1
    assert cache.list_second_brain_activity() == []
