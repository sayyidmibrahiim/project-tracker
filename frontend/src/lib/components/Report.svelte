<script lang="ts">
  import { callBridge, isPywebviewReady } from "../bridge";
  import { BridgeErrorCode } from "../types";
  import type { DashboardProject } from "../types";
  import { addToast } from "../stores/toastStore";

  let _props: Record<string, unknown> = $props();

  type LoadState = "idle" | "loading" | "error" | "loaded";
  let loadState: LoadState = $state("idle");
  let errorCode: string = $state("");
  let errorMessage: string = $state("");

  let yearFilter: string = $state("all");
  let projectStateFilter: string = $state("all");
  let crStateFilter: string = $state("all");
  let droneStateFilter: string = $state("all");
  let monthFilter: string = $state("all");
  let searchFilter: string = $state("");
  let fetchKey: number = $state(0);
  let filterDebounce: ReturnType<typeof setTimeout> | null = null;
  let projects: DashboardProject[] = $state([]);
  let exportState: "idle" | "saving" = $state("idle");

  const projectStates = ["UAT_PREPARE", "PROD_READY", "IMPLEMENTED", "POSTPONED"];
  const crStates = ["PENDING SUBMISSION", "PENDING APPROVAL", "APPROVED", "IN-PROGRESS", "FINISHED", "CANCELED", "REOPEN"];
  const droneStates = ["OPEN", "IN-PROGRESS", "DONE", "CANCELED", "REOPEN"];
  // Years are loaded live from `year_list` (real filesystem scan), not hardcoded.
  let yearOptions: string[] = $state([]);

  // Visible rows after client-side Month + Drone filters (extra server filters).
  let visibleProjects = $derived.by(() => {
    let rows = projects;
    if (droneStateFilter !== "all") {
      rows = rows.filter((p) => droneState(p, true) === droneStateFilter);
    }
    if (monthFilter !== "all") {
      rows = rows.filter((p) => rowMonth(p) === monthFilter);
    }
    return rows;
  });

  function droneState(p: DashboardProject, normalize = false): string {
    const raw = p.drone_tickets?.[0]?.drone_state || "";
    return raw || (normalize ? "" : "—");
  }

  function rowMonth(p: DashboardProject): string {
    const iso = p.start_datetime || p.end_datetime || p.updated_at || "";
    if (!iso) return "";
    const d = new Date(iso);
    if (isNaN(d.getTime())) return "";
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
  }

  let availableMonths = $derived.by(() => {
    const set = new Set<string>();
    for (const p of projects) {
      const m = rowMonth(p);
      if (m) set.add(m);
    }
    return Array.from(set).sort();
  });

  let summary = $derived({
    total: visibleProjects.length,
    uat: visibleProjects.filter((p) => p.project_state === "UAT_PREPARE").length,
    prod: visibleProjects.filter((p) => p.project_state === "PROD_READY").length,
    impl: visibleProjects.filter((p) => p.project_state === "IMPLEMENTED").length,
    postponed: visibleProjects.filter((p) => p.project_state === "POSTPONED").length,
  });

  let crStateSummary = $derived.by(() => {
    const map: Record<string, number> = {};
    for (const p of visibleProjects) {
      const key = p.cr_state || "—";
      map[key] = (map[key] ?? 0) + 1;
    }
    return Object.entries(map).sort((a, b) => b[1] - a[1]);
  });

  let droneStateSummary = $derived.by(() => {
    const map: Record<string, number> = {};
    for (const p of visibleProjects) {
      const key = droneState(p) || "—";
      map[key] = (map[key] ?? 0) + 1;
    }
    return Object.entries(map).sort((a, b) => b[1] - a[1]);
  });

  let monthlySummary = $derived.by(() => {
    const map: Record<string, number> = {};
    for (const p of visibleProjects) {
      const m = rowMonth(p);
      if (!m) continue;
      map[m] = (map[m] ?? 0) + 1;
    }
    return Object.entries(map).sort((a, b) => a[0].localeCompare(b[0]));
  });

  async function loadReport() {
    loadState = "loading";
    errorMessage = "";
    errorCode = "";

    if (!isPywebviewReady()) {
      errorCode = BridgeErrorCode.BRIDGE_UNAVAILABLE;
      errorMessage = "pywebview bridge is not available. Running outside desktop shell.";
      loadState = "error";
      return;
    }

    const response = await callBridge<DashboardProject[]>(
      "report_filter_projects",
      yearFilter === "all" ? undefined : yearFilter,
      projectStateFilter === "all" ? undefined : projectStateFilter,
      crStateFilter === "all" ? undefined : crStateFilter,
      searchFilter || undefined,
    );

    if (!response.ok) {
      errorCode = response.error.code;
      errorMessage = response.error.message;
      loadState = "error";
      return;
    }

    projects = response.data ?? [];
    loadState = "loaded";
  }

  async function handleExportCsv() {
    if (!isPywebviewReady()) return;
    exportState = "saving";
    const response = await callBridge<string>(
      "report_export_csv",
      yearFilter === "all" ? undefined : yearFilter,
      projectStateFilter === "all" ? undefined : projectStateFilter,
      crStateFilter === "all" ? undefined : crStateFilter,
      searchFilter || undefined,
    );
    if (!response.ok || !response.data) {
      exportState = "idle";
      addToast(response.ok ? "No CSV data returned." : response.error.message, "error", 4000);
      return;
    }
    const suggested = `report_${new Date().toISOString().slice(0, 10)}.csv`;
    const saveResp = await callBridge<{ path: string | null; written: boolean }>("util_save_file", suggested, response.data);
    if (saveResp.ok && saveResp.data?.written && saveResp.data.path) {
      exportState = "idle";
      addToast(`Report saved: ${saveResp.data.path}`, "success", 4000);
    } else if (saveResp.ok && saveResp.data && saveResp.data.written === false) {
      const blob = new Blob([response.data], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = suggested;
      anchor.click();
      URL.revokeObjectURL(url);
      exportState = "idle";
      addToast("Report downloaded via browser", "success", 4000);
    } else {
      const blob = new Blob([response.data], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = suggested;
      anchor.click();
      URL.revokeObjectURL(url);
      exportState = "idle";
      addToast("Report downloaded via browser", "success", 4000);
    }
  }

  let yearsLoaded = false;
  async function loadYears() {
    if (yearsLoaded || !isPywebviewReady()) return;
    const resp = await callBridge<string[]>("year_list");
    if (resp.ok && resp.data) yearOptions = resp.data;
    yearsLoaded = true;
  }

  function handleApplyFilters() { fetchKey++; }
  function handleClearFilters() {
    yearFilter = "all";
    projectStateFilter = "all";
    crStateFilter = "all";
    droneStateFilter = "all";
    monthFilter = "all";
    searchFilter = "";
    fetchKey++;
  }

  $effect(() => {
    void fetchKey;
    void loadYears();
    loadReport();
  });

  // Prototype flow: filters/search apply directly. Search is debounced to avoid
  // a bridge call for every keystroke; selects share the same short delay.
  $effect(() => {
    void yearFilter;
    void projectStateFilter;
    void crStateFilter;
    void searchFilter;
    if (filterDebounce) clearTimeout(filterDebounce);
    filterDebounce = setTimeout(() => { fetchKey++; }, 200);
    return () => { if (filterDebounce) clearTimeout(filterDebounce); };
  });

  export function refresh() { fetchKey++; }

  function fmt(iso: string | null): string {
    if (!iso) return "—";
    const d = new Date(iso);
    if (isNaN(d.getTime())) return "—";
    return d.toLocaleDateString("en-GB", { weekday: "short", day: "2-digit", month: "short", year: "numeric" });
  }
</script>

<section class="screen active" id="screen-report">
  <div class="page-header">
    <div class="page-header-left">
      <span class="page-header-icon"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg></span>
      <h2 class="page-header-title">Report</h2>
    </div>
    <div class="page-header-actions">
      <label class="field-label" for="report-year">Year</label>
      <select id="report-year" class="combo" bind:value={yearFilter}>
        <option value="all">All Years</option>
        {#each yearOptions as y}<option value={y}>{y}</option>{/each}
      </select>
      <label class="field-label" for="report-month">Month</label>
      <select id="report-month" class="combo" bind:value={monthFilter}>
        <option value="all">All Months</option>
        {#each availableMonths as m}<option value={m}>{m}</option>{/each}
      </select>
      <label class="field-label" for="report-folder">Folder State</label>
      <select id="report-folder" class="combo" bind:value={projectStateFilter}>
        <option value="all">All Folder</option>
        {#each projectStates as ps}<option value={ps}>{ps.replace(/_/g, " ")}</option>{/each}
      </select>
      <label class="field-label" for="report-cr">CR State</label>
      <select id="report-cr" class="combo" bind:value={crStateFilter}>
        <option value="all">All CR</option>
        {#each crStates as cs}<option value={cs}>{cs.charAt(0) + cs.slice(1).toLowerCase()}</option>{/each}
      </select>
      <label class="field-label" for="report-drone">Drone State</label>
      <select id="report-drone" class="combo" bind:value={droneStateFilter}>
        <option value="all">All Drone</option>
        {#each droneStates as ds}<option value={ds}>{ds}</option>{/each}
      </select>
      <div class="search-shell"><span class="search-icon">⌕</span><input id="report-search" class="input" placeholder="Search report..." bind:value={searchFilter} /></div>
      <button class="btn-secondary" onclick={handleClearFilters}>Clear</button>
      <button class="btn-primary" disabled={exportState === "saving"} onclick={() => void handleExportCsv()}>{exportState === "saving" ? "Exporting…" : "Export CSV"}</button>
    </div>
  </div>

  {#if loadState === "loading"}
    <div class="dashboard-banner banner-loading" role="status" aria-live="polite"><span class="banner-icon">◌</span><span>Loading report data…</span></div>
  {:else if loadState === "error"}
    <div class="dashboard-banner banner-error" role="alert"><span class="banner-icon">⚠</span><div><p class="banner-title">Report unavailable</p><p class="banner-detail">{errorCode}: {errorMessage}</p></div></div>
  {/if}

  <div class="metric-row">
    <div class="metric-card"><div class="metric-icon">Σ</div><div><div class="metric-value">{summary.total}</div><div class="metric-label">Total</div></div></div>
    <div class="metric-card"><div class="metric-icon">U</div><div><div class="metric-value">{summary.uat}</div><div class="metric-label">UAT Prepare</div></div></div>
    <div class="metric-card"><div class="metric-icon">P</div><div><div class="metric-value">{summary.prod}</div><div class="metric-label">Prod Ready</div></div></div>
    <div class="metric-card"><div class="metric-icon">I</div><div><div class="metric-value">{summary.impl}</div><div class="metric-label">Implemented</div></div></div>
    <div class="metric-card"><div class="metric-icon">⏸</div><div><div class="metric-value">{summary.postponed}</div><div class="metric-label">Postponed</div></div></div>
  </div>

  <div class="split report-split">
    <div class="panel-card accent" style="flex:1">
      <div class="panel-title-row"><span class="panel-title-icon">▤</span><span class="panel-title">CR States</span><span class="panel-subtitle">{crStateSummary.length}</span></div>
      <div class="report-summary-list">
        {#each crStateSummary as [key, count]}<div class="report-summary-row"><span>{key.charAt(0) + key.slice(1).toLowerCase()}</span><strong>{count}</strong></div>{:else}<div class="table-empty">No CR data.</div>{/each}
      </div>
    </div>
    <div class="panel-card accent" style="flex:1">
      <div class="panel-title-row"><span class="panel-title-icon">◴</span><span class="panel-title">Drone States</span><span class="panel-subtitle">{droneStateSummary.length}</span></div>
      <div class="report-summary-list">
        {#each droneStateSummary as [key, count]}<div class="report-summary-row"><span>{key}</span><strong>{count}</strong></div>{:else}<div class="table-empty">No drone data.</div>{/each}
      </div>
    </div>
    <div class="panel-card accent" style="flex:1">
      <div class="panel-title-row"><span class="panel-title-icon">▦</span><span class="panel-title">Monthly Activity</span><span class="panel-subtitle">{monthlySummary.length}</span></div>
      <div class="report-summary-list">
        {#each monthlySummary as [key, count]}<div class="report-summary-row"><span>{key}</span><strong>{count}</strong></div>{:else}<div class="table-empty">No date data.</div>{/each}
      </div>
    </div>
  </div>

  <div class="panel-card accent" style="flex:1;">
    <div class="panel-title-row"><span class="panel-title-icon">▤</span><span class="panel-title">Report</span>{#if loadState === "loaded"}<span class="panel-subtitle">{visibleProjects.length} row{visibleProjects.length !== 1 ? "s" : ""}</span>{/if}</div>
    <div style="overflow:auto;">
      <table class="mini-table">
        <thead><tr><th>#</th><th>Project</th><th>CR Number</th><th>Folder State</th><th>CR State</th><th>Drone State</th><th>T-10</th><th>Last Updated</th></tr></thead>
        <tbody>
          {#if loadState === "loaded" && visibleProjects.length > 0}
            {#each visibleProjects as p, i}
              <tr><td>{i + 1}</td><td>{p.project_name}</td><td>{p.cr_number || "—"}</td><td>{p.project_state.replace(/_/g, " ")}</td><td>{p.cr_state.charAt(0) + p.cr_state.slice(1).toLowerCase()}</td><td>{droneState(p)}</td><td>{p.t10_status}</td><td>{fmt(p.updated_at)}</td></tr>
            {/each}
          {:else}
            <tr><td colspan="8" style="text-align:center;color:var(--text-secondary);padding:24px;">{loadState === "error" ? errorMessage : "No projects match the current filters."}</td></tr>
          {/if}
        </tbody>
      </table>
    </div>
  </div>
</section>

<style>
  .report-split { gap: 10px; }
  .report-summary-list { display:flex; flex-direction:column; gap:4px; max-height:180px; overflow:auto; }
  .report-summary-row { display:flex; justify-content:space-between; align-items:center; padding:5px 8px; background:var(--main-panel-bg); border:1px solid var(--soft-white-border); border-radius:5px; font-size:11px; font-weight:800; color:var(--text-strong); }
  .report-summary-row strong { color:var(--primary-red); }
  :global(.banner-success) { background:#dcfce7; color:#166534; border:1px solid #86efac; border-radius:6px; padding:8px 12px; font-weight:900; display:flex; align-items:center; gap:8px; }
</style>
