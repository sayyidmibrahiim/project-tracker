"""JsApi response contract helpers."""

from collections.abc import Mapping
from dataclasses import asdict, dataclass, fields, is_dataclass
from datetime import datetime
from enum import Enum
import base64
import ctypes
import os
from pathlib import Path
from typing import Any, Protocol

from core.rules import validate_windows_folder_name
from web.event_queue import drain_events
from infrastructure.outlook_client import get_current_user_name


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
    """Drain queued bridge events (module-level, kept for test compatibility)."""
    try:
        return ok(drain_events(limit))
    except Exception as exc:
        return fail(str(exc), code="EVENT_POLL_FAILED")


class DashboardServiceProtocol(Protocol):
    """Read-only dashboard service surface used by JsApi."""

    def list_projects(self, year: str | None = None, appcode: str | None = None) -> object:
        """Return dashboard project DTOs."""

    def get_summary(self, year: str | None = None, appcode: str | None = None) -> object:
        """Return dashboard summary DTO."""

    def get_dashboard(self, year: str | None = None, appcode: str | None = None) -> object:
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

    def list_entries(self) -> object:
        """Return persisted scheduler entries."""

    def create_entry(self, data: dict[str, object]) -> object:
        """Create a scheduler entry."""

    def update_entry(self, entry_id: str, data: dict[str, object]) -> object:
        """Update a scheduler entry."""

    def delete_entry(self, entry_id: str) -> None:
        """Delete a scheduler entry."""

    def set_enabled(self, entry_id: str, enabled: bool) -> object:
        """Enable or disable a scheduler entry."""

    def trigger_entry(self, entry_id: str) -> object:
        """Trigger one scheduler entry now."""


class GlobalPlanServiceProtocol(Protocol):
    """Global plan service surface used by JsApi."""

    def get_plan(self) -> object:
        """Return global project plan."""

    def save_plan(self, data: dict[str, object]) -> object:
        """Persist global project plan."""


class YearServiceProtocol(Protocol):
    """Year service surface used by JsApi."""

    def list_years(self, appcode: str) -> object:
        """Return available years for an appcode."""

    def create_year(self, appcode: str, year: str) -> object:
        """Create a year folder structure under an appcode."""


class ProjectServiceProtocol(Protocol):
    """Project service surface used by JsApi (read-only slice)."""

    def get_project(self, project_path: Path) -> object:
        """Return full project detail DTO."""

    def list_projects(self, year: str | None = None, appcode: str | None = None) -> object:
        """Return project list DTOs."""

    def open_folder(self, project_path: Path) -> None:
        """Open project folder in OS file manager."""

    def create_project(self, data: dict[str, object]) -> object:
        """Create project and return project DTO."""

    def update_project(self, project_path: Path, data: dict[str, object]) -> object:
        """Update project and return project DTO."""

    def rename_project(self, project_path: Path, new_name: str) -> object:
        """Rename project and return project DTO."""

    def delete_project(self, project_path: Path) -> object:
        """Delete project (route to Recycle Bin) and return result."""

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

    def list_drones(self, project_path: Path) -> object:
        """Return drone list."""

    def create_drone(self, project_path: Path, name: str) -> object:
        """Create drone folder (UAT/PRD/notes.md)."""

    def delete_drone(self, project_path: Path, name: str) -> object:
        """Delete drone folder."""

    def set_non_cr_state(self, project_path: Path, target_state: str) -> object:
        """Set Non-CR project state (metadata-only)."""


class AppCodeServiceProtocol(Protocol):
    """Appcode service surface used by JsApi."""

    def list_appcodes(self) -> object:
        """Return registered appcodes."""

    def add_appcode(self, name: str) -> object:
        """Create appcode folder + appcode.json + CICD/."""

    def remove_appcode(self, name: str) -> object:
        """Remove appcode (send2trash)."""

    def get_appcode_config(self, appcode: str) -> object:
        """Return appcode config."""

    def update_appcode_config(self, appcode: str, data: dict[str, object]) -> object:
        """Update appcode config."""


class FileServiceProtocol(Protocol):
    """File service surface used by JsApi."""

    def list_files(self, path: Path) -> object:
        """Return file list."""

    def open_file(self, path: Path) -> None:
        """Open file through service layer."""

    def open_folder(self, path: Path) -> None:
        """Open folder through service layer."""

    def create_file(self, folder: Path, filename: str) -> object:
        """Create a new empty file in ``folder``."""

    def create_file_from_template(self, folder: Path, template_name: str) -> object:
        """Create a new file in ``folder`` from a configured template."""

    def rename_file(self, filepath: Path, new_name: str) -> object:
        """Rename the file at ``filepath`` to ``new_name``."""

    def delete_file(self, filepath: Path) -> object:
        """Delete the file at ``filepath`` (route to Recycle Bin)."""


class NotesServiceProtocol(Protocol):
    """Notes service surface used by JsApi."""

    def get_notes(self, project_path: Path) -> object:
        """Return project notes."""

    def update_notes(self, project_path: Path, notes: str) -> object:
        """Update project notes."""

    def get_rte_file(self, file_path: Path) -> object:
        """Read a file for RTE editing. Returns {content, format, editable}.

        For ``_cr-docs/uat-signoff`` and ``_cr-docs/prod-lv`` the file is lazily
        scaffolded (0-byte) on first read. ``format`` is one of
        ``html`` (the two CR-doc names), ``markdown`` (``*.md``), ``msg``
        (``*.msg``, binary never read) or ``text``. ``editable`` is False when
        the containing project is in IMPLEMENTED or for ``msg`` files.
        """

    def save_rte_file(self, file_path: Path, content: str) -> object:
        """Save RTE content back to ``file_path`` (atomic write).

        Rejected when the containing project is IMPLEMENTED (``LOCKED``) or
        when the target is a ``msg`` file (``NOT_EDITABLE``).
        """


class SettingsDependencyProtocol(Protocol):
    """Settings service/store surface used by JsApi."""

    def get_settings(self) -> object:
        """Return settings."""

    def update_settings(self, data: dict[str, object]) -> object:
        """Update settings."""


class LinkBankDependencyProtocol(Protocol):
    """Link bank service/store surface used by JsApi."""

    def get_linkbank(self) -> object:
        """Return link bank data."""

    def update_linkbank(self, data: dict[str, object]) -> object:
        """Update link bank data."""

    def add_link(self, data: dict[str, object]) -> object:
        """Add link."""

    def archive_link(self, link_id: str) -> object:
        """Archive link."""

    def category_create(self, name: str) -> object:
        """Create category."""

    def category_rename(self, old_name: str, new_name: str) -> object:
        """Rename category."""

    def category_archive(self, name: str) -> object:
        """Archive category."""

    def export_json(self) -> object:
        """Export full link bank JSON."""

    def import_json(self, data: dict[str, object]) -> object:
        """Import full link bank JSON."""


