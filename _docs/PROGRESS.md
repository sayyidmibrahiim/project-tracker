# Progress

> Single status source. Full history: `_docs/_archive/PROJECT_STATUS_history.md`

## Current Phase

Linux-green PRD-completion increment complete. Windows manual packaging/verification gate remains.
Branch: `prd-v31-migration`. PRD.md v3.1 = product truth.

## Active Blockers

- Windows-only runtime (Outlook COM, Teams pyautogui, os.startfile, PyInstaller) not yet verified — requires manual Windows testing.

## Pending PRD-Completion Slices

| Slice          | Area                                                          | Status  |
| -------------- | ------------------------------------------------------------- | ------- |
| 15.4/15.5/15.7 | Outlook off-Windows property test (P10), unit tests, frontend | Pending |
| 17.2-17.4      | Teams JsApi methods, tests, frontend                          | Pending |
| 19.2-19.4      | Scheduler JsApi methods, tests, frontend tab                  | Pending |
| 21.2-21.5      | Rules JsApi methods, P8 test, frontend CRUD/logs              | Pending |
| 23.1-23.3      | Bridge contract reconciliation, P7 shape test                 | Pending |

## Last 3 Completed Slices

1. **Dashboard Master-Detail Redesign** (2026-06-23): 38/62 master-detail layout, inline edits, DBS primary red tokens, layout tests updated.
2. **Claude Design System Migration** (2026-06-22): Global CSS props migrated to warm-editorial palette across all Svelte components. 1759 backend + 140 frontend tests pass.
3. **Dashboard Professional Polish** (2026-06-22): Header/controls/table/dock refinements, CR/Drone link display with copy/open, reduced-motion transitions.

## Pre-existing Test Failures (baseline)

| Test                                          | Root Cause                                      | Blocks Cleanup? |
| --------------------------------------------- | ----------------------------------------------- | --------------- |
| `test_file_open_dev_skipped_off_windows` (x2) | Missing `pytest.skip` guard on Windows          | No              |
| `test_create_js_api_returns_JsApi_instance`   | Import path shadow (intermittent in full suite) | No              |
| `test_run_creates_window_with_js_api...`      | Same import path shadow                         | No              |

## Verification (latest)

```
pytest: 1755 passed, 4 pre-existing failures, 20 skipped
svelte-check: 0 errors, 0 warnings
vite build: clean → web/static/
```
