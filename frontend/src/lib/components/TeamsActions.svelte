<script lang="ts">
  /**
   * Gated Teams message control for the Automations → Teams tab
   * (Requirements 3.1, 9.1, 9.3).
   *
   * Preview is the DEFAULT, non-sending action (Preview_First):
   *  - teams_preview_message(message, ...) opens the deep link + copies text with
   *    no keystroke/auto-send (Req 9.1). Issued directly, NO Confirmation_UI.
   *
   * Auto-send is high-risk and OPT-IN:
   *  - Offered only when the persisted `teams_auto_send` setting is true (Req 9.3);
   *    otherwise a disabled hint explains it is off.
   *  - When offered, teams_send_message(...) is routed through `ConfirmModal` and
   *    NO bridge call is issued until the user confirms (Req 3.1). Cancel leaves
   *    the draft/state unchanged.
   *
   * Responses are surfaced honestly: ok=false → error (no success); ok=true with
   * status "dev_skipped" (off-Windows) → notice, not a sent success.
   *
   * All bridge access goes through `callBridge` (no direct `window.pywebview`).
   */
  import { onMount } from "svelte";
  import { callBridge, isPywebviewReady } from "../bridge";
  import ConfirmModal from "./ConfirmModal.svelte";

  type TeamsResultData = { status?: string; message?: string } | null;
  type Feedback =
    | { kind: "none" }
    | { kind: "success"; text: string }
    | { kind: "notice"; text: string }
    | { kind: "error"; text: string };

  let message: string = $state("");
  let targetEmail: string = $state("");
  let targetGroup: string = $state("");
  let mentionsRaw: string = $state("");
  let autoSendEnabled: boolean = $state(false);
  let busy: boolean = $state(false);
  let pendingSend: boolean = $state(false);
  let feedback: Feedback = $state({ kind: "none" });

  function mentions(): string[] {
    return mentionsRaw.split(",").map((m) => m.trim()).filter((m) => m.length > 0);
  }

  function feedbackForSuccess(data: TeamsResultData): Feedback {
    if (data?.status === "dev_skipped") {
      return { kind: "notice", text: data.message ?? "Skipped in a non-Windows environment." };
    }
    if (data?.status === "preview_opened") {
      return { kind: "success", text: "Teams message copied for manual paste." };
    }
    return { kind: "success", text: data?.message ?? "Teams message dispatched." };
  }

  async function loadAutoSend() {
    if (!isPywebviewReady()) return;
    const resp = await callBridge<Record<string, unknown>>("settings_get");
    if (!resp.ok || !resp.data) return;
    const teams = resp.data.teams as Record<string, unknown> | undefined;
    autoSendEnabled = teams?.teams_auto_send === true;
  }

  onMount(loadAutoSend);

  /** Preview is the default action — issued directly, no Confirmation_UI (Req 9.1). */
  async function preview() {
    feedback = { kind: "none" };
    if (!message.trim()) {
      feedback = { kind: "error", text: "Enter a message to preview." };
      return;
    }
    busy = true;
    const resp = await callBridge<TeamsResultData>(
      "teams_preview_message",
      message,
      targetEmail,
      targetGroup,
      mentions(),
    );
    busy = false;
    feedback = resp.ok ? feedbackForSuccess(resp.data) : { kind: "error", text: resp.error.message };
  }

  function requestSend() {
    feedback = { kind: "none" };
    if (!message.trim()) {
      feedback = { kind: "error", text: "Enter a message to send." };
      return;
    }
    pendingSend = true;
  }

  function cancelSend() {
    pendingSend = false;
  }

  /** Confirmed auto-send. Gated behind ConfirmModal.onConfirm (Req 3.1). */
  async function confirmSend() {
    pendingSend = false;
    busy = true;
    const resp = await callBridge<TeamsResultData>(
      "teams_send_message",
      message,
      targetEmail,
      targetGroup,
      mentions(),
    );
    busy = false;
    feedback = resp.ok ? feedbackForSuccess(resp.data) : { kind: "error", text: resp.error.message };
  }
</script>

