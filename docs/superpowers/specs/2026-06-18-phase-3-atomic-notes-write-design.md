# Phase 3 Atomic Notes Write Design

## Purpose

Fix `notes.md` writes so a failed write cannot partially overwrite or corrupt existing project notes. This is a small data-safety slice for the `P2-25` cleanup finding.

## Source of Truth

`PRD.md` v3.1 keeps `notes.md` as primary notes storage. Existing migration rules require atomic writes for JSON; this slice applies the same safety pattern to free-form notes text without changing the notes storage model.

## Scope

In scope:

- Add a targeted regression test proving an interrupted `notes_update` preserves existing `notes.md` content.
- Add a small atomic UTF-8 text write helper.
- Route `_NotesServiceAdapter.update_notes()` through the helper.
- Keep `IMPLEMENTED` view-only lock behavior unchanged.
- Update `PROJECT_STATUS.md` with Phase 3 verification.
- Run relevant tests/build/live probe and refresh graphify.

Out of scope:

- No note editor UI changes.
- No storage migration.
- No change to JSON metadata writes.
- No app-wide filesystem refactor.
- No dead-code removal.
- No packaging execution.

## Implementation Design

Add a local helper in `project_tracker/app_web.py`:

```python
def _atomic_write_text(path: Path, content: str) -> None:
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

Then change `_NotesServiceAdapter.update_notes()` from direct `notes_file.write_text(...)` to `_atomic_write_text(notes_file, notes)`.

The helper is local because the slice only needs notes text writes. A broader infrastructure helper can be extracted later if more text-file atomic writes appear.

## Test Design

Extend `tests/test_phase_e_notes_persistence.py` with two checks:

1. Success path still writes and creates `notes.md`.
2. Failure path preserves existing content.

Failure path will monkeypatch `Path.write_text` so only the temp notes file write raises. Expected behavior:

- `js_api.notes_update(...)` returns `ok: false` through existing bridge error wrapping.
- original `notes.md` remains unchanged.
- temp file does not remain on disk when failure happens before replace.

## Verification Design

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_phase_e_notes_persistence.py -q
.\.venv\Scripts\python.exe -m py_compile project_tracker\app_web.py
.\.venv\Scripts\python.exe -m pytest tests\ -q
npm --prefix frontend run build
npm --prefix frontend run check
.\.venv\Scripts\python.exe -m project_tracker.main
```

Live probe must confirm:

- `/index.html` returns HTTP 200.
- built app HTML is present.
- JS asset returns HTTP 200.

After verification, run:

```powershell
graphify update .
```

## Risks

- Monkeypatching `Path.write_text` can affect fixture setup if scoped too broadly; patch only after fixture setup and only fail paths ending in `.notes.md.tmp` / `.notes.md.tmp` equivalent for the test project.
- If failure occurs after `replace()`, target may already be replaced; this design guarantees preservation only for failures before atomic replace, matching the existing JSON atomic write semantics.
- Existing dirty tree is broad; this slice must not revert unrelated files.

## Approval

Approved by user on 2026-06-18.
