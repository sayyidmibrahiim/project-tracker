/**
 * Unit tests for the DOCX pipeline state helpers (D-0012).
 * Pure logic — no DOM, runs under node --test type stripping.
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import { IdleExportScheduler, docxCountdownLabel, docxStatusLabel, mapExportState } from "../src/lib/rteDocxState.ts";
import type { RteExportState } from "../src/lib/types.ts";

function state(partial: Partial<RteExportState>): RteExportState {
  return {
    state: "idle",
    revision: 0,
    last_exported_revision: 0,
    export_pending: false,
    last_error: null,
    ...partial,
  };
}

test("mapExportState maps backend states onto display states", () => {
  assert.equal(mapExportState(null), "idle");
  assert.equal(mapExportState(state({ state: "running" })), "exporting");
  assert.equal(mapExportState(state({ state: "pending_retry", last_error: "locked" })), "locked");
  assert.equal(mapExportState(state({ state: "error", last_error: "boom" })), "failed");
  assert.equal(mapExportState(state({ revision: 3, last_exported_revision: 3 })), "done");
  // Never exported yet → idle, not done.
  assert.equal(mapExportState(state({ revision: 1, last_exported_revision: 0 })), "idle");
});

test("docxStatusLabel renders pipeline labels and falls back to the base label", () => {
  assert.equal(docxStatusLabel("exporting", "Saved"), "Exporting DOCX…");
  assert.equal(docxStatusLabel("done", "Saved"), "DOCX saved");
  assert.equal(docxStatusLabel("locked", "Saved"), "DOCX locked — will retry");
  assert.equal(docxStatusLabel("failed", "Saved"), "Export failed — source safe");
  assert.equal(docxStatusLabel("idle", "Saved"), "Saved");
});

test("docxCountdownLabel shows whole seconds and never 0s", () => {
  assert.equal(docxCountdownLabel(5), "Saved — DOCX in 5s");
  assert.equal(docxCountdownLabel(1), "Saved — DOCX in 1s");
  assert.equal(docxCountdownLabel(0.4), "Saved — DOCX in 1s");
});

test("IdleExportScheduler fires once per quiet period; bumps restart the wait", async () => {
  let fired = 0;
  const sched = new IdleExportScheduler(30, () => { fired += 1; });
  sched.bump();
  sched.bump(); // typing continues → restart, no double fire
  assert.equal(sched.pending, true);
  await new Promise((r) => setTimeout(r, 80));
  assert.equal(fired, 1);
  assert.equal(sched.pending, false);
  // Nothing fires again without a new bump (selection-only changes never bump).
  await new Promise((r) => setTimeout(r, 50));
  assert.equal(fired, 1);
});

test("IdleExportScheduler cancel prevents the pending fire", async () => {
  let fired = 0;
  const sched = new IdleExportScheduler(20, () => { fired += 1; });
  sched.bump();
  sched.cancel();
  await new Promise((r) => setTimeout(r, 60));
  assert.equal(fired, 0);
  assert.equal(sched.pending, false);
});
