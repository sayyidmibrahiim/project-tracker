# Master Prompt — Project Tracker DBS PRD/UI Completion

You are Claude Code working in `/home/sayyidmibrahim/Development/projects/project_tracker_dbs` on branch `prd-v31-migration`.

## Mission

Finish Project Tracker DBS until production app is as complete as possible against `PRD.md` v3.1 and UX intent from `redesign_ui/*.py`, then make it ready for Windows build/package handoff.

Target outcome:

- App behavior: 100% PRD-aligned where feasible.
- UI/UX: match PyQt6 prototype intent as closely as possible while implementing in Svelte, not PyQt.
- Edge cases: actively identify and fix gaps in userflow, state, persistence, safety, packaging, and Windows runtime assumptions.
- Verification: Linux-safe checks green; Windows-only gates explicitly prepared and not falsely claimed unless actually run on Windows.

## Non-negotiable source order

1. `PRD.md` v3.1 = product + architecture source of truth.
2. `CLAUDE.md` = repo operating rules.
3. `redesign_ui/*.py` + `redesign_ui/UI_FEATURE_DOCUMENTATION.md` = UX/reference only.
4. Current code/tests/docs = implementation reality.

If PRD conflicts with PyQt prototype, follow PRD unless a better approved userflow is obvious and does not violate PRD constraints. If code/docs conflict with PRD, report conflict before changing production code.

## Current known state

From latest status/audits:

- Backend/domain/bridge/Svelte implementation is mature and Linux-green.
- Recorded Linux checks: `pytest` 1696 passed; `svelte-check` 0 errors; Vite build clean; `py_compile` pass for `project_tracker/app_web.py` + `project_tracker/web/js_api.py`.
- Windows release not verified yet: WebView2/pywebview, Outlook COM, Teams `pyautogui`, `send2trash`, `os.startfile`, PyInstaller output, clean Windows launch.
- UI is not 100% AS-IS mirror of PyQt prototypes. Approx gaps from prior audit:
  - Dashboard ~75%
  - Project Details ~50%
  - Second Brain ~45%
  - Report ~60%
  - Automations ~35%
  - Settings ~85%
- Biggest UI/flow gaps: Automations, Project Details, Second Brain, Report, Dashboard details, Settings polish.
- Packaging docs/status may conflict around PyInstaller `.spec` existence. Reconcile before packaging.

## Mandatory first actions

1. Read:
   - `PRD.md`
   - `CLAUDE.md`
   - `PROJECT_STATUS.md`
   - `MIGRATION_PLAN.md`
   - `docs/windows-manual-test-checklist.md`
   - `docs/packaging-readiness.md`
   - `redesign_ui/UI_FEATURE_DOCUMENTATION.md`
   - all `redesign_ui/*.py` relevant to the UI page being worked on
2. Inspect current git status.
3. Do not overwrite or delete untracked local artifacts unless explicitly approved.
4. Report any PRD/status/packaging contradictions before coding.
5. Choose smallest useful skills/plugins/MCPs for the task:
   - planning/architecture: `superpowers:brainstorming`, `superpowers:writing-plans`, `harness-plan`, `architecture-drift`
   - implementation: `superpowers:subagent-driven-development` or `superpowers:executing-plans`
   - frontend: `frontend-design`, `frontend-polish`, Svelte/TS expertise, Context7 docs for Svelte/Vite/Tailwind if config/API behavior is version-sensitive
   - Python: `fullstack-dev-skills:python-pro`, `superpowers:test-driven-development`, `superpowers:verification-before-completion`
   - review/safety: `code-review`, `security-reviewer`, `secure-code-guardian`, `verify`
   - packaging/release: `harness-release`, `superpowers:finishing-a-development-branch`

## Work strategy

Do not try to fix whole app in one giant edit. Work page-by-page and flow-by-flow.

For each slice:

1. Build a parity matrix:
   - PRD requirement
   - PyQt prototype behavior/layout
   - current Svelte behavior
   - status: `done | gap | intentional deviation | Windows-only`
   - chosen fix
2. Pick best userflow. Prefer full-featured, automatic, low-friction workflow for deployment/support engineer.
3. Implement only that slice.
4. Add/update tests where practical.
5. Run verification.
6. Update `PROJECT_STATUS.md` and/or implementation plan docs.
7. Run review.

## UI target

Do not build new PyQt. Production UI stays:

- Svelte
- TypeScript
- Vite
- Tailwind bundled locally
- pywebview shell serving `web/static/`

Prototype goal is not literal PyQt code copy. Goal is PRD-compliant Svelte app that visually and behaviorally mirrors prototype intent:

- enterprise red/black/white palette
- utilitarian + modern minimalist density
- persistent sidebar notifications
- red header per page
- internally scrolling panels
- splitter-style layouts where PRD/prototype expects them
- no decorative fluff
- visible disabled states with reasons
- confirmations for destructive/automation actions
- clear loading/error/empty/saved states

## Page priority

### 1. Automations

Audit/fix toward PRD §16 and `redesign_ui/automations_redesign.py`.

Must include:

