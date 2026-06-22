<script lang="ts">
  import { callBridge, isPywebviewReady, waitForPywebviewReady } from "../bridge";
  import type { BridgeResponse, DashboardProject, DashboardSummary, DashboardRowDrone } from "../types";
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
  let isBridgeUnavailable = $derived(errorCode === BridgeErrorCode.BRIDGE_UNAVAILABLE);
  let dashboardErrorTitle = $derived(isBridgeUnavailable ? "Open in Project Tracker desktop app" : "Dashboard could not load");
  let dashboardErrorDetail = $derived(isBridgeUnavailable
    ? "Live project data is only available from the desktop shell. Launch Project Tracker, then refresh Dashboard."
    : errorMessage || "Try refreshing Dashboard. Your project files were not changed.");

  let projects: DashboardProject[] = $state([]);
  let summary: DashboardSummary | null = $state(null);

  // Inline-edit transient state
  let savingKeys: string[] = $state([]);
  let actionError: string = $state("");
  type PendingState = { kind: "cr" | "drone" | "reopen"; path: string; index: number; next: string; name: string };
  let pendingState: PendingState | null = $state(null);

  function startSaving(key: string) {
    if (!savingKeys.includes(key)) savingKeys = [...savingKeys, key];
  }

  function finishSaving(key: string) {
    savingKeys = savingKeys.filter((value) => value !== key);
  }

  function isSaving(key: string): boolean {
    return savingKeys.includes(key);
  }

  async function withSaving(key: string, action: () => Promise<BridgeResponse<unknown>>) {
    startSaving(key);
    actionError = "";
    try {
      const r = await action();
      if (!r.ok) actionError = r.error?.message ?? "Update failed.";
    } catch (error) {
      actionError = error instanceof Error ? error.message : "Update failed.";
    } finally {
      finishSaving(key);
      await loadDashboard({ clearActionError: false });
    }
  }

  const CR_STATE_OPTIONS = ["PENDING SUBMISSION", "PENDING APPROVAL", "APPROVED", "IN-PROGRESS", "FINISHED", "POSTPONED", "CANCELED"];
  const DRONE_STATE_OPTIONS = ["UAT", "PENDING APPROVAL", "APPROVED", "IN-PROGRESS", "FINISHED", "POSTPONED", "CANCELED"];
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

  function projectNeedsReview(p: DashboardProject): boolean {
    const drones = p.drone_tickets ?? [];
    return !p.cr_link?.trim() || !p.start_datetime || !p.end_datetime || drones.some((d) => !d.drone_link?.trim());
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
  const columns = ["No", "Project", "Sub Project", "Start", "End", "Drone Ticket", "Drone State", "CR Number", "CR State", "More"];

  // ── Filter: status tab + search ──
  let filteredProjects: DashboardProject[] = $derived.by(() => {
    let result = activeStatus === "needs-review"
      ? projects.filter(projectNeedsReview)
      : activeStatus === "all"
        ? projects
        : projects.filter((p) => p.project_state === activeStatus);
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
  interface LoadDashboardOptions { clearActionError?: boolean }

  async function loadDashboard(options: LoadDashboardOptions = {}) {
    const { clearActionError = true } = options;
    loadState = "loading";
    errorMessage = ""; errorCode = "";
    if (clearActionError) actionError = "";
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
    await withSaving(`${p.project_path}:crlink`, () => callBridge("cr_update_link", p.project_path, value));
  }

  async function saveProjectDatetime(p: DashboardProject, field: "start_datetime" | "end_datetime", value: string) {
    const next = fromDatetimeLocal(value);
    const current = toDatetimeLocal(field === "start_datetime" ? p.start_datetime : p.end_datetime);
    if (value === current) return;
    await withSaving(`${p.project_path}:${field}`, () => callBridge("project_update", p.project_path, { [field]: next }));
  }

  async function saveDroneLink(p: DashboardProject, row: AlignedDroneRow, value: string) {
    const next = value.trim();
    if (next === row.drone_link) return;
    const keyIndex = row.existingIndex >= 0 ? row.existingIndex : row.subfolder_name ?? "new";
    await withSaving(`${p.project_path}:dronelink:${keyIndex}`, () => row.existingIndex >= 0
      ? callBridge("drone_update", p.project_path, row.existingIndex, { drone_link: next })
      : callBridge("drone_add", p.project_path, { drone_link: next, subfolder_name: row.subfolder_name, owner: "" }));
  }

  function escapeHtml(value: string): string {
    return value.replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char] ?? char);
  }

  async function copyRichLink(url: string, label: string) {
    const href = url.trim();
    if (!href) return;
    actionError = "";
    try {
      const html = `<a href="${escapeHtml(href)}">${escapeHtml(label || href)}</a>`;
      if (typeof navigator !== "undefined" && navigator.clipboard && "write" in navigator.clipboard && typeof ClipboardItem !== "undefined") {
        await navigator.clipboard.write([
          new ClipboardItem({
            "text/html": new Blob([html], { type: "text/html" }),
            "text/plain": new Blob([href], { type: "text/plain" }),
          }),
        ]);
        return;
      }
      if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(href);
        return;
      }
      throw new Error("Clipboard unavailable");
    } catch {
      actionError = "Copy failed. Open the link, then copy from the browser.";
    }
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
    await withSaving(`${path}:crstate`, () => callBridge("cr_update_state", path, next));
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
    await withSaving(`${path}:dronestate:${index}`, () => callBridge("drone_update", path, index, { drone_state: next }));
  }

  async function reopenProject(path: string) {
    await withSaving(`${path}:crstate`, () => callBridge("folder_reopen", path));
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
  {#if loadState !== "idle"}
    <!-- Status filter bar -->
    <div class="dashboard-status-bar">
      <div class="dash-filter-tabs" aria-label="Dashboard status filters">
        {#each statuses as s}
          <button class="status-tab" class:active={activeStatus === s.key} onclick={() => (activeStatus = s.key)}>
            {s.label} ({s.count})
          </button>
        {/each}
      </div>
      <button class="dash-reset-filter" type="button" disabled={activeStatus === "all"} onclick={() => (activeStatus = "all")} title="Clear status filter">Clear</button>
      <span class="project-count">{filteredProjects.length} project(s)</span>
    </div>
  {/if}

  {#if actionError}
    <div class="dash-action-error" role="alert"><span aria-hidden="true">!</span> {actionError}</div>
  {/if}

  <!-- Project table -->
  <div class="table-scroll dashboard-table-scroll">
  <div class="project-table dashboard-project-table">
  <div class="table-header-row dash-column-row">
  {#each columns as col}
  <div class="table-header-cell">{col}</div>
  {/each}
  </div>

  {#if loadState === "loading"}
  {#each [0, 1, 2, 3] as i}
  <div class="project-row dash-skel"><div class="table-cell" style="grid-column:1 / -1;"><div class="dash-skel-bar"></div></div></div>
  {/each}
  {:else if loadState === "error"}
  <div class="table-empty dash-recovery-state">
  <p class="empty-title">{dashboardErrorTitle}</p>
  <p class="empty-sub">{dashboardErrorDetail}</p>
  </div>
  {:else if loadState === "idle"}
  <div class="table-empty"><p class="empty-title">Preparing Dashboard…</p></div>
  {:else if filteredProjects.length === 0}
  <div class="table-empty">
  <p class="empty-title">No projects found</p>
  <p class="empty-sub">Create a year folder first, then add a project. Existing filters may also be hiding rows.</p>
  <div class="dash-empty-actions">
  {#if onAddYear}<button class="dash-empty-cta secondary" type="button" onclick={() => onAddYear?.()}>Add Year</button>{/if}
  <button class="dash-empty-cta" type="button" onclick={() => onAddProject?.()}>Add Project</button>
  </div>
  </div>
  {:else}
  {#each filteredProjects as p, idx}
  {@const rows = alignedDroneRows(p)}
  <div class="project-row dash-row" class:alt={idx % 2 === 1}>
  <div class="table-cell cell-center"><strong>{idx + 1}</strong></div>

  <!-- Main Project (click → open folder) -->
  <div class="table-cell dash-name-cell">
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

  <!-- Start / End inline edit (user override of PRD §11.15 read-only rule) -->
  <div class="table-cell cell-center">
  <input
  class="dash-datetime-edit"
  type="datetime-local"
  value={toDatetimeLocal(p.start_datetime)}
  title={`Start: ${fmtDate(p.start_datetime, "date")} ${fmtDate(p.start_datetime, "time")}`}
  onblur={(e) => saveProjectDatetime(p, "start_datetime", (e.currentTarget as HTMLInputElement).value)}
  disabled={isSaving(`${p.project_path}:start_datetime`)}
  />
  </div>
  <div class="table-cell cell-center">
  <input
  class="dash-datetime-edit"
  type="datetime-local"
  value={toDatetimeLocal(p.end_datetime)}
  title={`End: ${fmtDate(p.end_datetime, "date")} ${fmtDate(p.end_datetime, "time")}`}
  onblur={(e) => saveProjectDatetime(p, "end_datetime", (e.currentTarget as HTMLInputElement).value)}
  disabled={isSaving(`${p.project_path}:end_datetime`)}
  />
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
  {#if d.drone_link}
  <span class="dash-id-label saved" title={d.drone_link}>{d.drone_ticket || "Drone Link"}</span>
  <button class="dash-icon-btn" type="button" title="Copy Drone link" aria-label="Copy Drone link" onclick={() => copyRichLink(d.drone_link, d.drone_ticket || "Drone Link")}>⧉</button>
  <a class="dash-icon-btn" href={d.drone_link} target="_blank" rel="noopener noreferrer" title="Open Drone link" aria-label="Open Drone link">↗</a>
  {:else}
  <input
  class="link-edit"
  value={d.drone_link}
  placeholder={d.subfolder_name ? `Paste drone URL for ${d.subfolder_name}…` : "Paste drone URL…"}
  title={d.subfolder_name || "Drone ticket"}
  onkeydown={onInputKey}
  onblur={(e) => saveDroneLink(p, d, (e.currentTarget as HTMLInputElement).value)}
  disabled={isSaving(`${p.project_path}:dronelink:${droneKey}`)}
  />
  {/if}
  {#if isSaving(`${p.project_path}:dronelink:${droneKey}`)}<span class="dash-cell-spin" aria-label="Saving"></span>{/if}
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
  <select class="dash-state-select {stateChipClass(d.drone_state)}" value={d.drone_state} onchange={(e) => onDroneStateChange(p, d, (e.currentTarget as HTMLSelectElement).value)} disabled={isSaving(`${p.project_path}:dronestate:${d.existingIndex}`)}>
  {#each legalDroneOptionsFor(d.drone_state) as opt}
  <option value={opt} disabled={opt === "IN-PROGRESS"}>{opt}</option>
  {/each}
  </select>
  {#if isSaving(`${p.project_path}:dronestate:${d.existingIndex}`)}<span class="dash-cell-spin" aria-label="Saving"></span>{/if}
  {/if}
  </div>
  {/each}
  {/if}
  </div>
  </div>

  <!-- CR Number (inline paste + open link) -->
  <div class="table-cell">
  <div class="dash-link-cell">
  {#if p.cr_link}
  <span class="dash-id-label saved" title={p.cr_link}>{p.cr_number || "CR Link"}</span>
  <button class="dash-icon-btn" type="button" title="Copy CR link" aria-label="Copy CR link" onclick={() => copyRichLink(p.cr_link, p.cr_number || "CR Link")}>⧉</button>
  <a class="dash-icon-btn" href={p.cr_link} target="_blank" rel="noopener noreferrer" title="Open CR link" aria-label="Open CR link">↗</a>
  {:else}
  <input
  class="link-edit"
  value={p.cr_link}
  placeholder="Paste CR URL…"
  title="CR link"
  onkeydown={onInputKey}
  onblur={(e) => saveCrLink(p, (e.currentTarget as HTMLInputElement).value)}
  disabled={isSaving(`${p.project_path}:crlink`)}
  />
  {/if}
  {#if isSaving(`${p.project_path}:crlink`)}<span class="dash-cell-spin" aria-label="Saving"></span>{/if}
  </div>
  </div>

  <!-- CR State (inline dropdown + guard + confirm) -->
  <div class="table-cell">
  <div class="dash-link-cell">
  {#if !p.cr_link}
  <select class="dash-state-select dash-state-guard" disabled title="Add CR Link First"><option>Add CR Link First</option></select>
  {:else}
  <select class="dash-state-select {stateChipClass(p.cr_state)}" value={p.cr_state} onchange={(e) => onCrStateChange(p, (e.currentTarget as HTMLSelectElement).value)} disabled={isSaving(`${p.project_path}:crstate`)}>
  {#each legalCrOptionsFor(p.cr_state) as opt}
  <option value={opt} disabled={opt === "IN-PROGRESS"}>{opt}</option>
  {/each}
  </select>
  {#if isSaving(`${p.project_path}:crstate`)}<span class="dash-cell-spin" aria-label="Saving"></span>{/if}
  {/if}
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
  .dashboard-status-bar { background:#fff; border:1px solid var(--light-border); border-radius:7px; padding:6px; display:flex; align-items:center; gap:6px; min-width:0; overflow-x:auto; flex:0 0 auto; }
  .dash-filter-tabs { display:flex; align-items:center; gap:4px; min-width:0; }
  .dash-reset-filter { height:26px; border:1px solid transparent; border-radius:5px; background:#fff; color:var(--text-secondary); font-weight:900; padding:0 9px; }
  .dash-reset-filter:hover:not(:disabled) { background:var(--row-alt); border-color:var(--light-border); color:var(--text-strong); }
  .dash-reset-filter:disabled { opacity:.45; cursor:not-allowed; }
  .dashboard-table-card { box-shadow:none; }
  .dashboard-table-scroll { border:0; border-radius:0; box-shadow:none; padding:0; background:#fff; scrollbar-gutter:stable; }
  .dashboard-project-table { min-width:1450px; border:0; border-radius:0; }
  .dashboard-project-table .table-header-row, .dashboard-project-table .project-row { grid-template-columns:40px 150px minmax(190px,.9fr) 138px 138px minmax(225px,1fr) 148px 220px 190px 56px; }
  .dashboard-project-table .project-row { min-height:88px; border-top:1px solid var(--light-border); transition:background .16s ease, box-shadow .16s ease; }
  .dashboard-project-table .project-row.alt { min-height:88px; background:#fff; }
  .dashboard-project-table .table-cell { border-right:1px solid var(--light-border); }
  .dashboard-project-table .table-cell:nth-child(3), .dashboard-project-table .table-cell:nth-child(5), .dashboard-project-table .table-cell:nth-child(7), .dashboard-project-table .table-cell:nth-child(9) { border-right-color:var(--light-border); }
  .dash-column-row { position:sticky; top:0; z-index:3; border-top:1px solid var(--light-border); border-bottom:1px solid var(--light-border); }
  .dashboard-project-table .table-header-cell { background:#fff; color:var(--text-secondary); border-right-color:var(--light-border); text-transform:none; font-size:10px; letter-spacing:0; justify-content:flex-start; }
  .dashboard-project-table .table-header-cell:first-child, .dashboard-project-table .table-header-cell:nth-child(4), .dashboard-project-table .table-header-cell:nth-child(5), .dashboard-project-table .table-header-cell:last-child { justify-content:center; }
  .dashboard-project-table .table-header-cell:nth-child(3), .dashboard-project-table .table-header-cell:nth-child(5), .dashboard-project-table .table-header-cell:nth-child(7), .dashboard-project-table .table-header-cell:nth-child(9) { border-right-color:var(--light-border); }
  .dash-action-error { background:var(--color-soft-pink-surface); border:1px solid var(--color-soft-pink-border); color:var(--color-dbs-red); border-radius:8px; padding:8px 12px; font-size:12px; font-weight:800; flex:0 0 auto; }
  .dash-name-cell { align-items:center; justify-content:center; text-align:center; }
  .dash-name-btn { border:0; background:transparent; padding:0; font-size:12px; font-weight:900; color:var(--primary-red); cursor:pointer; text-align:center; line-height:1.1; }
  .dash-name-btn:hover { color:var(--red-hover); text-decoration:underline; }
  .dash-hl { background:var(--color-soft-pink-surface); color:var(--color-dbs-red); border-radius:3px; padding:0 2px; }
  .dash-sub-btn { border:0; background:transparent; padding:0; font-size:12px; font-weight:500; color:var(--color-ink); cursor:pointer; text-align:left; }
  .dash-sub-btn:hover { color:var(--color-dbs-red); }
  .dash-link-cell { display:flex; align-items:center; gap:6px; width:100%; min-width:0; }
  .dash-link-cell .link-edit { flex:1; min-width:0; }
  .dash-datetime-edit { width:100%; min-width:0; height:28px; border:1px solid var(--input-border); border-radius:6px; background:#fff; color:var(--text-strong); font-size:10px; font-weight:800; padding:2px 5px; outline:none; text-align:center; transition:border-color .16s ease, box-shadow .16s ease; }
  .dash-datetime-edit:focus { border-color:var(--primary-red); background:#fff; box-shadow:0 0 0 2px rgba(185,28,28,.12); }
  .dash-datetime-edit:disabled { opacity:.55; cursor:not-allowed; }
  .dash-icon-btn { flex:0 0 26px; width:26px; height:26px; border:1px solid var(--light-border); border-radius:6px; background:#fff; color:var(--text-strong); display:inline-flex; align-items:center; justify-content:center; text-decoration:none; font-size:13px; font-weight:900; line-height:1; transition:background .16s ease, color .16s ease, border-color .16s ease, transform .16s cubic-bezier(.22,1,.36,1); }
  .dash-icon-btn:hover { background:var(--soft-pink-surface); border-color:var(--soft-pink-border); color:var(--primary-red); transform:translateY(-1px); }
  .dash-open { flex:0 0 auto; color:var(--color-muted); font-weight:850; text-decoration:none; font-size:10px; padding:2px 6px; border:1px solid transparent; border-radius:4px; }
  .dash-open:hover { background:var(--row-alt); border-color:var(--light-border); color:var(--color-dbs-red); }
  /* Inline state select — matches AS-IS .state-combo solid red */
  .dash-state-select { min-height:26px; width:100%; border:1px solid var(--red-hover); border-radius:7px; background:var(--primary-red); color:#fff; font-size:10px; font-weight:900; outline:none; padding:0 8px; cursor:pointer; max-width:100%; appearance:auto; line-height:1.05; text-align:center; display:flex; align-items:center; justify-content:center; transition:background .16s ease, box-shadow .16s ease, opacity .16s ease; }
  .dash-state-select:hover { background:var(--red-hover); }
  .dash-state-select:focus { box-shadow:0 0 0 2px var(--active-red); }
  .dash-state-select:disabled { opacity:0.72; cursor:not-allowed; }
  .dash-state-select.dash-state-guard { background:var(--surface-dark); border-color:var(--surface-dark); color:#fff; }
  .dash-row:hover { background:var(--color-row-hover); box-shadow:inset 0 0 0 1px rgba(185,28,28,.08); }
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
  .dash-id-label { flex:0 1 auto; font-size:10px; font-weight:900; color:var(--text-strong); background:var(--color-workspace); border:1px solid var(--color-border); border-radius:6px; padding:4px 8px; max-width:132px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .dash-id-label.saved { border-color:var(--soft-pink-border); background:var(--soft-pink-surface); color:var(--primary-red); }

  /* AS-IS parity: state selects stay solid red regardless of state (no Notion soft chips) */
  .dash-state-select.chip-approved, .dash-state-select.chip-pending, .dash-state-select.chip-negative { background:var(--primary-red); color:#fff; }
  .dash-state-select.chip-approved:disabled, .dash-state-select.chip-pending:disabled, .dash-state-select.chip-negative:disabled { opacity:0.55; }

  /* C4 — per-cell saving spinner */
  .dash-cell-spin { flex:0 0 auto; width:12px; height:12px; border:2px solid var(--color-border); border-top-color:var(--color-dbs-red); border-radius:50%; display:inline-block; animation:dash-cell-spin 0.6s linear infinite; }
  @keyframes dash-cell-spin { to { transform:rotate(360deg); } }
  @media (prefers-reduced-motion: reduce) {
    .dashboard-project-table .project-row, .dash-datetime-edit, .dash-icon-btn, .dash-state-select, .dash-cell-spin, .dash-skel-bar { transition:none; animation:none; }
  }
</style>
