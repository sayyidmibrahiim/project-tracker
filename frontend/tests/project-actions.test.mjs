/**
 * Component tests for rename/delete/drone-delete gating —
 * ProjectActions.svelte (Task 7.5).
 *
 * No DOM testing library is installed and dependencies are frozen by the
 * release-candidate rules, so this combines two dependency-free techniques
 * (mirroring transitions.test.mjs):
 *
 *  1. Real Svelte SSR to render the component for each Folder_State and assert
 *     the gated control surface — the active rename/delete controls in
 *     UAT_PREPARE, the PROD_READY / IMPLEMENTED DisabledHints naming the state,
 *     and that NO bridge / `window.pywebview` access happens during render.
 *  2. Source-structure assertions for the interactive contract SSR cannot reach
 *     (confirm / cancel / error live in internal `$state`, not props): the
 *     arming step issues no bridge call, the bridge call is gated behind
 *     `ConfirmModal.onConfirm`, cancel only resets state, deletes are routed as
 *     irreversible, and an `ok=false` response renders `error.message`.
 *
 * Covers:
 *  - All three actions routed through ConfirmModal; no bridge call before confirm (Req 3.1)
 *  - Deletes use irreversible styling; rename is reversible (Req 3.1 / ConfirmModal contract)
 *  - PROD_READY / IMPLEMENTED render a DisabledHint naming the state (Req 3.5, 5.3, 5.5)
 *  - ok=false renders the error and shows no success (Req 3.7)
 *
 * Validates: Requirements 3.1, 3.5, 5.3, 5.5
 */
import { test, beforeEach, afterEach, after } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

import { render } from "svelte/server";
import ProjectActions from "../src/lib/components/ProjectActions.svelte";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SOURCE = readFileSync(
  resolve(__dirname, "../src/lib/components/ProjectActions.svelte"),
  "utf8",
);

function baseProps(overrides) {
  return {
    projectPath: "/Temp_Root/2024/UAT_PREPARE/Acme-Migration",
    projectState: "UAT_PREPARE",
    projectName: "Acme-Migration",
    drones: ["Phase-1", "Phase-2"],
    onRenamed: undefined,
    onDeleted: undefined,
    onDronesChanged: undefined,
    ...overrides,
  };
}

function renderBody(props) {
  return render(ProjectActions, { props: baseProps(props) }).body;
}

// A render-time spy: any property access on `window.pywebview` during SSR would
// flip the flag, proving the component reaches the bridge while rendering.
let bridgeTouched = false;
beforeEach(() => {
  bridgeTouched = false;
  const trap = new Proxy(
    {},
    {
      get() {
        bridgeTouched = true;
        return undefined;
      },
    },
  );
  globalThis.window = { pywebview: { api: trap } };
});
afterEach(() => {
  delete globalThis.window;
});

// ── SSR render: gated control surface + no bridge access at render (Req 3.1) ──

test("UAT_PREPARE renders active rename/delete controls and touches no bridge (Req 3.1)", () => {
  const body = renderBody({ projectState: "UAT_PREPARE" });
  assert.match(body, /New project name/);
  assert.match(body, /Rename/);
  assert.match(body, /Delete project/);
  // Subprojects each get a delete control.
  assert.match(body, /Phase-1/);
  assert.match(body, /Phase-2/);
  // No ConfirmModal is armed at render → no bridge call before confirm.
  assert.equal(bridgeTouched, false);
  assert.doesNotMatch(body, /pywebview/i);
  assert.doesNotMatch(body, /confirm-overlay/);
});

test("PROD_READY locks rename/delete/drone-delete with DisabledHints naming the state (Req 3.5, 5.3, 5.5)", () => {
  const body = renderBody({ projectState: "PROD_READY" });
  assert.match(body, /aria-disabled="true"/);
  assert.match(body, /PROD_READY/);
  assert.match(body, /partial lock/i);
  // No active rename input rendered while locked.
  assert.doesNotMatch(body, /New project name/);
  assert.equal(bridgeTouched, false);
});

