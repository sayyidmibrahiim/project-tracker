<script lang="ts">
  import { onMount } from "svelte";
  import { callBridge, isPywebviewReady } from "../bridge";
  import ApprovalTemplates from "./ApprovalTemplates.svelte";

  type Feedback = { kind: "none" } | { kind: "notice"; text: string } | { kind: "error"; text: string };
  const sendCategories = [
    { kind: "uat" as const, label: "Email Ack (UAT)", purpose: "UAT approval request", conditions: "Drone PENDING APPROVAL + CR PENDING SUBMISSION" },
    { kind: "lv" as const, label: "Email LV (Prod)", purpose: "LV / prod approval request", conditions: "CR APPROVED or Drone APPROVED" },
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
  let editingKind: "uat" | "lv" | null = $state(null);
  let defaultEnabled: boolean = $state(false);

  function openTemplate(kind: "uat" | "lv") { feedback = { kind: "none" }; editingKind = kind; }
  function closeTemplate() { editingKind = null; }
  function onDialogKey(event: KeyboardEvent) { if (editingKind !== null && event.key === "Escape") closeTemplate(); }

  async function loadDefaultEnabled() {
    if (!isPywebviewReady()) return;
    const resp = await callBridge<{ automation_default_enabled?: boolean }>("settings_get");
    if (resp.ok) defaultEnabled = Boolean(resp.data?.automation_default_enabled);
  }

  async function toggleDefaultEnabled() {
    const resp = await callBridge("settings_update", { automation_default_enabled: !defaultEnabled });
    if (!resp.ok) { feedback = { kind: "error", text: resp.error.message }; return; }
    await loadDefaultEnabled();
    feedback = { kind: "notice", text: `CR automation default is now ${defaultEnabled ? "ON" : "OFF"} for projects without an explicit toggle.` };
  }

  onMount(() => { loadDefaultEnabled(); });

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

<svelte:window onkeydown={onDialogKey} />

<div class="automation-outlook">
  <div class="metric-row">
    {#each kpis as kpi}
      <div class="metric-card"><div class="metric-icon">▣</div><div><div class="metric-value">{kpi.value}</div><div class="metric-label">{kpi.label}</div><div class="metric-helper">Outlook automation</div></div></div>
    {/each}
  </div>

  <div class="splitter">
    <div class="pane">
      <section class="panel-card accent" aria-label="Send automation">
        <div class="panel-title-row"><span class="panel-title-icon">✉</span><span class="panel-title">SEND AUTOMATION</span><span class="panel-subtitle">draft-first templates</span><button class="btn-secondary" type="button" title="Projects without an explicit toggle inherit this" onclick={toggleDefaultEnabled}>New-CR automation default: {defaultEnabled ? "ON" : "OFF"}</button></div>
        <table class="mini-table" aria-label="Outlook send categories"><thead><tr><th>Category</th><th>Purpose</th><th>Conditions</th><th>Action</th></tr></thead><tbody>{#each sendCategories as row}<tr><td>{row.label}</td><td>{row.purpose}</td><td>{row.conditions}</td><td><button class="btn-tiny" type="button" onclick={() => openTemplate(row.kind)}>Edit Template</button></td></tr>{/each}</tbody></table>
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
  {#if editingKind !== null}
    <div class="apt-backdrop">
      <button class="apt-backdrop-close" type="button" aria-label="Close dialog" onclick={closeTemplate}></button>
      <div class="apt-dialog" role="dialog" aria-modal="true" tabindex="-1" aria-label={`Approval template for ${editingKind === "uat" ? "Email Ack (UAT)" : "Email LV (Prod)"}`}>
        <header class="apt-head">
          <div>
            <span class="apt-kicker">Approval Template</span>
            <h2 class="apt-title">{editingKind === "uat" ? "Email Ack (UAT)" : "Email LV (Prod)"}</h2>
          </div>
          <button class="apt-x" type="button" aria-label="Close" onclick={closeTemplate}>✕</button>
        </header>
        <div class="apt-dialog-body">
          <ApprovalTemplates initialKind={editingKind} />
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .automation-outlook { display:flex; flex-direction:column; gap:10px; min-height:0; }
  .panel-title-row .btn-secondary { margin-left:auto; }
  .list-row { padding:8px 10px; font-size:10px; }
  .list-row p { margin:4px 0 0; color:var(--color-muted); }
  .safety-line { margin:0; color:var(--color-muted); font-size:10px; font-weight:800; }
  .apt-backdrop { position:fixed; inset:0; background:rgba(0,0,0,0.45); display:flex; align-items:center; justify-content:center; z-index:60; padding:20px; }
  .apt-backdrop-close { position:absolute; inset:0; width:100%; height:100%; margin:0; padding:0; border:0; background:transparent; cursor:default; z-index:0; }
  .apt-dialog { position:relative; z-index:1; background:#fff; border:1px solid #D7DCE2; border-radius:10px; box-shadow:0 18px 50px rgba(0,0,0,0.35); width:min(720px,100%); max-height:92vh; display:flex; flex-direction:column; overflow:hidden; }
  .apt-head { display:flex; align-items:flex-start; justify-content:space-between; padding:14px 16px; border-bottom:1px solid #E5E7EB; background:var(--color-dbs-red); color:#fff; }
  .apt-kicker { display:block; font-size:9px; font-weight:850; letter-spacing:0.4px; text-transform:uppercase; opacity:0.85; }
  .apt-title { margin:2px 0 0; font-size:16px; font-weight:900; letter-spacing:0.5px; }
  .apt-x { background:transparent; border:0; color:#fff; font-size:15px; font-weight:900; cursor:pointer; line-height:1; padding:2px 6px; border-radius:4px; }
  .apt-x:hover { background:rgba(255,255,255,0.2); }
  .apt-dialog-body { padding:14px 16px; overflow-y:auto; min-height:0; }
</style>
