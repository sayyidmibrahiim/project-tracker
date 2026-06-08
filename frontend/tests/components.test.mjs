/**
 * Component render tests for ConfirmModal and DisabledHint (Task 1.4).
 *
 * Verified via Svelte SSR (see ssrHelper.mjs) because no DOM testing library
 * is installed and dependencies are frozen by the release-candidate rules.
 *
 * Covers:
 *  - ConfirmModal irreversible rendering for `reversible="unknown"` (Req 3.3)
 *  - ConfirmModal reversible/irreversible binary statement + target naming (Req 3.2)
 *  - ConfirmModal renders distinct Cancel and confirm controls that back the
 *    confirm-vs-cancel callbacks (Req 3.1, 3.4)
 *  - DisabledHint renders a disabled, non-interactive control whose message
 *    names the Folder_State lock (Req 3.5) or the deferred status (Req 3.6)
 *
 * Validates: Requirements 3.2, 3.3, 3.4, 3.5, 3.6
 */
import { test, after } from "node:test";
import assert from "node:assert/strict";

import { renderComponent, cleanup } from "./ssrHelper.mjs";
import { lockReason } from "../src/lib/folderLocks.ts";

const CONFIRM = "../src/lib/components/ConfirmModal.svelte";
const DISABLED = "../src/lib/components/DisabledHint.svelte";

const noop = () => {};

after(() => cleanup());

function confirmProps(overrides) {
  return {
    title: "Delete project",
    actionLabel: "Delete",
    targetName: "Acme-Migration",
    reversible: false,
    onConfirm: noop,
    onCancel: noop,
    ...overrides,
  };
}

// --- ConfirmModal: reversibility (Req 3.2, 3.3) ------------------------------

test('ConfirmModal renders "irreversible" when reversible="unknown" (Req 3.3)', async () => {
  const body = await renderComponent(CONFIRM, confirmProps({ reversible: "unknown" }));
  assert.match(body, /irreversible/i);
  assert.doesNotMatch(body, /This action is reversible/i);
});

test('ConfirmModal renders "irreversible" when reversible=false', async () => {
  const body = await renderComponent(CONFIRM, confirmProps({ reversible: false }));
  assert.match(body, /This action is irreversible/i);
});

test('ConfirmModal renders "reversible" when reversible=true', async () => {
  const body = await renderComponent(CONFIRM, confirmProps({ reversible: true }));
  assert.match(body, /This action is reversible/i);
  assert.doesNotMatch(body, /This action is irreversible/i);
});

// --- ConfirmModal: action/target statement (Req 3.2) -------------------------

test("ConfirmModal states the action label, title, and target name (Req 3.2)", async () => {
  const body = await renderComponent(
    CONFIRM,
    confirmProps({ title: "Delete project", actionLabel: "Delete", targetName: "Acme-Migration" }),
  );
  assert.match(body, /Delete project/);
  assert.match(body, /Acme-Migration/);
  assert.match(body, /Delete/);
});

// --- ConfirmModal: distinct confirm vs cancel controls (Req 3.1, 3.4) --------

test("ConfirmModal renders distinct Cancel and confirm controls (Req 3.1, 3.4)", async () => {
  const body = await renderComponent(CONFIRM, confirmProps({ actionLabel: "Delete" }));
  // A dedicated Cancel control backs onCancel (dismiss leaves state unchanged).
  assert.match(body, /confirm-btn-cancel/);
  assert.match(body, /Cancel/);
  // A dedicated proceed control labelled with the action backs onConfirm.
  assert.match(body, /confirm-btn-proceed/);
  // Irreversible actions get the irreversible-styled proceed button.
  assert.match(body, /irreversible/);
});

test("ConfirmModal markup contains no bridge/window access (Req 3.1)", async () => {
  const body = await renderComponent(CONFIRM, confirmProps({}));
  assert.doesNotMatch(body, /pywebview/i);
  assert.doesNotMatch(body, /callBridge/i);
});

// --- DisabledHint: message naming the lock (Req 3.5) -------------------------

test("DisabledHint renders a disabled, non-interactive control (Req 3.5)", async () => {
  const message = lockReason("IMPLEMENTED", "rename_project");
  const body = await renderComponent(DISABLED, {
    label: "Rename",
    message,
    variant: "lock",
  });
  assert.match(body, /disabled/);
  assert.match(body, /aria-disabled="true"/);
  assert.match(body, /Rename/);
});

test("DisabledHint message names the Folder_State lock (Req 3.5)", async () => {
  const message = lockReason("PROD_READY", "delete_project");
  const body = await renderComponent(DISABLED, {
    label: "Delete",
    message,
    variant: "lock",
  });
  assert.match(body, /PROD_READY/);
  assert.match(body, /partial lock/i);
});

test("DisabledHint renders the deferred variant message (Req 3.6)", async () => {
  const body = await renderComponent(DISABLED, {
    label: "Download emails",
    message: "This capability is not yet available.",
    variant: "deferred",
  });
  assert.match(body, /not yet available/i);
  assert.match(body, /data-variant="deferred"/);
});
