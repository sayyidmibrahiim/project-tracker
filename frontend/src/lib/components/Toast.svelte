<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { subscribe, removeToast } from "../stores/toastStore";
  import type { ToastItem } from "../stores/toastStore";

  let toasts: ToastItem[] = $state([]);
  let unsub: (() => void) | undefined;

  const icons: Record<string, string> = {
    success: "✓",
    error: "✗",
    warning: "⚠",
    info: "ℹ",
  };

  onMount(() => {
    unsub = subscribe((t) => (toasts = t));
  });
  onDestroy(() => unsub?.());
</script>

{#if toasts.length > 0}
  <div class="toast-container" role="status" aria-live="polite">
    {#each toasts as toast (toast.id)}
      <div class="toast toast-{toast.type}">
        <span class="toast-icon">{icons[toast.type]}</span>
        <span class="toast-msg">{toast.message}</span>
        {#if toast.action}
          <button class="toast-action" onclick={() => { toast.action!.fn(); removeToast(toast.id); }}>{toast.action!.label}</button>
        {/if}
        <button class="toast-close" onclick={() => removeToast(toast.id)} aria-label="Dismiss">✕</button>
      </div>
    {/each}
  </div>
{/if}

<style>
  .toast-container {
    position: fixed;
    bottom: 16px;
    right: 16px;
    z-index: 200;
    display: flex;
    flex-direction: column;
    gap: 6px;
    pointer-events: none;
    max-width: 360px;
  }
  .toast {
    pointer-events: auto;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 10px 8px 12px;
    border-radius: 6px;
    background: var(--black-chrome, #0a0a0b);
    color: #fff;
    font-size: 11px;
    font-weight: 800;
    box-shadow: 0 4px 16px rgba(0,0,0,0.35);
    animation: toast-in .2s ease-out;
  }
  .toast-icon { flex-shrink: 0; width: 16px; text-align: center; font-size: 13px; }
  .toast-msg { flex: 1; min-width: 0; }
  .toast-action { flex-shrink: 0; padding: 2px 8px; border: 1px solid rgba(255,255,255,0.3); border-radius: 4px; background: transparent; color: #fff; font-size: 10px; font-weight: 900; cursor: pointer; }
  .toast-action:hover { background: rgba(255,255,255,0.12); }
  .toast-close { flex-shrink: 0; width: 18px; height: 18px; border: 0; border-radius: 3px; background: transparent; color: rgba(255,255,255,0.5); font-size: 11px; cursor: pointer; display: grid; place-items: center; }
  .toast-close:hover { background: rgba(255,255,255,0.1); color: #fff; }
  .toast-success { border-left: 3px solid #22c55e; }
  .toast-error { border-left: 3px solid #ef4444; }
  .toast-warning { border-left: 3px solid #f59e0b; }
  .toast-info { border-left: 3px solid #3b82f6; }

  @media (prefers-reduced-motion: reduce) {
    .toast { animation: none; }
  }

  @keyframes toast-in {
    from { opacity: 0; transform: translateX(30px); }
    to { opacity: 1; transform: translateX(0); }
  }
</style>
