/**
 * Component tests for file create/open/rename/delete gating —
 * FileActions.svelte (Task 9.4).
 *
 * No DOM testing library is installed and dependencies are frozen by the
 * release-candidate rules, so this combines two dependency-free techniques
 * (mirroring project-actions.test.mjs):
 *
 *  1. Real Svelte SSR to render the component for each Folder_State and assert
 *     the gated control surface — the active create/rename/delete controls in
 *     UAT_PREPARE, the PROD_READY / IMPLEMENTED DisabledHints naming the state,
 *     and that NO bridge / `window.pywebview` access happens during render.
 *  2. Source-structure assertions for the interactive contract SSR cannot reach
 *     (confirm / cancel / error live in internal `$state`, not props): the
 *     arming step issues no bridge call, the rename/delete bridge calls are
 *     gated behind `ConfirmModal.onConfirm`, cancel only resets state, delete is
 *     routed as irreversible while rename is reversible, and an `ok=false`
 *     response renders `error.message`.
 *
 * Covers:
 *  - Rename/delete routed through ConfirmModal; no bridge call before confirm (Req 3.1)
 *  - Delete uses irreversible styling; rename is reversible (Req 3.1 / ConfirmModal contract)
 *  - PROD_READY / IMPLEMENTED render a DisabledHint naming the state (Req 3.5, 6.10)
 *  - ok=false renders the error and shows no success (Req 3.7)
 *
 * Validates: Requirements 3.1, 3.5, 6.10
 */
import { test, beforeEach, afterEach, after } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

import { render } from "svelte/server";
import FileActions from "../src/lib/components/FileActions.svelte";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SOURCE = readFileSync(
  resolve(__dirname, "../src/lib/components/FileActions.svelte"),
  "utf8",
);

function baseProps(overrides) {
  return {
    projectPath: "/Temp_Root/2024/UAT_PREPARE/Acme-Migration",
    projectState: "UAT_PREPARE",
    files: [
      { name: "evidence.txt", path: "/Temp_Root/2024/UAT_PREPARE/Acme-Migration/evidence.txt" },
      { name: "plan.md", path: "/Temp_Root/2024/UAT_PREPARE/Acme-Migration/plan.md" },
    ],
    onFilesChanged: undefined,
    ...overrides,
  };
}

function renderBody(props) {
  return render(FileActions, { props: baseProps(props) }).body;
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

test("UAT_PREPARE renders active create/open/rename/delete controls and touches no bridge (Req 3.1)", () => {
  const body = renderBody({ projectState: "UAT_PREPARE" });
  assert.match(body, /New file name/);
  assert.match(body, /Template name/);
  assert.match(body, /evidence\.txt/);
  assert.match(body, /plan\.md/);
  assert.match(body, /Open/);
  assert.match(body, /Rename/);
  assert.match(body, /Delete/);
  // No ConfirmModal is armed at render → no bridge call before confirm.
  assert.equal(bridgeTouched, false);
  assert.doesNotMatch(body, /pywebview/i);
  assert.doesNotMatch(body, /confirm-overlay/);
});

test("PROD_READY locks create/rename/delete with DisabledHints naming the state (Req 3.5, 6.10)", () => {
  const body = renderBody({ projectState: "PROD_READY" });
  assert.match(body, /aria-disabled="true"/);
  assert.match(body, /PROD_READY/);
  assert.match(body, /partial lock/i);
  // No active create input rendered while locked.
  assert.doesNotMatch(body, /New file name/);
  assert.equal(bridgeTouched, false);
});

test("IMPLEMENTED locks create/rename/delete with DisabledHints naming the state (Req 3.5, 6.10)", () => {
  const body = renderBody({ projectState: "IMPLEMENTED" });
  assert.match(body, /aria-disabled="true"/);
  assert.match(body, /IMPLEMENTED/);
  assert.doesNotMatch(body, /New file name/);
  assert.equal(bridgeTouched, false);
});

test("renders an empty-files message when there are none", () => {
  const body = renderBody({ projectState: "UAT_PREPARE", files: [] });
  assert.match(body, /No files/);
  assert.equal(bridgeTouched, false);
});

// ── Source-structure: interactive gating contract SSR cannot reach ───────────

test("the rename/delete arming steps issue no bridge call (Req 3.1)", () => {
  for (const name of ["requestRename", "requestDelete"]) {
    const fn = extractFunction(SOURCE, name);
    assert.ok(fn, `${name} should exist`);
    assert.doesNotMatch(fn, /callBridge/, `${name} must not call the bridge`);
    assert.match(fn, /pending\s*=\s*\{/, `${name} only arms the pending action`);
  }
});

test("rename/delete bridge calls are gated behind ConfirmModal.onConfirm (Req 3.1)", () => {
  const runAction = extractFunction(SOURCE, "runAction");
  assert.ok(runAction, "runAction should exist");
  assert.match(runAction, /"file_rename"/);
  assert.match(runAction, /"file_delete"/);

  const confirmPending = extractFunction(SOURCE, "confirmPending");
  assert.ok(confirmPending, "confirmPending should exist");
  assert.match(confirmPending, /runAction\(action\)/);

  // The ConfirmModal's confirm handler is wired to confirmPending; the rename
  // and delete bridge calls therefore only fire after explicit confirmation.
  assert.match(SOURCE, /<ConfirmModal[\s\S]*?onConfirm=\{confirmPending\}/);
  // The modal is gated behind the pending action.
  assert.match(SOURCE, /\{#if pending\}\s*<ConfirmModal/);

  // The two gated bridge calls (file_rename + file_delete) live in runAction.
  assert.equal(countOccurrences(runAction, "callBridge"), 2, "exactly two gated bridge calls");
});

test("create/create-from-template/open are direct (non-destructive) form actions but surface errors (Req 6.10)", () => {
  // Create and create-from-template are form actions: they call the bridge
  // directly (no Confirmation_UI) but still surface error.message on ok=false.
  for (const [name, method] of [
    ["createFile", "file_create"],
    ["createFromTemplate", "file_create_from_template"],
    ["openFile", "file_open"],
  ]) {
    const fn = extractFunction(SOURCE, name);
    assert.ok(fn, `${name} should exist`);
    assert.match(fn, new RegExp(`"${method}"`), `${name} calls ${method}`);
    assert.match(fn, /errorMessage = response\.error\.message/, `${name} surfaces errors`);
  }
});

test("cancel only resets pending state — no bridge call, no applied change (Req 3.4)", () => {
  const cancelConfirm = extractFunction(SOURCE, "cancelConfirm");
  assert.ok(cancelConfirm, "cancelConfirm should exist");
  assert.match(cancelConfirm, /pending\s*=\s*null/);
  assert.doesNotMatch(cancelConfirm, /callBridge/);
  assert.match(SOURCE, /<ConfirmModal[\s\S]*?onCancel=\{cancelConfirm\}/);
});

test("delete is irreversible and rename is reversible in the Confirmation_UI (Req 3.1)", () => {
  assert.match(SOURCE, /confirmReversible[\s\S]*?pending\?\.kind === "rename"/);
  assert.match(SOURCE, /<ConfirmModal[\s\S]*?reversible=\{confirmReversible\}/);
});

test("an ok=false response renders error.message and shows no success (Req 3.7)", () => {
  const runAction = extractFunction(SOURCE, "runAction");
  assert.match(runAction, /if\s*\(!response\.ok\)/);
  assert.match(runAction, /errorMessage = response\.error\.message/);
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
