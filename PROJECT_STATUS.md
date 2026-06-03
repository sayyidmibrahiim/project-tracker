# Project Status

## Current Phase

**Phase 0 — Migration readiness and tracking**

This file supersedes `PROJECT_STATUS_old.md`. Keep `PROJECT_STATUS_old.md` as historical reference only unless deletion is explicitly approved.

## Source of Truth

`PRD.md` v3.1 is the product and architecture source of truth.

If current code, old docs, comments, folder structure, or reference prototypes conflict with `PRD.md`, report the conflict before implementation.

## Current Repo Reality Summary

Repository is partially migrated and not ready for PRD v3.1 implementation beyond Phase 0 documentation work.

Current state:

- `PRD.md` v3.1 exists and is authoritative.
- `CLAUDE.md` already aligns with PRD v3.1 migration direction.
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

Current backend package exists under `project_tracker/`, with partial core, infrastructure, and service modules.

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

Status: implemented and verified on Linux.

Verified scope:

- `ProjectState.CANCELED` exists.
- `CRState.POSTPONED` exists.
- `CRState.REOPEN` remains as a deprecated compatibility value and must not be persisted by REOPEN flows.
- `ProjectMetadata.to_dict()` does not serialize `project_state`.
- `ProjectMetadata.to_dict()` does not serialize legacy `notes`.
- `ProjectMetadata.from_dict()` ignores legacy `notes` input so it is not re-emitted.
- `DroneTicket.owner` exists and defaults to an empty string.
- timezone-aware datetime serialization behavior is preserved.

Verification run:

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

Status: implemented and verified on Linux.

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
- T-10, deployment date guards, CR link guards, auto IN-PROGRESS predicates, and REOPEN service compatibility cleanup remain deferred.
- `project_tracker/services/` was not changed; existing `CRState.REOPEN` service compatibility debt remains for Phase A.2.2 or later.

Verification run:

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

Status: implemented and verified on Linux.

Verified scope:

- `CRState.REOPEN` remains as a deprecated compatibility enum value.
- `CRState.REOPEN` remains rejected as a persistent CR transition target.
- REOPEN is now folder-state-based in core helpers.
- REOPEN is allowed from `ProjectState.POSTPONED` and `ProjectState.CANCELED`.
- REOPEN is rejected from `ProjectState.UAT_PREPARE`, `ProjectState.PROD_READY`, and `ProjectState.IMPLEMENTED`.
- REOPEN result targets `ProjectState.UAT_PREPARE` and `CRState.PENDING_SUBMISSION`.
- `ProjectService.reopen_project()` moves reopened projects to `UAT_PREPARE`.
- `ProjectService.reopen_project()` persists `CRState.PENDING_SUBMISSION`, not `CRState.REOPEN`.
- REOPEN is recorded as a history action/event.
- `cancel_project()`, `postpone_project()`, T-10/rules/link guards, frontend, and pywebview bridge were not changed.

Verification run:

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

## Next Phase

**Next phase: Phase A.3 — Core rules and guards**

Phase A should verify or implement only core-domain readiness from PRD v3.1:

- enum values
- pure domain models
- state machine guards
- T-10 rule
- folder name validation
- CR/Drone link extraction
- organizational folder exclusion logic
- history entry model

Do not start Svelte, SQLite, APScheduler, pywebview bridge rewrite, or frontend migration during Phase A unless an approved Phase A implementation plan explicitly includes it.

## Phase 0 Boundary

Phase 0 allowed documentation files:

- `PROJECT_STATUS.md`
- `MIGRATION_PLAN.md`
- `redesign_ui/_REFERENCE_ONLY.md`

Phase 0 forbidden files:

- `PRD.md`
- `requirements.txt`
- `project_tracker/`
- `frontend/`
- `redesign_ui/*.py`
- `PRD_old.md`
- `PROJECT_STATUS_old.md`

No production code is implemented in Phase 0.
