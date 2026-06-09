<script lang="ts">
  /**
   * Email Template Dialog — PRD §16.3.
   *
   * Edits a single Outlook send-category template (ACK_UAT, ACK_SOP, APRVL_CR,
   * APRVL_SOP). Configuration is persisted as part of application settings
   * (`AppSettings.email.categories[code]`), so this dialog loads via the existing
   * `settings_get` bridge method and saves via `settings_update` using a
   * full-object round-trip that mutates ONLY the edited category — no new bridge
   * contract is introduced and no other settings are touched.
   *
   * Draft-first safety: the per-category mode defaults to "Use global default"
   * (the global default is Draft). "Send Immediately" is an explicit opt-in and
   * still requires Windows Outlook COM + the project-context send confirmation to
   * actually send; this dialog only stores the template/mode.
   */
  import { onMount, tick } from "svelte";
  import { callBridge, isPywebviewReady } from "../bridge";

  interface Props {
    categoryCode: string;
    onClose: () => void;
    onSaved?: (categoryCode: string) => void;
  }
  let { categoryCode, onClose, onSaved }: Props = $props();

  interface Condition {
    field: string;
    operator: string;
    value: string;
  }
  interface CategoryForm {
    to: string;
    cc: string;
    subject_template: string;
    body_template: string;
    attachment_template_file: string;
    mode_override: "" | "draft" | "send";
    conditions: Condition[];
  }

  // Canonical placeholders (EmailService.REQUIRED_PLACEHOLDERS, PRD §16.3).
  const PLACEHOLDERS = [
    "{PROJECT_NAME}", "{CR_NUMBER}", "{CR_LINK}", "{CR_STATE}",
    "{DRONE_TICKET}", "{DRONE_LINK}", "{DRONE_STATE}", "{START_DATETIME}",
    "{END_DATETIME}", "{IMPLEMENTATION_PLAN}", "{DISPLAY_NAME}",
  ];

  // Condition fields/operators that the backend EmailService actually evaluates.
  const CONDITION_FIELDS = [
    "project_name", "cr_number", "cr_link", "cr_state", "drone_count", "implementation_plan",
  ];
  const CONDITION_OPERATORS = [
    { value: "equals", label: "equals" },
    { value: "not_equals", label: "is not equals" },
    { value: "contains", label: "contains" },
    { value: "exists", label: "is not empty" },
  ];

  type LoadState = "idle" | "loading" | "loaded" | "error";
  let loadState = $state<LoadState>("idle");
  let loadError = $state("");
  type SaveState = "idle" | "saving" | "success" | "error";
  let saveState = $state<SaveState>("idle");
  let saveError = $state("");

  let originalRaw: Record<string, unknown> = $state({});
  let form: CategoryForm = $state({
    to: "",
    cc: "",
    subject_template: "",
    body_template: "",
    attachment_template_file: "",
    mode_override: "",
    conditions: [],
  });

  // Track the last-focused template field + element so placeholder chips insert
  // at the caret of the field the user was editing.
  let lastField: "subject_template" | "body_template" = $state("body_template");
  let subjectEl: HTMLInputElement | null = $state(null);
  let bodyEl: HTMLTextAreaElement | null = $state(null);

  async function load() {
    loadState = "loading";
    loadError = "";
    if (!isPywebviewReady()) {
      loadState = "error";
      loadError = "pywebview bridge unavailable. Browser preview is read-only; values cannot load or save.";
      return;
    }
    const res = await callBridge<Record<string, unknown>>("settings_get");
    if (!res.ok) {
      loadState = "error";
      loadError = res.error.message;
      return;
    }
    originalRaw = res.data ?? {};
    const email = (originalRaw.email ?? {}) as Record<string, unknown>;
    const categories = (email.categories ?? {}) as Record<string, Record<string, unknown>>;
    const cat = (categories[categoryCode] ?? {}) as Record<string, unknown>;
    const rawConditions = Array.isArray(cat.conditions) ? cat.conditions : [];
    form = {
      to: String(cat.to ?? ""),
      cc: String(cat.cc ?? ""),
      subject_template: String(cat.subject_template ?? ""),
      body_template: String(cat.body_template ?? ""),
      attachment_template_file: String(cat.attachment_template_file ?? ""),
      mode_override: cat.mode_override === "draft" || cat.mode_override === "send" ? cat.mode_override : "",
      conditions: rawConditions.map((c) => {
        const cond = (c ?? {}) as Record<string, unknown>;
        return {
          field: String(cond.field ?? "cr_state"),
          operator: String(cond.operator ?? "equals"),
          value: String(cond.value ?? ""),
        };
      }),
    };
    loadState = "loaded";
  }

  onMount(load);

  async function insertPlaceholder(token: string) {
    const field = lastField;
    const el = field === "subject_template" ? subjectEl : bodyEl;
    const current = form[field];
    let caret = current.length;
    if (el && typeof el.selectionStart === "number") {
      const start = el.selectionStart;
      const end = el.selectionEnd ?? start;
      form[field] = current.slice(0, start) + token + current.slice(end);
      caret = start + token.length;
    } else {
      form[field] = current + token;
    }
    await tick();
    if (el) {
      el.focus();
      try {
        el.setSelectionRange(caret, caret);
      } catch {
        /* setSelectionRange unsupported on this element type — ignore */
      }
    }
  }

  function addCondition() {
    form.conditions = [...form.conditions, { field: "cr_state", operator: "equals", value: "" }];
  }
  function removeCondition(index: number) {
    form.conditions = form.conditions.filter((_, i) => i !== index);
  }

  const conditionPreview = $derived(
    form.conditions.length === 0
      ? "No conditions — this template always applies when triggered."
      : form.conditions
          .map((c) => `${c.field} ${c.operator}${c.operator === "exists" ? "" : ` "${c.value}"`}`)
          .join("   AND   "),
  );

  const modeLabel = $derived(
    form.mode_override === "send"
      ? "Send Immediately (requires confirmation + Outlook COM)"
      : form.mode_override === "draft"
        ? "Draft Only"
        : "Use global default (Draft)",
  );

  async function save() {
    saveState = "saving";
    saveError = "";
    if (!isPywebviewReady()) {
      saveState = "error";
      saveError = "Bridge unavailable. Cannot save from browser preview.";
      return;
    }
    // Full-object round-trip: clone loaded settings and replace ONLY this category.
    const payload: Record<string, unknown> = { ...originalRaw };
    const email = { ...((originalRaw.email ?? {}) as Record<string, unknown>) };
    const categories = { ...((email.categories ?? {}) as Record<string, unknown>) };
    categories[categoryCode] = {
      to: form.to,
      cc: form.cc,
      subject_template: form.subject_template,
      body_template: form.body_template,
      attachment_template_file: form.attachment_template_file,
      mode_override: form.mode_override ? form.mode_override : null,
      conditions: form.conditions.map((c) => ({ field: c.field, operator: c.operator, value: c.value })),
    };
    email.categories = categories;
    payload.email = email;

    const res = await callBridge<Record<string, unknown>>("settings_update", payload);
    if (!res.ok) {
      saveState = "error";
      saveError = res.error.message;
      return;
    }
    originalRaw = (res.data as Record<string, unknown>) ?? payload;
    saveState = "success";
    onSaved?.(categoryCode);
    setTimeout(() => {
      if (saveState === "success") saveState = "idle";
    }, 2000);
  }

  function onBackdropKey(event: KeyboardEvent) {
    if (event.key === "Escape") onClose();
  }
