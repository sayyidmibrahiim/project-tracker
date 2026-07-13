from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Iterable

from core.enums import CRState, DroneState, NonCrState, ProjectState, ProjectType
from core.models import (
    Notification,
    datetime_from_json,
    datetime_to_json,
    local_now,
)
from core.rules import extract_cr_number, extract_drone_ticket, validate_t10

NON_CR_FOLDER_STATE = "NON_CR"
#: Task 5: capped recent-activity ledger — newest ``SECOND_BRAIN_ACTIVITY_CAP``
#: rows retained, oldest trimmed after every append.
SECOND_BRAIN_ACTIVITY_CAP = 200
from infrastructure.filesystem import ScannedProject, scan_appcode_year, scan_year
from infrastructure.metadata_store import MetadataStore


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
    project_state: ProjectState | None
    project_name: str
    cr_link: str = ""
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    cr_number: str | None = ""
    cr_state: CRState = CRState.PENDING_SUBMISSION
    cr_pending_approval_at: datetime | None = None
    drone_tickets_json: str = "[]"
    drone_paths_json: str = "[]"
    t10_status: str = "UNKNOWN"
    appcode: str = ""
    project_type: ProjectType = ProjectType.CR
    non_cr_state: NonCrState | None = None
    created_at: datetime | None = None
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
class AutomationLogRow:
    """Slice 5: cross-module automation log entry (LogEntry logical model)."""

    id: int = 0
    module: str = ""  # outlook / teams / cr_automation / rules_engine / all
    rule_id: str = ""
    cr_id: str = ""
    timestamp: datetime | None = None
    event_type: str = ""  # e.g. APPROVAL_TEST_DRAFT_OPENED, AUTO_UPDATE_CR_STATE
    detail: str = ""


