# Project Status

## Current Phase

**Phase C remaining gap planning — next slice after C.7**

Phase A is completed and verified on Linux. Phase B implementation slices B.1 through B.3 are completed and verified on Linux. Phase C implementation slices C.1 through C.7 are completed and verified on Linux.

## Source of Truth

`PRD.md` v3.1 is the product and architecture source of truth.

If current code, old docs, comments, folder structure, or reference prototypes conflict with `PRD.md`, report the conflict before implementation.

## Current Repo Reality Summary

Repository has completed Phase A core-domain migration slices, Phase B.1 through B.3 infrastructure slices, and Phase C.1 through C.7 service and JsApi slices.

Current state:

- `PRD.md` v3.1 exists and is authoritative.
- `CLAUDE.md` aligns with PRD v3.1 migration direction.
- Phase A core domain work is implemented and verified.
- Phase B infrastructure stores, SQLite cache foundation/mapping/rebuild, safe delete helpers, and guarded Windows integration stubs are implemented and verified.
- Phase C.1 ScannerService cache integration is implemented and verified.
- Phase C.2 DashboardService read-only cache-backed DTOs and summary are implemented and verified.
- Phase C.3a event queue foundation (`web/event_queue.py`) is implemented and verified.
- Phase C.3b NotificationService event queue integration is implemented and verified.
- Phase C.3c1 auto-transition event emission is implemented and verified.
- Phase C.3c2 ProjectService auto-transition cleanup is implemented and verified.
- Phase C.4a scheduler service foundation is implemented and verified.
- Phase C.4b auto-transition scheduler integration is implemented and verified.
- Phase C.5a JsApi response contract foundation is implemented and verified.
- Phase C.5b JsApi event polling is implemented and verified.
- Phase C.5c JsApi dashboard read methods are implemented and verified.
- Phase C.5d JsApi notification methods are implemented and verified.
- Phase C.5e-C.5g JsApi scanner, scheduler, and integration service facades are implemented and verified.
- Phase C.6 ReportService backend foundation is implemented and verified.
- Phase C.7 JsApi report facade is implemented and verified.
- Current pywebview shell exists in `project_tracker/app_web.py`, but it still loads static HTML from `frontend/` through a file URI.
- Static HTML frontend files exist under `frontend/` and are legacy/reference, not migrated production UI.
- Svelte + TypeScript + Vite structure is missing.
- `web/js_api.py` bridge module is implemented but not wired into `app_web.py` production shell.
- PyQt6 files under `redesign_ui/` are UX/function reference only and are not production code.

## Frontend Status

Static HTML frontend is **legacy/reference only**.

Files such as these are not PRD v3.1 migrated screens:

- `frontend/index.html`
- `frontend/dashboard.html`
- `frontend/project_detail.html`
- `frontend/second_brain.html`
- `frontend/report.html`
- `frontend/automations.html`
- `frontend/settings.html`
- `frontend/assets/tailwind.min.js`

Production frontend target remains:

- Svelte
- TypeScript
- Vite
- Tailwind CSS bundled locally through the frontend build
- Vite output served by pywebview through `web/static/` / serve-folder mode

Current missing frontend structure:

```text
frontend/package.json
frontend/tsconfig.json
frontend/vite.config.ts
frontend/src/
web/static/
```

## Backend / Infrastructure Status

Current backend package exists under `project_tracker/`, with Phase A core-domain work, Phase B infrastructure slices complete through B.3, and Phase C service/JsApi slices complete through C.7.

Known remaining gaps against PRD v3.1:

- `web/js_api.py` exists with response contract, event polling, dashboard, notification, scanner, scheduler, and report facades.
- `web/event_queue.py` exists with `push_event()`, `drain_events()`, `clear_events()` API.
- Existing bridge logic lives inside `project_tracker/app_web.py` and does not yet match the PRD bridge architecture.
- Automation service remains deferred.
- Project action JsApi facade remains deferred.
- Settings/link bank JsApi facade remains deferred.
- Second Brain service remains deferred.

## PyQt6 Status

PyQt6 code is reference only.

`redesign_ui/*.py` files may be used to understand:

- UX intent
- screen layout
- user flows
- menu behavior
- interaction behavior

They must not be imported into production code or used as the basis for new production PyQt6 UI.

## Phase A Progress

### Phase A.1 — Core enums and metadata serialization

Status: completed and verified on Linux.

Verified scope:

