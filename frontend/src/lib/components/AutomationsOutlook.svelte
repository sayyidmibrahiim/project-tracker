<script lang="ts">
  import { callBridge, isPywebviewReady } from "../bridge";
  import EmailTemplateDialog from "./EmailTemplateDialog.svelte";

  type Feedback = { kind: "none" } | { kind: "notice"; text: string } | { kind: "error"; text: string };
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

  function openTemplate(code: string) { feedback = { kind: "none" }; editingCategory = code; }
  function closeTemplate() { editingCategory = null; }
  function onTemplateSaved(code: string) { feedback = { kind: "notice", text: `Saved Outlook template for ${code}.` }; }
  function addCategoryDeferred() { feedback = { kind: "notice", text: "The four PRD send categories are fixed by settings model; custom categories are not yet supported." }; }

  async function openDownloadedEmails() {
    feedback = { kind: "none" };
    if (!isPywebviewReady()) {
      feedback = { kind: "notice", text: "Downloaded Emails requires the pywebview bridge. Browser preview is read-only." };
      return;
    }
    busy = true;
    const response = await callBridge<unknown>("outlook_download_emails");
    busy = false;
    feedback = response.ok ? { kind: "notice", text: "Downloaded Emails bridge returned. Detailed searchable dialog is the next Outlook slice." } : { kind: "error", text: response.error.message };
  }
</script>

<div class="automation-outlook">
  <div class="metric-row">
    {#each kpis as kpi}
      <div class="metric-card"><div class="metric-icon">▣</div><div><div class="metric-value">{kpi.value}</div><div class="metric-label">{kpi.label}</div><div class="metric-helper">Outlook automation</div></div></div>
    {/each}
  </div>

  <div class="splitter">
    <div class="pane">
      <section class="panel-card accent" aria-label="Send automation">
        <div class="panel-title-row"><span class="panel-title-icon">✉</span><span class="panel-title">SEND AUTOMATION</span><span class="panel-subtitle">draft-first templates</span><button class="btn-primary" type="button" onclick={addCategoryDeferred}>+ Add Category</button></div>
        <table class="mini-table" aria-label="Outlook send categories"><thead><tr><th>Category</th><th>Purpose</th><th>Conditions</th><th>Action</th></tr></thead><tbody>{#each sendCategories as row}<tr><td>{row.code}</td><td>{row.purpose}</td><td>{row.conditions}</td><td><button class="btn-tiny" type="button" onclick={() => openTemplate(row.code)}>Edit Template</button></td></tr>{/each}</tbody></table>
        <div class="list-box"><div class="list-row"><strong>Send Automation Log</strong><p>[deferred] Template configuration pending. Draft email stays safe default.</p></div></div>
      </section>
    </div>
    <div class="split-handle"></div>
    <div class="pane">
      <section class="panel-card accent" aria-label="Download automation">
        <div class="panel-title-row"><span class="panel-title-icon">⇩</span><span class="panel-title">DOWNLOAD AUTOMATION</span><span class="panel-subtitle">Outlook COM guarded</span><button class="btn-secondary" type="button" onclick={openDownloadedEmails} disabled={busy}>Downloaded Emails ▶</button></div>
        <table class="mini-table" aria-label="Outlook download jobs"><thead><tr><th>Category</th><th>Details</th></tr></thead><tbody>{#each downloadJobs as row}<tr><td>{row.category}</td><td>{row.details}</td></tr>{/each}</tbody></table>
        <div class="list-box"><div class="list-row"><strong>Download Tool Log</strong><p>[deferred] Searchable Downloaded Emails dialog will list subject, sender, CR number, date, category.</p></div></div>
      </section>
    </div>
  </div>

  <p class="safety-line">Draft-first Outlook is the safe default. Send-immediately requires explicit confirmation and Windows Outlook COM.</p>
  {#if feedback.kind === "notice"}<div class="dashboard-banner banner-loading" role="status"><span class="banner-icon">⊘</span><span>{feedback.text}</span></div>{:else if feedback.kind === "error"}<div class="dashboard-banner banner-error" role="alert"><span class="banner-icon">⚠</span><span>{feedback.text}</span></div>{/if}
  {#if editingCategory !== null}<EmailTemplateDialog categoryCode={editingCategory} onClose={closeTemplate} onSaved={onTemplateSaved} />{/if}
</div>

<style>
  .automation-outlook { display:flex; flex-direction:column; gap:10px; min-height:0; }
  .panel-title-row .btn-primary, .panel-title-row .btn-secondary { margin-left:auto; }
  .list-row { padding:8px 10px; font-size:10px; }
  .list-row p { margin:4px 0 0; color:var(--color-muted); }
  .safety-line { margin:0; color:var(--color-muted); font-size:10px; font-weight:800; }
</style>
