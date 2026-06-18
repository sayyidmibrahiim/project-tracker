# Project Status

## Current Phase

**Linux-green PRD-completion increment complete; Windows manual packaging/verification gate remains.**

Current branch: `prd-v31-migration`.

`PRD.md` v3.1 remains the product and architecture source of truth. The current codebase has a mature backend/domain/bridge/Svelte implementation and Linux-automated verification has passed for the PRD-completion increment. The app is **not yet final Windows-release verified** because real Windows-only runtime behavior still requires manual testing on Windows 10/11.

Project Details prototype-parity pivot (2026-06-18): user overrode the prior Notion-style direction for menu/page layout and requested `redesign_ui/*.py` parity. `ProjectDetails.svelte` now follows `redesign_ui/project_details_redesign.py` more closely: Project Command Center contains Project/Sub Project selectors plus Open/Delete only; body remains 50/50 with Project Identity, Schedule, Sub Projects on the left and Files, Notes, Activity History on the right; extra in-page Folder Transitions and Project Actions panels were removed from this page; Add Sub Project is surfaced inside the Sub Projects panel using the existing `subproject_create` bridge. Phase 4 datetime + implementation_plan editor remains wired through `project_update`. Gates: `npm --prefix frontend run check` clean, `npm --prefix frontend test` 101 passed, `npm --prefix frontend run build` clean. Runtime/manual WebView2 verification still pending below.

Dashboard inline-edit + Project Details UX repair (2026-06-18): fixed the transient `BRIDGE_UNAVAILABLE` startup race by adding `waitForPywebviewReady()` in the frontend bridge and using it before first Dashboard/Project Details loads. Dashboard now exposes inline `datetime-local` Start/End editors backed by existing `project_update`, and aligns subproject rows with drone rows so a subproject without a drone ticket still shows a paste target; placeholder drone rows call `drone_add`, existing rows call `drone_update`, and state dropdowns activate after ticket creation. Cache/service DTOs now carry `subprojects_json`/`DashboardProject.subprojects` from filesystem scanning so SQLite remains rebuildable cache only. Project Details now has a workflow strip, selected-subproject drone ticket editor, clearer `Save identity + schedule`, and a separate Implementation Plan section. Gates: `npm --prefix frontend run check` clean, `npm --prefix frontend test` 107 passed, `npm --prefix frontend run build` clean, targeted cache/dashboard pytest 33 passed. Runtime/manual WebView2 verification still pending below.

Slice 0 truth reset: documentation alignment completed on 2026-06-08; production code unchanged.

Dashboard menu completion (2026-06-09, PRD §11, plan in docs/dashboard-fix-plan.md,
audit in docs/dashboard-parity-matrix.md): closed the A–F audit findings T1–T17.
Backend: `DashboardProject` now carries `drone_tickets` (parsed from cached
drone_tickets_json — no extra query) and a new guarded `year_create` bridge
creates `{root}/{year}/` + the five Folder_State folders. Frontend: Dashboard
rebuilt on `dashboard_data` (real filter-tab counts incl. Canceled), real
sub-project/drone columns, inline CR/Drone link paste and state dropdowns (guarded,
IN-PROGRESS disabled, POSTPONED/CANCELED confirm), `DashboardRowMenu` (Project
Details navigation, Open Folder, Delete with confirm+lock, embedded transitions),
clickable name/sub-folder + link-open; header now has a live DateTime clock, year
dropdown from `year_list`, working Add Project → NEW_PROJECT, Add Year (+) dialog,
debounced search (200ms) with name highlight, fixed Refresh (was a no-op; now a
tracked `refreshToken` + 650ms spin); First-Run Setup overlay when `root_folder`
is unset; event poll aligned to 1.5s; table polish (sticky header, row hover,
skeleton, empty-state CTA). Documented deviation: inline CR/Drone state changes
update state only (independence model from product-context), not auto folder move;
folder moves stay in the row menu. Windows-only at runtime: Open Folder, link-open,
native folder picker (manual-path fallback). Linux gates green: svelte-check 0/0,
vite build clean, frontend node tests 87 passed, pytest 1700 passed, py_compile
clean.

Dashboard auto-move + gap-closure increment (2026-06-10, PRD §11.10/§11.11,
spec in docs/superpowers/specs/2026-06-10-dashboard-auto-move-design.md, plan in
docs/superpowers/plans/2026-06-10-dashboard-auto-move.md). **Supersedes the
prior "metadata-only, no auto-move" deviation noted above.** Inline CR/Drone
state changes now drive real folder transitions:

- Pure `resolve_auto_move(cr_state, drone_states, current_folder)` in
  `core/state_machine.py` decides the target Folder_State (no-op on
  target==current, terminal IMPLEMENTED, or illegal transition); orchestration
  lives in the `_apply_auto_move` adapter helper in `app_web.py`, which routes to
  the existing tested `ProjectService` move methods, rebuilds the cache, pushes
  an `AUTO_MOVE` EventQueue event (R3, picked up by the 1.5s poll), and emits a
  notification. On a blocked structural guard it returns a non-blocking banner;
  the state change still persists.
- **T-10 reclassified** from a hard prod-ready guard to a non-blocking **H-10
  reminder**: `compute_h10`/`h10_reminder_due` in `core/rules.py`,
  `h10_reminder_days` setting (default 10) + `h10_notified_at` dedup stamp on
  `ProjectMetadata`. Evaluated best-effort on dashboard load (`_evaluate_h10_reminders`,
  isolated so a reminder write can never blank the dashboard), fires once, re-arms
  when the condition resolves. The old T-10 block was removed from
  `validate_uat_to_prod_ready_transition` (structural guards remain).
- **G1 guard**: CR cannot become APPROVED while any drone is not APPROVED
  (`validate_cr_approved_requires_drones`), enforced in `update_cr_state`; makes
  the PROD_READY auto-move deterministic. **R4**: CR→FINISHED cascade to
  IMPLEMENTED is blocked (with a surfaced reason) when any drone has no legal path
  to FINISHED (`drones_blocking_finish`), instead of silently skipping.
- History entries now appended on inline CR state, drone state, and CR link
  changes (previously missing).
