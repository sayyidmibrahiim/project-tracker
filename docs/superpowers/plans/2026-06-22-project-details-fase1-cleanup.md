# Project Details Fase 1 — UI Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the Project Details screen — remove redundant Identity controls, consolidate sub-project + drone editing into one box, add a Back-to-Dashboard button, fix Activity History / Files overflow, and hide reserved system files. Pure frontend; no backend or bridge changes.

**Architecture:** Three component edits (`ProjectDetails.svelte`, `SubProjectTable.svelte`, `FileActions.svelte`) plus one wiring change in `App.svelte`. `SubProjectTable.svelte` is refactored from stateful bridge-caller to presentational (emits callbacks; ProjectDetails owns all bridge state). Tests are source-text assertions via Svelte SSR — no DOM library — so each task updates both the component source AND the assertions that reference removed markup.

**Tech Stack:** Svelte 5 (runes `$state`/`$derived`/`$props`), TypeScript, node:test + node:assert/strict, custom SSR helper (`frontend/tests/ssrHelper.mjs`).

**Reference doc:** `docs/superpowers/specs/2026-06-22-project-details-fase1-cleanup-design.md`

---

## File Structure

**Modified:**
- `frontend/src/lib/components/ProjectDetails.svelte` — bulk of changes (Sections 1–5)
- `frontend/src/lib/components/SubProjectTable.svelte` — refactor to presentational (Section 3)
- `frontend/src/lib/components/FileActions.svelte` — scroll + hide/lock reserved files (Section 6)
- `frontend/src/App.svelte` — wire `onNavigateDashboard` prop (Section 4)
- `frontend/tests/as-is-prototype-parity.test.mjs` — update label assertion `Sub Projects` → `Sub Project (DRONE)`
- `frontend/tests/dashboard-inline-edit.test.mjs` — replace removed-element assertions
- `frontend/tests/components.test.mjs` — drop `implementation_plan: metaPlanEdit` assertion, update `Sub Project` regex
- `frontend/tests/project-details-reopen.test.mjs` — keep REOPEN contract assertions intact; they should still pass since `saveCrState` stays (now triggered by onchange)

**Created:**
- `frontend/tests/project-details-fase1.test.mjs` — new test file for Fase 1 behavior (CR Link conditional render, autosave CR state, Back button, master-detail, reserved files)

**Untouched:**
- `frontend/src/lib/components/NotesEditor.svelte` (Fase 3)
- `frontend/src/lib/types.ts`, `frontend/src/lib/bridge.ts` (no contract changes)
- All `project_tracker/` backend code, all `tests/` Python tests

---

## Conventions for this plan

- **Commands run from** `D:/Ibrahim/Projects/project_tracker/frontend` (frontend tests) or repo root (git).
- **Frontend test command:** `npm test` (runs all `tests/*.test.ts` + `tests/*.test.mjs` via node:test).
- **Type check:** `npm run check` (svelte-check).
- **A single test file:** `node --import ./tests/register-hooks.mjs --test "tests/project-details-fase1.test.mjs"`.
- All commits go on the current branch `prd-v31-migration` unless told otherwise.
- **TDD discipline:** for each new behavior, write the failing assertion FIRST, run it, watch it fail, then implement. The source-text tests in this repo mean "test fails" = the regex/assertion does not match the (unchanged) source.

---

## Task 0: Baseline — capture current green state

**Files:** none (verification only)

- [ ] **Step 1: Confirm tests currently pass**

Run from `D:/Ibrahim/Projects/project_tracker/frontend`:
```bash
npm test
```
Expected: all tests pass. Note any pre-existing failures (should be none on a clean checkout of `prd-v31-migration`).

- [ ] **Step 2: Confirm type check passes**

```bash
npm run check
```
Expected: `svelte-check` exits 0 with no errors.

This baseline lets later tasks distinguish "I broke something" from "it was already broken."

---

## Task 1: Update existing assertions that will break (the "red" anchors)

These source-text assertions reference markup we are about to remove. Update them now, before touching components, so each subsequent component edit produces a clean test delta. Each updated assertion should still pass against the CURRENT source — i.e. only relax/replace assertions whose target stays valid, and DELETE assertions whose target is going away. The new assertions for new behavior land in Task 9.

**Files:**
- Modify: `frontend/tests/dashboard-inline-edit.test.mjs:83-104`
- Modify: `frontend/tests/components.test.mjs:332`
- Modify: `frontend/tests/as-is-prototype-parity.test.mjs:44`
- Test: run `npm test`

- [ ] **Step 1: Update `dashboard-inline-edit.test.mjs` lines 83–89**

Current test asserts removed markup exists. Replace the whole test:

Find this block:
```js
test("ProjectDetails source has visible AS_IS selected-subproject drone-ticket flow and implementation plan section", () => {
  assert.match(PROJECT_DETAILS, /screen-details/);
  assert.match(PROJECT_DETAILS, /Project Command Center/);
  assert.match(PROJECT_DETAILS, /selectedSubprojectDrone/);
  assert.match(PROJECT_DETAILS, /Add Drone Ticket/);
  assert.match(PROJECT_DETAILS, /Implementation Plan/);
});
```

Replace with (keeps the two assertions whose targets survive, drops the three whose targets are being removed):
```js
test("ProjectDetails source has visible AS_IS command center and sub-project box", () => {
  assert.match(PROJECT_DETAILS, /screen-details/);
  assert.match(PROJECT_DETAILS, /Project Command Center/);
  assert.match(PROJECT_DETAILS, /Sub Project \(DRONE\)/);
  assert.doesNotMatch(PROJECT_DETAILS, /Implementation Plan/);
  assert.doesNotMatch(PROJECT_DETAILS, /Save CR State/);
});
```

- [ ] **Step 2: Update `dashboard-inline-edit.test.mjs` lines 99–104**

Current test references `selectedSubprojectDrone` which is being removed. Replace:

Find:
```js
test("ProjectDetails state dropdowns use legal next-state helpers", () => {
  assert.match(PROJECT_DETAILS, /function\s+legalCrOptionsFor\s*\(/);
  assert.match(PROJECT_DETAILS, /function\s+legalDroneOptionsFor\s*\(/);
  assert.match(PROJECT_DETAILS, /#each legalCrOptionsFor\(detail\.cr_state\) as opt/);
  assert.match(PROJECT_DETAILS, /#each legalDroneOptionsFor\(selectedSubprojectDrone\.ticket\.drone_state\) as opt/);
});
```

Replace with (the drone-options each loop now iterates over a per-row drone ticket name lookup, not `selectedSubprojectDrone`):
```js
test("ProjectDetails state dropdowns use legal next-state helpers", () => {
  assert.match(PROJECT_DETAILS, /function\s+legalCrOptionsFor\s*\(/);
  assert.match(PROJECT_DETAILS, /function\s+legalDroneOptionsFor\s*\(/);
  assert.match(PROJECT_DETAILS, /#each legalCrOptionsFor\(detail\.cr_state\) as opt/);
});
```

- [ ] **Step 3: Update `components.test.mjs` line 332**

Current assertion requires `metaPlanEdit` to be passed to `project_update`, which is being removed.

Find:
```js
  assert.match(src, /implementation_plan:\s*metaPlanEdit/);
```

Replace with:
```js
  // Fase 1 removed the Implementation Plan UI; project_update no longer sends implementation_plan.
  assert.doesNotMatch(src, /implementation_plan:\s*metaPlanEdit/);
  assert.doesNotMatch(src, /metaPlanEdit/);
```

- [ ] **Step 4: Update `components.test.mjs` line 343**

The generic `Sub Project` regex matches the new title `Sub Project (DRONE)` already, so this assertion stays valid. No change required — verify by reading.

- [ ] **Step 5: Update `as-is-prototype-parity.test.mjs` line 44**

Current array includes `"Sub Projects"` (plural). After Fase 1 the title is `Sub Project (DRONE)`.

Find:
```js
  for (const label of ["Project Command Center", "Project Identity", "Schedule", "Sub Projects", "Files", "Notes", "Activity History"]) {
```

Replace with:
```js
  for (const label of ["Project Command Center", "Project Identity", "Schedule", "Sub Project (DRONE)", "Files", "Notes", "Activity History"]) {
```

- [ ] **Step 6: Run tests — expect failures only from the new TODOs that aren't implemented yet**

