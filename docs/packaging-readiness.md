# Packaging Readiness Audit

Audit-only. No packaging is performed here. Packaging must run on Windows and
only after the Windows manual RC test passes
(`docs/windows-manual-test-checklist.md`).

## Gate rule: manual test must pass first (Requirements 14.1, 14.6)

- Packaging is BLOCKED until the Windows manual test gate passes. The gate runs
  exclusively against a disposable test root, never real project folders
  (Requirement 14.1).
- If ANY check in the manual gate fails, all packaging steps are blocked and the
  failing check must be identified in the manual checklist observation log
  (Requirement 14.6).
- Do not begin a packaging session until every manual check is green.

## Current readiness

- **App entry point**: `project_tracker/main.py` → `project_tracker.app_web.run()`
  → `webview.start(http_server=True)` on the main thread. Suitable as the
  PyInstaller entry script.
- **Frontend output**: `vite build` writes to `web/static/` and is served by the
  pywebview HTTP server. This folder MUST be bundled as data in any package.
- **Packaging/runtime deps declared consistently**: `requirements.txt` and
  `pyproject.toml` both declare the approved runtime dependency set:
  `pywebview`, `pywin32`, `pyinstaller`, `pyautogui`, `pyperclip`,
  `send2trash`, `watchdog`, `python-dateutil`, and `APScheduler`. `PyQt6` is
  intentionally absent from production dependency metadata because the PyQt6 UI
  is reference-only legacy.
- **PyInstaller spec is authored** (`project_tracker_dbs.spec`) at the repo root.
  It bundles `web/static/` and `assets/` as data, excludes `PyQt6`, declares
  guarded Windows hidden imports (`webview`, `apscheduler`, `dateutil`,
  `send2trash`), and refuses evaluation off Windows via a `sys.platform != "win32"`
  guard. It has NOT been executed on Windows yet, so the produced bundle is
  unverified and packaging remains Windows-gated.
- **A Windows-only packaging entry point is authored** (`scripts/package.py`). It
  refuses to run on non-Windows with a clear message and non-zero exit, verifies
  required build inputs (`web/static/`, `assets/`, the spec) before invoking
  PyInstaller, and imports PyInstaller lazily only on Windows. The refuse path is
  Linux-runnable and exercised by automated checks.
- **Windows runtime deps present**: `pywin32`, `pyautogui`, `pyperclip`,
  `send2trash`, `watchdog`, `APScheduler`, `python-dateutil`, and `pywebview`
  are declared. WebView2 Runtime is an OS prerequisite, not a pip dependency.

## Missing pieces (blockers/gaps for packaging)

1. **Spec and invocation now exist but are unexecuted on Windows.** Both
   `project_tracker_dbs.spec` and `scripts/package.py` are authored with
   Windows-only guards. Neither has run on Windows yet, so the produced bundle is
   unverified. Remaining work: run `python scripts/package.py` (or
   `pyinstaller project_tracker_dbs.spec --noconfirm`) on Windows after the manual
   RC gate, then confirm the one-folder build launches with the Svelte UI.
2. **`web/static/` bundling is declared in the spec but unverified at runtime.**
   The spec maps `(web/static, "web/static")` and `(assets, "assets")` as data, so
   a bare `--add-data` flag is no longer required. This still must be verified on
   Windows: a missing/empty `web/static/` at build time (frontend not built) would
   produce a blank window. Build the frontend first so the spec's pre-build
   directory check passes.
3. **Dependency manifest drift is resolved (2026-06-18 Phase 2).**
   `pyproject.toml` and `requirements.txt` now declare the same approved runtime
   dependency names. `PyQt6` is not a production runtime dependency.
4. **WebView2 Runtime availability** on target machines must be confirmed
   (Evergreen runtime install or fixed-version bundling decision).
5. **Settings/data path strategy** for a packaged build must be confirmed (where
   `SettingsStore`, link bank, SQLite cache land under Windows app-data).

## Recommended packaging tool

PyInstaller (already declared). It supports pywebview + WebView2 desktop apps and
data bundling. Nuitka is an alternative but is not declared and would be a new
dependency — out of scope.

## Windows-only requirements

- Build and run PyInstaller on Windows only. Do NOT run PyInstaller on Linux
  (per CLAUDE.md environment boundaries).
- Build the frontend (`npm --prefix frontend run build`) before packaging so
  `web/static/` exists to bundle.
- Confirm WebView2 Runtime on the target.

## Risk list

- Missing `web/static/` in the bundle → blank window at runtime.
- Windows-only imports (Outlook COM, pyautogui) must remain lazy/guarded so the
  packaged app starts even when those subsystems are unavailable.
- Dependency drift is now guarded by
  `tests/test_phase_2_dependency_entrypoint_reconciliation.py`; keep it green
  if either `requirements.txt` or `pyproject.toml` changes.
- Path handling: Windows settings paths must not be normalized to POSIX.
- Secrets/machine-specific paths must not be bundled.

## Exact next prompt for a packaging session

> Packaging session (Windows only). Preconditions: Windows manual RC test in
> `docs/windows-manual-test-checklist.md` passed; `npm --prefix frontend run
build` done so `web/static/` exists. Tasks: (1) Confirm
> `tests/test_phase_2_dependency_entrypoint_reconciliation.py` is green so
> dependency metadata and entry points are still aligned. (2) Use the existing
> authored spec (`project_tracker_dbs.spec`) and entry point
> (`scripts/package.py`) for entry `project_tracker/main.py`; review that it
> bundles `web/static/` as data and keeps Windows-only imports lazy. (3) Build a
> one-folder build first, launch it, confirm WebView2 window + Svelte UI load.
> (4) Confirm settings/cache/data land in intended Windows app-data locations and
> no secrets/machine paths are bundled. (5) Only then attempt one-file build.
> Do not add dependencies without explicit approval. Do not run PyInstaller on
> Linux.
