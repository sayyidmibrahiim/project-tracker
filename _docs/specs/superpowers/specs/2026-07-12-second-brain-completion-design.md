# Second Brain Completion Design

**Status:** Approved by user on 2026-07-12  
**Menu:** Second Brain  
**Branch:** `second-brain/complete-menu`

## 1. Goal

Finish Second Brain as a production-ready local knowledge workspace with two tabs:

1. **Notes** — browse and edit Personal Notes plus operational Project Documents.
2. **Link Bank** — maintain categorized, searchable, import/export-ready links.

The finished menu must use real filesystem data, preserve local-first safety, work from 960×640 through 1920×1080, and remove the current fake/placeholder behavior.

## 2. Non-goals

- Cloud sync or multi-user collaboration.
- OCR or PDF-content indexing.
- Embedded web browser.
- CICD repository search; CICD has its own menu.
- Hard delete.
- A new editor, copied editor, or Second-Brain-specific editor fork.
- Knowledge graph/database as canonical content storage.
- Changes to `NotesEditor.svelte`, `frontend/src/lib/extensions/*`, or `frontend/src/lib/markdown.ts` without a separate approval round.

## 3. Sources of truth

- `PRD.md` §§13, 14, 21.9, 21.10, 26.4.
- `_docs/DESIGN_RULES.md`.
- `_docs/ARCHITECTURE.md`.
- `_docs/DECISIONS.md`, especially D-0005, D-0007, D-0011, D-0012, D-0015, D-0016.
- `PRODUCT.md` and `DESIGN.md` loaded through the Impeccable product register.
- User-approved decisions captured in this document.

Implemented decisions beat `_reference/` and old PRD shell details. The current single page header and TitleBar clock remain authoritative.

## 4. Approved product decisions

### 4.1 Personal Notes location

- When `second_brain_folder` is empty, startup creates and stores:
  `Documents\Project Tracker\Second Brain`.
- Settings keeps an optional folder override.
- Adopting the default never relocates an existing configured override. Existing
  D-0016 whole-root migration semantics still apply when that override already
  lives inside a root folder being migrated.
- A missing override is surfaced as an error; the app does not silently fall back.

### 4.2 Editor parity

- Second Brain imports and mounts the existing `NotesEditor.svelte` directly.
- No copy, fork, alternate toolbar, or reduced behavior is allowed.
- Autosave, formatting, images, DOCX pipeline, zoom, fullscreen, shortcuts, status, revision handling, and read-only behavior remain the Project Details implementation.
- If reuse proves impossible with the existing public props, implementation stops for user approval rather than changing the editor.

### 4.3 Project Documents behavior

- Supported files mirror Project Details capability and project-lock behavior.
- Editable capability edits the original project file.
- Locked projects mount the same editor read-only.
- Unsupported formats show metadata and `Open externally`.
- No copies are created.

### 4.4 Project Documents scope

- Include all user files inside CR, Non-CR, and Drone project trees.
- Exclude all CICD content.
- Exclude the resolved Personal Notes folder from Project Documents even when
  the default or override is located inside the fixed project root, preventing
  the same file from appearing under both sources.
- Exclude app-owned/internal content, including:
  - `.git/`
  - `.rte/`
  - hidden files and hidden directories
  - `project_data.json`
  - `appcode.json`
  - `.project_tracker_index.json`
  - other explicit app metadata/sidecar names introduced by this feature
- `notes.md` and other user-facing content remain visible even when initially created by the app.

### 4.5 Link Bank formats

- Export supports JSON and CSV.
- Import supports JSON and CSV.
- Every import uses parse, validation, preview, conflict summary, confirmation, then atomic merge.
- Import never overwrites the entire bank without confirmation.

## 5. Design direction

**Direction:** Explorer-first Red Binder workspace.

- Dark chrome remains only in TitleBar.
- Workspace remains white.
- DBS red marks active selection and primary action only.
- Flat borders provide structure; permanent card shadows and nested cards are removed.
- Typography uses existing Inter/Segoe UI/Arial tokens only.
- Motion communicates state in 150–200 ms and respects reduced motion.

The signature element is the **source ribbon** above the editor. It encodes whether the selected file is Personal or Project content, its breadcrumb, capability, file type, and project lock. It is functional dossier metadata, not decoration.

## 6. Information architecture

### 6.1 Page shell

```text
Second Brain                         [Notes] [Link Bank] [Refresh]
────────────────────────────────────────────────────────────────
active tab workspace fills remaining window height
```

