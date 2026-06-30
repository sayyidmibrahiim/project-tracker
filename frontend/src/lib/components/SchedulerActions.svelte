<script lang="ts">
  /**
   * Scheduler control surface for the Automations → Scheduler tab
   * (Requirements 3.1, 10.1, 10.7).
   *
   *  - Status: scheduler_status / scheduler_start / scheduler_stop / scheduler_run_once.
   *  - Entry table: scheduler_entry_list / create / update / delete / toggle.
   *  - Outlook/Teams-channel entries are flagged via the backend
   *    ``requires_confirmation`` field. Triggering such an entry is gated behind
   *    a ConfirmModal; cancel/dismiss issues no bridge call (Req 3.1).
   *
   * All bridge access goes through `callBridge` (no direct `window.pywebview`).
   */
  import { onMount } from "svelte";
  import { callBridge, isPywebviewReady } from "../bridge";
  import ConfirmModal from "./ConfirmModal.svelte";

  type SchedulerStatus = { is_running: boolean };

  type SchedulerEntry = {
    id: string;
    name: string;
    notes?: string;
    schedule_type: string;
    schedule_config?: Record<string, unknown>;
    project_filter?: string | null;
    state_filter?: string | null;
    channels: string[];
    channel_configs?: Record<string, unknown>;
    enabled: boolean;
    status: string;
    requires_confirmation?: boolean;
  };

  const SCHEDULE_TYPES = ["one_time", "daily", "weekly", "monthly", "cron"] as const;
  const CHANNELS = ["in_app", "outlook_email", "teams"] as const;

  let status: SchedulerStatus = $state({ is_running: false });
  let entries: SchedulerEntry[] = $state([]);
  let busy: boolean = $state(false);
  let errorText: string = $state("");

  // New-entry form state.
  let formOpen: boolean = $state(false);
  let editingId: string = $state("");
  let formName: string = $state("");
  let formScheduleType: string = $state("daily");
  let formChannels: Set<string> = $state(new Set(["in_app"]));
  let formProjectFilter: string = $state("");
  let formStateFilter: string = $state("");

  let pendingTriggerEntry: SchedulerEntry | null = $state(null);
  let pendingDeleteEntry: SchedulerEntry | null = $state(null);
  let triggerMessage: string = $state("");

  function setError(msg: string) {
    errorText = msg;
  }

  async function refreshStatus() {
    if (!isPywebviewReady()) return;
    const resp = await callBridge<SchedulerStatus>("scheduler_status");
    if (resp.ok && resp.data) status = resp.data;
  }

  async function refreshEntries() {
    if (!isPywebviewReady()) return;
    const resp = await callBridge<SchedulerEntry[]>("scheduler_entry_list");
    if (!resp.ok) {
      setError(resp.error.message);
      return;
    }
    entries = resp.data ?? [];
    setError("");
  }

  async function startScheduler() {
    busy = true;
    const resp = await callBridge<SchedulerStatus>("scheduler_start");
    busy = false;
    if (!resp.ok) { setError(resp.error.message); return; }
    if (resp.data) status = resp.data;
  }
  async function stopScheduler() {
    busy = true;
    const resp = await callBridge<SchedulerStatus>("scheduler_stop");
    busy = false;
    if (!resp.ok) { setError(resp.error.message); return; }
    if (resp.data) status = resp.data;
  }
  async function runOnce() {
    busy = true;
    const resp = await callBridge<SchedulerStatus>("scheduler_run_once");
    busy = false;
    if (!resp.ok) { setError(resp.error.message); return; }
    if (resp.data) status = resp.data;
  }

  function openCreate() {
    editingId = "";
    formName = "";
    formScheduleType = "daily";
    formChannels = new Set(["in_app"]);
    formProjectFilter = "";
    formStateFilter = "";
    formOpen = true;
  }

  function openEdit(entry: SchedulerEntry) {
    editingId = entry.id;
    formName = entry.name;
    formScheduleType = entry.schedule_type;
    formChannels = new Set(entry.channels ?? []);
    formProjectFilter = entry.project_filter ?? "";
    formStateFilter = entry.state_filter ?? "";
    formOpen = true;
  }

  function closeForm() {
    formOpen = false;
    editingId = "";
  }

  function toggleChannel(ch: string, on: boolean) {
    const next = new Set(formChannels);
    if (on) next.add(ch); else next.delete(ch);
    formChannels = next;
  }

  async function submitForm() {
    if (!formName.trim()) { setError("Entry name is required."); return; }
    busy = true;
    const payload = {
      name: formName.trim(),
      schedule_type: formScheduleType,
      channels: [...formChannels],
      project_filter: formProjectFilter.trim() || null,
      state_filter: formStateFilter.trim() || null,
    };
    const resp = editingId
      ? await callBridge<SchedulerEntry>("scheduler_entry_update", editingId, payload)
      : await callBridge<SchedulerEntry>("scheduler_entry_create", payload);
    busy = false;
    if (!resp.ok) { setError(resp.error.message); return; }
    closeForm();
    await refreshEntries();
  }

  function requestDelete(entry: SchedulerEntry) {
    setError("");
    pendingDeleteEntry = entry;
  }
  function cancelDelete() {
    pendingDeleteEntry = null;
  }
  async function confirmDelete() {
    const entry = pendingDeleteEntry;
    pendingDeleteEntry = null;
    if (!entry) return;
    busy = true;
    const resp = await callBridge<{ deleted: string }>("scheduler_entry_delete", entry.id);
    busy = false;
    if (!resp.ok) { setError(resp.error.message); return; }
    await refreshEntries();
  }

  async function toggleEntry(entry: SchedulerEntry) {
    busy = true;
    const resp = await callBridge<SchedulerEntry>("scheduler_entry_toggle", entry.id, !entry.enabled);
    busy = false;
    if (!resp.ok) { setError(resp.error.message); return; }
    await refreshEntries();
  }

  function requestTrigger(entry: SchedulerEntry) {
    setError("");
    if (entry.requires_confirmation) {
      pendingTriggerEntry = entry;
      return;
    }
    triggerEntry(entry.id);
  }
  function cancelTrigger() {
    pendingTriggerEntry = null;
  }
  async function triggerEntry(entryId: string) {
    busy = true;
    triggerMessage = "";
    const resp = await callBridge<Record<string, unknown>>("scheduler_entry_trigger", entryId);
    busy = false;
    if (!resp.ok || !resp.data) {
      setError(resp.ok ? "Trigger returned no data." : resp.error.message);
      return;
    }
    const data = resp.data as Record<string, unknown>;
    const matched = Array.isArray(data.matched_projects) ? (data.matched_projects as string[]).join(", ") : "";
    if (data.matched) {
      const pending = Array.isArray(data.pending_confirmation_channels) ? (data.pending_confirmation_channels as string[]).join(", ") : "";
      triggerMessage = `Matched: ${matched || "(no names)"}` + (pending ? ` · pending confirmation: ${pending}` : "");
    } else {
      triggerMessage = `No match: ${data.reason ?? "unknown"}`;
    }
    await refreshEntries();
  }
  async function confirmTrigger() {
    const entry = pendingTriggerEntry;
    pendingTriggerEntry = null;
    if (!entry) return;
    await triggerEntry(entry.id);
  }

  onMount(async () => {
    await refreshStatus();
    await refreshEntries();
  });
