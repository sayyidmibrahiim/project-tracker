<script lang="ts">
  import { onMount } from "svelte";
  import { callBridge, isPywebviewReady } from "../bridge";
  import { BridgeErrorCode } from "../types";

  // ── Tab state ──
  type TabId = "notes" | "linkbank";
  let activeTab: TabId = $state("linkbank");

  // ── Link Bank data (read-only; mutations deferred — backend not wired) ──
  interface LinkItem {
    name: string;
    url: string;
    notes: string;
    category: string;
  }

  interface LinkBankData {
    categories: string[];
    links: LinkItem[];
  }

  type LoadState = "idle" | "loading" | "error" | "loaded";
  let loadState: LoadState = $state("idle");
  let errorCode: string = $state("");
  let errorMessage: string = $state("");

  let bank: LinkBankData = $state({ categories: [], links: [] });

  // ── Local filters ──
  let searchQuery: string = $state("");
  let categoryFilter: string = $state("all");

  let filteredLinks: LinkItem[] = $derived.by(() => {
    let result = categoryFilter === "all"
      ? bank.links
      : bank.links.filter((l) => l.category === categoryFilter);
    const q = searchQuery.trim().toLowerCase();
    if (q) {
      result = result.filter(
        (l) =>
          l.name.toLowerCase().includes(q) ||
          l.url.toLowerCase().includes(q) ||
          l.notes.toLowerCase().includes(q) ||
          l.category.toLowerCase().includes(q),
      );
    }
    return result;
  });

  // ── Load ──
  async function loadLinkBank() {
    loadState = "loading";
    errorCode = "";
    errorMessage = "";

    if (!isPywebviewReady()) {
      errorCode = BridgeErrorCode.BRIDGE_UNAVAILABLE;
      errorMessage = "pywebview bridge is not available. Running outside desktop shell.";
      loadState = "error";
      return;
    }

    const response = await callBridge<LinkBankData>("linkbank_get");
    if (!response.ok) {
      errorCode = response.error.code;
      errorMessage = response.error.message;
      loadState = "error";
      return;
    }

    bank = response.data ?? { categories: [], links: [] };
    loadState = "loaded";
  }

  onMount(() => {
    if (activeTab === "linkbank") loadLinkBank();
  });

  function onTabSwitch(tab: TabId) {
    activeTab = tab;
    if (tab === "linkbank" && loadState === "idle") loadLinkBank();
  }

  // Expose refresh for parent
  export function refresh() {
    if (activeTab === "linkbank") loadLinkBank();
  }
</script>

