# Step 5a DOCX Overflow Clamp Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Export DOCX files with Word Narrow margins while clamping images and specified table widths to printable A4 width.

**Architecture:** `infrastructure/docx_writer.py` owns page geometry and export clamps. `services/rte_document_service.py` migrates stored settings only when content creates a new revision. Existing Phase E tests cover defaults, migration, and real Word output.

**Tech Stack:** Python 3.12+, python-docx, pytest, existing RTE document service.

## Global Constraints

- Work only on branch `project-details/tiptap-docx-pipeline` from repo root `D:/Ibrahim/Projects/project_tracker`.
- Change only `infrastructure/docx_writer.py`, `services/rte_document_service.py`, and `tests/test_phase_e_notes_persistence.py`.
- Default A4 margins are `12.7` mm on all four sides.
- Keep Step 5b editor page width and Step 5c image drag-resize out of this round.
- Add no files, dependencies, frontend changes, or abstractions.
- Run one Step 5a manual gate before commit.
- Never run `npm run build` while Project Tracker may be open.
- Run every command from repo root; Python commands use repo-root venv.

---

## File Map

- `tests/test_phase_e_notes_persistence.py`: regressions for Narrow defaults, settings migration, image clamp, and table clamp.
- `infrastructure/docx_writer.py`: printable-width helper, Narrow page setup, and export bounds.
- `services/rte_document_service.py`: revision-time settings migration.

### Task 1: Prove Step 5a Requirements

**Files:**
- Modify: `tests/test_phase_e_notes_persistence.py:364`
- Modify: `tests/test_phase_e_notes_persistence.py:510`

**Interfaces:**
- Consumes: `DEFAULT_DOCUMENT_SETTINGS`, planned `content_width_mm(settings: dict[str, Any]) -> float`, `RteDocumentService.save_document()`, and existing `PNG_1PX`.
- Produces: regressions for defaults, migration, image clamp, and table clamp.

- [ ] **Step 1: Add default-width and sidecar-migration tests**

Add after `test_rte_pipeline_save_revisions_hash_skip_and_stale`:

```python
def test_docx_writer_uses_narrow_printable_width():
    from docx import Document
    from docx.shared import Mm

    from infrastructure.docx_writer import (
        DEFAULT_DOCUMENT_SETTINGS,
        _apply_page_setup,
        content_width_mm,
    )

    assert {
        DEFAULT_DOCUMENT_SETTINGS["margin_top_mm"],
        DEFAULT_DOCUMENT_SETTINGS["margin_right_mm"],
        DEFAULT_DOCUMENT_SETTINGS["margin_bottom_mm"],
        DEFAULT_DOCUMENT_SETTINGS["margin_left_mm"],
    } == {12.7}
    assert content_width_mm(DEFAULT_DOCUMENT_SETTINGS) == pytest.approx(184.6)
    assert content_width_mm({"margin_left_mm": 100, "margin_right_mm": 100}) == 40.0

    document = Document()
    _apply_page_setup(document, {})
    section = document.sections[0]
    assert section.top_margin == Mm(12.7)
    assert section.right_margin == Mm(12.7)
    assert section.bottom_margin == Mm(12.7)
    assert section.left_margin == Mm(12.7)


def test_rte_pipeline_revision_migrates_document_settings(rte_docx):
    import json as jsonlib

    from infrastructure.docx_writer import DEFAULT_DOCUMENT_SETTINGS

    svc, docx = rte_docx["service"], rte_docx["docx"]
    source = svc._new_source(docx)
    source["document_settings"] = {
        **DEFAULT_DOCUMENT_SETTINGS,
        "margin_top_mm": 20,
        "margin_right_mm": 20,
        "margin_bottom_mm": 20,
        "margin_left_mm": 20,
    }
    svc._store_source(docx, source)

    saved = svc.save_document(docx, {"content": _doc("narrow"), "base_revision": 0})

    assert saved["revision"] == 1
    stored = jsonlib.loads(svc.source_path(docx).read_text(encoding="utf-8"))
    assert stored["document_settings"] == DEFAULT_DOCUMENT_SETTINGS
```

- [ ] **Step 2: Add real-export overflow test**

Add after `test_rte_pipeline_real_export_roundtrip`:

