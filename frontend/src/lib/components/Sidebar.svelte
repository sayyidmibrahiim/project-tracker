<script lang="ts">
  import { onDestroy } from "svelte";
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
    { id: "dashboard", label: "Dashboard", icon: "⌂" },
    { id: "project-detail", label: "Project Details", icon: "▧" },
    { id: "second-brain", label: "Second Brain", icon: "✦" },
    { id: "report", label: "Report", icon: "▥" },
    { id: "automations", label: "Automations", icon: "⚙" },
    { id: "settings", label: "Settings", icon: "◎" },
  ];

  let notificationOpen = $state(false);
  let dockHidden = $state(false);
  let idleTimer: ReturnType<typeof setTimeout> | null = null;
  let unreadCount = $derived(notifications.filter((n) => !n.dismissed).length);

  function revealDockSoon(delay = 900) {
    if (idleTimer) clearTimeout(idleTimer);
    idleTimer = setTimeout(() => (dockHidden = false), delay);
  }

  function handleGlobalActivity(event: Event) {
    const target = event.target as Element | null;
    if (target?.closest?.(".dock-hover-zone")) {
      dockHidden = false;
      return;
    }
    if (notificationOpen) return;
    dockHidden = true;
    revealDockSoon(event.type === "keydown" ? 1200 : 750);
  }

  onDestroy(() => {
    if (idleTimer) clearTimeout(idleTimer);
  });

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

<svelte:window onmousemove={handleGlobalActivity} onkeydown={handleGlobalActivity} />

<div class="dock-hover-zone" class:hidden-by-activity={dockHidden}>
  <aside id="sidebar" class="sidebar dock-sidebar" aria-label="Main navigation dock">
    <button class="dock-brand" type="button" title="Project Tracker" onclick={() => onNavigate("dashboard")}>PT</button>

    <nav class="nav sidebar-nav dock-nav" aria-label="Main navigation">
      {#each navItems as item}
        <button
          class="nav-btn dock-nav-btn"
          class:active={currentPage === item.id}
          title={item.label}
          aria-label={item.label}
          onclick={() => onNavigate(item.id)}
        >
          <span class="nav-icon">{item.icon}</span>
          <span class="nav-text">{item.label}</span>
        </button>
      {/each}
      <button
        class="nav-btn dock-nav-btn dock-notification-btn"
        class:active={notificationOpen}
        title="Notifications"
        aria-label="Notifications"
        onmouseenter={() => (notificationOpen = true)}
        onclick={() => (notificationOpen = !notificationOpen)}
      >
        <span class="nav-icon">●</span>
        {#if unreadCount > 0}<span class="dock-badge">{unreadCount}</span>{/if}
        <span class="nav-text">Notifications</span>
      </button>
    </nav>

    <div class="notification-panel dock-notification-popover" class:open={notificationOpen} role="region" aria-label="Notifications" onmouseleave={() => (notificationOpen = false)}>
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
    </div>
  </aside>
</div>

<style>
  .notif-item-row { display:flex; justify-content:space-between; align-items:flex-start; gap:4px; }
  .notif-item-dismiss { border:0; background:transparent; color:var(--text-muted); font-size:14px; font-weight:900; cursor:pointer; padding:0 2px; line-height:1; }
  .notif-item-dismiss:hover { color:var(--primary-red); }
  .notif-placeholder { color:var(--text-muted); font-size:10px; font-weight:800; text-align:center; padding:18px 4px; }
  .notif-error { color:var(--primary-red); }
</style>
