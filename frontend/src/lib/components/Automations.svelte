<script lang="ts">
  import AutomationsOutlook from "./AutomationsOutlook.svelte";
  import TeamsActions from "./TeamsActions.svelte";
  import SchedulerActions from "./SchedulerActions.svelte";
  import RulesActions from "./RulesActions.svelte";

  type TabId = "outlook" | "teams" | "reminder" | "rules";
  const tabs: { id: TabId; label: string }[] = [
    { id: "outlook", label: "Outlook" },
    { id: "teams", label: "Teams" },
    { id: "reminder", label: "Reminder" },
    { id: "rules", label: "Rules Engine" },
  ];

  let activeTab: TabId = $state("outlook");
  function onTabSwitch(tab: TabId) { activeTab = tab; }
  export function refresh() {}
</script>

<section class="screen active" id="screen-automations">
  <div class="page-header">
    <div class="page-header-left">
      <span class="page-header-icon"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg></span>
      <h2 class="page-header-title">Automations</h2>
    </div>
    <div class="page-header-actions">
      {#each tabs as tab}
        <button class="sb-tab" class:active={activeTab === tab.id} onclick={() => onTabSwitch(tab.id)}>{tab.label}</button>
      {/each}
    </div>
  </div>

  <div class="page-stack active">
    {#if activeTab === "outlook"}
      <AutomationsOutlook />
    {:else if activeTab === "teams"}
      <div class="split">
        <div class="panel-card accent" style="flex:7"><div class="panel-title-row"><span class="panel-title-icon">💬</span><span class="panel-title">Teams Message Automation</span><span class="panel-subtitle">deep link + clipboard + confirmation gate</span></div><TeamsActions /></div>
        <div class="panel-card accent" style="flex:3"><div class="panel-title-row"><span class="panel-title-icon">📶</span><span class="panel-title">Teams Status</span></div><div class="metric-card"><div class="metric-icon">P</div><div><div class="metric-label">Preview First</div><div class="metric-helper">Default mode; no auto-send</div></div></div><div class="metric-card"><div class="metric-icon">⚠</div><div><div class="metric-label">Guarded Send</div><div class="metric-helper">Explicit confirmation required</div></div></div></div>
      </div>
    {:else if activeTab === "reminder"}
      <div class="metric-row"><div class="metric-card"><div class="metric-icon">⌛</div><div><div class="metric-value">0</div><div class="metric-label">Due Soon</div><div class="metric-helper">Scheduler entries</div></div></div><div class="metric-card"><div class="metric-icon">!</div><div><div class="metric-value">0</div><div class="metric-label">Overdue</div><div class="metric-helper">Needs attention</div></div></div><div class="metric-card"><div class="metric-icon">Ⅱ</div><div><div class="metric-value">0</div><div class="metric-label">Postponed</div><div class="metric-helper">Deferred items</div></div></div><div class="metric-card"><div class="metric-icon">🔔</div><div><div class="metric-value">Rules</div><div class="metric-label">Reminder Rules</div><div class="metric-helper">Local notifications</div></div></div></div>
      <div class="panel-card accent" style="flex:1"><div class="panel-title-row"><span class="panel-title-icon">🔔</span><span class="panel-title">Reminder Rules</span><span class="panel-subtitle">scheduler control surface</span></div><SchedulerActions /></div>
    {:else}
      <div class="panel-card accent" style="flex:1"><div class="panel-title-row"><span class="panel-title-icon">▣</span><span class="panel-title">Rules Engine</span><span class="panel-subtitle">trigger / condition / action</span></div><RulesActions /></div>
    {/if}
  </div>
</section>
