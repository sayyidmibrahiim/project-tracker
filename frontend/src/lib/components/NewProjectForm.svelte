<script lang="ts">
  /**
   * NEW_PROJECT create form — PRD §12.4.
   *
   * Minimal create flow that matches the backend `project_create` contract,
   * which accepts only `project_name` + `year` (creating
   * {ROOT}/{YEAR}/UAT_PREPARE/{NAME}/ with default metadata). The project name
   * is validated in realtime via the `util_validate_windows_folder_name` bridge;
   * Save is disabled while the name is empty or invalid. On success the parent
   * navigates to SHOW_EDIT for the new project, where the optional fields (CR
   * link, drone, implementation plan) are already editable.
   *
   * Deviation from PRD §12.4: the optional CR/drone/plan/schedule fields are not
   * collected here because `project_create` ignores them; they are filled in the
   * detail screen the user lands on. Schedule (start/end) has no editor anywhere
   * yet (pre-existing gap, tracked in the parity matrix).
   */
  import { untrack } from "svelte";
  import { callBridge, isPywebviewReady } from "../bridge";

  interface Props {
    yearOptions: string[];
    defaultYear: string;
    onCancel: () => void;
    onCreated: (projectPath: string) => void;
  }
  let { yearOptions, defaultYear, onCancel, onCreated }: Props = $props();

  let name = $state("");
  let year = $state(untrack(() => defaultYear));
  let nameValid = $state<boolean | null>(null);
  let nameError = $state("");
  let busy = $state(false);
  let createError = $state("");
  let timer: ReturnType<typeof setTimeout> | undefined;

  const canSave = $derived(!busy && name.trim().length > 0 && nameValid !== false);

  function onNameInput() {
    createError = "";
    if (timer) clearTimeout(timer);
    const candidate = name.trim();
    if (!candidate) {
      nameValid = false;
      nameError = "Project name is required.";
      return;
    }
    if (!isPywebviewReady()) {
      // No bridge in browser preview — defer to backend validation on create.
      nameValid = null;
      nameError = "Name is validated when you create (desktop app).";
      return;
    }
    nameValid = null;
    nameError = "Checking…";
    timer = setTimeout(async () => {
      const resp = await callBridge<{ valid: boolean; error: string | null }>(
        "util_validate_windows_folder_name",
        candidate,
      );
      if (resp.ok && resp.data) {
        nameValid = resp.data.valid;
        nameError = resp.data.valid ? "" : resp.data.error ?? "Invalid Windows folder name.";
      } else {
        nameValid = null;
        nameError = "";
      }
    }, 250);
  }

  async function create() {
    const candidate = name.trim();
    if (!candidate || nameValid === false || busy) return;
    if (timer) clearTimeout(timer);
    busy = true;
    createError = "";
    if (!isPywebviewReady()) {
      busy = false;
      createError = "pywebview bridge unavailable. Cannot create a project in browser preview.";
      return;
    }
    const resp = await callBridge<{ project_path: string }>("project_create", {
      project_name: candidate,
      year,
    });
    busy = false;
    if (!resp.ok) {
      createError = resp.error.message;
      return;
    }
    const path = resp.data?.project_path ?? "";
    onCreated(path);
  }
</script>

