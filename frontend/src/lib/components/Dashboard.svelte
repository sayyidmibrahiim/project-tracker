<script lang="ts">
  import { callBridge, isPywebviewReady } from "../bridge";
  import type { DashboardProject, DashboardSummary, DashboardRowDrone } from "../types";
  import { BridgeErrorCode } from "../types";
  import ConfirmModal from "./ConfirmModal.svelte";
  import DashboardRowMenu from "./DashboardRowMenu.svelte";

  // ── Props from parent ──
  let {
    selectedYear,
    searchQuery,
    refreshToken = 0,
    onOpenProjectDetails,
  }: {
    selectedYear: string;
    searchQuery: string;
    refreshToken?: number;
    onOpenProjectDetails?: (path: string) => void;
    [key: string]: unknown;
  } = $props();

  type LoadState = "idle" | "loading" | "error" | "loaded";
  let loadState: LoadState = $state("idle");
  let errorMessage: string = $state("");
  let errorCode: string = $state("");
  let activeStatus: string = $state("all");

  let projects: DashboardProject[] = $state([]);
  let summary: DashboardSummary | null = $state(null);

  // Inline-edit transient state
  let savingKey: string = $state("");
  let actionError: string = $state("");
  type PendingState = { kind: "cr" | "drone"; path: string; index: number; next: string; name: string };
  let pendingState: PendingState | null = $state(null);

  const CR_STATE_OPTIONS = ["PENDING SUBMISSION", "PENDING APPROVAL", "APPROVED", "IN-PROGRESS", "FINISHED", "POSTPONED", "CANCELED"];
  const DRONE_STATE_OPTIONS = ["UAT", "PENDING APPROVAL", "APPROVED", "IN-PROGRESS", "FINISHED", "CANCELED"];
  const DESTRUCTIVE = new Set(["POSTPONED", "CANCELED"]);

  // ── Status filter tabs (counts from real summary) ──
  interface StatusTab { key: string; label: string; count: number }
  let statuses: StatusTab[] = $derived.by(() => {
    const by = summary?.by_project_state ?? {};
    return [
      { key: "all", label: "All", count: summary?.total_projects ?? projects.length },
      { key: "UAT_PREPARE", label: "UAT Prepare", count: by["UAT_PREPARE"] ?? 0 },
      { key: "PROD_READY", label: "Prod Ready", count: by["PROD_READY"] ?? 0 },
      { key: "IMPLEMENTED", label: "Implemented", count: by["IMPLEMENTED"] ?? 0 },
      { key: "POSTPONED", label: "Postponed", count: by["POSTPONED"] ?? 0 },
      { key: "CANCELED", label: "Canceled", count: by["CANCELED"] ?? 0 },
    ];
  });

  const columns = ["No", "Main Project", "Sub Project", "Start Datetime", "End Datetime", "Drone Ticket", "Drone State", "CR Number", "CR State", ""];

  // ── Filter: status tab + search ──
  let filteredProjects: DashboardProject[] = $derived.by(() => {
    let result = activeStatus === "all" ? projects : projects.filter((p) => p.project_state === activeStatus);
    const q = searchQuery.trim().toLowerCase();
    if (q) {
      result = result.filter((p) => {
        const drones = p.drone_tickets ?? [];
        const haystack = [
          p.project_name, p.cr_number, p.cr_state, p.project_state, p.year, p.project_path,
          ...drones.map((d) => `${d.subfolder_name ?? ""} ${d.drone_ticket} ${d.drone_link} ${d.drone_state} ${d.owner}`),
        ].join(" ").toLowerCase();
        return haystack.includes(q);
      });
    }
    return result;
  });

  function subprojectsOf(p: DashboardProject): string[] {
    const names = (p.drone_tickets ?? [])
      .map((d) => d.subfolder_name)
      .filter((n): n is string => !!n && n.trim().length > 0);
    return Array.from(new Set(names));
  }

  function fmtDate(iso: string | null, which: "date" | "time"): string {
    if (!iso) return "—";
    const d = new Date(iso);
    if (isNaN(d.getTime())) return "—";
    return which === "date"
      ? d.toLocaleDateString("en-GB", { weekday: "short", day: "2-digit", month: "short", year: "numeric" })
      : d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
  }

  function joinPath(base: string, child: string): string {
    const sep = base.includes("\\") ? "\\" : "/";
    return base.endsWith(sep) ? base + child : base + sep + child;
  }

  // ── Load ──
  async function loadDashboard() {
    loadState = "loading";
    errorMessage = ""; errorCode = ""; actionError = "";
    if (!isPywebviewReady()) {
      errorCode = BridgeErrorCode.BRIDGE_UNAVAILABLE;
      errorMessage = "pywebview bridge is not available. Running outside desktop shell.";
      loadState = "error";
      return;
    }
    const yearParam = selectedYear === "all" ? undefined : selectedYear;
    const response = await callBridge<{ projects: DashboardProject[]; summary: DashboardSummary }>("dashboard_data", yearParam);
    if (!response.ok) {
      errorCode = response.error.code;
      errorMessage = response.error.message;
      loadState = "error";
      return;
    }
    projects = response.data?.projects ?? [];
    summary = response.data?.summary ?? null;
    loadState = "loaded";
  }

  // Re-fetch on year or refresh-token change.
  $effect(() => {
    void selectedYear;
    void refreshToken;
    loadDashboard();
  });

  // ── Inline edits ──
  async function saveCrLink(p: DashboardProject, value: string) {
    if (value === p.cr_link) return;
    savingKey = `${p.project_path}:crlink`;
    actionError = "";
    const r = await callBridge("cr_update_link", p.project_path, value);
    savingKey = "";
    if (!r.ok) { actionError = r.error.message; }
    await loadDashboard();
  }

  async function saveDroneLink(p: DashboardProject, index: number, value: string) {
    if (value === (p.drone_tickets?.[index]?.drone_link ?? "")) return;
    savingKey = `${p.project_path}:dronelink:${index}`;
    actionError = "";
    const r = await callBridge("drone_update", p.project_path, index, { drone_link: value });
    savingKey = "";
    if (!r.ok) { actionError = r.error.message; }
    await loadDashboard();
  }

  function onCrStateChange(p: DashboardProject, next: string) {
    if (next === p.cr_state) return;
    if (DESTRUCTIVE.has(next)) {
      pendingState = { kind: "cr", path: p.project_path, index: -1, next, name: p.project_name };
      return;
    }
    void applyCrState(p.project_path, next);
  }
  async function applyCrState(path: string, next: string) {
    savingKey = `${path}:crstate`;
    actionError = "";
    const r = await callBridge("cr_update_state", path, next);
    savingKey = "";
    if (!r.ok) actionError = r.error.message;
    await loadDashboard();
  }

  function onDroneStateChange(p: DashboardProject, index: number, next: string) {
    if (next === (p.drone_tickets?.[index]?.drone_state ?? "")) return;
    if (DESTRUCTIVE.has(next)) {
      pendingState = { kind: "drone", path: p.project_path, index, next, name: `${p.project_name} · drone ${index + 1}` };
      return;
    }
    void applyDroneState(p.project_path, index, next);
  }
  async function applyDroneState(path: string, index: number, next: string) {
    savingKey = `${path}:dronestate:${index}`;
    actionError = "";
    const r = await callBridge("drone_update", path, index, { drone_state: next });
    savingKey = "";
    if (!r.ok) actionError = r.error.message;
    await loadDashboard();
  }

  async function confirmPendingState() {
    const ps = pendingState;
    pendingState = null;
    if (!ps) return;
    if (ps.kind === "cr") await applyCrState(ps.path, ps.next);
    else await applyDroneState(ps.path, ps.index, ps.next);
  }
  async function cancelPendingState() {
    pendingState = null;
    await loadDashboard(); // reset any select that visually changed
  }

  async function openFolder(path: string) {
    actionError = "";
    if (!isPywebviewReady()) { actionError = "Open Folder requires the desktop app."; return; }
    const r = await callBridge("project_open_folder", path);
    if (!r.ok) actionError = r.error.message;
  }
  async function openSubfolder(path: string, sub: string) {
    actionError = "";
    if (!isPywebviewReady()) { actionError = "Open Folder requires the desktop app."; return; }
    const r = await callBridge("folder_open", joinPath(path, sub));
    if (!r.ok) actionError = r.error.message;
  }

  function onInputKey(event: KeyboardEvent) {
    if (event.key === "Enter") (event.currentTarget as HTMLInputElement).blur();
  }
