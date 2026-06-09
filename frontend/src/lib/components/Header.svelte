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
  } = $props();

  // ── Add Year (PRD §11.7) ──
  const currentYear = new Date().getFullYear();
  let addYearOpen = $state(false);
  let addYearValue = $state(String(currentYear + 1));
  let addYearError = $state("");
  let addYearBusy = $state(false);
  let addYearWarn = $derived(Number(addYearValue) > currentYear + 2);

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

  const pageTitles: Record<string, string> = {
    dashboard: "Dashboard",
    "project-detail": "Project Details",
    "second-brain": "Second Brain",
    report: "Report",
    automations: "Automations",
    settings: "Settings",
  };

  // ── Live datetime badge (PRD §11.2) ──
  function formatNow(): string {
    const d = new Date();
    const date = d.toLocaleDateString("en-GB", { weekday: "short", day: "2-digit", month: "short", year: "numeric" });
    const time = d.toLocaleTimeString("en-GB", { hour12: false });
    return `${date} ${time}`;
  }
  let nowText = $state(formatNow());
  let clockTimer: ReturnType<typeof setInterval> | undefined;

  // ── Refresh spin (PRD §11.14) ──
  let spinning = $state(false);
  function triggerRefresh() {
    onRefresh();
    spinning = true;
    setTimeout(() => (spinning = false), 650);
  }

  // ── Search debounce 200ms (PRD §11.5) ──
  let searchTimer: ReturnType<typeof setTimeout> | undefined;

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
    <h1 class="page-title">{pageTitles[currentPage] ?? currentPage.replace("-", " ")}</h1>
  </div>

  <div class="header-center">
    <div class="datetime-badge">
      <span class="datetime-icon">▣</span>
      <span>{nowText}</span>
    </div>
  </div>

  <div class="header-actions">
    {#if showDashboardControls}
      <div class="header-year">
        <select class="header-combo" aria-label="Year" value={selectedYear} onchange={handleYearInput}>
          <option value="all">All years</option>
          {#each years as y}
            <option value={y}>{y}</option>
          {/each}
        </select>
        <button class="header-addyear" type="button" aria-label="Add year" title="Add year folder" onclick={toggleAddYear}>＋</button>
        {#if addYearOpen}
          <div class="header-year-pop">
            <label class="hy-label">New year
              <input class="hy-input" type="number" bind:value={addYearValue} min="2000" max="2100" />
            </label>
            {#if addYearWarn}<p class="hy-warn">⚠ Far in the future — confirm this is intended.</p>{/if}
            {#if addYearError}<p class="hy-err">✗ {addYearError}</p>{/if}
            <div class="hy-actions">
              <button class="hy-btn" type="button" onclick={() => (addYearOpen = false)} disabled={addYearBusy}>Cancel</button>
              <button class="hy-btn hy-primary" type="button" onclick={submitAddYear} disabled={addYearBusy || !addYearValue.trim()}>{addYearBusy ? "Creating…" : "Create"}</button>
            </div>
          </div>
        {/if}
      </div>
      <div class="header-search">
        <span class="search-icon">⌕</span>
        <input class="header-input" placeholder="Search projects here..." value={searchQuery} oninput={handleSearchInput} />
      </div>
      <select class="header-combo" aria-label="Filter" disabled title="CR filter deferred">
        <option>All CR</option>
        <option>Pending</option>
        <option>Approved</option>
      </select>
      <button class="btn-black" onclick={() => onAddProject()}>＋ Add Project</button>
    {/if}
    <button class="btn-refresh" title="Refresh Data" onclick={triggerRefresh}><span class="btn-refresh-icon" class:spinning>↻</span></button>
  </div>
</header>

<style>
  .btn-refresh-icon { display:inline-block; }
  .btn-refresh-icon.spinning { animation: header-refresh-spin 0.65s linear; }
  @keyframes header-refresh-spin { to { transform: rotate(360deg); } }
  .header-year { position:relative; display:flex; align-items:center; gap:4px; }
  .header-addyear { width:26px; height:26px; border:1px solid var(--color-input-border, #D7D7DC); border-radius:4px; background:#fff; color:var(--color-dbs-red); font-size:13px; font-weight:900; cursor:pointer; line-height:1; }
  .header-addyear:hover { border-color:var(--color-dbs-red); }
  .header-year-pop { position:absolute; top:32px; left:0; z-index:60; min-width:210px; background:#fff; border:1px solid #D7DCE2; border-radius:8px; box-shadow:0 12px 32px rgba(0,0,0,0.28); padding:10px; display:flex; flex-direction:column; gap:7px; }
  .hy-label { display:flex; flex-direction:column; gap:4px; font-size:9px; font-weight:850; text-transform:uppercase; letter-spacing:0.3px; color:var(--color-muted); }
  .hy-input { height:28px; border:1px solid var(--color-input-border, #D7DCE2); border-radius:5px; padding:0 8px; font-size:12px; font-weight:750; color:var(--color-ink); outline:none; }
  .hy-input:focus { border:2px solid var(--color-dbs-red); }
  .hy-warn { margin:0; font-size:10px; font-weight:800; color:#92400e; }
  .hy-err { margin:0; font-size:10px; font-weight:800; color:var(--color-dbs-red); }
  .hy-actions { display:flex; justify-content:flex-end; gap:6px; }
  .hy-btn { height:28px; padding:0 12px; border:1px solid #D7DCE2; border-radius:5px; background:#fff; color:var(--color-ink); font-size:11px; font-weight:850; cursor:pointer; }
  .hy-btn:hover:not(:disabled) { border-color:var(--color-dbs-red); color:var(--color-dbs-red); }
  .hy-btn:disabled { opacity:0.5; cursor:not-allowed; }
  .hy-primary { background:var(--color-dbs-red); border-color:var(--color-dbs-red); color:#fff; }
  .hy-primary:hover:not(:disabled) { color:#fff; }
</style>
