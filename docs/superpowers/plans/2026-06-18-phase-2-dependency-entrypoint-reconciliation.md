# Phase 2 Dependency + Entry-Point Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconcile Python dependency metadata and entry-point documentation so Windows packaging uses one truthful runtime path.

**Architecture:** No runtime behavior changes. `requirements.txt` remains the install manifest used by Windows setup; `pyproject.toml` becomes a matching project metadata manifest for approved runtime dependencies. Canonical launch stays `python -m project_tracker.main`, which calls `project_tracker.app_web.run()` and is used by `project_tracker_dbs.spec`.

**Tech Stack:** Python 3.12, pywebview, APScheduler, PyInstaller, Svelte/Vite/Tailwind build output in `web/static/`, stdlib `tomllib` tests.

---

## File Structure

- Modify: `pyproject.toml`
  - Responsibility: project metadata and approved runtime dependency list.
- Create: `tests/test_phase_2_dependency_entrypoint_reconciliation.py`
  - Responsibility: regression guard for dependency drift and canonical entry-point chain.
- Modify: `docs/packaging-readiness.md`
  - Responsibility: packaging audit status; remove stale drift blocker after fix.
- Modify: `PROJECT_STATUS.md`
  - Responsibility: record Phase 2 completion evidence and remaining gate.
- No change: `requirements.txt`
  - It is already accurate; tests compare against it.
- No change: `project_tracker/main.py`
  - It already calls `project_tracker.app_web.run()`.
- No change: `project_tracker_dbs.spec`
  - It already points at `project_tracker/main.py`.
- No change: runtime app code.

---

### Task 1: Add failing dependency + entry-point regression tests

**Files:**

- Create: `tests/test_phase_2_dependency_entrypoint_reconciliation.py`
- Read-only inputs: `pyproject.toml`, `requirements.txt`, `project_tracker/main.py`, `project_tracker_dbs.spec`

- [ ] **Step 1: Create test file**

Write this exact file:

```python
from __future__ import annotations

import ast
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

APPROVED_RUNTIME_DEPS = {
    "apscheduler",
    "pyautogui",
    "pyinstaller",
    "pyperclip",
    "python-dateutil",
    "pywebview",
    "pywin32",
    "send2trash",
    "watchdog",
}

LEGACY_RUNTIME_DEPS = {"pyqt6"}


def _normalize_dependency_name(requirement: str) -> str:
    requirement = requirement.strip()
    requirement = requirement.split(";", 1)[0].strip()
    match = re.match(r"([A-Za-z0-9_.-]+)", requirement)
    assert match is not None, f"Could not parse dependency name from {requirement!r}"
    return match.group(1).replace("_", "-").lower()


def _requirements_dependencies() -> set[str]:
    lines = (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    return {
        _normalize_dependency_name(line)
        for line in lines
        if line.strip() and not line.lstrip().startswith("#")
    }


def _pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def _pyproject_dependencies() -> set[str]:
    dependencies = _pyproject()["project"]["dependencies"]
    return {_normalize_dependency_name(dep) for dep in dependencies}


def test_pyproject_declares_approved_runtime_dependencies() -> None:
    assert APPROVED_RUNTIME_DEPS <= _pyproject_dependencies()


def test_pyproject_runtime_dependencies_match_requirements_baseline() -> None:
    requirements_deps = _requirements_dependencies()
    pyproject_deps = _pyproject_dependencies()

    assert APPROVED_RUNTIME_DEPS <= requirements_deps
    assert APPROVED_RUNTIME_DEPS <= pyproject_deps
    assert pyproject_deps == requirements_deps


def test_pyproject_does_not_declare_legacy_pyqt6_runtime() -> None:
    assert _pyproject_dependencies().isdisjoint(LEGACY_RUNTIME_DEPS)


def test_pyproject_has_pep517_build_system() -> None:
    data = _pyproject()

    assert data["build-system"]["requires"] == ["setuptools>=68"]
    assert data["build-system"]["build-backend"] == "setuptools.build_meta"


def test_project_tracker_main_calls_app_web_run() -> None:
    source = (ROOT / "project_tracker" / "main.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    imports_run = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "project_tracker.app_web"
        and any(alias.name == "run" for alias in node.names)
        for node in tree.body
    )
    raises_system_exit_run = any(
        isinstance(node, ast.If)
        and any(
            isinstance(child, ast.Raise)
            and isinstance(child.exc, ast.Call)
            and isinstance(child.exc.func, ast.Name)
            and child.exc.func.id == "SystemExit"
            and child.exc.args
            and isinstance(child.exc.args[0], ast.Call)
            and isinstance(child.exc.args[0].func, ast.Name)
            and child.exc.args[0].func.id == "run"
            for child in node.body
        )
        for node in tree.body
    )

    assert imports_run
    assert raises_system_exit_run


def test_pyinstaller_spec_uses_project_tracker_main_entry_script() -> None:
    spec_text = (ROOT / "project_tracker_dbs.spec").read_text(encoding="utf-8")

    assert 'ENTRY_SCRIPT = str(REPO_ROOT / "project_tracker" / "main.py")' in spec_text
    assert "ENTRY_SCRIPT" in spec_text
    assert "Analysis(" in spec_text
```

