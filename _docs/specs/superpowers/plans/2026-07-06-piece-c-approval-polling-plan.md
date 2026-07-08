# Piece C Approval Polling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. This plan is written so ANY executor model produces the same result: every step contains the exact code to write. Do NOT redesign, rename, "improve", or reorder anything. If a step's exact `old_string` anchor is missing, STOP and report — do not guess.

**Goal:** Conditional "Send Request UAT Approval" / "Send Request LV" buttons in Project Details with per-project automation toggle, Outlook email send via per-project templates, background inbox polling for the reply, auto-download of the reply as `.msg` into `_cr-docs/`, persisted/resumable jobs, template editor in Automations, polling config in Settings.

**Architecture:** New `services/approval_polling_service.py` owns conditions, template resolution, send, polling workers (adapted from the proven `DownloadEmailWorker` COM pattern), and SQLite job persistence. Email rendering reuses `EmailService.render_email_template` by wrapping approval templates in `EmailCategorySettings`. Bridge follows the existing `JsApi` protocol + `ok()/fail()` pattern. Frontend follows existing `callBridge` + `$state` patterns.

**Tech Stack:** Python 3.12, pywin32 COM (guarded, Windows-only), SQLite (`CacheDb`), Svelte 5 + TS, pywebview bridge.

**Spec:** `_docs/specs/superpowers/specs/2026-07-02-approval-automation-design.md` + master plan Branch 3 section (`_docs/specs/superpowers/plans/2026-07-04-completion-master-plan.md`).

## Global Constraints

- Branch `automations/approval-polling` (already created from `main`). Repo root `D:/Ibrahim/Projects/project_tracker`. All commands from repo root.
- **No new Python test files** (user hard rule). Extend ONLY: `tests/test_phase_c_automation_service.py`, `tests/test_phase_b_cache_db.py`, `tests/test_phase_c_js_api_automations.py`, `tests/test_email_service_render.py`.
- New Python runtime file allowed: `services/approval_polling_service.py` only. New frontend component allowed: `frontend/src/lib/components/ApprovalTemplates.svelte` only.
- COM only on background threads with `pythoncom.CoInitialize()` / `CoUninitialize()` (copy the existing worker pattern exactly). Never on the pywebview main thread.
- Every bridge method returns `{ok, data, error}` via existing `ok()`/`fail()` helpers in `web/js_api.py`.
- Off-Windows: never execute COM; return dev-skipped responses mirroring `download_emails`.
- Run pytest with TEMP redirected if `pytest-of-unknown\pytest-current` PermissionError appears:
  `$env:TEMP='<any writable temp dir>'; $env:TMP=$env:TEMP;` then rerun.
- Known pre-existing failures (NOT yours, do not fix): `tests/test_phase_c_js_api_project.py::test_project_list_returns_converted_rows`, `test_year_create.py` (2), `test_phase_d_app_web_project_service_adapter.py` — they fail on `main` too.
- Never run `npm --prefix frontend run build` while the app may be open; ask the user to close it and wait for the reply `closed`.
- Do NOT merge to main. Merge happens only after the user's manual `pass` + explicit merge instruction. Do not delete branches.

## Locked design decisions (do not revisit)

| Decision | Value |
| -------- | ----- |
| Request kinds | `"uat"` and `"lv"` (strings, used everywhere) |
| Template keys | `approval_templates["uat_approval"]` / `["lv_approval"]`; fields `to, cc, subject, body, mode` (`mode` ∈ `"draft"`/`"send"`, default `"draft"`) |
| Template fallback | project `metadata.approval_templates[key]` if non-empty dict, else `settings.default_approval_templates[key]`, else button disabled reason `"template_missing"` |
| Subject rule | resolved template `subject` MUST contain literal `{CR_NUMBER}`; else fail `APPROVAL_TEMPLATE_INVALID` |
| CR number | `extract_cr_number(metadata.cr_link)` from `core.rules`; empty → condition fails |
| Signoff files | UAT: `<project>/_cr-docs/uat-signoff.docx`; LV: `<project>/_cr-docs/prod-lv.docx`; condition = exists AND `st_size > 0` |
| Reply .msg target | UAT: `<project>/_cr-docs/uat-approval.msg`; LV: `<project>/_cr-docs/prod-approval.msg`; overwrite; Outlook `item.SaveAs(str(target), 3)` (3 = olMSG) |
| UAT conditions (ALL) | `project_type == ProjectType.CR`, `len(drone_tickets) >= 1`, at least one drone `drone_state == DroneState.PENDING_APPROVAL`, `cr_number` non-empty, `cr_state == CRState.PENDING_SUBMISSION`, uat-signoff size > 0 |
| LV conditions (ALL) | `project_type == ProjectType.CR`, (`cr_state == CRState.APPROVED` OR any drone `drone_state == DroneState.APPROVED`), `cr_number` non-empty, prod-lv size > 0 |
| Job persistence | SQLite table `approval_polling_jobs` in `CacheDb` (master-plan decision); statuses `polling / completed / timeout / stopped / dev_skipped`; resume on startup |
| Polling engine | dedicated worker thread per job (copy of `DownloadEmailWorker` loop shape), interval = `settings.approval_polling_interval_minutes * 60` s, timeout = `settings.approval_polling_max_hours * 3600` s; COM errors inside the loop log + retry next interval (do NOT stop) |
| Email match | inbox item where `cr_number.upper() in str(item.Subject).upper()` AND `item.ReceivedTime > sent_at` (naive local compare, same style as existing worker); first match wins |
| Toggle persistence | `metadata.automation_enabled` in `project_data.json` |
| Settings | `approval_polling_interval_minutes: int = 5` (clamp 1–60), `approval_polling_max_hours: int = 3` (clamp 1–24) |
| Bridge methods (8) | `get_approval_status`, `approval_set_enabled`, `send_uat_approval_request`, `send_lv_approval_request`, `stop_approval_polling`, `get_approval_template`, `update_approval_template`, `preview_approval_template` (first four names from spec §4) |
| PD UI | toggle + buttons in `.page-header-actions`, visible only when `detail && !isNonCr && mode !== "new"`; status text under header reuses `.cr-link-feedback` classes |
| Template editor | new `ApprovalTemplates.svelte` in a new 5th Automations tab `approval` label `Approval`; project dropdown (empty = edit global defaults via `update_settings`) |
| History | on successful send append `HistoryEntry(action="APPROVAL_REQUEST_SENT", detail="<kind>: <subject>")` |

---

### Task 1: Model fields

**Files:**
- Modify: `core/models.py`
- Test: `tests/test_phase_c_automation_service.py` (extend)

**Interfaces:**
- Produces: `ProjectMetadata.automation_enabled: bool`, `ProjectMetadata.approval_templates: dict`, `AppSettings.default_approval_templates: dict`, `AppSettings.approval_polling_interval_minutes: int`, `AppSettings.approval_polling_max_hours: int` — all round-trip through `from_dict`/`to_dict`.

- [ ] **Step 1: Write the failing test.** Append to `tests/test_phase_c_automation_service.py`:

