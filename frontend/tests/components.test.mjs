/**
 * Component render tests for ConfirmModal and DisabledHint (Task 1.4).
 *
 * Verified via Svelte SSR (see ssrHelper.mjs) because no DOM testing library
 * is installed and dependencies are frozen by the release-candidate rules.
 *
 * Covers:
 *  - ConfirmModal irreversible rendering for `reversible="unknown"` (Req 3.3)
 *  - ConfirmModal reversible/irreversible binary statement + target naming (Req 3.2)
 *  - ConfirmModal renders distinct Cancel and confirm controls that back the
 *    confirm-vs-cancel callbacks (Req 3.1, 3.4)
 *  - DisabledHint renders a disabled, non-interactive control whose message
 *    names the Folder_State lock (Req 3.5) or the deferred status (Req 3.6)
 *
 * Validates: Requirements 3.2, 3.3, 3.4, 3.5, 3.6
 */
import { test, after } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { render } from "svelte/server";
import { renderComponent, cleanup } from "./ssrHelper.mjs";
import { lockReason } from "../src/lib/folderLocks.ts";

const CONFIRM = "../src/lib/components/ConfirmModal.svelte";
const DISABLED = "../src/lib/components/DisabledHint.svelte";
const AUTOMATIONS = "../src/lib/components/Automations.svelte";
const AUTOMATIONS_OUTLOOK = "../src/lib/components/AutomationsOutlook.svelte";
const EMAIL_TEMPLATE_DIALOG = "../src/lib/components/EmailTemplateDialog.svelte";
const NOTES_EDITOR = "../src/lib/components/NotesEditor.svelte";
const NEW_PROJECT_FORM = "../src/lib/components/NewProjectForm.svelte";
const SUB_PROJECT_TABLE = "../src/lib/components/SubProjectTable.svelte";
const DASHBOARD = "../src/lib/components/Dashboard.svelte";
const DASHBOARD_ROW_MENU = "../src/lib/components/DashboardRowMenu.svelte";
const FIRST_RUN_SETUP = "../src/lib/components/FirstRunSetup.svelte";
const PROJECT_DETAILS_SRC = "../src/lib/components/ProjectDetails.svelte";

const noop = () => {};

after(() => cleanup());

function confirmProps(overrides) {
  return {
    title: "Delete project",
    actionLabel: "Delete",
    targetName: "Acme-Migration",
    reversible: false,
    onConfirm: noop,
    onCancel: noop,
    ...overrides,
  };
}

// --- ConfirmModal: reversibility (Req 3.2, 3.3) ------------------------------

test('ConfirmModal renders "irreversible" when reversible="unknown" (Req 3.3)', async () => {
  const body = await renderComponent(CONFIRM, confirmProps({ reversible: "unknown" }));
  assert.match(body, /irreversible/i);
  assert.doesNotMatch(body, /This action is reversible/i);
});

test('ConfirmModal renders "irreversible" when reversible=false', async () => {
  const body = await renderComponent(CONFIRM, confirmProps({ reversible: false }));
  assert.match(body, /This action is irreversible/i);
});

test('ConfirmModal renders "reversible" when reversible=true', async () => {
  const body = await renderComponent(CONFIRM, confirmProps({ reversible: true }));
  assert.match(body, /This action is reversible/i);
  assert.doesNotMatch(body, /This action is irreversible/i);
});

// --- ConfirmModal: action/target statement (Req 3.2) -------------------------

test("ConfirmModal states the action label, title, and target name (Req 3.2)", async () => {
  const body = await renderComponent(
    CONFIRM,
    confirmProps({ title: "Delete project", actionLabel: "Delete", targetName: "Acme-Migration" }),
  );
  assert.match(body, /Delete project/);
  assert.match(body, /Acme-Migration/);
  assert.match(body, /Delete/);
});

// --- ConfirmModal: distinct confirm vs cancel controls (Req 3.1, 3.4) --------

