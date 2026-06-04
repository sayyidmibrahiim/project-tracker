"""Scheduler service foundation for APScheduler-backed interval jobs.

Phase C.4a only wires lifecycle around an injected job callable.
No project scanning, notifications, frontend bridge, or event queue behavior lives here.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

DEFAULT_JOB_ID = "scheduler_service_interval_job"


class SchedulerService:
    """Small wrapper around APScheduler BackgroundScheduler lifecycle."""

    def __init__(
        self,
        job: Callable[[], None],
        interval_seconds: int = 60,
        scheduler: Any | None = None,
        job_id: str = DEFAULT_JOB_ID,
    ) -> None:
        self._job = job
        self._interval_seconds = interval_seconds
        self._scheduler = scheduler if scheduler is not None else self._create_scheduler()
        self._job_id = job_id
        self._started = False

    @property
    def is_running(self) -> bool:
        """Return whether the underlying scheduler is running."""
        return bool(getattr(self._scheduler, "running", False))

    def start(self) -> None:
        """Schedule the interval job and start the scheduler once."""
        if self._started:
            return
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
        """Run the scheduled job immediately in the caller thread."""
        self._job()

    @staticmethod
    def _create_scheduler() -> Any:
        from apscheduler.schedulers.background import BackgroundScheduler

        return BackgroundScheduler()
