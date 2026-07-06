"""Piece C approval automation: conditions, templated send, reply polling.

Send path renders the approval template through EmailService (reusing the
proven placeholder engine) and drafts/sends via the guarded outlook_client.
Each started request persists an approval_polling_jobs row (SQLite via CacheDb)
and runs one background worker thread (same COM shape as DownloadEmailWorker):
CoInitialize on the worker thread, poll the inbox every interval, SaveAs the
first matching reply as .msg into _cr-docs/, CoUninitialize in finally.
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime
from pathlib import Path
from threading import Event, Thread
from typing import TYPE_CHECKING, Any

from core.enums import CRState, DroneState, ProjectType
from core.models import EmailCategorySettings, HistoryEntry, ProjectMetadata, local_now
from core.rules import current_user, extract_cr_number
from infrastructure import outlook_client
from services.email_service import EmailService, TemplateConditionsNotMetError, UnresolvedPlaceholderError

if TYPE_CHECKING:
    from infrastructure.cache_db import CacheDb
    from infrastructure.metadata_store import MetadataStore
    from services.notification_service import NotificationService

REQUEST_KINDS: dict[str, dict[str, str]] = {
    "uat": {
        "template_key": "uat_approval",
        "signoff_file": "uat-signoff.docx",
        "msg_file": "uat-approval.msg",
        "label": "UAT Approval",
    },
    "lv": {
        "template_key": "lv_approval",
        "signoff_file": "prod-lv.docx",
        "msg_file": "prod-approval.msg",
        "label": "LV",
    },
}

TEMPLATE_FIELDS = ("to", "cc", "subject", "body", "mode")


def _ok(data: Any = None) -> dict[str, Any]:
    return {"ok": True, "data": data, "error": None}


def _fail(message: str, code: str) -> dict[str, Any]:
    return {"ok": False, "data": None, "error": {"code": code, "message": message}}


def _file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


class ApprovalPollingWorker:
    """Background reply poller for one approval request (COM on this thread)."""

    def __init__(
        self,
        job: dict[str, Any],
        target_msg: Path,
        poll_interval_seconds: int,
        timeout_seconds: int,
        on_found,
        on_timeout,
        on_warning,
    ) -> None:
        self.job = job
        self.target_msg = target_msg
        self.poll_interval_seconds = max(30, int(poll_interval_seconds))
        self.timeout_seconds = max(60, int(timeout_seconds))
        self._on_found = on_found
        self._on_timeout = on_timeout
        self._on_warning = on_warning
        self._stop_event = Event()
        self._thread: Thread | None = None
        self._outlook = None
        self._com_initialized = False
        # Compared against inbox ReceivedTime; resume shortening is handled by
        # the caller passing a reduced timeout_seconds (_start_worker).
        self.sent_at = datetime.fromisoformat(str(job["sent_at"]))

    def start(self) -> None:
        self._thread = Thread(target=self.run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        start_time = datetime.now()
        try:
            while not self._stop_event.is_set():
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed >= self.timeout_seconds:
                    self._on_timeout(self.job)
                    return
                try:
                    subject = self._check_and_save_reply()
                    if subject is not None:
                        self._on_found(self.job, subject)
                        return
                except Exception as exc:  # noqa: BLE001 - spec: retry next interval
                    self._on_warning(self.job, str(exc) or exc.__class__.__name__)
                self._stop_event.wait(self.poll_interval_seconds)
        finally:
            if self._com_initialized:
                import pythoncom

                pythoncom.CoUninitialize()
                self._com_initialized = False

    def _ensure_outlook(self) -> None:
        if self._outlook is None:
            if sys.platform != "win32":
                raise RuntimeError("Outlook COM is only available on Windows")
            import pythoncom
            import win32com.client

            pythoncom.CoInitialize()
            self._com_initialized = True
            self._outlook = win32com.client.Dispatch("Outlook.Application")

    def _check_and_save_reply(self) -> str | None:
        """Return the reply subject after saving it as .msg, else None."""
        self._ensure_outlook()
        namespace = self._outlook.GetNamespace("MAPI")
        inbox = namespace.GetDefaultFolder(6)  # 6 = olFolderInbox
        cr_number = str(self.job["cr_number"]).upper()
        for item in inbox.Items:
            try:
                received = item.ReceivedTime
                received_naive = datetime(
                    received.year, received.month, received.day, received.hour, received.minute, received.second
                )
                if received_naive <= self.sent_at:
                    continue
                subject = str(item.Subject)
                if cr_number and cr_number in subject.upper():
                    self.target_msg.parent.mkdir(parents=True, exist_ok=True)
                    item.SaveAs(str(self.target_msg), 3)  # 3 = olMSG
                    return subject
            except Exception:  # noqa: BLE001 - skip unreadable items
                continue
        return None


class ApprovalPollingService:
    """Piece C service: conditions, templates, send, polling, persistence."""

    def __init__(
        self,
        settings_store: Any,
        metadata_store: "MetadataStore",
        email_service: EmailService,
        cache: "CacheDb",
        notification_service: "NotificationService | None" = None,
    ) -> None:
        self._settings_store = settings_store
        self._metadata_store = metadata_store
        self._email_service = email_service
        self._cache = cache
        self._notification_service = notification_service
        self._workers: dict[str, ApprovalPollingWorker] = {}

    # ── conditions + status ────────────────────────────────────────────
    def get_status(self, project_path: Path) -> dict[str, Any]:
        path = Path(project_path)
        metadata = self._metadata_store.read(path) or ProjectMetadata(project_name=path.name)
        cr_number = extract_cr_number(metadata.cr_link) or ""
        status: dict[str, Any] = {
            "automation_enabled": metadata.automation_enabled,
            "outlook_available": outlook_client.IS_WINDOWS,
        }
        for kind, config in REQUEST_KINDS.items():
            reasons = self._condition_reasons(metadata, path, cr_number, kind)
            job = self._cache.latest_approval_job(str(path), kind)
            template_ok = self._resolve_template(metadata, kind) is not None
            if not template_ok:
                reasons.append("template_missing")
            status[kind] = {"eligible": not reasons, "reasons": reasons, "job": job}
        return status

    def _condition_reasons(
        self, metadata: ProjectMetadata, path: Path, cr_number: str, kind: str
    ) -> list[str]:
        config = REQUEST_KINDS[kind]
        reasons: list[str] = []
        if metadata.project_type != ProjectType.CR:
            reasons.append("not_cr_project")
        if not cr_number:
            reasons.append("cr_number_missing")
        if _file_size(path / "_cr-docs" / config["signoff_file"]) <= 0:
            reasons.append("signoff_missing_or_empty")
        if kind == "uat":
            if not metadata.drone_tickets:
                reasons.append("no_drone_ticket")
            elif not any(d.drone_state == DroneState.PENDING_APPROVAL for d in metadata.drone_tickets):
                reasons.append("no_drone_pending_approval")
            if metadata.cr_state != CRState.PENDING_SUBMISSION:
                reasons.append("cr_not_pending_submission")
        else:
            cr_approved = metadata.cr_state == CRState.APPROVED
            drone_approved = any(d.drone_state == DroneState.APPROVED for d in metadata.drone_tickets)
            if not (cr_approved or drone_approved):
                reasons.append("not_approved")
        return reasons

    # ── toggle ─────────────────────────────────────────────────────────
    def set_enabled(self, project_path: Path, enabled: bool) -> dict[str, Any]:
        path = Path(project_path)
        metadata = self._metadata_store.read(path)
        if metadata is None:
            return _fail(f"Project metadata not found: {path}", "APPROVAL_PROJECT_NOT_FOUND")
        metadata.automation_enabled = bool(enabled)
        metadata.updated_at = local_now()
        self._metadata_store.write(path, metadata)
        return _ok({"automation_enabled": metadata.automation_enabled})

    # ── templates ──────────────────────────────────────────────────────
    def _resolve_template(self, metadata: ProjectMetadata, kind: str) -> dict[str, Any] | None:
        key = REQUEST_KINDS[kind]["template_key"]
        project_template = metadata.approval_templates.get(key)
        if isinstance(project_template, dict) and project_template:
            return dict(project_template)
        default = self._settings_store.read().default_approval_templates.get(key)
        if isinstance(default, dict) and default:
            return dict(default)
        return None

    def get_template(self, project_path: Path, kind: str) -> dict[str, Any]:
        if kind not in REQUEST_KINDS:
            return _fail(f"Unknown request kind: {kind}", "APPROVAL_KIND_INVALID")
        path = Path(project_path)
        metadata = self._metadata_store.read(path) or ProjectMetadata(project_name=path.name)
        key = REQUEST_KINDS[kind]["template_key"]
        project_template = metadata.approval_templates.get(key)
        if isinstance(project_template, dict) and project_template:
            return _ok({"source": "project", "template": dict(project_template)})
        default = self._settings_store.read().default_approval_templates.get(key)
        if isinstance(default, dict) and default:
            return _ok({"source": "default", "template": dict(default)})
        return _ok({"source": "none", "template": {field: "" for field in TEMPLATE_FIELDS} | {"mode": "draft"}})

    def update_template(self, project_path: Path, kind: str, template: dict[str, Any]) -> dict[str, Any]:
        if kind not in REQUEST_KINDS:
            return _fail(f"Unknown request kind: {kind}", "APPROVAL_KIND_INVALID")
        if not isinstance(template, dict):
            return _fail("Template must be a mapping", "APPROVAL_TEMPLATE_INVALID")
        path = Path(project_path)
        metadata = self._metadata_store.read(path)
        if metadata is None:
            return _fail(f"Project metadata not found: {path}", "APPROVAL_PROJECT_NOT_FOUND")
        clean = {field: str(template.get(field, "")) for field in TEMPLATE_FIELDS}
        if clean["mode"] not in ("draft", "send"):
            clean["mode"] = "draft"
        metadata.approval_templates[REQUEST_KINDS[kind]["template_key"]] = clean
        metadata.updated_at = local_now()
        self._metadata_store.write(path, metadata)
        return _ok({"source": "project", "template": clean})

    def preview_template(self, project_path: Path, kind: str, template: dict[str, Any] | None) -> dict[str, Any]:
        if kind not in REQUEST_KINDS:
            return _fail(f"Unknown request kind: {kind}", "APPROVAL_KIND_INVALID")
        path = Path(project_path)
        metadata = self._metadata_store.read(path)
        if metadata is None:
            return _fail(f"Project metadata not found: {path}", "APPROVAL_PROJECT_NOT_FOUND")
        resolved = dict(template) if isinstance(template, dict) and template else self._resolve_template(metadata, kind)
        if resolved is None:
            return _fail("No template configured", "APPROVAL_TEMPLATE_MISSING")
        cr_number = extract_cr_number(metadata.cr_link) or ""
        try:
            rendered = self._render(metadata, resolved, cr_number)
        except (UnresolvedPlaceholderError, TemplateConditionsNotMetError) as exc:
            return _fail(str(exc), "APPROVAL_TEMPLATE_INVALID")
        return _ok({"to": rendered.to, "cc": rendered.cc, "subject": rendered.subject, "body": rendered.body})

    def _render(self, metadata: ProjectMetadata, template: dict[str, Any], cr_number: str):
        category = EmailCategorySettings(
            to=str(template.get("to", "")),
            cc=str(template.get("cc", "")),
            subject_template=str(template.get("subject", "")).replace("{CR_NUMBER}", cr_number),
            body_template=str(template.get("body", "")).replace("{CR_NUMBER}", cr_number),
        )
        return self._email_service.render_email_template(metadata, category, self._settings_store.read())

    # ── send + polling ─────────────────────────────────────────────────
    def send_request(self, project_path: Path, kind: str) -> dict[str, Any]:
        if kind not in REQUEST_KINDS:
            return _fail(f"Unknown request kind: {kind}", "APPROVAL_KIND_INVALID")
        path = Path(project_path)
        metadata = self._metadata_store.read(path)
        if metadata is None:
            return _fail(f"Project metadata not found: {path}", "APPROVAL_PROJECT_NOT_FOUND")
        cr_number = extract_cr_number(metadata.cr_link) or ""
        reasons = self._condition_reasons(metadata, path, cr_number, kind)
        if reasons:
            return _fail(f"Conditions not met: {', '.join(reasons)}", "APPROVAL_CONDITIONS_NOT_MET")

        template = self._resolve_template(metadata, kind)
        if template is None:
            return _fail("No approval template configured", "APPROVAL_TEMPLATE_MISSING")
        if "{CR_NUMBER}" not in str(template.get("subject", "")):
            return _fail("Template subject must contain {CR_NUMBER}", "APPROVAL_TEMPLATE_INVALID")

        try:
            rendered = self._render(metadata, template, cr_number)
        except (UnresolvedPlaceholderError, TemplateConditionsNotMetError) as exc:
            return _fail(str(exc), "APPROVAL_TEMPLATE_INVALID")

        if not outlook_client.IS_WINDOWS:
            return _ok({"status": "dev_skipped", "message": f"[DEV] Would send {kind} approval request: {rendered.subject}"})

        send = outlook_client.send_email if template.get("mode") == "send" else outlook_client.create_draft_email
        result = send(rendered.to, rendered.cc, rendered.subject, rendered.body, None)
        if not result.get("ok"):
            return result

        sent_at = local_now().replace(tzinfo=None)
        job = {
            "job_id": str(uuid.uuid4()),
            "project_path": str(path),
            "request_type": kind,
            "cr_number": cr_number,
            "email_subject": rendered.subject,
            "sent_at": sent_at.isoformat(),
            "status": "polling",
            "reply_received_at": None,
        }
        self._cache.upsert_approval_job(job)
        metadata.history.append(
            HistoryEntry(
                timestamp=local_now(),
                action="APPROVAL_REQUEST_SENT",
                detail=f"{kind}: {rendered.subject}",
                user=current_user(self._settings_store.read()),
            )
        )
        self._metadata_store.write(path, metadata)
        self._start_worker(job)
        return _ok({"status": "polling", "job_id": job["job_id"], "subject": rendered.subject})

    def stop(self, project_path: Path, kind: str) -> dict[str, Any]:
        path = Path(project_path)
        job = self._cache.latest_approval_job(str(path), kind)
        if job is None or job["status"] != "polling":
            return _ok({"status": "not_polling"})
        worker = self._workers.pop(str(job["job_id"]), None)
        if worker is not None:
            worker.stop()
        self._cache.update_approval_job(str(job["job_id"]), status="stopped")
        return _ok({"status": "stopped"})

    def resume_pending(self) -> None:
        """Restart workers for jobs still 'polling' after an app restart."""
        if not outlook_client.IS_WINDOWS:
            return
        for job in self._cache.list_polling_approval_jobs():
            sent_at = datetime.fromisoformat(str(job["sent_at"]))
            max_seconds = self._settings_store.read().approval_polling_max_hours * 3600
            if (datetime.now() - sent_at).total_seconds() >= max_seconds:
                self._on_timeout(job)
                continue
            self._start_worker(job)

    def shutdown(self) -> None:
        for worker in self._workers.values():
            worker.stop()
        self._workers.clear()

    def _start_worker(self, job: dict[str, Any]) -> None:
        settings = self._settings_store.read()
        config = REQUEST_KINDS[str(job["request_type"])]
        target = Path(str(job["project_path"])) / "_cr-docs" / config["msg_file"]
        sent_at = datetime.fromisoformat(str(job["sent_at"]))
        elapsed = max(0.0, (datetime.now() - sent_at).total_seconds())
        remaining = max(60, int(settings.approval_polling_max_hours * 3600 - elapsed))
        worker = ApprovalPollingWorker(
            job=job,
            target_msg=target,
            poll_interval_seconds=settings.approval_polling_interval_minutes * 60,
            timeout_seconds=remaining,
            on_found=self._on_found,
            on_timeout=self._on_timeout,
            on_warning=self._on_warning,
        )
        self._workers[str(job["job_id"])] = worker
        worker.start()

    def _on_found(self, job: dict[str, Any], subject: str) -> None:
        self._workers.pop(str(job["job_id"]), None)
        self._cache.update_approval_job(
            str(job["job_id"]), status="completed", reply_received_at=local_now().replace(tzinfo=None).isoformat()
        )
        if self._notification_service:
            self._notification_service.add(
                type="SUCCESS",
                title="Approval received",
                message=f"Reply for {job['cr_number']} saved to _cr-docs ({REQUEST_KINDS[str(job['request_type'])]['msg_file']})",
                project_path=Path(str(job["project_path"])),
            )

    def _on_timeout(self, job: dict[str, Any]) -> None:
        self._workers.pop(str(job["job_id"]), None)
        self._cache.update_approval_job(str(job["job_id"]), status="timeout")
        if self._notification_service:
            self._notification_service.add(
                type="WARNING",
                title="Approval polling timeout",
                message=f"No reply for {job['cr_number']} within the polling window",
                project_path=Path(str(job["project_path"])),
            )

    def _on_warning(self, job: dict[str, Any], message: str) -> None:
        print(f"[approval-polling] WARN {job['job_id']}: {message}")


_ACTIVE_SERVICE: ApprovalPollingService | None = None


def register_approval_polling_service(service: ApprovalPollingService) -> None:
    global _ACTIVE_SERVICE
    _ACTIVE_SERVICE = service


def shutdown_approval_polling_service() -> None:
    if _ACTIVE_SERVICE is not None:
        _ACTIVE_SERVICE.shutdown()
