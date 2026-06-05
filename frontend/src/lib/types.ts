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

// ── Dashboard DTOs — match Python DashboardProject / DashboardSummary / DashboardData ──

/** Mirrors project_tracker.services.dashboard_service.DashboardProject (after _to_frontend_safe). */
export interface DashboardProject {
  project_path: string;
  year: string;
  project_name: string;
  project_state: string;
  cr_number: string | null;
  cr_link: string;
  cr_state: string;
  cr_pending_approval_at: string | null;
  start_datetime: string | null;
  end_datetime: string | null;
  t10_status: string;
  drone_ticket_count: number;
  updated_at: string | null;
  scanned_at: string | null;
}

/** Mirrors project_tracker.services.dashboard_service.DashboardSummary. */
export interface DashboardSummary {
  total_projects: number;
  by_project_state: Record<string, number>;
  by_cr_state: Record<string, number>;
  by_t10_status: Record<string, number>;
  total_drone_tickets: number;
}

/** Mirrors project_tracker.services.dashboard_service.DashboardData. */
export interface DashboardData {
  projects: DashboardProject[];
  summary: DashboardSummary;
}
