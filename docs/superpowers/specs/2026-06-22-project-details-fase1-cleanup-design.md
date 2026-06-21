# Project Details UI — Fase 1: Cleanup & Structural Fixes

**Status:** Approved design (pending implementation)
**Date:** 2026-06-22
**Scope owner:** Sayyid Ibrahim
**Origin review:** User feedback on Project Details UI/UX (12 points total)
**Phase:** 1 of 4 — see *Phase Roadmap* below for 2–4.

## Goal

Restructure the Project Details screen so the main-project view is clean, focused, and
behaves like a modern productivity app (Notion-class), by removing redundant controls,
consolidating related editing surfaces, and fixing layout overflow. This phase is
deliberately **cleanup + small structural changes only** — no new design language
(Fase 2), no WYSIWYG editor (Fase 3), no sub-project-as-first-class-entity (Fase 4).

## Non-goals (deferred to later phases)

| Review point | Phase | Why deferred |
|---|---|---|
| 5. Replace all ASCII glyph icons with professional SVG | Fase 2 | Needs icon-set decision + visual mockups |
| 6. Notion-like visual polish / nuance | Fase 2 | Design-language overhaul — needs visual companion |
| 8.1. Microsoft Word-style WYSIWYG Notes | Fase 3 | Needs library-vs-custom decision (Tiptap vs contenteditable) |
| 8.2. Checklist (checkbox) support in Notes | Fase 3 | Part of WYSIWYG |
| 10. Different Notes content for main vs sub project | Fase 4 | Needs sub-project first-class data model |
| 11. Sub-project dates inherit from main project | Fase 4 | Needs backend date-inheritance logic |
| 12. Project Details view adapted for sub-projects | Fase 4 | Needs `project_get` backend fix + parent linkage |

Review points covered by Fase 1: **1.1, 1.2, 1.3, 1.4, 2, 3.1, 3.2, 3.3, 3.4, 4, 7.1, 9.1, 9.2.**

## Current state (what exists today)

`frontend/src/lib/components/ProjectDetails.svelte` renders the screen as two panes:

- **Left pane:** Project Identity (name, CR number, CR link, CR state, Drone State
  summary, Drone Ticket form), Schedule, Implementation Plan, Sub Projects table.
- **Right pane:** Files, Notes editor, Activity History.

Sub-project editing today lives inside the **Project Identity** box as a "Drone Ticket"
sub-block that is only shown when a Sub Project filter is selected from the Command
Center dropdown. CR State changes require an explicit "Save CR State" button. The
Sub Projects table shows Sub Project name, Drone Ticket URL, Drone State, Owner, and
an Open Folder action.

`SubProjectTable.svelte` and `FileActions.svelte` are child components. `NotesEditor.svelte`
is untouched in Fase 1.

## Design

### Section 1 — Project Identity box (review points 1.1, 1.2, 1.3, 1.4)

**1.1 — Remove "Selected Sub Project" row.**
The `<div class="pd-dl-item"><dt>Selected Sub Project</dt><dd>…</dd></div>` row inside
the `pd-detail-grid` is deleted. With only the CR Number field remaining, the
`pd-detail-grid` two-column layout is no longer justified — collapse to a single
full-width row displaying CR Number. The `pd-detail-grid` CSS class can stay (unused
in this section) or be removed; removing is cleaner.

**1.2 — Remove "Save CR State" button; autosave on change.**
The `<button onclick={saveCrState}>Save CR State</button>` is removed. The CR State
`<select>` now fires save on `onchange` instead of waiting for a button press.

Behavior:
- **Non-destructive transitions:** any selected value that is the project's current
  `cr_state` OR a forward target in `CR_NEXT[currentState]` that is **not** in the
  destructive set `{POSTPONED, CANCELED}`. Concretely these are: PENDING SUBMISSION →
  PENDING APPROVAL; PENDING APPROVAL → APPROVED; APPROVED → (none — its only forward
  targets are destructive); IN-PROGRESS → FINISHED. These autosave immediately via
  `cr_update_state`.
