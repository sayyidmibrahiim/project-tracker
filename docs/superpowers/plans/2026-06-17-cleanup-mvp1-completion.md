# Cleanup & MVP-1 Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clean, fix, align, package Project Tracker DBS to MVP-1 shippable state without PRD/code drift.

**Architecture:** Keep Svelte UI thin and UI-state-only. Route frontend calls through typed pywebview `JsApi`, service adapters, Python services, core domain, and infrastructure. Filesystem + per-project JSON remain canonical; SQLite stays cache/partial local persistence exactly as documented.

**Tech Stack:** Python 3.12+ / current Windows Python 3.14, pywebview, Svelte 5, TypeScript, Vite 6, Tailwind v4, SQLite, APScheduler, PyInstaller.

---

## Non-Negotiable Working Rules

- Use graphify first for codebase orientation: `graphify query "<question>"` before raw grep/read. Raw reads allowed for exact edit lines.
- Git is local tooling only. Do not commit unless user asks or delegate-agent workflow needs checkpoint. No upload/push.
- Edit inline. Avoid conflicting parallel edits. Only tracking files may change continuously (`PROJECT_STATUS.md`, this plan).
- After every phase/significant code change:
  1. Run tests/build relevant to changed area.
  2. Run app with `.\.venv\Scripts\python.exe -m project_tracker.main` or `python -m project_tracker.main`.
  3. Give user manual checklist.
  4. Live-monitor stdout/stderr for traceback/errors while user tests.
  5. Report monitor findings + user feedback.
- Hard delete forbidden for app behavior. For repo junk cleanup, remove only generated probe/log artifacts and only after inspecting status.
- No new deps unless PRD-approved or explicitly confirmed. P0-6 likely stale; verify before adding sqlalchemy.

---

## File Structure / Ownership Map

### Tracking / docs

- Modify: `PROJECT_STATUS.md` — phase status, commands run, pass/fail, manual-test notes.
- Modify: `docs/superpowers/specs/2026-06-16-cleanup-mvp1-completion-design.md` — already updated with R1-R4.
- Create/modify: `docs/windows-manual-test-checklist.md` — manual RC checklist for MVP-1.
- Modify: `PRD.md` — reconcile documented truth: H-10, entry point, menu scope, Tailwind/Vite/pywebview versions, SQLite partial truth.
- Modify/create: `docs/adr/ADR-002*.md` or current ADR file — SQLite partial truth/cache statement.

### Packaging / deps

- Modify: `pyproject.toml` — sync runtime deps with `requirements.txt`, remove PyQt6/watchdog once watchdog-out task lands, add `[build-system]`.
- Modify: `requirements.txt` — remove `watchdog>=4.0.0` when `watchdog_service.py` removed.
- Modify: `project_tracker_dbs.spec` — hidden imports for lazy Windows integrations; `upx=False`.
- Modify: `WINDOWS_SETUP.md` — entry point + build instructions only if drift found.

### Backend correctness

- Modify: `project_tracker/app_web.py`
  - `_ProjectServiceAdapter.get_project()` include `history`, `implementation_plan`.
  - `_ProjectServiceAdapter.open_folder()` wire to infrastructure `open_folder()`.
  - `_ProjectServiceAdapter.create_subproject()` wire to filesystem/project service pattern.
  - `_NotesServiceAdapter.update_notes()` atomic write.
  - Remove dead `AppAPI` after JsApi path confirmed.
- Modify: `project_tracker/web/js_api.py`
  - Keep stable response objects.
  - `notification_dismiss_all()` can call real service method after P2-26.
- Modify: `project_tracker/services/scheduler_service.py`
  - Deduplicate `_create_scheduler_safe()`.
  - Verify no `SQLAlchemyJobStore` import; no sqlalchemy dep if absent.
- Modify: `project_tracker/core/rules.py`
  - Fix `drone_state` condition to evaluate all drone tickets.
- Modify: `project_tracker/core/models.py`
  - Resolve `ProjectMetadata.notes` dead field: preferred remove from dataclass because notes live in `notes.md`; do not persist notes in `project_data.json`.
- Modify: `project_tracker/services/notification_service.py`
  - Add `dismiss_all()`.
- Modify: `project_tracker/services/second_brain_service.py`
  - Replace `flags["pinned"]` / `flags["favorite"]` with `.get(..., False)`.
- Modify/Create: `project_tracker/services/signals.py`
  - Shared `Signal` if dedup done.
- Delete only with explicit phase step: `project_tracker/infrastructure/watchdog_service.py`, `project_tracker/services/outlook_service.py` after verifying no imports.

### Frontend MVP-1

- Modify: `frontend/src/lib/components/ProjectDetails.svelte`
  - Start/end datetime editor.
  - `implementation_plan` editor.
  - Activity History rendering from `project_get().data.history`.
- Modify: frontend API types wherever project detail shape is declared.
- Test: `frontend/tests/components.test.mjs`, add/extend for Project Details fields if current harness supports it.

### Tests

- Add/modify targeted Python tests under `tests/`:
  - `tests/test_phase_d_app_web_project_details_read_wiring.py`
  - `tests/test_phase_d_app_web_project_actions_wiring.py`
  - `tests/test_rules_engine_unit.py` or existing rules tests
  - `tests/test_scheduler_entries_unit.py`
  - `tests/test_phase_c_notification_service_events.py`
  - `tests/test_second_brain_service.py` / existing second brain tests
  - packaging smoke tests if present; otherwise manual packaging gate.

