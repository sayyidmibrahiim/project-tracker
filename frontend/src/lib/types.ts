/** Bridge error payload — mirrors Python `fail()` error shape. */
export interface BridgeError {
  code: string;
  message: string;
  details?: unknown;
}

/** Success bridge response. */
export interface BridgeOk<T = unknown> {
  ok: true;
  data: T | null;
  error: null;
}

/** Failure bridge response. */
export interface BridgeFail {
  ok: false;
  data: null;
  error: BridgeError;
}

/** Generic bridge response — union of ok/fail shapes. */
export type BridgeResponse<T = unknown> = BridgeOk<T> | BridgeFail;

/** Known bridge error codes for controlled client-side handling. */
export const BridgeErrorCode = {
  BRIDGE_UNAVAILABLE: "BRIDGE_UNAVAILABLE",
  BRIDGE_METHOD_MISSING: "BRIDGE_METHOD_MISSING",
  BRIDGE_CALL_FAILED: "BRIDGE_CALL_FAILED",
} as const;

/** pywebview API surface — method name → callable. */
export interface PywebviewApi {
  [method: string]: ((...args: unknown[]) => unknown) | undefined;
}

/** pywebview global — only present inside pywebview's WebView2/webview shell. */
export interface PywebviewGlobal {
  api: PywebviewApi | undefined;
}

/** Extend Window with optional pywebview property. */
declare global {
  interface Window {
    pywebview?: PywebviewGlobal;
  }
}
