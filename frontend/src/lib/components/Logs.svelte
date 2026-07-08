<script lang="ts">
  /**
   * Slice 5: cross-module automation Logs top-level view.
   *
   * Overview cards per module (Outlook / Teams / CR Automation / Rules Engine / All)
   * + filter dropdowns (module, cr_id, event_type) + chronological table.
   * Newest-first. Right-sidebar drilldown lives in RulesActions / PD (this page
   * is the global overview only).
   */
  import { onMount, untrack } from "svelte";
  import { callBridge, isPywebviewReady } from "../bridge";

  type LogEntry = {
    id: number;
    module: string;
    rule_id: string;
    cr_id: string;
    timestamp: string;
    event_type: string;
    detail: string;
  };

  const MODULES = [
    { id: "all", label: "All" },
    { id: "outlook", label: "Outlook" },
    { id: "teams", label: "Teams" },
    { id: "cr_automation", label: "CR Automation" },
    { id: "rules_engine", label: "Rules Engine" },
  ];

  let { initialCrId = "" }: { initialCrId?: string } = $props();

  let logs: LogEntry[] = $state([]);
  let loading: boolean = $state(false);
  let errorMsg: string = $state("");
  let filterModule: string = $state("all");
  let filterCrId: string = $state(untrack(() => initialCrId));

  let moduleCounts = $derived({
    all: logs.length,
    outlook: logs.filter((l) => l.module === "outlook").length,
    teams: logs.filter((l) => l.module === "teams").length,
    cr_automation: logs.filter((l) => l.module === "cr_automation").length,
    rules_engine: logs.filter((l) => l.module === "rules_engine").length,
  });

  async function loadLogs() {
    loading = true;
    errorMsg = "";
    if (!isPywebviewReady()) {
      loading = false;
      return;
    }
    const resp = await callBridge<LogEntry[]>("logs_list", filterModule, filterCrId.trim(), "", 200);
    loading = false;
    if (!resp.ok) {
      errorMsg = resp.error.message;
      return;
    }
    logs = resp.data ?? [];
  }

  async function clearAll() {
    if (!confirm("Clear ALL automation logs? This cannot be undone.")) return;
    const resp = await callBridge<{ deleted: number }>("logs_clear", "", "");
    if (resp.ok) {
      await loadLogs();
    } else {
      errorMsg = resp.error.message;
    }
  }

  function moduleLabel(id: string): string {
    return MODULES.find((m) => m.id === id)?.label ?? id;
  }

  onMount(loadLogs);
</script>

<section class="screen active" id="screen-logs">
  <div class="page-header">
    <div class="page-header-left">
      <span class="page-header-icon">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
      </span>
      <h2 class="page-header-title">Logs</h2>
    </div>
    <div class="page-header-actions">
      <button class="sb-tab" onclick={loadLogs} disabled={loading}>{loading ? "◌ Loading…" : "↻ Refresh"}</button>
      <button class="sb-tab" onclick={clearAll} disabled={logs.length === 0}>✕ Clear all</button>
    </div>
  </div>

  <div class="page-stack active">
    <div class="metric-row">
      {#each MODULES as m}
        <div class="metric-card">
          <div class="metric-icon">{moduleCounts[m.id as keyof typeof moduleCounts] ?? 0}</div>
          <div>
            <div class="metric-label">{m.label}</div>
            <div class="metric-helper">automation log entries</div>
          </div>
        </div>
      {/each}
    </div>

    <div class="panel-card accent" style="flex:1">
      <div class="panel-title-row">
        <span class="panel-title-icon">📋</span>
        <span class="panel-title">AUTOMATION LOGS</span>
        <span class="panel-subtitle">cross-module, newest first</span>
      </div>
      <div class="logs-filters">
        <label class="field">
          <span>Module</span>
          <select class="input" bind:value={filterModule} onchange={loadLogs}>
            {#each MODULES as m}<option value={m.id}>{m.label}</option>{/each}
          </select>
        </label>
        <label class="field">
          <span>CR filter</span>
          <input class="input" bind:value={filterCrId} onchange={loadLogs} placeholder="e.g. 2026-001" />
        </label>
      </div>
      {#if errorMsg}
        <div class="dashboard-banner banner-error"><span class="banner-icon">⚠</span><span>{errorMsg}</span></div>
      {:else if loading}
        <p class="logs-hint">◌ Loading…</p>
      {:else if logs.length === 0}
        <p class="logs-hint">No automation log entries for this filter.</p>
      {:else}
        <table class="mini-table">
          <thead>
            <tr><th>Timestamp</th><th>Module</th><th>Event</th><th>CR</th><th>Detail</th></tr>
          </thead>
          <tbody>
            {#each logs as log}
              <tr>
                <td class="log-ts">{log.timestamp || "—"}</td>
                <td>{moduleLabel(log.module)}</td>
                <td><code>{log.event_type || "—"}</code></td>
                <td>{log.cr_id || "—"}</td>
                <td class="log-detail">{log.detail}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      {/if}
    </div>
  </div>
</section>

<style>
  .logs-filters { display:flex; gap:12px; flex-wrap:wrap; padding:10px 12px; }
  .logs-filters .field { display:flex; flex-direction:column; gap:4px; font-size:9px; font-weight:800; color:var(--color-muted); text-transform:uppercase; letter-spacing:0.3px; min-width:140px; }
  .logs-filters .input { padding:5px 8px; font-size:11px; border:1px solid #D7DCE2; border-radius:5px; background:#fff; color:var(--color-ink); text-transform:none; letter-spacing:normal; }
  .logs-hint { font-size:11px; font-weight:700; color:var(--color-muted); padding:14px; text-align:center; }
  .log-ts { font-family:monospace; font-size:10px; white-space:nowrap; }
  .log-detail { font-size:10px; color:var(--color-muted); max-width:380px; }
  .mini-table code { font-size:9px; font-family:monospace; background:#f3f4f6; padding:1px 5px; border-radius:3px; }
</style>
