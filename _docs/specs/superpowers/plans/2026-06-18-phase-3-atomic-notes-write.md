# Phase 3 Atomic Notes Write Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Project Details notes writes atomic so interrupted writes preserve existing `notes.md` content.

**Architecture:** Keep the existing notes storage model: `notes.md` remains the primary per-project notes file and `_NotesServiceAdapter` remains the pywebview bridge adapter. Add one local atomic UTF-8 text write helper in `project_tracker/app_web.py` and route only notes updates through it. No UI, bridge signature, storage migration, or packaging behavior changes.

**Tech Stack:** Python 3.12+, pathlib, pytest, pywebview bridge adapters, Svelte/Vite verification gates.

---

## File Structure

- Modify: `project_tracker/app_web.py`
  - Add `_atomic_write_text(path: Path, content: str) -> None` helper near existing pure helper functions.
  - Change `_NotesServiceAdapter.update_notes()` to use the helper instead of direct `Path.write_text()`.
- Modify: `tests/test_phase_e_notes_persistence.py`
  - Add regression tests for atomic failure preservation.
- Modify: `PROJECT_STATUS.md`
  - Add Phase 3 completion entry with verification evidence.
- Existing dirty files must remain untouched unless explicitly part of this plan.
- No frontend source changes are expected.

---

### Task 1: Add failing atomic-preservation regression test

**Files:**

- Modify: `tests/test_phase_e_notes_persistence.py`
- Read-only: `project_tracker/app_web.py`

- [ ] **Step 1: Add import for `Path` if not already present**

`tests/test_phase_e_notes_persistence.py` already imports `Path`:

```python
from pathlib import Path
```

Do not duplicate it.

- [ ] **Step 2: Add this regression test after `test_notes_update_round_trip`**

```python
def test_notes_update_failure_preserves_existing_notes_file(
    js_api, temp_project, monkeypatch
):
    """Failed notes update leaves existing notes.md unchanged and removes temp file."""
    project_path = temp_project["project_path"]
    notes_file = project_path / "notes.md"
    notes_file.write_text("original notes", encoding="utf-8")
    original_write_text = Path.write_text

    def fail_temp_notes_write(self: Path, data: str, *args, **kwargs):
        if self.name == ".notes.md.tmp":
            raise OSError("simulated temp write failure")
        return original_write_text(self, data, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_temp_notes_write)

    result = js_api.notes_update(str(project_path), "new notes")

    assert result["ok"] is False
    assert notes_file.read_text(encoding="utf-8") == "original notes"
    assert not (project_path / ".notes.md.tmp").exists()
```

