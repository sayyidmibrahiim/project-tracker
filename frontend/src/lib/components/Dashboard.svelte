<script lang="ts">
  import { onMount } from "svelte";
  import { callBridge, isPywebviewReady } from "../bridge";
  import type { DashboardProject, DashboardSummary } from "../types";
  import { BridgeErrorCode } from "../types";
  import ProjectTransitions from "./ProjectTransitions.svelte";

  // ── Props from parent ──
  let { selectedYear, searchQuery }: {
    selectedYear: string;
    searchQuery: string;
    [key: string]: unknown;
  } = $props();

  // ── State ──
  type LoadState = "idle" | "loading" | "error" | "loaded";

  let loadState: LoadState = $state("idle");
  let errorMessage: string = $state("");
  let errorCode: string = $state("");
  let activeStatus: string = $state("all");
  let fetchKey: number = $state(0);

  // Data from bridge
  let projects: DashboardProject[] = $state([]);
  let summary: DashboardSummary | null = $state(null);
  let isBridgeAvailable: boolean = $state(false);

  // ── Status tab definitions ──
  interface StatusTab {
    key: string;
    label: string;
    count: number;
  }

  let statuses: StatusTab[] = $derived([
    { key: "all", label: "All", count: (summary as DashboardSummary | null)?.total_projects ?? projects.length },
    { key: "UAT_PREPARE", label: "UAT Prepare", count: (summary as DashboardSummary | null)?.by_project_state?.["UAT_PREPARE"] ?? 0 },
    { key: "PROD_READY", label: "Prod Ready", count: (summary as DashboardSummary | null)?.by_project_state?.["PROD_READY"] ?? 0 },
    { key: "IMPLEMENTED", label: "Implemented", count: (summary as DashboardSummary | null)?.by_project_state?.["IMPLEMENTED"] ?? 0 },
    { key: "POSTPONED", label: "Postponed", count: (summary as DashboardSummary | null)?.by_project_state?.["POSTPONED"] ?? 0 },
  ]);

  // ── Filtered projects: status tab + search query (local) ──
  let filteredProjects: DashboardProject[] = $derived.by(() => {
    let result = activeStatus === "all" ? projects : projects.filter((p) => p.project_state === activeStatus);
    const q = searchQuery.trim().toLowerCase();
    if (q) {
      result = result.filter((p) => {
        const haystack = [
          p.project_name,
          p.cr_number,
          p.cr_state,
          p.project_state,
          p.year,
          p.project_path,
        ].join(" ").toLowerCase();
        return haystack.includes(q);
      });
    }
    return result;
  });

  // ── Columns ──
  const columns = [
    "No",
    "Main Project",
    "Sub Project",
    "Start Datetime",
    "End Datetime",
    "Drone Ticket",
    "Drone State",
    "CR Number",
    "CR State",
    "",
  ];

  // ── Mapper: DashboardProject → row display ──
  interface ProjectRow {
    no: number;
    name: string;
    folder: string;
    subProjects: string[];
    startDate: string;
    startTime: string;
    endDate: string;
    endTime: string;
    droneTickets: string[];
    droneStates: string[];
    crNumber: string;
    crState: string;
    alt: boolean;
  }

  function mapProjectToRow(p: DashboardProject, i: number): ProjectRow {
    const fmtDate = (iso: string | null, which: "date" | "time"): string => {
      if (!iso) return "—";
      try {
        const d = new Date(iso);
        if (isNaN(d.getTime())) return "—";
        if (which === "date") {
          return d.toLocaleDateString("en-GB", { weekday: "short", day: "2-digit", month: "short", year: "numeric" });
        }
        return d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
      } catch {
        return "—";
      }
    };

    return {
      no: i + 1,
      name: p.project_name || "Untitled",
      folder: `project folder · ${p.year || "—"}`,
      subProjects: p.project_name ? [p.project_name] : ["—"],
      startDate: fmtDate(p.start_datetime, "date"),
      startTime: fmtDate(p.start_datetime, "time"),
      endDate: fmtDate(p.end_datetime, "date"),
      endTime: fmtDate(p.end_datetime, "time"),
      droneTickets: p.cr_number ? [p.cr_number] : ["—"],
      droneStates: ["—"],
      crNumber: p.cr_number || "—",
      crState: p.cr_state || "—",
      alt: i % 2 === 1,
    };
  }

  // ── Load dashboard data ──
  async function loadDashboard() {
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

    const yearParam = selectedYear === "all" ? undefined : selectedYear;
    const response = await callBridge<DashboardProject[]>("dashboard_list_projects", yearParam);

    if (!response.ok) {
      errorCode = response.error.code;
      errorMessage = response.error.message;
      loadState = "error";
      return;
    }

    projects = response.data ?? [];
    loadState = "loaded";
  }

  // ── Re-fetch when year or refresh changes ──
  $effect(() => {
    // Track selectedYear + fetchKey to trigger re-fetch
    void selectedYear;
    void fetchKey;
    loadDashboard();
  });

  // Expose refresh for parent
  export function refresh() {
    fetchKey++;
  }
