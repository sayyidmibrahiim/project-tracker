import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const src = (path) => readFileSync(resolve(__dirname, path), "utf8");

const APP = src("../src/App.svelte");
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
  assert.match(STYLES, /--sidebar-expanded:\s*160px/);
  assert.match(APP, /class="app-shell"/);
  assert.match(APP, /<main class="main">/);
  assert.match(APP, /class="app-content"/);
  // D-0011: the red app-header is gone; page headers own the titles.
  assert.doesNotMatch(STYLES, /\.app-header/);
});

test("Page header titles are present per page (red app-header removed, D-0011)", () => {
  const pages = [
    [DASHBOARD, "Dashboard"],
    [PROJECT_DETAILS, "Project Details"],
    [SECOND_BRAIN, "Second Brain"],
    [REPORT, "Report"],
    [AUTOMATIONS, "Automations"],
    [SETTINGS, "Settings"],
  ];
  for (const [source, title] of pages) {
    assert.match(source, new RegExp(title));
  }
});

test("AS_IS page titles and core sections are present", () => {
  for (const label of ["No", "Project", "Drone", "Start", "End", "Drone Ticket", "Drone State", "CR Number", "CR State"]) {
    assert.match(DASHBOARD, new RegExp(label));
  }
  for (const label of ["Project Command Center", "Project Identity", "Schedule", "Drone Tickets", "Files", "Notes", "Activity History"]) {
    assert.match(PROJECT_DETAILS, new RegExp(label));
  }
  for (const label of ["Second Brain", "Notes", "Link Bank", "Backlinks", "Recent Activity"]) {
    assert.match(SECOND_BRAIN, new RegExp(label));
  }
  for (const label of ["Total", "UAT Prepare", "Prod Ready", "Implemented", "Postponed"]) {
    assert.match(REPORT, new RegExp(label));
  }
  assert.doesNotMatch(DASHBOARD, /dash-group-cell/);
  assert.doesNotMatch(DASHBOARD, /dashboard-command-strip/);
  for (const label of ["Outlook", "Teams", "Reminder", "Rules Engine"]) {
    assert.match(AUTOMATIONS, new RegExp(label));
  }
  for (const label of ["Settings", "General", "Behavior", "Paths", "Help Center"]) {
    assert.match(SETTINGS, new RegExp(label));
  }
});
