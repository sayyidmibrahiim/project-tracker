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
  <div class="workspace-tab-inner" aria-label="Automation workspace tabs">
    <span class="panel-title-icon">⚙</span>
    <span class="panel-title">Automation Center</span>
    <span class="panel-subtitle" style="margin-right:auto;">Automation Workspace · Outlook, Teams, and Reminder rules</span>
    {#each tabs as tab}
      <button class="sb-tab" class:active={activeTab === tab.id} onclick={() => onTabSwitch(tab.id)}>{tab.label}</button>
    {/each}
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