</script>

<div class="dashboard-screen">
  {#if loadState === "error"}
    <div class="dashboard-banner banner-error">
      <span class="banner-icon">⚠</span>
      <div>
        <p class="banner-title">Dashboard unavailable</p>
        <p class="banner-detail">{errorCode}: {errorMessage}</p>
      </div>
    </div>
  {/if}

  {#if loadState === "loaded" || loadState === "loading"}
    <!-- Status filter bar -->
    <div class="filter-frame">
      <div class="status-inner">
        {#each statuses as s}
          <button class="status-tab" class:active={activeStatus === s.key} onclick={() => (activeStatus = s.key)}>
            {s.label} ({s.count})
          </button>
        {/each}
        <span class="project-count">{filteredProjects.length} project(s)</span>
      </div>
    </div>
  {/if}

  {#if actionError}
    <div class="dash-action-error" role="alert">⚠ {actionError}</div>
  {/if}

  <!-- Table card -->
  <div class="table-card">
    <div class="table-card-head">
      <span class="table-head-icon">▦</span>
      <span>CR - Project Summary Table</span>
    </div>
    <div class="table-scroll">
      <div class="project-table">
        <div class="table-header-row">
          {#each columns as col}
            <div class="table-header-cell">{col}</div>
          {/each}
        </div>

        {#if loadState === "loading"}
          <div class="table-empty"><p class="empty-title">Loading…</p><p class="empty-sub">Fetching project data from backend.</p></div>
        {:else if loadState === "error"}
          <div class="table-empty"><p class="empty-title">No data</p><p class="empty-sub">Backend returned: {errorMessage}</p></div>
        {:else if loadState === "idle"}
          <div class="table-empty"><p class="empty-title">Initializing…</p></div>
        {:else if filteredProjects.length === 0}
          <div class="table-empty"><p class="empty-title">No projects found</p><p class="empty-sub">Add a project or adjust filters to see results.</p></div>
        {:else}
          {#each filteredProjects as p, idx}
            {@const drones = (p.drone_tickets ?? [])}
            {@const subs = subprojectsOf(p)}
            <div class="project-row" class:alt={idx % 2 === 1}>
              <div class="table-cell cell-center"><strong>{idx + 1}</strong></div>

              <!-- Main Project (click → open folder) -->
              <div class="table-cell cell-top">
                <div>
                  <button class="dash-name-btn" type="button" title="Open project folder" onclick={() => openFolder(p.project_path)}>{p.project_name || "Untitled"}</button>
                  <div class="project-folder">project folder · {p.year || "—"}</div>
                </div>
              </div>

              <!-- Sub Project (click → open subfolder) -->
              <div class="table-cell">
                <div class="stack-lines">
                  {#if subs.length === 0}
                    <div class="stack-line"><span class="muted-text">—</span></div>
                  {:else}
                    {#each subs as sp}
                      <div class="stack-line"><button class="dash-sub-btn" type="button" title="Open sub-project folder" onclick={() => openSubfolder(p.project_path, sp)}>{sp}</button></div>
                    {/each}
                  {/if}
                </div>
              </div>

              <!-- Start / End -->
              <div class="table-cell cell-center">
                {#if p.start_datetime}<div class="date-block">{fmtDate(p.start_datetime, "date")}<br /><span class="date-time">{fmtDate(p.start_datetime, "time")}</span></div>{:else}<span class="muted-text">—</span>{/if}
              </div>
              <div class="table-cell cell-center">
                {#if p.end_datetime}<div class="date-block">{fmtDate(p.end_datetime, "date")}<br /><span class="date-time">{fmtDate(p.end_datetime, "time")}</span></div>{:else}<span class="muted-text">—</span>{/if}
              </div>

              <!-- Drone Ticket (inline paste + open link) -->
              <div class="table-cell">
                <div class="stack-lines">
                  {#if drones.length === 0}
                    <div class="stack-line"><span class="muted-text">—</span></div>
                  {:else}
                    {#each drones as d, di}
                      <div class="stack-line dash-link-cell">
                        <input
                          class="link-edit"
                          value={d.drone_link}
                          placeholder="Paste drone URL…"
                          title={d.drone_ticket || d.drone_link}
                          onkeydown={onInputKey}
                          onblur={(e) => saveDroneLink(p, di, (e.currentTarget as HTMLInputElement).value)}
                          disabled={savingKey === `${p.project_path}:dronelink:${di}`}
                        />
                        {#if d.drone_link}<a class="dash-open" href={d.drone_link} target="_blank" rel="noopener noreferrer" title="Open in browser">↗</a>{/if}
                      </div>
                    {/each}
                  {/if}
                </div>
              </div>

              <!-- Drone State (inline dropdown + guard) -->
              <div class="table-cell">
                <div class="stack-lines">
                  {#if drones.length === 0}
                    <div class="stack-line"><span class="muted-text">—</span></div>
                  {:else}
                    {#each drones as d, di}
                      <div class="stack-line">
                        <select class="dash-state-select" value={d.drone_state} onchange={(e) => onDroneStateChange(p, di, (e.currentTarget as HTMLSelectElement).value)} disabled={savingKey === `${p.project_path}:dronestate:${di}`}>
                          {#each DRONE_STATE_OPTIONS as opt}<option value={opt} disabled={opt === "IN-PROGRESS"}>{opt}</option>{/each}
                          {#if !DRONE_STATE_OPTIONS.includes(d.drone_state) && d.drone_state}<option value={d.drone_state}>{d.drone_state}</option>{/if}
                        </select>
                      </div>
                    {/each}
                  {/if}
                </div>
              </div>

              <!-- CR Number (inline paste + open link) -->
              <div class="table-cell">
                <div class="dash-link-cell">
                  <input
                    class="link-edit"
                    value={p.cr_link}
                    placeholder="Paste CR URL…"
                    title={p.cr_number || p.cr_link}
                    onkeydown={onInputKey}
                    onblur={(e) => saveCrLink(p, (e.currentTarget as HTMLInputElement).value)}
                    disabled={savingKey === `${p.project_path}:crlink`}
                  />
                  {#if p.cr_link}<a class="dash-open" href={p.cr_link} target="_blank" rel="noopener noreferrer" title="Open in browser">↗</a>{/if}
                </div>
              </div>

              <!-- CR State (inline dropdown + guard + confirm) -->
              <div class="table-cell">
                <select class="dash-state-select" value={p.cr_state} onchange={(e) => onCrStateChange(p, (e.currentTarget as HTMLSelectElement).value)} disabled={savingKey === `${p.project_path}:crstate`}>
                  {#each CR_STATE_OPTIONS as opt}<option value={opt} disabled={opt === "IN-PROGRESS"}>{opt}</option>{/each}
                  {#if !CR_STATE_OPTIONS.includes(p.cr_state) && p.cr_state}<option value={p.cr_state}>{p.cr_state}</option>{/if}
                </select>
              </div>

              <!-- Actions -->
              <div class="table-cell cell-center">
                <DashboardRowMenu
                  projectPath={p.project_path}
                  projectState={p.project_state}
                  projectName={p.project_name}
                  onOpenDetails={(path) => onOpenProjectDetails?.(path)}
                  onChanged={() => loadDashboard()}
                />
              </div>
            </div>
          {/each}
        {/if}
      </div>
    </div>
  </div>
</div>

{#if pendingState}
  <ConfirmModal
    title={pendingState.next === "CANCELED" ? "Mark as Canceled?" : "Postpone project?"}
    actionLabel={pendingState.next === "CANCELED" ? "Set Canceled" : "Set Postponed"}
    targetName={`${pendingState.name} → ${pendingState.next}`}
    reversible={false}
    onConfirm={confirmPendingState}
    onCancel={cancelPendingState}
  />
{/if}

<style>
  .dash-action-error { background:var(--color-soft-pink-surface); border:1px solid var(--color-soft-pink-border); color:var(--color-dbs-red); border-radius:6px; padding:7px 12px; font-size:11px; font-weight:800; flex:0 0 auto; }
  .dash-name-btn { border:0; background:transparent; padding:0; font-size:13px; font-weight:900; color:var(--color-dbs-red); cursor:pointer; text-align:left; }
  .dash-name-btn:hover { text-decoration:underline; }
  .dash-sub-btn { border:0; background:transparent; padding:0; font-size:11px; font-weight:800; color:var(--color-ink); cursor:pointer; text-align:left; }
  .dash-sub-btn:hover { color:var(--color-dbs-red); text-decoration:underline; }
  .dash-link-cell { display:flex; align-items:center; gap:5px; width:100%; }
  .dash-link-cell .link-edit { flex:1; min-width:0; }
  .dash-open { flex:0 0 auto; color:var(--color-dbs-red); font-weight:900; text-decoration:none; font-size:12px; padding:0 2px; }
  .dash-open:hover { background:var(--color-soft-pink-surface); border-radius:3px; }
  .dash-state-select { height:28px; border:1px solid var(--color-input-border, #D7DCE2); border-radius:5px; background:#fff; color:var(--color-ink); font-size:10px; font-weight:850; outline:none; padding:0 6px; cursor:pointer; max-width:100%; }
  .dash-state-select:focus { border-color:var(--color-dbs-red); }
  .dash-state-select:disabled { background:var(--color-workspace-panel); color:var(--color-muted); cursor:not-allowed; }
</style>
