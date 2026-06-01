"""Auto transition service — timer-based background checker for deployment windows."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from threading import Event, Thread
from typing import TYPE_CHECKING

from project_tracker.core.models import AppSettings, local_now
from project_tracker.services.project_service import ProjectService

if TYPE_CHECKING:
    from project_tracker.services.notification_service import NotificationService


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
    ) -> None:
        self.transition_completed = Signal()
        self.error_occurred = Signal()
        self.settings = settings
        self.notification_service = notification_service
        self._project_service = ProjectService()
        self._interval_seconds = 60.0
        self._stop_event = Event()
        self._thread: Thread | None = None
        self._running = False

    def start(self) -> None:
        """Start the background timer."""
        if not self._running:
            self._running = True
            self._stop_event.clear()
            self._thread = Thread(target=self._run_loop, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """Stop the background timer."""
        if self._running:
            self._running = False
            self._stop_event.set()
            if self._thread is not None:
                self._thread.join(timeout=1.0)
                self._thread = None

    def set_interval(self, milliseconds: int) -> None:
        """Set the timer interval in milliseconds."""
        self._interval_seconds = milliseconds / 1000

    def _run_loop(self) -> None:
        while not self._stop_event.wait(self._interval_seconds):
            self._check_and_transition()

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

    def _transition_project(self, project_path: Path, metadata: object) -> None:
        """Perform the auto-transition for a project."""
        try:
            old_state = metadata.cr_state.value
            self._project_service.auto_transition_in_progress(
                project_path, self.settings, current_time=local_now()
            )
            new_state = "IN-PROGRESS"

            self.transition_completed.emit(project_path, old_state, new_state)

            if self.notification_service:
                self.notification_service.add(
                    type="INFO",
                    title="Auto IN-PROGRESS",
                    message=f"Project {project_path.name} auto-transitioned to IN-PROGRESS",
                    project_path=project_path,
                )
        except Exception as e:
            self.error_occurred.emit(f"Auto-transition failed for {project_path.name}: {e}")
