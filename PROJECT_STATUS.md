# Project Status

## Current Phase

**Phase B readiness — Infrastructure / persistence / SQLite cache planning**

Phase A is completed and verified on Linux. Next work should be Phase B planning before any infrastructure implementation.

## Source of Truth

`PRD.md` v3.1 is the product and architecture source of truth.

If current code, old docs, comments, folder structure, or reference prototypes conflict with `PRD.md`, report the conflict before implementation.

## Current Repo Reality Summary

Repository has completed Phase A core-domain migration slices and is ready for Phase B planning.

Current state:

- `PRD.md` v3.1 exists and is authoritative.
- `CLAUDE.md` aligns with PRD v3.1 migration direction.
- Phase A core domain work is implemented and verified.
- Current pywebview shell exists in `project_tracker/app_web.py`, but it still loads static HTML from `frontend/` through a file URI.
- Static HTML frontend files exist under `frontend/` and are legacy/reference, not migrated production UI.
- Svelte + TypeScript + Vite structure is missing.
- SQLite rebuildable cache/index is missing.
- APScheduler-backed scheduler/event flow is missing.
- Background-to-frontend event queue is missing.
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

Current backend package exists under `project_tracker/`, with Phase A core-domain work complete and infrastructure/service/frontend migration still pending.

Known gaps against PRD v3.1:

- SQLite cache/index is missing.
- `project_tracker/infrastructure/cache_db.py` is missing.
- APScheduler usage is missing.
- Event queue is missing.
- Target `web/js_api.py` bridge module is missing.
- Target `web/event_queue.py` module is missing.
- Existing bridge logic lives inside `project_tracker/app_web.py` and does not yet match the PRD bridge architecture.

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

## Next Recommended Phase

**Phase B — Infrastructure / persistence / SQLite cache planning**

Do not start infrastructure implementation until a Phase B plan is approved.

Phase B should cover:

- filesystem operations
- metadata store
- settings store
- link bank store
- SQLite rebuildable cache/index
- guarded Outlook/Teams infrastructure stubs
- safe delete behavior

Do not start Svelte, APScheduler service behavior, pywebview bridge rewrite, or frontend migration during Phase B planning unless explicitly included in an approved Phase B plan.

## Phase 0 Boundary

Phase 0 documentation alignment is complete. `PROJECT_STATUS_old.md` remains historical reference unless deletion is explicitly approved.

No legacy/reference files should be deleted without explicit approval.