- `ProjectState.CANCELED` exists.
- `CRState.POSTPONED` exists.
- `CRState.REOPEN` remains as a deprecated compatibility value and must not be persisted by REOPEN flows.
- `DroneTicket.owner` exists and defaults to an empty string.
- `ProjectMetadata.to_dict()` does not serialize `project_state`.
- `ProjectMetadata.to_dict()` does not serialize legacy `notes`.
- `ProjectMetadata.from_dict()` ignores legacy `notes` input so it is not re-emitted.
- timezone-aware datetime serialization behavior is preserved.

Verification evidence:

```bash
rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/test_core_enums.py tests/test_core_models.py -v
rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m py_compile project_tracker/core/enums.py project_tracker/core/models.py
```

Result:

```text
11 passed
py_compile completed with no output
```

### Phase A.2.1 — Pure state transition matrices and helpers

Status: completed and verified on Linux.

Verified scope:

- Strict CR transition matrix exists for manual and scheduler-only transitions.
- `CRState.REOPEN` remains for compatibility but is rejected as a persistent CR transition target.
- Manual CR `IN_PROGRESS` target is rejected.
- Automatic CR `APPROVED -> IN_PROGRESS` is allowed.
- Strict Drone transition matrix exists for manual and scheduler-only transitions.
- Manual Drone `IN_PROGRESS` target is rejected.
- Automatic Drone `APPROVED -> IN_PROGRESS` is allowed.
- `validate_drone_state_change_allowed()` rejects empty or blank `drone_link` before validating transitions.
- Strict `ProjectState` folder transition matrix exists.
- `target_project_state_for_cr_state()` maps `APPROVED`, `FINISHED`, `POSTPONED`, and `CANCELED` correctly.

Verification evidence:

```bash
rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/test_core_enums.py tests/test_core_models.py tests/test_core_state_machine.py -v
rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/ -q
rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m py_compile project_tracker/core/enums.py project_tracker/core/state_machine.py project_tracker/core/exceptions.py
```

Result:

```text
32 passed
32 passed
py_compile completed with no output
```

### Phase A.2.2 — REOPEN compatibility cleanup

Status: completed and verified on Linux.

Verified scope:

- `CRState.REOPEN` remains as a deprecated compatibility enum value.
- `CRState.REOPEN` remains rejected as a persistent CR transition target.
- REOPEN is folder-state-based in core helpers.
- REOPEN is allowed from `ProjectState.POSTPONED` and `ProjectState.CANCELED`.
- REOPEN is rejected from `ProjectState.UAT_PREPARE`, `ProjectState.PROD_READY`, and `ProjectState.IMPLEMENTED`.
- REOPEN result targets `ProjectState.UAT_PREPARE` and `CRState.PENDING_SUBMISSION`.
- `ProjectService.reopen_project()` moves reopened projects to `UAT_PREPARE`.
- `ProjectService.reopen_project()` persists `CRState.PENDING_SUBMISSION`, not `CRState.REOPEN`.
- REOPEN is recorded as a history action/event.

Verification evidence:

```bash
rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/test_core_state_machine.py tests/test_project_service_reopen.py -v
rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/ -q
rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m py_compile project_tracker/core/state_machine.py project_tracker/services/project_service.py
```

Result:

```text
29 passed
40 passed
py_compile completed with no output
```

### Phase A.3.1 — Link extraction helpers

Status: completed and verified on Linux.

Verified scope:

- `extract_cr_number()` extracts `CRNumber=CR...` query values.
- `extract_drone_ticket()` extracts terminal `D-...` Drone ticket path segment.
- Empty, blank, and unmatched inputs return `None`.

### Phase A.3.2 — T-10 refinement and transition guards

Status: completed and verified on Linux.

Verified scope:

- T-10 uses `cr_pending_approval_at`, not `cr_state_updated_at`.
- Missing T-10 proof fails when CR is beyond `PENDING SUBMISSION`.
- Missing T-10 proof is neutral while CR remains `PENDING SUBMISSION`.
- `UAT_PREPARE -> PROD_READY` guard validates start/end datetimes, timezone awareness, backdated values, CR link, CR state, Drone links/states, and T-10 proof.
- `PROD_READY -> IMPLEMENTED` guard validates CR `FINISHED` and all Drone tickets `FINISHED`.

### Phase A.3.3 — Auto IN-PROGRESS predicates

Status: completed and verified on Linux.

Latest completed commit:

```text
992d1bc implement phase A.3.3 auto in-progress predicates
```

Verified scope:

