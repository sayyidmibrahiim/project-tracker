<script lang="ts">
  /**
   * Rules CRUD + per-rule logs view for the Automations → Rules tab
   * (Requirements 3.1, 11.1).
   *
   * Wires:
   *  - automation_list_rules / automation_evaluate_rule / automation_evaluate_all
   *  - rules_create / rules_update / rules_delete / rules_toggle / rules_get_logs
   *
   * Outlook/Teams actions inside a rule are flagged and saving such a rule is
   * gated behind a ConfirmModal (Req 3.1). Cancel/dismiss issues no bridge call.
   *
   * All bridge access goes through `callBridge` (no direct `window.pywebview`).
   */
  import { onMount } from "svelte";
  import { callBridge, isPywebviewReady } from "../bridge";
  import type { AutomationRule, AutomationResult } from "../types";
  import { BridgeErrorCode } from "../types";
  import ConfirmModal from "./ConfirmModal.svelte";

  type RuleAction = { type: string; params?: Record<string, unknown> };
  type StoredRule = AutomationRule & { actions?: RuleAction[] };

  type RuleLog = {
    rule_id: string;
    rule_name: string;
    trigger_type: string;
    conditions_passed: number | boolean;
    actions_executed: unknown;
    success: boolean;
    error_message: string | null;
    timestamp: string;
  };

  const ACTION_TYPES = [
    "download_email",
    "save_attachment",
    "update_cr_state",
    "update_drone_state",
    "send_outlook_email",
    "send_teams_message",
    "in_app_notification",
    "append_history",
  ] as const;
  const HIGH_RISK_ACTIONS = new Set(["send_outlook_email", "send_teams_message"]);

  type LoadState = "idle" | "loading" | "error" | "loaded";
  let loadState: LoadState = $state("idle");
  let errorCode: string = $state("");
  let errorMessage: string = $state("");

  let rules: StoredRule[] = $state([]);
  let evalResults: Record<string, AutomationResult | null> = $state({});
  let evalPending: Record<string, boolean> = $state({});
  let evalAllPending: boolean = $state(false);
  let execPending: Record<string, boolean> = $state({});
  let execResults: Record<string, string> = $state({});

  // Form state.
  let formOpen: boolean = $state(false);
  let editingId: string = $state("");
  let formName: string = $state("");
  let formEnabled: boolean = $state(true);
  let formActions: { type: string }[] = $state([]);
  let pendingHighRiskSave: { payload: Record<string, unknown>; isUpdate: boolean } | null = $state(null);

  // Per-rule logs panel.
  let logsForRule: string = $state("");
  let logsLoading: boolean = $state(false);
  let logs: RuleLog[] = $state([]);

  // ── load ──
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
    const resp = await callBridge<StoredRule[]>("automation_list_rules");
    if (!resp.ok) {
      errorCode = resp.error.code;
      errorMessage = resp.error.message;
      loadState = "error";
      return;
    }
    rules = resp.data ?? [];
    loadState = "loaded";
  }

  onMount(loadRules);

  // ── evaluate ──
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

  async function executeRule(ruleId: string) {
    if (!isPywebviewReady()) return;
    execPending = { ...execPending, [ruleId]: true };
    const resp = await callBridge<Record<string, unknown>>("automation_execute_rule", ruleId, {});
    execPending = { ...execPending, [ruleId]: false };
    if (!resp.ok) {
      execResults = { ...execResults, [ruleId]: `✗ ${resp.error.message}` };
      return;
    }
    const data = resp.data ?? {};
    if (data.skipped) {
      execResults = { ...execResults, [ruleId]: "⊘ skipped (disabled)" };
    } else if (!data.conditions_met) {
      execResults = { ...execResults, [ruleId]: "⊘ conditions not met" };
    } else if (data.ok === false) {
      execResults = { ...execResults, [ruleId]: `✗ ${data.failed_action ?? ""}: ${data.error_message ?? ""}` };
    } else {
      const executed = Array.isArray(data.actions_executed) ? (data.actions_executed as string[]).join(", ") : "";
      execResults = { ...execResults, [ruleId]: executed ? `✓ executed: ${executed}` : "✓ executed" };
    }
  }

  // ── form helpers ──
  function openCreate() {
    editingId = "";
    formName = "";
    formEnabled = true;
    formActions = [];
    formOpen = true;
  }
  function openEdit(rule: StoredRule) {
    editingId = rule.id;
    formName = rule.name;
    formEnabled = rule.enabled !== false;
    formActions = (rule.actions ?? []).map((a) => ({ type: a.type }));
    formOpen = true;
  }
  function closeForm() {
    formOpen = false;
    editingId = "";
    pendingHighRiskSave = null;
  }
  function addAction() {
    formActions = [...formActions, { type: ACTION_TYPES[0] }];
  }
  function setActionType(idx: number, value: string) {
    formActions = formActions.map((a, i) => (i === idx ? { type: value } : a));
  }
  function removeAction(idx: number) {
    formActions = formActions.filter((_, i) => i !== idx);
  }
  function hasHighRisk(actions: { type: string }[]): boolean {
    return actions.some((a) => HIGH_RISK_ACTIONS.has(a.type));
  }

  async function submitForm() {
    if (!formName.trim()) {
      errorMessage = "Rule name is required.";
      return;
    }
    const payload: Record<string, unknown> = {
      name: formName.trim(),
      enabled: formEnabled,
      actions: formActions,
    };
    const isUpdate = Boolean(editingId);
    if (hasHighRisk(formActions)) {
      pendingHighRiskSave = { payload, isUpdate };
      return;
    }
    await persistRule(payload, isUpdate);
  }
  async function confirmHighRiskSave() {
    if (!pendingHighRiskSave) return;
    const { payload, isUpdate } = pendingHighRiskSave;
    pendingHighRiskSave = null;
    await persistRule(payload, isUpdate);
  }
  function cancelHighRiskSave() {
    pendingHighRiskSave = null;
  }
  async function persistRule(payload: Record<string, unknown>, isUpdate: boolean) {
    const resp = isUpdate
      ? await callBridge<StoredRule>("rules_update", editingId, payload)
      : await callBridge<StoredRule>("rules_create", payload);
    if (!resp.ok) {
      errorMessage = resp.error.message;
      errorCode = resp.error.code;
      return;
    }
    closeForm();
    await loadRules();
  }

  async function toggleRule(rule: StoredRule) {
    const resp = await callBridge<StoredRule>("rules_toggle", rule.id, !rule.enabled);
    if (!resp.ok) {
      errorMessage = resp.error.message;
      errorCode = resp.error.code;
      return;
    }
    await loadRules();
  }
  async function deleteRule(rule: StoredRule) {
    const resp = await callBridge<{ deleted: string }>("rules_delete", rule.id);
    if (!resp.ok) {
      errorMessage = resp.error.message;
      errorCode = resp.error.code;
      return;
    }
    await loadRules();
  }

  async function viewLogs(rule: StoredRule) {
    logsForRule = rule.id;
    logsLoading = true;
    logs = [];
    const resp = await callBridge<RuleLog[]>("rules_get_logs", rule.id, 50);
    logsLoading = false;
    if (resp.ok) logs = resp.data ?? [];
  }
  function closeLogs() {
    logsForRule = "";
    logs = [];
  }
