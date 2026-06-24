"""Download Email service — background polling for Outlook reply emails."""

from __future__ import annotations

import sys
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from threading import Event, Thread
from typing import TYPE_CHECKING

from core.models import DownloadEmailJob, local_now
from core.signal import Signal

if TYPE_CHECKING:
    from services.notification_service import NotificationService


class DownloadEmailWorker:
    """Background worker that polls Outlook for reply emails."""

    def __init__(
        self,
        job: DownloadEmailJob,
        poll_interval_seconds: int = 10,
        timeout_seconds: int = 10800,  # 3 hours default
    ) -> None:
        self.email_found = Signal()
        self.timeout = Signal()
        self.error = Signal()
        self.progress = Signal()
        self.finished = Signal()
        self.job = job
        self.poll_interval_seconds = poll_interval_seconds
        self.timeout_seconds = timeout_seconds
        self._stop_event = Event()
        self._thread: Thread | None = None
        self._outlook = None
        self._initialized = False
        self._com_initialized = False

    def start(self) -> None:
        self._thread = Thread(target=self.run, daemon=True)
        self._thread.start()

    def run(self) -> None:
        """Main polling loop (runs in background thread)."""
        start_time = datetime.now()

        try:
            while not self._stop_event.is_set():
                elapsed = (datetime.now() - start_time).total_seconds()

                if elapsed >= self.timeout_seconds:
                    self.timeout.emit()
                    return

                self.progress.emit(int(elapsed))

                try:
                    email = self._check_outlook_for_reply()
                    if email:
                        self.email_found.emit(email["subject"], email["body"])
                        return
                except Exception as e:
                    self.error.emit(str(e))
                    return

                self._sleep_until_next_poll()
        finally:
            self._uninitialize_com()
            self.finished.emit()

    def stop(self) -> None:
        """Request worker to stop."""
        self._stop_event.set()

    def _sleep_until_next_poll(self) -> None:
        self._stop_event.wait(self.poll_interval_seconds)

    def _uninitialize_com(self) -> None:
        if self._com_initialized:
            import pythoncom

            pythoncom.CoUninitialize()
            self._com_initialized = False

    def _ensure_outlook_initialized(self) -> None:
        """Initialize Outlook COM on first use (Windows only)."""
        if not self._initialized:
            if sys.platform != "win32":
                raise RuntimeError("Outlook COM is only available on Windows")
            import pythoncom
            import win32com.client

            pythoncom.CoInitialize()
            self._com_initialized = True
            self._outlook = win32com.client.Dispatch("Outlook.Application")
            self._initialized = True

    def _check_outlook_for_reply(self) -> dict[str, str] | None:
        """Check Outlook inbox for reply email matching CR number.

        Returns:
            dict with subject and body if found, None otherwise

        Raises:
            RuntimeError: If not running on Windows or Outlook not available
        """
        self._ensure_outlook_initialized()

        # Get inbox folder
        namespace = self._outlook.GetNamespace("MAPI")
        inbox = namespace.GetDefaultFolder(6)  # 6 = olFolderInbox

        # Search for emails with CR number in subject
        # Only check recent emails (last 24 hours)
        cutoff_time = datetime.now() - timedelta(hours=24)

        for item in inbox.Items:
            try:
                # Check if email is recent
                received_time = item.ReceivedTime
                if received_time < cutoff_time:
                    continue

                # Check if CR number is in subject
                subject = str(item.Subject)
                if self.job.cr_number.upper() in subject.upper():
                    # Save attachments under the target project folder before
                    # returning (Requirement 8.8). COM attachment objects must be
                    # handled on this COM thread, so the save happens here.
                    self._save_attachments(item)
                    return {
                        "subject": subject,
                        "body": str(item.Body),
                        "item": item,  # Keep reference for saving attachments
                    }
            except Exception:
                continue  # Skip items that can't be read

        return None

    def _save_attachments(self, item: object) -> None:
        """Save an Outlook mail item's attachments under the project folder.

        Each attachment is written to ``job.project_path`` using ``pathlib`` for
        path construction so attachments always land under the target project
        folder (Requirement 8.8). Accepts any object exposing the Outlook
        ``Attachments`` collection interface (``Count`` + ``Item(i)``), which
        keeps the method unit-testable without a live COM object.
        """
        attachments = getattr(item, "Attachments", None)
        if attachments is None:
            return

        try:
            count = int(attachments.Count)
        except (AttributeError, TypeError, ValueError):
            return

        for index in range(1, count + 1):
            attachment = attachments.Item(index)
            filename = str(getattr(attachment, "FileName", "") or "")
            if not filename:
                continue
            # Use only the base name to keep the file under the project folder.
            target = self.job.project_path / Path(filename).name
            attachment.SaveAsFile(str(target))


