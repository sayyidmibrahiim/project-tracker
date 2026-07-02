<script lang="ts">
  import type { DroneTicket } from "../types";

  interface Props {
    subprojects?: string[];
    drones?: string[];
    droneTickets: DroneTicket[];
    selectedRow: string | null;
    droneStateBusyName: string | null;
    droneStateErrorName: Record<string, string>;
    onSelectRow: (name: string) => void;
    onChangeDroneState: (name: string, nextState: string) => void;
    onOpenFolder: (name: string) => void;
    legalDroneOptionsFor: (droneState: string) => string[];
    onSaveDroneLink?: (name: string, link: string) => void;
  }
  let {
    subprojects,
    drones,
    droneTickets,
    selectedRow,
    droneStateBusyName,
    droneStateErrorName,
    onSelectRow,
    onChangeDroneState,
    onOpenFolder,
    legalDroneOptionsFor,
    onSaveDroneLink,
  }: Props = $props();

  interface Row {
    name: string;
    droneTicket: string;
    droneLink: string;
    droneState: string;
  }

  const droneNames = $derived(drones ?? subprojects ?? []);

  const rows = $derived<Row[]>(
    droneNames.map((name) => {
      const drone = droneTickets.find((t) => (t.subfolder_name ?? "") === name);
      return {
        name,
        droneTicket: drone?.drone_ticket ?? "",
        droneLink: drone?.drone_link ?? "",
        droneState: drone?.drone_state ?? "",
      };
    }),
  );

  let editingDrone: Record<string, boolean> = $state({});

  function escapeHtml(value: string): string {
    return value.replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char] ?? char);
  }

  async function copyRichLink(url: string, label: string) {
    const href = url.trim();
    if (!href) return;
    try {
      const html = `<a href="${escapeHtml(href)}">${escapeHtml(label || href)}</a>`;
      if (typeof navigator !== "undefined" && navigator.clipboard && "write" in navigator.clipboard && typeof ClipboardItem !== "undefined") {
        await navigator.clipboard.write([
          new ClipboardItem({
            "text/html": new Blob([html], { type: "text/html" }),
            "text/plain": new Blob([href], { type: "text/plain" }),
          }),
        ]);
        return;
      }
      if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(href);
        return;
      }
    } catch { /* ignore */ }
  }

  function handleSave(name: string, value: string) {
    editingDrone = {...editingDrone, [name]: false};
    if (onSaveDroneLink) onSaveDroneLink(name, value);
  }
</script>

