<script lang="ts">
  import { callBridge, isPywebviewReady, waitForPywebviewReady } from "../bridge";
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
    // Optional. Parent must adapt its Add-Year flow to a bare () => void here
    // (the parent's addYear is (year) => Promise<string|null>, so wire a
    // wrapper that prompts for the year — do not bind addYear directly).
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
  type PendingState = { kind: "cr" | "drone" | "reopen"; path: string; index: number; next: string; name: string };
  let pendingState: PendingState | null = $state(null);

  const CR_STATE_OPTIONS = ["PENDING SUBMISSION", "PENDING APPROVAL", "APPROVED", "IN-PROGRESS", "FINISHED", "POSTPONED", "CANCELED"];
  const DRONE_STATE_OPTIONS = ["UAT", "PENDING APPROVAL", "APPROVED", "IN-PROGRESS", "FINISHED", "CANCELED"];
  const DESTRUCTIVE = new Set(["POSTPONED", "CANCELED"]);
  const REOPENABLE = new Set(["POSTPONED", "CANCELED"]);
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
  const DRONE_NEXT: Record<string, string[]> = {
    "UAT": ["PENDING APPROVAL", "CANCELED"],
    "PENDING APPROVAL": ["APPROVED", "CANCELED"],
    "APPROVED": ["CANCELED"],
    "IN-PROGRESS": ["FINISHED", "CANCELED"],
    "FINISHED": [],
    "CANCELED": [],
  };

  function uniqueOptions(current: string, next: string[], fallback: string[]): string[] {
    const options = [current, ...next].filter((value) => value && value.trim().length > 0);
    return options.length > 0 ? Array.from(new Set(options)) : fallback;
  }

  /** Legal CR next states for user-controlled dropdown; backend remains authoritative. */
  function legalCrOptionsFor(crState: string): string[] {
    return uniqueOptions(crState, CR_NEXT[crState] ?? [], [crState || "PENDING SUBMISSION"]);
  }

  /** Back-compat source marker for reopen tests; use legalCrOptionsFor in markup. */
  function crOptionsFor(crState: string): string[] {
    return legalCrOptionsFor(crState);
  }

  /** Legal Drone next states for user-controlled dropdown; IN-PROGRESS stays auto-only. */
  function legalDroneOptionsFor(droneState: string): string[] {
    return uniqueOptions(droneState, DRONE_NEXT[droneState] ?? [], [droneState || "UAT"]);
  }

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

  interface AlignedDroneRow extends DashboardRowDrone {
    existingIndex: number;
  }

  function subprojectsOf(p: DashboardProject): string[] {
    const names = [
      ...(p.subprojects ?? []),
      ...(p.drone_tickets ?? [])
        .map((d) => d.subfolder_name)
        .filter((n): n is string => !!n && n.trim().length > 0),
    ];
    return Array.from(new Set(names));
  }

  function alignedDroneRows(p: DashboardProject): AlignedDroneRow[] {
    const drones = p.drone_tickets ?? [];
    const used = new Set<number>();
    const rows: AlignedDroneRow[] = subprojectsOf(p).map((sub) => {
      const index = drones.findIndex((d, i) => !used.has(i) && (d.subfolder_name ?? "") === sub);
      if (index >= 0) {
        used.add(index);
        return { ...drones[index], existingIndex: index };
      }
      return { subfolder_name: sub, drone_ticket: "", drone_link: "", drone_state: "", owner: "", existingIndex: -1 };
    });
    drones.forEach((d, index) => {
      if (!used.has(index)) rows.push({ ...d, existingIndex: index });
    });
    return rows;
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

  function joinPath(base: string, child: string): string {
    const sep = base.includes("\\") ? "\\" : "/";
    return base.endsWith(sep) ? base + child : base + sep + child;
  }

  // ── Load ──
  async function loadDashboard() {
    loadState = "loading";
    errorMessage = ""; errorCode = ""; actionError = "";
    if (!isPywebviewReady() && !(await waitForPywebviewReady())) {
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

  async function saveProjectDatetime(p: DashboardProject, field: "start_datetime" | "end_datetime", value: string) {
    const nextValue = fromDatetimeLocal(value);
    if (nextValue === p[field]) return;
    savingKey = `${p.project_path}:${field}`;
    actionError = "";
    const r = await callBridge("project_update", p.project_path, {
      start_datetime: field === "start_datetime" ? nextValue : p.start_datetime,
      end_datetime: field === "end_datetime" ? nextValue : p.end_datetime,
    });
    savingKey = "";
    if (!r.ok) { actionError = r.error.message; }
    await loadDashboard();
  }

  async function saveDroneLink(p: DashboardProject, row: AlignedDroneRow, value: string) {
    const next = value.trim();
    if (next === row.drone_link) return;
    const keyIndex = row.existingIndex >= 0 ? row.existingIndex : row.subfolder_name ?? "new";
    savingKey = `${p.project_path}:dronelink:${keyIndex}`;
    actionError = "";
    const r = row.existingIndex >= 0
      ? await callBridge("drone_update", p.project_path, row.existingIndex, { drone_link: next })
      : await callBridge("drone_add", p.project_path, { drone_link: next, subfolder_name: row.subfolder_name, owner: "" });
    savingKey = "";
    if (!r.ok) { actionError = r.error.message; }
    await loadDashboard();
  }

  function onCrStateChange(p: DashboardProject, next: string) {
    if (next === p.cr_state) return;
    if (next === REOPEN_OPTION) {
      pendingState = { kind: "reopen", path: p.project_path, index: -1, next, name: p.project_name };
      return;
    }
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

  function onDroneStateChange(p: DashboardProject, row: AlignedDroneRow, next: string) {
    if (row.existingIndex < 0 || next === row.drone_state) return;
    if (DESTRUCTIVE.has(next)) {
      pendingState = { kind: "drone", path: p.project_path, index: row.existingIndex, next, name: `${p.project_name} · ${row.subfolder_name ?? `drone ${row.existingIndex + 1}`}` };
      return;
    }
    void applyDroneState(p.project_path, row.existingIndex, next);
  }
  async function applyDroneState(path: string, index: number, next: string) {
    savingKey = `${path}:dronestate:${index}`;
    actionError = "";
    const r = await callBridge("drone_update", path, index, { drone_state: next });
    savingKey = "";
    if (!r.ok) actionError = r.error.message;
    await loadDashboard();
  }

  async function reopenProject(path: string) {
    savingKey = `${path}:crstate`;
    actionError = "";
    const r = await callBridge("folder_reopen", path);
    savingKey = "";
    if (!r.ok) actionError = r.error.message;
    await loadDashboard();
  }

  async function confirmPendingState() {
    const ps = pendingState;
    pendingState = null;
    if (!ps) return;
    if (ps.kind === "reopen") await reopenProject(ps.path);
    else if (ps.kind === "cr") await applyCrState(ps.path, ps.next);
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

<section class="screen active" id="screen-dashboard">
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
            {@const rows = alignedDroneRows(p)}
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
                  {#if rows.length === 0}
                    <div class="stack-line"><span class="muted-text">—</span></div>
                  {:else}
                    {#each rows as row}
                      <div class="stack-line">
                        {#if row.subfolder_name}
                          <button class="dash-sub-btn dash-truncate" type="button" title={row.subfolder_name} onclick={() => openSubfolder(p.project_path, row.subfolder_name!)}>{row.subfolder_name}</button>
                        {:else}
                          <span class="muted-text">—</span>
                        {/if}
                      </div>
                    {/each}
                  {/if}
                </div>
              </div>

              <!-- Start / End -->
              <div class="table-cell cell-center">
                <div class="dash-date-wrap">
                  <input class="dash-date-input" type="datetime-local" value={toDatetimeLocal(p.start_datetime)} onblur={(e) => saveProjectDatetime(p, "start_datetime", (e.currentTarget as HTMLInputElement).value)} disabled={savingKey === `${p.project_path}:start_datetime`} />
                  {#if p.start_datetime}<span class="date-time">{fmtDate(p.start_datetime, "date")} · {fmtDate(p.start_datetime, "time")}</span>{/if}
                  {#if savingKey === `${p.project_path}:start_datetime`}<span class="dash-cell-spin" aria-label="Saving"></span>{/if}
                </div>
              </div>
              <div class="table-cell cell-center">
                <div class="dash-date-wrap">
                  <input class="dash-date-input" type="datetime-local" value={toDatetimeLocal(p.end_datetime)} onblur={(e) => saveProjectDatetime(p, "end_datetime", (e.currentTarget as HTMLInputElement).value)} disabled={savingKey === `${p.project_path}:end_datetime`} />
                  {#if p.end_datetime}<span class="date-time">{fmtDate(p.end_datetime, "date")} · {fmtDate(p.end_datetime, "time")}</span>{/if}
                  {#if savingKey === `${p.project_path}:end_datetime`}<span class="dash-cell-spin" aria-label="Saving"></span>{/if}
                </div>
              </div>

              <!-- Drone Ticket (inline paste + open link) -->
              <div class="table-cell">
                <div class="stack-lines">
                  {#if rows.length === 0}
                    <div class="stack-line"><span class="muted-text">—</span></div>
                  {:else}
                    {#each rows as d}
                      {@const droneKey = d.existingIndex >= 0 ? d.existingIndex : d.subfolder_name ?? "new"}
                      <div class="stack-line dash-link-cell">
                        <input
                          class="link-edit"
                          value={d.drone_link}
                          placeholder={d.subfolder_name ? `Paste drone URL for ${d.subfolder_name}…` : "Paste drone URL…"}
                          title={d.drone_ticket || d.drone_link || d.subfolder_name || "Drone ticket"}
                          onkeydown={onInputKey}
                          onblur={(e) => saveDroneLink(p, d, (e.currentTarget as HTMLInputElement).value)}
                          disabled={savingKey === `${p.project_path}:dronelink:${droneKey}`}
                        />
                        {#if savingKey === `${p.project_path}:dronelink:${droneKey}`}<span class="dash-cell-spin" aria-label="Saving"></span>{/if}
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
                  {#if rows.length === 0}
                    <div class="stack-line"><span class="muted-text">—</span></div>
                  {:else}
                    {#each rows as d}
                      <div class="stack-line">
                        {#if d.existingIndex < 0}
                          <select class="dash-state-select" disabled title="Add drone ticket first"><option>Add ticket first</option></select>
                        {:else}
                          <select class="dash-state-select {stateChipClass(d.drone_state)}" value={d.drone_state} onchange={(e) => onDroneStateChange(p, d, (e.currentTarget as HTMLSelectElement).value)} disabled={savingKey === `${p.project_path}:dronestate:${d.existingIndex}`}>
                            {#each legalDroneOptionsFor(d.drone_state) as opt}<option value={opt} disabled={opt === "IN-PROGRESS"}>{opt}</option>{/each}
                            {#if !DRONE_STATE_OPTIONS.includes(d.drone_state) && d.drone_state}<option value={d.drone_state}>{d.drone_state}</option>{/if}
                          </select>
                          {#if savingKey === `${p.project_path}:dronestate:${d.existingIndex}`}<span class="dash-cell-spin" aria-label="Saving"></span>{/if}
                        {/if}
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
                    {#each legalCrOptionsFor(p.cr_state) as opt}<option value={opt} disabled={opt === "IN-PROGRESS"}>{opt}</option>{/each}
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
</section>

{#if pendingState}
  <ConfirmModal
    title={pendingState.kind === "reopen" ? "Reopen project?" : pendingState.next === "CANCELED" ? "Mark as Canceled?" : "Postpone project?"}
    actionLabel={pendingState.kind === "reopen" ? "Reopen to UAT_PREPARE" : pendingState.next === "CANCELED" ? "Set Canceled" : "Set Postponed"}
    targetName={pendingState.kind === "reopen" ? `${pendingState.name} → UAT_PREPARE` : `${pendingState.name} → ${pendingState.next}`}
    reversible={pendingState.kind === "reopen"}
    onConfirm={confirmPendingState}
    onCancel={cancelPendingState}
  />
{/if}

<style>
  .dash-action-error { background:var(--color-soft-pink-surface); border:1px solid var(--color-soft-pink-border); color:var(--color-dbs-red); border-radius:8px; padding:8px 12px; font-size:12px; font-weight:500; flex:0 0 auto; }
  .dash-name-btn { border:0; background:transparent; padding:0; font-size:13px; font-weight:600; color:var(--color-ink-strong); cursor:pointer; text-align:left; }
  .dash-name-btn:hover { color:var(--color-dbs-red); }
  .dash-hl { background:var(--color-soft-pink-surface); color:var(--color-dbs-red); border-radius:3px; padding:0 2px; }
  .dash-sub-btn { border:0; background:transparent; padding:0; font-size:12px; font-weight:500; color:var(--color-ink); cursor:pointer; text-align:left; }
  .dash-sub-btn:hover { color:var(--color-dbs-red); }
  .dash-link-cell { display:flex; align-items:center; gap:5px; width:100%; }
  .dash-link-cell .link-edit { flex:1; min-width:0; }
  .dash-date-wrap { display:flex; flex-direction:column; align-items:center; gap:4px; width:100%; }
  .dash-date-input { width:100%; min-width:130px; height:28px; border:1px solid transparent; border-radius:6px; background:transparent; color:var(--color-ink); font-size:11px; font-weight:600; padding:0 6px; outline:none; }
  .dash-date-input:hover { background:var(--color-row-hover); }
  .dash-date-input:focus { border-color:var(--color-dbs-red); background:var(--color-workspace-panel); }
  .dash-open { flex:0 0 auto; color:var(--color-muted); font-weight:700; text-decoration:none; font-size:12px; padding:1px 4px; border-radius:4px; }
  .dash-open:hover { background:var(--color-soft-pink-surface); color:var(--color-dbs-red); }
  /* Inline state select — Notion soft-tag pill */
  .dash-state-select { height:28px; border:1px solid var(--primary-red); border-radius:6px; background:var(--primary-red); color:#fff; font-size:11.5px; font-weight:800; outline:none; padding:0 8px; cursor:pointer; max-width:100%; appearance:auto; transition:filter 0.12s ease; }
  .dash-state-select:hover { filter:brightness(0.95); }
  .dash-state-select:focus { box-shadow:0 0 0 2px var(--color-dbs-red-active); }
  .dash-state-select:disabled { opacity:0.55; cursor:not-allowed; }
  .dash-row:hover { background:var(--color-row-hover); }
  .dash-skel-bar { height:14px; border-radius:5px; background:linear-gradient(90deg,#eee 25%,#f6f6f6 37%,#eee 63%); background-size:400% 100%; animation:dash-shimmer 1.2s ease infinite; }
  @keyframes dash-shimmer { 0% { background-position:100% 0; } 100% { background-position:-100% 0; } }
  .dash-empty-cta { margin-top:10px; height:32px; padding:0 16px; border:1px solid var(--color-dbs-red); border-radius:7px; background:var(--color-dbs-red); color:#fff; font-size:12px; font-weight:600; cursor:pointer; transition:background 0.12s ease; }
  .dash-empty-cta:hover { background:var(--color-dbs-red-hover); }
  .dash-empty-actions { display:flex; gap:8px; justify-content:center; }
  .dash-empty-cta.secondary { background:var(--color-workspace-panel); color:var(--color-dbs-red); }
  .dash-empty-cta.secondary:hover { background:var(--color-soft-pink-surface); }

  /* B4 — long name ellipsis (cell stays single-line, hover title shows full) */
  .dash-name-wrap { min-width:0; }
  .dash-truncate { display:block; max-width:100%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }

  /* A4 — extracted CR/drone identifier shown beside the link cell */
  .dash-id-label { flex:0 0 auto; font-size:9.5px; font-weight:600; color:var(--color-muted); background:var(--color-workspace); border:1px solid var(--color-border); border-radius:4px; padding:1px 5px; max-width:96px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }

  /* C2 — semantic soft-tag colours on the inline state selects (Notion style) */
  .dash-state-select.chip-approved { background:var(--tag-green-bg); color:var(--tag-green-ink); }
  .dash-state-select.chip-pending { background:var(--tag-amber-bg); color:var(--tag-amber-ink); }
  .dash-state-select.chip-negative { background:var(--tag-red-bg); color:var(--tag-red-ink); }
  .dash-state-select.chip-approved:disabled, .dash-state-select.chip-pending:disabled, .dash-state-select.chip-negative:disabled { opacity:0.55; }

  /* C4 — per-cell saving spinner */
  .dash-cell-spin { flex:0 0 auto; width:12px; height:12px; border:2px solid var(--color-border); border-top-color:var(--color-dbs-red); border-radius:50%; display:inline-block; animation:dash-cell-spin 0.6s linear infinite; }
  @keyframes dash-cell-spin { to { transform:rotate(360deg); } }
</style>
