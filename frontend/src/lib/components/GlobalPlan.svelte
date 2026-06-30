<script lang="ts">
  import { onMount } from "svelte";
  import { globalPlanGet, globalPlanSave, isPywebviewReady, waitForPywebviewReady } from "../bridge";
  import type { GlobalPlan, GlobalPlanItem, GlobalPlanStatus } from "../types";

  const columns: { id: GlobalPlanStatus; label: string; helper: string }[] = [
    { id: "doing", label: "Now", helper: "One active goal" },
    { id: "ready", label: "Next", helper: "Ready branch work" },
    { id: "backlog", label: "Backlog", helper: "Future work" },
    { id: "review", label: "Review", helper: "Needs user approval" },
    { id: "done", label: "Done", helper: "Approved" },
  ];

  let plan: GlobalPlan | null = $state(null);
  let loadState: "idle" | "loading" | "error" | "loaded" = $state("idle");
  let errorMessage = $state("");
  let savingId = $state("");
  let saveMessage = $state("");
  let draggingId = $state("");
  let dragOverStatus: GlobalPlanStatus | "" = $state("");
  let dragOverItemId = $state("");

  function countStatus(status: GlobalPlanStatus): number {
    return plan?.items.filter((item: GlobalPlanItem) => item.status === status).length ?? 0;
  }

  function currentItem(): GlobalPlanItem | null {
    return plan?.items.find((item: GlobalPlanItem) => item.status === "doing") ?? null;
  }

  onMount(loadPlan);

  async function loadPlan() {
    loadState = "loading";
    errorMessage = "";
    await waitForPywebviewReady();
    if (!isPywebviewReady()) {
      loadState = "error";
      errorMessage = "Desktop bridge unavailable.";
      return;
    }
    const response = await globalPlanGet();
    if (!response.ok || !response.data) {
      loadState = "error";
      errorMessage = response.error?.message ?? "Global plan unavailable.";
      return;
    }
    plan = response.data;
    loadState = "loaded";
  }

  function byStatus(status: GlobalPlanStatus): GlobalPlanItem[] {
    return plan?.items.filter((item) => item.status === status) ?? [];
  }

  async function savePlan(nextPlan: GlobalPlan, itemId: string) {
    savingId = itemId;
    saveMessage = "";
    const response = await globalPlanSave(nextPlan);
    savingId = "";
    if (!response.ok || !response.data) {
      saveMessage = response.error?.message ?? "Save failed.";
      return;
    }
    plan = response.data;
    saveMessage = "Saved";
    setTimeout(() => { saveMessage = ""; }, 1200);
  }

  async function setStatus(item: GlobalPlanItem, status: GlobalPlanStatus) {
    if (!plan || item.status === status || savingId) return;
    const nextPlan: GlobalPlan = {
      ...plan,
      items: plan.items.map((candidate) => candidate.id === item.id ? { ...candidate, status, updated_at: new Date().toISOString().slice(0, 10) } : candidate),
    };
    await savePlan(nextPlan, item.id);
  }

  function onDragStart(event: DragEvent, item: GlobalPlanItem) {
    if (savingId) return;
    draggingId = item.id;
    event.dataTransfer?.setData("text/plain", item.id);
    if (event.dataTransfer) event.dataTransfer.effectAllowed = "move";
  }

  function onDragOver(event: DragEvent, status: GlobalPlanStatus, beforeId = "") {
    if (!draggingId || savingId) return;
    event.preventDefault();
    dragOverStatus = status;
    dragOverItemId = beforeId;
    if (event.dataTransfer) event.dataTransfer.dropEffect = "move";
  }

  function onDragEnd() {
    draggingId = "";
    dragOverStatus = "";
    dragOverItemId = "";
  }

  async function onDrop(event: DragEvent, targetStatus: GlobalPlanStatus, beforeId = "") {
    event.preventDefault();
    if (!plan || savingId) return;
    const itemId = event.dataTransfer?.getData("text/plain") || draggingId;
    onDragEnd();
    if (!itemId) return;
    const dragged = plan.items.find((item) => item.id === itemId);
    if (!dragged) return;
    const remaining = plan.items.filter((item) => item.id !== itemId);
    const moved = { ...dragged, status: targetStatus, updated_at: new Date().toISOString().slice(0, 10) };
    const targetIndex = beforeId ? remaining.findIndex((item) => item.id === beforeId) : -1;
    const items = [...remaining];
    if (targetIndex >= 0) items.splice(targetIndex, 0, moved);
    else items.push(moved);
    await savePlan({ ...plan, items }, itemId);
  }
</script>

