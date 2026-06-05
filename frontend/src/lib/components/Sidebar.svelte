<script lang="ts">
  import type { NotificationItem } from "../types";

  let {
    currentPage,
    onNavigate,
    notifications,
    notifLoadState,
    onDismiss,
    onDismissAll,
  }: {
    currentPage: string;
    onNavigate: (id: string) => void;
    notifications: NotificationItem[];
    notifLoadState: "loading" | "error" | "loaded" | "idle";
    onDismiss: (id: string) => void;
    onDismissAll: () => void;
  } = $props();

  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: "◔" },
    { id: "project-detail", label: "Project Details", icon: "▣" },
    { id: "second-brain", label: "Second Brain", icon: "◆" },
    { id: "report", label: "Report", icon: "▤" },
    { id: "automations", label: "Automations", icon: "⚙" },
    { id: "settings", label: "Settings", icon: "◌" },
  ];

  function formatTime(iso: string): string {
    try {
      const d = new Date(iso);
      if (isNaN(d.getTime())) return iso;
      const now = Date.now();
      const diffMs = now - d.getTime();
      const diffMin = Math.floor(diffMs / 60000);
      if (diffMin < 1) return "Just now";
      if (diffMin < 60) return `${diffMin}m ago`;
      if (diffMin < 1440) return `${Math.floor(diffMin / 60)}h ago`;
      return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
    } catch {
      return iso;
    }
  }
</script>

<aside class="sidebar">
  <!-- Brand -->
  <div class="sidebar-brand">
    <div class="brand-icon">▦</div>
    <h1 class="brand-title">Project Tracker DBS</h1>
  </div>

  <!-- Nav -->
  <nav class="sidebar-nav" aria-label="Main navigation">
    {#each navItems as item}
      <button
        class="nav-btn"
        class:active={currentPage === item.id}
        onclick={() => onNavigate(item.id)}
      >
        <span class="nav-icon">{item.icon}</span>
        <span class="nav-text">{item.label}</span>
      </button>
    {/each}
  </nav>

  <!-- Notification panel -->
  <div class="sidebar-notif-panel">
    <div class="notif-head">
      <span class="notif-title">
        <span class="notif-dot">●</span>
        Notifications
        {#if notifications.length > 0}
          <span class="notif-count">{notifications.length}</span>
        {/if}
      </span>
      {#if notifications.length > 0}
        <button class="notif-dismiss" onclick={() => onDismissAll()}>Dismiss all</button>
      {/if}
    </div>
    <div class="notif-list">
      {#if notifLoadState === "loading"}
        <div class="notif-placeholder">Loading notifications…</div>
      {:else if notifLoadState === "error"}
        <div class="notif-placeholder notif-error">Notifications unavailable</div>
      {:else if notifications.length === 0}
        <div class="notif-placeholder">No notifications</div>
      {:else}
        {#each notifications as n}
          <article class="notif-item">
            <div class="notif-item-row">
              <p class="notif-item-title">{n.title}</p>
              <button
                class="notif-item-dismiss"
                title="Dismiss"
                onclick={() => onDismiss(n.id)}
              >×</button>
            </div>
            <p class="notif-item-time">{formatTime(n.timestamp)}</p>
            <p class="notif-item-msg">{n.message}</p>
          </article>
        {/each}
      {/if}
    </div>
  </div>

  <!-- Footer -->
  <div class="sidebar-footer">v0.1.0 · Svelte + Vite</div>
</aside>

<style>
  .notif-count {
    background: var(--color-dbs-red);
    color: #fff;
    font-size: 9px;
    font-weight: 900;
    padding: 1px 5px;
    border-radius: 9px;
    margin-left: 4px;
  }
  .notif-item-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }
  .notif-item-dismiss {
    border: 0;
    background: transparent;
    color: var(--color-muted-light);
    font-size: 14px;
    font-weight: 900;
    cursor: pointer;
    padding: 0 2px;
    line-height: 1;
  }
  .notif-item-dismiss:hover { color: var(--color-dbs-red); }
  .notif-placeholder {
    color: var(--color-muted-light);
    font-size: 10px;
    font-weight: 650;
    text-align: center;
    padding: 16px 4px;
  }
  .notif-error { color: var(--color-dbs-red); }
</style>
