<script lang="ts">
  let currentPage = $state("dashboard");
</script>

<div class="flex h-screen overflow-hidden">
  <!-- Sidebar placeholder -->
  <aside class="w-64 bg-gray-900 text-gray-100 flex flex-col shrink-0">
    <div class="px-4 py-5 border-b border-gray-800">
      <h1 class="text-lg font-semibold tracking-tight">Project Tracker DBS</h1>
    </div>
    <nav class="flex-1 px-3 py-4 space-y-1" aria-label="Main navigation">
      {#each [
        { id: "dashboard", label: "Dashboard" },
        { id: "second-brain", label: "Second Brain" },
        { id: "report", label: "Report" },
        { id: "automations", label: "Automations" },
        { id: "settings", label: "Settings" },
      ] as item}
        <button
          class="w-full text-left px-3 py-2 rounded text-sm transition-colors
                 {currentPage === item.id
                   ? 'bg-gray-700 text-white'
                   : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'}"
          onclick={() => (currentPage = item.id)}
        >
          {item.label}
        </button>
      {/each}
    </nav>
    <div class="px-4 py-3 border-t border-gray-800 text-xs text-gray-500">
      v0.1.0 &middot; Svelte + Vite
    </div>
  </aside>

  <!-- Main content -->
  <main class="flex-1 flex flex-col min-w-0">
    <!-- Header placeholder -->
    <header class="h-14 border-b border-gray-200 flex items-center px-6 bg-white shrink-0">
      <h2 class="text-base font-medium text-gray-800 capitalize">{currentPage.replace("-", " ")}</h2>
      <span class="ml-auto text-xs text-gray-400">{new Date().toLocaleString()}</span>
    </header>

    <!-- Content area -->
    <div class="flex-1 overflow-auto p-6">
      <div class="rounded-lg border border-dashed border-gray-300 bg-white p-8 text-center">
        <p class="text-gray-500 text-sm">Phase D.1 scaffold &mdash; {currentPage} page placeholder</p>
        <p class="text-gray-400 text-xs mt-1">No API calls yet. Frontend scaffold only.</p>
      </div>
    </div>
  </main>
</div>