</script>

<div class="dashboard-screen">
  <!-- Loading state -->
  {#if loadState === "loading"}
    <div class="dashboard-banner banner-loading">
      <span class="banner-icon">◌</span>
      <span>Loading dashboard data…</span>
    </div>
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
          <div class="table-empty">
            <p class="empty-title">Loading…</p>
            <p class="empty-sub">Fetching project data from backend.</p>
          </div>
        </div>
      </div>
    </div>

  <!-- Error state -->
  {:else if loadState === "error"}
    <div class="dashboard-banner banner-error">
      <span class="banner-icon">⚠</span>
      <div>
        <p class="banner-title">Dashboard unavailable</p>
        <p class="banner-detail">{errorCode}: {errorMessage}</p>
      </div>
    </div>
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
          <div class="table-empty">
            <p class="empty-title">No data</p>
            <p class="empty-sub">Backend returned error: {errorMessage}</p>
          </div>
        </div>
      </div>
    </div>

  <!-- Loaded state -->
  {:else if loadState === "loaded"}
    <!-- Status filter bar -->
    <div class="filter-frame">
      <div class="status-inner">
        {#each statuses as s}
          <button
            class="status-tab"
            class:active={activeStatus === s.key}
            onclick={() => (activeStatus = s.key)}
          >
            {s.label} ({s.count})
          </button>
        {/each}
        <span class="project-count">{filteredProjects.length} project(s)</span>
      </div>
    </div>

    <!-- Table card -->
    <div class="table-card">
      <div class="table-card-head">
        <span class="table-head-icon">▦</span>
        <span>CR - Project Summary Table</span>
      </div>

      <div class="table-scroll">
        <div class="project-table">
          <!-- Header -->
          <div class="table-header-row">
            {#each columns as col}
              <div class="table-header-cell">{col}</div>
            {/each}
          </div>

          {#if filteredProjects.length === 0}
            <div class="table-empty">
              <p class="empty-title">No projects found</p>
              <p class="empty-sub">Add projects or adjust filters to see results.</p>
            </div>
          {:else}
            {#each filteredProjects as p, idx}
              {@const row = mapProjectToRow(p, idx)}
              <div class="project-row" class:alt={row.alt}>
                <div class="table-cell cell-center"><strong>{row.no}</strong></div>
                <div class="table-cell cell-top">
                  <div>
                    <div class="project-name" class:dark={row.alt}>{row.name}</div>
                    <div class="project-folder">{row.folder}</div>
                  </div>
                </div>
                <div class="table-cell">
                  <div class="stack-lines">
                    {#each row.subProjects as sp}
                      <div class="stack-line"><span class="stack-text">{sp}</span></div>
                    {/each}
                  </div>
                </div>
                <div class="table-cell cell-center">
                  {#if row.startDate === "—"}
                    <span class="muted-text">—</span>
                  {:else}
                    <div class="date-block">{row.startDate}<br /><span class="date-time">{row.startTime}</span></div>
                  {/if}
                </div>
                <div class="table-cell cell-center">
                  {#if row.endDate === "—"}
                    <span class="muted-text">—</span>
                  {:else}
                    <div class="date-block">{row.endDate}<br /><span class="date-time">{row.endTime}</span></div>
                  {/if}
                </div>
                <div class="table-cell">
                  <div class="stack-lines">
                    {#each row.droneTickets as dt}
                      <div class="stack-line"><input class="link-edit" value={dt} readonly /></div>
                    {/each}
                  </div>
                </div>
                <div class="table-cell">
                  <div class="stack-lines">
                    {#each row.droneStates as ds}
                      <div class="stack-line"><span class="state-combo">{ds}</span></div>
                    {/each}
                  </div>
                </div>
                <div class="table-cell"><input class="link-edit" value={row.crNumber} readonly /></div>
                <div class="table-cell"><span class="state-combo">{row.crState}</span></div>
                <div class="table-cell cell-center">
                  <ProjectTransitions
                    projectPath={p.project_path}
                    projectState={p.project_state}
                    projectName={p.project_name}
                    variant="menu"
                    onApplied={() => refresh()}
                  />
                </div>
              </div>
            {/each}
          {/if}
        </div>
      </div>
    </div>

  <!-- Idle (initial) -->
  {:else}
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
          <div class="table-empty">
            <p class="empty-title">Initializing…</p>
          </div>
        </div>
      </div>
    </div>
  {/if}
</div>
