<script lang="ts">
  import { callBridge, isPywebviewReady } from "../bridge";
  import type { DashboardProject } from "../types";
  import { BridgeErrorCode } from "../types";

  let {
    selectedYear,
    searchQuery,
  }: {
    selectedYear: string;
    searchQuery: string;
    [key: string]: unknown;
  } = $props();

  type LoadState = "idle" | "loading" | "error" | "loaded";
  let loadState: LoadState = $state("idle");
  let errorMessage: string = $state("");
  let errorCode: string = $state("");

  // ── Filter state (local, not App-level) ──
  let yearFilter: string = $state("all");
  let projectStateFilter: string = $state("all");
  let crStateFilter: string = $state("all");
  let searchFilter: string = $state("");
  let fetchKey: number = $state(0);

  // ── Data ──
  let projects: DashboardProject[] = $state([]);
  let isBridgeAvailable: boolean = $state(false);

  const projectStates = ["UAT_PREPARE", "PROD_READY", "IMPLEMENTED", "POSTPONED", "CANCELED"];
  const crStates = [
    "PENDING SUBMISSION", "PENDING APPROVAL", "APPROVED",
    "IN-PROGRESS", "FINISHED", "POSTPONED", "CANCELED",
  ];
  const yearOptions = ["2026", "2025", "2024"];

  // ── Derived KPI summary ──
  let summary = $derived({
    total: projects.length,
    uat: projects.filter((p) => p.project_state === "UAT_PREPARE").length,
    prod: projects.filter((p) => p.project_state === "PROD_READY").length,
    impl: projects.filter((p) => p.project_state === "IMPLEMENTED").length,
    postponed: projects.filter((p) => p.project_state === "POSTPONED").length,
    canceled: projects.filter((p) => p.project_state === "CANCELED").length,
  });

  // ── Table columns (available fields from DashboardProject DTO) ──
  const columns = [
    "No", "Project Name", "Year", "Folder State",
    "CR Number", "CR State", "Start DateTime", "End DateTime",
    "T-10 Status", "Drone Tickets", "Project Path",
  ];

  // ── Bridge load ──
  async function loadReport() {
    loadState = "loading";
    errorMessage = "";
    errorCode = "";

    if (!isPywebviewReady()) {
      isBridgeAvailable = false;
      errorCode = BridgeErrorCode.BRIDGE_UNAVAILABLE;
      errorMessage = "pywebview bridge is not available. Running outside desktop shell.";
      loadState = "error";
      return;
    }

    isBridgeAvailable = true;

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

  function handleApplyFilters() {
    fetchKey++;
  }

  function handleClearFilters() {
    yearFilter = "all";
    projectStateFilter = "all";
    crStateFilter = "all";
    searchFilter = "";
    fetchKey++;
  }

  // ── Re-fetch on fetchKey ──
  $effect(() => {
    void fetchKey;
    loadReport();
  });

  export function refresh() {
    fetchKey++;
  }

  // ── Row mapper ──
  function mapToRow(p: DashboardProject, i: number) {
    const fmt = (iso: string | null): string => {
      if (!iso) return "—";
      try {
        const d = new Date(iso);
        if (isNaN(d.getTime())) return "—";
        return (
          d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" }) +
          " " +
          d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })
        );
      } catch {
        return "—";
      }
    };
    return {
      no: i + 1,
      name: p.project_name || "Untitled",
      year: p.year,
      state: p.project_state,
      crNumber: p.cr_number || "—",
      crState: p.cr_state,
      start: fmt(p.start_datetime),
      end: fmt(p.end_datetime),
      t10: p.t10_status,
      droneCount: String(p.drone_ticket_count),
      path: p.project_path,
      alt: i % 2 === 1,
    };
  }
</script>