---

## Phase 0 — Working Tree Hygiene & Baseline

**Goal:** Remove generated junk, protect future junk, record baseline, avoid touching user frontend work.

**Files:**

- Modify: `.gitignore`
- Modify: `PROJECT_STATUS.md`
- Remove from working tree: `_memprobe.py`, `_memprobe2.py`, `_probe3.py`, `_app_stdout.txt`, `_app_stderr.txt`
- Inspect only: `project_data.json`

### Task 0.1: Baseline status and tests

- [ ] Run graphify orientation.

```powershell
graphify query "working tree hygiene project_data root junk artifacts"
```

Expected: scoped nodes or no useful result; continue with exact status.

- [ ] Run status.

```powershell
git status --short
```

Expected: shows existing frontend modifications + junk files. Do not revert frontend files.

- [ ] Run backend baseline.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q
```

Expected baseline from prior session: `1724 passed, 20 skipped` or newer pass count. If fail, stop and fix only regression blocker.

- [ ] Run frontend baseline.

```powershell
npm --prefix frontend run build
```

Expected: Vite build succeeds.

### Task 0.2: Ignore generated probe/log/root metadata artifacts

- [ ] Read `.gitignore`.
- [ ] Add exact entries if missing:

```gitignore
# Claude/debug probe artifacts
_memprobe*.py
_probe*.py
_app_stdout.txt
_app_stderr.txt

# Root-level accidental metadata; canonical metadata is per-project project_data.json.
/project_data.json
```

- [ ] Remove only generated probe/log files from disk.

```powershell
Remove-Item -LiteralPath _memprobe.py,_memprobe2.py,_probe3.py,_app_stdout.txt,_app_stderr.txt -Force -Confirm:$false
```

Expected: probe/log files gone. `project_data.json` remains unless user explicitly approves removal.

- [ ] Verify.

```powershell
git status --short
```

Expected: no `_memprobe*`, `_probe*`, `_app_*` untracked. `project_data.json` ignored or still visible until `.gitignore` applied.

### Task 0.3: Update PROJECT_STATUS phase record

- [ ] Add Phase 0 entry to `PROJECT_STATUS.md`:

```markdown
## 2026-06-17 — Cleanup MVP-1 Phase 0

Status: in progress

Baseline:

- Backend tests: `<paste result>`
- Frontend build: `<paste result>`
- Working tree: frontend changes preserved; generated probe/log files removed; root project_data.json ignored pending user decision.

Next:

- Phase 1 crash bugs.
```

- [ ] Run graph update.

```powershell
graphify update .
```

Expected: graph rebuild/update succeeds.

### Task 0.4: Phase 0 app/manual gate

- [ ] Run app with monitor output redirected.

```powershell
.\.venv\Scripts\python.exe -m project_tracker.main *> _app_live_phase0.log
```

Expected: app opens WebView. Keep process running while user tests.

- [ ] User checklist:
  - App launches.
  - Dashboard visible.
  - Existing project rows visible.
  - No traceback in `_app_live_phase0.log`.

- [ ] Stop app after user check. Read `_app_live_phase0.log`; report errors.

---

## Phase 1 — Crash Bugs (P0-7, P0-5, P0-6, P0-8)

**Goal:** Remove known crash paths before feature work.

**Files:**

- Modify: `project_tracker/app_web.py`
- Modify: `project_tracker/services/scheduler_service.py`
- Modify: `project_tracker_dbs.spec`
- Test: `tests/test_phase_d_app_web_project_details_read_wiring.py`
- Test: `tests/test_phase_d_app_web_project_actions_wiring.py`
- Test: `tests/test_scheduler_entries_unit.py`

### Task 1.1: P0-7 test open_folder adapter no longer SERVICE_UNAVAILABLE

- [ ] Add/adjust test in `tests/test_phase_d_app_web_project_details_read_wiring.py`.

```python
def test_project_open_folder_wired_and_returns_ok(tmp_path, monkeypatch):
    import project_tracker.infrastructure.filesystem as filesystem
    from project_tracker.app_web import create_js_api

    opened: list[Path] = []
    monkeypatch.setattr(filesystem, "open_folder", lambda path: opened.append(Path(path)))

    api = create_js_api()
    project = temp_project(tmp_path)

    response = api.project_open_folder(str(project))

    assert response["ok"] is True
    assert opened == [project]
```

Expected initial result before implementation: FAIL or current behavior returns failure due `None` callable.

- [ ] Run targeted test.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_phase_d_app_web_project_details_read_wiring.py::test_project_open_folder_wired_and_returns_ok -v
```

Expected before fix: FAIL.

### Task 1.2: Implement `_ProjectServiceAdapter.open_folder()`

- [ ] In `project_tracker/app_web.py`, import filesystem module or function safely.

Use module import if monkeypatch tests need it:

```python
from project_tracker.infrastructure import filesystem
```

- [ ] Replace lines currently like:

```python
# ── unsupported: return None so JsApi returns SERVICE_UNAVAILABLE ──
open_folder = None  # type: ignore[assignment]
create_subproject = None  # type: ignore[assignment]
```

with:

