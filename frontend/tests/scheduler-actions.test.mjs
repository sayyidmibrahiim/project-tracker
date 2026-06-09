/**
 * Component tests for Scheduler entry delete confirmation — SchedulerActions.svelte.
 *
 * PRD §16.5 requires "Delete → confirmation → remove". Previously the Scheduler
 * Delete button deleted immediately. This mirrors the dependency-free technique
 * in project-actions.test.mjs:
 *
 *  1. SSR render + a window.pywebview Proxy spy: no bridge access at render and
 *     no ConfirmModal armed before interaction.
 *  2. Source-structure assertions for the interactive gating SSR cannot reach:
 *     requestDelete only arms pendingDeleteEntry (no bridge call), confirmDelete
 *     holds the scheduler_entry_delete bridge call, cancelDelete resets state,
 *     and the delete ConfirmModal is gated behind {#if pendingDeleteEntry}.
 *
 * Validates: Requirements 3.1, 3.4 and PRD §16.5 delete confirmation.
 */
import { test, beforeEach, afterEach, after } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

import { render } from "svelte/server";
import SchedulerActions from "../src/lib/components/SchedulerActions.svelte";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SOURCE = readFileSync(
  resolve(__dirname, "../src/lib/components/SchedulerActions.svelte"),
  "utf8",
);

// Render-time spy: any property access on window.pywebview during SSR flips this.
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
after(() => {
  delete globalThis.window;
});

// ── SSR render: control surface + no bridge / no confirm armed at render ──────

test("Scheduler renders its control surface and touches no bridge or confirm at render", () => {
  const { body } = render(SchedulerActions, { props: {} });
  assert.match(body, /Scheduler/);
  assert.match(body, /\+ New entry/);
  // onMount does not run during SSR, so the entry list is empty here.
  assert.match(body, /No scheduler entries/);
  // No ConfirmModal armed before interaction → no proceed control, no bridge touch.
  assert.doesNotMatch(body, /confirm-btn-proceed/);
  assert.equal(bridgeTouched, false);
  assert.doesNotMatch(body, /pywebview/i);
});

// ── Source-structure: interactive delete-confirm gating SSR cannot reach ──────

test("requestDelete only arms the pending entry and issues no bridge call (Req 3.1 / PRD §16.5)", () => {
  const fn = extractFunction(SOURCE, "requestDelete");
  assert.ok(fn, "requestDelete should exist");
  assert.doesNotMatch(fn, /callBridge/, "arming must not call the bridge");
  assert.match(fn, /pendingDeleteEntry\s*=\s*entry/, "arming only sets the pending entry");
});

test("the scheduler delete bridge call is gated behind confirmDelete / ConfirmModal.onConfirm (PRD §16.5)", () => {
  const confirmDelete = extractFunction(SOURCE, "confirmDelete");
  assert.ok(confirmDelete, "confirmDelete should exist");
  assert.match(confirmDelete, /callBridge/);
  assert.match(confirmDelete, /"scheduler_entry_delete"/);
  // The delete ConfirmModal is gated behind the pending entry and wired to confirmDelete.
  assert.match(SOURCE, /\{#if pendingDeleteEntry\}\s*<ConfirmModal/);
  assert.match(SOURCE, /<ConfirmModal[\s\S]*?onConfirm=\{confirmDelete\}/);
});

test("cancelDelete resets pending state with no bridge call (Req 3.4)", () => {
  const cancelDelete = extractFunction(SOURCE, "cancelDelete");
  assert.ok(cancelDelete, "cancelDelete should exist");
  assert.match(cancelDelete, /pendingDeleteEntry\s*=\s*null/);
  assert.doesNotMatch(cancelDelete, /callBridge/);
  assert.match(SOURCE, /<ConfirmModal[\s\S]*?onCancel=\{cancelDelete\}/);
});

test("scheduler delete is presented as irreversible in the Confirmation_UI", () => {
  assert.match(SOURCE, /title="Delete scheduler entry"[\s\S]*?reversible=\{false\}/);
});

// ── helper ────────────────────────────────────────────────────────────────────

/** Extract a brace-balanced function body for `name` from source text. */
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
