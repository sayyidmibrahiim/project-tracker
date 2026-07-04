<script lang="ts">
  /**
   * NEW_PROJECT create form — PRD §12.4 (Piece A).
   *
   * Project Type radio (CR / Non-CR only), appcode dropdown with inline "+"
   * create, and optional start/end datetime. Drone creation is lazy (done in
   * Project Details), so this form never sends drone_name.
   */
  import { onMount, untrack } from "svelte";
  import { callBridge, isPywebviewReady } from "../bridge";
  import type { AppCode } from "../types";

  interface Props {
    yearOptions: string[];
    defaultYear: string;
    onCancel: () => void;
    onCreated: (projectPath: string, appcode: string) => void;
  }
  let { yearOptions, defaultYear = "", onCancel, onCreated }: Props = $props();

  type ProjectTypeChoice = "CR" | "NON_CR";
  let projectType = $state<ProjectTypeChoice>("CR");
  let name = $state("");
  let appcode = $state("");
  let year = $state(untrack(() => defaultYear || String(new Date().getFullYear())));
  let appcodes = $state<AppCode[]>([]);
  let showAppcodeCreate = $state(false);
  let newAppcode = $state("");
  let appcodeError = $state("");
  let addingAppcode = $state(false);
  let startDatetime = $state("");
  let endDatetime = $state("");
  let nameValid = $state<boolean | null>(null);
  let nameError = $state("");
  let busy = $state(false);
  let createError = $state("");
  let timer: ReturnType<typeof setTimeout> | undefined;

  const yearChoices = $derived(yearOptions.length > 0 ? yearOptions : [String(new Date().getFullYear())]);
  const targetSegment = $derived(projectType === "NON_CR" ? "Non-CR" : "CR/UAT_PREPARE");
  const canSave = $derived(
    !busy &&
      appcode.trim().length > 0 &&
      year.trim().length > 0 &&
      name.trim().length > 0 &&
      nameValid !== false,
  );

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

  async function loadAppcodes() {
    if (!isPywebviewReady()) return;
    const resp = await callBridge<AppCode[]>("appcode_list");
    if (!resp.ok || !resp.data) return;
    appcodes = resp.data;
  }

  onMount(loadAppcodes);

  async function addAppcode() {
    appcodeError = "";
    const candidate = newAppcode.trim();
    if (!candidate || busy || addingAppcode) return;
    if (!isPywebviewReady()) {
      appcodeError = "pywebview bridge unavailable. Cannot create appcode in browser preview.";
      return;
    }
    addingAppcode = true;
    const resp = await callBridge<AppCode>("appcode_add", candidate);
    addingAppcode = false;
    if (!resp.ok || !resp.data) {
      appcodeError = resp.ok ? "Failed to create appcode." : resp.error.message;
      return;
    }
    if (!appcodes.some((item) => item.name === resp.data!.name)) {
      appcodes = [...appcodes, resp.data].sort((a, b) => a.name.localeCompare(b.name));
    }
    appcode = resp.data.name;
    newAppcode = "";
    showAppcodeCreate = false;
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
    const currentAppcode = appcode.trim();
    const payload: Record<string, string> = {
      appcode: currentAppcode,
      project_name: candidate,
      year,
      project_type: projectType,
    };
    if (startDatetime.trim()) payload.start_datetime = startDatetime.trim();
    if (endDatetime.trim()) payload.end_datetime = endDatetime.trim();
    const resp = await callBridge<{ project_path: string }>("project_create", payload);
    busy = false;
    if (!resp.ok) {
      createError = resp.error.message;
      return;
    }
    const path = resp.data?.project_path ?? "";
    onCreated(path, currentAppcode);
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
    Creates <code>{`{root}`}/{appcode.trim() || "{appcode}"}/{year || "{year}"}/{targetSegment}/{name.trim() || "{name}"}</code>. Drone tickets are added later in Project Details.
  </p>

  <div class="np-field">
    <span class="np-label">Project Type</span>
    <div class="np-radio-row" role="radiogroup" aria-label="Project Type">
      <label class="np-radio"><input type="radio" bind:group={projectType} value="CR" disabled={busy} /> CR</label>
      <label class="np-radio"><input type="radio" bind:group={projectType} value="NON_CR" disabled={busy} /> Non-CR</label>
    </div>
  </div>

  <div class="np-field">
    <span class="np-label">Appcode</span>
    <div class="np-inline-row">
      <select class="np-input" bind:value={appcode} disabled={busy}>
        <option value="" disabled>{appcodes.length === 0 ? "Select appcode or click +" : "Select appcode"}</option>
        {#each appcodes as item}
          <option value={item.name}>{item.display_name || item.name}</option>
        {/each}
      </select>
      <button
        class="np-add-btn"
        type="button"
        onclick={() => (showAppcodeCreate = !showAppcodeCreate)}
        disabled={busy}
        aria-label="Create appcode"
        title="Create appcode"
      >+</button>
    </div>
    {#if showAppcodeCreate}
      <div class="np-inline-row">
        <input
          class="np-input"
          type="text"
          bind:value={newAppcode}
          placeholder="New appcode name"
          disabled={busy || addingAppcode}
          autocomplete="off"
        />
        <button class="np-add-btn" type="button" onclick={addAppcode} disabled={busy || addingAppcode || newAppcode.trim().length === 0}>
          {addingAppcode ? "…" : "Add"}
        </button>
      </div>
    {/if}
    {#if appcodeError}
      <small class="np-msg np-err">{appcodeError}</small>
    {/if}
  </div>

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

  <div class="np-grid">
    <label class="np-field">
      <span class="np-label">Start datetime</span>
      <input class="np-input" type="datetime-local" bind:value={startDatetime} disabled={busy} />
    </label>
    <label class="np-field">
      <span class="np-label">End datetime</span>
      <input class="np-input" type="datetime-local" bind:value={endDatetime} disabled={busy} />
    </label>
  </div>

  <label class="np-field">
    <span class="np-label">Year</span>
    <select class="np-input np-year" bind:value={year} disabled={busy}>
      {#each yearChoices as y}
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
  .np-input.invalid { border-color:var(--active-red); }
  .np-input:disabled { background:var(--color-workspace-panel); color:var(--color-muted); }
  .np-year { max-width:160px; cursor:pointer; }
  .np-grid { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
  .np-radio-row { display:flex; gap:14px; }
  .np-radio { display:flex; align-items:center; gap:5px; font-size:12px; font-weight:800; color:var(--color-ink); cursor:pointer; }
  .np-radio input { accent-color:var(--color-dbs-red); }
  .np-inline-row { display:flex; gap:6px; }
  .np-add-btn { flex:0 0 auto; height:30px; min-width:34px; padding:0 8px; border:1px solid #D7DCE2; border-radius:5px; background:#fff; color:var(--color-ink); font-size:13px; font-weight:900; cursor:pointer; }
  .np-add-btn:hover:not(:disabled) { border-color:var(--color-dbs-red); color:var(--color-dbs-red); }
  .np-add-btn:disabled { opacity:0.5; cursor:not-allowed; }
  .np-msg { font-size:10px; font-weight:800; }
  .np-err { color:var(--active-red); }
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
