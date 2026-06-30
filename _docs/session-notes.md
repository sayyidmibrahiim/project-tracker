# Session Notes

> Brief recovery ledger. Do not paste transcripts or secrets.
>
> - **DECISIONS.md** → permanent ADRs (why)
> - **PROGRESS.md** → tracking (what's done, what's next)
> - **session-notes.md** → what's active NOW

---

**Now:** Production-readiness pass done on `general/global-plan`, pending user manual verify.

Cross-menu fix sweep (one-time branch scope override approved by user):

- Global Plan: productionized as official menu 7, native HTML5 drag/drop (status + reorder), seeded all 17 audit backlog items.
- Automations: scheduler `project_provider` now real (was `lambda: []`); added `scheduler_entry_trigger` bridge + UI target entry; metrics derived from real entries (no more hardcoded `0`); rules Execute exposed separately from preview Evaluate.
- Report: Month + Drone State filters; CR/Drone/Monthly summary cards; expanded table columns (#, CR Number, T-10, Last Updated); native save-dialog CSV with UTF-8 BOM, Blob fallback.
- Second Brain: wired search/sort/type/date filters to real filesystem notes; added Link Bank export/import/rename/restore.
- Settings: removed Theme switch (PRD = fixed theme); added T-10/numeric validation, trailing-slash guard, restart-required notice.

**Next:** User manual verify across all menus. Then Windows runtime verification + packaging (needs real Windows).

**Blocked:** None in code. Windows runtime + packaging need a real Windows machine.

**active_menu:** general/global-plan (cross-menu sweep)

---

## 2026-07-01

Branch aktif: `general/global-plan`
File diubah: `CLAUDE.md`, `_docs/PROGRESS.md`, `_docs/session-notes.md`, `services/global_plan_service.py`, `web/js_api.py`, `app_web.py`, `frontend/src/lib/types.ts`, `frontend/src/lib/bridge.ts`, `frontend/src/lib/components/GlobalPlan.svelte`, `frontend/src/App.svelte`, `frontend/src/lib/components/TitleBar.svelte`, `frontend/src/lib/components/Header.svelte`, `frontend/src/lib/components/Report.svelte`, `frontend/src/lib/components/SecondBrain.svelte`, `frontend/src/lib/components/Settings.svelte`, `frontend/src/lib/components/Automations.svelte`, `frontend/src/lib/components/SchedulerActions.svelte`, `frontend/src/lib/components/RulesActions.svelte`
Keputusan teknis: one-branch multi-menu override (explicit user approval); Global Plan is official menu 7; scheduler real project provider; native save dialog with fallback; no new dependency.
Verifikasi: svelte-check 0 errors (4 pre-existing SubProjectTable a11y warnings); python imports ok; app startup ok.

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
Smoke: plugin list OK; graphify query degraded/noisy but executable; RTK OK.
Blocked: Windows manual product verification remains separate from bootstrap.
