/**
 * Tests for frontend/src/lib/folderLocks.ts (Task 1.4).
 *
 * Covers the Folder_State -> disabled-action mapping (PRD §9.5) and the
 * Disabled_State_Message naming the locking rule.
 *
 * Validates: Requirements 3.5, 3.6, 3.7
 *
 * Run with: node --test "tests/*.test.ts"
 * (No test-runner dependency: uses the Node built-in test runner + TS strip.)
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  isFolderState,
  isActionDisabled,
  lockReason,
  disabledActions,
  type FolderState,
  type LockableAction,
} from "../src/lib/folderLocks.ts";

const ALL_ACTIONS: LockableAction[] = [
  "edit_metadata",
  "rename_project",
  "delete_project",
  "drone_delete",
  "file_create",
  "file_rename",
  "file_delete",
  "notes_edit",
  "change_cr_drone_state",
  "move_folder",
];

const KNOWN_STATES: FolderState[] = [
  "UAT_PREPARE",
  "PROD_READY",
  "IMPLEMENTED",
  "POSTPONED",
  "CANCELED",
];

// --- isFolderState -----------------------------------------------------------

test("isFolderState accepts every known Folder_State", () => {
  for (const state of KNOWN_STATES) {
    assert.equal(isFolderState(state), true, `expected ${state} to be valid`);
  }
});

test("isFolderState rejects unknown / malformed states", () => {
  for (const bad of ["", "uat_prepare", "DONE", "prod_ready", "unknown", " "]) {
    assert.equal(isFolderState(bad), false, `expected "${bad}" to be invalid`);
  }
});

// --- folderLocks mapping per state (PRD §9.5) --------------------------------

test("UAT_PREPARE is fully editable (nothing disabled)", () => {
  for (const action of ALL_ACTIONS) {
    assert.equal(
      isActionDisabled("UAT_PREPARE", action),
      false,
      `${action} should be enabled in UAT_PREPARE`,
    );
  }
  assert.deepEqual(disabledActions("UAT_PREPARE"), []);
});

test("PROD_READY partial lock: edit/rename/delete + destructive file ops disabled", () => {
  const expectedDisabled: LockableAction[] = [
    "edit_metadata",
    "rename_project",
    "delete_project",
    "drone_delete",
    "file_create",
    "file_rename",
    "file_delete",
  ];
  for (const action of expectedDisabled) {
    assert.equal(
      isActionDisabled("PROD_READY", action),
      true,
      `${action} should be disabled in PROD_READY`,
    );
  }
  // Notes editing, CR/Drone progression, and folder moves remain allowed.
  for (const action of ["notes_edit", "change_cr_drone_state", "move_folder"] as LockableAction[]) {
    assert.equal(
      isActionDisabled("PROD_READY", action),
      false,
      `${action} should remain allowed in PROD_READY`,
    );
  }
  assert.deepEqual(
    [...disabledActions("PROD_READY")].sort(),
    [...expectedDisabled].sort(),
  );
});

test("IMPLEMENTED is fully locked / read-only (every action disabled, notes view-only)", () => {
  for (const action of ALL_ACTIONS) {
    assert.equal(
      isActionDisabled("IMPLEMENTED", action),
      true,
      `${action} should be disabled in IMPLEMENTED`,
    );
  }
  assert.deepEqual(
    [...disabledActions("IMPLEMENTED")].sort(),
    [...ALL_ACTIONS].sort(),
  );
});

test("POSTPONED and CANCELED are editable per §9.5 (nothing disabled here)", () => {
  for (const state of ["POSTPONED", "CANCELED"] as FolderState[]) {
    for (const action of ALL_ACTIONS) {
      assert.equal(
        isActionDisabled(state, action),
        false,
        `${action} should be enabled in ${state}`,
      );
    }
    assert.deepEqual(disabledActions(state), []);
  }
});

// --- fail-safe for unknown states --------------------------------------------

test("unknown state is treated as fully locked (fail-safe)", () => {
  for (const action of ALL_ACTIONS) {
    assert.equal(
      isActionDisabled("MYSTERY", action),
      true,
      `${action} should be disabled for an unknown state`,
    );
  }
  assert.deepEqual(
    [...disabledActions("MYSTERY")].sort(),
    [...ALL_ACTIONS].sort(),
  );
});

// --- lockReason: Disabled_State_Message names the locking rule ---------------

test("lockReason returns null when the action is allowed", () => {
  assert.equal(lockReason("UAT_PREPARE", "delete_project"), null);
  assert.equal(lockReason("PROD_READY", "notes_edit"), null);
  assert.equal(lockReason("POSTPONED", "file_delete"), null);
});

test("lockReason for PROD_READY names the state and partial lock", () => {
  const reason = lockReason("PROD_READY", "delete_project");
  assert.notEqual(reason, null);
  assert.match(reason as string, /PROD_READY/);
  assert.match(reason as string, /partial lock/i);
});

test("lockReason for IMPLEMENTED names the state and full lock", () => {
  const reason = lockReason("IMPLEMENTED", "rename_project");
  assert.notEqual(reason, null);
  assert.match(reason as string, /IMPLEMENTED/);
  assert.match(reason as string, /locked|read-only/i);
});

test("lockReason for IMPLEMENTED notes_edit states notes are view-only", () => {
  const reason = lockReason("IMPLEMENTED", "notes_edit");
  assert.notEqual(reason, null);
  assert.match(reason as string, /view-only/i);
  assert.match(reason as string, /IMPLEMENTED/);
});

test("lockReason for an unknown state names the unknown state", () => {
  const reason = lockReason("MYSTERY", "file_create");
  assert.notEqual(reason, null);
  assert.match(reason as string, /unknown/i);
  assert.match(reason as string, /MYSTERY/);
});

test("every disabled action yields a non-empty lockReason; allowed ones yield null", () => {
  for (const state of KNOWN_STATES) {
    for (const action of ALL_ACTIONS) {
      const disabled = isActionDisabled(state, action);
      const reason = lockReason(state, action);
      if (disabled) {
        assert.equal(typeof reason, "string", `${state}/${action} should have a reason`);
        assert.ok((reason as string).length > 0);
      } else {
        assert.equal(reason, null, `${state}/${action} should have no reason`);
      }
    }
  }
});