<section class="screen active global-plan-screen" id="screen-global-plan">
  <div class="page-header">
    <div class="page-header-left">
      <span class="page-header-icon"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg></span>
      <h2 class="page-header-title">Global Plan</h2>
    </div>
    <div class="page-header-actions">
      <button class="btn-secondary" type="button" onclick={loadPlan}>Refresh</button>
      {#if saveMessage}<span class="gp-save-msg">{saveMessage}</span>{/if}
    </div>
  </div>

  {#if loadState === "loading" || loadState === "idle"}
    <div class="panel-card gp-empty">Loading global plan…</div>
  {:else if loadState === "error"}
    <div class="panel-card gp-empty gp-error">{errorMessage}</div>
  {:else if plan}
    <div class="metric-row gp-metrics">
      {#each columns as column}
        <div class="metric-card">
          <div class="metric-icon">{countStatus(column.id)}</div>
          <div><div class="metric-value">{column.label}</div><div class="metric-label">{column.id}</div><div class="metric-helper">{column.helper}</div></div>
        </div>
      {/each}
    </div>

    <div class="gp-loop panel-card">
      <div class="panel-title-row"><span class="panel-title-icon">↻</span><span class="panel-title">AI Loop Status</span><span class="panel-subtitle">branch → graphify → verify → review</span></div>
      <div class="gp-loop-grid">
        <div><span>Current branch</span><strong>{currentItem() ? `${currentItem()!.menu}/${currentItem()!.branch_desc}` : "none"}</strong></div>
        {#each plan.loop_rule as rule, index}<div><span>{index + 1}</span><strong>{rule}</strong></div>{/each}
      </div>
    </div>

    <div class="gp-board">
      {#each columns as column}
        <div class="panel-card gp-column" class:drag-over={dragOverStatus === column.id && !dragOverItemId}>
          <div class="panel-title-row"><span class="panel-title-icon">■</span><span class="panel-title">{column.label}</span><span class="panel-subtitle">{byStatus(column.id).length}</span></div>
          <div class="gp-list" role="list" ondragover={(event) => onDragOver(event, column.id)} ondrop={(event) => onDrop(event, column.id)}>
            {#each byStatus(column.id) as item}
              <article class="gp-card" class:dragging={draggingId === item.id} class:drop-before={dragOverItemId === item.id} draggable={!savingId} ondragstart={(event) => onDragStart(event, item)} ondragover={(event) => onDragOver(event, column.id, item.id)} ondrop={(event) => onDrop(event, column.id, item.id)} ondragend={onDragEnd}>
                <div class="gp-card-head"><strong>{item.title}</strong><span>{item.menu}/{item.branch_desc}</span></div>
                <p>{item.goal}</p>
                {#if item.acceptance_checks.length}
                  <ul>{#each item.acceptance_checks as check}<li>{check}</li>{/each}</ul>
                {/if}
                {#if item.blocked_reason}<div class="gp-blocked">Blocked: {item.blocked_reason}</div>{/if}
                {#if item.notes}<div class="gp-notes">{item.notes}</div>{/if}
                <div class="gp-actions">
                  {#each columns as target}
                    <button class="sb-tab" class:active={item.status === target.id} disabled={savingId === item.id} onclick={() => setStatus(item, target.id)}>{target.id}</button>
                  {/each}
                </div>
              </article>
            {:else}
              <div class="gp-placeholder">Drop {column.id} items here</div>
            {/each}
          </div>
        </div>
      {/each}
    </div>
  {/if}
</section>

<style>
  .global-plan-screen { overflow: hidden; }
  .gp-save-msg { color: var(--text-strong); font-weight: 900; }
  .gp-empty { flex: 1; align-items: center; justify-content: center; color: var(--text-secondary); font-weight: 900; }
  .gp-error { color: var(--primary-red); }
  .gp-metrics { grid-template-columns: repeat(5, minmax(120px, 1fr)); }
  .gp-loop { flex: 0 0 auto; }
  .gp-loop-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
  .gp-loop-grid div { background: var(--main-panel-bg); border: 1px solid var(--soft-white-border); border-radius: 6px; padding: 8px; min-width: 0; }
  .gp-loop-grid span { display: block; color: var(--text-secondary); font-weight: 850; margin-bottom: 3px; }
  .gp-loop-grid strong { display: block; color: var(--text-strong); font-weight: 900; line-height: 1.25; }
  .gp-board { flex: 1; min-height: 0; display: grid; grid-template-columns: repeat(5, minmax(180px, 1fr)); gap: 10px; overflow: hidden; }
  .gp-column { padding: 10px; transition: border-color .16s ease, background .16s ease; }
  .gp-column.drag-over { border-color: var(--primary-red); background: var(--soft-pink-surface); }
  .gp-list { flex: 1; min-height: 0; overflow: auto; display: flex; flex-direction: column; gap: 8px; }
  .gp-card { background: var(--main-panel-bg); border: 1px solid var(--soft-white-border); border-radius: 7px; padding: 9px; display: flex; flex-direction: column; gap: 7px; cursor: grab; transition: opacity .16s ease, border-color .16s ease, transform .16s ease; }
  .gp-card:active { cursor: grabbing; }
  .gp-card.dragging { opacity: .45; }
  .gp-card.drop-before { border-top: 3px solid var(--primary-red); }
  .gp-card-head { display: flex; flex-direction: column; gap: 2px; }
  .gp-card-head strong { color: var(--text-strong); font-weight: 900; font-size: 12px; }
  .gp-card-head span, .gp-card p, .gp-notes, .gp-placeholder { color: var(--text-secondary); font-weight: 750; margin: 0; line-height: 1.35; }
  .gp-card ul { margin: 0; padding-left: 16px; color: var(--text-primary); font-weight: 750; line-height: 1.35; }
  .gp-blocked { color: var(--primary-red); font-weight: 900; }
  .gp-actions { display: flex; flex-wrap: wrap; gap: 4px; }
  .gp-actions .sb-tab { height: 22px; padding: 0 6px; font-size: 10px; }
  @media (max-width: 1180px) { .gp-board { grid-template-columns: repeat(3, minmax(180px, 1fr)); } .gp-metrics { grid-template-columns: repeat(3, minmax(120px, 1fr)); } }
</style>
