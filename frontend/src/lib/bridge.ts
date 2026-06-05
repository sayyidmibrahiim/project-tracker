import type { BridgeResponse, PywebviewApi } from "./types";
import { BridgeErrorCode } from "./types";

/**
 * Return true when the pywebview bridge is available.
 * Safe to call during SSR/Vite dev/build — no global assumptions.
 */
export function isPywebviewReady(): boolean {
  try {
    return typeof window !== "undefined" && window.pywebview?.api !== undefined;
  } catch {
    return false;
  }
}

function bridgeError(code: string, message: string): BridgeResponse<never> {
  return {
    ok: false,
    data: null,
    error: { code, message },
  };
}

/**
 * Call a named pywebview API method with controlled error handling.
 *
 * - Bridge missing → `{ ok: false, error: { code: "BRIDGE_UNAVAILABLE" } }`
 * - Method missing → `{ ok: false, error: { code: "BRIDGE_METHOD_MISSING" } }`
 * - Throws/rejects → `{ ok: false, error: { code: "BRIDGE_CALL_FAILED" } }`
 * - Returns BridgeResponse dict → passed through as-is.
 * - Returns non-BridgeResponse value → wrapped as `{ ok: true, data: value }`.
 */
export async function callBridge<T = unknown>(
  methodName: string,
  ...args: unknown[]
): Promise<BridgeResponse<T>> {
  if (!isPywebviewReady()) {
    return bridgeError(
      BridgeErrorCode.BRIDGE_UNAVAILABLE,
      "pywebview bridge is not available. Running outside desktop shell or WebView2 not loaded.",
    );
  }

  const api = window.pywebview!.api! as PywebviewApi;
  const fn = api[methodName];

  if (typeof fn !== "function") {
    return bridgeError(
      BridgeErrorCode.BRIDGE_METHOD_MISSING,
      `Bridge method "${methodName}" is not registered on window.pywebview.api.`,
    );
  }

  try {
    const raw = await fn(...args);

    // If backend returned a BridgeResponse-shaped dict, pass it through.
    if (typeof raw === "object" && raw !== null && "ok" in raw) {
      return raw as BridgeResponse<T>;
    }

    // Otherwise wrap as success.
    return { ok: true, data: raw as T, error: null };
  } catch (err: unknown) {
    const message =
      err instanceof Error ? err.message : String(err);
    return bridgeError(
      BridgeErrorCode.BRIDGE_CALL_FAILED,
      `Bridge call "${methodName}" threw: ${message}`,
    );
  }
}