- Tab order: Outlook, Teams, Scheduler, Rules Engine.
- Outlook two-column send/download UI.
- Email Template Dialog flow.
- Downloaded Emails dialog.
- Teams automation dialog/preview/send flow.
- Scheduler entry CRUD/status/KPI.
- Rules Engine CRUD/logs/action ordering.
- Draft-first Outlook, preview-first Teams.
- `teams_auto_send=false` default.
- Windows-only COM/pyautogui guarded.

### 2. Project Details

Audit/fix toward PRD §12 and `redesign_ui/project_details_redesign.py`.

Must include:

- NEW_PROJECT mode.
- SHOW_EDIT mode.
- Project Command Center.
- Left identity/schedule/subprojects column.
- Right files/notes/history column.
- Subproject table.
- CR/Drone link edit + state guard UX.
- File/template actions.
- Notes markdown edit/preview/toolbar/autosave if feasible; if explicit Save remains, document deviation.
- Activity history.
- REOPEN/postpone/cancel/folder move confirmation flows.
- Locking rules visible and enforced by backend.

### 3. Second Brain + Link Bank

Audit/fix toward PRD §§13–14 and `redesign_ui/second_brain_redesign.py`.

Must include:

- Notes tree groups: Search Results, Pinned, Favorites, Second Brain Notes, Project Documents.
- Search/date/sort/filter.
- Create folder/file with inline rename or equivalent low-friction UX.
- Editable text/markdown/code files.
- Image preview.
- External open mode.
- Pin/favorite persistence.
- Markdown toolbar + preview.
- Backlinks/related notes/recent activity where feasible.
- Link Bank category-left/content-right split.
- Link detail panel, copy URL, tags, pin/favorite, archive/restore, import/export if PRD-required.

### 4. Report

Audit/fix toward PRD §15 and `redesign_ui/report_redesign.py`.

Must include:

- Year/month/folder-state/CR-state/Drone-state/search filters.
- Clear.
- Export CSV respecting active filters.
- KPI row.
- CR state / Drone state / monthly summary panels.
- Exact PRD table columns.
- Excel-compatible CSV.

### 5. Dashboard

Audit/fix toward PRD §11 and `redesign_ui/project_tracker_clean.py`.

Must include:

- Initial load + first-run root setup.
- Year dropdown + Add Year.
- Search debounce + highlight.
- Folder-state filter chips.
- KPI row.
- Inline CR/Drone link paste.
- Inline CR/Drone state dropdown.
- Row action menu.
- Refresh scan/rebuild cache.
- Empty-area click clears selection.

### 6. Settings

Audit/fix toward PRD §17 and `redesign_ui/settings_redesign.py`.

Must include:

- 50/50 settings/help layout.
- Resizable splitter if feasible.
- General/Behavior/Paths cards.
- Browse buttons.
- Save with validation.
- Restart-required warning when relevant.
- Help Center search/topic docs.

## Backend/domain constraints

- Filesystem + `project_data.json` canonical.
- `project_state` must never be stored in `project_data.json`.
- SQLite is rebuildable cache only.
- Delete uses Recycle Bin via `send2trash`; no hard delete.
- Windows imports lazy + guarded with `sys.platform == "win32"`.
- Outlook COM runs on background thread with `pythoncom.CoInitialize()`/`CoUninitialize()` inside that thread.
- pywebview start runs on main thread.
- Use `pathlib.Path`, no string path concatenation.
- Keep Windows paths as Windows paths in settings; do not normalize to Linux paths.

## Verification commands

Use `rtk` prefix for shell commands.

Linux-safe checks:

```bash
rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/ -q
rtk npm --prefix frontend run build
rtk npm --prefix frontend run test
rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m py_compile project_tracker/app_web.py project_tracker/web/js_api.py
```

If frontend config/API docs are needed, use Context7 before changing Svelte/Vite/Tailwind config or version-sensitive usage.

Windows-only checks must be prepared but not falsely claimed on Linux:

- pywebview/WebView2 launch
- Outlook COM draft/send
- Teams deep link + paste + optional auto-send
- `send2trash`
- `os.startfile`
- PyInstaller build
- clean Windows launch from extracted zip

## Packaging target

Before final zip:

1. Reconcile `PROJECT_STATUS.md` vs `docs/packaging-readiness.md` about `.spec` existence.
2. Ensure Vite build output `web/static/` exists and is included.
3. Ensure `assets/` included.
4. Ensure legacy/reference PyQt not bundled unless explicitly needed as docs/reference.
5. Build only on Windows.
6. Test extracted app on Windows path with spaces, non-admin user, disposable root folder.
7. Include README, known limitations, verification log.

Never claim “Windows release ready” until Windows manual checklist is actually run.

## Output discipline

For every work slice, report:

- files changed
- PRD/prototype sections used
- decisions made when PRD/prototype/code conflicted
- tests/build commands run
- what was not tested
- remaining risk
- next slice

## Decision authority

If requirements are incomplete, decide the best flow based on:

1. deployment/support engineer daily work speed
2. fewer clicks
3. explicit safety for destructive/automation actions
4. local-first recoverability
5. PRD compliance
6. PyQt prototype UX intent

Ask user only when decision changes product scope, dependency set, destructive behavior, or Windows-only action. Otherwise choose best path and proceed.