@dataclass(frozen=True, slots=True)
class SecondBrainActivityRow:
    """Task 5: capped recent-activity ledger entry for Second Brain items.

    Deduped by ``(item_id, action)`` — a repeat of the same action on the
    same item updates the existing row's path/title/source/timestamp instead
    of accumulating a duplicate.
    """

    id: int = 0
    item_id: str = ""
    path: Path = Path("")
    title: str = ""
    source: str = "personal"
    action: str = ""
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
        drone_paths_json=json.dumps([path.name for path in scanned.drone_paths], ensure_ascii=False),
        t10_status=_t10_status(scanned),
        appcode=scanned.appcode,
        project_type=scanned.project_type,
        non_cr_state=metadata.non_cr_state,
        created_at=metadata.created_at,
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
    is_appcode_year = year_path.parent.is_dir() and not year_path.parent.name.isdigit() and year_path.parent.name != "CR"
    if is_appcode_year:
        scanned_projects = scan_appcode_year(year_path.parent, year_path.name, store)
        cache.replace_projects_for_appcode_year(
            year_path.parent.name,
            year_path.name,
            [cached_project_row_from_scan(scanned) for scanned in scanned_projects],
        )
    else:
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
            self._migrate_schema(connection)

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
                project_states = tuple(state.value for state in ProjectState) + (NON_CR_FOLDER_STATE,)
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
                "approval_polling_jobs",
                "automation_logs",
                "second_brain_activity",
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
                    drone_paths_json,
                    t10_status,
                    appcode,
                    project_type,
                    non_cr_state,
                    created_at,
                    updated_at,
                    scanned_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    appcode = excluded.appcode,
                    project_type = excluded.project_type,
                    non_cr_state = excluded.non_cr_state,
                    created_at = excluded.created_at,
                    updated_at = excluded.updated_at,
                    drone_paths_json = excluded.drone_paths_json,
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
                        drone_paths_json,
                        t10_status,
                        appcode,
                        project_type,
                        non_cr_state,
                        created_at,
                        updated_at,
                        scanned_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        drone_paths_json = excluded.drone_paths_json,
                        t10_status = excluded.t10_status,
                        appcode = excluded.appcode,
                        project_type = excluded.project_type,
                        non_cr_state = excluded.non_cr_state,
                        created_at = excluded.created_at,
                        updated_at = excluded.updated_at,
                        scanned_at = excluded.scanned_at
                    """,
                    self._project_values(row),
                )

    def list_projects(self, year: str | None = None, appcode: str | None = None) -> list[CachedProjectRow]:
        cols = ("path, year, folder_state, name, cr_link, start_datetime, "
                "end_datetime, cr_number, cr_state, cr_pending_approval_at, "
                "drone_tickets_json, drone_paths_json, t10_status, appcode, project_type, "
                "non_cr_state, created_at, updated_at, scanned_at")
        with self._connect() as connection:
            if year is None and appcode is None:
                rows = connection.execute(
                    f"SELECT {cols} FROM project_index ORDER BY year, name, path"
                ).fetchall()
            elif year is not None and appcode is not None:
                rows = connection.execute(
                    f"SELECT {cols} FROM project_index WHERE year = ? AND appcode = ? ORDER BY year, name, path",
                    (year, appcode),
                ).fetchall()
            elif year is not None:
                rows = connection.execute(
                    f"SELECT {cols} FROM project_index WHERE year = ? ORDER BY year, name, path",
                    (year,),
                ).fetchall()
            else:
                rows = connection.execute(
                    f"SELECT {cols} FROM project_index WHERE appcode = ? ORDER BY year, name, path",
                    (appcode,),
                ).fetchall()
        return [self._project_from_row(row) for row in rows]
    def replace_projects_for_appcode_year(self, appcode: str, year: str, rows: Iterable[CachedProjectRow]) -> None:
        """Replace all projects for a specific appcode+year combination."""
        replacement_rows = list(rows)
        replacement_paths = {str(row.project_path) for row in replacement_rows}
        with self._connect() as connection:
            existing_paths = {
                row[0]
                for row in connection.execute(
                    "SELECT path FROM project_index WHERE year = ? AND appcode = ?",
                    (year, appcode),
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
                        path, name, year, folder_state, cr_link, cr_number, cr_state,
                        cr_pending_approval_at, start_datetime, end_datetime,
                        drone_tickets_json, drone_paths_json, t10_status, appcode,
                        project_type, non_cr_state, created_at, updated_at, scanned_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(path) DO UPDATE SET
                        name = excluded.name, year = excluded.year,
                        folder_state = excluded.folder_state, cr_link = excluded.cr_link,
                        cr_number = excluded.cr_number, cr_state = excluded.cr_state,
                        cr_pending_approval_at = excluded.cr_pending_approval_at,
                        start_datetime = excluded.start_datetime,
                        end_datetime = excluded.end_datetime,
                        drone_tickets_json = excluded.drone_tickets_json,
                        drone_paths_json = excluded.drone_paths_json,
                        t10_status = excluded.t10_status,
                        appcode = excluded.appcode,
                        project_type = excluded.project_type,
                        non_cr_state = excluded.non_cr_state,
                        created_at = excluded.created_at,
                        updated_at = excluded.updated_at,
                        scanned_at = excluded.scanned_at
                    """,
                    self._project_values(row),
                )

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

    def clear_rule_logs(self, rule_id: str) -> int:
        """Delete automation_rule_logs for one rule; returns count deleted."""
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM automation_rule_logs WHERE rule_id = ?",
                (rule_id,),
            )
        return int(cursor.rowcount or 0)

    # ── Slice 5: cross-module automation_logs ─────────────────────────────
    def append_log(self, row: AutomationLogRow) -> int:
        """Append a cross-module log entry; return its row id."""
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO automation_logs (module, rule_id, cr_id, timestamp, event_type, detail)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    row.module,
                    row.rule_id,
                    row.cr_id,
                    datetime_to_json(row.timestamp),
                    row.event_type,
                    row.detail,
                ),
            )
        return int(cursor.lastrowid or 0)

    def list_logs(
        self,
        *,
        module: str = "",
        cr_id: str = "",
        rule_id: str = "",
        limit: int = 200,
    ) -> list[AutomationLogRow]:
        """Return automation_logs filtered by module/cr_id/rule_id, newest first."""
        clauses: list[str] = []
        params: list[object] = []
        if module and module != "all":
            clauses.append("module = ?")
            params.append(module)
        if cr_id:
            clauses.append("cr_id = ?")
            params.append(cr_id)
        if rule_id:
            clauses.append("rule_id = ?")
            params.append(rule_id)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(int(limit))
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT id, module, rule_id, cr_id, timestamp, event_type, detail
                FROM automation_logs
                {where}
                ORDER BY id DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
        return [
            AutomationLogRow(
                id=int(r[0]),
                module=str(r[1]),
                rule_id=str(r[2]),
                cr_id=str(r[3]),
                timestamp=datetime_from_json(r[4]),
                event_type=str(r[5]),
                detail=str(r[6]),
            )
            for r in rows
        ]

    def purge_logs_for_cr(self, cr_id: str) -> int:
        """Delete all automation_logs rows for a CR (retention on terminal state).

        Returns the number of rows deleted. ``automation_rule_logs`` is NOT
        touched (rules-only backward-compat table).
        """
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM automation_logs WHERE cr_id = ?",
                (cr_id,),
            )
        return int(cursor.rowcount or 0)

    def clear_all_logs(self) -> int:
        """Delete all automation_logs rows. Returns count deleted."""
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM automation_logs")
        return int(cursor.rowcount or 0)

    # ── Task 5: second_brain_activity (capped recent-activity ledger) ──────
    def append_second_brain_activity(self, row: SecondBrainActivityRow) -> SecondBrainActivityRow:
        """Append one activity row, deduping repeated opens.

        A repeated open of the same item updates the existing row in place
        (path/title/source/timestamp) so it moves to the newest position on
        the next read instead of creating a duplicate. Other actions preserve
        their event history. The table is trimmed to the newest
        ``SECOND_BRAIN_ACTIVITY_CAP`` rows after every write.
        """
        item_id, path, title, source, action, timestamp = self._activity_values(row)
        with self._connect() as connection:
            existing = None
            if action in {"opened", "opened_externally"}:
                existing = connection.execute(
                    "SELECT id FROM second_brain_activity WHERE item_id = ? AND action = ?",
                    (item_id, action),
                ).fetchone()
            if existing is not None:
                row_id = int(existing[0])
                connection.execute(
                    """
                    UPDATE second_brain_activity
                    SET path = ?, title = ?, source = ?, timestamp = ?
                    WHERE id = ?
                    """,
                    (path, title, source, timestamp, row_id),
                )
            else:
                cursor = connection.execute(
                    """
                    INSERT INTO second_brain_activity (item_id, path, title, source, action, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (item_id, path, title, source, action, timestamp),
                )
                row_id = int(cursor.lastrowid or 0)
            stale_ids = [
                stale_row[0]
                for stale_row in connection.execute(
                    "SELECT id FROM second_brain_activity ORDER BY timestamp DESC, id DESC LIMIT -1 OFFSET ?",
                    (SECOND_BRAIN_ACTIVITY_CAP,),
                ).fetchall()
            ]
            if stale_ids:
                connection.executemany(
                    "DELETE FROM second_brain_activity WHERE id = ?",
                    [(stale_id,) for stale_id in stale_ids],
                )
        return replace(row, id=row_id)

    def list_second_brain_activity(
        self, *, item_id: str = "", limit: int = SECOND_BRAIN_ACTIVITY_CAP
    ) -> list[SecondBrainActivityRow]:
        """Return activity rows newest-first (timestamp then id).

        Filtered to one item when ``item_id`` is given; otherwise the full
        capped ledger up to ``limit``.
        """
        cols = "id, item_id, path, title, source, action, timestamp"
        with self._connect() as connection:
            if item_id:
                rows = connection.execute(
                    f"""
                    SELECT {cols} FROM second_brain_activity
                    WHERE item_id = ?
                    ORDER BY timestamp DESC, id DESC
                    LIMIT ?
                    """,
                    (item_id, int(limit)),
                ).fetchall()
            else:
                rows = connection.execute(
                    f"""
                    SELECT {cols} FROM second_brain_activity
                    ORDER BY timestamp DESC, id DESC
                    LIMIT ?
                    """,
                    (int(limit),),
                ).fetchall()
        return [self._activity_from_row(row) for row in rows]

    def clear_second_brain_activity(self) -> int:
        """Delete all second_brain_activity rows (disposable/rebuildable state)."""
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM second_brain_activity")
        return int(cursor.rowcount or 0)

    @staticmethod
    def _activity_values(row: SecondBrainActivityRow) -> tuple[str, str, str, str, str, str | None]:
        return (
            row.item_id,
            str(row.path),
            row.title,
            row.source,
            row.action,
            datetime_to_json(row.timestamp),
        )

    @staticmethod
    def _activity_from_row(
        row: tuple[int, str, str, str, str, str, str | None],
    ) -> SecondBrainActivityRow:
        return SecondBrainActivityRow(
            id=int(row[0]),
            item_id=row[1],
            path=Path(row[2]),
            title=row[3],
            source=row[4],
            action=row[5],
            timestamp=datetime_from_json(row[6]),
        )

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

    _APPROVAL_COLUMNS = (
        "job_id",
        "project_path",
        "request_type",
        "cr_number",
        "email_subject",
        "sent_at",
        "status",
        "reply_received_at",
    )

    def upsert_approval_job(self, row: dict[str, object]) -> None:
        values = tuple(row.get(column) for column in self._APPROVAL_COLUMNS)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO approval_polling_jobs
                    (job_id, project_path, request_type, cr_number, email_subject, sent_at, status, reply_received_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    status = excluded.status,
                    reply_received_at = excluded.reply_received_at
                """,
                values,
            )

    def update_approval_job(self, job_id: str, status: str, reply_received_at: str | None = None) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE approval_polling_jobs SET status = ?, reply_received_at = ? WHERE job_id = ?",
                (status, reply_received_at, job_id),
            )

    def latest_approval_job(self, project_path: str, request_type: str) -> dict[str, object] | None:
        with self._connect() as connection:
            row = connection.execute(
                f"SELECT {', '.join(self._APPROVAL_COLUMNS)} FROM approval_polling_jobs"
                " WHERE project_path = ? AND request_type = ?"
                " ORDER BY created_at DESC, job_id DESC LIMIT 1",
                (project_path, request_type),
            ).fetchone()
        if row is None:
            return None
        return dict(zip(self._APPROVAL_COLUMNS, row))

    def list_polling_approval_jobs(self) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT {', '.join(self._APPROVAL_COLUMNS)} FROM approval_polling_jobs WHERE status = 'polling'",
            ).fetchall()
        return [dict(zip(self._APPROVAL_COLUMNS, row)) for row in rows]

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
                drone_paths_json TEXT NOT NULL DEFAULT '[]',
                t10_status TEXT,
                appcode TEXT NOT NULL DEFAULT '',
                project_type TEXT NOT NULL DEFAULT 'CR',
                non_cr_state TEXT,
                created_at TEXT,
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
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS automation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module TEXT NOT NULL DEFAULT '',
                rule_id TEXT NOT NULL DEFAULT '',
                cr_id TEXT NOT NULL DEFAULT '',
                timestamp TEXT,
                event_type TEXT NOT NULL DEFAULT '',
                detail TEXT NOT NULL DEFAULT ''
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS second_brain_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id TEXT NOT NULL DEFAULT '',
                path TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT '',
                action TEXT NOT NULL DEFAULT '',
                timestamp TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS approval_polling_jobs (
                job_id TEXT PRIMARY KEY,
                project_path TEXT NOT NULL,
                request_type TEXT NOT NULL,
                cr_number TEXT NOT NULL DEFAULT '',
                email_subject TEXT NOT NULL DEFAULT '',
                sent_at TEXT,
                status TEXT NOT NULL DEFAULT 'polling',
                reply_received_at TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )

    @staticmethod
    def _migrate_schema(connection: sqlite3.Connection) -> None:
        project_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(project_index)").fetchall()
        }
        if "drone_paths_json" not in project_columns:
            connection.execute(
                "ALTER TABLE project_index ADD COLUMN drone_paths_json TEXT NOT NULL DEFAULT '[]'"
            )
        if "appcode" not in project_columns:
            connection.execute(
                "ALTER TABLE project_index ADD COLUMN appcode TEXT NOT NULL DEFAULT ''"
            )
        if "project_type" not in project_columns:
            connection.execute(
                "ALTER TABLE project_index ADD COLUMN project_type TEXT NOT NULL DEFAULT 'CR'"
            )
        if "non_cr_state" not in project_columns:
            connection.execute(
                "ALTER TABLE project_index ADD COLUMN non_cr_state TEXT"
            )
        if "created_at" not in project_columns:
            connection.execute(
                "ALTER TABLE project_index ADD COLUMN created_at TEXT"
            )

    @staticmethod
    def _project_values(
        row: CachedProjectRow,
    ) -> tuple[
        str,
        str,
        str,
        str,
        str,
        str | None,
        str,
        str | None,
        str | None,
        str | None,
        str,
        str,
        str,
        str,
        str,
        str | None,
        str | None,
        str | None,
        str | None,
    ]:
        return (
            str(row.project_path),
            row.project_name,
            row.year,
            row.project_state.value if row.project_state else NON_CR_FOLDER_STATE,
            row.cr_link,
            row.cr_number or "",
            row.cr_state.value,
            datetime_to_json(row.cr_pending_approval_at),
            datetime_to_json(row.start_datetime),
            datetime_to_json(row.end_datetime),
            row.drone_tickets_json,
            row.drone_paths_json,
            row.t10_status,
            row.appcode,
            row.project_type.value,
            row.non_cr_state.value if row.non_cr_state else None,
            datetime_to_json(row.created_at),
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
            str | None,
        ]
    ) -> CachedProjectRow:
        return CachedProjectRow(
            project_path=Path(row[0]),
            year=row[1],
            project_state=None if row[2] == NON_CR_FOLDER_STATE else ProjectState(row[2]),
            project_name=row[3],
            cr_link=row[4] or "",
            start_datetime=datetime_from_json(row[5]),
            end_datetime=datetime_from_json(row[6]),
            cr_number=row[7],
            cr_state=CRState(row[8]),
            cr_pending_approval_at=datetime_from_json(row[9]),
            drone_tickets_json=row[10] or "[]",
            drone_paths_json=row[11] or "[]",
            t10_status=row[12] or "UNKNOWN",
            appcode=row[13] or "",
            project_type=ProjectType(row[14]) if row[14] else ProjectType.CR,
            non_cr_state=NonCrState(row[15]) if row[15] else None,
            created_at=datetime_from_json(row[16]),
            updated_at=datetime_from_json(row[17]),
            scanned_at=datetime_from_json(row[18]),
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
