<script lang="ts">
  /**
   * Automations → Outlook workspace scaffold (PRD §16.3).
   *
   * Renders the two-column SEND / DOWNLOAD automation layout, the PRD metrics
   * row, send-category and download-job tables, and per-column logs. This is a
   * UI scaffold: the full Email Template Dialog and searchable Downloaded Emails
   * dialog are explicit next-slice deferrals (surfaced with honest reasons, not
   * hidden as done). Outlook COM execution is Windows-only and guarded — nothing
   * here claims a send/draft happened on Linux. The only live bridge call is the
   * real `outlook_download_emails` method, and only when the pywebview bridge is
   * present.
   */
  import { callBridge, isPywebviewReady } from "../bridge";
  import EmailTemplateDialog from "./EmailTemplateDialog.svelte";

  type Feedback =
    | { kind: "none" }
    | { kind: "notice"; text: string }
    | { kind: "error"; text: string };

  const sendCategories = [
    { code: "ACK_UAT", purpose: "UAT acknowledgment", conditions: "CR submitted" },
    { code: "ACK_SOP", purpose: "SOP acknowledgment", conditions: "CR submitted" },
    { code: "APRVL_CR", purpose: "CR approval request", conditions: "Ready for approval" },
    { code: "APRVL_SOP", purpose: "SOP approval request", conditions: "SOP ready" },
  ];

  const downloadJobs = [
    { category: "On Going ACK", details: "Monitor ACK replies" },
    { category: "On Going Tech LV", details: "Monitor technical lead approvals" },
  ];

  const kpis = [
    { label: "Send Categories", value: sendCategories.length },
    { label: "Download Jobs", value: downloadJobs.length },
    { label: "HTML Templates", value: 0 },
    { label: "On Going ACK", value: 0 },
    { label: "On Going Tech LV", value: 0 },
  ];

  let feedback: Feedback = $state({ kind: "none" });
  let busy: boolean = $state(false);
  let editingCategory: string | null = $state(null);

  function openTemplate(code: string) {
    feedback = { kind: "none" };
    editingCategory = code;
  }

  function closeTemplate() {
    editingCategory = null;
  }

  function onTemplateSaved(code: string) {
    feedback = { kind: "notice", text: `Saved Outlook template for ${code}.` };
  }

  function addCategoryDeferred() {
    feedback = {
      kind: "notice",
      text: "The four PRD send categories (ACK_UAT, ACK_SOP, APRVL_CR, APRVL_SOP) are fixed by the settings model; custom categories are not yet supported.",
    };
  }

  async function openDownloadedEmails() {
    feedback = { kind: "none" };
    if (!isPywebviewReady()) {
      feedback = {
        kind: "notice",
        text: "Downloaded Emails requires the pywebview bridge. Browser preview is read-only.",
      };
      return;
    }
    busy = true;
    const response = await callBridge<unknown>("outlook_download_emails");
    busy = false;
    if (!response.ok) {
      feedback = { kind: "error", text: response.error.message };
      return;
    }
    feedback = {
      kind: "notice",
      text: "Downloaded Emails bridge returned. Detailed searchable dialog is the next Outlook slice.",
    };
  }
</script>

