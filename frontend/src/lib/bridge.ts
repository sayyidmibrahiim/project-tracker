import type {
  ApprovalStatus,
  ApprovalTemplate,
  BridgeResponse,
  DocxExportResult,
  GlobalPlan,
  PywebviewApi,
  RteDocumentPayload,
  RteExportState,
  RteFileContent,
  RteImageSaveResult,
  RteSaveReason,
  RteSaveResult,
} from "./types";
import { BridgeErrorCode } from "./types";

/** Maximum time to wait for a single bridge call before treating it as failed. */
const BRIDGE_TIMEOUT_MS = 30_000;

function summarizeArg(arg: unknown): unknown {
  if (arg === null || arg === undefined) return arg;
  if (typeof arg === "string") return { type: "string", len: arg.length, sample: arg.length > 80 ? `${arg.slice(0, 80)}…` : arg };
  if (typeof arg === "number" || typeof arg === "boolean") return arg;
  if (Array.isArray(arg)) return { type: "array", len: arg.length };
  if (typeof arg === "object") return { type: "object", keys: Object.keys(arg as Record<string, unknown>).slice(0, 20) };
  return { type: typeof arg };
}

function logBridgeEvent(event: Record<string, unknown>): void {
  void import("./activityLogger")
    .then(({ logBridgeCall }) => logBridgeCall(event))
    .catch(() => {});
}

/**
 * Track whether the `pywebviewready` DOM event has fired. pywebview injects
 * an empty `window.pywebview.api` object early; methods are only populated
 * once the event fires. Polling the object alone causes a race where
 * `isPywebviewReady()` returns true but methods are not yet registered.
 */
let _pywebviewEventFired = false;

if (typeof window !== "undefined") {
  // pywebview fires this event once the bridge is fully initialized.
  window.addEventListener("pywebviewready", () => {
    _pywebviewEventFired = true;
  });
  // In case the event already fired before this script loaded:
  if (window.pywebview?.api && Object.keys(window.pywebview.api).length > 0) {
    _pywebviewEventFired = true;
  }
}

/**
 * Return true when the pywebview bridge is available AND fully populated.
 * Safe to call during SSR/Vite dev/build — no global assumptions.
 */
export function isPywebviewReady(): boolean {
  try {
    if (typeof window === "undefined") return false;
    const api = window.pywebview?.api;
    if (api === undefined) return false;
    const hasKeys = Object.keys(api).length > 0;
    // Accept either the event having fired OR the api being populated (covers
    // both normal runtime and test environments where events aren't available).
    if (hasKeys) _pywebviewEventFired = true;
    return _pywebviewEventFired && hasKeys;
  } catch {
    return false;
  }
}

