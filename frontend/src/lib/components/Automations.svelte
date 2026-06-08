<script lang="ts">
  import { onMount } from "svelte";
  import { callBridge, isPywebviewReady } from "../bridge";
  import type { AutomationRule, AutomationResult } from "../types";
  import { BridgeErrorCode } from "../types";
  import TeamsActions from "./TeamsActions.svelte";
  import SchedulerActions from "./SchedulerActions.svelte";

  type TabId = "rules" | "outlook" | "teams" | "scheduler";
  let activeTab: TabId = $state("rules");

  type LoadState = "idle" | "loading" | "error" | "loaded";
  let loadState: LoadState = $state("idle");
  let errorCode: string = $state("");
  let errorMessage: string = $state("");

  let rules: AutomationRule[] = $state([]);
  let evalResults: Record<string, AutomationResult | null> = $state({});
  let evalPending: Record<string, boolean> = $state({});
  let evalAllPending: boolean = $state(false);

  async function loadRules() {
    loadState = "loading";
    errorCode = "";
    errorMessage = "";

    if (!isPywebviewReady()) {
      errorCode = BridgeErrorCode.BRIDGE_UNAVAILABLE;
      errorMessage = "pywebview bridge unavailable.";
      loadState = "error";
      return;
    }
    const resp = await callBridge<AutomationRule[]>("automation_list_rules");
    if (!resp.ok) {
      errorCode = resp.error.code;
      errorMessage = resp.error.message;
      loadState = "error";
      return;
    }
    rules = resp.data ?? [];
    loadState = "loaded";
  }

  async function evaluateRule(ruleId: string) {
    if (!isPywebviewReady()) return;
    evalPending = { ...evalPending, [ruleId]: true };
    const resp = await callBridge<AutomationResult>("automation_evaluate_rule", ruleId, {});
    evalPending = { ...evalPending, [ruleId]: false };
    evalResults = { ...evalResults, [ruleId]: resp.ok ? (resp.data ?? null) : null };
  }

  async function evaluateAll() {
    if (!isPywebviewReady()) return;
    evalAllPending = true;
    const resp = await callBridge<AutomationResult[]>("automation_evaluate_all", {});
    evalAllPending = false;
    if (resp.ok && resp.data) {
      const next: Record<string, AutomationResult | null> = {};
      for (const r of resp.data) next[r.rule_id] = r;
      evalResults = next;
    }
  }

  function onTabSwitch(tab: TabId) {
    activeTab = tab;
    if (tab === "rules" && loadState === "idle") loadRules();
  }

  onMount(() => { if (activeTab === "rules") loadRules(); });

  export function refresh() { if (activeTab === "rules") loadRules(); }

  const deferredTabs: Record<Exclude<TabId, "rules">, { title: string; body: string }> = {
    outlook: { title: "Outlook Automation", body: "Email templates, categories, send/download logs. Requires Windows Outlook COM. Deferred pending Windows integration and manual testing." },
    teams: { title: "Teams Automation", body: "Preview-first message automations with guarded Windows execution. Requires pyautogui + Teams desktop. Deferred pending Windows integration and manual testing." },
    scheduler: { title: "Scheduler & Rules Engine", body: "APScheduler job management and trigger-condition-action rule creation. Real controls deferred pending implementation and Windows testing." },
  };
</script>

