# Project Status

## Current Phase

**Release candidate backend/frontend safe slice complete through Phase G.3 — Svelte frontend scaffold, dashboard, Project Details metadata/notes/CR/Drone actions, Link Bank stable ID CRUD, Automation preview UI, project create/update contract, and Second Brain read-only filesystem index**

Phase A is completed and verified on Linux. Phase B implementation slices B.1 through B.3 are completed and verified on Linux. Phase C implementation slices C.1 through C.15 are completed and verified on Linux. Phase D implementation slices D.1 through D.16 are completed and verified on Linux. Phase E metadata-contract slices E.1 through E.3 are completed and verified on Linux. Phase F metadata/UI completion slices F.1, F.3, and F.4 are completed and verified on Linux (F.2 blocked — Second Brain pin/favorite lacked persistence). Phase G safe release-candidate slices G.1 and G.3 are completed and verified on Linux; G.2 folder transitions remain deferred as high-risk folder moves.

## Source of Truth

`PRD.md` v3.1 is the product and architecture source of truth.

If current code, old docs, comments, folder structure, or reference prototypes conflict with `PRD.md`, report the conflict before implementation.

## Current Repo Reality Summary

Repository has completed Phase A core-domain migration slices, Phase B.1 through B.3 infrastructure slices, and Phase C.1 through C.15 service and JsApi slices.

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
- Current pywebview shell in `project_tracker/app_web.py` serves built Svelte output from `web/static/index.html` through pywebview HTTP server mode.
- Static HTML frontend files exist under `frontend/` and are legacy/reference, not migrated production UI.
- Svelte + TypeScript + Vite structure is implemented and verified through Phase D.9.
- `web/js_api.py` bridge module is wired into `app_web.py` production shell.
- PyQt6 files under `redesign_ui/` are UX/function reference only and are not production code.

## Frontend Status

Svelte + TypeScript + Vite + Tailwind frontend scaffold, dashboard binding, notifications, static serving, and navigation shell are **complete** (Phase D.1–D.9).

Existing static HTML files under `frontend/` remain as **legacy/reference only** — not wired into the production shell.

Production frontend build outputs to `web/static/` via `vite build`. The Vite build is clean and ready for pywebview serve-folder wiring. `svelte-check` passes with zero errors.

Production frontend structure present:

```text
frontend/package.json          ✓ Svelte 5 + Vite 6 + Tailwind 4
frontend/tsconfig.json          ✓ TypeScript 5.8
frontend/vite.config.ts         ✓ outDir: ../web/static
frontend/src/App.svelte         ✓ Shell + notifications + polling
frontend/src/lib/bridge.ts      ✓ Typed pywebview bridge wrapper
frontend/src/lib/types.ts       ✓ TS interfaces mirror Python DTOs
frontend/src/lib/components/    ✓ Sidebar, Header, Dashboard
web/static/                     ✓ Vite build output (production ready)
```

## Backend / Infrastructure Status

Current backend package exists under `project_tracker/`, with Phase A core-domain work, Phase B infrastructure slices complete through B.3, and Phase C service/JsApi slices complete through C.15.

Known remaining gaps against PRD v3.1:

- `web/js_api.py` exists with response contract, event polling, dashboard, notification, scanner, scheduler, report, project read/mutation/action, subproject/file/notes, settings/linkbank, app/util/year, second brain, and automation facades.
- `web/event_queue.py` exists with `push_event()`, `drain_events()`, `clear_events()` API.
- Existing bridge logic lives inside `project_tracker/app_web.py` and does not yet match the PRD bridge architecture.
- AutomationService foundation implemented (Phase C.14-C.15).
- Project action JsApi facade implemented (Phase C.8c-C.8e).
- Settings/link bank JsApi facade implemented (Phase C.11).
- SecondBrainService foundation implemented (Phase C.12-C.13).
- Frontend/pywebview production wiring to built Svelte output is implemented and verified through Phase D.8.
- Outlook/Teams real execution remains deferred (stubs in place).
- Automation action execution beyond rule evaluation remains deferred.
- Persistent automation logs not yet implemented.
- Real Second Brain filesystem index not yet implemented.
- Actual Windows manual testing remains deferred.

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

**Phase C exit audit complete — next: frontend/pywebview integration planning**

Phase C backend service and JsApi facade slices (C.1 through C.15) are complete with 330 tests passing.

Remaining PRD v3.1 gaps:

- Frontend Svelte + TypeScript + Vite + Tailwind production UI
- pywebview bridge wiring to JsApi
- Actual Windows manual testing
- Outlook/Teams real execution (stubs in place)
- Automation action execution beyond rule evaluation
- Persistent automation logs
- Real Second Brain filesystem index

Do not start frontend migration or Svelte project scaffolding until the appropriate phase is approved.

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

### Phase C.8a — Project read JsApi facade

Status: completed and verified on Linux.

Latest completed commit:

```text
54fae8e implement phase C.8a js api project read facade
```

### Phase C.8b — Project mutation JsApi facade

Status: completed and verified on Linux.

Latest completed commit:

```text
ee90285 implement phase C.8b js api project mutations
```

### Phase C.8c-C.8e — CR/Drone/folder transition JsApi facades

Status: completed and verified on Linux.

Latest completed commit:

```text
25e6054 implement phase C.8c-C.8e js api project actions
```

### Phase C.9 — App/util/year JsApi facades

Status: completed and verified on Linux.

Verified scope:

- App info, utility, and year JsApi facades.
- `notification_dismiss_all` method.

Latest completed commit:

```text
e9bf2d1 implement phase C.9 js api app util year facades
```

### Phase C.10 — Subproject/file/notes JsApi facades

Status: completed and verified on Linux.

Latest completed commit:

```text
5c890a7 implement phase C.10 js api subproject file notes facades
```

### Phase C.11 — Settings/linkbank JsApi facades

Status: completed and verified on Linux.

Latest completed commit:

```text
e84b91a implement phase C.11 js api settings linkbank facades
```

### Phase C.12-C.13 — SecondBrainService + JsApi facade

Status: completed and verified on Linux.

Latest completed commit:

```text
6f2c6a4 implement phase C.12-C.13 second brain service and js api
```

### Phase C.14-C.15 — AutomationService + JsApi facade

Status: completed and verified on Linux.

Latest completed commit:

```text
6b36042 implement phase C.14-C.15 automation service and js api
```

## Phase C Exit Audit

```text
Branch: prd-v31-migration
Working tree: clean
Tests: 341 passed
Latest completed commit: c58130b wire app web to js api factory
```

Phase C backend service and JsApi facade slices (C.1 through C.15) are complete and verified on Linux.

All previously deferred items now implemented:

- Project action JsApi facade (C.8c-C.8e)
- Settings/linkbank JsApi facade (C.11)
- SecondBrainService foundation (C.12-C.13)
- AutomationService foundation (C.14-C.15)

Remaining deferred:

- Frontend / pywebview production wiring
- Actual Windows manual testing
- Outlook/Teams real execution
- Automation action execution beyond rule evaluation
- Persistent automation logs
- Real Second Brain filesystem index

## Phase D-pre — app_web → JsApi Factory Wiring

Status: completed and verified on Linux.

Verified scope:

- `app_web.py` exposes `create_js_api()` factory.
- Factory constructs and wires `CacheDb`, `DashboardService`, `NotificationService`, `ReportService`, `AutomationService`, `SecondBrainService` into `JsApi`.
- `_SettingsAdapter` bridges `SettingsStore.read()` → `get_settings()` protocol.
- `app_web` import is Linux-safe (no pywebview at import time).
- 11 targeted tests cover import safety, factory existence, JsApi identity, and wired delegation for dashboard/notification/settings/report/automation/second_brain.

Latest completed commit:

```text
c58130b wire app web to js api factory
```

Known remaining gap:

- `ProjectService` not yet wired — lacks `list_projects`/`get_project`/etc. protocol methods. Deferred to later phase (service protocol adapter work).

## Phase D Progress

### Phase D.1 — Svelte frontend scaffold

Status: completed and verified on Linux.

Verified scope:

- `frontend/package.json` with Svelte 5, Vite 6, TypeScript 5.8, Tailwind 4.
- `frontend/tsconfig.json` with strict mode and Svelte integration.
- `frontend/vite.config.ts` with `@sveltejs/vite-plugin-svelte` and `@tailwindcss/vite`.
- `frontend/src/app.html` pywebview HTML shell.
- `frontend/src/main.ts` Vite entry point with `App.svelte` mount.
- `npm run check` (svelte-check) passes: 0 errors, 0 warnings.
- `npm run build` (vite build) outputs to `web/static/` cleanly.

Latest completed commit:

```text
c4b4974 implement phase D.1 svelte frontend scaffold
```