test("ConfirmModal renders distinct Cancel and confirm controls (Req 3.1, 3.4)", async () => {
  const body = await renderComponent(CONFIRM, confirmProps({ actionLabel: "Delete" }));
  // A dedicated Cancel control backs onCancel (dismiss leaves state unchanged).
  assert.match(body, /confirm-btn-cancel/);
  assert.match(body, /Cancel/);
  // A dedicated proceed control labelled with the action backs onConfirm.
  assert.match(body, /confirm-btn-proceed/);
  // Irreversible actions get the irreversible-styled proceed button.
  assert.match(body, /irreversible/);
});

test("ConfirmModal markup contains no bridge/window access (Req 3.1)", async () => {
  const body = await renderComponent(CONFIRM, confirmProps({}));
  assert.doesNotMatch(body, /pywebview/i);
  assert.doesNotMatch(body, /callBridge/i);
});

// --- DisabledHint: message naming the lock (Req 3.5) -------------------------

test("DisabledHint renders a disabled, non-interactive control (Req 3.5)", async () => {
  const message = lockReason("IMPLEMENTED", "rename_project");
  const body = await renderComponent(DISABLED, {
    label: "Rename",
    message,
    variant: "lock",
  });
  assert.match(body, /disabled/);
  assert.match(body, /aria-disabled="true"/);
  assert.match(body, /Rename/);
});

test("DisabledHint message names the Folder_State lock (Req 3.5)", async () => {
  const message = lockReason("PROD_READY", "delete_project");
  const body = await renderComponent(DISABLED, {
    label: "Delete",
    message,
    variant: "lock",
  });
  assert.match(body, /PROD_READY/);
  assert.match(body, /partial lock/i);
});

test("DisabledHint renders the deferred variant message (Req 3.6)", async () => {
  const body = await renderComponent(DISABLED, {
    label: "Download emails",
    message: "This capability is not yet available.",
    variant: "deferred",
  });
  assert.match(body, /not yet available/i);
  assert.match(body, /data-variant="deferred"/);
});

// --- Automations: PRD §16.2 tab order + Outlook scaffold ---------------------

/**
 * Render a component (and any child `.svelte`/`.ts` imports) by importing it
 * directly so the svelte-loader keeps the real source URL and relative imports
 * resolve against the source tree. The temp-file `renderComponent` helper cannot
 * do this for parent components or components that import `.ts` modules (see
 * tests/svelte-loader.mjs), so these tests use the loader-backed import path.
 */
async function renderViaLoader(relativeSveltePath, props = {}) {
  const mod = await import(relativeSveltePath);
  const { body } = render(mod.default, { props });
  return body;
}

test("Automations renders AS_IS tab order with Outlook first and mounts the Outlook scaffold", async () => {
  const body = await renderViaLoader(AUTOMATIONS, {});
  const outlook = body.indexOf("Outlook");
  const teams = body.indexOf("Teams");
  const reminder = body.indexOf("Reminder");
  const rules = body.indexOf("Rules Engine");
  assert.ok(outlook >= 0, "Outlook tab is rendered");
  assert.ok(teams > outlook, "Teams follows Outlook");
  assert.ok(reminder > teams, "Reminder follows Teams");
  assert.ok(rules > reminder, "Rules Engine follows Reminder");
  assert.match(body, /Automation Center/);
  assert.match(body, /SEND AUTOMATION/);
  assert.doesNotMatch(body, /Project-scoped/);
});

test("AutomationsOutlook renders the two-column send/download scaffold and draft-first safety copy", async () => {
  const body = await renderViaLoader(AUTOMATIONS_OUTLOOK, {});
  assert.match(body, /SEND AUTOMATION/);
  assert.match(body, /DOWNLOAD AUTOMATION/);
  assert.match(body, /Downloaded Emails/);
  assert.match(body, /Draft-first Outlook is the safe default/);
  assert.match(body, /ACK_UAT/);
  assert.match(body, /APRVL_CR/);
});

