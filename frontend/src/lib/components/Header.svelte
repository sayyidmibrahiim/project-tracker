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

  const headerConfig: Record<string, { title: string; rich: boolean; search: boolean; add: boolean; placeholder: string }> = {
    dashboard: { title: "Dashboard.", rich: true, search: true, add: true, placeholder: "Search projects here..." },
    "project-detail": { title: "Project Details.", rich: true, search: true, add: true, placeholder: "Search project details..." },
    "second-brain": { title: "Second Brain.", rich: false, search: false, add: false, placeholder: "" },
    report: { title: "Report.", rich: false, search: false, add: false, placeholder: "" },
    automations: { title: "Automations.", rich: false, search: false, add: false, placeholder: "" },
    settings: { title: "Settings.", rich: false, search: false, add: false, placeholder: "" },
  };

  let cfg = $derived(headerConfig[currentPage] ?? headerConfig.dashboard);

  function nowParts(): { date: string; time: string } {
    const d = new Date();
    return {
      date: d.toLocaleDateString("en-US", { weekday: "short", day: "2-digit", month: "short", year: "numeric" }),
      time: d.toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" }),
    };
  }

  let nowText = $state(nowParts());
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
    clockTimer = setInterval(() => (nowText = nowParts()), 1000);
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
    <div class="date-time-badge" aria-label={`Current date and time: ${nowText.date} ${nowText.time}`}>
      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" class="datetime-icon" style="color: var(--color-ink-strong); margin-right: 6px;"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>
      <span class="datetime-copy">
        <span class="datetime-date">{nowText.date}</span>
        <span class="datetime-time">{nowText.time}</span>
      </span>
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
        <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="search-icon"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
        <input class="input" placeholder={cfg.placeholder} value={searchQuery} oninput={handleSearchInput} />
      </div>
      <button class="btn-black" class:hidden={!cfg.add} onclick={() => onAddProject()}>
        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="display:inline;vertical-align:middle;margin-right:4px;"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
        Add Project
      </button>
    {/if}
    <button class="refresh-button" title="Refresh Data" onclick={triggerRefresh}><svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class:spinning><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg></button>
  </div>
</header>

<style>
  .header-year { position: relative; display: flex; align-items: center; gap: 6px; }
  .header-year-pop { position:absolute; top:36px; left:0; z-index:60; min-width:218px; background:var(--main-panel-bg); border:1px solid var(--soft-white-border); border-radius:10px; box-shadow:var(--shadow-panel); padding:10px; display:flex; flex-direction:column; gap:8px; animation:header-pop-in .16s cubic-bezier(.22,1,.36,1); }
  .hy-warn, .hy-err { margin:0; font-size:10px; font-weight:800; }
  .hy-warn { color:#92400e; }
  .hy-err { color:var(--primary-red); }
  .spinning { display:inline-block; animation: spin .65s linear; }
  @keyframes header-pop-in { from { opacity:0; transform:translateY(-3px); } to { opacity:1; transform:translateY(0); } }
  @media (prefers-reduced-motion: reduce) { .header-year-pop, .spinning { animation:none; } }
</style>
