/**
 * Component tests for transition gating — ProjectTransitions.svelte (Task 5.6).
 *
 * No DOM testing library is installed and dependencies are frozen by the
 * release-candidate rules, so this combines two dependency-free techniques:
 *
 *  1. Real Svelte SSR (via the `.svelte` load hook in `svelte-loader.mjs`) to
 *     render the component for each Folder_State and assert the gated control
 *     surface — the transition catalog per state, the IMPLEMENTED lock hint, and
 *     that NO bridge / `window.pywebview` access happens during render.
 *  2. Source-structure assertions on the component itself for the interactive
 *     contract that SSR cannot reach (confirm / cancel / error live in internal
 *     `$state`, not props): the arming step issues no bridge call, the bridge
 *     call is gated behind `ConfirmModal.onConfirm`, cancel only resets state,
 *     and an `ok=false` response renders `error.message` and leaves UI unchanged.
 *
 * Covers:
 *  - No bridge call before confirm (Req 3.1)
 *  - Cancel / dismiss leaves prior state unchanged (Req 3.4)
 *  - `ok=false` renders the error and shows no success (Req 3.7)
 *
 * Validates: Requirements 3.1, 3.4, 3.7
 */
import { test, after, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

import { render } from "svelte/server";
import ProjectTransitions from "../src/lib/components/ProjectTransitions.svelte";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SOURCE = readFileSync(
  resolve(__dirname, "../src/lib/components/ProjectTransitions.svelte"),
  "utf8",
);

function baseProps(overrides) {
  return {
    projectPath: "/Temp_Root/2024/UAT_PREPARE/Acme-Migration",
    projectState: "UAT_PREPARE",
    projectName: "Acme-Migration",
    variant: "menu",
    onApplied: undefined,
    ...overrides,
  };
}

function renderBody(props) {
  return render(ProjectTransitions, { props: baseProps(props) }).body;
}

// A render-time spy: any property access on `window.pywebview` during SSR would
// throw, proving the component reaches the bridge while rendering.
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

test("the ⋮ menu trigger renders closed — no transition surface before interaction (Req 3.1)", () => {
  const body = renderBody({ projectState: "UAT_PREPARE", variant: "menu" });
  assert.match(body, /aria-haspopup="menu"/);
  assert.match(body, /aria-expanded="false"/);
  // The menu starts closed: no menu items and no ConfirmModal at render.
  assert.doesNotMatch(body, /pt-menu-item/);
  assert.doesNotMatch(body, /confirm-overlay/);
  // Rendering must not reach the bridge (no bridge call before confirm).
  assert.equal(bridgeTouched, false);
  assert.doesNotMatch(body, /pywebview/i);
});

test("UAT_PREPARE renders its transition catalog and touches no bridge at render (Req 3.1)", () => {
  const body = renderBody({ projectState: "UAT_PREPARE", variant: "inline" });
  assert.match(body, /Move to Prod Ready/);
  assert.match(body, /Postpone/);
  assert.match(body, /Cancel/);
  // No ConfirmModal is armed at render → no bridge call before confirm.
  assert.equal(bridgeTouched, false);
  assert.doesNotMatch(body, /pywebview/i);
  assert.doesNotMatch(body, /confirm-overlay/);
});

test("PROD_READY renders its transition catalog (Move to Implemented / Postpone / Cancel)", () => {
  const body = renderBody({ projectState: "PROD_READY", variant: "inline" });
  assert.match(body, /Move to Implemented/);
  assert.match(body, /Postpone/);
  assert.match(body, /Cancel/);
  assert.equal(bridgeTouched, false);
});

test("POSTPONED and CANCELED render a Reopen transition", () => {
  for (const state of ["POSTPONED", "CANCELED"]) {
    const body = renderBody({ projectState: state, variant: "inline" });
    assert.match(body, /Reopen/, `expected Reopen for ${state}`);
    assert.equal(bridgeTouched, false);
  }
});

test("IMPLEMENTED locks folder moves and renders a DisabledHint naming the lock (Req 3.5)", () => {
  const body = renderBody({ projectState: "IMPLEMENTED" });
  // Move is locked in IMPLEMENTED → disabled, non-interactive hint, no actions.
  assert.match(body, /aria-disabled="true"/);
  assert.match(body, /IMPLEMENTED/);
  assert.doesNotMatch(body, /pt-menu-item/);
  assert.equal(bridgeTouched, false);
});

test("inline variant renders action buttons rather than a ⋮ menu", () => {
  const body = renderBody({ projectState: "UAT_PREPARE", variant: "inline" });
  assert.match(body, /pt-action-btn/);
  assert.doesNotMatch(body, /aria-haspopup="menu"/);
  assert.equal(bridgeTouched, false);
});

// ── Source-structure: interactive gating contract SSR cannot reach ───────────

test("the arming step (requestTransition) issues no bridge call (Req 3.1)", () => {
  const fn = extractFunction(SOURCE, "requestTransition");
  assert.ok(fn, "requestTransition should exist");
  assert.doesNotMatch(fn, /callBridge/);
  // Arming only sets the pending transition that gates the ConfirmModal.
  assert.match(fn, /pending\s*=\s*t/);
});

test("the bridge call is gated behind ConfirmModal.onConfirm (Req 3.1)", () => {
  // callBridge appears only inside runTransition.
  const runTransition = extractFunction(SOURCE, "runTransition");
  assert.ok(runTransition, "runTransition should exist");
  assert.match(runTransition, /callBridge/);

  const confirmPending = extractFunction(SOURCE, "confirmPending");
  assert.ok(confirmPending, "confirmPending should exist");
  assert.match(confirmPending, /runTransition\(t,\s*false\)/);

  // The ConfirmModal's confirm handler is wired to confirmPending; the bridge
  // therefore only fires after explicit confirmation.
  assert.match(SOURCE, /<ConfirmModal[\s\S]*?onConfirm=\{confirmPending\}/);
  // The modal is gated behind the pending transition.
  assert.match(SOURCE, /\{#if pending\}\s*<ConfirmModal/);

  // The two bridge calls (written as `callBridge<…>(…)`) both live in
  // runTransition; the only other mention of the symbol is its import.
  assert.equal(countOccurrences(SOURCE, "callBridge<"), 2, "exactly two bridge calls");
  assert.equal(countOccurrences(runTransition, "callBridge<"), 2, "both gated in runTransition");
});

test("cancel only resets pending state — no bridge call, no applied change (Req 3.4)", () => {
  const cancelConfirm = extractFunction(SOURCE, "cancelConfirm");
  assert.ok(cancelConfirm, "cancelConfirm should exist");
  assert.match(cancelConfirm, /pending\s*=\s*null/);
  assert.doesNotMatch(cancelConfirm, /callBridge/);
  assert.doesNotMatch(cancelConfirm, /onApplied/);
  // The ConfirmModal's cancel handler is wired to cancelConfirm.
  assert.match(SOURCE, /<ConfirmModal[\s\S]*?onCancel=\{cancelConfirm\}/);
});

test("declining the T-10 override leaves the project unchanged (Req 3.4/3.7)", () => {
  const cancelOverride = extractFunction(SOURCE, "cancelOverride");
  assert.ok(cancelOverride, "cancelOverride should exist");
  assert.match(cancelOverride, /overridePending\s*=\s*null/);
  assert.doesNotMatch(cancelOverride, /callBridge/);
  assert.doesNotMatch(cancelOverride, /onApplied/);
});

test("an ok=false response renders error.message and shows no success (Req 3.7)", () => {
  const runTransition = extractFunction(SOURCE, "runTransition");
  // Failure branch surfaces the bridge error message and returns early — the
  // success path (successMessage / onApplied) is never reached.
  assert.match(runTransition, /if\s*\(!response\.ok\)/);
  const errIdx = runTransition.indexOf("errorMessage = response.error.message");
  assert.ok(errIdx > 0, "failure branch assigns the bridge error message");
  const returnIdx = runTransition.indexOf("return;", errIdx);
  const successIdx = runTransition.indexOf("successMessage = `");
  assert.ok(returnIdx > 0, "failure branch returns early");
  assert.ok(successIdx > 0, "a success message assignment exists");
  assert.ok(returnIdx < successIdx, "the early return precedes the success path");
  // The template renders the error message in an alert region.
  assert.match(SOURCE, /errorMessage[\s\S]*?role="alert"|role="alert"[\s\S]*?errorMessage/);
});

test("only success (ok=true) invokes onApplied with the next path/state (Req 3.7)", () => {
  const runTransition = extractFunction(SOURCE, "runTransition");
  const successIdx = runTransition.indexOf("successMessage = `");
  const failReturnIdx = runTransition.indexOf("return;");
  // onApplied is invoked strictly after the failure early-return.
  assert.ok(successIdx > failReturnIdx, "success path follows the failure early-return");
  assert.match(runTransition, /onApplied\?\.\(next\)/);
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
