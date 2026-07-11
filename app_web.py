"""pywebview application bootstrap for the HTML/Tailwind frontend."""

from __future__ import annotations

import base64
import hashlib
import json
import sys
import tempfile
import uuid
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

# pywebview is imported lazily in run() so app_web stays importable headless
# (tests/CI have no window). Tests patch app_web.webview, so keep it a module attr.
webview = None

from core.enums import CRState, DroneState, NonCrState, ProjectState, ProjectType
from core.models import AppCodeConfig, AppSettings, DroneTicket, ProjectMetadata, local_now
from core.rules import TransitionGuardResult, extract_cr_number, extract_drone_ticket
from infrastructure.cache_db import CacheDb, rebuild_year_cache
from infrastructure import app_logger, filesystem, outlook_client
from infrastructure.filesystem import (
    create_directory,
    create_file,
    create_file_from_template,
    discover_drone_paths,
    discover_subproject_paths,
    ensure_appcode_year_structure,
    rename_file,
)
from infrastructure.link_bank_store import LinkBankStore
from infrastructure.metadata_store import MetadataStore
from infrastructure.settings_store import SettingsStore, app_config_dir
from services.automation_service import AutomationService
from services.approval_polling_service import ApprovalPollingService, register_approval_polling_service
from services.dashboard_service import DashboardService
from services.download_email_service import DownloadEmailService
from services.email_service import (
    EmailService,
    TemplateConditionsNotMetError,
    UnresolvedPlaceholderError,
)
from services.notification_service import NotificationService
from services.project_service import ProjectService
from services.report_service import ReportService
from services.scheduler_service import SchedulerService
from services.second_brain_service import SecondBrainItem, SecondBrainService
from services.teams_service import TeamsMessage, TeamsService
from web.js_api import JsApi, fail, ok


def _runtime_project_root() -> Path:
    """Return project root in source runs and PyInstaller-frozen runs."""
    if getattr(sys, "frozen", False):
        bundle_root = getattr(sys, "_MEIPASS", None)
        if bundle_root:
            return Path(bundle_root).resolve()
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


PROJECT_ROOT = _runtime_project_root()
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