### Phase D.2 — Frontend design shell

Status: completed and verified on Linux.

Verified scope:

- Global CSS with enterprise banking color palette, typography (Inter), and component standards from PRD §6.
- `App.svelte` shell layout: sidebar + header + page content area.
- `Sidebar.svelte` with 6 nav items (Dashboard, Project Details, Second Brain, Report, Automations, Settings) + notification panel + footer.
- `Header.svelte` with page title + divider, datetime badge, year dropdown, search input, filter dropdown, Add Project button, refresh button.
- Tailwind bundled locally via Vite — no CDN.
- `svelte-check` clean, `vite build` clean.

Latest completed commit:

```text
fd76c0b implement phase D.2 frontend design shell
```

### Phase D.3 — Static dashboard layout

Status: completed and verified on Linux.

Verified scope:

- `Dashboard.svelte` with KPI status filter bar (All, UAT Prepare, Prod Ready, Implemented, Postponed).
- Table card with header "CR - Project Summary Table" and 10 columns (No, Main Project, Sub Project, Start Datetime, End Datetime, Drone Ticket, Drone State, CR Number, CR State, Actions).
- Static placeholder rows rendered with alternating row colors.
- Filter tabs toggle active state (UI-only, no data binding yet).
- Loading, error, idle state banners.
- `svelte-check` clean, `vite build` clean.

Latest completed commit:

```text
80c9342 implement phase D.3 static dashboard layout
```

### Phase D.4 — Frontend bridge wrapper

Status: completed and verified on Linux.

Verified scope:

- `bridge.ts` with `isPywebviewReady()`, `callBridge<T>()` typed wrapper.
- `BridgeResponse<T>`, `BridgeErrorCode`, `PywebviewApi` types.
- Graceful fallback when `window.pywebview.api` missing (dev/browser mode).
- Three error codes: `BRIDGE_UNAVAILABLE`, `BRIDGE_METHOD_MISSING`, `BRIDGE_CALL_FAILED`.
- Passes through `{ ok, data, error }` BridgeResponse-shaped dicts.
- Wraps non-BridgeResponse returns as `{ ok: true, data }`.
- `DashboardProject`, `DashboardSummary`, `DashboardData`, `NotificationItem`, `EventItem` TypeScript interfaces.
- `svelte-check` clean, `vite build` clean.

Latest completed commit:

```text
f78080f implement phase D.4 frontend bridge wrapper
```

### Phase D.5 — Dashboard read binding

Status: completed and verified on Linux.

Verified scope:

- `Dashboard.svelte` calls `dashboard_list_projects` via bridge on mount/year change/refresh.
- Bridge-unavailable state: clear error with code `BRIDGE_UNAVAILABLE`.
- Bridge-available state: loading → loaded with real projects from backend.
- Status filter tabs show live counts from `DashboardSummary` via `by_project_state`.
- Table renders real `DashboardProject` rows with date formatting, project name, CR number, CR state.
- Search filters visible rows in-memory (debounce handled by parent).
- `$effect()` re-fetches on `selectedYear` or `fetchKey` change.
- `svelte-check` clean, `vite build` clean.

Latest completed commit:

```text
3e8ce99 implement phase D.5 dashboard read binding
```

### Phase D.6 — Dashboard controls behavior

Status: completed and verified on Linux.

Verified scope:

- Year dropdown in Header triggers `onYearChange` → re-fetches dashboard for selected year.
- Search input triggers `onSearchChange` → filters visible rows by project name, CR number, CR state, project state, year, project_path.
- Refresh button triggers `onRefresh` → increments `fetchKey` → re-fetches dashboard.
- "Add Project" button present in header (UI-only, no navigation wired yet — deferred to project details phase).
- Filter dropdown present in header (UI-only, no backend filter yet).
- `svelte-check` clean, `vite build` clean.

Latest completed commit:

```text
8ccbcef implement phase D.6 dashboard controls behavior
```

### Phase D.7 — Notification event binding

Status: completed and verified on Linux.

Verified scope:

- `App.svelte` loads notifications on mount via `notification_list` bridge call.
- Dismiss single notification via `notification_dismiss` bridge call with optimistic UI removal.
- Dismiss all notifications via `notification_dismiss_all` bridge call.
- Event polling at 5-second interval via `poll_events` bridge call.
- On `NOTIFICATION` event received → re-fetches notification list.
- `Sidebar.svelte` renders notifications from parent with loading/error/empty states.
- Notification items show title, relative time (Just now / Xm ago / Xh ago / date), message, dismiss button.
- Bridge-unavailable state handled gracefully (no polling started, notifications show unavailable).
- `svelte-check` clean, `vite build` clean.

