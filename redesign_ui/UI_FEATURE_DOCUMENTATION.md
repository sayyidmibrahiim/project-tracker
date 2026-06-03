# Project Tracker DBS UI Feature Documentation

This document records the user-facing features, user flows, and expected behavior for the redesign UI prototypes. The `.py` files in `redesign_ui/` are UX reference only; current implementation target is HTML/Tailwind files in `frontend/` rendered through pywebview. It must be kept up to date whenever a feature is added, changed, or removed.

## Documentation Maintenance Rule

When any redesign UI feature changes, update this document in the same work session. This includes:

- new features
- removed features
- renamed actions, buttons, tabs, or panels
- changed user flow
- changed empty state or error state
- changed file handling behavior
- changed search behavior
- changed responsive layout behavior

If the UI prototype and this document disagree, the prototype is unfinished until the documentation is updated.

## Second Brain

Source prototype: `second_brain_redesign.py`

Second Brain is a personal knowledge workspace inside Project Tracker DBS. It combines notes, project documents, pinned/favorite flows, file discovery, indexed search, and reusable links.

### Main Navigation

Second Brain uses two main workspace tabs:

1. **Notes**
2. **Link Bank**

The tab header follows the Automation screen style. The header contains the workspace icon, title, subtitle, and pill-style tab buttons.

### Notes Workspace

The Notes workspace is split into two resizable panels.

#### Left Panel: Notes & Documents

The left panel helps the user find, organize, and review notes and files.

Main elements:

- indexed search field
- date filter with unclipped calendar icon/popup
- search sort dropdown
- search results shown inside the folder/file tree under **Search Results**
- filter chips
- folder and file actions with inline tree rename/edit
- template picker
- file type picker for `.md`, `.txt`, `.sh`, `.ps1`, `.py`, `.json`, `.sql`, and `.log`
- notes/documents tree with **Pinned**, **Favorites**, **Second Brain Notes**, and **Project Documents** roots
- visible tree border and compact VS Code-like rows

#### Right Panel: Editor, Related Notes, and Activity

The right panel is for writing, previewing, and reviewing note context.

Main elements:

- note metadata fields
- editor/preview content box
- always-visible document state indicator
- editor mode toolbar with **Pin** and **Favorite** on the right side
- markdown toolbar
- related notes/backlinks panel
- recent activity panel

### Quick Capture Removed

Quick Capture is removed from this prototype. Notes are opened, pinned, favorited, searched, and edited through the normal Notes tree and editor flow.

Prototype actions:

- **Add Folder** creates a root folder when no tree item is selected.
- **Add Folder** creates a child folder when a tree item is selected.
- **Add File** creates a new file using the selected file type and immediately starts inline rename/edit in the tree.
- Clicking empty tree area clears selection.

### Template Picker

Template Picker helps create common note types quickly.

Available prototype templates:

- Meeting Note
- UAT Checklist
- Release Playbook
- Incident Notes

User flow:

1. User clicks **Note** or opens the template picker.
2. User selects a template.
3. Editor is expected to load starter markdown content.
4. User edits and saves as a markdown note.

Prototype behavior:

- visual-only dropdown
- no template insertion yet

Production intent:

- insert predefined markdown structure
- keep templates local-first
- allow future user-managed templates if approved

### Pinned and Favorite Notes

Pinned notes provide quick access to important daily documents.

Prototype pinned/favorite items:

- Deployment Evidence Follow-up
- UAT Screenshot Request
- Release Board Cleanup
- UAT Checklist

User flow:

1. User clicks a pinned/favorite tree item.
2. The note opens in the editor.
3. User clicks **Pin** or **Favorite** from the right side of the editor toolbar.
4. The visible status label confirms the tested flow.
5. Pinned/favorite indicators remain visible in the tree.

Production intent:

- store favorite/pinned status in local settings or note metadata
- keep pinned/favorite notes visible in tree groups without crowding search controls
- keep flow testable with explicit status feedback