```python
def test_rte_pipeline_real_export_clamps_image_and_table(temp_project):
    import base64 as b64

    from docx import Document
    from docx.oxml.ns import qn
    from docx.shared import Mm

    from infrastructure.docx_writer import DEFAULT_DOCUMENT_SETTINGS, content_width_mm
    from services.rte_document_service import RteDocumentService

    svc = RteDocumentService()
    docx = temp_project["project_path"] / "_cr-docs" / "wide-content.docx"
    docx.parent.mkdir(parents=True, exist_ok=True)
    image = svc.save_image(docx, b64.b64encode(PNG_1PX).decode())
    content = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{
                    "type": "image",
                    "attrs": {
                        "src": image["src"],
                        "assetId": image["asset_id"],
                        "width": 5000,
                    },
                }],
            },
            {
                "type": "table",
                "content": [{
                    "type": "tableRow",
                    "content": [
                        {
                            "type": "tableCell",
                            "attrs": {"colspan": 1, "rowspan": 1, "colwidth": [900]},
                            "content": [{"type": "paragraph", "content": [{"type": "text", "text": "A"}]}],
                        },
                        {
                            "type": "tableCell",
                            "attrs": {"colspan": 1, "rowspan": 1, "colwidth": [900]},
                            "content": [{"type": "paragraph", "content": [{"type": "text", "text": "B"}]}],
                        },
                    ],
                }],
            },
        ],
    }

    svc.save_document(docx, {"content": content, "base_revision": 0, "reason": "manual"})
    assert svc.coordinator.wait_idle(timeout_s=15)
    svc.coordinator.shutdown(timeout_s=5.0)

    exported = Document(str(docx))
    printable_mm = content_width_mm(DEFAULT_DOCUMENT_SETTINGS)
    assert exported.inline_shapes[0].width <= Mm(printable_mm) + 1000
    widths_dxa = []
    for cell in exported.tables[0].rows[0].cells:
        tc_w = cell._tc.get_or_add_tcPr().find(qn("w:tcW"))
        assert tc_w is not None
        widths_dxa.append(int(tc_w.get(qn("w:w"))))
    printable_dxa = printable_mm / 25.4 * 96.0 * 15
    assert sum(widths_dxa) <= printable_dxa + 15
```

- [ ] **Step 3: Run focused tests and confirm red state**

Run:

```powershell
D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_phase_e_notes_persistence.py -k "narrow_printable_width or migrates_document_settings or clamps_image_and_table" -v
```

Expected: failure importing `content_width_mm`; production helper does not exist yet.

### Task 2: Implement Printable-Width Bounds

**Files:**
- Modify: `infrastructure/docx_writer.py:20-41`
- Modify: `infrastructure/docx_writer.py:96-112`
- Modify: `infrastructure/docx_writer.py:214-295`
- Modify: `infrastructure/docx_writer.py:405-447`
- Modify: `services/rte_document_service.py:439-444`
- Test: `tests/test_phase_e_notes_persistence.py`

**Interfaces:**
- Consumes: source `document_settings`, image `attrs.width`, table cell `attrs.colwidth`, and existing `DEFAULT_DOCUMENT_SETTINGS` service import.
- Produces: `content_width_mm(settings: dict[str, Any]) -> float`, `_Renderer.content_width_px: float`, Narrow page setup, bounded Word output, and settings migration.

- [ ] **Step 1: Add Narrow defaults and printable-width helper**

Change defaults and add helper below them:

```python
DEFAULT_DOCUMENT_SETTINGS: dict[str, Any] = {
    "page_format": "A4",
    "margin_top_mm": 12.7,
    "margin_right_mm": 12.7,
    "margin_bottom_mm": 12.7,
    "margin_left_mm": 12.7,
    "default_font_family": "Times New Roman",
    "default_font_size_pt": 11,
    "line_height": 1.15,
}


def content_width_mm(settings: dict[str, Any]) -> float:
    return max(
        210.0
        - float(settings.get("margin_left_mm", 12.7))
        - float(settings.get("margin_right_mm", 12.7)),
        40.0,
    )
```

- [ ] **Step 2: Cache printable width in renderer**

Add after `self.settings = settings`:

```python
self.content_width_px = content_width_mm(settings) / 25.4 * 96.0
```

- [ ] **Step 3: Scale oversized specified table widths**

Insert before existing px-to-dxa loop:

```python
specified_width_px = sum(px for px in col_widths_px if px is not None)
if specified_width_px > self.content_width_px:
    scale = self.content_width_px / specified_width_px
    col_widths_px = [px * scale if px is not None else None for px in col_widths_px]
```

Keep existing px-to-dxa loop unchanged.

- [ ] **Step 4: Clamp explicit and natural image widths**

Add import:

```python
from docx.image.image import Image as _DocxImage
```

Replace current width/kwargs block in `_image_run()`:

