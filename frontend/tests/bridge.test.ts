/**
 * Unit tests for `src/lib/bridge.ts` — timeout and malformed-response handling.
 *
 * These tests cover Requirements 1.7 and 1.8:
 *  - 1.8: a malformed/absent Bridge_Response, or a call that does not resolve
 *    within 30 seconds, is treated as failed.
 *  - 1.7: a well-formed `ok=false` response is passed through unchanged and never
 *    presented as a success (no success state on failure).
 *
 * Runtime: Node's built-in test runner (`node:test`) with its mock timers, so the
 * 30-second timeout is exercised without real waiting. Source is bundled with the
 * already-installed `esbuild` (see `npm test`) — no new dependencies are added.
 */
import { test, mock } from "node:test";
import assert from "node:assert/strict";

import { callBridge, waitForPywebviewReady } from "../src/lib/bridge.ts";
import { BridgeErrorCode } from "../src/lib/types.ts";

type AnyApi = Record<string, unknown> | undefined;

/** Install a fake `window.pywebview.api` (or remove the bridge entirely). */
function setBridge(api: AnyApi): void {
  if (api === undefined) {
    // Bridge present as a window but no pywebview → unavailable.
    (globalThis as unknown as { window: unknown }).window = {};
    return;
  }
  (globalThis as unknown as { window: unknown }).window = {
    pywebview: { api },
  };
}

function clearBridge(): void {
  delete (globalThis as unknown as { window?: unknown }).window;
}

const okResponse = { ok: true, data: { value: 42 }, error: null };
const failResponse = {
  ok: false,
  data: null,
  error: { code: "PROJECT_RENAME_FAILED", message: "name already exists" },
};

test("returns BRIDGE_UNAVAILABLE when the bridge is missing", async () => {
  setBridge(undefined);
  try {
    const res = await callBridge("anything");
    assert.equal(res.ok, false);
    assert.equal(res.error?.code, BridgeErrorCode.BRIDGE_UNAVAILABLE);
  } finally {
    clearBridge();
  }
});

test("waitForPywebviewReady resolves true when the bridge appears before timeout", async () => {
  setBridge(undefined);
  mock.timers.enable({ apis: ["setTimeout"] });
  try {
    const pending = waitForPywebviewReady(3000, 50);
    mock.timers.tick(100);
    setBridge({ existing: () => okResponse });
    mock.timers.tick(50);
    assert.equal(await pending, true);
  } finally {
    mock.timers.reset();
    clearBridge();
  }
});

test("waitForPywebviewReady resolves false after timeout when bridge never appears", async () => {
  setBridge(undefined);
  try {
    assert.equal(await waitForPywebviewReady(5, 1), false);
  } finally {
    clearBridge();
  }
});

test("returns BRIDGE_METHOD_MISSING when the method is not registered", async () => {
  setBridge({ existing: () => okResponse });
  try {
    const res = await callBridge("missing_method");
    assert.equal(res.ok, false);
    assert.equal(res.error?.code, BridgeErrorCode.BRIDGE_METHOD_MISSING);
  } finally {
    clearBridge();
  }
});

test("passes through a well-formed ok=true response unchanged", async () => {
  setBridge({ get_value: () => okResponse });
  try {
    const res = await callBridge<{ value: number }>("get_value");
    assert.equal(res.ok, true);
    assert.deepEqual(res.data, { value: 42 });
    assert.equal(res.error, null);
  } finally {
    clearBridge();
  }
});

test("passes through a well-formed ok=false response without any success state", async () => {
  // Requirement 1.7: ok=false is surfaced as a failure, never as success.
  setBridge({ rename: () => failResponse });
  try {
    const res = await callBridge("rename");
    assert.equal(res.ok, false);
    assert.equal(res.data, null);
    assert.equal(res.error?.code, "PROJECT_RENAME_FAILED");
    assert.equal(res.error?.message, "name already exists");
  } finally {
    clearBridge();
  }
});

test("treats an absent (undefined) response as BRIDGE_MALFORMED_RESPONSE", async () => {
  setBridge({ noop: () => undefined });
  try {
    const res = await callBridge("noop");
    assert.equal(res.ok, false);
    assert.equal(res.error?.code, BridgeErrorCode.BRIDGE_MALFORMED_RESPONSE);
  } finally {
    clearBridge();
  }
});

test("treats a response missing the `ok` field as malformed", async () => {
  setBridge({ weird: () => ({ data: { value: 1 }, error: null }) });
  try {
    const res = await callBridge("weird");
    assert.equal(res.ok, false);
    assert.equal(res.error?.code, BridgeErrorCode.BRIDGE_MALFORMED_RESPONSE);
  } finally {
    clearBridge();
  }
});

test("treats an ok=true response with no `data` key as malformed", async () => {
  setBridge({ partial: () => ({ ok: true, error: null }) });
  try {
    const res = await callBridge("partial");
    assert.equal(res.ok, false);
    assert.equal(res.error?.code, BridgeErrorCode.BRIDGE_MALFORMED_RESPONSE);
  } finally {
    clearBridge();
  }
});

test("treats an ok=false response with no `error` object as malformed", async () => {
  setBridge({ inconsistent: () => ({ ok: false, data: null, error: null }) });
  try {
    const res = await callBridge("inconsistent");
    assert.equal(res.ok, false);
    assert.equal(res.error?.code, BridgeErrorCode.BRIDGE_MALFORMED_RESPONSE);
  } finally {
    clearBridge();
  }
});

test("returns BRIDGE_CALL_FAILED when the bridge method throws", async () => {
  setBridge({
    boom: () => {
      throw new Error("kaboom");
    },
  });
  try {
    const res = await callBridge("boom");
    assert.equal(res.ok, false);
    assert.equal(res.error?.code, BridgeErrorCode.BRIDGE_CALL_FAILED);
    assert.match(res.error?.message ?? "", /kaboom/);
  } finally {
    clearBridge();
  }
});

test("returns BRIDGE_TIMEOUT after 30s when the call never resolves", async () => {
  // A method whose promise never settles must not hang the caller forever.
  setBridge({ hang: () => new Promise<never>(() => {}) });
  mock.timers.enable({ apis: ["setTimeout"] });
  try {
    const pending = callBridge("hang");
    // Advance virtual time to the 30s boundary; the timeout branch should win.
    mock.timers.tick(30_000);
    const res = await pending;
    assert.equal(res.ok, false);
    assert.equal(res.error?.code, BridgeErrorCode.BRIDGE_TIMEOUT);
  } finally {
    mock.timers.reset();
    clearBridge();
  }
});

test("does not time out when the call resolves before 30s", async () => {
  setBridge({ quick: () => okResponse });
  mock.timers.enable({ apis: ["setTimeout"] });
  try {
    const res = await callBridge<{ value: number }>("quick");
    assert.equal(res.ok, true);
    assert.deepEqual(res.data, { value: 42 });
  } finally {
    mock.timers.reset();
    clearBridge();
  }
});