<div class="secondbrain-screen">
  <!-- ── Tab bar ── -->
  <div class="sb-tab-bar">
    <button
      class="sb-tab"
      class:active={activeTab === "notes"}
      onclick={() => onTabSwitch("notes")}
    >Notes</button>
    <button
      class="sb-tab"
      class:active={activeTab === "linkbank"}
      onclick={() => onTabSwitch("linkbank")}
    >Link Bank</button>
  </div>

  <!-- ── Notes tab (deferred placeholder) ── -->
  {#if activeTab === "notes"}
    <div class="sb-notes-placeholder">
      <div class="placeholder-hero">
        <span class="placeholder-kicker">Coming next</span>
        <h2>Notes & Second Brain</h2>
        <p>Markdown notes editor, searchable knowledge base, and project documents browser. Landing in Phase E.</p>
      </div>
    </div>

  <!-- ── Link Bank tab (read-only; add/edit/archive deferred) ── -->
  {:else}
    {#if loadState === "loading"}
      <div class="dashboard-banner banner-loading">
        <span class="banner-icon">◌</span>
        <span>Loading link bank…</span>
      </div>
    {:else if loadState === "error"}
      <div class="dashboard-banner banner-error">
        <span class="banner-icon">⚠</span>
        <div>
          <p class="banner-title">Link Bank unavailable</p>
          <p class="banner-detail">{errorCode}: {errorMessage}</p>
        </div>
      </div>
    {:else}
      <!-- Toolbar -->
      <div class="lb-toolbar">
        <div class="lb-toolbar-left">
          <select class="header-combo" bind:value={categoryFilter}>
            <option value="all">All Categories</option>
            {#each bank.categories as cat}
              <option value={cat}>{cat}</option>
            {/each}
          </select>
          <div class="header-search">
            <span class="search-icon">⌕</span>
            <input
              class="header-input"
              placeholder="Search links…"
              bind:value={searchQuery}
            />
          </div>
        </div>
        <div class="lb-toolbar-right">
          <span class="project-count">{filteredLinks.length} link(s)</span>
          <span class="lb-deferred-hint">✎ Add/Edit deferred</span>
        </div>
      </div>

      <!-- Link list -->
      <div class="lb-list">
        {#if filteredLinks.length === 0}
          <div class="table-empty">
            <p class="empty-title">No links found</p>
            <p class="empty-sub">
              {bank.links.length === 0 ? "No links in link bank. Add/edit support landing in a future phase." : "Adjust filters to see results."}
            </p>
          </div>
        {:else}
          {#each filteredLinks as link}
            <article class="lb-card">
              <span class="lb-card-accent"></span>
              <div class="lb-card-body">
                <div class="lb-card-top">
                  <h4 class="lb-card-title">
                    <a href={link.url} target="_blank" rel="noopener" class="lb-link">{link.name}</a>
                  </h4>
                  {#if link.category}
                    <span class="lb-category-badge">{link.category}</span>
                  {/if}
                </div>
                {#if link.url}
                  <p class="lb-card-url">{link.url}</p>
                {/if}
                {#if link.notes}
                  <p class="lb-card-notes">{link.notes}</p>
                {/if}
              </div>
            </article>
          {/each}
        {/if}
      </div>
    {/if}
  {/if}
</div>

<style>
  /* ── Screen ── */
  .secondbrain-screen {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    padding: 14px;
    gap: 12px;
    overflow: hidden;
  }

  /* ── Tab bar ── */
  .sb-tab-bar {
    display: flex;
    gap: 4px;
    flex: 0 0 auto;
    background: var(--color-workspace-panel);
    border: 1px solid #D7DCE2;
    border-radius: 8px;
    padding: 6px;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.30);
  }
  .sb-tab {
    height: 28px;
    border-radius: 5px;
    padding: 0 16px;
    background: transparent;
    border: 1px solid transparent;
    color: var(--color-ink);
    font-weight: 850;
    font-size: 11px;
    cursor: pointer;
    transition: background 0.15s ease, color 0.15s ease;
  }
  .sb-tab:hover {
    background: var(--color-soft-pink-surface);
    color: var(--color-dbs-red);
  }
  .sb-tab.active {
    background: var(--color-dbs-red);
    color: #fff;
    font-weight: 900;
  }

  /* ── Notes placeholder ── */
  .sb-notes-placeholder {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .sb-notes-placeholder .placeholder-hero {
    max-width: 520px;
  }

  /* ── Link Bank Toolbar ── */
  .lb-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    flex: 0 0 auto;
    background: var(--color-workspace-panel);
    border: 1px solid #D7DCE2;
    border-radius: 8px;
    padding: 10px 12px;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.30);
  }
  .lb-toolbar-left {
    display: flex;
    align-items: center;
    gap: 7px;
  }
  .lb-toolbar-right {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .lb-deferred-hint {
    font-size: 10px;
    font-weight: 800;
    color: var(--color-muted-light);
    font-style: italic;
  }

  /* ── Link list ── */
  .lb-list {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding-right: 2px;
  }

  /* ── Link card ── */
  .lb-card {
    background: #fff;
    border: 1px solid #E5E7EB;
    border-left: 3px solid var(--color-dbs-red);
    border-radius: 8px;
    box-shadow: var(--shadow-subtle);
    padding: 10px 12px;
    display: flex;
    gap: 10px;
    align-items: flex-start;
    transition: box-shadow 0.15s ease;
  }
  .lb-card:hover {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  }
  .lb-card-accent {
    width: 3px;
    min-width: 3px;
    height: 16px;
    border-radius: 2px;
    background: var(--color-dbs-red);
    margin-top: 2px;
  }
  .lb-card-body {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  .lb-card-top {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }
  .lb-card-title {
    margin: 0;
    font-size: 12px;
    font-weight: 900;
  }
  .lb-link {
    color: var(--color-dbs-red);
    text-decoration: none;
  }
  .lb-link:hover { text-decoration: underline; }
  .lb-category-badge {
    display: inline-flex;
    align-items: center;
    height: 18px;
    padding: 0 7px;
    border-radius: 999px;
    background: var(--color-workspace-panel);
    border: 1px solid #D7DCE2;
    font-size: 9px;
    font-weight: 800;
    color: var(--color-muted);
  }
  .lb-card-url {
    margin: 0;
    font-size: 10px;
    color: var(--color-muted);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-weight: 750;
  }
  .lb-card-notes {
    margin: 0;
    font-size: 10px;
    font-weight: 700;
    color: var(--color-muted-light);
    line-height: 1.35;
  }
</style>
