---
inclusion: always
---

# Release Candidate Rules

These rules govern all Release Candidate (RC) work. They summarize and point back
to root `CLAUDE.md` and `PRD.md`, which remain authoritative.

## Hard Rules

- **No fake success.** Never claim a feature works without real verification. Do
  not hide bridge/runtime errors; surface them in the UI and in reports.
- **No invented API contracts.** Frontend `callBridge(...)` names must map to
  real `project_tracker/web/js_api.py` methods wired in `create_js_api()`.
- **No destructive real filesystem operations.** No folder move/rename/delete or
  file write/delete against real user folders during dev or tests. Tests must use
  temp dirs / temp stores only.
- **No Outlook / Teams / COM / pyautogui execution** without explicit user
  approval. Guarded stubs only on Linux.
- **No package dependency changes.** Do not add/remove/upgrade dependencies.
- **No `js_api.py` signature changes** unless proven necessary, with all tests
  and docs updated in the same slice.
- **No direct `window.pywebview`** usage outside the bridge wrapper
  (`frontend/src/lib/bridge.ts`).
- **Do not edit** root `CLAUDE.md`, `PRD.md`, or `MIGRATION_PLAN.md`.

## High-Risk Runtime Actions

Folder transitions, file open/write/delete, Outlook/Teams/COM, and scheduler
real controls must have confirmation UI and must be tested with temp dirs, never
real project folders. Until implemented + reviewed, they stay deferred/disabled
with accurate disabled-state messaging.

## Verification (run after EVERY change)

```bash
rtk npm --prefix frontend run check
rtk npm --prefix frontend run build
rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/ -q
rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m py_compile project_tracker/app_web.py project_tracker/web/js_api.py
```

All four must pass before a change is considered complete.

## Commit Policy

- Commit each green slice separately. Do not amend, rebase, or reset.
- If there are no changes, do not commit.
- If a pre-commit hook only reformats markdown, accept it.
- If any change unexpectedly touches forbidden files, STOP AND ASK.
- Stop conditions: destructive filesystem risk, Windows-only execution needed,
  unclear product decision, failed verification, or unexpected dirty scope.
