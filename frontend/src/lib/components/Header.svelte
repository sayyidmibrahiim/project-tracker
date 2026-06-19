<script lang="ts">
  import { onMount, onDestroy } from "svelte";

  let {
    currentPage,
    selectedYear,
    searchQuery,
    years = [],
    showDashboardControls = false,
    onYearChange,
    onSearchChange,
    onRefresh,
    onAddProject = () => {},
    onAddYear = async () => null,
    openAddYearToken = 0,
  }: {
    currentPage: string;
    selectedYear: string;
    searchQuery: string;
    years?: string[];
    showDashboardControls?: boolean;
    onYearChange: (year: string) => void;
    onSearchChange: (q: string) => void;
    onRefresh: () => void;
    onAddProject?: () => void;
    onAddYear?: (year: string) => Promise<string | null>;
    openAddYearToken?: number;
  } = $props();

  const currentYear = new Date().getFullYear();
  let addYearOpen = $state(false);
  let addYearValue = $state(String(currentYear + 1));
  let addYearError = $state("");
  let addYearBusy = $state(false);
  let addYearWarn = $derived(Number(addYearValue) > currentYear + 2);
  let lastAddYearToken = 0;

  $effect(() => {
    if (openAddYearToken > lastAddYearToken) {
      lastAddYearToken = openAddYearToken;
      addYearError = "";
      addYearValue = String(currentYear + 1);
      addYearOpen = true;
    }
  });

  const headerConfig: Record<string, { title: string; rich: boolean; search: boolean; filter: boolean; add: boolean; placeholder: string }> = {
    dashboard: { title: "Dashboard.", rich: true, search: true, filter: true, add: true, placeholder: "Search projects here..." },
    "project-detail": { title: "Project Details.", rich: true, search: true, filter: false, add: true, placeholder: "Search project details..." },
    "second-brain": { title: "Second Brain.", rich: false, search: false, filter: false, add: false, placeholder: "" },
    report: { title: "Report.", rich: false, search: false, filter: false, add: false, placeholder: "" },
    automations: { title: "Automations.", rich: false, search: false, filter: false, add: false, placeholder: "" },
    settings: { title: "Settings.", rich: false, search: false, filter: false, add: false, placeholder: "" },
  };

  let cfg = $derived(headerConfig[currentPage] ?? headerConfig.dashboard);

  function formatNow(): string {
    const d = new Date();
    const date = d.toLocaleDateString("en-US", { weekday: "short", day: "2-digit", month: "short", year: "numeric" });
    const time = d.toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
    return `${date} ${time}`;
  }

  let nowText = $state(formatNow());
  let clockTimer: ReturnType<typeof setInterval> | undefined;
  let spinning = $state(false);
  let searchTimer: ReturnType<typeof setTimeout> | undefined;

  function triggerRefresh() {
    onRefresh();
    spinning = true;
    setTimeout(() => (spinning = false), 650);
  }

  function toggleAddYear() {
    addYearError = "";
    addYearValue = String(currentYear + 1);
    addYearOpen = !addYearOpen;
  }

  async function submitAddYear() {
    addYearError = "";
    addYearBusy = true;
    const err = await onAddYear(addYearValue.trim());
    addYearBusy = false;
    if (err) {
      addYearError = err;
      return;
    }
    addYearOpen = false;
  }

  function handleYearInput(e: Event) {
    onYearChange((e.target as HTMLSelectElement).value);
  }

  function handleSearchInput(e: Event) {
    const value = (e.target as HTMLInputElement).value;
    if (searchTimer) clearTimeout(searchTimer);
    searchTimer = setTimeout(() => onSearchChange(value), 200);
  }

  onMount(() => {
    clockTimer = setInterval(() => (nowText = formatNow()), 1000);
  });
  onDestroy(() => {
    if (clockTimer) clearInterval(clockTimer);
    if (searchTimer) clearTimeout(searchTimer);
  });
</script>

<header class="app-header">
  <div class="header-title-box">
    <div class="page-title-divider"></div>
    <h1 class="page-title">{cfg.title}</h1>
  </div>

  <div class="header-title-box header-center">
    <div class="date-time-badge">
      <span class="icon datetime-icon">▣</span>
      <span>{nowText}</span>
    </div>
  </div>

  <div class="header-action-box header-actions" class:hidden={!cfg.rich}>
    {#if cfg.rich}
      <div class="header-year" class:hidden={!showDashboardControls}>
        <select class="combo" aria-label="Year" value={selectedYear} onchange={handleYearInput}>
          <option value="all">All years</option>
          {#each years as y}
            <option value={y}>{y}</option>
          {/each}
        </select>
        <button class="btn-tiny" type="button" aria-label="Add year" title="Add year folder" onclick={toggleAddYear}>＋</button>
        {#if addYearOpen}
          <div class="header-year-pop">
            <label class="field-label">New year
              <input class="input" type="number" bind:value={addYearValue} min="2000" max="2100" />
            </label>
            {#if addYearWarn}<p class="hy-warn">⚠ Far in the future — confirm this is intended.</p>{/if}
            {#if addYearError}<p class="hy-err">✗ {addYearError}</p>{/if}
            <div class="toolbar" style="justify-content:flex-end;">
              <button class="btn-secondary" type="button" onclick={() => (addYearOpen = false)} disabled={addYearBusy}>Cancel</button>
              <button class="btn-primary" type="button" onclick={submitAddYear} disabled={addYearBusy || !addYearValue.trim()}>{addYearBusy ? "Creating…" : "Create"}</button>
            </div>
          </div>
        {/if}
      </div>
      <div class="search-shell" class:hidden={!cfg.search}>
        <span class="search-icon">⌕</span>
        <input class="input" placeholder={cfg.placeholder} value={searchQuery} oninput={handleSearchInput} />
      </div>
      <select class="combo" aria-label="Filter" disabled class:hidden={!cfg.filter}>
        <option>All CR</option>
        <option>Pending</option>
        <option>Approved</option>
      </select>
      <button class="btn-black" class:hidden={!cfg.add} onclick={() => onAddProject()}>＋ Add Project</button>
    {/if}
    <button class="refresh-button" title="Refresh Data" onclick={triggerRefresh}><span class:spinning>↻</span></button>
  </div>
</header>

<style>
  .header-year { position: relative; display: flex; align-items: center; gap: 5px; }
  .header-year-pop { position:absolute; top:34px; left:0; z-index:60; min-width:210px; background:var(--main-panel-bg); border:1px solid var(--soft-white-border); border-radius:8px; box-shadow:var(--shadow-panel); padding:10px; display:flex; flex-direction:column; gap:8px; }
  .hy-warn, .hy-err { margin:0; font-size:10px; font-weight:800; }
  .hy-warn { color:#92400e; }
  .hy-err { color:var(--primary-red); }
  .spinning { display:inline-block; animation: spin .65s linear; }
</style>
