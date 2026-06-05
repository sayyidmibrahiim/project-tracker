<script lang="ts">
  let {
    currentPage,
    selectedYear,
    searchQuery,
    showDashboardControls = false,
    onYearChange,
    onSearchChange,
    onRefresh,
  }: {
    currentPage: string;
    selectedYear: string;
    searchQuery: string;
    showDashboardControls?: boolean;
    onYearChange: (year: string) => void;
    onSearchChange: (q: string) => void;
    onRefresh: () => void;
  } = $props();

  const years = ["2026", "2025", "2024", "all"];
  const pageTitles: Record<string, string> = {
    dashboard: "Dashboard",
    "project-detail": "Project Details",
    "second-brain": "Second Brain",
    report: "Report",
    automations: "Automations",
    settings: "Settings",
  };

  function handleYearInput(e: Event) {
    const target = e.target as HTMLSelectElement;
    onYearChange(target.value);
  }

  function handleSearchInput(e: Event) {
    const target = e.target as HTMLInputElement;
    onSearchChange(target.value);
  }
</script>

<header class="app-header">
  <div class="header-title-box">
    <div class="page-title-divider"></div>
    <h1 class="page-title">{pageTitles[currentPage] ?? currentPage.replace("-", " ")}</h1>
  </div>

  <div class="header-center">
    <div class="datetime-badge">
      <span class="datetime-icon">▣</span>
      <span>Mon, 01 Jun 2026 14:32:11</span>
    </div>
  </div>

  <div class="header-actions">
    {#if showDashboardControls}
      <select class="header-combo" aria-label="Year" value={selectedYear} onchange={handleYearInput}>
        {#each years as y}
          <option value={y}>{y === "all" ? "All years" : y}</option>
        {/each}
      </select>
      <div class="header-search">
        <span class="search-icon">⌕</span>
        <input class="header-input" placeholder="Search projects here..." value={searchQuery} oninput={handleSearchInput} />
      </div>
      <select class="header-combo" aria-label="Filter">
        <option>All CR</option>
        <option>Pending</option>
        <option>Approved</option>
      </select>
      <button class="btn-black">＋ Add Project</button>
    {/if}
    <button class="btn-refresh" title="Refresh Data" onclick={() => onRefresh()}>↻</button>
  </div>
</header>