<div class="am-screen">
  <!-- Tab bar -->
  <div class="am-tab-bar">
    <button class="am-tab" class:active={activeTab === "rules"} onclick={() => onTabSwitch("rules")}>Rules</button>
    <button class="am-tab" class:active={activeTab === "outlook"} onclick={() => onTabSwitch("outlook")}>Outlook</button>
    <button class="am-tab" class:active={activeTab === "teams"} onclick={() => onTabSwitch("teams")}>Teams</button>
    <button class="am-tab" class:active={activeTab === "scheduler"} onclick={() => onTabSwitch("scheduler")}>Scheduler</button>
  </div>

  {#if activeTab === "rules"}
    {#if loadState === "loading"}
      <div class="dashboard-banner banner-loading"><span class="banner-icon">◌</span><span>Loading rules…</span></div>
    {:else if loadState === "error"}
      <div class="dashboard-banner banner-error"><span class="banner-icon">⚠</span><div><p class="banner-title">Rules unavailable</p><p class="banner-detail">{errorCode}: {errorMessage}</p></div></div>
    {:else if rules.length === 0}
      <div class="table-empty"><p class="empty-title">No rules defined</p><p class="empty-sub">Automation rules will appear here. Rule creation is deferred.</p></div>
    {:else}
      <div class="am-rules-list">
        {#each rules as rule}
          <div class="am-rule-card">
            <span class="am-rule-accent" class:enabled={rule.enabled} class:disabled={!rule.enabled}></span>
            <div class="am-rule-body">
              <div class="am-rule-top">
                <h4 class="am-rule-name">{rule.name}</h4>
                <span class="am-rule-badge" class:enabled={rule.enabled} class:disabled={!rule.enabled}>
                  {rule.enabled ? "Enabled" : "Disabled"}
                </span>
                <span class="am-rule-id">{rule.id}</span>
              </div>
              {#if rule.conditions && rule.conditions.length > 0}
                <div class="am-rule-conditions">
                  <span class="am-cond-label">Conditions:</span>
                  {#each rule.conditions as cond}
                    {#if cond && typeof cond === "object" && "field" in cond}
                      <span class="am-cond-pill">
                        <span class="am-cond-field">{String((cond as Record<string, unknown>).field)}</span>
                        <span class="am-cond-op">{String((cond as Record<string, unknown>).operator ?? "?")}</span>
                        {#if (cond as Record<string, unknown>).operator !== "exists" && "value" in cond}
                          <span class="am-cond-val">{String((cond as Record<string, unknown>).value)}</span>
                        {/if}
                      </span>
                    {:else}
                      <code class="am-cond-code">{JSON.stringify(cond)}</code>
                    {/if}
                  {/each}
                </div>
              {:else}
                <p class="muted-text">No conditions defined.</p>
              {/if}
              <div class="am-rule-actions">
                <button class="am-eval-btn" disabled={evalPending[rule.id] === true} onclick={() => evaluateRule(rule.id)}>
                  {#if evalPending[rule.id] === true}◌ Evaluating…{:else}Evaluate (preview){/if}
                </button>
                {#if evalResults[rule.id] !== undefined}
                  {@const r = evalResults[rule.id]}
                  {#if r}
                    <span class="am-eval-result" class:passed={r.passed} class:failed={!r.passed && !r.skipped} class:skipped={r.skipped}>
                      {r.skipped ? "Skipped" : r.passed ? "Passed" : "Failed"} ({r.matched_conditions.length} match)
                    </span>
                  {:else}
                    <span class="am-eval-error">Evaluation failed</span>
                  {/if}
                {/if}
              </div>
            </div>
          </div>
        {/each}
      </div>
      <div class="am-eval-all-bar">
        <button class="am-eval-all-btn" disabled={evalAllPending} onclick={evaluateAll}>
          {#if evalAllPending}◌ Evaluating all…{:else}Evaluate All (preview){/if}
        </button>
        <span class="am-eval-all-hint">Runs all rules with empty context — no real project data, no side effects.</span>
      </div>
      <div class="am-deferred-bar">
        <span>⚠ Rule create/edit/delete deferred. Evaluation uses empty context (no real project data). Outlook/Teams/Scheduler actions not executed. Deferred pending Windows integration.</span>
      </div>
    {/if}
  {:else if activeTab === "teams"}
    <div class="am-teams-pane">
      <TeamsActions />
    </div>
  {:else if activeTab === "scheduler"}
    <div class="am-teams-pane">
      <SchedulerActions />
    </div>
  {:else}
    {@const dt = deferredTabs[activeTab]}
    <div class="am-deferred-tab">
      <div class="placeholder-hero">
        <span class="placeholder-kicker">Deferred</span>
        <h2>{dt.title}</h2>
        <p>{dt.body}</p>
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
  .am-rules-list { flex:1; min-height:0; overflow-y:auto; display:flex; flex-direction:column; gap:8px; padding-right:2px; }
  .am-rule-card { background:#fff; border:1px solid #E5E7EB; border-radius:8px; box-shadow:var(--shadow-subtle); padding:12px; display:flex; gap:10px; }
  .am-rule-accent { width:3px; min-width:3px; border-radius:3px; }
  .am-rule-accent.enabled { background:var(--color-dbs-red); }
  .am-rule-accent.disabled { background:var(--color-muted-light); }
  .am-rule-body { flex:1; min-width:0; display:flex; flex-direction:column; gap:6px; }
  .am-rule-top { display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
  .am-rule-name { margin:0; font-size:12px; font-weight:900; color:var(--color-ink); }
  .am-rule-badge { display:inline-flex; align-items:center; height:18px; padding:0 7px; border-radius:999px; font-size:9px; font-weight:800; }
  .am-rule-badge.enabled { background:var(--color-soft-pink-surface); color:var(--color-dbs-red); border:1px solid var(--color-soft-pink-border); }
  .am-rule-badge.disabled { background:var(--color-workspace-panel); color:var(--color-muted-light); border:1px solid #D7DCE2; }
  .am-rule-id { font-size:9px; color:var(--color-muted-light); font-weight:650; font-family:monospace; }
  .am-rule-conditions { display:flex; align-items:center; gap:6px; flex-wrap:wrap; }
  .am-cond-label { font-size:10px; font-weight:800; color:var(--color-muted); }
  .am-cond-code { font-size:9px; background:var(--color-workspace-panel); padding:2px 6px; border-radius:3px; font-family:monospace; color:var(--color-ink); }
  .am-cond-pill { display:inline-flex; align-items:stretch; border-radius:4px; overflow:hidden; border:1px solid #D7DCE2; font-size:9px; font-weight:750; }
  .am-cond-pill > span { padding:2px 6px; display:inline-flex; align-items:center; }
  .am-cond-field { background:var(--color-workspace-panel); color:var(--color-ink); font-family:monospace; font-weight:800; }
  .am-cond-op { background:var(--color-soft-pink-surface); color:var(--color-dbs-red); font-weight:800; border-left:1px solid #D7DCE2; }
  .am-cond-val { background:#fff; color:var(--color-ink); font-family:monospace; border-left:1px solid #D7DCE2; }
  .am-rule-actions { display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-top:4px; }
  .am-eval-btn { height:24px; border-radius:5px; padding:0 10px; background:var(--color-dbs-red); color:#fff; border:1px solid var(--color-dbs-red-hover); font-weight:800; font-size:10px; cursor:pointer; white-space:nowrap; transition:background 0.15s; }
  .am-eval-btn:hover:not(:disabled) { background:var(--color-dbs-red-hover); }
  .am-eval-btn:disabled { opacity:0.55; cursor:not-allowed; }
  .am-eval-result { font-size:10px; font-weight:800; padding:2px 8px; border-radius:4px; }
  .am-eval-result.passed { background:#dcfce7; color:#166534; }
  .am-eval-result.failed { background:var(--color-soft-pink-surface); color:var(--color-dbs-red); }
  .am-eval-result.skipped { background:var(--color-workspace-panel); color:var(--color-muted); }
  .am-eval-error { font-size:10px; color:var(--color-dbs-red); font-weight:750; }
  .am-eval-all-bar { display:flex; align-items:center; gap:10px; flex:0 0 auto; flex-wrap:wrap; }
  .am-eval-all-btn { height:28px; border-radius:5px; padding:0 14px; background:var(--color-dbs-red); color:#fff; border:1px solid var(--color-dbs-red-hover); font-weight:850; font-size:11px; cursor:pointer; white-space:nowrap; transition:background 0.15s; }
  .am-eval-all-btn:hover:not(:disabled) { background:var(--color-dbs-red-hover); }
  .am-eval-all-btn:disabled { opacity:0.55; cursor:not-allowed; }
  .am-eval-all-hint { font-size:10px; color:var(--color-muted); font-weight:700; }
  .am-deferred-tab { flex:1; display:flex; align-items:center; justify-content:center; }
  .am-teams-pane { flex:1; min-height:0; overflow-y:auto; padding:4px 2px; }
  .am-deferred-tab .placeholder-hero { max-width:520px; }
  .am-deferred-bar { background:var(--color-soft-pink-surface); border:1px solid var(--color-soft-pink-border); border-radius:6px; padding:8px 12px; font-size:10px; font-weight:750; color:var(--color-dbs-red); flex:0 0 auto; }
</style>
