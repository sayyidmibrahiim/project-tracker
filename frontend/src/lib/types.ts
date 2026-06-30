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
  BRIDGE_TIMEOUT: "BRIDGE_TIMEOUT",
  BRIDGE_MALFORMED_RESPONSE: "BRIDGE_MALFORMED_RESPONSE",
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

/** Mirrors a drone ticket shown inline on a Dashboard row (DashboardRowDrone). */
export interface DashboardRowDrone {
  subfolder_name: string | null;
  drone_ticket: string;
  drone_link: string;
  drone_state: string;
  owner: string;
}

/** Mirrors services.dashboard_service.DashboardProject (after _to_frontend_safe). */
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
  subprojects: string[];
  updated_at: string | null;
  scanned_at: string | null;
  drone_tickets: DashboardRowDrone[];
}

/** Mirrors services.dashboard_service.DashboardSummary. */
export interface DashboardSummary {
  total_projects: number;
  by_project_state: Record<string, number>;
  by_cr_state: Record<string, number>;
  by_t10_status: Record<string, number>;
  total_drone_tickets: number;
}

/** Mirrors services.dashboard_service.DashboardData. */
export interface DashboardData {
  projects: DashboardProject[];
  summary: DashboardSummary;
}

// ── Notification / Event DTOs ──

/** Mirrors notification item after _to_frontend_safe. */
export interface NotificationItem {
  id: string;
  type: string;
  title: string;
  message: string;
  timestamp: string;
  project_path: string | null;
  dismissed: boolean;
}

/** Mirrors event queue item after drain_events. */
export interface EventItem {
  type: string;
  payload: Record<string, unknown>;
  timestamp: string;
}

// ── Project Details DTOs — match Python project_get / project_list shapes ──

/** Mirrors project detail returned by project_get (FakeProjectDetail shape from tests). */
export interface ProjectDetail {
  project_name: string;
  project_path: string;
  project_state: string;
  cr_number: string;
  cr_link: string;
  cr_state: string;
  start_datetime: string | null;
  end_datetime: string | null;
  t10_status: string;
  drone_ticket_count: number;
  drone_tickets: DroneTicket[];
  implementation_plan?: string | null;
  history?: HistoryEntry[];
  is_subproject?: boolean;
  subprojects?: string[];
}

/** Mirrors HistoryEntry metadata rows returned by project_get. */
export interface HistoryEntry {
  timestamp: string;
  action: string;
  detail: string;
  user: string;
}

/** Mirrors DroneTicket metadata fields. */
export interface DroneTicket {
  subfolder_name: string | null;
  drone_link: string;
  drone_ticket?: string;
  drone_state: string;
  owner: string;
}

/** Mirrors project row returned by project_list. */
export interface ProjectRow {
  project_name: string;
  project_path: string;
  project_state: string;
  cr_number: string;
  cr_state: string;
}

/** Mirrors file row returned by file_list. */
export interface FileRow {
  name: string;
  path: string;
}

// ── Global Plan DTOs ──

export type GlobalPlanStatus = "backlog" | "ready" | "doing" | "review" | "done";

export interface GlobalPlanItem {
  id: string;
  title: string;
  menu: string;
  branch_desc: string;
  status: GlobalPlanStatus;
  goal: string;
  acceptance_checks: string[];
  notes: string;
  blocked_reason: string;
  updated_at: string;
}

export interface GlobalPlan {
  schema: number;
  loop_rule: string[];
  items: GlobalPlanItem[];
}

// ── Automation DTOs — match Python automation_list_rules / evaluate shapes ──

/** Mirrors automation rule returned by automation_list_rules. */
export interface AutomationRule {
  id: string;
  name: string;
  enabled: boolean;
  conditions: Record<string, unknown>[];
}

/** Mirrors automation evaluation result. */
export interface AutomationResult {
  rule_id: string;
  rule_name: string;
  passed: boolean;
  skipped: boolean;
  matched_conditions: Record<string, unknown>[];
}

// ── Second Brain DTOs — match Python second_brain_list/search/get shapes ──

/** Mirrors SecondBrainItem from second_brain_list/search/get. */
export interface SecondBrainItem {
  id: string;
  title: string;
  path: string;
  item_type: string;
  updated_at: string | null;
  pinned: boolean;
  favorite: boolean;
  excerpt?: string;
}
