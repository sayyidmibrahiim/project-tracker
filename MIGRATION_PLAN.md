# Migration Plan

## Rule: PRD v3.1 Phase Order

Migration follows `PRD.md` v3.1 phase order. Do not implement the whole PRD at once.

Each phase needs explicit approval and verification before moving to the next phase.

## Phase 0 — PRD Lock / Migration Readiness

### Entry Criteria

- `PRD.md` v3.1 exists.
- User approves Phase 0 documentation-only work.
- No production code changes are in scope.

### Allowed Files

- `PROJECT_STATUS.md`
- `MIGRATION_PLAN.md`
- `redesign_ui/_REFERENCE_ONLY.md`

### Forbidden Files

- `PRD.md`
- `requirements.txt`
- `project_tracker/`
- `frontend/`
- `redesign_ui/*.py`
- historical PRD/status snapshots deleted only after explicit approval

### Exit Criteria

- `PROJECT_STATUS.md` records current migration status.
- `MIGRATION_PLAN.md` records phase order, entry criteria, and exit criteria.
- `redesign_ui/_REFERENCE_ONLY.md` clarifies PyQt6/reference/static-HTML boundaries.
- Git diff shows only Phase 0 allowed files changed.
- No production code is changed.

### Slice 0 Truth Reset Addendum — 2026-06-08

This addendum supersedes stale phase-status wording when it conflicts with `PROJECT_STATUS.md` current summary. It does not supersede `PRD.md` v3.1.

Purpose:

- Reconcile old phase labels with current PRD-completion implementation reality.
- Make Windows-only gates explicit before release packaging.
- Prevent production coding against stale deferred/gap lists.

Acceptance categories:

| Category         | Meaning                                                                    |
| ---------------- | -------------------------------------------------------------------------- |
| `linux-verified` | Automated Linux tests/build/import checks passed for this area.            |
| `safe-slice`     | Feature works in guarded/local scope but still needs Windows manual smoke. |
| `windows-manual` | Cannot be fully verified on Linux; must run on Windows.                    |
| `docs-only`      | Planning/status/checklist work only.                                       |
| `deferred`       | Explicitly outside current release scope or blocked by Windows gate.       |

Current PRD-to-release acceptance matrix:

| Area                         | Category       | Required next action                                                                         |
| ---------------------------- | -------------- | -------------------------------------------------------------------------------------------- |
| PRD/status truth             | docs-only      | Keep `PROJECT_STATUS.md` current after every verified slice.                                 |
| Dependency/runtime alignment | safe-slice     | Re-check `pyproject.toml`, `requirements.txt`, frontend package metadata before packaging.   |
| Bridge/API contract          | linux-verified | Keep `test_bridge_contract_guard.py` green after frontend/bridge edits.                      |
| Main project userflow        | safe-slice     | Run manual Windows disposable-workspace flow before release.                                 |
| Filesystem operations        | windows-manual | Verify `send2trash`, `os.startfile`, path-with-spaces, and non-admin permissions on Windows. |
| Second Brain                 | safe-slice     | Verify filesystem index, note CRUD, pin/favorite, and reload persistence on Windows.         |
| Link Bank                    | safe-slice     | Verify link/category CRUD, archive/restore, and `link_bank.json` persistence on Windows.     |
| Report CSV                   | safe-slice     | Verify save dialog/path permissions and Excel-compatible CSV on Windows.                     |
| Outlook automation           | windows-manual | Test draft-first flow with real Outlook profile; send-now only with explicit confirmation.   |
| Teams automation             | windows-manual | Test preview-first paste; auto-send only with `teams_auto_send=true` and cancel path.        |
| Scheduler / Rules Engine     | safe-slice     | Verify persistence/logs on Linux; verify timed UI behavior on Windows.                       |
| PyInstaller packaging        | windows-manual | Build only on Windows; include `web/static/` and `assets/`; test clean launch.               |
| Final zip handoff            | windows-manual | Zip only after manual Windows checklist is green.                                            |

## Phase A — Core Domain

### Scope

Build or verify:

- `core/enums.py`
- `core/models.py`
- `core/state_machine.py`
- `core/rules.py`
- `core/exceptions.py`

### Entry Criteria

- Phase 0 exit criteria met.
- User approves a Phase A implementation plan.
- Relevant PRD core-domain sections are reviewed.

### Exit Criteria

- All enum values match PRD v3.1.
- Core models match PRD v3.1 data rules.
- `project_state` is never stored in `project_data.json`.
- Notes storage direction is clear: `notes.md` is primary; JSON `notes` is legacy/not used.
- State transition guards are covered by tests.
- T-10 rule uses `cr_pending_approval_at`.
- Folder name validation covers Windows-invalid and reserved names.
- CR/Drone link extraction is covered by tests.
- Core layer has no UI, service, infrastructure, or Windows-only imports.
- Relevant Python tests pass on Linux.

## Phase B — Infrastructure & Stores

### Scope

Build or verify:

- filesystem operations
- metadata store
- settings store
- link bank store
- SQLite rebuildable cache/index
- guarded Outlook/Teams infrastructure stubs
- safe delete behavior

