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
  let i = source.indexOf("{", m.index);
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

test("Dashboard source supports inline datetime-local save through project_update", () => {
  assert.match(DASHBOARD, /type="datetime-local"/);
  const fn = extractFunction(DASHBOARD, "saveProjectDatetime");
  assert.ok(fn, "saveProjectDatetime should exist");
  assert.match(fn, /callBridge\("project_update"/);
  assert.match(fn, /start_datetime/);
  assert.match(fn, /end_datetime/);
});

test("Dashboard source aligns subprojects to placeholder drone rows and uses drone_add", () => {
  assert.match(DASHBOARD, /alignedDroneRows/);
  assert.match(DASHBOARD, /existingIndex:\s*-1/);
  const fn = extractFunction(DASHBOARD, "saveDroneLink");
  assert.ok(fn, "saveDroneLink should exist");
  assert.match(fn, /callBridge\("drone_add"/);
  assert.match(fn, /callBridge\("drone_update"/);
});

test("ProjectDetails source has visible AS_IS selected-subproject drone-ticket flow and implementation plan section", () => {
  assert.match(PROJECT_DETAILS, /screen-details/);
  assert.match(PROJECT_DETAILS, /Project Command Center/);
  assert.match(PROJECT_DETAILS, /selectedSubprojectDrone/);
  assert.match(PROJECT_DETAILS, /Add Drone Ticket/);
  assert.match(PROJECT_DETAILS, /Implementation Plan/);
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
  assert.match(PROJECT_DETAILS, /#each legalDroneOptionsFor\(selectedSubprojectDrone\.ticket\.drone_state\) as opt/);
});

test("AS_IS state dropdowns keep solid red chip styling", () => {
  assert.match(DASHBOARD, /background:\s*var\(--primary-red\)/);
  assert.match(DASHBOARD, /color:\s*#fff/);
  assert.match(PROJECT_DETAILS, /background:\s*var\(--primary-red\)/);
  assert.match(PROJECT_DETAILS, /color:\s*#fff/);
});
