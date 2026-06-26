# Tech Stack Details

## Frontend

- **Svelte** — component framework (not SvelteKit, plain Svelte + Vite)
- **TypeScript** — strict mode preferred
- **Vite** — bundler, output to `web/static/`
- **Tailwind CSS** — local build via PostCSS, never CDN
- Production frontend served by pywebview local HTTP server, never raw `file://`
- Source lives in `frontend/`, build output in `web/static/`
- Before changing build config → use context7 for current Svelte/Vite/Tailwind docs

## Backend

- **Python 3.12+**
- Layered monolith (services → core + infrastructure; core → nothing)
- `pathlib.Path` everywhere, never string concatenation
- Windows paths stay Windows-formatted in settings JSON
- Windows-only imports guarded with `sys.platform == "win32"` — keep guards even on Windows

## Desktop Shell

- **pywebview** with `frameless=True` + custom Svelte titlebar component
- WebView2 runtime (Windows)
- `pywebview.start()` must run on main thread — non-negotiable
- Prebuilt `web/static/` included so app runs after `pip install` alone
- Rebuild frontend only when frontend source changes

## Data & Persistence

- **Canonical:** Filesystem + `project_data.json` (metadata only)
- **Cache:** SQLite — rebuildable from filesystem + JSON + local files
- `project_state` derived from folder location, never stored in `project_data.json`
- Atomic JSON writes via metadata store mechanism
- Hard delete forbidden — use `send2trash` on Windows
- Datetimes: ISO 8601 timezone-aware, local OS timezone

## Windows Integrations

- **Outlook COM** — `pythoncom.CoInitialize()` on background thread, `CoUninitialize()` in finally
- **Teams** — `pyautogui` for desktop automation, guarded Windows-only service code
- **send2trash** — Recycle Bin delete
- **os.startfile** — open files/folders in Windows default app

## Scheduling

- **APScheduler** — in-process, local scheduled/background jobs
- Acceptable for desktop app; not designed for server deployment

## Packaging

- **PyInstaller** — runs on this Windows machine (no longer Linux-restricted)
- Script: `scripts/package.py`

## Dependencies

Do not add dependencies without user confirmation except those approved in PRD.md v3.1.

## RTK (Optional)

RTK is a token-optimization CLI proxy, Linux-oriented. If installed, prefix commands with `rtk`. If not installed (normal on Windows), run commands directly without it.

## Known Weaknesses & Mitigations

| #   | Weakness                          | Impact                                                                                                                                  | Mitigation                                                                                                                                                                   |
| --- | --------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| W1  | **pywebview WebView2 dependency** | Runtime requires WebView2 (preinstalled Win10/11, edge cases on LTSC/Server). Larger bundle vs Tauri. Limited API surface.              | Pin WebView2 fixed-version bundling for distribution. Evaluate Tauri if bundle size becomes blocker.                                                                         |
| W2  | **app_web.py 69KB/1572 lines**    | Single composition root growing unbounded. Maintainability risk, no DI.                                                                 | Split incrementally — extract JS API methods to per-domain modules (dashboard_api, project_api, email_api). Composition root stays thin. Pattern started in `web/js_api.py`. |
| W3  | **pyautogui for Teams**           | Fragile — depends on window coordinates/focus, breaks when Teams UI changes.                                                            | Document Teams version dependency. Fallback to manual. Consider Graph API if Teams cloud available.                                                                          |
| W4  | **Outlook COM threading**         | `pythoncom.CoInitialize()` required on background thread, `CoUninitialize()` in finally. Race condition if COM called from main thread. | Enforce thread boundary in service layer. Test COM on background thread only.                                                                                                |
| W5  | **APScheduler in-process**        | Not for server. Job state lost on crash.                                                                                                | Acceptable for desktop single-user. Persist job config to settings.json, rebuild scheduler at startup.                                                                       |
| W6  | **Python version mismatch**       | `requires-python = ">=3.12"` but env runs **Python 3.14.0**. Potential stdlib changes, C-ext compat.                                    | Either pin upper bound (`<3.15`) for stability, or update `requires-python = ">=3.14"` and test. Document production target version.                                         |