def _atomic_write_text(path: Path, content: str) -> None:
    """Write UTF-8 text through a sibling temp file then atomic replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp")
    try:
        temp_path.write_text(content, encoding="utf-8")
        temp_path.replace(path)
    except Exception:
        try:
            temp_path.unlink()
        except OSError:
            pass
        raise


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


def _appcode_from_project_path(path: Path) -> str:
    parts = list(Path(path).parts)
    for marker in ("CR", "Non-CR"):
        if marker in parts:
            index = parts.index(marker)
            return parts[index - 2] if index >= 2 else ""
    return ""


# Slice 3: pre-seeded rules (DISABLED by default — user must enable).
_PRESEEDED_RULES: list[dict[str, object]] = [
    {
        "name": "Send UAT Acknowledgement",
        "goal": "send_email",
        "trigger": {"type": "manual"},
        "actions": [{"type": "send_outlook_email", "params": {"template_id": "uat_approval"}}],
    },
    {
        "name": "Send LV Acknowledgement",
        "goal": "send_email",
        "trigger": {"type": "manual"},
        "actions": [{"type": "send_outlook_email", "params": {"template_id": "lv_approval"}}],
    },
    {
        "name": "Auto Update CR State",
        "goal": "auto_update_status",
        # DEFAULT AMAN: no patterns configured → engine no-ops (Slice 4).
        "trigger": {"type": "email_received"},
        "actions": [{"type": "update_cr_state"}],
    },
]


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

    class _LiveDashboardService:
        def __init__(self, dashboard: DashboardService, cache: CacheDb, settings_store: SettingsStore, metadata_store: MetadataStore) -> None:
            self._dashboard = dashboard
            self._cache = cache
            self._settings_store = settings_store
            self._metadata_store = metadata_store

        def _rebuild(self, year: str | None = None) -> None:
            settings = self._settings_store.read()
            root = settings.root_folder
            if root is None or not root.exists():
                return
            appcodes = [p for p in root.iterdir() if p.is_dir()]
            for appcode_path in appcodes:
                years = [str(year)] if year and str(year) != "all" else [p.name for p in appcode_path.iterdir() if p.is_dir() and p.name.isdigit()]
                for year_name in years:
                    rebuild_year_cache(self._cache, appcode_path / year_name, self._metadata_store)

        def list_projects(self, year: str | None = None, appcode: str | None = None) -> object:
            self._rebuild(year)
            return self._dashboard.list_projects(year, appcode)

        def get_summary(self, year: str | None = None, appcode: str | None = None) -> object:
            self._rebuild(year)
            return self._dashboard.get_summary(year, appcode)

        def get_dashboard(self, year: str | None = None, appcode: str | None = None) -> object:
            self._rebuild(year)
            return self._dashboard.get_dashboard(year, appcode)

    # ── services ─────────────────────────────────────────────────────
    _metadata_store = MetadataStore()
    raw_dashboard_svc = _dashboard_service or DashboardService(cache=cache_db)
    dashboard_svc = raw_dashboard_svc if _dashboard_service is not None else _LiveDashboardService(raw_dashboard_svc, cache_db, _settings_store, _metadata_store)
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
        project_provider=lambda: dashboard_svc.list_projects(),
    )
    second_brain_svc = SecondBrainService(
        items_provider=_second_brain_items_provider,
        folder_provider=lambda: _settings_store.read().second_brain_folder,
    )
    email_svc = EmailService()
    approval_svc = ApprovalPollingService(
        settings_store=_settings_store,
        metadata_store=_metadata_store,
        email_service=email_svc,
        cache=cache_db,
        notification_service=notification_svc,
    )
    approval_svc.resume_pending()
    register_approval_polling_service(approval_svc)

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
            for key in ("name", "url", "notes", "details", "tags", "category", "archived", "pinned", "favorite"):
                if key in data:
                    target[key] = str(data[key])
            if "details" in data and "notes" not in data:
                target["notes"] = str(data["details"])
            if "notes" in data and "details" not in data:
                target["details"] = str(data["notes"])
            old_category = target.get("category", "")
            if old_category and old_category not in bank.categories:
                bank.categories.append(old_category)
            self._store.write(bank)
            return dict(target)

        def add_link(self, data: dict[str, object]) -> object:
            """Create a new link with a stable uuid id and persist it."""
            name = str(data.get("name", data.get("title", ""))).strip()
            url = str(data.get("url", "")).strip()
            if not name or not url:
                raise ValueError("Link name and url are required")
            parsed_url = urlparse(url)
            if parsed_url.scheme not in {"http", "https"}:
                raise ValueError("Link url must use http or https")
            details = str(data.get("details", data.get("notes", "")))
            bank = self._store.read()
            link = {
                "id": uuid.uuid4().hex,
                "name": name,
                "url": url,
                "notes": details,
                "details": details,
                "tags": str(data.get("tags", "")),
                "category": str(data.get("category", "")),
                "archived": "false",
                "pinned": str(data.get("pinned", "false")).lower(),
                "favorite": str(data.get("favorite", "false")).lower(),
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

        def category_create(self, name: str) -> object:
            category = str(name).strip()
            if not category:
                raise ValueError("Category name is required")
            bank = self._store.read()
            if category not in bank.categories:
                bank.categories.append(category)
            self._store.write(bank)
            return bank.to_dict()

        def category_rename(self, old_name: str, new_name: str) -> object:
            old = str(old_name).strip()
            new = str(new_name).strip()
            if not old or not new:
                raise ValueError("Old and new category names are required")
            bank = self._store.read()
            bank.categories = [new if cat == old else cat for cat in bank.categories]
            for link in bank.links:
                if link.get("category") == old:
                    link["category"] = new
            if new not in bank.categories:
                bank.categories.append(new)
            self._store.write(bank)
            return bank.to_dict()

        def category_archive(self, name: str) -> object:
            category = str(name).strip()
            if not category:
                raise ValueError("Category name is required")
            bank = self._store.read()
            for link in bank.links:
                if link.get("category") == category:
                    link["archived"] = "true"
            bank.categories = [cat for cat in bank.categories if cat != category]
            self._store.write(bank)
            return bank.to_dict()

        def export_json(self) -> object:
            return self._store.read().to_dict()

        def import_json(self, data: dict[str, object]) -> object:
            from infrastructure.link_bank_store import LinkBank

            bank = LinkBank.from_dict(data)
            self._store.write(bank)
            return bank.to_dict()

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

        def list_projects(self, year: str | None = None, appcode: str | None = None) -> object:
            return self._dashboard.list_projects(year, appcode)

        def _evaluate_h10_reminders(self, project_paths: list[Path]) -> None:
            """Emit/dedup/re-arm H-10 reminders for the visible projects.

            Called on dashboard load. For each project:
            - if past H-10 with CR/Drone not APPROVED and no prior stamp, emit one
              notification, append a history entry, and stamp ``h10_notified_at``;
            - if the condition has resolved but a stamp remains, clear it (re-arm);
            - otherwise leave the project untouched.

            Settings are read once for the whole batch.
            """
            from core.models import HistoryEntry
            from core.rules import current_user, h10_reminder_due

            if self._notification_service is None:
                return
            settings = self._settings_store.read()
            now = local_now()
            for path in project_paths:
                try:
                    metadata = self._metadata_store.read(path)
                    if metadata is None:
                        continue
                    due = h10_reminder_due(
                        metadata, now=now, reminder_days=settings.h10_reminder_days
                    )
                    if due and metadata.h10_notified_at is None:
                        self._notification_service.add(
                            type="H10_REMINDER",
                            title="H-10 cutoff passed",
                            message=(
                                f"{path.name}: H-10 cutoff passed — CR/Drone not yet "
                                "APPROVED. Change start date or request management approval."
                            ),
                            project_path=path,
                        )
                        metadata.history.append(
                            HistoryEntry(
                                timestamp=now,
                                action="H10_REMINDER",
                                detail="H-10 cutoff passed; CR/Drone not yet APPROVED",
                                user=current_user(settings),
                            )
                        )
                        metadata.h10_notified_at = now
                        self._metadata_store.write(path, metadata)
                    elif not due and metadata.h10_notified_at is not None:
                        metadata.h10_notified_at = None
                        self._metadata_store.write(path, metadata)
                except Exception:  # noqa: BLE001 - one bad project must not skip the batch
                    continue

        # ── wired read methods ──

        def get_project(self, project_path: Path) -> object:
            """Return project detail from MetadataStore + filesystem."""
            path = Path(project_path)
            metadata = self._metadata_store.read(path)
            if metadata is None:
                raise FileNotFoundError(f"Project metadata not found: {path}")

            raw_project_type = getattr(metadata, "project_type", None) or filesystem.project_type_from_path(path)
            project_type = raw_project_type if isinstance(raw_project_type, ProjectType) else ProjectType(str(raw_project_type))
            is_non_cr = project_type == ProjectType.NON_CR
            project_state = None if is_non_cr else (_folder_state_for_path(path) or ProjectState.UAT_PREPARE)

            # Sub-project detection: parent contains project_data.json. Non-CR projects are never drones.
            is_subproject = (not is_non_cr) and (path.parent / "project_data.json").is_file()

            if is_subproject:
                parent_path = path.parent
                parent_meta = self._metadata_store.read(parent_path)
                if parent_meta:
                    metadata.cr_link = parent_meta.cr_link
                    metadata.cr_state = parent_meta.cr_state
                    metadata.start_datetime = parent_meta.start_datetime
                    metadata.end_datetime = parent_meta.end_datetime
                drone_tickets = []
                drone_paths = []
            elif is_non_cr:
                drone_tickets = []
                drone_paths = []
            else:
                drone_tickets = getattr(metadata, "drone_tickets", None) or []
                drone_paths = discover_drone_paths(path)

            cr_number = extract_cr_number(metadata.cr_link)
            drone_names = [p.name for p in drone_paths]
            project_state_value = project_state.value if project_state is not None else None

            return {
                "project_name": metadata.project_name or path.name,
                "project_path": str(path),
                "project_state": project_state_value,
                "appcode": _appcode_from_project_path(path),
                "project_type": project_type.value,
                "non_cr_state": metadata.non_cr_state.value if metadata.non_cr_state else None,
                "drones": drone_names,
                "drone_paths": [str(p) for p in drone_paths],
                "cr_number": cr_number or "",
                "cr_link": metadata.cr_link or "",
                "cr_state": metadata.cr_state.value,
                "start_datetime": metadata.start_datetime,
                "end_datetime": metadata.end_datetime,
                "t10_status": "N/A",
                "drone_ticket_count": len(drone_tickets),
                "implementation_plan": metadata.implementation_plan,
                "history": [entry.to_dict() for entry in metadata.history] if not is_subproject else [],
                "drone_tickets": [
                    {
                        "subfolder_name": t.subfolder_name,
                        "drone_link": t.drone_link,
                        "drone_ticket": extract_drone_ticket(t.drone_link) or "",
                        "drone_state": t.drone_state.value,
                        "owner": t.owner,
                    }
                    for t in drone_tickets
                ],
                "is_subproject": is_subproject,
                "subprojects": drone_names,
            }

        def list_drones(self, project_path: Path) -> object:
            """Return drone folder names under project_path."""
            return [p.name for p in discover_drone_paths(Path(project_path))]

        def list_subprojects(self, project_path: Path) -> object:
            """Backward-compatible alias for list_drones."""
            return self.list_drones(project_path)

        # ── wired mutation: update_cr_link (metadata-only) ──

        def update_cr_link(self, project_path: Path, cr_link: str) -> object:
            """Update CR link in metadata and persist."""
            from core.models import HistoryEntry
            from core.rules import current_user

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
            project_state = _folder_state_for_path(path) or ProjectState.UAT_PREPARE
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
            from core.models import DroneTicket

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
            now = local_now()
            state_changed = False
            if "drone_link" in data:
                next_link = str(data["drone_link"])
                if next_link != ticket.drone_link:
                    ticket.drone_link = next_link
                    if ticket.drone_state != DroneState.UAT:
                        ticket.drone_state = DroneState.UAT
                        ticket.drone_state_updated_at = now
                        ticket.previous_drone_state_before_canceled = None
                        state_changed = True
                else:
                    ticket.drone_link = next_link
            if "owner" in data:
                ticket.owner = str(data["owner"])
            if "subfolder_name" in data:
                ticket.subfolder_name = str(data["subfolder_name"]) or None
            if "drone_state" in data:
                from core.models import HistoryEntry
                from core.rules import current_user
                from core.state_machine import validate_drone_state_change_allowed

                target = DroneState(str(data["drone_state"]))
                if target == DroneState.CANCELED and metadata.cr_state != CRState.CANCELED:
                    raise ValueError("Drone state cannot be CANCELED while CR state is not CANCELED")
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

        def delete_drone_ticket(self, project_path: Path, drone_index: int) -> object:
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
            from core.models import HistoryEntry
            from core.rules import (
                current_user,
                validate_cr_approved_requires_drones,
            )
            from core.state_machine import validate_cr_transition

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
            project_state = _folder_state_for_path(path) or ProjectState.UAT_PREPARE
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

            is_subproject = (path.parent / "project_data.json").is_file()

            if "project_name" in data:
                metadata.project_name = str(data["project_name"])
            if "implementation_plan" in data:
                metadata.implementation_plan = str(data["implementation_plan"])

            # If dates or CR details are updated on a sub-project, propagate to parent
            if is_subproject:
                parent_path = path.parent
                parent_meta = self._metadata_store.read(parent_path)
                if parent_meta:
                    if "cr_link" in data:
                        parent_meta.cr_link = str(data["cr_link"])
                    if "start_datetime" in data:
                        parent_meta.start_datetime = _parse_optional_datetime(data["start_datetime"])
                    if "end_datetime" in data:
                        parent_meta.end_datetime = _parse_optional_datetime(data["end_datetime"])
                    parent_meta.updated_at = local_now()
                    self._metadata_store.write(parent_path, parent_meta)
            else:
                if "cr_link" in data:
                    metadata.cr_link = str(data["cr_link"])
                if "start_datetime" in data:
                    metadata.start_datetime = _parse_optional_datetime(data["start_datetime"])
                if "end_datetime" in data:
                    metadata.end_datetime = _parse_optional_datetime(data["end_datetime"])

            metadata.updated_at = local_now()
            self._metadata_store.write(path, metadata)

            project_state = _folder_state_for_path(path) or ProjectState.UAT_PREPARE
            return {
                "project_path": str(path),
                "project_name": metadata.project_name or path.name,
                "project_state": project_state.value,
                "cr_state": metadata.cr_state.value,
            }

        # ── wired mutation: create_project (folder + initial metadata) ──

        def create_project(self, data: dict[str, object]) -> object:
            """Create a project folder under {root}/{year}/UAT_PREPARE/{name}."""
            from core.rules import validate_windows_folder_name

            name = str(data.get("project_name", "")).strip()
            if not name:
                raise ValueError("Project name is required")
            validate_windows_folder_name(name)

            year = str(data.get("year", "")).strip() or str(local_now().year)
            settings = _settings_store.read()
            if settings.root_folder is None:
                raise ValueError("Root folder is not configured")

            appcode_name = str(data.get("appcode", "")).strip()
            project_type_str = str(data.get("project_type", "CR")).strip()
            if not appcode_name:
                raise ValueError("Appcode is required")
            # Optional Piece A fields. Drone is lazy (created later in Project Details),
            # so any legacy drone_name from old callers is ignored.
            start_dt = _parse_optional_datetime(data.get("start_datetime"))
            end_dt = _parse_optional_datetime(data.get("end_datetime"))
            cr_link = str(data.get("cr_link", "")).strip()
            implementation_plan = str(data.get("implementation_plan", "")).strip()
            appcode_path = settings.root_folder / appcode_name
            appcode_path.mkdir(parents=True, exist_ok=True)
            year_path = appcode_path / year
            project_type = ProjectType(project_type_str)
            if project_type == ProjectType.CR:
                ensure_appcode_year_structure(appcode_path, int(year))
                project_dir = year_path / "CR" / "UAT_PREPARE" / name
                if project_dir.exists():
                    raise ValueError(f"Project folder already exists: {project_dir}")
                project_dir.mkdir(parents=True)
                now = local_now()
                metadata = ProjectMetadata(
                    project_name=name,
                    project_type=ProjectType.CR,
                    created_at=now,
                    updated_at=now,
                    start_datetime=start_dt,
                    end_datetime=end_dt,
                    cr_link=cr_link,
                    implementation_plan=implementation_plan,
                )
                (project_dir / "notes.md").touch()
                (project_dir / "_cr-docs").mkdir()
                self._metadata_store.write(project_dir, metadata)
                return {"project_path": str(project_dir), "project_name": name, "project_state": "UAT_PREPARE", "project_type": "CR", "cr_state": metadata.cr_state.value}
            else:
                ensure_appcode_year_structure(appcode_path, int(year))
                project_dir = year_path / "Non-CR" / name
                if project_dir.exists():
                    raise ValueError(f"Project folder already exists: {project_dir}")
                project_dir.mkdir(parents=True)
                now = local_now()
                metadata = ProjectMetadata(
                    project_name=name,
                    project_type=ProjectType.NON_CR,
                    non_cr_state=NonCrState.PLANNING,
                    created_at=now,
                    updated_at=now,
                    start_datetime=start_dt,
                    end_datetime=end_dt,
                )
                (project_dir / "notes.md").touch()
                self._metadata_store.write(project_dir, metadata)
                return {"project_path": str(project_dir), "project_name": name, "project_type": "NON_CR", "non_cr_state": "PLANNING"}

        # ── wired mutation: folder state transitions (guarded + rollback) ──

        def _rebuild_cache_for(self, moved_path: Path) -> None:
            """Rebuild the year cache after a successful transition (Req 4.11)."""
            year_path = moved_path.parent.parent.parent if moved_path.parent.parent.name == "CR" else moved_path.parent.parent
            rebuild_year_cache(self._cache_db, year_path, self._metadata_store)

        def set_non_cr_state(self, project_path: Path, target_state: str) -> object:
            """Set Non-CR state and rebuild appcode/year cache."""
            path = Path(project_path)
            moved = self._project_service.set_non_cr_state(
                path,
                NonCrState(str(target_state)),
                self._settings_store.read(),
            )
            self._rebuild_cache_for(moved)
            metadata = self._metadata_store.read(moved)
            return {
                "project_path": str(moved),
                "project_type": "NON_CR",
                "non_cr_state": metadata.non_cr_state.value if metadata and metadata.non_cr_state else None,
            }

        def _run_transition(
            self,
            project_path: object,
            service_call: Callable[[AppSettings], object],
        ) -> object:
            """Execute a transition, map guard blocks, and update cache on success.

            - Loads ``AppSettings`` and invokes ``service_call``.
            - A blocked ``TransitionGuardResult`` raises with joined reasons so the
              JsApi facade returns ``ok=false`` (Req 4.9).
            - On success the Cache_Db is rebuilt before returning (Req 4.11). Any
              exception during the physical move propagates without a cache update,
              leaving the prior state and returning ``ok=false`` (Req 4.12).
            """
            settings = self._settings_store.read()
            result = service_call(settings)

            if isinstance(result, TransitionGuardResult) and not result.allowed:
                raise ValueError("; ".join(result.failed_guards))

            moved_path = Path(str(result))
            self._rebuild_cache_for(moved_path)
            project_state = _folder_state_for_path(moved_path) or ProjectState.UAT_PREPARE
            # Slice 5: retention — purge automation_logs when CR reaches a
            # terminal state (FINISHED/CANCELED). POSTPONED is reversible so we
            # keep its logs. Swallow errors: retention must never block a move.
            try:
                metadata_after = self._metadata_store.read(moved_path)
                if metadata_after is not None and metadata_after.cr_state in (
                    CRState.FINISHED,
                    CRState.CANCELED,
                ):
                    cr_id = extract_cr_number(metadata_after.cr_link) or metadata_after.project_name
                    if cr_id:
                        self._cache_db.purge_logs_for_cr(cr_id)
            except Exception:  # noqa: BLE001
                pass
            return {
                "project_path": str(moved_path),
                "project_state": project_state.value,
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
            from core.state_machine import resolve_auto_move
            from web.event_queue import push_event

            path = Path(project_path)
            metadata = self._metadata_store.read(path)
            if metadata is None:
                return None
            current_folder = _folder_state_for_path(path) or ProjectState.UAT_PREPARE
            drone_states = [t.drone_state for t in metadata.drone_tickets]
            target = resolve_auto_move(metadata.cr_state, drone_states, current_folder)
            if target is None:
                return None

            if target == ProjectState.IMPLEMENTED:
                from core.state_machine import drones_blocking_finish

                blocked = drones_blocking_finish(drone_states)
                if blocked:
                    return {"banner": (
                        f"{blocked} drone(s) cannot auto-finish (illegal state). "
                        "Move to IMPLEMENTED blocked."
                    )}

            settings = self._settings_store.read()
            if target == ProjectState.PROD_READY:
                result = self._project_service.move_to_prod_ready(
                    path,
                    settings,
                    local_now(),
                    settings.t10_threshold_days,
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

        def move_to_prod_ready(self, project_path: Path) -> object:
            return self._run_transition(
                project_path,
                lambda settings: self._project_service.move_to_prod_ready(
                    Path(project_path),
                    settings,
                    local_now(),
                    settings.t10_threshold_days,
                ),
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
            state = _folder_state_for_path(Path(project_path))
            if state is None:
                return ProjectState.UAT_PREPARE
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
            project_state = _folder_state_for_path(moved_path) or ProjectState.UAT_PREPARE
            return {
                "project_path": str(moved_path),
                "project_name": new_name,
                "project_state": project_state.value,
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
            year_path = path.parent.parent.parent if path.parent.parent.name == "CR" else path.parent.parent
            self._project_service.delete_project(path)
            rebuild_year_cache(self._cache_db, year_path, self._metadata_store)
            return {"project_path": str(path), "deleted": True}

        def delete_drone(self, project_path: Path, drone: int | str) -> object:
            """Delete a drone ticket by index or a drone folder by name."""
            if isinstance(drone, int):
                return self.delete_drone_ticket(project_path, drone)
            project = Path(project_path)
            drone_name = str(drone)
            drone_path = project / drone_name
            self._project_service.delete_drone(drone_path)
            metadata = self._metadata_store.read(project)
            if metadata is not None:
                metadata.drone_tickets = [
                    ticket
                    for ticket in metadata.drone_tickets
                    if (ticket.subfolder_name or "") != drone_name
                ]
                metadata.updated_at = local_now()
                self._metadata_store.write(project, metadata)
            self._rebuild_cache_for(project)
            return {"project_path": str(project), "drone": drone_name, "deleted": True}

        def delete_subproject(self, project_path: Path, name: str) -> object:
            """Backward-compatible alias for delete_drone."""
            return self.delete_drone(project_path, name)

        def open_folder(self, project_path: Path) -> object:
            """Open a project folder through the infrastructure helper."""
            path = Path(project_path)
            filesystem.open_folder(path)
            return {"project_path": str(path), "opened": True}

        def create_drone(self, project_path: Path, name: str) -> object:
            """Create a drone folder (UAT/PRD/notes.md) inside the project."""
            from infrastructure.filesystem import _scaffold_drone
            project = Path(project_path)
            metadata = self._metadata_store.read(project)
            if metadata is None:
                raise FileNotFoundError(f"Project metadata not found: {project}")
            drone_path = _scaffold_drone(project, name)
            if any((ticket.subfolder_name or "") == drone_path.name for ticket in metadata.drone_tickets):
                raise ValueError(f"Drone ticket already exists: {drone_path.name}")
            metadata.drone_tickets.append(DroneTicket(subfolder_name=drone_path.name))
            metadata.updated_at = local_now()
            self._metadata_store.write(project, metadata)
            self._rebuild_cache_for(project)
            return {
                "project_path": str(project),
                "drone": drone_path.name,
                "path": str(drone_path),
            }

    # ── appcode service adapter (SettingsStore → appcode folders) ─────
    class _AppCodeServiceAdapter:
        """Appcode adapter backed by {root}/{appcode}/appcode.json."""

        def __init__(self, settings_store: SettingsStore) -> None:
            self._settings_store = settings_store

        def _root(self) -> Path:
            root = self._settings_store.read().root_folder
            if root is None:
                raise ValueError("Root folder is not configured")
            root.mkdir(parents=True, exist_ok=True)
            return root

        @staticmethod
        def _payload(entry: filesystem.AppCodeEntry) -> dict[str, object]:
            config = entry.config
            return {
                "name": entry.name,
                "path": str(entry.path),
                "display_name": config.display_name or entry.name,
                "cicd_location": config.cicd_location,
                "cicd_shared_path": str(config.cicd_shared_path) if config.cicd_shared_path else None,
            }

        def _appcode_path(self, appcode: str) -> Path:
            name = str(appcode).strip()
            if not name:
                raise ValueError("Appcode is required")
            from core.rules import validate_windows_folder_name

            validate_windows_folder_name(name)
            return self._root() / name

        def list_appcodes(self) -> object:
            return [self._payload(entry) for entry in filesystem.discover_appcodes(self._root())]

        def add_appcode(self, name: str) -> object:
            appcode_path = self._appcode_path(name)
            if appcode_path.exists() and (appcode_path / "appcode.json").exists():
                raise ValueError(f"Appcode already exists: {appcode_path.name}")
            appcode_path.mkdir(parents=True, exist_ok=True)
            (appcode_path / "CICD").mkdir(exist_ok=True)
            ensure_appcode_year_structure(appcode_path, local_now().year)
            config = AppCodeConfig(display_name=appcode_path.name, created_at=local_now())
            (appcode_path / "appcode.json").write_text(
                json.dumps(config.to_dict(), indent=2),
                encoding="utf-8",
            )
            return self._payload(filesystem.AppCodeEntry(path=appcode_path, name=appcode_path.name, config=config))

        def remove_appcode(self, name: str) -> object:
            root = self._root()
            appcode_path = self._appcode_path(name)
            if not appcode_path.exists():
                raise FileNotFoundError(f"Appcode not found: {appcode_path.name}")
            filesystem.send_to_recycle_bin(appcode_path, base=root)
            return {"name": appcode_path.name, "path": str(appcode_path), "deleted": True}

        def get_appcode_config(self, appcode: str) -> object:
            appcode_path = self._appcode_path(appcode)
            config_path = appcode_path / "appcode.json"
            if config_path.is_file():
                config = AppCodeConfig.from_dict(json.loads(config_path.read_text(encoding="utf-8")))
            elif appcode_path.is_dir():
                # ponytail: folder made manually on disk (e.g. SSID: year subfolder, no
                # appcode.json) still lists in discover_appcodes — synthesize the same
                # default here instead of raising, so selecting it doesn't error.
                config = AppCodeConfig(display_name=appcode_path.name)
            else:
                raise FileNotFoundError(f"Appcode not found: {appcode_path.name}")
            return self._payload(filesystem.AppCodeEntry(path=appcode_path, name=appcode_path.name, config=config))

        def update_appcode_config(self, appcode: str, data: dict[str, object]) -> object:
            appcode_path = self._appcode_path(appcode)
            config_path = appcode_path / "appcode.json"
            current = AppCodeConfig()
            if config_path.is_file():
                current = AppCodeConfig.from_dict(json.loads(config_path.read_text(encoding="utf-8")))
            if "display_name" in data:
                current.display_name = str(data.get("display_name") or "").strip() or appcode_path.name
            if "cicd_location" in data:
                current.cicd_location = str(data.get("cicd_location") or "per_appcode")
            if "cicd_shared_path" in data:
                shared = str(data.get("cicd_shared_path") or "").strip()
                current.cicd_shared_path = Path(shared) if shared else None
            config_path.write_text(json.dumps(current.to_dict(), indent=2), encoding="utf-8")
            return self._payload(filesystem.AppCodeEntry(path=appcode_path, name=appcode_path.name, config=current))

    # ── cicd service adapter (git clone + repo browse) ────────────────
    class _CicdServiceAdapter:
        """Resolve each appcode's CICD dir (reusing appcode config) then
        delegate git work to CicdService. per_appcode -> {appcode}/CICD;
        shared_root -> AppCodeConfig.cicd_shared_path."""

        def __init__(self, appcode_adapter, service) -> None:
            self._appcode = appcode_adapter
            self._service = service

        def _cicd_dir(self, appcode: str) -> Path:
            config = self._appcode.get_appcode_config(appcode)
            return self._cicd_dir_from_config(config)

        @staticmethod
        def _cicd_dir_from_config(config: dict[str, object]) -> Path:
            if config.get("cicd_location") == "shared_root":
                shared = config.get("cicd_shared_path")
                if not shared:
                    raise ValueError("Shared CICD path is not configured for this appcode")
                cicd_dir = Path(str(shared))
            else:
                cicd_dir = Path(str(config["path"])) / "CICD"
            cicd_dir.mkdir(parents=True, exist_ok=True)
            return cicd_dir

        def preview_link(self, clone_url: str) -> object:
            from services.cicd_service import parse_clone_url

            info = parse_clone_url(clone_url)
            appcodes = list(self._appcode.list_appcodes())
            matches = [item for item in appcodes if str(item["name"]).casefold() == info.appcode_candidate.casefold()]
            if len(matches) > 1:
                raise ValueError(f"Multiple appcodes match: {info.appcode_candidate}")
            matched = matches[0] if matches else None
            appcode = str(matched["name"] if matched else info.appcode_candidate)
            if not matched:
                from core.rules import validate_windows_folder_name

                validate_windows_folder_name(appcode)
            cicd_dir = self._cicd_dir_from_config(matched) if matched else (self._appcode._root() / appcode / "CICD")
            warnings = []
            if any(separator in info.appcode_candidate for separator in ("-", "_", ".", " ")):
                warnings.append("Appcode candidate contains a separator; confirm or correct it before clone.")
            return {
                "repo_name": info.repo_name,
                "appcode_candidate": info.appcode_candidate,
                "matched_appcode": appcode if matched else "",
                "appcode_exists": matched is not None,
                "needs_confirmation": matched is None,
                "target_dir": str(cicd_dir),
                "target_repo_path": str(cicd_dir / info.repo_name),
                "warnings": warnings,
            }

        def git_status(self) -> object:
            return self._service.git_status()

        @staticmethod
        def _same_remote(left: str, right: str) -> bool:
            def norm(value: str) -> str:
                value = str(value or "").strip().rstrip("/")
                return value[:-4] if value.casefold().endswith(".git") else value

            return norm(left) == norm(right)

        def clone(self, appcode: str, clone_url: str) -> object:
            return self._service.start_clone(clone_url, self._cicd_dir(appcode))

        def clone_from_link(self, clone_url: str, appcode_override: str = "", confirm_create: bool = False) -> object:
            from core.rules import validate_windows_folder_name
            from services.cicd_service import encode_repo_id, parse_clone_url

            info = parse_clone_url(clone_url)
            appcode = str(appcode_override or info.appcode_candidate).strip()
            validate_windows_folder_name(appcode)
            appcodes = list(self._appcode.list_appcodes())
            matches = [item for item in appcodes if str(item["name"]).casefold() == appcode.casefold()]
            if len(matches) > 1:
                raise ValueError(f"Multiple appcodes match: {appcode}")
            if not matches:
                if not confirm_create:
                    raise ValueError("Create appcode confirmation is required before cloning")
                self._appcode.add_appcode(appcode)
                matches = [self._appcode.get_appcode_config(appcode)]
            appcode = str(matches[0]["name"])
            cicd_dir = self._cicd_dir_from_config(matches[0])
            repo_dir = cicd_dir / info.repo_name
            repo_id = encode_repo_id(appcode, info.repo_name)
            if repo_dir.exists():
                remote = self._service.remote_url(repo_dir)
                if self._same_remote(remote, info.clone_url):
                    return {"job_id": "", "repo_id": repo_id, "repo_name": info.repo_name, "appcode": appcode, "status": "exists"}
                raise ValueError(f"Repository folder already exists with a different remote: {repo_dir}")
            started = self._service.start_clone(info.clone_url, cicd_dir)
            return {"job_id": info.repo_name, "repo_id": repo_id, "repo_name": info.repo_name, "appcode": appcode, "status": started.get("status", "cloning")}

        def _repo_path(self, repo_id: str) -> tuple[str, str, Path]:
            from services.cicd_service import decode_repo_id

            info = decode_repo_id(repo_id)
            appcode = info["appcode"]
            repo = info["repo"]
            config = self._appcode.get_appcode_config(appcode)
            cicd_dir = self._cicd_dir_from_config(config).resolve()
            repo_path = (cicd_dir / repo).resolve()
            if cicd_dir not in repo_path.parents and repo_path != cicd_dir:
                raise ValueError("Repository path is outside CICD folder")
            return appcode, repo, repo_path

        def workspace(self, appcode: str = "") -> object:
            from services.cicd_service import encode_repo_id

            appcodes = list(self._appcode.list_appcodes())
            selected = str(appcode or (appcodes[0]["name"] if appcodes else ""))
            repos = []
            if selected:
                for repo in self._service.list_repos(self._cicd_dir(selected)):
                    repo = dict(repo)
                    repo["repo_id"] = encode_repo_id(selected, str(repo["name"]))
                    repos.append(repo)
            return {"appcodes": appcodes, "repos": repos, "selected_appcode": selected}

        def repo_status(self, repo_id: str) -> object:
            _appcode, _repo, repo_path = self._repo_path(repo_id)
            return self._service.repo_status(repo_path)

        def _file_path(self, repo_id: str, rel_path: str) -> Path:
            _appcode, _repo, repo_path = self._repo_path(repo_id)
            rel = Path(str(rel_path or ""))
            if rel.is_absolute() or ".." in rel.parts or rel.parts[:1] == (".git",):
                raise ValueError("File path is outside CICD repo")
            file_path = (repo_path / rel).resolve()
            if repo_path not in file_path.parents:
                raise ValueError("File path is outside CICD repo")
            return file_path

        def file_read(self, repo_id: str, rel_path: str) -> object:
            return self._service.file_read(self._file_path(repo_id, rel_path))

        def file_save(self, repo_id: str, rel_path: str, content: str, expected_hash: str) -> object:
            _appcode, _repo, repo_path = self._repo_path(repo_id)
            status = self._service.repo_status(repo_path)
            if status.get("branch") != "cicd":
                raise ValueError("Save allowed only on branch cicd")
            return self._service.file_save(self._file_path(repo_id, rel_path), content, expected_hash)

        def git_action(self, repo_id: str, action: str, payload: dict[str, object] | None = None) -> object:
            _appcode, _repo, repo_path = self._repo_path(repo_id)
            return self._service.git_action(repo_path, action, payload)

        def job(self, job_id: str) -> object:
            data = self._service.clone_status(job_id)
            return {"job_id": job_id, "kind": "clone", "state": data.get("status", "unknown"), "progress_label": data.get("status", "unknown"), "exit_code": None, "stdout_tail": "", "stderr_tail": data.get("error", ""), "repo_id": ""}

        def clone_status(self, repo_name: str) -> object:
            return self._service.clone_status(repo_name)

        def list_repos(self, appcode: str) -> object:
            return self._service.list_repos(self._cicd_dir(appcode))

        def list_files(self, repo_path: str) -> object:
            return self._service.list_files(Path(repo_path))

    # ── year service adapter (SettingsStore → year list) ──────────────
    class _YearServiceAdapter:
        """Read-only year discovery from SettingsStore root_folder."""

        def __init__(self, settings_store: SettingsStore) -> None:
            self._settings_store = settings_store

        def list_years(self, appcode: str = "") -> object:
            settings = self._settings_store.read()
            root_folder = settings.root_folder
            if root_folder is None or not root_folder.exists():
                return []
            appcode = str(appcode).strip()
            appcode_paths = [root_folder / appcode] if appcode else [p for p in root_folder.iterdir() if p.is_dir()]
            years: set[str] = set()
            for appcode_path in appcode_paths:
                if not appcode_path.is_dir():
                    continue
                years.update(child.name for child in appcode_path.iterdir() if child.is_dir() and child.name.isdigit())
            return sorted(years)

        def create_year(self, appcode: str, year: str) -> object:
            """Create {root}/{appcode}/{year}/{5 states}."""
            year = str(year).strip()
            if not year.isdigit():
                raise ValueError("Year must be numeric (e.g. 2026)")
            settings = self._settings_store.read()
            root_folder = settings.root_folder
            if root_folder is None:
                raise ValueError("Root folder is not configured")
            appcode = str(appcode).strip()
            if not appcode:
                raise ValueError("Appcode is required")
            appcode_path = root_folder / appcode
            appcode_path.mkdir(parents=True, exist_ok=True)
            year_dir = appcode_path / year
            if year_dir.exists():
                raise ValueError(f"Year folder already exists: {year_dir}")
            ensure_appcode_year_structure(appcode_path, int(year))
            return {"appcode": appcode, "year": year, "path": str(year_dir)}

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
        ) -> None:
            self._settings_store = settings_store

        def list_files(self, path: Path) -> object:
            p = Path(path)
            if not p.is_dir():
                return []
            entries = [
                {"name": child.name, "path": str(child)}
                for child in p.iterdir()
                if child.is_file() and child.name not in ("notes.md", "project_data.json")
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
            filesystem.send_to_recycle_bin(target)
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
            _atomic_write_text(notes_file, notes)
            return notes

        # ── _cr-docs RTE files (Piece B) ───────────────────────────────
        # Reuses the notes adapter: same IMPLEMENTED lock rule (signoff
        # evidence is treated like notes per spec amendment A3). Revision 2 stores
        # the two editable CR docs as native Word files so Windows double-click and
        # Outlook copy/paste preserve tables/images.
        _CR_DOC_NAMES = frozenset({"uat-signoff.docx", "prod-lv.docx"})

        def _detect_rte_format(self, path: Path) -> str:
            """Return the RTE format for ``path``.

            docx → ``*.docx``; markdown → ``*.md``; msg → ``*.msg`` (binary,
            never read into memory); html → ``*.html``/``*.htm``; text → other.
            """
            suffix = Path(path).suffix.casefold()
            if suffix == ".docx":
                return "docx"
            if suffix == ".md":
                return "markdown"
            if suffix == ".msg":
                return "msg"
            if suffix in {".html", ".htm"}:
                return "html"
            return "text"

        def _rte_capability_for(self, path: Path, fmt: str, state: ProjectState | None) -> dict[str, object]:
            """Return honest editor capability metadata for an RTE target."""
            if fmt == "msg":
                return {
                    "capability": "unsupported",
                    "editable": False,
                    "message": f"Format {Path(path).suffix or Path(path).name} belum dapat dibuka di editor ini.",
                    "saveStrategy": "none",
                    "supportedEditorFeatures": [],
                }
            if fmt == "docx":
                return {
                    "capability": "read_only",
                    "editable": False,
                    "message": "Read-only: format ini dapat ditampilkan tetapi belum dapat diedit dengan aman.",
                    "saveStrategy": "none",
                    "supportedEditorFeatures": [],
                }
            if state is ProjectState.IMPLEMENTED:
                return {
                    "capability": "read_only",
                    "editable": False,
                    "message": "Read-only: project is in IMPLEMENTED state.",
                    "saveStrategy": "none",
                    "supportedEditorFeatures": [],
                }
            if fmt == "text":
                return {
                    "capability": "editable",
                    "editable": True,
                    "message": "Plain text only.",
                    "saveStrategy": "plain_text",
                    "supportedEditorFeatures": ["plain_text"],
                }
            if fmt == "html":
                return {
                    "capability": "editable",
                    "editable": True,
                    "message": "Saved as HTML.",
                    "saveStrategy": "html",
                    "supportedEditorFeatures": ["bold", "italic", "strike", "heading", "list", "link", "code", "image", "table"],
                }
            return {
                "capability": "editable",
                "editable": True,
                "message": "Saved as Markdown.",
                "saveStrategy": "markdown",
                "supportedEditorFeatures": ["bold", "italic", "strike", "heading", "list", "task_list", "link", "code", "image", "table"],
            }

        def _html_to_docx_bytes(self, html: str) -> bytes:
            from docx import Document
            from htmldocx import HtmlToDocx

            document = Document()
            parser = HtmlToDocx()
            parser.add_html_to_document(html or "", document)
            buffer = BytesIO()
            document.save(buffer)
            return buffer.getvalue()

        def _docx_to_html(self, path: Path) -> str:
            import mammoth

            # Read bytes into memory first so Windows releases the file before a
            # later autosave tries to atomically replace the .docx.
            with BytesIO(path.read_bytes()) as source:
                result = mammoth.convert_to_html(source)
            return str(result.value or "")

        def _write_docx_bytes(self, path: Path, data: bytes) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = path.with_name(f".{path.name}.tmp")
            try:
                temp_path.write_bytes(data)
                temp_path.replace(path)
            except Exception:
                try:
                    temp_path.unlink()
                except OSError:
                    pass
                raise

        def get_rte_file(self, file_path: Path) -> object:
            path = Path(file_path)
            fmt = self._detect_rte_format(path)
            state = _folder_state_for_path(path)
            capability = self._rte_capability_for(path, fmt, state)

            if fmt == "msg":
                # Binary Outlook message — never read into memory; the frontend
                # renders an "Open externally" panel instead of the editor.
                return {"content": "", "format": fmt, **capability}

            if fmt == "docx" and path.name in self._CR_DOC_NAMES and not path.exists():
                self._write_docx_bytes(path, self._html_to_docx_bytes(""))

            if not path.is_file():
                # Markdown/text/html arbitrary targets are never auto-created.
                return {"content": "", "format": fmt, **capability}

            if fmt == "docx":
                return {"content": self._docx_to_html(path), "format": fmt, **capability}

            content = path.read_text(encoding="utf-8")
            return {"content": content, "format": fmt, **capability}

        def save_rte_file(self, file_path: Path, content: str) -> object:
            path = Path(file_path)
            fmt = self._detect_rte_format(path)
            state = _folder_state_for_path(path)
            capability = self._rte_capability_for(path, fmt, state)
            if capability["capability"] != "editable" or capability["saveStrategy"] == "none":
                raise ValueError(str(capability["message"]))
            _atomic_write_text(path, content)
            return {"saved": True}

        def export_to_docx(self, content_html: str) -> str:
            return base64.b64encode(self._html_to_docx_bytes(content_html)).decode("ascii")

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

        def clear_rule_logs(self, rule_id: str) -> dict[str, object]:
            return {"deleted": self._cache.clear_rule_logs(rule_id)}

        # -- Slice 3: conflict detection + pre-seeded rules ----------------
        def detect_conflicts(self) -> list[dict[str, object]]:
            """Return conflict warnings for enabled rules sharing trigger+goal+scope.

            A conflict is a WARNING, never a block. Each entry names the two
            colliding rule ids + the shared key so the UI can badge them.
            """
            _, rules = self._read()
            enabled = [r for r in rules if r.get("enabled", True)]
            conflicts: list[dict[str, object]] = []
            for i, a in enumerate(enabled):
                for b in enabled[i + 1 :]:
                    key_a = self._conflict_key(a)
                    if key_a and key_a == self._conflict_key(b):
                        conflicts.append(
                            {
                                "rule_ids": [str(a.get("id", "")), str(b.get("id", ""))],
                                "rule_names": [str(a.get("name", "")), str(b.get("name", ""))],
                                "key": key_a,
                            }
                        )
            return conflicts

        @staticmethod
        def _conflict_key(rule: dict[str, object]) -> str:
            """Build the trigger+goal+scope signature for conflict detection."""
            from services.automation_service import rules_conflict_key  # noqa: PLC0415

            return rules_conflict_key(rule)

        def seed_defaults(self) -> list[dict[str, object]]:
            """Seed pre-seeded rules DISABLED by default. Idempotent.

            Returns the list of pre-seeded rules (existing or newly seeded).
            User must explicitly enable them.
            """
            settings, rules = self._read()
            existing_names = {
                str(r.get("name", ""))
                for r in rules
                if r.get("is_pre_seeded")
            }
            seeded: list[dict[str, object]] = []
            added = False
            for preset in _PRESEEDED_RULES:
                if preset["name"] in existing_names:
                    continue
                import uuid

                rule = {
                    "id": str(uuid.uuid4()),
                    "name": preset["name"],
                    "enabled": False,  # DEFAULT AMAN: disabled, user enables
                    "goal": preset["goal"],
                    "scope": {"type": "all"},
                    "trigger": preset["trigger"],
                    "actions": preset["actions"],
                    "conditions": [],
                    "is_pre_seeded": True,
                }
                rules.append(rule)
                seeded.append(rule)
                added = True
            if added:
                self._persist(settings, rules)
            return seeded

        # -- Slice 5: cross-module automation_logs ------------------------
        def list_logs(
            self,
            *,
            module: str = "all",
            cr_id: str = "",
            rule_id: str = "",
            limit: int = 200,
        ) -> list[dict[str, object]]:
            rows = self._cache.list_logs(
                module=module, cr_id=cr_id, rule_id=rule_id, limit=limit
            )
            return [
                {
                    "id": r.id,
                    "module": r.module,
                    "rule_id": r.rule_id,
                    "cr_id": r.cr_id,
                    "timestamp": r.timestamp.isoformat() if r.timestamp else "",
                    "event_type": r.event_type,
                    "detail": r.detail,
                }
                for r in rows
            ]

        def clear_logs(self, *, cr_id: str = "") -> dict[str, object]:
            if cr_id:
                deleted = self._cache.purge_logs_for_cr(cr_id)
            else:
                deleted = self._cache.clear_all_logs()
            return {"deleted": deleted}

    rules_adapter = _RulesAdapter(_settings_store, cache_db)
    # Re-build automation service so rules CRUD + evaluation share one rule list.
    # Slice 3: inject metadata_store so update_cr_state / update_drone_state /
    # append_history mutate real project metadata.
    automation_svc = AutomationService(
        rules_provider=rules_adapter.list_rules,
        cache=cache_db,
        notification_service=notification_svc,
        metadata_store=_metadata_store,
    )

    # ── JsApi ─────────────────────────────────────────────────────────
    from services.cicd_service import CicdService

    _appcode_adapter = _AppCodeServiceAdapter(_settings_store)
    _cicd_adapter = _CicdServiceAdapter(_appcode_adapter, CicdService())
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
        appcode_service=_appcode_adapter,
        file_service=_FileServiceAdapter(_settings_store),
        notes_service=_NotesServiceAdapter(),
        rte_document_service=_get_rte_document_service_lazy(),
        outlook_service=_OutlookServiceAdapter(
            _settings_store,
            _metadata_store,
            email_svc,
            DownloadEmailService(notification_service=notification_svc),
        ),
        teams_service=_TeamsServiceAdapter(
            _settings_store,
            TeamsService(),
        ),
        approval_service=approval_svc,
        cicd_service=_cicd_adapter,
    )


def _get_rte_document_service_lazy():
    """Process-wide docx pipeline service (D-0012); import kept local so tests
    that build a JsApi without the pipeline stay import-light."""
    from services.rte_document_service import get_rte_document_service

    return get_rte_document_service()


def get_frontend_entry_path(*, project_root: Path = PROJECT_ROOT) -> Path:
    """Return production Svelte frontend entry path."""
    entry_path = (project_root / "web" / "static" / "index.html").resolve()
    if not entry_path.is_file():
        raise FileNotFoundError(
            f"Built Svelte frontend not found: {entry_path}. Run `npm --prefix frontend run build`."
        )
    return entry_path


def resolve_frontend_url(*, dev: bool = False, project_root: Path = PROJECT_ROOT) -> str:
    """Return frontend URL/path for dev or production pywebview startup."""
    if dev:
        return VITE_DEV_SERVER_URL
    return str(get_frontend_entry_path(project_root=project_root))


def run(*, dev: bool = False, start_webview: bool = True) -> None:
    """Create webview window and start pywebview on main thread."""
    global webview
    if webview is None:  # lazy real import; tests pre-patch app_web.webview with a fake
        import webview as _webview
        webview = _webview

    logger = app_logger.setup_backend_logging()
    logger.info(
        "backend.app.start",
        extra={
            "payload": {
                "dev": dev,
                "start_webview": start_webview,
                "frozen": bool(getattr(sys, "frozen", False)),
                "config_dir": str(app_config_dir()),
                "static_dir": str(SVELTE_STATIC_DIR),
            }
        },
    )
    # Bootstrap root folder before creating JsApi so cache is correct.
    from services.bootstrap_service import bootstrap_root  # noqa: PLC0415
    from services.scanner_service import ScannerService  # noqa: PLC0415

    _bootstrap_settings = SettingsStore()
    _bootstrap_cache = CacheDb(app_config_dir() / "project_tracker_cache.db")
    _bootstrap_cache.initialize()
    _bootstrap_scanner = ScannerService(_bootstrap_cache)
    try:
        bootstrap_root(_bootstrap_settings, _bootstrap_cache, _bootstrap_scanner)
    except Exception:  # noqa: BLE001 — bootstrap must never block startup
        logger.warning("root folder bootstrap failed; continuing with current state")

    js_api = create_js_api(db_path=app_config_dir() / "project_tracker_cache.db")
    # Slice 3: seed pre-seeded rules (DISABLED) idempotently at real app start.
    try:
        js_api.rules_seed_defaults()
    except Exception:  # noqa: BLE001 — seeding must never block startup
        logger.warning("rules_seed_defaults failed; continuing without seeding")
    window = webview.create_window(
        "Project Tracker DBS",
        url=resolve_frontend_url(dev=dev),
        js_api=js_api,
        width=1200,
        height=760,
        min_size=(960, 640),
        frameless=True,
        easy_drag=False,
    )
    _app_window = window  # keep reference for window-control bridge methods
    if hasattr(window, "events"):
        from web.js_api import register_win_events  # noqa: PLC0415
        register_win_events(window)
    if start_webview:
        webview.start(http_server=True)
        # Window closed: flush pending DOCX exports. source.json is already
        # saved by the frontend debounce; only derived .docx files may lag,
        # and export_pending regenerates them on next open (flow-tiptap §21).
        from services.rte_document_service import shutdown_rte_document_service  # noqa: PLC0415

        shutdown_rte_document_service(timeout_s=10.0)

        from services.approval_polling_service import shutdown_approval_polling_service  # noqa: PLC0415

        shutdown_approval_polling_service()


if __name__ == "__main__":
    run(dev="--dev" in sys.argv)