<div class="np-card">
  <div class="np-head">
    <span class="np-accent"></span>
    <div>
      <span class="np-kicker">New Project</span>
      <h3 class="np-title">Create a project</h3>
    </div>
  </div>

  <p class="np-hint">
    Creates <code>{`{root}`}/{year || "{year}"}/UAT_PREPARE/{name.trim() || "{name}"}</code>. CR link,
    drone tickets, and implementation plan are set on the next screen.
  </p>

  <label class="np-field">
    <span class="np-label">Project Name</span>
    <input
      class="np-input"
      class:invalid={nameValid === false}
      type="text"
      bind:value={name}
      oninput={onNameInput}
      placeholder="e.g. CR-2026-001-Acme-Migration"
      disabled={busy}
      autocomplete="off"
    />
    {#if nameValid === false}
      <small class="np-msg np-err">✗ {nameError}</small>
    {:else if nameError}
      <small class="np-msg np-muted">{nameError}</small>
    {:else if nameValid === true}
      <small class="np-msg np-ok">✓ Valid name</small>
    {/if}
  </label>

  <label class="np-field">
    <span class="np-label">Year</span>
    <select class="np-input np-year" bind:value={year} disabled={busy}>
      {#each yearOptions as y}
        <option value={y}>{y}</option>
      {/each}
    </select>
  </label>

  {#if createError}
    <div class="np-create-err" role="alert">⚠ {createError}</div>
  {/if}

  <div class="np-actions">
    <button class="np-btn" type="button" onclick={onCancel} disabled={busy}>Cancel</button>
    <button class="np-btn np-btn-primary" type="button" onclick={create} disabled={!canSave}>
      {busy ? "Creating…" : "Create Project"}
    </button>
  </div>
</div>

<style>
  .np-card { background:#fff; border:1px solid #E5E7EB; border-radius:8px; box-shadow:var(--shadow-subtle); padding:16px; display:flex; flex-direction:column; gap:12px; }
  .np-head { display:flex; align-items:center; gap:10px; }
  .np-accent { width:4px; min-width:4px; height:28px; border-radius:2px; background:var(--color-dbs-red); }
  .np-kicker { display:block; font-size:9px; font-weight:850; letter-spacing:0.4px; text-transform:uppercase; color:var(--color-muted); }
  .np-title { margin:2px 0 0; font-size:15px; font-weight:900; color:var(--color-ink); }
  .np-hint { margin:0; font-size:10px; font-weight:700; color:var(--color-muted); line-height:1.45; }
  .np-hint code { font-family:"JetBrains Mono","Fira Code",monospace; font-size:10px; background:var(--color-workspace-panel); padding:1px 5px; border-radius:3px; word-break:break-all; }
  .np-field { display:flex; flex-direction:column; gap:4px; }
  .np-label { font-size:9px; font-weight:850; color:var(--color-muted); text-transform:uppercase; letter-spacing:0.3px; }
  .np-input { height:30px; border:1px solid var(--color-input-border); border-radius:5px; background:#fff; color:var(--color-ink); font-weight:750; font-size:12px; outline:none; padding:0 9px; width:100%; font-family:inherit; }
  .np-input:focus { border:2px solid var(--color-dbs-red); }
  .np-input.invalid { border-color:#DC2626; }
  .np-input:disabled { background:var(--color-workspace-panel); color:var(--color-muted); }
  .np-year { max-width:160px; cursor:pointer; }
  .np-msg { font-size:10px; font-weight:800; }
  .np-err { color:#DC2626; }
  .np-ok { color:#15803D; }
  .np-muted { color:var(--color-muted); font-weight:700; }
  .np-create-err { background:var(--color-soft-pink-surface); border:1px solid var(--color-soft-pink-border); color:var(--color-dbs-red); border-radius:6px; padding:7px 10px; font-size:11px; font-weight:800; }
  .np-actions { display:flex; justify-content:flex-end; gap:8px; padding-top:2px; }
  .np-btn { height:32px; padding:0 16px; border:1px solid #D7DCE2; border-radius:5px; background:#fff; color:var(--color-ink); font-size:11px; font-weight:850; cursor:pointer; }
  .np-btn:hover:not(:disabled) { border-color:var(--color-dbs-red); color:var(--color-dbs-red); }
  .np-btn:disabled { opacity:0.5; cursor:not-allowed; }
  .np-btn-primary { background:var(--color-dbs-red); border-color:var(--color-dbs-red-hover); color:#fff; }
  .np-btn-primary:hover:not(:disabled) { background:var(--color-dbs-red-hover); color:#fff; }
</style>
