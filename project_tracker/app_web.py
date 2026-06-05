"""pywebview application bootstrap for the HTML/Tailwind frontend."""

from __future__ import annotations

import sys
import tempfile
from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import webview

from project_tracker.core.enums import ProjectState
from project_tracker.core.models import AppSettings, ProjectMetadata, local_now
from project_tracker.infrastructure.cache_db import CacheDb
from project_tracker.infrastructure.filesystem import scan_year
from project_tracker.infrastructure.link_bank_store import LinkBankStore
from project_tracker.infrastructure.metadata_store import MetadataStore
from project_tracker.infrastructure.settings_store import SettingsStore
from project_tracker.services.automation_service import AutomationService
from project_tracker.services.dashboard_service import DashboardService
from project_tracker.services.email_service import EmailService
from project_tracker.services.notification_service import NotificationService
from project_tracker.services.project_service import ProjectService
from project_tracker.services.report_service import ReportService
from project_tracker.services.safe_delete_service import SafeDeleteService
from project_tracker.services.second_brain_service import SecondBrainService
from project_tracker.services.teams_service import TeamsMessage
from project_tracker.web.js_api import JsApi


class AppAPI:
    """JavaScript bridge exposed as ``pywebview.api``."""

    def __init__(self) -> None:
        self.settings_store = SettingsStore()
        self.metadata_store = MetadataStore()
        self.project_service = ProjectService(self.metadata_store)
        self.link_bank_store = LinkBankStore()
        self._notifications: list[dict[str, Any]] = []

    def get_projects(self, year: int | str | None = None) -> list[dict[str, Any]]:
        """Scan the configured project root and return real filesystem projects."""
        settings = self.settings_store.read()
        if settings.root_folder is None:
            return []

        root_folder = settings.root_folder.resolve(strict=False)
        if year is not None:
            if not isinstance(year, (int, str)) or not str(year).isdigit():
                return []
            years = [str(year)]
        else:
            years = self._discover_years(root_folder)
        projects: list[dict[str, Any]] = []
        for year_name in years:
            year_path = (root_folder / year_name).resolve(strict=False)
            if year_path.parent != root_folder:
                continue
            for project in scan_year(year_path, self.metadata_store):
                metadata = project.metadata
                projects.append(
                    {
                        "id": str(project.path),
                        "path": str(project.path),
                        "name": metadata.project_name or project.path.name,
                        "year": project.year,
                        "state": project.project_state.value,
                        "cr_state": metadata.cr_state.value,
                        "owner": settings.display_name,
                        "cr_link": metadata.cr_link,
                        "start_datetime": self._json_datetime(metadata.start_datetime),
                        "end_datetime": self._json_datetime(metadata.end_datetime),
                        "notes": metadata.notes,
                        "implementation_plan": metadata.implementation_plan,
                        "subprojects": [str(path) for path in project.subproject_paths],
                    }
                )
        return projects

    def get_settings(self) -> dict[str, Any]:
        """Return persisted application settings."""
        return self.settings_store.read().to_dict()

    def save_settings(self, data: dict[str, Any]) -> dict[str, Any]:
        """Persist application settings from the web bridge."""
        return self._wrap(lambda: self._save_settings(data))

    def choose_root_folder(self) -> dict[str, Any]:
        """Open a native folder dialog and save the selected root folder."""
        return self._wrap(self._choose_root_folder)

    def save_project(self, project: dict[str, Any]) -> dict[str, Any]:
        """Save editable project metadata for an existing project folder."""
        return self._wrap(lambda: self._save_project(project))

    def transition_project(self, project_path: str, action: str) -> dict[str, Any]:
        """Move a project through supported ProjectService transitions."""
        return self._wrap(lambda: self._transition_project(project_path, action))

    def delete_project(self, project_path: str) -> dict[str, Any]:
        """Move a project folder to the Windows Recycle Bin via SafeDeleteService."""
        validated_path = self._wrap(lambda: {"ok": True, "path": self._validate_project_path(project_path, require_existing=True)})
        if not validated_path.get("ok"):
            return validated_path
        if sys.platform != "win32":
            return self._todo("Delete project is unavailable on non-Windows platforms")
        return self._wrap(lambda: SafeDeleteService().delete_to_trash(validated_path["path"]))

    def generate_report(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        # TODO: Wire report generation when a report service exists for the HTML bridge.
        return self._todo("Report generation backend is not implemented")

    def run_email_rule(self, project_path: str, category_name: str) -> dict[str, Any]:
        """Render an email rule payload; Outlook sending remains service-guarded elsewhere."""
        return self._wrap(lambda: self._run_email_rule(project_path, category_name))

    def prepare_teams_message(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Prepare a Teams message payload without invoking Windows automation."""
        return self._wrap(lambda: self._prepare_teams_message(payload or {}))

    def start_download_email(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        # TODO: DownloadEmailService depends on the legacy signal/thread worker; bridge adapter is absent.
        return self._todo("Download email bridge adapter is not implemented")

    def create_note(self, project_path: str, note: str) -> dict[str, Any]:
        """Append a note to project metadata."""
        return self._wrap(lambda: self._create_note(project_path, note))

    def save_link(self, link: dict[str, Any]) -> dict[str, Any]:
        """Persist a link-bank entry."""
        return self._wrap(lambda: self._save_link(link))

    def get_notifications(self) -> list[dict[str, Any]]:
        """Return in-memory bridge notifications."""
        return [notification for notification in self._notifications if not notification.get("dismissed")]

    def dismiss_notifications(self, notification_ids: list[str] | None = None) -> dict[str, Any]:
        """Dismiss selected notifications, or all notifications if no ids are supplied."""
        ids = set(notification_ids or [])
        for notification in self._notifications:
            if not ids or notification.get("id") in ids:
                notification["dismissed"] = True
        return {"ok": True, "dismissed": len(ids) if ids else "all"}

    def _save_settings(self, data: dict[str, Any]) -> dict[str, Any]:
        current = self.settings_store.read().to_dict()
        current.update(data)
        settings = AppSettings.from_dict(current)
        self.settings_store.write(settings)
        return {"ok": True, "settings": settings.to_dict()}

    def _choose_root_folder(self) -> dict[str, Any]:
        selection = webview.windows[0].create_file_dialog(webview.FOLDER_DIALOG) if webview.windows else None
        if not selection:
            return {"ok": False, "error": "No folder selected"}
        folder = Path(selection[0])
        settings = replace(self.settings_store.read(), root_folder=folder)
        self.settings_store.write(settings)
        return {"ok": True, "root_folder": str(folder), "settings": settings.to_dict()}

    def _save_project(self, project: dict[str, Any]) -> dict[str, Any]:
        project_path = self._validate_project_path(str(project.get("path") or project.get("id") or ""), require_existing=True)
        metadata = self.metadata_store.read(project_path) or ProjectMetadata(project_name=project_path.name)
        metadata = self._merge_metadata(metadata, project)
        metadata.updated_at = local_now()
        self.metadata_store.write(project_path, metadata)
        return {"ok": True, "project": self._project_payload(project_path, metadata)}

    def _transition_project(self, project_path: str, action: str) -> dict[str, Any]:
        settings = self.settings_store.read()
        path = self._validate_project_path(project_path, settings=settings, require_existing=True)
        normalized = action.lower().replace("-", "_")
        if normalized in {"prod_ready", "move_to_prod_ready"}:
            result = self.project_service.move_to_prod_ready(path, settings, local_now(), settings.t10_threshold_days)
        elif normalized in {"implemented", "move_to_implemented"}:
            result = self.project_service.move_to_implemented(path, settings, local_now())
        elif normalized in {"postpone", "postponed"}:
            result = self.project_service.postpone_project(path, settings)
        elif normalized in {"cancel", "canceled"}:
            result = self.project_service.cancel_project(path, settings)
        elif normalized in {"resume", "uat_prepare"}:
            result = self.project_service.resume_project(path, settings)
        elif normalized == "reopen":
            result = self.project_service.reopen_project(path, settings)
        else:
            return self._todo(f"Unsupported transition action: {action}")

        if hasattr(result, "allowed") and not result.allowed:
            return {"ok": False, "error": "; ".join(result.reasons), "warnings": result.warnings}
        return {"ok": True, "path": str(result)}

    def _run_email_rule(self, project_path: str, category_name: str) -> dict[str, Any]:
        settings = self.settings_store.read()
        path = self._validate_project_path(project_path, settings=settings, require_existing=True)
        metadata = self.metadata_store.read(path)
        if metadata is None:
            raise FileNotFoundError(f"Project metadata not found: {path}")
        category = settings.email.categories.get(category_name)
        if category is None:
            return self._todo(f"Email category is not configured: {category_name}")
        rendered = EmailService().render_email_template(metadata, category, settings)
        return {
            "ok": True,
            "email": {
                "to": rendered.to,
                "cc": rendered.cc,
                "subject": rendered.subject,
                "body": rendered.body,
                "attachment_path": str(rendered.attachment_path) if rendered.attachment_path else "",
            },
        }

    def _prepare_teams_message(self, payload: dict[str, Any]) -> dict[str, Any]:
        message = TeamsMessage(
            target_email=str(payload.get("target_email", "")),
            target_group=str(payload.get("target_group", "")),
            mentions=[str(item) for item in payload.get("mentions", [])],
            message=str(payload.get("message") or payload.get("message_template") or ""),
            auto_send=bool(payload.get("auto_send", False)),
        )
        return {"ok": True, "message": asdict(message)}

    def _create_note(self, project_path: str, note: str) -> dict[str, Any]:
        path = self._validate_project_path(project_path, require_existing=True)
        metadata = self.metadata_store.read(path) or ProjectMetadata(project_name=path.name)
        timestamp = local_now().isoformat()
        separator = "\n\n" if metadata.notes else ""
        metadata.notes = f"{metadata.notes}{separator}[{timestamp}] {note}"
        metadata.updated_at = local_now()
        self.metadata_store.write(path, metadata)
        return {"ok": True, "notes": metadata.notes}

    def _save_link(self, link: dict[str, Any]) -> dict[str, Any]:
        bank = self.link_bank_store.read()
        normalized = {
            "name": str(link.get("name", "")),
            "url": str(link.get("url", "")),
            "notes": str(link.get("notes", "")),
            "category": str(link.get("category", "")),
        }
        if not normalized["name"] or not normalized["url"]:
            raise ValueError("Link name and url are required")
        parsed_url = urlparse(normalized["url"])
        if parsed_url.scheme not in {"http", "https"}:
            raise ValueError("Link url must use http or https")
        bank.links.append(normalized)
        category = normalized["category"]
        if category and category not in bank.categories:
            bank.categories.append(category)
        self.link_bank_store.write(bank)
        return {"ok": True, "link": normalized}

    def _discover_years(self, root_folder: Path) -> list[str]:
        if not root_folder.exists():
            return []
        return sorted(child.name for child in root_folder.iterdir() if child.is_dir() and child.name.isdigit())

    def _validate_project_path(
        self,
        project_path: str,
        *,
        settings: AppSettings | None = None,
        require_existing: bool = True,
    ) -> Path:
        settings = settings or self.settings_store.read()
        if settings.root_folder is None:
            raise ValueError("Project root folder is not configured")

        path = Path(project_path).resolve(strict=False)
        root_folder = settings.root_folder.resolve(strict=False)
        if path != root_folder and root_folder not in path.parents:
            raise ValueError("Project path is outside the configured root folder")
        if require_existing and not path.is_dir():
            raise FileNotFoundError(f"Project folder not found: {path}")
        if path.parent == path or path.parent.parent == path.parent:
            raise ValueError("Project path must be inside a year and state folder")
        try:
            ProjectState(path.parent.name)
        except ValueError as exc:
            raise ValueError(f"Invalid project state folder: {path.parent.name}") from exc
        if not path.parent.parent.name.isdigit():
            raise ValueError(f"Invalid project year folder: {path.parent.parent.name}")
        return path

    def _project_payload(self, project_path: Path, metadata: ProjectMetadata) -> dict[str, Any]:
        return {
            "id": str(project_path),
            "path": str(project_path),
            "name": metadata.project_name or project_path.name,
            "state": project_path.parent.name,
            "year": project_path.parent.parent.name,
            "metadata": metadata.to_dict(),
        }

    def _merge_metadata(self, metadata: ProjectMetadata, values: dict[str, Any]) -> ProjectMetadata:
        data = metadata.to_dict()
        for key, value in values.items():
            if key in data and key != "$schema":
                data[key] = value
        if "name" in values:
            data["project_name"] = values["name"]
        for key in ("start_datetime", "end_datetime", "cr_state_updated_at", "cr_pending_approval_at"):
            if key in data:
                data[key] = self._normalize_datetime_input(data[key])
        return ProjectMetadata.from_dict(data)

    def _normalize_datetime_input(self, value: Any) -> str | None:
        if value in (None, ""):
            return None
        if not isinstance(value, str):
            return str(value)
        candidate = value.strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError:
            candidate = candidate.replace(" ", "T", 1)
            parsed = datetime.fromisoformat(candidate)
        if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
            parsed = parsed.replace(tzinfo=local_now().tzinfo)
        return parsed.isoformat()

    def _wrap(self, action: Callable[[], Any]) -> dict[str, Any]:
        try:
            result = action()
            if isinstance(result, dict) and "ok" in result:
                return result
            return {"ok": True, "result": result}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _todo(self, message: str) -> dict[str, Any]:
        return {"ok": False, "error": f"TODO: {message}"}

    def _json_datetime(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


def create_js_api(
    *,
    db_path: Path | None = None,
    settings_store: SettingsStore | None = None,
    _dashboard_service: object = None,
) -> JsApi:
    """Create wired JsApi with all available service dependencies.

    Args:
        db_path: Optional override for SQLite cache database path.
            When None, a temporary database is used (test/dev default).
        settings_store: Optional override for settings store.
            When None, a fresh SettingsStore is created.
        _dashboard_service: Optional override for dashboard service (test only).

    Returns:
        JsApi with all available service dependencies wired.
    """
    _db_path = db_path or Path(tempfile.gettempdir()) / "project_tracker_cache.db"
    cache_db = CacheDb(_db_path)
    cache_db.initialize()

    _settings_store = settings_store or SettingsStore()

    # ── services ─────────────────────────────────────────────────────
    dashboard_svc = _dashboard_service or DashboardService(cache=cache_db)
    notification_svc = NotificationService()
    report_svc = ReportService(dashboard_service=dashboard_svc)
    automation_svc = AutomationService()
    second_brain_svc = SecondBrainService()

    # ── settings adapter (SettingsStore.read() → get_settings()) ──────
    class _SettingsAdapter:
        """Thin adapter exposing SettingsStore as JsApi protocol."""

        def __init__(self, store: SettingsStore) -> None:
            self._store = store

        def get_settings(self) -> object:
            return self._store.read().to_dict()

        def update_settings(self, data: dict[str, object]) -> object:
            current = self._store.read().to_dict()
            current.update(data)
            settings = AppSettings.from_dict(current)
            self._store.write(settings)
            return {"ok": True, "settings": settings.to_dict()}

    # ── project service adapter (dashboard → project protocol) ────────
    class _ProjectServiceAdapter:
        """Thin adapter: delegates list to DashboardService.

        JsApi.project_list() calls list_projects(year); DashboardService
        already has that.  Mutations (create/update/delete/rename/folder-*)
        are not yet wired and return controlled errors.
        """

        def __init__(self, dashboard: object) -> None:
            self._dashboard = dashboard

        def list_projects(self, year: str | None = None) -> object:
            return self._dashboard.list_projects(year)

        # ── unsupported: return None so JsApi returns SERVICE_UNAVAILABLE ──
        get_project = None  # type: ignore[assignment]
        open_folder = None  # type: ignore[assignment]
        create_project = None  # type: ignore[assignment]
        update_project = None  # type: ignore[assignment]
        rename_project = None  # type: ignore[assignment]
        update_cr_link = None  # type: ignore[assignment]
        update_cr_state = None  # type: ignore[assignment]
        add_drone = None  # type: ignore[assignment]
        update_drone = None  # type: ignore[assignment]
        delete_drone = None  # type: ignore[assignment]
        move_to_prod_ready = None  # type: ignore[assignment]
        move_to_implemented = None  # type: ignore[assignment]
        postpone_project = None  # type: ignore[assignment]
        resume_project = None  # type: ignore[assignment]
        cancel_project = None  # type: ignore[assignment]
        reopen_project = None  # type: ignore[assignment]
        list_subprojects = None  # type: ignore[assignment]
        create_subproject = None  # type: ignore[assignment]
        delete_subproject = None  # type: ignore[assignment]

    # ── JsApi ─────────────────────────────────────────────────────────
    return JsApi(
        dashboard_service=dashboard_svc,
        notification_service=notification_svc,
        report_service=report_svc,
        project_service=_ProjectServiceAdapter(dashboard_svc),
        settings_store=_SettingsAdapter(_settings_store),
        automation_service=automation_svc,
        second_brain_service=second_brain_svc,
    )


def run() -> None:
    """Create webview window and start pywebview on main thread."""
    frontend_path = Path(__file__).resolve().parent.parent / "frontend" / "dashboard.html"
    webview.create_window(
        "Project Tracker DBS",
        frontend_path.as_uri(),
        js_api=AppAPI(),
        width=1200,
        height=760,
        min_size=(960, 640),
    )
    webview.start()


if __name__ == "__main__":
    run()
