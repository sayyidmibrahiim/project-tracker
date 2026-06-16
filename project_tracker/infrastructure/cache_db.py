from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from project_tracker.core.enums import CRState, DroneState, ProjectState
from project_tracker.core.models import (
    Notification,
    datetime_from_json,
    datetime_to_json,
    local_now,
)
from project_tracker.core.rules import extract_cr_number, extract_drone_ticket, validate_t10
from project_tracker.infrastructure.filesystem import ScannedProject, scan_year
from project_tracker.infrastructure.metadata_store import MetadataStore


def _placeholders(values: tuple[str, ...]) -> str:
    return ", ".join("?" for _ in values)


def _t10_status(scanned: ScannedProject) -> str:
    metadata = scanned.metadata
    if metadata.start_datetime is None:
        return "UNKNOWN"
    return "PASS" if validate_t10(metadata).passed else "FAIL"


@dataclass(frozen=True, slots=True)
class CachedProjectRow:
    project_path: Path
    year: str
    project_state: ProjectState
    project_name: str
    cr_link: str = ""
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    cr_number: str | None = ""
    cr_state: CRState = CRState.PENDING_SUBMISSION
    cr_pending_approval_at: datetime | None = None
    drone_tickets_json: str = "[]"
    t10_status: str = "UNKNOWN"
    updated_at: datetime | None = None
    scanned_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class AutomationRuleLogRow:
    rule_id: str
    rule_name: str = ""
    trigger_type: str = ""
    conditions_passed: int = 0
    actions_executed: str = "[]"
    success: bool = False
    error_message: str | None = None
    timestamp: datetime | None = None


@dataclass(frozen=True, slots=True)
class CachedDroneTicketRow:
    project_path: Path
    subfolder_name: str | None = None
    drone_ticket: str | None = ""
    drone_state: DroneState = DroneState.UAT
    owner: str = ""
    display: str | None = ""
    updated_at: datetime | None = None


def cached_project_row_from_scan(scanned: ScannedProject) -> CachedProjectRow:
    metadata = scanned.metadata
    return CachedProjectRow(
        project_path=scanned.path,
        year=scanned.year,
        project_state=scanned.project_state,
        project_name=metadata.project_name or scanned.path.name,
        cr_link=metadata.cr_link,
        start_datetime=metadata.start_datetime,
        end_datetime=metadata.end_datetime,
        cr_number=extract_cr_number(metadata.cr_link),
        cr_state=metadata.cr_state,
        cr_pending_approval_at=metadata.cr_pending_approval_at,
        drone_tickets_json=json.dumps([ticket.to_dict() for ticket in metadata.drone_tickets], ensure_ascii=False),
        t10_status=_t10_status(scanned),
        updated_at=metadata.updated_at,
        scanned_at=local_now(),
    )


def cached_drone_rows_from_scan(scanned: ScannedProject) -> list[CachedDroneTicketRow]:
    rows: list[CachedDroneTicketRow] = []
    for ticket in scanned.metadata.drone_tickets:
        drone_ticket = extract_drone_ticket(ticket.drone_link)
        rows.append(
            CachedDroneTicketRow(
                project_path=scanned.path,
                subfolder_name=ticket.subfolder_name,
                drone_ticket=drone_ticket,
                drone_state=ticket.drone_state,
                owner=ticket.owner,
                display=drone_ticket,
                updated_at=ticket.drone_state_updated_at,
            )
        )
    return rows


def rebuild_year_cache(
    cache: CacheDb,
    year_path: Path,
    metadata_store: MetadataStore | None = None,
) -> list[str]:
    store = metadata_store or MetadataStore()
    scanned_projects = scan_year(year_path, store)
    cache.replace_projects_for_year(
        year_path.name,
        [cached_project_row_from_scan(scanned) for scanned in scanned_projects],
    )
    for scanned in scanned_projects:
        cache.replace_drone_tickets_for_project(scanned.path, cached_drone_rows_from_scan(scanned))
    return list(store.warnings)


