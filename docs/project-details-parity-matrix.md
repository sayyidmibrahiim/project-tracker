# Project Details Parity Matrix

Audit of Project Details against PRD §12 (lines 1031–1211) and the PyQt prototype
(`redesign_ui/project_details_redesign.py`, reference only), mapped to current
Svelte behavior in `frontend/src/lib/components/ProjectDetails.svelte` and its
child components. Basis for selecting bounded, high-value slices.

| Requirement                          | PRD §12 behavior                                                                 | Current Svelte behavior                                                                 | Status              | Chosen fix / note                                                                 |
| ------------------------------------- | -------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- | ------------------- | --------------------------------------------------------------------------------- |
| SHOW_EDIT mode                        | §12.5 view/edit an existing project                                              | Present: list + detail panel with metadata, CR/Drone, files, notes, actions             | done                | —                                                                                 |
| CR link edit                          | §12.6 paste URL → extract → auto-set PENDING SUBMISSION → save → history          | `cr_update_link` with save + feedback                                                   | done                | —                                                                                 |
| CR state change + guard               | §12.7 valid states, transition guard, failure modal                              | CR state dropdown + `cr_update_state`; backend guard surfaces error                      | done                | —                                                                                 |
| Drone add/edit/delete + state guard   | §12.8/§12.10 drone CRUD, inline state edit with guard                             | drone add/edit/delete + per-drone state save via `drone_update`                          | done                | —                                                                                 |
| File management + template            | §12.11 add/template/open/delete/rename; locked in PROD_READY/IMPLEMENTED          | `FileActions` component (create/template/open/rename/delete + lock hints)                | done                | —                                                                                 |
| Folder transitions + REOPEN           | §12.7/§12.13 move/postpone/cancel/reopen with confirmation                       | `ProjectTransitions` (inline) with ConfirmModal + onApplied reload                       | done                | —                                                                                 |
| Locking rules visible + enforced      | §12.11 file ops locked in PROD_READY/IMPLEMENTED                                  | `folderLocks` + DisabledHints in ProjectActions/FileActions/ProjectTransitions           | done                | —                                                                                 |
| Notes: autosave + toolbar + preview   | §12.12 autosave 1000ms, Saving/Saved, markdown toolbar at caret, Edit/Preview     | Was plain textarea + explicit "Save Notes" button — no toolbar/preview/autosave          | done (this slice)   | New `NotesEditor.svelte`: 1000ms autosave, toolbar (B/I/H1/H2/Code/List/Quote/Link), Edit/Preview via dependency-free `lib/markdown.ts` (no marked.js) |
| NEW_PROJECT mode                      | §12.4 create-project form (name validation, year, dates, CR/drone, plan)         | Implemented: `NewProjectForm` (name + year, realtime validation) → create → SHOW_EDIT    | done                | `project_create` accepts only name+year; optional CR/drone/plan set in SHOW_EDIT (deviation noted below) |
| Activity History panel                | §12.5/§12.13 read-only history list, newest first                                | Absent — no history shown; `ProjectDetail` payload has no history field                  | gap (backend-gated) | Needs a serialized history field on `project_get` (backend/bridge slice) before UI |
| Sub Project table                     | §12.10 columns Sub Project/Drone/State/Owner/Actions (open/delete/rename)         | Subprojects are a `string[]` managed via ProjectActions (create/delete only)             | gap (next slice)    | Build a subproject table with per-row drone mapping/owner/actions                  |
| Two-column Command Center layout      | §12.5 left identity/schedule/subprojects, right files/notes/history              | Single stacked detail card (sections in one column)                                      | gap (layout)        | Restructure detail into the PRD two-column layout (later slice)                    |
| Owner picker (Outlook contacts)       | §12.8 owner picker searches Outlook contacts (Windows COM) or free text          | Free-text owner input only                                                               | gap (Windows-gated) | Contacts search is Windows COM; free-text fallback already present                 |

## Selected implementation target (this slice)

PRD §12.12 **Notes editor** — the highest-value, self-contained, Linux-testable
gap, and a daily-use workflow win (fewer clicks via autosave):

- Replaced the explicit "Save Notes" button with **1000ms debounced autosave**
  (flush-on-blur), with Editing…/Saving…/Saved/error/offline status.
- Added a **markdown toolbar** that inserts syntax at the caret.
- Added an **Edit/Preview toggle**; Preview uses a new dependency-free,
  XSS-safe renderer in `frontend/src/lib/markdown.ts` (PRD names marked.js, but
  the release rules forbid adding dependencies).
- `NotesEditor` is keyed by project path in `ProjectDetails`, so it remounts
  cleanly per project; it seeds from the `initialNotes` prop and owns its buffer.

Deviation documented: PRD §12.12 specifies marked.js for preview; we render a
safe Markdown subset locally instead (no dependency change). The explicit Save
button was intentionally replaced by autosave per the same section.

## Conflict to surface (reported, not changed)

`frontend/src/lib/folderLocks.ts` marks `notes_edit` as view-only in
`IMPLEMENTED` (a `lockReason` exists and is unit-tested), but PRD §12.11 says file
ops are locked "except Add/Edit Notes", and the current `ProjectDetails` notes
textarea was always editable regardless of state. This slice preserves the
existing always-editable Notes behavior (aligned with PRD §12.11) and does **not**
change locking semantics. The `folderLocks.notes_edit` rule is a latent
inconsistency that should be reconciled in a dedicated, approved slice (it may be
intended for a different surface). No locking behavior was altered here.

## Deferred (each surfaced honestly; not hidden as done)

- Sub Project table with per-row drone mapping/owner/actions.
- Activity History panel (needs a serialized history field on `project_get`).
- Two-column Command Center layout restructure.
- Outlook-contacts owner picker (Windows COM; free-text fallback exists).
- Optional create-time fields (CR link, first drone, implementation plan) and
  Start/End schedule editing: `project_create` accepts only `project_name` +
  `year`, and no Start/End editor exists anywhere yet. NEW_PROJECT collects
  name + year and lands the user in SHOW_EDIT, where CR link, drone, and plan are
  already editable; collecting them at create-time needs backend support.
