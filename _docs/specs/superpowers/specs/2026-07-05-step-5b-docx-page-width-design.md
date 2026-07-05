# Step 5b DOCX Page Width Design

## Goal

Show DOCX content at fixed printable-page width in editor while leaving Markdown and text editors responsive.

## Scope

- Change production behavior only in `frontend/src/lib/components/NotesEditor.svelte`.
- Add focused source-contract coverage to existing `frontend/tests/project-details-fase3-fase4.test.mjs`.
- Keep Step 5c image drag-resize out of this round.
- Add no backend, Markdown serialization, extension, dependency, or state changes.

## Layout

Editor host receives `class:ne-docx-page={docxPipelineMode}`. Class exists only while active file uses DOCX pipeline.

DOCX host uses horizontal overflow. Mounted `.ne-textarea` uses fixed `720px` border-box width, no responsive maximum, and centered auto margins.

Width calculation:

- Printable A4 width from Step 5a: `184.6mm`.
- At `96dpi`: approximately `698px`.
- Existing editor padding: `10px` each side.
- Existing border: `1px` each side.
- Total border-box width: `698 + 20 + 2 = 720px`.

Code comment records calculation beside CSS to prevent unexplained drift.

## Responsive Behavior

- Host wider than `720px`: page stays centered.
- Host narrower than `720px`: page keeps exact width and host scrolls horizontally.
- DOCX fullscreen: page remains centered at `720px`; existing fullscreen height logic remains unchanged.
- Markdown and text modes retain current `width:100%` behavior.

## Data and Failure Behavior

No data flow changes. Save, load, export, revision, interaction-lock, and editor lifecycle paths remain untouched.

CSS has no new error state. Existing editor fallback and status behavior remain unchanged.

## Verification

Existing source-contract test file asserts:

- Host has `class:ne-docx-page={docxPipelineMode}`.
- DOCX selector is scoped through `.ne-editor-host.ne-docx-page`.
- DOCX host uses `overflow-x:auto`.
- DOCX textarea uses `width:720px`, `max-width:none`, `margin:0 auto`, and `box-sizing:border-box`.
- Base textarea keeps `width:100%` for non-DOCX modes.

Required automated checks:

```powershell
npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run check
npm --prefix D:/Ibrahim/Projects/project_tracker/frontend test
npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run build
```

Build runs only after user confirms Project Tracker app is closed.

## Manual Acceptance Gate

After restart:

1. Open editable DOCX and confirm fixed page is centered.
2. At narrow window, confirm horizontal scroll appears and page does not shrink.
3. At medium and maximized windows, confirm page stays centered.
4. Confirm a `100%` table fills editor printable width and matches Word output width.
5. Open `notes.md` and `.txt`; confirm editor still fills available width with no forced `720px` page.
6. Confirm typing, save, DOCX export countdown, file switching, fullscreen, and titlebar navigation remain normal.

Commit Step 5b only after user reports this gate passed.