### Entry Criteria

- Phase A exit criteria met.
- User approves a Phase B implementation plan.
- SQLite cache responsibilities are reviewed from PRD v3.1.

### Exit Criteria

- `cache_db.py` exists and creates PRD-defined SQLite tables.
- SQLite is rebuildable and not source of truth.
- Metadata/settings/link bank writes are atomic.
- Filesystem scanner derives project year and folder state from paths.
- Delete behavior uses Recycle Bin through `send2trash` on Windows.
- Windows-only integrations are lazy/guarded and do not crash on Linux.
- Relevant infrastructure tests pass on Linux.

## Phase C — Services & Event Queue

### Scope

Build or verify:

- project service orchestration
- scanner service cache population
- automation service
- scheduler service
- second brain service
- report service
- `web/event_queue.py`
- `web/js_api.py`

### Entry Criteria

- Phase B exit criteria met.
- User approves a Phase C implementation plan.
- APScheduler and event queue behavior are reviewed from PRD v3.1.

### Exit Criteria

- Services coordinate use cases without putting business rules in UI code.
- Event queue supports background-to-frontend polling.
- Bridge methods return predictable response objects.
- Scheduler service manages APScheduler jobs.
- Report service supports filtered CSV export logic.
- Second Brain service supports file/tree/search operations needed by PRD.
- Relevant service and bridge tests pass on Linux.

## Phase D — Svelte Frontend Shell

### Scope

Build:

- Svelte app structure
- TypeScript config
- Vite config
- Tailwind bundled build
- app shell
- sidebar
- header
- notification panel
- router/page selection
- frontend stores
- typed bridge wrappers

### Entry Criteria

- Phase C exit criteria met.
- User approves a Phase D implementation plan.
- Context7 docs are consulted for Svelte, Vite, and Tailwind before build configuration changes.

### Exit Criteria

- `frontend/package.json`, `frontend/tsconfig.json`, `frontend/vite.config.ts`, and `frontend/src/` exist.
- Vite builds to `web/static/`.
- Tailwind is bundled locally through the frontend build.
- Static HTML is no longer treated as migrated production UI.
- App shell matches PRD navigation structure.
- Frontend build passes.

## Phase E — Dashboard & Project Details

### Scope

Build:

- Dashboard page
- Project Details page
- Add Year flow
- Add Project flow
- KPI cards
- filter tabs
- project table
- inline CR/Drone editing
- project/subproject/file/notes/history flows
- locking and REOPEN flows

### Entry Criteria

- Phase D exit criteria met.
- User approves a Phase E implementation plan.
- UI preview approach is approved before production frontend edits.

### Exit Criteria

- Dashboard uses real backend/cache data.
- Project Details connects to real project data.
- No migrated screen is static/dummy.
- CR/Drone state changes go through Python services.
- Notes autosave writes to `notes.md`.
- Relevant tests/build pass.
- Windows-only behavior is marked for manual Windows verification where needed.

## Phase F — Second Brain, Link Bank, Report

### Scope

Build:

- Second Brain Notes tab
- Link Bank tab
- Report page
- search/filter behavior
- local persistence
- CSV export

### Entry Criteria

- Phase E exit criteria met.
- User approves a Phase F implementation plan.

### Exit Criteria

- Second Brain shows Second Brain Notes and Project Documents.
- Search covers notes/files/tags as specified.
- Link Bank CRUD persists to `link_bank.json`.
- Report filters and CSV export work from real data.
- Relevant tests/build pass.

## Phase G — Automations

### Scope

Build:

- Outlook tab
- Teams tab
- Scheduler tab
- Rules Engine tab
- Windows-guarded automation services

### Entry Criteria

- Phase F exit criteria met.
- User approves a Phase G implementation plan.
- Windows integration boundaries are reviewed.

### Exit Criteria

- Outlook automation defaults to draft-first behavior.
- Teams automation defaults to preview/paste-first behavior.
- APScheduler entries persist and trigger as specified.
- Rules Engine executes ordered actions and logs results.
- Linux tests cover guarded behavior.
- Windows manual verification is completed or explicitly deferred.

## Phase H — Settings & Packaging

### Scope

Build:

- Settings page
- Help Center
- first-run setup
- packaging configuration
- Windows packaging verification

### Entry Criteria

- Phase G exit criteria met.
- User approves a Phase H implementation plan.

### Exit Criteria

- Settings persist under app data path.
- Help Center renders/searches local help content.
- Fresh install creates app data defaults.
- PyInstaller build includes `web/static/` and `assets/`.
- Windows packaging is performed only on Windows.
- Clean Windows verification is completed or explicitly deferred.

## Global Migration Rules

- Do not implement all PRD at once.
- Work phase by phase.
- Do not skip verification gates.
- Do not treat static HTML as migrated Svelte UI.
- Do not treat PyQt6 prototypes as production code.
- Do not add dependencies without explicit approval unless already approved by PRD v3.1 and current phase plan.
- Do not delete legacy/reference files without explicit approval.
- Do not touch files outside the approved phase scope.
