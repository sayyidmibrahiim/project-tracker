<script lang="ts">
  /**
   * Second Brain — thin tabbed shell (Task 10).
   *
   * Owns ONLY tab selection + the flush-before-switch/refresh-active-child
   * contracts. All business logic, bridge calls, and the editor live in the
   * two workspace components below.
   */
  import SecondBrainNotes from "./SecondBrainNotes.svelte";
  import LinkBank from "./LinkBank.svelte";

  type TabId = "notes" | "linkbank";

  // Tab state is component-session-only: it lives in this instance's $state
  // and resets whenever the shell remounts. Notes is always the default.
  let activeTab: TabId = $state("notes");
  // Link Bank lazy-mounts on first selection, then stays mounted (hidden via
  // CSS, never destroyed) so its state survives further tab switches.
  let linkBankMounted: boolean = $state(false);

  let notesRef: SecondBrainNotes | undefined = $state();
  let linkBankRef: LinkBank | undefined = $state();

  async function selectTab(tab: TabId) {
    if (tab === activeTab) return;
    // Leaving Notes must flush its mounted editor first; a failed save
    // aborts the switch and keeps the current document open (never destroy
    // Notes' state to force this — it stays mounted regardless).
    if (activeTab === "notes") {
      const flushed = await notesRef?.flush();
      if (flushed === false) return;
    }
    if (tab === "linkbank") linkBankMounted = true;
    activeTab = tab;
  }

  async function refreshActive() {
    if (activeTab === "notes") await notesRef?.refresh();
    else await linkBankRef?.refresh();
  }
</script>

<section class="screen active" id="screen-secondbrain">
  <div class="page-header">
    <div class="page-header-left">
      <span class="page-header-icon"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg></span>
      <h2 class="page-header-title">Second Brain</h2>
    </div>
    <div class="page-header-actions">
      <div class="toolbar" role="tablist" aria-label="Second Brain views">
        <button
          class="status-tab"
          class:active={activeTab === "notes"}
          type="button"
          role="tab"
          id="sb-tab-notes"
          aria-selected={activeTab === "notes"}
          aria-controls="sb-panel-notes"
          onclick={() => selectTab("notes")}
        >Notes</button>
        <button
          class="status-tab"
          class:active={activeTab === "linkbank"}
          type="button"
          role="tab"
          id="sb-tab-linkbank"
          aria-selected={activeTab === "linkbank"}
          aria-controls="sb-panel-linkbank"
          onclick={() => selectTab("linkbank")}
        >Link Bank</button>
      </div>
      <button class="sb-tab" type="button" onclick={refreshActive}>↻ Refresh</button>
    </div>
  </div>

  <div class="page-stack active">
    <div
      class="sb-panel"
      class:sb-panel-hidden={activeTab !== "notes"}
      id="sb-panel-notes"
      role="tabpanel"
      aria-labelledby="sb-tab-notes"
    >
      <SecondBrainNotes bind:this={notesRef} />
    </div>
    {#if linkBankMounted}
      <div
        class="sb-panel"
        class:sb-panel-hidden={activeTab !== "linkbank"}
        id="sb-panel-linkbank"
        role="tabpanel"
        aria-labelledby="sb-tab-linkbank"
      >
        <LinkBank bind:this={linkBankRef} />
      </div>
    {/if}
  </div>
</section>

<style>
  /* Panels stay mounted; only display toggles so neither child is ever
     destroyed by a tab switch (Notes keeps editor state, Link Bank keeps
     its loaded workspace once lazy-mounted). */
  .sb-panel { display: flex; flex-direction: column; flex: 1; min-height: 0; }
  .sb-panel-hidden { display: none; }
</style>
