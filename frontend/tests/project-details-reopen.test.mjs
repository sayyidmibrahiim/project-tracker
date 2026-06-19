/**
 * Project Details reopen-via-CR-dropdown behavior tests.
 *
 * Mirrors the Dashboard reopen contract (PRD §9.4/§12.13): REOPEN is an action,
 * not a CR state — `validate_cr_transition` rejects it. On Project Details it
 * must be surfaced as a CR-dropdown option ONLY when the CR state is POSTPONED
 * or CANCELED, and selecting it routes to the `folder_reopen` bridge (not
 * `cr_update_state`) behind a ConfirmModal.
 *
 * Source-structure assertions (no DOM testing lib; deps frozen).
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SOURCE = readFileSync(
  resolve(__dirname, "../src/lib/components/ProjectDetails.svelte"),
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

// ── REOPEN option is gated to POSTPONED/CANCELED in the legal map ────────────

test("ProjectDetails legal CR map offers REOPEN only for POSTPONED/CANCELED", () => {
  const fn = extractFunction(SOURCE, "legalCrOptionsFor");
  assert.ok(fn, "legalCrOptionsFor should exist");
  // The reopen option constant must exist.
  assert.match(SOURCE, /REOPEN_OPTION\s*=\s*"REOPEN"/);
  // The legal transition map must route POSTPONED/CANCELED to the reopen option.
  assert.match(SOURCE, /"POSTPONED":\s*\[REOPEN_OPTION\]/);
  assert.match(SOURCE, /"CANCELED":\s*\[REOPEN_OPTION\]/);
  assert.match(fn, /CR_NEXT\[crState\]/);
});

test("ProjectDetails CR dropdown renders options from legalCrOptionsFor", () => {
  assert.match(SOURCE, /#each legalCrOptionsFor\(detail\.cr_state\) as opt/);
});

// ── Selecting REOPEN arms a confirm; Save CR State branches on REOPEN ───────

test("saving CR state routes REOPEN to a confirm + folder_reopen, not cr_update_state", () => {
  // The save flow must branch: REOPEN arms a pending reopen; other states call cr_update_state.
  const save = extractFunction(SOURCE, "saveCrState");
  assert.ok(save, "saveCrState should exist");
  assert.match(save, /REOPEN_OPTION/);
  // When REOPEN is selected, do NOT call cr_update_state — arm confirm instead.
  assert.match(save, /pendingReopen\s*=/);
  assert.match(save, /return;/);
});

test("a reopenProject helper calls the folder_reopen bridge, never cr_update_state", () => {
  const fn = extractFunction(SOURCE, "reopenProject");
  assert.ok(fn, "reopenProject should exist");
  assert.match(fn, /callBridge\("folder_reopen"/);
  assert.doesNotMatch(fn, /cr_update_state/);
});

test("exactly one folder_reopen call exists, in reopenProject", () => {
  assert.equal(countOccurrences(SOURCE, 'callBridge("folder_reopen"'), 1, "one reopen call");
  const fn = extractFunction(SOURCE, "reopenProject");
  assert.equal(
    countOccurrences(fn ?? "", 'callBridge("folder_reopen"'),
    1,
    "reopen call lives in reopenProject",
  );
});

test("the reopen bridge call is gated behind ConfirmModal.onConfirm", () => {
  assert.match(SOURCE, /pendingReopen\.kind === "reopen"|pendingReopen\b/);
  assert.match(SOURCE, /Reopen project\?/);
  assert.match(SOURCE, /onConfirm=\{confirmReopen\}/);
});

test("cancelling a pending reopen issues no bridge call", () => {
  const cancel = extractFunction(SOURCE, "cancelReopen");
  assert.ok(cancel, "cancelReopen should exist");
  assert.match(cancel, /pendingReopen\s*=\s*null/);
  assert.doesNotMatch(cancel, /folder_reopen/);
});
