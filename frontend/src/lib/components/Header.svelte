<script lang="ts">
  import { onDestroy } from "svelte";

  let {
    currentPage,
    selectedYear,
    years = [],
    showDashboardControls = false,
    onYearChange,
    onRefresh,
    onAddProject = () => {},
    onAddYear = async () => null,
    openAddYearToken = 0,
    interactionLocked = false,
  }: {
    currentPage: string;
    selectedYear: string;
    years?: string[];
    showDashboardControls?: boolean;
    onYearChange: (year: string) => void;
    onRefresh: () => void;
    onAddProject?: () => void;
    onAddYear?: (year: string) => Promise<string | null>;
    openAddYearToken?: number;
    interactionLocked?: boolean;
  } = $props();

  const currentYear = new Date().getFullYear();
  let addYearOpen = $state(false);
  let addYearValue = $state(String(currentYear + 1));
  let addYearError = $state("");
  let addYearBusy = $state(false);
  let addYearWarn = $derived(Number(addYearValue) > currentYear + 2);
  let lastAddYearToken = 0;

  const pageTitle: Record<string, string> = {
    dashboard: "Dashboard",
    "project-detail": "Project Details",
    "second-brain": "Second Brain",
    report: "Report",
    automations: "Automations",
    "global-plan": "Global Plan",
    settings: "Settings",
  };

  let title = $derived(pageTitle[currentPage] ?? "");

  $effect(() => {
    if (openAddYearToken > lastAddYearToken) {
      lastAddYearToken = openAddYearToken;
      addYearError = "";
      addYearValue = String(currentYear + 1);
      addYearOpen = true;
    }
  });

  let spinning = $state(false);

  function triggerRefresh() {
    if (interactionLocked) return;
    onRefresh();
    spinning = true;
    setTimeout(() => (spinning = false), 650);
  }

  function toggleAddYear() {
    if (interactionLocked) return;
    addYearError = "";
    addYearValue = String(currentYear + 1);
    addYearOpen = !addYearOpen;
  }

  async function submitAddYear() {
    if (interactionLocked) return;
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
    if (interactionLocked) return;
    onYearChange((e.target as HTMLSelectElement).value);
  }

  onDestroy(() => {});
</script>

<header class="app-header">
  <div class="header-title-box">
    <h1 class="page-title">{title}</h1>
  </div>

  <div class="header-right">
    {#if showDashboardControls}
      <div class="header-year">
        <select class="combo" aria-label="Year" value={selectedYear} onchange={handleYearInput} disabled={interactionLocked} aria-disabled={interactionLocked}>
          <option value="all">All years</option>
          {#each years as y}
            <option value={y}>{y}</option>
          {/each}
        </select>
        <button class="btn-tiny" type="button" aria-label="Add year" title="Add year folder" onclick={toggleAddYear} disabled={interactionLocked} aria-disabled={interactionLocked}>＋</button>
        {#if addYearOpen}
          <div class="header-year-pop">
            <label class="field-label">New year
              <input class="input" type="number" bind:value={addYearValue} min="2000" max="2100" />
            </label>
            {#if addYearWarn}<p class="hy-warn">⚠ Far in the future — confirm this is intended.</p>{/if}
            {#if addYearError}<p class="hy-err">✗ {addYearError}</p>{/if}
            <div class="toolbar" style="justify-content:flex-end;">
              <button class="btn-secondary" type="button" onclick={() => (addYearOpen = false)} disabled={addYearBusy || interactionLocked}>Cancel</button>
              <button class="btn-primary" type="button" onclick={submitAddYear} disabled={addYearBusy || interactionLocked || !addYearValue.trim()}>{addYearBusy ? "Creating…" : "Create"}</button>
            </div>
          </div>
        {/if}
      </div>
      <button class="btn-black" onclick={() => { if (!interactionLocked) onAddProject(); }} disabled={interactionLocked} aria-disabled={interactionLocked}>
        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="display:inline;vertical-align:middle;margin-right:4px;"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
        Add Project
      </button>
    {/if}
    <button class="refresh-button" title="Refresh Data" onclick={triggerRefresh} disabled={interactionLocked} aria-disabled={interactionLocked}><svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class:spinning><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg></button>
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
