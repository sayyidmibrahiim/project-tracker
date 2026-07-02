<script lang="ts">
  /**
   * Gated project rename / delete + drone delete control
   * (Requirements 3.1, 3.5, 5.3, 5.5).
   *
   * Routes EVERY high-risk action (project rename, project delete, drone
   * delete) through `ConfirmModal`. No bridge call is issued until the user
   * explicitly confirms (Req 3.1):
   *
   *  - Project rename → reversible Confirmation_UI (a name can be changed back).
   *  - Project delete  → irreversible-styled Confirmation_UI (`reversible={false}`).
   *  - Subproject delete → irreversible-styled Confirmation_UI.
   *
   * While the Folder_State locks an action (PROD_READY / IMPLEMENTED), a
   * `DisabledHint` naming the state is rendered instead of the active control
   * (Req 3.5, 5.3, 5.5). The Python backend remains the authoritative guard.
   *
   * On `ok=false` the returned `error.message` is shown and the surrounding UI
   * state is left unchanged — no fake success (Req 3.7). Cancel / dismiss leaves
   * the prior UI state unchanged (Req 3.4).
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
    drones = [],
    onRenamed,
    onDeleted,
    onDronesChanged,
  }: {
    /** Absolute project folder path (action target). */
    projectPath: string;
    /** Current Folder_State (e.g. "UAT_PREPARE"). */
    projectState: string;
    /** Human-readable project name shown in the Confirmation_UI. */
    projectName: string;
    /** Subproject names (delete targets). */
    drones?: string[];
    /** Called after a successful rename with the renamed project's new path. */
    onRenamed?: (next: { projectPath: string }) => void;
    /** Called after a successful project delete. */
    onDeleted?: () => void;
    /** Called after a successful drone delete. */
    onDronesChanged?: () => void;
  } = $props();

  /** A high-risk action awaiting explicit confirmation (gates the bridge call). */
  type PendingAction =
    | { kind: "rename"; newName: string }
    | { kind: "delete_project" }
    | { kind: "drone_delete"; name: string };

  // ── State ──
  let renameDraft: string = $state("");
  let busy: boolean = $state(false);
  let errorMessage: string = $state("");
  let successMessage: string = $state("");
  // The action awaiting confirmation, or null when no modal is open.
  let pending: PendingAction | null = $state(null);

  // ── Folder_State locks (PRD §9.5; backend is authoritative) ──
  let renameLocked: boolean = $derived(isActionDisabled(projectState, "rename_project"));
  let renameLockMsg: string = $derived(lockReason(projectState, "rename_project") ?? "");
  let deleteLocked: boolean = $derived(isActionDisabled(projectState, "delete_project"));
  let deleteLockMsg: string = $derived(lockReason(projectState, "delete_project") ?? "");
  let subDeleteLocked: boolean = $derived(isActionDisabled(projectState, "drone_delete"));
  let subDeleteLockMsg: string = $derived(lockReason(projectState, "drone_delete") ?? "");

  // ── Confirmation_UI copy derived from the pending action (Req 3.2/3.3) ──
  let confirmTitle: string = $derived.by(() => {
    if (pending?.kind === "rename") return "Rename project";
    if (pending?.kind === "delete_project") return "Delete project";
    if (pending?.kind === "drone_delete") return "Delete drone";
    return "";
  });
  let confirmActionLabel: string = $derived.by(() => {
    if (pending?.kind === "rename") return "Rename";
    if (pending?.kind === "delete_project") return "Delete project";
    if (pending?.kind === "drone_delete") return "Delete drone";
    return "";
  });
  let confirmTarget: string = $derived.by(() => {
    if (pending?.kind === "drone_delete") return pending.name;
    if (pending?.kind === "rename") return `${projectName} → ${pending.newName}`;
    return projectName;
  });
  // Rename is reversible (a name can be changed back); deletes are irreversible.
  let confirmReversible: boolean = $derived.by(() => pending?.kind === "rename");

  function clearFeedback() {
    errorMessage = "";
    successMessage = "";
  }

  /** Arm the rename Confirmation_UI; issue no bridge call yet (Req 3.1). */
  function requestRename() {
    clearFeedback();
    const trimmed = renameDraft.trim();
    if (!trimmed) {
      errorMessage = "Enter a new project name before renaming.";
      return;
    }
    if (trimmed === projectName) {
      errorMessage = "The new name matches the current name.";
      return;
    }
    pending = { kind: "rename", newName: trimmed };
  }

  /** Arm the project-delete Confirmation_UI; issue no bridge call yet (Req 3.1). */
  function requestDeleteProject() {
    clearFeedback();
    pending = { kind: "delete_project" };
  }

  /** Arm the drone-delete Confirmation_UI; issue no bridge call yet (Req 3.1). */
  function requestSubprojectDelete(name: string) {
    clearFeedback();
    pending = { kind: "drone_delete", name };
  }

  /** Cancel / dismiss leaves the prior UI state unchanged (Req 3.4). */
  function cancelConfirm() {
    pending = null;
  }

  /** Run the confirmed action's bridge call. Gated behind ConfirmModal.onConfirm. */
  async function runAction(action: PendingAction) {
    busy = true;
    clearFeedback();

    if (action.kind === "rename") {
      const response = await callBridge<{ project_path?: string }>(
        "project_rename",
        projectPath,
        action.newName,
      );
      busy = false;
      if (!response.ok) {
        // Surface the error; leave UI unchanged — no fake success (Req 3.7).
        errorMessage = response.error.message;
        return;
      }
      successMessage = `Renamed to ${action.newName}.`;
      renameDraft = "";
      const nextPath =
        typeof response.data?.project_path === "string"
          ? response.data.project_path
          : projectPath;
      onRenamed?.({ projectPath: nextPath });
      return;
    }

    if (action.kind === "delete_project") {
      const response = await callBridge("project_delete", projectPath);
      busy = false;
      if (!response.ok) {
        errorMessage = response.error.message;
        return;
      }
      successMessage = "Project deleted to the Recycle Bin.";
      onDeleted?.();
      return;
    }

    // action.kind === "drone_delete"
    const response = await callBridge("drone_delete", projectPath, action.name);
    busy = false;
    if (!response.ok) {
      errorMessage = response.error.message;
      return;
    }
    successMessage = `Subproject "${action.name}" deleted to the Recycle Bin.`;
    onDronesChanged?.();
  }

  async function confirmPending() {
    const action = pending;
    pending = null;
    if (action) await runAction(action);
  }