class AutomationServiceProtocol(Protocol):
    """Automation service surface used by JsApi."""

    def list_rules(self) -> object:
        """Return all rules."""

    def evaluate_rule(
        self, rule_id: str, context: dict[str, object]
    ) -> object:
        """Evaluate a single rule."""

    def evaluate_all(
        self, context: dict[str, object]
    ) -> object:
        """Evaluate all rules."""


class RulesServiceProtocol(Protocol):
    """Rules-engine CRUD + log surface used by JsApi (Req 11.1/11.2)."""

    def create(self, data: dict[str, object]) -> object:
        """Create a rule; reject incomplete/unsupported definitions."""

    def update(self, rule_id: str, data: dict[str, object]) -> object:
        """Update a rule by id."""

    def delete(self, rule_id: str) -> None:
        """Delete a rule by id."""

    def toggle(self, rule_id: str, enabled: bool) -> object:
        """Enable or disable a rule by id."""

    def get_logs(self, rule_id: str, limit: int) -> object:
        """Return up to ``limit`` recent execution logs for ``rule_id``."""


class SecondBrainServiceProtocol(Protocol):
    """Second Brain service surface used by JsApi."""

    def list_items(self) -> object:
        """Return Second Brain items."""

    def search(self, query: str) -> object:
        """Search Second Brain items."""

    def get_item(self, item_id: str) -> object:
        """Return Second Brain item."""

    def pin_item(self, item_id: str) -> object:
        """Pin Second Brain item."""

    def favorite_item(self, item_id: str) -> object:
        """Favorite Second Brain item."""

    def create_note(self, parent: Path, filename: str, content: str = "") -> object:
        """Create a new Second Brain note."""

    def write_note(self, filepath: Path, content: str) -> object:
        """Write content to an existing Second Brain note."""

    def delete_note(self, filepath: Path) -> object:
        """Delete a Second Brain note."""


class OutlookServiceProtocol(Protocol):
    """Outlook service surface used by JsApi.

    Each method returns a complete Bridge_Response dict ``{ok, data, error}``.
    Off-Windows the underlying client returns dev-skipped/dev-fallback responses
    and never executes COM. Runtime failures are returned as ``ok=false`` without
    claiming the email was drafted or sent (Req 8.9).
    """

    def draft_email(self, category_code: str, project_path: Path) -> dict[str, object]:
        """Create an Outlook draft email (Draft_First; never sends)."""

    def send_email(self, category_code: str, project_path: Path) -> dict[str, object]:
        """Send an Outlook email (only after frontend confirmation)."""

    def get_contacts(self, query: str = "") -> dict[str, object]:
        """Return matching Outlook contacts (dev fallback off-Windows)."""

    def download_emails(
        self, project_path: Path, cr_number: str = "", project_name: str = ""
    ) -> dict[str, object]:
        """Download reply emails/attachments (guarded; dev-skipped off-Windows)."""


