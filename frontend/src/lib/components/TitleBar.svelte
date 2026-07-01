<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import type { NotificationItem } from "../types";
  import { winMinimize, winToggleMaximize, winClose, getUserProfile, waitForPywebviewReady, onWinStateChange } from "../bridge";

  let {
    currentPage,
    onNavigate,
    notifications,
    notifLoadState,
    onDismiss,
    onDismissAll,
    searchQuery,
    onSearchChange,
  }: {
    currentPage: string;
    onNavigate: (id: string) => void;
    notifications: NotificationItem[];
    notifLoadState: "loading" | "error" | "loaded" | "idle";
    onDismiss: (id: string) => void;
    onDismissAll: () => void;
    searchQuery: string;
    onSearchChange: (q: string) => void;
  } = $props();

  const navItems = [
    { id: "dashboard", label: "Dashboard" },
    { id: "project-detail", label: "Project Details" },
    { id: "second-brain", label: "Second Brain" },
    { id: "report", label: "Report" },
    { id: "automations", label: "Automations" },
    { id: "global-plan", label: "Global Plan" },
    { id: "settings", label: "Settings" },
  ];

  let userName = $state("");
  let userInitials = $state("U");
  let debugInfo = $state("");
  let notifOpen = $state(false);
  let helpOpen = $state(false);
  let unreadCount = $derived(notifications.filter((n) => !n.dismissed).length);
  let winState = $state<"normal" | "maximized" | "minimized">("normal");
  let unsubWinState: (() => void) | undefined;
  let searchTimer: ReturnType<typeof setTimeout> | undefined;
  let searchFocused = $state(false);
  let notifContainerEl = $state<HTMLDivElement | undefined>(undefined);
  let helpContainerEl = $state<HTMLDivElement | undefined>(undefined);

  function handleWindowClick(e: MouseEvent) {
    if (notifOpen && notifContainerEl && !notifContainerEl.contains(e.target as Node)) {
      notifOpen = false;
    }
    if (helpOpen && helpContainerEl && !helpContainerEl.contains(e.target as Node)) {
      helpOpen = false;
    }
  }

  onMount(async () => {
    await waitForPywebviewReady();
    const resp = await getUserProfile();
    if (resp.ok && resp.data) {
      userName = resp.data.name;
      userInitials = resp.data.initials || "U";
      if (resp.data._debug) debugInfo = resp.data._debug;
    } else {
      userName = resp.error?.message || "bridge_failed";
      debugInfo = resp.error?.code || "";
    }
    window.addEventListener("click", handleWindowClick);
    unsubWinState = onWinStateChange((s) => (winState = s));
  });

  onDestroy(() => {
    window.removeEventListener("click", handleWindowClick);
    unsubWinState?.();
  });

  function handleSearchInput(e: Event) {
    const value = (e.target as HTMLInputElement).value;
    if (searchTimer) clearTimeout(searchTimer);
    searchTimer = setTimeout(() => onSearchChange(value), 200);
  }

  function handleMinimize() { winMinimize(); }
  function handleToggleMaximize() { winToggleMaximize(); }
  function handleClose() { winClose(); }

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

  const navIcons: Record<string, string> = {
    dashboard: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>`,
    "project-detail": `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>`,
    "second-brain": `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>`,
    report: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>`,
    automations: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06A2 2 0 0 1 22 4.6l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>`,
    "global-plan": `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>`,
    settings: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>`,
  };
</script>