```python
def test_piece_c_model_fields_round_trip():
    from core.models import AppSettings, ProjectMetadata

    meta = ProjectMetadata.from_dict(
        {
            "automation_enabled": True,
            "approval_templates": {"uat_approval": {"to": "a@b", "subject": "UAT {CR_NUMBER}"}},
        }
    )
    assert meta.automation_enabled is True
    assert meta.approval_templates["uat_approval"]["to"] == "a@b"
    out = meta.to_dict()
    assert out["automation_enabled"] is True
    assert out["approval_templates"]["uat_approval"]["subject"] == "UAT {CR_NUMBER}"
    assert ProjectMetadata.from_dict({}).automation_enabled is False
    assert ProjectMetadata.from_dict({}).approval_templates == {}

    settings = AppSettings.from_dict(
        {
            "default_approval_templates": {"lv_approval": {"subject": "LV {CR_NUMBER}"}},
            "approval_polling_interval_minutes": 7,
            "approval_polling_max_hours": 2,
        }
    )
    assert settings.approval_polling_interval_minutes == 7
    assert settings.approval_polling_max_hours == 2
    assert settings.default_approval_templates["lv_approval"]["subject"] == "LV {CR_NUMBER}"
    out = settings.to_dict()
    assert out["approval_polling_interval_minutes"] == 7
    assert out["approval_polling_max_hours"] == 2
    defaults = AppSettings.from_dict({})
    assert defaults.approval_polling_interval_minutes == 5
    assert defaults.approval_polling_max_hours == 3
    assert defaults.default_approval_templates == {}
```

- [ ] **Step 2: Run it, expect FAIL** (`TypeError`/`AttributeError` on unknown fields):
`D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_phase_c_automation_service.py -k piece_c_model -q`

- [ ] **Step 3: Implement.** In `core/models.py`, `class ProjectMetadata` — after the dataclass field line `non_cr_state: NonCrState | None = None` add:

```python
    automation_enabled: bool = False
    approval_templates: dict[str, Any] = field(default_factory=dict)
```

In `ProjectMetadata.from_dict`, after the `non_cr_state=...` argument line add:

```python
            automation_enabled=bool(data.get("automation_enabled", False)),
            approval_templates=dict(data["approval_templates"]) if isinstance(data.get("approval_templates"), dict) else {},
```

In `ProjectMetadata.to_dict`, after the `"non_cr_state": ...` entry add:

```python
            "automation_enabled": self.automation_enabled,
            "approval_templates": self.approval_templates,
```

In `class AppSettings` — after `automation: AutomationSettings = field(default_factory=AutomationSettings)` add:

```python
    default_approval_templates: dict[str, Any] = field(default_factory=dict)
    approval_polling_interval_minutes: int = 5
    approval_polling_max_hours: int = 3
```

In `AppSettings.from_dict`, after the `automation=AutomationSettings.from_dict(...)` argument line add:

```python
            default_approval_templates=dict(data["default_approval_templates"]) if isinstance(data.get("default_approval_templates"), dict) else {},
            approval_polling_interval_minutes=int(data.get("approval_polling_interval_minutes", 5)),
            approval_polling_max_hours=int(data.get("approval_polling_max_hours", 3)),
```

In `AppSettings.to_dict`, after the `"automation": self.automation.to_dict(),` entry add:

```python
            "default_approval_templates": self.default_approval_templates,
            "approval_polling_interval_minutes": self.approval_polling_interval_minutes,
            "approval_polling_max_hours": self.approval_polling_max_hours,
```

- [ ] **Step 4: Run test, expect PASS**, then commit:

```powershell
git add -- core/models.py tests/test_phase_c_automation_service.py
git commit -m "feat(automations): piece c approval model fields"
```

### Task 2: SQLite job persistence

**Files:**
- Modify: `infrastructure/cache_db.py`
- Test: `tests/test_phase_b_cache_db.py` (extend)

**Interfaces:**
- Produces on `CacheDb`: `upsert_approval_job(row: dict) -> None`, `update_approval_job(job_id: str, status: str, reply_received_at: str | None = None) -> None`, `latest_approval_job(project_path: str, request_type: str) -> dict | None`, `list_polling_approval_jobs() -> list[dict]`.
- Row keys: `job_id, project_path, request_type, cr_number, email_subject, sent_at, status, reply_received_at`.