class CacheDb:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            self._create_schema(connection)

    def health_check(self) -> bool:
        try:
            with self._connect() as connection:
                integrity = connection.execute("PRAGMA integrity_check").fetchone()
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
                    ).fetchall()
                }
                project_states = tuple(state.value for state in ProjectState)
                cr_states = tuple(state.value for state in CRState)
                drone_states = tuple(state.value for state in DroneState)
                invalid_project_states = connection.execute(
                    f"SELECT 1 FROM project_index WHERE folder_state NOT IN ({_placeholders(project_states)}) LIMIT 1",
                    project_states,
                ).fetchone()
                invalid_cr_states = connection.execute(
                    f"SELECT 1 FROM project_index WHERE cr_state IS NULL OR cr_state NOT IN ({_placeholders(cr_states)}) LIMIT 1",
                    cr_states,
                ).fetchone()
                invalid_drone_states = connection.execute(
                    f"SELECT 1 FROM drone_tickets WHERE drone_state NOT IN ({_placeholders(drone_states)}) LIMIT 1",
                    drone_states,
                ).fetchone()
        except sqlite3.DatabaseError:
            return False
        return (
            integrity == ("ok",)
            and tables == {
                "project_index",
                "drone_tickets",
                "scan_warnings",
                "notifications",
                "automation_rule_logs",
            }
            and invalid_project_states is None
            and invalid_cr_states is None
            and invalid_drone_states is None
        )

    def reset(self) -> None:
        if self.db_path.exists():
            self.db_path.unlink()
        self.initialize()

    def upsert_project(self, row: CachedProjectRow) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO project_index (
                    path,
                    name,
                    year,
                    folder_state,
                    cr_link,
                    cr_number,
                    cr_state,
                    cr_pending_approval_at,
                    start_datetime,
                    end_datetime,
                    drone_tickets_json,
                    t10_status,
                    updated_at,
                    scanned_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    name = excluded.name,
                    year = excluded.year,
                    folder_state = excluded.folder_state,
                    cr_link = excluded.cr_link,
                    cr_number = excluded.cr_number,
                    cr_state = excluded.cr_state,
                    cr_pending_approval_at = excluded.cr_pending_approval_at,
                    start_datetime = excluded.start_datetime,
                    end_datetime = excluded.end_datetime,
                    drone_tickets_json = excluded.drone_tickets_json,
                    t10_status = excluded.t10_status,
                    updated_at = excluded.updated_at,
                    scanned_at = excluded.scanned_at
                """,
                self._project_values(row),
            )

    def replace_projects_for_year(self, year: str, rows: Iterable[CachedProjectRow]) -> None:
        replacement_rows = list(rows)
        if any(row.year != year for row in replacement_rows):
            raise ValueError("CachedProjectRow.year must match replacement year")
        replacement_paths = {str(row.project_path) for row in replacement_rows}
        with self._connect() as connection:
            existing_paths = {
                row[0]
                for row in connection.execute(
                    "SELECT path FROM project_index WHERE year = ?",
                    (year,),
                ).fetchall()
            }
            removed_paths = existing_paths - replacement_paths
            for project_path in removed_paths:
                connection.execute("DELETE FROM drone_tickets WHERE project_path = ?", (project_path,))
                connection.execute("DELETE FROM project_index WHERE path = ?", (project_path,))
            for row in replacement_rows:
                connection.execute(
                    """
                    INSERT INTO project_index (
                        path,
                        name,
                        year,
                        folder_state,
                        cr_link,
                        cr_number,
                        cr_state,
                        cr_pending_approval_at,
                        start_datetime,
                        end_datetime,
                        drone_tickets_json,
                        t10_status,
                        updated_at,
                        scanned_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(path) DO UPDATE SET
                        name = excluded.name,
                        year = excluded.year,
                        folder_state = excluded.folder_state,
                        cr_link = excluded.cr_link,
                        cr_number = excluded.cr_number,
                        cr_state = excluded.cr_state,
                        cr_pending_approval_at = excluded.cr_pending_approval_at,
                        start_datetime = excluded.start_datetime,
                        end_datetime = excluded.end_datetime,
                        drone_tickets_json = excluded.drone_tickets_json,
                        t10_status = excluded.t10_status,
                        updated_at = excluded.updated_at,
                        scanned_at = excluded.scanned_at
                    """,
                    self._project_values(row),
                )

    def list_projects(self, year: str | None = None) -> list[CachedProjectRow]:
        with self._connect() as connection:
            if year is None:
                rows = connection.execute(
                    """
                    SELECT path, year, folder_state, name, cr_link, start_datetime,
                           end_datetime, cr_number, cr_state, cr_pending_approval_at,
                           drone_tickets_json, t10_status, updated_at, scanned_at
                    FROM project_index
                    ORDER BY year, name, path
                    """
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT path, year, folder_state, name, cr_link, start_datetime,
                           end_datetime, cr_number, cr_state, cr_pending_approval_at,
                           drone_tickets_json, t10_status, updated_at, scanned_at
                    FROM project_index
                    WHERE year = ?
                    ORDER BY year, name, path
                    """,
                    (year,),
                ).fetchall()
        return [self._project_from_row(row) for row in rows]

    def replace_drone_tickets_for_project(
        self,
        project_path: Path,
        rows: Iterable[CachedDroneTicketRow],
    ) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM drone_tickets WHERE project_path = ?", (str(project_path),))
            connection.executemany(
                """
                INSERT INTO drone_tickets (
                    project_path,
                    subfolder_name,
                    drone_ticket,
                    drone_state,
                    owner,
                    display,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [self._drone_values(row) for row in rows],
            )

    def list_drone_tickets(self, project_path: Path) -> list[CachedDroneTicketRow]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT project_path, subfolder_name, drone_ticket, drone_state, owner, display, updated_at
                FROM drone_tickets
                WHERE project_path = ?
                ORDER BY subfolder_name, drone_ticket
                """,
                (str(project_path),),
            ).fetchall()
        return [self._drone_from_row(row) for row in rows]

    def append_rule_log(self, row: AutomationRuleLogRow) -> int:
        """Persist a single automation rule execution result.

        Returns the new row id. Raises sqlite3.DatabaseError on write failure
        so callers can retain the in-memory result and surface the error.
        """
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO automation_rule_logs (
                    rule_id,
                    rule_name,
                    trigger_type,
                    conditions_passed,
                    actions_executed,
                    success,
                    error_message,
                    timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._rule_log_values(row),
            )
            return int(cursor.lastrowid or 0)

    def list_rule_logs(self) -> list[AutomationRuleLogRow]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT rule_id, rule_name, trigger_type, conditions_passed,
                       actions_executed, success, error_message, timestamp
                FROM automation_rule_logs
                ORDER BY id
                """
            ).fetchall()
        return [self._rule_log_from_row(row) for row in rows]

    def insert_notification(self, notification: Notification) -> None:
        """Persist a notification keyed by its id.

        Idempotent: re-inserting the same id updates the stored content and
        dismissed state. A single-statement write means a failure raises
        sqlite3.DatabaseError and leaves the prior persisted state unchanged
        with no partial update, so callers can surface the error.
        """
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO notifications (
                    id,
                    type,
                    title,
                    message,
                    timestamp,
                    project_path,
                    dismissed
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    type = excluded.type,
                    title = excluded.title,
                    message = excluded.message,
                    timestamp = excluded.timestamp,
                    project_path = excluded.project_path,
                    dismissed = excluded.dismissed
                """,
                self._notification_values(notification),
            )

    def set_notification_dismissed(self, notification_id: str, dismissed: bool = True) -> None:
        """Persist the dismissed state for a single notification.

        Raises sqlite3.DatabaseError on write failure so callers can retain the
        prior persisted state and surface the error.
        """
        with self._connect() as connection:
            connection.execute(
                "UPDATE notifications SET dismissed = ? WHERE id = ?",
                (1 if dismissed else 0, notification_id),
            )

    def list_notifications(self) -> list[Notification]:
        """Load all persisted notifications preserving stored dismissed state."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, type, title, message, timestamp, project_path, dismissed
                FROM notifications
                ORDER BY created_at, id
                """
            ).fetchall()
        return [self._notification_from_row(row) for row in rows]

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _create_schema(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS project_index (
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
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS drone_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_path TEXT NOT NULL,
                subfolder_name TEXT,
                drone_ticket TEXT NOT NULL DEFAULT '',
                drone_state TEXT NOT NULL,
                owner TEXT NOT NULL DEFAULT '',
                display TEXT NOT NULL DEFAULT '',
                updated_at TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS scan_warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year TEXT NOT NULL DEFAULT '',
                project_path TEXT NOT NULL DEFAULT '',
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL DEFAULT '',
                message TEXT NOT NULL DEFAULT '',
                timestamp TEXT,
                project_path TEXT NOT NULL DEFAULT '',
                dismissed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS automation_rule_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_id TEXT NOT NULL DEFAULT '',
                rule_name TEXT NOT NULL DEFAULT '',
                trigger_type TEXT NOT NULL DEFAULT '',
                conditions_passed INTEGER NOT NULL DEFAULT 0,
                actions_executed TEXT NOT NULL DEFAULT '',
                success INTEGER NOT NULL DEFAULT 0,
                error_message TEXT,
                timestamp TEXT
            )
            """
        )

    @staticmethod
    def _project_values(
        row: CachedProjectRow,
    ) -> tuple[str, str, str, str, str, str | None, str, str | None, str | None, str | None, str, str, str | None, str | None]:
        return (
            str(row.project_path),
            row.project_name,
            row.year,
            row.project_state.value,
            row.cr_link,
            row.cr_number or "",
            row.cr_state.value,
            datetime_to_json(row.cr_pending_approval_at),
            datetime_to_json(row.start_datetime),
            datetime_to_json(row.end_datetime),
            row.drone_tickets_json,
            row.t10_status,
            datetime_to_json(row.updated_at),
            datetime_to_json(row.scanned_at),
        )

    @staticmethod
    def _project_from_row(
        row: tuple[
            str,
            str,
            str,
            str,
            str | None,
            str | None,
            str | None,
            str,
            str | None,
            str | None,
            str | None,
            str | None,
            str | None,
            str | None,
        ]
    ) -> CachedProjectRow:
        return CachedProjectRow(
            project_path=Path(row[0]),
            year=row[1],
            project_state=ProjectState(row[2]),
            project_name=row[3],
            cr_link=row[4] or "",
            start_datetime=datetime_from_json(row[5]),
            end_datetime=datetime_from_json(row[6]),
            cr_number=row[7],
            cr_state=CRState(row[8]),
            cr_pending_approval_at=datetime_from_json(row[9]),
            drone_tickets_json=row[10] or "[]",
            t10_status=row[11] or "UNKNOWN",
            updated_at=datetime_from_json(row[12]),
            scanned_at=datetime_from_json(row[13]),
        )

    @staticmethod
    def _drone_values(row: CachedDroneTicketRow) -> tuple[str, str | None, str | None, str, str, str | None, str | None]:
        return (
            str(row.project_path),
            row.subfolder_name,
            row.drone_ticket or "",
            row.drone_state.value,
            row.owner,
            row.display or "",
            datetime_to_json(row.updated_at),
        )

    @staticmethod
    def _drone_from_row(row: tuple[str, str | None, str | None, str, str, str | None, str | None]) -> CachedDroneTicketRow:
        return CachedDroneTicketRow(
            project_path=Path(row[0]),
            subfolder_name=row[1],
            drone_ticket=row[2],
            drone_state=DroneState(row[3]),
            owner=row[4],
            display=row[5],
            updated_at=datetime_from_json(row[6]),
        )

    @staticmethod
    def _rule_log_values(
        row: AutomationRuleLogRow,
    ) -> tuple[str, str, str, int, str, int, str | None, str | None]:
        return (
            row.rule_id,
            row.rule_name,
            row.trigger_type,
            int(row.conditions_passed),
            row.actions_executed,
            1 if row.success else 0,
            row.error_message,
            datetime_to_json(row.timestamp),
        )

    @staticmethod
    def _rule_log_from_row(
        row: tuple[str, str, str, int, str, int, str | None, str | None],
    ) -> AutomationRuleLogRow:
        return AutomationRuleLogRow(
            rule_id=row[0],
            rule_name=row[1],
            trigger_type=row[2],
            conditions_passed=int(row[3]),
            actions_executed=row[4] or "[]",
            success=bool(row[5]),
            error_message=row[6],
            timestamp=datetime_from_json(row[7]),
        )

    @staticmethod
    def _notification_values(
        notification: Notification,
    ) -> tuple[str, str, str, str, str | None, str, int]:
        return (
            notification.id,
            notification.type,
            notification.title,
            notification.message,
            datetime_to_json(notification.timestamp),
            str(notification.project_path) if notification.project_path else "",
            1 if notification.dismissed else 0,
        )

    @staticmethod
    def _notification_from_row(
        row: tuple[str, str, str, str, str | None, str | None, int],
    ) -> Notification:
        project_path = Path(row[5]) if row[5] else None
        return Notification(
            id=row[0],
            type=row[1],
            title=row[2],
            message=row[3],
            timestamp=datetime_from_json(row[4]) or local_now(),
            project_path=project_path,
            dismissed=bool(row[6]),
        )