test("EmailTemplateDialog renders the PRD §16.3 two-column editor for a fixed category", async () => {
  const body = await renderViaLoader(EMAIL_TEMPLATE_DIALOG, {
    categoryCode: "ACK_UAT",
    onClose: () => {},
  });
  assert.match(body, /ACK_UAT/);
  assert.match(body, /Subject Template/);
  assert.match(body, /Body Template/);
  assert.match(body, /Active Conditions/);
  assert.match(body, /Condition Preview/);
  // Placeholder chips and the always-present condition controls render.
  assert.match(body, /\{PROJECT_NAME\}/);
  assert.match(body, /\{IMPLEMENTATION_PLAN\}/);
  assert.match(body, /\+ Add Condition/);
  assert.match(body, /No conditions defined/);
  // Draft-first mode options render (send-immediately is an explicit opt-in).
  assert.match(body, /Send Immediately/);
  // Footer controls.
  assert.match(body, /Save/);
  assert.match(body, /Cancel/);
});

test("NotesEditor renders the markdown toolbar, edit/preview toggle, and autosave status", async () => {
  const body = await renderViaLoader(NOTES_EDITOR, {
    projectPath: "/Temp_Root/2026/UAT_PREPARE/Acme-Migration",
    initialNotes: "# Hi",
  });
  // Toolbar (insert-at-caret) controls.
  assert.match(body, /title="Bold"/);
  assert.match(body, /title="Heading 1"/);
  assert.match(body, /title="Inline code"/);
  assert.match(body, /title="Link"/);
  // Edit/Preview toggle.
  assert.match(body, />Edit</);
  assert.match(body, />Preview</);
  // Default edit mode shows the textarea; autosave (not an explicit Save button).
  assert.match(body, /ne-textarea/);
  assert.match(body, /Autosave on/);
  assert.doesNotMatch(body, /Save Notes/);
});

test("NewProjectForm renders the PRD §12.4 create form (name, year, disabled until valid)", async () => {
  const body = await renderViaLoader(NEW_PROJECT_FORM, {
    yearOptions: ["2026", "2025"],
    defaultYear: "2026",
    onCancel: () => {},
    onCreated: () => {},
  });
  assert.match(body, /New Project/);
  assert.match(body, /Project Name/);
  assert.match(body, /Create Project/);
  assert.match(body, /Cancel/);
  // Year options render.
  assert.match(body, />2026</);
  assert.match(body, />2025</);
  // With an empty name, Save (Create Project) is disabled.
  assert.match(body, /disabled/);
});

test("SubProjectTable renders the PRD §12.10 columns and maps drones to sub-projects", async () => {
  const body = await renderViaLoader(SUB_PROJECT_TABLE, {
    projectPath: "/Temp_Root/2026/UAT_PREPARE/Acme-Migration",
    subprojects: ["alpha", "beta"],
    droneTickets: [
      { subfolder_name: "alpha", drone_link: "https://drone/DRN-1", drone_state: "UAT", owner: "Ops" },
    ],
  });
  // Column headers.
  assert.match(body, /Sub Project/);
  assert.match(body, /Drone Ticket/);
  assert.match(body, /Drone State/);
  assert.match(body, /Owner/);
  // Mapped sub-project shows its drone link/state/owner.
  assert.match(body, /alpha/);
  assert.match(body, /https:\/\/drone\/DRN-1/);
  assert.match(body, /UAT/);
  assert.match(body, /Ops/);
  // Unmapped sub-project still renders with em-dash placeholders.
  assert.match(body, /beta/);
  assert.match(body, /Open Folder/);
});

test("SubProjectTable renders an empty state when there are no sub-projects", async () => {
  const body = await renderViaLoader(SUB_PROJECT_TABLE, {
    projectPath: "/Temp_Root/2026/UAT_PREPARE/Acme-Migration",
    subprojects: [],
    droneTickets: [],
  });
  assert.match(body, /No sub projects/);
});

