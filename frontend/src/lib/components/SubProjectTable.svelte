<script lang="ts">
  /**
   * Sub Project table — PRD §12.10.
   *
   * Displays each sub-project mapped to its drone ticket (matched by
   * `subfolder_name`): Sub Project | Drone Ticket | Drone State | Owner |
   * Actions. The only action here is Open Folder (via the existing `folder_open`
   * bridge — Windows-guarded; dev-skipped off Windows). Sub-project create/delete
   * and drone-state editing remain in their dedicated, tested surfaces
   * (ProjectActions and the Drone Tickets card) to avoid duplicating destructive
   * flows. No new bridge contract is introduced.
   */
  import { callBridge, isPywebviewReady } from "../bridge";
  import type { DroneTicket } from "../types";

  interface Props {
    projectPath: string;
    subprojects: string[];
    droneTickets: DroneTicket[];
  }
  let { projectPath, subprojects, droneTickets }: Props = $props();

  interface Row {
    name: string;
    droneLink: string;
    droneState: string;
    owner: string;
  }

  const rows = $derived<Row[]>(
    subprojects.map((name) => {
      const drone = droneTickets.find((t) => (t.subfolder_name ?? "") === name);
      return {
        name,
        droneLink: drone?.drone_link ?? "",
        droneState: drone?.drone_state ?? "",
        owner: drone?.owner ?? "",
      };
    }),
  );

  let busyName = $state("");
  let feedback = $state("");

  function joinPath(base: string, child: string): string {
    const sep = base.includes("\\") ? "\\" : "/";
    return base.endsWith(sep) ? base + child : base + sep + child;
  }

  async function openFolder(name: string) {
    feedback = "";
    if (!isPywebviewReady()) {
      feedback = "Open Folder requires the desktop app (browser preview is read-only).";
      return;
    }
    busyName = name;
    const resp = await callBridge("folder_open", joinPath(projectPath, name));
    busyName = "";
    if (!resp.ok) feedback = resp.error.message;
  }
</script>

<div class="sp-root">
  {#if subprojects.length === 0}
    <div class="sp-empty">No sub projects. Add one from Project Actions, then map a drone ticket via its Subfolder field.</div>
  {:else}
    <div class="sp-table" role="table" aria-label="Sub projects">
      <div class="sp-tr sp-th" role="row">
        <span>Sub Project</span><span>Drone Ticket</span><span>Drone State</span><span>Owner</span><span>Actions</span>
      </div>
      {#each rows as row (row.name)}
        <div class="sp-tr" role="row">
          <span class="sp-name">{row.name}</span>
          <span class="sp-link" title={row.droneLink}>{row.droneLink || "—"}</span>
          <span class="sp-state">{row.droneState || "—"}</span>
          <span class="sp-owner">{row.owner || "—"}</span>
          <span class="sp-actions">
            <button class="sp-btn" type="button" onclick={() => openFolder(row.name)} disabled={busyName === row.name}>Open Folder</button>
          </span>
        </div>
      {/each}
    </div>
  {/if}

  {#if feedback}
    <p class="sp-feedback" role="status">⊘ {feedback}</p>
  {/if}
</div>

<style>
  .sp-root { display:flex; flex-direction:column; gap:6px; }
  .sp-empty { font-size:10px; font-weight:700; color:var(--color-muted); padding:8px; background:var(--color-workspace-panel); border:1px dashed #D7DCE2; border-radius:6px; }
  .sp-table { display:flex; flex-direction:column; border:1px solid #E5E7EB; border-radius:6px; overflow:hidden; }
  .sp-tr { display:grid; grid-template-columns:1fr 1.4fr 0.8fr 0.8fr auto; gap:8px; align-items:center; padding:7px 8px; border-top:1px solid #E5E7EB; font-size:10px; font-weight:750; color:var(--color-ink); }
  .sp-tr:first-child { border-top:0; }
  .sp-th { background:#111; color:#fff; font-size:9px; font-weight:900; text-transform:uppercase; letter-spacing:0.3px; }
  .sp-name { font-weight:900; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .sp-link { font-family:monospace; color:var(--color-dbs-red); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .sp-state { font-weight:850; }
  .sp-owner { color:var(--color-muted); }
  .sp-actions { display:flex; justify-content:flex-end; }
  .sp-btn { padding:4px 9px; border:1px solid #D7DCE2; border-radius:5px; background:#fff; color:var(--color-ink); font-size:9px; font-weight:850; cursor:pointer; white-space:nowrap; }
  .sp-btn:hover:not(:disabled) { border-color:var(--color-dbs-red); color:var(--color-dbs-red); }
  .sp-btn:disabled { opacity:0.5; cursor:not-allowed; }
  .sp-feedback { margin:0; font-size:10px; font-weight:800; color:var(--color-muted); }
</style>
