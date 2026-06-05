<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import Sidebar from "./lib/components/Sidebar.svelte";
  import Header from "./lib/components/Header.svelte";
  import Dashboard from "./lib/components/Dashboard.svelte";
  import Report from "./lib/components/Report.svelte";
  import Settings from "./lib/components/Settings.svelte";
  import PagePlaceholder from "./lib/components/PagePlaceholder.svelte";
  import { callBridge, isPywebviewReady } from "./lib/bridge";
  import type { NotificationItem } from "./lib/types";

  type PageId = "dashboard" | "project-detail" | "second-brain" | "report" | "automations" | "settings";

  const pageShells: Record<Exclude<PageId, "dashboard" | "report" | "settings">, { title: string; subtitle: string; sections: { title: string; detail: string }[] }> = {
    "project-detail": {
      title: "Project Details",
      subtitle: "Operational workspace shell for NEW_PROJECT and SHOW_EDIT flows. Data binding lands in Phase E.",
      sections: [
        { title: "Project Command Center", detail: "Year, project, sub project selectors plus open/delete actions." },
        { title: "Metadata Forms", detail: "CR link, Drone tickets, schedule, implementation plan, and state controls." },
        { title: "Files, Notes, History", detail: "File list, markdown notes, autosave indicators, and read-only activity history." },
      ],
    },
    "second-brain": {
      title: "Second Brain",
      subtitle: "Local knowledge shell for Notes and Link Bank. No search/index calls yet.",
      sections: [
        { title: "Notes Tree", detail: "Pinned, Favorites, Second Brain Notes, and Project Documents." },
        { title: "Editor / Preview", detail: "Markdown editor, image preview, external file affordance." },
        { title: "Link Bank", detail: "Categories, link cards, tags, pin/favorite, import/export." },
      ],
    },
    automations: {
      title: "Automations",
      subtitle: "Automation command deck shell. Outlook, Teams, Scheduler, and Rules Engine stay deferred.",
      sections: [
        { title: "Outlook", detail: "Email categories, templates, conditions, and send/download logs." },
        { title: "Teams", detail: "Preview-first message automations with guarded Windows execution." },
        { title: "Scheduler & Rules", detail: "APScheduler entries plus trigger-condition-action rules." },
      ],
    },
  };

  let currentPage: PageId = $state("dashboard");
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
    const validPages = ["dashboard", "report", "settings"];
    if (id in pageShells || validPages.includes(id)) {
      currentPage = id as PageId;
    }
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
    />
    {#if currentPage === "dashboard"}
      <Dashboard {selectedYear} {searchQuery} key={refreshKey} />
    {:else if currentPage === "report"}
      <Report {selectedYear} {searchQuery} key={refreshKey} />
    {:else if currentPage === "settings"}
      <Settings />
    {:else}
      {@const shell = pageShells[currentPage]}
      <PagePlaceholder title={shell.title} subtitle={shell.subtitle} sections={shell.sections} />
    {/if}
  </main>
</div>
