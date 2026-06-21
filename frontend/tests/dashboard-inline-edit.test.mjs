import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const DASHBOARD = readFileSync(resolve(__dirname, "../src/lib/components/Dashboard.svelte"), "utf8");
const PROJECT_DETAILS = readFileSync(resolve(__dirname, "../src/lib/components/ProjectDetails.svelte"), "utf8");

function extractFunction(source, name) {
  const re = new RegExp(`function\\s+${name}\\s*\\(`);
  const m = re.exec(source);
  if (!m) return null;
  let i = source.indexOf("(", m.index);
  if (i < 0) return null;
  let parenDepth = 0;
  for (; i < source.length; i++) {
    const ch = source[i];
    if (ch === "(") parenDepth++;
    else if (ch === ")") {
      parenDepth--;
      if (parenDepth === 0) break;
    }
  }
  i = source.indexOf("{", i);
  if (i < 0) return null;
  let depth = 0;
  const start = i;
  for (; i < source.length; i++) {
    const ch = source[i];
    if (ch === "{") depth++;
    else if (ch === "}") {
      depth--;
      if (depth === 0) return source.slice(start, i + 1);
    }
  }
  return null;
}

test("Dashboard waits briefly for pywebview before declaring BRIDGE_UNAVAILABLE", () => {
  assert.match(DASHBOARD, /waitForPywebviewReady/);
  const fn = extractFunction(DASHBOARD, "loadDashboard");
  assert.ok(fn, "loadDashboard should exist");
  assert.match(fn, /await waitForPywebviewReady/);
});

test("Dashboard Start/End use inline datetime-local editors", () => {
  assert.match(DASHBOARD, /type="datetime-local"/);
  assert.match(DASHBOARD, /function\s+saveProjectDatetime/);
  assert.match(DASHBOARD, /callBridge\("project_update"/);
});

test("Dashboard tracks concurrent inline saves by edit key", () => {
  assert.doesNotMatch(DASHBOARD, /let\s+savingKey:\s*string/);
  assert.match(DASHBOARD, /let\s+savingKeys:\s*string\[\]/);
  assert.match(DASHBOARD, /function\s+startSaving\(key:\s*string\)/);
  assert.match(DASHBOARD, /function\s+finishSaving\(key:\s*string\)/);
  assert.match(DASHBOARD, /function\s+isSaving\(key:\s*string\)/);
  assert.doesNotMatch(DASHBOARD, /savingKey\s*=\s*""/);
  assert.match(DASHBOARD, /disabled=\{isSaving\(`\$\{p\.project_path\}:start_datetime`\)\}/);
});

test("Dashboard preserves failed inline save errors while reloading row data", () => {
  const load = extractFunction(DASHBOARD, "loadDashboard");
  const save = extractFunction(DASHBOARD, "withSaving");
  assert.ok(load, "loadDashboard should exist");
  assert.ok(save, "withSaving should exist");
  assert.match(DASHBOARD, /interface\s+LoadDashboardOptions\s*\{\s*clearActionError\?:\s*boolean\s*\}/);
  assert.match(load, /if \(clearActionError\) actionError = ""/);
  assert.match(save, /await loadDashboard\(\{ clearActionError:\s*false \}\)/);
});

test("Dashboard source aligns subprojects to placeholder drone rows and uses drone_add", () => {
  assert.match(DASHBOARD, /alignedDroneRows/);
  assert.match(DASHBOARD, /existingIndex:\s*-1/);
  const fn = extractFunction(DASHBOARD, "saveDroneLink");
  assert.ok(fn, "saveDroneLink should exist");
  assert.match(fn, /callBridge\("drone_add"/);
  assert.match(fn, /callBridge\("drone_update"/);
});

test("ProjectDetails source has visible AS_IS command center and sub-project box", () => {
  assert.match(PROJECT_DETAILS, /screen-details/);
  assert.match(PROJECT_DETAILS, /Project Command Center/);
  assert.match(PROJECT_DETAILS, /Sub Project \(DRONE\)/);
  assert.doesNotMatch(PROJECT_DETAILS, /Implementation Plan/);
  assert.doesNotMatch(PROJECT_DETAILS, /Save CR State/);
});

test("Dashboard state dropdowns use legal next-state helpers instead of full catalogs", () => {
  assert.match(DASHBOARD, /function\s+legalCrOptionsFor\s*\(/);
  assert.match(DASHBOARD, /function\s+legalDroneOptionsFor\s*\(/);
  assert.match(DASHBOARD, /#each legalCrOptionsFor\(p\.cr_state\) as opt/);
  assert.match(DASHBOARD, /#each legalDroneOptionsFor\(d\.drone_state\) as opt/);
  assert.doesNotMatch(DASHBOARD, /#each DRONE_STATE_OPTIONS as opt/);
});

test("ProjectDetails state dropdowns use legal next-state helpers", () => {
  assert.match(PROJECT_DETAILS, /function\s+legalCrOptionsFor\s*\(/);
  assert.match(PROJECT_DETAILS, /function\s+legalDroneOptionsFor\s*\(/);
  assert.match(PROJECT_DETAILS, /#each legalCrOptionsFor\(detail\.cr_state\) as opt/);
});

test("AS_IS state dropdowns keep solid red chip styling", () => {
  assert.match(DASHBOARD, /background:\s*var\(--primary-red\)/);
  assert.match(DASHBOARD, /color:\s*#fff/);
  assert.match(PROJECT_DETAILS, /background:\s*var\(--primary-red\)/);
  assert.match(PROJECT_DETAILS, /color:\s*#fff/);
});

test("Dashboard removes redundant command strip and grouped table chrome", () => {
  assert.doesNotMatch(DASHBOARD, /dashboard-command-strip/);
  assert.doesNotMatch(DASHBOARD, /dash-command-metric/);
  assert.doesNotMatch(DASHBOARD, /dash-group-row/);
  assert.doesNotMatch(DASHBOARD, /dash-group-cell/);
  assert.doesNotMatch(DASHBOARD, /direct-table-container/);
  assert.match(DASHBOARD, /activeStatus === "needs-review"/);
  assert.match(DASHBOARD, /projectNeedsReview/);
});

test("Dashboard project title cell is centered", () => {
  assert.match(DASHBOARD, /dash-name-cell/);
  assert.match(DASHBOARD, /\.dash-name-cell\s*\{[^}]*justify-content:\s*center/s);
  assert.match(DASHBOARD, /\.dash-name-btn\s*\{[^}]*text-align:\s*center/s);
});

test("Header no longer renders unused All CR filter dropdown", () => {
  const HEADER = readFileSync(resolve(__dirname, "../src/lib/components/Header.svelte"), "utf8");
  assert.doesNotMatch(HEADER, /All CR/);
  assert.doesNotMatch(HEADER, /aria-label="Filter"/);
});

test("Sidebar is bottom dock with activity-hide notifications", () => {
  const SIDEBAR = readFileSync(resolve(__dirname, "../src/lib/components/Sidebar.svelte"), "utf8");
  assert.match(SIDEBAR, /dock-hover-zone/);
  assert.match(SIDEBAR, /hidden-by-activity/);
  assert.match(SIDEBAR, /handleGlobalActivity/);
  assert.match(SIDEBAR, /dock-notification-popover/);
  assert.match(SIDEBAR, /unreadCount/);
  assert.doesNotMatch(SIDEBAR, /collapseBtn/);
});