- [ ] **Step 2: Run targeted test to verify current failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_phase_2_dependency_entrypoint_reconciliation.py -q
```

Expected before implementation: FAIL. At least these assertions should fail:

```text
test_pyproject_declares_approved_runtime_dependencies
```

because `pyproject.toml` is missing `pywebview`, `python-dateutil`, and `APScheduler`, and still includes `PyQt6`.

- [ ] **Step 3: Do not change runtime code in this task**

Confirm no files under `project_tracker/` changed from this task except read-only inspection.

Run:

```powershell
git diff -- project_tracker
```

Expected: no diff.

---

### Task 2: Reconcile `pyproject.toml`

**Files:**

- Modify: `pyproject.toml`
- Test: `tests/test_phase_2_dependency_entrypoint_reconciliation.py`

- [ ] **Step 1: Replace dependency section and add build-system**

Update `pyproject.toml` so the whole file is exactly:

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "project-tracker-dbs"
version = "0.1.0"
description = "Windows desktop tracker for CR deployment projects"
requires-python = ">=3.12"
dependencies = [
  "pywebview>=6.2.1",
  "pywin32>=306; platform_system == 'Windows'",
  "pyinstaller>=6.0.0",
  "pyautogui>=0.9.54",
  "pyperclip>=1.8.2",
  "send2trash>=1.8.3",
  "watchdog>=4.0.0",
  "python-dateutil>=2.9.0",
  "APScheduler>=3.10,<4",
]

[tool.pytest.ini_options]
pythonpath = ["."]
```

- [ ] **Step 2: Run targeted test**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_phase_2_dependency_entrypoint_reconciliation.py -q
```

Expected: PASS.

```text
6 passed
```

- [ ] **Step 3: Verify no runtime code changed**

Run:

```powershell
git diff -- project_tracker
```

Expected: no diff.

---

### Task 3: Update packaging readiness doc

**Files:**

- Modify: `docs/packaging-readiness.md`
- Test: manual markdown review plus full verification in Task 5

- [ ] **Step 1: Update current readiness dependency bullets**

In `docs/packaging-readiness.md`, update the dependency/status bullets so they say:

```markdown
- **Packaging/runtime deps declared consistently**: `requirements.txt` and
  `pyproject.toml` both declare the approved runtime dependency set:
  `pywebview`, `pywin32`, `pyinstaller`, `pyautogui`, `pyperclip`,
  `send2trash`, `watchdog`, `python-dateutil`, and `APScheduler`. `PyQt6` is
  intentionally absent from production dependency metadata because the PyQt6 UI
  is reference-only legacy.
