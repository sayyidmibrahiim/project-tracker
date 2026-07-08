<script lang="ts">
  import { onMount, untrack } from "svelte";
  import {
    approvalAutocompleteTokens,
    callBridge,
    getApprovalTemplate,
    isPywebviewReady,
    previewApprovalTemplate,
    resetApprovalTemplate,
    testApprovalTemplate,
    updateApprovalTemplate,
  } from "../bridge";
  import type { ApprovalTemplate } from "../types";

  type Kind = "uat" | "lv";
  const KINDS: { id: Kind; label: string; key: string }[] = [
    { id: "uat", label: "UAT Approval", key: "uat_approval" },
    { id: "lv", label: "LV Approval", key: "lv_approval" },
  ];
  const EMPTY: ApprovalTemplate = { to: "", cc: "", subject: "", body: "", mode: "draft" };

  let { initialKind = null }: { initialKind?: Kind | null } = $props();

  type ProjectRow = { project_path: string; project_name: string };
  let projects: ProjectRow[] = $state([]);
  let selectedProject = $state("");
  let kind: Kind = $state(untrack(() => initialKind) ?? "uat");
  let form: ApprovalTemplate = $state({ ...EMPTY });
  let source = $state("none");
  let status = $state("");
  let statusIsError = $state(false);
  let preview: { to: string; cc: string; subject: string; body: string } | null = $state(null);

  // { autocomplete state
  type TokenEntry = { token: string; value: string };
  let tokens: TokenEntry[] = $state([]);
  let acOpen = $state(false);
  let acItems = $state<TokenEntry[]>([]);
  let acIndex = $state(0);
  let acAnchor: HTMLInputElement | HTMLTextAreaElement | null = $state(null);
  let acQueryStart = $state(-1);
  let acActiveField: "subject" | "body" | null = $state(null);

  async function loadProjects() {
    if (!isPywebviewReady()) return;
    const resp = await callBridge<ProjectRow[]>("project_list");
    if (resp.ok && Array.isArray(resp.data)) projects = resp.data;
  }

  async function loadTokens() {
    if (!selectedProject) { tokens = []; return; }
    const resp = await approvalAutocompleteTokens(selectedProject);
    if (resp.ok && resp.data) tokens = resp.data.tokens.map(([token, value]) => ({ token, value }));
  }

  async function loadTemplate() {
    preview = null; status = ""; statusIsError = false;
    if (!selectedProject) {
      // Global defaults live in settings.default_approval_templates.
      const resp = await callBridge<{ default_approval_templates?: Record<string, ApprovalTemplate> }>("settings_get");
      const key = KINDS.find((k) => k.id === kind)!.key;
      form = { ...EMPTY, ...(resp.ok ? resp.data?.default_approval_templates?.[key] : undefined) };
      source = "global default";
      tokens = [];
      return;
    }
    const resp = await getApprovalTemplate(selectedProject, kind);
    if (!resp.ok) { status = resp.error.message; statusIsError = true; return; }
    form = { ...EMPTY, ...resp.data?.template };
    source = resp.data?.source ?? "none";
    await loadTokens();
  }

  async function save() {
    status = ""; statusIsError = false;
    if (!form.subject.includes("{CR_NUMBER}")) { status = "Subject must contain {CR_NUMBER}"; statusIsError = true; return; }
    if (!selectedProject) {
      const key = KINDS.find((k) => k.id === kind)!.key;
      const current = await callBridge<{ default_approval_templates?: Record<string, ApprovalTemplate> }>("settings_get");
      const defaults = { ...(current.ok ? current.data?.default_approval_templates : {}) , [key]: { ...form } };
      const resp = await callBridge("settings_update", { default_approval_templates: defaults });
      status = resp.ok ? "Saved global default" : resp.error.message;
      statusIsError = !resp.ok;
    } else {
      const resp = await updateApprovalTemplate(selectedProject, kind, { ...form });
      status = resp.ok ? "Saved for project" : resp.error.message;
      statusIsError = !resp.ok;
    }
    if (!statusIsError) await loadTemplate();
  }

  async function doPreview() {
    status = ""; statusIsError = false;
    if (!selectedProject) { status = "Pick a project to preview with real data"; statusIsError = true; return; }
    const resp = await previewApprovalTemplate(selectedProject, kind, { ...form });
    if (!resp.ok) { status = resp.error.message; statusIsError = true; return; }
    preview = resp.data ?? null;
  }

  async function doTest() {
    status = ""; statusIsError = false;
    if (!selectedProject) { status = "Pick a project to test with real data"; statusIsError = true; return; }
    const resp = await testApprovalTemplate(selectedProject, kind, { ...form });
    if (!resp.ok) { status = resp.error.message; statusIsError = true; return; }
    status = resp.data?.status === "dev_skipped"
      ? "Test draft (dev-skipped off-Windows)"
      : `Test draft opened: ${resp.data?.subject ?? ""}`;
  }

  async function doReset() {
    status = ""; statusIsError = false;
    if (!selectedProject) { status = "Pick a project to reset its override"; statusIsError = true; return; }
    const resp = await resetApprovalTemplate(selectedProject, kind);
    if (!resp.ok) { status = resp.error.message; statusIsError = true; return; }
    status = resp.data?.removed ? "Override removed, default restored" : "No override to remove";
    await loadTemplate();
  }

  // { autocomplete: open dropdown on "{", filter tokens, keyboard nav
  function onFieldKey(e: KeyboardEvent, field: "subject" | "body") {
    const el = e.currentTarget as HTMLInputElement | HTMLTextAreaElement;
    if (acOpen) {
      if (e.key === "ArrowDown") { e.preventDefault(); acIndex = Math.min(acIndex + 1, acItems.length - 1); return; }
      if (e.key === "ArrowUp") { e.preventDefault(); acIndex = Math.max(acIndex - 1, 0); return; }
      if (e.key === "Enter" || e.key === "Tab") {
        if (acItems[acIndex]) { e.preventDefault(); insertToken(field, acItems[acIndex].token, el); return; }
      }
      if (e.key === "Escape") { acOpen = false; return; }
    }
    if (e.key === "{") {
      acAnchor = el;
      acActiveField = field;
      acQueryStart = el.selectionStart ?? form[field].length;
      acItems = tokens;
      acIndex = 0;
      acOpen = tokens.length > 0;
    }
  }

  function onFieldInput(field: "subject" | "body") {
    if (!acOpen || !acAnchor) return;
    const after = form[field].slice(acQueryStart + 1).toUpperCase();
    if (!after) { acItems = tokens; acIndex = 0; return; }
    acItems = tokens.filter((t) => t.token.toUpperCase().includes(after));
    acIndex = 0;
    acOpen = acItems.length > 0;
  }

  function insertToken(field: "subject" | "body", token: string, el: HTMLInputElement | HTMLTextAreaElement) {
    // Replace the typed "{" (and partial query) with the chosen token.
    const before = form[field].slice(0, acQueryStart);
    const afterCursor = form[field].slice(el.selectionStart ?? form[field].length);
    form[field] = before + token + afterCursor;
    acOpen = false;
    acActiveField = null;
    requestAnimationFrame(() => { el.focus(); const pos = (before + token).length; el.setSelectionRange(pos, pos); });
  }

  onMount(() => { loadProjects(); loadTemplate(); });
