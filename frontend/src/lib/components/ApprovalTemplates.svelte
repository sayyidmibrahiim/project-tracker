<script lang="ts">
  import { onMount, untrack } from "svelte";
  import { callBridge, getApprovalTemplate, isPywebviewReady, previewApprovalTemplate, updateApprovalTemplate } from "../bridge";
  import type { ApprovalTemplate } from "../types";

  type Kind = "uat" | "lv";
  const KINDS: { id: Kind; label: string; key: string }[] = [
    { id: "uat", label: "UAT Approval", key: "uat_approval" },
    { id: "lv", label: "LV Approval", key: "lv_approval" },
  ];
  const PLACEHOLDERS = "{CR_NUMBER} {PROJECT_NAME} {DRONE_TICKET} {START_DATETIME} {END_DATETIME}";
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

  async function loadProjects() {
    if (!isPywebviewReady()) return;
    const resp = await callBridge<ProjectRow[]>("project_list");
    if (resp.ok && Array.isArray(resp.data)) projects = resp.data;
  }

  async function loadTemplate() {
    preview = null; status = ""; statusIsError = false;
    if (!selectedProject) {
      // Global defaults live in settings.default_approval_templates.
      const resp = await callBridge<{ default_approval_templates?: Record<string, ApprovalTemplate> }>("settings_get");
      const key = KINDS.find((k) => k.id === kind)!.key;
      form = { ...EMPTY, ...(resp.ok ? resp.data?.default_approval_templates?.[key] : undefined) };
      source = "global default";
      return;
    }
    const resp = await getApprovalTemplate(selectedProject, kind);
    if (!resp.ok) { status = resp.error.message; statusIsError = true; return; }
    form = { ...EMPTY, ...resp.data?.template };
    source = resp.data?.source ?? "none";
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
  <p class="apt-source">Editing: <strong>{source}</strong> · Placeholders: <code>{PLACEHOLDERS}</code></p>
  <label class="field"><span>To</span><input class="input" bind:value={form.to} /></label>
  <label class="field"><span>CC</span><input class="input" bind:value={form.cc} /></label>
  <label class="field"><span>Subject (must contain {"{CR_NUMBER}"})</span><input class="input" bind:value={form.subject} /></label>
  <label class="field"><span>Body</span><textarea class="input apt-body" rows="6" bind:value={form.body}></textarea></label>
  <label class="field"><span>Mode</span>
    <select class="input" bind:value={form.mode}><option value="draft">Draft (open in Outlook)</option><option value="send">Send immediately</option></select>
  </label>
  <div class="apt-actions">
    <button type="button" class="pd-command-btn" onclick={save}>Save template</button>
    <button type="button" class="pd-command-btn" onclick={doPreview}>Preview with real data</button>
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
  .apt-root { display: flex; flex-direction: column; gap: 8px; }
  .apt-row { display: flex; gap: 12px; align-items: flex-end; flex-wrap: wrap; }
  .apt-tabs { display: flex; gap: 4px; }
  .apt-source { font-size: 12px; color: var(--text-secondary); margin: 0; }
  .apt-body { resize: vertical; font-family: inherit; }
  .apt-actions { display: flex; gap: 8px; align-items: center; }
  .apt-preview { border: 1px solid var(--light-border); border-radius: 6px; padding: 10px; font-size: 12px; }
  .apt-preview pre { white-space: pre-wrap; margin: 4px 0 0; font-family: inherit; }
</style>