- `Notes` is the initial tab.
- The active tab may persist for the current app session only.
- Clock remains in TitleBar; it is not duplicated.

### 6.2 Notes tab

```text
┌──────────────────────────┬───────────────────────────────────────────────┐
│ Search · Date · Sort     │ Source ribbon                                │
│ Add folder · Add file    │ Source · breadcrumb · type · capability      │
├──────────────────────────┤ Pin · Favorite · Open externally · lock      │
│ Search Results           ├───────────────────────────────────────────────┤
│ Pinned                   │                                               │
│ Favorites                │ Existing NotesEditor.svelte                   │
│ Personal Notes           │ with Project Details behavior                 │
│ Project Documents        │                                               │
│  Appcode                 │                                               │
│   Year                   ├───────────────────────────────────────────────┤
│    Project / Drone       │ Related Notes | Recent Activity               │
└──────────────────────────┴───────────────────────────────────────────────┘
```

- Explorer width: `clamp(260px, 24vw, 340px)`.
- Tree uses actual folders and expandable hierarchy.
- Search Results exists only while search is active.
- Pinned and Favorites are aliases to canonical tree items.
- Related Notes and Recent Activity live in a collapsible context shelf below the editor.
- The source ribbon exposes tag chips and an inline tag editor. These tags are
  Second Brain metadata; editing them does not modify document content.

### 6.3 Link Bank tab

```text
┌ Categories ┬──────────── Link workspace ────────────────┐
│ Search     │ Search · Date · Sort · Add · Import/Export│
│ Pinned     ├──────────────────┬─────────────────────────┤
│ Favorites  │ Compact link list│ Selected link / form    │
│ Categories │                  │ URL, tags, description  │
│ Archived   │                  │ Copy, Edit, Archive     │
└────────────┴──────────────────┴─────────────────────────┘
```

- Add and Edit reuse the detail pane instead of opening a modal.
- Category rows show link counts.
- Archived categories and links have Restore actions.
- Hard delete is unavailable.

## 7. Component boundaries

```text
SecondBrain.svelte
├─ SecondBrainNotes.svelte
│  └─ NotesEditor.svelte (existing, unchanged)
└─ LinkBank.svelte
```

- `SecondBrain.svelte`: page header, tabs, active-tab refresh routing.
- `SecondBrainNotes.svelte`: explorer, filters, selection, source ribbon, related notes, activity.
- `LinkBank.svelte`: category rail, list, detail/form, archive/restore, import/export.
- Recursive tree rendering stays local to `SecondBrainNotes.svelte`; no one-use shared abstraction is added.
- DTOs remain in `frontend/src/lib/types.ts`.

## 8. Persistence and ownership

| Data | Canonical store | Notes |
| --- | --- | --- |
| Personal note content | Filesystem | Default or overridden Personal Notes folder |
| Project document content | Filesystem | Original project/Drone file |
| Pin/favorite/tags | `.project_tracker_index.json` | Atomic sidecar in Personal Notes folder; tags never rewrite document content |
| Link Bank | `%APPDATA%\ProjectTrackerDBS\link_bank.json` | Atomic JSON writes |
| Recent Activity | SQLite cache | Convenience history, capped and disposable |
| Search/tree index | Process memory | Rebuilt from filesystem |

Filesystem remains canonical. SQLite never becomes required to recover notes, project documents, or links.

## 9. Notes index

The in-memory index records:

- stable item ID;
- title and filename;
- absolute and relative path;
- parent/folder hierarchy;
- Personal or Project source;
- appcode, year, project, and Drone context when applicable;
- modified timestamp;
- file type and open mode;
- project state/lock and editor capability;
- pin, favorite, and tags;
- searchable text for safe text files;
- read/index warnings.

Text content is indexed only when safely readable and below a bounded size. Binary or oversized files remain searchable by filename and path. One unreadable file produces a warning entry and does not fail the complete index.

Eligible text files are indexed in full rather than using the current
200-character excerpt as editor or search content. The excerpt remains display
data only. Opening a file always loads its complete content through the same RTE
bridge used by Project Details.

The index is invalidated after create, rename, save, recycle, metadata update, or manual refresh.

## 10. Search and related notes

### 10.1 Search

- Frontend debounce: 150 ms.
- Search fields: title, filename, path, content, tags, and context.
- Filters: date, type, source.
- Sort: newest, oldest, A–Z, type.
- Clearing search restores the normal tree without discarding a still-valid selection.

