<script lang="ts">
  /**
   * Gated Outlook email control for the Project Details area
   * (Requirements 3.1, 8.1, 8.2, 8.3, 8.9).
   *
   * Draft is the DEFAULT, non-transmitting action (Draft_First):
   *  - outlook_draft_email(category_code, project_path) is issued directly with
   *    NO Confirmation_UI — it only creates a draft and never sends (Req 8.1).
   *
   * Send is a high-risk, transmitting action:
   *  - outlook_send_email(category_code, project_path) is routed through
   *    `ConfirmModal` and NO bridge call is issued until the user explicitly
   *    confirms (Req 8.2). Sending an email cannot be undone, so the
   *    Confirmation_UI is presented as irreversible.
   *  - Cancel / dismiss issues no send and leaves the prior draft and UI state
   *    unchanged — the draft is retained (Req 8.3, 3.4).
   *
   * A Template_Category selector (ACK_UAT / ACK_SOP / APRVL_CR / APRVL_SOP)
   * chooses the template used for both draft and send (Req 8.4).
   *
   * Responses are surfaced honestly (Req 8.9):
   *  - ok=false → show `error.message`, NO success indication.
   *  - ok=true with status "drafted"/"sent" → success.
   *  - ok=true with status "skipped" → shown as a skipped notice with the
   *    reason, NOT as a sent/drafted success.
   *  - ok=true with status "dev_skipped" (off-Windows) → shown as a dev-skipped
   *    notice with the message, NOT as a sent/drafted success.
   *
   * All bridge access goes through `callBridge` (no direct `window.pywebview`).
   */
  import { callBridge } from "../bridge";
  import ConfirmModal from "./ConfirmModal.svelte";

  let {
    projectPath,
    projectName,
  }: {
    /** Absolute project folder path (bridge calls take project_path). */
    projectPath: string;
    /** Human-readable project name shown in the Confirmation_UI. */
    projectName: string;
  } = $props();

  /** Template_Category values supported by the Outlook templates (Req 8.4). */
  const TEMPLATE_CATEGORIES = ["ACK_UAT", "ACK_SOP", "APRVL_CR", "APRVL_SOP"] as const;

  /** Shape of the `data` payload returned by the outlook_* bridge methods. */
  type OutlookResultData = {
    status?: string;
    subject?: string;
    reason?: string;
    message?: string;
  } | null;

  /** Feedback kinds: success (drafted/sent) vs an honest non-success notice. */
  type Feedback =
    | { kind: "none" }
    | { kind: "success"; text: string }
    | { kind: "notice"; text: string }
    | { kind: "error"; text: string };

  // ── State ──
  let category: string = $state(TEMPLATE_CATEGORIES[0]);
  let busy: boolean = $state(false);
  let feedback: Feedback = $state({ kind: "none" });
  // When set, a send is awaiting explicit confirmation (gates the bridge call).
  let pendingSend: boolean = $state(false);

  function clearFeedback() {
    feedback = { kind: "none" };
  }

  /**
   * Map an ok=true Outlook response to honest feedback. "drafted"/"sent" are
   * real successes; "skipped" and "dev_skipped" are surfaced as notices so a
   * skipped or dev-skipped response is never shown as a sent success (Req 8.9).
   */
  function feedbackForSuccess(data: OutlookResultData, draftedLabel: string): Feedback {
    const status = data?.status;
    if (status === "skipped") {
      const reason = data?.reason ? `: ${data.reason}` : ".";
      return { kind: "notice", text: `Skipped${reason}` };
    }
    if (status === "dev_skipped") {
      const message = data?.message ?? "Action skipped in a non-Windows environment.";
      return { kind: "notice", text: message };
    }
    // "drafted" / "sent" (or any other explicit ok status) → success.
    return { kind: "success", text: draftedLabel };
  }

  /** Draft is the default action — issued directly, no Confirmation_UI (Req 8.1). */
  async function draftEmail() {
    clearFeedback();
    busy = true;
    const response = await callBridge<OutlookResultData>(
      "outlook_draft_email",
      category,
      projectPath,
    );
    busy = false;
    if (!response.ok) {
      // Surface the error; no success indication (Req 8.9).
      feedback = { kind: "error", text: response.error.message };
      return;
    }
    feedback = feedbackForSuccess(response.data, `Draft created for ${category}.`);
  }

  /** Arm the send Confirmation_UI; issue NO bridge call yet (Req 8.2). */
  function requestSend() {
    clearFeedback();
    pendingSend = true;
  }

  /** Cancel / dismiss: no send, the draft is retained, state unchanged (Req 8.3). */
  function cancelSend() {
    pendingSend = false;
  }

  /** Run the confirmed send. Gated behind ConfirmModal.onConfirm (Req 8.2). */
  async function confirmSend() {
    pendingSend = false;
    busy = true;
    const response = await callBridge<OutlookResultData>(
      "outlook_send_email",
      category,
      projectPath,
    );
    busy = false;
    if (!response.ok) {
      // Surface the error; no success indication (Req 8.9).
      feedback = { kind: "error", text: response.error.message };
      return;
    }
    feedback = feedbackForSuccess(response.data, `Email sent for ${category}.`);
  }
