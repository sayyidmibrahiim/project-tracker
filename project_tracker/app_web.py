"""pywebview application bootstrap for the HTML/Tailwind frontend."""

from __future__ import annotations

import hashlib
import sys
import tempfile
import uuid
from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import webview

from project_tracker.core.enums import CRState, ProjectState
from project_tracker.core.models import AppSettings, ProjectMetadata, local_now
from project_tracker.core.rules import TransitionGuardResult, extract_cr_number
from project_tracker.infrastructure.cache_db import CacheDb, rebuild_year_cache
from project_tracker.infrastructure import outlook_client
from project_tracker.infrastructure.filesystem import (
    create_file,
    create_file_from_template,
    discover_subproject_paths,
    rename_file,
    scan_year,
)
from project_tracker.infrastructure.link_bank_store import LinkBankStore
from project_tracker.infrastructure.metadata_store import MetadataStore
from project_tracker.infrastructure.settings_store import SettingsStore
from project_tracker.services.automation_service import AutomationService
from project_tracker.services.dashboard_service import DashboardService
from project_tracker.services.download_email_service import DownloadEmailService
from project_tracker.services.email_service import (
    EmailService,
    TemplateConditionsNotMetError,
    UnresolvedPlaceholderError,
)
from project_tracker.services.notification_service import NotificationService
from project_tracker.services.project_service import ProjectService
from project_tracker.services.report_service import ReportService
from project_tracker.services.safe_delete_service import SafeDeleteService
from project_tracker.services.scheduler_service import SchedulerService
from project_tracker.services.second_brain_service import SecondBrainItem, SecondBrainService
from project_tracker.services.teams_service import TeamsMessage, TeamsService
from project_tracker.web.js_api import JsApi, fail, ok


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SVELTE_STATIC_DIR = PROJECT_ROOT / "web" / "static"
SVELTE_ENTRY_PATH = SVELTE_STATIC_DIR / "index.html"
VITE_DEV_SERVER_URL = "http://localhost:5173"


def _parse_optional_datetime(value: object) -> datetime | None:
    """Parse an optional ISO-8601 datetime string into a tz-aware datetime."""
    if value is None or value == "":
        return None
    candidate = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        candidate = candidate.replace(" ", "T", 1)
        parsed = datetime.fromisoformat(candidate)
    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        parsed = parsed.replace(tzinfo=local_now().tzinfo)
    return parsed