### Search Result Mode

Search should be fast, case-insensitive, date-filterable, sortable, and pattern-based.

When the user types in the search field or changes the date filter, the UI shows clickable file results directly inside the folder/file tree under **Search Results**.

Result item types:

- editable notes
- previewable text-like documents
- non-previewable documents that open with the Windows default app
- links or link-related file contexts when available

Search should match:

- note title and body/content
- document name, path, and text-like content
- tags
- links
- path
- any partial pattern

User flow:

1. User types a partial search pattern.
2. User clicks the date filter and chooses a date from the unclipped popup calendar.
3. User chooses sort order when needed.
4. Matching files appear under **Search Results** in the normal folder/file tree.
5. User clicks a tree result.
6. Editable or previewable content opens in the editor/preview panel.
7. Unsupported files show the intended **open with default app** flow.

Prototype behavior:

- popup calendar sets `YYYYMMDD` date filter
- sort dropdown supports modified/title ascending and descending order
- indexed/pattern search preview text updates as query/date/sort changes
- tree result items can be clicked
- no real filesystem scan yet
- default-app opening is status/preview text only

Production intent:

- use an in-memory precomputed index
- normalize searchable text with `.casefold()`
- include searchable document/link content where safe and practical
- do not rescan filesystem on each keystroke
- debounce search input around 100-200ms if needed

### Notes and Documents Tree

The tree shows both Second Brain notes and project documents.

Prototype groups:

- Search Results (visible only when query/date filter is active)
- Pinned
- Favorites
- Second Brain Notes
- Project Documents

Example files shown:

- `.md` notes
- `.xlsx` spreadsheet
- `.pdf` document
- `.png` image
- `.sql` script
- `.zip` archive

Expected file behavior:

- Markdown notes are editable in-app.
- Text-like files can be displayed or edited in-app if safe.
- Images are preview-only if the app can display them.
- Unsupported file types open with the Windows default application.

### Editor and Preview

The editor uses one main content box.

Modes:

- **Edit** — content box is editable.
- **Preview** — same content box becomes read-only and shows preview-style content.

User flow:

1. User selects a note.
2. Note metadata appears above the editor.
3. User edits content in Edit mode.
4. User switches to Preview mode to review formatted output.
5. Preview mode prevents editing.
6. User switches back to Edit mode to continue writing.

Prototype behavior:

- mode buttons change content and read-only state
- no markdown rendering engine yet

Production intent:

- autosave markdown with 1000ms debounce
- preview should use browser-native HTML rendering or plain text unless a markdown dependency is approved

### Document Preview State

The editor shows the current handling state for selected content.

Prototype states:

- **Editable text**
- **Preview only image**
- **Open externally**

Expected behavior:

- Editable text opens inside the editor.
- Preview-only image appears inside the app if supported.
- Unsupported files use default Windows application.

### Markdown Toolbar

The toolbar shows common markdown actions.

Prototype actions:

- Bold
- Italic
- Underline intent
- H1
- H2
- Code
- Link
- Horizontal rule
- Quote

Production intent:

- insert markdown syntax into the editor
- keep behavior keyboard-friendly
- avoid blocking dialogs

### Backlinks and Related Notes

Related Notes show context connected to the current note.

Prototype matching examples:

- same tag
- title mention
- wiki-style link such as `[[Release Playbook.md]]`
- same project file context

User flow:

1. User opens a note.
2. Related notes appear below the editor.
3. User can click a related item to navigate.

Prototype behavior:

- static related note examples

Production intent:

- build relationships from tags, note titles, links, and file metadata
- keep matching local and fast

### Recent Activity

Recent Activity helps users resume work quickly.

Prototype examples:

- edited note
- opened document
- captured new note

User flow:

1. User opens Second Brain.
2. Recent items show what was last touched.
3. User clicks an item to resume work.

Prototype behavior:

- static activity examples

Production intent:

- record local activity history
- show recent notes/files in newest-first order

## Link Bank