Latest completed commit:

```text
44e5182 implement phase D.7 notification event binding
```

### Phase D.8 — app_web serves built Svelte static output

Status: completed and verified on Linux.

Verified scope:

- `project_tracker/app_web.py` resolves `web/static/index.html` for production startup.
- Built Svelte output under `web/static/` is served through pywebview HTTP server mode.
- Vite build output remains `web/static/`.
- `svelte-check` clean, `vite build` clean, Python tests clean.

Latest completed commit:

```text
8ac46de implement phase D.8 app web svelte static serving
```

### Phase D.9 — App navigation/page shell

Status: completed and verified on Linux.

Verified scope:

- `App.svelte` tracks active page state.
- `Sidebar.svelte` nav routes between Dashboard, Project Details, Second Brain, Report, Automations, and Settings shells.
- `Header.svelte` title/controls update by active page.
- `PagePlaceholder.svelte` provides deferred-page shells for non-dashboard pages.
- Dashboard remains the only real data-bound frontend page in this phase.
- `svelte-check` clean, `vite build` clean, Python tests clean.

Latest completed commit:

```text
852c764 implement phase D.9 app navigation shell
```

### Phase D.10 — Report frontend page + read binding

Status: completed and verified on Linux.

Verified scope:

- `Report.svelte` replaces placeholder with real read-only report page.
- `report_filter_projects` JsApi bound with year, project_state, cr_state, search filters.
- `report_export_csv` JsApi bound — CSV download via Blob without backend changes.
- KPI summary row: Total, UAT Prepare, PROD Ready, Implemented, Postponed, Canceled.
- Report table: 11 columns from `DashboardProject` DTO.
- Loading, error, empty, loaded states implemented.
- No backend changes, no mutations, no polling.
- `App.svelte` routes "report" page to `Report` component.
- `svelte-check` clean, `vite build` clean, Python tests clean.

Latest completed commit:

```text
fc0d721 implement phase D.10 report frontend binding
```

### Phase D.11 — Settings frontend page + read/write binding

Status: completed and verified on Linux.

Verified scope:

- `Settings.svelte` replaces placeholder with real Settings page.
- `settings_get` JsApi bound — loads settings on mount via bridge.
- `settings_update` JsApi bound — local edit before explicit Save.
- No autosave, no polling.
- Help Center sidebar with 10 searchable help topics.
- Form fields organized in General, Behavior, and Paths cards.
- Pass-through of unrecognized DTO keys on save.
- Bridge-unavailable and error states handled.
- Save success toast with 2.5s auto-dismiss.
- `App.svelte` routes "settings" page to `Settings` component.
- `svelte-check` clean, `vite build` clean, Python tests clean.

Latest completed commit:

```text
eae30f7 implement phase D.11 settings frontend binding
```

### Phase D.12 — Link Bank read binding

Status: completed and verified on Linux.

Verified scope:

- `SecondBrain.svelte` routes to read-only Link Bank section (default tab).
- `linkbank_get` JsApi bound — loads link bank data on mount via bridge.
- `app_web.py` `create_js_api()` wires `_LinkBankAdapter` from `LinkBankStore`.
- Link cards rendered with name, URL, category badge, notes.
- Category dropdown filter (local-only) and free-text search (name/URL/notes/category).
- Notes tab remains deferred placeholder ("Coming next — Landing in Phase E").
- Link count badge and "Add/Edit deferred" hint in toolbar.
- Bridge-unavailable, loading, error, and empty states handled.
- Add/edit/archive deferred — `_LinkBankAdapter` raises `RuntimeError` for mutations.
- No backend changes, no polling.
- `svelte-check` clean, `vite build` clean, Python tests clean.

Latest completed commit:

```text
ab195b0 implement phase D.12 link bank read binding
```

### Phase D.13 — Read-only frontend pages (Project Details, Automations, Second Brain Notes)

Status: completed and verified on Linux.

Verified scope:

- `ProjectDetails.svelte` replaces placeholder with read-only project list + detail panel.
  - `project_list` JsApi bound with year filter (dynamic year options from `year_list`).
  - `project_get` JsApi bound on row select — shows CR info, subprojects, files, notes.
  - `subproject_list`, `file_list`, `notes_get` JsApi bound in parallel with detail load.
  - Detail panel: CR number, CR state, start/end datetime, T-10 status, drone ticket count.
  - Subprojects, files, and notes sections with deferred hints.
  - Loading, error, empty, loaded states implemented.
  - All mutations deferred (add/edit/delete, CR/Drone state change, folder move, rename).
- `Automations.svelte` replaces placeholder with read-only rules tab + evaluate preview.
  - `automation_list_rules` JsApi bound — renders rules with name, enabled badge, conditions.
  - `automation_evaluate_rule` JsApi bound per rule — shows Passed/Failed/Skipped result badge.
  - Tab bar: Rules (live), Outlook (deferred), Teams (deferred), Scheduler (deferred).
  - No Outlook/Teams/COM/pyautogui execution.
  - No rule create/edit/delete.
- `SecondBrain.svelte` Notes tab added alongside preserved Link Bank.
  - `second_brain_list` JsApi bound on Notes tab mount.
  - `second_brain_search` JsApi bound via search input (live search, falls back to list on empty).
  - `second_brain_get` JsApi bound on note row click — detail panel with type, state, flags.
  - Pin/Favorite/Edit deferred (read-only preview only).
  - Link Bank D.12 binding preserved unchanged.
- `App.svelte` routes `project-detail` → `<ProjectDetails />`, `automations` → `<Automations />`.
  - No more placeholder shells for these two pages.
- No backend, js_api, package, or dependency changes.
- `svelte-check` clean (90 files, 0 errors, 0 warnings), `vite build` clean, Python tests 355 passed.

Latest completed commit:

```text
6eec35b implement phase D.13 read-only frontend pages
```

### Phase D.14 — Frontend polish pass

Status: completed and verified on Linux.

Verified scope:

- `frontend-polish.md` added as supplemental UI polish guidance.
- CSS-only polish pass — no component logic, API, bridge, or backend changes.
- `focus-visible` accessibility baseline added via global styles.
- Notification spacing normalized in Sidebar.
- Shared polish utilities added (`styles.css` polish utilities section).
- Global disabled control styling added.
- No functionality changed.
- No API/bridge changed.
- No backend/package changes.
- `svelte-check` clean (90 files, 0 errors, 0 warnings), `vite build` clean, Python tests 355 passed.

Latest completed commit:

```text
11f43d2 implement phase D.14 frontend polish pass
```

### Phase D.15a — Project Details read-path production wiring

Status: completed and verified on Linux.

Verified scope:

- `create_js_api()` runtime gap fixed for Project Details read methods.
- `year_list` wired through `_YearServiceAdapter` — discovers digit-named dirs from SettingsStore.root_folder.
- `project_get` wired through `_ProjectServiceAdapter.get_project()` — reads MetadataStore, extracts cr_number via `extract_cr_number()`.
- `subproject_list` wired through `_ProjectServiceAdapter.list_subprojects()` — delegates to `discover_subproject_paths()`.
- `file_list` wired through `_FileServiceAdapter.list_files()` — read-only, no open/write/delete.
- `notes_get` wired through `_NotesServiceAdapter.get_notes()` — reads from MetadataStore.
- `_ProjectServiceAdapter` now accepts `MetadataStore` alongside `DashboardService`.
- All mutations remain deferred (8 tests prove `SERVICE_UNAVAILABLE`).
- No frontend source changed.
- No `js_api.py` signature changes.
- No backend DTO changes.
- `tests/test_phase_d_app_web_project_details_read_wiring.py` added (17 tests).
- Project Details frontend from D.13 now has real runtime read support.
- `svelte-check` clean (90 files, 0 errors, 0 warnings), `vite build` clean, Python tests 372 passed.

Latest completed commit:

```text
080d684 implement phase D.15a project details read wiring
```

### Phase D.15b — CR Link update end-to-end

Status: completed and verified on Linux.

Verified scope:

- `cr_update_link` production runtime wiring through `create_js_api()`.
- `_ProjectServiceAdapter.update_cr_link()` performs metadata-only mutation — reads `MetadataStore`, sets `cr_link`, updates `updated_at`, persists, returns refreshed DTO with `cr_number` extracted via `extract_cr_number()`.
- ProjectDetails CR Link explicit Save UI — `cr-link-input` + Save button, no autosave, disabled while saving or unchanged.
- Save success/error feedback with 2.5s auto-dismiss on success.
- No CR state mutation.
- No Drone mutation.
- No folder/file/project mutation.
- No `js_api.py` signature changes.
- No backend DTO changes.
- `svelte-check` clean (90 files, 0 errors, 0 warnings), `vite build` clean, Python tests 377 passed.