class TeamsServiceProtocol(Protocol):
    """Teams service surface used by JsApi.

    Each method returns a complete Bridge_Response dict ``{ok, data, error}``.
    Preview_First is the default: ``preview_message`` opens the deep link and
    copies the text with no keystroke/auto-send (Req 9.1). ``send_message``
    auto-sends only when ``teams_auto_send`` is enabled in settings and the
    frontend has confirmed; the adapter reads ``teams_auto_send``/
    ``countdown_seconds`` from ``AppSettings.teams``. Off-Windows the underlying
    client returns dev-skipped responses and never executes ``pyautogui``.
    """

    def preview_message(
        self,
        message: str,
        *,
        target_email: str = "",
        target_group: str = "",
        mentions: list[str] | None = None,
    ) -> dict[str, object]:
        """Preview a Teams message (deep link + clipboard; never auto-sends)."""

    def send_message(
        self,
        message: str,
        *,
        target_email: str = "",
        target_group: str = "",
        mentions: list[str] | None = None,
    ) -> dict[str, object]:
        """Send a Teams message (auto-send only when enabled and confirmed)."""


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
        settings_service: SettingsDependencyProtocol | None = None,
        settings_store: SettingsDependencyProtocol | None = None,
        linkbank_service: LinkBankDependencyProtocol | None = None,
        linkbank_store: LinkBankDependencyProtocol | None = None,
        second_brain_service: SecondBrainServiceProtocol | None = None,
        automation_service: AutomationServiceProtocol | None = None,
        rules_service: RulesServiceProtocol | None = None,
        outlook_service: OutlookServiceProtocol | None = None,
        teams_service: TeamsServiceProtocol | None = None,
        global_plan_service: GlobalPlanServiceProtocol | None = None,
        appcode_service: AppCodeServiceProtocol | None = None,
    ) -> None:
        self._dashboard_service = dashboard_service
        self._notification_service = notification_service
        self._scanner_service = scanner_service
        self._scheduler_service = scheduler_service
        self._report_service = report_service
        self._project_service = project_service
        self._year_service = year_service
        self._automation_service = automation_service
        self._rules_service = rules_service
        self._file_service = file_service
        self._notes_service = notes_service
        self._settings_dependency = settings_service or settings_store
        self._linkbank_dependency = linkbank_service or linkbank_store
        self._second_brain_service = second_brain_service
        self._outlook_service = outlook_service
        self._teams_service = teams_service
        self._global_plan_service = global_plan_service
        self._appcode_service = appcode_service

    def poll_events(self, limit: int | None = None) -> dict[str, object]:
        """Drain queued bridge events."""
        try:
            return ok(drain_events(limit))
        except Exception as exc:
            return fail(str(exc), code="EVENT_POLL_FAILED")

    def app_get_status(self) -> dict[str, object]:
        """Return static app/backend status."""
        return ok(
            {
                "app_name": "Project Tracker DBS",
                "backend": "python",
                "phase": "phase_c_js_api",
            }
        )

    def get_user_profile(self) -> dict[str, object]:
        """Return user display name and initials (Outlook COM → Win32 API → OS env)."""
        name = ""
        _method = "fallback"

        try:
            resp = get_current_user_name()
            if resp.get("ok") and resp.get("data"):
                n = (resp["data"].get("name") or "").strip()
                if n:
                    name = n
                    _method = "outlook_com"
        except Exception:
            pass

        if not name:
            try:
                buf = ctypes.create_unicode_buffer(256)
                size = ctypes.c_ulong(256)
                if ctypes.windll.advapi32.GetUserNameW(buf, ctypes.byref(size)):
                    n = buf.value.strip()
                    if n:
                        name = n
                        _method = "getusernamew"
            except Exception:
                pass

        if not name:
            n = os.environ.get("USERNAME") or os.environ.get("USER") or ""
            if n:
                name = n
                _method = "env"

        parts = [p for p in name.replace("_", " ").replace(".", " ").split() if p]
        initials = "".join(p[0].upper() for p in parts)[:2] if parts else (name[:1].upper() if name else "U")
        return ok({"name": name, "initials": initials, "_debug": _method})

    def win_minimize(self) -> dict[str, object]:
        try:
            import webview  # noqa: PLC0415
            if webview.windows:
                webview.windows[0].minimize()
            return ok()
        except Exception as exc:
            return fail(str(exc), code="WIN_MINIMIZE_FAILED")

    def win_toggle_maximize(self) -> dict[str, object]:
        try:
            import webview  # noqa: PLC0415
            if webview.windows:
                w = webview.windows[0]
                w.maximize() if not w.maximized else w.restore()
            return ok()
        except Exception as exc:
            return fail(str(exc), code="WIN_TOGGLE_MAXIMIZE_FAILED")

    def win_close(self) -> dict[str, object]:
        try:
            import webview  # noqa: PLC0415
            if webview.windows:
                webview.windows[0].destroy()
            return ok()
        except Exception as exc:
            return fail(str(exc), code="WIN_CLOSE_FAILED")

    def util_validate_windows_folder_name(self, name: str) -> dict[str, object]:
        """Validate Windows-safe folder name without filesystem mutation."""
        try:
            validate_windows_folder_name(name)
            return ok({"valid": True, "error": None})
        except Exception as exc:
            return ok({"valid": False, "error": str(exc)})

    def util_choose_folder(self) -> dict[str, object]:
        """Open the native OS folder picker and return the chosen path.

        Lazily imports pywebview so the bridge stays importable in headless
        Linux/dev/test environments where pywebview has no window. Returns the
        chosen path in ``data.path`` (null when the user cancels). Any dialog
        failure surfaces as a standard fail envelope rather than crashing the
        bridge call.
        """
        try:
            import webview  # lazy: not imported at module load
        except Exception as exc:  # pragma: no cover - pywebview always importable in app
            return fail(
                f"Folder picker unavailable: {exc}",
                code="FOLDER_PICKER_UNAVAILABLE",
            )

        windows = getattr(webview, "windows", []) or []
        if not windows:
            return fail(
                "No application window is available to host the folder picker.",
                code="FOLDER_PICKER_UNAVAILABLE",
            )

        try:
            file_dialog = getattr(webview, "FileDialog", None)
            folder_dialog = (
                getattr(file_dialog, "FOLDER", None)
                if file_dialog is not None
                else None
            )
            if folder_dialog is None:
                folder_dialog = getattr(webview, "FOLDER_DIALOG")
            result = windows[0].create_file_dialog(folder_dialog)
        except Exception as exc:
            return fail(str(exc), code="FOLDER_PICKER_FAILED")

        # pywebview returns a tuple/list of selected paths, or empty on cancel.
        path: str | None = None
        if result:
            first = result[0] if isinstance(result, (list, tuple)) else result
            path = str(first) if first else None
        return ok({"path": path})

    def util_save_file(self, suggested_name: str, content: str) -> dict[str, object]:
        """Open the native OS save dialog and write UTF-8 content to the chosen path.

        Lazily imports pywebview so the bridge stays importable in headless dev.
        Returns ``data.path`` (the written file path, null on cancel). A UTF-8
        BOM is prepended for CSV content so Excel opens accented text correctly.
        """
        try:
            import webview  # lazy: not imported at module load
        except Exception as exc:  # pragma: no cover
            return fail(f"Save dialog unavailable: {exc}", code="SAVE_DIALOG_UNAVAILABLE")

        windows = getattr(webview, "windows", []) or []
        if not windows:
            return fail("No application window is available to host the save dialog.", code="SAVE_DIALOG_UNAVAILABLE")

        try:
            file_dialog = getattr(webview, "FileDialog", None)
            save_dialog = (
                getattr(file_dialog, "SAVE", None)
                if file_dialog is not None
                else None
            )
            if save_dialog is None:
                save_dialog = getattr(webview, "SAVE_DIALOG")
            result = windows[0].create_file_dialog(
                save_dialog, save_filename=str(suggested_name or "export.csv")
            )
        except Exception as exc:
            return fail(str(exc), code="SAVE_DIALOG_FAILED")

        # pywebview returns a tuple/list with the selected path, or empty on cancel.
        path_str: str | None = None
        if result:
            first = result[0] if isinstance(result, (list, tuple)) else result
            path_str = str(first) if first else None
        if not path_str:
            return ok({"path": None, "written": False})

        try:
            out_path = Path(path_str)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            # CSV gets a UTF-8 BOM so Excel renders accented columns correctly.
            payload = content or ""
            is_csv = out_path.suffix.lower() == ".csv"
            with out_path.open("wb") as file:
                if is_csv:
                    file.write(b"\xef\xbb\xbf")
                file.write(payload.encode("utf-8"))
        except Exception as exc:
            return fail(str(exc), code="SAVE_DIALOG_WRITE_FAILED")
        return ok({"path": str(out_path), "written": True})

    def util_choose_image(self) -> dict[str, object]:
        """Open the native OS image picker and return the chosen image as a data URI.

        Lets the NotesEditor embed local images without a URL. Lazily imports
        pywebview so the bridge stays importable in headless dev/test. Returns
        ``data.data_uri`` (a ``data:image/<mime>;base64,...`` string, null when
        the user cancels) and ``data.name`` (the file name for default alt text).
        Any dialog/read failure surfaces as a standard fail envelope.
        """
        try:
            import webview  # lazy: not imported at module load
        except Exception as exc:  # pragma: no cover - pywebview always importable in app
            return fail(
                f"Image picker unavailable: {exc}",
                code="IMAGE_PICKER_UNAVAILABLE",
            )

        windows = getattr(webview, "windows", []) or []
        if not windows:
            return fail(
                "No application window is available to host the image picker.",
                code="IMAGE_PICKER_UNAVAILABLE",
            )

        try:
            file_dialog = getattr(webview, "FileDialog", None)
            open_dialog = (
                getattr(file_dialog, "OPEN_FILES", None)
                if file_dialog is not None
                else None
            )
            if open_dialog is None:
                # Older pywebview exposes the constant on the module itself.
                open_dialog = getattr(
                    webview, "OPEN_FILES", getattr(webview, "OPEN_DIALOG")
                )
            result = windows[0].create_file_dialog(
                open_dialog,
                file_types=(
                    "Image files (*.png;*.jpg;*.jpeg;*.gif;*.webp;*.bmp;*.svg)",
                ),
            )
        except Exception as exc:
            return fail(str(exc), code="IMAGE_PICKER_FAILED")

        # pywebview returns a tuple/list of selected paths, or empty on cancel.
        if not result:
            return ok({"data_uri": None, "name": None})
        first = result[0] if isinstance(result, (list, tuple)) else result
        if not first:
            return ok({"data_uri": None, "name": None})
        p = Path(str(first))
        ext = p.suffix.lower().lstrip(".")
        mime = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "webp": "image/webp",
            "bmp": "image/bmp",
            "svg": "image/svg+xml",
        }.get(ext, "application/octet-stream")
        try:
            raw = p.read_bytes()
        except Exception as exc:
            return fail(str(exc), code="IMAGE_PICKER_FAILED")
        encoded = base64.b64encode(raw).decode("ascii")
        return ok({"data_uri": f"data:{mime};base64,{encoded}", "name": p.name})

    def year_list(self, appcode: str = "") -> dict[str, object]:
        """Return years from injected year service."""
        try:
            if self._year_service is None:
                raise RuntimeError("year_service is not configured")
            try:
                years = self._year_service.list_years(appcode)
            except TypeError as exc:
                if "positional argument" not in str(exc):
                    raise
                years = self._year_service.list_years()
            return ok(_to_frontend_safe(years))
        except Exception as exc:
            return fail(str(exc), code="YEAR_LIST_FAILED")

    def year_create(self, year: str, appcode: str = "") -> dict[str, object]:
        """Create an appcode-scoped year folder."""
        try:
            if self._year_service is None:
                raise RuntimeError("year_service is not configured")
            return ok(_to_frontend_safe(self._year_service.create_year(appcode, year)))
        except Exception as exc:
            return fail(str(exc), code="YEAR_CREATE_FAILED")

    def appcode_list(self) -> dict[str, object]:
        """Return discovered appcodes."""
        try:
            if self._appcode_service is None:
                return fail("appcode_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(_to_frontend_safe(self._appcode_service.list_appcodes()))
        except Exception as exc:
            return fail(str(exc), code="APPCODE_LIST_FAILED")

    def appcode_add(self, name: str) -> dict[str, object]:
        """Create appcode folder + config."""
        try:
            if self._appcode_service is None:
                return fail("appcode_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(_to_frontend_safe(self._appcode_service.add_appcode(name)))
        except Exception as exc:
            return fail(str(exc), code="APPCODE_ADD_FAILED")

    def appcode_remove(self, name: str) -> dict[str, object]:
        """Remove appcode folder via service."""
        try:
            if self._appcode_service is None:
                return fail("appcode_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(_to_frontend_safe(self._appcode_service.remove_appcode(name)))
        except Exception as exc:
            return fail(str(exc), code="APPCODE_REMOVE_FAILED")

    def appcode_get_config(self, appcode: str) -> dict[str, object]:
        """Return appcode config."""
        try:
            if self._appcode_service is None:
                return fail("appcode_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(_to_frontend_safe(self._appcode_service.get_appcode_config(appcode)))
        except Exception as exc:
            return fail(str(exc), code="APPCODE_GET_CONFIG_FAILED")

    def appcode_update_config(self, appcode: str, data: dict[str, object]) -> dict[str, object]:
        """Update appcode config."""
        try:
            if self._appcode_service is None:
                return fail("appcode_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(_to_frontend_safe(self._appcode_service.update_appcode_config(appcode, data)))
        except Exception as exc:
            return fail(str(exc), code="APPCODE_UPDATE_CONFIG_FAILED")

    def dashboard_list_projects(self, year: str | None = None, appcode: str | None = None) -> dict[str, object]:
        """Return dashboard project rows."""
        try:
            return ok(_to_frontend_safe(self._dashboard_service.list_projects(year, appcode)))
        except Exception as exc:
            return fail(str(exc), code="DASHBOARD_LIST_PROJECTS_FAILED")

    def dashboard_summary(self, year: str | None = None, appcode: str | None = None) -> dict[str, object]:
        """Return dashboard summary."""
        try:
            return ok(_to_frontend_safe(self._dashboard_service.get_summary(year, appcode)))
        except Exception as exc:
            return fail(str(exc), code="DASHBOARD_SUMMARY_FAILED")

    def dashboard_data(self, year: str | None = None, appcode: str | None = None) -> dict[str, object]:
        """Return dashboard rows plus summary."""
        try:
            data = self._dashboard_service.get_dashboard(year, appcode)
        except Exception as exc:
            return fail(str(exc), code="DASHBOARD_DATA_FAILED")
        # H-10 reminder evaluation is a best-effort side effect that writes
        # metadata stamps; it runs AFTER the read succeeds and is isolated so a
        # reminder write failure can never blank the dashboard.
        self._evaluate_h10_reminders_for(data)
        return ok(_to_frontend_safe(data))

    def _evaluate_h10_reminders_for(self, data: object) -> None:
        """Run H-10 reminder evaluation over the visible dashboard projects.

        Delegates to the project-service adapter, which owns metadata and the
        notification service. Best-effort: a no-op when the adapter does not
        expose the hook (e.g. lightweight test doubles), and any exception
        raised during evaluation (including metadata write failures) is
        swallowed so a dashboard read never fails because of reminder
        evaluation. The broad ``except`` is intentional — reminder bookkeeping
        must never take down the primary screen.
        """
        evaluator = getattr(self._project_service, "_evaluate_h10_reminders", None)
        if evaluator is None:
            return
        try:
            paths = [
                project.project_path
                for project in getattr(data, "projects", ())
                if getattr(project, "project_path", None) is not None
            ]
            evaluator(paths)
        except Exception:  # noqa: BLE001 - best-effort; never break dashboard load
            pass

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

    def scheduler_entry_list(self) -> dict[str, object]:
        """Return persisted scheduler entries (Req 10.7)."""
        try:
            if self._scheduler_service is None:
                return fail("scheduler_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok([_scheduler_entry_payload(e) for e in self._scheduler_service.list_entries()])
        except Exception as exc:
            return fail(str(exc), code="SCHEDULER_ENTRY_LIST_FAILED")

    def scheduler_entry_create(self, data: dict[str, object]) -> dict[str, object]:
        """Create a scheduler entry; validation failure leaves state unchanged (Req 10.7)."""
        try:
            if self._scheduler_service is None:
                return fail("scheduler_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(_scheduler_entry_payload(self._scheduler_service.create_entry(dict(data or {}))))
        except Exception as exc:
            return fail(str(exc), code="SCHEDULER_ENTRY_CREATE_FAILED")

    def scheduler_entry_update(self, entry_id: str, data: dict[str, object]) -> dict[str, object]:
        """Update a scheduler entry; validation failure leaves state unchanged (Req 10.7)."""
        try:
            if self._scheduler_service is None:
                return fail("scheduler_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(_scheduler_entry_payload(self._scheduler_service.update_entry(entry_id, dict(data or {}))))
        except Exception as exc:
            return fail(str(exc), code="SCHEDULER_ENTRY_UPDATE_FAILED")

    def scheduler_entry_delete(self, entry_id: str) -> dict[str, object]:
        """Delete a scheduler entry (Req 10.7)."""
        try:
            if self._scheduler_service is None:
                return fail("scheduler_service is not configured", code="SERVICE_UNAVAILABLE")
            self._scheduler_service.delete_entry(entry_id)
            return ok({"deleted": entry_id})
        except Exception as exc:
            return fail(str(exc), code="SCHEDULER_ENTRY_DELETE_FAILED")

    def scheduler_entry_toggle(self, entry_id: str, enabled: bool) -> dict[str, object]:
        """Enable or disable a scheduler entry (Req 10.8)."""
        try:
            if self._scheduler_service is None:
                return fail("scheduler_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(_scheduler_entry_payload(self._scheduler_service.set_enabled(entry_id, bool(enabled))))
        except Exception as exc:
            return fail(str(exc), code="SCHEDULER_ENTRY_TOGGLE_FAILED")

    def scheduler_entry_trigger(self, entry_id: str) -> dict[str, object]:
        """Trigger one scheduler entry now."""
        try:
            if self._scheduler_service is None:
                return fail("scheduler_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(_to_frontend_safe(self._scheduler_service.trigger_entry(entry_id)))
        except Exception as exc:
            return fail(str(exc), code="SCHEDULER_ENTRY_TRIGGER_FAILED")

    def project_get(self, project_path: str) -> dict[str, object]:
        """Return full project detail."""
        try:
            return ok(_to_frontend_safe(self._project_service.get_project(Path(project_path))))
        except Exception as exc:
            return fail(str(exc), code="PROJECT_GET_FAILED")

    def project_list(self, year: str | None = None, appcode: str | None = None) -> dict[str, object]:
        """Return project list."""
        try:
            return ok(_to_frontend_safe(self._project_service.list_projects(year, appcode)))
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

    def project_delete(self, project_path: str) -> dict[str, object]:
        """Delete a project folder to the Recycle Bin through the service layer.

        Routes to ``ProjectService.delete_project`` →
        ``SafeDeleteService.delete_to_trash``. Rename/delete are rejected by the
        adapter while the project is in ``PROD_READY`` or ``IMPLEMENTED``. On a
        ``send2trash`` failure the exception propagates here and the facade
        returns ``ok=false`` with the folder left in place and no cache update.
        """
        try:
            if self._project_service is None:
                return fail("project_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(
                _to_frontend_safe(
                    self._project_service.delete_project(Path(project_path))
                )
            )
        except Exception as exc:
            return fail(str(exc), code="PROJECT_DELETE_FAILED")

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

    def set_non_cr_state(self, project_path: str, target_state: str) -> dict[str, object]:
        """Update Non-CR project state through service layer."""
        try:
            if self._project_service is None:
                return fail("project_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(
                _to_frontend_safe(
                    self._project_service.set_non_cr_state(Path(project_path), target_state)
                )
            )
        except Exception as exc:
            return fail(str(exc), code="SET_NON_CR_STATE_FAILED")

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

    def drone_delete(self, project_path: str, drone: int | str) -> dict[str, object]:
        """Delete Drone ticket or folder through service layer."""
        try:
            return ok(
                _to_frontend_safe(
                    self._project_service.delete_drone(Path(project_path), drone)
                )
            )
        except Exception as exc:
            return fail(str(exc), code="DRONE_DELETE_FAILED")

    def folder_move_to_prod_ready(self, project_path: str) -> dict[str, object]:
        """Move project to PROD_READY through service layer.

        T-10 is no longer a blocking guard (it is now a non-blocking H-10
        reminder), so there is no override path — the move succeeds whenever the
        remaining structural guards pass.
        """
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

    def drone_list(self, project_path: str) -> dict[str, object]:
        """List drone folders through service layer."""
        try:
            if self._project_service is None:
                return fail("project_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(
                _to_frontend_safe(
                    self._project_service.list_drones(Path(project_path))
                )
            )
        except Exception as exc:
            return fail(str(exc), code="DRONE_LIST_FAILED")

    def drone_create(self, project_path: str, name: str) -> dict[str, object]:
        """Create drone folder through service layer."""
        try:
            if self._project_service is None:
                return fail("project_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(
                _to_frontend_safe(
                    self._project_service.create_drone(Path(project_path), name)
                )
            )
        except Exception as exc:
            return fail(str(exc), code="DRONE_CREATE_FAILED")

    def subproject_list(self, project_path: str) -> dict[str, object]:
        """Backward-compatible alias for drone_list."""
        return self.drone_list(project_path)

    def subproject_create(self, project_path: str, name: str) -> dict[str, object]:
        """Backward-compatible alias for drone_create."""
        return self.drone_create(project_path, name)

    def subproject_delete(self, project_path: str, name: str) -> dict[str, object]:
        """Backward-compatible alias for drone_delete."""
        return self.drone_delete(project_path, name)

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

    def file_create(self, path: str, filename: str) -> dict[str, object]:
        """Create a new manual file in the target folder (Req 6.2/6.3/6.10).

        The file name is validated and the create is rejected when the name
        already exists, so an existing file is never overwritten. Creation is
        disabled (rejected) while the containing project is in ``PROD_READY`` or
        ``IMPLEMENTED``. Any validation/existence/filesystem failure returns
        ``ok=false`` with the folder contents left unchanged.
        """
        try:
            if self._file_service is None:
                return fail("file_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(
                _to_frontend_safe(self._file_service.create_file(Path(path), filename))
            )
        except Exception as exc:
            return fail(str(exc), code="FILE_CREATE_FAILED")

    def file_create_from_template(
        self, path: str, template_name: str
    ) -> dict[str, object]:
        """Create a new file in the target folder from a template (Req 6.1/6.3/6.10).

        Copies the configured template into the target folder. The target name is
        validated and the copy is rejected when the name already exists. Creation
        is disabled while the project is in ``PROD_READY`` or ``IMPLEMENTED``. A
        failed copy leaves the folder contents unchanged.
        """
        try:
            if self._file_service is None:
                return fail("file_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(
                _to_frontend_safe(
                    self._file_service.create_file_from_template(
                        Path(path), template_name
                    )
                )
            )
        except Exception as exc:
            return fail(str(exc), code="FILE_CREATE_FROM_TEMPLATE_FAILED")

    def file_rename(self, filepath: str, new_name: str) -> dict[str, object]:
        """Rename a file through the service layer (Req 6.6/6.7/6.10).

        The new name is validated against the same rules as file creation and the
        rename is rejected when the destination already exists. Rename is disabled
        while the project is in ``PROD_READY`` or ``IMPLEMENTED``. A rejected
        rename leaves the file unchanged.
        """
        try:
            if self._file_service is None:
                return fail("file_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(
                _to_frontend_safe(
                    self._file_service.rename_file(Path(filepath), new_name)
                )
            )
        except Exception as exc:
            return fail(str(exc), code="FILE_RENAME_FAILED")

    def file_delete(self, filepath: str) -> dict[str, object]:
        """Delete a file by routing it to the Recycle Bin (Req 6.8/6.10).

        Routes the delete to ``SafeDeleteService.delete_to_trash`` (``send2trash``).
        Delete is disabled while the project is in ``PROD_READY`` or
        ``IMPLEMENTED``. On a ``send2trash`` failure the exception propagates here
        and the facade returns ``ok=false`` with the file left in place.
        """
        try:
            if self._file_service is None:
                return fail("file_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(
                _to_frontend_safe(self._file_service.delete_file(Path(filepath)))
            )
        except Exception as exc:
            return fail(str(exc), code="FILE_DELETE_FAILED")

    def outlook_draft_email(
        self, category_code: str, project_path: str
    ) -> dict[str, object]:
        """Create an Outlook draft email from a template (Draft_First, no send).

        Reuses ``EmailService.render_email_template`` to compose the email for the
        Template_Category ``category_code`` (``ACK_UAT``/``ACK_SOP``/``APRVL_CR``/
        ``APRVL_SOP``) and creates a draft through the guarded Outlook_Client; the
        email is never transmitted (Req 8.1). An unresolved required placeholder
        returns ``ok=false`` naming it (``OUTLOOK_DRAFT_FAILED``); unmet template
        conditions return a skipped Bridge_Response. Off-Windows the client returns
        a dev-skipped response and no COM is executed. A runtime failure returns
        ``ok=false`` without claiming the email was drafted (Req 8.9).
        """
        try:
            if self._outlook_service is None:
                return fail("outlook_service is not configured", code="SERVICE_UNAVAILABLE")
            return self._outlook_service.draft_email(category_code, Path(project_path))
        except Exception as exc:
            return fail(str(exc), code="OUTLOOK_DRAFT_FAILED")

    def outlook_send_email(
        self, category_code: str, project_path: str
    ) -> dict[str, object]:
        """Send an Outlook email from a template (only after frontend confirmation).

        The Frontend gates this call behind a Confirmation_UI (Req 8.2/8.3); the
        backend performs the send through the guarded Outlook_Client. Composition
        reuses ``EmailService.render_email_template``; an unresolved placeholder or
        unmet condition is handled exactly as for drafting. Off-Windows the client
        returns a dev-skipped response and no COM is executed. A runtime failure
        returns ``ok=false`` without claiming the email was sent (Req 8.9).
        """
        try:
            if self._outlook_service is None:
                return fail("outlook_service is not configured", code="SERVICE_UNAVAILABLE")
            return self._outlook_service.send_email(category_code, Path(project_path))
        except Exception as exc:
            return fail(str(exc), code="OUTLOOK_SEND_FAILED")

    def outlook_get_contacts(self, query: str = "") -> dict[str, object]:
        """Return Outlook contacts matching ``query`` (Req 8.7).

        On Windows the guarded Outlook_Client returns contacts whose display name
        or email matches ``query``; off-Windows a dev fallback contact is returned
        and no COM is executed.
        """
        try:
            if self._outlook_service is None:
                return fail("outlook_service is not configured", code="SERVICE_UNAVAILABLE")
            return self._outlook_service.get_contacts(query)
        except Exception as exc:
            return fail(str(exc), code="OUTLOOK_CONTACTS_FAILED")

    def outlook_download_emails(
        self,
        project_path: str,
        cr_number: str = "",
        project_name: str = "",
    ) -> dict[str, object]:
        """Download reply emails/attachments for a project (Req 8.8).

        On Windows the guarded Outlook_Client retrieves reply emails and stores
        attachments under the target project folder; off-Windows a dev-skipped
        Bridge_Response is returned and no COM is executed. A runtime failure
        returns ``ok=false``.
        """
        try:
            if self._outlook_service is None:
                return fail("outlook_service is not configured", code="SERVICE_UNAVAILABLE")
            return self._outlook_service.download_emails(
                Path(project_path), cr_number, project_name
            )
        except Exception as exc:
            return fail(str(exc), code="OUTLOOK_DOWNLOAD_FAILED")

    def teams_preview_message(
        self,
        message: str,
        target_email: str = "",
        target_group: str = "",
        mentions: list[str] | None = None,
    ) -> dict[str, object]:
        """Preview a Teams message (Preview_First; deep link + clipboard, no send).

        Builds a ``TeamsMessage`` from the supplied text and optional
        target/mentions and previews it through the guarded Teams_Client: the deep
        link is opened and the text is copied with no keystroke/auto-send (Req 9.1).
        Off-Windows the client returns a dev-skipped response and no ``pyautogui``/
        ``pyperclip`` action is executed. A runtime failure returns ``ok=false``
        (``TEAMS_PREVIEW_FAILED``) and leaves the user's draft unchanged.
        """
        try:
            if self._teams_service is None:
                return fail("teams_service is not configured", code="SERVICE_UNAVAILABLE")
            return self._teams_service.preview_message(
                message,
                target_email=target_email,
                target_group=target_group,
                mentions=mentions,
            )
        except Exception as exc:
            return fail(str(exc), code="TEAMS_PREVIEW_FAILED")

    def teams_send_message(
        self,
        message: str,
        target_email: str = "",
        target_group: str = "",
        mentions: list[str] | None = None,
    ) -> dict[str, object]:
        """Send a Teams message (auto-send only when enabled and confirmed).

        Builds a ``TeamsMessage`` from the supplied text and optional
        target/mentions and sends it through the guarded Teams_Client. The adapter
        reads ``teams_auto_send``/``countdown_seconds`` from ``AppSettings.teams``;
        auto-send runs only when ``teams_auto_send`` is enabled (and the Frontend
        has confirmed) after a visible countdown (Req 9.3/9.4). When auto-send is
        not enabled this behaves as Preview_First. Off-Windows the client returns a
        dev-skipped response and no ``pyautogui`` action is executed (Req 9.6). A
        runtime failure returns ``ok=false`` (``TEAMS_SEND_FAILED``) and leaves the
        ``teams_auto_send`` setting and the user's draft unchanged (Req 9.7).
        """
        try:
            if self._teams_service is None:
                return fail("teams_service is not configured", code="SERVICE_UNAVAILABLE")
            return self._teams_service.send_message(
                message,
                target_email=target_email,
                target_group=target_group,
                mentions=mentions,
            )
        except Exception as exc:
            return fail(str(exc), code="TEAMS_SEND_FAILED")

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

    def get_rte_file(self, file_path: str) -> dict[str, object]:
        """Read a file for RTE editing through the service layer."""
        try:
            if self._notes_service is None:
                return fail("notes_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(
                _to_frontend_safe(self._notes_service.get_rte_file(Path(file_path)))
            )
        except Exception as exc:
            return fail(str(exc), code="RTE_GET_FAILED")

    def save_rte_file(self, file_path: str, content: str) -> dict[str, object]:
        """Save RTE content back to ``file_path`` through the service layer."""
        try:
            if self._notes_service is None:
                return fail("notes_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(
                _to_frontend_safe(
                    self._notes_service.save_rte_file(Path(file_path), content)
                )
            )
        except Exception as exc:
            return fail(str(exc), code="RTE_SAVE_FAILED")

    def global_plan_get(self) -> dict[str, object]:
        """Return global app plan."""
        try:
            if self._global_plan_service is None:
                return fail("global_plan_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(_to_frontend_safe(self._global_plan_service.get_plan()))
        except Exception as exc:
            return fail(str(exc), code="GLOBAL_PLAN_GET_FAILED")

    def global_plan_save(self, data: dict[str, object]) -> dict[str, object]:
        """Persist global app plan."""
        try:
            if self._global_plan_service is None:
                return fail("global_plan_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(_to_frontend_safe(self._global_plan_service.save_plan(dict(data or {}))))
        except Exception as exc:
            return fail(str(exc), code="GLOBAL_PLAN_SAVE_FAILED")

    def settings_get(self) -> dict[str, object]:
        """Return settings through injected dependency."""
        try:
            if self._settings_dependency is None:
                return fail("settings dependency is not configured", code="SERVICE_UNAVAILABLE")
            return ok(_to_frontend_safe(self._settings_dependency.get_settings()))
        except Exception as exc:
            return fail(str(exc), code="SETTINGS_GET_FAILED")

    def settings_update(self, data: dict[str, object]) -> dict[str, object]:
        """Update settings through injected dependency."""
        try:
            if self._settings_dependency is None:
                return fail("settings dependency is not configured", code="SERVICE_UNAVAILABLE")
            return ok(_to_frontend_safe(self._settings_dependency.update_settings(data)))
        except Exception as exc:
            return fail(str(exc), code="SETTINGS_UPDATE_FAILED")

    def linkbank_get(self) -> dict[str, object]:
        """Return link bank through injected dependency."""
        try:
            if self._linkbank_dependency is None:
                return fail("linkbank dependency is not configured", code="SERVICE_UNAVAILABLE")
            return ok(_to_frontend_safe(self._linkbank_dependency.get_linkbank()))
        except Exception as exc:
            return fail(str(exc), code="LINKBANK_GET_FAILED")

    def linkbank_update(self, data: dict[str, object]) -> dict[str, object]:
        """Update link bank through injected dependency."""
        try:
            if self._linkbank_dependency is None:
                return fail("linkbank dependency is not configured", code="SERVICE_UNAVAILABLE")
            return ok(_to_frontend_safe(self._linkbank_dependency.update_linkbank(data)))
        except Exception as exc:
            return fail(str(exc), code="LINKBANK_UPDATE_FAILED")

    def linkbank_add_link(self, data: dict[str, object]) -> dict[str, object]:
        """Add link through injected dependency."""
        try:
            if self._linkbank_dependency is None:
                return fail("linkbank dependency is not configured", code="SERVICE_UNAVAILABLE")
            return ok(_to_frontend_safe(self._linkbank_dependency.add_link(data)))
        except Exception as exc:
            return fail(str(exc), code="LINKBANK_ADD_LINK_FAILED")

    def linkbank_archive_link(self, link_id: str) -> dict[str, object]:
        """Archive link through injected dependency."""
        try:
            if self._linkbank_dependency is None:
                return fail("linkbank dependency is not configured", code="SERVICE_UNAVAILABLE")
            return ok(_to_frontend_safe(self._linkbank_dependency.archive_link(link_id)))
        except Exception as exc:
            return fail(str(exc), code="LINKBANK_ARCHIVE_LINK_FAILED")

    def linkbank_category_create(self, name: str) -> dict[str, object]:
        try:
            if self._linkbank_dependency is None:
                return fail("linkbank dependency is not configured", code="SERVICE_UNAVAILABLE")
            return ok(_to_frontend_safe(self._linkbank_dependency.category_create(name)))
        except Exception as exc:
            return fail(str(exc), code="LINKBANK_CATEGORY_CREATE_FAILED")

    def linkbank_category_rename(self, old_name: str, new_name: str) -> dict[str, object]:
        try:
            if self._linkbank_dependency is None:
                return fail("linkbank dependency is not configured", code="SERVICE_UNAVAILABLE")
            return ok(_to_frontend_safe(self._linkbank_dependency.category_rename(old_name, new_name)))
        except Exception as exc:
            return fail(str(exc), code="LINKBANK_CATEGORY_RENAME_FAILED")

    def linkbank_category_archive(self, name: str) -> dict[str, object]:
        try:
            if self._linkbank_dependency is None:
                return fail("linkbank dependency is not configured", code="SERVICE_UNAVAILABLE")
            return ok(_to_frontend_safe(self._linkbank_dependency.category_archive(name)))
        except Exception as exc:
            return fail(str(exc), code="LINKBANK_CATEGORY_ARCHIVE_FAILED")

    def linkbank_export(self) -> dict[str, object]:
        try:
            if self._linkbank_dependency is None:
                return fail("linkbank dependency is not configured", code="SERVICE_UNAVAILABLE")
            return ok(_to_frontend_safe(self._linkbank_dependency.export_json()))
        except Exception as exc:
            return fail(str(exc), code="LINKBANK_EXPORT_FAILED")

    def linkbank_import(self, data: dict[str, object]) -> dict[str, object]:
        try:
            if self._linkbank_dependency is None:
                return fail("linkbank dependency is not configured", code="SERVICE_UNAVAILABLE")
            return ok(_to_frontend_safe(self._linkbank_dependency.import_json(data)))
        except Exception as exc:
            return fail(str(exc), code="LINKBANK_IMPORT_FAILED")

    def automation_list_rules(self) -> dict[str, object]:
        """Return automation rules."""
        try:
            if self._automation_service is None:
                return fail("automation_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(_to_frontend_safe(self._automation_service.list_rules()))
        except Exception as exc:
            return fail(str(exc), code="AUTOMATION_LIST_RULES_FAILED")

    def automation_evaluate_rule(
        self, rule_id: str, context: dict[str, object]
    ) -> dict[str, object]:
        """Evaluate a single automation rule."""
        try:
            if self._automation_service is None:
                return fail("automation_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(_to_frontend_safe(self._automation_service.evaluate_rule(rule_id, context)))
        except Exception as exc:
            return fail(str(exc), code="AUTOMATION_EVALUATE_RULE_FAILED")

    def automation_evaluate_all(
        self, context: dict[str, object]
    ) -> dict[str, object]:
        """Evaluate all automation rules."""
        try:
            if self._automation_service is None:
                return fail("automation_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(_to_frontend_safe(self._automation_service.evaluate_all(context)))
        except Exception as exc:
            return fail(str(exc), code="AUTOMATION_EVALUATE_ALL_FAILED")

    def automation_execute_rule(
        self, rule_id: str, context: dict[str, object]
    ) -> dict[str, object]:
        """Execute a rule's actions (Req 11.3-11.9), gated by conditions."""
        try:
            if self._automation_service is None:
                return fail("automation_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(_to_frontend_safe(self._automation_service.execute_rule(rule_id, dict(context or {}))))
        except Exception as exc:
            return fail(str(exc), code="AUTOMATION_EXECUTE_RULE_FAILED")

    def rules_create(self, data: dict[str, object]) -> dict[str, object]:
        """Create a rule (Req 11.1/11.2). Reject incomplete/unsupported defs."""
        try:
            if self._rules_service is None:
                return fail("rules_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(_to_frontend_safe(self._rules_service.create(dict(data or {}))))
        except Exception as exc:
            return fail(str(exc), code="RULES_CREATE_FAILED")

    def rules_update(self, rule_id: str, data: dict[str, object]) -> dict[str, object]:
        """Update a rule by id (Req 11.1/11.2)."""
        try:
            if self._rules_service is None:
                return fail("rules_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(_to_frontend_safe(self._rules_service.update(rule_id, dict(data or {}))))
        except Exception as exc:
            return fail(str(exc), code="RULES_UPDATE_FAILED")

    def rules_delete(self, rule_id: str) -> dict[str, object]:
        """Delete a rule by id (Req 11.1)."""
        try:
            if self._rules_service is None:
                return fail("rules_service is not configured", code="SERVICE_UNAVAILABLE")
            self._rules_service.delete(rule_id)
            return ok({"deleted": rule_id})
        except Exception as exc:
            return fail(str(exc), code="RULES_DELETE_FAILED")

    def rules_toggle(self, rule_id: str, enabled: bool) -> dict[str, object]:
        """Enable or disable a rule by id (Req 11.1)."""
        try:
            if self._rules_service is None:
                return fail("rules_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(_to_frontend_safe(self._rules_service.toggle(rule_id, bool(enabled))))
        except Exception as exc:
            return fail(str(exc), code="RULES_TOGGLE_FAILED")

    def rules_get_logs(self, rule_id: str, limit: int = 50) -> dict[str, object]:
        """Return up to ``limit`` recent execution logs for ``rule_id`` (Req 11.1)."""
        try:
            if self._rules_service is None:
                return fail("rules_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(_to_frontend_safe(self._rules_service.get_logs(rule_id, int(limit or 50))))
        except Exception as exc:
            return fail(str(exc), code="RULES_GET_LOGS_FAILED")

    def second_brain_list(self) -> dict[str, object]:
        """Return Second Brain items."""
        try:
            if self._second_brain_service is None:
                return fail("second_brain_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(_to_frontend_safe(self._second_brain_service.list_items()))
        except Exception as exc:
            return fail(str(exc), code="SECOND_BRAIN_LIST_FAILED")

    def second_brain_search(self, query: str) -> dict[str, object]:
        """Search Second Brain items."""
        try:
            if self._second_brain_service is None:
                return fail("second_brain_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(_to_frontend_safe(self._second_brain_service.search(query)))
        except Exception as exc:
            return fail(str(exc), code="SECOND_BRAIN_SEARCH_FAILED")

    def second_brain_get(self, item_id: str) -> dict[str, object]:
        """Return Second Brain item."""
        try:
            if self._second_brain_service is None:
                return fail("second_brain_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(_to_frontend_safe(self._second_brain_service.get_item(item_id)))
        except Exception as exc:
            return fail(str(exc), code="SECOND_BRAIN_GET_FAILED")

    def second_brain_pin(self, item_id: str) -> dict[str, object]:
        """Pin Second Brain item."""
        try:
            if self._second_brain_service is None:
                return fail("second_brain_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(_to_frontend_safe(self._second_brain_service.pin_item(item_id)))
        except Exception as exc:
            return fail(str(exc), code="SECOND_BRAIN_PIN_FAILED")

    def second_brain_favorite(self, item_id: str) -> dict[str, object]:
        """Favorite Second Brain item."""
        try:
            if self._second_brain_service is None:
                return fail("second_brain_service is not configured", code="SERVICE_UNAVAILABLE")
            return ok(_to_frontend_safe(self._second_brain_service.favorite_item(item_id)))
        except Exception as exc:
            return fail(str(exc), code="SECOND_BRAIN_FAVORITE_FAILED")

    def second_brain_note_create(
        self, parent: str, filename: str, content: str = ""
    ) -> dict[str, object]:
        """Create a new Second Brain note ``parent/filename``."""
        try:
            if self._second_brain_service is None:
                return fail("second_brain_service is not configured", code="SERVICE_UNAVAILABLE")
            created = self._second_brain_service.create_note(
                Path(parent), filename, content
            )
            return ok(_to_frontend_safe(created))
        except Exception as exc:
            return fail(str(exc), code="SECOND_BRAIN_NOTE_CREATE_FAILED")

    def second_brain_folder_create(self, parent: str, name: str) -> dict[str, object]:
        """Create a subfolder ``parent/name`` in the Second Brain root."""
        try:
            if self._second_brain_service is None:
                return fail("second_brain_service is not configured", code="SERVICE_UNAVAILABLE")
            created = self._second_brain_service.create_folder(Path(parent), name)
            return ok(_to_frontend_safe(created))
        except Exception as exc:
            return fail(str(exc), code="SECOND_BRAIN_FOLDER_CREATE_FAILED")

    def second_brain_file_create(
        self, parent: str, filename: str, content: str = ""
    ) -> dict[str, object]:
        """Create a generic text-like file ``parent/filename`` in the Second Brain.

        Extension is restricted to a text-like allowlist; binary/unknown types
        are rejected (use the OS file system for those).
        """
        try:
            if self._second_brain_service is None:
                return fail("second_brain_service is not configured", code="SERVICE_UNAVAILABLE")
            created = self._second_brain_service.create_file(
                Path(parent), filename, content
            )
            return ok(_to_frontend_safe(created))
        except Exception as exc:
            return fail(str(exc), code="SECOND_BRAIN_FILE_CREATE_FAILED")

    def second_brain_note_write(self, filepath: str, content: str) -> dict[str, object]:
        """Write ``content`` to an existing Second Brain note."""
        try:
            if self._second_brain_service is None:
                return fail("second_brain_service is not configured", code="SERVICE_UNAVAILABLE")
            written = self._second_brain_service.write_note(Path(filepath), content)
            return ok(_to_frontend_safe(written))
        except Exception as exc:
            return fail(str(exc), code="SECOND_BRAIN_NOTE_WRITE_FAILED")

    def second_brain_note_delete(self, filepath: str) -> dict[str, object]:
        """Delete a Second Brain note (sends to Recycle Bin)."""
        try:
            if self._second_brain_service is None:
                return fail("second_brain_service is not configured", code="SERVICE_UNAVAILABLE")
            self._second_brain_service.delete_note(Path(filepath))
            return ok(None)
        except Exception as exc:
            return fail(str(exc), code="SECOND_BRAIN_NOTE_DELETE_FAILED")

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


def _scheduler_entry_payload(entry: object) -> dict[str, object]:
    """Return a frontend-safe scheduler entry dict with a confirmation flag.

    Outlook/Teams-channel entries are flagged ``requires_confirmation=True`` so
    the frontend gates them behind a Confirmation_UI before triggering (Req 10.7).
    """
    data = _to_frontend_safe(entry.to_dict())  # type: ignore[attr-defined]
    if isinstance(data, dict):
        channels = data.get("channels") or []
        data["requires_confirmation"] = isinstance(channels, list) and any(
            c in ("outlook_email", "teams") for c in channels
        )
    return data


def _push_js_state(w: object, state: str) -> None:
    """Push window state to frontend via evaluate_js (thread-safe)."""
    try:
        w.evaluate_js(f"window.dispatchEvent(new CustomEvent('pywin-state', {{detail:'{state}'}}))")
    except Exception:
        pass


def register_win_events(w: object) -> None:
    """Hook pywebview window events to sync state to frontend."""
    w.events.maximized += lambda: _push_js_state(w, "maximized")
    w.events.restored += lambda: _push_js_state(w, "normal")
    w.events.minimized += lambda: _push_js_state(w, "minimized")


def _to_frontend_safe(value: object) -> object:
    """Convert DTO data to JSON/frontend-safe primitives."""
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return value.as_posix()
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
