# Release Candidate Manual Test Plan

## Scope

This checklist covers manual Windows validation and packaging work that cannot be fully verified on Linux.

> **Disposable test root only (Requirement 14.1).** The Windows manual test gate
> runs exclusively against a disposable test root and disposable project folders.
> It must never be pointed at real project folders. The gate must pass before any
> packaging step begins.

## Requirement traceability

This plan, together with `docs/windows-manual-test-checklist.md` and
`docs/packaging-readiness.md`, covers Requirement 14:

| Req  | What the gate verifies                                                                                                                   | Where                                               |
| ---- | ---------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| 14.1 | Gate runs only against a disposable test root, never real folders; must pass before packaging                                            | This doc (header) + checklist §1                    |
| 14.2 | WebView2 loads bundled Svelte from `web/static/` via pywebview HTTP server, not raw `file://`                                            | "WebView2 / startup" below + checklist §4           |
| 14.3 | Root paths saved via Settings reload as identical Windows path strings (no Linux normalization)                                          | "Windows-path preservation" + checklist §5 Settings |
| 14.4 | Six page checks load with no runtime or bridge errors                                                                                    | "Six page checks" + checklist §5                    |
| 14.5 | Each deferred high-risk action presents a confirmation step before execution and shows an accurate disabled-state message while deferred | "Deferred high-risk action checks" + checklist §7   |
| 14.6 | Any failed check blocks all packaging and identifies which check failed                                                                  | "Packaging gate rule" + packaging-readiness         |

## Linux automated baseline

Expected before Windows handoff:

```bash
rtk npm --prefix frontend run check
rtk npm --prefix frontend run build
rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/ -q
rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m py_compile project_tracker/app_web.py project_tracker/web/js_api.py
```

Expected current result:

```text
svelte-check: 90 files, 0 errors, 0 warnings
vite build: clean
pytest: 453 passed
py_compile: pass (app_web.py, js_api.py — Linux)
```

Baseline after RC hardening (commits above `bd13d4f`):

- RC.1: `poll_events` wired as JsApi instance method
- RC.2: SecondBrainItem type fixed, null-guard updated_at, stale deferred bar updated
- RC.3: non-functional header buttons disabled

## Windows startup smoke test

- [ ] Create or select a safe **disposable** test root folder.
- [ ] Launch the pywebview app on Windows.
- [ ] Confirm WebView2 window opens.
- [ ] Confirm Svelte UI loads from bundled `web/static/` output (Requirement 14.2).
- [ ] Confirm production loading uses the pywebview HTTP server, NOT raw `file://`.
- [ ] Confirm Settings page can save and reload root folder paths without Linux path normalization.

## Windows-path preservation (Requirement 14.3)

- [ ] In Settings, save a root path as a Windows path (e.g. `C:\Temp\ptdbs_test_root`).
- [ ] Reload Settings; confirm the path is the identical Windows string.
- [ ] Confirm no POSIX/Linux normalization (no `/` substitution, no stripped
      drive letter, no backslash collapsing).
- [ ] Repeat for Second Brain folder and any template paths.

## Six page checks (Requirement 14.4)

Each of the six pages must load without runtime or bridge errors. Use only a
disposable test root.

- [ ] **Dashboard** loads (CR summary table, year dropdown, status filters, search, refresh).
- [ ] **Project Details** loads (project list, detail, files, subprojects, notes).
- [ ] **Report** loads (filter by year/all; CSV export returns text, no external write).
- [ ] **Settings** loads (root path, Second Brain folder, template paths save/reload).
- [ ] **Second Brain** loads (discovered files list, search, hidden files excluded).
- [ ] **Automations** loads (rules tab, evaluate/evaluate-all preview only).

## Project Details manual checks

Use only a disposable test root with disposable project folders.

- [ ] Project list loads for configured year.
- [ ] Project Details loads selected project.
- [ ] Edit Metadata saves project name / implementation plan.
- [ ] Notes textarea reads/writes `notes.md`.
- [ ] CR Link Save persists metadata.
- [ ] Guarded CR State Save accepts valid transitions and rejects invalid transitions with visible error.
- [ ] Drone add/edit/delete persists metadata-only changes.
- [ ] Guarded Drone State Save accepts valid transitions and rejects invalid transitions with visible error.
- [ ] Rename/delete/folder transition controls remain deferred or disabled.

## Link Bank manual checks

- [ ] Legacy links without `id` load and receive stable IDs after write.
- [ ] Add Link validates name and URL.
- [ ] Edit Link saves by stable ID.
- [ ] Archive Link soft-archives only; no destructive delete.
- [ ] Show archived toggle works.

## Second Brain manual checks

- [ ] Configure a disposable Second Brain folder in Settings.
- [ ] Add `.md`, `.txt`, and another file type manually outside the app.
- [ ] Notes tab lists discovered files.
- [ ] Search finds title/excerpt matches.
- [ ] Hidden files are not shown.
- [ ] Pin/favorite/note write remain deferred until persistence is implemented.

## Automation manual checks

- [ ] Rules tab loads.
- [ ] Evaluate preview shows result badges.
- [ ] Evaluate All preview remains read-only.
- [ ] Outlook/Teams/Scheduler tabs do not execute external actions.
- [ ] Rule create/edit/delete remains deferred.

## Deferred high-risk action checks (Requirement 14.5)

Each deferred high-risk action must EITHER (a) present a confirmation step before
it executes, OR (b) remain deferred/disabled with an accurate disabled-state
message explaining why. None of these may execute against real folders — only a
disposable test root is permitted if a confirmed action is exercised.

High-risk actions in scope:

- [ ] **Folder transitions** (move/rename/delete/state transition): confirmation
      UI shown before execution; while deferred, control is disabled with an
      accurate message.
- [ ] **File open / write / delete** (external app, create, write, delete):
      confirmation before execution; while deferred, disabled with accurate
      message.
- [ ] **Outlook / Teams / COM** (draft/send/download, Teams/pyautogui):
      confirmation before execution; while deferred, disabled with accurate
      message and no external action fires.
- [ ] **Scheduler real controls** (start/stop/run-once): confirmation before
      execution; while deferred, disabled with accurate message and the scheduler
      does not actually start/stop.

## Packaging gate rule (Requirement 14.6)

- [ ] If ANY check above fails, packaging is BLOCKED. Do not proceed to any
      packaging step.
- [ ] Record which specific check failed in the observation log so the blocker is
      identifiable.
- [ ] Packaging may begin only after every check passes (see
      `docs/packaging-readiness.md`).

## Packaging checklist

Packaging must be done on Windows, not Linux, and only after every check above
passes (Requirement 14.6 — failure blocks packaging).

- [ ] Build frontend first: `rtk npm --prefix frontend run build`.
- [ ] Run Python tests on Windows if feasible.
- [ ] Confirm pywebview app launches from packaged environment.
- [ ] Confirm WebView2 dependency availability.
- [ ] Confirm settings/config/data paths land under intended Windows app data locations.
- [ ] Confirm no secrets or machine-specific paths are bundled.
- [ ] Do not run PyInstaller on Linux.