</script>

<svelte:window onkeydown={onBackdropKey} />

<div class="etd-backdrop">
  <button class="etd-backdrop-close" type="button" aria-label="Close dialog" onclick={onClose}></button>
  <div
    class="etd-dialog"
    role="dialog"
    aria-modal="true"
    tabindex="-1"
    aria-label={`Email template for ${categoryCode}`}
  >
    <header class="etd-head">
      <div>
        <span class="etd-kicker">Email Template</span>
        <h2 class="etd-title">{categoryCode}</h2>
      </div>
      <button class="etd-x" type="button" aria-label="Close" onclick={onClose}>✕</button>
    </header>

    {#if loadState === "loading"}
      <div class="etd-banner etd-banner-info" role="status">◌ Loading template…</div>
    {:else if loadState === "error"}
      <div class="etd-banner etd-banner-warn" role="alert">⚠ {loadError}</div>
    {/if}

    <div class="etd-body">
      <!-- LEFT: template fields -->
      <section class="etd-col" aria-label="Template content">
        <label class="etd-field">
          <span>Category Code</span>
          <input class="etd-input" type="text" value={categoryCode} readonly aria-readonly="true" />
          <small class="etd-hint">Fixed PRD category. The four send categories are defined by the backend settings model.</small>
        </label>

        <div class="etd-row2">
          <label class="etd-field">
            <span>To</span>
            <input class="etd-input" type="text" bind:value={form.to} placeholder="recipient@example.com" />
          </label>
          <label class="etd-field">
            <span>CC</span>
            <input class="etd-input" type="text" bind:value={form.cc} placeholder="cc@example.com" />
          </label>
        </div>

        <label class="etd-field">
          <span>Subject Template</span>
          <input
            class="etd-input"
            type="text"
            bind:this={subjectEl}
            bind:value={form.subject_template}
            onfocus={() => (lastField = "subject_template")}
            placeholder="[{'{CR_NUMBER}'}] UAT acknowledgment for {'{PROJECT_NAME}'}"
          />
        </label>

        <label class="etd-field">
          <span>Body Template</span>
          <textarea
            class="etd-textarea"
            rows="6"
            bind:this={bodyEl}
            bind:value={form.body_template}
            onfocus={() => (lastField = "body_template")}
            placeholder="Dear team,&#10;&#10;CR {'{CR_NUMBER}'} ({'{CR_STATE}'}) is ready…"
          ></textarea>
        </label>

        <div class="etd-chips" aria-label="Insert placeholder">
          <span class="etd-chips-label">Insert placeholder:</span>
          {#each PLACEHOLDERS as token}
            <button class="etd-chip" type="button" onclick={() => insertPlaceholder(token)}>{token}</button>
          {/each}
        </div>

        <label class="etd-field">
          <span>Attachment Template File</span>
          <input
            class="etd-input"
            type="text"
            bind:value={form.attachment_template_file}
            placeholder="Optional path/filename within the template folder"
          />
        </label>

        <label class="etd-field">
          <span>Automation Mode</span>
          <select class="etd-input" bind:value={form.mode_override}>
            <option value="">Use global default (Draft)</option>
            <option value="draft">Draft Only</option>
            <option value="send">Send Immediately</option>
          </select>
          <small class="etd-hint">{modeLabel}</small>
        </label>
      </section>

      <!-- RIGHT: conditions + preview + log -->
      <section class="etd-col" aria-label="Conditions and preview">
        <div class="etd-subhead">
          <h3>Active Conditions</h3>
          <button class="etd-btn" type="button" onclick={addCondition}>+ Add Condition</button>
        </div>
        <p class="etd-hint">All conditions must pass (logical AND) before this email is composed.</p>

        <div class="etd-conditions">
          {#if form.conditions.length === 0}
            <div class="etd-empty">No conditions defined.</div>
          {/if}
          {#each form.conditions as cond, i}
            <div class="etd-cond-row">
              <select class="etd-input etd-cond-field" bind:value={cond.field}>
                {#each CONDITION_FIELDS as f}<option value={f}>{f}</option>{/each}
              </select>
              <select class="etd-input etd-cond-op" bind:value={cond.operator}>
                {#each CONDITION_OPERATORS as op}<option value={op.value}>{op.label}</option>{/each}
              </select>
              <input
                class="etd-input etd-cond-val"
                type="text"
                bind:value={cond.value}
                disabled={cond.operator === "exists"}
                placeholder={cond.operator === "exists" ? "n/a" : "value"}
              />
              <button class="etd-cond-del" type="button" aria-label="Remove condition" onclick={() => removeCondition(i)}>✕</button>
            </div>
          {/each}
        </div>

        <div class="etd-preview">
          <strong>Condition Preview</strong>
          <p>{conditionPreview}</p>
        </div>

        <div class="etd-log">
          <strong>Email Automation Log</strong>
          <p>[deferred] Per-category send history (latest 10) will appear here once Outlook COM logging is wired. Drafts remain visible in Outlook.</p>
        </div>
      </section>
    </div>

    <footer class="etd-foot">
      {#if saveState === "success"}
        <span class="etd-saved" role="status">✓ Saved</span>
      {:else if saveState === "error"}
        <span class="etd-savefail" role="alert">✗ {saveError}</span>
      {/if}
      <button class="etd-btn" type="button" onclick={onClose}>Cancel</button>
      <button
        class="etd-btn etd-btn-primary"
        type="button"
        onclick={save}
        disabled={loadState !== "loaded" || saveState === "saving"}
      >
        {saveState === "saving" ? "Saving…" : "Save"}
      </button>
    </footer>
  </div>
</div>

<style>
  .etd-backdrop { position:fixed; inset:0; background:rgba(0,0,0,0.45); display:flex; align-items:center; justify-content:center; z-index:60; padding:20px; }
  .etd-backdrop-close { position:absolute; inset:0; width:100%; height:100%; margin:0; padding:0; border:0; background:transparent; cursor:default; z-index:0; }
  .etd-dialog { position:relative; z-index:1; background:#fff; border:1px solid #D7DCE2; border-radius:10px; box-shadow:0 18px 50px rgba(0,0,0,0.35); width:min(960px,100%); max-height:92vh; display:flex; flex-direction:column; overflow:hidden; }
  .etd-head { display:flex; align-items:flex-start; justify-content:space-between; padding:14px 16px; border-bottom:1px solid #E5E7EB; background:var(--color-dbs-red); color:#fff; }
  .etd-kicker { display:block; font-size:9px; font-weight:850; letter-spacing:0.4px; text-transform:uppercase; opacity:0.85; }
  .etd-title { margin:2px 0 0; font-size:16px; font-weight:900; font-family:monospace; letter-spacing:0.5px; }
  .etd-x { background:transparent; border:0; color:#fff; font-size:15px; font-weight:900; cursor:pointer; line-height:1; padding:2px 6px; border-radius:4px; }
  .etd-x:hover { background:rgba(255,255,255,0.2); }
  .etd-banner { margin:10px 16px 0; padding:7px 10px; border-radius:6px; font-size:11px; font-weight:800; }
  .etd-banner-info { background:#f3f4f6; border:1px solid #D7DCE2; color:var(--color-muted); }
  .etd-banner-warn { background:var(--color-soft-pink-surface); border:1px solid var(--color-soft-pink-border); color:var(--color-dbs-red); }
  .etd-body { display:grid; grid-template-columns:1fr 1fr; gap:14px; padding:14px 16px; overflow-y:auto; min-height:0; }
  .etd-col { display:flex; flex-direction:column; gap:10px; min-width:0; }
  .etd-field { display:flex; flex-direction:column; gap:4px; font-size:11px; font-weight:800; color:var(--color-ink); }
  .etd-row2 { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
  .etd-input { height:28px; border:1px solid var(--color-input-border); border-radius:5px; background:#fff; color:var(--color-ink); font-weight:750; font-size:11px; outline:none; padding:0 8px; width:100%; font-family:inherit; }
  .etd-input:focus { border:2px solid var(--color-dbs-red); }
  .etd-input[readonly] { background:#f3f4f6; color:var(--color-muted); font-family:monospace; font-weight:900; }
  .etd-textarea { border:1px solid var(--color-input-border); border-radius:5px; background:#fff; color:var(--color-ink); font-weight:700; font-size:11px; outline:none; padding:8px; width:100%; font-family:inherit; resize:vertical; line-height:1.45; }
  .etd-textarea:focus { border:2px solid var(--color-dbs-red); }
  .etd-hint { font-size:9px; font-weight:700; color:var(--color-muted); }
  .etd-chips { display:flex; flex-wrap:wrap; gap:5px; align-items:center; }
  .etd-chips-label { font-size:9px; font-weight:850; color:var(--color-muted); text-transform:uppercase; letter-spacing:0.3px; }
  .etd-chip { font-family:monospace; font-size:9px; font-weight:800; padding:3px 6px; border:1px solid #D7DCE2; border-radius:4px; background:var(--color-workspace-panel); color:var(--color-ink); cursor:pointer; }
  .etd-chip:hover { border-color:var(--color-dbs-red); color:var(--color-dbs-red); }
  .etd-subhead { display:flex; align-items:center; justify-content:space-between; gap:8px; }
  .etd-subhead h3 { margin:0; font-size:12px; font-weight:900; color:var(--color-ink); }
  .etd-conditions { display:flex; flex-direction:column; gap:6px; }
  .etd-empty { font-size:10px; font-weight:700; color:var(--color-muted); padding:6px 0; }
  .etd-cond-row { display:grid; grid-template-columns:1.1fr 1fr 1.1fr auto; gap:5px; align-items:center; }
  .etd-cond-del { background:transparent; border:1px solid #D7DCE2; border-radius:4px; color:var(--color-muted); font-weight:900; font-size:10px; cursor:pointer; height:28px; width:28px; }
  .etd-cond-del:hover { border-color:var(--color-dbs-red); color:var(--color-dbs-red); }
  .etd-preview, .etd-log { background:var(--color-workspace-panel); border:1px solid #E5E7EB; border-radius:6px; padding:8px; font-size:10px; font-weight:700; color:var(--color-muted); }
  .etd-preview strong, .etd-log strong { display:block; margin-bottom:4px; color:var(--color-ink); }
  .etd-preview p { margin:0; font-family:monospace; color:var(--color-ink); word-break:break-word; }
  .etd-foot { display:flex; align-items:center; justify-content:flex-end; gap:8px; padding:12px 16px; border-top:1px solid #E5E7EB; }
  .etd-btn { height:30px; padding:0 16px; border:1px solid #D7DCE2; border-radius:5px; background:#fff; color:var(--color-ink); font-size:11px; font-weight:850; cursor:pointer; }
  .etd-btn:hover:not(:disabled) { border-color:var(--color-dbs-red); color:var(--color-dbs-red); }
  .etd-btn:disabled { opacity:0.55; cursor:not-allowed; }
  .etd-btn-primary { background:var(--color-dbs-red); border-color:var(--color-dbs-red-hover); color:#fff; }
  .etd-btn-primary:hover:not(:disabled) { background:var(--color-dbs-red-hover); color:#fff; }
  .etd-saved { color:#15803D; font-size:11px; font-weight:850; margin-right:auto; }
  .etd-savefail { color:var(--color-dbs-red); font-size:11px; font-weight:850; margin-right:auto; }
  @media (max-width: 820px) {
    .etd-body { grid-template-columns:1fr; }
  }
</style>