```python
def open_folder(self, project_path: Path) -> object:
    path = Path(project_path)
    filesystem.open_folder(path)
    return {"project_path": path.as_posix(), "opened": True}
```

Leave `create_subproject` for next task, not `None` after Task 1.4.

- [ ] Run targeted test.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_phase_d_app_web_project_details_read_wiring.py::test_project_open_folder_wired_and_returns_ok -v
```

Expected: PASS.

### Task 1.3: P0-7 test create_subproject adapter

- [ ] Add test in `tests/test_phase_d_app_web_project_details_read_wiring.py`.

```python
def test_subproject_create_wired_and_creates_folder(tmp_path):
    from project_tracker.app_web import create_js_api

    api = create_js_api()
    project = temp_project(tmp_path)

    response = api.subproject_create(str(project), "Sub A")

    assert response["ok"] is True
    assert (project / "Sub A").is_dir()
    assert response["data"]["subproject"] == "Sub A"
```

Expected before fix: FAIL or SERVICE_UNAVAILABLE.

- [ ] Run targeted test.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_phase_d_app_web_project_details_read_wiring.py::test_subproject_create_wired_and_creates_folder -v
```

Expected before fix: FAIL.

### Task 1.4: Implement `_ProjectServiceAdapter.create_subproject()`

- [ ] In `project_tracker/app_web.py`, import `create_directory` if not present:

```python
from project_tracker.infrastructure.filesystem import create_directory
```

- [ ] Add method under `_ProjectServiceAdapter`:

```python
def create_subproject(self, project_path: Path, name: str) -> object:
    project = Path(project_path)
    target = project / name
    created = create_directory(project, target)
    return {"project_path": project.as_posix(), "subproject": created.name, "path": created.as_posix()}
```

Security rule: `create_directory(project, target)` calls `assert_within()`, so path traversal rejected.

- [ ] Run targeted test.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_phase_d_app_web_project_details_read_wiring.py::test_subproject_create_wired_and_creates_folder -v
```

Expected: PASS.

### Task 1.5: P0-5 dedupe `_create_scheduler_safe()`

- [ ] Edit `project_tracker/services/scheduler_service.py` to keep exactly one `_create_scheduler_safe()` definition, with this docstring:

```python
@classmethod
def _create_scheduler_safe(cls) -> Any | None:
    """Create the default scheduler, tolerating a missing apscheduler.

    On platforms/environments where ``apscheduler`` is not installed, return
    ``None`` so entry CRUD still works (job-management calls are
    getattr-guarded no-ops). ``start()`` re-attempts creation and surfaces a
    clear error if a scheduler is genuinely required.
    """
    try:
        return cls._create_scheduler()
    except Exception:  # noqa: BLE001 - optional runtime scheduler dependency
        return None
```

- [ ] Verify only one definition remains.

```powershell
python - <<'PY'
from pathlib import Path
text = Path('project_tracker/services/scheduler_service.py').read_text()
print(text.count('def _create_scheduler_safe'))
PY
```

Expected: `1`.

- [ ] Run scheduler tests.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_scheduler_entries_unit.py -q
```

Expected: PASS.

### Task 1.6: P0-6 verify SQLAlchemy stale before deps

- [ ] Search only after graphify orientation already done.

```powershell
python - <<'PY'
from pathlib import Path
for p in Path('project_tracker').rglob('*.py'):
    text = p.read_text(encoding='utf-8')
    if 'SQLAlchemyJobStore' in text or 'apscheduler.jobstores.sqlalchemy' in text:
        print(p)
PY
```

Expected from current read: no output. If no output, do NOT add sqlalchemy.

- [ ] Add note to `PROJECT_STATUS.md`:

```markdown
- P0-6 SQLAlchemy: verified stale; no `SQLAlchemyJobStore` import found; no dependency added.
```

### Task 1.7: P0-8 hidden imports + UPX off

- [ ] Modify `project_tracker_dbs.spec` hiddenimports to include exact list:

```python
hiddenimports = [
    "webview",
    "webview.platforms.edgechromium",
    "apscheduler",
    "apscheduler.schedulers.background",
    "dateutil",
    "send2trash",
    "pythoncom",
    "win32com.client",
    "pyperclip",
    "pyautogui",
]
```

- [ ] Ensure `EXE(... upx=False, ...)` or equivalent PyInstaller config disables UPX. If spec has `upx=True`, change to `upx=False`.

- [ ] Run spec syntax check.

```powershell
.\.venv\Scripts\python.exe -m py_compile project_tracker\main.py
```

Expected: no syntax errors.

### Task 1.8: Phase 1 verification + live app gate

- [ ] Run targeted tests.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_phase_d_app_web_project_details_read_wiring.py tests/test_scheduler_entries_unit.py -q
```

Expected: PASS.

- [ ] Run full backend tests.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q
```

Expected: PASS.

- [ ] Run frontend build if API shape changed impacts frontend types.

```powershell
npm --prefix frontend run build
```

Expected: PASS.

- [ ] Run app live monitor.

```powershell
.\.venv\Scripts\python.exe -m project_tracker.main *> _app_live_phase1.log
```

Checklist for user:

- Dashboard opens.
- Click Open Folder from project row/details.
- Add Sub Project creates folder.
- No UI crash.
- `_app_live_phase1.log` has no traceback.

