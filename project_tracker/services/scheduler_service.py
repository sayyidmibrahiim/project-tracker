"""Scheduler service: APScheduler-backed interval job plus user-configured entries.

The service retains its original responsibility (Phase C.4a): wrapping the
APScheduler ``BackgroundScheduler`` lifecycle around a single injected interval
``job`` callable. ``AutoTransitionService`` builds one of these to run the
existing 60-second auto IN-PROGRESS evaluation; that behaviour is preserved and
untouched here.

Task 19.1 layers on a scheduler control surface:

* persist user entries under ``settings.automation.scheduler.entries`` via the
  injected ``SettingsStore`` (validation/persistence failure rejects the
  operation and retains the prior state);
* register / pause / resume / remove the APScheduler job that backs each entry;
* on trigger, apply the entry's project + state filters and act only on matching
  projects (no match -> record that no project matched and take no action);
* deliver in-app channel alarms through the injected ``NotificationService``;
* signal that Outlook / Teams channels require frontend confirmation rather than
  firing them automatically (the confirmation gate itself is Task 19.2 / 19.4).

No COM / pyautogui execution happens here, and no new dependencies are added.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from project_tracker.core.models import SchedulerEntry, local_now

if TYPE_CHECKING:
    from project_tracker.infrastructure.settings_store import SettingsStore
    from project_tracker.services.notification_service import NotificationService

DEFAULT_JOB_ID = "scheduler_service_interval_job"
ENTRY_JOB_PREFIX = "scheduler_entry_"

VALID_SCHEDULE_TYPES = {"one_time", "daily", "weekly", "monthly", "cron"}
VALID_CHANNELS = {"in_app", "outlook_email", "teams"}
CONFIRMATION_CHANNELS = {"outlook_email", "teams"}


class SchedulerEntryError(ValueError):
    """Raised when a scheduler entry fails validation or cannot be found."""


class SchedulerService:
    """Wrapper around APScheduler plus user-configured scheduler entries."""

    def __init__(
        self,
        job: Callable[[], None] | None = None,
        interval_seconds: int = 60,
        scheduler: Any | None = None,
        job_id: str = DEFAULT_JOB_ID,
        settings_store: "SettingsStore | None" = None,
        notification_service: "NotificationService | None" = None,
        project_provider: Callable[[], list[Any]] | None = None,
    ) -> None:
        self._job = job
        self._interval_seconds = interval_seconds
        self._scheduler = scheduler if scheduler is not None else self._create_scheduler_safe()
        self._job_id = job_id
        self._started = False
        self._settings_store = settings_store
        self._notification_service = notification_service
        self._project_provider = project_provider
        # In-memory record of trigger outcomes (matches / no-match / pending
        # confirmation). Kept for observability and unit-test assertions; the
        # durable record of entries themselves lives in settings.json.
        self.trigger_records: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Lifecycle (unchanged contract — preserves the 60s auto IN-PROGRESS job)
    # ------------------------------------------------------------------
    @property
    def is_running(self) -> bool:
        """Return whether the underlying scheduler is running."""
        return bool(getattr(self._scheduler, "running", False))

    def start(self) -> None:
        """Schedule the interval job (when present) and start the scheduler once."""
        if self._started:
            return
        if self._scheduler is None:
            self._scheduler = self._create_scheduler()  # raises clearly if apscheduler missing
        if self._job is not None:
            self._scheduler.add_job(
                self._job,
                trigger="interval",
                seconds=self._interval_seconds,
                id=self._job_id,
                replace_existing=True,
            )
        self._scheduler.start()
        self._started = True

    def stop(self) -> None:
        """Shutdown scheduler safely if running."""
        if not self.is_running:
            self._started = False
            return
        self._scheduler.shutdown(wait=False)
        self._started = False

    def run_once(self) -> None:
        """Run the scheduled interval job immediately in the caller thread."""
        if self._job is not None:
            self._job()

    @staticmethod
    def _create_scheduler() -> Any:
        from apscheduler.schedulers.background import BackgroundScheduler

        return BackgroundScheduler()

    @classmethod
    def _create_scheduler_safe(cls) -> Any | None:
        """Create the default scheduler, tolerating a missing apscheduler.

        On environments where ``apscheduler`` is not installed (Linux dev/test
        baseline), return ``None`` so entry CRUD still works (job-management
        calls are getattr-guarded no-ops). ``start()`` re-attempts creation and
        surfaces a clear error if a scheduler is genuinely required.
        """
        try:
            return cls._create_scheduler()
        except Exception:  # noqa: BLE001 - apscheduler optional off-Windows
            return None

    @classmethod
    def _create_scheduler_safe(cls) -> Any | None:
        """Create the default scheduler, tolerating a missing apscheduler.

        On environments where ``apscheduler`` is not installed (the Linux
        dev/test baseline), return ``None`` so entry CRUD still works
        (job-management calls are getattr-guarded no-ops). ``start()`` re-attempts
        creation and surfaces a clear error if a scheduler is genuinely required.
        """
        try:
            return cls._create_scheduler()
        except Exception:  # noqa: BLE001 - apscheduler optional off-Windows
            return None

    @classmethod
    def _create_scheduler_safe(cls) -> Any | None:
        """Create the default scheduler, tolerating a missing apscheduler.

        On platforms/environments where ``apscheduler`` is not installed (e.g. the
        Linux dev/test baseline), return ``None`` so entry CRUD still works
        (job-management calls are getattr-guarded no-ops). ``start()`` re-attempts
        creation and surfaces a clear error if a scheduler is genuinely required.
        """
        try:
            return cls._create_scheduler()
        except Exception:  # noqa: BLE001 - apscheduler optional off-Windows
            return None

    # ------------------------------------------------------------------
    # Entry CRUD (persisted under settings.automation.scheduler.entries)
    # ------------------------------------------------------------------
    def list_entries(self) -> list[SchedulerEntry]:
        """Return the persisted scheduler entries."""
        return list(self._read_entries())

    def create_entry(self, data: dict[str, Any]) -> SchedulerEntry:
        """Validate, persist, and register a new scheduler entry.

        Validation or persistence failure rejects the operation and leaves the
        prior persisted state unchanged.
        """
        entry = self._build_entry(data)
        if not entry.id:
            entry.id = str(uuid.uuid4())

        settings = self._load_settings()
        entries = list(settings.automation.scheduler.entries)
        if any(existing.id == entry.id for existing in entries):
            raise SchedulerEntryError(f"Scheduler entry already exists: {entry.id}")
        entries.append(entry)

        self._persist(settings, entries)
        self._sync_job(entry)
        return entry

    def update_entry(self, entry_id: str, data: dict[str, Any]) -> SchedulerEntry:
        """Validate, persist, and re-register an existing scheduler entry."""
        settings = self._load_settings()
        entries = list(settings.automation.scheduler.entries)
        index = self._index_of(entries, entry_id)

        merged = {**entries[index].to_dict(), **data, "id": entry_id}
        updated = self._build_entry(merged)
        entries[index] = updated

        self._persist(settings, entries)
        # Reconcile the backing job to the new definition.
        self._remove_job(entry_id)
        self._sync_job(updated)
        return updated

    def delete_entry(self, entry_id: str) -> None:
        """Remove a scheduler entry and its backing APScheduler job."""
        settings = self._load_settings()
        entries = list(settings.automation.scheduler.entries)
        index = self._index_of(entries, entry_id)
        del entries[index]

        self._persist(settings, entries)
        self._remove_job(entry_id)

    def pause_entry(self, entry_id: str) -> SchedulerEntry:
        """Pause a scheduler entry: pause its job and persist the paused status."""
        return self._set_paused(entry_id, paused=True)

    def resume_entry(self, entry_id: str) -> SchedulerEntry:
        """Resume a scheduler entry: resume its job and persist the active status."""
        return self._set_paused(entry_id, paused=False)

    def set_enabled(self, entry_id: str, enabled: bool) -> SchedulerEntry:
        """Enable or disable a scheduler entry, reconciling its backing job."""
        settings = self._load_settings()
        entries = list(settings.automation.scheduler.entries)
        index = self._index_of(entries, entry_id)
        entry = entries[index]
        entry.enabled = bool(enabled)
        if entry.enabled and entry.status == "paused":
            entry.status = "active"
        elif not entry.enabled:
            entry.status = "paused"

        self._persist(settings, entries)
        self._remove_job(entry_id)
        self._sync_job(entry)
        return entry

    # ------------------------------------------------------------------
    # Trigger handling (filters + in-app delivery + confirmation signalling)
    # ------------------------------------------------------------------
    def trigger_entry(self, entry_id: str) -> dict[str, Any]:
        """Apply an entry's filters and act only on matching projects.

        Returns (and records) the trigger outcome. When no project matches, the
        outcome is recorded and no channel action is taken. In-app alarms are
        delivered via the NotificationService; Outlook/Teams channels are flagged
        as requiring frontend confirmation rather than being fired here.
        """
        entry = self._find_entry(entry_id)
        if entry is None:
            record = {
                "entry_id": entry_id,
                "entry_name": None,
                "matched": False,
                "reason": "entry_not_found",
                "matched_projects": [],
                "pending_confirmation_channels": [],
                "timestamp": local_now().isoformat(),
            }
            self.trigger_records.append(record)
            return record

        projects = self._all_projects()
        matched = [p for p in projects if self._matches(entry, p)]

        if not matched:
            record = {
                "entry_id": entry.id,
                "entry_name": entry.name,
                "matched": False,
                "reason": "no_project_matched",
                "matched_projects": [],
                "pending_confirmation_channels": [],
                "timestamp": local_now().isoformat(),
            }
            self.trigger_records.append(record)
            return record

        matched_names = [self._project_name(p) for p in matched]
        pending_confirmation = [c for c in entry.channels if c in CONFIRMATION_CHANNELS]

        if "in_app" in entry.channels:
            self._deliver_in_app(entry, matched_names)

        record = {
            "entry_id": entry.id,
            "entry_name": entry.name,
            "matched": True,
            "reason": "matched",
            "matched_projects": matched_names,
            "pending_confirmation_channels": pending_confirmation,
            "timestamp": local_now().isoformat(),
        }
        self.trigger_records.append(record)
        return record

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _build_entry(self, data: dict[str, Any]) -> SchedulerEntry:
        if not isinstance(data, dict):
            raise SchedulerEntryError("Scheduler entry data must be a mapping")
        entry = SchedulerEntry.from_dict(data)
        self._validate_entry(entry)
        return entry

    @staticmethod
    def _validate_entry(entry: SchedulerEntry) -> None:
        if not entry.name.strip():
            raise SchedulerEntryError("Scheduler entry name is required")
        if entry.schedule_type not in VALID_SCHEDULE_TYPES:
            raise SchedulerEntryError(
                f"Unsupported schedule_type: {entry.schedule_type}"
            )
        invalid_channels = [c for c in entry.channels if c not in VALID_CHANNELS]
        if invalid_channels:
            raise SchedulerEntryError(
                f"Unsupported channel(s): {', '.join(invalid_channels)}"
            )

    def _load_settings(self):
        if self._settings_store is None:
            raise SchedulerEntryError("settings_store is not configured")
        return self._settings_store.read()

    def _read_entries(self) -> list[SchedulerEntry]:
        if self._settings_store is None:
            return []
        return list(self._settings_store.read().automation.scheduler.entries)

    def _persist(self, settings: Any, entries: list[SchedulerEntry]) -> None:
        """Write the proposed entries. On failure the prior state is retained.

        The settings store writes atomically (temp-file-then-replace), so a
        failed write leaves the prior settings.json unchanged; the backing jobs
        are only reconciled after a successful write by the caller.
        """
        settings.automation.scheduler.entries = entries
        self._settings_store.write(settings)

    @staticmethod
    def _index_of(entries: list[SchedulerEntry], entry_id: str) -> int:
        for i, entry in enumerate(entries):
            if entry.id == entry_id:
                return i
        raise SchedulerEntryError(f"Scheduler entry not found: {entry_id}")

    def _find_entry(self, entry_id: str) -> SchedulerEntry | None:
        for entry in self._read_entries():
            if entry.id == entry_id:
                return entry
        return None

    def _set_paused(self, entry_id: str, *, paused: bool) -> SchedulerEntry:
        settings = self._load_settings()
        entries = list(settings.automation.scheduler.entries)
        index = self._index_of(entries, entry_id)
        entry = entries[index]
        entry.status = "paused" if paused else "active"

        self._persist(settings, entries)
        job_id = self._entry_job_id(entry_id)
        if paused:
            self._call_scheduler("pause_job", job_id)
        else:
            self._call_scheduler("resume_job", job_id)
        return entry

    # -- job management -------------------------------------------------
    @staticmethod
    def _entry_job_id(entry_id: str) -> str:
        return f"{ENTRY_JOB_PREFIX}{entry_id}"

    def _sync_job(self, entry: SchedulerEntry) -> None:
        """Register (or skip) the APScheduler job that backs an entry."""
        if not entry.enabled or entry.status == "completed":
            return
        trigger_kwargs = self._trigger_kwargs(entry)
        job_id = self._entry_job_id(entry.id)
        self._call_scheduler(
            "add_job",
            self._make_entry_job(entry.id),
            id=job_id,
            replace_existing=True,
            **trigger_kwargs,
        )
        if entry.status == "paused":
            self._call_scheduler("pause_job", job_id)

    def _remove_job(self, entry_id: str) -> None:
        self._call_scheduler("remove_job", self._entry_job_id(entry_id))

    def _make_entry_job(self, entry_id: str) -> Callable[[], None]:
        def _run() -> None:
            self.trigger_entry(entry_id)

        return _run

    @staticmethod
    def _trigger_kwargs(entry: SchedulerEntry) -> dict[str, Any]:
        cfg = entry.schedule_config or {}
        schedule_type = entry.schedule_type
        if schedule_type == "one_time":
            return {"trigger": "date", "run_date": cfg.get("run_date")}
        if schedule_type == "daily":
            return {
                "trigger": "cron",
                "hour": cfg.get("hour", 0),
                "minute": cfg.get("minute", 0),
            }
        if schedule_type == "weekly":
            return {
                "trigger": "cron",
                "day_of_week": cfg.get("day_of_week", "mon"),
                "hour": cfg.get("hour", 0),
                "minute": cfg.get("minute", 0),
            }
        if schedule_type == "monthly":
            return {
                "trigger": "cron",
                "day": cfg.get("day", 1),
                "hour": cfg.get("hour", 0),
                "minute": cfg.get("minute", 0),
            }
        # cron — pass through recognised cron fields only.
        cron_fields = (
            "year",
            "month",
            "day",
            "week",
            "day_of_week",
            "hour",
            "minute",
            "second",
        )
        passthrough = {key: cfg[key] for key in cron_fields if key in cfg}
        return {"trigger": "cron", **passthrough}

    def _call_scheduler(self, method_name: str, *args: Any, **kwargs: Any) -> None:
        """Invoke a scheduler method when available.

        Job-management methods (``pause_job``/``resume_job``/``remove_job``) raise
        when the job is unknown; those are swallowed so reconciliation stays
        idempotent. ``add_job`` errors are allowed to propagate.
        """
        method = getattr(self._scheduler, method_name, None)
        if method is None:
            return
        if method_name == "add_job":
            method(*args, **kwargs)
            return
        try:
            method(*args, **kwargs)
        except Exception:  # noqa: BLE001 - unknown job during reconciliation
            return

    # -- filtering + delivery ------------------------------------------
    def _all_projects(self) -> list[Any]:
        if self._project_provider is None:
            return []
        return list(self._project_provider())

    def _matches(self, entry: SchedulerEntry, project: Any) -> bool:
        name_ok = not entry.project_filter or entry.project_filter == self._project_name(project)
        state_ok = not entry.state_filter or entry.state_filter == self._project_state(project)
        return name_ok and state_ok

    @staticmethod
    def _project_name(project: Any) -> str | None:
        if isinstance(project, dict):
            return project.get("name") or project.get("project_name")
        return getattr(project, "name", None) or getattr(project, "project_name", None)

    @staticmethod
    def _project_state(project: Any) -> str | None:
        if isinstance(project, dict):
            return project.get("state") or project.get("project_state")
        return getattr(project, "state", None) or getattr(project, "project_state", None)

    def _deliver_in_app(self, entry: SchedulerEntry, matched_names: list[str | None]) -> None:
        if self._notification_service is None:
            return
        names = ", ".join(name for name in matched_names if name) or "(unnamed projects)"
        self._notification_service.add(
            type="SCHEDULER",
            title=entry.name or "Scheduler alarm",
            message=f"Scheduler entry '{entry.name}' matched: {names}",
        )
