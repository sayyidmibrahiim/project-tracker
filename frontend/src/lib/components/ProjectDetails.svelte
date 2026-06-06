<script lang="ts">
  import { onMount } from "svelte";
  import { callBridge, isPywebviewReady } from "../bridge";
  import type { ProjectRow, ProjectDetail, FileRow, DroneTicket } from "../types";
  import { BridgeErrorCode } from "../types";

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

  // ── CR Link edit state ──
  let crLinkEdit: string = $state("");
  type CrLinkSave = "idle" | "saving" | "success" | "error";
  let crLinkSaveState: CrLinkSave = $state("idle");
  let crLinkSaveError: string = $state("");

  // ── CR State edit state ──
  // Real CRState enum values (REOPEN excluded — action/event, not a persist target).
  const CR_STATE_OPTIONS = ["PENDING SUBMISSION", "PENDING APPROVAL", "APPROVED", "IN-PROGRESS", "FINISHED", "POSTPONED", "CANCELED"];
  let crStateEdit: string = $state("");
  type CrStateSave = "idle" | "saving" | "success" | "error";
  let crStateSaveState: CrStateSave = $state("idle");
  let crStateSaveError: string = $state("");

  // ── Notes edit state ──
  let notesEdit: string = $state("");
  type NotesSave = "idle" | "saving" | "success" | "error";
  let notesSaveState: NotesSave = $state("idle");
  let notesSaveError: string = $state("");

  // ── Drone edit state ──
  let droneBusy: boolean = $state(false);
  let droneError: string = $state("");
  // Add-drone form
  let newDroneLink: string = $state("");
  let newDroneSubfolder: string = $state("");
  let newDroneOwner: string = $state("");
  // Per-index edit drafts
  let droneEditIndex: number = $state(-1);
  let droneEditLink: string = $state("");
  let droneEditSubfolder: string = $state("");
  let droneEditOwner: string = $state("");
  // ── Drone state edit state ──
  const DRONE_STATE_OPTIONS = ["UAT", "PENDING APPROVAL", "APPROVED", "IN-PROGRESS", "FINISHED", "CANCELED"];
  let droneStateEdits: Record<number, string> = $state({});
  let droneStateBusy: number = $state(-1);
  let droneStateError: Record<number, string> = $state({});

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

  async function loadProjects() {
    listState = "loading";
    if (!isPywebviewReady()) {
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
    crLinkEdit = ""; crLinkSaveState = "idle"; crLinkSaveError = "";
    crStateEdit = ""; crStateSaveState = "idle"; crStateSaveError = "";
    notesEdit = ""; notesSaveState = "idle"; notesSaveError = "";
    droneEditIndex = -1; droneError = ""; newDroneLink = ""; newDroneSubfolder = ""; newDroneOwner = "";
    droneStateEdits = {}; droneStateBusy = -1; droneStateError = {};
    errorCode = ""; errorMessage = "";

    if (!isPywebviewReady()) {
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

    if (detail) crLinkEdit = detail.cr_link || "";
    if (detail) crStateEdit = detail.cr_state || "";
    if (detail) syncDroneStateEdits();
    notesEdit = notes;

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

  async function saveCrState() {
    if (!selectedPath || !isPywebviewReady()) {
      crStateSaveError = "pywebview bridge unavailable.";
      crStateSaveState = "error";
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

  async function saveNotes() {
    if (!selectedPath) return;
    notesSaveState = "saving";
    notesSaveError = "";

    if (!isPywebviewReady()) {
      notesSaveError = "pywebview bridge unavailable.";
      notesSaveState = "error";
      return;
    }

    const resp = await callBridge("notes_update", selectedPath, notesEdit);
    if (!resp.ok) {
      notesSaveError = resp.error.message;
      notesSaveState = "error";
      return;
    }

    notes = notesEdit;
    notesSaveState = "success";
    setTimeout(() => { if (notesSaveState === "success") notesSaveState = "idle"; }, 2500);
  }

  async function addDrone() {
    if (!selectedPath || !isPywebviewReady()) return;
    droneBusy = true; droneError = "";
    const resp = await callBridge("drone_add", selectedPath, {
      drone_link: newDroneLink, subfolder_name: newDroneSubfolder, owner: newDroneOwner,
    });
    droneBusy = false;
    if (!resp.ok) { droneError = resp.error.message; return; }
    newDroneLink = ""; newDroneSubfolder = ""; newDroneOwner = "";
    await refreshDetail();
  }

  function startEditDrone(index: number, t: DroneTicket) {
    droneEditIndex = index;
    droneEditLink = t.drone_link;
    droneEditSubfolder = t.subfolder_name || "";
    droneEditOwner = t.owner;
  }

  function cancelEditDrone() { droneEditIndex = -1; }

  async function saveDrone() {
    if (!selectedPath || droneEditIndex < 0 || !isPywebviewReady()) return;
    droneBusy = true; droneError = "";
    const resp = await callBridge("drone_update", selectedPath, droneEditIndex, {
      drone_link: droneEditLink, subfolder_name: droneEditSubfolder, owner: droneEditOwner,
    });
    droneBusy = false;
    if (!resp.ok) { droneError = resp.error.message; return; }
    droneEditIndex = -1;
    await refreshDetail();
  }

  async function deleteDrone(index: number) {
    if (!selectedPath || !isPywebviewReady()) return;
    droneBusy = true; droneError = "";
    const resp = await callBridge("drone_delete", selectedPath, index);
    droneBusy = false;
    if (!resp.ok) { droneError = resp.error.message; return; }
    await refreshDetail();
  }

  async function saveDroneState(index: number) {
    if (!selectedPath || !isPywebviewReady() || !detail) return;
    const newState = droneStateEdits[index];
    if (!newState || newState === detail.drone_tickets[index]?.drone_state) return;
    droneStateBusy = index;
    droneStateError = { ...droneStateError, [index]: "" };
    const resp = await callBridge("drone_update", selectedPath, index, { drone_state: newState });
    droneStateBusy = -1;
    if (!resp.ok) {
      droneStateError = { ...droneStateError, [index]: resp.error.message };
      return;
    }
    droneStateError = { ...droneStateError, [index]: "" };
    await refreshDetail();
  }

  async function refreshDetail() {
    if (!selectedPath) return;
    const [dResp, ntResp] = await Promise.all([
      callBridge<ProjectDetail>("project_get", selectedPath),
      callBridge<string>("notes_get", selectedPath),
    ]);
    if (dResp.ok && dResp.data) { detail = dResp.data; syncDroneStateEdits(); }
    if (ntResp.ok) { notes = ntResp.data ?? ""; notesEdit = notes; }
  }

  function syncDroneStateEdits() {
    if (!detail) return;
    const edits: Record<number, string> = {};
    detail.drone_tickets.forEach((t, i) => { edits[i] = t.drone_state; });
    droneStateEdits = edits;
  }

  async function init() {
    if (isPywebviewReady()) {
      const yr = await callBridge<string[]>("year_list");
      if (yr.ok && yr.data && yr.data.length > 0) yearOptions = yr.data;
    }
    await loadProjects();
  }

  onMount(init);

  function handleYearChange(y: string) {
    yearFilter = y;
    detailState = "idle";
    detail = null;
    subprojects = [];
    files = [];
    notes = "";
    selectedPath = "";
    loadProjects();
  }

  export function refresh() { loadProjects(); }
</script>

<div class="pd-screen">
  <!-- Toolbar -->
  <div class="pd-toolbar">
    <div class="pd-toolbar-left">
      <select class="header-combo" value={yearFilter} onchange={(e) => handleYearChange((e.target as HTMLSelectElement).value)}>
        <option value="all">All Years</option>
        {#each yearOptions as y}
          <option value={y}>{y}</option>
        {/each}
      </select>
      <div class="header-search">
        <span class="search-icon">⌕</span>
        <input class="header-input" placeholder="Filter projects…" bind:value={searchText} />
      </div>
    </div>
    <span class="project-count">{filtered.length} project(s)</span>
  </div>

  <!-- Body: list + detail -->
  <div class="pd-body">
    <!-- Left: project list -->
    <div class="pd-list-panel">
      {#if listState === "loading"}
        <div class="dashboard-banner banner-loading"><span class="banner-icon">◌</span><span>Loading…</span></div>
      {:else if listState === "error"}
        <div class="dashboard-banner banner-error"><span class="banner-icon">⚠</span><div><p class="banner-title">Failed</p><p class="banner-detail">{errorCode}: {errorMessage}</p></div></div>
      {:else if filtered.length === 0}
        <div class="table-empty"><p class="empty-title">No projects</p><p class="empty-sub">No projects found for selected year or filter.</p></div>
      {:else}
        {#each filtered as p}
          <button class="pd-row" class:selected={selectedPath === p.project_path} onclick={() => selectProject(p.project_path)}>
            <span class="pd-row-name">{p.project_name}</span>
            <span class="state-combo-inline">{p.project_state}</span>
          </button>
        {/each}
      {/if}
    </div>

    <!-- Right: detail panel -->
    <div class="pd-detail-panel">
      {#if !selectedPath}
        <div class="table-empty"><p class="empty-title">Select a project</p><p class="empty-sub">Click a project from the list to view details.</p></div>
      {:else if detailState === "loading"}
        <div class="dashboard-banner banner-loading"><span class="banner-icon">◌</span><span>Loading details…</span></div>
      {:else if detailState === "error"}
        <div class="dashboard-banner banner-error"><span class="banner-icon">⚠</span><div><p class="banner-title">Detail load failed</p><p class="banner-detail">{errorCode}: {errorMessage}</p></div></div>
      {:else if detail}
        <div class="pd-detail-card">
          <div class="pd-detail-head">
            <span class="pd-detail-accent"></span>
            <div style="flex:1;min-width:0;">
              <h3 class="pd-detail-name">{detail.project_name}</h3>
              <p class="pd-detail-path">{detail.project_path}</p>
            </div>
            <span class="state-combo">{detail.project_state}</span>
          </div>
          <dl class="pd-detail-grid">
            <div class="pd-dl-item"><dt>CR Number</dt><dd>{detail.cr_number || "—"}</dd></div>
            <div class="pd-dl-item">
              <dt>CR State</dt>
              <dd>
                <div class="cr-state-row">
                  <select class="cr-state-select" bind:value={crStateEdit} disabled={crStateSaveState === "saving"}>
                    {#each CR_STATE_OPTIONS as opt}
                      <option value={opt}>{opt}</option>
                    {/each}
                  </select>
                  <button class="cr-link-save-btn" onclick={saveCrState} disabled={crStateSaveState === "saving" || crStateEdit === detail.cr_state}>
                    {#if crStateSaveState === "saving"}⏳{:else}Save{/if}
                  </button>
                </div>
                {#if crStateSaveState === "success"}
                  <span class="cr-link-feedback cr-link-ok">✓ Saved</span>
                {:else if crStateSaveState === "error"}
                  <span class="cr-link-feedback cr-link-err">✗ {crStateSaveError}</span>
                {/if}
              </dd>
            </div>
            <div class="pd-dl-item pd-dl-wide">
              <dt>CR Link</dt>
              <dd>
                <div class="cr-link-row">
                  <input class="cr-link-input" type="url" placeholder="https://cr.example.com/CR..." bind:value={crLinkEdit} disabled={crLinkSaveState === "saving"} />
                  <button class="cr-link-save-btn" onclick={saveCrLink} disabled={crLinkSaveState === "saving" || crLinkEdit === detail.cr_link}>
                    {#if crLinkSaveState === "saving"}⏳{:else}Save{/if}
                  </button>
                </div>
                {#if crLinkSaveState === "success"}
                  <span class="cr-link-feedback cr-link-ok">✓ Saved</span>
                {:else if crLinkSaveState === "error"}
                  <span class="cr-link-feedback cr-link-err">✗ {crLinkSaveError}</span>
                {/if}
              </dd>
            </div>
            <div class="pd-dl-item"><dt>Start</dt><dd>{detail.start_datetime ? new Date(detail.start_datetime).toLocaleString("en-GB") : "—"}</dd></div>
            <div class="pd-dl-item"><dt>End</dt><dd>{detail.end_datetime ? new Date(detail.end_datetime).toLocaleString("en-GB") : "—"}</dd></div>
            <div class="pd-dl-item"><dt>T-10</dt><dd>{detail.t10_status}</dd></div>
            <div class="pd-dl-item"><dt>Drone Tickets</dt><dd>{detail.drone_ticket_count}</dd></div>
          </dl>

          <div class="pd-section">
            <h4 class="pd-section-title">Drone Tickets</h4>
            {#if droneError}
              <p class="cr-link-feedback cr-link-err">✗ {droneError}</p>
            {/if}
            {#if detail.drone_tickets.length === 0}
              <p class="muted-text">No drone tickets.</p>
            {:else}
              <div class="pd-drone-list">
                {#each detail.drone_tickets as t, i}
                  {#if droneEditIndex === i}
                    <div class="pd-drone-edit-row">
                      <input class="pd-drone-input" placeholder="Drone link" bind:value={droneEditLink} />
                      <input class="pd-drone-input pd-drone-sm" placeholder="Subfolder" bind:value={droneEditSubfolder} />
                      <input class="pd-drone-input pd-drone-sm" placeholder="Owner" bind:value={droneEditOwner} />
                      <button class="cr-link-save-btn" onclick={saveDrone} disabled={droneBusy}>Save</button>
                      <button class="pd-drone-cancel-btn" onclick={cancelEditDrone}>Cancel</button>
                    </div>
                  {:else}
                    <div class="pd-drone-row">
                      <span class="pd-drone-link">{t.drone_link || "—"}</span>
                      <span class="pd-drone-owner">{t.owner || "—"}</span>
                      <select class="pd-drone-state-select" value={droneStateEdits[i] ?? t.drone_state} onchange={(e) => { droneStateEdits = { ...droneStateEdits, [i]: (e.target as HTMLSelectElement).value }; }} disabled={droneStateBusy === i}>
                        {#each DRONE_STATE_OPTIONS as opt}
                          <option value={opt}>{opt}</option>
                        {/each}
                      </select>
                      <button class="pd-drone-action-btn pd-drone-state-btn" onclick={() => saveDroneState(i)} disabled={droneStateBusy === i || (droneStateEdits[i] ?? t.drone_state) === t.drone_state}>
                        {#if droneStateBusy === i}…{:else}Save State{/if}
                      </button>
                      <button class="pd-drone-action-btn" onclick={() => startEditDrone(i, t)} disabled={droneBusy}>Edit</button>
                      <button class="pd-drone-action-btn pd-drone-del" onclick={() => deleteDrone(i)} disabled={droneBusy}>Del</button>
                    </div>
                    {#if droneStateError[i]}
                      <p class="cr-link-feedback cr-link-err pd-drone-state-err">✗ {droneStateError[i]}</p>
                    {/if}
                  {/if}
                {/each}
              </div>
            {/if}
            <div class="pd-drone-add-row">
              <input class="pd-drone-input" placeholder="Drone link" bind:value={newDroneLink} />
              <input class="pd-drone-input pd-drone-sm" placeholder="Subfolder" bind:value={newDroneSubfolder} />
              <input class="pd-drone-input pd-drone-sm" placeholder="Owner" bind:value={newDroneOwner} />
              <button class="cr-link-save-btn" onclick={addDrone} disabled={droneBusy || !newDroneLink.trim()}>Add</button>
            </div>
          </div>

          <div class="pd-section">
            <h4 class="pd-section-title">Subprojects <span class="pd-deferred-hint">(add/delete deferred)</span></h4>
            {#if subprojects.length === 0}
              <p class="muted-text">No subprojects.</p>
            {:else}
              <ul class="pd-simple-list">
                {#each subprojects as sp}
                  <li>{sp}</li>
                {/each}
              </ul>
            {/if}
          </div>

          <div class="pd-section">
            <h4 class="pd-section-title">Files <span class="pd-deferred-hint">(open/write deferred)</span></h4>
            {#if files.length === 0}
              <p class="muted-text">No files.</p>
            {:else}
              <ul class="pd-simple-list">
                {#each files as f}
                  <li><span class="pd-file-name">{f.name}</span> <span class="pd-file-path">{f.path}</span></li>
                {/each}
              </ul>
            {/if}
          </div>

          <div class="pd-section">
            <h4 class="pd-section-title">Notes</h4>
            <div class="pd-notes-edit">
              <textarea
                class="pd-notes-textarea"
                placeholder="Write project notes (saved to notes.md)…"
                bind:value={notesEdit}
                disabled={notesSaveState === "saving"}
                rows="6"
              ></textarea>
              <div class="pd-notes-actions">
                <button class="cr-link-save-btn" onclick={saveNotes} disabled={notesSaveState === "saving" || notesEdit === notes}>
                  {#if notesSaveState === "saving"}⏳ Saving…{:else}Save Notes{/if}
                </button>
                {#if notesSaveState === "success"}
                  <span class="cr-link-feedback cr-link-ok">✓ Saved</span>
                {:else if notesSaveState === "error"}
                  <span class="cr-link-feedback cr-link-err">✗ {notesSaveError}</span>
                {/if}
              </div>
            </div>
          </div>
        </div>
      {/if}

      <!-- Deferred bar -->
      {#if selectedPath}
        <div class="pd-deferred-bar">
          <span>⚠ Mutations deferred — add/edit/delete, CR/Drone state change, folder move, rename. Landing in Phase E.</span>
        </div>
      {/if}
    </div>
  </div>
</div>

<style>
  .pd-screen { flex:1; min-height:0; display:flex; flex-direction:column; padding:14px; gap:10px; overflow:hidden; }
  .pd-toolbar { display:flex; align-items:center; justify-content:space-between; gap:8px; flex:0 0 auto; background:var(--color-workspace-panel); border:1px solid #D7DCE2; border-radius:8px; padding:10px 12px; box-shadow:0 4px 15px rgba(0,0,0,0.30); }
  .pd-toolbar-left { display:flex; align-items:center; gap:7px; }
  .pd-body { flex:1; min-height:0; display:grid; grid-template-columns:260px 1fr; gap:10px; }
  @media (max-width:900px) { .pd-body { grid-template-columns:1fr; } }
  .pd-list-panel { background:#fff; border:1px solid #D7DCE2; border-radius:8px; box-shadow:var(--shadow-card); overflow-y:auto; display:flex; flex-direction:column; gap:2px; padding:6px; }
  .pd-row { display:flex; align-items:center; justify-content:space-between; gap:6px; padding:8px 10px; border:0; border-left:3px solid transparent; border-radius:5px; background:transparent; cursor:pointer; text-align:left; font-size:11px; font-weight:750; color:var(--color-ink); transition:background 0.12s; width:100%; }
  .pd-row:hover { background:var(--color-workspace-panel); }
  .pd-row.selected { background:var(--color-soft-pink-surface); border-left-color:var(--color-dbs-red); font-weight:900; }
  .pd-row-name { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; flex:1; min-width:0; }
  .state-combo-inline { display:inline-flex; align-items:center; height:20px; border-radius:4px; background:var(--color-dbs-red); color:#fff; font-size:9px; font-weight:900; padding:0 6px; white-space:nowrap; flex:0 0 auto; }
  .pd-detail-panel { display:flex; flex-direction:column; gap:8px; min-height:0; overflow-y:auto; }
  .pd-detail-card { background:#fff; border:1px solid #E5E7EB; border-radius:8px; box-shadow:var(--shadow-subtle); padding:14px; display:flex; flex-direction:column; gap:12px; flex:0 0 auto; }
  .pd-detail-head { display:flex; align-items:center; gap:10px; }
  .pd-detail-accent { width:4px; min-width:4px; height:28px; border-radius:2px; background:var(--color-dbs-red); }
  .pd-detail-name { margin:0; font-size:15px; font-weight:900; color:var(--color-ink); }
  .pd-detail-path { margin:2px 0 0; font-size:10px; color:var(--color-muted); font-weight:650; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .pd-detail-grid { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin:0; }
  @media (max-width:700px) { .pd-detail-grid { grid-template-columns:1fr; } }
  .pd-dl-item { display:flex; flex-direction:column; gap:2px; }
  .pd-dl-item dt { font-size:9px; font-weight:800; color:var(--color-muted); text-transform:uppercase; letter-spacing:0.3px; }
  .pd-dl-item dd { margin:0; font-size:12px; font-weight:850; color:var(--color-ink); }
  .pd-section { border-top:1px solid #E5E7EB; padding-top:10px; }
  .pd-section-title { margin:0 0 6px; font-size:11px; font-weight:900; color:var(--color-ink); display:flex; align-items:center; gap:6px; }
  .pd-deferred-hint { font-size:9px; font-weight:800; color:var(--color-muted-light); font-style:italic; }
  .pd-simple-list { margin:0; padding:0 0 0 16px; font-size:11px; font-weight:750; color:var(--color-ink); line-height:1.55; }
  .pd-file-name { font-weight:800; }
  .pd-file-path { color:var(--color-muted); font-size:9px; margin-left:4px; }
  .pd-notes-edit { display:flex; flex-direction:column; gap:6px; }
  .pd-notes-textarea { width:100%; min-height:100px; max-height:240px; padding:10px; background:var(--color-workspace-panel); border:1px solid #D7DCE2; border-radius:6px; font-size:10px; font-family:"JetBrains Mono","Fira Code",monospace; color:var(--color-ink); resize:vertical; outline:none; }
  .pd-notes-textarea:focus { border-color:var(--color-dbs-red); }
  .pd-notes-textarea:disabled { background:#f3f4f6; color:var(--color-muted); }
  .pd-notes-actions { display:flex; align-items:center; gap:8px; }
  .pd-drone-list { display:flex; flex-direction:column; gap:5px; margin-bottom:8px; }
  .pd-drone-row, .pd-drone-edit-row, .pd-drone-add-row { display:flex; align-items:center; gap:6px; flex-wrap:wrap; }
  .pd-drone-add-row { border-top:1px dashed #E5E7EB; padding-top:8px; }
  .pd-drone-link { flex:1; min-width:120px; font-size:10px; font-weight:800; color:var(--color-ink); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .pd-drone-owner { font-size:10px; font-weight:700; color:var(--color-muted); min-width:50px; }
  .pd-drone-state-select { padding:3px 6px; font-size:9px; font-weight:800; border:1px solid #D7DCE2; border-radius:5px; background:#fff; color:var(--color-ink); outline:none; cursor:pointer; flex:0 0 auto; }
  .pd-drone-state-select:focus { border-color:var(--color-dbs-red); }
  .pd-drone-state-select:disabled { background:var(--color-workspace-panel); color:var(--color-muted); cursor:not-allowed; }
  .pd-drone-state-btn { border-color:var(--color-dbs-red); color:var(--color-dbs-red); }
  .pd-drone-state-err { width:100%; margin-top:0; }
  .pd-drone-input { padding:4px 7px; font-size:10px; font-weight:700; border:1px solid #D7DCE2; border-radius:5px; background:#fff; color:var(--color-ink); outline:none; flex:1; min-width:90px; }
  .pd-drone-input.pd-drone-sm { flex:0 0 90px; min-width:70px; }
  .pd-drone-input:focus { border-color:var(--color-dbs-red); }
  .pd-drone-action-btn { padding:3px 9px; font-size:9px; font-weight:800; border:1px solid #D7DCE2; border-radius:5px; background:#fff; color:var(--color-ink); cursor:pointer; white-space:nowrap; }
  .pd-drone-action-btn:hover:not(:disabled) { border-color:var(--color-dbs-red); color:var(--color-dbs-red); }
  .pd-drone-action-btn:disabled { opacity:0.45; cursor:not-allowed; }
  .pd-drone-del:hover:not(:disabled) { border-color:#DC2626; color:#DC2626; }
  .pd-drone-cancel-btn { padding:5px 10px; font-size:10px; font-weight:800; border:1px solid #D7DCE2; border-radius:5px; background:#fff; color:var(--color-muted); cursor:pointer; }
  .pd-deferred-bar { background:var(--color-soft-pink-surface); border:1px solid var(--color-soft-pink-border); border-radius:6px; padding:8px 12px; font-size:10px; font-weight:750; color:var(--color-dbs-red); flex:0 0 auto; }
  .pd-dl-wide { grid-column: 1 / -1; }
  .cr-link-row { display:flex; gap:6px; align-items:center; }
  .cr-link-input { flex:1; min-width:0; padding:5px 8px; font-size:11px; font-weight:700; border:1px solid #D7DCE2; border-radius:5px; background:#fff; color:var(--color-ink); outline:none; }
  .cr-link-input:focus { border-color:var(--color-dbs-red); }
  .cr-link-input:disabled { background:var(--color-workspace-panel); color:var(--color-muted); }
  .cr-link-save-btn { padding:5px 12px; font-size:10px; font-weight:800; border:1px solid var(--color-dbs-red); border-radius:5px; background:var(--color-dbs-red); color:#fff; cursor:pointer; white-space:nowrap; transition:opacity 0.12s; }
  .cr-link-save-btn:hover:not(:disabled) { background:var(--color-dbs-red-hover, #991B1B); }
  .cr-link-save-btn:disabled { opacity:0.45; cursor:not-allowed; }
  .cr-link-feedback { display:inline-block; margin-top:4px; font-size:10px; font-weight:800; }
  .cr-link-ok { color:var(--color-dbs-red); }
  .cr-link-err { color:#DC2626; }
  .cr-state-row { display:flex; gap:6px; align-items:center; }
  .cr-state-select { padding:4px 8px; font-size:11px; font-weight:750; border:1px solid #D7DCE2; border-radius:5px; background:#fff; color:var(--color-ink); outline:none; cursor:pointer; }
  .cr-state-select:focus { border-color:var(--color-dbs-red); }
  .cr-state-select:disabled { background:var(--color-workspace-panel); color:var(--color-muted); cursor:not-allowed; }
</style>
