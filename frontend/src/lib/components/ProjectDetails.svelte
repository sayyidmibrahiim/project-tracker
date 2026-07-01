<script lang="ts">
  import { onMount } from "svelte";
  import { callBridge, isPywebviewReady, waitForPywebviewReady } from "../bridge";
  import type { ProjectRow, ProjectDetail, FileRow, DroneTicket } from "../types";
  import { BridgeErrorCode } from "../types";
  import FileActions from "./FileActions.svelte";
  import NotesEditor from "./NotesEditor.svelte";
  import NewProjectForm from "./NewProjectForm.svelte";
  import SubProjectTable from "./SubProjectTable.svelte";
  import ConfirmModal from "./ConfirmModal.svelte";
  import { addToast } from "../stores/toastStore";
  import type { ToastAction } from "../stores/toastStore";

  // Optional cross-page navigation from the Dashboard row menu / header Add Project.
  let { initialPath = null, startNew = false, onNavigateDashboard }: { initialPath?: string | null; startNew?: boolean; onNavigateDashboard?: () => void } = $props();

  type LoadState = "idle" | "loading" | "error" | "loaded";
  let listState: LoadState = $state("idle");
  let detailState: LoadState = $state("idle");
  let errorCode: string = $state("");
  let errorMessage: string = $state("");

  let projects: ProjectRow[] = $state([]);
  let selectedPath: string = $state("");
  let detail: ProjectDetail | null = $state(null);
  let isSubproject: boolean = $state(false);
  let selectedSubproject: string = $state("all");
  let subprojects: string[] = $state([]);
  let files: FileRow[] = $state([]);
  let notes: string = $state("");
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

  // ── Drone edit state ──
  let droneBusy: boolean = $state(false);
  let droneError: string = $state("");
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
  let subprojectBusy: boolean = $state(false);
  let subprojectFeedback: string = $state("");
  let subprojectFeedbackKind: "idle" | "success" | "error" = $state("idle");

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
    selectedPath = path;
    detailState = "loading";
    detail = null; isSubproject = false; selectedSubproject = "all"; subprojects = []; files = []; notes = "";
    topActionState = "idle"; topActionError = ""; topDeletePending = false;
    crLinkEdit = ""; crLinkSaveState = "idle"; crLinkSaveError = "";
    crStateEdit = ""; crStateSaveState = "idle"; crStateSaveError = "";
    droneError = "";
    selectedSubprojectRow = null;
    droneLinkEdit = "";
    droneLinkBusy = false;
    droneLinkError = "";
    droneLinkEditing = false;
    droneLinkCopied = false;
    droneStateBusyName = null;
    droneStateErrorName = {};
    newSubprojectName = ""; subprojectBusy = false; subprojectFeedback = ""; subprojectFeedbackKind = "idle";
    errorCode = ""; errorMessage = "";

    if (!isPywebviewReady() && !(await waitForPywebviewReady())) {
      errorCode = BridgeErrorCode.BRIDGE_UNAVAILABLE;
      errorMessage = "pywebview bridge unavailable.";
      detailState = "error";
      return;
    }

    const [dResp, spResp, flResp, ntResp] = await Promise.all([
      callBridge<ProjectDetail>("project_get", path),
      callBridge<string[]>("subproject_list", path),
      callBridge<FileRow[]>("file_list", path),
      callBridge<string>("notes_get", path),
    ]);

    detail = dResp.ok ? (dResp.data ?? null) : null;
    isSubproject = detail ? detail.is_subproject || false : false;
    subprojects = spResp.ok ? (spResp.data ?? []) : [];
    files = flResp.ok ? (flResp.data ?? []) : [];
    notes = ntResp.ok ? (ntResp.data ?? "") : "";

    if (detail) {
      crLinkEdit = detail.cr_link || "";
      crLinkEditing = !detail.cr_link;
      crLinkCopied = false;
    }
    if (detail) crStateEdit = detail.cr_state || "";
    if (detail) syncMetadataDrafts(detail);

    if (!dResp.ok) {
      errorCode = dResp.error.code;
      errorMessage = dResp.error.message;
      detailState = "error";
    } else {
      detailState = "loaded";
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
    subprojectFeedback = "";
    subprojectFeedbackKind = "idle";
    if (!selectedPath || !name) return;
    if (!isPywebviewReady()) {
      subprojectFeedback = "pywebview bridge unavailable.";
      subprojectFeedbackKind = "error";
      return;
    }
    subprojectBusy = true;
    const resp = await callBridge("subproject_create", selectedPath, name);
    subprojectBusy = false;
    if (!resp.ok) {
      subprojectFeedback = resp.error.message;
      subprojectFeedbackKind = "error";
      return;
    }
    newSubprojectName = "";
    selectedSubprojectRow = name;
    droneLinkEdit = "";
    subprojectFeedback = `Created ${name}.`;
    subprojectFeedbackKind = "success";
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
  }

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

  export function refresh() { loadProjects(); }

  // After project_create succeeds, leave NEW_PROJECT mode, reload the list, and
  // open the freshly created project in SHOW_EDIT (PRD §12.4 navigation).
  async function onProjectCreated(path: string) {
    mode = "browse";
    await loadProjects();
    if (path) await selectProject(path);
  }

  // After a successful delete the project folder is gone. Clear the selection
  // and reload the list so the dashboard reflects the change (Req 5.6).
  async function onProjectDeleted() {
    selectedPath = "";
    detail = null;
    subprojects = [];
    files = [];
    notes = "";
    detailState = "idle";
    await loadProjects();
  }

  // After a successful subproject delete, reload the subproject list (Req 5.7).
  async function reloadSubprojects() {
    if (!selectedPath || !isPywebviewReady()) return;
    const resp = await callBridge<string[]>("subproject_list", selectedPath);
    if (resp.ok) subprojects = resp.data ?? [];
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
      <label class="pd-command-field pd-command-project" for="pd-subproject-select">
        <span>Sub Project</span>
        <select id="pd-subproject-select" class="pd-control" bind:value={selectedSubproject} disabled={!selectedPath || subprojects.length === 0 || mode === "new"}>
          <option value="all">All Sub Projects</option>
          {#each subprojects as sp}
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
                <input id="meta-name" class="cr-link-input" bind:value={metaNameEdit} onblur={saveMetadataIfChanged} disabled={metaSaveState === "saving" || isSubproject} />
                <div class="pd-meta-datetime-row">
                  <div class="pd-meta-field">
                    <span class="pd-meta-label">CR Number</span>
                    {#if crLinkEditing && !isSubproject}
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
                        {#if !isSubproject}
                          <button class="pd-icon-btn" type="button" onclick={editCrLink} aria-label="Edit CR link">
                            <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" class="pd-icon"><title>Edit CR link</title><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 1 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>
                          </button>
                        {/if}
                      </div>
                    {/if}
                    {#if isSubproject}
                      <span class="pd-inherited-label">(Inherited from Main Project)</span>
                    {/if}
                  </div>
                  <label class="pd-meta-field" for="meta-cr-state">
                    <span class="pd-meta-label">CR State</span>
                    <select id="meta-cr-state" class="cr-state-select" value={crStateEdit} onchange={(e) => onCrStateChange((e.currentTarget as HTMLSelectElement).value)} disabled={crStateSaveState === "saving" || isSubproject}>
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
                </div>
              </div>
            </div>

            <div class="pd-section">
              <h4 class="pd-section-title">Schedule</h4>
              <div class="pd-meta-edit">
                <div class="pd-meta-datetime-row">
                  <label class="pd-meta-field" for="meta-start">
                    <span class="pd-meta-label">Start datetime</span>
                    <input id="meta-start" class="cr-link-input" type="datetime-local" bind:value={metaStartEdit} onblur={saveMetadataIfChanged} disabled={metaSaveState === "saving" || isSubproject} />
                  </label>
                  <label class="pd-meta-field" for="meta-end">
                    <span class="pd-meta-label">End datetime</span>
                    <input id="meta-end" class="cr-link-input" type="datetime-local" bind:value={metaEndEdit} onblur={saveMetadataIfChanged} disabled={metaSaveState === "saving" || isSubproject} />
                  </label>
                </div>
                {#if isSubproject}
                  <span class="pd-inherited-label">(Inherited from Main Project)</span>
                {/if}
                <div class="pd-notes-actions">
                  <button class="cr-link-save-btn" onclick={saveMetadata} disabled={metaSaveState === "saving" || metadataUnchanged(detail) || isSubproject}>{#if metaSaveState === "saving"}⏳ Saving…{:else}Save identity + schedule{/if}</button>
                  {#if metaSaveState === "success"}
                    <span class="cr-link-feedback cr-link-ok">✓ Saved</span>
                  {:else if metaSaveState === "error"}
                    <span class="cr-link-feedback cr-link-err">✗ {metaSaveError}</span>
                  {/if}
                </div>
              </div>
            </div>

            {#if !isSubproject}
              <div class="pd-section">
                <div class="pd-section-head">
                  <h4 class="pd-section-title">Sub Project (DRONE)</h4>
                  <div class="pd-inline-create">
                    <input class="pd-control" placeholder="Sub project name…" bind:value={newSubprojectName} disabled={subprojectBusy} />
                    <button class="pd-command-btn" type="button" onclick={addSubproject} disabled={subprojectBusy || !newSubprojectName.trim()}>Add Sub Project</button>
                  </div>
                </div>
                <SubProjectTable
                  {subprojects}
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
                {#if subprojectFeedback}
                  <p class:cr-link-ok={subprojectFeedbackKind === "success"} class:cr-link-err={subprojectFeedbackKind === "error"} class="cr-link-feedback">{subprojectFeedbackKind === "success" ? "✓" : "✗"} {subprojectFeedback}</p>
                {/if}
              </div>
            {/if}
          </div>

          <div class="pane">
            <div class="pd-section">
              <h4 class="pd-section-title">Files</h4>
              <FileActions projectPath={detail.project_path} projectState={detail.project_state} {files} onFilesChanged={reloadFiles} />
            </div>

            <div class="pd-section">
              <h4 class="pd-section-title">Notes</h4>
              {#key detail.project_path}
                <NotesEditor projectPath={detail.project_path} initialNotes={notes} onSaved={(n: string) => { notes = n; }} />
              {/key}
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
{/if}

<style>
  .pd-command-field { display:flex; flex-direction:column; gap:4px; min-width:110px; }
  .pd-command-field span { font-size:9.5px; font-weight:700; color:var(--color-muted); text-transform:uppercase; letter-spacing:0.05em; }
  .pd-command-project { min-width:180px; flex:0 1 240px; }
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
  .cr-link-err { color:#DC2626; }
  .cr-state-select { padding:5px 9px; font-size:11.5px; font-weight:800; border:1px solid var(--primary-red); border-radius:6px; background:var(--primary-red); color:#fff; outline:none; cursor:pointer; }
  .cr-state-select:focus { box-shadow:0 0 0 2px var(--color-dbs-red-active); }
  .cr-state-select:disabled { opacity:0.55; cursor:not-allowed; }
  .pd-drone-detail { margin-top: 8px; padding: 10px; border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-workspace); display: flex; flex-direction: column; gap: 6px; }
  .pd-drone-detail-title { margin: 0; font-size: 11px; font-weight: 800; color: var(--color-ink-strong); }
  .pd-history-scroll { max-height: 280px; overflow-y: auto; padding-right: 4px; }
  .pd-spinner { animation: spin 1s linear infinite; display: inline-block; vertical-align: middle; margin-right: 4px; }
  .pd-inherited-label { font-size: 10px; color: var(--color-muted); font-style: italic; margin-top: 2px; }
  @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
</style>
