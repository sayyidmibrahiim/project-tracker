# Progress

> Single status source. Full history: `_docs/_archive/PROJECT_STATUS_history.md`

## Current Work

Phase labels are deprecated for active work. Work now follows `{menu}/{desc}` branches from `main`.

Active branch: `general/appcode-structure`.
Active slice: Appcode folder structure + CR/Non-CR project types — new folder tree, ProjectType/NonCrState enums, drone rename, scanner/cache/model updates. Piece A of 4.

Previous completed area remains fixed: frameless titlebar, Dashboard, and Project Details layout decisions are implemented and should not be overwritten by `_reference/`.

## Active Blockers

- Windows-only runtime (Outlook COM, Teams pyautogui, os.startfile, PyInstaller) not yet verified — requires manual Windows testing.
- Avatar initials show "A" (single-part Windows username) instead of "AA" (Azzahra Ara) — Outlook COM not fully configured.

## Pending

| Area                | Status                  |
| ------------------- | ----------------------- |
| UX feature pack     | Done, pending user verify |
| Global App Plan     | Done, pending user verify |
| Report              | Done, pending user verify |
| Second Brain        | Done, pending user verify |
| Automations         | Done, pending user verify |
| Settings            | Done, pending user verify |
| Windows verify      | Not started (needs real Windows) |
| Packaging           | Not started |

## Last 4 Completed Slices

1. **UX feature pack** (2026-07-01, branch `general/ux-features`): Toast system (toastStore + Toast.svelte + App.svelte mount) wired into all save sites (Settings, Dashboard, ProjectDetails, EmailTemplateDialog). GlobalPlan, Report, SecondBrain inline feedback → toast store. Settings autosave (1500ms debounce + dirty flag). Undo toasts (CR link, CR state, Drone link/state) with 5s timeout. TitleBar `?` keyboard-shortcut popover. First-run WelcomeGuide overlay (localStorage once-and-never).
2. **Production-readiness pass** (2026-07-01, branch `general/global-plan`): cross-menu fix sweep. Global Plan productionized as official menu 7 with drag/drop; seeded full audit backlog. Scheduler trigger now targets real entry with real project provider; metrics derived from real entries. Rules Execute exposed separately from Evaluate. Report gains Month + Drone filters, CR/Drone/Monthly summaries, expanded columns, native save-dialog CSV with UTF-8 BOM + Blob fallback. Second Brain search/sort/type/date filters wired; Link Bank export/import/rename/restore added. Settings theme switch removed (PRD fixed theme), validation + restart notice added.
3. **CLAUDE.md Cold Start + Verification Rule Update** (2026-06-30): Truth order now starts from cold-start docs; `_reference/` cannot override implemented titlebar/Dashboard/Project Details decisions; default verification is app-run unless full tests are requested.
4. **Design All 6 Menus + Titlebar** (2026-06-29): Frameless `pywebview` titlebar with avatar/search/nav/notif/window-controls. Unified `.page-header` pattern across all 6 menus. 3-icon (Copy/Open/Edit) + two-state pattern on all CR Number & Drone Ticket inputs. Branch: `design/titlebar`.

## Verification (latest)

```
svelte-check: 0 errors, 4 pre-existing SubProjectTable a11y warnings
app startup: runs, no traceback (2026-07-01)
python imports: ok
```
