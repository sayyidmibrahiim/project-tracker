<script lang="ts">
  /**
   * Gated file management control for the Project Details Files area
   * (Requirements 3.1, 3.5, 6.10).
   *
   * Surfaces the wired file bridge methods (task 9.2) honestly and safely:
   *
   *  - file_create(path, filename) / file_create_from_template(path, template_name)
   *    are non-destructive form actions: they issue the bridge call directly
   *    (no Confirmation_UI) but still surface `error.message` on `ok=false` and
   *    refresh the listing on success.
   *  - file_rename(filepath, new_name) routes through `ConfirmModal` as a
   *    reversible action (a file can be renamed back) — no bridge call until the
   *    user explicitly confirms (Req 3.1).
   *  - file_delete(filepath) routes through `ConfirmModal` as an irreversible-
   *    styled action — no bridge call until confirm (Req 3.1).
   *  - file_open(path) just calls the bridge (dev-skipped off-Windows); it is a
   *    read-only open and needs no confirmation.
   *
   * While the Folder_State locks create / rename / delete (PROD_READY /
   * IMPLEMENTED), a `DisabledHint` naming the state is rendered instead of the
   * active control (Req 3.5, 6.10). The Python backend remains the authoritative
   * guard.
   *
   * On `ok=false` the returned `error.message` is shown and the surrounding UI
   * state is left unchanged — no fake success (Req 3.7). Cancel / dismiss leaves
   * the prior UI state unchanged (Req 3.4).
   *
   * All bridge access goes through `callBridge` (no direct `window.pywebview`).
   */
  import { callBridge } from "../bridge";
  import { isActionDisabled, lockReason } from "../folderLocks";
  import type { FileRow } from "../types";
  import ConfirmModal from "./ConfirmModal.svelte";
  import DisabledHint from "./DisabledHint.svelte";

  let {
    projectPath,
    projectState,
    files = [],
    onFilesChanged,
  }: {
    /** Absolute target folder path (create target). */
    projectPath: string;
    /** Current Folder_State (e.g. "UAT_PREPARE"). */
    projectState: string;
    /** Files listed in the target folder (rename/delete/open targets). */
    files?: FileRow[];
    /** Called after a successful create/rename/delete so the list can refresh. */
    onFilesChanged?: () => void;
  } = $props();

  /** A high-risk file action awaiting explicit confirmation (gates the bridge call). */
  type PendingAction =
    | { kind: "rename"; filepath: string; currentName: string; newName: string }
    | { kind: "delete"; filepath: string; name: string };

  // ── State ──
  let newFilename: string = $state("");
  let newTemplateName: string = $state("");
  // Per-file rename draft (keyed by file path); -1/"" sentinels via empty path.
  let renameEditPath: string = $state("");
  let renameDraft: string = $state("");
  let busy: boolean = $state(false);
  let errorMessage: string = $state("");
  let successMessage: string = $state("");
  // The action awaiting confirmation, or null when no modal is open.
  let pending: PendingAction | null = $state(null);

  // ── Folder_State locks (PRD §9.5; backend is authoritative) ──
  let createLocked: boolean = $derived(isActionDisabled(projectState, "file_create"));
  let createLockMsg: string = $derived(lockReason(projectState, "file_create") ?? "");
  let renameLocked: boolean = $derived(isActionDisabled(projectState, "file_rename"));
  let renameLockMsg: string = $derived(lockReason(projectState, "file_rename") ?? "");
  let deleteLocked: boolean = $derived(isActionDisabled(projectState, "file_delete"));
  let deleteLockMsg: string = $derived(lockReason(projectState, "file_delete") ?? "");

  // ── Confirmation_UI copy derived from the pending action (Req 3.2/3.3) ──
  let confirmTitle: string = $derived.by(() => {
    if (pending?.kind === "rename") return "Rename file";
    if (pending?.kind === "delete") return "Delete file";
    return "";
  });
  let confirmActionLabel: string = $derived.by(() => {
    if (pending?.kind === "rename") return "Rename";
    if (pending?.kind === "delete") return "Delete file";
    return "";
  });
  let confirmTarget: string = $derived.by(() => {
    if (pending?.kind === "rename") return `${pending.currentName} → ${pending.newName}`;
    if (pending?.kind === "delete") return pending.name;
    return "";
  });
  // Rename is reversible (a file can be renamed back); delete is irreversible.
  let confirmReversible: boolean = $derived.by(() => pending?.kind === "rename");

  function clearFeedback() {
    errorMessage = "";
    successMessage = "";
  }

  // ── Non-destructive form actions (no Confirmation_UI; still surface errors) ──

  /** Create a manual file. Form action — issues the bridge call directly. */
  async function createFile() {
    clearFeedback();
    const filename = newFilename.trim();
    if (!filename) {
      errorMessage = "Enter a file name before creating.";
      return;
    }
    if (RESERVED_FILES.has(filename.toLowerCase())) {
      errorMessage = "notes.md and project_data.json are reserved system files and cannot be created here.";
      return;
    }
    busy = true;
    const response = await callBridge("file_create", projectPath, filename);
    busy = false;
    if (!response.ok) {
      errorMessage = response.error.message;
      return;
    }
    successMessage = `Created "${filename}".`;
    newFilename = "";
    onFilesChanged?.();
  }

  /** Create a file from a template. Form action — issues the bridge call directly. */
  async function createFromTemplate() {
    clearFeedback();
    const templateName = newTemplateName.trim();
    if (!templateName) {
      errorMessage = "Enter a template name before creating.";
      return;
    }
    if (RESERVED_FILES.has(templateName.toLowerCase())) {
      errorMessage = "notes.md and project_data.json are reserved system files and cannot be created here.";
      return;
    }
    busy = true;
    const response = await callBridge(
      "file_create_from_template",
      projectPath,
      templateName,
    );
    busy = false;
    if (!response.ok) {
      errorMessage = response.error.message;
      return;
    }
    successMessage = `Created from template "${templateName}".`;
    newTemplateName = "";
    onFilesChanged?.();
  }

  /** Open a file externally (dev-skipped off-Windows). Read-only — no confirm. */
  async function openFile(filepath: string) {
    clearFeedback();
    busy = true;
    const response = await callBridge("file_open", filepath);
    busy = false;
    if (!response.ok) {
      errorMessage = response.error.message;
    }
  }

  // ── Rename draft management ──

  function startRename(file: FileRow) {
    clearFeedback();
    renameEditPath = file.path;
    renameDraft = file.name;
  }

  function cancelRename() {
    renameEditPath = "";
    renameDraft = "";
  }

  // ── High-risk actions: armed here, bridge call only after confirm (Req 3.1) ──

  /** Arm the rename Confirmation_UI; issue no bridge call yet. */
  function requestRename(file: FileRow) {
    clearFeedback();
    const trimmed = renameDraft.trim();
    if (!trimmed) {
      errorMessage = "Enter a new file name before renaming.";
      return;
    }
    if (trimmed === file.name) {
      errorMessage = "The new name matches the current name.";
      return;
    }
    if (RESERVED_FILES.has(trimmed.toLowerCase())) {
      errorMessage = "Cannot rename to a reserved system file name.";
      return;
    }
    pending = {
      kind: "rename",
      filepath: file.path,
      currentName: file.name,
      newName: trimmed,
    };
  }

  /** Arm the delete Confirmation_UI; issue no bridge call yet. */
  function requestDelete(file: FileRow) {
    clearFeedback();
    pending = { kind: "delete", filepath: file.path, name: file.name };
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
      const response = await callBridge("file_rename", action.filepath, action.newName);
      busy = false;
      if (!response.ok) {
        // Surface the error; leave UI unchanged — no fake success (Req 3.7).
        errorMessage = response.error.message;
        return;
      }
      successMessage = `Renamed to "${action.newName}".`;
      renameEditPath = "";
      renameDraft = "";
      onFilesChanged?.();
      return;
    }

    // action.kind === "delete"
    const response = await callBridge("file_delete", action.filepath);
    busy = false;
    if (!response.ok) {
      errorMessage = response.error.message;
      return;
    }
    successMessage = `Deleted "${action.name}" to the Recycle Bin.`;
    onFilesChanged?.();
  }

  async function confirmPending() {
    const action = pending;
    pending = null;
    if (action) await runAction(action);
  }

  const RESERVED_FILES = new Set(["project_data.json", "notes.md"]);
  let visibleFiles = $derived(files.filter((f) => !RESERVED_FILES.has(f.name.toLowerCase())));
