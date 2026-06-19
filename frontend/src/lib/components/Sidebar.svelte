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

  let collapsed = $state(false);

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
      const diffMin = Math.floor((Date.now() - d.getTime()) / 60000);
      if (diffMin < 1) return "Just now";
      if (diffMin < 60) return `${diffMin}m ago`;
      if (diffMin < 1440) return `${Math.floor(diffMin / 60)}h ago`;
      return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
    } catch {
      return iso;
    }
  }
</script>

<aside id="sidebar" class="sidebar" class:collapsed>
  <div class="brand sidebar-brand">
    <div class="brand-icon">▦</div>
    <div class="brand-title">Project Tracker</div>
  </div>

  <nav class="nav sidebar-nav" aria-label="Main navigation">
    {#each navItems as item}
      <button
        class="nav-btn"
        class:active={currentPage === item.id}
        title={collapsed ? item.label : undefined}
        onclick={() => onNavigate(item.id)}
      >
        <span class="nav-icon">{item.icon}</span>
        <span class="nav-text">{item.label}</span>
      </button>
    {/each}
    <button class="nav-btn nav-notif-collapsed" title="Notifications">
      <span class="nav-icon">●</span>
    </button>
  </nav>

  <div class="sidebar-fill">
    <section class="notification-panel sidebar-notif-panel">
      <div class="notification-head notif-head">
        <div class="notification-title notif-title"><span class="notification-dot notif-dot">●</span>Notifications</div>
        {#if notifications.length > 0}
          <button class="link-button notif-dismiss" onclick={() => onDismissAll()}>Dismiss</button>
        {/if}
      </div>
      <div class="notification-list notif-list" id="notifList">
        {#if notifLoadState === "loading"}
          <div class="notif-placeholder">Loading notifications…</div>
        {:else if notifLoadState === "error"}
          <div class="notif-placeholder notif-error">Notifications unavailable</div>
        {:else if notifications.length === 0}
          <div class="notif-placeholder">No notifications yet.</div>
        {:else}
          {#each notifications as n}
            <article class="notification-item notif-item">
              <div class="notif-item-row">
                <div class="notification-item-title notif-item-title">{n.title}</div>
                <button class="notif-item-dismiss" title="Dismiss" onclick={() => onDismiss(n.id)}>×</button>
              </div>
              <div class="notification-time notif-item-time">{formatTime(n.timestamp)}</div>
              <div class="notification-message notif-item-msg">{n.message}</div>
            </article>
          {/each}
        {/if}
      </div>
    </section>
  </div>

  <button
    class="collapse-btn sidebar-collapse-btn"
    id="collapseBtn"
    type="button"
    title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
    aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
    onclick={() => (collapsed = !collapsed)}
  >{collapsed ? "›" : "‹"}</button>
</aside>

<style>
  .notif-item-row { display:flex; justify-content:space-between; align-items:flex-start; gap:4px; }
  .notif-item-dismiss { border:0; background:transparent; color:var(--text-muted); font-size:14px; font-weight:900; cursor:pointer; padding:0 2px; line-height:1; }
  .notif-item-dismiss:hover { color:var(--primary-red); }
  .notif-placeholder { color:var(--text-muted); font-size:10px; font-weight:800; text-align:center; padding:18px 4px; }
  .notif-error { color:var(--primary-red); }
</style>