### 10.2 Related Notes

Results are derived from:

1. wiki references such as `[[NoteTitle.md]]`;
2. shared tags;
3. same project or Drone context.

Every related result states its reason. Clicking it uses the normal flush-before-switch flow.

## 11. Editor selection contract

Switching files mirrors Project Details:

```text
select path
  → set interaction lock
  → await current NotesEditor.flushNow()
  → abort switch when flush returns false
  → clear stale payload
  → load DOCX with rte_document_open, other supported files with get_rte_file
  → ignore stale async result when selection changed
  → mount NotesEditor with {#key path} and Project Details-equivalent props
  → release interaction lock
```

This prevents content from file A appearing or saving under file B.

The existing `onSaved` callback records an edit activity and invalidates the
Second Brain index for the saved path. This keeps content search current even
though NotesEditor writes through the shared RTE bridge rather than through the
Second Brain service.

## 12. Personal Notes operations

- Add file defaults to `.md`, then immediately selects the created file.
- Add folder creates below the selected Personal folder, or at Personal Notes root when no folder is selected.
- Create and rename are inline.
- Enter commits; Escape cancels; F2 renames.
- Name validation rejects empty values, Windows reserved names, separators, traversal, and duplicates.
- Rename updates descendant paths and transfers sidecar metadata to the new stable IDs.
- Delete is Personal Notes only and uses Recycle Bin through `send2trash`.
- Project Documents cannot be renamed or deleted from Second Brain.

## 13. Open modes

| State | UI |
| --- | --- |
| `.md` editable capability | Full existing NotesEditor in Markdown mode |
| `.txt`, `.py`, `.sh`, `.ps1`, `.sql`, `.json`, `.csv`, `.log`, `.yml`, `.yaml`, `.xml`, `.toml`, `.ini`, `.cfg`, `.env`, `.ts`, `.js`, `.html`, `.css` editable capability | Existing NotesEditor in plain-text mode |
| `.docx` editable capability | Existing NotesEditor with D-0012 DOCX pipeline |
| Read-only/locked | Existing NotesEditor in read-only mode with visible reason |
| `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp` | Inline preview, metadata, Open externally |
| Unsupported | Metadata, reason, Open externally |
| Missing after indexing | Close selected state, refresh tree, explanatory toast |

## 14. Recent Activity

Recorded actions:

- opened;
- created;
- edited;
- renamed;
- recycled;
- opened externally.

Rows are newest-first. Repeated opens are deduplicated. Storage is capped. Missing targets remain visible but disabled rather than causing an error.

## 15. Link Bank behavior

### 15.1 Data

Each link has:

- stable ID;
- title;
- `http` or `https` URL;
- category;
- free-form tags;
- description;
- pin/favorite/archive state;
- created and updated timestamps.

Active and archived categories remain separately restorable. Legacy link rows normalize on read without losing stable IDs.

### 15.2 User flows

- Category selection filters the link list.
- Link selection fills the detail pane.
- Add switches the detail pane to an empty form.
- Edit switches the same pane to an edit form.
- Copy URL produces a toast.
- Open URL uses the default OS browser.
- Archive link/category requires confirmation and never hard-deletes.
- Archived items can be restored.
- Search covers title, URL, category, tags, and description.
- Date filters use `updated_at`; sort supports newest, oldest, A–Z, favorite,
  and pinned.

### 15.3 Import/export

- JSON retains every field and is the preferred backup format.
- CSV supports Excel bulk editing.
- Import flow: choose → parse → validate → preview add/update/conflict/invalid counts → confirm → atomic merge.
- Invalid input produces no write.
- Export uses the native save dialog.

Merge identity is deterministic:

- matching stable link ID updates that link;
- a missing/new ID with a unique normalized URL adds a link;
- the same normalized URL under a different ID is reported as a conflict and is
  skipped rather than overwritten;
- category names merge case-insensitively while preserving existing spelling;
- invalid rows are never written, while valid rows may be merged only after the
  preview explicitly reports the skipped rows.

CSV uses explicit headers for `id`, `name`, `url`, `category`, `tags`,
`description`, `pinned`, `favorite`, `archived`, `created_at`, and `updated_at`.

## 16. Responsive behavior

| Window | Behavior |
| --- | --- |
| 960×640 | Explorer 260 px; editor owns remaining width; Link list/detail stack vertically |
| 1024×768 | Same structure; command bars wrap without clipped actions |
| 1280×720 | Link list/detail display side-by-side |
| 1920×1080 | Explorer reaches 340 px; context shelf can show Related and Activity side-by-side |

