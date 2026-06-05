<script lang="ts">
  import Sidebar from "./lib/components/Sidebar.svelte";
  import Header from "./lib/components/Header.svelte";
  import Dashboard from "./lib/components/Dashboard.svelte";

  let currentPage = $state("dashboard");

  function navigate(id: string) {
    currentPage = id;
  }
</script>

<div class="app-shell">
  <Sidebar {currentPage} onNavigate={navigate} />
  <main class="main-area">
    <Header {currentPage} />
    {#if currentPage === "dashboard"}
      <Dashboard />
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
