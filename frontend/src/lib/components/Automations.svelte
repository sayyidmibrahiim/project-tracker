<script lang="ts">
  /**
   * Automations screen — tab dispatcher.
   *
   * Each tab is implemented in its own component so this file stays a thin
   * tab bar + dispatcher with no per-tab state. Outlook is the only tab still
   * presented as a project-scoped action surface (used from ProjectDetails),
   * so it remains a deferred placeholder here.
   */
  import RulesActions from "./RulesActions.svelte";
  import TeamsActions from "./TeamsActions.svelte";
  import SchedulerActions from "./SchedulerActions.svelte";

  type TabId = "rules" | "outlook" | "teams" | "scheduler";
  let activeTab: TabId = $state("rules");

  function onTabSwitch(tab: TabId) {
    activeTab = tab;
  }

  // No-op refresh hook preserved for the surrounding page shell.
  export function refresh() {}
</script>

<div class="am-screen">
  <div class="am-tab-bar">
    <button class="am-tab" class:active={activeTab === "rules"} onclick={() => onTabSwitch("rules")}>Rules</button>
    <button class="am-tab" class:active={activeTab === "outlook"} onclick={() => onTabSwitch("outlook")}>Outlook</button>
    <button class="am-tab" class:active={activeTab === "teams"} onclick={() => onTabSwitch("teams")}>Teams</button>
    <button class="am-tab" class:active={activeTab === "scheduler"} onclick={() => onTabSwitch("scheduler")}>Scheduler</button>
  </div>

  {#if activeTab === "rules"}
    <div class="am-pane"><RulesActions /></div>
  {:else if activeTab === "teams"}
    <div class="am-pane"><TeamsActions /></div>
  {:else if activeTab === "scheduler"}
    <div class="am-pane"><SchedulerActions /></div>
  {:else}
    <div class="am-deferred-tab">
      <div class="placeholder-hero">
        <span class="placeholder-kicker">Project-scoped</span>
        <h2>Outlook Automation</h2>
        <p>Outlook draft/send actions are exposed in the Project Details panel (Draft is default; Send is gated by confirmation). Off-Windows the integration returns dev-skipped responses with no COM execution.</p>
      </div>
    </div>
  {/if}
</div>

<style>
  .am-screen { flex:1; min-height:0; display:flex; flex-direction:column; padding:14px; gap:10px; overflow:hidden; }
  .am-tab-bar { display:flex; gap:4px; flex:0 0 auto; background:var(--color-workspace-panel); border:1px solid #D7DCE2; border-radius:8px; padding:6px; box-shadow:0 4px 15px rgba(0,0,0,0.30); }
  .am-tab { height:28px; border-radius:5px; padding:0 16px; background:transparent; border:1px solid transparent; color:var(--color-ink); font-weight:850; font-size:11px; cursor:pointer; transition:background 0.15s ease,color 0.15s ease; }
  .am-tab:hover { background:var(--color-soft-pink-surface); color:var(--color-dbs-red); }
  .am-tab.active { background:var(--color-dbs-red); color:#fff; font-weight:900; }
  .am-pane { flex:1; min-height:0; overflow-y:auto; padding:4px 2px; }
  .am-deferred-tab { flex:1; display:flex; align-items:center; justify-content:center; }
  .am-deferred-tab .placeholder-hero { max-width:520px; }
</style>