- Frontend (`Dashboard.svelte`): A4 extracted CR/drone identifiers beside link
  cells, C2 semantic state colour chips, C4 per-cell saving spinner, B4 long-name
  ellipsis+tooltip, B3 Add-Year empty-state (prop wiring pending — see follow-up).
  G1 rejection surfaces via the existing actionError banner.
- Known deferred (tracked follow-ups, not blockers): dead `override_t10`/`emit_t10`
  plumbing in `project_service.py`/`app_web.py` (unreachable after T-10 removal)
  to be removed; `onAddYear` not yet wired from `App.svelte` to `<Dashboard>` (B3
  button inert until then; signature needs an adapter wrapper).
- Linux gates green: svelte-check 0/0, vite build clean, frontend node tests 92
  passed, pytest 1744 passed, py_compile clean. Windows manual gate (real
  `shutil.move`, `os.startfile`, WebView2 render, visual chips/spinner) still
  required — user will verify on the Windows office laptop.

Dashboard + Project Details Notion redesign + ⋮-trim + reopen-via-dropdown
(2026-06-11, plan in ~/.claude/plans/curious-petting-donut.md). User-directed
simplification of the per-row action surface plus a full Notion-like visual pass
on both screens. **PRD conflict flagged and superseded by user instruction:** PRD
§11.13 lists Move/Postpone/Cancel/Reopen in the ⋮ menu; the user removed them
because folder transitions are already driven by the CR/Drone dropdowns + the
auto-move engine. Proceeding per user instruction, not §11.13.

- **Reopen via CR dropdown** (`Dashboard.svelte`): REOPEN is an action, not a CR
  state (PRD §9.1; `validate_cr_transition` rejects it as a target). The CR
  dropdown now offers a `REOPEN` option **only** when `cr_state` is POSTPONED or
  CANCELED (`crOptionsFor` + `REOPENABLE` set). Selecting it routes to the
  existing `folder_reopen` bridge (NOT `cr_update_state`) behind the ConfirmModal
  ("Reopen project?", reversible). Backend unchanged — `folder_reopen` →
  `reopen_project` → `_run_transition` already validates POSTPONED/CANCELED-only
  (`REOPEN_ALLOWED_FOLDER_STATES`), moves the folder to UAT_PREPARE, sets
  CR→PENDING SUBMISSION, writes history, and rebuilds the cache; the frontend
  `loadDashboard()` reflects the move. New tests: `frontend/tests/dashboard-reopen.test.mjs`.
- **⋮ menu trimmed** (`DashboardRowMenu.svelte`): now **Project Details + Delete**
  only. Removed the embedded `ProjectTransitions` block + import and the "Open
  Project Folder" item/handler (the project-name click already opens the folder).
  `ProjectTransitions.svelte` is retained — still used by Project Details (inline
  variant) for manual moves. `components.test.mjs` updated with a source-structure
  assertion that the menu carries only Details + Delete.
- **Notion-like redesign** (`styles.css` tokens + `Dashboard.svelte` and
  `ProjectDetails.svelte` style blocks): near-white paper workspace, white cards,
  hairline borders (`--color-hairline`), soft `--shadow-card`, sticky quiet table
  header, row hover tint, borderless-until-hover inline cells, and Notion-style
  soft-tag state chips (tinted bg + readable ink via `--tag-*` tokens) replacing
  the bold filled blocks. DBS red retained as accent (header band, active filter
  tab, selected-row left marker, primary buttons).
- **Display font bundled locally** (no CDN): Fira Sans (SIL OFL) Regular/SemiBold/
  Bold converted to woff2 and vendored at `frontend/src/assets/fonts/`, wired via
  `@font-face` + `--font-display`, applied to page title and section headers.
- Linux gates green: svelte-check 0/0, vite build clean (fonts emitted), frontend
  node tests 99 passed, targeted pytest 71 passed (backend untouched). Windows
  manual gate (real folder move on reopen, WebView2 font render, visual aesthetic)
  still required.

Sidebar + Header Notion refine (2026-06-11, follow-up to the redesign above).
Extends the Notion language to the two cross-screen chrome elements, per user
direction ("layout/position juga, bukan cuma warna"). Decisions: **dark sidebar
retained** (brand rail, pairs with red header) but refined; **red header band
retained** (brand accent) but flattened.

- Header (`styles.css` `.app-header` + controls, `Header.svelte` add-year popover):
  flat red band (1px border, light `--shadow-header`, no heavy drop shadow),
  translucent-white pill controls (year/search/filter/refresh) on the band, white
  primary "Add Project" button (red ink), 28px control rhythm, datetime as a
  translucent pill, Fira Sans title. Add-year popover restyled to a light paper
  card with `--shadow-panel`.
- Sidebar (`styles.css` `.sidebar` + nav + notif): widened to 224px, Notion-style
  rounded full-pill nav (removed the left-border-bar active style; active = soft
  red-tinted pill, hover = faint white), Fira Sans brand with a larger rounded
  brand chip, refined dark notification panel (subtle translucent surface + cards,
  dropped the bright `--shadow-notif`), lighter muted palette.
- Gates: svelte-check 0/0, vite build clean, frontend node tests 99 passed, graph
  refreshed. Windows manual gate (WebView2 render of the new chrome) still required.

