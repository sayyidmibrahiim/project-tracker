"""JsApi response contract helpers."""

from collections.abc import Mapping
from dataclasses import asdict, dataclass, fields, is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

from project_tracker.core.rules import validate_windows_folder_name
from project_tracker.web.event_queue import drain_events


@dataclass(frozen=True)
class BridgeResponse:
    """Frontend-safe bridge response DTO."""

    ok: bool
    data: object | None
    error: dict[str, object] | None

    def to_dict(self) -> dict[str, object]:
        """Return JSON/frontend-safe dict shape."""
        return asdict(self)


def ok(data: object | None = None) -> dict[str, object]:
    """Return success bridge response."""
    return BridgeResponse(ok=True, data=data, error=None).to_dict()


def fail(
    error: str,
    code: str = "ERROR",
    details: object | None = None,
) -> dict[str, object]:
    """Return failure bridge response."""
    error_payload: dict[str, object] = {
        "code": code,
        "message": error,
        "details": details,
    }
    return BridgeResponse(ok=False, data=None, error=error_payload).to_dict()


def poll_events(limit: int | None = None) -> dict[str, object]:
    """Drain queued bridge events."""
    try:
        return ok(drain_events(limit))
    except Exception as exc:
        return fail(str(exc), code="EVENT_POLL_FAILED")


class DashboardServiceProtocol(Protocol):
    """Read-only dashboard service surface used by JsApi."""

    def list_projects(self, year: str | None = None) -> object:
        """Return dashboard project DTOs."""

    def get_summary(self, year: str | None = None) -> object:
        """Return dashboard summary DTO."""

    def get_dashboard(self, year: str | None = None) -> object:
        """Return dashboard data DTO."""


class NotificationServiceProtocol(Protocol):
    """Read-only notification service surface used by JsApi."""

    def get_all(self) -> object:
        """Return all notifications."""

    def get_undismissed(self) -> object:
        """Return undismissed notifications."""

    def get_latest(self, limit: int = 3, undismissed_only: bool = False) -> object:
        """Return latest notifications."""

    def count(self, undismissed_only: bool = False) -> int:
        """Return notification count."""

    def dismiss(self, notification_id: str) -> None:
        """Dismiss notification."""

    def dismiss_all(self) -> int:
        """Dismiss all notifications and return count."""


class ScannerServiceProtocol(Protocol):
    """Scanner service surface used by JsApi."""

    def rebuild_year(self, year_path: Path) -> object:
        """Rebuild cache for a year folder."""


class SchedulerServiceProtocol(Protocol):
    """Scheduler service surface used by JsApi."""

    @property
    def is_running(self) -> bool:
        """Return scheduler running status."""

    def start(self) -> None:
        """Start scheduler."""

    def stop(self) -> None:
        """Stop scheduler."""

    def run_once(self) -> None:
        """Run scheduled job once."""


class YearServiceProtocol(Protocol):
    """Year service surface used by JsApi."""

    def list_years(self) -> object:
        """Return available years."""


class ProjectServiceProtocol(Protocol):
    """Project service surface used by JsApi (read-only slice)."""

    def get_project(self, project_path: Path) -> object:
        """Return full project detail DTO."""

    def list_projects(self, year: str | None = None) -> object:
        """Return project list DTOs."""

    def open_folder(self, project_path: Path) -> None:
        """Open project folder in OS file manager."""

    def create_project(self, data: dict[str, object]) -> object:
        """Create project and return project DTO."""

    def update_project(self, project_path: Path, data: dict[str, object]) -> object:
        """Update project and return project DTO."""

    def rename_project(self, project_path: Path, new_name: str) -> object:
        """Rename project and return project DTO."""

    def update_cr_link(self, project_path: Path, cr_link: str) -> object:
        """Update CR link and return project DTO."""

    def update_cr_state(self, project_path: Path, cr_state: str) -> object:
        """Update CR state and return project DTO."""

    def add_drone(self, project_path: Path, data: dict[str, object]) -> object:
        """Add Drone ticket and return project DTO."""

    def update_drone(
        self,
        project_path: Path,
        drone_index: int,
        data: dict[str, object],
    ) -> object:
        """Update Drone ticket and return project DTO."""

    def delete_drone(self, project_path: Path, drone_index: int) -> object:
        """Delete Drone ticket and return project DTO."""

    def move_to_prod_ready(self, project_path: Path) -> object:
        """Move project to PROD_READY and return result."""

    def move_to_implemented(self, project_path: Path) -> object:
        """Move project to IMPLEMENTED and return result."""

    def postpone_project(self, project_path: Path) -> object:
        """Postpone project and return result."""

    def resume_project(self, project_path: Path) -> object:
        """Resume project and return result."""

    def cancel_project(self, project_path: Path) -> object:
        """Cancel project and return result."""

    def reopen_project(self, project_path: Path) -> object:
        """Reopen project and return result."""

    def list_subprojects(self, project_path: Path) -> object:
        """Return subproject list."""

    def create_subproject(self, project_path: Path, name: str) -> object:
        """Create subproject."""

    def delete_subproject(self, project_path: Path, name: str) -> object:
        """Delete subproject."""