```

Also keep the WebView2 note:

```markdown
- **Windows runtime deps present**: `pywin32`, `pyautogui`, `pyperclip`,
  `send2trash`, `watchdog`, `APScheduler`, `python-dateutil`, and `pywebview`
  are declared. WebView2 Runtime is an OS prerequisite, not a pip dependency.
```

- [ ] **Step 2: Replace stale Missing Pieces dependency blocker**

Replace this blocker section:

```markdown
3. **Dependency manifest drift (report-only; do NOT change without approval).**
   `pyproject.toml` `[project.dependencies]` is out of sync with
   `requirements.txt`:
   - `pyproject.toml` is MISSING: `pywebview`, `APScheduler`, `python-dateutil`.
   - `pyproject.toml` still LISTS legacy `PyQt6` (reference-only per CLAUDE.md).
   - For packaging, `requirements.txt` is the more accurate runtime manifest.
     This drift should be reconciled in a dedicated, approved slice, not here.
```

with:

```markdown
3. **Dependency manifest drift is resolved (2026-06-18 Phase 2).**
   `pyproject.toml` and `requirements.txt` now declare the same approved runtime
   dependency names. `PyQt6` is not a production runtime dependency.
```

- [ ] **Step 3: Update risk list**

Replace this risk bullet:

```markdown
- `pyproject.toml`/`requirements.txt` drift could cause a packaged build to miss
  `pywebview`/`APScheduler` if the build resolves deps from `pyproject.toml`.
  Build from `requirements.txt` or reconcile first (approved slice).
```

with:

```markdown
- Dependency drift is now guarded by
  `tests/test_phase_2_dependency_entrypoint_reconciliation.py`; keep it green
  if either `requirements.txt` or `pyproject.toml` changes.
```

- [ ] **Step 4: Update exact next prompt**

In the quoted prompt at the bottom, replace task `(1)` with:

```markdown
> first. (1) Confirm `tests/test_phase_2_dependency_entrypoint_reconciliation.py`
> is green so dependency metadata and entry points are still aligned.
```

Keep packaging-gate wording unchanged: packaging still waits for Windows manual gate.

---

### Task 4: Update project status

**Files:**

- Modify: `PROJECT_STATUS.md`
- Test: manual markdown review plus full verification in Task 5

- [ ] **Step 1: Insert Phase 2 status entry after Phase 1 entry**

Add this section immediately after the 2026-06-18 Phase 1 entry and before `## Source of Truth`:

```markdown
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

- `npm --prefix frontend run build` — PASS.
- `npm --prefix frontend run check` — PASS.
- `.\.venv\Scripts\python.exe -m py_compile project_tracker\app_web.py project_tracker\web\js_api.py project_tracker\main.py scripts\package.py` — PASS.
- `.\.venv\Scripts\python.exe -m pytest tests\test_phase_2_dependency_entrypoint_reconciliation.py -q` — PASS.
- `.\.venv\Scripts\python.exe -m pytest tests\ -q` — PASS.
- `.\.venv\Scripts\python.exe -m project_tracker.main` live HTTP probe — PASS (`/index.html` 200, built app HTML present, JS asset 200).

Next: Phase 3 per cleanup/audit queue.
```

If a verification command later reports a different count/details, update this section with the actual observed output before final response.

- [ ] **Step 2: Preserve existing status history**

Do not delete older phase sections. This file is a historical log.

---

### Task 5: Run verification gates

**Files:**

- Read-only verification; update `PROJECT_STATUS.md` if command outputs differ.

- [ ] **Step 1: Run frontend build**

Run:

```powershell
npm --prefix frontend run build
```

Expected: PASS; Vite writes `web/static/`.

- [ ] **Step 2: Run frontend check**

Run:

```powershell
npm --prefix frontend run check
```

Expected: PASS with `0 ERRORS 0 WARNINGS`.

