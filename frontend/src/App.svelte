<script lang="ts">
  let currentPage = $state("dashboard");
  const navItems = [
    { id: "dashboard", label: "Dashboard" },
    { id: "project-detail", label: "Project Details" },
    { id: "second-brain", label: "Second Brain" },
    { id: "report", label: "Report" },
    { id: "automations", label: "Automations" },
    { id: "settings", label: "Settings" },
  ];
</script>

<div class="flex h-screen overflow-hidden bg-sidebar-950 text-ink">
  <!-- Sidebar -->
  <aside class="flex w-56 shrink-0 flex-col bg-sidebar-900 text-gray-200">
    <!-- Brand -->
    <div class="border-b border-white/10 px-5 py-4">
      <p class="text-[10px] font-black uppercase tracking-[0.25em] text-dbs-red">
        Project Tracker
      </p>
      <h1 class="mt-0.5 text-lg font-black tracking-tight text-white">DBS</h1>
    </div>

    <!-- Nav -->
    <nav class="flex-1 space-y-0.5 px-3 py-3" aria-label="Main navigation">
      {#each navItems as item}
        <button
          class="w-full rounded-md px-3 py-2 text-left text-sm font-semibold transition-colors
                 {currentPage === item.id
                   ? 'bg-dbs-red text-white'
                   : 'text-gray-400 hover:bg-white/5 hover:text-gray-200'}"
          onclick={() => (currentPage = item.id)}
        >
          {item.label}
        </button>
      {/each}
    </nav>

    <!-- Notification panel -->
    <div class="mx-3 mb-3 mt-auto flex min-h-[120px] flex-col rounded-md border border-white/10 bg-sidebar-950/50 p-3">
      <div class="mb-2 flex items-center justify-between">
        <p class="text-[10px] font-black uppercase tracking-widest text-dbs-red">Notifications</p>
        <button class="text-[10px] font-semibold text-gray-500 hover:text-gray-300">Dismiss</button>
      </div>
      <div class="flex-1 space-y-2 overflow-y-auto">
        <article class="rounded bg-white/5 p-2">
          <p class="text-xs font-bold text-gray-300">No active notifications</p>
          <p class="text-[11px] text-gray-500">Backend notification panel is empty.</p>
        </article>
      </div>
    </div>

    <!-- Footer -->
    <div class="border-t border-white/10 px-5 py-3 text-[10px] font-semibold text-gray-600">
      v0.1.0 &middot; Svelte + Vite
    </div>
  </aside>

  <!-- Main workspace -->
  <main class="flex min-w-0 flex-1 flex-col bg-workspace">
    <!-- Header -->
    <header class="flex h-14 shrink-0 items-center bg-dbs-red px-5 text-white">
      <h2 class="text-lg font-black capitalize">
        {currentPage.replace("-", " ")}
      </h2>

      <div class="ml-auto flex items-center gap-2">
        <!-- Year select (static visual) -->
        <select
          class="h-8 rounded-md border-0 bg-white/15 px-3 text-xs font-bold text-white
                 focus:outline-none focus:ring-1 focus:ring-white/30"
        >
          <option>All years</option>
          <option>2025</option>
          <option>2026</option>
        </select>

        <!-- Search (static visual) -->
        <input
          type="text"
          class="h-8 w-56 rounded-md border-0 bg-white/15 px-3 text-xs font-bold text-white
                 placeholder:text-white/50 focus:outline-none focus:ring-1 focus:ring-white/30"
          placeholder="Search project, CR, Drone"
        />

        <!-- CR filter (static visual) -->
        <select
          class="h-8 rounded-md border-0 bg-white/15 px-3 text-xs font-bold text-white
                 focus:outline-none focus:ring-1 focus:ring-white/30"
        >
          <option>All CR states</option>
        </select>

        <!-- Add Project button -->
        <button
          class="h-8 rounded-md bg-sidebar-950 px-3 text-xs font-bold text-white
                 transition-colors hover:bg-sidebar-800"
        >
          + Add Project
        </button>

        <!-- Refresh button -->
        <button
          class="h-8 rounded-md bg-sidebar-950 px-4 text-xs font-bold text-white
                 transition-colors hover:bg-sidebar-800"
        >
          Refresh
        </button>
      </div>
    </header>

    <!-- Content area -->
    <div class="flex min-h-0 flex-1 flex-col gap-3 p-4">
      <!-- Status tabs bar -->
      <div class="rounded-md border border-border bg-white px-4 py-3">
        <div class="flex flex-wrap gap-2">
          {#each ["All", "UAT Prepare", "Prod Ready", "Implemented", "Postponed"] as status}
            <button
              class="rounded-md border border-border px-3 py-1 text-xs font-bold
                     {status === 'All'
                       ? 'border-dbs-red bg-dbs-red text-white'
                       : 'bg-white text-ink hover:bg-gray-50'}"
            >
              {status}
              <span class="ml-1 opacity-60">0</span>
            </button>
          {/each}
        </div>
      </div>

      <!-- Table placeholder -->
      <div class="flex min-h-0 flex-1 flex-col overflow-hidden rounded-md border border-border bg-white shadow-subtle">
        <!-- Table header -->
        <div
          class="grid shrink-0 grid-cols-[44px_1.3fr_0.9fr_0.9fr_0.9fr_0.9fr_0.9fr_160px]
                 bg-sidebar-900 text-xs font-black uppercase text-white"
        >
          <div class="p-2">No</div>
          <div class="p-2">Project</div>
          <div class="p-2">CR</div>
          <div class="p-2">CR State</div>
          <div class="p-2">Drone</div>
          <div class="p-2">Folder</div>
          <div class="p-2">Window</div>
          <div class="p-2">Actions</div>
        </div>

        <!-- Table body placeholder -->
        <div class="flex flex-1 items-center justify-center border-t border-border p-10">
          <div class="text-center">
            <p class="text-sm font-semibold text-muted">
              {currentPage} &mdash; placeholder content
            </p>
            <p class="mt-1 text-xs text-muted/70">
              No real API calls yet. Frontend scaffold only. Svelte + Vite + Tailwind v4.
            </p>
          </div>
        </div>
      </div>
    </div>
  </main>
</div>
