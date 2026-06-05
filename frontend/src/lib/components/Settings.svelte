<script lang="ts">
  import { callBridge, isPywebviewReady } from "../bridge";
  import { BridgeErrorCode } from "../types";

  // ── Props (accept any from parent; unused) ──
  let _props: Record<string, unknown> = $props();

  // ── Load/save state ──
  type LoadState = "idle" | "loading" | "error" | "loaded";
  let loadState: LoadState = $state("idle");
  let errorCode: string = $state("");
  let errorMessage: string = $state("");
  type SaveState = "idle" | "saving" | "success" | "error";
  let saveState: SaveState = $state("idle");
  let saveError: string = $state("");

  // ── Form data (populated from backend, mutable for local edits) ──
  type SettingsForm = Record<string, string | number>;
  let form: SettingsForm = $state({});

  // ── DTO key set used in form — pass-through extra keys untouched on save
  const FORM_FIELDS: { key: string; card: "general" | "behavior" | "paths" }[] = [
    { key: "root_folder", card: "general" },
    { key: "display_name", card: "general" },
    { key: "language", card: "general" },
    { key: "datetime_format", card: "general" },
    { key: "t10_threshold_days", card: "behavior" },
    { key: "auto_refresh_interval", card: "behavior" },
    { key: "startup_behavior", card: "behavior" },
    { key: "second_brain_folder", card: "paths" },
    { key: "file_template_folder", card: "paths" },
  ];

  let originalRaw: Record<string, unknown> = $state({});

  // ── Load settings ──
  async function loadSettings() {
    loadState = "loading";
    errorCode = "";
    errorMessage = "";

    if (!isPywebviewReady()) {
      errorCode = BridgeErrorCode.BRIDGE_UNAVAILABLE;
      errorMessage = "pywebview bridge is not available. Running outside desktop shell.";
      loadState = "error";
      return;
    }

    const response = await callBridge<Record<string, unknown>>("settings_get");
    if (!response.ok) {
      errorCode = response.error.code;
      errorMessage = response.error.message;
      loadState = "error";
      return;
    }

    originalRaw = response.data ?? {};
    // Seed form with recognized keys only
    const seed: SettingsForm = {};
    for (const f of FORM_FIELDS) {
      const v = originalRaw[f.key];
      seed[f.key] = typeof v === "string" || typeof v === "number" ? v : "";
    }
    form = seed;
    loadState = "loaded";
  }

  // ── Save settings ──
  async function handleSave() {
    saveState = "saving";
    saveError = "";

    if (!isPywebviewReady()) {
      saveState = "error";
      saveError = "Bridge unavailable.";
      return;
    }

    // Build payload: recognized form fields + pass-through extra DTO keys
    const payload: Record<string, unknown> = { ...originalRaw };
    for (const f of FORM_FIELDS) {
      payload[f.key] = form[f.key];
    }

    const response = await callBridge<Record<string, unknown>>("settings_update", payload);
    if (!response.ok) {
      saveState = "error";
      saveError = response.error.message;
      return;
    }

    // Refresh originalRaw so next save uses updated state
    originalRaw = (response.data as Record<string, unknown>) ?? payload;
    saveState = "success";
    setTimeout(() => {
      if (saveState === "success") saveState = "idle";
    }, 2500);
  }

  function handleFieldChange(key: string, value: string) {
    form = { ...form, [key]: value };
    if (saveState === "success") saveState = "idle";
  }

  // ── Help Center ──
  interface HelpTopic {
    title: string;
    body: string;
  }

  const helpTopics: HelpTopic[] = [
    { title: "General Settings", body: "Configure root folder, display name, language, and datetime format. Root folder is the top-level directory where all project year folders live. Display name appears in history entries and automation signatures." },
    { title: "Behavior", body: "T-10 threshold days controls the minimum days between PENDING APPROVAL and deployment start. Auto-refresh interval determines how often the dashboard rescans the filesystem. Startup behavior sets the default page on app launch." },
    { title: "Paths", body: "Second Brain folder stores your personal notes and knowledge base files outside of project folders. File Template folder provides template files for new project file creation." },
    { title: "Notifications", body: "Notifications appear in the sidebar across all pages. They include state transitions, T-10 warnings, folder moves, automation results, and scheduler alarms. Dismiss individually or all at once." },
    { title: "Automations", body: "Manage Outlook email templates, Teams message automations, scheduler alarms, and trigger-condition-action rules from the Automations page. Settings here only configure global defaults like automation mode and countdown timers." },
    { title: "Project Details", body: "Each project has a dedicated workspace with metadata forms, CR/Drone link management, sub-project management, file operations, a markdown notes editor, and a read-only activity history log." },
    { title: "Report", body: "Filter projects by year, folder state, and CR state, then export the results as a CSV file. The report table shows all key fields including T-10 status and last-updated timestamps." },
    { title: "Responsive UI", body: "The interface adapts to different window sizes. Sidebar collapses to icon-only mode. Tables scroll horizontally when content overflows. KPI cards wrap on narrow screens. All panels resize fluidly." },
    { title: "Troubleshooting", body: "If the dashboard shows stale data, click Refresh to rescan the filesystem. If the app behaves unexpectedly, check that your root folder path is valid and that year/project folders follow the expected structure. The SQLite cache can be rebuilt by restarting the app." },
    { title: "Future Documentation", body: "Additional help topics, contextual tooltips, and a searchable user guide will be added in future releases. For now, refer to PRD.md for the complete product specification." },
  ];

  let helpSearch: string = $state("");

  let filteredHelp: HelpTopic[] = $derived.by(() => {
    const q = helpSearch.trim().toLowerCase();
    if (!q) return helpTopics;
    return helpTopics.filter(
      (t) =>
        t.title.toLowerCase().includes(q) ||
        t.body.toLowerCase().includes(q),
    );
  });

  // ── Load on mount ──
  import { onMount } from "svelte";
  onMount(() => {
    loadSettings();
  });

  // Expose refresh for parent
  export function refresh() {
    loadSettings();
  }