def _folder_state_for_path(path: Path) -> ProjectState | None:
    """Return the ProjectState of the project folder that contains ``path``.

    The canonical layout is ``root/<year>/<STATE>/<project>/...`` so the state is
    derived by scanning the path parts for a segment whose name matches a
    ``ProjectState`` value. Returns ``None`` when no state folder is present in
    the path (e.g. a Second Brain or template location outside the project tree),
    in which case file-mutation locks do not apply.
    """
    state_values = {state.value for state in ProjectState}
    for part in Path(path).parts:
        if part in state_values:
            return ProjectState(part)
    return None


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
    linkbank_store: LinkBankStore | None = None,
    _dashboard_service: object = None,
) -> JsApi:
    """Create wired JsApi with all available service dependencies.

    Args:
        db_path: Optional override for SQLite cache database path.
            When None, a temporary database is used (test/dev default).
        settings_store: Optional override for settings store.
            When None, a fresh SettingsStore is created.
        linkbank_store: Optional override for link bank store.
            When None, a fresh LinkBankStore is created.
        _dashboard_service: Optional override for dashboard service (test only).

    Returns:
        JsApi with all available service dependencies wired.
    """
    _db_path = db_path or Path(tempfile.gettempdir()) / "project_tracker_cache.db"
    cache_db = CacheDb(_db_path)
    cache_db.initialize()

    _settings_store = settings_store or SettingsStore()
    _linkbank_store = linkbank_store or LinkBankStore()

    def _second_brain_items_provider() -> list[SecondBrainItem]:
        """Read-only filesystem index from AppSettings.second_brain_folder."""
        folder = _settings_store.read().second_brain_folder
        if folder is None or not folder.is_dir():
            return []

        items: list[SecondBrainItem] = []
        for path in folder.rglob("*"):
            if not path.is_file() or any(part.startswith(".") for part in path.relative_to(folder).parts):
                continue
            relative = path.relative_to(folder).as_posix()
            item_id = hashlib.sha1(relative.encode("utf-8")).hexdigest()[:16]
            suffix = path.suffix.casefold()
            excerpt = ""
            if suffix in {".md", ".txt"}:
                try:
                    excerpt = path.read_text(encoding="utf-8", errors="replace")[:200]
                except OSError:
                    excerpt = ""
            try:
                updated_at = datetime.fromtimestamp(path.stat().st_mtime).astimezone()
            except OSError:
                updated_at = None
            items.append(
                SecondBrainItem(
                    id=item_id,
                    title=path.stem,
                    path=path,
                    item_type="note" if suffix in {".md", ".txt"} else "file",
                    updated_at=updated_at,
                    excerpt=excerpt,
                )
            )
        return sorted(items, key=lambda item: (item.title.casefold(), str(item.path).casefold()))

    # ── services ─────────────────────────────────────────────────────
    dashboard_svc = _dashboard_service or DashboardService(cache=cache_db)
    notification_svc = NotificationService(cache=cache_db)
    notification_svc.load_persisted()
    report_svc = ReportService(dashboard_service=dashboard_svc)
    automation_svc = AutomationService()
    # Scheduler control surface (entry CRUD persisted under settings.automation.
    # scheduler.entries). No interval job here — the 60s auto IN-PROGRESS job is
    # owned by AutoTransitionService; the scheduler is not auto-started.
    scheduler_svc = SchedulerService(
        settings_store=_settings_store,
        notification_service=notification_svc,
        project_provider=lambda: [],
    )
    second_brain_svc = SecondBrainService(
        items_provider=_second_brain_items_provider,
        folder_provider=lambda: _settings_store.read().second_brain_folder,
    )

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

    # ── link bank adapter (LinkBankStore.read() → get_linkbank()) ────
    class _LinkBankAdapter:
        """Thin adapter exposing LinkBankStore as read-only JsApi protocol."""

        def __init__(self, store: LinkBankStore) -> None:
            self._store = store

        def get_linkbank(self) -> object:
            return self._store.read().to_dict()

        def update_linkbank(self, data: dict[str, object]) -> object:
            """Update a single link's fields by id."""
            link_id = str(data.get("id", ""))
            if not link_id:
                raise ValueError("Link id is required")
            bank = self._store.read()
            target = next((link for link in bank.links if link.get("id") == link_id), None)
            if target is None:
                raise ValueError(f"Link not found: {link_id}")
            for key in ("name", "url", "notes", "category"):
                if key in data:
                    target[key] = str(data[key])
            old_category = target.get("category", "")
            if old_category and old_category not in bank.categories:
                bank.categories.append(old_category)
            self._store.write(bank)
            return dict(target)

        def add_link(self, data: dict[str, object]) -> object:
            """Create a new link with a stable uuid id and persist it."""
            name = str(data.get("name", "")).strip()
            url = str(data.get("url", "")).strip()
            if not name or not url:
                raise ValueError("Link name and url are required")
            parsed_url = urlparse(url)
            if parsed_url.scheme not in {"http", "https"}:
                raise ValueError("Link url must use http or https")
            bank = self._store.read()
            link = {
                "id": uuid.uuid4().hex,
                "name": name,
                "url": url,
                "notes": str(data.get("notes", "")),
                "category": str(data.get("category", "")),
                "archived": "false",
            }
            bank.links.append(link)
            category = link["category"]
            if category and category not in bank.categories:
                bank.categories.append(category)
            self._store.write(bank)
            return dict(link)

        def archive_link(self, link_id: str) -> object:
            """Soft-archive a link by id."""
            link_id = str(link_id)
            if not link_id:
                raise ValueError("Link id is required")
            bank = self._store.read()
            target = next((link for link in bank.links if link.get("id") == link_id), None)
            if target is None:
                raise ValueError(f"Link not found: {link_id}")
            target["archived"] = "true"
            self._store.write(bank)
            return dict(target)

    # ── project service adapter (dashboard → project protocol) ────────
    class _ProjectServiceAdapter:
        """Thin adapter: delegates list to DashboardService.

        JsApi.project_list() calls list_projects(year); DashboardService
        already has that.  Read methods get_project/list_subprojects are
        now wired through MetadataStore.  Mutations (create/update/delete/
        rename/folder-*) are not yet wired and return controlled errors.
        """

        def __init__(
            self,
            dashboard: object,
            metadata_store: MetadataStore,
            project_service: ProjectService,
            settings_store: SettingsStore,
            cache_db: CacheDb,
            notification_service: NotificationService,
        ) -> None:
            self._dashboard = dashboard
            self._metadata_store = metadata_store
            self._project_service = project_service
            self._settings_store = settings_store
            self._cache_db = cache_db
            self._notification_service = notification_service

        def list_projects(self, year: str | None = None) -> object:
            return self._dashboard.list_projects(year)

        # ── wired read methods ──

        def get_project(self, project_path: Path) -> object:
            """Return project detail from MetadataStore + filesystem."""
            path = Path(project_path)
            metadata = self._metadata_store.read(path)
            if metadata is None:
                raise FileNotFoundError(f"Project metadata not found: {path}")

            project_state = ProjectState(path.parent.name)
            drone_tickets = getattr(metadata, "drone_tickets", None) or []
            cr_number = extract_cr_number(metadata.cr_link)

            return {
                "project_name": metadata.project_name or path.name,
                "project_path": str(path),
                "project_state": project_state.value,
                "cr_number": cr_number or "",
                "cr_link": metadata.cr_link or "",
                "cr_state": metadata.cr_state.value,
                "start_datetime": metadata.start_datetime,
                "end_datetime": metadata.end_datetime,
                "t10_status": "N/A",
                "drone_ticket_count": len(drone_tickets),
                "drone_tickets": [
                    {
                        "subfolder_name": t.subfolder_name,
                        "drone_link": t.drone_link,
                        "drone_state": t.drone_state.value,
                        "owner": t.owner,
                    }
                    for t in drone_tickets
                ],
            }

        def list_subprojects(self, project_path: Path) -> object:
            """Return subproject paths under project_path."""
            return [str(p) for p in discover_subproject_paths(Path(project_path))]

        # ── wired mutation: update_cr_link (metadata-only) ──

        def update_cr_link(self, project_path: Path, cr_link: str) -> object:
            """Update CR link in metadata and persist."""
            from project_tracker.core.models import HistoryEntry
            from project_tracker.core.rules import current_user

            path = Path(project_path)
            metadata = self._metadata_store.read(path)
            if metadata is None:
                raise FileNotFoundError(f"Project metadata not found: {path}")
            metadata.cr_link = cr_link
            metadata.updated_at = local_now()
            metadata.history.append(
                HistoryEntry(
                    timestamp=metadata.updated_at,
                    action="CR_LINK",
                    detail="CR link updated",
                    user=current_user(self._settings_store.read()),
                )
            )
            self._metadata_store.write(path, metadata)
            project_state = ProjectState(path.parent.name)
            cr_number = extract_cr_number(cr_link)
            return {
                "project_path": str(path),
                "project_state": project_state.value,
                "cr_state": metadata.cr_state.value,
                "cr_number": cr_number or "",
                "cr_link": cr_link,
            }

        # ── wired mutation: drone CRUD (metadata-only) ──

        def add_drone(self, project_path: Path, data: dict[str, object]) -> object:
            """Append a new drone ticket to metadata."""
            path = Path(project_path)
            metadata = self._metadata_store.read(path)
            if metadata is None:
                raise FileNotFoundError(f"Project metadata not found: {path}")
            from project_tracker.core.models import DroneTicket

            ticket = DroneTicket(
                subfolder_name=str(data.get("subfolder_name", "")) or None,
                drone_link=str(data.get("drone_link", "")),
                owner=str(data.get("owner", "")),
            )
            metadata.drone_tickets.append(ticket)
            metadata.updated_at = local_now()
            self._metadata_store.write(path, metadata)
            return {"project_path": str(path), "drone_ticket_count": len(metadata.drone_tickets)}

        def update_drone(self, project_path: Path, drone_index: int, data: dict[str, object]) -> object:
            """Update drone ticket fields at index.

            Field edits (drone_link/owner/subfolder_name) are metadata-only.
            ``drone_state``, when present, is routed through the state-machine
            guard ``validate_drone_state_change_allowed`` which raises
            InvalidTransitionError on disallowed transitions or empty link.
            """
            path = Path(project_path)
            metadata = self._metadata_store.read(path)
            if metadata is None:
                raise FileNotFoundError(f"Project metadata not found: {path}")
            if drone_index < 0 or drone_index >= len(metadata.drone_tickets):
                raise IndexError(f"Drone index {drone_index} out of range")
            ticket = metadata.drone_tickets[drone_index]
            if "drone_link" in data:
                ticket.drone_link = str(data["drone_link"])
            if "owner" in data:
                ticket.owner = str(data["owner"])
            if "subfolder_name" in data:
                ticket.subfolder_name = str(data["subfolder_name"]) or None
            now = local_now()
            state_changed = False
            if "drone_state" in data:
                from project_tracker.core.enums import DroneState
                from project_tracker.core.models import HistoryEntry
                from project_tracker.core.rules import current_user
                from project_tracker.core.state_machine import validate_drone_state_change_allowed

                target = DroneState(str(data["drone_state"]))
                validate_drone_state_change_allowed(ticket.drone_link, ticket.drone_state, target)
                old_state = ticket.drone_state
                ticket.drone_state = target
                ticket.drone_state_updated_at = now
                label = ticket.subfolder_name or f"ticket {drone_index + 1}"
                metadata.history.append(
                    HistoryEntry(
                        timestamp=now,
                        action="DRONE_STATE_CHANGE",
                        detail=f"Drone {label}: {old_state.value} → {target.value}",
                        user=current_user(self._settings_store.read()),
                    )
                )
                state_changed = True
            metadata.updated_at = now
            self._metadata_store.write(path, metadata)
            response = {"project_path": str(path), "drone_ticket_count": len(metadata.drone_tickets)}
            if state_changed:
                # A drone reaching APPROVED can let a pending CR-APPROVED move
                # land; resolve_auto_move keys on metadata.cr_state so drone-only
                # changes won't over-trigger.
                result = self._apply_auto_move(path)
                if result is not None and "moved_path" in result:
                    response["project_path"] = result["moved_path"]
            return response

        def delete_drone(self, project_path: Path, drone_index: int) -> object:
            """Remove drone ticket at index."""
            path = Path(project_path)
            metadata = self._metadata_store.read(path)
            if metadata is None:
                raise FileNotFoundError(f"Project metadata not found: {path}")
            if drone_index < 0 or drone_index >= len(metadata.drone_tickets):
                raise IndexError(f"Drone index {drone_index} out of range")
            metadata.drone_tickets.pop(drone_index)
            metadata.updated_at = local_now()
            self._metadata_store.write(path, metadata)
            return {"project_path": str(path), "drone_ticket_count": len(metadata.drone_tickets)}

        # ── wired mutation: guarded CR state (metadata-only, no folder move) ──

        def update_cr_state(self, project_path: Path, cr_state: str) -> object:
            """Update CR state through state-machine guard, then auto-move.

            Runs the G1 guard before approving (CR cannot be APPROVED while any
            drone is not APPROVED), appends a history entry, persists, and then
            asks ``_apply_auto_move`` whether the folder should move (e.g. a CR
            reaching APPROVED lands the project in PROD_READY).
            """
            from project_tracker.core.models import HistoryEntry
            from project_tracker.core.rules import (
                current_user,
                validate_cr_approved_requires_drones,
            )
            from project_tracker.core.state_machine import validate_cr_transition

            path = Path(project_path)
            metadata = self._metadata_store.read(path)
            if metadata is None:
                raise FileNotFoundError(f"Project metadata not found: {path}")
            target = CRState(cr_state)
            validate_cr_transition(metadata.cr_state, target)
            if target == CRState.APPROVED:
                g1 = validate_cr_approved_requires_drones(metadata.drone_tickets)
                if not g1.allowed:
                    raise ValueError("; ".join(g1.failed_guards))
            now = local_now()
            settings = self._settings_store.read()
            old = metadata.cr_state
            # Capture project_state while ``path`` is still valid; _apply_auto_move
            # may physically move the folder out from under it.
            project_state = ProjectState(path.parent.name)
            metadata.cr_state = target
            metadata.cr_state_updated_at = now
            metadata.updated_at = now
            if (
                target == CRState.PENDING_APPROVAL
                and metadata.cr_pending_approval_at is None
            ):
                metadata.cr_pending_approval_at = now
            metadata.history.append(
                HistoryEntry(
                    timestamp=now,
                    action="CR_STATE_CHANGE",
                    detail=f"CR {old.value} → {target.value}",
                    user=current_user(settings),
                )
            )
            self._metadata_store.write(path, metadata)
            response = {
                "project_path": str(path),
                "project_state": project_state.value,
                "cr_state": target.value,
            }
            result = self._apply_auto_move(path)
            if result is not None:
                if "banner" in result:
                    response["banner"] = result["banner"]
                elif "moved_path" in result:
                    response["project_path"] = result["moved_path"]
                    response["project_state"] = result["to_state"]
            return response

        # ── wired mutation: update_project (metadata-only) ──

        def update_project(self, project_path: Path, data: dict[str, object]) -> object:
            """Update allowed metadata fields and persist. No folder move."""
            path = Path(project_path)
            if not path.is_dir():
                raise FileNotFoundError(f"Project folder not found: {path}")
            metadata = self._metadata_store.read(path)
            if metadata is None:
                raise FileNotFoundError(f"Project metadata not found: {path}")
            if "project_name" in data:
                metadata.project_name = str(data["project_name"])
            if "implementation_plan" in data:
                metadata.implementation_plan = str(data["implementation_plan"])
            if "cr_link" in data:
                metadata.cr_link = str(data["cr_link"])
            if "start_datetime" in data:
                metadata.start_datetime = _parse_optional_datetime(data["start_datetime"])
            if "end_datetime" in data:
                metadata.end_datetime = _parse_optional_datetime(data["end_datetime"])
            metadata.updated_at = local_now()
            self._metadata_store.write(path, metadata)
            project_state = ProjectState(path.parent.name)
            return {
                "project_path": str(path),
                "project_name": metadata.project_name or path.name,
                "project_state": project_state.value,
                "cr_state": metadata.cr_state.value,
            }

        # ── wired mutation: create_project (folder + initial metadata) ──

        def create_project(self, data: dict[str, object]) -> object:
            """Create a project folder under {root}/{year}/UAT_PREPARE/{name}."""
            from project_tracker.core.rules import validate_windows_folder_name

            name = str(data.get("project_name", "")).strip()
            if not name:
                raise ValueError("Project name is required")
            validate_windows_folder_name(name)

            year = str(data.get("year", "")).strip() or str(local_now().year)
            settings = _settings_store.read()
            if settings.root_folder is None:
                raise ValueError("Root folder is not configured")

            project_dir = settings.root_folder / year / "UAT_PREPARE" / name
            if project_dir.exists():
                raise ValueError(f"Project folder already exists: {project_dir}")

            project_dir.mkdir(parents=True)
            now = local_now()
            metadata = ProjectMetadata(
                project_name=name,
                created_at=now,
                updated_at=now,
            )
            self._metadata_store.write(project_dir, metadata)
            return {
                "project_path": str(project_dir),
                "project_name": name,
                "project_state": "UAT_PREPARE",
                "cr_state": metadata.cr_state.value,
            }

        # ── wired mutation: folder state transitions (guarded + rollback) ──

        def _rebuild_cache_for(self, moved_path: Path) -> None:
            """Rebuild the year cache after a successful transition (Req 4.11)."""
            year_path = moved_path.parent.parent
            rebuild_year_cache(self._cache_db, year_path, self._metadata_store)

        def _run_transition(
            self,
            project_path: object,
            service_call: Callable[[AppSettings], object],
            *,
            emit_t10: bool = False,
        ) -> object:
            """Execute a transition, map guard blocks, and update cache on success.

            - Loads ``AppSettings`` and invokes ``service_call``.
            - A blocked ``TransitionGuardResult`` raises with joined reasons so the
              JsApi facade returns ``ok=false`` (Req 4.9). When ``emit_t10`` is set
              and the sole failure is the T-10 guard, a T-10 violation notification
              is emitted (Req 4.3).
            - On success the Cache_Db is rebuilt before returning (Req 4.11). Any
              exception during the physical move propagates without a cache update,
              leaving the prior state and returning ``ok=false`` (Req 4.12).
            """
            settings = self._settings_store.read()
            result = service_call(settings)

            if isinstance(result, TransitionGuardResult) and not result.allowed:
                reasons = list(result.failed_guards)
                only_t10 = len(reasons) == 1 and "T-10" in reasons[0]
                if emit_t10 and only_t10 and self._notification_service is not None:
                    self._notification_service.add(
                        type="T10_VIOLATION",
                        title="T-10 violation",
                        message=reasons[0],
                        project_path=Path(str(project_path)),
                    )
                raise ValueError("; ".join(reasons))

            moved_path = Path(str(result))
            self._rebuild_cache_for(moved_path)
            return {
                "project_path": str(moved_path),
                "project_state": ProjectState(moved_path.parent.name).value,
            }

        def _apply_auto_move(self, project_path: Path) -> dict[str, object] | None:
            """Move the folder after an inline state persist (Req auto-move).

            Reads metadata, asks the pure ``resolve_auto_move`` evaluator for a
            target Folder_State, and routes to the matching tested
            ``ProjectService`` move method. On a successful move the Cache_Db is
            rebuilt, an ``AUTO_MOVE`` event is pushed, and a notification is
            emitted.

            Returns:
            - ``None`` when no move is needed (callers leave their response as-is).
            - ``{"banner": str}`` when a structural guard blocks the move.
            - ``{"moved_path": str, "to_state": str}`` on a successful move, so
              callers can refresh their response with the new on-disk location
              instead of returning the stale pre-move path.
            """
            from project_tracker.core.state_machine import resolve_auto_move
            from project_tracker.web.event_queue import push_event

            path = Path(project_path)
            metadata = self._metadata_store.read(path)
            if metadata is None:
                return None
            current_folder = ProjectState(path.parent.name)
            drone_states = [t.drone_state for t in metadata.drone_tickets]
            target = resolve_auto_move(metadata.cr_state, drone_states, current_folder)
            if target is None:
                return None

            settings = self._settings_store.read()
            if target == ProjectState.PROD_READY:
                result = self._project_service.move_to_prod_ready(
                    path,
                    settings,
                    local_now(),
                    settings.t10_threshold_days,
                    override_t10=False,
                )
            elif target == ProjectState.IMPLEMENTED:
                result = self._project_service.move_to_implemented(
                    path, settings, local_now()
                )
            elif target == ProjectState.POSTPONED:
                result = self._project_service.postpone_project(path, settings)
            elif target == ProjectState.CANCELED:
                result = self._project_service.cancel_project(path, settings)
            else:
                return None

            if isinstance(result, TransitionGuardResult) and not result.allowed:
                return {"banner": "; ".join(result.failed_guards)}

            moved_path = Path(str(result))
            self._rebuild_cache_for(moved_path)
            push_event(
                "AUTO_MOVE",
                {
                    "project_path": str(moved_path),
                    "from_state": current_folder.value,
                    "to_state": target.value,
                },
            )
            if self._notification_service is not None:
                self._notification_service.add(
                    type="AUTO_MOVE",
                    title="Project moved",
                    message=f"{path.name}: {current_folder.value} → {target.value}",
                    project_path=moved_path,
                )
            return {"moved_path": str(moved_path), "to_state": target.value}

        def move_to_prod_ready(
            self, project_path: Path, *, override_t10: bool = False
        ) -> object:
            return self._run_transition(
                project_path,
                lambda settings: self._project_service.move_to_prod_ready(
                    Path(project_path),
                    settings,
                    local_now(),
                    settings.t10_threshold_days,
                    override_t10=override_t10,
                ),
                emit_t10=True,
            )

        def move_to_implemented(self, project_path: Path) -> object:
            return self._run_transition(
                project_path,
                lambda settings: self._project_service.move_to_implemented(
                    Path(project_path), settings, local_now()
                ),
            )

        def postpone_project(self, project_path: Path) -> object:
            return self._run_transition(
                project_path,
                lambda settings: self._project_service.postpone_project(
                    Path(project_path), settings
                ),
            )

        def cancel_project(self, project_path: Path) -> object:
            return self._run_transition(
                project_path,
                lambda settings: self._project_service.cancel_project(
                    Path(project_path), settings
                ),
            )

        def resume_project(self, project_path: Path) -> object:
            return self._run_transition(
                project_path,
                lambda settings: self._project_service.resume_project(
                    Path(project_path), settings
                ),
            )

        def reopen_project(self, project_path: Path) -> object:
            return self._run_transition(
                project_path,
                lambda settings: self._project_service.reopen_project(
                    Path(project_path), settings
                ),
            )

        # ── wired mutation: rename / delete (guarded + cache rebuild) ──

        def _reject_if_locked(self, project_path: Path, action: str) -> ProjectState:
            """Return the Folder_State, rejecting rename/delete when locked.

            Rename and delete are disabled while a project is in ``PROD_READY``
            or ``IMPLEMENTED`` (Req 5.3 / 5.5). The state is derived from the
            path's parent (state) folder name; the backend is the authoritative
            guard regardless of the frontend lock model.
            """
            state = ProjectState(Path(project_path).parent.name)
            if state in (ProjectState.PROD_READY, ProjectState.IMPLEMENTED):
                raise ValueError(
                    f"{action} is disabled while the project is in {state.value}"
                )
            return state

        def rename_project(self, project_path: Path, new_name: str) -> object:
            """Rename a project folder and rebuild the year cache (Req 5.1-5.3, 5.6).

            Name validation and the case-insensitive sibling-duplicate check are
            performed by ``ProjectService.rename_project``; invalid names raise and
            leave the folder unchanged. On success the Cache_Db is rebuilt before
            returning so the dashboard reflects the new name on next read.
            """
            self._reject_if_locked(project_path, "Rename")
            settings = self._settings_store.read()
            moved_path = Path(
                str(self._project_service.rename_project(Path(project_path), new_name, settings))
            )
            self._rebuild_cache_for(moved_path)
            return {
                "project_path": str(moved_path),
                "project_name": new_name,
                "project_state": ProjectState(moved_path.parent.name).value,
            }

        def delete_project(self, project_path: Path) -> object:
            """Route a project-folder delete to the Recycle Bin (Req 5.4-5.6, 5.8).

            Rejected in PROD_READY/IMPLEMENTED. On success the Cache_Db is rebuilt
            before returning ``ok=true``. If ``send2trash`` fails the exception
            propagates (so the facade returns ``ok=false``); the folder is left in
            place and the cache is not updated.
            """
            path = Path(project_path)
            self._reject_if_locked(path, "Delete")
            year_path = path.parent.parent
            self._project_service.delete_project(path)
            rebuild_year_cache(self._cache_db, year_path, self._metadata_store)
            return {"project_path": str(path), "deleted": True}

        def delete_subproject(self, project_path: Path, name: str) -> object:
            """Route a subproject-folder delete to the Recycle Bin (Req 5.7-5.8).

            Resolves the subproject path under ``project_path`` and routes to
            ``ProjectService.delete_subproject`` → ``SafeDeleteService``. On a
            ``send2trash`` failure the exception propagates and the folder is left
            in place.
            """
            subproject_path = Path(project_path) / name
            self._project_service.delete_subproject(subproject_path)
            return {"project_path": str(Path(project_path)), "subproject": name, "deleted": True}

        # ── unsupported: return None so JsApi returns SERVICE_UNAVAILABLE ──
        open_folder = None  # type: ignore[assignment]
        create_subproject = None  # type: ignore[assignment]

    # ── year service adapter (SettingsStore → year list) ──────────────
    class _YearServiceAdapter:
        """Read-only year discovery from SettingsStore root_folder."""

        def __init__(self, settings_store: SettingsStore) -> None:
            self._settings_store = settings_store

        def list_years(self) -> object:
            settings = self._settings_store.read()
            root_folder = settings.root_folder
            if root_folder is None or not root_folder.exists():
                return []
            return sorted(
                child.name
                for child in root_folder.iterdir()
                if child.is_dir() and child.name.isdigit()
            )

        def create_year(self, year: str) -> object:
            """Create {root}/{year}/ plus the five Folder_State subfolders."""
            year = str(year).strip()
            if not year.isdigit():
                raise ValueError("Year must be numeric (e.g. 2026)")
            settings = self._settings_store.read()
            root_folder = settings.root_folder
            if root_folder is None:
                raise ValueError("Root folder is not configured")
            year_dir = root_folder / year
            if year_dir.exists():
                raise ValueError(f"Year folder already exists: {year_dir}")
            for state in ProjectState:
                (year_dir / state.value).mkdir(parents=True, exist_ok=True)
            return {"year": year, "path": str(year_dir)}

    # ── file service adapter (list / open / create / rename / delete) ─
    class _FileServiceAdapter:
        """File management adapter backed by ``filesystem.py`` helpers.

        - ``list_files``: read-only directory listing.
        - ``open_file``: guarded ``os.startfile`` on Windows; a dev-skipped
          no-op off-Windows that never invokes ``os.startfile`` (Req 6.4/6.5).
        - ``create_file`` / ``create_file_from_template`` / ``rename_file``:
          name-validated, reject existing names, routed through ``assert_within``
          so a failure leaves folder contents unchanged (Req 6.1-6.3, 6.6-6.7, 6.9).
        - ``delete_file``: routed to ``SafeDeleteService`` (send2trash, Req 6.8).
        - Create/rename/delete are rejected while the containing project is in
          ``PROD_READY`` or ``IMPLEMENTED`` (Req 6.10), enforced backend-side.
        """

        def __init__(
            self,
            settings_store: SettingsStore,
            safe_delete_service: SafeDeleteService,
        ) -> None:
            self._settings_store = settings_store
            self._safe_delete_service = safe_delete_service

        def list_files(self, path: Path) -> object:
            p = Path(path)
            if not p.is_dir():
                return []
            entries = [
                {"name": child.name, "path": str(child)}
                for child in p.iterdir()
                if child.is_file()
            ]
            entries.sort(key=lambda e: e["name"])
            return entries

        def open_file(self, path: Path) -> None:
            """Open a file externally; guarded on Windows, dev-skipped elsewhere."""
            if sys.platform == "win32":
                import os

                os.startfile(str(Path(path)))  # noqa: S606 (Windows-only guarded)
                return
            # Dev-skipped off-Windows: never invoke os.startfile (Req 6.5).
            return None

        def _reject_if_locked(self, path: Path, action: str) -> None:
            """Reject create/rename/delete while the project is locked (Req 6.10)."""
            state = _folder_state_for_path(Path(path))
            if state in (ProjectState.PROD_READY, ProjectState.IMPLEMENTED):
                raise ValueError(
                    f"{action} is disabled while the project is in {state.value}"
                )

        def create_file(self, folder: Path, filename: str) -> object:
            target_folder = Path(folder)
            self._reject_if_locked(target_folder, "File create")
            created = create_file(target_folder, target_folder / filename)
            return {"path": str(created), "name": created.name}

        def create_file_from_template(self, folder: Path, template_name: str) -> object:
            target_folder = Path(folder)
            self._reject_if_locked(target_folder, "File create")
            template_folder = self._settings_store.read().file_template_folder
            if template_folder is None:
                raise ValueError("Template folder is not configured")
            template = Path(template_folder) / template_name
            created = create_file_from_template(
                target_folder, template, target_folder / template_name
            )
            return {"path": str(created), "name": created.name}

        def rename_file(self, filepath: Path, new_name: str) -> object:
            source = Path(filepath)
            self._reject_if_locked(source, "File rename")
            base = source.parent
            renamed = rename_file(base, source, base / new_name)
            return {"path": str(renamed), "name": renamed.name}

        def delete_file(self, filepath: Path) -> object:
            target = Path(filepath)
            self._reject_if_locked(target, "File delete")
            self._safe_delete_service.delete_to_trash(target)
            return {"path": str(target), "deleted": True}

        open_folder = None  # type: ignore[assignment]

    # ── notes service adapter (MetadataStore → notes) ─────────────────
    class _NotesServiceAdapter:
        """Notes adapter: read/write notes.md file (PRD-correct).

        Notes remain editable in ``PROD_READY`` (Req 6.11) but are view-only in
        ``IMPLEMENTED`` (Req 6.12): edit submissions are rejected without
        persisting, leaving the existing notes file unchanged.
        """

        def get_notes(self, project_path: Path) -> object:
            notes_file = Path(project_path) / "notes.md"
            if not notes_file.is_file():
                return ""
            return notes_file.read_text(encoding="utf-8")

        def update_notes(self, project_path: Path, notes: str) -> object:
            state = _folder_state_for_path(Path(project_path))
            if state is ProjectState.IMPLEMENTED:
                raise ValueError(
                    "Notes are view-only while the project is in IMPLEMENTED"
                )
            notes_file = Path(project_path) / "notes.md"
            notes_file.write_text(notes, encoding="utf-8")
            return notes

    # ── outlook service adapter (EmailService + guarded outlook_client) ─
    class _OutlookServiceAdapter:
        """Outlook automation adapter (Draft_First, guarded, layered).

        Composes emails by reusing ``EmailService.render_email_template`` for the
        Template_Category (``ACK_UAT``/``ACK_SOP``/``APRVL_CR``/``APRVL_SOP``) and
        performs draft/send through the guarded ``outlook_client`` (dev-skipped
        off-Windows, never executing COM). An unresolved required placeholder
        returns ``ok=false`` naming it; unmet Template_Category conditions return a
        skipped Bridge_Response (Req 8.5/8.6). Contacts use
        ``outlook_client.get_contacts`` with name/email filtering on Windows and a
        dev fallback off-Windows (Req 8.7). Download is dev-skipped off-Windows and
        routed through ``DownloadEmailService`` on Windows (Req 8.8). Every method
        returns a complete Bridge_Response dict; runtime failures are ``ok=false``
        without claiming the email was drafted or sent (Req 8.9).
        """

        def __init__(
            self,
            settings_store: SettingsStore,
            metadata_store: MetadataStore,
            email_service: EmailService,
            download_email_service: DownloadEmailService,
        ) -> None:
            self._settings_store = settings_store
            self._metadata_store = metadata_store
            self._email_service = email_service
            self._download_email_service = download_email_service

        def _render(self, category_code: str, project_path: Path) -> object:
            """Resolve metadata + category and render the email (may raise)."""
            path = Path(project_path)
            settings = self._settings_store.read()
            metadata = self._metadata_store.read(path)
            if metadata is None:
                raise FileNotFoundError(f"Project metadata not found: {path}")
            category = settings.email.categories.get(category_code)
            if category is None:
                raise ValueError(f"Email category is not configured: {category_code}")
            return self._email_service.render_email_template(metadata, category, settings)

        def draft_email(self, category_code: str, project_path: Path) -> dict[str, object]:
            try:
                rendered = self._render(category_code, project_path)
            except UnresolvedPlaceholderError as exc:
                return fail(
                    str(exc),
                    code="OUTLOOK_DRAFT_FAILED",
                    details={"placeholder": exc.placeholder},
                )
            except TemplateConditionsNotMetError as exc:
                return ok({"status": "skipped", "reason": exc.reason})
            return outlook_client.create_draft_email(
                rendered.to,
                rendered.cc,
                rendered.subject,
                rendered.body,
                rendered.attachment_path,
            )

        def send_email(self, category_code: str, project_path: Path) -> dict[str, object]:
            try:
                rendered = self._render(category_code, project_path)
            except UnresolvedPlaceholderError as exc:
                return fail(
                    str(exc),
                    code="OUTLOOK_SEND_FAILED",
                    details={"placeholder": exc.placeholder},
                )
            except TemplateConditionsNotMetError as exc:
                return ok({"status": "skipped", "reason": exc.reason})
            return outlook_client.send_email(
                rendered.to,
                rendered.cc,
                rendered.subject,
                rendered.body,
                rendered.attachment_path,
            )

        def get_contacts(self, query: str = "") -> dict[str, object]:
            result = outlook_client.get_contacts()
            # Off-Windows the client returns the dev fallback contact; never filter
            # it away (Req 8.7). Filter real contacts only on Windows.
            if not query or not result.get("ok") or not outlook_client.IS_WINDOWS:
                return result
            data = result.get("data") or {}
            contacts = data.get("contacts", []) if isinstance(data, dict) else []
            needle = query.casefold()
            filtered = [
                contact
                for contact in contacts
                if needle in str(contact.get("name", "")).casefold()
                or needle in str(contact.get("email", "")).casefold()
            ]
            return ok({"contacts": filtered})

        def download_emails(
            self,
            project_path: Path,
            cr_number: str = "",
            project_name: str = "",
        ) -> dict[str, object]:
            path = Path(project_path)
            if not outlook_client.IS_WINDOWS:
                # Dev-skipped off-Windows: no COM, no worker started (Req 8.8).
                message = f"[DEV] Would download Outlook reply emails for {path}"
                return ok({"status": "dev_skipped", "message": message})
            # Windows path (manual-tested): derive identifiers from metadata when
            # not supplied, then start the guarded background download job.
            if not cr_number or not project_name:
                metadata = self._metadata_store.read(path)
                if metadata is not None:
                    if not project_name:
                        project_name = metadata.project_name or path.name
                    if not cr_number:
                        cr_number = extract_cr_number(metadata.cr_link) or ""
            job_id = self._download_email_service.start_job(cr_number, project_name, path)
            return ok({"status": "started", "job_id": job_id})

    # ── teams service adapter (TeamsService + guarded teams_client) ────
    class _TeamsServiceAdapter:
        """Teams automation adapter (Preview_First, opt-in auto-send, layered).

        Builds a ``TeamsMessage`` from the bridge args (message text plus optional
        target/mentions) and delegates to ``TeamsService`` (``services ->
        infrastructure``). Preview is always Preview_First (deep link + clipboard,
        no keystroke; Req 9.1). For send, the adapter reads ``teams_auto_send`` and
        ``countdown_seconds`` from ``AppSettings.teams`` so auto-send only ever runs
        on an explicit opt-in after a visible countdown (Req 9.2-9.4); when
        disabled it behaves as Preview_First. Off-Windows the underlying client is
        dev-skipped and no ``pyautogui``/``pyperclip`` runs (Req 9.6). Runtime
        failures surface as ``ok=false`` with settings/draft unchanged (Req 9.7).
        """

        def __init__(
            self,
            settings_store: SettingsStore,
            teams_service: TeamsService,
        ) -> None:
            self._settings_store = settings_store
            self._teams_service = teams_service

        @staticmethod
        def _build_message(
            message: str,
            target_email: str,
            target_group: str,
            mentions: list[str] | None,
        ) -> TeamsMessage:
            return TeamsMessage(
                target_email=str(target_email or ""),
                target_group=str(target_group or ""),
                mentions=[str(item) for item in (mentions or [])],
                message=str(message or ""),
            )

        def preview_message(
            self,
            message: str,
            *,
            target_email: str = "",
            target_group: str = "",
            mentions: list[str] | None = None,
        ) -> dict[str, object]:
            teams_message = self._build_message(
                message, target_email, target_group, mentions
            )
            return self._teams_service.preview_message(teams_message)

        def send_message(
            self,
            message: str,
            *,
            target_email: str = "",
            target_group: str = "",
            mentions: list[str] | None = None,
        ) -> dict[str, object]:
            settings = self._settings_store.read()
            teams_settings = settings.teams
            teams_message = self._build_message(
                message, target_email, target_group, mentions
            )
            return self._teams_service.send_message(
                teams_message,
                teams_auto_send=teams_settings.teams_auto_send,
                countdown_seconds=teams_settings.countdown_seconds,
            )

    # ── rules adapter (settings-backed CRUD + cache-backed log retrieval) ──
    class _RulesAdapter:
        """Persist rules under ``settings.automation.rules_engine["rules"]``.

        Provides CRUD over rule dicts (Req 11.1/11.2) and a ``get_logs`` helper
        that filters the durable ``automation_rule_logs`` cache by rule id and
        returns the most recent ``limit`` entries. Validation rejects incomplete
        or unsupported definitions and leaves the prior persisted state unchanged.
        """

        SUPPORTED_ACTIONS = {
            "download_email",
            "save_attachment",
            "update_cr_state",
            "update_drone_state",
            "send_outlook_email",
            "send_teams_message",
            "in_app_notification",
            "append_history",
        }

        def __init__(self, settings_store: SettingsStore, cache: CacheDb) -> None:
            self._settings_store = settings_store
            self._cache = cache

        # -- helpers -------------------------------------------------
        def _read(self) -> tuple[Any, list[dict[str, object]]]:
            settings = self._settings_store.read()
            store = settings.automation.rules_engine
            if not isinstance(store, dict):
                store = {}
                settings.automation.rules_engine = store
            rules = store.get("rules") or []
            if not isinstance(rules, list):
                rules = []
            return settings, [dict(r) for r in rules]

        def _persist(self, settings: Any, rules: list[dict[str, object]]) -> None:
            store = settings.automation.rules_engine
            if not isinstance(store, dict):
                store = {}
                settings.automation.rules_engine = store
            store["rules"] = rules
            self._settings_store.write(settings)

        @classmethod
        def _validate(cls, rule: dict[str, object]) -> None:
            if not isinstance(rule, dict):
                raise ValueError("Rule must be a mapping")
            name = str(rule.get("name", "")).strip()
            if not name:
                raise ValueError("Rule name is required")
            actions = rule.get("actions") or []
            if not isinstance(actions, list):
                raise ValueError("Rule actions must be a list")
            for action in actions:
                if not isinstance(action, dict):
                    raise ValueError("Each action must be a mapping")
                action_type = action.get("type")
                if action_type not in cls.SUPPORTED_ACTIONS:
                    raise ValueError(f"Unsupported action type: {action_type!r}")

        def _index_of(self, rules: list[dict[str, object]], rule_id: str) -> int:
            for i, rule in enumerate(rules):
                if str(rule.get("id", "")) == rule_id:
                    return i
            raise ValueError(f"Rule not found: {rule_id}")

        # -- provider for AutomationService --------------------------
        def list_rules(self) -> list[dict[str, object]]:
            _, rules = self._read()
            return rules

        # -- CRUD ----------------------------------------------------
        def create(self, data: dict[str, object]) -> dict[str, object]:
            payload = dict(data)
            if not payload.get("id"):
                import uuid

                payload["id"] = str(uuid.uuid4())
            payload.setdefault("enabled", True)
            payload.setdefault("conditions", [])
            payload.setdefault("actions", [])
            self._validate(payload)
            settings, rules = self._read()
            if any(str(r.get("id", "")) == payload["id"] for r in rules):
                raise ValueError(f"Rule already exists: {payload['id']}")
            rules.append(payload)
            self._persist(settings, rules)
            return payload

        def update(self, rule_id: str, data: dict[str, object]) -> dict[str, object]:
            settings, rules = self._read()
            index = self._index_of(rules, rule_id)
            merged = {**rules[index], **dict(data), "id": rule_id}
            self._validate(merged)
            rules[index] = merged
            self._persist(settings, rules)
            return merged

        def delete(self, rule_id: str) -> None:
            settings, rules = self._read()
            index = self._index_of(rules, rule_id)
            del rules[index]
            self._persist(settings, rules)

        def toggle(self, rule_id: str, enabled: bool) -> dict[str, object]:
            settings, rules = self._read()
            index = self._index_of(rules, rule_id)
            rules[index] = {**rules[index], "enabled": bool(enabled)}
            self._persist(settings, rules)
            return rules[index]

        def get_logs(self, rule_id: str, limit: int) -> list[dict[str, object]]:
            try:
                rows = self._cache.list_rule_logs()
            except Exception:  # noqa: BLE001 — return empty on cache failure
                return []
            matched = [r for r in rows if getattr(r, "rule_id", None) == rule_id]
            if limit and limit > 0:
                matched = matched[-limit:]
            return [
                {
                    "rule_id": getattr(r, "rule_id", ""),
                    "rule_name": getattr(r, "rule_name", ""),
                    "trigger_type": getattr(r, "trigger_type", ""),
                    "conditions_passed": getattr(r, "conditions_passed", False),
                    "actions_executed": getattr(r, "actions_executed", []),
                    "success": getattr(r, "success", False),
                    "error_message": getattr(r, "error_message", ""),
                    "timestamp": getattr(r, "timestamp", ""),
                }
                for r in matched
            ]

    rules_adapter = _RulesAdapter(_settings_store, cache_db)
    # Re-build automation service so rules CRUD + evaluation share one rule list.
    automation_svc = AutomationService(
        rules_provider=rules_adapter.list_rules,
        cache=cache_db,
        notification_service=notification_svc,
    )

    # ── JsApi ─────────────────────────────────────────────────────────
    _metadata_store = MetadataStore()
    return JsApi(
        dashboard_service=dashboard_svc,
        notification_service=notification_svc,
        report_service=report_svc,
        project_service=_ProjectServiceAdapter(
            dashboard_svc,
            _metadata_store,
            ProjectService(_metadata_store),
            _settings_store,
            cache_db,
            notification_svc,
        ),
        settings_store=_SettingsAdapter(_settings_store),
        linkbank_store=_LinkBankAdapter(_linkbank_store),
        automation_service=automation_svc,
        rules_service=rules_adapter,
        second_brain_service=second_brain_svc,
        scheduler_service=scheduler_svc,
        year_service=_YearServiceAdapter(_settings_store),
        file_service=_FileServiceAdapter(_settings_store, SafeDeleteService()),
        notes_service=_NotesServiceAdapter(),
        outlook_service=_OutlookServiceAdapter(
            _settings_store,
            _metadata_store,
            EmailService(),
            DownloadEmailService(notification_service=notification_svc),
        ),
        teams_service=_TeamsServiceAdapter(
            _settings_store,
            TeamsService(),
        ),
    )


def get_frontend_entry_path(*, project_root: Path = PROJECT_ROOT) -> Path:
    """Return production Svelte frontend entry path."""
    entry_path = project_root / "web" / "static" / "index.html"
    if not entry_path.is_file():
        raise FileNotFoundError(
            f"Built Svelte frontend not found: {entry_path}. Run `npm run build` from frontend/."
        )
    return entry_path


def resolve_frontend_url(*, dev: bool = False, project_root: Path = PROJECT_ROOT) -> str:
    """Return frontend URL/path for dev or production pywebview startup."""
    if dev:
        return VITE_DEV_SERVER_URL
    get_frontend_entry_path(project_root=project_root)
    return "web/static/index.html"


def run(*, dev: bool = False, start_webview: bool = True) -> None:
    """Create webview window and start pywebview on main thread."""
    webview.create_window(
        "Project Tracker DBS",
        url=resolve_frontend_url(dev=dev),
        js_api=create_js_api(),
        width=1200,
        height=760,
        min_size=(960, 640),
    )
    if start_webview:
        webview.start(http_server=True)


if __name__ == "__main__":
    run(dev="--dev" in sys.argv)
