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
- Modular monolith (core → services → infrastructure)
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
