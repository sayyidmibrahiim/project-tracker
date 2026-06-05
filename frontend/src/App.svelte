<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import Sidebar from "./lib/components/Sidebar.svelte";
  import Header from "./lib/components/Header.svelte";
  import Dashboard from "./lib/components/Dashboard.svelte";
  import { callBridge, isPywebviewReady } from "./lib/bridge";
  import type { NotificationItem } from "./lib/types";

  let currentPage = $state("dashboard");
  let selectedYear = $state("all");
  let searchQuery = $state("");
  let refreshKey = $state(0);

  // Notification state
  let notifications: NotificationItem[] = $state([]);
  type NotifLoadState = "idle" | "loading" | "error" | "loaded";
  let notifLoadState: NotifLoadState = $state("idle");

  // Event polling
  let pollTimer: ReturnType<typeof setInterval> | null = null;
  const POLL_INTERVAL_MS = 5000;

  function navigate(id: string) {
    currentPage = id;
  }

  function handleYearChange(year: string) {
    selectedYear = year;
  }

  function handleSearchChange(q: string) {
    searchQuery = q;
  }

  function handleRefresh() {
    refreshKey++;
  }

  // ── Notification loading ──

  async function loadNotifications() {
    if (!isPywebviewReady()) return;

    notifLoadState = "loading";
    const response = await callBridge<NotificationItem[]>("notification_list");

    if (!response.ok) {
      notifLoadState = "error";
      return;
    }

    notifications = response.data ?? [];
    notifLoadState = "loaded";
  }

  async function handleDismiss(id: string) {
    if (!isPywebviewReady()) return;
    await callBridge("notification_dismiss", id);
    notifications = notifications.filter((n) => n.id !== id);
  }

  async function handleDismissAll() {
    if (!isPywebviewReady()) return;
    await callBridge("notification_dismiss_all");
    notifications = [];
  }

  // ── Event polling ──

  async function pollEvents() {
    if (!isPywebviewReady()) return;
    try {
      const response = await callBridge<{ type: string }[]>("poll_events");
      if (response.ok && response.data) {
        const hasNotification = response.data.some((e) => e.type === "NOTIFICATION");
        if (hasNotification) {
          await loadNotifications();
        }
      }
    } catch {
      // Silently ignore poll errors — not worth spamming
    }
  }

  function startPolling() {
    if (!isPywebviewReady()) return;
    stopPolling();
    pollTimer = setInterval(pollEvents, POLL_INTERVAL_MS);
  }

  function stopPolling() {
    if (pollTimer !== null) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  onMount(() => {
    loadNotifications();
    startPolling();
  });

  onDestroy(() => {
    stopPolling();
  });
</script>

<div class="app-shell">
  <Sidebar
    {currentPage}
    {notifications}
    {notifLoadState}
    onNavigate={navigate}
    onDismiss={handleDismiss}
    onDismissAll={handleDismissAll}
  />
  <main class="main-area">
    <Header
      {currentPage}
      {selectedYear}
      {searchQuery}
      onYearChange={handleYearChange}
      onSearchChange={handleSearchChange}
      onRefresh={handleRefresh}
    />
    {#if currentPage === "dashboard"}
      <Dashboard {selectedYear} {searchQuery} key={refreshKey} />
    {:else}
      <div class="placeholder-screen">
        <div class="placeholder-card">
          <p class="placeholder-title">{currentPage.replace("-", " ")}</p>
          <p class="placeholder-sub">Page not yet implemented. Static scaffold only.</p>
        </div>
      </div>
    {/if}
  </main>
</div>
