<script lang="ts">
  /**
   * Sub Project table — Fase 1 §3 + Polish. Presentational only.
   *
   * Renders one row per sub-project with: name (basename), Drone Ticket, and Drone State.
   * Clicking a row opens its folder directly.
   *
   * Columns: Sub Project | Drone Ticket | Drone State (matches Dashboard parity).
   */
  import type { DroneTicket } from "../types";

  interface Props {
    subprojects: string[];
    droneTickets: DroneTicket[];
    selectedRow: string | null;
    droneStateBusyName: string | null;
    droneStateErrorName: Record<string, string>;
    onSelectRow: (name: string) => void;
    onChangeDroneState: (name: string, nextState: string) => void;
    onOpenFolder: (name: string) => void;
    legalDroneOptionsFor: (droneState: string) => string[];
  }
  let {
    subprojects,
    droneTickets,
    selectedRow,
    droneStateBusyName,
    droneStateErrorName,
    onSelectRow,
    onChangeDroneState,
    onOpenFolder,
    legalDroneOptionsFor,
  }: Props = $props();

  interface Row {
    name: string;
    droneLink: string;
    droneState: string;
  }

  const rows = $derived<Row[]>(
    subprojects.map((name) => {
      const drone = droneTickets.find((t) => (t.subfolder_name ?? "") === name);
      return {
        name,
        droneLink: drone?.drone_link ?? "",
        droneState: drone?.drone_state ?? "",
      };
    }),
  );
</script>

<div class="sp-root">
  {#if subprojects.length === 0}
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
          style="cursor:pointer;"
        >
          <span class="sp-name" title={row.name}>{row.name}</span>
          <span class="sp-link" title={row.droneLink}>{row.droneLink || "—"}</span>
          <span class="sp-state" onclick={(e) => e.stopPropagation()}>
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
  .sp-link { font-family: monospace; color: var(--color-dbs-red); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .sp-state { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; min-width: 0; }
  .sp-state-select { min-height: 22px; max-width: 100%; padding: 0 6px; border: 1px solid rgba(45,61,52,.35); border-radius: 6px; background: var(--primary-red); color: #fff; font-weight: 900; font-size: 9.5px; cursor: pointer; }
  .sp-state-select:hover { background: var(--red-hover); }
  .sp-state-select:disabled { opacity: 0.55; cursor: not-allowed; }
  .sp-muted { color: var(--color-muted); }
  .sp-err { color: var(--color-dbs-red); font-size: 9px; }
</style>