Latest completed commit:

```text
7d5c811 implement phase D.15b cr link update
```

### Phase D.16 — Automation rules evaluate-all preview

Status: completed and verified on Linux.

Verified scope:

- "Evaluate All (preview)" button added to Automations rules tab.
- `automation_evaluate_all` JsApi bound — calls with empty context, read-only, no side effects.
- Results populate per-rule evaluation badges (Passed/Failed/Skipped) in the existing rules list.
- Disabled state while pending.
- Hint text explains empty context / no side effects.
- No Outlook/Teams/COM/pyautogui execution.
- No scheduler start/stop.
- No rule create/edit/delete.
- No backend, js_api, or package changes.
- `svelte-check` clean (90 files, 0 errors, 0 warnings), `vite build` clean, Python tests 377 passed.

Latest completed commit:

```text
ed0f74c improve automation rules preview
```

## Phase D Exit Audit

```text
Branch: prd-v31-migration
Working tree: clean
svelte-check: 90 files, 0 errors, 0 warnings
vite build: clean, outputs to web/static/
Tests: 377 passed
Latest completed commit: ed0f74c improve automation rules preview
```

Phase D.1 through D.16 Svelte frontend scaffold, design shell, dashboard, bridge wrapper, read binding, controls behavior, notification event binding, Svelte static serving, app navigation/page shell, report frontend page, settings frontend page, link bank read binding, project details read-only page, automations read-only/rules preview page, second brain notes read-only list/search/detail, frontend polish pass, Project Details read-path production wiring, CR Link update end-to-end, and automation rules evaluate-all preview are complete and verified on Linux.

Remaining deferred:

- Project Details mutations (create/update/rename)
- Drone state transitions (guarded, separate from metadata edit)
- Folder move/rename/delete
- File write/delete/open execution
- Automation rule create/edit/delete
- Outlook/Teams/COM/pyautogui execution
- Scheduler real frontend controls
- Second Brain note write/edit/delete/pin/favorite
- Link Bank add/edit/archive/tags/pin/favorite
- Windows manual test
- packaging

## Phase E Progress

### Phase E.1 — Notes persistence (notes.md)

Status: completed and verified on Linux.

Verified scope:

- Notes stored in `notes.md` per PRD (JSON notes field is legacy/unused).
- `_NotesServiceAdapter.get_notes()` reads `{project_path}/notes.md`.
- `_NotesServiceAdapter.update_notes()` writes `{project_path}/notes.md`.
- Missing `notes.md` returns empty string (backward compatible).
- `update_notes` creates `notes.md` if absent.
- No `ProjectMetadata` serialization change (Phase A.1 tests preserved).
- ProjectDetails Notes editable textarea with explicit Save Notes button.
- No autosave. Local edit state before save. Success/error feedback.
- `svelte-check` clean, `vite build` clean, Python tests 385 passed.

Latest completed commit:

```text
e87da33 implement phase E.1 notes persistence
```

### Phase E.2 — Drone metadata CRUD

Status: completed and verified on Linux.

Verified scope:

- `project_get` response now includes `drone_tickets` array (not just count).
- `drone_add` appends new ticket to metadata (default state: UAT).
- `drone_update` edits `drone_link`, `owner`, `subfolder_name` at index. Does NOT change `drone_state` (state guards respected).
- `drone_delete` removes ticket at index.
- All operations metadata-only, persist via MetadataStore.
- Index-based targeting (existing JsApi contract).
- ProjectDetails frontend: drone list, Add/Edit/Delete buttons.
- No folder/file/project mutations.
- No `js_api.py` signature changes.
- `svelte-check` clean, `vite build` clean, Python tests 396 passed.

Latest completed commit:

```text
e6352f9 implement phase E.2 drone metadata actions
```

### Phase E.3 — Guarded CR state update

Status: completed and verified on Linux.

Verified scope:

- `cr_update_state` wired through `validate_cr_transition()` state-machine guard.
- Allowed manual transitions succeed and persist `cr_state` + `cr_state_updated_at`.
- REOPEN rejected as persistent target.
- IN-PROGRESS rejected as manual target (automatic-only).
- Invalid transitions fail with controlled error.
- No folder moves triggered on CR state change.
- Frontend dropdown uses real CRState enum values (REOPEN excluded).
- Explicit Save button, disabled when unchanged.
- `svelte-check` clean, `vite build` clean, Python tests 407 passed.

Latest completed commit:

```text
f667344 implement phase E.3 guarded cr state update
```

## Phase E Exit Audit

```text
Branch: prd-v31-migration
Working tree: clean
svelte-check: 90 files, 0 errors, 0 warnings
vite build: clean, outputs to web/static/
Tests: 407 passed
Latest completed commit: f667344 implement phase E.3 guarded cr state update
```

## Phase F Progress

### Phase F.1 — Guarded drone state update

Status: completed and verified on Linux.

Verified scope:

- `_ProjectServiceAdapter.update_drone()` now routes `drone_state` through `validate_drone_state_change_allowed()` state-machine guard.
- Invalid transitions and empty `drone_link` rejected with controlled error.
- IN-PROGRESS rejected as manual target (automatic-only).
- `drone_state_updated_at` set on success.
- Drone field edit (link/owner/subfolder) from E.2 preserved.
- ProjectDetails per-row state dropdown + Save State button.
- Metadata-only, no folder moves, no `js_api.py` signature change.
- `svelte-check` clean, `vite build` clean, Python tests 413 passed.

Latest completed commit:

```text
d8e2115 implement phase F.1 guarded drone state update
```

### Phase F.2 — Second Brain pin/favorite

Status: BLOCKED — deferred.

Reason: production `SecondBrainService()` uses default `items_provider=list` → empty items, in-memory only, no persistence layer. PRD lists "Real Second Brain filesystem index" as deferred. Wiring would produce fake success (empty list, lost state on restart). Deferred until real filesystem index exists.

### Phase F.3 — Link Bank stable ID actions

Status: completed and verified on Linux.

Verified scope:

- Link model gains stable `id` (uuid4 hex) + `archived` flag.
- Backward-compatible: legacy links without `id` get one generated on read; `archived` defaults to "false".
- `_LinkBankAdapter` wires `add_link` (http/https validation), `update_linkbank` (by id), `archive_link` (soft archive by id).
- Frontend Link Bank: Add Link form, inline Edit/Save, Archive button, show-archived toggle, local search/category filter preserved.
- No destructive delete. No `js_api.py` signature change.
- `svelte-check` clean, `vite build` clean, Python tests 431 passed.

Latest completed commit:

```text
7fed61b implement phase F.3 link bank stable id actions
```

### Phase F.4 — Automation preview UI polish

Status: completed and verified on Linux.

Verified scope:

- Rule conditions render as readable field/operator/value pills instead of raw JSON.
- `exists` operator omits value segment. Raw JSON fallback when `field` missing.
- Frontend-only, read-only. No bridge/backend change.
- `svelte-check` clean, `vite build` clean, Python tests 431 passed.

Latest completed commit:

```text
4966704 improve phase F.4 automation preview ui
```

## Phase F Exit Audit

```text
Branch: prd-v31-migration
Working tree: clean
svelte-check: 90 files, 0 errors, 0 warnings
vite build: clean, outputs to web/static/
Tests: 431 passed
Latest completed commit: 4966704 improve phase F.4 automation preview ui
```

## Phase G Progress

### Phase G.1 — Project create/update contract

Status: completed and verified on Linux.

Verified scope:

- `project_create` wired through `create_js_api()` and `_ProjectServiceAdapter`.
- Creates project folder only under configured root/year/`UAT_PREPARE` using temp-dir-tested behavior.
- Validates project name with Windows folder-name rules.
- Writes initial `project_data.json` metadata with created/updated timestamps.
- `project_update` metadata-only: project name, implementation plan, CR link, start/end datetimes.
- ProjectDetails frontend adds explicit Edit Metadata + Save.
- Rename/delete remain deferred.
- `svelte-check` clean, `vite build` clean, Python tests 443 passed.

Latest completed commit:

```text
f673e95 implement phase G.1 project create update contract
```

### Phase G.2 — Folder transitions audit

Status: BLOCKED — deferred.

Reason: existing ProjectService transition methods physically move folders via `shutil.move`, require full AppSettings/guard context, and need explicit confirmation UX + guard-reason display before production wiring. Deferred to a dedicated high-risk filesystem phase.

