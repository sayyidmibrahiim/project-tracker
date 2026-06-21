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
    detail = null; subprojects = []; files = []; notes = "";
    topActionState = "idle"; topActionError = ""; topDeletePending = false;
    crLinkEdit = ""; crLinkSaveState = "idle"; crLinkSaveError = "";
    crStateEdit = ""; crStateSaveState = "idle"; crStateSaveError = "";
    droneError = "";
    selectedSubprojectRow = null;
    droneLinkEdit = "";
    droneLinkBusy = false;
    droneLinkError = "";
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
    if (detail) detail.cr_link = crLinkEdit;
    crLinkSaveState = "success";
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
    if (detail) detail.cr_state = crStateEdit;
    crStateSaveState = "success";
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
    setTimeout(() => { if (metaSaveState === "success") metaSaveState = "idle"; }, 2500);
    await refreshDetail();
  }

  function onSelectSubprojectRow(name: string) {
    selectedSubprojectRow = selectedSubprojectRow === name ? null : name;
    droneLinkEdit = selectedSubprojectRowDetail?.ticket?.drone_link ?? "";
    droneLinkError = "";
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

  async function saveDroneLinkFromPanel() {
    if (!detail || !selectedPath || !selectedSubprojectRowDetail) return;
    if (selectedSubprojectRowDetail.index < 0 || !selectedSubprojectRowDetail.ticket) return;
    const next = droneLinkEdit.trim();
    const current = selectedSubprojectRowDetail.ticket.drone_link ?? "";
    if (next === current) return;
    droneLinkBusy = true; droneLinkError = "";
    const resp = await callBridge("drone_update", selectedPath, selectedSubprojectRowDetail.index, { drone_link: next });
    droneLinkBusy = false;
    if (!resp.ok) { droneLinkError = resp.error.message; return; }
    await refreshDetail();
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
  {#if onNavigateDashboard}
    <div class="pd-back-bar">
      <button type="button" class="pd-back-btn" onclick={() => onNavigateDashboard?.()}>
        <span class="pd-back-arrow" aria-hidden="true">←</span>
        <span>Back to Dashboard</span>
      </button>
    </div>
  {/if}
  <div class="panel-card" style="flex:0 0 auto;">
    <div class="toolbar">
      <div class="panel-title-row" style="margin:0 18px 0 0;"><span class="panel-title-icon">▣</span><span class="panel-title">Project Command Center</span><span class="panel-subtitle">compact editing workspace</span></div>
      <label class="pd-command-field pd-command-project" for="pd-project-select">
        <span>Project</span>
        <select id="pd-project-select" class="pd-control" value={selectedPath} onchange={(e) => selectProject((e.target as HTMLSelectElement).value)} disabled={filtered.length === 0 || mode === "new"}>
          <option value="">Select project…</option>
          {#each filtered as p}
            <option value={p.project_path}>{p.project_name}</option>
          {/each}
        </select>
      </label>
      <div class="pd-command-spacer"></div>
      <button class="pd-command-btn" type="button" onclick={openProjectFolder} disabled={!selectedPath || topActionState === "saving"}>Open</button>
      <button class="pd-command-btn pd-command-danger" type="button" onclick={requestTopDelete} disabled={!selectedPath || topActionState === "saving"}>Delete</button>
    </div>
    {#if topActionState === "error"}
      <p class="cr-link-feedback cr-link-err">✗ {topActionError}</p>
    {:else if topActionState === "success"}
      <p class="cr-link-feedback cr-link-ok">✓ Done</p>
    {/if}
  </div>

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
        <div class="dashboard-banner banner-error"><span class="banner-icon">⚠</span><div><p class="banner-title">Failed</p><p class="banner-detail">{errorCode}: {errorMessage}</p></div></div>
      {:else if !selectedPath}
        <div class="table-empty"><p class="empty-title">Select a project</p><p class="empty-sub">Use the Project Command Center selector to view details.</p></div>
      {:else if detailState === "loading"}
        <div class="dashboard-banner banner-loading"><span class="banner-icon">◌</span><span>Loading details…</span></div>
      {:else if detailState === "error"}
        <div class="dashboard-banner banner-error"><span class="banner-icon">⚠</span><div><p class="banner-title">Detail load failed</p><p class="banner-detail">{errorCode}: {errorMessage}</p></div></div>
      {:else if detail}
        <div class="split">
          <div class="pane">
            <div class="pd-section">
              <h4 class="pd-section-title">Project Identity</h4>
              <div class="pd-meta-edit">
                <label class="pd-meta-label" for="meta-name">Project Name</label>
                <input id="meta-name" class="cr-link-input" bind:value={metaNameEdit} disabled={metaSaveState === "saving"} />
                <div class="pd-dl-item"><dt>CR Number</dt><dd>{detail.cr_number || "—"}</dd></div>
                <label class="pd-meta-label" for="meta-cr-link">CR Link</label>
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
                    <span class="pd-cr-link-number">{detail.cr_number || detail.cr_link}</span>
                    <button class="pd-icon-btn" type="button" title="Copy CR link" onclick={copyCrLink} aria-label="Copy CR link">📋{#if crLinkCopied} ✓{/if}</button>
                    <button class="pd-icon-btn" type="button" title="Open CR link in browser" onclick={openCrLink} aria-label="Open CR link in browser">↗</button>
                    <button class="pd-icon-btn" type="button" title="Edit CR link" onclick={editCrLink} aria-label="Edit CR link">✎</button>
                  </div>
                {/if}
                <div class="pd-meta-datetime-row">
                  <label class="pd-meta-field" for="meta-cr-state">
                    <span class="pd-meta-label">CR State</span>
                    <select id="meta-cr-state" class="cr-state-select" value={crStateEdit} onchange={(e) => onCrStateChange((e.currentTarget as HTMLSelectElement).value)} disabled={crStateSaveState === "saving"}>
                      {#each legalCrOptionsFor(detail.cr_state) as opt}
                        <option value={opt} disabled={opt === "IN-PROGRESS"}>{opt}</option>
                      {/each}
                    </select>
                  </label>
                </div>
                {#if crStateSaveState === "saving"}
                  <span class="cr-link-feedback">⏳ Saving…</span>
                {:else if crStateSaveState === "success"}
                  <span class="cr-link-feedback cr-link-ok">✓ Saved</span>
                {:else if crStateSaveState === "error"}
                  <span class="cr-link-feedback cr-link-err">✗ {crStateSaveError}</span>
                {/if}
              </div>
            </div>

            <div class="pd-section">
              <h4 class="pd-section-title">Schedule</h4>
              <div class="pd-meta-edit">
                <div class="pd-meta-datetime-row">
                  <label class="pd-meta-field" for="meta-start">
                    <span class="pd-meta-label">Start datetime</span>
                    <input id="meta-start" class="cr-link-input" type="datetime-local" bind:value={metaStartEdit} disabled={metaSaveState === "saving"} />
                  </label>
                  <label class="pd-meta-field" for="meta-end">
                    <span class="pd-meta-label">End datetime</span>
                    <input id="meta-end" class="cr-link-input" type="datetime-local" bind:value={metaEndEdit} disabled={metaSaveState === "saving"} />
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
              />
              {#if selectedSubprojectRowDetail}
                {@const ticket = selectedSubprojectRowDetail.ticket}
                <div class="pd-drone-detail">
                  <h5 class="pd-drone-detail-title">{selectedSubprojectRow} · Drone Ticket</h5>
                  <label class="pd-meta-field" for="row-drone-link">
                    <span class="pd-meta-label">Drone URL</span>
                    <input
                      id="row-drone-link"
                      class="cr-link-input"
                      type="url"
                      placeholder="Paste drone URL…"
                      value={droneLinkEdit}
                      oninput={(e) => (droneLinkEdit = (e.currentTarget as HTMLInputElement).value)}
                      onblur={saveDroneLinkFromPanel}
                      disabled={droneLinkBusy}
                    />
                  </label>
                  {#if !ticket}
                    <button class="cr-link-save-btn" type="button" onclick={addDroneForSelectedRow} disabled={droneLinkBusy || !droneLinkEdit.trim()}>Add Drone Ticket</button>
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
          </div>

          <div class="pane">
            <div class="pd-section">
              <h4 class="pd-section-title">Files</h4>
              <FileActions projectPath={detail.project_path} projectState={detail.project_state} {files} onFilesChanged={reloadFiles} />
            </div>

            <div class="pd-section">
              <h4 class="pd-section-title">Notes</h4>
              {#key detail.project_path}
                <NotesEditor projectPath={detail.project_path} initialNotes={notes} onSaved={(n) => { notes = n; }} />
              {/key}
            </div>

            <div class="pd-section">
              <h4 class="pd-section-title">Activity History</h4>
              {#if detail.history?.length}
                <ol class="pd-history-list">
                  {#each detail.history as entry}
                    <li class="pd-history-item"><time>{entry.timestamp}</time><strong>{entry.action}</strong><span>{entry.detail}</span><small>{entry.user}</small></li>
                  {/each}
                </ol>
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
  .split { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:12px; align-items:start; }
  .pane { display:flex; flex-direction:column; gap:10px; min-width:0; }
  .pd-muted { margin:0; font-size:11px; font-weight:400; color:var(--color-muted); line-height:1.5; }
  @media (max-width:980px) { .split { grid-template-columns:1fr; } }
  .pd-dl-item { display:flex; flex-direction:column; gap:3px; }
  .pd-dl-item dt { font-size:9.5px; font-weight:600; color:var(--color-muted); text-transform:uppercase; letter-spacing:0.05em; }
  .pd-dl-item dd { margin:0; font-size:12.5px; font-weight:500; color:var(--color-ink-strong); }
  .pd-section { background:var(--color-workspace-panel); border:1px solid var(--color-border); border-left:3px solid var(--color-dbs-red); border-radius:10px; box-shadow:var(--shadow-card); padding:14px; }
  .pd-section-head { display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:8px; flex-wrap:wrap; }
  .pd-section-head .pd-section-title { margin:0; }
  .pd-section-title { margin:0 0 8px; font-family:var(--font-display); font-size:13px; font-weight:600; letter-spacing:-0.01em; color:var(--color-ink-strong); display:flex; align-items:center; gap:6px; }
  .pd-inline-create { display:flex; align-items:center; gap:6px; flex:0 1 360px; }
  .pd-inline-create .pd-control { flex:1; }
  .pd-meta-edit { display:flex; flex-direction:column; gap:6px; }
  .pd-meta-datetime-row { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
  @media (max-width:700px) { .pd-meta-datetime-row { grid-template-columns:1fr; } }
  .pd-meta-field { display:flex; flex-direction:column; gap:5px; min-width:0; }
  .pd-meta-label { font-size:9.5px; font-weight:600; color:var(--color-muted); text-transform:uppercase; letter-spacing:0.05em; }
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
  .pd-back-bar { flex: 0 0 auto; display: flex; align-items: center; }
  .pd-back-btn { display: inline-flex; align-items: center; gap: 6px; height: 28px; padding: 0 12px; border: 1px solid var(--color-border); border-radius: 7px; background: #fff; color: var(--color-ink); font-size: 12px; font-weight: 700; cursor: pointer; }
  .pd-back-btn:hover { border-color: var(--color-dbs-red); color: var(--color-dbs-red); }
  .pd-back-arrow { font-weight: 900; }
  .pd-drone-detail { margin-top: 8px; padding: 10px; border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-workspace); display: flex; flex-direction: column; gap: 6px; }
  .pd-drone-detail-title { margin: 0; font-size: 11px; font-weight: 800; color: var(--color-ink-strong); }
</style>
