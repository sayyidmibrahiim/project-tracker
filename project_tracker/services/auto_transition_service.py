"""Auto transition service — scheduler-backed background checker for deployment windows."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from project_tracker.core.models import AppSettings, local_now
from project_tracker.services.project_service import ProjectService
from project_tracker.services.scheduler_service import SchedulerService
from project_tracker.web.event_queue import push_event

if TYPE_CHECKING:
    from project_tracker.services.notification_service import NotificationService

AUTO_TRANSITION_JOB_ID = "auto_transition_check"


class Signal:
    def __init__(self) -> None:
        self._callbacks: list[Callable[..., None]] = []

    def connect(self, callback: Callable[..., None]) -> None:
        self._callbacks.append(callback)

    def emit(self, *args: object) -> None:
        for callback in list(self._callbacks):
            callback(*args)


class AutoTransitionService:
    """Background service that checks deployment windows and auto-transitions projects."""

    def __init__(
        self,
        settings: AppSettings,
        notification_service: NotificationService | None = None,
        event_publisher: Callable[[str, dict[str, object] | None], None] | None = push_event,
        scheduler: Any | None = None,
    ) -> None:
        self.transition_completed = Signal()
        self.error_occurred = Signal()
        self.settings = settings
        self.notification_service = notification_service
        self._event_publisher = event_publisher
        self._project_service = ProjectService()
        self._interval_seconds = 60
        self._scheduler = scheduler
        self._scheduler_service: SchedulerService | None = None
        if scheduler is not None:
            self._scheduler_service = self._build_scheduler_service(scheduler)

    def _build_scheduler_service(self, scheduler: Any | None = None) -> SchedulerService:
        return SchedulerService(
            job=self._check_and_transition,
            interval_seconds=self._interval_seconds,
            scheduler=scheduler,
            job_id=AUTO_TRANSITION_JOB_ID,
        )

    def start(self) -> None:
        """Start the background scheduler."""
        if self._scheduler_service is None:
            self._scheduler_service = self._build_scheduler_service(self._scheduler)
        self._scheduler_service.start()

    def stop(self) -> None:
        """Stop the background scheduler."""
        if self._scheduler_service is not None:
            self._scheduler_service.stop()

    def set_interval(self, milliseconds: int) -> None:
        """Set the timer interval in milliseconds. Rebuilds SchedulerService if already created."""
        self._interval_seconds = milliseconds // 1000
        if self._scheduler_service is not None:
            self._scheduler = self._scheduler_service._scheduler
            self._scheduler_service = self._build_scheduler_service(self._scheduler)

    def _check_and_transition(self) -> None:
        """Check all projects and auto-transition those in deployment window."""
        if self.settings.root_folder is None:
            return

        from project_tracker.infrastructure.filesystem import state_folders_for_year
        from project_tracker.infrastructure.metadata_store import MetadataStore

        now = local_now()
        metadata_store = MetadataStore()

        # Scan all year folders
        for year_path in self.settings.root_folder.iterdir():
            if not year_path.is_dir() or not year_path.name.isdigit():
                continue

            # Check each state folder
            for state_folder in state_folders_for_year(year_path):
                if not state_folder.is_dir():
                    continue

                # Scan projects in this state folder
                for project_path in state_folder.iterdir():
                    if not project_path.is_dir():
                        continue

                    try:
                        metadata = metadata_store.load(project_path)
                    except Exception:
                        continue  # Skip corrupt projects

                    # Check if within deployment window
                    if not metadata.start_datetime or not metadata.end_datetime:
                        continue

                    if now < metadata.start_datetime or now >= metadata.end_datetime:
                        continue

                    # Check if transition needed
                    if metadata.cr_state.value == "APPROVED":
                        self._transition_project(project_path, metadata)

    @staticmethod
    def _auto_in_progress_payload(project_path: Path, old_state: str, new_state: str) -> dict[str, object]:
        return {
            "project_path": str(project_path),
            "project_name": project_path.name,
            "old_state": old_state,
            "new_state": new_state,
        }

    def _transition_project(self, project_path: Path, metadata: object) -> None:
        """Perform the auto-transition for a project."""
        try:
            old_state = metadata.cr_state.value
            changed = self._project_service.auto_transition_in_progress(
                project_path, self.settings, current_time=local_now()
            )
            if not changed:
                return

            new_state = "IN-PROGRESS"

            self.transition_completed.emit(project_path, old_state, new_state)

            if self._event_publisher is not None:
                self._event_publisher("AUTO_IN_PROGRESS", self._auto_in_progress_payload(project_path, old_state, new_state))

            if self.notification_service:
                self.notification_service.add(
                    type="INFO",
                    title="Auto IN-PROGRESS",
                    message=f"Project {project_path.name} auto-transitioned to IN-PROGRESS",
                    project_path=project_path,
                )
        except Exception as e:
            self.error_occurred.emit(f"Auto-transition failed for {project_path.name}: {e}")
