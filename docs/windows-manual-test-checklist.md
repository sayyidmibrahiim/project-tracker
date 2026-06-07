# Windows Manual Test Checklist

Reproducible, step-by-step manual validation for the Release Candidate on
Windows. This complements `docs/release-candidate-manual-test-plan.md` by adding
environment prerequisites, exact launch/verification commands, rollback notes,
and an observation log.

> Safety: use a DISPOSABLE test root and DISPOSABLE project folders only. Never
> point the app at real production project folders during manual testing.

## 1. Environment prerequisites

- Windows 10/11 with **WebView2 Runtime** installed (Edge WebView2). Verify via
  "Apps > Installed apps" → "Microsoft Edge WebView2 Runtime".
- Python 3.12+ on PATH (`python --version`).
- Node.js 18+ and npm (`node --version`, `npm --version`) for the frontend build.
- A Python virtual environment with project dependencies installed.
- A disposable test root folder, e.g. `C:\Temp\ptdbs_test_root`, containing a
  year subfolder and PRD state subfolders, e.g.
  `C:\Temp\ptdbs_test_root\2026\UAT_PREPARE\SampleProject`.

### One-time setup (PowerShell, from repo root)

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
npm --prefix frontend install
```

## 2. Build frontend (required before launch)

The pywebview shell serves the built Svelte output from `web/static/`. Build
first; otherwise `get_frontend_entry_path()` raises FileNotFoundError.

```powershell
npm --prefix frontend run build
```

Expected: `vite build` completes and writes `web/static/index.html` plus
`web/static/assets/`.

## 3. Run automated baseline on Windows (optional but recommended)

```powershell
npm --prefix frontend run check
.\.venv\Scripts\python -m pytest tests/ -q
.\.venv\Scripts\python -m py_compile project_tracker\app_web.py project_tracker\web\js_api.py
```

Expected: svelte-check 0 errors, pytest all passed, py_compile silent.

## 4. Launch the pywebview app

```powershell
.\.venv\Scripts\python -m project_tracker.main
```

(Entry point: `project_tracker/main.py` → `project_tracker.app_web.run()`, which
calls `webview.start(http_server=True)` on the main thread.)

- [ ] WebView2 window titled "Project Tracker DBS" opens.
- [ ] Svelte UI renders from bundled `web/static/` (not a raw `file://` page).
- [ ] No blank/white screen; sidebar + header + content visible.

## 5. Per-page checks

### Dashboard

- [ ] CR - Project Summary table renders.
- [ ] Year dropdown switches data set.
- [ ] Status filter tabs reflect live counts.
- [ ] Search filters visible rows.
- [ ] Refresh re-fetches.

### Settings

- [ ] Settings load.
- [ ] Save root folder path as a Windows path (e.g. `C:\Temp\ptdbs_test_root`).
- [ ] Reload: path persists and is NOT normalized into a Linux/POSIX path.
- [ ] Second Brain folder and template paths persist the same way.

### Project Details

- [ ] Project list loads for selected year.
- [ ] Selecting a project loads detail, files, subprojects, notes.

### Report

- [ ] Report filter loads projects for selected year / all.
- [ ] Export CSV returns CSV text (no external write side effects).

### Second Brain

- [ ] Configure disposable Second Brain folder in Settings.
- [ ] Add `.md`, `.txt`, and another file type OUTSIDE the app.
- [ ] Notes tab lists discovered files; hidden/dotfiles excluded.
- [ ] Search matches title/excerpt.
- [ ] Pin/Favorite/Edit show as deferred read-only (no write).

### Automations

- [ ] Rules tab loads.
- [ ] Evaluate (preview) and Evaluate All (preview) show result badges only.
- [ ] Outlook/Teams/Scheduler tabs show deferred placeholders and execute nothing.

## 6. Mutation checks (temp data only)

- [ ] CR Link Save persists; reload shows saved link.
- [ ] Notes Save writes `notes.md`; reload shows saved text.
- [ ] Drone add/edit/delete persists (metadata-only).
- [ ] Guarded CR State Save: valid transition succeeds; invalid transition shows
      a visible error and does NOT persist.
- [ ] Guarded Drone State Save: same valid/invalid behavior; empty drone link is
      rejected.
- [ ] Link Bank add/edit/archive: archive is soft (no hard delete).

## 7. Deferred checks — confirm still disabled/deferred

- [ ] Folder move/rename/delete/transition controls deferred or disabled.
- [ ] File open / external-app / write / delete not executed.
- [ ] Outlook COM draft/send/download not executed.
- [ ] Teams / pyautogui not executed.
- [ ] Scheduler start/stop/run-once not executed from real controls.

## 8. Rollback notes

- All mutations target the disposable test root only. To roll back, delete the
  disposable test root folder and recreate it from the sample structure.
- Settings persist via `SettingsStore`. To reset, restore or delete the settings
  file written by the app (note its location during testing) and relaunch.
- The SQLite cache is rebuildable; deleting the cache DB and rescanning restores
  it from filesystem + JSON. No canonical data lives only in SQLite.
- No git changes result from manual testing; if any appear, discard them.

## 9. Observation log

Record actual results for the handoff. Example table:

| Area | Step | Expected | Observed | Pass/Fail | Notes |
| ---- | ---- | -------- | -------- | --------- | ----- |
| Startup | WebView2 opens | window + UI | | | |
| Settings | Save Windows path | not normalized | | | |
| Project Details | CR Link Save | persists | | | |
| Project Details | Guarded CR state invalid | visible error, no persist | | | |
| Second Brain | List files | dotfiles excluded | | | |
| Automations | Evaluate preview | badge only, no side effects | | | |

A green run here is the gate before any packaging session (see
`docs/packaging-readiness.md`).
