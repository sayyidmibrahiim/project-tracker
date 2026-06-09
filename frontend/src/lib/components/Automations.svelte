<script lang="ts">
  /**
   * Automations screen — PRD §16.2 tab dispatcher.
   *
   * Tab order is fixed by PRD: Outlook, Teams, Scheduler, Rules Engine, and the
   * page defaults to Outlook. Each tab owns only UI state. Python services
   * remain the owner of automation persistence, rule execution, scheduler jobs,
   * and Windows-only integrations.
   */
  import AutomationsOutlook from "./AutomationsOutlook.svelte";
  import TeamsActions from "./TeamsActions.svelte";
  import SchedulerActions from "./SchedulerActions.svelte";
  import RulesActions from "./RulesActions.svelte";

  type TabId = "outlook" | "teams" | "scheduler" | "rules";

  const tabs: { id: TabId; label: string }[] = [
    { id: "outlook", label: "Outlook" },
    { id: "teams", label: "Teams" },
    { id: "scheduler", label: "Scheduler" },
    { id: "rules", label: "Rules Engine" },
  ];

  let activeTab: TabId = $state("outlook");

  function onTabSwitch(tab: TabId) {
    activeTab = tab;
  }

  // No-op refresh hook preserved for the surrounding page shell.
  export function refresh() {}
</script>

<div class="am-screen">
  <div class="am-tab-bar" aria-label="Automations tabs">
    {#each tabs as tab}
      <button class="am-tab" class:active={activeTab === tab.id} onclick={() => onTabSwitch(tab.id)}>{tab.label}</button>
    {/each}
  </div>

  {#if activeTab === "outlook"}
    <div class="am-pane"><AutomationsOutlook /></div>
  {:else if activeTab === "teams"}
    <div class="am-pane"><TeamsActions /></div>
  {:else if activeTab === "scheduler"}
    <div class="am-pane"><SchedulerActions /></div>
  {:else}
    <div class="am-pane"><RulesActions /></div>
  {/if}
</div>

<style>
  .am-screen { flex:1; min-height:0; display:flex; flex-direction:column; padding:14px; gap:10px; overflow:hidden; }
  .am-tab-bar { display:flex; gap:4px; flex:0 0 auto; background:var(--color-workspace-panel); border:1px solid #D7DCE2; border-radius:8px; padding:6px; box-shadow:0 4px 15px rgba(0,0,0,0.30); }
  .am-tab { height:28px; border-radius:5px; padding:0 16px; background:transparent; border:1px solid transparent; color:var(--color-ink); font-weight:850; font-size:11px; cursor:pointer; transition:background 0.15s ease,color 0.15s ease; }
  .am-tab:hover { background:var(--color-soft-pink-surface); color:var(--color-dbs-red); }
  .am-tab.active { background:var(--color-dbs-red); color:#fff; font-weight:900; }
  .am-pane { flex:1; min-height:0; overflow-y:auto; padding:4px 2px; }
</style>