- [ ] Update `PROJECT_STATUS.md` + `graphify update .`.

---

## Phase 2 — Dependency & Entry Point (P0-1, P0-4)

**Goal:** Install/package metadata matches real app and docs have one official entry point.

**Files:**

- Modify: `pyproject.toml`
- Modify: `WINDOWS_SETUP.md`
- Modify: `PRD.md`
- Maybe Modify: `README.md` if entry point appears there

### Task 2.1: Sync `pyproject.toml` runtime deps

- [ ] Replace dependency block with approved deps from `requirements.txt` minus PyQt6. Keep watchdog until Phase 5 removes service.

```toml
[project]
name = "project-tracker-dbs"
version = "0.1.0"
description = "Windows desktop tracker for CR deployment projects"
requires-python = ">=3.12"
dependencies = [
  "pywebview>=6.2.1",
  "pywin32>=306; platform_system == 'Windows'",
  "pyinstaller>=6.0.0",
  "pyautogui>=0.9.54",
  "pyperclip>=1.8.2",
  "send2trash>=1.8.3",
  "watchdog>=4.0.0",
  "python-dateutil>=2.9.0",
  "APScheduler>=3.10,<4",
]

[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["project_tracker*"]
```

- [ ] Run metadata check in disposable venv only if time allows. Otherwise run:

```powershell
.\.venv\Scripts\python.exe -m pip check
```

Expected: no broken requirements.

### Task 2.2: Single entry point docs

- [ ] In `PRD.md`, `WINDOWS_SETUP.md`, README-like docs, replace stale root `app_web.py` launch references with:

```powershell
.\.venv\Scripts\python.exe -m project_tracker.main
```

- [ ] If `.spec` references `project_tracker/main.py`, leave it.

- [ ] Verify no stale root `app_web.py` entry references remain except legacy/reference explanation.

```powershell
python - <<'PY'
from pathlib import Path
for p in [Path('PRD.md'), Path('WINDOWS_SETUP.md')]:
    if p.exists() and 'app_web.py' in p.read_text(encoding='utf-8'):
        print(p)
PY
```

Expected: no output or only explicit legacy note.

### Task 2.3: Phase 2 verification + live app gate

- [ ] Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q
npm --prefix frontend run build
.\.venv\Scripts\python.exe -m project_tracker.main *> _app_live_phase2.log
```

Checklist:

- App launches through official entry point.
- Settings still loads.
- Dashboard still loads.
- No traceback.

- [ ] Update `PROJECT_STATUS.md` + `graphify update .`.

---

## Phase 3 — Logic Bugs (P1-14, P1-15, P1-13)

**Goal:** Fix multi-drone condition, serve history/details, remove dead metadata field.

**Files:**

- Modify: `project_tracker/core/rules.py`
- Modify: `project_tracker/app_web.py`
- Modify: `project_tracker/core/models.py`
- Tests: rules/project details tests

### Task 3.1: P1-14 write multi-drone failing tests

- [ ] Add test in existing rules test file (use current helper names). If no helper exists, create `tests/test_rules_drone_state.py`:

```python
from project_tracker.core.enums import DroneState
from project_tracker.core.models import DroneTicket, ProjectMetadata
from project_tracker.core.rules import evaluate_condition


def test_drone_state_equals_passes_when_any_drone_matches(tmp_path):
    metadata = ProjectMetadata(
        drone_tickets=[
            DroneTicket(subfolder_name="A", drone_state=DroneState.DRAFT),
            DroneTicket(subfolder_name="B", drone_state=DroneState.APPROVED),
        ]
    )

    result = evaluate_condition(
        {"type": "drone_state", "operator": "equals", "value": DroneState.APPROVED.value},
        metadata,
        tmp_path,
    )

    assert result.passed is True


def test_drone_state_not_equals_fails_when_any_drone_matches_forbidden_state(tmp_path):
    metadata = ProjectMetadata(
        drone_tickets=[
            DroneTicket(subfolder_name="A", drone_state=DroneState.DRAFT),
            DroneTicket(subfolder_name="B", drone_state=DroneState.APPROVED),
        ]
    )

    result = evaluate_condition(
        {"type": "drone_state", "operator": "not_equals", "value": DroneState.APPROVED.value},
        metadata,
        tmp_path,
    )

    assert result.passed is False
```

- [ ] Run tests.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_rules_drone_state.py -v
```

Expected before fix: first test FAILS because only first drone checked.

### Task 3.2: P1-14 implement all-drone evaluation

- [ ] Replace `drone_state` branch in `project_tracker/core/rules.py` with:

```python
elif cond_type == "drone_state":
    if not metadata.drone_tickets:
        return ConditionResult(False, "No drone tickets")
    states = [ticket.drone_state.value for ticket in metadata.drone_tickets]
    if operator == "equals":
        passed = value in states
        reason = "Drone state matched" if passed else f"No drone state is {value}"
    elif operator == "not_equals":
        passed = value not in states
        reason = f"No drone state is {value}" if passed else f"At least one drone state is {value}"
    else:
        return ConditionResult(False, f"Unknown operator: {operator}")
    return ConditionResult(passed, reason)
```

