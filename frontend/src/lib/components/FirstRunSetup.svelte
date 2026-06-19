<script lang="ts">
  /**
   * First-Run Setup — PRD §11.3.
   *
   * Shown by the App shell when `root_folder` is unset. Persists the chosen root
   * via the existing `settings_get`/`settings_update` bridge (full-object
   * round-trip). A native folder picker is Windows-only; on other platforms the
   * user types the path (the saved Windows path is preserved as-is by the
   * backend settings store).
   */
  import { callBridge, isPywebviewReady } from "../bridge";

  interface Props {
    onSaved: () => void;
  }
  let { onSaved }: Props = $props();

  let rootPath = $state("");
  let busy = $state(false);
  let browseBusy = $state(false);
  let error = $state("");

  async function browse() {
    if (!isPywebviewReady()) {
      error = "Folder picker requires the desktop app. Type a path manually.";
      return;
    }
    browseBusy = true;
    const resp = await callBridge<{ path: string | null }>("util_choose_folder");
    browseBusy = false;
    if (!resp.ok) {
      error = resp.error.message;
      return;
    }
    const path = resp.data?.path ?? null;
    if (path) {
      rootPath = path;
      error = "";
    }
  }

  async function save() {
    const value = rootPath.trim();
    if (!value) {
      error = "Enter the root folder path to continue.";
      return;
    }
    error = "";
    if (!isPywebviewReady()) {
      error = "The desktop app is required to save settings.";
      return;
    }
    busy = true;
    const current = await callBridge<Record<string, unknown>>("settings_get");
    if (!current.ok) {
      busy = false;
      error = current.error.message;
      return;
    }
    const payload = { ...(current.data ?? {}), root_folder: value };
    const saved = await callBridge("settings_update", payload);
    busy = false;
    if (!saved.ok) {
      error = saved.error.message;
      return;
    }
    onSaved();
  }
</script>

<div class="fr-backdrop">
  <div class="fr-card" role="dialog" aria-modal="true" aria-label="First-run setup" tabindex="-1">
    <span class="fr-kicker">First-Run Setup</span>
    <h2 class="fr-title">Choose your root folder</h2>
    <p class="fr-hint">
      Project Tracker DBS stores every project year folder under one root folder. Enter its full path to
      continue. A native folder picker is available in the Windows desktop app; on other platforms, type
      the path.
    </p>
    <div class="fr-input-row">
      <input class="fr-input" type="text" bind:value={rootPath} placeholder="D:\WORK\CR" disabled={busy} />
      <button class="fr-btn fr-browse" type="button" onclick={browse} disabled={busy || browseBusy}>{browseBusy ? "…" : "Browse"}</button>
    </div>
    {#if error}<p class="fr-err" role="alert">⚠ {error}</p>{/if}
    <div class="fr-actions">
      <button class="fr-btn fr-primary" type="button" onclick={save} disabled={busy}>{busy ? "Saving…" : "Save & Continue"}</button>
    </div>
  </div>
</div>

<style>
  .fr-backdrop { position:fixed; inset:0; z-index:80; background:rgba(0,0,0,0.55); display:flex; align-items:center; justify-content:center; padding:20px; }
  .fr-card { width:min(480px,100%); background:#fff; border:1px solid #D7DCE2; border-radius:10px; box-shadow:0 18px 50px rgba(0,0,0,0.4); padding:20px; display:flex; flex-direction:column; gap:10px; }
  .fr-kicker { font-size:9px; font-weight:850; letter-spacing:0.4px; text-transform:uppercase; color:var(--color-muted); }
  .fr-title { margin:0; font-size:18px; font-weight:900; color:var(--color-ink); }
  .fr-hint { margin:0; font-size:11px; font-weight:700; color:var(--color-muted); line-height:1.5; }
  .fr-input { height:32px; border:1px solid var(--color-input-border, #D7DCE2); border-radius:6px; padding:0 10px; font-size:12px; font-weight:750; color:var(--color-ink); outline:none; font-family:inherit; }
  .fr-input:focus { border:2px solid var(--color-dbs-red); }
  .fr-input-row { display:flex; gap:8px; align-items:center; }
  .fr-input-row .fr-input { flex:1; min-width:0; }
  .fr-browse { background:#fff; color:var(--color-dbs-red); border-color:var(--color-dbs-red); }
  .fr-browse:hover:not(:disabled) { background:var(--color-soft-pink-surface, #FFF1F4); }
  .fr-err { margin:0; font-size:11px; font-weight:800; color:var(--color-dbs-red); }
  .fr-actions { display:flex; justify-content:flex-end; }
  .fr-btn { height:34px; padding:0 18px; border-radius:6px; font-size:12px; font-weight:850; cursor:pointer; border:1px solid var(--color-dbs-red); }
  .fr-primary { background:var(--color-dbs-red); color:#fff; }
  .fr-primary:hover:not(:disabled) { background:var(--color-dbs-red-hover); }
  .fr-btn:disabled { opacity:0.55; cursor:not-allowed; }
</style>