class DownloadEmailService:
    """Service for managing Download Email automation jobs."""

    def __init__(
        self,
        notification_service: NotificationService | None = None,
    ) -> None:
        self.job_started = Signal()
        self.job_completed = Signal()
        self.job_timeout = Signal()
        self.job_stopped = Signal()
        self.job_progress = Signal()
        self.notification_service = notification_service
        self._active_jobs: dict[str, tuple[DownloadEmailJob, DownloadEmailWorker]] = {}
        self._job_history: list[DownloadEmailJob] = []

    def start_job(
        self,
        cr_number: str,
        project_name: str,
        project_path: Path,
        matching_rule: str | None = None,
    ) -> str:
        """Start a new Download Email job.

        Args:
            cr_number: CR number to match in email subject
            project_name: Project name for display
            project_path: Path to project folder for saving email/attachments
            matching_rule: Optional matching rule (not implemented in MVP)

        Returns:
            job_id: Unique identifier for the job
        """
        job_id = str(uuid.uuid4())

        job = DownloadEmailJob(
            job_id=job_id,
            cr_number=cr_number,
            project_name=project_name,
            project_path=project_path,
            start_time=local_now(),
            status="active",
            matching_rule=matching_rule,
        )

        worker = DownloadEmailWorker(job)
        worker.email_found.connect(lambda subject, body: self._on_email_found(job_id, subject, body))
        worker.timeout.connect(lambda: self._on_timeout(job_id))
        worker.error.connect(lambda error: self._on_error(job_id, error))
        worker.progress.connect(lambda elapsed: self._on_progress(job_id, elapsed))
        worker.finished.connect(lambda: self._on_worker_finished(job_id))

        self._active_jobs[job_id] = (job, worker)
        worker.start()

        self.job_started.emit(job_id)
        return job_id

    def stop_job(self, job_id: str) -> None:
        """Stop an active job.

        Args:
            job_id: Job identifier
        """
        if job_id not in self._active_jobs:
            return

        job, worker = self._active_jobs[job_id]
        worker.stop()

        job.status = "stopped"
        self._job_history.append(job)
        del self._active_jobs[job_id]

        self.job_stopped.emit(job_id)

    def get_active_jobs(self) -> list[DownloadEmailJob]:
        """Get list of active jobs."""
        return [job for job, _ in self._active_jobs.values()]

    def get_job_history(self) -> list[DownloadEmailJob]:
        """Get list of completed/stopped/timeout jobs."""
        return self._job_history.copy()

    def _on_email_found(self, job_id: str, subject: str, body: str) -> None:
        """Handle email found event."""
        if job_id not in self._active_jobs:
            return

        job, worker = self._active_jobs[job_id]

        email_file = job.project_path / f"email_{job.cr_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            if not job.project_path.is_dir():
                raise FileNotFoundError(job.project_path)
            email_file.write_text(f"Subject: {subject}\n\nBody:\n{body}", encoding="utf-8")
        except OSError as e:
            self._on_error(job_id, str(e))
            return

        job.status = "completed"
        self._job_history.append(job)
        del self._active_jobs[job_id]

        self.job_completed.emit(job_id)

        if self.notification_service:
            self.notification_service.add(
                type="SUCCESS",
                title="Email Downloaded",
                message=f"Reply email for {job.cr_number} saved to {job.project_name}",
                project_path=job.project_path,
            )

    def _on_timeout(self, job_id: str) -> None:
        """Handle timeout event."""
        if job_id not in self._active_jobs:
            return

        job, worker = self._active_jobs[job_id]
        job.status = "timeout"
        self._job_history.append(job)
        del self._active_jobs[job_id]

        self.job_timeout.emit(job_id)

        if self.notification_service:
            self.notification_service.add(
                type="WARNING",
                title="Email Download Timeout",
                message=f"No reply email found for {job.cr_number} after 3 hours",
                project_path=job.project_path,
            )

    def _on_error(self, job_id: str, error: str) -> None:
        """Handle error event."""
        if job_id not in self._active_jobs:
            return

        job, worker = self._active_jobs[job_id]
        job.status = "stopped"
        self._job_history.append(job)
        del self._active_jobs[job_id]

        self.job_stopped.emit(job_id)

        if self.notification_service:
            self.notification_service.add(
                type="ERROR",
                title="Email Download Error",
                message=f"Error downloading email for {job.cr_number}: {error}",
                project_path=job.project_path,
            )

    def _on_progress(self, job_id: str, elapsed: int) -> None:
        """Handle progress event."""
        self.job_progress.emit(job_id, elapsed)

    def _on_worker_finished(self, job_id: str) -> None:
        """Handle worker finished event (cleanup)."""
        # Worker cleanup is handled in other event handlers
        pass
