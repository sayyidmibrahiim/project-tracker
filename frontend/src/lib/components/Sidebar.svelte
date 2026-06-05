<script lang="ts">
  let { currentPage, onNavigate }: { currentPage: string; onNavigate: (id: string) => void } = $props();

  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: "◔" },
    { id: "project-detail", label: "Project Details", icon: "▣" },
    { id: "second-brain", label: "Second Brain", icon: "◆" },
    { id: "report", label: "Report", icon: "▤" },
    { id: "automations", label: "Automations", icon: "⚙" },
    { id: "settings", label: "Settings", icon: "◌" },
  ];

  const notifications = [
    {
      id: "1",
      title: "T-10 reminder",
      time: "Just now",
      message: "Approval check visual sample. Check UAT Prepare approvals.",
    },
    {
      id: "2",
      title: "Folder scan",
      time: "5m ago",
      message: "2 projects found under year 2026.",
    },
  ];
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
      </span>
      <button class="notif-dismiss">Dismiss</button>
    </div>
    <div class="notif-list">
      {#each notifications as n}
        <article class="notif-item">
          <p class="notif-item-title">{n.title}</p>
          <p class="notif-item-time">{n.time}</p>
          <p class="notif-item-msg">{n.message}</p>
        </article>
      {/each}
    </div>
  </div>

  <!-- Footer -->
  <div class="sidebar-footer">v0.1.0 · Svelte + Vite</div>
</aside>