<div class="sp-root">
  {#if droneNames.length === 0}
    <div class="sp-empty">No sub projects yet. Add one above.</div>
  {:else}
    <div class="sp-table" role="table" aria-label="Sub projects">
      <div class="sp-tr sp-th" role="row">
        <span>Sub Project</span><span>Drone Ticket</span><span>Drone State</span>
      </div>
      {#each rows as row (row.name)}
        <div
          class="sp-tr"
          role="row"
          class:sp-selected={selectedRow === row.name}
          onclick={() => onOpenFolder(row.name)}
          onkeydown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onOpenFolder(row.name); } }}
          tabindex="0"
          style="cursor:pointer;"
        >
          <span class="sp-name" title={row.name}>{row.name}</span>
          <span class="sp-link-cell">
            {#if row.droneLink && !editingDrone[row.name]}
              <span class="sp-link-label" title={row.droneLink}>{row.droneTicket || "Drone Link"}</span>
              <button class="sp-icon-btn" type="button" title="Copy Drone link" aria-label="Copy Drone link" onclick={(e) => { e.stopPropagation(); copyRichLink(row.droneLink, row.droneTicket || "Drone Link"); }}>
                <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path><rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect></svg>
              </button>
              <a class="sp-icon-btn" href={row.droneLink} target="_blank" rel="noopener noreferrer" title="Open Drone link" aria-label="Open Drone link" onclick={(e) => e.stopPropagation()}>
                <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
              </a>
              <button class="sp-icon-btn" type="button" title="Edit Drone link" aria-label="Edit Drone link" onclick={(e) => { e.stopPropagation(); editingDrone = {...editingDrone, [row.name]: true}; }}>
                <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 1 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>
              </button>
            {:else}
              <div class="sp-link-edit-wrap">
                <input
                  class="sp-link-input"
                  type="url"
                  value={row.droneLink}
                  placeholder="Paste drone URL…"
                  title={row.name}
                  onkeydown={(e) => { if (e.key === "Enter") (e.currentTarget as HTMLInputElement).blur(); }}
                  onblur={(e) => { e.stopPropagation(); handleSave(row.name, (e.currentTarget as HTMLInputElement).value); }}
                  onclick={(e) => e.stopPropagation()}
                />
              </div>
            {/if}
          </span>
          <span class="sp-state">
            {#if row.droneState}
              <select
                class="sp-state-select"
                value={row.droneState}
                onchange={(e) => onChangeDroneState(row.name, (e.currentTarget as HTMLSelectElement).value)}
                disabled={droneStateBusyName === row.name}
                aria-label={`Drone state for ${row.name}`}
              >
                {#each legalDroneOptionsFor(row.droneState) as opt}
                  <option value={opt} disabled={opt === "IN-PROGRESS"}>{opt}</option>
                {/each}
              </select>
            {:else}
              <span class="sp-muted">—</span>
            {/if}
            {#if droneStateErrorName[row.name]}
              <span class="sp-err" role="alert">✗ {droneStateErrorName[row.name]}</span>
            {/if}
          </span>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .sp-root { display: flex; flex-direction: column; gap: 6px; }
  .sp-empty { font-size: 10px; font-weight: 700; color: var(--color-muted); padding: 8px; background: var(--color-workspace-panel); border: 1px dashed #D7DCE2; border-radius: 6px; }
  .sp-table { display: flex; flex-direction: column; border: 1px solid #E5E7EB; border-radius: 6px; overflow: hidden; }
  .sp-tr { display: grid; grid-template-columns: 1.2fr 1.4fr 0.9fr; gap: 8px; align-items: center; padding: 7px 8px; border-top: 1px solid #E5E7EB; font-size: 10px; font-weight: 750; color: var(--color-ink); }
  .sp-tr:first-child { border-top: 0; }
  .sp-tr.sp-selected { background: var(--color-soft-pink-surface); }
  .sp-tr:hover:not(.sp-th) { background: var(--color-row-alt); }
  .sp-th { background: #111; color: #fff; font-size: 9px; font-weight: 900; text-transform: uppercase; letter-spacing: 0.3px; pointer-events: none; }
  .sp-name { font-weight: 900; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--color-ink); }
  .sp-link-cell { display:flex; align-items:center; gap:4px; min-width:0; overflow:hidden; }
  .sp-link-label { font-family:monospace; color:var(--color-dbs-red); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; flex:0 1 auto; max-width:100px; font-size:9.5px; font-weight:750; background:var(--color-soft-pink-surface); border:1px solid var(--color-soft-pink-border); border-radius:4px; padding:2px 5px; }
  .sp-icon-btn { flex:0 0 22px; width:22px; height:22px; padding:0; border:1px solid #E5E7EB; border-radius:5px; background:#fff; color:var(--color-ink); cursor:pointer; display:inline-flex; align-items:center; justify-content:center; text-decoration:none; transition:background .12s ease, color .12s ease, border-color .12s ease; }
  .sp-icon-btn:hover { background:var(--color-soft-pink-surface); border-color:var(--color-soft-pink-border); color:var(--color-dbs-red); }
  .sp-link-edit-wrap { flex:1; min-width:0; }
  .sp-link-input { width:100%; min-width:0; padding:4px 6px; font-size:10px; border:1px solid var(--color-border); border-radius:5px; background:var(--color-workspace-panel); color:var(--color-ink); outline:none; }
  .sp-link-input:focus { border-color:var(--color-dbs-red); }
  .sp-state { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; min-width: 0; }
  .sp-state-select { min-height: 22px; max-width: 100%; padding: 0 6px; border: 1px solid rgba(45,61,52,.35); border-radius: 6px; background: var(--primary-red); color: #fff; font-weight: 900; font-size: 9.5px; cursor: pointer; }
  .sp-state-select:hover { background: var(--red-hover); }
  .sp-state-select:disabled { opacity: 0.55; cursor: not-allowed; }
  .sp-muted { color: var(--color-muted); }
  .sp-err { color: var(--color-dbs-red); font-size: 9px; }
</style>