</script>

<div class="ru-root">
  <!-- Toolbar -->
  <div class="ru-toolbar">
    <button class="ru-btn ru-btn-primary" onclick={openCreate} disabled={formOpen}>+ New rule</button>
    <button class="ru-btn" onclick={evaluateAll} disabled={evalAllPending}>
      {#if evalAllPending}◌ Evaluating all…{:else}Evaluate All (preview){/if}
    </button>
    <span class="ru-hint">Empty-context preview — no real project data, no side effects.</span>
  </div>

  {#if loadState === "loading"}
    <div class="dashboard-banner banner-loading"><span class="banner-icon">◌</span><span>Loading rules…</span></div>
  {:else if loadState === "error"}
    <div class="dashboard-banner banner-error"><span class="banner-icon">⚠</span><div><p class="banner-title">Rules unavailable</p><p class="banner-detail">{errorCode}: {errorMessage}</p></div></div>
  {:else if rules.length === 0}
    <div class="ru-empty">No rules defined. Click “+ New rule” to add one.</div>
  {:else}
    <div class="ru-list">
      {#each rules as rule}
        <div class="ru-card" class:disabled={!rule.enabled}>
          <div class="ru-card-head">
            <span class="ru-name">{rule.name || "(unnamed)"}</span>
            <span class="ru-pill" class:enabled={rule.enabled} class:disabled={!rule.enabled}>{rule.enabled ? "Enabled" : "Disabled"}</span>
            {#if hasHighRisk(rule.actions ?? [])}
              <span class="ru-pill ru-pill-warn" title="Outlook/Teams action">⚠ high-risk</span>
            {/if}
            <span class="ru-id">{rule.id}</span>
          </div>
          {#if rule.actions && rule.actions.length > 0}
            <div class="ru-actions-list">
              {#each rule.actions as action}
                <span class="ru-action-pill" class:warn={HIGH_RISK_ACTIONS.has(action.type)}>{action.type}</span>
              {/each}
            </div>
          {/if}
          <div class="ru-card-actions">
            <button class="ru-btn" onclick={() => evaluateRule(rule.id)} disabled={evalPending[rule.id] === true}>
              {#if evalPending[rule.id] === true}◌ Evaluating…{:else}Evaluate (preview){/if}
            </button>
            <button class="ru-btn ru-btn-primary" onclick={() => executeRule(rule.id)} disabled={execPending[rule.id] === true}>
              {#if execPending[rule.id] === true}◌ Executing…{:else}Execute{/if}
            </button>
            {#if evalResults[rule.id] !== undefined}
              {@const r = evalResults[rule.id]}
              {#if r}
                <span class="ru-eval-badge" class:passed={r.passed} class:failed={!r.passed && !r.skipped} class:skipped={r.skipped}>
                  {r.skipped ? "Skipped" : r.passed ? "Passed" : "Failed"}
                </span>
              {/if}
            {/if}
            {#if execResults[rule.id]}<span class="ru-exec-badge">{execResults[rule.id]}</span>{/if}
            <button class="ru-btn" onclick={() => openEdit(rule)}>Edit</button>
            <button class="ru-btn" onclick={() => toggleRule(rule)}>{rule.enabled ? "Disable" : "Enable"}</button>
            <button class="ru-btn" onclick={() => viewLogs(rule)}>Logs</button>
            <button class="ru-btn ru-btn-danger" onclick={() => deleteRule(rule)}>Delete</button>
          </div>
        </div>
      {/each}
    </div>
  {/if}

  <!-- Form -->
  {#if formOpen}
    <div class="ru-form">
      <h4 class="ru-form-title">{editingId ? "Edit rule" : "New rule"}</h4>
      <label class="ru-label">Name<input class="ru-input" bind:value={formName} /></label>
      <label class="ru-checkbox"><input type="checkbox" bind:checked={formEnabled} /> Enabled</label>
      <div class="ru-form-block">
        <span class="ru-label">Actions (executed in order, halt on first failure)</span>
        {#each formActions as action, i}
          <div class="ru-form-action-row">
            <select class="ru-input" value={action.type} onchange={(e) => setActionType(i, (e.currentTarget as HTMLSelectElement).value)}>
              {#each ACTION_TYPES as t}<option value={t}>{t}</option>{/each}
            </select>
            {#if HIGH_RISK_ACTIONS.has(action.type)}
              <span class="ru-pill ru-pill-warn">⚠ high-risk</span>
            {/if}
            <button class="ru-btn ru-btn-danger" onclick={() => removeAction(i)}>Remove</button>
          </div>
        {/each}
        <button class="ru-btn" onclick={addAction}>+ Add action</button>
      </div>
      <div class="ru-form-actions">
        <button class="ru-btn" onclick={closeForm}>Cancel</button>
        <button class="ru-btn ru-btn-primary" onclick={submitForm}>{editingId ? "Save" : "Create"}</button>
      </div>
    </div>
  {/if}

  <!-- Logs -->
  {#if logsForRule}
    <div class="ru-form">
      <h4 class="ru-form-title">Logs · <code>{logsForRule}</code></h4>
      {#if logsLoading}<p class="ru-hint">◌ Loading logs…</p>
      {:else if logs.length === 0}<p class="ru-hint">No execution logs recorded for this rule.</p>
      {:else}
        <div class="ru-logs">
          {#each logs as log}
            <div class="ru-log-row" class:ok={log.success} class:err={!log.success}>
              <span class="ru-log-ts">{log.timestamp}</span>
              <span class="ru-log-result">{log.success ? "✓ ok" : "✗ failed"}</span>
              {#if log.error_message}<span class="ru-log-err">{log.error_message}</span>{/if}
            </div>
          {/each}
        </div>
      {/if}
      <div class="ru-form-actions"><button class="ru-btn" onclick={closeLogs}>Close</button></div>
    </div>
  {/if}
</div>

{#if pendingHighRiskSave}
  <ConfirmModal
    title={pendingHighRiskSave.isUpdate ? "Save rule with high-risk action" : "Create rule with high-risk action"}
    actionLabel={pendingHighRiskSave.isUpdate ? "Save rule" : "Create rule"}
    targetName={`${formName} — includes Outlook/Teams action`}
    reversible={false}
    onConfirm={confirmHighRiskSave}
    onCancel={cancelHighRiskSave}
  />
{/if}

<style>
  .ru-root { display:flex; flex-direction:column; gap:10px; }
  .ru-toolbar { display:flex; align-items:center; gap:8px; flex-wrap:wrap; padding:6px 10px; background:var(--color-workspace-panel); border:1px solid #D7DCE2; border-radius:6px; }
  .ru-btn { padding:5px 11px; font-size:10px; font-weight:800; border:1px solid #D7DCE2; border-radius:5px; background:#fff; color:var(--color-ink,#111827); cursor:pointer; white-space:nowrap; }
  .ru-btn:hover:not(:disabled) { border-color:var(--color-dbs-red,#DA1E28); color:var(--color-dbs-red,#DA1E28); }
  .ru-btn:disabled { opacity:0.5; cursor:not-allowed; }
  .ru-btn-primary { border-color:var(--color-dbs-red,#DA1E28); color:#fff; background:var(--color-dbs-red,#DA1E28); }
  .ru-btn-primary:hover:not(:disabled) { background:var(--color-dbs-red-hover,#B71820); }
  .ru-btn-danger { border-color:var(--color-dbs-red,#DA1E28); color:var(--color-dbs-red,#DA1E28); }
  .ru-btn-danger:hover:not(:disabled) { background:var(--color-dbs-red,#DA1E28); color:#fff; }
  .ru-hint { font-size:10px; color:var(--color-muted); font-weight:700; }
  .ru-empty { font-size:11px; font-weight:700; color:var(--color-muted); padding:14px; text-align:center; background:#fff; border:1px dashed #D7DCE2; border-radius:6px; }
  .ru-list { display:flex; flex-direction:column; gap:8px; }
  .ru-card { background:#fff; border:1px solid #E5E7EB; border-left:3px solid var(--color-dbs-red); border-radius:6px; padding:10px 12px; display:flex; flex-direction:column; gap:6px; box-shadow:var(--shadow-subtle); }
  .ru-card.disabled { border-left-color:var(--color-muted-light); opacity:0.85; }
  .ru-card-head { display:flex; align-items:center; gap:6px; flex-wrap:wrap; }
  .ru-name { font-size:12px; font-weight:900; color:var(--color-ink); }
  .ru-id { font-size:9px; color:var(--color-muted-light); font-weight:650; font-family:monospace; }
  .ru-pill { font-size:9px; font-weight:800; padding:2px 7px; border-radius:999px; border:1px solid #D7DCE2; background:var(--color-workspace-panel); color:var(--color-muted-light); }
  .ru-pill.enabled { background:var(--color-soft-pink-surface); color:var(--color-dbs-red); border-color:var(--color-soft-pink-border); }
  .ru-pill-warn { background:#fef3c7; color:#92400e; border-color:#fde68a; }
  .ru-actions-list { display:flex; gap:4px; flex-wrap:wrap; }
  .ru-action-pill { font-size:9px; font-weight:750; padding:2px 7px; border-radius:4px; background:#f3f4f6; color:var(--color-ink); border:1px solid #D7DCE2; font-family:monospace; }
  .ru-action-pill.warn { background:#fef3c7; color:#92400e; border-color:#fde68a; }
  .ru-card-actions { display:flex; gap:6px; flex-wrap:wrap; }
  .ru-eval-badge { font-size:9px; font-weight:800; padding:2px 7px; border-radius:4px; }
  .ru-eval-badge.passed { background:#dcfce7; color:#166534; }
  .ru-eval-badge.failed { background:var(--color-soft-pink-surface); color:var(--color-dbs-red); }
  .ru-eval-badge.skipped { background:var(--color-workspace-panel); color:var(--color-muted); }
  .ru-exec-badge { font-size:9px; font-weight:800; padding:2px 7px; border-radius:4px; background:var(--color-workspace-panel); color:var(--color-ink); border:1px solid #D7DCE2; max-width:320px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .ru-form { background:#fff; border:1px solid #D7DCE2; border-radius:6px; padding:12px; display:flex; flex-direction:column; gap:8px; }
  .ru-form-title { margin:0; font-size:12px; font-weight:900; color:var(--color-ink); }
  .ru-label { display:flex; flex-direction:column; gap:4px; font-size:9px; font-weight:800; color:var(--color-muted); text-transform:uppercase; letter-spacing:0.3px; }
  .ru-checkbox { font-size:10px; font-weight:700; color:var(--color-ink); display:inline-flex; gap:4px; align-items:center; }
  .ru-input { padding:5px 8px; font-size:11px; font-weight:700; border:1px solid #D7DCE2; border-radius:5px; background:#fff; color:var(--color-ink); outline:none; text-transform:none; letter-spacing:normal; }
  .ru-input:focus { border-color:var(--color-dbs-red); }
  .ru-form-block { display:flex; flex-direction:column; gap:6px; }
  .ru-form-action-row { display:flex; gap:6px; align-items:center; flex-wrap:wrap; }
  .ru-form-actions { display:flex; gap:6px; justify-content:flex-end; }
  .ru-logs { display:flex; flex-direction:column; gap:4px; max-height:280px; overflow-y:auto; }
  .ru-log-row { display:flex; gap:8px; padding:4px 6px; border-radius:4px; font-size:10px; font-weight:700; flex-wrap:wrap; }
  .ru-log-row.ok { background:#ecfdf5; color:#166534; }
  .ru-log-row.err { background:var(--color-soft-pink-surface); color:var(--color-dbs-red); }
  .ru-log-ts { font-family:monospace; }
  .ru-log-result { font-weight:900; }
</style>
