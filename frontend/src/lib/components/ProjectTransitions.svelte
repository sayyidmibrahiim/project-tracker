<script lang="ts">
  /**
   * Gated Folder_State transition control (Requirements 3.1, 3.7, 4.1).
   *
   * Renders the folder transitions available for a project's current
   * Folder_State and routes EVERY transition through `ConfirmModal`. No bridge
   * call is issued until the user explicitly confirms (Req 3.1).
   *
   * - On `ok=false` the returned `error.message` is shown and the surrounding
   *   UI state is left unchanged — no fake success (Req 3.7).
   * - When the project's Folder_State locks folder moves (IMPLEMENTED), a
   *   `DisabledHint` naming the lock is rendered instead (Req 3.5).
   *
   * All bridge access goes through `callBridge` (no direct `window.pywebview`).
   */
  import { callBridge } from "../bridge";
  import { isActionDisabled, lockReason } from "../folderLocks";
  import ConfirmModal from "./ConfirmModal.svelte";
  import DisabledHint from "./DisabledHint.svelte";

  let {
    projectPath,
    projectState,
    projectName,
    variant = "menu",
    onApplied,
  }: {
    /** Absolute project folder path (transition target). */
    projectPath: string;
    /** Current Folder_State (e.g. "UAT_PREPARE"). */
    projectState: string;
    /** Human-readable project name shown in the Confirmation_UI. */
    projectName: string;
    /** "menu" = ⋮ dropdown (Dashboard); "inline" = button row (ProjectDetails). */
    variant?: "menu" | "inline";
    /** Called after a successful transition with the new path + state. */
    onApplied?: (next: { projectPath: string; projectState: string }) => void;
  } = $props();

  interface Transition {
    key: string;
    /** Bridge method name — must map to a real JsApi method. */
    method: string;
    /** Menu button label. */
    label: string;
    /** Confirmation title. */
    title: string;
    /** Confirmation action label. */
    actionLabel: string;
    /** Explicit reversibility for the Confirmation_UI (Req 3.2/3.3). */
    reversible: boolean | "unknown";
  }

  /** Transition catalog keyed by source Folder_State (mirrors PRD §9.5 flow). */
  const TRANSITIONS: Record<string, Transition[]> = {
    UAT_PREPARE: [
      { key: "prod_ready", method: "folder_move_to_prod_ready", label: "Move to Prod Ready", title: "Move to Prod Ready", actionLabel: "Move to Prod Ready", reversible: true },
      { key: "postpone", method: "folder_postpone", label: "Postpone", title: "Postpone project", actionLabel: "Postpone", reversible: true },
      { key: "cancel", method: "folder_cancel", label: "Cancel", title: "Cancel project", actionLabel: "Cancel project", reversible: "unknown" },
    ],
    PROD_READY: [
      { key: "implemented", method: "folder_move_to_implemented", label: "Move to Implemented", title: "Move to Implemented", actionLabel: "Move to Implemented", reversible: false },
      { key: "postpone", method: "folder_postpone", label: "Postpone", title: "Postpone project", actionLabel: "Postpone", reversible: true },
      { key: "cancel", method: "folder_cancel", label: "Cancel", title: "Cancel project", actionLabel: "Cancel project", reversible: "unknown" },
    ],
    POSTPONED: [
      { key: "reopen", method: "folder_reopen", label: "Reopen", title: "Reopen project", actionLabel: "Reopen", reversible: true },
    ],
    CANCELED: [
      { key: "reopen", method: "folder_reopen", label: "Reopen", title: "Reopen project", actionLabel: "Reopen", reversible: true },
    ],
  };

  // ── State ──
  let open: boolean = $state(false);
  let busy: boolean = $state(false);
  let errorMessage: string = $state("");
  let successMessage: string = $state("");
  // The transition awaiting the first confirmation, or null when no modal.
  let pending: Transition | null = $state(null);

  let available: Transition[] = $derived(TRANSITIONS[projectState] ?? []);
  // Folder moves are locked while a project is IMPLEMENTED (PRD §9.5).
  let moveLocked: boolean = $derived(isActionDisabled(projectState, "move_folder"));
  let lockMessage: string = $derived(lockReason(projectState, "move_folder") ?? "");

  function toggleMenu() {
    open = !open;
  }

  /** Begin a transition: arm the Confirmation_UI; issue no bridge call yet. */
  function requestTransition(t: Transition) {
    errorMessage = "";
    successMessage = "";
    pending = t;
    open = false;
  }

  function cancelConfirm() {
    // Cancel/dismiss leaves prior UI state unchanged (Req 3.4).
    pending = null;
  }

  async function runTransition(t: Transition) {
    busy = true;
    errorMessage = "";
    successMessage = "";

    const response = await callBridge<{ project_path: string; project_state: string }>(t.method, projectPath);

    busy = false;

    if (!response.ok) {
      // Surface the error; leave UI unchanged (Req 3.7).
      errorMessage = response.error.message;
      return;
    }

    successMessage = `${t.label} succeeded.`;
    const next = {
      projectPath: response.data?.project_path ?? projectPath,
      projectState: response.data?.project_state ?? projectState,
    };
    onApplied?.(next);
  }

  async function confirmPending() {
    const t = pending;
    pending = null;
    if (t) await runTransition(t);
  }
