<script lang="ts">
  import { callBridge, isPywebviewReady } from "../bridge";
  import type { DashboardProject, DashboardSummary, DashboardRowDrone } from "../types";
  import { BridgeErrorCode } from "../types";
  import { stateChipClass } from "../dashboardChips";
  import ConfirmModal from "./ConfirmModal.svelte";
  import DashboardRowMenu from "./DashboardRowMenu.svelte";

  // ── Props from parent ──
  let {
    selectedYear,
    searchQuery,
    refreshToken = 0,
    onOpenProjectDetails,
    onAddProject,
    onAddYear,
  }: {
    selectedYear: string;
    searchQuery: string;
    refreshToken?: number;
    onOpenProjectDetails?: (path: string) => void;
    onAddProject?: () => void;
    onAddYear?: () => void;
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

  // Split text into highlight segments around the (case-insensitive) search query.
  // Returned as data (rendered with <mark>) — no {@html}, so it stays XSS-safe.
  function hlSegments(text: string): { text: string; hit: boolean }[] {
    const value = text ?? "";
    const q = searchQuery.trim();
    if (!q) return [{ text: value, hit: false }];
    const lower = value.toLowerCase();
    const ql = q.toLowerCase();
    const out: { text: string; hit: boolean }[] = [];
    let i = 0;
    while (i < value.length) {
      const idx = lower.indexOf(ql, i);
      if (idx === -1) {
        out.push({ text: value.slice(i), hit: false });
        break;
      }
      if (idx > i) out.push({ text: value.slice(i, idx), hit: false });
      out.push({ text: value.slice(idx, idx + q.length), hit: true });
      i = idx + q.length;
    }
    return out;
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
        <div class="table-header-row" style="position:sticky;top:0;z-index:2;">
          {#each columns as col}
            <div class="table-header-cell">{col}</div>
          {/each}
        </div>

        {#if loadState === "loading"}
          {#each [0, 1, 2, 3] as i}
            <div class="project-row dash-skel"><div class="table-cell" style="grid-column:1 / -1;"><div class="dash-skel-bar"></div></div></div>
          {/each}
        {:else if loadState === "error"}
          <div class="table-empty"><p class="empty-title">No data</p><p class="empty-sub">Backend returned: {errorMessage}</p></div>
        {:else if loadState === "idle"}
          <div class="table-empty"><p class="empty-title">Initializing…</p></div>
        {:else if filteredProjects.length === 0}
          <div class="table-empty">
            <p class="empty-title">No projects found</p>
            <p class="empty-sub">Add a project or adjust filters to see results.</p>
            <div class="dash-empty-actions">
              {#if onAddYear}<button class="dash-empty-cta secondary" type="button" onclick={() => onAddYear?.()}>＋ Add Year</button>{/if}
              <button class="dash-empty-cta" type="button" onclick={() => onAddProject?.()}>＋ Add Project</button>
            </div>
          </div>
        {:else}
          {#each filteredProjects as p, idx}
            {@const drones = (p.drone_tickets ?? [])}
            {@const subs = subprojectsOf(p)}
            <div class="project-row dash-row" class:alt={idx % 2 === 1}>
              <div class="table-cell cell-center"><strong>{idx + 1}</strong></div>

              <!-- Main Project (click → open folder) -->
              <div class="table-cell cell-top">
                <div class="dash-name-wrap">
                  <button class="dash-name-btn dash-truncate" type="button" title={p.project_name || "Untitled"} onclick={() => openFolder(p.project_path)}>{#each hlSegments(p.project_name || "Untitled") as seg}{#if seg.hit}<mark class="dash-hl">{seg.text}</mark>{:else}{seg.text}{/if}{/each}</button>
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
                      <div class="stack-line"><button class="dash-sub-btn dash-truncate" type="button" title={sp} onclick={() => openSubfolder(p.project_path, sp)}>{sp}</button></div>
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
                        {#if savingKey === `${p.project_path}:dronelink:${di}`}<span class="dash-cell-spin" aria-label="Saving"></span>{/if}
                        {#if d.drone_ticket}<span class="dash-id-label" title={d.drone_ticket}>{d.drone_ticket}</span>{/if}
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
                        <select class="dash-state-select {stateChipClass(d.drone_state)}" value={d.drone_state} onchange={(e) => onDroneStateChange(p, di, (e.currentTarget as HTMLSelectElement).value)} disabled={savingKey === `${p.project_path}:dronestate:${di}`}>
                          {#each DRONE_STATE_OPTIONS as opt}<option value={opt} disabled={opt === "IN-PROGRESS"}>{opt}</option>{/each}
                          {#if !DRONE_STATE_OPTIONS.includes(d.drone_state) && d.drone_state}<option value={d.drone_state}>{d.drone_state}</option>{/if}
                        </select>
                        {#if savingKey === `${p.project_path}:dronestate:${di}`}<span class="dash-cell-spin" aria-label="Saving"></span>{/if}
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
                  {#if savingKey === `${p.project_path}:crlink`}<span class="dash-cell-spin" aria-label="Saving"></span>{/if}
                  {#if p.cr_number}<span class="dash-id-label" title={p.cr_number}>{p.cr_number}</span>{/if}
                  {#if p.cr_link}<a class="dash-open" href={p.cr_link} target="_blank" rel="noopener noreferrer" title="Open in browser">↗</a>{/if}
                </div>
              </div>

              <!-- CR State (inline dropdown + guard + confirm) -->
              <div class="table-cell">
                <div class="dash-link-cell">
                  <select class="dash-state-select {stateChipClass(p.cr_state)}" value={p.cr_state} onchange={(e) => onCrStateChange(p, (e.currentTarget as HTMLSelectElement).value)} disabled={savingKey === `${p.project_path}:crstate`}>
                    {#each CR_STATE_OPTIONS as opt}<option value={opt} disabled={opt === "IN-PROGRESS"}>{opt}</option>{/each}
                    {#if !CR_STATE_OPTIONS.includes(p.cr_state) && p.cr_state}<option value={p.cr_state}>{p.cr_state}</option>{/if}
                  </select>
                  {#if savingKey === `${p.project_path}:crstate`}<span class="dash-cell-spin" aria-label="Saving"></span>{/if}
                </div>
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
  .dash-hl { background:var(--color-soft-pink-surface); color:var(--color-dbs-red); border-radius:2px; padding:0 1px; }
  .dash-sub-btn { border:0; background:transparent; padding:0; font-size:11px; font-weight:800; color:var(--color-ink); cursor:pointer; text-align:left; }
  .dash-sub-btn:hover { color:var(--color-dbs-red); text-decoration:underline; }
  .dash-link-cell { display:flex; align-items:center; gap:5px; width:100%; }
  .dash-link-cell .link-edit { flex:1; min-width:0; }
  .dash-open { flex:0 0 auto; color:var(--color-dbs-red); font-weight:900; text-decoration:none; font-size:12px; padding:0 2px; }
  .dash-open:hover { background:var(--color-soft-pink-surface); border-radius:3px; }
  .dash-state-select { height:28px; border:1px solid var(--color-input-border, #D7DCE2); border-radius:5px; background:#fff; color:var(--color-ink); font-size:10px; font-weight:850; outline:none; padding:0 6px; cursor:pointer; max-width:100%; }
  .dash-state-select:focus { border-color:var(--color-dbs-red); }
  .dash-state-select:disabled { background:var(--color-workspace-panel); color:var(--color-muted); cursor:not-allowed; }
  .dash-row:hover { background:var(--color-soft-pink-surface); }
  .dash-skel-bar { height:14px; border-radius:4px; background:linear-gradient(90deg,#ececec 25%,#f6f6f6 37%,#ececec 63%); background-size:400% 100%; animation:dash-shimmer 1.2s ease infinite; }
  @keyframes dash-shimmer { 0% { background-position:100% 0; } 100% { background-position:-100% 0; } }
  .dash-empty-cta { margin-top:10px; height:30px; padding:0 16px; border:1px solid var(--color-dbs-red); border-radius:5px; background:var(--color-dbs-red); color:#fff; font-size:11px; font-weight:850; cursor:pointer; }
  .dash-empty-cta:hover { background:var(--color-dbs-red-hover); }
  .dash-empty-actions { display:flex; gap:8px; justify-content:center; }
  .dash-empty-cta.secondary { background:#fff; color:var(--color-dbs-red); }
  .dash-empty-cta.secondary:hover { background:var(--color-soft-pink-surface); }

  /* B4 — long name ellipsis (cell stays single-line, hover title shows full) */
  .dash-name-wrap { min-width:0; }
  .dash-truncate { display:block; max-width:100%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }

  /* A4 — extracted CR/drone identifier shown beside the link cell */
  .dash-id-label { flex:0 0 auto; font-size:9px; font-weight:850; color:var(--color-muted); background:var(--color-workspace-panel); border-radius:3px; padding:1px 4px; max-width:96px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }

  /* C2 — semantic state colour chips on the inline state selects */
  .dash-state-select.chip-approved { border-color:#1f9d57; color:#1f7a44; background:#eafaf0; }
  .dash-state-select.chip-pending { border-color:#d39e00; color:#9a7400; background:#fff8e6; }
  .dash-state-select.chip-negative { border-color:var(--color-dbs-red); color:var(--color-dbs-red); background:var(--color-soft-pink-surface); }

  /* C4 — per-cell saving spinner */
  .dash-cell-spin { flex:0 0 auto; width:12px; height:12px; border:2px solid var(--color-input-border, #D7DCE2); border-top-color:var(--color-dbs-red); border-radius:50%; display:inline-block; animation:dash-cell-spin 0.6s linear infinite; }
  @keyframes dash-cell-spin { to { transform:rotate(360deg); } }
</style>