- [ ] Run targeted test.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_rules_drone_state.py -v
```

Expected: PASS.

### Task 3.3: P1-15 serve history + implementation_plan in project_get

- [ ] Add failing test in `tests/test_phase_d_app_web_project_details_read_wiring.py`:

```python
def test_project_get_returns_history_and_implementation_plan(tmp_path):
    from project_tracker.app_web import create_js_api
    from project_tracker.core.models import HistoryEntry, ProjectMetadata, local_now
    from project_tracker.infrastructure.metadata_store import MetadataStore

    api = create_js_api()
    project = temp_project(tmp_path)
    metadata = ProjectMetadata(
        project_name="Alpha",
        implementation_plan="Step 1",
        history=[HistoryEntry(timestamp=local_now(), action="TEST", detail="Created", user="tester")],
    )
    MetadataStore().write(project, metadata)

    response = api.project_get(str(project))

    assert response["ok"] is True
    assert response["data"]["implementation_plan"] == "Step 1"
    assert response["data"]["history"][0]["action"] == "TEST"
```

- [ ] Run targeted test.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_phase_d_app_web_project_details_read_wiring.py::test_project_get_returns_history_and_implementation_plan -v
```

Expected before fix: FAIL missing keys.

- [ ] In `project_tracker/app_web.py` `_ProjectServiceAdapter.get_project()`, add fields before closing return dict:

```python
"implementation_plan": metadata.implementation_plan,
"history": [entry.to_dict() for entry in metadata.history],
```

- [ ] Run targeted test again. Expected: PASS.

### Task 3.4: P1-13 remove dead `notes` metadata field

- [ ] Verify frontend/backend notes flow uses `notes.md` via `_NotesServiceAdapter`, not `ProjectMetadata.notes`.

```powershell
graphify query "ProjectMetadata notes field notes.md NotesServiceAdapter"
```

Expected: notes live in file adapter.

- [ ] Remove line from `project_tracker/core/models.py`:

```python
notes: str = ""
```

- [ ] Run model tests.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q
```

Expected: PASS. If any test instantiates `ProjectMetadata(notes=...)`, update test to use `notes.md` adapter instead.

### Task 3.5: Phase 3 verification + live app gate

- [ ] Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q
npm --prefix frontend run build
.\.venv\Scripts\python.exe -m project_tracker.main *> _app_live_phase3.log
```

Checklist:

- Project Details opens.
- Activity History visible if project has history.
- Drone condition dependent automations still work.
- No traceback.

- [ ] Update `PROJECT_STATUS.md` + `graphify update .`.

---

## Phase 4 — MVP-1 Missing Features (P1-6, P1-12)

**Goal:** Project Details can edit start/end datetime and implementation plan.

**Files:**

- Modify: `project_tracker/app_web.py` if backend update methods incomplete
- Modify: `project_tracker/web/js_api.py` if endpoint missing
- Modify: `frontend/src/lib/components/ProjectDetails.svelte`
- Tests: Python adapter tests + frontend component tests where practical

### Task 4.1: Backend update endpoint for project detail fields

- [ ] Query graphify:

```powershell
graphify query "project_update start_datetime end_datetime implementation_plan JsApi"
```

- [ ] If `project_update()` already persists metadata fields, write tests only. If missing, add adapter method that:
  - reads metadata
  - updates only allowed fields: `start_datetime`, `end_datetime`, `implementation_plan`
  - writes via `MetadataStore.write()` atomic mechanism
  - returns updated `get_project()` payload.

Expected implementation shape in `app_web.py`:

```python
def update_project_details(self, project_path: Path, data: Mapping[str, object]) -> object:
    path = Path(project_path)
    metadata = self._metadata_store.read(path)
    if metadata is None:
        raise FileNotFoundError(f"Project metadata not found: {path}")
    if "start_datetime" in data:
        metadata.start_datetime = datetime_from_json(data.get("start_datetime"))
    if "end_datetime" in data:
        metadata.end_datetime = datetime_from_json(data.get("end_datetime"))
    if "implementation_plan" in data:
        metadata.implementation_plan = str(data.get("implementation_plan") or "")
    metadata.updated_at = local_now()
    self._metadata_store.write(path, metadata)
    return self.get_project(path)
```

- [ ] Add/update `JsApi.project_update()` to call that adapter for these fields if not already doing so.

### Task 4.2: Backend tests for datetime + implementation_plan persistence

- [ ] Add tests:

```python
def test_project_update_persists_start_end_datetime_and_plan(tmp_path):
    from project_tracker.app_web import create_js_api

    api = create_js_api()
    project = temp_project(tmp_path)

    response = api.project_update(
        str(project),
        {
            "start_datetime": "2026-06-17T09:00:00+07:00",
            "end_datetime": "2026-06-17T10:00:00+07:00",
            "implementation_plan": "Deploy CR",
        },
    )

    assert response["ok"] is True
    data = api.project_get(str(project))["data"]
    assert data["start_datetime"] == "2026-06-17T09:00:00+07:00"
    assert data["end_datetime"] == "2026-06-17T10:00:00+07:00"
    assert data["implementation_plan"] == "Deploy CR"
```

- [ ] Run targeted tests. Expected: PASS after implementation.

### Task 4.3: Frontend ProjectDetails datetime editor

- [ ] In `frontend/src/lib/components/ProjectDetails.svelte`, add UI state:

```ts
let draftStartDatetime = $state("");
let draftEndDatetime = $state("");
let draftImplementationPlan = $state("");
let savingDetails = $state(false);
let detailsError = $state<string | null>(null);
```

