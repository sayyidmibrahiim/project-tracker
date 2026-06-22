# Project Details & Header Polish — Design Spec

**Date:** 2026-06-22
**Scope owner:** Sayyid Ibrahim
**Applies to:** Project Details menu only.

## Goal

Fix layout/behavior issues in Project Details and polish Header for Notion-like productivity feel.

## Changes

### 1. Project Command Center

1.1 **Restore Sub Project dropdown** in the Command Center toolbar. Add `<select id="pd-subproject-select">` with `bind:value={selectedSubproject}` and `disabled` logic matching previous implementation. Place it after the Project dropdown.

1.2 **Remove subtitle text** `compact editing workspace`.

1.3 **Move Back to Dashboard button** into the Command Center toolbar. Place it at the far left, before the Project dropdown. Remove the standalone `.pd-back-bar` wrapper above the panel.

Layout: `[← Back] [Project ▾] [Sub Project ▾] ... [Open] [Delete]`

### 2. Project Identity

2.1 **Remove CR Number display row** (`<div class="pd-dl-item"><dt>CR Number</dt>...</div>`).

2.2 **Rename "CR Link" label to "CR Number"** on both input mode and display mode.

2.3 **CR State dropdown inline (horizontal) with CR Number field.** Wrap CR Number (input/display) and CR State `<select>` in a single `.pd-meta-datetime-row` grid so they sit side-by-side.

### 3. Sub Project Table

3.1 **Columns:** `Sub Project | Drone Ticket | Drone State` (match Dashboard parity).

3.2 **Remove Actions column.** No "Open Folder" button.

3.3 **Row click opens folder.** Clicking a sub-project name triggers `onOpenFolder(name)` → bridge `folder_open`.

### 4. Notes WYSIWYG & Checklist

4.1 **Debounced markdown sync.** Remove `syncToMarkdown()` from `onEditorInput`. Only convert HTML→Markdown on: (a) autosave debounce timer fire, (b) editor blur. This prevents cursor jump during formatting/typing.

4.2 **execCommand formatting preserved.** Toolbar buttons use `onmousedown preventDefault` + `document.execCommand`. Bold/Italic/etc format live text and selection natively (MS Word behavior).

4.3 **Checklist bug fix.** Ensure `.ne-todo-item` renders inside the contenteditable area, not outside. Fix `formatChecklist()` to insert at caret position within the editor div.

### 5. Header Polish

5.1 **Calendar icon.** Replace `.datetime-glyph` clock glyph with inline SVG calendar icon (rectangle + grid lines).

5.2 **Button polish.** Update `.btn-black`, `.refresh-button`, `.search-shell` styles: thinner borders, white background, subtle hover (red DBS accent), minimal shadow. Notion-like clean.

## Testing

- Update `project-details-fase1.test.mjs` and `project-details-fase3-fase4.test.mjs` assertions for layout changes (Sub Project dropdown restored, Back button in toolbar, CR Number label).
- Run `npm test` and `npm run check` after each task.
- Manual smoke test checklist at end.
