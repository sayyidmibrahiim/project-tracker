<script lang="ts">
  /**
   * Confirmation_UI for high-risk actions (Requirement 3.1–3.4).
   *
   * - States the action, the target name/path, and an explicit binary
   *   reversible/irreversible statement.
   * - `reversible="unknown"` is presented as irreversible (Req 3.3).
   * - Issues NO bridge call itself: it only invokes `onConfirm` / `onCancel`
   *   callbacks. The calling component is responsible for the bridge call,
   *   and only after `onConfirm` fires (Req 3.1).
   * - Cancel / dismiss (backdrop click or Escape) invokes `onCancel` and leaves
   *   the prior UI state unchanged (Req 3.4).
   */
  let {
    title,
    actionLabel,
    targetName,
    reversible,
    onConfirm,
    onCancel,
  }: {
    title: string;
    actionLabel: string;
    targetName: string;
    reversible: boolean | "unknown";
    onConfirm: () => void;
    onCancel: () => void;
  } = $props();

  // "unknown" reversibility is treated as irreversible (Req 3.3).
  const isReversible: boolean = $derived(reversible === true);

  function handleConfirm() {
    onConfirm();
  }

  function handleCancel() {
    onCancel();
  }

  function handleBackdropKeydown(event: KeyboardEvent) {
    if (event.key === "Escape") {
      handleCancel();
    }
  }

  function handleOverlayKeydown(event: KeyboardEvent) {
    if (event.key === "Escape") {
      handleCancel();
    }
  }
</script>

<svelte:window on:keydown={handleBackdropKeydown} />

<div
  class="confirm-overlay"
  role="presentation"
  onclick={handleCancel}
  onkeydown={handleOverlayKeydown}
>
  <div
    class="confirm-dialog"
    role="alertdialog"
    aria-modal="true"
    aria-labelledby="confirm-title"
    aria-describedby="confirm-body"
    tabindex="-1"
    onclick={(e) => e.stopPropagation()}
    onkeydown={(e) => e.stopPropagation()}
  >
    <div class="confirm-head">
      <span class="confirm-accent"></span>
      <h3 id="confirm-title">{title}</h3>
    </div>

    <div id="confirm-body" class="confirm-body">
      <p class="confirm-action">
        <span class="confirm-action-label">{actionLabel}</span>
        <span class="confirm-target">{targetName}</span>
      </p>

      <p
        class="confirm-reversibility"
        class:is-irreversible={!isReversible}
        class:is-reversible={isReversible}
      >
        {#if isReversible}
          <span class="confirm-rev-icon" aria-hidden="true">↺</span>
          This action is reversible.
        {:else}
          <span class="confirm-rev-icon" aria-hidden="true">⚠</span>
          This action is irreversible.
        {/if}
      </p>
    </div>

    <div class="confirm-actions">
      <button class="confirm-btn confirm-btn-cancel" type="button" onclick={handleCancel}>
        Cancel
      </button>
      <button
        class="confirm-btn confirm-btn-proceed"
        class:irreversible={!isReversible}
        type="button"
        onclick={handleConfirm}
      >
        {actionLabel}
      </button>
    </div>
  </div>
</div>

<style>
  .confirm-overlay {
    position: fixed;
    inset: 0;
    z-index: 100;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(17, 24, 39, 0.45);
    padding: 20px;
  }

  .confirm-dialog {
    background: #fff;
    border: 1px solid #E5E7EB;
    border-left: 3px solid var(--color-dbs-red);
    border-radius: 8px;
    box-shadow: var(--shadow-panel);
    width: 100%;
    max-width: 420px;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .confirm-head {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .confirm-head h3 {
    margin: 0;
    color: var(--color-ink);
    font-size: 13px;
    font-weight: 900;
    letter-spacing: 0.2px;
  }
  .confirm-accent {
    width: 3px;
    min-width: 3px;
    height: 16px;
    border-radius: 2px;
    background: var(--color-dbs-red);
  }

  .confirm-body {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .confirm-action {
    margin: 0;
    font-size: 12px;
    font-weight: 750;
    color: var(--color-ink);
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  .confirm-action-label {
    font-weight: 900;
  }
  .confirm-target {
    font-weight: 800;
    color: var(--color-muted);
    word-break: break-all;
  }

  .confirm-reversibility {
    margin: 0;
    font-size: 11px;
    font-weight: 900;
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 10px;
    border-radius: 6px;
  }
  .confirm-reversibility.is-irreversible {
    color: var(--color-dbs-red);
    background: var(--color-soft-pink, #FDECEC);
    border: 1px solid var(--color-soft-pink-border, #F5C2C2);
  }
  .confirm-reversibility.is-reversible {
    color: #166534;
    background: #ECFDF3;
    border: 1px solid #BBF7D0;
  }
  .confirm-rev-icon {
    font-size: 12px;
  }

  .confirm-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
  }
  .confirm-btn {
    height: 32px;
    border-radius: 5px;
    font-weight: 900;
    font-size: 11px;
    padding: 0 16px;
    cursor: pointer;
    white-space: nowrap;
    transition: background 0.15s ease, transform 0.15s ease;
  }
  .confirm-btn-cancel {
    background: #fff;
    border: 1px solid var(--color-input-border);
    color: var(--color-ink);
  }
  .confirm-btn-cancel:hover {
    background: #F3F4F6;
  }
  .confirm-btn-proceed {
    background: var(--color-ink);
    border: 1px solid var(--color-ink);
    color: #fff;
  }
  .confirm-btn-proceed:hover {
    transform: translateY(-1px);
  }
  .confirm-btn-proceed.irreversible {
    background: var(--color-dbs-red);
    border: 1px solid var(--color-dbs-red-hover);
  }
  .confirm-btn-proceed.irreversible:hover {
    background: var(--color-dbs-red-hover);
  }
</style>
