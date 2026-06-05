<script lang="ts">
  let { currentPage }: { currentPage: string } = $props();
</script>

<header class="app-header">
  <div class="header-title-box">
    <div class="page-title-divider"></div>
    <h1 class="page-title">{currentPage.replace("-", " ")}</h1>
  </div>

  <div class="header-center">
    <div class="datetime-badge">
      <span class="datetime-icon">▣</span>
      <span>Mon, 01 Jun 2026 14:32:11</span>
    </div>
  </div>

  <div class="header-actions">
    <select class="header-combo" aria-label="Year">
      <option>2026</option>
      <option>2025</option>
      <option>2024</option>
    </select>
    <div class="header-search">
      <span class="search-icon">⌕</span>
      <input class="header-input" placeholder="Search projects here..." />
    </div>
    <select class="header-combo" aria-label="Filter">
      <option>All CR</option>
      <option>Pending</option>
      <option>Approved</option>
    </select>
    <button class="btn-black">＋ Add Project</button>
    <button class="btn-refresh" title="Refresh Data">↻</button>
  </div>
</header>
