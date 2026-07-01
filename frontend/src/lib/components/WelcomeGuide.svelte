<script lang="ts">
  let dismissed = $state(
    typeof localStorage !== "undefined" && localStorage.getItem("welcome_dismissed") === "true"
  );

  function dismiss() {
    dismissed = true;
    try { localStorage.setItem("welcome_dismissed", "true"); } catch { /* noop */ }
  }
</script>

{#if !dismissed}
  <div class="wg-backdrop" onclick={dismiss} role="presentation"></div>
  <div class="wg-dialog" role="dialog" aria-modal="true" aria-label="Welcome">
    <div class="wg-body">
      <h2 class="wg-heading">Welcome to Project Tracker</h2>
      <p class="wg-intro">Your all-in-one desktop tool for managing CRs, Drone tickets, and project documentation.</p>
      <div class="wg-steps">
        <div class="wg-step"><span class="wg-step-num">1</span><div><strong>Dashboard or Project Details</strong><p>Track every project's CR link, state, and Drone tickets. Inline edits are instant with undo.</p></div></div>
        <div class="wg-step"><span class="wg-step-num">2</span><div><strong>Second Brain</strong><p>Link bank for bookmarks, docs, and reference links plus a notes editor for freeform markdown.</p></div></div>
        <div class="wg-step"><span class="wg-step-num">3</span><div><strong>Automations</strong><p>Schedule Outlook emails, Teams messages, and custom rules on a timer.</p></div></div>
        <div class="wg-step"><span class="wg-step-num">4</span><div><strong>Global Plan</strong><p>Kanban-style Now/Next/Backlog for high-level task tracking across projects.</p></div></div>
      </div>
      <p class="wg-tip"><strong>Tip:</strong> Use <kbd>Ctrl+Shift+D</kbd> through <kbd>Ctrl+Shift+</kbd> to jump between pages. Press <kbd>?</kbd> in the titlebar for all shortcuts.</p>
    </div>
    <div class="wg-footer">
      <button class="btn-secondary" onclick={dismiss}>Skip</button>
      <button class="btn-primary" onclick={dismiss}>Got It</button>
    </div>
  </div>
{/if}

<style>
  .wg-backdrop {
    position: fixed; inset: 0; z-index: 300;
    background: rgba(0,0,0,0.55);
  }
  .wg-dialog {
    position: fixed; top: 50%; left: 50%; transform: translate(-50%,-50%);
    z-index: 310; width: 420px; max-width: 90vw;
    background: var(--main-panel-bg); border: 1px solid var(--soft-white-border);
    border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    display: flex; flex-direction: column; overflow: hidden;
  }
  .wg-body { padding: 20px 20px 12px; }
  .wg-heading { font-size: 15px; font-weight: 900; margin: 0 0 4px; color: var(--text-strong); }
  .wg-intro { font-size: 11px; color: var(--text-secondary); margin: 0 0 14px; line-height: 1.4; }
  .wg-steps { display: flex; flex-direction: column; gap: 8px; }
  .wg-step { display: flex; gap: 10px; align-items: flex-start; }
  .wg-step-num {
    flex-shrink: 0; width: 22px; height: 22px; border-radius: 50%;
    background: var(--primary-red); color: #fff;
    display: grid; place-items: center; font-size: 11px; font-weight: 900;
  }
  .wg-step strong { font-size: 11px; color: var(--text-strong); }
  .wg-step p { font-size: 10px; color: var(--text-secondary); margin: 2px 0 0; line-height: 1.35; }
  .wg-tip { font-size: 10px; color: var(--text-secondary); margin: 12px 0 0; }
  .wg-tip kbd {
    display: inline-block; padding: 1px 5px; background: var(--surface-dark);
    border: 1px solid var(--border-soft); border-radius: 3px;
    font-size: 9px; font-weight: 800; color: var(--text-strong);
    font-family: var(--font);
  }
  .wg-footer {
    display: flex; justify-content: flex-end; gap: 6px;
    padding: 10px 20px; border-top: 1px solid var(--soft-white-border);
  }
</style>
