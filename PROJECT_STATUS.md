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

## Next Phase

**Next phase: Phase A — Core Domain readiness**

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