Link Bank stores reusable web links grouped by category.

### Category-First Layout

Link Bank uses a resizable two-panel layout.

Left panel:

- indexed category/link search
- date filter
- add category
- rename category
- archive category
- category list with link counts

Right panel:

- Add/Edit Link panel
- selected category details
- search within selected category
- sortable link header/list controls
- shared action toolbar for the selected link
- compact link card list with separate card boxes for each link
- selected link detail panel beside the list

Links are hidden until a category is selected. Link cards use compact VS Code-like rows with visible borders, link title, small tags/badges, and a bottom-right **Last modified** label. URL, details, category, path, date, and status metadata appear in the selected link detail panel. The prototype includes enough dummy link cards so vertical scrolling can be tested when the list is full.

Selection behavior:

- clicking empty category-list area clears selected category
- **Add Category** creates a root category when nothing is selected
- **Add Category** starts inline edit in the category list
- **Pinned** row above categories was removed; pin/favorite is handled in editor/actions instead

### Link Actions

The selected link action toolbar supports:

- **Copy URL** — copy selected URL to clipboard
- **Edit** — edit selected link metadata
- **Remove** — remove or archive selected link after confirmation in production

User flow:

1. User clicks a link card body in the compact link list.
2. The detail panel updates for the selected link.
3. User clicks the URL inside the selected link detail panel to open the link flow.
4. User clicks **Edit** to load selected link into the Add/Edit Link panel.
5. User changes fields and clicks **Save**.
6. User can click Copy URL or Remove from the shared toolbar.

The action buttons are not repeated inside every link card, keeping the list compact. The shared **Open** button was removed because the URL itself is shown and clickable in the selected link detail panel.

Link fields:

- Left column: Link Title, Link, Tags
- Right column: Description
- Bottom-right actions: Pin, Favorite, Save

### Link Search

Search should be case-insensitive, date-filterable, sortable, and should match:

- link title
- link URL
- tags
- details
- category
- path
- partial pattern
- searchable content stored in link metadata

Prototype behavior:

- date filter opens an unclipped popup calendar and stores selected date as `YYYYMMDD`
- sort dropdown supports modified/title ascending and descending order
- indexed/pattern search preview updates when query/date/sort changes
- link result text remains clickable through link cards/detail flow
- no real persisted index yet

Production intent:

- use local `link_bank.json`
- precompute searchable `.casefold()` text
- preserve category-first mental model even when search is active

### Pinned Links

Pinned links are not shown as a separate **Pinned** row above categories in this prototype. Pin and Favorite actions live with the Add/Edit Link panel actions so category controls stay compact.

### Recent Opened Links

Recent links help the user resume work quickly.

Prototype examples:

- PROD · 10m
- UAT · 1h
- SOP · Yesterday

Production intent:

- record local link-open history
- show newest opened links first

### Link Badges

Links can show badges to explain environment, link type, and status.

Prototype badges:

- PROD
- UAT
- SOP
- Portal
- Dashboard
- Working
- Login Needed
- Internal Only

Production intent:

- make link scanning faster
- allow manual status labels first
- optional automated link health checks can be considered later

### Add/Edit Link Panel

Add/Edit Link panel lets the user create a new Link Bank entry or edit the selected link from one place.

Fields:

- Link Title
- Link
- Tags
- Details

User flow:

1. User fills Link Title, Link, Tags, and Details.
2. User reviews the grid layout: title/link/tags on the left and description on the right.
3. User clicks bottom-right **Save** to save a new link prototype.
4. Or user selects an existing link card and clicks **Edit**.
5. Selected link data appears in the Add/Edit Link panel.
6. User changes fields and clicks the same **Save** button.

Prototype behavior:

- visual-only in-memory update
- grid layout keeps title/link/tags left and description right
- Pin/Favorite/Save actions align at bottom-right
- one Save button for add and edit
- no duplicate warning or domain-preview dummy text is shown

### Link Detail Panel