test("Dashboard renders the PRD §11.15 summary table shell and touches no bridge at render", async () => {
  const body = await renderViaLoader(DASHBOARD, { selectedYear: "2026", searchQuery: "" });
  assert.match(body, /CR - Project Summary Table/);
  // Column headers (real PRD §11.15 columns).
  assert.match(body, /Main Project/);
  assert.match(body, /Sub Project/);
  assert.match(body, /Drone Ticket/);
  assert.match(body, /Drone State/);
  assert.match(body, /CR State/);
  // SSR (no $effect/bridge) → no pywebview access at render.
  assert.doesNotMatch(body, /pywebview/i);
});

test("DashboardRowMenu renders a closed ⋮ trigger with no menu open at render", async () => {
  const body = await renderViaLoader(DASHBOARD_ROW_MENU, {
    projectPath: "/Temp_Root/2026/UAT_PREPARE/Acme-Migration",
    projectState: "UAT_PREPARE",
    projectName: "Acme-Migration",
    onOpenDetails: () => {},
    onChanged: () => {},
  });
  assert.match(body, /Row actions/);
  // Menu items only render once opened (open=false at render).
  assert.doesNotMatch(body, /Open Project Folder/);
  assert.doesNotMatch(body, /Project Details/);
});

test("DashboardRowMenu source carries only Details + Delete — no transitions or Open Folder", () => {
  const src = readFileSync(
    fileURLToPath(new URL("../src/lib/components/DashboardRowMenu.svelte", import.meta.url)),
    "utf8",
  );
  // The trimmed menu keeps Project Details and Delete only.
  assert.match(src, /Project Details/);
  assert.match(src, /Delete project…/);
  // Folder transitions and Open Project Folder were removed (auto-move + name-click cover them).
  assert.doesNotMatch(src, /ProjectTransitions/);
  assert.doesNotMatch(src, /Open Project Folder/);
  assert.doesNotMatch(src, /project_open_folder/);
});

test("FirstRunSetup renders the root-folder setup dialog (PRD §11.3)", async () => {
  const body = await renderViaLoader(FIRST_RUN_SETUP, { onSaved: () => {} });
  assert.match(body, /First-Run Setup/);
  assert.match(body, /root folder/i);
  assert.match(body, /Continue/);
});

// --- Project Details: MVP-1 date/plan editor (P1-6, P1-12) ------------------

test("ProjectDetails source includes datetime-local editors and saves date fields through project_update", () => {
  const src = readFileSync(
    fileURLToPath(new URL(PROJECT_DETAILS_SRC, import.meta.url)),
    "utf8",
  );

  assert.match(src, /type="datetime-local"/);
  assert.match(src, /metaStartEdit/);
  assert.match(src, /metaEndEdit/);
  assert.match(src, /start_datetime:\s*fromDatetimeLocal\(metaStartEdit\)/);
  assert.match(src, /end_datetime:\s*fromDatetimeLocal\(metaEndEdit\)/);
  assert.match(src, /implementation_plan:\s*metaPlanEdit/);
});

test("ProjectDetails source follows the prototype Project Command Center structure", () => {
  const src = readFileSync(
    fileURLToPath(new URL(PROJECT_DETAILS_SRC, import.meta.url)),
    "utf8",
  );

  assert.match(src, /screen-details/);
  assert.match(src, /Project Command Center/);
  assert.match(src, /Sub Project/);
  assert.match(src, /Project Identity/);
  assert.match(src, /Schedule/);
  assert.match(src, /Activity History/);
  assert.match(src, /Add Sub Project/);
  assert.match(src, /openProjectFolder/);
  assert.match(src, /requestTopDelete/);
  assert.doesNotMatch(src, /pd-list-panel/);
  assert.doesNotMatch(src, /ProjectTransitions/);
  assert.doesNotMatch(src, /Project Actions/);
  assert.doesNotMatch(src, /Folder Transitions/);
});