Automations parity slice (from `master-prompt.md`, 2026-06-09): added
`docs/automations-parity-matrix.md` (PRD §16 vs PyQt prototype vs current Svelte
audit) and implemented the smallest high-value gap from it. The Automations tab
order/default now follows PRD §16.2 (Outlook, Teams, Scheduler, Rules Engine;
default Outlook), replacing the prior Rules-first order. A new
`AutomationsOutlook.svelte` provides the PRD §16.3 two-column SEND/DOWNLOAD
workspace: the five-tile KPI row (Send Categories, Download Jobs, HTML Templates,
On Going ACK, On Going Tech LV), the four send categories (ACK_UAT, ACK_SOP,
APRVL_CR, APRVL_SOP), download jobs, per-column logs, and draft-first safety copy.
The `Downloaded Emails` action calls the real `outlook_download_emails` bridge
method (guarded; browser preview is read-only — no API contract invented). The
full Email Template Dialog and the searchable Downloaded Emails dialog remain
explicit next-slice gates, surfaced in-UI with honest deferral reasons rather than
hidden as done; real Outlook COM stays Windows-only and manual. Test note: the new
SSR regression tests use a direct loader-backed `import` + `svelte/server` render
(not the temp-dir `renderComponent` helper, which cannot resolve a parent
component's child `.svelte`/`.ts` imports).

Automations Email Template Dialog slice (2026-06-09, follow-up): added
`EmailTemplateDialog.svelte` implementing PRD §16.3 — a two-column modal (template
fields + 11 placeholder chips that insert at the caret on the left; conditions
grid, live condition preview, and a deferred per-category log on the right). It
loads via `settings_get` and saves via `settings_update` using a full-object
round-trip that mutates only `email.categories[code]`, so no new bridge contract
is introduced and no other settings are touched. Condition operators are limited to
those the backend `EmailService` actually evaluates
(`equals/not_equals/contains/exists`). Draft-first is preserved: per-category mode
defaults to the global Draft default and "Send Immediately" is an explicit opt-in
that still requires Windows Outlook COM + confirmation to send. The Outlook tab's
Edit Template buttons now open the dialog; "+ Add Category" is an honest deferral
(the four categories are fixed by the settings model). Backend untouched. Modal
a11y verified (svelte-check returned to 0 errors/0 warnings after switching to a
focusable dialog + dedicated close button). Deferred next: searchable Downloaded
Emails dialog, per-category send log, Teams Automation Dialog + countdown,
Scheduler KPI row.

Automations Scheduler delete-confirmation slice (2026-06-09, follow-up): PRD §16.5
requires "Delete → confirmation → remove", but the Scheduler Delete button
deleted immediately. Routed scheduler entry delete through the existing
`ConfirmModal` (irreversible), mirroring the trigger-confirmation pattern:
`requestDelete` only arms `pendingDeleteEntry` (no bridge call), `confirmDelete`
holds the single `scheduler_entry_delete` bridge call, and `cancelDelete` resets
state. Added `frontend/tests/scheduler-actions.test.mjs` (SSR bridge-spy + source
gating assertions). Backend untouched. Audit finding recorded: the PRD Scheduler
KPI row stays deferred because "Due Soon"/"Overdue" need a next-run timestamp that
the scheduler entry payload does not serialize to the frontend (only
`status` = active/paused/completed is available); adding it would be a separate
backend/bridge slice. Linux gates green: svelte-check 0/0, vite build clean,
frontend node tests 72 passed, pytest 1696 passed, py_compile clean.

Project Details Notes editor slice (2026-06-09, PRD §12.12): added
`docs/project-details-parity-matrix.md` (PRD §12 audit) and implemented its
highest-value gap. The Notes section was a plain textarea + explicit "Save Notes"
button; it is now `NotesEditor.svelte` with 1000ms debounced autosave
(flush-on-blur; Editing…/Saving…/Saved/offline/error status), a markdown toolbar
that inserts syntax at the caret (Bold/Italic/H1/H2/Code/List/Quote/Link), and an
Edit/Preview toggle. Preview uses a new dependency-free, XSS-safe Markdown subset
renderer, `frontend/src/lib/markdown.ts` (PRD names marked.js, but the release
rules forbid adding dependencies — input is HTML-escaped first and link hrefs are
restricted to http/https/mailto). `NotesEditor` is keyed by project path so it
remounts per project and owns its buffer; it seeds from `initialNotes` via
`untrack`. Tests added: `frontend/tests/markdown.test.ts` (renderer + XSS/href
sanitization) and a NotesEditor SSR test. Documented deviations: explicit Save
replaced by autosave per §12.12, and a local renderer instead of marked.js.
Conflict reported (not changed): `folderLocks.notes_edit` marks notes view-only in
IMPLEMENTED, but PRD §12.11 keeps notes editable while files lock; existing
always-editable behavior was preserved and the discrepancy is flagged for a
dedicated slice. Deferred next for Project Details: NEW_PROJECT create-form mode,
sub-project table, Activity History panel (needs a serialized history field), and
the two-column Command Center layout. Backend untouched. Linux gates green:
svelte-check 0/0, vite build clean, frontend node tests 81 passed, pytest 1696
passed, py_compile clean.

Project Details NEW_PROJECT mode slice (2026-06-09, PRD §12.4): added
`NewProjectForm.svelte` and a "+ Add Project" toolbar button that toggles
ProjectDetails into a create form. The form collects Project Name (realtime
validation via `util_validate_windows_folder_name`; Save disabled while empty or
invalid) and Year (dropdown, defaulting from the current filter), calls
`project_create`, then navigates to SHOW_EDIT for the new project. Documented
deviation: `project_create` accepts only `project_name` + `year`, so the optional
CR link / first drone / implementation plan from PRD §12.4 are entered on the
detail screen the user lands on (all already editable there); Start/End schedule
has no editor anywhere yet (pre-existing gap, tracked in the parity matrix). The
form remounts per new-mode entry and seeds Year via `untrack`. Added a
NewProjectForm SSR test. Backend untouched. Linux gates green: svelte-check 0/0,
vite build clean, frontend node tests 82 passed, pytest 1696 passed, py_compile
clean.

Project Details Command Center + Sub Project table slice (2026-06-09, PRD
§12.5/§12.10): restructured the detail panel into the PRD two-column Command
Center — a header bar plus a two-column body (left: Project Identity, Folder
Transitions, Edit Metadata, Drone Tickets, Sub Projects, Project Actions; right:
Files, Notes, Activity History, Outlook). Added `SubProjectTable.svelte`
implementing the §12.10 table (Sub Project | Drone Ticket | Drone State | Owner |
Actions) that maps each sub-project to its drone ticket via `subfolder_name` and
offers Open Folder through the existing `folder_open` bridge; sub-project
create/delete remain in the tested ProjectActions and drone-state editing in the
Drone Tickets card (no duplicated destructive flows, no new bridge contract).
Activity History is an honest deferred placeholder card (the `project_get` payload
has no history field yet). Minor deviation: Start/End remain inside the Identity
card (no separate Schedule card; no Start/End editor exists anywhere yet). Added
two SubProjectTable SSR tests. Built with Context7-confirmed Svelte 5 runes
patterns (keyed each, `$derived` mapping, typed `$props`). Backend untouched.
Linux gates green: svelte-check 0/0, vite build clean, frontend node tests 84
passed, pytest 1696 passed, py_compile clean.

Packaging-readiness reconciliation (2026-06-09): `docs/packaging-readiness.md`
previously claimed no PyInstaller `.spec` existed and listed it as blocker #1. That
was stale. Corrected to reflect reality: `project_tracker_dbs.spec` (repo root,
`sys.platform != "win32"` refuse guard, bundles `web/static/` + `assets/`, excludes
`PyQt6`) and `scripts/package.py` (Windows-only refuse guard, lazy PyInstaller
import) both exist. They remain UNEXECUTED on Windows, so packaging stays
Windows-gated and no Windows-release claim is made.

Linux verification for this slice: svelte-check 0 errors/0 warnings; vite build
clean; frontend node tests 66 passed (incl. 2 new Automations tests); pytest 1696
passed; `py_compile` clean for `project_tracker/app_web.py` and
`project_tracker/web/js_api.py`. Backend was not modified (frontend + docs only).

## 2026-06-17 — Cleanup MVP-1 Phase 0

Status: in progress

Baseline:

- Backend tests: PASS — `1724 passed, 20 skipped in 108.00s`.
- Frontend build: PASS — `npm --prefix frontend run build` completed, Vite built in 4.35s.
- Working tree: existing frontend changes preserved; generated probe/log files removed; root `project_data.json` inspected and ignored pending user decision.
- Graphify orientation: ran `graphify query "working tree hygiene project_data root junk artifacts"`; output skewed by minified Tailwind god-node, so exact status/file inspection used for Phase 0.

Next:

- Phase 1 crash bugs.

## 2026-06-18 — Cleanup MVP-1 Phase 1 crash bugs

Status: completed / verified on Windows dev machine.

- P0-7: `project_open_folder` and `subproject_create` are wired through `create_js_api()` and covered by regression tests.
- P0-5: `_create_scheduler_safe()` deduped to a single definition.
- P0-6: SQLAlchemy finding verified stale; no `SQLAlchemyJobStore` / `apscheduler.jobstores.sqlalchemy` import remains; no dependency added.
- P0-8: PyInstaller spec includes lazy Windows hidden imports (`pythoncom`, `win32com.client`, `pyperclip`, `pyautogui`) and disables UPX.
- Static-serving preflight fix: pywebview serves built Svelte `web/static/index.html` via absolute path; `/index.html` returns 200 in live HTTP probe.

Verification:

- `npm --prefix frontend run build` — PASS.
- `npm --prefix frontend run check` — PASS (`110 FILES 0 ERRORS 0 WARNINGS`).
- `.\.venv\Scripts\python.exe -m py_compile project_tracker\app_web.py project_tracker\web\js_api.py` — PASS.
- `.\.venv\Scripts\python.exe -m pytest tests/test_phase_d_app_web_project_details_read_wiring.py::test_project_open_folder_wired_and_returns_ok tests/test_phase_d_app_web_project_details_read_wiring.py::test_subproject_create_wired_and_creates_folder -q` — PASS (`2 passed`).
- `.\.venv\Scripts\python.exe -m pytest tests/test_scheduler_entries_unit.py -q` — PASS (`12 passed`).
- `.\.venv\Scripts\python.exe -m pytest tests/test_phase_d_app_web_svelte_static_serving.py -q` — PASS (`6 passed`).
- `.\.venv\Scripts\python.exe -m pytest tests/ -q` — PASS (`1725 passed, 20 skipped`).
- `.\.venv\Scripts\python.exe -m project_tracker.main` live HTTP probe — PASS (`/index.html` 200, built app HTML present, JS asset 200).

Next: Phase 2 dependency & entry-point reconciliation.

## 2026-06-18 — Cleanup MVP-1 Phase 2 dependency + entry-point reconciliation

Status: completed / verified on Windows dev machine.

- P0-1: `pyproject.toml` dependency drift resolved. It now matches
  `requirements.txt` for approved runtime dependency names: `pywebview`,
  `pywin32`, `pyinstaller`, `pyautogui`, `pyperclip`, `send2trash`, `watchdog`,
  `python-dateutil`, and `APScheduler`.
- Legacy `PyQt6` removed from production dependency metadata; PyQt6 remains
  reference-only under `redesign_ui/` and is excluded from PyInstaller.
- Minimal PEP 517 build metadata added to `pyproject.toml`.
- P0-4: canonical app entry point reaffirmed as
  `.\.venv\Scripts\python.exe -m project_tracker.main`, which calls
  `project_tracker.app_web.run()`. PyInstaller continues to use
  `project_tracker/main.py` as `ENTRY_SCRIPT`.
- PRD conflict noted: PRD §3.2 still shows root `app_web.py` examples; current
  Windows setup, package spec, and runtime code use `project_tracker.main`. PRD
  source edits are deferred unless explicitly approved.
- Added regression guard:
  `tests/test_phase_2_dependency_entrypoint_reconciliation.py`.

Verification:

- `npm --prefix frontend run build` — PASS (`vite build` completed in 3.16s).
- `npm --prefix frontend run check` — PASS (`110 FILES 0 ERRORS 0 WARNINGS`).
- `.\.venv\Scripts\python.exe -m py_compile project_tracker\app_web.py project_tracker\web\js_api.py project_tracker\main.py scripts\package.py` — PASS.
- `.\.venv\Scripts\python.exe -m pytest tests\test_phase_2_dependency_entrypoint_reconciliation.py -q` — PASS (`6 passed`).
- `.\.venv\Scripts\python.exe -m pytest tests\ -q` — PASS (`1731 passed, 20 skipped`).
- `.\.venv\Scripts\python.exe -m project_tracker.main` live HTTP probe — PASS (`/index.html` 200, JS asset 200).

Next: Phase 3 per cleanup/audit queue.

## 2026-06-18 — Cleanup MVP-1 Phase 3 atomic notes write

Status: completed / verified on Windows dev machine.

- P2-25: `_NotesServiceAdapter.update_notes()` now writes `notes.md` via a
  sibling temp file and atomic replace instead of direct `Path.write_text()`.
- Existing `IMPLEMENTED` view-only lock behavior is unchanged.
- Added regression coverage proving a failed temp-file write preserves existing
  `notes.md` content and leaves no `.notes.md.tmp` file behind.
- No note editor UI, bridge signature, metadata JSON, packaging, or storage
  migration changes were made.

Verification:

- `.\.venv\Scripts\python.exe -m pytest tests\test_phase_e_notes_persistence.py -q` — PASS (`9 passed`).
- `.\.venv\Scripts\python.exe -m py_compile project_tracker\app_web.py` — PASS.
- `.\.venv\Scripts\python.exe -m pytest tests\ -q` — PASS (`1732 passed, 20 skipped`).
- `npm --prefix frontend run build` — PASS (`vite build` completed in 3.35s).
- `npm --prefix frontend run check` — PASS (`110 FILES 0 ERRORS 0 WARNINGS`).
- `.\.venv\Scripts\python.exe -m project_tracker.main` live HTTP probe — PASS (`/index.html` 200, JS asset 200).
- `graphify update .` — PASS (`graph.json` and `GRAPH_REPORT.md` updated; HTML skipped because graph has 5462 nodes > 5000 limit).

Next: Phase 4 cleanup queue.

## 2026-06-18 — Cleanup MVP-1 Phase 4 Project Details datetime + plan editor

Status: completed / automated verification green on Windows dev machine; live manual UI check pending.

- P1-6: Project Details metadata editor now includes `datetime-local` controls for `start_datetime` and `end_datetime`.
- P1-12: `implementation_plan` remains editable in the same metadata editor and is saved with the datetime fields through `project_update`.
- `project_get` now returns `implementation_plan` and serialized `history`, allowing the Activity History card to render real history rows instead of the stale deferred placeholder.
- Datetime draft conversion preserves local wall-clock input and sends timezone-aware ISO strings with the OS local offset.
- Added regression coverage for `project_update` persistence of start/end datetime + implementation plan, plus a frontend source guard for the Project Details editor wiring.

Verification:

- `.\.venv\Scripts\python.exe -m pytest tests\test_phase_g_project_create_update.py::test_project_update_persists_start_end_datetime_and_plan -q` — RED first (`KeyError: 'implementation_plan'`), then PASS (`1 passed`).
- `npm --prefix frontend test -- --test-name-pattern "ProjectDetails source includes datetime-local"` — RED first, then PASS (`100 passed`).
- `.\.venv\Scripts\python.exe -m pytest tests\test_phase_g_project_create_update.py tests\test_phase_d_app_web_project_details_read_wiring.py -q` — PASS (`32 passed`).
- `.\.venv\Scripts\python.exe -m py_compile project_tracker\app_web.py` — PASS.
- `npm --prefix frontend run check` — PASS (`110 FILES 0 ERRORS 0 WARNINGS`).
- `npm --prefix frontend run build` — PASS (`vite build` completed in 5.89s).
- `npm --prefix frontend test` — PASS (`100 passed`).
- `.\.venv\Scripts\python.exe -m pytest tests\ -q` — PASS (`1733 passed, 20 skipped`).

Next: run live app monitor + manual Phase 4 checklist, then Phase 5 dead-code purge queue.

## Source of Truth

`PRD.md` v3.1 is authoritative. If code, old docs, comments, folder structure, or PyQt6 prototype behavior conflicts with `PRD.md`, report the conflict before implementation.

PyQt6 files in `redesign_ui/` are UX/reference only. They must not be imported into production code or used as production UI. PyQt6 redesign_ui may inform UX, but can be overruled when `PRD.md` v3.1 or approved userflow provides a better direction.

## Current Repo Reality Summary

Implemented and Linux-verified:

- Core domain: states, transition guards, T-10 rules, folder-name validation, link extraction, metadata serialization rules.
- Infrastructure: filesystem safety helpers, atomic JSON metadata/settings/link-bank stores, SQLite rebuildable cache/index, guarded Windows integration stubs.
- Services: project/scanner/dashboard/notification/scheduler/report/second-brain/automation/email/Teams services.
- Bridge: `project_tracker/web/js_api.py` standard BridgeResponse shape and frontend contract guard.
- Frontend: Svelte + TypeScript + Vite + Tailwind app shell and all six PRD pages.
- Main userflows: dashboard, project details, project create/update/rename/delete, CR/Drone metadata and guarded state updates, folder transitions, file actions, Second Brain CRUD/pin/favorite, Link Bank CRUD/archive, report export, scheduler/rules UI, Teams guarded preview/send surface.
- Packaging prep: PyInstaller spec/docs exist for Windows-only execution; `web/static/` build output is generated by Vite.

Known remaining gates:

- Windows manual verification is still required for WebView2/pywebview, Outlook COM, Teams `pyautogui`, `os.startfile`, `send2trash`, and PyInstaller output.
- Final Windows zip must not be claimed complete until `docs/windows-manual-test-checklist.md` and `docs/packaging-readiness.md` are executed on a disposable Windows test root.
- Linux cannot verify real Outlook COM, Teams desktop automation, Windows Explorer file open, or PyInstaller runtime behavior.

## Latest Verified Evidence

```text
Branch: prd-v31-migration
Linux automated status: green at latest recorded PRD-completion exit audit
svelte-check: 0 errors, 0 warnings
vite build: clean, outputs to web/static/
pytest: 1696 passed
py_compile: pass (project_tracker/app_web.py, project_tracker/web/js_api.py)
Latest recorded verification commit: 0dd3735 test: bridge contract guard + P7 Bridge_Response shape
```

## PRD Area Acceptance Matrix

| PRD Area             | Current Status                 | Evidence / Notes                                                                    | Remaining Gate                                |
| -------------------- | ------------------------------ | ----------------------------------------------------------------------------------- | --------------------------------------------- |
| Core data + metadata | Linux-verified                 | `project_state` excluded from metadata; atomic JSON tests; datetime tests           | Windows path/manual workspace smoke           |
| State machine + T-10 | Linux-verified                 | Core/service/property tests cover guarded transitions and T-10 override paths       | Manual UI flow smoke on Windows               |
| Filesystem safety    | Linux-verified                 | `assert_within`, temp root, safe delete route tests                                 | Real `send2trash` + `os.startfile` on Windows |
| SQLite cache/index   | Linux-verified                 | Cache rebuild/schema tests; notifications/logs tables                               | Delete cache + relaunch on Windows            |
| Bridge contract      | Linux-verified                 | `test_bridge_contract_guard.py` maps frontend `callBridge` names to `JsApi` methods | pywebview live call smoke on Windows          |
| Svelte UI shell      | Linux-verified                 | Vite build + Svelte checks; all six pages present                                   | Visual smoke in WebView2                      |
| Dashboard            | Linux-verified safe slice      | Real backend/cache data, filters/search/actions wired                               | Windows app manual flow                       |
| Project Details      | Linux-verified safe slice      | Metadata, CR/Drone, transitions, files, notes, project actions wired                | Windows file/open/delete smoke                |
| Second Brain         | Linux-verified                 | Filesystem provider, CRUD, pin/favorite sidecar                                     | Manual persistence/reload on Windows          |
| Link Bank            | Linux-verified                 | Stable ID CRUD/archive; `link_bank.json` persistence                                | Manual import/export if used                  |
| Report               | Linux-verified                 | Filter/export service + frontend                                                    | Export CSV path dialog on Windows             |
| Automations          | Linux-verified guarded surface | Rules/scheduler/Teams/Outlook surfaces + tests                                      | Real Outlook/Teams manual tests               |
| Settings             | Linux-verified                 | Read/write binding and Windows-path preservation tests                              | AppData + path browser smoke on Windows       |
| Packaging            | Prepared, not Windows-verified | PyInstaller spec/docs exist; Linux build forbidden                                  | PyInstaller on Windows + clean machine launch |

> Historical note: sections below record status at their phase boundaries. Later PRD-completion slices implemented some deferred items; see Current Repo Reality Summary and PRD Area Acceptance Matrix above for latest truth.

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

| Commit    | Subject                                                                                                                                                                                     |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `75780e9` | update project status after rc hardening                                                                                                                                                    |
| `8cf64b6` | style: format markdown files with prettier                                                                                                                                                  |
| `572eb23` | add kiro steering for project tracker dbs (`.kiro/steering/*.md`)                                                                                                                           |
| `c74d47d` | improve windows manual test documentation (`docs/windows-manual-test-checklist.md`)                                                                                                         |
| `fa0b5f4` | document packaging readiness (`docs/packaging-readiness.md`)                                                                                                                                |
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

## PRD Completion Spec — In Progress (uncommitted, 2026-06-08)

Implementation against `.kiro/specs/prd-completion/` (Requirements / Design /
Tasks) is in progress on `prd-v31-migration`. All work below is **uncommitted**
in the working tree on top of `3cb5dac update release candidate documentation`.

The spec scope is the deferred high-risk and Windows-only work that the RC
intentionally left out: filesystem safety, folder transitions, project/file
mutations, persistent automation/notification logs, Second Brain CRUD,
guarded Outlook/Teams, scheduler control surface, rules engine execution, the
bridge-contract guard, and the Windows manual-test/packaging gate.

### Slice Status

| Spec Slice | Area                                                                                                                                                                 | Status  |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| 1.1–1.4    | Frontend safety foundation (`bridge.ts` timeout/malformed, `ConfirmModal`, `DisabledHint`, `folderLocks.ts`)                                                         | Done    |
| 3.1–3.8    | Filesystem safety (`assert_within`, atomic write preservation, `SafeDeleteService` route, P1–P4 + Windows-path test)                                                 | Done    |
| 5.1–5.6    | Folder state transitions (`_ProjectServiceAdapter` wiring, T-10 override `override_t10` keyword, rollback, P5, gated UI in Dashboard/ProjectDetails)                 | Done    |
| 7.1–7.5    | Project rename/delete + subproject delete (validator, `project_delete`, `subproject_delete` wiring, P6, gated UI)                                                    | Done    |
| 9.1–9.4    | File management (`file_create`, `file_create_from_template`, `file_rename`, `file_delete`, `_FileServiceAdapter`, gated UI)                                          | Done    |
| 11.1–11.4  | Persistent automation + notification logs (`notifications` and `automation_rule_logs` schemas wired to services)                                                     | Done    |
| 13.1–13.5  | Second Brain CRUD + persistent pin/favorite (sidecar `.project_tracker_index.json`, atomic note write, P9, frontend Notes CRUD)                                      | Done    |
| 15.1–15.3  | Outlook guarding + `EmailService` reuse + `outlook_*` JsApi methods (`outlook_draft_email`, `outlook_send_email`, `outlook_get_contacts`, `outlook_download_emails`) | Done    |
| 15.4       | Off-Windows guarding property test (P10)                                                                                                                             | Pending |
| 15.5, 15.7 | Outlook unit tests + frontend Outlook actions                                                                                                                        | Pending |
| 17.1       | Teams `teams_service.py` / `teams_client.py` preview/send + countdown + FAILSAFE                                                                                     | Done    |
| 17.2–17.4  | Teams JsApi methods + tests + frontend                                                                                                                               | Pending |
| 19.1       | Scheduler service entry CRUD + filters + 60-second auto-IN-PROGRESS preserved                                                                                        | Done    |
| 19.2–19.4  | Scheduler `scheduler_entry_*` JsApi methods + tests + frontend Scheduler tab                                                                                         | Pending |
| 21.1       | Rules engine execution (trigger → condition → action, halt-on-failure, log row)                                                                                      | Done    |
| 21.2–21.5  | Rules `rules_*` JsApi methods + tests (P8) + frontend Rules tab                                                                                                      | Pending |
| 23.1–23.3  | Bridge-contract guard (`callBridge` ↔ `create_js_api()` reconciliation + P7)                                                                                         | Pending |
| 25.1–25.2  | Manual-test docs refresh + `project_tracker_dbs.spec` PyInstaller spec with non-Windows refuse guard                                                                 | Done    |

### New Implementation Surface (uncommitted)

Backend:

- `infrastructure/filesystem.py` — `assert_within()` guard + file create/rename/delete helpers.
- `infrastructure/metadata_store.py` — atomic-write failure-preservation path.
- `infrastructure/cache_db.py` — `notifications` + `automation_rule_logs` schemas wired to services.
- `infrastructure/outlook_client.py` / `infrastructure/teams_client.py` — hardened guarding, COM thread `CoInitialize`/`CoUninitialize` pattern, lazy Windows-only imports.
- `services/project_service.py` — transition guards/rollback/T-10 override + rename/delete validation.
- `services/email_service.py`, `services/download_email_service.py` — placeholder/condition handling and attachment storage.
- `services/teams_service.py` — Preview-First default, countdown clamp, FAILSAFE abort.
- `services/scheduler_service.py` — entry CRUD, filter logic, in-app delivery, 60-second auto-IN-PROGRESS preserved.
- `services/automation_service.py` — execution engine + persistent rule logs.
- `services/notification_service.py` — persistence on create/dismiss + restore on startup.
- `services/second_brain_service.py` — sidecar pin/favorite store + note CRUD with atomic write.
- `web/js_api.py` — new methods: `project_delete`, `file_create`, `file_create_from_template`, `file_rename`, `file_delete`, `outlook_draft_email`, `outlook_send_email`, `outlook_get_contacts`, `outlook_download_emails`, `second_brain_note_create`, `second_brain_note_write`, `second_brain_note_delete`. Existing `folder_*`, `project_rename`, `subproject_delete`, `second_brain_pin`/`favorite` adapters wired to real services. Only proven-necessary signature change: `override_t10: bool = False` optional keyword on the relevant transition path (preserves all existing callers).
- `app_web.py` — `_ProjectServiceAdapter` transition + rename/delete hooks; new `_FileServiceAdapter`; new Outlook/Teams/Scheduler/Rules adapters; durable Second Brain store; cache-update on success; rollback on failure.

Frontend:

- `frontend/src/lib/bridge.ts` — 30-second timeout, malformed-response guard, stable error codes (`BRIDGE_TIMEOUT`, `BRIDGE_MALFORMED_RESPONSE`).
- `frontend/src/lib/folderLocks.ts` — Folder_State → disabled-action mapping (mirrors PRD §9.5; backend remains authoritative).
- New components: `ConfirmModal.svelte`, `DisabledHint.svelte`, `ProjectActions.svelte`, `ProjectTransitions.svelte`, `FileActions.svelte`, `OutlookActions.svelte`.
- `Dashboard.svelte` / `ProjectDetails.svelte` / `SecondBrain.svelte` — gated transitions, rename/delete, file CRUD, Notes CRUD, persistent pin/favorite.
- `frontend/tests/` — new component + `bridge.ts` unit tests (Node `--test` runner); 64 tests passing.

Tests added (Linux-runnable; destructive paths use `tmp_path` only):

- `tests/test_filesystem_assert_within.py`, `tests/test_filesystem_temp_root_property.py` (P1)
- `tests/test_metadata_store_atomic_write.py`, `tests/test_metadata_store_atomic_write_property.py` (P2)
- `tests/test_metadata_store_project_state_property.py` (P3)
- `tests/test_metadata_store_datetime_property.py` (P4)
- `tests/test_settings_windows_path_preservation.py`
- `tests/test_project_transitions_unit.py`, `tests/test_project_transitions_property.py` (P5)
- `tests/test_project_rename_delete.py`, `tests/test_name_validation_property.py` (P6)
- `tests/test_project_file_operations.py`
- `tests/test_persistence_logs_notifications.py`, `tests/test_phase_c_automation_service_persistence.py`
- `tests/test_second_brain_note_crud.py`, `tests/test_second_brain_pin_favorite_property.py` (P9)
- `tests/test_outlook_off_windows_property.py` (work-in-progress for P10)
- `tests/test_email_service_render.py`, `tests/test_download_email_attachments.py`, `tests/test_project_outlook_service_adapter.py`

Packaging artifact (Windows-manual only, not Linux-executable):

- `project_tracker_dbs.spec` — PyInstaller spec bundling `web/static/` + `assets/`, with platform-guard refusing to package off-Windows.

### Verification_Suite (current state, uncommitted)

```text
Branch: prd-v31-migration
Working tree: dirty (PRD-completion implementation in progress, not yet committed)
svelte-check: 0 errors, 0 warnings
vite build: clean, outputs to web/static/
Backend tests (pytest): 1664 passed (up from 453 RC baseline)
Frontend tests (node --test): 64 passed
py_compile: pass (app_web.py, js_api.py — Linux)
Latest committed commit: 3cb5dac update release candidate documentation
```

### Remaining Before PRD-Completion Exit

- Slices 15.4 / 15.5 / 15.7 — Outlook off-Windows property test (P10), Outlook unit tests, and frontend Outlook actions.
- Slices 17.2 / 17.3 / 17.4 — Teams `teams_preview_message` / `teams_send_message` JsApi methods, unit tests, and frontend Teams actions.
- Slices 19.2 / 19.3 / 19.4 — Scheduler `scheduler_entry_*` JsApi methods, unit tests, and frontend Scheduler tab bindings.
- Slices 21.2 / 21.3 / 21.4 / 21.5 — Rules `rules_*` JsApi methods, action-ordering property test (P8), unit tests, and frontend Rules CRUD/logs view.
- Slices 23.1 / 23.2 / 23.3 — `callBridge` ↔ `create_js_api()` reconciliation, contract guard test, and Bridge_Response shape property (P7).
- Commit each completed slice separately (per `release-candidate-rules.md`); the working tree currently bundles many slices together and must be sliced into per-slice commits before merge.
- Windows manual test gate + Windows packaging session remain deferred (Linux-unrunnable by design).

Linux-automated readiness for the PRD-completion increment is **green**. Windows-only runtime behavior (real Outlook COM, Teams `pyautogui` send, `os.startfile`, real PyInstaller packaging) is **not verified** — that remains gated by the manual Windows test plan in `docs/release-candidate-manual-test-plan.md` and `docs/windows-manual-test-checklist.md`.

## PRD Completion Final Exit Audit (2026-06-08)

All Linux-safe PRD-completion slices are implemented, verified, and committed
on `prd-v31-migration` (no force-push, no rebase). The remaining unchecked
items in `.kiro/specs/prd-completion/tasks.md` are intentional Windows-only
gates (slices 16/18/20/22/24/26 are checkpoint markers; slice 25 packaging is
a Windows-manual gate).

### Slices Completed in This Session

| Commit    | Subject                                                                       |
| --------- | ----------------------------------------------------------------------------- |
| `844e61a` | Teams preview/send unit tests (slice 17.3); mark 15.5/15.7/17.2 [x]           |
| `8758db4` | Teams frontend actions in Automations tab (slice 17.4)                        |
| `52bddce` | scheduler*entry*\* JsApi + adapter + unit tests (slices 19.2/19.3)            |
| `000d9ac` | Scheduler control surface + entry CRUD UI (slice 19.4)                        |
| `8c6d4a6` | rules\_\* JsApi methods + settings-backed adapter (slice 21.2)                |
| `551a18d` | Rules CRUD + execution + P8 ordering halt-on-failure tests (slices 21.3/21.4) |
| `c8b8f5b` | Rules CRUD + per-rule logs view (slice 21.5)                                  |
| `0dd3735` | Bridge contract guard + P7 Bridge_Response shape (slices 23.1/23.2/23.3)      |

### New Backend Surface (this session)

- `project_tracker/web/js_api.py`: `RulesServiceProtocol`, `rules_service` slot,
  `scheduler_entry_list`/`scheduler_entry_create`/`scheduler_entry_update`/
  `scheduler_entry_delete`/`scheduler_entry_toggle`, `rules_create`/
  `rules_update`/`rules_delete`/`rules_toggle`/`rules_get_logs`,
  `_scheduler_entry_payload` (attaches `requires_confirmation` flag for
  Outlook/Teams channels).
- `project_tracker/services/scheduler_service.py`: `_create_scheduler_safe()`
  classmethod tolerates a missing `apscheduler` on Linux; `start()` re-attempts
  creation and surfaces a clear error if a scheduler is required.
- `project_tracker/app_web.py`: `SchedulerService` wired into `create_js_api()`;
  `_RulesAdapter` (CRUD over `settings.automation.rules_engine["rules"]`,
  validates the eight supported action types, fetches filtered logs from the
  durable `automation_rule_logs` cache); `AutomationService` rebuilt with the
  shared `rules_provider` so evaluation and CRUD see one rule list.

### New Frontend Surface (this session)

- `frontend/src/lib/components/TeamsActions.svelte`: preview default;
  auto-send gated by `ConfirmModal` and only offered when
  `settings.teams.teams_auto_send === true`.
- `frontend/src/lib/components/SchedulerActions.svelte`: status pill +
  start/stop/run-once + entry table with create/edit/delete/toggle/trigger,
  Outlook/Teams entries gated by `ConfirmModal` via `requires_confirmation`.
- `frontend/src/lib/components/RulesActions.svelte`: full CRUD form, per-rule
  logs viewer, evaluate single + evaluate all, `ConfirmModal` gating any rule
  whose actions include `send_outlook_email` or `send_teams_message`.
- `frontend/src/lib/components/Automations.svelte`: rewritten as a clean tab
  dispatcher delegating to `RulesActions` / `TeamsActions` / `SchedulerActions`;
  Outlook tab now points to the project-scoped `OutlookActions` in
  `ProjectDetails`.

### New Tests (Linux-runnable)

- `tests/test_teams_service_unit.py` (10 tests): auto-send default,
  countdown clamp, FAILSAFE abort under simulated Windows, off-Windows
  dev-skip.
- `tests/test_scheduler_entries_unit.py` (12 tests): entry CRUD persistence,
  enable/disable, trigger filter match/no-match, 60-second auto-IN-PROGRESS
  preservation, JsApi `requires_confirmation` flag.
- `tests/test_rules_engine_unit.py` (7 tests): rules CRUD validation, log
  retrieval filtered by rule id, unmet-condition skip, dispatch of all eight
  supported action types, **P8 property test** (200 random orderings;
  halt-on-failure leaves `actions_executed = order[:fail_at]` and writes
  exactly one `automation_rule_logs` row).
- `tests/test_bridge_contract_guard.py` (3 tests): every frontend
  `callBridge(...)` literal maps to a real `JsApi` method on `create_js_api()`,
  `window.pywebview` only inside `bridge.ts` (comments stripped so doc
  reminders are not false positives), **P7 Bridge_Response shape property**
  via reflection.

### Final Verification (2026-06-08, Linux)

```text
Branch: prd-v31-migration
Working tree: clean before final-status update
svelte-check: 0 errors, 0 warnings
vite build: clean, outputs to web/static/
Tests (pytest): 1696 passed
py_compile: pass (project_tracker/app_web.py, project_tracker/web/js_api.py)
Latest commit: 0dd3735 test: bridge contract guard + P7 Bridge_Response shape
```

### Tasks Still Pending (Windows-Manual Only)

| Item                                                                                 | Reason                                          |
| ------------------------------------------------------------------------------------ | ----------------------------------------------- |
| `.kiro/specs/prd-completion/tasks.md` § 25.\* (manual test + packaging)              | Windows-manual gate; spec/docs already produced |
| `.kiro/specs/prd-completion/tasks.md` § 15/16/17/18/19/20/21/22/23/24/26 checkpoints | Markers only, no executable work                |
| Real Outlook COM, Teams `pyautogui` send, `os.startfile`, PyInstaller                | Windows-only runtime; deferred by design        |

Linux-automated readiness for the PRD-completion increment is **green**. The
manual Windows gate plan in `docs/release-candidate-manual-test-plan.md` and
the packaging readiness check in `docs/packaging-readiness.md` remain the only
pre-release work, executed on a Windows machine against a disposable test
root.
