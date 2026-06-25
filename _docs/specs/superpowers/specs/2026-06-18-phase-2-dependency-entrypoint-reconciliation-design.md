# Phase 2 Dependency + Entry-Point Reconciliation Design

## Purpose

Reconcile runtime dependency metadata and launch/package entry-point documentation before Windows packaging. This slice removes stale packaging risk without changing application behavior.

## Source of Truth

`PRD.md` v3.1 remains authoritative for product architecture. During context review, one conflict was found: PRD §3.2 examples still describe a root `app_web.py` launch shape, while current code and Windows setup use `python -m project_tracker.main` as the canonical launch command. This slice records and documents the current canonical entry point; it does not rewrite the PRD unless separately approved.

## Scope

In scope:

- Align `pyproject.toml` runtime dependencies with `requirements.txt` for approved dependencies.
- Remove legacy `PyQt6` from runtime dependency metadata.
- Add a minimal PEP 517 `[build-system]` section if absent.
- Preserve canonical launch flow: `project_tracker/main.py` -> `project_tracker.app_web.run()`.
- Preserve PyInstaller spec entry script: `project_tracker/main.py`.
- Update packaging/status docs to mark dependency drift fixed and entry point canonical.
- Add regression tests covering dependency metadata and entry-point consistency.
- Run full relevant verification and live app probe.
- Refresh graphify after changes if CLI is available.

Out of scope:

- No new runtime features.
- No frontend UI behavior changes.
- No pywebview threading changes.
- No PyInstaller packaging execution unless explicitly requested as a packaging session.
- No PRD rewrite beyond reporting the entry-point conflict.
- No dependency additions outside already approved PRD/runtime dependencies.

## Dependency Design

`requirements.txt` is currently the most accurate runtime install manifest. `pyproject.toml` will be reconciled to match approved runtime dependencies used by the app:

- `pywebview>=6.2.1`
- `pywin32>=306; platform_system == 'Windows'`
- `pyinstaller>=6.0.0`
- `pyautogui>=0.9.54`
- `pyperclip>=1.8.2`
- `send2trash>=1.8.3`
- `watchdog>=4.0.0`
- `python-dateutil>=2.9.0`
- `APScheduler>=3.10,<4`

`PyQt6` will be removed from `pyproject.toml` because PyQt6 is reference-only legacy UI and is excluded from production packaging.

A minimal build-system section will be added if absent:

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"
```

This supports `pip install .` metadata resolution without introducing application behavior changes.

## Entry-Point Design

Canonical source/run path stays unchanged:

```text
python -m project_tracker.main
  -> project_tracker/main.py
  -> project_tracker.app_web.run()
  -> webview.start(http_server=True)
```

Packaging remains unchanged:

```text
scripts/package.py
  -> project_tracker_dbs.spec
  -> ENTRY_SCRIPT = project_tracker/main.py
```

This keeps `pywebview.start()` on the main thread and keeps packaging aligned with the runtime launch path.

## Documentation Design

`docs/packaging-readiness.md` will be updated to remove the stale dependency-drift blocker and state that `pyproject.toml`/`requirements.txt` are reconciled for approved runtime dependencies.

`PROJECT_STATUS.md` will get a Phase 2 entry with:

- files changed
- dependency reconciliation result
- entry-point decision
- verification commands and results
- remaining Windows packaging/manual gate

If PRD conflict wording needs a product-source update later, it should be a separate explicit PRD documentation slice.

## Test Design

Add a targeted regression test file that uses Python stdlib only:

- Parse `requirements.txt` and `pyproject.toml` dependency names.
- Assert approved runtime deps exist in both manifests: `pywebview`, `pywin32`, `pyinstaller`, `pyautogui`, `pyperclip`, `send2trash`, `watchdog`, `python-dateutil`, `APScheduler`.
- Assert `PyQt6` is absent from `pyproject.toml` runtime dependencies.
- Assert `pyproject.toml` has `[build-system]`.
- Assert `project_tracker_dbs.spec` uses `project_tracker/main.py` as `ENTRY_SCRIPT`.
- Assert `project_tracker/main.py` imports and calls `project_tracker.app_web.run`.

## Verification Design

Minimum gates:

```powershell
npm --prefix frontend run build
npm --prefix frontend run check
.\.venv\Scripts\python.exe -m py_compile project_tracker\app_web.py project_tracker\web\js_api.py project_tracker\main.py scripts\package.py
.\.venv\Scripts\python.exe -m pytest tests\test_phase_2_dependency_entrypoint_reconciliation.py -q
.\.venv\Scripts\python.exe -m pytest tests\ -q
.\.venv\Scripts\python.exe -m project_tracker.main
```

Live app probe must confirm:

- `/index.html` returns HTTP 200.
- built app HTML is present.
- at least one JS asset returns HTTP 200.

After verification, run `graphify update .` if available.

## Risks

- `pyproject.toml` install behavior may expose packaging metadata assumptions not used by `requirements.txt`; targeted tests reduce this risk.
- PRD §3.2 root `app_web.py` example remains stale; this slice records the conflict instead of editing product source without explicit PRD-edit approval.
- Windows packaging remains unverified until separate manual packaging session.

## Approval

Approved by user on 2026-06-18 with option 1: metadata + docs.