test("IMPLEMENTED locks rename/delete/drone-delete with DisabledHints naming the state (Req 3.5, 5.3, 5.5)", () => {
  const body = renderBody({ projectState: "IMPLEMENTED" });
  assert.match(body, /aria-disabled="true"/);
  assert.match(body, /IMPLEMENTED/);
  assert.doesNotMatch(body, /New project name/);
  assert.equal(bridgeTouched, false);
});

test("renders an empty-drones message when there are none", () => {
  const body = renderBody({ projectState: "UAT_PREPARE", drones: [] });
  assert.match(body, /No drones/);
  assert.equal(bridgeTouched, false);
});

// ── Source-structure: interactive gating contract SSR cannot reach ───────────

test("the arming steps issue no bridge call (Req 3.1)", () => {
  for (const name of ["requestRename", "requestDeleteProject", "requestSubprojectDelete"]) {
    const fn = extractFunction(SOURCE, name);
    assert.ok(fn, `${name} should exist`);
    assert.doesNotMatch(fn, /callBridge/, `${name} must not call the bridge`);
    assert.match(fn, /pending\s*=\s*\{/, `${name} only arms the pending action`);
  }
});

test("every bridge call is gated behind ConfirmModal.onConfirm (Req 3.1)", () => {
  // All three callBridge calls live inside runAction only.
  const runAction = extractFunction(SOURCE, "runAction");
  assert.ok(runAction, "runAction should exist");
  assert.match(runAction, /callBridge/);
  assert.match(runAction, /"project_rename"/);
  assert.match(runAction, /"project_delete"/);
  assert.match(runAction, /"drone_delete"/);

  const confirmPending = extractFunction(SOURCE, "confirmPending");
  assert.ok(confirmPending, "confirmPending should exist");
  assert.match(confirmPending, /runAction\(action\)/);

  // The ConfirmModal's confirm handler is wired to confirmPending; the bridge
  // therefore only fires after explicit confirmation.
  assert.match(SOURCE, /<ConfirmModal[\s\S]*?onConfirm=\{confirmPending\}/);
  // The modal is gated behind the pending action.
  assert.match(SOURCE, /\{#if pending\}\s*<ConfirmModal/);

  // The three bridge calls (written as `callBridge(`/`callBridge<`) all live in
  // runAction; the only other mention of the symbol is its import.
  assert.equal(countOccurrences(runAction, "callBridge"), 3, "exactly three gated bridge calls");
});

test("cancel only resets pending state — no bridge call, no applied change (Req 3.4)", () => {
  const cancelConfirm = extractFunction(SOURCE, "cancelConfirm");
  assert.ok(cancelConfirm, "cancelConfirm should exist");
  assert.match(cancelConfirm, /pending\s*=\s*null/);
  assert.doesNotMatch(cancelConfirm, /callBridge/);
  // The ConfirmModal's cancel handler is wired to cancelConfirm.
  assert.match(SOURCE, /<ConfirmModal[\s\S]*?onCancel=\{cancelConfirm\}/);
});

test("deletes are irreversible and rename is reversible in the Confirmation_UI (Req 3.1)", () => {
  // confirmReversible is true only for the rename action; deletes are false.
  assert.match(SOURCE, /confirmReversible[\s\S]*?pending\?\.kind === "rename"/);
  // The ConfirmModal is fed the derived reversibility.
  assert.match(SOURCE, /<ConfirmModal[\s\S]*?reversible=\{confirmReversible\}/);
});

test("an ok=false response renders error.message and shows no success (Req 3.7)", () => {
  const runAction = extractFunction(SOURCE, "runAction");
  // Each failure branch assigns the bridge error message and returns early.
  assert.match(runAction, /if\s*\(!response\.ok\)/);
  assert.match(runAction, /errorMessage = response\.error\.message/);
  // The template renders the error message in an alert region.
  assert.match(SOURCE, /errorMessage[\s\S]*?role="alert"|role="alert"[\s\S]*?errorMessage/);
});

// ── helpers ──────────────────────────────────────────────────────────────────

/** Extract a function body (brace-balanced) for `name` from source text. */
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

function countOccurrences(haystack, needle) {
  let count = 0;
  let idx = haystack.indexOf(needle);
  while (idx !== -1) {
    count++;
    idx = haystack.indexOf(needle, idx + needle.length);
  }
  return count;
}

after(() => {
  delete globalThis.window;
});