<div class="ta-root">
  <div class="ta-block">
    <span class="ta-label">Message</span>
    <textarea class="ta-textarea" bind:value={message} disabled={busy} rows="3" placeholder="Teams message…"></textarea>
  </div>
  <div class="ta-row">
    <div class="ta-block">
      <span class="ta-label">Target email (optional)</span>
      <input class="ta-input" bind:value={targetEmail} disabled={busy} placeholder="name@bank.com" />
    </div>
    <div class="ta-block">
      <span class="ta-label">Target group (optional)</span>
      <input class="ta-input" bind:value={targetGroup} disabled={busy} placeholder="Group name" />
    </div>
    <div class="ta-block">
      <span class="ta-label">Mentions (comma-separated)</span>
      <input class="ta-input" bind:value={mentionsRaw} disabled={busy} placeholder="alice, bob" />
    </div>
  </div>

  <div class="ta-block">
    <span class="ta-label">Actions</span>
    <div class="ta-actions">
      <button class="ta-btn" type="button" onclick={preview} disabled={busy}>Preview in Teams</button>
      <button
        class="ta-btn ta-btn-danger"
        type="button"
        onclick={requestSend}
        disabled={busy || !autoSendEnabled}
      >Send (auto)…</button>
    </div>
    {#if autoSendEnabled}
      <p class="ta-hint">Preview is the default and never sends. Auto-send requires explicit confirmation.</p>
    {:else}
      <p class="ta-hint">⚠ Auto-send is off (teams_auto_send=false). Enable it in Settings to allow confirmed auto-send. Preview only.</p>
    {/if}
  </div>

  {#if feedback.kind === "error"}
    <span class="ta-feedback ta-err" role="alert">✗ {feedback.text}</span>
  {:else if feedback.kind === "notice"}
    <span class="ta-feedback ta-notice" role="status">⊘ {feedback.text}</span>
  {:else if feedback.kind === "success"}
    <span class="ta-feedback ta-ok" role="status">✓ {feedback.text}</span>
  {/if}
</div>

{#if pendingSend}
  <ConfirmModal
    title="Send Teams message (auto-send)"
    actionLabel="Send message"
    targetName={targetEmail || targetGroup || "Teams"}
    reversible={false}
    onConfirm={confirmSend}
    onCancel={cancelSend}
  />
{/if}

<style>
  .ta-root { display:flex; flex-direction:column; gap:12px; max-width:640px; }
  .ta-row { display:flex; gap:10px; flex-wrap:wrap; }
  .ta-row .ta-block { flex:1; min-width:160px; }
  .ta-block { display:flex; flex-direction:column; gap:6px; }
  .ta-label { font-size:9px; font-weight:800; color:var(--color-muted); text-transform:uppercase; letter-spacing:0.3px; }
  .ta-textarea, .ta-input { padding:6px 8px; font-size:11px; font-weight:700; border:1px solid var(--color-input-border, #D7DCE2); border-radius:5px; background:#fff; color:var(--color-ink); outline:none; resize:vertical; }
  .ta-textarea:focus, .ta-input:focus { border-color:var(--color-dbs-red); }
  .ta-textarea:disabled, .ta-input:disabled { background:#f3f4f6; color:var(--color-muted); }
  .ta-actions { display:flex; align-items:center; gap:6px; flex-wrap:wrap; }
  .ta-btn { padding:5px 11px; font-size:10px; font-weight:800; border:1px solid #D7DCE2; border-radius:5px; background:#fff; color:var(--color-ink,#111827); cursor:pointer; white-space:nowrap; }
  .ta-btn:hover:not(:disabled) { border-color:var(--color-dbs-red); color:var(--color-dbs-red); }
  .ta-btn:disabled { opacity:0.5; cursor:not-allowed; }
  .ta-btn-danger { border-color:var(--color-dbs-red); color:var(--color-dbs-red); }
  .ta-btn-danger:hover:not(:disabled) { background:var(--color-dbs-red); color:#fff; }
  .ta-hint { margin:0; font-size:9px; font-weight:700; color:var(--color-muted); line-height:1.4; }
  .ta-feedback { font-size:10px; font-weight:800; line-height:1.3; }
  .ta-err { color:var(--color-dbs-red); }
  .ta-ok { color:#166534; }
  .ta-notice { color:var(--color-muted,#6B7280); }
</style>