</script>

<div class="apt-root">
  <div class="apt-row">
    <label class="field"><span>Project (empty = global default)</span>
      <select class="input" bind:value={selectedProject} onchange={loadTemplate}>
        <option value="">Global defaults</option>
        {#each projects as p}<option value={p.project_path}>{p.project_name}</option>{/each}
      </select>
    </label>
    {#if initialKind === null}
      <div class="apt-tabs">
        {#each KINDS as k}
          <button type="button" class="sb-tab" class:active={kind === k.id} onclick={() => { kind = k.id; void loadTemplate(); }}>{k.label}</button>
        {/each}
      </div>
    {/if}
  </div>
  <p class="apt-source">Editing: <strong>{source}</strong> · Type <code>{"{"}</code> in subject/body for placeholder autocomplete ({tokens.length} tokens loaded){#if tokens.length === 0 && selectedProject} — none loaded{/if}</p>
  <label class="field"><span>To</span><input class="input" bind:value={form.to} /></label>
  <label class="field"><span>CC</span><input class="input" bind:value={form.cc} /></label>
  <label class="field apt-field-with-ac">
    <span>Subject (must contain {"{CR_NUMBER}"})</span>
    <input
      class="input"
      bind:value={form.subject}
      onkeydown={(e) => onFieldKey(e, "subject")}
      oninput={() => onFieldInput("subject")}
    />
    {#if acOpen && acActiveField === "subject"}
      <ul class="ac-list">
        {#each acItems as entry, i}
          <li class:active={i === acIndex} onclick={() => insertToken("subject", entry.token, acAnchor!)}>
            <span class="ac-token">{entry.token}</span>
            <span class="ac-value">{entry.value || "(empty)"}</span>
          </li>
        {/each}
      </ul>
    {/if}
  </label>
  <label class="field apt-field-with-ac">
    <span>Body</span>
    <textarea
      class="input apt-body"
      rows="6"
      bind:value={form.body}
      onkeydown={(e) => onFieldKey(e, "body")}
      oninput={() => onFieldInput("body")}
    ></textarea>
    {#if acOpen && acActiveField === "body"}
      <ul class="ac-list">
        {#each acItems as entry, i}
          <li class:active={i === acIndex} onclick={() => insertToken("body", entry.token, acAnchor!)}>
            <span class="ac-token">{entry.token}</span>
            <span class="ac-value">{entry.value || "(empty)"}</span>
          </li>
        {/each}
      </ul>
    {/if}
  </label>
  <label class="field"><span>Mode</span>
    <select class="input" bind:value={form.mode}><option value="draft">Draft (open in Outlook)</option><option value="send">Send immediately</option></select>
  </label>
  <div class="apt-actions">
    <button type="button" class="pd-command-btn" onclick={save}>Save template</button>
    <button type="button" class="pd-command-btn" onclick={doPreview}>Preview with real data</button>
    <button type="button" class="pd-command-btn" onclick={doTest}>Test (open Outlook draft)</button>
    <button type="button" class="pd-command-btn" onclick={doReset} disabled={!selectedProject}>Reset to default</button>
    {#if status}<span class="cr-link-feedback" class:cr-link-err={statusIsError} class:cr-link-ok={!statusIsError}>{status}</span>{/if}
  </div>
  {#if preview}
    <div class="apt-preview">
      <p><strong>To:</strong> {preview.to} <strong>CC:</strong> {preview.cc}</p>
      <p><strong>Subject:</strong> {preview.subject}</p>
      <pre>{preview.body}</pre>
    </div>
  {/if}
</div>

<style>
  .apt-root { display: flex; flex-direction: column; gap: 8px; position: relative; }
  .apt-row { display: flex; gap: 12px; align-items: flex-end; flex-wrap: wrap; }
  .apt-tabs { display: flex; gap: 4px; }
  .apt-source { font-size: 12px; color: var(--text-secondary); margin: 0; }
  .apt-body { resize: vertical; font-family: inherit; }
  .apt-actions { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .apt-preview { border: 1px solid var(--light-border); border-radius: 6px; padding: 10px; font-size: 12px; }
  .apt-preview pre { white-space: pre-wrap; margin: 4px 0 0; font-family: inherit; }
  .apt-field-with-ac { position: relative; }
  .ac-list {
    position: absolute; z-index: 50; left: 0; right: 0; top: 100%;
    background: var(--bg-secondary, #fff); border: 1px solid var(--light-border); border-radius: 6px;
    margin: 2px 0 0; padding: 0; list-style: none; max-height: 200px; overflow-y: auto; font-size: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  }
  .ac-list li { display: flex; justify-content: space-between; gap: 12px; padding: 6px 10px; cursor: pointer; }
  .ac-list li.active, .ac-list li:hover { background: var(--accent-bg, #e8f0fe); }
  .ac-token { font-family: monospace; color: var(--text-primary); }
  .ac-value { color: var(--text-secondary); font-style: italic; max-width: 60%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