/** Wait for the pywebview bridge to be fully ready (event-driven, not just object existence). */
export async function waitForPywebviewReady(timeoutMs = 5_000, intervalMs = 50): Promise<boolean> {
  if (isPywebviewReady()) return true;
  return new Promise((resolve) => {
    let elapsed = 0;
    const check = () => {
      if (isPywebviewReady()) {
        resolve(true);
        return;
      }
      elapsed += intervalMs;
      if (elapsed >= timeoutMs) {
        resolve(false);
        return;
      }
      setTimeout(check, intervalMs);
    };
    setTimeout(check, intervalMs);
  });
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
async function callBridgeCore<T = unknown>(
  methodName: string,
  args: unknown[],
  log: boolean,
): Promise<BridgeResponse<T>> {
  const started = performance.now();
  if (log) logBridgeEvent({ event: "start", methodName, args: args.map(summarizeArg) });
  if (!isPywebviewReady()) {
    const resp = bridgeError(
      BridgeErrorCode.BRIDGE_UNAVAILABLE,
      "pywebview bridge is not available. Running outside desktop shell or WebView2 not loaded.",
    );
    if (log) logBridgeEvent({ event: "finish", methodName, durationMs: Math.round(performance.now() - started), ok: false, errorCode: resp.error?.code });
    return resp;
  }

  const api = window.pywebview!.api! as PywebviewApi;
  const fn = api[methodName];

  if (typeof fn !== "function") {
    const resp = bridgeError(
      BridgeErrorCode.BRIDGE_METHOD_MISSING,
      `Bridge method "${methodName}" is not registered on window.pywebview.api.`,
    );
    if (log) logBridgeEvent({ event: "finish", methodName, durationMs: Math.round(performance.now() - started), ok: false, errorCode: resp.error?.code });
    return resp;
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
    const result = await Promise.race([callPromise, timeoutPromise]);
    if (log) {
      logBridgeEvent({
        event: "finish",
        methodName,
        durationMs: Math.round(performance.now() - started),
        ok: result.ok,
        errorCode: result.ok ? null : result.error.code,
      });
    }
    return result;
  } finally {
    if (timeoutId !== undefined) {
      clearTimeout(timeoutId);
    }
  }
}

export async function callBridge<T = unknown>(
  methodName: string,
  ...args: unknown[]
): Promise<BridgeResponse<T>> {
  return callBridgeCore<T>(methodName, args, true);
}

export async function callBridgeSilent<T = unknown>(
  methodName: string,
  ...args: unknown[]
): Promise<BridgeResponse<T>> {
  return callBridgeCore<T>(methodName, args, false);
}

// ── Window controls ──

export function winMinimize(): Promise<BridgeResponse<null>> {
  return callBridge("win_minimize");
}

export function winToggleMaximize(): Promise<BridgeResponse<null>> {
  return callBridge("win_toggle_maximize");
}

export function winClose(): Promise<BridgeResponse<null>> {
  return callBridge("win_close");
}

/** Callback type for window state changes. */
export type WinStateCallback = (state: "normal" | "maximized" | "minimized") => void;

let _winStateListeners: WinStateCallback[] = [];

if (typeof window !== "undefined") {
  window.addEventListener("pywin-state", ((e: CustomEvent) => {
    const s = e.detail as "normal" | "maximized" | "minimized";
    _winStateListeners.forEach((cb) => cb(s));
  }) as EventListener);
}

export function onWinStateChange(cb: WinStateCallback): () => void {
  _winStateListeners.push(cb);
  return () => { _winStateListeners = _winStateListeners.filter((f) => f !== cb); };
}

// ── User profile ──

export function getUserProfile(): Promise<BridgeResponse<{ name: string; initials: string; _debug?: string }>> {
  return callBridge("get_user_profile");
}

// ── Global Plan ──

export function globalPlanGet(): Promise<BridgeResponse<GlobalPlan>> {
  return callBridge("global_plan_get");
}

export function globalPlanSave(plan: GlobalPlan): Promise<BridgeResponse<GlobalPlan>> {
  return callBridge("global_plan_save", plan);
}

// ── CR Docs RTE (Piece B) ──

/** Read a file for RTE editing. See backend get_rte_file. */
export function getRteFile(filePath: string): Promise<BridgeResponse<RteFileContent>> {
  return callBridge("get_rte_file", filePath);
}

/** Save RTE content back to a file. See backend save_rte_file. */
export function saveRteFile(
  filePath: string,
  content: string,
): Promise<BridgeResponse<{ saved: boolean }>> {
  return callBridge("save_rte_file", filePath, content);
}

/** Export rendered HTML to a user-chosen Word .docx file. */
export function exportToDocx(
  html: string,
  suggestedName: string,
): Promise<BridgeResponse<DocxExportResult>> {
  return callBridge("export_to_docx", html, "html", suggestedName);
}

// ── Piece C approval automation ──

export function approvalGetStatus(projectPath: string): Promise<BridgeResponse<ApprovalStatus>> {
  return callBridge("get_approval_status", projectPath);
}

export function approvalSetEnabled(projectPath: string, enabled: boolean): Promise<BridgeResponse<{ automation_enabled: boolean }>> {
  return callBridge("approval_set_enabled", projectPath, enabled);
}

export function approvalSetAutoDownload(projectPath: string, kind: "uat" | "lv", enabled: boolean): Promise<BridgeResponse<{ kind: string; auto_download: boolean }>> {
  return callBridge("approval_set_auto_download", projectPath, kind, enabled);
}

export function sendUatApprovalRequest(projectPath: string): Promise<BridgeResponse<{ status: string; job_id?: string }>> {
  return callBridge("send_uat_approval_request", projectPath);
}

export function sendLvApprovalRequest(projectPath: string): Promise<BridgeResponse<{ status: string; job_id?: string }>> {
  return callBridge("send_lv_approval_request", projectPath);
}

export function stopApprovalPolling(projectPath: string, requestType: "uat" | "lv"): Promise<BridgeResponse<{ status: string }>> {
  return callBridge("stop_approval_polling", projectPath, requestType);
}

export function getApprovalTemplate(projectPath: string, kind: "uat" | "lv"): Promise<BridgeResponse<{ source: string; template: ApprovalTemplate }>> {
  return callBridge("get_approval_template", projectPath, kind);
}

export function updateApprovalTemplate(projectPath: string, kind: "uat" | "lv", template: ApprovalTemplate): Promise<BridgeResponse<{ source: string; template: ApprovalTemplate }>> {
  return callBridge("update_approval_template", projectPath, kind, template);
}

export function previewApprovalTemplate(projectPath: string, kind: "uat" | "lv", template: ApprovalTemplate | null): Promise<BridgeResponse<{ to: string; cc: string; subject: string; body: string }>> {
  return callBridge("preview_approval_template", projectPath, kind, template);
}

// ── DOCX pipeline (D-0012): source.json = truth, .docx = derived export ──

/** Open a pipeline document (Tiptap JSON source or migration HTML). */
export function rteDocumentOpen(filePath: string): Promise<BridgeResponse<RteDocumentPayload>> {
  return callBridge("rte_document_open", filePath);
}

/** Save a Tiptap JSON revision to the document's source.json. */
export function rteDocumentSave(
  filePath: string,
  payload: { content: unknown; base_revision: number; reason: RteSaveReason },
): Promise<BridgeResponse<RteSaveResult>> {
  return callBridge("rte_document_save", filePath, payload);
}

/** Store a pasted/inserted image as an asset file next to the document. */
export function rteImageSave(
  filePath: string,
  dataB64: string,
): Promise<BridgeResponse<RteImageSaveResult>> {
  return callBridge("rte_image_save", filePath, dataB64);
}

/** Resolve an asset reference (asset:// or .rte/assets/...) to a data URI. */
export function rteAssetRead(
  filePath: string,
  src: string,
): Promise<BridgeResponse<{ data_uri: string }>> {
  return callBridge("rte_asset_read", filePath, src);
}

/** Queue a background DOCX export of the latest saved revision. */
export function rteExportRequest(filePath: string): Promise<BridgeResponse<RteExportState>> {
  return callBridge("rte_export_request", filePath);
}

/** Poll the export state (only while an export is known to be active). */
export function rteExportStatus(filePath: string): Promise<BridgeResponse<RteExportState>> {
  return callBridge("rte_export_status", filePath);
}