</script>

<div class="oa-root">
  <!-- ── Template category selector (Req 8.4) ── -->
  <div class="oa-block">
    <span class="oa-block-label">Template Category</span>
    <select class="oa-select" bind:value={category} disabled={busy}>
      {#each TEMPLATE_CATEGORIES as cat}
        <option value={cat}>{cat}</option>
      {/each}
    </select>
  </div>

  <!-- ── Actions: draft (default) + send (gated) ── -->
  <div class="oa-block">
    <span class="oa-block-label">Actions</span>
    <div class="oa-actions">
      <button
        class="oa-btn"
        type="button"
        onclick={draftEmail}
        disabled={busy}
      >Draft email</button>
      <button
        class="oa-btn oa-btn-danger"
        type="button"
        onclick={requestSend}
        disabled={busy}
      >Send email…</button>
    </div>
    <p class="oa-hint">
      Draft is the default and never transmits. Sending requires explicit confirmation.
    </p>
  </div>

  {#if feedback.kind === "error"}
    <span class="oa-feedback oa-err" role="alert">✗ {feedback.text}</span>
  {:else if feedback.kind === "notice"}
    <span class="oa-feedback oa-notice" role="status">⊘ {feedback.text}</span>
  {:else if feedback.kind === "success"}
    <span class="oa-feedback oa-ok" role="status">✓ {feedback.text}</span>
  {/if}
</div>

{#if pendingSend}
  <ConfirmModal
    title="Send Outlook email"
    actionLabel="Send email"
    targetName={`${category} — ${projectName}`}
    reversible={false}
    onConfirm={confirmSend}
    onCancel={cancelSend}
  />
{/if}

<style>
  .oa-root {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .oa-block {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .oa-block-label {
    font-size: 9px;
    font-weight: 800;
    color: var(--color-muted);
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }
  .oa-select {
    align-self: flex-start;
    min-width: 160px;
    padding: 5px 8px;
    font-size: 11px;
    font-weight: 800;
    border: 1px solid var(--color-input-border, #D7DCE2);
    border-radius: 5px;
    background: #fff;
    color: var(--color-ink);
    outline: none;
  }
  .oa-select:focus {
    border-color: var(--color-dbs-red);
  }
  .oa-select:disabled {
    background: #f3f4f6;
    color: var(--color-muted);
  }
  .oa-actions {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
  }
  .oa-btn {
    padding: 5px 11px;
    font-size: 10px;
    font-weight: 800;
    border: 1px solid #D7DCE2;
    border-radius: 5px;
    background: #fff;
    color: var(--color-ink, #111827);
    cursor: pointer;
    white-space: nowrap;
    flex: 0 0 auto;
  }
  .oa-btn:hover:not(:disabled) {
    border-color: var(--color-dbs-red);
    color: var(--color-dbs-red);
  }
  .oa-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .oa-btn-danger {
    border-color: var(--color-dbs-red);
    color: var(--color-dbs-red);
  }
  .oa-btn-danger:hover:not(:disabled) {
    background: var(--color-dbs-red);
    color: #fff;
  }
  .oa-hint {
    margin: 0;
    font-size: 9px;
    font-weight: 700;
    color: var(--color-muted);
    line-height: 1.4;
  }
  .oa-feedback {
    font-size: 10px;
    font-weight: 800;
    line-height: 1.3;
  }
  .oa-err {
    color: var(--color-dbs-red);
  }
  .oa-ok {
    color: #166534;
  }
  .oa-notice {
    color: var(--color-muted, #6B7280);
  }
</style>