Each panel owns its scroll. The app body never gains horizontal overflow.

## 17. Accessibility and control states

- Tree rows, tabs, context shelf, and actions have keyboard paths and visible focus.
- Ctrl+F focuses Notes search while the menu is active.
- Color is never the only state indicator.
- Disabled actions show a reason.
- Mutation controls expose default, hover, focus, active, disabled, loading, success, and error behavior.
- Duplicate mutations are disabled while a request is active.
- Reduced-motion users receive instant state transitions.

## 18. Error handling

- Missing/unreadable override: keep the configured path visible and offer `Browse folder` plus `Use default folder`.
- Partial index failure: render available data and show the failed-file count.
- Save/DOCX errors: existing NotesEditor behavior remains authoritative.
- Link import validation failure: no write.
- Link merge/write failure: prior file remains intact through atomic write.
- Empty states explain the next action.
- Loading uses skeleton rows rather than a lone center spinner.

## 19. Proposed bridge surface

Existing RTE and external-open bridges remain reused. Second Brain bridge methods may be expanded to cover:

- tree/list and filtered search;
- selection metadata and related notes;
- guarded image-preview reads;
- Personal folder/file create, rename, recycle;
- pin/favorite/tags;
- activity list/record;
- Link Bank category restore and link restore;
- JSON/CSV import preview and confirmed merge;
- JSON/CSV export payload generation.

Every method returns the standard `{ok, data, error}` contract. Business and filesystem rules remain in Python services, not Svelte.

## 20. Automated verification

- Default folder creation without moving an existing override.
- Personal and Project hierarchy.
- CICD/internal/metadata exclusion.
- Full-content search without the current 200-character truncation.
- Title/path/content/tags/date/source/type search.
- Project state lock and capability mapping.
- Flush-before-switch and stale-load guards.
- Personal CRUD, traversal/name guards, atomic writes, Recycle Bin.
- Pin/favorite/tags persistence across restart and rename.
- Related-note ranking.
- Activity append, dedupe, and cap.
- Link/category CRUD, archive/restore, timestamps.
- JSON/CSV parse, validation, preview, merge, conflict, and rollback.
- Bridge response contracts.
- Frontend interaction/source contracts.
- Targeted backend/frontend tests, `svelte-check`, Python compile, and `git diff --check`.
- App runtime smoke from repository root.

Full test suite is not the default and runs only when explicitly requested.

## 21. Manual checklist draft

### Notes

- [ ] Fresh empty setting creates and uses the default Personal Notes folder.
- [ ] Existing override remains unchanged.
- [ ] Tree shows Personal Notes and Project Documents hierarchy.
- [ ] CICD and app metadata never appear.
- [ ] Search covers title, path, full content, and tags.
- [ ] Date, type, source, and sort controls work.
- [ ] Create file/folder, inline rename, validation, and Recycle Bin work.
- [ ] Pin/Favorite aliases open the canonical item.
- [ ] Related and Activity rows open valid targets.
- [ ] Image preview and unsupported external-open work.

### NotesEditor parity

- [ ] Toolbar and formatting match Project Details.
- [ ] Autosave/status, undo/redo, links, images, tables, zoom, and fullscreen match.
- [ ] DOCX migration/export and revision handling match.
- [ ] Read-only lock matches.
- [ ] File switch flushes first and blocks on save failure.

### Link Bank

- [ ] Category/link add, edit, search, pin, favorite, archive, and restore persist.
- [ ] Copy and OS-browser open work.
- [ ] JSON and CSV export work.
- [ ] JSON and CSV import preview, conflict summary, confirmation, and atomic merge work.
- [ ] Empty, loading, validation, and failure states are actionable.

### Responsive and accessibility

- [ ] 960×640, 1024×768, 1280×720, and 1920×1080 remain usable.
- [ ] Panel-owned scrolling prevents body overflow.
- [ ] Keyboard navigation and focus indicators work.
- [ ] Buttons expose default, hover, active, disabled, loading, and error states.
- [ ] Colors and typography match the existing design tokens.

## 22. Build and live-test guard

- Do not run the production frontend build while Project Tracker is open.
- After a build, restart the app before manual verification because `web/static` is gitignored and does not follow branch switches.
- Automated checks do not prove NotesEditor interaction parity; live user verification remains required.