- [ ] **Step 3: Run targeted test and confirm it fails before implementation**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_phase_e_notes_persistence.py::test_notes_update_failure_preserves_existing_notes_file -q
```

Expected before implementation: FAIL, because direct `notes_file.write_text(...)` writes the final target path and the monkeypatch does not intercept a `.notes.md.tmp` write. The test should fail at:

```text
assert result["ok"] is False
```

- [ ] **Step 4: Confirm no runtime source changed in Task 1**

Run:

```powershell
git diff -- project_tracker\app_web.py
```

Expected: no new diff from this task. Pre-existing Phase 1 diff in `app_web.py` may appear; do not revert it.

---

### Task 2: Implement atomic notes text write

**Files:**

- Modify: `project_tracker/app_web.py`
- Test: `tests/test_phase_e_notes_persistence.py`

- [ ] **Step 1: Add local helper after `_parse_optional_datetime`**

In `project_tracker/app_web.py`, add this function after `_parse_optional_datetime` and before `_folder_state_for_path`:

```python
def _atomic_write_text(path: Path, content: str) -> None:
    """Write UTF-8 text through a sibling temp file then atomic replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp")
    try:
        temp_path.write_text(content, encoding="utf-8")
        temp_path.replace(path)
    except Exception:
        try:
            temp_path.unlink()
        except OSError:
            pass
        raise
```

- [ ] **Step 2: Replace direct notes write**

Find `_NotesServiceAdapter.update_notes()` in `project_tracker/app_web.py` and replace:

```python
notes_file.write_text(notes, encoding="utf-8")
```

with:

```python
_atomic_write_text(notes_file, notes)
```

Keep this lock behavior unchanged:

```python
state = _folder_state_for_path(Path(project_path))
if state is ProjectState.IMPLEMENTED:
    raise ValueError(
        "Notes are view-only while the project is in IMPLEMENTED"
    )
```

- [ ] **Step 3: Run targeted failure-preservation test**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_phase_e_notes_persistence.py::test_notes_update_failure_preserves_existing_notes_file -q
```

Expected: PASS.

- [ ] **Step 4: Run full notes persistence tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_phase_e_notes_persistence.py -q
```

Expected: PASS. Current expected count after adding one test: `10 passed`.

---

### Task 3: Update project status

**Files:**

- Modify: `PROJECT_STATUS.md`

- [ ] **Step 1: Add Phase 3 status entry after Phase 2 entry**

Insert this section after `## 2026-06-18 — Cleanup MVP-1 Phase 2 dependency + entry-point reconciliation` and before `## Source of Truth`:

```markdown
## 2026-06-18 — Cleanup MVP-1 Phase 3 atomic notes write

Status: completed / verified on Windows dev machine.

- P2-25: `_NotesServiceAdapter.update_notes()` now writes `notes.md` via a
  sibling temp file and atomic replace instead of direct `Path.write_text()`.
- Existing `IMPLEMENTED` view-only lock behavior is unchanged.
- Added regression coverage proving a failed temp-file write preserves existing
  `notes.md` content and leaves no `.notes.md.tmp` file behind.
- No note editor UI, bridge signature, metadata JSON, packaging, or storage
  migration changes were made.

Verification:

- `.\.venv\Scripts\python.exe -m pytest tests\test_phase_e_notes_persistence.py -q` — PASS.
- `.\.venv\Scripts\python.exe -m py_compile project_tracker\app_web.py` — PASS.
- `.\.venv\Scripts\python.exe -m pytest tests\ -q` — PASS.
- `npm --prefix frontend run build` — PASS.
- `npm --prefix frontend run check` — PASS.
- `.\.venv\Scripts\python.exe -m project_tracker.main` live HTTP probe — PASS (`/index.html` 200, JS asset 200).

Next: Phase 4 cleanup queue.
```

If actual command output differs, update this text before final response.

---

### Task 4: Run verification gates

**Files:**

- Read-only verification; update `PROJECT_STATUS.md` if outputs differ.

- [ ] **Step 1: Run notes tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_phase_e_notes_persistence.py -q
```

Expected: PASS.

- [ ] **Step 2: Run py_compile**

Run:

```powershell
.\.venv\Scripts\python.exe -m py_compile project_tracker\app_web.py
```

Expected: PASS with no output.

- [ ] **Step 3: Run full backend tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ -q
```

Expected: PASS. Record exact pass/skip count in `PROJECT_STATUS.md`.

- [ ] **Step 4: Run frontend build**

Run:

```powershell
npm --prefix frontend run build
```

Expected: PASS.

- [ ] **Step 5: Run frontend check**

Run:

```powershell
npm --prefix frontend run check
```

Expected: PASS with `0 ERRORS 0 WARNINGS`.

- [ ] **Step 6: Run live app HTTP probe**

Use this PowerShell probe pattern from Phase 2:

```powershell
$before = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty LocalPort -Unique
$p = Start-Process -FilePath '.\.venv\Scripts\python.exe' -ArgumentList '-m','project_tracker.main' -PassThru -WindowStyle Minimized
try {
  Start-Sleep -Seconds 10
  $after = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty LocalPort -Unique
  $newPorts = $after | Where-Object { $before -notcontains $_ }
  $ok = $false
  foreach ($port in $newPorts) {
    try {
      $index = Invoke-WebRequest -Uri "http://127.0.0.1:$port/index.html" -UseBasicParsing -TimeoutSec 3
      $asset = [regex]::Match($index.Content, 'src="/([^\"]+\.js)"')
      if ($index.StatusCode -eq 200 -and $asset.Success) {
        $js = Invoke-WebRequest -Uri "http://127.0.0.1:$port/$($asset.Groups[1].Value)" -UseBasicParsing -TimeoutSec 3
        if ($js.StatusCode -eq 200) {
          "PASS port=$port index=200 js=200 asset=$($asset.Groups[1].Value)"
          $ok = $true
          break
        }
      }
    } catch {}
  }
  if (-not $ok) {
    "FAIL ports=$($newPorts -join ',')"
    exit 1
  }
} finally {
  if ($p -and -not $p.HasExited) {
    Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
  }
}
```

Expected:

```text
PASS port=<port> index=200 js=200 asset=<asset>
```

- [ ] **Step 7: Refresh graphify**

Run:

```powershell
graphify update .
```

Expected: PASS. If graph is too large for HTML viz, that warning is acceptable if `graph.json` and `GRAPH_REPORT.md` update.

---

### Task 5: Final review and response

**Files:**

- Verify final diff only.

- [ ] **Step 1: Review Phase 3 diff**

Run:

```powershell
git diff -- project_tracker\app_web.py tests\test_phase_e_notes_persistence.py PROJECT_STATUS.md docs\superpowers\specs\2026-06-18-phase-3-atomic-notes-write-design.md docs\superpowers\plans\2026-06-18-phase-3-atomic-notes-write.md
```

Expected Phase 3 changes:

```text
project_tracker/app_web.py
tests/test_phase_e_notes_persistence.py
PROJECT_STATUS.md
docs/superpowers/specs/2026-06-18-phase-3-atomic-notes-write-design.md
docs/superpowers/plans/2026-06-18-phase-3-atomic-notes-write.md
```

Pre-existing unrelated dirty files may remain. Do not revert them.

- [ ] **Step 2: Run review**

Run a read-only review focused on:

- helper preserves target on pre-replace failures
- temp cleanup happens
- IMPLEMENTED lock unchanged
- no UI/bridge signature drift
- tests are not false-positive

- [ ] **Step 3: Final response**

Use this structure:

```markdown
Phase 3 complete.

Changed:

- project_tracker/app_web.py
- tests/test_phase_e_notes_persistence.py
- PROJECT_STATUS.md
- docs/superpowers/specs/2026-06-18-phase-3-atomic-notes-write-design.md
- docs/superpowers/plans/2026-06-18-phase-3-atomic-notes-write.md

Verified:

- notes tests -> PASS (<exact count>)
- py_compile app_web.py -> PASS
- full pytest -> PASS (<exact count>)
- npm --prefix frontend run build -> PASS
- npm --prefix frontend run check -> PASS
- live HTTP probe -> PASS
- graphify update . -> PASS

Notes:

- `notes.md` writes now use temp-file + atomic replace.
- Existing IMPLEMENTED notes lock unchanged.
- No frontend/UI or bridge signature changes.
- Existing unrelated dirty tree left as-is.
```

---

## Self-review checklist

- Spec coverage: atomic text write, tests, status update, verification, graphify refresh all mapped to tasks.
- Placeholder scan: no TBD/TODO/unclear placeholders. Commands and expected outputs explicit.
- Type consistency: helper signature `_atomic_write_text(path: Path, content: str) -> None` matches implementation and tests. Temp file name `.notes.md.tmp` matches test monkeypatch and helper.
