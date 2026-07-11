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
  project_state: string | null;
  cr_number: string | null;
  cr_link: string;
  cr_state: string;
  cr_pending_approval_at: string | null;
  start_datetime: string | null;
  end_datetime: string | null;
  t10_status: string;
  drone_ticket_count: number;
  created_at: string | null;
  appcode: string;
  project_type: "CR" | "NON_CR";
  non_cr_state: "PLANNING" | "IN_PROGRESS" | "DONE" | null;
  drones: string[];
  updated_at: string | null;
  scanned_at: string | null;
  drone_tickets: DashboardRowDrone[];
}

/** Mirrors services.dashboard_service.DashboardSummary. */
export interface DashboardSummary {
  total_projects: number;
  by_project_state: Record<string, number>;
  by_cr_state: Record<string, number>;
  by_project_type: Record<string, number>;
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
  appcode: string;
  project_type: "CR" | "NON_CR";
  non_cr_state: "PLANNING" | "IN_PROGRESS" | "DONE" | null;
  drones: string[];
  drone_paths: string[];
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

/** Mirrors AppCodeEntry from infrastructure.filesystem. */
export interface AppCode {
  name: string;
  path: string;
  display_name: string;
  cicd_location: "per_appcode" | "shared_root";
  cicd_shared_path: string | null;
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

// ── CR Docs RTE (Piece B) — mirror get_rte_file / save_rte_file shapes ──

/** RTE file format reported by the backend (see _detect_rte_format). */
export type RteFormat = "html" | "markdown" | "msg" | "text" | "docx";
export type RteCapabilityLevel = "editable" | "read_only" | "unsupported";
export type RteSaveStrategy = "markdown" | "plain_text" | "html" | "docx_legacy" | "docx_pipeline" | "none";
export type RteEditorFeature =
  | "plain_text"
  | "bold"
  | "italic"
  | "strike"
  | "heading"
  | "list"
  | "task_list"
  | "link"
  | "code"
  | "image"
  | "table";

/** A selectable entry in the CR Docs file dropdown. */
export interface RteFile {
  name: string;
  path: string;
  format: RteFormat;
  editable: boolean;
  capability?: RteCapabilityLevel;
  message?: string;
  saveStrategy?: RteSaveStrategy;
  supportedEditorFeatures?: RteEditorFeature[];
  /** True for files the editor cannot render (e.g. .msg → open externally). */
  isOpenable: boolean;
}

/** Payload returned by get_rte_file. */
export interface RteFileContent {
  content: string;
  format: RteFormat;
  editable: boolean;
  capability?: RteCapabilityLevel;
  message?: string;
  saveStrategy?: RteSaveStrategy;
  supportedEditorFeatures?: RteEditorFeature[];
}

/** Result from the native legacy .docx export save dialog. */
export interface DocxExportResult {
  path: string | null;
  written: boolean;
}

// ── DOCX pipeline (D-0012) — mirror rte_document_* bridge shapes ──

/** Export state block returned by rte_export_status / rte_document_open. */
export interface RteExportState {
  state: "idle" | "running" | "pending_retry" | "error";
  revision: number;
  last_exported_revision: number;
  export_pending: boolean;
  last_error: string | null;
}

/** Payload returned by rte_document_open. */
export interface RteDocumentPayload {
  /** Hydrated Tiptap JSON doc, or null when needs_migration. */
  content: Record<string, unknown> | null;
  /** Mammoth HTML for first migration of an existing .docx. */
  content_html: string | null;
  needs_migration: boolean;
  revision: number;
  content_hash: string;
  format: "docx";
  editable: boolean;
  capability: RteCapabilityLevel;
  saveStrategy: RteSaveStrategy;
  supportedEditorFeatures: RteEditorFeature[];
  message?: string;
  export: RteExportState;
}

/** Result of rte_document_save. */
export interface RteSaveResult {
  revision: number;
  content_hash: string;
  skipped: boolean;
  export_scheduled: boolean;
}

/** Result of rte_image_save. */
export interface RteImageSaveResult {
  asset_id: string;
  file_name: string;
  /** Canonical stored reference (asset://<id>.<ext>). */
  src: string;
  /** Path relative to the document folder (.rte/assets/<id>.<ext>) for md files. */
  rel_src: string;
  /** Display source for the editor. */
  data_uri: string;
}

export type RteSaveReason = "autosave" | "manual" | "switch" | "migration";

// ── Piece C approval automation ──
export interface ApprovalJob {
  job_id: string;
  project_path: string;
  request_type: "uat" | "lv";
  cr_number: string;
  email_subject: string;
  sent_at: string | null;
  status: "polling" | "completed" | "timeout" | "stopped" | "dev_skipped";
  reply_received_at: string | null;
}

export interface ApprovalKindStatus {
  eligible: boolean;
  reasons: string[];
  job: ApprovalJob | null;
  auto_download: boolean;
}

export interface ApprovalStatus {
  /** Effective value: per-project override else global default, forced off when locked. */
  automation_enabled: boolean;
  automation_locked: boolean;
  outlook_available: boolean;
  cr_number: string;
  auto_update_cr_state: boolean;
  uat: ApprovalKindStatus;
  lv: ApprovalKindStatus;
}

export interface ApprovalTemplate {
  to: string;
  cc: string;
  subject: string;
  body: string;
  mode: "draft" | "send";
}

/** Slice 2: template summary row for the Automations template list. */
export interface ApprovalTemplateSummary {
  kind: string;
  key: string;
  name: string;
  type: string;
  has_default: boolean;
}