The selected link detail panel keeps the link list compact while still showing full context.

Fields shown in prototype:

- clickable URL
- tags
- details
- category
- path
- date
- status
- prototype status message for clicked buttons and selected cards

Production intent:

- store richer metadata per link
- keep editing in a side/detail panel instead of overcrowding each row

### Archive and Restore

Archive should be preferred over immediate hard deletion.

User flow:

1. User clicks **Archive** on a link.
2. Link is hidden from active category.
3. Link appears in Archived section.
4. User can restore it later.

Production intent:

- prevent accidental data loss
- keep delete confirmation for permanent delete if ever added

### Bulk Import and Export

Import/export supports future backup and transfer workflows.

Prototype actions:

- Import
- Export

Production intent:

- export `link_bank.json` or CSV
- import from supported local file
- validate imported data before merging

### Global Search Result Mode

Global search shows results across all categories while preserving category context.

Prototype examples:

- PROD / PROD Portal
- UAT / Evidence Folder
- CR & ITSM Tools / CR Portal

Expected behavior:

- clicking a result should select its category
- selected link should be highlighted or opened in the detail panel

## Responsive Behavior

Redesign prototypes use `responsive_utils.py` as the shared responsive engine. Prototype files should not define local fallback sizing helpers such as `_scale_factor()`, `scaled()`, `scaled_font()`, or `screen_fraction()`.

The engine detects:

- OS/platform
- available logical workspace
- physical workspace derived from device pixel ratio
- device pixel ratio / HiDPI scale
- logical DPI
- device class such as small laptop, laptop, desktop, ultrawide, retina, or fallback
- density such as compact, comfortable, or spacious

Responsive rules:

- use `QSplitter` for major resizable panels
- splitter handles are visible and hover-highlighted so users know panels can be dragged
- `scaled(0)` preserves true zero for flush margins, spacing, and scrollbar pseudo-elements
- scaling uses OS-specific comfort clamps so controls remain readable on small Windows laptops, Linux dev monitors, and macOS/Retina displays
- density changes layout spacing, margins, row heights, icon sizes, sidebar widths, and header heights
- readability wins before mathematical pixel precision; panels may scroll before text becomes tiny
- sidebar expanded/collapsed widths stay consistent before and after repeated toggles
- header search uses laptop-safe animated widths so title, date, and refresh controls remain visible
- Notes uses a resizable Notes tree / Editor split with laptop-safe minimum widths
- Notes folder tree uses VS Code-like compact indentation while still scrolling vertically and horizontally so deeply nested folders remain reachable
- Notes editor is stretchable and scrolls internally instead of forcing page overflow
- Link Bank uses a category / right-content splitter plus nested link-list / selected-detail splitter
- category, tree, and list panels scroll vertically and horizontally when content is full
- visible high-contrast borders separate major panels and editable content from the background
- filter buttons use a single funnel icon without any toolkit-specific menu arrow
- date filter buttons keep enough width for proportional calendar icon rendering at common scale factors
- avoid fixed major widget sizes; use minimum sizes only for readability boundaries
- use shared helpers such as `scaled`, `scaled_font`, `scaled_icon`, `screen_fraction`, `margin_inner`, `spacing_tight`, `row_height_tree`, and semantic token helpers
- keep editor content stretchable

## Prototype Interaction Feedback

Buttons, dropdowns, search fields, tree items, empty-area unselect gestures, link cards, and the selected link URL provide visible prototype feedback so the user can understand the intended flow. These interactions update UI state or status text only; they do not create files, open browsers, persist links, or call production services yet.

## Current Prototype Limitations

The current redesign file is a UI prototype only.

Not implemented yet:

- real note file creation/persistence
- real folder creation
- real file scanning
- real search indexing beyond prototype preview text
- real markdown autosave
- real markdown preview rendering
- real image preview
- real external file opening
- real link persistence
- real clipboard actions

These behaviors should be wired later when the design is approved and integrated into `../project_tracker/`.
