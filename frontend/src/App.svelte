<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import TitleBar from "./lib/components/TitleBar.svelte";
  import Header from "./lib/components/Header.svelte";
  import Dashboard from "./lib/components/Dashboard.svelte";
  import Report from "./lib/components/Report.svelte";
  import Settings from "./lib/components/Settings.svelte";
  import SecondBrain from "./lib/components/SecondBrain.svelte";
  import ProjectDetails from "./lib/components/ProjectDetails.svelte";
  import Automations from "./lib/components/Automations.svelte";
  import GlobalPlan from "./lib/components/GlobalPlan.svelte";
  import FirstRunSetup from "./lib/components/FirstRunSetup.svelte";
  import WelcomeGuide from "./lib/components/WelcomeGuide.svelte";
  import Toast from "./lib/components/Toast.svelte";
  import { callBridge, isPywebviewReady, waitForPywebviewReady } from "./lib/bridge";
  import { installGlobalActivityLogging, logActivity } from "./lib/activityLogger";
  import type { NotificationItem } from "./lib/types";

  type PageId = "dashboard" | "project-detail" | "second-brain" | "report" | "automations" | "global-plan" | "settings";

  // All pages have real components — no placeholder needed.

  let currentPage: PageId = $state("dashboard");
  let selectedYear = $state("all");
  let selectedAppcode = $state("");
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
  let stopActivityLogging: (() => void) | null = null;
  const POLL_INTERVAL_MS = 1500;

  // Years for the dashboard header dropdown (from year_list).
  let years: string[] = $state([]);

  // First-Run Setup (PRD §11.3): shown when root_folder is unset.
  let rootUnset: boolean = $state(false);

  function navigate(id: string) {
    const validPages = ["dashboard", "report", "settings", "second-brain", "project-detail", "automations", "global-plan"];
    logActivity({ source: "App.navigate", kind: "navigation", event: "start", from: currentPage, to: id, valid: validPages.includes(id) });
    if (validPages.includes(id)) {
      if (id !== "project-detail") {
        pendingProjectPath = null;
        startNewProject = false;
      }
      currentPage = id as PageId;
      logActivity({ source: "App.navigate", kind: "navigation", event: "done", currentPage });
    }
  }

  function openProjectDetails(path: string) {
    logActivity({ source: "App.openProjectDetails", kind: "navigation", path });
    pendingProjectPath = path;
    startNewProject = false;
    currentPage = "project-detail";
  }

  function openNewProjectPage() {
    logActivity({ source: "App.openNewProjectPage", kind: "navigation" });
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

  async function loadYears() {
    if (!isPywebviewReady()) return;
    const resp = await callBridge<string[]>("year_list", selectedAppcode || "");
    if (resp.ok && resp.data) years = resp.data;
  }

  // Add Year (PRD §11.7): create the folder, refresh the list, select it.
  async function addYear(year: string): Promise<string | null> {
    if (!isPywebviewReady()) return "The desktop app is required to create a year folder.";
    const r = await callBridge("year_create", year, selectedAppcode || "");
    if (!r.ok) return r.error.message;
    await loadYears();
    selectedYear = year;
    refreshKey++;
    return null;
  }

  // Bumped by the Dashboard empty-state "Add Year" button; opens Header's dialog.
  let openAddYearToken = $state(0);
  function openAddYear() {
    openAddYearToken++;
  }

  async function checkRoot() {
    if (!isPywebviewReady()) return;
    const r = await callBridge<Record<string, unknown>>("settings_get");
    if (r.ok && r.data) {
      const root = r.data["root_folder"];
      rootUnset = !root || String(root).trim() === "";
    }
  }

  function onRootConfigured() {
    rootUnset = false;
    loadYears();
    refreshKey++;
  }

  onMount(async () => {
    stopActivityLogging = installGlobalActivityLogging(() => currentPage);
    // Wait for pywebview to fully register bridge methods before any call.
    // Without this, early isPywebviewReady() returns false (or true with an
    // empty api object) and all initial loads silently bail.
    await waitForPywebviewReady();
    logActivity({ source: "App.onMount", kind: "lifecycle", event: "bridge-ready", currentPage });
    loadNotifications();
    loadYears();
    checkRoot();
    startPolling();
  });

  onDestroy(() => {
    stopPolling();
    stopActivityLogging?.();
  });
</script>

<div class="resize-edge">
  <div class="resize-edge-top"></div>
  <div class="resize-edge-bottom"></div>
  <div class="resize-edge-left"></div>
  <div class="resize-edge-right"></div>
  <div class="resize-edge-tl"></div>
  <div class="resize-edge-tr"></div>
  <div class="resize-edge-bl"></div>
  <div class="resize-edge-br"></div>
</div>
<div class="app-shell">
  <TitleBar
    {currentPage}
    {notifications}
    {notifLoadState}
    {searchQuery}
    onNavigate={navigate}
    onDismiss={handleDismiss}
    onDismissAll={handleDismissAll}
    onSearchChange={handleSearchChange}
  />
  <main class="main">
    <Header
      {currentPage}
      {selectedYear}
      {years}
      showDashboardControls={currentPage === "dashboard"}
      onYearChange={handleYearChange}
      onRefresh={handleRefresh}
      onAddProject={openNewProjectPage}
      onAddYear={addYear}
      {openAddYearToken}
    />
    <div class="app-content">
      {#if currentPage === "dashboard"}
        <Dashboard {selectedYear} {searchQuery} refreshToken={refreshKey} onOpenProjectDetails={openProjectDetails} onAddProject={openNewProjectPage} onAddYear={openAddYear} />
      {:else if currentPage === "report"}
        <Report {selectedYear} {searchQuery} key={refreshKey} />
      {:else if currentPage === "settings"}
        <Settings />
      {:else if currentPage === "second-brain"}
        <SecondBrain />
      {:else if currentPage === "project-detail"}
        <ProjectDetails initialPath={pendingProjectPath} startNew={startNewProject} onNavigateDashboard={() => navigate("dashboard")} />
      {:else if currentPage === "automations"}
        <Automations />
      {:else if currentPage === "global-plan"}
        <GlobalPlan />
      {/if}
    </div>
  </main>
  {#if rootUnset}
    <FirstRunSetup onSaved={onRootConfigured} />
  {/if}
  <WelcomeGuide />
</div>

<Toast />