- [ ] When project loads, set drafts from project detail:

```ts
draftStartDatetime = toDatetimeLocal(project.start_datetime);
draftEndDatetime = toDatetimeLocal(project.end_datetime);
draftImplementationPlan = project.implementation_plan ?? "";
```

- [ ] Add helpers:

```ts
function toDatetimeLocal(value?: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toISOString().slice(0, 16);
}

function fromDatetimeLocal(value: string): string | null {
  if (!value) return null;
  const date = new Date(value);
  return date.toISOString();
}
```

- [ ] Add form controls in Project Details metadata section:

```svelte
<label>
  <span>Start datetime</span>
  <input type="datetime-local" bind:value={draftStartDatetime} />
</label>
<label>
  <span>End datetime</span>
  <input type="datetime-local" bind:value={draftEndDatetime} />
</label>
<label>
  <span>Implementation plan</span>
  <textarea bind:value={draftImplementationPlan} rows="8"></textarea>
</label>
<button disabled={savingDetails} onclick={saveProjectDetails}>Save details</button>
{#if detailsError}<p class="error">{detailsError}</p>{/if}
```

- [ ] Add save handler:

```ts
async function saveProjectDetails() {
  if (!project) return;
  savingDetails = true;
  detailsError = null;
  const response = await bridge.project_update(project.project_path, {
    start_datetime: fromDatetimeLocal(draftStartDatetime),
    end_datetime: fromDatetimeLocal(draftEndDatetime),
    implementation_plan: draftImplementationPlan,
  });
  savingDetails = false;
  if (!response.ok) {
    detailsError = response.error?.message ?? "Failed to save project details";
    return;
  }
  project = response.data;
}
```

### Task 4.4: Frontend Activity History render

- [ ] In `ProjectDetails.svelte`, render history:

```svelte
<section>
  <h3>Activity History</h3>
  {#if project?.history?.length}
    <ul>
      {#each project.history as entry}
        <li>
          <time>{entry.timestamp}</time>
          <strong>{entry.action}</strong>
          <span>{entry.detail}</span>
          <small>{entry.user}</small>
        </li>
      {/each}
    </ul>
  {:else}
    <p>No activity yet.</p>
  {/if}
</section>
```

- [ ] Run frontend build.

```powershell
npm --prefix frontend run build
```

Expected: PASS.

### Task 4.5: Phase 4 verification + live app gate

- [ ] Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q
npm --prefix frontend run build
.\.venv\Scripts\python.exe -m project_tracker.main *> _app_live_phase4.log
```

Checklist:

- Open Project Details.
- Edit Start datetime; Save; close/reopen; value persists.
- Edit End datetime; Save; close/reopen; value persists.
- Edit Implementation Plan; Save; close/reopen; value persists.
- Activity History visible.
- No traceback.

- [ ] Update `PROJECT_STATUS.md` + `graphify update .`.

---

## Phase 5 — Dead Code Purge + Watchdog Out

**Goal:** Remove approved dead code and dependency drift without breaking imports.

**Files:**

- Delete: `project_tracker/infrastructure/watchdog_service.py`
- Delete: `project_tracker/services/outlook_service.py`
- Modify: `requirements.txt`
- Modify: `pyproject.toml`
- Modify: services with duplicate `Signal`
- Modify: `project_tracker/infrastructure/cache_db.py` if `scan_warnings` removed
- Tests: full suite

### Task 5.1: Verify dead imports before delete

- [ ] Run graphify queries:

```powershell
graphify query "watchdog_service imports references"
graphify query "outlook_service.py imports references"
graphify query "scan_warnings cache_db read write"
graphify query "Signal class duplicates services"
```

- [ ] Run exact import scan:

```powershell
python - <<'PY'
from pathlib import Path
for needle in ['watchdog_service', 'outlook_service', 'scan_warnings']:
    print(f'-- {needle} --')
    for p in Path('.').rglob('*'):
        if p.is_file() and p.suffix in {'.py', '.md', '.toml', '.txt'} and '.git' not in p.parts:
            text = p.read_text(encoding='utf-8', errors='ignore')
            if needle in text:
                print(p)