- [ ] **Step 1: Write the failing test.** Append to `tests/test_phase_b_cache_db.py` (reuse the file's existing `CacheDb` construction fixture style — a `tmp_path / "cache.db"` instance):

```python
def test_approval_polling_jobs_persist_and_resume(tmp_path):
    from infrastructure.cache_db import CacheDb

    cache = CacheDb(tmp_path / "cache.db")
    cache.initialize()
    assert cache.health_check() is True

    row = {
        "job_id": "j-1",
        "project_path": "C:/root/APP/2026/CR/UAT_PREPARE/CR-2026-001",
        "request_type": "uat",
        "cr_number": "CR-2026-001",
        "email_subject": "Request UAT Approval CR-2026-001",
        "sent_at": "2026-07-06T10:00:00",
        "status": "polling",
        "reply_received_at": None,
    }
    cache.upsert_approval_job(row)
    assert [j["job_id"] for j in cache.list_polling_approval_jobs()] == ["j-1"]

    latest = cache.latest_approval_job(row["project_path"], "uat")
    assert latest is not None and latest["status"] == "polling"

    cache.update_approval_job("j-1", status="completed", reply_received_at="2026-07-06T11:00:00")
    assert cache.list_polling_approval_jobs() == []
    latest = cache.latest_approval_job(row["project_path"], "uat")
    assert latest["status"] == "completed"
    assert latest["reply_received_at"] == "2026-07-06T11:00:00"
```

- [ ] **Step 2: Run it, expect FAIL** (no table / no methods):
`D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_phase_b_cache_db.py -k approval -q`

- [ ] **Step 3: Implement.** In `infrastructure/cache_db.py`:

(a) In `_create_schema`, after the `automation_rule_logs` `connection.execute(...)` block add:

```python
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS approval_polling_jobs (
                job_id TEXT PRIMARY KEY,
                project_path TEXT NOT NULL,
                request_type TEXT NOT NULL,
                cr_number TEXT NOT NULL DEFAULT '',
                email_subject TEXT NOT NULL DEFAULT '',
                sent_at TEXT,
                status TEXT NOT NULL DEFAULT 'polling',
                reply_received_at TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
```

(b) In `health_check`, the expected table set currently is:

```python
            and tables == {
                "project_index",
                "drone_tickets",
                "scan_warnings",
                "notifications",
                "automation_rule_logs",
            }
```

Add `"approval_polling_jobs",` to that set (CRITICAL: forgetting this makes health_check fail and forces cache rebuilds every startup).

(c) Add these methods to `class CacheDb` (place after the notifications-related methods; module-level, follow the `self._connect()` context-manager style used by every other method):

```python
    _APPROVAL_COLUMNS = (
        "job_id",
        "project_path",
        "request_type",
        "cr_number",
        "email_subject",
        "sent_at",
        "status",
        "reply_received_at",
    )

    def upsert_approval_job(self, row: dict[str, object]) -> None:
        values = tuple(row.get(column) for column in self._APPROVAL_COLUMNS)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO approval_polling_jobs
                    (job_id, project_path, request_type, cr_number, email_subject, sent_at, status, reply_received_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    status = excluded.status,
                    reply_received_at = excluded.reply_received_at
                """,
                values,
            )

    def update_approval_job(self, job_id: str, status: str, reply_received_at: str | None = None) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE approval_polling_jobs SET status = ?, reply_received_at = ? WHERE job_id = ?",
                (status, reply_received_at, job_id),
            )

    def latest_approval_job(self, project_path: str, request_type: str) -> dict[str, object] | None:
        with self._connect() as connection:
            row = connection.execute(
                f"SELECT {', '.join(self._APPROVAL_COLUMNS)} FROM approval_polling_jobs"
                " WHERE project_path = ? AND request_type = ?"
                " ORDER BY created_at DESC, job_id DESC LIMIT 1",
                (project_path, request_type),
            ).fetchone()
        if row is None:
            return None
        return dict(zip(self._APPROVAL_COLUMNS, row))

    def list_polling_approval_jobs(self) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT {', '.join(self._APPROVAL_COLUMNS)} FROM approval_polling_jobs WHERE status = 'polling'",
            ).fetchall()
        return [dict(zip(self._APPROVAL_COLUMNS, row)) for row in rows]
```

- [ ] **Step 4: Run the new test AND the whole cache_db file, expect PASS** (existing `health_check` tests in this file may assert the old table set — if one fails on the table list, update that assertion to include `approval_polling_jobs`; that is the only permitted existing-test edit):
`D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_phase_b_cache_db.py tests/test_persistence_logs_notifications.py -q`

- [ ] **Step 5: Commit:**

```powershell
git add -- infrastructure/cache_db.py tests/test_phase_b_cache_db.py
git commit -m "feat(automations): approval polling jobs table"
```

### Task 3: ApprovalPollingService

**Files:**
- Create: `services/approval_polling_service.py`
- Test: `tests/test_phase_c_automation_service.py` (extend)

**Interfaces:**
- Consumes: Task 1 fields, Task 2 CacheDb methods, `EmailService.render_email_template`, `outlook_client.create_draft_email/send_email/IS_WINDOWS`, `extract_cr_number`, `NotificationService.add`, `MetadataStore.read/write`, `SettingsStore.read`.
- Produces (used by Task 4 bridge):
  - `ApprovalPollingService(settings_store, metadata_store, email_service, cache, notification_service=None)`
  - `get_status(project_path: Path) -> dict`
  - `set_enabled(project_path: Path, enabled: bool) -> dict`
  - `send_request(project_path: Path, kind: str) -> dict`  (Bridge_Response)
  - `stop(project_path: Path, kind: str) -> dict`
  - `get_template(project_path: Path, kind: str) -> dict`
  - `update_template(project_path: Path, kind: str, template: dict) -> dict`
  - `preview_template(project_path: Path, kind: str, template: dict | None) -> dict`
  - `resume_pending() -> None`
  - `shutdown() -> None`

- [ ] **Step 1: Write the failing tests.** Append to `tests/test_phase_c_automation_service.py`:

```python
def _piece_c_service(tmp_path, monkeypatch=None):
    from infrastructure.cache_db import CacheDb
    from infrastructure.metadata_store import MetadataStore
    from services.approval_polling_service import ApprovalPollingService
    from services.email_service import EmailService

    class _FakeSettingsStore:
        def __init__(self):
            from core.models import AppSettings

            self.settings = AppSettings.from_dict(
                {
                    "default_approval_templates": {
                        "uat_approval": {"to": "boss@corp", "cc": "", "subject": "Request UAT Approval {CR_NUMBER}", "body": "Please approve {PROJECT_NAME}", "mode": "draft"},
                        "lv_approval": {"to": "boss@corp", "cc": "", "subject": "Request LV {CR_NUMBER}", "body": "LV for {PROJECT_NAME}", "mode": "draft"},
                    }
                }
            )

        def read(self):
            return self.settings

        def write(self, settings):
            self.settings = settings

    cache = CacheDb(tmp_path / "cache.db")
    cache.initialize()
    return ApprovalPollingService(
        settings_store=_FakeSettingsStore(),
        metadata_store=MetadataStore(),
        email_service=EmailService(),
        cache=cache,
    )


def _piece_c_project(tmp_path, *, drone_state="PENDING APPROVAL", cr_state="PENDING SUBMISSION", signoff=b"x", lv=b""):
    import json

    project = tmp_path / "CR-2026-001"
    docs = project / "_cr-docs"
    docs.mkdir(parents=True)
    if signoff is not None:
        (docs / "uat-signoff.docx").write_bytes(signoff)
    if lv is not None:
        (docs / "prod-lv.docx").write_bytes(lv)
    (project / "project_data.json").write_text(
        json.dumps(
            {
                "project_name": "CR-2026-001",
                "project_type": "CR",
                "cr_link": "https://jira/browse/CR-2026-001",
                "cr_state": cr_state,
                "drone_tickets": [{"drone_link": "", "drone_state": drone_state}],
                "automation_enabled": True,
            }
        ),
        encoding="utf-8",
    )
    return project


def test_piece_c_conditions_gate_uat_and_lv(tmp_path):
    service = _piece_c_service(tmp_path)

    eligible = _piece_c_project(tmp_path / "a")
    status = service.get_status(eligible)
    assert status["automation_enabled"] is True
    assert status["uat"]["eligible"] is True
    assert status["lv"]["eligible"] is False  # empty prod-lv + not approved

    empty_signoff = _piece_c_project(tmp_path / "b", signoff=b"")
    assert service.get_status(empty_signoff)["uat"]["eligible"] is False

    lv_ready = _piece_c_project(tmp_path / "c", cr_state="APPROVED", lv=b"x")
    assert service.get_status(lv_ready)["lv"]["eligible"] is True

    drone_approved_lv = _piece_c_project(tmp_path / "d", drone_state="APPROVED", lv=b"x")
    assert service.get_status(drone_approved_lv)["lv"]["eligible"] is True


def test_piece_c_send_validates_template_and_records_job(tmp_path, monkeypatch):
    import services.approval_polling_service as aps

    service = _piece_c_service(tmp_path)
    project = _piece_c_project(tmp_path / "a")

    sent: list[tuple] = []
    monkeypatch.setattr(aps.outlook_client, "IS_WINDOWS", True)
    monkeypatch.setattr(
        aps.outlook_client,
        "create_draft_email",
        lambda to, cc, subject, body, attachment_path=None: (sent.append((to, subject)) or {"ok": True, "data": {"status": "drafted"}, "error": None}),
    )
    monkeypatch.setattr(aps.ApprovalPollingService, "_start_worker", lambda self, job: None)

    result = service.send_request(project, "uat")
    assert result["ok"] is True
    assert sent and "CR-2026-001" not in "{CR_NUMBER}"
    assert "2026-001" in sent[0][1] or "CR-2026-001" in sent[0][1]

    job = service._cache.latest_approval_job(str(project), "uat")
    assert job is not None and job["status"] == "polling"

    status = service.get_status(project)
    assert status["uat"]["job"]["status"] == "polling"

    stopped = service.stop(project, "uat")
    assert stopped["ok"] is True
    assert service._cache.latest_approval_job(str(project), "uat")["status"] == "stopped"


def test_piece_c_send_rejects_subject_without_cr_placeholder(tmp_path):
    service = _piece_c_service(tmp_path)
    project = _piece_c_project(tmp_path / "a")
    service.update_template(project, "uat", {"to": "x@y", "cc": "", "subject": "no placeholder", "body": "b", "mode": "draft"})
    result = service.send_request(project, "uat")
    assert result["ok"] is False
    assert result["error"]["code"] == "APPROVAL_TEMPLATE_INVALID"


def test_piece_c_template_get_update_preview(tmp_path):
    service = _piece_c_service(tmp_path)
    project = _piece_c_project(tmp_path / "a")

    got = service.get_template(project, "uat")
    assert got["ok"] is True and got["data"]["source"] == "default"

    service.update_template(project, "uat", {"to": "me@corp", "cc": "", "subject": "UAT {CR_NUMBER}", "body": "hi {PROJECT_NAME}", "mode": "send"})
    got = service.get_template(project, "uat")
    assert got["data"]["source"] == "project" and got["data"]["template"]["to"] == "me@corp"

    preview = service.preview_template(project, "uat", None)
    assert preview["ok"] is True
    assert "CR-2026-001" in preview["data"]["body"] or "2026-001" in preview["data"]["subject"]
```

- [ ] **Step 2: Run them, expect FAIL** (module missing):
`D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_phase_c_automation_service.py -k piece_c -q`

- [ ] **Step 3: Create `services/approval_polling_service.py` with EXACTLY this content:**

```python
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
from core.rules import extract_cr_number
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
        try:
            rendered = self._render(metadata, resolved)
        except (UnresolvedPlaceholderError, TemplateConditionsNotMetError) as exc:
            return _fail(str(exc), "APPROVAL_TEMPLATE_INVALID")
        return _ok({"to": rendered.to, "cc": rendered.cc, "subject": rendered.subject, "body": rendered.body})

    def _render(self, metadata: ProjectMetadata, template: dict[str, Any]):
        category = EmailCategorySettings(
            to=str(template.get("to", "")),
            cc=str(template.get("cc", "")),
            subject_template=str(template.get("subject", "")),
            body_template=str(template.get("body", "")),
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
            rendered = self._render(metadata, template)
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
            HistoryEntry(timestamp=local_now(), action="APPROVAL_REQUEST_SENT", detail=f"{kind}: {rendered.subject}")
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
```

- [ ] **Step 4: Run the piece_c tests, expect PASS:**
`D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_phase_c_automation_service.py -k piece_c -q`

- [ ] **Step 5: Commit:**

```powershell
git add -- services/approval_polling_service.py tests/test_phase_c_automation_service.py
git commit -m "feat(automations): approval polling service"
```

### Task 4: Bridge methods + wiring

**Files:**
- Modify: `web/js_api.py`
- Modify: `app_web.py`
- Test: `tests/test_phase_c_js_api_automations.py` (extend)

**Interfaces:**
- Consumes: Task 3 service methods.
- Produces bridge methods (exact names, called by Task 5 frontend): `get_approval_status(project_path)`, `approval_set_enabled(project_path, enabled)`, `send_uat_approval_request(project_path)`, `send_lv_approval_request(project_path)`, `stop_approval_polling(project_path, request_type)`, `get_approval_template(project_path, kind)`, `update_approval_template(project_path, kind, template)`, `preview_approval_template(project_path, kind, template)`.

- [ ] **Step 1: Write the failing test.** Append to `tests/test_phase_c_js_api_automations.py` (follow the file's existing JsApi construction style):

```python
def test_approval_bridge_methods_delegate_and_guard():
    from web.js_api import JsApi

    class _FakeApproval:
        def __init__(self):
            self.calls = []

        def get_status(self, project_path):
            self.calls.append(("status", str(project_path)))
            return {"automation_enabled": True, "uat": {"eligible": False, "reasons": [], "job": None}, "lv": {"eligible": False, "reasons": [], "job": None}, "outlook_available": False}

        def set_enabled(self, project_path, enabled):
            return {"ok": True, "data": {"automation_enabled": bool(enabled)}, "error": None}

        def send_request(self, project_path, kind):
            return {"ok": True, "data": {"status": "polling", "kind": kind}, "error": None}

        def stop(self, project_path, kind):
            return {"ok": True, "data": {"status": "stopped"}, "error": None}

        def get_template(self, project_path, kind):
            return {"ok": True, "data": {"source": "default", "template": {}}, "error": None}

        def update_template(self, project_path, kind, template):
            return {"ok": True, "data": {"source": "project", "template": template}, "error": None}

        def preview_template(self, project_path, kind, template):
            return {"ok": True, "data": {"subject": "S"}, "error": None}

    fake = _FakeApproval()
    api = JsApi(dashboard_service=None, approval_service=fake)

    assert api.get_approval_status("C:/p")["ok"] is True
    assert api.approval_set_enabled("C:/p", True)["data"]["automation_enabled"] is True
    assert api.send_uat_approval_request("C:/p")["data"]["kind"] == "uat"
    assert api.send_lv_approval_request("C:/p")["data"]["kind"] == "lv"
    assert api.stop_approval_polling("C:/p", "uat")["data"]["status"] == "stopped"
    assert api.get_approval_template("C:/p", "uat")["ok"] is True
    assert api.update_approval_template("C:/p", "uat", {"to": "x"})["ok"] is True
    assert api.preview_approval_template("C:/p", "uat", None)["ok"] is True

    bare = JsApi(dashboard_service=None)
    assert bare.get_approval_status("C:/p")["ok"] is False
    assert bare.get_approval_status("C:/p")["error"]["code"] == "SERVICE_UNAVAILABLE"
```

- [ ] **Step 2: Run it, expect FAIL:**
`D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_phase_c_js_api_automations.py -k approval_bridge -q`

- [ ] **Step 3: Implement in `web/js_api.py`.**

(a) After the `class TeamsServiceProtocol` block (search `class TeamsServiceProtocol`), add a protocol:

```python
class ApprovalServiceProtocol(Protocol):
    """Piece C approval automation surface used by JsApi."""

    def get_status(self, project_path: Path) -> dict[str, object]:
        """Conditions + latest job per request kind."""

    def set_enabled(self, project_path: Path, enabled: bool) -> dict[str, object]:
        """Persist the per-project automation toggle."""

    def send_request(self, project_path: Path, kind: str) -> dict[str, object]:
        """Send an approval request email and start polling."""

    def stop(self, project_path: Path, kind: str) -> dict[str, object]:
        """Stop polling for a request kind."""

    def get_template(self, project_path: Path, kind: str) -> dict[str, object]:
        """Return the effective template + its source."""

    def update_template(self, project_path: Path, kind: str, template: dict[str, object]) -> dict[str, object]:
        """Persist a per-project template override."""

    def preview_template(self, project_path: Path, kind: str, template: dict[str, object] | None) -> dict[str, object]:
        """Render a template with real project data."""
```

(b) In `JsApi.__init__`, add parameter `approval_service: ApprovalServiceProtocol | None = None,` after `appcode_service...` and assign `self._approval_service = approval_service` with the other assignments.

(c) Add methods to `JsApi` (place next to `scheduler_entry_trigger`; every one follows the same guard shape):

```python
    def _approval_guard(self):
        if self._approval_service is None:
            return fail("approval_service is not configured", code="SERVICE_UNAVAILABLE")
        return None

    def get_approval_status(self, project_path: str) -> dict[str, object]:
        """Piece C: conditions + job status for both request kinds."""
        guard = self._approval_guard()
        if guard is not None:
            return guard
        try:
            return ok(_to_frontend_safe(self._approval_service.get_status(Path(project_path))))
        except Exception as exc:
            return fail(str(exc), code="APPROVAL_STATUS_FAILED")

    def approval_set_enabled(self, project_path: str, enabled: bool) -> dict[str, object]:
        """Piece C: persist the per-project automation toggle."""
        guard = self._approval_guard()
        if guard is not None:
            return guard
        try:
            return self._approval_service.set_enabled(Path(project_path), bool(enabled))
        except Exception as exc:
            return fail(str(exc), code="APPROVAL_TOGGLE_FAILED")

    def send_uat_approval_request(self, project_path: str) -> dict[str, object]:
        """Piece C: send the UAT approval request and start polling."""
        guard = self._approval_guard()
        if guard is not None:
            return guard
        try:
            return self._approval_service.send_request(Path(project_path), "uat")
        except Exception as exc:
            return fail(str(exc), code="APPROVAL_SEND_FAILED")

    def send_lv_approval_request(self, project_path: str) -> dict[str, object]:
        """Piece C: send the LV approval request and start polling."""
        guard = self._approval_guard()
        if guard is not None:
            return guard
        try:
            return self._approval_service.send_request(Path(project_path), "lv")
        except Exception as exc:
            return fail(str(exc), code="APPROVAL_SEND_FAILED")

    def stop_approval_polling(self, project_path: str, request_type: str) -> dict[str, object]:
        """Piece C: stop polling for one request kind."""
        guard = self._approval_guard()
        if guard is not None:
            return guard
        try:
            return self._approval_service.stop(Path(project_path), str(request_type))
        except Exception as exc:
            return fail(str(exc), code="APPROVAL_STOP_FAILED")

    def get_approval_template(self, project_path: str, kind: str) -> dict[str, object]:
        """Piece C: effective approval template + source."""
        guard = self._approval_guard()
        if guard is not None:
            return guard
        try:
            return self._approval_service.get_template(Path(project_path), str(kind))
        except Exception as exc:
            return fail(str(exc), code="APPROVAL_TEMPLATE_FAILED")

    def update_approval_template(self, project_path: str, kind: str, template: dict[str, object]) -> dict[str, object]:
        """Piece C: persist a per-project approval template."""
        guard = self._approval_guard()
        if guard is not None:
            return guard
        try:
            return self._approval_service.update_template(Path(project_path), str(kind), template)
        except Exception as exc:
            return fail(str(exc), code="APPROVAL_TEMPLATE_FAILED")

    def preview_approval_template(self, project_path: str, kind: str, template: dict[str, object] | None = None) -> dict[str, object]:
        """Piece C: render a template with real project data."""
        guard = self._approval_guard()
        if guard is not None:
            return guard
        try:
            return self._approval_service.preview_template(Path(project_path), str(kind), template)
        except Exception as exc:
            return fail(str(exc), code="APPROVAL_TEMPLATE_FAILED")
```

If `_to_frontend_safe` is not already imported/defined in scope of these methods, use the same helper the scheduler methods use (it exists — `scheduler_entry_trigger` calls it).

(d) In `app_web.py`:
- Import: add `from services.approval_polling_service import ApprovalPollingService` next to the other service imports.
- After `global_plan_svc = GlobalPlanService()` add:

```python
    approval_svc = ApprovalPollingService(
        settings_store=_settings_store,
        metadata_store=_metadata_store,
        email_service=email_svc,
        cache=cache_db,
        notification_service=notification_svc,
    )
    approval_svc.resume_pending()
```

IMPORTANT: `email_svc` must exist before this block. Find where `EmailService()` is constructed in `app_web.py` (search `EmailService(`) — if it is constructed later (e.g. inline in the JsApi wiring near line ~1877), move/define `email_svc = EmailService()` before `approval_svc` and pass the SAME instance to both places.
- In the `JsApi(...)` construction (search `DownloadEmailService(notification_service=notification_svc)` around line ~1877), add `approval_service=approval_svc,` as a keyword argument.
- In the shutdown path (search for the existing shutdown flush of `rte_document_service` / `shutdown` in `app_web.py`), add `approval_svc.shutdown()` alongside it.

- [ ] **Step 4: Run tests, expect PASS** (contract guard included):
`D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_phase_c_js_api_automations.py tests/test_bridge_contract_guard.py -q`

- [ ] **Step 5: Commit:**

```powershell
git add -- web/js_api.py app_web.py tests/test_phase_c_js_api_automations.py
git commit -m "feat(automations): approval bridge methods"
```

### Task 5: Frontend bridge wrappers

**Files:**
- Modify: `frontend/src/lib/bridge.ts`
- Modify: `frontend/src/lib/types.ts`

**Interfaces:**
- Produces (used by Tasks 6–7): `approvalGetStatus`, `approvalSetEnabled`, `sendUatApprovalRequest`, `sendLvApprovalRequest`, `stopApprovalPolling`, `getApprovalTemplate`, `updateApprovalTemplate`, `previewApprovalTemplate`, and types `ApprovalStatus`, `ApprovalTemplate`.

- [ ] **Step 1: Add types.** In `frontend/src/lib/types.ts`, append at the end:

```typescript
// ── Piece C approval automation ──
export interface ApprovalJob {
  job_id: string;
  project_path: string;
  request_type: "uat" | "lv";
  cr_number: string;
  email_subject: string;
  sent_at: string | null;
  status: "polling" | "completed" | "timeout" | "stopped" | "dev_skipped";
  reply_received_at: string | null;
}

export interface ApprovalKindStatus {
  eligible: boolean;
  reasons: string[];
  job: ApprovalJob | null;
}

export interface ApprovalStatus {
  automation_enabled: boolean;
  outlook_available: boolean;
  uat: ApprovalKindStatus;
  lv: ApprovalKindStatus;
}

export interface ApprovalTemplate {
  to: string;
  cc: string;
  subject: string;
  body: string;
  mode: "draft" | "send";
}
```

- [ ] **Step 2: Add wrappers.** In `frontend/src/lib/bridge.ts`, after the `exportToDocx` function block, add (import `ApprovalStatus`/`ApprovalTemplate` in the existing `types` import at the top of the file):

```typescript
// ── Piece C approval automation ──

export function approvalGetStatus(projectPath: string): Promise<BridgeResponse<ApprovalStatus>> {
  return callBridge("get_approval_status", projectPath);
}

export function approvalSetEnabled(projectPath: string, enabled: boolean): Promise<BridgeResponse<{ automation_enabled: boolean }>> {
  return callBridge("approval_set_enabled", projectPath, enabled);
}

export function sendUatApprovalRequest(projectPath: string): Promise<BridgeResponse<{ status: string; job_id?: string }>> {
  return callBridge("send_uat_approval_request", projectPath);
}

export function sendLvApprovalRequest(projectPath: string): Promise<BridgeResponse<{ status: string; job_id?: string }>> {
  return callBridge("send_lv_approval_request", projectPath);
}

export function stopApprovalPolling(projectPath: string, requestType: "uat" | "lv"): Promise<BridgeResponse<{ status: string }>> {
  return callBridge("stop_approval_polling", projectPath, requestType);
}

export function getApprovalTemplate(projectPath: string, kind: "uat" | "lv"): Promise<BridgeResponse<{ source: string; template: ApprovalTemplate }>> {
  return callBridge("get_approval_template", projectPath, kind);
}

export function updateApprovalTemplate(projectPath: string, kind: "uat" | "lv", template: ApprovalTemplate): Promise<BridgeResponse<{ source: string; template: ApprovalTemplate }>> {
  return callBridge("update_approval_template", projectPath, kind, template);
}

export function previewApprovalTemplate(projectPath: string, kind: "uat" | "lv", template: ApprovalTemplate | null): Promise<BridgeResponse<{ to: string; cc: string; subject: string; body: string }>> {
  return callBridge("preview_approval_template", projectPath, kind, template);
}
```

- [ ] **Step 3: Verify + commit:**

```powershell
npm --prefix frontend run check
git add -- frontend/src/lib/bridge.ts frontend/src/lib/types.ts
git commit -m "feat(automations): approval bridge wrappers"
```

Expected: `0 errors` (unused-export warnings are not emitted by svelte-check; if it reports the new imports unused, finish Task 6 before committing).

### Task 6: Project Details toggle + buttons

**Files:**
- Modify: `frontend/src/lib/components/ProjectDetails.svelte`
- Test: `frontend/tests/project-details-fase3-fase4.test.mjs` (extend)

**Interfaces:**
- Consumes: Task 5 wrappers.

Behavior contract:
- Block visible only when `detail && !isNonCr && mode !== "new"`.
- Toggle bound to `approvalStatus.automation_enabled`, persists via `approvalSetEnabled`, reloads status.
- Buttons visible only when toggle ON and `eligible` true OR a job exists (to show its state).
- Button label per state: eligible+no active job → `Send UAT Approval` / `Send LV`; job `polling` → `Waiting for reply…` (disabled) + a `Stop` mini button; `completed` → `Approval received ✓` (disabled); `timeout` → `No reply (timeout)` (clickable to resend when still eligible).
- While any job is `polling`, poll `approvalGetStatus` every 15 s; clear the interval on project change and destroy.

- [ ] **Step 1: Write the failing source-contract test.** Append to `frontend/tests/project-details-fase3-fase4.test.mjs`:

```javascript
test("ProjectDetails wires Piece C approval automation controls", () => {
  assert.match(PD, /approvalGetStatus|get_approval_status/);
  assert.match(PD, /approvalSetEnabled/);
  assert.match(PD, /sendUatApprovalRequest/);
  assert.match(PD, /sendLvApprovalRequest/);
  assert.match(PD, /stopApprovalPolling/);
  assert.match(PD, /Send UAT Approval/);
  assert.match(PD, /Send LV/);
  assert.match(PD, /Waiting for reply/);
  assert.match(PD, /clearInterval\(approvalPollTimer\)/);
});
```

Run and confirm FAIL:
`node --import ./frontend/tests/register-hooks.mjs --test --test-name-pattern "Piece C approval" ./frontend/tests/project-details-fase3-fase4.test.mjs`

- [ ] **Step 2: Script additions.** In `ProjectDetails.svelte` `<script>`:

(a) Extend the bridge import (find the existing `from "../bridge"` import) with: `approvalGetStatus, approvalSetEnabled, sendUatApprovalRequest, sendLvApprovalRequest, stopApprovalPolling`. Extend the types import with `ApprovalStatus`.

(b) After the `let isNonCr: boolean = $state(false);` line add:

```typescript
  // ── Piece C approval automation (spec 2026-07-02) ──
  let approvalStatus: ApprovalStatus | null = $state(null);
  let approvalBusy: "" | "uat" | "lv" | "toggle" = $state("");
  let approvalError = $state("");
  let approvalPollTimer: ReturnType<typeof setInterval> | undefined;

  function stopApprovalStatusPoll() {
    if (approvalPollTimer !== undefined) { clearInterval(approvalPollTimer); approvalPollTimer = undefined; }
  }

  async function loadApprovalStatus() {
    if (!selectedPath || isNonCr || !isPywebviewReady()) { approvalStatus = null; stopApprovalStatusPoll(); return; }
    const resp = await approvalGetStatus(selectedPath);
    if (!resp.ok) { approvalError = resp.error.message; return; }
    approvalStatus = resp.data ?? null;
    const polling = approvalStatus?.uat.job?.status === "polling" || approvalStatus?.lv.job?.status === "polling";
    if (polling && approvalPollTimer === undefined) {
      approvalPollTimer = setInterval(() => void loadApprovalStatus(), 15000);
    } else if (!polling) {
      stopApprovalStatusPoll();
    }
  }

  async function toggleApproval() {
    if (!selectedPath || !approvalStatus) return;
    approvalBusy = "toggle"; approvalError = "";
    const resp = await approvalSetEnabled(selectedPath, !approvalStatus.automation_enabled);
    if (!resp.ok) approvalError = resp.error.message;
    await loadApprovalStatus();
    approvalBusy = "";
  }

  async function sendApproval(kind: "uat" | "lv") {
    if (!selectedPath) return;
    approvalBusy = kind; approvalError = "";
    const resp = kind === "uat" ? await sendUatApprovalRequest(selectedPath) : await sendLvApprovalRequest(selectedPath);
    if (!resp.ok) approvalError = resp.error.message;
    await loadApprovalStatus();
    approvalBusy = "";
  }

  async function stopApproval(kind: "uat" | "lv") {
    if (!selectedPath) return;
    approvalBusy = kind; approvalError = "";
    const resp = await stopApprovalPolling(selectedPath, kind);
    if (!resp.ok) approvalError = resp.error.message;
    await loadApprovalStatus();
    approvalBusy = "";
  }
```

(c) Call `void loadApprovalStatus();` at the end of the existing detail-load success path — find where `isNonCr = detail ? detail.project_type === "NON_CR" : false;` is set (line ~273) and add `void loadApprovalStatus();` after that block's CR-docs load call (`if (detail && !isNonCr) await loadCrDocs();` region, line ~291 or ~625 — add it once, immediately after the `loadCrDocs()` call inside the same `if`). Also add `stopApprovalStatusPoll();` inside the reset path (the line `detail = null; isNonCr = false; ...` at ~233). Add `onDestroy(() => stopApprovalStatusPoll());` (import `onDestroy` from `svelte` if not imported).

- [ ] **Step 3: Template.** In the `.page-header-actions` div, immediately BEFORE `<div class="pd-command-spacer"></div>` add:

```svelte
      {#if detail && !isNonCr && mode !== "new" && approvalStatus}
        <label class="pd-command-field" for="pd-approval-toggle" title={approvalStatus.outlook_available ? "Approval automation" : "Outlook not configured"}>
          <span>Automation</span>
          <button id="pd-approval-toggle" type="button" class="pd-control pd-approval-toggle" class:on={approvalStatus.automation_enabled} disabled={approvalBusy === "toggle" || !approvalStatus.outlook_available} onclick={toggleApproval}>
            {approvalStatus.automation_enabled ? "ON" : "OFF"}
          </button>
        </label>
        {#if approvalStatus.automation_enabled}
          {#each [["uat", "Send UAT Approval"], ["lv", "Send LV"]] as [kind, label]}
            {@const ks = kind === "uat" ? approvalStatus.uat : approvalStatus.lv}
            {#if ks.eligible || ks.job}
              {#if ks.job?.status === "polling"}
                <button class="pd-command-btn" type="button" disabled>Waiting for reply…</button>
                <button class="pd-command-btn pd-command-danger" type="button" disabled={approvalBusy !== ""} onclick={() => stopApproval(kind as "uat" | "lv")}>Stop</button>
              {:else if ks.job?.status === "completed"}
                <button class="pd-command-btn" type="button" disabled>Approval received ✓</button>
              {:else}
                <button class="pd-command-btn" type="button" disabled={!ks.eligible || approvalBusy !== ""} title={ks.eligible ? "" : ks.reasons.join(", ")} onclick={() => sendApproval(kind as "uat" | "lv")}>
                  {ks.job?.status === "timeout" ? `${label} (retry)` : label}
                </button>
              {/if}
            {/if}
          {/each}
        {/if}
      {/if}
```

And after the `{:else if topActionState === "success"}` feedback block (after line `<p class="cr-link-feedback cr-link-ok">✓ Done</p>` and its `{/if}`), add:

```svelte
  {#if approvalError}
    <p class="cr-link-feedback cr-link-err">✗ {approvalError}</p>
  {/if}
```

- [ ] **Step 4: CSS.** In the component `<style>` block add:

```css
  .pd-approval-toggle { min-width: 44px; font-weight: 800; }
  .pd-approval-toggle.on { background: var(--soft-pink-surface); border-color: var(--primary-red); color: var(--primary-red); }
```

(Use existing tokens only; check the file's `<style>` — if it uses `--color-dbs-red` instead of `--primary-red`, match whatever the neighboring rules use.)

- [ ] **Step 5: Verify + commit:**

```powershell
node --import ./frontend/tests/register-hooks.mjs --test --test-name-pattern "Piece C approval" ./frontend/tests/project-details-fase3-fase4.test.mjs
npm --prefix frontend run check
git add -- frontend/src/lib/components/ProjectDetails.svelte frontend/tests/project-details-fase3-fase4.test.mjs
git commit -m "feat(automations): project details approval controls"
```

Expected: test PASS, svelte-check 0 errors 0 warnings.

### Task 7: Template editor tab + Settings fields

**Files:**
- Create: `frontend/src/lib/components/ApprovalTemplates.svelte`
- Modify: `frontend/src/lib/components/Automations.svelte`
- Modify: `frontend/src/lib/components/Settings.svelte`
- Test: `frontend/tests/components.test.mjs` (extend — follow its existing source-contract style)

- [ ] **Step 1: Failing test.** Append to `frontend/tests/components.test.mjs` (mirror how that file loads component sources; add a `readFileSync` constant for `ApprovalTemplates.svelte`, `Automations.svelte`, `Settings.svelte` if not present):

```javascript
test("Automations exposes Piece C approval template editor", () => {
  const AT = readFileSync(resolve(__dirname, "../src/lib/components/ApprovalTemplates.svelte"), "utf8");
  const AU = readFileSync(resolve(__dirname, "../src/lib/components/Automations.svelte"), "utf8");
  const ST = readFileSync(resolve(__dirname, "../src/lib/components/Settings.svelte"), "utf8");
  assert.match(AT, /getApprovalTemplate/);
  assert.match(AT, /updateApprovalTemplate/);
  assert.match(AT, /previewApprovalTemplate/);
  assert.match(AT, /\{CR_NUMBER\}/);
  assert.match(AU, /ApprovalTemplates/);
  assert.match(AU, /"approval"/);
  assert.match(ST, /approval_polling_interval_minutes/);
  assert.match(ST, /approval_polling_max_hours/);
});
```

Run, expect FAIL:
`node --import ./frontend/tests/register-hooks.mjs --test --test-name-pattern "approval template editor" ./frontend/tests/components.test.mjs`

- [ ] **Step 2: Create `frontend/src/lib/components/ApprovalTemplates.svelte`:**

```svelte
<script lang="ts">
  import { onMount } from "svelte";
  import { callBridge, getApprovalTemplate, isPywebviewReady, previewApprovalTemplate, updateApprovalTemplate } from "../bridge";
  import type { ApprovalTemplate } from "../types";

  type Kind = "uat" | "lv";
  const KINDS: { id: Kind; label: string; key: string }[] = [
    { id: "uat", label: "UAT Approval", key: "uat_approval" },
    { id: "lv", label: "LV Approval", key: "lv_approval" },
  ];
  const PLACEHOLDERS = "{CR_NUMBER} {PROJECT_NAME} {DRONE_TICKET} {START_DATETIME} {END_DATETIME}";
  const EMPTY: ApprovalTemplate = { to: "", cc: "", subject: "", body: "", mode: "draft" };

  type ProjectRow = { project_path: string; project_name: string };
  let projects: ProjectRow[] = $state([]);
  let selectedProject = $state("");
  let kind: Kind = $state("uat");
  let form: ApprovalTemplate = $state({ ...EMPTY });
  let source = $state("none");
  let status = $state("");
  let statusIsError = $state(false);
  let preview: { to: string; cc: string; subject: string; body: string } | null = $state(null);

  async function loadProjects() {
    if (!isPywebviewReady()) return;
    const resp = await callBridge<ProjectRow[]>("project_list");
    if (resp.ok && Array.isArray(resp.data)) projects = resp.data;
  }

  async function loadTemplate() {
    preview = null; status = ""; statusIsError = false;
    if (!selectedProject) {
      // Global defaults live in settings.default_approval_templates.
      const resp = await callBridge<{ default_approval_templates?: Record<string, ApprovalTemplate> }>("get_settings");
      const key = KINDS.find((k) => k.id === kind)!.key;
      form = { ...EMPTY, ...(resp.ok ? resp.data?.default_approval_templates?.[key] : undefined) };
      source = "global default";
      return;
    }
    const resp = await getApprovalTemplate(selectedProject, kind);
    if (!resp.ok) { status = resp.error.message; statusIsError = true; return; }
    form = { ...EMPTY, ...resp.data?.template };
    source = resp.data?.source ?? "none";
  }

  async function save() {
    status = ""; statusIsError = false;
    if (!form.subject.includes("{CR_NUMBER}")) { status = "Subject must contain {CR_NUMBER}"; statusIsError = true; return; }
    if (!selectedProject) {
      const key = KINDS.find((k) => k.id === kind)!.key;
      const current = await callBridge<{ default_approval_templates?: Record<string, ApprovalTemplate> }>("get_settings");
      const defaults = { ...(current.ok ? current.data?.default_approval_templates : {}) , [key]: { ...form } };
      const resp = await callBridge("update_settings", { default_approval_templates: defaults });
      status = resp.ok ? "Saved global default" : resp.error.message;
      statusIsError = !resp.ok;
    } else {
      const resp = await updateApprovalTemplate(selectedProject, kind, { ...form });
      status = resp.ok ? "Saved for project" : resp.error.message;
      statusIsError = !resp.ok;
    }
    if (!statusIsError) await loadTemplate();
  }

  async function doPreview() {
    status = ""; statusIsError = false;
    if (!selectedProject) { status = "Pick a project to preview with real data"; statusIsError = true; return; }
    const resp = await previewApprovalTemplate(selectedProject, kind, { ...form });
    if (!resp.ok) { status = resp.error.message; statusIsError = true; return; }
    preview = resp.data ?? null;
  }

  onMount(() => { loadProjects(); loadTemplate(); });
</script>

<div class="apt-root">
  <div class="apt-row">
    <label class="field"><span>Project (empty = global default)</span>
      <select class="input" bind:value={selectedProject} onchange={loadTemplate}>
        <option value="">Global defaults</option>
        {#each projects as p}<option value={p.project_path}>{p.project_name}</option>{/each}
      </select>
    </label>
    <div class="apt-tabs">
      {#each KINDS as k}
        <button type="button" class="sb-tab" class:active={kind === k.id} onclick={() => { kind = k.id; void loadTemplate(); }}>{k.label}</button>
      {/each}
    </div>
  </div>
  <p class="apt-source">Editing: <strong>{source}</strong> · Placeholders: <code>{PLACEHOLDERS}</code></p>
  <label class="field"><span>To</span><input class="input" bind:value={form.to} /></label>
  <label class="field"><span>CC</span><input class="input" bind:value={form.cc} /></label>
  <label class="field"><span>Subject (must contain {"{CR_NUMBER}"})</span><input class="input" bind:value={form.subject} /></label>
  <label class="field"><span>Body</span><textarea class="input apt-body" rows="6" bind:value={form.body}></textarea></label>
  <label class="field"><span>Mode</span>
    <select class="input" bind:value={form.mode}><option value="draft">Draft (open in Outlook)</option><option value="send">Send immediately</option></select>
  </label>
  <div class="apt-actions">
    <button type="button" class="pd-command-btn" onclick={save}>Save template</button>
    <button type="button" class="pd-command-btn" onclick={doPreview}>Preview with real data</button>
    {#if status}<span class="cr-link-feedback" class:cr-link-err={statusIsError} class:cr-link-ok={!statusIsError}>{status}</span>{/if}
  </div>
  {#if preview}
    <div class="apt-preview">
      <p><strong>To:</strong> {preview.to} <strong>CC:</strong> {preview.cc}</p>
      <p><strong>Subject:</strong> {preview.subject}</p>
      <pre>{preview.body}</pre>
    </div>
  {/if}
</div>

<style>
  .apt-root { display: flex; flex-direction: column; gap: 8px; }
  .apt-row { display: flex; gap: 12px; align-items: flex-end; flex-wrap: wrap; }
  .apt-tabs { display: flex; gap: 4px; }
  .apt-source { font-size: 12px; color: var(--text-secondary); margin: 0; }
  .apt-body { resize: vertical; font-family: inherit; }
  .apt-actions { display: flex; gap: 8px; align-items: center; }
  .apt-preview { border: 1px solid var(--light-border); border-radius: 6px; padding: 10px; font-size: 12px; }
  .apt-preview pre { white-space: pre-wrap; margin: 4px 0 0; font-family: inherit; }
</style>
```

If `project_list` requires a year argument in this codebase (check `tests/test_phase_c_js_api_project.py::test_project_list_returns_converted_rows` for its signature), call it the same way ProjectDetails does — reuse the exact bridge call ProjectDetails uses to fill its project selector.

- [ ] **Step 3: Automations tab.** In `Automations.svelte`:
- `import ApprovalTemplates from "./ApprovalTemplates.svelte";`
- Change `type TabId = "outlook" | "teams" | "reminder" | "rules";` to `type TabId = "outlook" | "teams" | "reminder" | "rules" | "approval";`
- Add `{ id: "approval", label: "Approval" },` after the `rules` entry in `tabs`.
- In the template, change the final `{:else}` branch to `{:else if activeTab === "rules"}` and append:

```svelte
    {:else}
      <div class="panel-card accent" style="flex:1"><div class="panel-title-row"><span class="panel-title-icon">✉</span><span class="panel-title">Approval Templates</span><span class="panel-subtitle">Piece C — UAT/LV request emails + polling</span></div><ApprovalTemplates /></div>
```

(The existing `{:else}` body for Rules keeps its content under the new `{:else if activeTab === "rules"}`.)

- [ ] **Step 4: Settings fields.** In `Settings.svelte`:
- Add to `FORM_FIELDS`: `{ key: "approval_polling_interval_minutes", card: "behavior" },` and `{ key: "approval_polling_max_hours", card: "behavior" },`
- Add validation next to the existing `t10` numeric validation:

```typescript
    const pollMin = Number(form["approval_polling_interval_minutes"]);
    if (!Number.isInteger(pollMin) || pollMin < 1 || pollMin > 60) errors["approval_polling_interval_minutes"] = "1–60 minutes";
    const pollMax = Number(form["approval_polling_max_hours"]);
    if (!Number.isInteger(pollMax) || pollMax < 1 || pollMax > 24) errors["approval_polling_max_hours"] = "1–24 hours";
```

(Match the file's actual validation pattern — if it does not use an `errors` map, mirror exactly what the `t10_threshold_days` check does, including how it blocks save.)
- Add two labeled number inputs next to the T-10 field, following its exact markup:

```svelte
            <label class="field"><span>Approval polling interval (minutes)</span><input class="input" type="number" min="1" max="60" value={String(form["approval_polling_interval_minutes"] ?? 5)} oninput={(e) => handleFieldChange("approval_polling_interval_minutes", (e.target as HTMLInputElement).value)} /></label>
            <label class="field"><span>Approval polling max duration (hours)</span><input class="input" type="number" min="1" max="24" value={String(form["approval_polling_max_hours"] ?? 3)} oninput={(e) => handleFieldChange("approval_polling_max_hours", (e.target as HTMLInputElement).value)} /></label>
```

- [ ] **Step 5: Verify + commit:**

```powershell
node --import ./frontend/tests/register-hooks.mjs --test --test-name-pattern "approval template editor" ./frontend/tests/components.test.mjs
npm --prefix frontend run check
git add -- frontend/src/lib/components/ApprovalTemplates.svelte frontend/src/lib/components/Automations.svelte frontend/src/lib/components/Settings.svelte frontend/tests/components.test.mjs
git commit -m "feat(automations): approval template editor and polling settings"
```

### Task 8: Full verification, docs sync, build gate, manual gate

- [ ] **Step 1: Full verification:**

```powershell
npm --prefix frontend run check
node --import ./frontend/tests/register-hooks.mjs --test ./frontend/tests/*.test.mjs
D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_phase_c_automation_service.py tests/test_phase_b_cache_db.py tests/test_phase_c_js_api_automations.py tests/test_bridge_contract_guard.py tests/test_email_service_render.py -q
D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/ -q
```

Expected: svelte-check 0/0; frontend suite all pass; targeted pytest all pass; full pytest only the known pre-existing failures.

- [ ] **Step 2: App smoke** (backend wiring check): `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m main` — watch startup stderr ~15 s, stop. No tracebacks allowed.

- [ ] **Step 3: Docs sync (commit separately):**
- `_docs/DECISIONS.md`: add row `D-0013 | 2026-07-06 (or actual date) | Piece C approval automation: per-project automation_enabled + approval_templates in project_data.json; polling jobs persisted in SQLite approval_polling_jobs (resume on startup); reply matched by CR number in subject + received-after-sent; .msg saved via Outlook SaveAs olMSG into _cr-docs/ | Spec 2026-07-02 approved; SQLite chosen by master plan for job state (job state is operational, cache stays rebuildable — a lost job row only stops an in-flight poll) | LOCKED`
- `PRD.md` §16 (Automations): document toggle, conditional buttons, templates (per-project + global defaults), polling interval/max, .msg download targets.
- `_docs/PROGRESS.md`: Piece C row → implemented, awaiting user manual check; `_docs/session-notes.md`: new entry (branch, changed files, next).
- Commit: `git commit -m "docs(automations): sync piece c approval polling"`.

- [ ] **Step 4: Build gate.** Ask the user EXACTLY: `Tutup app Project Tracker dulu. Balas 'closed', nanti aku build Piece C dan kasih checklist manual.` After `closed`: `npm --prefix frontend run build`.

- [ ] **Step 5: Manual checklist (give in Indonesian):** toggle ON/OFF per project persists; UAT button appears ONLY when all 6 conditions met (test each: no drone, drone not PENDING APPROVAL, no CR number, CR state wrong, uat-signoff empty); click → Outlook draft/send appears with CR number in subject; status "Waiting for reply…" + Stop works; reply email (send yourself a mail containing the CR number) → `_cr-docs/uat-approval.msg` appears + notification; timeout after configured hours (set 1 minute interval / test with small max for verification); LV button same with prod-lv/APPROVED; restart app while polling → polling resumes; template editor saves per-project + global default + preview; Settings fields validate 1–60/1–24; regression: Dashboard, Project Details editors, Automations other tabs normal.

- [ ] **Step 6:** If user reports failure → fix on this branch, re-verify, repeat gate. If `pass` → rerun Step 1 verification fresh, then STOP and ask the user for merge approval. Never merge without it.

## Self-Review

- Spec coverage: toggle, both buttons + all conditions, templates + placeholders + defaults, polling interval/max settings, CR-number+timestamp matching, .msg SaveAs targets, job persistence + restart resume, error table (Outlook missing → `outlook_available` disables toggle; template missing → reason `template_missing`; send fail → error surfaced, no job; COM error → retry next interval; multiple matches → first wins; empty signoff → ineligible), tests, UI positions per spec, out-of-scope respected.
- Placeholder scan: none — every step has full code. One deliberate `ponytail:` reduction is explicitly instructed (`_already_elapsed` → `return 0.0`).
- Type consistency: `kind`/`request_type` strings `"uat"|"lv"` everywhere; template field names `to/cc/subject/body/mode` everywhere; bridge names match between `JsApi`, `bridge.ts`, and tests.