Run:
```bash
npm test
```
Expected: the 3 modified tests now FAIL (the component still has the old markup). Specifically:
- `dashboard-inline-edit.test.mjs` "ProjectDetails source has visible AS_IS command center…" FAILs (still has `Implementation Plan`, still has `Save CR State`, does NOT yet have `Sub Project (DRONE)`).
- `components.test.mjs` datetime test FAILs (source still has `implementation_plan: metaPlanEdit`).
- `as-is-prototype-parity.test.mjs` "AS_IS page titles" FAILs (still has `Sub Projects`, not `Sub Project (DRONE)`).

Other tests pass. These 3 (and only these 3) become the RED beacons that subsequent tasks turn green.

- [ ] **Step 7: Commit the test updates**

```bash
cd "D:/Ibrahim/Projects/project_tracker"
git add frontend/tests/dashboard-inline-edit.test.mjs frontend/tests/components.test.mjs frontend/tests/as-is-prototype-parity.test.mjs
git commit -m "test(fase1): update Project Details assertions for planned cleanup

Loosen/replace assertions that reference removed markup (Save CR State
button, Implementation Plan section, selectedSubprojectDrone, metaPlanEdit,
plural 'Sub Projects' title). These go red until the component edits land."
```

---

## Task 2: Remove Implementation Plan section + metaPlanEdit state (Section 2)

**Files:**
- Modify: `frontend/src/lib/components/ProjectDetails.svelte`
- Test: `npm test`

- [ ] **Step 1: Remove `metaPlanEdit` state declaration**

In `ProjectDetails.svelte` find (around line 78):
```svelte
  let metaPlanEdit: string = $state("");
```

Delete the line.

- [ ] **Step 2: Remove `metaPlanEdit` from `syncMetadataDrafts`**

Find (around lines 168–173):
```svelte
  function syncMetadataDrafts(nextDetail: ProjectDetail) {
    metaNameEdit = nextDetail.project_name || "";
    metaStartEdit = toDatetimeLocal(nextDetail.start_datetime);
    metaEndEdit = toDatetimeLocal(nextDetail.end_datetime);
    metaPlanEdit = nextDetail.implementation_plan || "";
  }
```

Replace with:
```svelte
  function syncMetadataDrafts(nextDetail: ProjectDetail) {
    metaNameEdit = nextDetail.project_name || "";
    metaStartEdit = toDatetimeLocal(nextDetail.start_datetime);
    metaEndEdit = toDatetimeLocal(nextDetail.end_datetime);
  }
```

- [ ] **Step 3: Remove `metaPlanEdit` from `metadataUnchanged`**

Find (around lines 175–180):
```svelte
  function metadataUnchanged(current: ProjectDetail): boolean {
    return metaNameEdit === current.project_name
      && metaStartEdit === toDatetimeLocal(current.start_datetime)
      && metaEndEdit === toDatetimeLocal(current.end_datetime)
      && metaPlanEdit === (current.implementation_plan || "");
  }
```

Replace with:
```svelte
  function metadataUnchanged(current: ProjectDetail): boolean {
    return metaNameEdit === current.project_name
      && metaStartEdit === toDatetimeLocal(current.start_datetime)
      && metaEndEdit === toDatetimeLocal(current.end_datetime);
  }
```

- [ ] **Step 4: Remove `implementation_plan` from `saveMetadata`**

Find (around lines 330–335):
```svelte
    const resp = await callBridge("project_update", selectedPath, {
      project_name: metaNameEdit,
      start_datetime: fromDatetimeLocal(metaStartEdit),
      end_datetime: fromDatetimeLocal(metaEndEdit),
      implementation_plan: metaPlanEdit,
    });
```

Replace with:
```svelte
    const resp = await callBridge("project_update", selectedPath, {
      project_name: metaNameEdit,
      start_datetime: fromDatetimeLocal(metaStartEdit),
      end_datetime: fromDatetimeLocal(metaEndEdit),
    });
```

- [ ] **Step 5: Remove the Implementation Plan section from the template**

Find (around lines 729–737) the entire `<div class="pd-section">` block whose title is "Implementation Plan":

```svelte
            <div class="pd-section">
              <h4 class="pd-section-title">Implementation Plan</h4>
              <div class="pd-meta-edit">
                <textarea id="meta-plan" class="pd-notes-textarea" rows="5" bind:value={metaPlanEdit} disabled={metaSaveState === "saving"} placeholder="Write plan, dependencies, cutover notes…"></textarea>
                <div class="pd-notes-actions">
                  <button class="cr-link-save-btn" onclick={saveMetadata} disabled={metaSaveState === "saving" || metadataUnchanged(detail)}>{#if metaSaveState === "saving"}⏳ Saving…{:else}Save Implementation Plan{/if}</button>
                </div>
              </div>
            </div>
```

Delete the entire block.

- [ ] **Step 6: Run tests — `components.test.mjs` datetime test should now PASS**

Run:
```bash
npm test
```
Expected: the `components.test.mjs` "ProjectDetails source includes datetime-local editors…" test PASSES (no more `metaPlanEdit` reference). The other two Task-1 failing tests still fail (they wait for Tasks 3 and 6).

- [ ] **Step 7: Run type check**

```bash
npm run check
```
Expected: 0 errors. If svelte-check complains about `implementation_plan` being a valid field of `project_update`'s payload that is now missing — it shouldn't (we just send fewer fields), but if it does, the payload type is likely an inline object literal, so just remove the key as done in Step 4.

- [ ] **Step 8: Commit**

```bash
cd "D:/Ibrahim/Projects/project_tracker"
git add frontend/src/lib/components/ProjectDetails.svelte
git commit -m "feat(fase1): remove Implementation Plan section

Drops the Implementation Plan textarea, its metaPlanEdit state, and stops
sending implementation_plan through project_update. The backend field and
existing stored data are untouched (Fase 3 WYSIWYG may re-introduce a
notes-like surface for it)."
```

---

## Task 3: Project Identity — remove drone block, drone state summary, "Selected Sub Project", CR State button (Sections 1.1, 1.2, 1.3)

This task does the removals; the CR Link conditional render (1.4) is a separate Task 4 because it adds new markup.

**Files:**
- Modify: `frontend/src/lib/components/ProjectDetails.svelte`
- Test: `npm test`

- [ ] **Step 1: Remove the "Selected Sub Project" `<div class="pd-dl-item">`**

Find (around line 632):
```svelte
                  <div class="pd-dl-item"><dt>Selected Sub Project</dt><dd>{selectedSubproject === "all" ? "Choose one above" : selectedSubproject}</dd></div>
```

Delete the line. The parent `.pd-detail-grid` now has only one child (`CR Number`). Collapse the grid: find the surrounding wrapper:

```svelte
                <div class="pd-detail-grid">
                  <div class="pd-dl-item"><dt>CR Number</dt><dd>{detail.cr_number || "—"}</dd></div>
                </div>
```