```python
width = attrs.get("width")
kwargs = {}
max_width = Inches(self.content_width_px / 96.0)
if isinstance(width, (int, float)) and width > 0:
    kwargs["width"] = min(Inches(float(width) / 96.0), max_width)
else:
    try:
        probe = _DocxImage.from_file(str(path))
        natural = Inches(probe.px_width / float(probe.horz_dpi or 96))
        if natural > max_width:
            kwargs["width"] = max_width
    except Exception:
        pass
```

Keep existing `add_picture()` and unreadable-image fallback unchanged.

- [ ] **Step 5: Change page-setup fallbacks to Narrow**

Replace four margin assignments:

```python
section.top_margin = Mm(float(settings.get("margin_top_mm", 12.7)))
section.right_margin = Mm(float(settings.get("margin_right_mm", 12.7)))
section.bottom_margin = Mm(float(settings.get("margin_bottom_mm", 12.7)))
section.left_margin = Mm(float(settings.get("margin_left_mm", 12.7)))
```

- [ ] **Step 6: Migrate sidecar settings on revision change**

Change revision block in `save_document()`:

```python
if new_hash != source.get("content_hash"):
    source["revision"] = stored_revision + 1
    source["content"] = dehydrated
    source["content_hash"] = new_hash
    source["saved_at"] = _utc_now_iso()
    source["document_settings"] = dict(DEFAULT_DOCUMENT_SETTINGS)
    self._store_source(docx_path, source)
```

- [ ] **Step 7: Run focused tests and confirm green state**

Run:

```powershell
D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_phase_e_notes_persistence.py -k "narrow_printable_width or migrates_document_settings or clamps_image_and_table" -v
```

Expected: 3 selected tests pass.

- [ ] **Step 8: Run required non-build checks**

Run:

```powershell
npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run check
npm --prefix D:/Ibrahim/Projects/project_tracker/frontend test
D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_phase_e_notes_persistence.py -v
```

Expected: svelte-check 0 errors and warnings; frontend tests 0 failures; Phase E test file 0 failures.

- [ ] **Step 9: Stop until user confirms app closed, then build**

After explicit confirmation Project Tracker is closed, run:

```powershell
npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run build
```

Expected: exit code 0. Chunk-size warning allowed. Do not launch app automatically.

### Task 3: Manual Gate and Commit

**Files:**
- Verify: `infrastructure/docx_writer.py`
- Verify: `services/rte_document_service.py`
- Verify: `tests/test_phase_e_notes_persistence.py`

**Interfaces:**
- Consumes: built `web/static`, existing launch command, and exported DOCX output.
- Produces: user-verified Step 5a commit; no Step 5b or Step 5c work.

- [ ] **Step 1: Give exact manual checklist**

Ask user to launch from repo root:

```powershell
D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m main
```

Checklist:

1. Open CR project and select editable DOCX.
2. Use DOCX containing oversized image and wide two-column table, or insert large screenshot and widen table columns.
3. Save with `Ctrl+S`; wait for `DOCX saved`.
4. Switch DOCX files and menus; confirm load, save, titlebar navigation, typing, and table editing remain normal.
5. Open exported file in Word.
6. Confirm Layout margins show Narrow (`12.7` mm each side).
7. Confirm image and table stay inside right margin; text and table content remain intact.
8. Repeat at three app window sizes; backend-only change must not alter editor layout or controls.

- [ ] **Step 2: Wait for user verdict**

Expected pass: user confirms normal app behavior and Word output has no cutoff.

If abnormality appears, do not commit. Restore only uncommitted Step 5a changes, rebuild baseline after user closes app, record symptom in `_docs/session-notes.md`, and stop.

- [ ] **Step 3: Commit only Step 5a files after pass**

Run:

```powershell
git add -- infrastructure/docx_writer.py services/rte_document_service.py tests/test_phase_e_notes_persistence.py
git diff --cached --check
git commit -m "fix(rte): clamp DOCX content to Narrow margins"
```

Expected: one commit containing only three Step 5a files. Leave unrelated dirty files untouched. Stop before Step 5b.

## Self-Review

- Spec coverage: Narrow defaults, fallback margins, 184.6 mm width, 40 mm floor, explicit and natural image handling, table scaling, sidecar migration, existing failure behavior, required checks, manual gate, and commit boundary covered.
- Placeholder scan: clear; all code-changing steps include exact code.
- Type consistency: `content_width_mm(settings: dict[str, Any]) -> float` and `self.content_width_px` use same names in tests and production steps.
- Scope: three existing files only; Step 5b and Step 5c excluded.
