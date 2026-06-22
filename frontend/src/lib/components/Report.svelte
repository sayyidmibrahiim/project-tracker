<script lang="ts">
  import { callBridge, isPywebviewReady } from "../bridge";
  import { BridgeErrorCode } from "../types";
  import type { DashboardProject } from "../types";

  let _props: Record<string, unknown> = $props();

  type LoadState = "idle" | "loading" | "error" | "loaded";
  let loadState: LoadState = $state("idle");
  let errorCode: string = $state("");
  let errorMessage: string = $state("");

  let yearFilter: string = $state("all");
  let projectStateFilter: string = $state("all");
  let crStateFilter: string = $state("all");
  let searchFilter: string = $state("");
  let fetchKey: number = $state(0);
  let filterDebounce: ReturnType<typeof setTimeout> | null = null;
  let projects: DashboardProject[] = $state([]);

  const projectStates = ["UAT_PREPARE", "PROD_READY", "IMPLEMENTED", "POSTPONED"];
  const crStates = ["PENDING SUBMISSION", "PENDING APPROVAL", "APPROVED", "IN-PROGRESS", "FINISHED", "CANCELED", "REOPEN"];
  // Years are loaded live from `year_list` (real filesystem scan), not hardcoded.
  let yearOptions: string[] = $state([]);

  let summary = $derived({
    total: projects.length,
    uat: projects.filter((p) => p.project_state === "UAT_PREPARE").length,
    prod: projects.filter((p) => p.project_state === "PROD_READY").length,
    impl: projects.filter((p) => p.project_state === "IMPLEMENTED").length,
    postponed: projects.filter((p) => p.project_state === "POSTPONED").length,
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
    const response = await callBridge<string>(
      "report_export_csv",
      yearFilter === "all" ? undefined : yearFilter,
      projectStateFilter === "all" ? undefined : projectStateFilter,
      crStateFilter === "all" ? undefined : crStateFilter,
      searchFilter || undefined,
    );
    if (!response.ok || !response.data) return;
    const blob = new Blob([response.data], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `report_${new Date().toISOString().slice(0, 10)}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
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

  function droneState(p: DashboardProject): string {
    return p.drone_tickets?.[0]?.drone_state || "—";
  }
</script>

<section class="screen active" id="screen-report">
  <div class="filter-frame">
    <div class="status-inner">
      <label class="field-label" for="report-year">Year</label>
      <select id="report-year" class="combo" bind:value={yearFilter}>
        <option value="all">All Years</option>
        {#each yearOptions as y}<option value={y}>{y}</option>{/each}
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
      <div class="search-shell"><span class="search-icon">⌕</span><input id="report-search" class="input" placeholder="Search report..." bind:value={searchFilter} /></div>
      <button class="btn-secondary" onclick={handleClearFilters}>Clear</button>
      <button class="btn-primary" onclick={() => void handleExportCsv()}>Export CSV</button>
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

  <div class="panel-card accent" style="flex:1;">
    <div class="panel-title-row"><span class="panel-title-icon">▤</span><span class="panel-title">Report</span>{#if loadState === "loaded"}<span class="panel-subtitle">{projects.length} row{projects.length !== 1 ? "s" : ""}</span>{/if}</div>
    <div style="overflow:auto;">
      <table class="mini-table">
        <thead><tr><th>Year</th><th>Project</th><th>Folder State</th><th>CR State</th><th>Drone State</th><th>Start</th><th>End</th></tr></thead>
        <tbody>
          {#if loadState === "loaded" && projects.length > 0}
            {#each projects as p}
              <tr><td>{p.year}</td><td>{p.project_name}</td><td>{p.project_state.replace(/_/g, " ")}</td><td>{p.cr_state.charAt(0) + p.cr_state.slice(1).toLowerCase()}</td><td>{droneState(p)}</td><td>{fmt(p.start_datetime)}</td><td>{fmt(p.end_datetime)}</td></tr>
            {/each}
          {:else}
            <tr><td colspan="7" style="text-align:center;color:var(--text-secondary);padding:24px;">{loadState === "error" ? errorMessage : "No projects match the current filters."}</td></tr>
          {/if}
        </tbody>
      </table>
    </div>
  </div>
</section>