<div class="ao-root">
  <div class="ao-kpis" aria-label="Outlook automation KPIs">
    {#each kpis as kpi}
      <div class="ao-kpi">
        <span class="ao-kpi-value">{kpi.value}</span>
        <span class="ao-kpi-label">{kpi.label}</span>
      </div>
    {/each}
  </div>

  <div class="ao-columns">
    <section class="ao-card" aria-label="Send automation">
      <div class="ao-card-head">
        <div>
          <h3>SEND AUTOMATION</h3>
          <p>Hint: select a category to configure its draft-first template.</p>
        </div>
        <button class="ao-btn ao-btn-primary" type="button" onclick={addCategoryDeferred}>+ Add Category</button>
      </div>

      <div class="ao-table" role="table" aria-label="Outlook send categories">
        <div class="ao-tr ao-th" role="row">
          <span>Category</span><span>Purpose</span><span>Conditions</span><span>Action</span>
        </div>
        {#each sendCategories as row}
          <div class="ao-tr" role="row">
            <span class="ao-code">{row.code}</span>
            <span>{row.purpose}</span>
            <span>{row.conditions}</span>
            <button class="ao-link" type="button" onclick={() => openTemplate(row.code)}>Edit Template</button>
          </div>
        {/each}
      </div>

      <div class="ao-log">
        <strong>Send Automation Log</strong>
        <p>[deferred] Template configuration is pending. Project Details keeps Draft email as the default safe action.</p>
      </div>
    </section>

    <section class="ao-card" aria-label="Download automation">
      <div class="ao-card-head">
        <div>
          <h3>DOWNLOAD AUTOMATION</h3>
          <p>Relation to Send categories. Windows Outlook COM remains guarded.</p>
        </div>
        <button class="ao-btn" type="button" onclick={openDownloadedEmails} disabled={busy}>Downloaded Emails ▶</button>
      </div>

      <div class="ao-table two" role="table" aria-label="Outlook download jobs">
        <div class="ao-tr ao-th" role="row"><span>Category</span><span>Details</span></div>
        {#each downloadJobs as row}
          <div class="ao-tr" role="row"><span class="ao-code">{row.category}</span><span>{row.details}</span></div>
        {/each}
      </div>

      <div class="ao-log">
        <strong>Download Tool Log</strong>
        <p>[deferred] Searchable Downloaded Emails dialog will list subject, sender, CR number, date, and category.</p>
      </div>
    </section>
  </div>

  <p class="ao-safety">Draft-first Outlook is the safe default. Send-immediately requires explicit confirmation and Windows Outlook COM.</p>

  {#if feedback.kind === "notice"}
    <div class="ao-feedback ao-notice" role="status">⊘ {feedback.text}</div>
  {:else if feedback.kind === "error"}
    <div class="ao-feedback ao-error" role="alert">⚠ {feedback.text}</div>
  {/if}

  {#if editingCategory !== null}
    <EmailTemplateDialog categoryCode={editingCategory} onClose={closeTemplate} onSaved={onTemplateSaved} />
  {/if}
</div>

<style>
  .ao-root { display:flex; flex-direction:column; gap:10px; min-height:0; }
  .ao-kpis { display:grid; grid-template-columns:repeat(5,minmax(110px,1fr)); gap:8px; }
  .ao-kpi { background:#fff; border:1px solid #E5E7EB; border-left:3px solid var(--color-dbs-red); border-radius:6px; padding:8px 10px; box-shadow:var(--shadow-subtle); }
  .ao-kpi-value { display:block; color:var(--color-dbs-red); font-size:20px; line-height:1; font-weight:900; }
  .ao-kpi-label { display:block; margin-top:4px; color:var(--color-muted); font-size:9px; font-weight:850; text-transform:uppercase; letter-spacing:0.25px; }
  .ao-columns { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:12px; min-height:0; }
  .ao-card { background:#fff; border:1px solid #D7DCE2; border-radius:8px; padding:12px; display:flex; flex-direction:column; gap:10px; min-width:0; }
  .ao-card-head { display:flex; align-items:flex-start; justify-content:space-between; gap:10px; }
  .ao-card h3 { margin:0; color:var(--color-ink); font-size:12px; font-weight:900; letter-spacing:0.2px; }
  .ao-card p { margin:3px 0 0; color:var(--color-muted); font-size:10px; font-weight:700; line-height:1.35; }
  .ao-table { display:flex; flex-direction:column; border:1px solid #E5E7EB; border-radius:6px; overflow:hidden; }
  .ao-tr { display:grid; grid-template-columns:0.8fr 1.2fr 1.2fr 0.8fr; gap:8px; align-items:center; padding:7px 8px; border-top:1px solid #E5E7EB; font-size:10px; font-weight:750; color:var(--color-ink); }
  .ao-table.two .ao-tr { grid-template-columns:1fr 1.5fr; }
  .ao-tr:first-child { border-top:0; }
  .ao-th { background:#111; color:#fff; font-size:9px; font-weight:900; text-transform:uppercase; letter-spacing:0.3px; }
  .ao-code { font-family:monospace; font-weight:900; }
  .ao-btn, .ao-link { padding:5px 10px; border:1px solid #D7DCE2; border-radius:5px; background:#fff; color:var(--color-ink); font-size:10px; font-weight:850; cursor:pointer; white-space:nowrap; }
  .ao-btn:hover:not(:disabled), .ao-link:hover:not(:disabled) { border-color:var(--color-dbs-red); color:var(--color-dbs-red); }
  .ao-btn:disabled { opacity:0.55; cursor:not-allowed; }
  .ao-btn-primary { background:var(--color-dbs-red); border-color:var(--color-dbs-red); color:#fff; }
  .ao-btn-primary:hover:not(:disabled) { color:#fff; }
  .ao-log { min-height:70px; background:var(--color-workspace-panel); border:1px solid #E5E7EB; border-radius:6px; padding:8px; color:var(--color-muted); font-size:10px; font-weight:700; }
  .ao-log strong { color:var(--color-ink); display:block; margin-bottom:4px; }
  .ao-safety { margin:0; color:var(--color-muted); font-size:10px; font-weight:800; }
  .ao-feedback { padding:7px 10px; border-radius:6px; font-size:10px; font-weight:850; }
  .ao-notice { background:#f3f4f6; border:1px solid #D7DCE2; color:var(--color-muted); }
  .ao-error { background:var(--color-soft-pink-surface); border:1px solid var(--color-soft-pink-border); color:var(--color-dbs-red); }
  @media (max-width: 980px) {
    .ao-kpis { grid-template-columns:repeat(2,minmax(120px,1fr)); }
    .ao-columns { grid-template-columns:1fr; }
  }
</style>
