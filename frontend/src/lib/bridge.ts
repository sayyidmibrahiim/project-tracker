import type { BridgeResponse, PywebviewApi } from "./types";
import { BridgeErrorCode } from "./types";

/** Maximum time to wait for a single bridge call before treating it as failed. */
const BRIDGE_TIMEOUT_MS = 30_000;

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
 * Return true when `raw` is a structurally consistent Bridge_Response:
 * - it is a non-null object with a boolean `ok`;
 * - when `ok === false`, it carries an `error` object with string `code` and `message`;
 * - when `ok === true`, it carries a `data` key and no non-null `error`.
 *
 * Anything else (missing `ok`, non-object, ok-shaped but inconsistent) is malformed.
 */
function isWellFormedBridgeResponse(raw: unknown): boolean {
  if (typeof raw !== "object" || raw === null) {
    return false;
  }
  const obj = raw as Record<string, unknown>;
  if (typeof obj.ok !== "boolean") {
    return false;
  }

  if (obj.ok === false) {
    const err = obj.error;
    if (typeof err !== "object" || err === null) {
      return false;
    }
    const errObj = err as Record<string, unknown>;
    return typeof errObj.code === "string" && typeof errObj.message === "string";
  }

  // ok === true: must expose a `data` key and must not carry a non-null error.
  if (!("data" in obj)) {
    return false;
  }
  return obj.error === undefined || obj.error === null;
}

/**
 * Call a named pywebview API method with controlled error handling.
 *
 * - Bridge missing → `{ ok: false, error: { code: "BRIDGE_UNAVAILABLE" } }`
 * - Method missing → `{ ok: false, error: { code: "BRIDGE_METHOD_MISSING" } }`
 * - Throws/rejects → `{ ok: false, error: { code: "BRIDGE_CALL_FAILED" } }`
 * - Does not resolve within 30s → `{ ok: false, error: { code: "BRIDGE_TIMEOUT" } }`
 * - Malformed/absent response → `{ ok: false, error: { code: "BRIDGE_MALFORMED_RESPONSE" } }`
 * - Returns a well-formed BridgeResponse dict → passed through as-is.
 *
 * All `window.pywebview` access is contained within this function.
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

  // Resolve the actual call (with error + malformed handling) and race it against
  // a 30-second timeout so a hung bridge never leaves the caller waiting forever.
  let timeoutId: ReturnType<typeof setTimeout> | undefined;
  const timeoutPromise = new Promise<BridgeResponse<T>>((resolve) => {
    timeoutId = setTimeout(() => {
      resolve(
        bridgeError(
          BridgeErrorCode.BRIDGE_TIMEOUT,
          `Bridge call "${methodName}" did not resolve within 30 seconds.`,
        ),
      );
    }, BRIDGE_TIMEOUT_MS);
  });

  const callPromise: Promise<BridgeResponse<T>> = (async () => {
    try {
      const raw = await fn(...args);

      if (!isWellFormedBridgeResponse(raw)) {
        return bridgeError(
          BridgeErrorCode.BRIDGE_MALFORMED_RESPONSE,
          `Bridge call "${methodName}" returned a malformed or absent response.`,
        );
      }

      // Well-formed BridgeResponse (ok=true or ok=false) → pass through as-is.
      return raw as BridgeResponse<T>;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      return bridgeError(
        BridgeErrorCode.BRIDGE_CALL_FAILED,
        `Bridge call "${methodName}" threw: ${message}`,
      );
    }
  })();

  try {
    return await Promise.race([callPromise, timeoutPromise]);
  } finally {
    if (timeoutId !== undefined) {
      clearTimeout(timeoutId);
    }
  }
}