</script>

<div class="sc-root">
  <!-- Status bar -->
  <div class="sc-status-bar">
    <span class="sc-status-label">Scheduler</span>
    <span class="sc-status-pill" class:running={status.is_running}>{status.is_running ? "Running" : "Stopped"}</span>
    <button class="sc-btn" onclick={startScheduler} disabled={busy || status.is_running}>Start</button>
    <button class="sc-btn" onclick={stopScheduler} disabled={busy || !status.is_running}>Stop</button>
    <button class="sc-btn" onclick={runOnce} disabled={busy}>Run once</button>
    <button class="sc-btn sc-btn-primary" onclick={openCreate} disabled={busy || formOpen}>+ New entry</button>
  </div>

  {#if errorText}
    <div class="sc-error" role="alert">⚠ {errorText}</div>
  {/if}
  {#if triggerMessage}
    <div class="sc-info" role="status">▸ {triggerMessage}</div>
  {/if}

  <!-- Entry list -->
  {#if entries.length === 0}
    <div class="sc-empty">No scheduler entries. Click “+ New entry” to add one.</div>
  {:else}
    <div class="sc-list">
      {#each entries as entry}
        <div class="sc-card" class:disabled={!entry.enabled}>
          <div class="sc-card-head">
            <span class="sc-name">{entry.name || "(unnamed)"}</span>
            <span class="sc-pill" class:enabled={entry.enabled} class:disabled={!entry.enabled}>{entry.enabled ? "Enabled" : "Disabled"}</span>
            <span class="sc-pill sc-pill-info">{entry.schedule_type}</span>
            {#each entry.channels as ch}
              <span class="sc-pill sc-pill-channel">{ch}</span>
            {/each}
            {#if entry.requires_confirmation}
              <span class="sc-pill sc-pill-warn" title="Outlook/Teams channel — requires confirmation">⚠ confirm</span>
            {/if}
          </div>
          <div class="sc-card-meta">
            {#if entry.project_filter}<span>project: <code>{entry.project_filter}</code></span>{/if}
            {#if entry.state_filter}<span>state: <code>{entry.state_filter}</code></span>{/if}
            <span class="sc-id">{entry.id}</span>
          </div>
          <div class="sc-card-actions">
            <button class="sc-btn" onclick={() => openEdit(entry)} disabled={busy}>Edit</button>
            <button class="sc-btn" onclick={() => toggleEntry(entry)} disabled={busy}>
              {entry.enabled ? "Disable" : "Enable"}
            </button>
            <button class="sc-btn" onclick={() => requestTrigger(entry)} disabled={busy}>Trigger now</button>
            <button class="sc-btn sc-btn-danger" onclick={() => requestDelete(entry)} disabled={busy}>Delete</button>
          </div>
        </div>
      {/each}
    </div>
  {/if}

  <!-- Create/edit form -->
  {#if formOpen}
    <div class="sc-form">
      <h4 class="sc-form-title">{editingId ? "Edit scheduler entry" : "New scheduler entry"}</h4>
      <div class="sc-form-row">
        <label class="sc-label">Name<input class="sc-input" bind:value={formName} disabled={busy} /></label>
        <label class="sc-label">Schedule type
          <select class="sc-input" bind:value={formScheduleType} disabled={busy}>
            {#each SCHEDULE_TYPES as t}<option value={t}>{t}</option>{/each}
          </select>
        </label>
      </div>
      <div class="sc-form-row">
        <label class="sc-label">Project filter (exact name)<input class="sc-input" bind:value={formProjectFilter} disabled={busy} placeholder="(optional)" /></label>
        <label class="sc-label">State filter<input class="sc-input" bind:value={formStateFilter} disabled={busy} placeholder="(optional)" /></label>
      </div>
      <div class="sc-form-row">
        <span class="sc-label">Channels</span>
        <div class="sc-channel-row">
          {#each CHANNELS as ch}
            <label class="sc-channel-chk">
              <input type="checkbox" checked={formChannels.has(ch)} onchange={(e) => toggleChannel(ch, (e.currentTarget as HTMLInputElement).checked)} disabled={busy} />
              {ch}
            </label>
          {/each}
        </div>
      </div>
      <div class="sc-form-actions">
        <button class="sc-btn" onclick={closeForm} disabled={busy}>Cancel</button>
        <button class="sc-btn sc-btn-primary" onclick={submitForm} disabled={busy}>{editingId ? "Save" : "Create"}</button>
      </div>
    </div>
  {/if}
</div>

{#if pendingTriggerEntry}
  <ConfirmModal
    title="Trigger scheduler entry"
    actionLabel="Trigger"
    targetName={`${pendingTriggerEntry.name} — channels: ${pendingTriggerEntry.channels.join(", ")}`}
    reversible={false}
    onConfirm={confirmTrigger}
    onCancel={cancelTrigger}
  />
{/if}

{#if pendingDeleteEntry}
  <ConfirmModal
    title="Delete scheduler entry"
    actionLabel="Delete"
    targetName={pendingDeleteEntry.name || pendingDeleteEntry.id}
    reversible={false}
    onConfirm={confirmDelete}
    onCancel={cancelDelete}
  />
{/if}

<style>
  .sc-root { display:flex; flex-direction:column; gap:10px; max-width:760px; }
  .sc-status-bar { display:flex; align-items:center; gap:8px; flex-wrap:wrap; padding:8px 10px; background:var(--color-workspace-panel); border:1px solid #D7DCE2; border-radius:6px; }
  .sc-status-label { font-size:11px; font-weight:900; color:var(--color-ink); margin-right:4px; }
  .sc-status-pill { font-size:9px; font-weight:800; padding:2px 8px; border-radius:999px; background:var(--color-workspace-panel); color:var(--color-muted-light); border:1px solid #D7DCE2; }
  .sc-status-pill.running { background:#dcfce7; color:#166534; border-color:#86efac; }
  .sc-btn { padding:5px 11px; font-size:10px; font-weight:800; border:1px solid #D7DCE2; border-radius:5px; background:#fff; color:var(--color-ink,#111827); cursor:pointer; white-space:nowrap; }
  .sc-btn:hover:not(:disabled) { border-color:var(--color-dbs-red,#DA1E28); color:var(--color-dbs-red,#DA1E28); }
  .sc-btn:disabled { opacity:0.5; cursor:not-allowed; }
  .sc-btn-primary { border-color:var(--color-dbs-red,#DA1E28); color:#fff; background:var(--color-dbs-red,#DA1E28); }
  .sc-btn-primary:hover:not(:disabled) { background:var(--color-dbs-red-hover,#B71820); }
  .sc-btn-danger { border-color:var(--color-dbs-red,#DA1E28); color:var(--color-dbs-red,#DA1E28); }
  .sc-btn-danger:hover:not(:disabled) { background:var(--color-dbs-red,#DA1E28); color:#fff; }
  .sc-error { font-size:10px; font-weight:800; color:var(--color-dbs-red,#DA1E28); padding:6px 10px; background:var(--color-soft-pink-surface); border:1px solid var(--color-soft-pink-border); border-radius:5px; }
  .sc-info { font-size:10px; font-weight:800; color:#166534; padding:6px 10px; background:#dcfce7; border:1px solid #86efac; border-radius:5px; }
  .sc-empty { font-size:11px; font-weight:700; color:var(--color-muted); padding:14px; text-align:center; background:#fff; border:1px dashed #D7DCE2; border-radius:6px; }
  .sc-list { display:flex; flex-direction:column; gap:8px; }
  .sc-card { background:#fff; border:1px solid #E5E7EB; border-left:3px solid var(--color-dbs-red); border-radius:6px; padding:10px 12px; display:flex; flex-direction:column; gap:6px; box-shadow:var(--shadow-subtle); }
  .sc-card.disabled { border-left-color:var(--color-muted-light); opacity:0.85; }
  .sc-card-head { display:flex; align-items:center; gap:6px; flex-wrap:wrap; }
  .sc-name { font-size:12px; font-weight:900; color:var(--color-ink); }
  .sc-pill { font-size:9px; font-weight:800; padding:2px 7px; border-radius:999px; border:1px solid #D7DCE2; background:var(--color-workspace-panel); color:var(--color-muted-light); }
  .sc-pill.enabled { background:var(--color-soft-pink-surface); color:var(--color-dbs-red); border-color:var(--color-soft-pink-border); }
  .sc-pill.disabled { background:var(--color-workspace-panel); color:var(--color-muted-light); }
  .sc-pill-info { background:#eef2ff; color:#3730a3; border-color:#c7d2fe; }
  .sc-pill-channel { background:#f3f4f6; color:var(--color-ink); border-color:#D7DCE2; }
  .sc-pill-warn { background:#fef3c7; color:#92400e; border-color:#fde68a; }
  .sc-card-meta { display:flex; gap:10px; flex-wrap:wrap; font-size:10px; color:var(--color-muted); font-weight:700; }
  .sc-id { font-family:monospace; opacity:0.7; }
  .sc-card-actions { display:flex; gap:6px; flex-wrap:wrap; }
  .sc-form { background:#fff; border:1px solid #D7DCE2; border-radius:6px; padding:12px; display:flex; flex-direction:column; gap:10px; }
  .sc-form-title { margin:0; font-size:12px; font-weight:900; color:var(--color-ink); }
  .sc-form-row { display:flex; gap:10px; flex-wrap:wrap; }
  .sc-label { display:flex; flex-direction:column; gap:4px; flex:1; min-width:160px; font-size:9px; font-weight:800; color:var(--color-muted); text-transform:uppercase; letter-spacing:0.3px; }
  .sc-input { padding:5px 8px; font-size:11px; font-weight:700; border:1px solid #D7DCE2; border-radius:5px; background:#fff; color:var(--color-ink); outline:none; text-transform:none; letter-spacing:normal; }
  .sc-input:focus { border-color:var(--color-dbs-red); }
  .sc-input:disabled { background:#f3f4f6; color:var(--color-muted); }
  .sc-channel-row { display:flex; gap:10px; flex-wrap:wrap; }
  .sc-channel-chk { display:inline-flex; align-items:center; gap:4px; font-size:10px; font-weight:700; color:var(--color-ink); text-transform:none; letter-spacing:normal; }
  .sc-form-actions { display:flex; justify-content:flex-end; gap:8px; }
</style>
