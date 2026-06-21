import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const src = (path) => readFileSync(resolve(__dirname, path), "utf8");

const APP = src("../src/App.svelte");
const HEADER = src("../src/lib/components/Header.svelte");
const SIDEBAR = src("../src/lib/components/Sidebar.svelte");
const DASHBOARD = src("../src/lib/components/Dashboard.svelte");
const PROJECT_DETAILS = src("../src/lib/components/ProjectDetails.svelte");
const SECOND_BRAIN = src("../src/lib/components/SecondBrain.svelte");
const REPORT = src("../src/lib/components/Report.svelte");
const AUTOMATIONS = src("../src/lib/components/Automations.svelte");
const SETTINGS = src("../src/lib/components/Settings.svelte");
const STYLES = src("../src/styles.css");

test("AS_IS shell tokens and classes are present", () => {
  assert.match(STYLES, /--black-chrome:\s*#0A0A0B/);
  assert.match(STYLES, /--primary-red:\s*#B91C1C/);
  assert.match(STYLES, /--header-h:\s*58px/);
  assert.match(STYLES, /--sidebar-expanded:\s*160px/);
  assert.match(APP, /class="app-shell"/);
  assert.match(APP, /<main class="main">/);
  assert.match(APP, /class="app-content"/);
});

test("AS_IS header and sidebar labels are present", () => {
  for (const title of ["Dashboard.", "Project Details.", "Second Brain.", "Report.", "Automations.", "Settings."]) {
    assert.match(HEADER, new RegExp(title.replace(".", "\\.")));
  }
  for (const label of ["Project Tracker", "Dashboard", "Project Details", "Second Brain", "Report", "Automations", "Settings"]) {
    assert.match(SIDEBAR, new RegExp(label));
  }
});

test("AS_IS page titles and core sections are present", () => {
  for (const label of ["No", "Project", "Sub Project", "Start", "End", "Drone Ticket", "Drone State", "CR Number", "CR State"]) {
    assert.match(DASHBOARD, new RegExp(label));
  }
  for (const label of ["Project Command Center", "Project Identity", "Schedule", "Sub Project \\(DRONE\\)", "Files", "Notes", "Activity History"]) {
    assert.match(PROJECT_DETAILS, new RegExp(label));
  }
  for (const label of ["Second Brain", "Notes", "Link Bank", "Backlinks", "Recent Activity"]) {
    assert.match(SECOND_BRAIN, new RegExp(label));
  }
  for (const label of ["Report Table", "Total CR", "Folder: UAT_PREPARE", "Folder: PROD_READY", "Folder: IMPLEMENTED", "Folder: POSTPONED"]) {
    assert.match(REPORT, new RegExp(label));
  }
  assert.doesNotMatch(DASHBOARD, /dash-group-cell/);
  assert.doesNotMatch(DASHBOARD, /dashboard-command-strip/);
  for (const label of ["Automation Center", "Outlook", "Teams", "Reminder", "Rules Engine"]) {
    assert.match(AUTOMATIONS, new RegExp(label));
  }
  for (const label of ["Settings", "General", "Behavior", "Paths", "Help Center"]) {
    assert.match(SETTINGS, new RegExp(label));
  }
});