<div class="report-screen">
  <!-- ── Loading banner ── -->
  {#if loadState === "loading"}
    <div class="dashboard-banner banner-loading">
      <span class="banner-icon">◌</span>
      <span>Loading report data…</span>
    </div>

  <!-- ── Error banner ── -->
  {:else if loadState === "error"}
    <div class="dashboard-banner banner-error">
      <span class="banner-icon">⚠</span>
      <div>
        <p class="banner-title">Report unavailable</p>
        <p class="banner-detail">{errorCode}: {errorMessage}</p>
      </div>
    </div>

  <!-- ── Loaded / idle ── -->
  {:else}
    <!-- KPI row -->
    <div class="report-kpi-row">
      <div class="report-kpi-card">
        <span class="kpi-value">{summary.total}</span>
        <span class="kpi-label">Total CR</span>
      </div>
      <div class="report-kpi-card">
        <span class="kpi-value">{summary.uat}</span>
        <span class="kpi-label">UAT Prepare</span>
      </div>
      <div class="report-kpi-card">
        <span class="kpi-value">{summary.prod}</span>
        <span class="kpi-label">PROD Ready</span>
      </div>
      <div class="report-kpi-card">
        <span class="kpi-value">{summary.impl}</span>
        <span class="kpi-label">Implemented</span>
      </div>
      <div class="report-kpi-card">
        <span class="kpi-value">{summary.postponed}</span>
        <span class="kpi-label">Postponed</span>
      </div>
      <div class="report-kpi-card kpi-canceled">
        <span class="kpi-value">{summary.canceled}</span>
        <span class="kpi-label">Canceled</span>
      </div>
    </div>

    <!-- Filter row -->
    <div class="report-filter-row">
      <select class="header-combo" bind:value={yearFilter}>
        <option value="all">All Years</option>
        {#each yearOptions as y}
          <option value={y}>{y}</option>
        {/each}
      </select>
      <select class="header-combo" bind:value={projectStateFilter}>
        <option value="all">All States</option>
        {#each projectStates as ps}
          <option value={ps}>{ps.replace(/_/g, " ")}</option>
        {/each}
      </select>
      <select class="header-combo" bind:value={crStateFilter}>
        <option value="all">All CR States</option>
        {#each crStates as cs}
          <option value={cs}>{cs}</option>
        {/each}
      </select>
      <div class="header-search">
        <span class="search-icon">⌕</span>
        <input
          class="header-input"
          placeholder="Search projects…"
          bind:value={searchFilter}
        />
      </div>
      <button class="btn-black" onclick={handleApplyFilters}>Apply</button>
      <button class="report-btn-clear" onclick={handleClearFilters}>Clear</button>
      <button class="btn-black report-export-btn" onclick={handleExportCsv}>
        Export CSV
      </button>
      <span class="project-count">{projects.length} project(s)</span>
    </div>
  {/if}

  <!-- ── Table card (always rendered) ── -->
  <div class="table-card">
    <div class="table-card-head">
      <span class="table-head-icon">▤</span>
      <span>Report — Deployment Summary</span>
    </div>

    <div class="table-scroll">
      <div class="report-table-wrapper">
        <!-- Header -->
        <div class="report-table-header-row">
          {#each columns as col}
            <div class="table-header-cell">{col}</div>
          {/each}
        </div>

        {#if loadState === "loading" || loadState === "idle"}
          <div class="table-empty">
            <p class="empty-title">
              {loadState === "loading" ? "Loading…" : "Apply filters to load report"}
            </p>
            <p class="empty-sub">
              {loadState === "loading"
                ? "Fetching project data from backend."
                : "Select filters and click Apply."}
            </p>
          </div>
        {:else if loadState === "error"}
          <div class="table-empty">
            <p class="empty-title">Unable to load report</p>
            <p class="empty-sub">{errorMessage}</p>
          </div>
        {:else if projects.length === 0}
          <div class="table-empty">
            <p class="empty-title">No projects match</p>
            <p class="empty-sub">Adjust your filters to see results.</p>
          </div>
        {:else}
          {#each projects as p, idx}
            {@const row = mapToRow(p, idx)}
            <div class="report-table-row" class:alt={row.alt}>
              <div class="table-cell cell-center"><strong>{row.no}</strong></div>
              <div class="table-cell cell-top">
                <div class="project-name">{row.name}</div>
              </div>
              <div class="table-cell cell-center">{row.year}</div>
              <div class="table-cell cell-center">
                <span class="state-combo">{row.state}</span>
              </div>
              <div class="table-cell cell-center">
                <span class="report-cr-number">{row.crNumber}</span>
              </div>
              <div class="table-cell cell-center">
                <span class="state-combo">{row.crState}</span>
              </div>
              <div class="table-cell cell-center">
                <span class="muted-text">{row.start}</span>
              </div>
              <div class="table-cell cell-center">
                <span class="muted-text">{row.end}</span>
              </div>
              <div class="table-cell cell-center">{row.t10}</div>
              <div class="table-cell cell-center">{row.droneCount}</div>
              <div class="table-cell">
                <span class="report-path">{row.path}</span>
              </div>
            </div>
          {/each}
        {/if}
      </div>
    </div>
  </div>
</div>
