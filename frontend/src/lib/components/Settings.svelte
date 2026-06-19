<script lang="ts">
  import { onMount } from "svelte";
  import { callBridge, isPywebviewReady } from "../bridge";
  import { BridgeErrorCode } from "../types";

  let _props: Record<string, unknown> = $props();

  type LoadState = "idle" | "loading" | "error" | "loaded";
  let loadState: LoadState = $state("idle");
  let errorCode: string = $state("");
  let errorMessage: string = $state("");
  type SaveState = "idle" | "saving" | "success" | "error";
  let saveState: SaveState = $state("idle");
  let saveError: string = $state("");

  type SettingsForm = Record<string, string | number>;
  let form: SettingsForm = $state({});
  let originalRaw: Record<string, unknown> = $state({});

  const FORM_FIELDS: { key: string; card: "general" | "behavior" | "paths" }[] = [
    { key: "root_folder", card: "paths" },
    { key: "display_name", card: "general" },
    { key: "language", card: "general" },
    { key: "datetime_format", card: "general" },
    { key: "theme", card: "general" },
    { key: "t10_threshold_days", card: "behavior" },
    { key: "auto_refresh_interval", card: "behavior" },
    { key: "startup_behavior", card: "behavior" },
    { key: "second_brain_folder", card: "paths" },
    { key: "file_template_folder", card: "paths" },
  ];

  // Folder picker — backed by the util_choose_folder bridge (native OS dialog).
  // Falls back gracefully when the picker is unavailable (Linux dev/headless):
  // the input stays editable so the user can still type a path manually.
  let browseBusy: "" | "root_folder" | "second_brain_folder" | "file_template_folder" = $state("");
  let browseError: string = $state("");

  async function browseFolder(
    key: "root_folder" | "second_brain_folder" | "file_template_folder",
  ) {
    browseError = "";
    if (!isPywebviewReady()) {
      browseError = "Folder picker requires the desktop app. Type a path manually.";
      return;
    }
    browseBusy = key;
    const resp = await callBridge<{ path: string | null }>("util_choose_folder");
    browseBusy = "";
    if (!resp.ok) {
      browseError = resp.error.message;
      return;
    }
    const path = resp.data?.path ?? null;
    if (path) handleFieldChange(key, path);
  }

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
    const seed: SettingsForm = {};
    for (const f of FORM_FIELDS) {
      const v = originalRaw[f.key];
      seed[f.key] = typeof v === "string" || typeof v === "number" ? v : "";
    }
    form = seed;
    loadState = "loaded";
  }

  async function handleSave() {
    saveState = "saving";
    saveError = "";

    if (!isPywebviewReady()) {
      saveState = "error";
      saveError = "Bridge unavailable.";
      return;
    }

    const payload: Record<string, unknown> = { ...originalRaw };
    for (const f of FORM_FIELDS) payload[f.key] = form[f.key];

    const response = await callBridge<Record<string, unknown>>("settings_update", payload);
    if (!response.ok) {
      saveState = "error";
      saveError = response.error.message;
      return;
    }

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

  interface HelpTopic { title: string; body: string; }
  const helpTopics: HelpTopic[] = [
    { title: "General Settings", body: "Configure root folder, display name, language, and datetime format. Root folder is the top-level directory where all project year folders live." },
    { title: "Behavior", body: "T-10 threshold days controls the minimum days between PENDING APPROVAL and deployment start. Auto-refresh interval determines rescans." },
    { title: "Paths", body: "Second Brain folder stores notes and knowledge base files. File Template folder provides reusable files for projects." },
    { title: "Notifications", body: "Notifications appear in the sidebar across all pages for state changes, warnings, folder moves, automation results, and reminders." },
    { title: "Automations", body: "Manage Outlook templates, Teams messages, scheduler alarms, and trigger-condition-action rules from Automations." },
    { title: "Project Details", body: "Each project has metadata, CR/Drone links, sub-projects, files, notes, and activity history." },
    { title: "Report", body: "Filter projects by year, folder state, CR state, then export CSV." },
    { title: "Troubleshooting", body: "If data looks stale, click Refresh. Confirm root folder path and expected year/project folder structure." },
  ];

  let helpSearch: string = $state("");
  let filteredHelp: HelpTopic[] = $derived.by(() => {
    const q = helpSearch.trim().toLowerCase();
    if (!q) return helpTopics;
    return helpTopics.filter((t) => t.title.toLowerCase().includes(q) || t.body.toLowerCase().includes(q));
  });

  onMount(loadSettings);
  export function refresh() { loadSettings(); }
</script>

<section class="screen active" id="screen-settings">
  {#if loadState === "loading"}
    <div class="dashboard-banner banner-loading"><span class="banner-icon">◌</span><span>Loading settings…</span></div>
  {:else if loadState === "error"}
    <div class="dashboard-banner banner-error"><span class="banner-icon">⚠</span><div><p class="banner-title">Settings unavailable</p><p class="banner-detail">{errorCode}: {errorMessage}</p></div></div>
  {/if}

  {#if saveState === "success"}
    <div class="toast">✓ Settings saved</div>
  {:else if saveState === "error"}
    <div class="toast toast-error">✗ Save failed: {saveError}</div>
  {/if}

  <div class="splitter">
    <div class="pane">
      <div class="panel-card accent">
        <div class="panel-title-row"><span class="panel-title-icon">⚙</span><span class="panel-title">Settings</span><span class="panel-subtitle">application preferences</span></div>

        <div class="panel-card accent">
          <div class="panel-title-row"><span class="panel-title-icon">▣</span><span class="panel-title">General</span></div>
          <div class="form-grid">
            <label class="field"><span>Display Name</span><input class="input" value={String(form["display_name"] ?? "")} oninput={(e) => handleFieldChange("display_name", (e.target as HTMLInputElement).value)} /></label>
            <label class="field"><span>Language</span><select class="combo" value={String(form["language"] ?? "en")} onchange={(e) => handleFieldChange("language", (e.target as HTMLSelectElement).value)}><option value="en">English</option><option value="id">Bahasa Indonesia</option></select></label>
            <label class="field"><span>Datetime Format</span><input class="input" value={String(form["datetime_format"] ?? "")} oninput={(e) => handleFieldChange("datetime_format", (e.target as HTMLInputElement).value)} placeholder="ddd, dd MMM yyyy HH:mm" /></label>
            <label class="field"><span>Theme</span><select class="combo" value={String(form["theme"] ?? "dark")} onchange={(e) => handleFieldChange("theme", (e.target as HTMLSelectElement).value)}><option value="dark">DBS Red Chrome (Dark)</option><option value="light">Light</option></select></label>
          </div>
        </div>

        <div class="panel-card accent">
          <div class="panel-title-row"><span class="panel-title-icon">◷</span><span class="panel-title">Behavior</span></div>
          <div class="form-grid">
            <label class="field"><span>T-10 Threshold Days</span><input class="input" type="number" min="1" max="30" value={String(form["t10_threshold_days"] ?? 10)} oninput={(e) => handleFieldChange("t10_threshold_days", (e.target as HTMLInputElement).value)} /></label>
            <label class="field"><span>Auto Refresh</span><select class="combo" value={String(form["auto_refresh_interval"] ?? "off")} onchange={(e) => handleFieldChange("auto_refresh_interval", (e.target as HTMLSelectElement).value)}><option value="off">Off</option><option value="15s">15 seconds</option><option value="30s">30 seconds</option><option value="1min">1 minute</option></select></label>
            <label class="field"><span>Startup Behavior</span><select class="combo" value={String(form["startup_behavior"] ?? "current_year_dashboard")} onchange={(e) => handleFieldChange("startup_behavior", (e.target as HTMLSelectElement).value)}><option value="current_year_dashboard">Current Year Dashboard</option><option value="project_details">Project Details</option><option value="second_brain">Second Brain</option></select></label>
          </div>
        </div>

        <div class="panel-card accent">
          <div class="panel-title-row"><span class="panel-title-icon">▤</span><span class="panel-title">Paths</span></div>
          <div class="form-grid one-col">
            <label class="field"><span>Root Folder</span><div class="field-row"><input class="input" value={String(form["root_folder"] ?? "")} oninput={(e) => handleFieldChange("root_folder", (e.target as HTMLInputElement).value)} placeholder="D:\WORK\CR" /><button class="btn-secondary" onclick={() => browseFolder("root_folder")} disabled={browseBusy === "root_folder"}>{browseBusy === "root_folder" ? "…" : "Browse"}</button></div></label>
            <label class="field"><span>Second Brain Folder</span><div class="field-row"><input class="input" value={String(form["second_brain_folder"] ?? "")} oninput={(e) => handleFieldChange("second_brain_folder", (e.target as HTMLInputElement).value)} placeholder="%APPDATA%\ProjectTrackerDBS\SecondBrain" /><button class="btn-secondary" onclick={() => browseFolder("second_brain_folder")} disabled={browseBusy === "second_brain_folder"}>{browseBusy === "second_brain_folder" ? "…" : "Browse"}</button></div></label>
            <label class="field"><span>File Template Folder</span><div class="field-row"><input class="input" value={String(form["file_template_folder"] ?? "")} oninput={(e) => handleFieldChange("file_template_folder", (e.target as HTMLInputElement).value)} placeholder="Optional template folder path" /><button class="btn-secondary" onclick={() => browseFolder("file_template_folder")} disabled={browseBusy === "file_template_folder"}>{browseBusy === "file_template_folder" ? "…" : "Browse"}</button></div></label>
            {#if browseError}<span class="browse-error">⚠ {browseError}</span>{/if}
          </div>
        </div>

        <div class="toolbar right"><button class="btn-primary" disabled={loadState !== "loaded" || saveState === "saving"} onclick={handleSave}>{saveState === "saving" ? "Saving…" : "Save Settings"}</button></div>
      </div>
    </div>

    <div class="split-handle"></div>

    <div class="pane">
      <div class="panel-card accent" style="height:100%;">
        <div class="panel-title-row"><span class="panel-title-icon">?</span><span class="panel-title">Help Center</span><span class="panel-subtitle">searchable guide</span></div>
        <div class="search-shell"><span class="search-icon">⌕</span><input class="input" placeholder="Search help topics…" bind:value={helpSearch} /></div>
        <div class="list-box" style="margin-top:10px;">
          {#each filteredHelp as topic}
            <article class="list-row"><span class="panel-title-icon">▸</span><div><strong>{topic.title}</strong><p>{topic.body}</p></div></article>
          {:else}
            <div class="table-empty">No topics match your search.</div>
          {/each}
        </div>
      </div>
    </div>
  </div>
</section>

<style>
  .toast { position:absolute; top:18px; right:22px; z-index:40; background:var(--black-chrome); color:#fff; font-weight:900; font-size:11px; padding:8px 16px; border-radius:6px; box-shadow:var(--shadow-panel); pointer-events:none; }
  .toast-error { background:var(--primary-red); }
  .field-row { display:flex; gap:6px; align-items:center; }
  .field-row .input { flex:1; min-width:0; }
  .one-col { grid-template-columns:1fr; }
  .right { justify-content:flex-end; }
  .list-row { display:flex; gap:8px; padding:8px 10px; border-bottom:1px solid var(--border-soft); font-size:11px; }
  .list-row p { margin:3px 0 0; color:var(--color-muted); font-size:10px; line-height:1.4; }
  .browse-error { color:var(--primary-red); font-size:10px; font-weight:800; }
</style>
