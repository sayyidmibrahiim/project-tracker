# Project Details UI — Fase 3: WYSIWYG Notes & Fase 4: Sub-project Detail View

**Status:** Approved design (pending implementation)
**Date:** 2026-06-22
**Scope owner:** Sayyid Ibrahim
**Origin review:** User feedback on Project Details UI/UX (review points 8.1, 8.2, 10, 11, 12)
**Phase:** 3 and 4 of 4 (Combined for unified execution)

## Goal

- **Fase 3 (WYSIWYG Notes & Checklist):** Replace the markdown editor's dual "Edit/Preview" tabs with a single, live, automatic WYSIWYG contenteditable editor. Format content on the fly (bold, italic, list, quotes, link, code) using native formatting commands, support Checklist checkboxes, and transparently compile back to standard Markdown for saving to disk.
- **Fase 4 (Sub-project Detail View & Inheritance):** Resolve backend path crashes by transitioning from `ProjectState(path.parent.name)` to ancestor-based state resolution. Extend `get_project` to recognize sub-projects, inherit dates/CR states from parent projects, disable date/CR editing and sub-project nesting on sub-project detail views, and customize sub-project notes.

---

## Design Specification — Fase 3: WYSIWYG Notes & Checklist

### 1. WYSIWYG Editor Component (`NotesEditor.svelte`)

- The `<textarea>` and `mode` (edit/preview toggle) are **removed**.
- Render a single `<div contenteditable="true" class="ne-editor-area" bind:this={editorEl}>` which displays rich-text formatting directly.
- Font is changed to clean proportional sans-serif (`Inter`, same as Notion) instead of monospace JetBrains/Fira.
- Styles are applied directly to paragraphs, lists, headers, and code tags inside the editor block.

### 2. Formatting Toolbar

Formatting buttons invoke direct selections and programmatic range wrapping:

- **Bold / Italic / Bullet List / Quote / Link**: Uses standard `document.execCommand` selectors (`bold`, `italic`, `insertUnorderedList`, `formatBlock` with `<blockquote>`, `createLink`).
- **Heading 1 / Heading 2**: Uses `document.execCommand('formatBlock', false, '<h1>')` and `<h2>`.
- **Inline Code**: Programmatically wraps the active selection range in a `<code>` node.
- **Checklist**: Inserts a checkbox line:
  `<div class="ne-todo-item"><input type="checkbox" class="ne-todo-checkbox" /> <span>Todo item</span></div>`
  We listen to checking/unchecking events on the checkbox to instantly sync and trigger autosave.

### 3. Markdown Round-Trip Conversion

To satisfy the backend constraint that notes must remain saved on disk as plain Markdown (`notes.md` / `Notes.md`), the editor converts formats bidirectionally:

- **Markdown to HTML (Editor Load):**
  Uses the existing XSS-safe `renderMarkdown(markdown)` in `markdown.ts` to generate safe HTML, which is then injected into the `contenteditable` div's `innerHTML` on mount and on project switch.
- **HTML to Markdown (Editor Autosave):**
  A new utility function `htmlToMarkdown(html: string): string` parses the `innerHTML` and translates tags back into plain markdown block sequences:
  - `<h1>text</h1>` -> `# text\n\n`
  - `<h2>text</h2>` -> `## text\n\n`
  - `<blockquote>text</blockquote>` -> `> text\n\n`
  - `<strong>text</strong>`, `<b>text</b>` -> `**text**`
  - `<em>text</em>`, `<i>text</i>` -> `*text*`
  - `<code>text</code>` -> `` `text` ``
  - `<ul><li>text</li></ul>` -> `- text\n`
  - Checkbox items:
    - `<input type="checkbox" /> text` -> `- [ ] text\n`
    - `<input type="checkbox" checked /> text` -> `- [x] text\n`
  - `<a href="url">text</a>` -> `[text](url)`
  - Inline spacing and line breaks are converted to clean double newlines.

---

## Design Specification — Fase 4: Sub-project Detail View & Inheritance

### 1. Backend Path Fixes (`project_tracker/app_web.py`)

To prevent `ValueError` crashes when loading detail views or executing mutations on sub-project folders (`year/STATE/parent/sub`), we change all occurrences of:
`project_state = ProjectState(path.parent.name)`
to:
`project_state = _folder_state_for_path(path) or ProjectState.UAT_PREPARE`

Locations modified:

- `get_project(self, project_path: Path)` (line 451)
- `update_cr_link(self, project_path: Path, cr_link: str)` (line 505)
- `update_cr_state(self, project_path: Path, ...)` (line 646)
- `update_project(self, project_path: Path, ...)` (line 700)
- `folder_reopen(self, project_path: Path)` (line 800)

### 2. Sub-project Recognition in `get_project`

A path is classified as a sub-project if its parent contains a `project_data.json` file.

```python
is_subproject = (path.parent / "project_data.json").is_file()
```

If `is_subproject` is true:

- We read the parent's `project_data.json` using `self._metadata_store.read(path.parent)`.
- We inherit CR details and dates from the parent:
  - `metadata.cr_link = parent_meta.cr_link`
  - `metadata.cr_state = parent_meta.cr_state`
  - `metadata.start_datetime = parent_meta.start_datetime`
  - `metadata.end_datetime = parent_meta.end_datetime`
- We set `subprojects_list = []` (sub-projects cannot contain nested sub-projects).
- Return `"is_subproject": True` in the returned dictionary.

### 3. Date / State Propagation in `update_project`

If a sub-project's dates or CR link are updated, they are propagated to the parent folder's metadata file (so the parent remains the single source of truth for dates/CRs).

### 4. UI Adjustments for Sub-project detail view (`ProjectDetails.svelte`)

When the loaded project has `"is_subproject": true`:

- **Disable / Read-only Fields:** Input fields for CR Link, Start datetime, and End datetime are disabled (or render as read-only labels). The CR State dropdown is disabled. A small label `(Inherited from Main Project)` is shown below these fields.
- **Hide nesting block:** The "Sub Project (DRONE)" section card is completely hidden.
- **Notes & Files remain editable:** Since notes read/write is path-agnostic, a sub-project automatically reads and writes to `subproject_folder/notes.md`, making its notes distinct from the parent's notes. Files are also listed and managed within `subproject_folder/`.

---

## Testing Strategy

1. **Verify WYSIWYG Notes:**
   - Test markdown conversion round-trip (`markdownToHtml` and `htmlToMarkdown`).
   - Verify checkboxes (`- [ ]`, `- [x]`) map correctly to Svelte checkbox states.
2. **Verify Sub-project Details:**
   - Test `get_project` on a sub-project path returns `is_subproject: true` and inherits parent dates.
   - Verify UI disables CR link, CR state, and dates, and hides the subproject table card when `is_subproject` is true.
3. **Run all tests** to ensure no regressions.