</script>

<div class="fa-root">
  <!-- ── Create file ── -->
  <div class="fa-block">
    <span class="fa-block-label">Create File</span>
    {#if createLocked}
      <DisabledHint label="Create file" message={createLockMsg} variant="lock" />
    {:else}
      <div class="fa-row">
        <input
          class="fa-input"
          placeholder="New file name…"
          bind:value={newFilename}
          disabled={busy}
        />
        <button
          class="fa-btn"
          type="button"
          onclick={createFile}
          disabled={busy || !newFilename.trim()}
        >Create</button>
      </div>
      <div class="fa-row">
        <input
          class="fa-input"
          placeholder="Template name…"
          bind:value={newTemplateName}
          disabled={busy}
        />
        <button
          class="fa-btn"
          type="button"
          onclick={createFromTemplate}
          disabled={busy || !newTemplateName.trim()}
        >From template</button>
      </div>
    {/if}
  </div>

  <!-- ── File list with open / rename / delete ── -->
  <div class="fa-block">
    <span class="fa-block-label">Files</span>
    {#if visibleFiles.length === 0}
      <p class="fa-muted">No files.</p>
    {:else}
      <ul class="fa-file-list">
        {#each visibleFiles as f (f.path)}
          <li class="fa-file-row">
            {#if renameEditPath === f.path}
              <input
                class="fa-input"
                bind:value={renameDraft}
                disabled={busy}
              />
              <button
                class="fa-btn fa-btn-sm"
                type="button"
                onclick={() => requestRename(f)}
                disabled={busy || !renameDraft.trim()}
              >Rename</button>
              <button
                class="fa-btn fa-btn-sm"
                type="button"
                onclick={cancelRename}
                disabled={busy}
              >Cancel</button>
            {:else}
              <span class="fa-file-name" title={f.path}>{f.name}</span>
              <div class="fa-file-actions">
                <button
                  class="fa-btn fa-btn-sm"
                  type="button"
                  onclick={() => openFile(f.path)}
                  disabled={busy}
                >Open</button>
                {#if renameLocked}
                  <DisabledHint label="Rename" message={renameLockMsg} variant="lock" />
                {:else}
                  <button
                    class="fa-btn fa-btn-sm"
                    type="button"
                    onclick={() => startRename(f)}
                    disabled={busy}
                  >Rename</button>
                {/if}
                {#if deleteLocked}
                  <DisabledHint label="Delete" message={deleteLockMsg} variant="lock" />
                {:else}
                  <button
                    class="fa-btn fa-btn-danger fa-btn-sm"
                    type="button"
                    onclick={() => requestDelete(f)}
                    disabled={busy}
                  >Delete</button>
                {/if}
              </div>
            {/if}
          </li>
        {/each}
      </ul>
    {/if}
  </div>

  {#if errorMessage}
    <span class="fa-feedback fa-err" role="alert">✗ {errorMessage}</span>
  {:else if successMessage}
    <span class="fa-feedback fa-ok" role="status">✓ {successMessage}</span>
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
  .fa-root {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .fa-block {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .fa-block-label {
    font-size: 9px;
    font-weight: 800;
    color: var(--color-muted);
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }
  .fa-row {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
  }
  .fa-input {
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
  .fa-input:focus {
    border-color: var(--color-dbs-red);
  }
  .fa-input:disabled {
    background: #f3f4f6;
    color: var(--color-muted);
  }
  .fa-btn {
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
  .fa-btn:hover:not(:disabled) {
    border-color: var(--color-dbs-red, #DA1E28);
    color: var(--color-dbs-red, #DA1E28);
  }
  .fa-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .fa-btn-danger {
    border-color: var(--color-dbs-red, #DA1E28);
    color: var(--color-dbs-red, #DA1E28);
  }
  .fa-btn-danger:hover:not(:disabled) {
    background: var(--color-dbs-red, #DA1E28);
    color: #fff;
  }
  .fa-btn-sm {
    padding: 3px 9px;
    font-size: 9px;
  }
  .fa-file-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin: 0;
    padding: 0;
    list-style: none;
    max-height: 320px;
    overflow-y: auto;
    padding-right: 4px;
  }
  .fa-file-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    flex-wrap: wrap;
  }
  .fa-file-name {
    font-size: 11px;
    font-weight: 800;
    color: var(--color-ink);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;
    min-width: 0;
  }
  .fa-file-actions {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
    flex: 0 0 auto;
  }
  .fa-muted {
    margin: 0;
    font-size: 11px;
    font-weight: 700;
    color: var(--color-muted);
  }
  .fa-feedback {
    font-size: 10px;
    font-weight: 800;
    line-height: 1.3;
  }
  .fa-err {
    color: var(--color-dbs-red, #DA1E28);
  }
  .fa-ok {
    color: #166534;
  }
</style>
