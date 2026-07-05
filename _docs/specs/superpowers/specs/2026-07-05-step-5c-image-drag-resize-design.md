# Step 5c Image Drag-Resize Design

## Goal

Add drag-resize for rich-editor images in `.docx` pipeline documents and `notes.md`, with persisted pixel width after save, file switch, app restart, and DOCX export. Keep `.txt` unchanged because it is plain text and has no image editor surface.

## Scope

- One RTE behavior round only: image drag-resize.
- Target branch: `project-details/tiptap-docx-pipeline`.
- Runtime files in scope:
  - `frontend/src/lib/extensions/AssetImage.ts`
  - `frontend/src/lib/markdown.ts`
  - `frontend/src/lib/components/NotesEditor.svelte`
- Test files in scope:
  - `frontend/tests/markdown.test.ts`
  - `frontend/tests/project-details-fase3-fase4.test.mjs`
- No backend changes. Step 5a already clamps exported image width to printable page width.
- No table changes. Existing Tiptap table column resize remains as-is.

## User Behavior

When the editor displays an image in `.docx` or `notes.md`, hovering or selecting the image shows a small red resize handle at the bottom-right corner. Dragging the handle previews the image width live. Releasing the mouse writes a positive integer `width` attribute into the image node.

Minimum image width is `40px`. There is no new maximum in the editor because Step 5a clamps export output. The editor still uses `max-width:100%` so oversized images do not visually escape the editor surface.

The persisted width survives:

- autosave and reload,
- switching CR docs,
- app restart,
- DOCX source JSON save/export,
- `notes.md` Markdown round-trip.

## Architecture

Use a minimal Tiptap NodeView inside `AssetImage.ts`. This is the smallest correct seam because the drag handle must be attached to the image node and must update ProseMirror node attributes. A CSS-only resize is rejected because it cannot persist width. A wrapper managed by `NotesEditor.svelte` is rejected because it would duplicate Tiptap node lifecycle work.

`AssetImage` extends the existing image node with one extra attribute:

- `width`: `number | null`, parsed from an HTML `width` attribute only when it is a positive integer.

NodeView output:

```html
<span class="ne-img-wrap">
  <img ... />
  <span class="ne-img-handle"></span>
</span>
```

The NodeView keeps the current ProseMirror node reference, applies `src`, `alt`, `data-asset-id`, `data-asset-src`, and `style.width`, and returns `false` only when the updated node type differs.

Dragging the handle:

1. stops default selection behavior,
2. records the image bounding width and starting mouse X,
3. previews `img.style.width = "<next>px"` during `mousemove`,
4. on `mouseup`, dispatches `editor.view.state.tr.setNodeMarkup(getPos(), undefined, { ...current.attrs, width: next })`,
5. removes document-level mouse listeners.

The handle is appended only when `editor.isEditable` is true. Read-only documents still display persisted width, but do not show a resize control.

## Markdown Contract

`markdown.ts` keeps the current compact Markdown image syntax when no width exists:

```md
![shot](.rte/assets/ab12cd34ef56ab78.png)
```

When a width exists, Markdown syntax cannot represent it, so serialization uses sanitized inline HTML:

```html
<img src=".rte/assets/ab12cd34ef56ab78.png" alt="shot" width="240" />
```

Rules:

- `TAG_ATTRS.img` allows `width`.
- `renderMarkdown()` preserves sanitized `width` on whitelisted `<img>` HTML.
- `htmlToMarkdown()` serializes a DOM image with valid width to inline HTML.
- `htmlToMarkdown()` serializes an image without width to existing Markdown image syntax.
- `fallbackHtmlToMarkdown()` follows the same width rule and restores width image HTML after stripping other tags.
- Source text must never contain a literal NUL byte. Placeholder tokens use the existing escaped `\u0000` string pattern.

## CSS

`NotesEditor.svelte` adds only image wrapper/handle CSS:

- `.ne-img-wrap`: inline-block positioned wrapper with `max-width:100%`.
- `.ne-img-wrap img`: block display with `max-width:100%`.
- `.ne-img-handle`: 11px red-bordered bottom-right handle, hidden by default.
- Hovered wrapper or selected node reveals the handle.

No toolbar, save, export, paste/drop, zoom, table, or backend behavior changes.

## Test Plan

Automated tests:

1. `markdown.test.ts`: `htmlToMarkdown()` converts a resized asset image to inline HTML with `src`, `alt`, and `width`.
2. `markdown.test.ts`: `renderMarkdown()` preserves an inline asset image `width`.
3. `markdown.test.ts`: images without width continue using existing Markdown image syntax.
4. `project-details-fase3-fase4.test.mjs`: `AssetImage.ts` exposes `width`, `addNodeView`, `.ne-img-handle`, `setNodeMarkup`, and `Math.max(40`.
5. `project-details-fase3-fase4.test.mjs`: `NotesEditor.svelte` contains the scoped image wrapper/handle CSS.

Required verification before user manual gate:

- Focused Step 5c tests red before implementation and green after implementation.
- `npm --prefix frontend run check`.
- `node --import ./frontend/tests/register-hooks.mjs --test ./frontend/tests/*.test.mjs`.
- Build only after the user confirms Project Tracker is closed.

Manual checklist:

- `.docx`: paste/drop image, hover handle, drag smaller/larger, save, switch file, reopen, confirm size persists.
- `.docx`: export after resize, confirm exported image respects resized width and Step 5a clamp.
- `notes.md`: insert asset image, resize, save, switch file, restart app, confirm size persists.
- `notes.md`: image without resize still round-trips as normal Markdown image.
- `.txt`: unchanged plain-text editor behavior.
- Regression: typing near images, selecting images, toolbar commands, zoom, fullscreen, table column resize, file switching, and titlebar navigation remain normal.

## Failure Handling

If manual testing reports abnormal editor behavior, do not commit implementation. Restore only uncommitted Step 5c files, rebuild baseline after the app is closed, record the symptom, and stop before Step 6.
