<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import Sidebar from "./lib/components/Sidebar.svelte";
  import Header from "./lib/components/Header.svelte";
  import Dashboard from "./lib/components/Dashboard.svelte";
  import Report from "./lib/components/Report.svelte";
  import Settings from "./lib/components/Settings.svelte";
  import SecondBrain from "./lib/components/SecondBrain.svelte";
  import ProjectDetails from "./lib/components/ProjectDetails.svelte";
  import Automations from "./lib/components/Automations.svelte";
  import PagePlaceholder from "./lib/components/PagePlaceholder.svelte";
  import { callBridge, isPywebviewReady } from "./lib/bridge";
  import type { NotificationItem } from "./lib/types";

  type PageId = "dashboard" | "project-detail" | "second-brain" | "report" | "automations" | "settings";

  // No remaining placeholder pages — all pages have real components.
  // pageShells kept for type safety if new placeholder pages are added later.
  const pageShells: Partial<Record<PageId, { title: string; subtitle: string; sections: { title: string; detail: string }[] }>> = {};

  let currentPage: PageId = $state("dashboard");
  let selectedYear = $state("all");
  let searchQuery = $state("");
  let refreshKey = $state(0);
  let pendingProjectPath: string | null = $state(null);
  let startNewProject: boolean = $state(false);

  // Notification state
  let notifications: NotificationItem[] = $state([]);
  type NotifLoadState = "idle" | "loading" | "error" | "loaded";
  let notifLoadState: NotifLoadState = $state("idle");

  // Event polling
  let pollTimer: ReturnType<typeof setInterval> | null = null;
  const POLL_INTERVAL_MS = 5000;

  function navigate(id: string) {
    const validPages = ["dashboard", "report", "settings", "second-brain", "project-detail", "automations"];
    if (id in pageShells || validPages.includes(id)) {
      if (id !== "project-detail") {
        pendingProjectPath = null;
        startNewProject = false;
      }
      currentPage = id as PageId;
    }
  }

  function openProjectDetails(path: string) {
    pendingProjectPath = path;
    startNewProject = false;
    currentPage = "project-detail";
  }

  function openNewProjectPage() {
    startNewProject = true;
    pendingProjectPath = null;
    currentPage = "project-detail";
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
      showDashboardControls={currentPage === "dashboard"}
      onYearChange={handleYearChange}
      onSearchChange={handleSearchChange}
      onRefresh={handleRefresh}
      onAddProject={openNewProjectPage}
    />
    {#if currentPage === "dashboard"}
      <Dashboard {selectedYear} {searchQuery} refreshToken={refreshKey} onOpenProjectDetails={openProjectDetails} />
    {:else if currentPage === "report"}
      <Report {selectedYear} {searchQuery} key={refreshKey} />
    {:else if currentPage === "settings"}
      <Settings />
    {:else if currentPage === "second-brain"}
      <SecondBrain />
    {:else if currentPage === "project-detail"}
      <ProjectDetails initialPath={pendingProjectPath} startNew={startNewProject} />
    {:else if currentPage === "automations"}
      <Automations />
    {:else}
      <PagePlaceholder title="Unknown Page" subtitle="Page not found." sections={[]} />
    {/if}
  </main>
</div>
