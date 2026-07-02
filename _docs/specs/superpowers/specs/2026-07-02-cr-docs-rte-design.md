# Piece B Design — _cr-docs Editable Files + Multi-file RTE Editor

**Date:** 2026-07-02
**Author:** Sayyid M. Ibrahim
**Branch:** `project-details/cr-docs-rte` (branch from `main` after Piece A merge)
**Status:** Approved (pending implementation)
**Dependencies:** Piece A (folder structure + _cr-docs/ created empty for CR projects)

---

## Context

Piece A created `_cr-docs/` as an empty folder inside each CR project. Piece B fills it with editable rich-text documents and adds a multi-file RTE dropdown to Project Details.

## Scope

1. Create `uat-signoff` and `prod-lv` as empty HTML files on CR project creation (only CR projects, not Non-CR)
2. RTE dropdown in Project Details — context-sensitive file selector
3. Reuse existing Tiptap v3 editor (NotesEditor) for editing these files
4. `.msg` files are NOT editable — they appear in dropdown but open externally (Piece C downloads them)

## Section 1: File Format & Creation

### Format: HTML (Tiptap native)

Files stored as HTML strings — Tiptap's native format. This preserves:
- Images (base64 data URI via existing `util_choose_image` bridge)
- Clickable links (Tiptap link extension)
- Tables, font sizes, all ProseMirror marks
- No Markdown roundtrip loss

File names: `uat-signoff` and `prod-lv` (no extension, HTML content inside).

### Creation timing

On CR project creation (Piece A's `create_project` with `project_type=CR`):
- `_cr-docs/` already created by Piece A
- Piece B adds: `_cr-docs/uat-signoff` (empty, 0 bytes) + `_cr-docs/prod-lv` (empty, 0 bytes)
- Non-CR projects: no `_cr-docs/`, no these files

### The 4 files in `_cr-docs/`

| File | Format | Created by | Editable in RTE? |
|------|--------|-----------|-----------------|
| `uat-signoff` | HTML | Piece B (on project creation) | Yes — Tiptap editor |
| `prod-lv` | HTML | Piece B (on project creation) | Yes — Tiptap editor |
| `uat-approval.msg` | Outlook .msg | Piece C (auto-download reply) | No — open externally |
| `prod-approval.msg` | Outlook .msg | Piece C (auto-download reply) | No — open externally |

---

## Section 2: RTE Dropdown — Context-Sensitive File Selector

### Project level (viewing project folder)

Dropdown shows all files in the project folder:
- `notes.md` (project notes)
- `_cr-docs/uat-signoff` (if CR project)
- `_cr-docs/prod-lv` (if CR project)
- `_cr-docs/*.msg` (if exist — from Piece C)
- Any other files in the project folder

### Drone level (viewing a drone folder)

Dropdown shows all files in the drone folder:
- `notes.md` (drone's own notes)
- Any other files in the drone folder

### Behavior

- Selecting a file from dropdown loads its content into the Tiptap editor
- For HTML files (uat-signoff, prod-lv): load HTML directly into Tiptap `editor.commands.setContent(html)`
- For Markdown files (notes.md): existing Markdown→HTML conversion (markdown.ts layer)
- For `.msg` files: do NOT load in editor — show "Open externally" button instead
- For unknown file types: show as text or "Open externally"
- Saving: reverse — Tiptap HTML → save to file (HTML files save as HTML, notes.md saves as Markdown via domToMarkdown)

### Bridge methods (new)

```python
def get_rte_file(self, file_path: str) -> object:
    """Read a file for RTE editing. Returns {content, format, editable}."""
    # format: "html" | "markdown" | "msg" | "text"
    # editable: bool

def save_rte_file(self, file_path: str, content: str) -> object:
    """Save RTE content back to file."""
```

### Frontend changes

- `ProjectDetails.svelte`: add file dropdown next to RTE toolbar
- `NotesEditor.svelte`: accept `filePath` + `fileFormat` props, load/save based on format
- `bridge.ts`: add `get_rte_file` + `save_rte_file` wrappers

---

## Section 3: Project Creation Update

Update `app_web.py` `create_project` for CR type to also create the 2 empty files:

```python
# After _cr-docs/ mkdir:
(project_dir / "_cr-docs" / "uat-signoff").touch()  # empty HTML
(project_dir / "_cr-docs" / "prod-lv").touch()      # empty HTML
```

---

## Section 4: Error Handling & Edge Cases

| Edge case | Handling |
|-----------|----------|
| File not found in dropdown | Bridge returns error, dropdown shows "File not found" |
| Corrupt HTML in uat-signoff | Tiptap renders what it can, logs warning |
| .msg file selected | Show "This is an Outlook message. Open externally?" with button |
| File deleted while editing | Save fails with "File no longer exists" error |
| Non-CR project | Dropdown doesn't show _cr-docs files (folder doesn't exist) |
| Empty file (0 bytes) | Editor shows empty state — user can start typing |

---

## Section 5: Testing

### New test files
- `tests/test_cr_docs_creation.py` — verify uat-signoff + prod-lv created on CR project creation
- `tests/test_rte_file_bridge.py` — get_rte_file/save_rte_file for HTML, Markdown, .msg formats

### Manual checklist
- Create CR project → verify _cr-docs/ has uat-signoff + prod-lv (empty)
- Open Project Details → RTE dropdown shows notes.md + uat-signoff + prod-lv
- Select uat-signoff → type text + insert image + add link → save → reopen → content preserved
- Select notes.md → existing behavior unchanged
- Create Non-CR project → verify no _cr-docs/ folder
- Open drone → dropdown shows drone/notes.md only

---

## UI/UX Design (Piece B)

### RTE File Dropdown Position

Dropdown is in the **RTE toolbar**, leftmost position, before format buttons:
`
[notes.md v]  [B][I][H1][H2][Code][Link]...
`

- Shows current file name (e.g. notes.md, uat-signoff, prod-lv)
- Click to see list of files in active folder context
- Selecting a file loads it into the Tiptap editor
- .msg files show in dropdown but selecting them shows Open Externally button instead of editor

### Context Sensitivity

- **Project level**: dropdown lists notes.md + _cr-docs/uat-signoff + _cr-docs/prod-lv + _cr-docs/*.msg (if exist) + other files in project folder
- **Drone level**: dropdown lists drone/notes.md + other files in drone folder

### .msg File Handling

When .msg file selected from dropdown:
- Editor area shows: This is an Outlook message. [Open Externally]
- Button opens file with os.startfile (default Windows app)

## Out of Scope

- `.msg` file auto-download (Piece C — approval automation)
- Email polling (Piece C)
- Approval buttons (Piece C)