- `is_in_deployment_window()` returns true only for timezone-aware `start_datetime <= now <= end_datetime`.
- `is_in_deployment_window()` returns false for missing start/end, naive datetimes, end-before-start, before-window, and after-window inputs.
- `should_auto_start_cr()` returns true only for CR `APPROVED` inside deployment window.
- `should_auto_start_drone()` returns true only for Drone `APPROVED` with non-blank `drone_link` inside deployment window.
- Predicates do not mutate metadata or tickets.
- Predicates do not call scheduler, filesystem, metadata store, SQLite, service, or state machine transition validators.

Verification evidence:

```bash
rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/test_core_rules_guards.py -v
rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/test_core_state_machine.py -v
rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/ -q
rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m py_compile project_tracker/core/rules.py
```

Result:

```text
50 passed
26 passed
98 passed
py_compile completed with no output
```

## Phase A Final Completion Checklist

Completed and verified:

- `ProjectState.CANCELED`
- `CRState.POSTPONED`
- `CRState.REOPEN` deprecated compatibility only
- `DroneTicket.owner`
- `ProjectMetadata` does not serialize `project_state`
- `ProjectMetadata` does not serialize legacy `notes`
- strict CR transition matrix
- strict Drone transition matrix
- strict `ProjectState` transition matrix
- REOPEN action resets folder to `UAT_PREPARE` and CR to `PENDING_SUBMISSION`
- `extract_cr_number()`
- `extract_drone_ticket()`
- T-10 missing proof behavior
- `UAT_PREPARE -> PROD_READY` guard
- `PROD_READY -> IMPLEMENTED` guard
- auto IN-PROGRESS pure predicates

Final Phase A audit evidence:

```text
Branch: prd-v31-migration
Working tree: clean before PROJECT_STATUS.md update
Tests: 98 passed
Core py_compile: pass
Core import purity: pass
Latest completed commit: 992d1bc implement phase A.3.3 auto in-progress predicates
```

## Phase B Progress

### Phase B.1 — Infrastructure baseline tests

Status: completed and verified on Linux.

### Phase B.2.1 — SQLite cache DB foundation

Status: completed and verified on Linux.

### Phase B.2.2a — Cache mapping helpers

Status: completed and verified on Linux.

### Phase B.2.2b — Year cache rebuild orchestration

Status: completed and verified on Linux.

### Phase B.2.3 — PRD-aligned cache schema and safe filesystem helpers

Status: completed and verified on Linux.

Verified scope:

- SQLite project cache table is named `project_index` per PRD v3.1.
- `project_index` includes PRD cache columns: `path`, `name`, `year`, `folder_state`, `cr_link`, `cr_number`, `cr_state`, `cr_pending_approval_at`, `start_datetime`, `end_datetime`, `drone_tickets_json`, `t10_status`, `updated_at`, `scanned_at`.
- Existing normalized `drone_tickets` table remains for query-friendly Drone ticket rows.
- Safe delete helper routes paths through `send2trash.send2trash(str(path))`.
- Linux `open_folder()` dev behavior is guarded and non-crashing.

### Phase B.3 — Guarded Outlook/Teams infrastructure stubs

Status: completed and verified on Linux.

Verified scope:

- `project_tracker/infrastructure/outlook_client.py` imports without Windows dependencies on Linux.
- Outlook draft creation returns a dev-skipped response on Linux.
- Outlook contact lookup returns a dev fallback contact on Linux.
- `project_tracker/infrastructure/teams_client.py` imports without Windows dependencies on Linux.
- Teams message sending returns a dev-skipped response on Linux.
- Windows-only imports remain lazy and guarded.

Verification evidence:

```bash
rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/ -q
rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m py_compile project_tracker/infrastructure/cache_db.py project_tracker/infrastructure/filesystem.py project_tracker/infrastructure/outlook_client.py project_tracker/infrastructure/teams_client.py
```

Result:

```text
154 passed
py_compile completed with no output
```

## Next Recommended Phase

**Next Phase C service slice planning**

Recommended next slice:

- Select next Phase C service slice from remaining PRD gaps.
- Keep changes surgical and phase-scoped.
- Add targeted tests for selected service slice.
- Run full Python test suite.
- Update `PROJECT_STATUS.md` with next slice status.

Deferred (not yet implemented):

- `BridgeResponse` dataclass / `web/js_api.py`
- frontend / Svelte / pywebview bridge
- `automation_service.py`
- `report_service.py` / CSV export
- `second_brain_service.py`
- actual Windows manual testing

