/**
 * Tests for frontend/src/lib/dashboardChips.ts (Task 10, C2).
 *
 * Covers the CR/Drone state -> semantic colour-chip class mapping used by the
 * inline state selects on the dashboard.
 *
 * Run with: node --test "tests/*.test.ts"
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import { stateChipClass } from "../src/lib/dashboardChips.ts";

test("APPROVED maps to the green chip", () => {
  assert.equal(stateChipClass("APPROVED"), "chip-approved");
  assert.equal(stateChipClass("approved"), "chip-approved");
});

test("any PENDING state maps to the amber chip", () => {
  assert.equal(stateChipClass("PENDING SUBMISSION"), "chip-pending");
  assert.equal(stateChipClass("PENDING APPROVAL"), "chip-pending");
  assert.equal(stateChipClass("PENDING_APPROVAL"), "chip-pending");
});

test("CANCELED and POSTPONED map to the negative (red) chip", () => {
  assert.equal(stateChipClass("CANCELED"), "chip-negative");
  assert.equal(stateChipClass("POSTPONED"), "chip-negative");
});

test("other states map to the neutral chip", () => {
  assert.equal(stateChipClass("IN-PROGRESS"), "chip-neutral");
  assert.equal(stateChipClass("IN_PROGRESS"), "chip-neutral");
  assert.equal(stateChipClass("FINISHED"), "chip-neutral");
  assert.equal(stateChipClass("UAT"), "chip-neutral");
});

test("blank / nullish state is neutral, never throws", () => {
  assert.equal(stateChipClass(""), "chip-neutral");
  assert.equal(stateChipClass(null), "chip-neutral");
  assert.equal(stateChipClass(undefined), "chip-neutral");
});