- [ ] **Step 3: Run py_compile**

Run:

```powershell
.\.venv\Scripts\python.exe -m py_compile project_tracker\app_web.py project_tracker\web\js_api.py project_tracker\main.py scripts\package.py
```

Expected: PASS with no output.

- [ ] **Step 4: Run targeted Python tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_phase_2_dependency_entrypoint_reconciliation.py -q
```

Expected: PASS.

- [ ] **Step 5: Run full Python tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ -q
```

Expected: PASS. Record exact passed/skipped count in `PROJECT_STATUS.md` if it differs from prefilled text.

- [ ] **Step 6: Run live app probe**

Start app in background:

```powershell
.\.venv\Scripts\python.exe -m project_tracker.main
```

Probe launched local HTTP server. Use whatever URL/port the app prints, then verify:

```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:<PORT>/index.html" -UseBasicParsing
Invoke-WebRequest -Uri "http://127.0.0.1:<PORT>/<JS_ASSET_FROM_INDEX>" -UseBasicParsing
```

Expected:

```text
/index.html -> 200
JS asset -> 200
```

Stop the app after the probe.

- [ ] **Step 7: Refresh graphify if available**

Run:

```powershell
graphify update .
```

Expected: PASS if graphify CLI is installed. If unavailable, record skipped.

---

### Task 6: Final review and status report

**Files:**

- Verify final diff only.

- [ ] **Step 1: Review changed files**

Run:

```powershell
git diff -- pyproject.toml tests\test_phase_2_dependency_entrypoint_reconciliation.py docs\packaging-readiness.md PROJECT_STATUS.md docs\superpowers\specs\2026-06-18-phase-2-dependency-entrypoint-reconciliation-design.md docs\superpowers\plans\2026-06-18-phase-2-dependency-entrypoint-reconciliation.md
```

Expected changed files:

```text
pyproject.toml
tests/test_phase_2_dependency_entrypoint_reconciliation.py
docs/packaging-readiness.md
PROJECT_STATUS.md
docs/superpowers/specs/2026-06-18-phase-2-dependency-entrypoint-reconciliation-design.md
docs/superpowers/plans/2026-06-18-phase-2-dependency-entrypoint-reconciliation.md
```

Existing unrelated dirty files may remain from prior phases. Do not revert them.

- [ ] **Step 2: Confirm runtime source unchanged**

Run:

```powershell
git diff -- project_tracker
```

Expected: no diff, except if unrelated pre-existing changes were already present before Phase 2. If there are pre-existing changes, report them as pre-existing and do not modify them.

- [ ] **Step 3: Final response contents**

Final response must include:

```markdown
Phase 2 complete.

Changed:

- pyproject.toml
- tests/test_phase_2_dependency_entrypoint_reconciliation.py
- docs/packaging-readiness.md
- PROJECT_STATUS.md
- docs/superpowers/specs/2026-06-18-phase-2-dependency-entrypoint-reconciliation-design.md
- docs/superpowers/plans/2026-06-18-phase-2-dependency-entrypoint-reconciliation.md

Verified:

- npm --prefix frontend run build -> PASS
- npm --prefix frontend run check -> PASS
- py_compile -> PASS
- targeted pytest -> PASS
- full pytest -> PASS (<exact count>)
- live HTTP probe -> PASS
- graphify update . -> PASS/SKIPPED

Notes:

- No runtime app code changed.
- Canonical entry point remains `python -m project_tracker.main`.
- Windows packaging still gated by manual checklist.
- Existing unrelated dirty tree left as-is.
```

---

## Self-review checklist

- Spec coverage: dependency metadata, entry-point chain, docs/status update, tests, verification, graphify refresh all mapped to tasks.
- Placeholder scan: no TBD/TODO/fill-in placeholders. Commands and expected outputs are explicit.
- Type/name consistency: test file name is identical across tasks; dependency names normalize consistently; entry script path matches spec file literal.