Do not start Svelte, pywebview bridge rewrite, automation/report/second-brain services, or frontend migration until the appropriate later phase is approved.

## Phase C Progress

### Phase C.1 — ScannerService cache integration

Status: completed and verified on Linux.

Verified scope:

- `ScannerService` wraps cache rebuild with `ScanWarning` and `ScanYearResult` DTOs.
- Service coordinates `MetadataStore` and `CacheDb` for year-level cache rebuild.
- Service layer does not expose raw infrastructure APIs.

Verification evidence:

```bash
rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/test_phase_c_scanner_service.py -v
rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/ -q
```

Result:

```text
172 passed (after C.2)
```

Latest completed commit:

```text
cce9fec implement phase C.1 scanner service cache integration
```

### Phase C.2 — DashboardService read-only cache-backed DTOs

Status: completed and verified on Linux.

Verified scope:

- `DashboardService` reads from SQLite cache via `CacheDb`.
- `list_projects()` returns `DashboardProject` DTOs with all PRD dashboard columns.
- `list_drone_tickets()` returns `DashboardDroneTicket` DTOs.
- `get_summary()` returns `DashboardSummary` with state counts and KPI data.
- `get_dashboard()` returns combined `DashboardData` DTO.
- No frontend/bridge wiring implemented.

Verification evidence:

```bash
rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/test_phase_c_dashboard_service.py -v
rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/ -q
```

Result:

```text
172 passed
```

Latest completed commit:

```text
a4d3f4f implement phase C.2 dashboard read service
```

### Phase C.3a — Event queue foundation

Status: completed and verified on Linux.

Verified scope:

- `web/event_queue.py` created with pure stdlib `queue.Queue` implementation.
- `push_event(event_type, payload)` pushes events with timezone-aware ISO timestamps.
- `drain_events(limit)` drains FIFO, removes returned events, supports optional limit.
- `clear_events()` removes all queued events (test isolation).
- Payload defaults to `{}` when omitted.
- Event shape: `{"type": str, "payload": dict, "timestamp": str}`.
- Thread-safe: concurrent push from multiple threads drains all events without loss.
- No pywebview, service, or frontend dependencies.
- No NotificationService wiring yet.
- No auto_transition_service wiring yet.
- No APScheduler or scheduler_service yet.
- No BridgeResponse or js_api.py yet.

Verification evidence:

```bash
rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/test_phase_c_event_queue.py -v
rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/ -q
rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m py_compile project_tracker/web/event_queue.py
```

Result:

```text
12 passed (targeted)
184 passed (full suite)
py_compile completed with no output
```

Latest completed commit:

```text
1db1bfe implement phase C.3a event queue foundation
```

Phase C.3a audit evidence:

```text
Branch: prd-v31-migration
Working tree: clean before PROJECT_STATUS.md update
Tests: 184 passed
py_compile: pass
Latest completed commit: 1db1bfe implement phase C.3a event queue foundation
```

### Phase C.3b — NotificationService event queue integration

Status: completed and verified on Linux.

Latest completed commit:

```text
8838e21 implement phase C.3b notification event queue integration
```

### Phase C.3c1 — Auto-transition event emission

Status: completed and verified on Linux.

Latest completed commit:

```text
75e90a1 implement phase C.3c1 auto-transition event emission
```

### Phase C.3c2 — ProjectService auto-transition cleanup

Status: completed and verified on Linux.

Latest completed commit:

```text
f8e9059 implement phase C.3c2 project service auto-transition cleanup
```

### Phase C.4a — Scheduler service foundation

Status: completed and verified on Linux.

Latest completed commit:

```text
9fafd65 implement phase C.4a scheduler service foundation
```

### Phase C.4b — Auto-transition scheduler integration

Status: completed and verified on Linux.

Latest completed commit:

```text
39f2370 implement phase C.4b auto-transition scheduler integration
```

Phase C.4b audit evidence:

```text
Branch: prd-v31-migration
Working tree: clean before PROJECT_STATUS.md update
Tests: 222 passed
Latest completed commit: 39f2370 implement phase C.4b auto-transition scheduler integration
```

Phase C.7 audit evidence:

```text
Branch: prd-v31-migration
Working tree: clean before PROJECT_STATUS.md update
Tests: 266 passed
Latest completed commit: 15fee00 implement phase C.7 js api report facade
```

## Phase 0 Boundary

Phase 0 documentation alignment is complete. `PROJECT_STATUS_old.md` remains historical reference unless deletion is explicitly approved.

No legacy/reference files should be deleted without explicit approval.