</script>

<span class="pt-root" class:pt-inline={variant === "inline"}>
  {#if moveLocked}
    <DisabledHint label="Transitions" message={lockMessage} variant="lock" />
  {:else if available.length === 0}
    <DisabledHint label="Transitions" message={`No folder transitions available from ${projectState}.`} variant="lock" />
  {:else if variant === "menu"}
    <button
      class="cell-action"
      type="button"
      aria-haspopup="menu"
      aria-expanded={open}
      title="Folder transitions"
      onclick={toggleMenu}
      disabled={busy}
    >⋮</button>
    {#if open}
      <div class="pt-menu" role="menu">
        {#each available as t}
          <button class="pt-menu-item" type="button" role="menuitem" onclick={() => requestTransition(t)} disabled={busy}>
            {t.label}
          </button>
        {/each}
      </div>
    {/if}
  {:else}
    <div class="pt-inline-actions">
      {#each available as t}
        <button class="pt-action-btn" type="button" onclick={() => requestTransition(t)} disabled={busy}>
          {t.label}
        </button>
      {/each}
    </div>
  {/if}

  {#if errorMessage}
    <span class="pt-feedback pt-err" role="alert">✗ {errorMessage}</span>
  {:else if successMessage}
    <span class="pt-feedback pt-ok" role="status">✓ {successMessage}</span>
  {/if}
</span>

{#if pending}
  <ConfirmModal
    title={pending.title}
    actionLabel={pending.actionLabel}
    targetName={projectName}
    reversible={pending.reversible}
    onConfirm={confirmPending}
    onCancel={cancelConfirm}
  />
{/if}

<style>
  .pt-root {
    position: relative;
    display: inline-flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
  .pt-inline {
    width: 100%;
  }
  .pt-menu {
    position: absolute;
    top: 100%;
    right: 0;
    z-index: 40;
    margin-top: 4px;
    min-width: 168px;
    background: #fff;
    border: 1px solid #E5E7EB;
    border-radius: 6px;
    box-shadow: var(--shadow-panel, 0 8px 24px rgba(0, 0, 0, 0.18));
    padding: 4px;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .pt-menu-item {
    text-align: left;
    padding: 7px 10px;
    border: 0;
    border-radius: 5px;
    background: transparent;
    color: var(--color-ink, #111827);
    font-size: 11px;
    font-weight: 800;
    cursor: pointer;
    white-space: nowrap;
  }
  .pt-menu-item:hover:not(:disabled) {
    background: var(--color-soft-pink-surface, #FDECEC);
    color: var(--color-dbs-red);
  }
  .pt-menu-item:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .pt-inline-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .pt-action-btn {
    padding: 5px 11px;
    font-size: 10px;
    font-weight: 800;
    border: 1px solid #D7DCE2;
    border-radius: 5px;
    background: #fff;
    color: var(--color-ink, #111827);
    cursor: pointer;
    white-space: nowrap;
  }
  .pt-action-btn:hover:not(:disabled) {
    border-color: var(--color-dbs-red);
    color: var(--color-dbs-red);
  }
  .pt-action-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .pt-feedback {
    font-size: 10px;
    font-weight: 800;
    line-height: 1.3;
  }
  .pt-err {
    color: var(--color-dbs-red);
  }
  .pt-ok {
    color: #166534;
  }
</style>
