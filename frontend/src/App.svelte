<script lang="ts">
  import Sidebar from "./lib/components/Sidebar.svelte";
  import Header from "./lib/components/Header.svelte";
  import Dashboard from "./lib/components/Dashboard.svelte";

  let currentPage = $state("dashboard");
  let selectedYear = $state("all");
  let searchQuery = $state("");

  function navigate(id: string) {
    currentPage = id;
  }

  function handleYearChange(year: string) {
    selectedYear = year;
  }

  function handleSearchChange(q: string) {
    searchQuery = q;
  }

  function handleRefresh() {
    // Trigger re-fetch via key increment could work, but simpler: just
    // re-mount/re-trigger $effect in Dashboard by incrementing key.
    // For now we increment a counter that $effect watches.
    refreshKey++;
  }

  let refreshKey = $state(0);
</script>

<div class="app-shell">
  <Sidebar {currentPage} onNavigate={navigate} />
  <main class="main-area">
    <Header
      {currentPage}
      {selectedYear}
      {searchQuery}
      onYearChange={handleYearChange}
      onSearchChange={handleSearchChange}
      onRefresh={handleRefresh}
    />
    {#if currentPage === "dashboard"}
      <Dashboard {selectedYear} {searchQuery} key={refreshKey} />
    {:else}
      <div class="placeholder-screen">
        <div class="placeholder-card">
          <p class="placeholder-title">{currentPage.replace("-", " ")}</p>
          <p class="placeholder-sub">Page not yet implemented. Static scaffold only.</p>
        </div>
      </div>
    {/if}
  </main>
</div>