</script>

<div class="pa-root">
  <!-- ── Rename ── -->
  <div class="pa-block">
    <span class="pa-block-label">Rename Project</span>
    {#if renameLocked}
      <DisabledHint label="Rename" message={renameLockMsg} variant="lock" />
    {:else}
      <div class="pa-rename-row">
        <input
          class="pa-input"
          placeholder="New project name…"
          bind:value={renameDraft}
          disabled={busy}
        />
        <button
          class="pa-btn"
          type="button"
          onclick={requestRename}
          disabled={busy || !renameDraft.trim()}
        >Rename</button>
      </div>
    {/if}
  </div>

  <!-- ── Delete project ── -->
  <div class="pa-block">
    <span class="pa-block-label">Delete Project</span>
    {#if deleteLocked}
      <DisabledHint label="Delete project" message={deleteLockMsg} variant="lock" />
    {:else}
      <button
        class="pa-btn pa-btn-danger"
        type="button"
        onclick={requestDeleteProject}
        disabled={busy}
      >Delete project</button>
    {/if}
  </div>

  <!-- ── Subproject delete ── -->
  <div class="pa-block">
    <span class="pa-block-label">Subprojects</span>
    {#if drones.length === 0}
      <p class="pa-muted">No drones.</p>
    {:else}
      <ul class="pa-sub-list">
        {#each drones as sp}
          <li class="pa-sub-row">
            <span class="pa-sub-name">{sp}</span>
            {#if subDeleteLocked}
              <DisabledHint label="Delete" message={subDeleteLockMsg} variant="lock" />
            {:else}
              <button
                class="pa-btn pa-btn-danger pa-btn-sm"
                type="button"
                onclick={() => requestSubprojectDelete(sp)}
                disabled={busy}
              >Delete</button>
            {/if}
          </li>
        {/each}
      </ul>
    {/if}
  </div>

  {#if errorMessage}
    <span class="pa-feedback pa-err" role="alert">✗ {errorMessage}</span>
  {:else if successMessage}
    <span class="pa-feedback pa-ok" role="status">✓ {successMessage}</span>
  {/if}
</div>

{#if pending}
  <ConfirmModal
    title={confirmTitle}
    actionLabel={confirmActionLabel}
    targetName={confirmTarget}
    reversible={confirmReversible}
    onConfirm={confirmPending}
    onCancel={cancelConfirm}
  />
{/if}

<style>
  .pa-root {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .pa-block {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .pa-block-label {
    font-size: 9px;
    font-weight: 800;
    color: var(--color-muted);
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }
  .pa-rename-row {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
  }
  .pa-input {
    flex: 1;
    min-width: 140px;
    padding: 5px 8px;
    font-size: 11px;
    font-weight: 700;
    border: 1px solid var(--color-input-border, #D7DCE2);
    border-radius: 5px;
    background: #fff;
    color: var(--color-ink);
    outline: none;
  }
  .pa-input:focus {
    border-color: var(--color-dbs-red);
  }
  .pa-input:disabled {
    background: #f3f4f6;
    color: var(--color-muted);
  }
  .pa-btn {
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
  .pa-btn:hover:not(:disabled) {
    border-color: var(--color-dbs-red, #DA1E28);
    color: var(--color-dbs-red, #DA1E28);
  }
  .pa-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .pa-btn-danger {
    border-color: var(--color-dbs-red, #DA1E28);
    color: var(--color-dbs-red, #DA1E28);
  }
  .pa-btn-danger:hover:not(:disabled) {
    background: var(--color-dbs-red, #DA1E28);
    color: #fff;
  }
  .pa-btn-sm {
    padding: 3px 9px;
    font-size: 9px;
  }
  .pa-sub-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin: 0;
    padding: 0;
    list-style: none;
  }
  .pa-sub-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    flex-wrap: wrap;
  }
  .pa-sub-name {
    font-size: 11px;
    font-weight: 800;
    color: var(--color-ink);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;
    min-width: 0;
  }
  .pa-muted {
    margin: 0;
    font-size: 11px;
    font-weight: 700;
    color: var(--color-muted);
  }
  .pa-feedback {
    font-size: 10px;
    font-weight: 800;
    line-height: 1.3;
  }
  .pa-err {
    color: var(--color-dbs-red, #DA1E28);
  }
  .pa-ok {
    color: #166534;
  }
</style>