- **Destructive transitions:** target in `{POSTPONED, CANCELED}` (from PENDING
  SUBMISSION, PENDING APPROVAL, APPROVED, or IN-PROGRESS), or `REOPEN` (only offered
  when current state is POSTPONED or CANCELED). These route through `ConfirmModal`
  exactly as today. REOPEN continues to call `folder_reopen` (not `cr_update_state`),
  preserving the existing safety contract. The dropdown visually shows the destructive
  value as the user picked it, but the underlying `detail.cr_state` only updates after
  confirm.

A transient inline status indicator (replacing the removed button's feedback) appears
next to the dropdown: `⏳ Saving…` / `✓ Saved` (auto-clear 2.5s) / `✗ <error>`
(persists until next action). Same `crStateSaveState` enum already in place; only the
trigger changes (onchange → save instead of button → save).

**1.3 — Remove the entire Drone Ticket block from Project Identity.**
The `<div class="pd-drone-flow">` block (heading "Drone Ticket", the "Choose a Sub
Project…" paragraph, and the three conditional forms — selected-subproject drone,
new-drone-form, selected-drone-state) is removed. All drone editing moves to the
Sub Project box (Section 3). The "Drone State" summary dropdown in the `pd-meta-datetime-row`
is also removed (it duplicated per-sub-project state and is meaningless on the main
project when no sub-project is selected).

State variables removed from `ProjectDetails.svelte`:
- `selectedSubprojectDrone` derived (the master-detail in Section 3 replaces it).
- `saveSelectedSubprojectDroneLink`, `saveSelectedSubprojectDroneOwner` (moved to
  Sub Project box handlers).
- `newDroneLink`, `newDroneSubfolder`, `newDroneOwner` (replaced by Sub Project box
  "add drone" flow keyed to the selected sub-project row).

State variables kept:
- `droneStateEdits`, `droneStateBusy`, `droneStateError` — repurposed for per-row
  state in the Sub Project table (keyed by sub-project name, not by drone ticket
  index — see Section 3).

**1.4 — CR Link conditional render.**

When `detail.cr_link` is empty/whitespace → **input mode**:
```
[ Paste CR link…                                   ]  ← single input, autosave on blur
```
- `<input type="url" placeholder="Paste CR link…">` with `bind:value={crLinkEdit}`.
- On `onblur`, if value changed and non-empty, call `cr_update_link`.
- Existing `crLinkSaveState` feedback reused (inline transient next to input).

When `detail.cr_link` is non-empty → **display mode**:
```
CR Number: CR-12345    [📋 Copy]  [↗ Open]
                                          [✎ Edit]   ← small pencil, toggles back to input
```
- Show `detail.cr_number` (or the raw `cr_link` if `cr_number` is empty — defensive).
- `📋 Copy` button → `navigator.clipboard.writeText(detail.cr_link)`. On success show
  transient "✓ Copied" (2s). On failure (clipboard API not available) show "✗ Press
  Ctrl+C" and select a hidden text input containing the link as fallback.
- `↗ Open` button → `window.open(detail.cr_link, "_blank", "noopener,noreferrer")`.
  WebView2 handles external-browser hand-off natively. (No bridge `url_open` exists
  today — confirmed via grep of `project_tracker/web/js_api.py`; `window.open` is the
  correct mechanism inside WebView2.)
- `✎ Edit` button → flips back to input mode with `crLinkEdit` pre-filled. User can
  then change and blur-to-save, or escape to cancel (revert `crLinkEdit` to
  `detail.cr_link`).

A single new state boolean `crLinkEditing` (default `false`, set `true` when in input
mode) gates the conditional render. `crLinkEditing` is initialized to `!detail.cr_link`
on project select.

### Section 2 — Remove Implementation Plan box (review point 2)

The entire `<div class="pd-section"><h4>Implementation Plan</h4>…</div>` block is
removed from the template. State variables `metaPlanEdit` and its references in
`syncMetadataDrafts` and `metadataUnchanged` are removed.

The backend `project_update` bridge still accepts `implementation_plan` and the
`ProjectMetadata` model still has the field — these are **untouched** for data
compatibility. `saveMetadata` simply stops sending `implementation_plan` (or sends
`undefined`, which the backend must already tolerate since the field is optional).
Existing stored `implementation_plan` data on disk is preserved, just not editable
from the UI in Fase 1. (Fase 3 WYSIWYG may re-introduce a notes-like surface for it,
or fold it into Notes — out of scope here.)

### Section 3 — Sub Project box (review points 3.1, 3.2, 3.3, 3.4)

**3.1 — Rename box title:** `Sub Projects` → `Sub Project (DRONE)`.

**3.2 — Show sub-project basename only in table.**
Today `subproject_list` (via `_subprojects_from_json` in dashboard_service) returns a
list of **folder names** (basenames), not full paths. `subprojects` prop is already
`string[]` of names. `SubProjectTable.svelte` already renders `{row.name}` directly.
The change is purely defensive: audit `SubProjectTable.svelte` for any path-joining
display logic, ensure only `row.name` is shown in the "Sub Project" column. (Expected:
no code change beyond verification — but the audit is in scope to be safe.)

**3.3 — Remove Owner column from table.**
The `Owner` `<span>` column is removed from both the header row and each data row.
`Row.owner` field is removed from the `Row` interface and from the `rows` derived.
Owner editing is no longer exposed in Fase 1. (The `DroneTicket.owner` model field
stays — backend-compat. If re-exposed in Fase 4's sub-project detail view, it lives
there, not here.)

**3.4 — Drone State dropdown per row + Drone URL master-detail.**

Table schema becomes:

| Sub Project | Drone State | Actions |
|---|---|---|
| `api-service` | `[IN-PROGRESS ▾]` | `📁 Open` |
| `▶ web-portal` (selected) | `[APPROVED ▾]` | `📁 Open` |

- **Drone State dropdown** in each row. Populated via the existing
  `legalDroneOptionsFor(row.droneState)` helper. On `onchange`:
  - Non-destructive target → autosave via `drone_update` with `{drone_state: next}`.
    The drone ticket index is resolved by matching `subfolder_name === row.name` in
    `detail.drone_tickets` (same logic as today's `selectedSubprojectDrone` derived).
  - Destructive target (POSTPONED/CANCELED) → ConfirmModal first, then save.
    Drone state has no REOPEN option (per existing `DRONE_NEXT` map), so REOPEN
    routing is CR-only.
- **Master-detail for Drone URL:** clicking a row selects it (`selectedSubprojectRow`
  state). Below the table, a detail panel appears:
  ```
  ┌─ web-portal · Drone Ticket ─────────────────┐
  │ Drone URL: [ https://drone.../WEB-101    ] 💾 │
  └──────────────────────────────────────────────┘
  ```
  - If the selected sub-project **has** a drone ticket (matched by `subfolder_name`):
    show input pre-filled with `drone_link`, autosave on blur via `drone_update` with
    `{drone_link: value}`.
  - If the selected sub-project **has no** drone ticket: show empty input + button
    "Add Drone Ticket" → calls `drone_add` with `{drone_link: value, subfolder_name:
    row.name}`.
- **Open Folder** action remains (`folder_open` via `joinPath(projectPath, name)`).

**Component refactor:** `SubProjectTable.svelte` becomes a **presentational**
component. New props:

```ts
interface SubProjectTableProps {
  projectPath: string;
  subprojects: string[];
  droneTickets: DroneTicket[];
  selectedRow: string | null;              // currently-selected sub-project name
  droneStateBusy: string | null;           // name of row currently saving state
  droneStateErrors: Record<string, string>; // keyed by sub-project name
  onSelectRow: (name: string) => void;
  onChangeDroneState: (name: string, nextState: string) => void;
  onOpenFolder: (name: string) => void;
}
```

The Drone URL master-detail panel **stays inside `ProjectDetails.svelte`** (not in
`SubProjectTable.svelte`), so `SubProjectTable` only emits row-selection events and
ProjectDetails renders the detail panel below the table. This keeps the table dumb
and testable; ProjectDetails owns all bridge interactions.

State removed from ProjectDetails:
- `selectedSubproject` filter in Command Center is **kept** (it still filters which
  drone ticket to show in Identity — wait, no: Identity drone block is gone in Section
  1). Re-evaluate: does the Command Center "Sub Project" `<select>` still serve a
  purpose after Section 1? **No** — its only consumer was the Identity drone block.
  The Command Center "Sub Project" dropdown is **removed in Fase 1** as a consequence.
  Sub-project selection is now via clicking a row in the Sub Project table.

  (This is an implication of Section 1.3 that was not explicit in the review points
  but is required for consistency — leaving a dead dropdown would be worse than
  removing it.)

New state added to ProjectDetails:
- `selectedSubprojectRow: string | null` — drives the master-detail panel.
- `droneLinkEdit: string` — draft for the Drone URL input in the detail panel.
- `droneLinkBusy: boolean`, `droneLinkError: string`.

### Section 4 — Back to Dashboard button (review point 4)

**Placement:** a new bar above the Command Center panel, full width:

```
┌─────────────────────────────────────────┐
│  ← Back to Dashboard                     │  ← new bar
├─────────────────────────────────────────┤
│ ┌─ Project Command Center ──────────────┐│
│ │ ...                                    ││
```

**Visual:** low-emphasis secondary button (white bg, dark text, subtle border). Left
arrow glyph `←` (ASCII for Fase 1; Fase 2 swaps to SVG). Not red — it's navigation,
not an action.

**Mechanism:** add new optional prop to `ProjectDetails.svelte`:

```ts
let { initialPath, startNew, onNavigateDashboard }: {
  initialPath?: string | null;
  startNew?: boolean;
  onNavigateDashboard?: () => void;
} = $props();
```

Wire in `App.svelte`:

```svelte
<ProjectDetails
  initialPath={pendingProjectPath}
  startNew={startNewProject}
  onNavigateDashboard={() => navigate("dashboard")}
/>
```

The button calls `onNavigateDashboard?.()`. If the prop is absent (defensive —
component is used elsewhere), the button is hidden.

### Section 5 — Activity History: fixed height + scroll (review point 7.1)

Wrap the existing `<ol class="pd-history-list">` in a new container:

```svelte
<div class="pd-history-scroll">
  <ol class="pd-history-list">…</ol>
</div>
```

CSS (added to ProjectDetails `<style>`):

```css
.pd-history-scroll {
  max-height: 280px;
  overflow-y: auto;
  padding-right: 4px;
}
```

280px is chosen to be visually comparable to the Notes editor's min-height (~120–300px)
and the Files box after Section 6 changes, so the three right-pane boxes (Files, Notes,
Activity History) reach roughly similar heights and the right pane doesn't lurch.

Scrollbar inherits the global `::-webkit-scrollbar` styling from `styles.css`.

### Section 6 — Files: scrollable + hide internal files (review points 9.1, 9.2)

**9.1 — Scrollable file list.** In `FileActions.svelte`, add:

```css
.fa-file-list {
  max-height: 320px;
  overflow-y: auto;
  padding-right: 4px;
}
```

The existing `.fa-file-list` rule (`display: flex; flex-direction: column; gap: 4px;
margin: 0; padding: 0; list-style: none;`) gains `max-height` and `overflow-y`. The
create-file form rows stay outside the scroll area (always visible).

**9.2 — Hide + lock reserved files.**

Constant in `FileActions.svelte`:

```ts
const RESERVED_FILES = new Set(["project_data.json", "notes.md"]);
```

- **Hide:** before rendering, filter the `files` prop:
  ```ts
  const visibleFiles = $derived(files.filter((f) => !RESERVED_FILES.has(f.name.toLowerCase())));
  ```
  Render `visibleFiles` instead of `files` in the list. Case-insensitive match —
  Windows is case-insensitive, so `Notes.md` is also reserved.
- **Lock create:** in `createFile()`, reject if `newFilename.trim().toLowerCase()` is
  in `RESERVED_FILES`. Error message: `"notes.md and project_data.json are reserved
  system files and cannot be created here."` Same check in `createFromTemplate()`
  (templates wouldn't normally target these names, but defense-in-depth).
- **Lock rename:** in `requestRename()`, reject if `renameDraft.trim().toLowerCase()`
  is in `RESERVED_FILES`. Error message: `"Cannot rename to a reserved system file
  name."`

The backend remains the authoritative guard — these are UX-level foot-gun prevention.
A determined user can still create the file via Explorer; the app simply hides it
from its own UI and would treat it as reserved on next read.

## Architecture decisions

- **No new bridge methods.** Fase 1 is pure frontend. All features reuse existing
  bridge calls: `cr_update_link`, `cr_update_state`, `folder_reopen`, `drone_add`,
  `drone_update`, `project_update`, `folder_open`, `notes_get`, `notes_update`,
  `file_list`, `file_create`, `file_rename`, `file_delete`. The `test_bridge_contract_guard`
  test continues to pass without changes.
- **SubProjectTable becomes presentational.** All bridge interactions move to
  `ProjectDetails.svelte`; the table emits callbacks. This makes the table unit-testable
  in isolation (props in → props out) and keeps `ProjectDetails.svelte` as the single
  owner of bridge state.
- **No dependency additions.** Consistent with the existing `markdown.ts` constraint
  ("no new dependencies"). The CR-link copy/open uses native browser APIs
  (`navigator.clipboard`, `window.open`).

## Testing strategy

Existing tests in `frontend/tests/` are `.mjs` component tests using Svelte's testing
utilities. Fase 1 requires:

1. **Update existing ProjectDetails tests** (`frontend/tests/components.test.mjs`,
   `frontend/tests/dashboard-inline-edit.test.mjs`, and any test that snapshots or
   asserts on ProjectDetails markup) to reflect the removed elements: no
   "Selected Sub Project" row, no "Save CR State" button, no "Implementation Plan"
   section, no Identity Drone Ticket block, no Command Center Sub Project dropdown.
2. **New tests:**
   - CR Link display mode shows copy/open/edit buttons when `cr_link` is non-empty.
   - CR Link input mode shows single input when `cr_link` is empty.
   - CR State autosave fires `cr_update_state` on `onchange` for non-destructive
     targets.
   - CR State destructive target opens `ConfirmModal` (no immediate bridge call).
   - Back to Dashboard button calls `onNavigateDashboard`.
   - Sub project table row click sets `selectedSubprojectRow`.
   - Drone URL detail panel renders for selected row, calls `drone_update` on blur.
   - Drone State dropdown per row calls `drone_update` with correct drone ticket index.
   - FileActions hides `notes.md` and `project_data.json`.
   - FileActions rejects Create/Rename to reserved names.
3. **Backend tests:** no changes — Fase 1 is frontend-only. `tests/test_bridge_contract_guard.py`
   must still pass (no new bridge names introduced).

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| Removing Implementation Plan loses user data on existing projects | Field stays in model + on disk; only UI editing removed. No migration needed. |
| Removing Command Center Sub Project dropdown breaks a flow that depended on it | Verified: its only consumer was the Identity drone block (removed in Section 1.3). No other code path reads `selectedSubproject`. |
| `navigator.clipboard` may be unavailable in some WebView2 configs | Fallback: select-and-instruct ("Press Ctrl+C"). |
| Master-detail adds a click to edit Drone URL (was previously inline) | Acceptable trade-off for the cleaner Identity box; matches Notion-style interaction. |
| Removing Owner editing may inconvenience existing workflows | Owner stays in the data model; re-exposed in Fase 4 sub-project detail if needed. |

## Open questions

None. All ambiguities resolved during clarifying questions:
- Drone URL editing location → master-detail in Sub Project box.
- Reserved files → hide + lock.
- CR State autosave → confirm for destructive, autosave otherwise.
- Back button placement → top-left, above Command Center.
