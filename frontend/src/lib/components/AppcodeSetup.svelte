<script lang="ts">
  /**
   * AppcodeSetup — first-run popup requiring at least one appcode.
   *
   * Shown by the App shell when no appcodes are discovered in root_folder.
   * Calls the existing `appcode_add` bridge (which creates the full D-0008
   * worktree: appcode.json, CICD/, year/CR/{5 states}/Non-CR/).
   * [Done] is disabled until at least one appcode is saved.
   */
  import { callBridge, isPywebviewReady } from "../bridge";

  interface AppcodeInfo {
    name: string;
    path: string;
    display_name: string;
  }

  interface Props {
    onDone: () => void;
  }
  let { onDone }: Props = $props();

  let inputName = $state("");
  let saved: AppcodeInfo[] = $state([]);
  let busy = $state(false);
  let error = $state("");

  async function addAppcode() {
    const name = inputName.trim();
    if (!name) {
      error = "Appcode name is required.";
      return;
    }
    if (!isPywebviewReady()) {
      error = "The desktop app is required to create appcodes.";
      return;
    }
    busy = true;
    error = "";
    const r = await callBridge<AppcodeInfo>("appcode_add", name);
    busy = false;
    if (!r.ok) {
      error = r.error.message;
      return;
    }
    if (!r.data) {
      error = "Appcode creation returned no data.";
      return;
    }
    saved = [...saved, r.data];
    inputName = "";
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === "Enter" && !busy) {
      e.preventDefault();
      addAppcode();
    }
  }
</script>

<div class="as-backdrop">
  <div class="as-card" role="dialog" aria-modal="true" aria-label="Appcode setup" tabindex="-1">
    <span class="as-kicker">Welcome</span>
    <h2 class="as-title">Set up your appcodes</h2>
    <p class="as-hint">
      An appcode represents a team or product line you manage. At least one
      appcode is required to create and organize projects.
    </p>
    <div class="as-input-row">
      <input
        class="as-input"
        type="text"
        bind:value={inputName}
        placeholder="appcode name"
        disabled={busy}
        onkeydown={handleKeydown}
      />
      <button class="as-btn as-add" type="button" onclick={addAppcode} disabled={busy}>
        {busy ? "…" : "Add"}
      </button>
    </div>
    {#if error}<p class="as-err" role="alert">⚠ {error}</p>{/if}
    {#if saved.length > 0}
      <div class="as-list">
        <span class="as-list-label">Saved appcodes:</span>
        <ul>
          {#each saved as item}
            <li>✓ {item.name}</li>
          {/each}
        </ul>
      </div>
    {/if}
    <div class="as-actions">
      <button
        class="as-btn as-primary"
        type="button"
        onclick={onDone}
        disabled={saved.length === 0}
      >
        Done
      </button>
    </div>
  </div>
</div>

<style>
  .as-backdrop { position:fixed; inset:0; z-index:80; background:rgba(0,0,0,0.55); display:flex; align-items:center; justify-content:center; padding:20px; }
  .as-card { width:min(480px,100%); background:#fff; border:1px solid #D7DCE2; border-radius:10px; box-shadow:0 18px 50px rgba(0,0,0,0.4); padding:20px; display:flex; flex-direction:column; gap:10px; }
  .as-kicker { font-size:9px; font-weight:850; letter-spacing:0.4px; text-transform:uppercase; color:var(--color-muted); }
  .as-title { margin:0; font-size:18px; font-weight:900; color:var(--color-ink); }
  .as-hint { margin:0; font-size:11px; font-weight:700; color:var(--color-muted); line-height:1.5; }
  .as-input { height:32px; border:1px solid var(--color-input-border, #D7DCE2); border-radius:6px; padding:0 10px; font-size:12px; font-weight:750; color:var(--color-ink); outline:none; font-family:inherit; }
  .as-input:focus { border:2px solid var(--color-dbs-red); }
  .as-input-row { display:flex; gap:8px; align-items:center; }
  .as-input-row .as-input { flex:1; min-width:0; }
  .as-add { background:#fff; color:var(--color-dbs-red); border-color:var(--color-dbs-red); }
  .as-add:hover:not(:disabled) { background:var(--color-soft-pink-surface, #FFF1F4); }
  .as-err { margin:0; font-size:11px; font-weight:800; color:var(--color-dbs-red); }
  .as-list { display:flex; flex-direction:column; gap:4px; }
  .as-list-label { font-size:10px; font-weight:800; color:var(--color-muted); text-transform:uppercase; letter-spacing:0.3px; }
  .as-list ul { margin:0; padding:0; list-style:none; display:flex; flex-direction:column; gap:2px; }
  .as-list li { font-size:12px; font-weight:750; color:var(--color-ink); }
  .as-actions { display:flex; justify-content:flex-end; }
  .as-btn { height:34px; padding:0 18px; border-radius:6px; font-size:12px; font-weight:850; cursor:pointer; border:1px solid var(--color-dbs-red); }
  .as-primary { background:var(--color-dbs-red); color:#fff; }
  .as-primary:hover:not(:disabled) { background:var(--color-dbs-red-hover); }
  .as-btn:disabled { opacity:0.55; cursor:not-allowed; }
</style>
