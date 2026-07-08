<script lang="ts">
  import { onDestroy, onMount } from "svelte";
  import { approvalForceCheck, approvalGetStatus, approvalSend, approvalSetAutoDownload, approvalSetAutoUpdateCrState, approvalSetEnabled, callBridge, getRteFile, isPywebviewReady, rteDocumentOpen, stopApprovalPolling, waitForPywebviewReady } from "../bridge";
  import type { ApprovalStatus, ProjectRow, ProjectDetail, FileRow, RteDocumentPayload, RteFile, RteFileContent } from "../types";
  import { BridgeErrorCode } from "../types";
  import FileActions from "./FileActions.svelte";
  import NotesEditor from "./NotesEditor.svelte";
  import NewProjectForm from "./NewProjectForm.svelte";
  import DroneTable from "./DroneTable.svelte";
  import ConfirmModal from "./ConfirmModal.svelte";
  import { addToast } from "../stores/toastStore";
  import type { ToastAction } from "../stores/toastStore";

  // Optional cross-page navigation from the Dashboard row menu / header Add Project.
  let { initialPath = null, startNew = false, onNavigateDashboard, onNavigateAutomations }: { initialPath?: string | null; startNew?: boolean; onNavigateDashboard?: () => void; onNavigateAutomations?: (kind?: "uat" | "lv", goal?: string) => void } = $props();

  type LoadState = "idle" | "loading" | "error" | "loaded";
  let listState: LoadState = $state("idle");
  let detailState: LoadState = $state("idle");
  let errorCode: string = $state("");
  let errorMessage: string = $state("");

  let projects: ProjectRow[] = $state([]);
  let selectedPath: string = $state("");
  let detail: ProjectDetail | null = $state(null);
  let isNonCr: boolean = $state(false);
  // ── Piece C approval automation (spec 2026-07-02) ──
  let approvalStatus: ApprovalStatus | null = $state(null);
  let approvalBusy: "" | "uat" | "lv" | "toggle" = $state("");
  let approvalError = $state("");
  let approvalPollTimer: ReturnType<typeof setInterval> | undefined;
  // Armed by the Send button (irreversible outward action → ConfirmModal gate).
  let pendingSend: { kind: "uat" | "lv"; label: string } | null = $state(null);

  function stopApprovalStatusPoll() {
    if (approvalPollTimer !== undefined) { clearInterval(approvalPollTimer); approvalPollTimer = undefined; }
  }

  async function loadApprovalStatus() {
    if (!selectedPath || isNonCr || !isPywebviewReady()) { approvalStatus = null; stopApprovalStatusPoll(); return; }
    const resp = await approvalGetStatus(selectedPath);
    if (!resp.ok) { approvalError = resp.error.message; return; }
    approvalStatus = resp.data ?? null;
    const polling = approvalStatus?.uat.job?.status === "polling" || approvalStatus?.lv.job?.status === "polling";
    if (polling && approvalPollTimer === undefined) {
      approvalPollTimer = setInterval(() => void loadApprovalStatus(), 15000);
    } else if (!polling) {
      stopApprovalStatusPoll();
    }
  }

  async function toggleApproval() {
    if (!selectedPath || !approvalStatus) return;
    approvalBusy = "toggle"; approvalError = "";
    const resp = await approvalSetEnabled(selectedPath, !approvalStatus.automation_enabled);
    if (!resp.ok) approvalError = resp.error.message;
    await loadApprovalStatus();
    approvalBusy = "";
  }

  function requestSend(kind: "uat" | "lv", label: string) {
    approvalError = "";
    pendingSend = { kind, label };
  }

  async function confirmSend() {
    const p = pendingSend;
    pendingSend = null;
    if (!p || !selectedPath) return;
    approvalBusy = p.kind; approvalError = "";
    const resp = await approvalSend(selectedPath, p.kind, "send");
    if (!resp.ok) approvalError = resp.error.message;
    else if (resp.data?.status === "sent") addToast("Sent — auto-download reply is OFF for this request", "info");
    else if (resp.data?.status === "polling") addToast("Sent — now waiting for the reply", "info");
    await loadApprovalStatus();
    approvalBusy = "";
  }

  async function draftApproval(kind: "uat" | "lv") {
    if (!selectedPath) return;
    approvalBusy = kind; approvalError = "";
    const resp = await approvalSend(selectedPath, kind, "draft");
    if (!resp.ok) approvalError = resp.error.message;
    else addToast("Draft opened in Outlook — review then send", "info");
    await loadApprovalStatus();
    approvalBusy = "";
  }

  async function forceCheck(kind: "uat" | "lv") {
    if (!selectedPath) return;
    approvalBusy = kind; approvalError = "";
    const resp = await approvalForceCheck(selectedPath, kind);
    if (!resp.ok) approvalError = resp.error.message;
    else if (resp.data?.status === "completed") addToast("Reply found and downloaded to _cr-docs", "info");
    else if (resp.data?.status === "polling") addToast("No reply yet — still waiting", "info");
    await loadApprovalStatus();
    approvalBusy = "";
  }

  async function toggleAutoDownload(kind: "uat" | "lv") {
    if (!selectedPath || !approvalStatus) return;
    const current = kind === "uat" ? approvalStatus.uat.auto_download : approvalStatus.lv.auto_download;
    approvalBusy = kind; approvalError = "";
    const resp = await approvalSetAutoDownload(selectedPath, kind, !current);
    if (!resp.ok) approvalError = resp.error.message;
    await loadApprovalStatus();
    approvalBusy = "";
  }

  async function toggleAutoUpdateCrState() {
    if (!selectedPath || !approvalStatus) return;
    approvalBusy = "toggle"; approvalError = "";
    const resp = await approvalSetAutoUpdateCrState(selectedPath, !approvalStatus.auto_update_cr_state);
    if (!resp.ok) approvalError = resp.error.message;
    await loadApprovalStatus();
    approvalBusy = "";
  }

  function openAutomations(kind?: "uat" | "lv", goal?: string) {
    onNavigateAutomations?.(kind, goal);
  }

  function devStub(message: string) {
    addToast(message, "info");
  }

  // Status dot class + short label per Outlook kind (🟢 Done, 🟡 Waiting, 🔴 Error, ⚪ Inactive/Ready).
  function autoDot(kind: "uat" | "lv"): string {
    if (!approvalStatus) return "dot-inactive";
    const ks = kind === "uat" ? approvalStatus.uat : approvalStatus.lv;
    const s = ks.job?.status ?? "";
    if (s === "completed") return "dot-done";
    if (s === "polling") return "dot-waiting";
    if (s === "timeout") return "dot-error";
    return ks.eligible ? "dot-ready" : "dot-inactive";
  }

  function autoLabel(kind: "uat" | "lv"): string {
    if (!approvalStatus) return "";
    const ks = kind === "uat" ? approvalStatus.uat : approvalStatus.lv;
    const s = ks.job?.status ?? "";
    const cr = approvalStatus.cr_number || "—";
    if (s === "completed") return "Reply received ✓";
    if (s === "polling") return `Waiting for reply · ${cr}`;
    if (s === "timeout") return "No reply (timeout) — retry";
    return ks.eligible ? `Ready · ${cr}` : `Not ready: ${ks.reasons.join(", ")}`;
  }

  async function stopApproval(kind: "uat" | "lv") {
    if (!selectedPath) return;
    approvalBusy = kind; approvalError = "";
    const resp = await stopApprovalPolling(selectedPath, kind);
    if (!resp.ok) approvalError = resp.error.message;
    await loadApprovalStatus();
    approvalBusy = "";
  }
  let selectedSubproject: string = $state("all");
  let drones: string[] = $state([]);
  let files: FileRow[] = $state([]);
  let notes: string = $state("");
  let showNotesEditor: boolean = $state(false);

  // ── CR Docs (Piece B): multi-file RTE selector for CR projects ──
  // For CR projects the Notes section becomes "Notes & CR Docs" with a dropdown
  // to switch between notes.md (markdown), _cr-docs/*.docx (Word), and any
  // _cr-docs/*.msg (open externally). Non-CR keeps plain Notes unchanged.
  let crDocsFiles: RteFile[] = $state([]);
  let selectedCrDocPath: string = $state("");
  let crDocContent: RteFileContent | null = $state(null);
  let crDocContentPath: string = $state("");
  /** DOCX pipeline payload (D-0012) for the selected .docx CR doc. */
  let crDocDocPayload: RteDocumentPayload | null = $state(null);
  let crDocsLoading: boolean = $state(false);
  let crDocsError: string = $state("");
  let crDocsFlushing: boolean = $state(false);
  let rteEditorFlush: (() => Promise<boolean>) | undefined;
  function setRteEditorApi(api: { flushNow: () => Promise<boolean> } | undefined) {
    rteEditorFlush = api?.flushNow;
  }
  type TopActionState = "idle" | "saving" | "success" | "error";
  let topActionState: TopActionState = $state("idle");
  let topActionError: string = $state("");
  let topDeletePending: boolean = $state(false);

  // ── NEW_PROJECT mode (PRD §12.4): toggles the detail panel into a create form ──
  let mode: "browse" | "new" = $state("browse");

  // ── CR Link edit state ──
  let crLinkEdit: string = $state("");
  let crLinkEditing: boolean = $state(false);
  let crLinkCopied: boolean = $state(false);
  type CrLinkSave = "idle" | "saving" | "success" | "error";
  let crLinkSaveState: CrLinkSave = $state("idle");
  let crLinkSaveError: string = $state("");

  // ── CR State edit state ──
  // Real CRState enum values (REOPEN excluded — action/event, not a persist target).
  const CR_STATE_OPTIONS = ["PENDING SUBMISSION", "PENDING APPROVAL", "APPROVED", "IN-PROGRESS", "FINISHED", "POSTPONED", "CANCELED"];
  // REOPEN is an action (PRD §9.1), not a persistent CR state. It is offered in
  // the CR dropdown only when the project folder is POSTPONED/CANCELED, and
  // selecting it routes to `folder_reopen` (not `cr_update_state`) behind a
  // ConfirmModal — mirroring the Dashboard contract (PRD §9.4/§12.13).
  const REOPEN_OPTION = "REOPEN";
  const CR_NEXT: Record<string, string[]> = {
    "PENDING SUBMISSION": ["PENDING APPROVAL", "POSTPONED", "CANCELED"],
    "PENDING APPROVAL": ["APPROVED", "POSTPONED", "CANCELED"],
    "APPROVED": ["POSTPONED", "CANCELED"],
    "IN-PROGRESS": ["FINISHED", "POSTPONED", "CANCELED"],
    "FINISHED": [],
    "POSTPONED": [REOPEN_OPTION],
    "CANCELED": [REOPEN_OPTION],
  };
  function legalCrOptionsFor(crState: string): string[] {
    const options = [crState, ...(CR_NEXT[crState] ?? [])].filter((value) => value && value.trim().length > 0);
    return options.length > 0 ? Array.from(new Set(options)) : [crState || "PENDING SUBMISSION"];
  }
  // Pending REOPEN confirm — armed by saveCrState, gated by ConfirmModal.
  let pendingReopen: { path: string; name: string } | null = $state(null);
  let crStateEdit: string = $state("");
  type CrStateSave = "idle" | "saving" | "success" | "error";
  let crStateSaveState: CrStateSave = $state("idle");
  let crStateSaveError: string = $state("");

  // ── Non-CR state edit state (PRD §12 / Piece A) ──
  const NON_CR_STATE_OPTIONS = ["PLANNING", "IN_PROGRESS", "DONE"];
  let nonCrStateEdit: string = $state("PLANNING");
  type NonCrStateSave = "idle" | "saving" | "success" | "error";
  let nonCrStateSaveState: NonCrStateSave = $state("idle");
  let nonCrStateSaveError: string = $state("");
  function nonCrStateLabel(value: string | null | undefined): string {
    if (value === "IN_PROGRESS") return "In Progress";
    if (value === "DONE") return "Done";
    return "Planning";
  }

  // ── Notes state ──
  // Notes editing now lives in NotesEditor.svelte (autosave + toolbar + preview,
  // PRD §12.12). `notes` holds the last loaded/saved value passed into it.

  // ── Metadata edit state ──
  let metaNameEdit: string = $state("");
  let metaStartEdit: string = $state("");
  let metaEndEdit: string = $state("");
  type MetaSave = "idle" | "saving" | "success" | "error";
  let metaSaveState: MetaSave = $state("idle");
  let metaSaveError: string = $state("");

  // ── Drone state edit state ──
  const DRONE_STATE_OPTIONS = ["UAT", "PENDING APPROVAL", "APPROVED", "IN-PROGRESS", "FINISHED", "POSTPONED", "CANCELED"];
  const DRONE_NEXT: Record<string, string[]> = {
    "UAT": ["PENDING APPROVAL", "CANCELED"],
    "PENDING APPROVAL": ["APPROVED", "CANCELED"],
    "APPROVED": ["CANCELED"],
    "IN-PROGRESS": ["FINISHED", "CANCELED"],
    "FINISHED": [],
    "CANCELED": [],
  };
  function legalDroneOptionsFor(droneState: string): string[] {
    const options = [droneState, ...(DRONE_NEXT[droneState] ?? [])].filter((value) => value && value.trim().length > 0);
    return options.length > 0 ? Array.from(new Set(options)) : [droneState || "UAT"];
  }
  // ── Sub-project master-detail (Fase 1 §3.4) ──
  let selectedSubprojectRow: string | null = $state(null);
  let droneLinkEdit: string = $state("");
  let droneLinkBusy: boolean = $state(false);
  let droneLinkError: string = $state("");
  let droneLinkEditing: boolean = $state(false);
  let droneLinkCopied: boolean = $state(false);
  // Drone state busy/error keyed by sub-project NAME (not drone ticket index) — Fase 1 §3.4.
  let droneStateBusyName: string | null = $state(null);
  let droneStateErrorName: Record<string, string> = $state({});

  let selectedSubprojectRowDetail = $derived.by(() => {
    if (!detail || !selectedSubprojectRow) return null;
    const index = detail.drone_tickets.findIndex((t) => (t.subfolder_name ?? "") === selectedSubprojectRow);
    return index >= 0 ? { ticket: detail.drone_tickets[index], index } : { ticket: null, index: -1 };
  });

  // ── Sub-project create state (prototype Add Sub Project action) ──
  let newSubprojectName: string = $state("");
  let droneBusy: boolean = $state(false);
  let droneFeedback: string = $state("");
  let droneFeedbackKind: "idle" | "success" | "error" = $state("idle");

  let yearFilter: string = $state("all");
  let searchText: string = $state("");
  let yearOptions: string[] = $state(["2026", "2025", "2024"]);

  let filtered: ProjectRow[] = $derived.by(() => {
    let result = yearFilter === "all" ? projects : projects.filter((p) => p.project_path.includes(yearFilter));
    const q = searchText.trim().toLowerCase();
    if (q) {
      result = result.filter((p) =>
        p.project_name.toLowerCase().includes(q) ||
        p.cr_number.toLowerCase().includes(q) ||
        p.project_state.toLowerCase().includes(q) ||
        p.project_path.toLowerCase().includes(q),
      );
    }
    return result;
  });

  function pad2(value: number): string {
    return String(value).padStart(2, "0");
  }

  function toDatetimeLocal(value?: string | null): string {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}T${pad2(date.getHours())}:${pad2(date.getMinutes())}`;
  }

  function fromDatetimeLocal(value: string): string | null {
    if (!value) return null;
    const [datePart, timePart] = value.split("T");
    if (!datePart || !timePart) return null;
    const [year, month, day] = datePart.split("-").map(Number);
    const [hour, minute] = timePart.split(":").map(Number);
    const date = new Date(year, month - 1, day, hour, minute, 0, 0);
    if (Number.isNaN(date.getTime())) return null;
    const offsetMinutes = -date.getTimezoneOffset();
    const sign = offsetMinutes >= 0 ? "+" : "-";
    const absOffset = Math.abs(offsetMinutes);
    return `${datePart}T${timePart}:00${sign}${pad2(Math.floor(absOffset / 60))}:${pad2(absOffset % 60)}`;
  }

  function syncMetadataDrafts(nextDetail: ProjectDetail) {
    metaNameEdit = nextDetail.project_name || "";
    metaStartEdit = toDatetimeLocal(nextDetail.start_datetime);
    metaEndEdit = toDatetimeLocal(nextDetail.end_datetime);
  }

  function metadataUnchanged(current: ProjectDetail): boolean {
    return metaNameEdit === current.project_name
      && metaStartEdit === toDatetimeLocal(current.start_datetime)
      && metaEndEdit === toDatetimeLocal(current.end_datetime);
  }

  async function loadProjects() {
    listState = "loading";
    if (!isPywebviewReady() && !(await waitForPywebviewReady())) {
      errorCode = BridgeErrorCode.BRIDGE_UNAVAILABLE;
      errorMessage = "pywebview bridge unavailable.";
      listState = "error";
      return;
    }
    const resp = await callBridge<ProjectRow[]>("project_list", yearFilter === "all" ? undefined : yearFilter);
    if (!resp.ok) {
      errorCode = resp.error.code;
      errorMessage = resp.error.message;
      listState = "error";
      return;
    }
    projects = resp.data ?? [];
    listState = "loaded";
  }

  async function selectProject(path: string) {
    await rteEditorFlush?.();
    selectedPath = path;
    detailState = "loading";
    stopApprovalStatusPoll();
    detail = null; isNonCr = false; selectedSubproject = "all"; drones = []; files = []; notes = "";
    crDocsFiles = []; selectedCrDocPath = ""; crDocContent = null; crDocContentPath = ""; crDocDocPayload = null; crDocsLoading = false; crDocsError = "";
    topActionState = "idle"; topActionError = ""; topDeletePending = false;
    crLinkEdit = ""; crLinkSaveState = "idle"; crLinkSaveError = "";
    crStateEdit = ""; crStateSaveState = "idle"; crStateSaveError = "";
    nonCrStateEdit = "PLANNING"; nonCrStateSaveState = "idle"; nonCrStateSaveError = "";
    selectedSubprojectRow = null;
    droneLinkEdit = "";
    droneLinkBusy = false;
    droneLinkError = "";
    droneLinkEditing = false;
    droneLinkCopied = false;
    droneStateBusyName = null;
    droneStateErrorName = {};
    newSubprojectName = ""; droneBusy = false; droneFeedback = ""; droneFeedbackKind = "idle";
    errorCode = ""; errorMessage = "";

    try {
      if (!isPywebviewReady() && !(await waitForPywebviewReady())) {
        errorCode = BridgeErrorCode.BRIDGE_UNAVAILABLE;
        errorMessage = "pywebview bridge unavailable.";
        detailState = "error";
        return;
      }

      const [dResp, spResp, flResp, ntResp] = await Promise.all([
        callBridge<ProjectDetail>("project_get", path),
        callBridge<string[]>("drone_list", path),
        callBridge<FileRow[]>("file_list", path),
        callBridge<string>("notes_get", path),
      ]);

      if (!dResp.ok) {
        errorCode = dResp.error.code;
        errorMessage = dResp.error.message;
        detailState = "error";
        return;
      }

      detail = dResp.data ?? null;
      isNonCr = detail ? detail.project_type === "NON_CR" : false;
      drones = spResp.ok ? (spResp.data ?? []) : [];
      files = flResp.ok ? (flResp.data ?? []) : [];
      notes = ntResp.ok ? (ntResp.data ?? "") : "";
      showNotesEditor = false;

      if (detail) {
        crLinkEdit = detail.cr_link || "";
        crLinkEditing = !detail.cr_link;
        crLinkCopied = false;
        crStateEdit = detail.cr_state || "";
        nonCrStateEdit = detail.non_cr_state ?? "PLANNING";
        syncMetadataDrafts(detail);
      }

      // Show core project data immediately. CR Docs load independently below.
      detailState = "loaded";

      if (detail && !isNonCr) {
        void loadCrDocs();
        void loadApprovalStatus();
      }
    } catch (err) {
      errorCode = "PROJECT_DETAIL_LOAD_FAILED";
      errorMessage = err instanceof Error ? err.message : String(err);
      detailState = "error";
    }
  }

  async function saveCrLink() {
    if (!selectedPath) return;
    crLinkSaveState = "saving";
    crLinkSaveError = "";

    if (!isPywebviewReady()) {
      crLinkSaveError = "pywebview bridge unavailable.";
      crLinkSaveState = "error";
      return;
    }

    const resp = await callBridge("cr_update_link", selectedPath, crLinkEdit);
    if (!resp.ok) {
      crLinkSaveError = resp.error.message;
      crLinkSaveState = "error";
      return;
    }

    // Refresh detail to show updated state
    const oldLink = detail?.cr_link ?? "";
    if (detail) detail.cr_link = crLinkEdit;
    crLinkSaveState = "success";
    addToast("CR link saved", "success", 5000, { label: "Undo", fn: () => { void callBridge("cr_update_link", selectedPath, oldLink); } });
    setTimeout(() => { if (crLinkSaveState === "success") crLinkSaveState = "idle"; }, 2500);
  }

  async function saveCrLinkFromInput() {
    if (!detail) return;
    if (crLinkEdit === detail.cr_link) return;
    await saveCrLink();
    if (crLinkSaveState === "success" && crLinkEdit.trim()) {
      crLinkEditing = false;
    }
  }

  async function copyCrLink() {
    if (!detail?.cr_link) return;
    try {
      await navigator.clipboard.writeText(detail.cr_link);
      crLinkCopied = true;
      setTimeout(() => { crLinkCopied = false; }, 2000);
    } catch {
      // ignore
    }
  }

  function openCrLink() {
    if (!detail?.cr_link) return;
    window.open(detail.cr_link, "_blank", "noopener,noreferrer");
  }

  function editCrLink() {
    if (!detail) return;
    crLinkEdit = detail.cr_link || "";
    crLinkEditing = true;
  }

  async function saveCrState() {
    if (!selectedPath || !isPywebviewReady()) {
      crStateSaveError = "pywebview bridge unavailable.";
      crStateSaveState = "error";
      return;
    }
    // REOPEN is an action, not a CR state (PRD §9.1). Route it to folder_reopen
    // behind a confirm; never call cr_update_state with REOPEN (the backend
    // validator would reject it).
    if (crStateEdit === REOPEN_OPTION) {
      pendingReopen = { path: selectedPath, name: detail?.project_name ?? selectedPath };
      return;
    }
    crStateSaveState = "saving";
    crStateSaveError = "";
    const resp = await callBridge("cr_update_state", selectedPath, crStateEdit);
    if (!resp.ok) {
      crStateSaveError = resp.error.message;
      crStateSaveState = "error";
      return;
    }
    if (resp.data && (resp.data as any).project_path) {
      selectedPath = (resp.data as any).project_path;
    }
    const oldState = detail?.cr_state ?? "";
    if (detail) detail.cr_state = crStateEdit;
    crStateSaveState = "success";
    addToast("CR state saved", "success", 5000, { label: "Undo", fn: () => { void callBridge("cr_update_state", selectedPath, oldState); } });
    setTimeout(() => { if (crStateSaveState === "success") crStateSaveState = "idle"; }, 2500);
  }

  async function onCrStateChange(next: string) {
    crStateEdit = next;
    await saveCrState();
  }

  /** Reopen moves the folder POSTPONED/CANCELED → UAT_PREPARE and CR → PENDING SUBMISSION. */
  async function reopenProject(path: string) {
    crStateSaveState = "saving";
    crStateSaveError = "";
    const r = await callBridge("folder_reopen", path);
    crStateSaveState = "idle";
    if (!r.ok) {
      crStateSaveError = r.error.message;
      return;
    }
    if (r.data && (r.data as any).project_path) {
      selectedPath = (r.data as any).project_path;
    }
    await refreshDetail();
  }

  async function confirmReopen() {
    const ps = pendingReopen;
    pendingReopen = null;
    if (!ps) return;
    await reopenProject(ps.path);
  }

  function cancelReopen() {
    pendingReopen = null;
    // Reset the dropdown back to the current detail state so the UI stays honest.
    if (detail) crStateEdit = detail.cr_state;
  }

  async function onNonCrStateChange(next: string) {
    if (!selectedPath || !isPywebviewReady()) {
      nonCrStateSaveError = "pywebview bridge unavailable.";
      nonCrStateSaveState = "error";
      return;
    }
    nonCrStateEdit = next;
    nonCrStateSaveState = "saving";
    nonCrStateSaveError = "";
    const resp = await callBridge("set_non_cr_state", selectedPath, next);
    if (!resp.ok) {
      nonCrStateSaveError = resp.error.message;
      nonCrStateSaveState = "error";
      return;
    }
    if (resp.data && (resp.data as any).project_path) {
      selectedPath = (resp.data as any).project_path;
    }
    nonCrStateSaveState = "success";
    addToast("Non-CR state saved", "success", 2000);
    setTimeout(() => { if (nonCrStateSaveState === "success") nonCrStateSaveState = "idle"; }, 2500);
    await refreshDetail();
  }

  async function saveMetadataIfChanged() {
    if (!detail) return;
    if (metadataUnchanged(detail)) return;
    await saveMetadata();
  }

  async function saveMetadata() {
    if (!selectedPath || !isPywebviewReady()) {
      metaSaveError = "pywebview bridge unavailable.";
      metaSaveState = "error";
      return;
    }
    metaSaveState = "saving";
    metaSaveError = "";
    const resp = await callBridge("project_update", selectedPath, {
      project_name: metaNameEdit,
      start_datetime: fromDatetimeLocal(metaStartEdit),
      end_datetime: fromDatetimeLocal(metaEndEdit),
    });
    if (!resp.ok) {
      metaSaveError = resp.error.message;
      metaSaveState = "error";
      return;
    }
    metaSaveState = "success";
    addToast("Project saved", "success", 2000);
    setTimeout(() => { if (metaSaveState === "success") metaSaveState = "idle"; }, 2500);
    await refreshDetail();
  }

  function onSelectSubprojectRow(name: string) {
    selectedSubprojectRow = selectedSubprojectRow === name ? null : name;
    droneLinkEdit = selectedSubprojectRowDetail?.ticket?.drone_link ?? "";
    droneLinkError = "";
    droneLinkEditing = false;
    droneLinkCopied = false;
  }

  function openSubprojectFolder(name: string) {
    if (!detail || !isPywebviewReady()) return;
    const sep = detail.project_path.includes("\\") ? "\\" : "/";
    const base = detail.project_path.endsWith(sep) ? detail.project_path : detail.project_path + sep;
    void callBridge("folder_open", base + name);
  }

  async function onChangeSubprojectDroneState(name: string, nextState: string) {
    if (!detail || !selectedPath || !isPywebviewReady()) return;
    const index = detail.drone_tickets.findIndex((t) => (t.subfolder_name ?? "") === name);
    if (index < 0) return;
    if (nextState === detail.drone_tickets[index]?.drone_state) return;
    droneStateBusyName = name;
    droneStateErrorName = { ...droneStateErrorName, [name]: "" };
    const resp = await callBridge("drone_update", selectedPath, index, { drone_state: nextState });
    droneStateBusyName = null;
    if (!resp.ok) {
      droneStateErrorName = { ...droneStateErrorName, [name]: resp.error.message };
      return;
    }
    if (resp.data && (resp.data as any).project_path) {
      selectedPath = (resp.data as any).project_path;
    }
    droneStateErrorName = { ...droneStateErrorName, [name]: "" };
    await refreshDetail();
  }

  async function addSubproject() {
    const name = newSubprojectName.trim();
    droneFeedback = "";
    droneFeedbackKind = "idle";
    if (!selectedPath || !name) return;
    if (!isPywebviewReady()) {
      droneFeedback = "pywebview bridge unavailable.";
      droneFeedbackKind = "error";
      return;
    }
    droneBusy = true;
    const resp = await callBridge("drone_create", selectedPath, name);
    droneBusy = false;
    if (!resp.ok) {
      droneFeedback = resp.error.message;
      droneFeedbackKind = "error";
      return;
    }
    newSubprojectName = "";
    selectedSubprojectRow = name;
    droneLinkEdit = "";
    droneFeedback = `Created ${name}.`;
    droneFeedbackKind = "success";
    await reloadSubprojects();
  }

  async function saveDroneLinkFromTable(name: string, link: string) {
    if (!detail || !selectedPath) return;
    const next = link.trim();
    const index = detail.drone_tickets.findIndex((t) => (t.subfolder_name ?? "") === name);
    const oldLink = index >= 0 ? detail.drone_tickets[index].drone_link : "";
    droneLinkBusy = true; droneLinkError = "";
    let resp: any;
    if (index >= 0) {
      resp = await callBridge("drone_update", selectedPath, index, { drone_link: next });
    } else {
      resp = await callBridge("drone_add", selectedPath, { drone_link: next, subfolder_name: name, owner: "" });
    }
    droneLinkBusy = false;
    if (!resp.ok) { droneLinkError = resp.error.message; return; }
    await refreshDetail();
    addToast("Drone link saved", "success", 5000,
      index >= 0 ? { label: "Undo", fn: () => { void callBridge("drone_update", selectedPath, index, { drone_link: oldLink }); } } : undefined);
  }

  async function saveDroneLinkFromPanel() {
    if (!detail || !selectedPath || !selectedSubprojectRowDetail) return;
    if (selectedSubprojectRowDetail.index < 0 || !selectedSubprojectRowDetail.ticket) return;
    const next = droneLinkEdit.trim();
    const current = selectedSubprojectRowDetail.ticket.drone_link ?? "";
    if (next === current) return;
    const oldLink = current;
    droneLinkBusy = true; droneLinkError = "";
    const resp = await callBridge("drone_update", selectedPath, selectedSubprojectRowDetail.index, { drone_link: next });
    droneLinkBusy = false;
    if (!resp.ok) { droneLinkError = resp.error.message; return; }
    await refreshDetail();
    addToast("Drone link saved", "success", 5000, { label: "Undo", fn: () => { void callBridge("drone_update", selectedPath, selectedSubprojectRowDetail.index, { drone_link: oldLink }); } });
  }

  async function addDroneForSelectedRow() {
    if (!detail || !selectedPath || !selectedSubprojectRow) return;
    const next = droneLinkEdit.trim();
    if (!next) return;
    droneLinkBusy = true; droneLinkError = "";
    const resp = await callBridge("drone_add", selectedPath, { drone_link: next, subfolder_name: selectedSubprojectRow, owner: "" });
    droneLinkBusy = false;
    if (!resp.ok) { droneLinkError = resp.error.message; return; }
    await refreshDetail();
    addToast("Drone ticket added", "success", 2000);
  }

  function editDroneLink() {
    if (!selectedSubprojectRowDetail?.ticket) return;
    droneLinkEdit = selectedSubprojectRowDetail.ticket.drone_link || "";
    droneLinkEditing = true;
  }

  async function copyDroneLink() {
    if (!selectedSubprojectRowDetail?.ticket?.drone_link) return;
    try {
      await navigator.clipboard.writeText(selectedSubprojectRowDetail.ticket.drone_link);
      droneLinkCopied = true;
      setTimeout(() => { droneLinkCopied = false; }, 2000);
    } catch { /* ignore */ }
  }

  async function saveDroneLinkFromInput() {
    if (!detail || !selectedPath || !selectedSubprojectRowDetail) return;
    if (selectedSubprojectRowDetail.index < 0 || !selectedSubprojectRowDetail.ticket) {
      // No existing ticket — add
      await addDroneForSelectedRow();
      return;
    }
    const next = droneLinkEdit.trim();
    const current = selectedSubprojectRowDetail.ticket.drone_link ?? "";
    if (next === current) { droneLinkEditing = false; return; }
    droneLinkBusy = true; droneLinkError = "";
    const resp = await callBridge("drone_update", selectedPath, selectedSubprojectRowDetail.index, { drone_link: next });
    droneLinkBusy = false;
    if (!resp.ok) { droneLinkError = resp.error.message; return; }
    droneLinkEditing = false;
    await refreshDetail();
  }

  async function refreshDetail() {
    if (!selectedPath) return;
    const [dResp, ntResp] = await Promise.all([
      callBridge<ProjectDetail>("project_get", selectedPath),
      callBridge<string>("notes_get", selectedPath),
    ]);
    if (dResp.ok && dResp.data) { detail = dResp.data; syncMetadataDrafts(dResp.data); }
    if (ntResp.ok) { notes = ntResp.data ?? ""; }
    if (detail && !isNonCr) await loadCrDocs();
  }

  // ── CR Docs helpers (Piece B) ──

  /** Mirror backend _detect_rte_format so the dropdown label matches behavior. */
  function rteFormatForName(name: string): RteFile["format"] {
    const suffix = name.slice(name.lastIndexOf(".") + 1).toLowerCase();
    if (suffix === "docx") return "docx";
    if (suffix === "md") return "markdown";
    if (suffix === "msg") return "msg";
    if (suffix === "html" || suffix === "htm") return "html";
    return "text";
  }

  /** Build the CR Docs file list for the current CR project and select notes.md. */
  async function loadCrDocs() {
    if (!detail) return;
    crDocsLoading = true;
    crDocsError = "";
    try {
      const projectPath = detail.project_path;
      const isLocked = detail.project_state === "IMPLEMENTED";
      // DOCX docs are editable through the pipeline (D-0012); only the
      // IMPLEMENTED folder state locks them (like every other doc).
      const list: RteFile[] = [
        { name: "notes.md", path: `${projectPath.replace(/\/$/, "")}/notes.md`, format: "markdown", editable: !isLocked, capability: isLocked ? "read_only" : "editable", saveStrategy: isLocked ? "none" : "markdown", isOpenable: false },
        { name: "uat-signoff.docx", path: `${projectPath.replace(/\/$/, "")}/_cr-docs/uat-signoff.docx`, format: "docx", editable: !isLocked, capability: isLocked ? "read_only" : "editable", saveStrategy: isLocked ? "none" : "docx_pipeline", isOpenable: false },
        { name: "prod-lv.docx", path: `${projectPath.replace(/\/$/, "")}/_cr-docs/prod-lv.docx`, format: "docx", editable: !isLocked, capability: isLocked ? "read_only" : "editable", saveStrategy: isLocked ? "none" : "docx_pipeline", isOpenable: false },
      ];
      // Append any .msg files already present in _cr-docs/ (created by Piece C).
      const msgResp = await callBridge<FileRow[]>("file_list", `${projectPath.replace(/\/$/, "")}/_cr-docs`);
      if (msgResp.ok && msgResp.data) {
        for (const f of msgResp.data) {
          if (f.name.toLowerCase().endsWith(".msg")) {
            list.push({ name: f.name, path: f.path, format: "msg", editable: false, capability: "unsupported", saveStrategy: "none", isOpenable: true });
          }
        }
      }
      crDocsFiles = list;
      // Default to notes.md; keep current selection if still valid.
      const stillValid = list.some((f) => f.path === selectedCrDocPath);
      if (!stillValid) selectedCrDocPath = list[0]?.path ?? "";
      await selectCrDoc(selectedCrDocPath);
    } catch (err) {
      crDocsError = err instanceof Error ? err.message : String(err);
    } finally {
      crDocsLoading = false;
    }
  }

  function setInteractionLock(source: string, locked: boolean) {
    if (typeof window === "undefined") return;
    window.dispatchEvent(new CustomEvent("app:interaction-lock", { detail: { source, locked } }));
  }

  /** Load the selected CR doc content (or prepare the .msg open-external panel). */
  async function selectCrDoc(path: string) {
    crDocsFlushing = true;
    setInteractionLock("project-details-rte", true);
    try {
      const flushed = await rteEditorFlush?.();
      if (flushed === false) { crDocsError = "Save failed"; return; }
      selectedCrDocPath = path;
      crDocContent = null;
      crDocContentPath = "";
      crDocDocPayload = null;
      const file = crDocsFiles.find((f) => f.path === path);
      if (!file) return;
      if (file.format === "msg") return; // rendered as open-external panel
      crDocsLoading = true; crDocsError = "";
      if (file.format === "docx") {
        // DOCX pipeline (D-0012): open the JSON source (or migration HTML).
        const resp = await rteDocumentOpen(path);
        if (!resp.ok || !resp.data) { crDocsError = resp.ok ? "Empty document payload" : resp.error.message; return; }
        if (selectedCrDocPath !== path) return;
        crDocDocPayload = resp.data;
        crDocContent = {
          content: resp.data.content_html ?? "",
          format: "docx",
          editable: resp.data.editable,
          capability: resp.data.capability,
          message: resp.data.message,
          saveStrategy: resp.data.saveStrategy,
          supportedEditorFeatures: resp.data.supportedEditorFeatures,
        };
        crDocContentPath = path;
        return;
      }
      const resp = await getRteFile(path);
      if (!resp.ok) { crDocsError = resp.error.message; return; }
      // A3 fix: only mount the editor after content for the selected path is ready.
      if (selectedCrDocPath !== path) return;
      crDocContent = resp.data;
      crDocContentPath = path;
    } catch (err) {
      crDocsError = err instanceof Error ? err.message : String(err);
    } finally {
      crDocsLoading = false;
      crDocsFlushing = false;
      setInteractionLock("project-details-rte", false);
    }
  }

  /** Open a .msg (or any external) file via the OS default app. */
  async function openCrDocExternal(path: string) {
    const resp = await callBridge("file_open", path);
    if (!resp.ok) addToast(`Could not open file: ${resp.error.message}`, "error");
  }

  /** The currently selected CR Docs file (or null). */
  const selectedCrDoc = $derived(crDocsFiles.find((f) => f.path === selectedCrDocPath) ?? null);
  const crDocReady = $derived(crDocContent !== null && crDocContentPath === selectedCrDocPath);

  async function openProjectFolder() {
    if (!selectedPath || !isPywebviewReady()) {
      topActionError = "pywebview bridge unavailable.";
      topActionState = "error";
      return;
    }
    topActionState = "saving";
    topActionError = "";
    const resp = await callBridge("project_open_folder", selectedPath);
    if (!resp.ok) {
      topActionError = resp.error.message;
      topActionState = "error";
      return;
    }
    topActionState = "success";
    setTimeout(() => { if (topActionState === "success") topActionState = "idle"; }, 2500);
  }

  function requestTopDelete() {
    topActionError = "";
    topDeletePending = true;
  }

  function cancelTopDelete() {
    topDeletePending = false;
  }

  async function confirmTopDelete() {
    if (!selectedPath || !isPywebviewReady()) {
      topActionError = "pywebview bridge unavailable.";
      topActionState = "error";
      topDeletePending = false;
      return;
    }
    topDeletePending = false;
    topActionState = "saving";
    topActionError = "";
    const resp = await callBridge("project_delete", selectedPath);
    if (!resp.ok) {
      topActionError = resp.error.message;
      topActionState = "error";
      return;
    }
    await onProjectDeleted();
    topActionState = "success";
  }

  async function init() {
    if (isPywebviewReady() || await waitForPywebviewReady()) {
      const yr = await callBridge<string[]>("year_list");
      if (yr.ok && yr.data && yr.data.length > 0) yearOptions = yr.data;
    }
    await loadProjects();
    if (startNew) {
      mode = "new";
    } else if (initialPath) {
      await selectProject(initialPath);
    }
  }

  onMount(init);
  onDestroy(() => stopApprovalStatusPoll());

  export function refresh() { loadProjects(); }

  // After project_create succeeds, leave NEW_PROJECT mode, reload the list, and
  // open the freshly created project in SHOW_EDIT (PRD §12.4 navigation).
  async function onProjectCreated(path: string, appcode: string) {
    void appcode;
    mode = "browse";
    await loadProjects();
    if (path) await selectProject(path);
  }

  // After a successful delete the project folder is gone. Clear the selection
  // and reload the list so the dashboard reflects the change (Req 5.6).
  async function onProjectDeleted() {
    selectedPath = "";
    detail = null;
    drones = [];
    files = [];
    notes = "";
    showNotesEditor = false;
    detailState = "idle";
    await loadProjects();
  }

  // After a successful drone delete, reload the drone list (Req 5.7).
  async function reloadSubprojects() {
    if (!selectedPath || !isPywebviewReady()) return;
    const resp = await callBridge<string[]>("drone_list", selectedPath);
    if (resp.ok) drones = resp.data ?? [];
  }

  // After a successful file create/rename/delete, reload the file list so the
  // Files area reflects the change (Req 6.10 — honest post-action state).
  async function reloadFiles() {
    if (!selectedPath || !isPywebviewReady()) return;
    const resp = await callBridge<FileRow[]>("file_list", selectedPath);
    if (resp.ok) files = resp.data ?? [];
  }

</script>

<section class="screen active" id="screen-details">
  <div class="page-header">
    <div class="page-header-left">
      <span class="page-header-icon"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg></span>
      <h2 class="page-header-title">Project Details</h2>
    </div>
    <div class="page-header-actions">
      {#if onNavigateDashboard}
        <button type="button" class="pd-command-btn" onclick={() => onNavigateDashboard?.()} title="Back to Dashboard">
          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:inline;vertical-align:middle;margin-right:4px;"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 5 12"></polyline></svg>
          Back
        </button>
      {/if}
      <label class="pd-command-field pd-command-project" for="pd-project-select">
        <span>Project</span>
        <select id="pd-project-select" class="pd-control" value={selectedPath} onchange={(e) => selectProject((e.target as HTMLSelectElement).value)} disabled={filtered.length === 0 || mode === "new"}>
          <option value="">Select project…</option>
          {#each filtered as p}
            <option value={p.project_path}>{p.project_name}</option>
          {/each}
        </select>
      </label>
      <label class="pd-command-field pd-command-project" for="pd-drone-select">
        <span>Drone</span>
        <select id="pd-drone-select" class="pd-control" bind:value={selectedSubproject} disabled={!selectedPath || drones.length === 0 || mode === "new"}>
          <option value="all">All Drones</option>
          {#each drones as sp}
            <option value={sp}>{sp}</option>
          {/each}
        </select>
      </label>
      <div class="pd-command-spacer"></div>
      <button class="pd-command-btn" type="button" onclick={openProjectFolder} disabled={!selectedPath || topActionState === "saving"}>Open</button>
      <button class="pd-command-btn pd-command-danger" type="button" onclick={requestTopDelete} disabled={!selectedPath || topActionState === "saving"}>Delete</button>
    </div>
  </div>
  {#if topActionState === "error"}
    <p class="cr-link-feedback cr-link-err">✗ {topActionError}</p>
  {:else if topActionState === "success"}
    <p class="cr-link-feedback cr-link-ok">✓ Done</p>
  {/if}
  <div class="pd-body">
    <div class="pd-detail-panel">
      {#if mode === "new"}
        <NewProjectForm
          yearOptions={yearOptions}
          defaultYear={yearFilter !== "all" ? yearFilter : (yearOptions[0] ?? "")}
          onCancel={() => (mode = "browse")}
          onCreated={onProjectCreated}
        />
      {:else if listState === "loading"}
        <div class="dashboard-banner banner-loading"><span class="banner-icon">◌</span><span>Loading projects…</span></div>
      {:else if listState === "error"}
        <div class="dashboard-banner banner-error">
          <span class="banner-icon"><svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="pd-icon"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg></span>
          <div><p class="banner-title">Failed</p><p class="banner-detail">{errorCode}: {errorMessage}</p></div>
        </div>
      {:else if !selectedPath}
        <div class="table-empty"><p class="empty-title">Select a project</p><p class="empty-sub">Use the Project Command Center selector to view details.</p></div>
      {:else if detailState === "loading"}
        <div class="dashboard-banner banner-loading"><span class="banner-icon">◌</span><span>Loading details…</span></div>
      {:else if detailState === "error"}
        <div class="dashboard-banner banner-error">
          <span class="banner-icon"><svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="pd-icon"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg></span>
          <div><p class="banner-title">Detail load failed</p><p class="banner-detail">{errorCode}: {errorMessage}</p></div>
        </div>
      {:else if detail}
        <div class="split">
          <div class="pane">
            <div class="pd-section">
              <h4 class="pd-section-title">Project Identity</h4>
              <div class="pd-meta-edit">
                <label class="pd-meta-label" for="meta-name">Project Name</label>
                <input id="meta-name" class="cr-link-input" bind:value={metaNameEdit} onblur={saveMetadataIfChanged} disabled={metaSaveState === "saving"} />
                <div class="pd-meta-datetime-row">
                  {#if isNonCr}
                    <label class="pd-meta-field" for="meta-non-cr-state">
                      <span class="pd-meta-label">Non-CR state</span>
                      <select id="meta-non-cr-state" class="cr-state-select" value={nonCrStateEdit} onchange={(e) => onNonCrStateChange((e.currentTarget as HTMLSelectElement).value)} disabled={nonCrStateSaveState === "saving"}>
                        {#each NON_CR_STATE_OPTIONS as opt}
                          <option value={opt}>{nonCrStateLabel(opt)}</option>
                        {/each}
                      </select>
                      {#if nonCrStateSaveState === "saving"}
                        <span class="cr-link-feedback">
                          <svg class="pd-spinner" xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="2" x2="12" y2="6"></line><line x1="12" y1="18" x2="12" y2="22"></line><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line><line x1="2" y1="12" x2="6" y2="12"></line><line x1="18" y1="12" x2="22" y2="12"></line><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line></svg>
                          Saving…
                        </span>
                      {:else if nonCrStateSaveState === "success"}
                        <span class="cr-link-feedback cr-link-ok">✓ Saved</span>
                      {:else if nonCrStateSaveState === "error"}
                        <span class="cr-link-feedback cr-link-err">✗ {nonCrStateSaveError}</span>
                      {/if}
                    </label>
                  {:else}
                  <div class="pd-meta-field">
                    <span class="pd-meta-label">CR Number</span>
                    {#if crLinkEditing}
                      <input
                        id="meta-cr-link"
                        class="cr-link-input"
                        type="url"
                        placeholder="Paste CR link…"
                        bind:value={crLinkEdit}
                        onblur={saveCrLinkFromInput}
                        disabled={crLinkSaveState === "saving"}
                      />
                      {#if crLinkSaveState === "error"}
                        <span class="cr-link-feedback cr-link-err">✗ {crLinkSaveError}</span>
                      {/if}
                    {:else}
                      <div class="pd-cr-link-display">
                        <span class="pd-cr-link-number">{detail.cr_number || detail.cr_link || "—"}</span>
                        {#if detail.cr_link}
                          <button class="pd-icon-btn" type="button" onclick={copyCrLink} aria-label="Copy CR link">
                            <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" class="pd-icon"><title>Copy CR link</title><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path><rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect></svg>
                            {#if crLinkCopied}<span style="font-size:9.5px;color:var(--tag-green-ink);margin-left:2px;">✓</span>{/if}
                          </button>
                          <button class="pd-icon-btn" type="button" onclick={openCrLink} aria-label="Open CR link in browser">
                            <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" class="pd-icon"><title>Open CR link in browser</title><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
                          </button>
                        {/if}
                        <button class="pd-icon-btn" type="button" onclick={editCrLink} aria-label="Edit CR link">
                          <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" class="pd-icon"><title>Edit CR link</title><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 1 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>
                        </button>
                      </div>
                    {/if}
                  </div>
                  <label class="pd-meta-field" for="meta-cr-state">
                    <span class="pd-meta-label">CR State</span>
                    <select id="meta-cr-state" class="cr-state-select" value={crStateEdit} onchange={(e) => onCrStateChange((e.currentTarget as HTMLSelectElement).value)} disabled={crStateSaveState === "saving"}>
                      {#each legalCrOptionsFor(detail.cr_state) as opt}
                        <option value={opt} disabled={opt === "IN-PROGRESS"}>{opt}</option>
                      {/each}
                    </select>
                    {#if crStateSaveState === "saving"}
                      <span class="cr-link-feedback">
                        <svg class="pd-spinner" xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="2" x2="12" y2="6"></line><line x1="12" y1="18" x2="12" y2="22"></line><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line><line x1="2" y1="12" x2="6" y2="12"></line><line x1="18" y1="12" x2="22" y2="12"></line><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line></svg>
                        Saving…
                      </span>
                    {:else if crStateSaveState === "success"}
                      <span class="cr-link-feedback cr-link-ok">✓ Saved</span>
                    {:else if crStateSaveState === "error"}
                      <span class="cr-link-feedback cr-link-err">✗ {crStateSaveError}</span>
                    {/if}
                  </label>
                  {/if}
                </div>
              </div>
            </div>

            <div class="pd-section">
              <h4 class="pd-section-title">Schedule</h4>
              <div class="pd-meta-edit">
                <div class="pd-meta-datetime-row">
                  <label class="pd-meta-field" for="meta-start">
                    <span class="pd-meta-label">Start datetime</span>
                    <input id="meta-start" class="cr-link-input" type="datetime-local" bind:value={metaStartEdit} onblur={saveMetadataIfChanged} disabled={metaSaveState === "saving"} />
                  </label>
                  <label class="pd-meta-field" for="meta-end">
                    <span class="pd-meta-label">End datetime</span>
                    <input id="meta-end" class="cr-link-input" type="datetime-local" bind:value={metaEndEdit} onblur={saveMetadataIfChanged} disabled={metaSaveState === "saving"} />
                  </label>
                </div>
                <div class="pd-notes-actions">
                  <button class="cr-link-save-btn" onclick={saveMetadata} disabled={metaSaveState === "saving" || metadataUnchanged(detail)}>{#if metaSaveState === "saving"}⏳ Saving…{:else}Save identity + schedule{/if}</button>
                  {#if metaSaveState === "success"}
                    <span class="cr-link-feedback cr-link-ok">✓ Saved</span>
                  {:else if metaSaveState === "error"}
                    <span class="cr-link-feedback cr-link-err">✗ {metaSaveError}</span>
                  {/if}
                </div>
              </div>
            </div>

            {#if !isNonCr}
              <div class="pd-section">
                <div class="pd-section-head">
                  <h4 class="pd-section-title">Drone Tickets</h4>
                  <div class="pd-inline-create">
                    <input class="pd-control" placeholder="Drone name…" bind:value={newSubprojectName} disabled={droneBusy} />
                    <button class="pd-command-btn" type="button" onclick={addSubproject} disabled={droneBusy || !newSubprojectName.trim()}>Add Drone Ticket</button>
                  </div>
                </div>
                <DroneTable
                  {drones}
                  droneTickets={detail.drone_tickets}
                  selectedRow={selectedSubprojectRow}
                  droneStateBusyName={droneStateBusyName}
                  droneStateErrorName={droneStateErrorName}
                  onSelectRow={onSelectSubprojectRow}
                  onChangeDroneState={onChangeSubprojectDroneState}
                  onOpenFolder={openSubprojectFolder}
                  {legalDroneOptionsFor}
                  onSaveDroneLink={saveDroneLinkFromTable}
                />
                {#if selectedSubprojectRowDetail}
                  {@const ticket = selectedSubprojectRowDetail.ticket}
                  <div class="pd-drone-detail">
                    <h5 class="pd-drone-detail-title">{selectedSubprojectRow} · Drone Ticket</h5>
                    {#if !droneLinkEditing && ticket?.drone_link}
                      <div class="pd-cr-link-display">
                        <span class="pd-cr-link-number">{ticket.drone_ticket || ticket.drone_link || "—"}</span>
                        <button class="pd-icon-btn" type="button" onclick={copyDroneLink} aria-label="Copy Drone link">
                          <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" class="pd-icon"><title>Copy Drone link</title><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path><rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect></svg>
                          {#if droneLinkCopied}<span style="font-size:9.5px;color:var(--tag-green-ink);margin-left:2px;">✓</span>{/if}
                        </button>
                        <button class="pd-icon-btn" type="button" onclick={() => window.open(ticket.drone_link, "_blank", "noopener,noreferrer")} aria-label="Open Drone link in browser">
                          <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" class="pd-icon"><title>Open Drone link in browser</title><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
                        </button>
                        <button class="pd-icon-btn" type="button" onclick={editDroneLink} aria-label="Edit Drone link">
                          <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" class="pd-icon"><title>Edit Drone link</title><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 1 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>
                        </button>
                      </div>
                    {:else}
                      <label class="pd-meta-field" for="row-drone-link">
                        <span class="pd-meta-label">Drone URL</span>
                        <input
                          id="row-drone-link"
                          class="cr-link-input"
                          type="url"
                          placeholder="Paste drone URL…"
                          value={droneLinkEdit}
                          onkeydown={(e) => { if (e.key === "Enter") (e.currentTarget as HTMLInputElement).blur(); }}
                          oninput={(e) => (droneLinkEdit = (e.currentTarget as HTMLInputElement).value)}
                          onblur={saveDroneLinkFromInput}
                          disabled={droneLinkBusy}
                        />
                      </label>
                      {#if !ticket}
                        <button class="cr-link-save-btn" type="button" onclick={addDroneForSelectedRow} disabled={droneLinkBusy || !droneLinkEdit.trim()}>Add Drone Ticket</button>
                      {/if}
                    {/if}
                    {#if droneLinkError}
                      <span class="cr-link-feedback cr-link-err">✗ {droneLinkError}</span>
                    {/if}
                  </div>
                {/if}
                {#if droneFeedback}
                  <p class:cr-link-ok={droneFeedbackKind === "success"} class:cr-link-err={droneFeedbackKind === "error"} class="cr-link-feedback">{droneFeedbackKind === "success" ? "✓" : "✗"} {droneFeedback}</p>
                {/if}
              </div>
            {/if}

            {#if !isNonCr && approvalStatus}
              <div class="pd-section">
                <div class="pd-section-head">
                  <h4 class="pd-section-title">Automations</h4>
                  <button
                    id="pd-approval-toggle"
                    type="button"
                    class="pd-control pd-approval-toggle"
                    class:on={approvalStatus.automation_enabled}
                    disabled={approvalBusy === "toggle" || approvalStatus.automation_locked || !approvalStatus.outlook_available}
                    title={approvalStatus.automation_locked
                      ? "Automation is unavailable: CR is FINISHED/POSTPONED/CANCELED"
                      : !approvalStatus.outlook_available
                        ? "Outlook not configured"
                        : "CR automation master toggle"}
                    onclick={toggleApproval}
                  >{approvalStatus.automation_enabled ? "ON" : "OFF"}</button>
                </div>
                {#if approvalStatus.automation_locked}
                  <p class="pd-auto-hint">Automation is forced OFF because the CR is finished, postponed, or canceled.</p>
                {/if}
                {#if approvalError}
                  <p class="cr-link-feedback cr-link-err">✗ {approvalError}</p>
                {/if}
                <div class="pd-auto-body" class:pd-auto-off={!approvalStatus.automation_enabled} inert={!approvalStatus.automation_enabled}>
                  <div class="pd-auto-group">
                    <span class="pd-auto-group-title">Automations Outlook</span>
                    {#each [["uat", "Send Ack Email"], ["lv", "Send LV Email"]] as [kind, title]}
                      {@const ks = kind === "uat" ? approvalStatus.uat : approvalStatus.lv}
                      {@const polling = ks.job?.status === "polling"}
                      <div class="pd-auto-item">
                        <div class="pd-auto-item-head">
                          <span class="pd-status-dot {autoDot(kind as 'uat' | 'lv')}"></span>
                          <span class="pd-auto-item-title">{title}</span>
                          <div class="pd-auto-item-actions">
                            <button class="pd-command-btn" type="button" disabled={!ks.eligible || approvalBusy !== ""} title={ks.eligible ? "Send now" : ks.reasons.join(", ")} onclick={() => requestSend(kind as "uat" | "lv", title)}>Send</button>
                            <button class="pd-command-btn" type="button" disabled={!ks.eligible || approvalBusy !== ""} title={ks.eligible ? "Open Outlook draft to review" : ks.reasons.join(", ")} onclick={() => draftApproval(kind as "uat" | "lv")}>Draft</button>
                            <button class="pd-command-btn" type="button" title="Open template settings" onclick={() => openAutomations(kind as "uat" | "lv")}>Setting</button>
                          </div>
                        </div>
                        <div class="pd-auto-item-sub">
                          <span class="pd-auto-status-label">{autoLabel(kind as "uat" | "lv")}</span>
                          <div class="pd-auto-item-actions">
                            <button class="pd-control pd-auto-mini-toggle" type="button" class:on={ks.auto_download} disabled={approvalBusy !== ""} onclick={() => toggleAutoDownload(kind as "uat" | "lv")}>Auto-download reply: {ks.auto_download ? "ON" : "OFF"}</button>
                            <button class="pd-command-btn" type="button" disabled={!polling || approvalBusy !== ""} title={polling ? "Check the inbox now" : "No pending reply to check"} onclick={() => forceCheck(kind as "uat" | "lv")}>Force Check Now</button>
                            {#if polling}<button class="pd-command-btn pd-command-danger" type="button" disabled={approvalBusy !== ""} onclick={() => stopApproval(kind as "uat" | "lv")}>Stop</button>{/if}
                          </div>
                        </div>
                      </div>
                    {/each}
                    <button class="pd-auto-add" type="button" onclick={() => openAutomations(undefined, "send_email")}>+ Add Email Automation</button>
                  </div>

                  <div class="pd-auto-group">
                    <span class="pd-auto-group-title">Automation CR</span>
                    <div class="pd-auto-item">
                      <div class="pd-auto-item-head">
                        <span class="pd-status-dot {approvalStatus.auto_update_cr_state ? 'dot-done' : 'dot-inactive'}"></span>
                        <span class="pd-auto-item-title">Auto Update CR State</span>
                        <div class="pd-auto-item-actions">
                          <button class="pd-control pd-auto-mini-toggle" type="button" class:on={approvalStatus.auto_update_cr_state} disabled={approvalBusy !== ""} onclick={toggleAutoUpdateCrState}>{approvalStatus.auto_update_cr_state ? "ON" : "OFF"}</button>
                          <button class="pd-command-btn" type="button" title="Open pattern settings" onclick={() => openAutomations(undefined, "auto_update_status")}>Setting</button>
                        </div>
                      </div>
                      <div class="pd-auto-item-sub"><span class="pd-auto-status-label">{approvalStatus.auto_update_cr_state ? "Watching inbox for state-change emails (engine pending)" : "Inactive"}</span></div>
                    </div>
                    <div class="pd-auto-item">
                      <div class="pd-auto-item-head">
                        <span class="pd-status-dot dot-inactive"></span>
                        <span class="pd-auto-item-title">Create Drone Ticket</span>
                        <div class="pd-auto-item-actions">
                          <button class="pd-command-btn" type="button" onclick={() => devStub("Create Drone Ticket butuh Jenkins API — tahap development.")}>Run</button>
                          <button class="pd-command-btn" type="button" onclick={() => devStub("Create Drone Ticket butuh Jenkins API — tahap development.")}>Setting</button>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div class="pd-auto-group">
                    <span class="pd-auto-group-title">Automation Teams</span>
                    {#each ["Auto Followup Ack", "Auto Followup Approval CR"] as label}
                      <div class="pd-auto-item">
                        <div class="pd-auto-item-head">
                          <span class="pd-status-dot dot-inactive"></span>
                          <span class="pd-auto-item-title">{label}</span>
                          <div class="pd-auto-item-actions">
                            <button class="pd-command-btn" type="button" onclick={() => devStub("Teams followup diatur setelah Template system (Slice 2).")}>Send</button>
                            <button class="pd-command-btn" type="button" onclick={() => devStub("Teams followup diatur setelah Template system (Slice 2).")}>Draft</button>
                            <button class="pd-command-btn" type="button" onclick={() => devStub("Teams followup diatur setelah Template system (Slice 2).")}>Setting</button>
                          </div>
                        </div>
                      </div>
                    {/each}
                    <button class="pd-auto-add" type="button" onclick={() => openAutomations(undefined, "send_teams")}>+ Add Automation Teams</button>
                  </div>
                </div>
              </div>
            {/if}
          </div>

          <div class="pane">
            <div class="pd-section">
              <h4 class="pd-section-title">Files</h4>
              <FileActions projectPath={detail.project_path} projectState={detail.project_state} {files} onFilesChanged={reloadFiles} />
            </div>

            <div class="pd-section">
              {#if isNonCr}
                <div class="pd-section-headline">
                  <h4 class="pd-section-title">Notes</h4>
                  <div class="pd-doc-actions">
                    <button class="pd-command-btn" type="button" onclick={() => (showNotesEditor = !showNotesEditor)}>
                      {showNotesEditor ? "Close Notes" : "Edit Notes"}
                    </button>
                  </div>
                </div>
                {#if showNotesEditor}
                  {#key detail.project_path}
                    <NotesEditor onReady={setRteEditorApi} projectPath={detail.project_path} initialNotes={notes} onSaved={(n: string) => { notes = n; }} />
                  {/key}
                {:else}
                  <div class="pd-notes-preview">
                    {notes.trim() || "No notes yet. Click Edit Notes to open the rich-text editor."}
                  </div>
                {/if}
              {:else}
                <div class="pd-section-headline">
                  <h4 class="pd-section-title">Notes &amp; CR Docs</h4>
                  <div class="pd-doc-actions">
                    <select
                      class="pd-doc-select"
                      aria-label="Select document to edit"
                      value={selectedCrDocPath}
                      onchange={(e) => selectCrDoc(e.currentTarget.value)}
                      disabled={crDocsLoading || crDocsFlushing}
                    >
                      {#each crDocsFiles as f}
                        <option value={f.path}>{f.name}</option>
                      {/each}
                    </select>
                    <span class="pd-rte-status" class:pd-rte-status-warn={selectedCrDoc?.capability === "read_only"} class:pd-rte-status-err={selectedCrDoc?.capability === "unsupported"}>
                      {#if crDocsFlushing}
                        Saving…
                      {:else if crDocsLoading}
                        Loading…
                      {:else if crDocsError}
                        Save failed
                      {:else if selectedCrDoc?.capability === "unsupported"}
                        Unsupported format
                      {:else if selectedCrDoc?.capability === "read_only"}
                        Read-only
                      {:else}
                        Saved
                      {/if}
                    </span>
                  </div>
                </div>
                {#if crDocsLoading}
                  <p class="pd-muted">Loading…</p>
                {:else if crDocsError}
                  <p class="pd-muted pd-error-text">Could not load document: {crDocsError}</p>
                {:else if selectedCrDoc && selectedCrDoc.format === "msg"}
                  <div class="pd-msg-panel">
                    <p class="pd-muted">Unsupported format: Format .msg belum dapat dibuka di editor ini.</p>
                    <button class="pd-command-btn" type="button" onclick={() => selectedCrDoc && openCrDocExternal(selectedCrDoc.path)}>
                      Open Externally
                    </button>
                  </div>
                {:else if selectedCrDoc}
                  {#if crDocContent?.capability === "read_only"}
                    <p class="pd-muted pd-locked-text">Read-only: {crDocContent.message || "dokumen ini terkunci dan tidak dapat diedit."}</p>
                  {:else if crDocContent?.capability === "unsupported"}
                    <div class="pd-msg-panel">
                      <p class="pd-muted pd-error-text">Unsupported format: {crDocContent.message || "Format ini belum dapat dibuka di editor ini."}</p>
                      <button class="pd-command-btn" type="button" onclick={() => selectedCrDoc && openCrDocExternal(selectedCrDoc.path)}>
                        Open Externally
                      </button>
                    </div>
                  {/if}
                  {#if !crDocReady}
                    <p class="pd-muted">Loading…</p>
                  {:else if crDocContent?.capability !== "unsupported"}
                    {#key selectedCrDoc.path}
                      <NotesEditor
                        onReady={setRteEditorApi}
                        projectPath={detail.project_path}
                        filePath={selectedCrDoc.path}
                        fileFormat={crDocContent?.format ?? selectedCrDoc?.format ?? "markdown"}
                        initialNotes={crDocContent?.content ?? ""}
                        editable={crDocContent?.editable ?? selectedCrDoc?.editable ?? false}
                        capability={crDocContent?.capability ?? selectedCrDoc?.capability ?? "unsupported"}
                        saveStrategy={crDocContent?.saveStrategy ?? selectedCrDoc?.saveStrategy ?? "none"}
                        supportedEditorFeatures={crDocContent?.supportedEditorFeatures ?? selectedCrDoc?.supportedEditorFeatures}
                        message={crDocContent?.message ?? selectedCrDoc?.message}
                        initialDoc={crDocDocPayload?.content ?? null}
                        initialRevision={crDocDocPayload?.revision ?? 0}
                        needsMigration={crDocDocPayload?.needs_migration ?? false}
                        onSaved={(n: string) => { notes = selectedCrDoc?.format === "markdown" ? n : notes; if (crDocContent) crDocContent.content = n; }}
                      />
                    {/key}
                  {/if}
                {:else}
                  <p class="pd-muted">No document selected.</p>
                {/if}
              {/if}
            </div>

            <div class="pd-section">
              <h4 class="pd-section-title">Activity History</h4>
              {#if detail.history?.length}
                <div class="pd-history-scroll">
                  <ol class="pd-history-list">
                    {#each detail.history as entry}
                      <li class="pd-history-item"><time>{entry.timestamp}</time><strong>{entry.action}</strong><span>{entry.detail}</span><small>{entry.user}</small></li>
                    {/each}
                  </ol>
                </div>
              {:else}
                <p class="pd-muted">No activity yet.</p>
              {/if}
            </div>

          </div>
        </div>
      {/if}
    </div>
  </div>
</section>

{#if topDeletePending && detail}
  <ConfirmModal title="Delete project" actionLabel="Delete project" targetName={detail.project_name} reversible={false} onConfirm={confirmTopDelete} onCancel={cancelTopDelete} />
{:else if pendingReopen}
  <ConfirmModal title="Reopen project?" actionLabel="Reopen to UAT_PREPARE" targetName={pendingReopen.name} reversible={true} onConfirm={confirmReopen} onCancel={cancelReopen} />
{:else if pendingSend}
  <ConfirmModal title="Send approval email?" actionLabel="Send now" targetName={`${pendingSend.label}${approvalStatus?.cr_number ? " · " + approvalStatus.cr_number : ""}`} reversible={false} onConfirm={confirmSend} onCancel={() => (pendingSend = null)} />
{/if}

<style>
  .pd-command-field { display:flex; flex-direction:column; gap:4px; min-width:110px; }
  .pd-command-field span { font-size:9.5px; font-weight:700; color:var(--color-muted); text-transform:uppercase; letter-spacing:0.05em; }
  .pd-command-project { min-width:180px; flex:0 1 240px; }
  .pd-approval-toggle { min-width: 44px; font-weight: 800; }
  .pd-approval-toggle.on { background: var(--soft-pink-surface); border-color: var(--color-dbs-red); color: var(--color-dbs-red); }
  .pd-auto-body { display:flex; flex-direction:column; gap:10px; }
  .pd-auto-body.pd-auto-off { opacity:.45; }
  .pd-auto-group { display:flex; flex-direction:column; gap:6px; }
  .pd-auto-group-title { font-size:9.5px; font-weight:800; color:var(--color-muted); text-transform:uppercase; letter-spacing:.05em; }
  .pd-auto-row { display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
  .pd-auto-mini-toggle { font-weight:800; }
  .pd-auto-mini-toggle.on { background:var(--soft-pink-surface); border-color:var(--color-dbs-red); color:var(--color-dbs-red); }
  .pd-auto-hint { font-size:10.5px; color:var(--color-muted); margin:0 0 6px; }
  .pd-auto-item { border:1px solid var(--color-input-border); border-radius:7px; padding:7px 9px; display:flex; flex-direction:column; gap:6px; background:#fff; }
  .pd-auto-item-head { display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
  .pd-auto-item-title { font-size:11.5px; font-weight:800; color:var(--color-ink); }
  .pd-auto-item-actions { display:flex; gap:6px; flex-wrap:wrap; align-items:center; margin-left:auto; }
  .pd-auto-item-sub { display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
  .pd-auto-status-label { font-size:10px; color:var(--color-muted); font-weight:700; }
  .pd-status-dot { width:9px; height:9px; border-radius:50%; flex:0 0 auto; box-shadow:0 0 0 2px rgba(0,0,0,0.04); }
  .pd-status-dot.dot-done { background:var(--tag-green-ink, #17803d); }
  .pd-status-dot.dot-waiting { background:#C77700; }
  .pd-status-dot.dot-error { background:var(--color-dbs-red); }
  .pd-status-dot.dot-ready { background:#2563EB; }
  .pd-status-dot.dot-inactive { background:#B7BEC7; }
  .pd-auto-add { align-self:flex-start; background:transparent; border:1px dashed var(--color-input-border); border-radius:6px; color:var(--color-muted); font-size:10.5px; font-weight:800; padding:4px 9px; cursor:pointer; }
  .pd-auto-add:hover { border-color:var(--color-dbs-red); color:var(--color-dbs-red); }
  .pd-command-spacer { flex:1 1 auto; }
  .pd-control { height:28px; min-width:0; border:1px solid var(--color-input-border); border-radius:6px; background:#fff; color:var(--color-ink); font-size:11.5px; font-weight:700; padding:3px 9px; outline:none; }
  .pd-control:focus { border-color:var(--color-dbs-red); }
  .pd-control:disabled { background:var(--color-row-alt); color:var(--color-muted); }
  .pd-command-btn { height:28px; padding:0 13px; border:1px solid var(--color-border); border-radius:7px; background:#fff; color:var(--color-ink); font-size:12px; font-weight:700; cursor:pointer; white-space:nowrap; }
  .pd-command-btn:hover:not(:disabled) { border-color:var(--color-dbs-red); color:var(--color-dbs-red); }
  .pd-command-danger { border-color:var(--color-dbs-red); color:var(--color-dbs-red); }
  .pd-command-danger:hover:not(:disabled) { background:var(--color-dbs-red); color:#fff; }
  .pd-command-btn:disabled { opacity:0.5; cursor:not-allowed; }
  .pd-body { flex:1; min-height:0; display:flex; flex-direction:column; gap:12px; }
  .pd-detail-panel { display:flex; flex-direction:column; gap:10px; min-height:0; overflow-y:auto; }
  .split { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:16px; align-items:start; }
  .pane { display:flex; flex-direction:column; gap:14px; min-width:0; }
  .pd-muted { margin:0; font-size:11px; font-weight:400; color:var(--color-muted); line-height:1.5; }
  @media (max-width:980px) { .split { grid-template-columns:1fr; } }
  .pd-section { background:var(--color-workspace-panel); border:1px solid var(--color-border); border-radius:8px; box-shadow:0 1px 3px rgba(0,0,0,0.05); padding:18px; }
  .pd-section-head { display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:8px; flex-wrap:wrap; }
  .pd-section-head .pd-section-title { margin:0; }
  .pd-section-headline { display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:8px; }
  .pd-section-headline .pd-section-title { margin:0; }
  .pd-notes-preview { white-space:pre-wrap; font-size:11px; line-height:1.5; color:var(--color-ink); background:var(--color-workspace); border:1px dashed var(--color-border); border-radius:6px; padding:10px; max-height:160px; overflow:auto; }
  .pd-doc-actions { display:flex; align-items:center; gap:6px; flex-wrap:wrap; justify-content:flex-end; }
  .pd-doc-select { height:28px; padding:0 8px; border:1px solid var(--color-border); border-radius:6px; background:#fff; color:var(--color-ink); font-size:11.5px; font-weight:700; cursor:pointer; max-width:200px; }
  .pd-doc-select:focus { border-color:var(--color-dbs-red); outline:none; box-shadow:0 0 0 2px var(--color-dbs-red-active); }
  .pd-doc-select:disabled { opacity:0.55; cursor:not-allowed; }
  .pd-rte-status { display:inline-flex; align-items:center; height:24px; padding:0 8px; border-radius:999px; background:var(--tag-green-bg); color:var(--tag-green-ink); font-size:10px; font-weight:900; white-space:nowrap; }
  .pd-rte-status-warn { background:var(--tag-amber-bg); color:var(--tag-amber-ink); }
  .pd-rte-status-err { background:var(--tag-red-bg); color:var(--tag-red-ink); }
  .pd-msg-panel { display:flex; flex-direction:column; gap:8px; align-items:flex-start; padding:10px; border:1px dashed var(--color-border); border-radius:6px; background:var(--color-workspace); }
  .pd-error-text { color:var(--color-dbs-red); }
  .pd-locked-text { color:var(--tag-amber-ink); margin-bottom:6px; }
  .pd-section-title { margin:0 0 8px; font-family:var(--font-display); font-size:13px; font-weight:600; letter-spacing:-0.01em; color:var(--color-ink-strong); display:flex; align-items:center; gap:6px; }
  .pd-inline-create { display:flex; align-items:center; gap:6px; flex:0 1 360px; }
  .pd-inline-create .pd-control { flex:1; }
  .pd-meta-edit { display:flex; flex-direction:column; gap:6px; }
  .pd-meta-datetime-row { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
  @media (max-width:700px) { .pd-meta-datetime-row { grid-template-columns:1fr; } }
  .pd-meta-field { display:flex; flex-direction:column; gap:5px; min-width:0; }
  .pd-meta-label { font-size:9.5px; font-weight:600; color:#6B7280; text-transform:uppercase; letter-spacing:0.05em; }
  .pd-history-list { list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:7px; }
  .pd-history-item { display:grid; grid-template-columns:minmax(120px,auto) minmax(70px,auto) 1fr; gap:6px 8px; padding:8px; border:1px solid var(--color-border); border-radius:8px; background:var(--color-workspace); font-size:11px; color:var(--color-ink); }
  .pd-history-item time { color:var(--color-muted); font-size:10px; }
  .pd-history-item strong { color:var(--color-ink-strong); font-size:10.5px; }
  .pd-history-item small { grid-column:3; color:var(--color-muted); font-size:10px; }
  .pd-cr-link-display { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
  .pd-cr-link-number { font-size: 12px; font-weight: 700; color: var(--color-ink-strong); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
  .pd-icon-btn { flex: 0 0 auto; width: 26px; height: 26px; padding: 0; border: 1px solid var(--color-border); border-radius: 6px; background: #fff; color: var(--color-ink); font-size: 12px; font-weight: 700; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; gap: 2px; }
  .pd-icon-btn:hover:not(:disabled) { border-color: var(--color-dbs-red); color: var(--color-dbs-red); }
  .cr-link-input { flex:1; min-width:0; padding:6px 9px; font-size:11.5px; font-weight:400; border:1px solid var(--color-border); border-radius:6px; background:var(--color-workspace-panel); color:var(--color-ink); outline:none; }
  .cr-link-input:focus { border-color:var(--color-dbs-red); }
  .cr-link-input:disabled { background:var(--color-row-alt); color:var(--color-muted); }
  .cr-link-save-btn { padding:6px 13px; font-size:11px; font-weight:600; border:1px solid var(--color-dbs-red); border-radius:6px; background:var(--color-dbs-red); color:#fff; cursor:pointer; white-space:nowrap; transition:background 0.12s; }
  .cr-link-save-btn:hover:not(:disabled) { background:var(--color-dbs-red-hover, #991B1B); }
  .cr-link-save-btn:disabled { opacity:0.45; cursor:not-allowed; }
  .cr-link-feedback { display:inline-block; margin-top:5px; font-size:10.5px; font-weight:600; }
  .cr-link-ok { color:var(--tag-green-ink); }
  .cr-link-err { color:var(--active-red); }
  .cr-state-select { padding:5px 9px; font-size:11.5px; font-weight:800; border:1px solid var(--primary-red); border-radius:6px; background:var(--primary-red); color:#fff; outline:none; cursor:pointer; }
  .cr-state-select:focus { box-shadow:0 0 0 2px var(--color-dbs-red-active); }
  .cr-state-select:disabled { opacity:0.55; cursor:not-allowed; }
  .pd-drone-detail { margin-top: 8px; padding: 10px; border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-workspace); display: flex; flex-direction: column; gap: 6px; }
  .pd-drone-detail-title { margin: 0; font-size: 11px; font-weight: 800; color: var(--color-ink-strong); }
  .pd-history-scroll { max-height: 280px; overflow-y: auto; padding-right: 4px; }
  .pd-spinner { animation: spin 1s linear infinite; display: inline-block; vertical-align: middle; margin-right: 4px; }
  @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
</style>