</script>

<div class="settings-screen">
  <!-- ── Banner states ── -->
  {#if loadState === "loading"}
    <div class="dashboard-banner banner-loading">
      <span class="banner-icon">◌</span>
      <span>Loading settings…</span>
    </div>
  {:else if loadState === "error"}
    <div class="dashboard-banner banner-error">
      <span class="banner-icon">⚠</span>
      <div>
        <p class="banner-title">Settings unavailable</p>
        <p class="banner-detail">{errorCode}: {errorMessage}</p>
      </div>
    </div>
  {/if}

  <!-- ── Save toast ── -->
  {#if saveState === "success"}
    <div class="save-toast">✓ Settings saved</div>
  {:else if saveState === "error"}
    <div class="save-toast save-toast-error">✗ Save failed: {saveError}</div>
  {/if}

  <!-- ── Two-column body ── -->
  <div class="settings-body">
    <!-- LEFT: Forms -->
    <div class="settings-forms">

      <!-- General card -->
      <div class="settings-card">
        <div class="settings-card-head">
          <span class="settings-card-accent"></span>
          <h3>General</h3>
        </div>
        <div class="settings-fields">
          <label class="settings-label">
            Root Folder
            <div class="settings-field-row">
              <input
                class="settings-input"
                type="text"
                value={String(form["root_folder"] ?? "")}
                oninput={(e) => handleFieldChange("root_folder", (e.target as HTMLInputElement).value)}
                placeholder="D:\WORK\CR"
              />
              <button class="settings-btn-browse" disabled title="Browse not yet implemented">Browse</button>
            </div>
          </label>
          <label class="settings-label">
            Display Name
            <input
              class="settings-input"
              type="text"
              value={String(form["display_name"] ?? "")}
              oninput={(e) => handleFieldChange("display_name", (e.target as HTMLInputElement).value)}
              placeholder="Enter your display name"
            />
          </label>
          <label class="settings-label">
            Language
            <select
              class="settings-input"
              value={String(form["language"] ?? "en")}
              onchange={(e) => handleFieldChange("language", (e.target as HTMLSelectElement).value)}
            >
              <option value="en">English</option>
              <option value="id">Bahasa Indonesia</option>
            </select>
          </label>
          <label class="settings-label">
            Datetime Format
            <input
              class="settings-input"
              type="text"
              value={String(form["datetime_format"] ?? "")}
              oninput={(e) => handleFieldChange("datetime_format", (e.target as HTMLInputElement).value)}
              placeholder="ddd, dd MMM yyyy HH:mm"
            />
          </label>
        </div>
      </div>

      <!-- Behavior card -->
      <div class="settings-card">
        <div class="settings-card-head">
          <span class="settings-card-accent"></span>
          <h3>Behavior</h3>
        </div>
        <div class="settings-fields">
          <label class="settings-label">
            T-10 Threshold Days
            <input
              class="settings-input settings-input-narrow"
              type="number"
              min="1"
              max="30"
              value={String(form["t10_threshold_days"] ?? 10)}
              oninput={(e) => handleFieldChange("t10_threshold_days", (e.target as HTMLInputElement).value)}
            />
          </label>
          <label class="settings-label">
            Auto Refresh Interval
            <select
              class="settings-input settings-input-narrow"
              value={String(form["auto_refresh_interval"] ?? "off")}
              onchange={(e) => handleFieldChange("auto_refresh_interval", (e.target as HTMLSelectElement).value)}
            >
              <option value="off">Off</option>
              <option value="15s">15 seconds</option>
              <option value="30s">30 seconds</option>
              <option value="1min">1 minute</option>
            </select>
          </label>
          <label class="settings-label">
            Startup Behavior
            <select
              class="settings-input"
              value={String(form["startup_behavior"] ?? "current_year_dashboard")}
              onchange={(e) => handleFieldChange("startup_behavior", (e.target as HTMLSelectElement).value)}
            >
              <option value="current_year_dashboard">Current Year Dashboard</option>
              <option value="project_details">Project Details</option>
              <option value="second_brain">Second Brain</option>
            </select>
          </label>
        </div>
      </div>

      <!-- Paths card -->
      <div class="settings-card">
        <div class="settings-card-head">
          <span class="settings-card-accent"></span>
          <h3>Paths</h3>
        </div>
        <div class="settings-fields">
          <label class="settings-label">
            Second Brain Folder
            <div class="settings-field-row">
              <input
                class="settings-input"
                type="text"
                value={String(form["second_brain_folder"] ?? "")}
                oninput={(e) => handleFieldChange("second_brain_folder", (e.target as HTMLInputElement).value)}
                placeholder="%APPDATA%\ProjectTrackerDBS\SecondBrain"
              />
              <button class="settings-btn-browse" disabled title="Browse not yet implemented">Browse</button>
            </div>
          </label>
          <label class="settings-label">
            File Template Folder
            <div class="settings-field-row">
              <input
                class="settings-input"
                type="text"
                value={String(form["file_template_folder"] ?? "")}
                oninput={(e) => handleFieldChange("file_template_folder", (e.target as HTMLInputElement).value)}
                placeholder="Optional template folder path"
              />
              <button class="settings-btn-browse" disabled title="Browse not yet implemented">Browse</button>
            </div>
          </label>
        </div>
      </div>

      <!-- Save button -->
      <div class="settings-save-row">
        <button
          class="btn-save"
          disabled={loadState !== "loaded" || saveState === "saving"}
          onclick={handleSave}
        >
          {#if saveState === "saving"}
            <span class="btn-save-spin">◌</span>
            Saving…
          {:else}
            Save Settings
          {/if}
        </button>
      </div>
    </div>

    <!-- RIGHT: Help Center -->
    <div class="settings-help">
      <div class="help-search">
        <span class="search-icon">⌕</span>
        <input
          class="settings-input help-search-input"
          type="text"
          placeholder="Search help topics…"
          bind:value={helpSearch}
        />
      </div>
      <div class="help-list">
        {#each filteredHelp as topic}
          <article class="help-topic">
            <span class="help-topic-accent"></span>
            <div>
              <h4 class="help-topic-title">{topic.title}</h4>
              <p class="help-topic-body">{topic.body}</p>
            </div>
          </article>
        {:else}
          <div class="help-empty">No topics match your search.</div>
        {/each}
      </div>
    </div>
  </div>
</div>

<style>
  /* ── Screen ── */
  .settings-screen {
    flex: 1;
    min-height: 0;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    padding: 14px;
    gap: 10px;
    position: relative;
  }

  /* ── Toast ── */
  .save-toast {
    position: absolute;
    top: 18px;
    right: 22px;
    z-index: 40;
    background: var(--color-ink);
    color: #fff;
    font-weight: 900;
    font-size: 11px;
    padding: 8px 16px;
    border-radius: 6px;
    box-shadow: var(--shadow-panel);
    pointer-events: none;
  }
  .save-toast-error {
    background: var(--color-dbs-red);
  }

  /* ── Two-column body ── */
  .settings-body {
    flex: 1;
    min-height: 0;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
  }
  @media (max-width: 1020px) {
    .settings-body { grid-template-columns: 1fr; }
  }

  /* ── Left forms column ── */
  .settings-forms {
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding-right: 4px;
  }

  /* ── Card ── */
  .settings-card {
    background: #fff;
    border: 1px solid #E5E7EB;
    border-left: 3px solid var(--color-dbs-red);
    border-radius: 8px;
    box-shadow: var(--shadow-subtle);
    padding: 14px;
    flex: 0 0 auto;
  }
  .settings-card-head {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 12px;
  }
  .settings-card-head h3 {
    margin: 0;
    color: var(--color-ink);
    font-size: 13px;
    font-weight: 900;
    letter-spacing: 0.2px;
  }
  .settings-card-accent {
    width: 3px;
    min-width: 3px;
    height: 16px;
    border-radius: 2px;
    background: var(--color-dbs-red);
  }

  /* ── Fields ── */
  .settings-fields {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .settings-label {
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-weight: 800;
    font-size: 11px;
    color: var(--color-ink);
  }
  .settings-input {
    height: 28px;
    border: 1px solid var(--color-input-border);
    border-radius: 5px;
    background: #fff;
    color: var(--color-ink);
    font-weight: 750;
    font-size: 11px;
    outline: none;
    padding: 0 8px;
    width: 100%;
    font-family: inherit;
  }
  .settings-input:focus {
    border: 2px solid var(--color-dbs-red);
  }
  .settings-input-narrow {
    max-width: 160px;
  }
  .settings-field-row {
    display: flex;
    gap: 6px;
    align-items: center;
  }
  .settings-field-row .settings-input {
    flex: 1;
    min-width: 0;
  }

  /* Browse button (stub) */
  .settings-btn-browse {
    height: 28px;
    border-radius: 5px;
    padding: 0 12px;
    background: #fff;
    border: 1px solid var(--color-soft-pink-border);
    color: var(--color-dbs-red);
    font-weight: 800;
    font-size: 11px;
    white-space: nowrap;
    cursor: not-allowed;
    opacity: 0.55;
    flex: 0 0 auto;
  }

  /* ── Save ── */
  .settings-save-row {
    display: flex;
    justify-content: flex-end;
    padding-top: 2px;
    flex: 0 0 auto;
  }
  .btn-save {
    height: 32px;
    border-radius: 5px;
    font-weight: 900;
    font-size: 11px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 0 20px;
    background: var(--color-dbs-red);
    color: #fff;
    border: 1px solid var(--color-dbs-red-hover);
    cursor: pointer;
    transition: background 0.15s ease, transform 0.15s ease;
    white-space: nowrap;
  }
  .btn-save:hover:not(:disabled) {
    background: var(--color-dbs-red-hover);
    transform: translateY(-1px);
  }
  .btn-save:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }
  .btn-save-spin {
    display: inline-block;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  /* ── Right Help Center ── */
  .settings-help {
    background: var(--color-workspace-panel);
    border: 1px solid #D7DCE2;
    border-radius: 8px;
    box-shadow: var(--shadow-table-card);
    display: flex;
    flex-direction: column;
    min-height: 0;
    overflow: hidden;
  }
  .help-search {
    position: relative;
    display: flex;
    align-items: center;
    padding: 12px 14px;
    border-bottom: 1px solid #D7DCE2;
    flex: 0 0 auto;
  }
  .help-search .search-icon {
    position: absolute;
    left: 22px;
    font-weight: 900;
    color: var(--color-ink);
    pointer-events: none;
    font-size: 11px;
  }
  .help-search-input {
    padding-left: 25px;
  }
  .help-list {
    flex: 1;
    overflow-y: auto;
    padding: 10px 14px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .help-topic {
    background: #fff;
    border: 1px solid #E5E7EB;
    border-left: 3px solid var(--color-dbs-red);
    border-radius: 6px;
    padding: 10px 12px;
    display: flex;
    gap: 10px;
    align-items: flex-start;
  }
  .help-topic-accent {
    width: 3px;
    min-width: 3px;
    height: 14px;
    border-radius: 2px;
    background: var(--color-dbs-red);
    margin-top: 2px;
  }
  .help-topic-title {
    margin: 0 0 3px;
    font-size: 11px;
    font-weight: 900;
    color: var(--color-ink);
  }
  .help-topic-body {
    margin: 0;
    font-size: 10px;
    font-weight: 700;
    color: var(--color-muted);
    line-height: 1.42;
  }
  .help-empty {
    color: var(--color-muted-light);
    font-size: 11px;
    font-weight: 700;
    text-align: center;
    padding: 24px;
  }
</style>