PY
```

Expected: only target file/doc/audit references. If active import appears, update caller or stop.

### Task 5.2: Delete watchdog + outlook dead service

- [ ] Remove files after verification:

```powershell
Remove-Item -LiteralPath project_tracker\infrastructure\watchdog_service.py,project_tracker\services\outlook_service.py -Force -Confirm:$false
```

- [ ] Remove `watchdog>=4.0.0` from `requirements.txt`.
- [ ] Remove `watchdog>=4.0.0` from `pyproject.toml`.

### Task 5.3: Deduplicate Signal class

- [ ] Create `project_tracker/services/signals.py`:

```python
"""Small synchronous signal helper for service events."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class Signal:
    def __init__(self) -> None:
        self._subscribers: list[Callable[..., None]] = []

    def connect(self, callback: Callable[..., None]) -> None:
        self._subscribers.append(callback)

    def emit(self, *args: Any, **kwargs: Any) -> None:
        for callback in list(self._subscribers):
            callback(*args, **kwargs)
```

- [ ] Replace local `class Signal` definitions in:
  - `project_tracker/services/automation_service.py`
  - `project_tracker/services/auto_transition_service.py`
  - `project_tracker/services/download_email_service.py`
  - `project_tracker/services/notification_service.py`

with:

```python
from project_tracker.services.signals import Signal
```

- [ ] Run service tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_phase_c_notification_service_events.py tests/test_scheduler_entries_unit.py -q
```

Expected: PASS.

### Task 5.4: Remove `scan_warnings` ghost table if unused

- [ ] In `project_tracker/infrastructure/cache_db.py`, remove schema creation for `scan_warnings` only if exact scan found no read/write users.
- [ ] If migration helpers reference it, remove only table-specific code; do not touch project/drone/cache tables.
- [ ] Run cache DB tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_phase_b_stores.py -q
```

Expected: PASS.

### Task 5.5: Phase 5 verification + live app gate

- [ ] Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q
npm --prefix frontend run build
.\.venv\Scripts\python.exe -m project_tracker.main *> _app_live_phase5.log
```

Checklist:

- App boots after deleted files.
- Outlook draft path still uses `_OutlookServiceAdapter` / `outlook_client`, not deleted dead `outlook_service.py`.
- Notifications still emit/dismiss.
- Scheduler screen still loads.
- No traceback.

- [ ] Update `PROJECT_STATUS.md` + `graphify update .`.

---

## Phase 6 — Safety & Atomicity (P2-25, P2-26, P2-32)

**Goal:** Fix non-atomic notes write, notification protocol mismatch, second brain persisted-flag KeyError.

**Files:**

- Modify: `project_tracker/app_web.py`
- Modify: `project_tracker/services/notification_service.py`
- Modify: `project_tracker/services/second_brain_service.py`
- Tests: notes, notification, second brain tests

### Task 6.1: P2-25 atomic notes write test

- [ ] Add/update test in notes adapter tests:

```python
def test_notes_update_writes_notes_file(tmp_path):
    from project_tracker.app_web import create_js_api

    api = create_js_api()
    project = temp_project(tmp_path)

    response = api.notes_update(str(project), "hello")

    assert response["ok"] is True
    assert (project / "notes.md").read_text(encoding="utf-8") == "hello"
```

- [ ] Implement atomic write in `_NotesServiceAdapter.update_notes()`:

```python
notes_file = Path(project_path) / "notes.md"
tmp_file = notes_file.with_name(f".{notes_file.name}.tmp")
tmp_file.write_text(notes, encoding="utf-8")
tmp_file.replace(notes_file)
return notes
```

- [ ] Run targeted notes test.

### Task 6.2: P2-26 real `NotificationService.dismiss_all()`

- [ ] Add test:

```python
def test_notification_service_dismiss_all_returns_count():
    service = NotificationService(event_publisher=None)
    service.add("info", "One", "A")
    service.add("info", "Two", "B")

    assert service.dismiss_all() == 2
    assert all(item.dismissed for item in service.get_all())
```

- [ ] Add method:

```python
def dismiss_all(self) -> int:
    dismissed = 0
    for notification in self._notifications:
        if not notification.dismissed:
            notification.dismissed = True
            dismissed += 1
            self.notification_dismissed.emit(notification.id)
    if dismissed and self._cache is not None:
        for notification in self._notifications:
            self._persist(notification)
    if dismissed and self._event_publisher is not None:
        self._event_publisher("notifications:changed", {"dismissed": dismissed})
    return dismissed
```

Use existing persistence helper name if different (`_persist`, `_persist_notification`, etc.). Match surrounding style.

- [ ] Run notification tests.

### Task 6.3: P2-32 second brain persisted flags safe defaults

- [ ] Add test with partial persisted flags:

```python
def test_second_brain_partial_persisted_flags_default_false(tmp_path):
    item = SecondBrainItem(id="a", title="A", kind="note", path=tmp_path / "a.md")
    service = SecondBrainService(folder=tmp_path, items_provider=lambda: [item])
    service._persisted = {"a": {"pinned": True}}

    result = service.list_items()

    assert result[0].pinned is True
    assert result[0].favorite is False
```

- [ ] Replace in `_items()`:

```python
pinned=bool(flags.get("pinned", False)),
favorite=bool(flags.get("favorite", False)),
```

- [ ] Run second brain tests.

### Task 6.4: Phase 6 verification + live app gate

- [ ] Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q
npm --prefix frontend run build
.\.venv\Scripts\python.exe -m project_tracker.main *> _app_live_phase6.log
```

Checklist:

- Notes edit persists.
- Dismiss All notifications works.
- Second Brain opens even with old/partial persisted flags.
- No traceback.

- [ ] Update `PROJECT_STATUS.md` + `graphify update .`.

---

## Phase 7 — Doc Truth Reconciliation (P1-1, P1-2, P1-3)

**Goal:** PRD/docs match product decisions and shipped implementation.

**Files:**

- Modify: `PRD.md`
- Modify: ADR-002 doc if present
- Modify: `PROJECT_STATUS.md`

### Task 7.1: PRD drift fixes

- [ ] Update PRD facts:
  - T-10 hard block → H-10 reminder.
  - ⋮ menu scope → actual MVP-1 menu.
  - marked.js → custom renderer if still true.
  - pywebview version → `>=6.2.1`.
  - Tailwind → v4 bundled locally.
  - Entry point → `python -m project_tracker.main`.
  - Watchdog → out of MVP-1; polling/manual refresh accepted.

- [ ] Run text scan:

```powershell
python - <<'PY'
from pathlib import Path
needles = ['app_web.py', 'Tailwind 3.4', 'marked.js', 'T-10']
for n in needles:
    print(f'-- {n} --')
    for p in [Path('PRD.md')]:
        text = p.read_text(encoding='utf-8')
        if n in text:
            print(p)
PY
```

Expected: no stale references except explicit historical notes.

### Task 7.2: ADR SQLite truth update

- [ ] Find ADR:

```powershell
graphify query "ADR-002 SQLite rebuildable cache partial truth notifications scheduler jobs"
```

- [ ] Update ADR wording:

```markdown
SQLite is a local rebuildable index for project existence/year/state/metadata derived from filesystem + project_data.json. It also stores local app data that is not rebuildable from project folders, including notifications, automation logs, and APScheduler job rows. Therefore SQLite is a partial local truth store, but never canonical for project existence, folder state, year, or project metadata.
```

### Task 7.3: Phase 7 verification

- [ ] Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q
npm --prefix frontend run build
graphify update .
```

- [ ] Update `PROJECT_STATUS.md`.

---

## Phase 8 — Packaging & Manual RC Gate

**Goal:** Build Windows package and run MVP-1 release-candidate manual gate.

**Files:**

- Modify/create: `docs/windows-manual-test-checklist.md`
- Modify: `PROJECT_STATUS.md`
- Maybe Modify: `scripts/package.py` only if packaging fails due real bug.

### Task 8.1: Manual checklist doc

- [ ] Create/update `docs/windows-manual-test-checklist.md`:

```markdown
# Windows Manual Test Checklist — MVP-1

## Launch

- [ ] `.exe` launches.
- [ ] Svelte UI renders.
- [ ] No traceback in console/log.

## Dashboard

- [ ] Year selector works.
- [ ] Project rows show real data.
- [ ] Open Folder works.
- [ ] Add Sub Project works.

## Project Details

- [ ] Start datetime edit persists.
- [ ] End datetime edit persists.
- [ ] Implementation Plan edit persists.
- [ ] Notes edit persists unless IMPLEMENTED.
- [ ] Activity History visible.

## Report

- [ ] KPI/table loads.
- [ ] CSV export works.

## Settings

- [ ] Root folder persists.
- [ ] App reload keeps setting.

## Second Brain / Link Bank

- [ ] Second Brain list opens.
- [ ] Link Bank CRUD works.

## Integrations

- [ ] Outlook draft creates draft only.
- [ ] Teams preview creates preview only; no auto-send.
- [ ] Scheduler CRUD works.
- [ ] Notifications display + dismiss all.
```

### Task 8.2: Package

- [ ] Run full verification:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q
npm --prefix frontend run build
.\.venv\Scripts\python.exe scripts\package.py
```

Expected: PyInstaller completes. If hidden import runtime issue appears, fix `.spec`; do not add unapproved deps except already approved stack deps.

### Task 8.3: Run packaged app live monitor

- [ ] Launch packaged `.exe` from `dist/` (exact path from package output). Redirect logs if supported; otherwise monitor terminal output.

Checklist: run entire `docs/windows-manual-test-checklist.md`.

- [ ] Record results in `PROJECT_STATUS.md`:

```markdown
## 2026-06-17 — MVP-1 RC Gate

Automated:

- Backend tests: PASS/FAIL
- Frontend build: PASS/FAIL
- Package: PASS/FAIL

Manual:

- Launch: PASS/FAIL
- Dashboard: PASS/FAIL
- Project Details: PASS/FAIL
- Report: PASS/FAIL
- Settings: PASS/FAIL
- Second Brain / Link Bank: PASS/FAIL
- Outlook draft-only: PASS/FAIL
- Teams preview-only: PASS/FAIL
- Scheduler / Notifications: PASS/FAIL

Open issues:

- ...
```

- [ ] Run final graph update:

```powershell
graphify update .
```

---

## Self-Review

Spec coverage:

- R1-R4 working rules covered in Non-Negotiable Working Rules and every phase gate.
- P0-1/P0-4 covered Phase 2.
- P0-5/P0-6/P0-7/P0-8 covered Phase 1.
- P1-13/P1-14/P1-15 covered Phase 3.
- P1-6/P1-12 covered Phase 4.
- Dead code + watchdog out covered Phase 5.
- P2-25/P2-26/P2-32 covered Phase 6.
- PRD/ADR drift covered Phase 7.
- Packaging/manual gate covered Phase 8.

No placeholders: plan has no TBD/TODO. Some steps require graphify/exact verification before deletion by safety design.

Type consistency:

- Bridge response shape remains `{ok, data/error}`.
- Paths cross bridge as `as_posix()` where new fields return paths.
- Metadata remains Python-owned; Svelte owns draft UI state.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-17-cleanup-mvp1-completion.md`.

Two execution options:

1. **Subagent-Driven (recommended)** — fresh subagent per task/phase, review between tasks, safer for broad cleanup.
2. **Inline Execution** — execute in this session with checkpoints; best for strict no-conflict direct edits.

User preference from design: git only for delegate agents, edit directly, inline/no-conflict. Recommended execution: **Inline Execution for Phase 0-1**, then decide if subagents needed for isolated later phases.