<div class="titlebar" ondblclick={handleToggleMaximize} role="region" aria-label="Window titlebar">
  <div class="titlebar-left">
    <div class="user-avatar" title="{userName} [{debugInfo}]">
      <span class="avatar-initials">{userInitials}</span>
      <span class="online-dot"></span>
    </div>
    <div class="search-box" class:focused={searchFocused}>
      <svg class="search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      <input
        type="text"
        class="search-input"
        placeholder="Search (Menu: keyword)&#x2026;"
        value={searchQuery}
        oninput={handleSearchInput}
        onfocus={() => (searchFocused = true)}
        onblur={() => setTimeout(() => (searchFocused = false), 150)}
      />
    </div>
  </div>

  <nav class="titlebar-nav">
    {#each navItems as item}
      <button
        class="nav-tab"
        class:active={currentPage === item.id}
        onclick={(e) => { e.stopPropagation(); onNavigate(item.id); }}
        onpointerdown={(e) => e.stopPropagation()}
      >
        <span class="nav-tab-icon">{@html navIcons[item.id]}</span>
        <span class="nav-tab-tooltip">{item.label}</span>
      </button>
    {/each}
  </nav>

  <div class="titlebar-right">
      <div class="notif-container" bind:this={notifContainerEl}>
      <button
        class="notif-btn"
        class:open={notifOpen}
        onclick={() => (notifOpen = !notifOpen)}
        title="Notifications"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
        {#if unreadCount > 0}<span class="notif-badge">{unreadCount}</span>{/if}
      </button>
      {#if notifOpen}
        <div class="notif-popover" role="region" aria-label="Notifications">
          <div class="notif-popover-head">
            <span class="notif-popover-title">Notifications</span>
            {#if notifications.length > 0}
              <button class="notif-dismiss-all" onclick={() => onDismissAll()}>Dismiss all</button>
            {/if}
          </div>
          <div class="notif-popover-list">
            {#if notifLoadState === "loading"}
              <div class="notif-placeholder">Loading&#x2026;</div>
            {:else if notifLoadState === "error"}
              <div class="notif-placeholder notif-error">Notifications unavailable</div>
            {:else if notifications.length === 0}
              <div class="notif-placeholder">No notifications</div>
            {:else}
              {#each notifications as n}
                <div class="notif-item">
                  <div class="notif-item-row">
                    <div class="notif-item-title">{n.title}</div>
                    <button class="notif-item-dismiss" onclick={() => onDismiss(n.id)}>✕</button>
    </div>
    <div class="help-container" bind:this={helpContainerEl}>
      <button class="help-btn" class:open={helpOpen} onclick={() => (helpOpen = !helpOpen)} title="Keyboard shortcuts">?</button>
      {#if helpOpen}
        <div class="help-popover" role="region" aria-label="Keyboard shortcuts">
          <div class="help-popover-head">
            <span class="help-popover-title">Keyboard Shortcuts</span>
          </div>
          <div class="help-popover-list">
            <div class="help-shortcut"><kbd>Ctrl+Shift+D</kbd><span>Dashboard</span></div>
            <div class="help-shortcut"><kbd>Ctrl+Shift+P</kbd><span>Project Details</span></div>
            <div class="help-shortcut"><kbd>Ctrl+Shift+B</kbd><span>Second Brain</span></div>
            <div class="help-shortcut"><kbd>Ctrl+Shift+R</kbd><span>Report</span></div>
            <div class="help-shortcut"><kbd>Ctrl+Shift+A</kbd><span>Automations</span></div>
            <div class="help-shortcut"><kbd>Ctrl+Shift+G</kbd><span>Global Plan</span></div>
            <div class="help-shortcut"><kbd>Ctrl+Shift+,</kbd><span>Settings</span></div>
            <div class="help-shortcut"><kbd>Ctrl+Shift+F</kbd><span>Search</span></div>
            <div class="help-shortcut"><kbd>Escape</kbd><span>Close popover / Back</span></div>
          </div>
        </div>
      {/if}
    </div>
                  <div class="notif-item-time">{formatTime(n.timestamp)}</div>
                  <div class="notif-item-msg">{n.message}</div>
                </div>
              {/each}
            {/if}
          </div>
        </div>
      {/if}
    </div>
    <div class="win-controls">
      <button class="win-btn" onclick={handleMinimize} title="Minimize">─</button>
      <button class="win-btn" onclick={handleToggleMaximize} title={winState === "maximized" ? "Restore" : "Maximize"}>{winState === "maximized" ? "▣" : "⛶"}</button>
      <button class="win-btn win-close" onclick={handleClose} title="Close">✕</button>
    </div>
  </div>
</div>

<style>
  .titlebar {
    display: flex;
    align-items: center;
    height: 48px;
    min-height: 48px;
    background: var(--black-chrome);
    border-bottom: 1px solid var(--dark-border);
    -webkit-app-region: drag;
    user-select: none;
    padding: 0 8px;
    gap: 8px;
    z-index: 100;
  }
  .titlebar-left { display: flex; align-items: center; gap: 10px; flex: 0 0 auto; }
  .titlebar-nav { display: flex; align-items: center; gap: 2px; flex: 1; justify-content: center; -webkit-app-region: no-drag; }
  .titlebar-right { display: flex; align-items: center; gap: 4px; flex: 0 0 auto; }

  .user-avatar {
    position: relative;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: var(--primary-red);
    display: flex;
    align-items: center;
    justify-content: center;
    -webkit-app-region: no-drag;
    cursor: default;
    flex: 0 0 32px;
  }
  .avatar-initials { color: #fff; font-size: 12px; font-weight: 900; line-height: 1; }
  .online-dot {
    position: absolute;
    bottom: 0;
    right: 0;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #22C55E;
    border: 2px solid var(--black-chrome);
  }

  .search-box {
    position: relative;
    display: flex;
    align-items: center;
    -webkit-app-region: no-drag;
    width: 240px;
    transition: width .18s ease;
  }
  .search-box.focused { width: 320px; }
  .search-icon {
    position: absolute;
    left: 10px;
    color: var(--text-muted);
    pointer-events: none;
  }
  .search-input {
    width: 100%;
    height: 30px;
    padding: 0 10px 0 32px;
    border: 1px solid var(--dark-border);
    border-radius: 6px;
    background: var(--surface-dark);
    color: #fff;
    font-size: 11px;
    font-weight: 600;
    outline: none;
    font-family: var(--font);
    transition: border-color .16s ease, background .16s ease;
  }
  .search-input::placeholder { color: var(--text-muted); }
  .search-input:hover { border-color: var(--text-muted); }
  .search-input:focus { border-color: var(--primary-red); background: #1A1A1D; }

  .nav-tab {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 36px;
    border: 0;
    border-radius: 8px;
    background: transparent;
    color: var(--inactive-nav-text);
    -webkit-app-region: no-drag;
    cursor: pointer;
    transition: background .15s ease, color .15s ease;
  }
  .nav-tab:hover { background: var(--active-nav-bg); color: #fff; }
  .nav-tab.active { color: var(--active-red); background: var(--active-nav-bg); }
  .nav-tab-icon { display: flex; }
  .nav-tab-tooltip {
    display: none;
    position: absolute;
    bottom: -28px;
    left: 50%;
    transform: translateX(-50%);
    white-space: nowrap;
    background: var(--black-chrome);
    color: #fff;
    border: 1px solid var(--dark-border);
    border-radius: 5px;
    padding: 3px 7px;
    font-size: 10px;
    font-weight: 800;
    z-index: 120;
    box-shadow: var(--shadow-panel);
    pointer-events: none;
  }
  .nav-tab:hover .nav-tab-tooltip { display: block; }

  .notif-container { position: relative; -webkit-app-region: no-drag; }
  .notif-btn {
    position: relative;
    width: 34px;
    height: 34px;
    border: 0;
    border-radius: 8px;
    background: transparent;
    color: var(--inactive-nav-text);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: background .15s ease, color .15s ease;
  }
  .notif-btn:hover, .notif-btn.open { background: var(--active-nav-bg); color: #fff; }
  .notif-badge {
    position: absolute;
    top: 2px;
    right: 2px;
    min-width: 16px;
    height: 16px;
    padding: 0 4px;
    border-radius: 999px;
    background: var(--primary-red);
    color: #fff;
    border: 1.5px solid var(--black-chrome);
    font-size: 9px;
    font-weight: 900;
    display: grid;
    place-items: center;
  }
  .notif-popover {
    position: absolute;
    right: 0;
    top: 40px;
    width: 340px;
    max-height: 420px;
    background: var(--notification-bg);
    border: 1px solid var(--dark-border);
    border-radius: 10px;
    box-shadow: var(--shadow-notif);
    display: flex;
    flex-direction: column;
    z-index: 200;
    overflow: hidden;
  }
  .notif-popover-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 12px;
    border-bottom: 1px solid var(--dark-border);
  }
  .notif-popover-title { color: #fff; font-weight: 900; font-size: 11px; }
  .notif-dismiss-all {
    border: 0;
    background: transparent;
    color: var(--text-muted);
    font-size: 10px;
    font-weight: 800;
    cursor: pointer;
    padding: 0;
  }
  .notif-dismiss-all:hover { color: #fff; text-decoration: underline; }
  .notif-popover-list {
    overflow: auto;
    padding: 8px;
    flex: 1;
    min-height: 0;
  }
  .notif-placeholder { color: var(--text-muted); font-size: 10px; font-weight: 800; text-align: center; padding: 18px 4px; }
  .notif-error { color: var(--primary-red); }
  .notif-item {
    background: rgba(255,255,255,.62);
    border: 1px solid rgba(45,61,52,.10);
    border-radius: 6px;
    padding: 8px;
    margin-bottom: 6px;
  }
  .notif-item-row { display: flex; justify-content: space-between; align-items: flex-start; gap: 4px; }
  .notif-item-title { font-size: 11px; font-weight: 900; color: var(--text-strong); margin: 0 0 3px; }
  .notif-item-dismiss {
    border: 0;
    background: transparent;
    color: var(--text-muted);
    font-size: 12px;
    font-weight: 900;
    cursor: pointer;
    padding: 0 2px;
    line-height: 1;
  }
  .notif-item-dismiss:hover { color: var(--primary-red); }
  .notif-item-time { color: rgba(45,61,52,.75); font-weight: 800; margin: 0 0 3px; }
  .notif-item-msg { color: rgba(45,61,52,.92); font-weight: 650; line-height: 1.28; margin: 0; }

  .help-container { position: relative; -webkit-app-region: no-drag; }
  .help-btn {
    width: 26px; height: 26px; border: 0; border-radius: 50%;
    background: transparent; color: var(--inactive-nav-text);
    font-size: 13px; font-weight: 900; cursor: pointer;
    display: grid; place-items: center;
    transition: background .12s ease, color .12s ease;
    font-family: var(--font);
  }
  .help-btn:hover, .help-btn.open { background: var(--surface-dark); color: #fff; }
  .help-popover {
    position: absolute; right: 0; top: 36px; width: 260px;
    background: var(--notification-bg); border: 1px solid var(--dark-border);
    border-radius: 10px; box-shadow: var(--shadow-notif);
    z-index: 200; overflow: hidden;
  }
  .help-popover-head { padding: 10px 12px; border-bottom: 1px solid var(--dark-border); }
  .help-popover-title { color: #fff; font-weight: 900; font-size: 11px; }
  .help-popover-list { padding: 8px; }
  .help-shortcut { display: flex; align-items: center; gap: 8px; padding: 5px 4px; font-size: 10px; }
  .help-shortcut kbd {
    display: inline-block; min-width: 64px; padding: 2px 6px;
    background: var(--surface-dark); border: 1px solid var(--dark-border);
    border-radius: 4px; color: #fff; font-size: 9px; font-weight: 800;
    font-family: var(--font); text-align: center;
  }
  .help-shortcut span { color: var(--text-muted); font-weight: 800; }

  .win-controls {
    display: flex;
    align-items: center;
    gap: 4px;
    -webkit-app-region: no-drag;
  }
  .win-btn {
    width: 36px;
    height: 28px;
    border: 0;
    border-radius: 5px;
    background: transparent;
    color: var(--inactive-nav-text);
    font-size: 13px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: background .12s ease, color .12s ease;
    font-family: var(--font);
  }
  .win-btn:hover { background: var(--surface-dark); color: #fff; }
  .win-close:hover { background: var(--primary-red); color: #fff; }

  @media (max-width: 900px) {
    .search-box { width: 140px; }
    .search-box.focused { width: 180px; }
    .titlebar-nav { gap: 0; }
  }
</style>
