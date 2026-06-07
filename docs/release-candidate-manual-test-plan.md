# Release Candidate Manual Test Plan

## Scope

This checklist covers manual Windows validation and packaging work that cannot be fully verified on Linux.

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

- [ ] Create or select a safe test root folder.
- [ ] Launch the pywebview app on Windows.
- [ ] Confirm WebView2 window opens.
- [ ] Confirm Svelte UI loads from bundled `web/static/` output.
- [ ] Confirm no raw `file://` production loading.
- [ ] Confirm Settings page can save and reload root folder paths without Linux path normalization.

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

## Windows-only integrations still deferred

Do not run real external actions until explicit implementation and review:

- [ ] Outlook COM draft/send/download behavior.
- [ ] Teams/pyautogui behavior.
- [ ] Scheduler start/stop/run-once.
- [ ] File open/external app behavior.
- [ ] Folder move/rename/delete transitions.

## Packaging checklist

Packaging must be done on Windows, not Linux.

- [ ] Build frontend first: `rtk npm --prefix frontend run build`.
- [ ] Run Python tests on Windows if feasible.
- [ ] Confirm pywebview app launches from packaged environment.
- [ ] Confirm WebView2 dependency availability.
- [ ] Confirm settings/config/data paths land under intended Windows app data locations.
- [ ] Confirm no secrets or machine-specific paths are bundled.
- [ ] Do not run PyInstaller on Linux.