class FileServiceProtocol(Protocol):
    """File service surface used by JsApi."""

    def list_files(self, path: Path) -> object:
        """Return file list."""

    def open_file(self, path: Path) -> None:
        """Open file through service layer."""

    def open_folder(self, path: Path) -> None:
        """Open folder through service layer."""


class NotesServiceProtocol(Protocol):
    """Notes service surface used by JsApi."""

    def get_notes(self, project_path: Path) -> object:
        """Return project notes."""

    def update_notes(self, project_path: Path, notes: str) -> object:
        """Update project notes."""


class ReportServiceProtocol(Protocol):
    """Report service surface used by JsApi."""

    def filter_projects(
        self,
        year: str | None = None,
        project_state: object | None = None,
        cr_state: object | None = None,
        search: str | None = None,
    ) -> object:
        """Return filtered report project DTOs."""

    def export_csv(self, projects: object) -> str:
        """Return CSV export text."""


class JsApi:
    """pywebview-safe API facade without importing pywebview."""

    def __init__(
        self,
        dashboard_service: DashboardServiceProtocol | None,
        notification_service: NotificationServiceProtocol | None = None,
        scanner_service: ScannerServiceProtocol | None = None,
        scheduler_service: SchedulerServiceProtocol | None = None,
        report_service: ReportServiceProtocol | None = None,
        project_service: ProjectServiceProtocol | None = None,
        year_service: YearServiceProtocol | None = None,
        file_service: FileServiceProtocol | None = None,
        notes_service: NotesServiceProtocol | None = None,
    ) -> None:
        self._dashboard_service = dashboard_service
        self._notification_service = notification_service
        self._scanner_service = scanner_service
        self._scheduler_service = scheduler_service
        self._report_service = report_service
        self._project_service = project_service
        self._year_service = year_service
        self._file_service = file_service
        self._notes_service = notes_service

    def app_get_status(self) -> dict[str, object]:
        """Return static app/backend status."""
        return ok(
            {
                "app_name": "Project Tracker DBS",
                "backend": "python",
                "phase": "phase_c_js_api",
            }
        )

    def util_validate_windows_folder_name(self, name: str) -> dict[str, object]:
        """Validate Windows-safe folder name without filesystem mutation."""
        try:
            validate_windows_folder_name(name)
            return ok({"valid": True, "error": None})
        except Exception as exc:
            return ok({"valid": False, "error": str(exc)})

    def year_list(self) -> dict[str, object]:
        """Return years from injected year service."""
        try:
            if self._year_service is None:
                raise RuntimeError("year_service is not configured")
            return ok(_to_frontend_safe(self._year_service.list_years()))
        except Exception as exc:
            return fail(str(exc), code="YEAR_LIST_FAILED")

    def dashboard_list_projects(self, year: str | None = None) -> dict[str, object]:
        """Return dashboard project rows."""
        try:
            return ok(_to_frontend_safe(self._dashboard_service.list_projects(year)))
        except Exception as exc:
            return fail(str(exc), code="DASHBOARD_LIST_PROJECTS_FAILED")

    def dashboard_summary(self, year: str | None = None) -> dict[str, object]:
        """Return dashboard summary."""
        try:
            return ok(_to_frontend_safe(self._dashboard_service.get_summary(year)))
        except Exception as exc:
            return fail(str(exc), code="DASHBOARD_SUMMARY_FAILED")

    def dashboard_data(self, year: str | None = None) -> dict[str, object]:
        """Return dashboard rows plus summary."""
        try:
            return ok(_to_frontend_safe(self._dashboard_service.get_dashboard(year)))
        except Exception as exc:
            return fail(str(exc), code="DASHBOARD_DATA_FAILED")

    def notification_list(self, undismissed_only: bool = False) -> dict[str, object]:
        """Return notifications."""
        try:
            source = (
                self._notification_service.get_undismissed()
                if undismissed_only
                else self._notification_service.get_all()
            )
            return ok(_to_frontend_safe(source))
        except Exception as exc:
            return fail(str(exc), code="NOTIFICATION_LIST_FAILED")

    def notification_latest(
        self,
        limit: int = 3,
        undismissed_only: bool = False,
    ) -> dict[str, object]:
        """Return latest notifications."""
        try:
            return ok(
                _to_frontend_safe(
                    self._notification_service.get_latest(limit, undismissed_only)
                )
            )
        except Exception as exc:
            return fail(str(exc), code="NOTIFICATION_LATEST_FAILED")

    def notification_count(self, undismissed_only: bool = False) -> dict[str, object]:
        """Return notification count."""
        try:
            return ok(self._notification_service.count(undismissed_only))
        except Exception as exc:
            return fail(str(exc), code="NOTIFICATION_COUNT_FAILED")

    def notification_dismiss(self, notification_id: str) -> dict[str, object]:
        """Dismiss notification by id."""
        try:
            self._notification_service.dismiss(notification_id)
            return ok()
        except Exception as exc:
            return fail(str(exc), code="NOTIFICATION_DISMISS_FAILED")

    def notification_dismiss_all(self) -> dict[str, object]:
        """Dismiss all notifications."""
        try:
            dismiss_all = getattr(self._notification_service, "dismiss_all", None)
            if dismiss_all is not None:
                dismissed = dismiss_all()
                return ok({"dismissed": dismissed})

            dismissed = 0
            for notification in self._notification_service.get_undismissed():
                notification_id = (
                    notification.get("id")
                    if isinstance(notification, Mapping)
                    else getattr(notification, "id")
                )
                self._notification_service.dismiss(str(notification_id))
                dismissed += 1
            return ok({"dismissed": dismissed})
        except Exception as exc:
            return fail(str(exc), code="NOTIFICATION_DISMISS_ALL_FAILED")

    def scanner_rebuild_year(self, year_path: str) -> dict[str, object]:
        """Rebuild scanner cache for one year path."""
        try:
            return ok(_to_frontend_safe(self._scanner_service.rebuild_year(Path(year_path))))
        except Exception as exc:
            return fail(str(exc), code="SCANNER_REBUILD_YEAR_FAILED")

    def scheduler_start(self) -> dict[str, object]:
        """Start scheduler."""
        try:
            self._scheduler_service.start()
            return ok(_scheduler_status_payload(self._scheduler_service))
        except Exception as exc:
            return fail(str(exc), code="SCHEDULER_START_FAILED")

    def scheduler_stop(self) -> dict[str, object]:
        """Stop scheduler."""
        try:
            self._scheduler_service.stop()
            return ok(_scheduler_status_payload(self._scheduler_service))
        except Exception as exc:
            return fail(str(exc), code="SCHEDULER_STOP_FAILED")

    def scheduler_run_once(self) -> dict[str, object]:
        """Run scheduler job once."""
        try:
            self._scheduler_service.run_once()
            return ok(_scheduler_status_payload(self._scheduler_service))
        except Exception as exc:
            return fail(str(exc), code="SCHEDULER_RUN_ONCE_FAILED")

    def scheduler_status(self) -> dict[str, object]:
        """Return scheduler status."""
        try:
            return ok(_scheduler_status_payload(self._scheduler_service))
        except Exception as exc:
            return fail(str(exc), code="SCHEDULER_STATUS_FAILED")

    def project_get(self, project_path: str) -> dict[str, object]:
        """Return full project detail."""
        try:
            return ok(_to_frontend_safe(self._project_service.get_project(Path(project_path))))
        except Exception as exc:
            return fail(str(exc), code="PROJECT_GET_FAILED")

    def project_list(self, year: str | None = None) -> dict[str, object]:
        """Return project list."""
        try:
            return ok(_to_frontend_safe(self._project_service.list_projects(year)))
        except Exception as exc:
            return fail(str(exc), code="PROJECT_LIST_FAILED")

    def project_open_folder(self, project_path: str) -> dict[str, object]:
        """Open project folder in OS file manager."""
        try:
            self._project_service.open_folder(Path(project_path))
            return ok()
        except Exception as exc:
            return fail(str(exc), code="PROJECT_OPEN_FOLDER_FAILED")

    def project_create(self, data: dict[str, object]) -> dict[str, object]:
        """Create project through service layer."""
        try:
            return ok(_to_frontend_safe(self._project_service.create_project(data)))
        except Exception as exc:
            return fail(str(exc), code="PROJECT_CREATE_FAILED")

    def project_update(
        self,
        project_path: str,
        data: dict[str, object],
    ) -> dict[str, object]:
        """Update project through service layer."""
        try:
            return ok(
                _to_frontend_safe(
                    self._project_service.update_project(Path(project_path), data)
                )
            )
        except Exception as exc:
            return fail(str(exc), code="PROJECT_UPDATE_FAILED")

    def project_rename(self, project_path: str, new_name: str) -> dict[str, object]:
        """Rename project through service layer."""
        try:
            return ok(
                _to_frontend_safe(
                    self._project_service.rename_project(Path(project_path), new_name)
                )
            )
        except Exception as exc:
            return fail(str(exc), code="PROJECT_RENAME_FAILED")

    def cr_update_link(self, project_path: str, cr_link: str) -> dict[str, object]:
        """Update project CR link through service layer."""
        try:
            return ok(
                _to_frontend_safe(
                    self._project_service.update_cr_link(Path(project_path), cr_link)
                )
            )
        except Exception as exc:
            return fail(str(exc), code="CR_UPDATE_LINK_FAILED")

    def cr_update_state(self, project_path: str, cr_state: str) -> dict[str, object]:
        """Update project CR state through service layer."""
        try:
            return ok(
                _to_frontend_safe(
                    self._project_service.update_cr_state(Path(project_path), cr_state)
                )
            )
        except Exception as exc:
            return fail(str(exc), code="CR_UPDATE_STATE_FAILED")

    def drone_add(self, project_path: str, data: dict[str, object]) -> dict[str, object]:
        """Add Drone ticket through service layer."""
        try:
            return ok(
                _to_frontend_safe(self._project_service.add_drone(Path(project_path), data))
            )
        except Exception as exc:
            return fail(str(exc), code="DRONE_ADD_FAILED")

    def drone_update(
        self,
        project_path: str,
        drone_index: int,
        data: dict[str, object],
    ) -> dict[str, object]:
        """Update Drone ticket through service layer."""
        try:
            return ok(
                _to_frontend_safe(
                    self._project_service.update_drone(
                        Path(project_path),
                        drone_index,
                        data,
                    )
                )
            )
        except Exception as exc:
            return fail(str(exc), code="DRONE_UPDATE_FAILED")

    def drone_delete(self, project_path: str, drone_index: int) -> dict[str, object]:
        """Delete Drone ticket through service layer."""
        try:
            return ok(
                _to_frontend_safe(
                    self._project_service.delete_drone(Path(project_path), drone_index)
                )
            )
        except Exception as exc:
            return fail(str(exc), code="DRONE_DELETE_FAILED")

    def folder_move_to_prod_ready(self, project_path: str) -> dict[str, object]:
        """Move project to PROD_READY through service layer."""
        try:
            return ok(
                _to_frontend_safe(
                    self._project_service.move_to_prod_ready(Path(project_path))
                )
            )
        except Exception as exc:
            return fail(str(exc), code="FOLDER_MOVE_TO_PROD_READY_FAILED")

    def folder_move_to_implemented(self, project_path: str) -> dict[str, object]:
        """Move project to IMPLEMENTED through service layer."""
        try:
            return ok(
                _to_frontend_safe(
                    self._project_service.move_to_implemented(Path(project_path))
                )
            )
        except Exception as exc:
            return fail(str(exc), code="FOLDER_MOVE_TO_IMPLEMENTED_FAILED")

    def folder_postpone(self, project_path: str) -> dict[str, object]:
        """Postpone project through service layer."""
        try:
            return ok(
                _to_frontend_safe(
                    self._project_service.postpone_project(Path(project_path))
                )
            )
        except Exception as exc:
            return fail(str(exc), code="FOLDER_POSTPONE_FAILED")

    def folder_resume(self, project_path: str) -> dict[str, object]:
        """Resume project through service layer."""
        try:
            return ok(
                _to_frontend_safe(self._project_service.resume_project(Path(project_path)))
            )
        except Exception as exc:
            return fail(str(exc), code="FOLDER_RESUME_FAILED")

    def folder_cancel(self, project_path: str) -> dict[str, object]:
        """Cancel project through service layer."""
        try:
            return ok(
                _to_frontend_safe(self._project_service.cancel_project(Path(project_path)))
            )
        except Exception as exc:
            return fail(str(exc), code="FOLDER_CANCEL_FAILED")

    def folder_reopen(self, project_path: str) -> dict[str, object]:
        """Reopen project through service layer."""
        try:
            return ok(
                _to_frontend_safe(self._project_service.reopen_project(Path(project_path)))
            )
        except Exception as exc:
            return fail(str(exc), code="FOLDER_REOPEN_FAILED")

    def subproject_list(self, project_path: str) -> dict[str, object]:
        """List subprojects through service layer."""
        try:
            if self._project_service is None:
                return fail("project_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(
                _to_frontend_safe(
                    self._project_service.list_subprojects(Path(project_path))
                )
            )
        except Exception as exc:
            return fail(str(exc), code="SUBPROJECT_LIST_FAILED")

    def subproject_create(self, project_path: str, name: str) -> dict[str, object]:
        """Create subproject through service layer."""
        try:
            if self._project_service is None:
                return fail("project_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(
                _to_frontend_safe(
                    self._project_service.create_subproject(Path(project_path), name)
                )
            )
        except Exception as exc:
            return fail(str(exc), code="SUBPROJECT_CREATE_FAILED")

    def subproject_delete(self, project_path: str, name: str) -> dict[str, object]:
        """Delete subproject through service layer."""
        try:
            if self._project_service is None:
                return fail("project_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(
                _to_frontend_safe(
                    self._project_service.delete_subproject(Path(project_path), name)
                )
            )
        except Exception as exc:
            return fail(str(exc), code="SUBPROJECT_DELETE_FAILED")

    def file_list(self, path: str) -> dict[str, object]:
        """List files through service layer."""
        try:
            if self._file_service is None:
                return fail("file_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(_to_frontend_safe(self._file_service.list_files(Path(path))))
        except Exception as exc:
            return fail(str(exc), code="FILE_LIST_FAILED")

    def file_open(self, path: str) -> dict[str, object]:
        """Open file through service layer."""
        try:
            if self._file_service is None:
                return fail("file_service is not configured", code="SERVICE_UNAVAILABLE")
            self._file_service.open_file(Path(path))
            return ok()
        except Exception as exc:
            return fail(str(exc), code="FILE_OPEN_FAILED")

    def folder_open(self, path: str) -> dict[str, object]:
        """Open folder through service layer."""
        try:
            if self._file_service is None:
                return fail("file_service is not configured", code="SERVICE_UNAVAILABLE")
            self._file_service.open_folder(Path(path))
            return ok()
        except Exception as exc:
            return fail(str(exc), code="FOLDER_OPEN_FAILED")

    def notes_get(self, project_path: str) -> dict[str, object]:
        """Return notes through service layer."""
        try:
            if self._notes_service is None:
                return fail("notes_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(_to_frontend_safe(self._notes_service.get_notes(Path(project_path))))
        except Exception as exc:
            return fail(str(exc), code="NOTES_GET_FAILED")

    def notes_update(self, project_path: str, notes: str) -> dict[str, object]:
        """Update notes through service layer."""
        try:
            if self._notes_service is None:
                return fail("notes_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(
                _to_frontend_safe(
                    self._notes_service.update_notes(Path(project_path), notes)
                )
            )
        except Exception as exc:
            return fail(str(exc), code="NOTES_UPDATE_FAILED")

    def report_filter_projects(
        self,
        year: str | None = None,
        project_state: object | None = None,
        cr_state: object | None = None,
        search: str | None = None,
    ) -> dict[str, object]:
        """Return filtered report projects."""
        try:
            projects = self._report_service.filter_projects(
                year=year,
                project_state=project_state,
                cr_state=cr_state,
                search=search,
            )
            return ok(_to_frontend_safe(projects))
        except Exception as exc:
            return fail(str(exc), code="REPORT_FILTER_PROJECTS_FAILED")

    def report_export_csv(
        self,
        year: str | None = None,
        project_state: object | None = None,
        cr_state: object | None = None,
        search: str | None = None,
    ) -> dict[str, object]:
        """Return CSV text for filtered report projects."""
        try:
            projects = self._report_service.filter_projects(
                year=year,
                project_state=project_state,
                cr_state=cr_state,
                search=search,
            )
            return ok(self._report_service.export_csv(projects))
        except Exception as exc:
            return fail(str(exc), code="REPORT_EXPORT_CSV_FAILED")


def _scheduler_status_payload(scheduler_service: SchedulerServiceProtocol) -> dict[str, object]:
    """Return frontend-safe scheduler status."""
    return {"is_running": bool(scheduler_service.is_running)}


def _to_frontend_safe(value: object) -> object:
    """Convert DTO data to JSON/frontend-safe primitives."""
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _to_frontend_safe(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Mapping):
        return {
            str(_to_frontend_safe(key)): _to_frontend_safe(item)
            for key, item in value.items()
        }
    if isinstance(value, tuple | list):
        return [_to_frontend_safe(item) for item in value]
    return value
