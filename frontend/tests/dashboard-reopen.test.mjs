/**
 * Dashboard reopen-via-CR-dropdown behavior tests.
 *
 * REOPEN is an action, not a CR state (PRD §9.1) — `validate_cr_transition`
 * rejects it as a CR target. On the Dashboard it is surfaced as a CR-dropdown
 * option ONLY when the CR state is POSTPONED or CANCELED, and selecting it must
 * route to the `folder_reopen` bridge (not `cr_update_state`) behind the
 * ConfirmModal.
 *
 * No DOM testing library is installed and deps are frozen, so this uses
 * source-structure assertions (same technique as transitions.test.mjs) for the
 * interactive contract that lives in internal $state, not props.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SOURCE = readFileSync(
  resolve(__dirname, "../src/lib/components/Dashboard.svelte"),
  "utf8",
);

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

// ── REOPEN option is gated to POSTPONED/CANCELED ─────────────────────────────

test("legalCrOptionsFor adds REOPEN only for reopenable CR states", () => {
  const fn = extractFunction(SOURCE, "legalCrOptionsFor");
  assert.ok(fn, "legalCrOptionsFor should exist");
  // The legal transition map drives whether REOPEN is appended.
  assert.match(SOURCE, /REOPENABLE\s*=\s*new Set\(\["POSTPONED",\s*"CANCELED"\]\)/);
  assert.match(SOURCE, /"POSTPONED":\s*\[REOPEN_OPTION\]/);
  assert.match(SOURCE, /"CANCELED":\s*\[REOPEN_OPTION\]/);
  assert.match(fn, /CR_NEXT\[crState\]/);
});

test("the CR dropdown renders options from legalCrOptionsFor, not the fixed catalog", () => {
  // The dropdown must use the per-row legal option function so REOPEN can appear only when legal.
  assert.match(SOURCE, /#each legalCrOptionsFor\(p\.cr_state\) as opt/);
});

// ── Selecting REOPEN routes to folder_reopen, not cr_update_state ────────────

test("onCrStateChange routes REOPEN to a reopen confirm, not applyCrState", () => {
  const fn = extractFunction(SOURCE, "onCrStateChange");
  assert.ok(fn, "onCrStateChange should exist");
  // REOPEN arms a pending reopen confirmation (no immediate bridge call).
  assert.match(fn, /next === REOPEN_OPTION/);
  assert.match(fn, /kind:\s*"reopen"/);
  assert.doesNotMatch(fn, /callBridge/);
});

test("reopen calls the folder_reopen bridge, never cr_update_state", () => {
  const fn = extractFunction(SOURCE, "reopenProject");
  assert.ok(fn, "reopenProject should exist");
  assert.match(fn, /callBridge\("folder_reopen"/);
  assert.doesNotMatch(fn, /cr_update_state/);
});

test("the reopen bridge call is gated behind ConfirmModal.onConfirm", () => {
  const confirm = extractFunction(SOURCE, "confirmPendingState");
  assert.ok(confirm, "confirmPendingState should exist");
  // The reopen branch dispatches to reopenProject only on confirm.
  assert.match(confirm, /ps\.kind === "reopen"/);
  assert.match(confirm, /reopenProject\(ps\.path\)/);
  // The modal's confirm handler is wired to confirmPendingState.
  assert.match(SOURCE, /onConfirm=\{confirmPendingState\}/);
  // Exactly one folder_reopen call exists, and it lives in reopenProject.
  assert.equal(countOccurrences(SOURCE, 'callBridge("folder_reopen"'), 1, "one reopen call");
  assert.equal(
    countOccurrences(extractFunction(SOURCE, "reopenProject"), 'callBridge("folder_reopen"'),
    1,
    "reopen call gated in reopenProject",
  );
});

test("cancelling a pending reopen issues no bridge call", () => {
  const cancel = extractFunction(SOURCE, "cancelPendingState");
  assert.ok(cancel, "cancelPendingState should exist");
  assert.match(cancel, /pendingState\s*=\s*null/);
  assert.doesNotMatch(cancel, /folder_reopen/);
});

// ── REOPEN is a reversible action; the confirm copy reflects that ────────────

test("the reopen confirmation is labelled and reversible", () => {
  assert.match(SOURCE, /Reopen project\?/);
  assert.match(SOURCE, /Reopen to UAT_PREPARE/);
  // reopen is presented as reversible (it just moves the folder back).
  assert.match(SOURCE, /pendingState\.kind === "reopen"/);
});
