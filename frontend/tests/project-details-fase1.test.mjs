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
  // Displays copy, open, and edit icons (as button + SVG nodes now)
  assert.match(PD, /aria-label="Copy CR link"[^>]*>\s*<svg/);
  assert.match(PD, /aria-label="Open CR link in browser"[^>]*>\s*<svg/);
  assert.match(PD, /aria-label="Edit CR link"[^>]*>\s*<svg/);
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
  assert.match(PD, /<svg[^>]*pd-icon-back/);
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