### Phase G.3 — Second Brain read-only filesystem index

Status: completed and verified on Linux.

Verified scope:

- `SecondBrainService` production wiring now receives a read-only filesystem provider backed by `AppSettings.second_brain_folder`.
- Missing/unconfigured folder returns empty list safely.
- Recursively scans files, skips hidden paths, derives stable IDs from relative paths, classifies `.md`/`.txt` as notes.
- Excerpt read is limited and guarded; no note write/delete/edit operations.
- Existing `second_brain_list`, `second_brain_search`, and `second_brain_get` now return real configured-folder data.
- Persistent pin/favorite/note write remain deferred.
- `svelte-check` clean, `vite build` clean, Python tests 453 passed.

Latest completed commit:

```text
027c2b7 implement phase G.3 second brain filesystem index
```

## Release Candidate Exit Audit

```text
Branch: prd-v31-migration
Working tree: clean
svelte-check: 90 files, 0 errors, 0 warnings
vite build: clean, outputs to web/static/
Tests: 453 passed
Latest completed commit: 027c2b7 implement phase G.3 second brain filesystem index
```

## RC Hardening (2026-06-08)

Four hardening slices completed:

| Slice | Commit    | Subject                                                                                                                                              |
| ----- | --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| RC.1  | `1b9183a` | fix release candidate bridge availability — `poll_events` wired as JsApi instance method                                                             |
| RC.2  | `1122206` | harden release candidate frontend states — SecondBrainItem type fix, null-guard updated_at, drop `(detail as any)` casts, stale deferred bar updated |
| RC.3  | `ff38fa1` | polish release candidate ui — disable non-functional Add Project and CR filter in header                                                             |
| RC.4  | `b549e90` | update release candidate manual test plan — add RC hardening baseline notes                                                                          |

Post-hardening checks:

```text
Branch: prd-v31-migration
Working tree: clean
svelte-check: 90 files, 0 errors, 0 warnings
vite build: clean
Tests: 453 passed
py_compile: pass (app_web.py, js_api.py — Linux)
Latest commit: b549e90 update release candidate manual test plan
```

RC readiness: **ready for manual Windows test**. All Linux-automatable checks pass. All high-risk actions deferred. Bridge fully wired. Frontend states hardened across all 6 pages.

Remaining deferred after RC hardening:

- Folder move/rename/delete/transitions
- File write/delete/open external app
- Outlook/Teams/COM/pyautogui execution
- Scheduler real frontend controls/status
- Automation rule CRUD persistence/execution
- Second Brain persistent pin/favorite/note write
- Windows manual test
- Windows packaging

## RC Polish & Documentation (post-hardening, 2026-06-08)

Slices completed after the RC Hardening section above (all docs/UI-copy only,
no bridge contract or service signature changes):

| Commit    | Subject                                                                                          |
| --------- | ------------------------------------------------------------------------------------------------ |
| `75780e9` | update project status after rc hardening                                                         |
| `8cf64b6` | style: format markdown files with prettier                                                       |
| `572eb23` | add kiro steering for project tracker dbs (`.kiro/steering/*.md`)                                 |
| `c74d47d` | improve windows manual test documentation (`docs/windows-manual-test-checklist.md`)              |
| `fa0b5f4` | document packaging readiness (`docs/packaging-readiness.md`)                                      |
| `0476b94` | fix release candidate polish issues — replace stale "Landing in Phase E" copy with accurate deferred-pending-Windows-integration messaging in `Automations.svelte` and `SecondBrain.svelte` |

Post-polish checks:

```text
Branch: prd-v31-migration
Working tree: clean
svelte-check: 0 errors, 0 warnings
vite build: clean, outputs to web/static/
Tests: 453 passed
py_compile: pass (app_web.py, js_api.py — Linux)
Latest commit: 0476b94 fix release candidate polish issues
```

No stale "Landing in Phase E" copy remains in the Svelte frontend. Bridge
consistency re-audited: all 32 frontend `callBridge(...)` names map to wired
`JsApi` methods in `create_js_api()`; `window.pywebview` is referenced only
inside `frontend/src/lib/bridge.ts`. RC readiness unchanged: **ready for manual
Windows test**.

## Phase 0 Boundary

Phase 0 documentation alignment is complete. `PROJECT_STATUS_old.md` remains historical reference unless deletion is explicitly approved.

No legacy/reference files should be deleted without explicit approval.