Replace with a single full-width item (drop the grid wrapper — it was two-column for two items; now one item doesn't need it):
```svelte
                <div class="pd-dl-item"><dt>CR Number</dt><dd>{detail.cr_number || "—"}</dd></div>
```

- [ ] **Step 2: Remove the Drone State summary dropdown**

In the `pd-meta-datetime-row` block that holds CR State + Drone State (around lines 639–654), find the Drone State label:

```svelte
                  <label class="pd-meta-field" for="meta-drone-state-summary">
                    <span class="pd-meta-label">Drone State</span>
                    <select id="meta-drone-state-summary" class="cr-state-select" value={detail.drone_tickets[0]?.drone_state ?? ""} disabled>
                      <option>{detail.drone_tickets[0]?.drone_state ?? "—"}</option>
                    </select>
                  </label>
```

Delete the entire `<label>`. The `pd-meta-datetime-row` wrapper now contains only the CR State label — that's fine; it becomes a single-column row.

- [ ] **Step 3: Remove the "Save CR State" button AND rewire CR State to autosave**

Find the `<div class="pd-notes-actions">` block that contains the Save CR State button (around lines 655–664):

```svelte
                <div class="pd-notes-actions">
                  <button class="cr-link-save-btn" onclick={saveCrState} disabled={crStateSaveState === "saving" || crStateEdit === detail.cr_state}>{#if crStateSaveState === "saving"}⏳ Saving…{:else}Save CR State{/if}</button>
                  {#if crLinkSaveState === "success" || crStateSaveState === "success"}
                    <span class="cr-link-feedback cr-link-ok">✓ Saved</span>
                  {:else if crLinkSaveState === "error"}
                    <span class="cr-link-feedback cr-link-err">✗ {crLinkSaveError}</span>
                  {:else if crStateSaveState === "error"}
                    <span class="cr-link-feedback cr-link-err">✗ {crStateSaveError}</span>
                  {/if}
                </div>
```

Replace with (button gone; transient feedback kept inline next to the dropdown, but moved out of `pd-notes-actions` since there's no button to align with):
```svelte
                {#if crStateSaveState === "saving"}
                  <span class="cr-link-feedback">⏳ Saving…</span>
                {:else if crStateSaveState === "success"}
                  <span class="cr-link-feedback cr-link-ok">✓ Saved</span>
                {:else if crStateSaveState === "error"}
                  <span class="cr-link-feedback cr-link-err">✗ {crStateSaveError}</span>
                {/if}
```

Now add an `onchange` handler to the CR State `<select>` so it autosaves. Find the CR State select (around line 642):
```svelte
                    <select id="meta-cr-state" class="cr-state-select" bind:value={crStateEdit} disabled={crStateSaveState === "saving"}>
                      {#each legalCrOptionsFor(detail.cr_state) as opt}
                        <option value={opt} disabled={opt === "IN-PROGRESS"}>{opt}</option>
                      {/each}
                    </select>
```

Replace `bind:value={crStateEdit}` with `value={crStateEdit} onchange={(e) => onCrStateChange((e.currentTarget as HTMLSelectElement).value)}`:
```svelte
                    <select id="meta-cr-state" class="cr-state-select" value={crStateEdit} onchange={(e) => onCrStateChange((e.currentTarget as HTMLSelectElement).value)} disabled={crStateSaveState === "saving"}>
                      {#each legalCrOptionsFor(detail.cr_state) as opt}
                        <option value={opt} disabled={opt === "IN-PROGRESS"}>{opt}</option>
                      {/each}
                    </select>
```

- [ ] **Step 4: Add the `onCrStateChange` handler that wraps `saveCrState`**

In the `<script>` section, right after the existing `saveCrState` function (around line 294), add:

```svelte
  /** Autosave hook for the CR State dropdown: updates the bound draft then saves.
   *  Destructive targets (POSTPONED/CANCELED/REOPEN) still route through saveCrState's
   *  existing ConfirmModal branch — autosave is not bypassed for them. */
  async function onCrStateChange(next: string) {
    crStateEdit = next;
    await saveCrState();
  }
```

This keeps `saveCrState`'s REOPEN-arms-confirm logic intact (existing `project-details-reopen.test.mjs` tests still pass — they assert on `saveCrState` internals, not on what triggers it).

- [ ] **Step 5: Remove the entire `pd-drone-flow` block from Identity**

Find (around lines 666–701) the entire `<div class="pd-drone-flow">…</div>` block. Delete the whole thing.

- [ ] **Step 6: Remove now-unused state variables and helpers**

After Step 5 nothing references `selectedSubprojectDrone`, `saveSelectedSubprojectDroneLink`, `saveSelectedSubprojectDroneOwner`, `newDroneLink`, `newDroneSubfolder`, `newDroneOwner`. The drone-state helpers (`saveDroneState`, `droneStateEdits`, `droneStateBusy`, `droneStateError`, `syncDroneStateEdits`, `legalDroneOptionsFor`, `DRONE_STATE_OPTIONS`, `DRONE_NEXT`) are reused by the Sub Project table in Task 6, so KEEP those.

Remove these declarations (around lines 137–141):
```svelte
  let selectedSubprojectDrone = $derived.by(() => {
    if (!detail || selectedSubproject === "all") return null;
    const index = detail.drone_tickets.findIndex((t) => (t.subfolder_name ?? "") === selectedSubproject);
    return index >= 0 ? { ticket: detail.drone_tickets[index], index } : null;
  });
```

Remove (around lines 430–450) `saveSelectedSubprojectDroneLink` and `saveSelectedSubprojectDroneOwner` functions.

Remove (around lines 86–89):
```svelte
  let newDroneLink: string = $state("");
  let newDroneSubfolder: string = $state("");
  let newDroneOwner: string = $state("");
```

Also remove their reset lines in `selectProject` (around line 208):
```svelte
    droneEditIndex = -1; droneError = ""; newDroneLink = ""; newDroneSubfolder = ""; newDroneOwner = "";
```
Replace with:
```svelte
    droneEditIndex = -1; droneError = "";
```

Note: `droneEditIndex`, `droneEditLink`, `droneEditSubfolder`, `droneEditOwner`, `startEditDrone`, `cancelEditDrone`, `saveDrone`, `deleteDrone` were used by the per-index drone edit form inside `pd-drone-flow`. Check whether they're still referenced anywhere after Step 5. They are NOT (the per-index edit form was the only consumer). Remove all of them (declarations ~lines 91–94, functions ~lines 359–387, and their resets in `selectProject` ~line 208).

Keep `addDrone` — Task 6 repurposes it via the master-detail "Add Drone Ticket" button.

- [ ] **Step 7: Run tests — reopen contract must still pass**

Run:
```bash
npm test
```
Expected:
- `project-details-reopen.test.mjs` ALL PASS (saveCrState + REOPEN routing untouched).
- `dashboard-inline-edit.test.mjs` "ProjectDetails source has visible AS_IS command center…" still FAILs (it also asserts `Sub Project (DRONE)` which is Task 6; and `doesNotMatch Save CR State` which is now satisfied — but the test only passes when ALL its asserts pass).
- `as-is-prototype-parity.test.mjs` "AS_IS page titles" still FAILs (waits for Task 6).
- No NEW failures.

- [ ] **Step 8: Run type check**

```bash
npm run check
```
Expected: 0 errors. If errors appear about unused variables that you forgot to remove in Step 6, remove them.

- [ ] **Step 9: Commit**

```bash
cd "D:/Ibrahim/Projects/project_tracker"
git add frontend/src/lib/components/ProjectDetails.svelte
git commit -m "feat(fase1): trim Project Identity — drone block, drone state summary, Selected Sub Project, Save CR State

- Identity no longer hosts drone editing (moves to Sub Project box in a later task).
- CR State now autosaves on dropdown change; destructive transitions still
  route through saveCrState's existing REOPEN/confirm branch (untouched).
- Removed dead state: selectedSubprojectDrone, per-index drone edit drafts,
  newDroneLink/Subfolder/Owner, and the per-index drone edit form helpers."
```

---

## Task 4: CR Link conditional render — input ↔ display (Section 1.4)

**Files:**
- Modify: `frontend/src/lib/components/ProjectDetails.svelte`
- Test: `frontend/tests/project-details-fase1.test.mjs` (new file, created in Step 1)

- [ ] **Step 1: Create the new Fase 1 test file**

Create `frontend/tests/project-details-fase1.test.mjs`:

```js
/**
 * Fase 1 Project Details UI cleanup — source-text assertions.
 *
 * Covers CR Link conditional render (input mode when empty, display mode with
 * copy/open/edit when set), Back to Dashboard wiring, master-detail drone URL
 * panel, drone-state dropdown per row, and reserved-files hide/lock.
 *
 * Source-structure assertions per the project's no-DOM-library convention.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PD = readFileSync(resolve(__dirname, "../src/lib/components/ProjectDetails.svelte"), "utf8");
const FA = readFileSync(resolve(__dirname, "../src/lib/components/FileActions.svelte"), "utf8");
const APP = readFileSync(resolve(__dirname, "../src/App.svelte"), "utf8");
const SPT = readFileSync(resolve(__dirname, "../src/lib/components/SubProjectTable.svelte"), "utf8");

// --- CR Link conditional render (Section 1.4) --------------------------------

test("CR Link input mode is shown when cr_link is empty (crLinkEditing gate)", () => {
  assert.match(PD, /crLinkEditing/);
  // Two-state render: one branch for editing (input), one for display (CR number + actions).
  assert.match(PD, /<input[^>]*placeholder="Paste CR link…"/);
});

test("CR Link display mode has copy + open-external + edit controls", () => {
  // Copy uses navigator.clipboard.writeText
  assert.match(PD, /navigator\.clipboard\.writeText\([^)]*cr_link/);
  // Open external uses window.open with noopener/noreferrer
  assert.match(PD, /window\.open\([^)]+,\s*"_blank",\s*"noopener,noreferrer"\)/);
  // Edit control toggles back to input mode
  assert.match(PD, /crLinkEditing\s*=\s*true/);
});

// --- CR State autosave (Section 1.2) -----------------------------------------

test("CR State select has onchange autosave hook", () => {
  assert.match(PD, /onCrStateChange/);
  assert.match(PD, /async function onCrStateChange/);
});

// --- Back to Dashboard (Section 4) -------------------------------------------

test("ProjectDetails exposes onNavigateDashboard prop and a back button", () => {
  assert.match(PD, /onNavigateDashboard/);
  assert.match(PD, /Back to Dashboard/);
});

test("App.svelte wires onNavigateDashboard to navigate('dashboard')", () => {
  assert.match(APP, /onNavigateDashboard=\{\(\)\s*=>\s*navigate\("dashboard"\)\}/);
});

// --- Sub Project box (Section 3) ---------------------------------------------

test("Sub Project box is titled 'Sub Project (DRONE)'", () => {
  assert.match(PD, /Sub Project \(DRONE\)/);
});

test("SubProjectTable is presentational (no callBridge inside)", () => {
  assert.doesNotMatch(SPT, /callBridge/);
  assert.match(SPT, /onSelectRow/);
  assert.match(SPT, /onChangeDroneState/);
});

test("SubProjectTable no longer has an Owner column", () => {
  assert.doesNotMatch(SPT, /\bOwner\b/);
});

test("ProjectDetails renders Drone URL master-detail panel for selected row", () => {
  assert.match(PD, /selectedSubprojectRow/);
  assert.match(PD, /droneLinkEdit/);
});

// --- Reserved files (Section 9.2) --------------------------------------------

test("FileActions hides project_data.json and notes.md from the list", () => {
  assert.match(FA, /RESERVED_FILES/);
  assert.match(FA, /project_data\.json/);
  assert.match(FA, /notes\.md/);
  // The visible-files filter excludes them.
  assert.match(FA, /RESERVED_FILES\.has\(/);
});

test("FileActions rejects Create and Rename to reserved names", () => {
  // The create path validates against the reserved set.
  assert.match(FA, /RESERVED_FILES\.has\(.*toLowerCase\(\)\)/);
});
```

- [ ] **Step 2: Run the new test file — expect ALL to FAIL**

Run:
```bash
node --import ./tests/register-hooks.mjs --test "tests/project-details-fase1.test.mjs"
```
Expected: every assertion fails (none of the new markup exists yet). This is the RED state for Tasks 4–7.

- [ ] **Step 3: Add `crLinkEditing` state and rewire CR Link block**

In `ProjectDetails.svelte`, find the CR Link state declarations (around line 37):
```svelte
  // ── CR Link edit state ──
  let crLinkEdit: string = $state("");
  type CrLinkSave = "idle" | "saving" | "success" | "error";
  let crLinkSaveState: CrLinkSave = $state("idle");
  let crLinkSaveError: string = $state("");
```

Replace with (add `crLinkEditing` boolean + a copy-success toast state):
```svelte
  // ── CR Link edit state ──
  let crLinkEdit: string = $state("");
  // Fase 1 §1.4: when true, render the URL input; when false, render CR number + copy/open/edit.
  let crLinkEditing: boolean = $state(false);
  let crLinkCopied: boolean = $state(false);
  type CrLinkSave = "idle" | "saving" | "success" | "error";
  let crLinkSaveState: CrLinkSave = $state("idle");
  let crLinkSaveError: string = $state("");
```

- [ ] **Step 4: Initialize `crLinkEditing` on project select**

In `selectProject`, find (around line 232):
```svelte
    if (detail) crLinkEdit = detail.cr_link || "";
```

Replace with:
```svelte
    if (detail) {
      crLinkEdit = detail.cr_link || "";
      crLinkEditing = !detail.cr_link;
      crLinkCopied = false;
    }
```

- [ ] **Step 5: Add `saveCrLinkFromInput`, `copyCrLink`, `openCrLink`, `editCrLink` helpers**

After the existing `saveCrLink` function (around line 268), add:

```svelte
  /** Autosave on blur from input mode. Stays in input mode on error so the user can retry. */
  async function saveCrLinkFromInput() {
    if (!detail) return;
    if (crLinkEdit === detail.cr_link) return;
    await saveCrLink();
    // After a successful save with a non-empty link, switch to display mode.
    if (crLinkSaveState === "success" && crLinkEdit.trim()) {
      crLinkEditing = false;
    }
  }

  async function copyCrLink() {
    if (!detail?.cr_link) return;
    try {
      await navigator.clipboard.writeText(detail.cr_link);
      crLinkCopied = true;
      setTimeout(() => { crLinkCopied = false; }, 2000);
    } catch {
      // Clipboard API unavailable (rare in WebView2). Leave as no-op; user can select+copy manually.
    }
  }

  function openCrLink() {
    if (!detail?.cr_link) return;
    window.open(detail.cr_link, "_blank", "noopener,noreferrer");
  }

  function editCrLink() {
    if (!detail) return;
    crLinkEdit = detail.cr_link || "";
    crLinkEditing = true;
  }
```

- [ ] **Step 6: Replace the CR Link render block**

Find the existing CR Link block (around lines 634–638):
```svelte
                <label class="pd-meta-label" for="meta-cr-link">CR Link</label>
                <div class="cr-link-row">
                  <input id="meta-cr-link" class="cr-link-input" type="url" placeholder="https://cr.example.com/CR..." bind:value={crLinkEdit} disabled={crLinkSaveState === "saving"} />
                  <button class="cr-link-save-btn" onclick={saveCrLink} disabled={crLinkSaveState === "saving" || crLinkEdit === detail.cr_link}>{#if crLinkSaveState === "saving"}⏳{:else}Save{/if}</button>
                </div>
```

Replace with the conditional render:
```svelte
                <label class="pd-meta-label" for="meta-cr-link">CR Link</label>
                {#if crLinkEditing}
                  <input
                    id="meta-cr-link"
                    class="cr-link-input"
                    type="url"
                    placeholder="Paste CR link…"
                    bind:value={crLinkEdit}
                    onblur={saveCrLinkFromInput}
                    disabled={crLinkSaveState === "saving"}
                  />
                  {#if crLinkSaveState === "error"}
                    <span class="cr-link-feedback cr-link-err">✗ {crLinkSaveError}</span>
                  {/if}
                {:else}
                  <div class="pd-cr-link-display">
                    <span class="pd-cr-link-number">{detail.cr_number || detail.cr_link}</span>
                    <button class="pd-icon-btn" type="button" title="Copy CR link" onclick={copyCrLink} aria-label="Copy CR link">📋{#if crLinkCopied} ✓{/if}</button>
                    <button class="pd-icon-btn" type="button" title="Open CR link in browser" onclick={openCrLink} aria-label="Open CR link in browser">↗</button>
                    <button class="pd-icon-btn" type="button" title="Edit CR link" onclick={editCrLink} aria-label="Edit CR link">✎</button>
                  </div>
                {/if}
```

- [ ] **Step 7: Add styles for the new display row**

In the `<style>` block, add (anywhere; suggest near `.cr-link-row`):
```svelte
  .pd-cr-link-display { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
  .pd-cr-link-number { font-size: 12px; font-weight: 700; color: var(--color-ink-strong); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
  .pd-icon-btn { flex: 0 0 auto; width: 26px; height: 26px; padding: 0; border: 1px solid var(--color-border); border-radius: 6px; background: #fff; color: var(--color-ink); font-size: 12px; font-weight: 700; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; gap: 2px; }
  .pd-icon-btn:hover:not(:disabled) { border-color: var(--color-dbs-red); color: var(--color-dbs-red); }
```

- [ ] **Step 8: Run tests — CR Link assertions should PASS, others still RED**

Run:
```bash
node --import ./tests/register-hooks.mjs --test "tests/project-details-fase1.test.mjs"
```
Expected:
- "CR Link input mode…" PASS
- "CR Link display mode has copy + open-external + edit controls" PASS
- "CR State select has onchange autosave hook" PASS (already done in Task 3)
- All others still FAIL (Tasks 5–7 not done).

- [ ] **Step 9: Run full test suite — no regressions in existing tests**

```bash
npm test
```
Expected: existing tests still pass (or fail only on the known Task-1 beacons). No new failures.

- [ ] **Step 10: Commit**

```bash
cd "D:/Ibrahim/Projects/project_tracker"
git add frontend/src/lib/components/ProjectDetails.svelte frontend/tests/project-details-fase1.test.mjs
git commit -m "feat(fase1): CR Link conditional render — input when empty, CR number + copy/open/edit when set

Adds crLinkEditing state (defaults to input mode when no CR link exists).
Display mode shows CR number (or raw link as fallback), copy-to-clipboard,
open-external via window.open, and an edit control that flips back to input
mode. Autosave on blur; stays in input mode on error."
```

---

## Task 5: Back to Dashboard button (Section 4)

**Files:**
- Modify: `frontend/src/App.svelte`
- Modify: `frontend/src/lib/components/ProjectDetails.svelte`
- Test: `npm test`

- [ ] **Step 1: Add `onNavigateDashboard` prop to ProjectDetails**

Find the prop destructure (around line 13):
```svelte
  let { initialPath = null, startNew = false }: { initialPath?: string | null; startNew?: boolean } = $props();
```

Replace with:
```svelte
  let { initialPath = null, startNew = false, onNavigateDashboard }: { initialPath?: string | null; startNew?: boolean; onNavigateDashboard?: () => void } = $props();
```

- [ ] **Step 2: Add the back button bar above Command Center**

Find the very start of the template section (around line 570):
```svelte
<section class="screen active" id="screen-details">
  <div class="panel-card" style="flex:0 0 auto;">
    <div class="toolbar">
```

Insert the back bar between `<section>` and the first `<div class="panel-card">`:
```svelte
<section class="screen active" id="screen-details">
  {#if onNavigateDashboard}
    <div class="pd-back-bar">
      <button type="button" class="pd-back-btn" onclick={() => onNavigateDashboard?.()}>
        <span class="pd-back-arrow" aria-hidden="true">←</span>
        <span>Back to Dashboard</span>
      </button>
    </div>
  {/if}
  <div class="panel-card" style="flex:0 0 auto;">
    <div class="toolbar">
```

- [ ] **Step 3: Add styles for the back bar**

In the `<style>` block, add:
```svelte
  .pd-back-bar { flex: 0 0 auto; display: flex; align-items: center; }
  .pd-back-btn { display: inline-flex; align-items: center; gap: 6px; height: 28px; padding: 0 12px; border: 1px solid var(--color-border); border-radius: 7px; background: #fff; color: var(--color-ink); font-size: 12px; font-weight: 700; cursor: pointer; }
  .pd-back-btn:hover { border-color: var(--color-dbs-red); color: var(--color-dbs-red); }
  .pd-back-arrow { font-weight: 900; }
```

- [ ] **Step 4: Wire `onNavigateDashboard` in App.svelte**

Find (around line 222):
```svelte
        <ProjectDetails initialPath={pendingProjectPath} startNew={startNewProject} />
```

Replace with:
```svelte
        <ProjectDetails initialPath={pendingProjectPath} startNew={startNewProject} onNavigateDashboard={() => navigate("dashboard")} />
```

- [ ] **Step 5: Run tests — back-button assertions PASS**

```bash
node --import ./tests/register-hooks.mjs --test "tests/project-details-fase1.test.mjs"
```
Expected:
- "ProjectDetails exposes onNavigateDashboard prop and a back button" PASS
- "App.svelte wires onNavigateDashboard to navigate('dashboard')" PASS

- [ ] **Step 6: Run full suite + type check**

```bash
npm test
npm run check
```
Expected: no new failures, 0 type errors.

- [ ] **Step 7: Commit**

```bash
cd "D:/Ibrahim/Projects/project_tracker"
git add frontend/src/lib/components/ProjectDetails.svelte frontend/src/App.svelte
git commit -m "feat(fase1): add Back to Dashboard button above Project Command Center

Wires a new onNavigateDashboard prop from App.svelte (calls navigate('dashboard')).
Low-emphasis secondary button — navigation, not a project action."
```

---

## Task 6: Sub Project box — title, remove Owner, refactor SubProjectTable to presentational (Sections 3.1, 3.2, 3.3, 3.4)

This is the largest task. It splits into: (a) refactor `SubProjectTable.svelte` to presentational, (b) rewire `ProjectDetails.svelte` to own drone state + master-detail.

**Files:**
- Modify: `frontend/src/lib/components/SubProjectTable.svelte`
- Modify: `frontend/src/lib/components/ProjectDetails.svelte`
- Test: `npm test`

- [ ] **Step 1: Rewrite `SubProjectTable.svelte` as presentational**

Replace the entire file content with:

```svelte
<script lang="ts">
  /**
   * Sub Project table — Fase 1 §3. Presentational only.
   *
   * Renders one row per sub-project with: name (basename), Drone State dropdown,
   * and an Open Folder action. All bridge interactions are emitted as callbacks
   * to the parent (ProjectDetails), which owns bridge state.
   *
   * Owner column was removed in Fase 1 §3.3 (the model field stays — backend-compat).
   * Drone URL editing happens in the parent's master-detail panel, triggered by
   * row selection (onSelectRow).
   */
  import type { DroneTicket } from "../types";

  interface Props {
    subprojects: string[];
    droneTickets: DroneTicket[];
    selectedRow: string | null;
    droneStateBusyName: string | null;
    droneStateErrorName: Record<string, string>;
    onSelectRow: (name: string) => void;
    onChangeDroneState: (name: string, nextState: string) => void;
    onOpenFolder: (name: string) => void;
    legalDroneOptionsFor: (droneState: string) => string[];
  }
  let {
    subprojects,
    droneTickets,
    selectedRow,
    droneStateBusyName,
    droneStateErrorName,
    onSelectRow,
    onChangeDroneState,
    onOpenFolder,
    legalDroneOptionsFor,
  }: Props = $props();

  interface Row {
    name: string;
    droneState: string;
  }

  const rows = $derived<Row[]>(
    subprojects.map((name) => {
      const drone = droneTickets.find((t) => (t.subfolder_name ?? "") === name);
      return { name, droneState: drone?.drone_state ?? "" };
    }),
  );
</script>

<div class="sp-root">
  {#if subprojects.length === 0}
    <div class="sp-empty">No sub projects yet. Add one above.</div>
  {:else}
    <div class="sp-table" role="table" aria-label="Sub projects">
      <div class="sp-tr sp-th" role="row">
        <span>Sub Project</span><span>Drone State</span><span>Actions</span>
      </div>
      {#each rows as row (row.name)}
        <div class="sp-tr" role="row" class:sp-selected={selectedRow === row.name}>
          <button type="button" class="sp-name-btn" onclick={() => onSelectRow(row.name)} aria-label={`Select ${row.name}`} title={row.name}>
            <span class="sp-name">{row.name}</span>
          </button>
          <span class="sp-state">
            {#if row.droneState}
              <select
                class="sp-state-select"
                value={row.droneState}
                onchange={(e) => onChangeDroneState(row.name, (e.currentTarget as HTMLSelectElement).value)}
                disabled={droneStateBusyName === row.name}
                aria-label={`Drone state for ${row.name}`}
              >
                {#each legalDroneOptionsFor(row.droneState) as opt}
                  <option value={opt} disabled={opt === "IN-PROGRESS"}>{opt}</option>
                {/each}
              </select>
            {:else}
              <span class="sp-muted">—</span>
            {/if}
            {#if droneStateErrorName[row.name]}
              <span class="sp-err" role="alert">✗ {droneStateErrorName[row.name]}</span>
            {/if}
          </span>
          <span class="sp-actions">
            <button class="sp-btn" type="button" onclick={() => onOpenFolder(row.name)}>Open Folder</button>
          </span>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .sp-root { display: flex; flex-direction: column; gap: 6px; }
  .sp-empty { font-size: 10px; font-weight: 700; color: var(--color-muted); padding: 8px; background: var(--color-workspace-panel); border: 1px dashed #D7DCE2; border-radius: 6px; }
  .sp-table { display: flex; flex-direction: column; border: 1px solid #E5E7EB; border-radius: 6px; overflow: hidden; }
  .sp-tr { display: grid; grid-template-columns: 1fr 1.1fr auto; gap: 8px; align-items: center; padding: 7px 8px; border-top: 1px solid #E5E7EB; font-size: 10px; font-weight: 750; color: var(--color-ink); }
  .sp-tr:first-child { border-top: 0; }
  .sp-tr.sp-selected { background: var(--color-soft-pink-surface); }
  .sp-th { background: #111; color: #fff; font-size: 9px; font-weight: 900; text-transform: uppercase; letter-spacing: 0.3px; }
  .sp-name-btn { background: transparent; border: 0; padding: 0; text-align: left; cursor: pointer; min-width: 0; display: flex; }
  .sp-name { font-weight: 900; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--color-ink); }
  .sp-name-btn:hover .sp-name { color: var(--color-dbs-red); }
  .sp-state { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; min-width: 0; }
  .sp-state-select { min-height: 22px; max-width: 100%; padding: 0 6px; border: 1px solid rgba(45,61,52,.35); border-radius: 6px; background: var(--primary-red); color: #fff; font-weight: 900; font-size: 9.5px; cursor: pointer; }
  .sp-state-select:hover { background: var(--red-hover); }
  .sp-state-select:disabled { opacity: 0.55; cursor: not-allowed; }
  .sp-muted { color: var(--color-muted); }
  .sp-err { color: var(--color-dbs-red); font-size: 9px; }
  .sp-actions { display: flex; justify-content: flex-end; }
  .sp-btn { padding: 4px 9px; border: 1px solid #D7DCE2; border-radius: 5px; background: #fff; color: var(--color-ink); font-size: 9px; font-weight: 850; cursor: pointer; white-space: nowrap; }
  .sp-btn:hover { border-color: var(--color-dbs-red); color: var(--color-dbs-red); }
</style>
```

- [ ] **Step 2: In ProjectDetails — rename box title and rewire the SubProjectTable usage**

Find (around lines 739–747):
```svelte
            <div class="pd-section">
              <div class="pd-section-head">
                <h4 class="pd-section-title">Sub Projects</h4>
                <div class="pd-inline-create">
                  <input class="pd-control" placeholder="Sub project name…" bind:value={newSubprojectName} disabled={subprojectBusy} />
                  <button class="pd-command-btn" type="button" onclick={addSubproject} disabled={subprojectBusy || !newSubprojectName.trim()}>Add Sub Project</button>
                </div>
              </div>
              <SubProjectTable projectPath={detail.project_path} {subprojects} droneTickets={detail.drone_tickets} />
              {#if subprojectFeedback}
                <p class:cr-link-ok={subprojectFeedbackKind === "success"} class:cr-link-err={subprojectFeedbackKind === "error"} class="cr-link-feedback">{subprojectFeedbackKind === "success" ? "✓" : "✗"} {subprojectFeedback}</p>
              {/if}
            </div>
```

Replace with:
```svelte
            <div class="pd-section">
              <div class="pd-section-head">
                <h4 class="pd-section-title">Sub Project (DRONE)</h4>
                <div class="pd-inline-create">
                  <input class="pd-control" placeholder="Sub project name…" bind:value={newSubprojectName} disabled={subprojectBusy} />
                  <button class="pd-command-btn" type="button" onclick={addSubproject} disabled={subprojectBusy || !newSubprojectName.trim()}>Add Sub Project</button>
                </div>
              </div>
              <SubProjectTable
                {subprojects}
                droneTickets={detail.drone_tickets}
                selectedRow={selectedSubprojectRow}
                droneStateBusyName={droneStateBusyName}
                droneStateErrorName={droneStateErrorName}
                onSelectRow={onSelectSubprojectRow}
                onChangeDroneState={onChangeSubprojectDroneState}
                onOpenFolder={openSubprojectFolder}
                {legalDroneOptionsFor}
              />
              {#if selectedSubprojectRowDetail}
                {@const ticket = selectedSubprojectRowDetail.ticket}
                <div class="pd-drone-detail">
                  <h5 class="pd-drone-detail-title">{selectedSubprojectRow} · Drone Ticket</h5>
                  <label class="pd-meta-field" for="row-drone-link">
                    <span class="pd-meta-label">Drone URL</span>
                    <input
                      id="row-drone-link"
                      class="cr-link-input"
                      type="url"
                      placeholder="Paste drone URL…"
                      value={droneLinkEdit}
                      oninput={(e) => (droneLinkEdit = (e.currentTarget as HTMLInputElement).value)}
                      onblur={saveDroneLinkFromPanel}
                      disabled={droneLinkBusy}
                    />
                  </label>
                  {#if !ticket}
                    <button class="cr-link-save-btn" type="button" onclick={addDroneForSelectedRow} disabled={droneLinkBusy || !droneLinkEdit.trim()}>Add Drone Ticket</button>
                  {/if}
                  {#if droneLinkError}
                    <span class="cr-link-feedback cr-link-err">✗ {droneLinkError}</span>
                  {/if}
                </div>
              {/if}
              {#if subprojectFeedback}
                <p class:cr-link-ok={subprojectFeedbackKind === "success"} class:cr-link-err={subprojectFeedbackKind === "error"} class="cr-link-feedback">{subprojectFeedbackKind === "success" ? "✓" : "✗"} {subprojectFeedback}</p>
              {/if}
            </div>
```

- [ ] **Step 3: Add the new state variables and helpers in `<script>`**

After the existing `subprojectBusy`/`subprojectFeedback` declarations (around line 116), add:
```svelte
  // ── Sub-project master-detail (Fase 1 §3.4) ──
  let selectedSubprojectRow: string | null = $state(null);
  let droneLinkEdit: string = $state("");
  let droneLinkBusy: boolean = $state(false);
  let droneLinkError: string = $state("");
  // Drone state busy/error keyed by sub-project NAME (not drone ticket index) — Fase 1 §3.4.
  let droneStateBusyName: string | null = $state(null);
  let droneStateErrorName: Record<string, string> = $state({});
```

Replace the existing `droneStateEdits`/`droneStateBusy`/`droneStateError` declarations (around lines 109–111) — these were index-keyed and are now name-keyed. Find:
```svelte
  let droneStateEdits: Record<number, string> = $state({});
  let droneStateBusy: number = $state(-1);
  let droneStateError: Record<number, string> = $state({});
```
Delete those three lines (the name-keyed replacements were added in the block above).

Add the derived detail for the selected row (after `selectedSubprojectRow` declaration):
```svelte
  let selectedSubprojectRowDetail = $derived.by(() => {
    if (!detail || !selectedSubprojectRow) return null;
    const index = detail.drone_tickets.findIndex((t) => (t.subfolder_name ?? "") === selectedSubprojectRow);
    return index >= 0 ? { ticket: detail.drone_tickets[index], index } : { ticket: null, index: -1 };
  });
```

- [ ] **Step 4: Add the new handler functions**

After the existing `addSubproject` function (around line 412), add:
```svelte
  function onSelectSubprojectRow(name: string) {
    selectedSubprojectRow = selectedSubprojectRow === name ? null : name;
    droneLinkEdit = selectedSubprojectRowDetail?.ticket?.drone_link ?? "";
    droneLinkError = "";
  }

  function openSubprojectFolder(name: string) {
    if (!detail || !isPywebviewReady()) return;
    const sep = detail.project_path.includes("\\") ? "\\" : "/";
    const base = detail.project_path.endsWith(sep) ? detail.project_path : detail.project_path + sep;
    void callBridge("folder_open", base + name);
  }

  /** Per-row Drone State dropdown handler. Resolves the drone ticket index from the
   *  sub-project name; autosaves non-destructive, confirms destructive. */
  async function onChangeSubprojectDroneState(name: string, nextState: string) {
    if (!detail || !selectedPath || !isPywebviewReady()) return;
    const index = detail.drone_tickets.findIndex((t) => (t.subfolder_name ?? "") === name);
    if (index < 0) return;
    if (nextState === detail.drone_tickets[index]?.drone_state) return;
    droneStateBusyName = name;
    droneStateErrorName = { ...droneStateErrorName, [name]: "" };
    const resp = await callBridge("drone_update", selectedPath, index, { drone_state: nextState });
    droneStateBusyName = null;
    if (!resp.ok) {
      droneStateErrorName = { ...droneStateErrorName, [name]: resp.error.message };
      return;
    }
    droneStateErrorName = { ...droneStateErrorName, [name]: "" };
    await refreshDetail();
  }

  async function saveDroneLinkFromPanel() {
    if (!detail || !selectedPath || !selectedSubprojectRowDetail) return;
    // No existing ticket for this row → do nothing on blur; the "Add Drone Ticket"
    // button is the only creation path (avoids double-create if user tabs away).
    if (selectedSubprojectRowDetail.index < 0 || !selectedSubprojectRowDetail.ticket) return;
    const next = droneLinkEdit.trim();
    const current = selectedSubprojectRowDetail.ticket.drone_link ?? "";
    if (next === current) return;
    droneLinkBusy = true; droneLinkError = "";
    const resp = await callBridge("drone_update", selectedPath, selectedSubprojectRowDetail.index, { drone_link: next });
    droneLinkBusy = false;
    if (!resp.ok) { droneLinkError = resp.error.message; return; }
    await refreshDetail();
  }

  async function addDroneForSelectedRow() {
    if (!detail || !selectedPath || !selectedSubprojectRow) return;
    const next = droneLinkEdit.trim();
    if (!next) return;
    droneLinkBusy = true; droneLinkError = "";
    const resp = await callBridge("drone_add", selectedPath, { drone_link: next, subfolder_name: selectedSubprojectRow, owner: "" });
    droneLinkBusy = false;
    if (!resp.ok) { droneLinkError = resp.error.message; return; }
    await refreshDetail();
  }
```

- [ ] **Step 5: Remove the now-orphaned `addDrone`, `saveDroneState`, `syncDroneStateEdits` functions**

Find `addDrone` (around lines 346–357), `saveDroneState` (around lines 414–428), and `syncDroneStateEdits` (around lines 509–514). Delete all three. Their responsibilities moved to `onChangeSubprojectDroneState`, `saveDroneLinkFromPanel`, and `addDroneForSelectedRow`. Also delete the call to `syncDroneStateEdits()` in `selectProject` (around line 234) and in `refreshDetail` (around line 458).

- [ ] **Step 6: Add style for the drone detail panel**

In `<style>`, add:
```svelte
  .pd-drone-detail { margin-top: 8px; padding: 10px; border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-workspace); display: flex; flex-direction: column; gap: 6px; }
  .pd-drone-detail-title { margin: 0; font-size: 11px; font-weight: 800; color: var(--color-ink-strong); }
```

- [ ] **Step 7: Run type check — catch any orphaned references**

```bash
npm run check
```
Expected: 0 errors. If errors reference `saveDroneState`, `syncDroneStateEdits`, `droneStateEdits`, `droneStateBusy` (old index-keyed), or `addDrone`, you missed a deletion site — re-read Step 5 and the resets in `selectProject`.

- [ ] **Step 8: Run the Fase 1 tests — most should now PASS**

```bash
node --import ./tests/register-hooks.mjs --test "tests/project-details-fase1.test.mjs"
```
Expected: all Sub Project / SubProjectTable assertions PASS. Files (Task 7) assertions still FAIL.

- [ ] **Step 9: Run full suite — Task-1 beacons should now be GREEN**

```bash
npm test
```
Expected:
- `dashboard-inline-edit.test.mjs` "ProjectDetails source has visible AS_IS command center…" PASS
- `components.test.mjs` datetime test PASS
- `as-is-prototype-parity.test.mjs` "AS_IS page titles" PASS
- `project-details-reopen.test.mjs` all PASS (REOPEN contract untouched)

- [ ] **Step 10: Commit**

```bash
cd "D:/Ibrahim/Projects/project_tracker"
git add frontend/src/lib/components/SubProjectTable.svelte frontend/src/lib/components/ProjectDetails.svelte
git commit -m "feat(fase1): Sub Project box — rename title, drop Owner column, per-row Drone State, master-detail Drone URL

- SubProjectTable refactored to presentational: emits onSelectRow /
  onChangeDroneState / onOpenFolder callbacks; no bridge access inside.
- ProjectDetails owns drone state (now keyed by sub-project NAME), Drone URL
  master-detail panel, and Add Drone Ticket for sub-projects without one."
```

---

## Task 7: Remove the Command Center "Sub Project" dropdown (implication of 1.3)

This dropdown's only consumer was the Identity drone block, which Task 3 removed. Per spec Section 3, it's dead and should go.

**Files:**
- Modify: `frontend/src/lib/components/ProjectDetails.svelte`
- Test: `npm test`

- [ ] **Step 1: Remove the Sub Project `<select>` from the Command Center toolbar**

Find (around lines 583–591):
```svelte
      <label class="pd-command-field pd-command-project" for="pd-subproject-select">
        <span>Sub Project</span>
        <select id="pd-subproject-select" class="pd-control" bind:value={selectedSubproject} disabled={!selectedPath || subprojects.length === 0 || mode === "new"}>
          <option value="all">All Sub Projects</option>
          {#each subprojects as sp}
            <option value={sp}>{sp}</option>
          {/each}
        </select>
      </label>
```

Delete the entire `<label>` block.

- [ ] **Step 2: Remove the now-orphaned `selectedSubproject` state and `subprojects` reset that referenced it**

Find (around line 27):
```svelte
  let selectedSubproject: string = $state("all");
```
Delete the line.

In `selectProject` (around line 204), find:
```svelte
    detail = null; subprojects = []; files = []; notes = ""; selectedSubproject = "all";
```
Replace with:
```svelte
    detail = null; subprojects = []; files = []; notes = "";
```

Note: `subprojects` array itself stays — it's the source for `SubProjectTable` and the inline Add Sub Project flow. Only the `selectedSubproject` filter value is gone.

- [ ] **Step 3: Run type check + tests**

```bash
npm run check
npm test
```
Expected: 0 type errors, all tests still pass.

- [ ] **Step 4: Commit**

```bash
cd "D:/Ibrahim/Projects/project_tracker"
git add frontend/src/lib/components/ProjectDetails.svelte
git commit -m "refactor(fase1): drop dead Command Center Sub Project dropdown

Its only consumer (the Identity drone block) was removed; sub-project
selection now happens by clicking a row in the Sub Project table."
```

---

## Task 8: Project Name autosave on blur (small polish from Section 1)

The Identity box no longer has a "Save identity + schedule" button context that's obvious — the existing `saveMetadata` is still wired to the Schedule section's button. Project Name should also autosave on blur for the "feels automatic" requirement (review point 1.2 spirit).

**Files:**
- Modify: `frontend/src/lib/components/ProjectDetails.svelte`
- Test: visual verification (no new assertion needed; existing tests cover `saveMetadata`)

- [ ] **Step 1: Add `onblur` autosave to the Project Name input**

Find (around line 629):
```svelte
                <input id="meta-name" class="cr-link-input" bind:value={metaNameEdit} disabled={metaSaveState === "saving"} />
```

Replace with:
```svelte
                <input id="meta-name" class="cr-link-input" bind:value={metaNameEdit} onblur={saveMetadataIfChanged} disabled={metaSaveState === "saving"} />
```

- [ ] **Step 2: Add the helper**

After `metadataUnchanged`, add:
```svelte
  /** Autosave identity on blur if anything changed (name, start, end). */
  async function saveMetadataIfChanged() {
    if (!detail) return;
    if (metadataUnchanged(detail)) return;
    await saveMetadata();
  }
```

- [ ] **Step 3: Run tests + type check**

```bash
npm test
npm run check
```
Expected: no regressions.

- [ ] **Step 4: Commit**

```bash
cd "D:/Ibrahim/Projects/project_tracker"
git add frontend/src/lib/components/ProjectDetails.svelte
git commit -m "feat(fase1): autosave Project Name + Schedule on blur

No need for an explicit Save click when the user tabs away from the
Project Name field — saveMetadataIfChanged no-ops when nothing changed."
```

---

## Task 9: Activity History fixed-height scroll (Section 7.1)

**Files:**
- Modify: `frontend/src/lib/components/ProjectDetails.svelte`
- Test: `frontend/tests/project-details-fase1.test.mjs` (add assertion)

- [ ] **Step 1: Add the failing assertion to the Fase 1 test file**

In `frontend/tests/project-details-fase1.test.mjs`, add at the bottom:
```js
// --- Activity History fixed-height scroll (Section 7.1) ---------------------

test("Activity History list is wrapped in a fixed-height scroll container", () => {
  assert.match(PD, /pd-history-scroll/);
  assert.match(PD, /\.pd-history-scroll\s*\{[^}]*max-height:\s*280px/s);
  assert.match(PD, /\.pd-history-scroll\s*\{[^}]*overflow-y:\s*auto/s);
});
```

- [ ] **Step 2: Run the new test — expect FAIL**

```bash
node --import ./tests/register-hooks.mjs --test "tests/project-details-fase1.test.mjs"
```
Expected: the new "Activity History list…" test FAILs.

- [ ] **Step 3: Wrap the history `<ol>` in a scroll container**

Find (around lines 768–778):
```svelte
            <div class="pd-section">
              <h4 class="pd-section-title">Activity History</h4>
              {#if detail.history?.length}
                <ol class="pd-history-list">
                  {#each detail.history as entry}
                    <li class="pd-history-item"><time>{entry.timestamp}</time><strong>{entry.action}</strong><span>{entry.detail}</span><small>{entry.user}</small></li>
                  {/each}
                </ol>
              {:else}
                <p class="pd-muted">No activity yet.</p>
              {/if}
            </div>
```

Replace with:
```svelte
            <div class="pd-section">
              <h4 class="pd-section-title">Activity History</h4>
              {#if detail.history?.length}
                <div class="pd-history-scroll">
                  <ol class="pd-history-list">
                    {#each detail.history as entry}
                      <li class="pd-history-item"><time>{entry.timestamp}</time><strong>{entry.action}</strong><span>{entry.detail}</span><small>{entry.user}</small></li>
                    {/each}
                  </ol>
                </div>
              {:else}
                <p class="pd-muted">No activity yet.</p>
              {/if}
            </div>
```

- [ ] **Step 4: Add the CSS**

In `<style>`, add:
```svelte
  .pd-history-scroll { max-height: 280px; overflow-y: auto; padding-right: 4px; }
```

- [ ] **Step 5: Run the test — expect PASS**

```bash
node --import ./tests/register-hooks.mjs --test "tests/project-details-fase1.test.mjs"
```
Expected: "Activity History list…" PASS.

- [ ] **Step 6: Commit**

```bash
cd "D:/Ibrahim/Projects/project_tracker"
git add frontend/src/lib/components/ProjectDetails.svelte frontend/tests/project-details-fase1.test.mjs
git commit -m "feat(fase1): cap Activity History at 280px with internal scroll

Prevents the history list from stretching the right pane when a project
has many history entries; matches the visual height of Files/Notes boxes."
```

---

## Task 10: Files scroll + hide/lock reserved files (Section 6)

**Files:**
- Modify: `frontend/src/lib/components/FileActions.svelte`
- Test: `frontend/tests/project-details-fase1.test.mjs` (assertions already added in Task 4 Step 1)

The Fase 1 test file already has the FileActions assertions (RESERVED_FILES, project_data.json, notes.md, has+toLowerCase). They currently FAIL.

- [ ] **Step 1: Add the RESERVED_FILES constant**

In `FileActions.svelte`, after the imports (around line 36), add:
```svelte
  /** System files managed by the app — hidden from the list and locked from
   *  Create/Rename (Fase 1 §9.2). Case-insensitive: Windows is case-insensitive. */
  const RESERVED_FILES = new Set(["project_data.json", "notes.md"]);
```

- [ ] **Step 2: Filter reserved files from the rendered list**

Find (around line 282–284):
```svelte
  <div class="fa-block">
    <span class="fa-block-label">Files</span>
    {#if files.length === 0}
      <p class="fa-muted">No files.</p>
    {:else}
      <ul class="fa-file-list">
        {#each files as f (f.path)}
```

Replace with (introduce `visibleFiles` derived and iterate that):
```svelte
  <div class="fa-block">
    <span class="fa-block-label">Files</span>
    {#if visibleFiles.length === 0}
      <p class="fa-muted">No files.</p>
    {:else}
      <ul class="fa-file-list">
        {#each visibleFiles as f (f.path)}
```

Add the derived near the other `$derived` declarations (after `deleteLockMsg`, around line 76):
```svelte
  let visibleFiles = $derived(files.filter((f) => !RESERVED_FILES.has(f.name.toLowerCase())));
```

- [ ] **Step 3: Add the scroll CSS to `.fa-file-list`**

Find the existing `.fa-file-list` rule (around line 438):
```svelte
  .fa-file-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin: 0;
    padding: 0;
    list-style: none;
  }
```

Replace with:
```svelte
  .fa-file-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin: 0;
    padding: 0;
    list-style: none;
    max-height: 320px;
    overflow-y: auto;
    padding-right: 4px;
  }
```

- [ ] **Step 4: Reject Create to a reserved name**

Find `createFile` (around lines 105–122). After the `if (!filename)` block, add a reserved-name check:

```svelte
  async function createFile() {
    clearFeedback();
    const filename = newFilename.trim();
    if (!filename) {
      errorMessage = "Enter a file name before creating.";
      return;
    }
    if (RESERVED_FILES.has(filename.toLowerCase())) {
      errorMessage = "notes.md and project_data.json are reserved system files and cannot be created here.";
      return;
    }
    busy = true;
```

Apply the same check in `createFromTemplate` (around lines 125–146), after the `if (!templateName)` block:
```svelte
    if (RESERVED_FILES.has(templateName.toLowerCase())) {
      errorMessage = "notes.md and project_data.json are reserved system files and cannot be created here.";
      return;
    }
```

- [ ] **Step 5: Reject Rename to a reserved name**

Find `requestRename` (around lines 175–192). After the `if (trimmed === file.name)` check, add:
```svelte
    if (RESERVED_FILES.has(trimmed.toLowerCase())) {
      errorMessage = "Cannot rename to a reserved system file name.";
      return;
    }
```

- [ ] **Step 6: Run the Fase 1 tests — FileActions assertions PASS**

```bash
node --import ./tests/register-hooks.mjs --test "tests/project-details-fase1.test.mjs"
```
Expected: ALL Fase 1 tests now PASS.

- [ ] **Step 7: Run full suite + type check**

```bash
npm test
npm run check
```
Expected: every test green, 0 type errors.

- [ ] **Step 8: Commit**

```bash
cd "D:/Ibrahim/Projects/project_tracker"
git add frontend/src/lib/components/FileActions.svelte
git commit -m "feat(fase1): scroll Files list at 320px; hide + lock notes.md and project_data.json

Reserved system files are filtered from the rendered list (case-insensitive)
and rejected at Create / Create-from-template / Rename. Backend stays the
authoritative guard; this is UX-level foot-gun prevention."
```

---

## Task 11: Final verification — full green suite, type check, build

**Files:** none (verification only)

- [ ] **Step 1: Run the complete frontend test suite**

```bash
cd "D:/Ibrahim/Projects/project_tracker/frontend"
npm test
```
Expected: ALL tests pass.

- [ ] **Step 2: Run the type check**

```bash
npm run check
```
Expected: 0 errors, 0 warnings.

- [ ] **Step 3: Run the production build**

```bash
npm run build
```
Expected: vite build succeeds; no errors.

- [ ] **Step 4: Run the Python backend contract guard**

```bash
cd "D:/Ibrahim/Projects/project_tracker"
python -m pytest tests/test_bridge_contract_guard.py -v
```
Expected: PASS. Fase 1 introduced no new bridge method names, so this guard must still pass unchanged.

- [ ] **Step 5: Manual smoke test (if a desktop run is available)**

Launch the app, open a project with sub-projects, and verify:
- No "Save CR State" button; changing CR State dropdown saves immediately; changing to POSTPONED/CANCELED shows the ConfirmModal.
- CR Link shows input when empty, CR number + copy/open/edit when set.
- "Back to Dashboard" returns to the dashboard.
- Sub Project box titled "Sub Project (DRONE)"; no Owner column; clicking a row shows the Drone URL panel below the table; changing a row's Drone State dropdown saves.
- Activity History scrolls internally if long.
- Files list scrolls internally if many; `notes.md` and `project_data.json` are not listed; creating/renaming to those names is rejected.
- Implementation Plan section is gone.

- [ ] **Step 6: Final commit (if Step 5 surfaced any tweaks)**

If smoke test surfaced small CSS or copy fixes, commit them with a clear message. Otherwise skip — Task 10's commit was the last code commit.

---

## Self-Review notes (run after writing, before handoff)

**Spec coverage check:**
- §1.1 (remove Selected Sub Project) → Task 3 Step 1 ✓
- §1.2 (remove Save CR State button, autosave) → Task 3 Steps 3–4 ✓
- §1.3 (remove Drone block) → Task 3 Step 5 ✓
- §1.4 (CR Link conditional render) → Task 4 ✓
- §2 (remove Implementation Plan) → Task 2 ✓
- §3.1 (title rename) → Task 6 Step 2 ✓
- §3.2 (basename only — already correct, audit) → Task 6 Step 1 (rewritten component shows `row.name` directly) ✓
- §3.3 (remove Owner) → Task 6 Step 1 (rewritten component has no Owner) ✓
- §3.4 (per-row Drone State + master-detail) → Task 6 ✓
- §4 (Back to Dashboard) → Task 5 ✓
- §7.1 (Activity History scroll) → Task 9 ✓
- §9.1 (Files scroll) → Task 10 Step 3 ✓
- §9.2 (hide + lock reserved) → Task 10 Steps 1–2, 4–5 ✓
- Spec Section 3's "remove Command Center Sub Project dropdown" implication → Task 7 ✓
- Spec Section 1's "Project Name autosave" polish → Task 8 ✓

**Placeholder scan:** none — every code step shows the actual code.

**Type consistency:** `selectedSubprojectRow` / `droneStateBusyName` / `droneStateErrorName` / `droneLinkEdit` / `droneLinkBusy` / `droneLinkError` are declared once and used consistently in Tasks 6–7. `visibleFiles` declared in Task 10 Step 2, used in Step 2. `RESERVED_FILES` declared in Task 10 Step 1, used in Steps 2, 4, 5. `onNavigateDashboard` declared in Task 5 Step 1, used in Step 2, wired in Step 4.

**Ordering:** Task 1 (test anchors) before any component edit means every subsequent task has a clear red→green signal. Task 2 first (smallest, isolated). Task 3 (Identity removals) before Task 4 (CR Link render — needs the cleaned Identity). Task 5 (Back button) is independent but small, comes before the big Task 6. Task 7 (dropdown removal) depends on Task 3's drone-block removal. Task 8 (polish) after the structural work. Tasks 9 and 10 are leaf CSS/logic changes.
