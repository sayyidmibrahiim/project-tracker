<script lang="ts">
  /**
   * Sub Project table — Fase 1 §3. Presentational only.
   *
   * Renders one row per sub-project with: name (basename), Drone State dropdown,
   * and an Open Folder action. All bridge interactions are emitted as callbacks
   * to the parent (ProjectDetails), which owns bridge state.
   *
   * The owner column was removed in Fase 1 §3.3 (the model field stays — backend-compat).
   * Drone URL editing happens in the parent's master-detail panel, triggered by
   * row selection (onSelectRow).
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
    droneState: string;
  }

  const rows = $derived<Row[]>(
    subprojects.map((name) => {
      const drone = droneTickets.find((t) => (t.subfolder_name ?? "") === name);
      return { name, droneState: drone?.drone_state ?? "" };
    }),
  );
</script>

<div class="sp-root">
  {#if subprojects.length === 0}
    <div class="sp-empty">No sub projects yet. Add one above.</div>
  {:else}
    <div class="sp-table" role="table" aria-label="Sub projects">
      <div class="sp-tr sp-th" role="row">
        <span>Sub Project</span><span>Drone State</span><span>Actions</span>
      </div>
      {#each rows as row (row.name)}
        <div class="sp-tr" role="row" class:sp-selected={selectedRow === row.name}>
          <button type="button" class="sp-name-btn" onclick={() => onSelectRow(row.name)} aria-label={`Select ${row.name}`} title={row.name}>
            <span class="sp-name">{row.name}</span>
          </button>
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
          <span class="sp-actions">
            <button class="sp-btn" type="button" onclick={() => onOpenFolder(row.name)}>Open Folder</button>
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
  .sp-tr { display: grid; grid-template-columns: 1fr 1.1fr auto; gap: 8px; align-items: center; padding: 7px 8px; border-top: 1px solid #E5E7EB; font-size: 10px; font-weight: 750; color: var(--color-ink); }
  .sp-tr:first-child { border-top: 0; }
  .sp-tr.sp-selected { background: var(--color-soft-pink-surface); }
  .sp-th { background: #111; color: #fff; font-size: 9px; font-weight: 900; text-transform: uppercase; letter-spacing: 0.3px; }
  .sp-name-btn { background: transparent; border: 0; padding: 0; text-align: left; cursor: pointer; min-width: 0; display: flex; }
  .sp-name { font-weight: 900; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--color-ink); }
  .sp-name-btn:hover .sp-name { color: var(--color-dbs-red); }
  .sp-state { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; min-width: 0; }
  .sp-state-select { min-height: 22px; max-width: 100%; padding: 0 6px; border: 1px solid rgba(45,61,52,.35); border-radius: 6px; background: var(--primary-red); color: #fff; font-weight: 900; font-size: 9.5px; cursor: pointer; }
  .sp-state-select:hover { background: var(--red-hover); }
  .sp-state-select:disabled { opacity: 0.55; cursor: not-allowed; }
  .sp-muted { color: var(--color-muted); }
  .sp-err { color: var(--color-dbs-red); font-size: 9px; }
  .sp-actions { display: flex; justify-content: flex-end; }
  .sp-btn { padding: 4px 9px; border: 1px solid #D7DCE2; border-radius: 5px; background: #fff; color: var(--color-ink); font-size: 9px; font-weight: 850; cursor: pointer; white-space: nowrap; }
  .sp-btn:hover { border-color: var(--color-dbs-red); color: var(--color-dbs-red); }
</style>
