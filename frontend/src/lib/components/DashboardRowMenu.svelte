<script lang="ts">
  /**
   * Dashboard row action menu — PRD §11.13.
   *
   * Single ⋮ dropdown: Project Details (navigate), Open Project Folder
   * (`project_open_folder`), folder transitions (embedded `ProjectTransitions`
   * inline — the tested authority for move/postpone/cancel/reopen + guards), and
   * Delete (Recycle Bin via `project_delete`, gated by Folder_State lock and a
   * ConfirmModal). All bridge access via `callBridge`; no new contract.
   */
  import { callBridge, isPywebviewReady } from "../bridge";
  import { lockReason } from "../folderLocks";
  import ConfirmModal from "./ConfirmModal.svelte";
  import ProjectTransitions from "./ProjectTransitions.svelte";

  interface Props {
    projectPath: string;
    projectState: string;
    projectName: string;
    onOpenDetails: (path: string) => void;
    onChanged: () => void;
  }
  let { projectPath, projectState, projectName, onOpenDetails, onChanged }: Props = $props();

  let open = $state(false);
  let busy = $state(false);
  let error = $state("");
  let pendingDelete = $state(false);

  const deleteLock = $derived(lockReason(projectState, "delete_project"));

  async function openFolder() {
    error = "";
    if (!isPywebviewReady()) {
      error = "Open Folder requires the desktop app.";
      return;
    }
    busy = true;
    const r = await callBridge("project_open_folder", projectPath);
    busy = false;
    if (!r.ok) error = r.error.message;
    else open = false;
  }

  function details() {
    open = false;
    onOpenDetails(projectPath);
  }

  function requestDelete() {
    error = "";
    pendingDelete = true;
  }
  function cancelDelete() {
    pendingDelete = false;
  }
  async function confirmDelete() {
    pendingDelete = false;
    if (!isPywebviewReady()) {
      error = "Delete requires the desktop app.";
      return;
    }
    busy = true;
    const r = await callBridge("project_delete", projectPath);
    busy = false;
    if (!r.ok) {
      error = r.error.message;
      return;
    }
    open = false;
    onChanged();
  }

  function onKey(event: KeyboardEvent) {
    if (event.key === "Escape") open = false;
  }
</script>

<svelte:window onkeydown={onKey} />

<div class="rm-root">
  <button
    class="rm-trigger"
    type="button"
    aria-label="Row actions"
    aria-haspopup="menu"
    aria-expanded={open}
    onclick={() => (open = !open)}
  >⋮</button>

  {#if open}
    <button class="rm-scrim" type="button" aria-label="Close menu" onclick={() => (open = false)}></button>
    <div class="rm-menu" role="menu">
      <button class="rm-item" type="button" role="menuitem" onclick={details}>Project Details</button>
      <button class="rm-item" type="button" role="menuitem" onclick={openFolder} disabled={busy}>Open Project Folder</button>
      <div class="rm-divider"></div>
      <div class="rm-transitions">
        <ProjectTransitions
          {projectPath}
          {projectState}
          {projectName}
          variant="inline"
          onApplied={() => { open = false; onChanged(); }}
        />
      </div>
      <div class="rm-divider"></div>
      {#if deleteLock}
        <div class="rm-locked" title={deleteLock}>🔒 Delete — {deleteLock}</div>
      {:else}
        <button class="rm-item rm-danger" type="button" role="menuitem" onclick={requestDelete} disabled={busy}>Delete project…</button>
      {/if}
      {#if error}
        <div class="rm-error" role="alert">⚠ {error}</div>
      {/if}
    </div>
  {/if}
</div>

{#if pendingDelete}
  <ConfirmModal
    title="Delete project"
    actionLabel="Delete"
    targetName={projectName}
    reversible={false}
    onConfirm={confirmDelete}
    onCancel={cancelDelete}
  />
{/if}

<style>
  .rm-root { position:relative; display:inline-flex; }
  .rm-trigger { width:28px; height:28px; border:0; border-radius:4px; background:transparent; color:var(--color-ink); font-size:14px; font-weight:900; cursor:pointer; line-height:1; }
  .rm-trigger:hover { background:#ADB9B2; }
  .rm-scrim { position:fixed; inset:0; z-index:40; border:0; background:transparent; cursor:default; }
  .rm-menu { position:absolute; right:0; top:30px; z-index:50; min-width:210px; background:#fff; border:1px solid #D7DCE2; border-radius:8px; box-shadow:0 12px 32px rgba(0,0,0,0.28); padding:6px; display:flex; flex-direction:column; gap:2px; }
  .rm-item { text-align:left; padding:7px 10px; border:0; border-radius:5px; background:transparent; color:var(--color-ink); font-size:11px; font-weight:800; cursor:pointer; white-space:nowrap; }
  .rm-item:hover:not(:disabled) { background:var(--color-soft-pink-surface); color:var(--color-dbs-red); }
  .rm-item:disabled { opacity:0.5; cursor:not-allowed; }
  .rm-danger { color:var(--color-dbs-red); }
  .rm-danger:hover:not(:disabled) { background:var(--color-dbs-red); color:#fff; }
  .rm-divider { height:1px; background:#E5E7EB; margin:3px 0; }
  .rm-transitions { padding:2px; }
  .rm-locked { padding:7px 10px; font-size:10px; font-weight:750; color:var(--color-muted); }
  .rm-error { padding:6px 10px; font-size:10px; font-weight:800; color:var(--color-dbs-red); background:var(--color-soft-pink-surface); border-radius:5px; }
</style>
