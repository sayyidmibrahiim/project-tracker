# Step 5a DOCX Overflow Clamp Design

## Goal

Export DOCX files with Word Narrow margins and keep images and tables inside printable page width.

## Scope

- Change only `infrastructure/docx_writer.py`, `services/rte_document_service.py`, and `tests/test_phase_e_notes_persistence.py` during implementation.
- Set all default and fallback A4 margins to `12.7` mm.
- Clamp exported images and specified table column widths to printable width.
- Migrate old sidecar document settings on next content revision.
- Keep Step 5b editor page width and Step 5c image drag-resize out of this round.
- Add no files, dependencies, frontend changes, or abstractions during implementation.

## Architecture

`docx_writer.py` remains sole owner of Word page geometry. A small `content_width_mm(settings)` helper derives printable A4 width from left and right margins, with a `40.0` mm floor. `_Renderer` converts that value to CSS pixels once and reuses it for image and table clamps.

`rte_document_service.py` remains sole owner of source-sidecar migration. When content changes and revision increments, service replaces `document_settings` with current `DEFAULT_DOCUMENT_SETTINGS` before storing source. Autosaves skipped because content hash is unchanged do not rewrite sidecar.

## Export Behavior

### Page setup

- Default margins: top, right, bottom, and left = `12.7` mm.
- Missing margin fallbacks in `_apply_page_setup()` also use `12.7` mm.
- A4 printable width with default margins: `210 - 12.7 - 12.7 = 184.6` mm.

### Images

- Explicit positive pixel width converts at 96 DPI and clamps to printable width.
- Image without explicit width keeps natural size when it fits.
- Oversized natural image clamps to printable width.
- Natural-size probe failure falls back to existing `python-docx` insertion behavior.
- Existing missing/unreadable-image placeholder behavior stays unchanged.

### Tables

- Existing column-width extraction remains unchanged.
- When sum of specified column widths exceeds printable width, all specified widths scale by same ratio.
- Tables already within printable width keep original widths.
- Existing colspan, rowspan, cell rendering, and unspecified-width behavior stay unchanged.

## Data Flow

1. Editor save reaches `RteDocumentService.save_document()`.
2. Changed content increments revision and stores current default document settings.
3. Export merges stored settings over defaults.
4. Renderer calculates one printable-width limit.
5. Image and table writers clamp output against that limit.
6. Existing atomic temporary-file validation and replacement writes final DOCX.

## Failure Handling

- Word file locks still raise `DocxTargetLockedError`; previous DOCX remains untouched.
- Other export failures still remove temporary file and preserve source sidecar.
- No new retry, bridge, UI status, or persistence path.

## Verification

Automated checks extend `tests/test_phase_e_notes_persistence.py`:

- Defaults and page-setup fallbacks equal `12.7` mm.
- `content_width_mm(DEFAULT_DOCUMENT_SETTINGS)` is approximately `184.6` mm.
- Revision save replaces an old `20` mm sidecar settings object with current defaults.
- Real export with a `5000` px image produces image width no greater than `Mm(184.6)` plus small EMU tolerance.
- Real export with two `900` px table columns produces summed first-row `w:tcW` no greater than printable-width dxa plus rounding tolerance.
- Existing Phase E persistence suite remains green.

Required protocol checks:

```powershell
npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run check
npm --prefix D:/Ibrahim/Projects/project_tracker/frontend test
D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_phase_e_notes_persistence.py -v
npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run build
```

Build runs only after user confirms Project Tracker app is closed.

## Manual Acceptance Gate

Restart app from repo root, edit and save a DOCX containing an oversized image and wide table, wait for export, then open file in Word. Confirm:

- Word shows Narrow `12.7` mm margins.
- Image stays inside right margin.
- Table stays inside right margin.
- Existing text and table content remain intact.
- App load, save, document switching, and titlebar navigation remain normal.

Commit Step 5a only after user reports this gate passed.
