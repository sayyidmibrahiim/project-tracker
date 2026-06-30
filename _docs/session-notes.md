# Session Notes

> Brief recovery ledger. Do not paste transcripts or secrets.
>
> - **DECISIONS.md** → permanent ADRs (why)
> - **PROGRESS.md** → tracking (what's done, what's next)
> - **session-notes.md** → what's active NOW

---

**Now:** Completed — merging `design/titlebar` to main.

Phase 1 (Design All 6 Menus) deliverable:

- TitleBar.svelte menggantikan Sidebar — avatar, search, 6 nav icons with tooltip, notif bell + popover, window controls
- Unified `.page-header` (36px, border-bottom, icon+title left, actions right) applied to all 6 menu pages
- 3-icon (Copy/Open/Edit SVG) + two-state pattern applied to ALL CR Number & Drone Ticket inputs across Dashboard, ProjectDetails panel, and SubProjectTable
- Backend: `frameless=True`, `get_user_profile()` with 3-tier fallback (Outlook COM → ctypes → USERNAME), `_debug` field
- Frontend: bridge wrappers, `waitForPywebviewReady()` race fix, notification click-outside

**Next:** Phase 2 (Backend/Logic) or Phase 3 (Windows Verify) — user decides.

**Blocked:** None

**active_menu:** Phase 1 — Design All Menus (done, merging)

---

## 2026-06-29

Branch aktif: `design/titlebar`  
File diubah: TitleBar.svelte (new), Sidebar.svelte → .bak, all 6 menu pages (page-header), Dashboard/ProjectDetails/SubProjectTable (3-icon CR/Drone), app_web.py, web/js_api.py, infrastructure/outlook_client.py, styles.css, App.svelte, Header.svelte, bridge.ts, various config/docs  
Keputusan teknis: D-0005 (TitleBar replaces Sidebar), D-0006 (3-icon pattern for all CR/Drone inputs)  
Verifikasi: svelte-check 0 errors, vite build clean

---

## 2026-06-27

Branch aktif: `chore/bootstrap-tooling`  
File diubah: bootstrap tooling/config docs only  
Design approved: none  
Keputusan teknis: context-mode owns tool-output compression; claude-mem owns cross-session recall; agentmemory disabled to avoid duplicate capture/injection; graphify is on-demand graph; RTK manual-only on native Windows.  
Next step: memory switch committed; start first approved design menu.  
Smoke: plugin list OK; graphify query degraded/noisy but executable; RTK OK.  
Blocked: Windows manual product verification remains separate from bootstrap.
