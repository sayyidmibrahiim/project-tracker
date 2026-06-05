<script lang="ts">
  const statuses = [
    { key: "all", label: "All", count: 2 },
    { key: "uat_prepare", label: "UAT Prepare", count: 2 },
    { key: "prod_ready", label: "Prod Ready", count: 0 },
    { key: "implemented", label: "Implemented", count: 0 },
    { key: "postponed", label: "Postponed", count: 0 },
  ];

  let activeStatus = $state("all");

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

  const projects = [
    {
      no: 1,
      name: "SOP CR",
      folder: "project folder · 2026",
      subProjects: ["a", "b", "c", "sub project a"],
      startDate: "Fri, 22 May 2026",
      startTime: "00:00:00",
      endDate: "Sat, 10 Jan 2026",
      endTime: "00:00:00",
      droneTickets: ["D-SSIDBI-159", "D-SSIDBI-160", "D-SSIDBI-161", "D-SSIDBI-162"],
      droneStates: ["UAT", "UAT", "UAT", "UAT"],
      crNumber: "CR202604209900114",
      crState: "PENDING SUBMISSION",
      alt: false,
    },
    {
      no: 2,
      name: "project_tracker",
      folder: "project folder · 2026",
      subProjects: ["—"],
      startDate: "—",
      startTime: "",
      endDate: "—",
      endTime: "",
      droneTickets: ["—"],
      droneStates: ["UAT"],
      crNumber: "—",
      crState: "PENDING SUBMISSION",
      alt: true,
    },
  ];
</script>

<div class="dashboard-screen">
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
      <span class="project-count">2 project(s)</span>
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

        <!-- Rows -->
        {#each projects as p}
          <div class="project-row" class:alt={p.alt}>
            <!-- No -->
            <div class="table-cell cell-center">
              <strong>{p.no}</strong>
            </div>

            <!-- Main Project -->
            <div class="table-cell cell-top">
              <div>
                <div class="project-name" class:dark={p.alt}>{p.name}</div>
                <div class="project-folder">{p.folder}</div>
              </div>
            </div>

            <!-- Sub Project (stacked) -->
            <div class="table-cell">
              <div class="stack-lines">
                {#each p.subProjects as sp}
                  <div class="stack-line"><span class="stack-text">{sp}</span></div>
                {/each}
              </div>
            </div>

            <!-- Start Datetime -->
            <div class="table-cell cell-center">
              {#if p.startDate === "—"}
                <span class="muted-text">—</span>
              {:else}
                <div class="date-block">
                  {p.startDate}<br /><span class="date-time">{p.startTime}</span>
                </div>
              {/if}
            </div>

            <!-- End Datetime -->
            <div class="table-cell cell-center">
              {#if p.endDate === "—"}
                <span class="muted-text">—</span>
              {:else}
                <div class="date-block">
                  {p.endDate}<br /><span class="date-time">{p.endTime}</span>
                </div>
              {/if}
            </div>

            <!-- Drone Ticket (stacked) -->
            <div class="table-cell">
              <div class="stack-lines">
                {#each p.droneTickets as dt}
                  <div class="stack-line">
                    <input class="link-edit" value={dt} readonly />
                  </div>
                {/each}
              </div>
            </div>

            <!-- Drone State (stacked combo chips) -->
            <div class="table-cell">
              <div class="stack-lines">
                {#each p.droneStates as ds}
                  <div class="stack-line">
                    <span class="state-combo">{ds}</span>
                  </div>
                {/each}
              </div>
            </div>

            <!-- CR Number -->
            <div class="table-cell">
              <input class="link-edit" value={p.crNumber} readonly />
            </div>

            <!-- CR State -->
            <div class="table-cell">
              <span class="state-combo">{p.crState}</span>
            </div>

            <!-- Actions -->
            <div class="table-cell cell-center">
              <button class="cell-action">⋮</button>
            </div>
          </div>
        {/each}
      </div>
    </div>
  </div>
</div>
