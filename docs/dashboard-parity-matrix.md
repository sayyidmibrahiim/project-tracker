# Dashboard Parity Matrix

Audit of the Dashboard (PRD §11, lines 863–1030) vs the prototype
(`redesign_ui/project_tracker_clean.py` + `approved_dashboard_preview.html`) vs
current Svelte (`Dashboard.svelte`, `Header.svelte`, `App.svelte`) and backend
(`dashboard_service.py`, `js_api.py`/`app_web.py`). Drives the fix plan in
`docs/dashboard-fix-plan.md`.

| Requirement                                            | PRD §11       | Prototype                                         | Current behavior                                                                                  | Status                                             | Fix (task)            |
| ------------------------------------------------------ | ------------- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------- | -------------------------------------------------- | --------------------- |
| Header layout (title/datetime/year/search/add/refresh) | §11.2         | red header, datetime badge, year, search, +Add, ↻ | Present in `Header.svelte`                                                                        | partial                                            | T11/T12/T9            |
| Live DateTime badge                                    | §11.2         | live clock                                        | Hardcoded `"Mon, 01 Jun 2026 14:32:11"`                                                           | gap                                                | T12                   |
| Year dropdown from filesystem                          | §11.6         | year select                                       | Hardcoded `["2026","2025","2024","all"]`                                                          | gap                                                | T11                   |
| Add Year (+)                                           | §11.7         | —                                                 | Absent; no `year_create` bridge                                                                   | gap (BE)                                           | T10                   |
| Add Project                                            | §11.8         | +Add Project                                      | Button `disabled` ("deferred")                                                                    | gap                                                | T9                    |
| Refresh rescan + spin                                  | §11.14        | ↻                                                 | `App` passes `key={refreshKey}` (ignored) → no-op; no spin                                        | gap (bug)                                          | T8                    |
| First-Run Setup (root unset)                           | §11.3         | —                                                 | Absent                                                                                            | gap                                                | T14                   |
| Event polling 1.5s                                     | §11.3         | —                                                 | 5000ms                                                                                            | deviation                                          | T16                   |
| KPI Row                                                | §11.2         | merged into filter tabs                           | Filter tabs with counts (no separate KPI)                                                         | intentional deviation (matches approved prototype) | keep / T17 mini-strip |
| Filter tabs incl. Canceled                             | §11.2         | All/UAT/Prod/Impl/Postponed (no Canceled)         | All/UAT/Prod/Impl/Postponed                                                                       | gap vs PRD (matches prototype)                     | T15 (confirm)         |
| Filter by folder state (in-memory)                     | §11.4         | tabs                                              | Works (local filter)                                                                              | done                                               | —                     |
| Search debounce 200ms + highlight                      | §11.5         | search                                            | Immediate `oninput`, no debounce, no highlight; haystack lacks subproject/drone                   | gap                                                | T13                   |
| Table column: No                                       | §11.15        | row no                                            | Done                                                                                              | done                                               | —                     |
| Table: Main Project (click→folder)                     | §11.15        | red name                                          | Static text, not clickable                                                                        | gap                                                | T7                    |
| Table: Sub Project (click→folder)                      | §11.15        | stacked names                                     | **Fake**: shows project name; not clickable                                                       | gap (data)                                         | T2/T3/T7              |
| Table: Start/End DateTime                              | §11.15        | formatted                                         | Real data, formatted                                                                              | done                                               | —                     |
| Table: Drone Ticket (id+link, paste)                   | §11.15/§11.12 | stacked link editors                              | **Fake**: shows CR number; `readonly`; no paste                                                   | gap (data+edit)                                    | T2/T3/T4/T7           |
| Table: Drone State (inline dropdown)                   | §11.15/§11.11 | state buttons                                     | **Fake**: always `"—"`; static span                                                               | gap (data+edit)                                    | T2/T3/T5              |
| Table: CR Number (id+link, paste)                      | §11.15/§11.12 | link editor                                       | Real value but `readonly`; no paste/link                                                          | gap (edit)                                         | T4/T7                 |
| Table: CR State (inline dropdown)                      | §11.15/§11.10 | state button                                      | Real value but static span; no dropdown/guard/confirm                                             | gap (edit)                                         | T5                    |
| Row action ⋮ menu                                      | §11.13        | ⋮                                                 | Only `ProjectTransitions` (move/postpone/cancel/reopen); missing Open Folder, Details nav, Delete | gap                                                | T6                    |
| Right-click context menu                               | —             | — (uses ⋮)                                        | Absent                                                                                            | not a gap                                          | —                     |
| Backend row payload (subprojects + drones)             | §11.15        | —                                                 | `DashboardProject` exposes only `drone_ticket_count`                                              | gap (BE root cause)                                | T2                    |
| Empty/loading/error states                             | —             | —                                                 | Present (text); could be skeleton                                                                 | partial                                            | T17                   |

## Root cause

`DashboardProject` (`dashboard_service.py`) carries only `drone_ticket_count`, not
the sub-projects or drone-ticket details. The cache row stores `drone_tickets_json`
(parsed for count only). The frontend therefore fabricates the Sub Project / Drone
Ticket / Drone State columns. T2 enriches the payload so T3–T7 can render and edit
real data.

## Selected target

Execute `docs/dashboard-fix-plan.md` T1→T17 in order: backend data foundation
(T2) → real table + inline edits + action menu + refresh fix (T3–T8) → header
controls (T9–T16) → design polish (T17). No deps added; Windows-only stays guarded.

## Resolution (T1–T17 complete, 2026-06-09)

All A–F findings closed on Linux:

- **A1–A5** (real data + interactions): `dashboard_data` now drives real
  filter-tab counts; Dashboard renders real sub-projects + drone tickets/states;
  inline CR/Drone link paste (`cr_update_link`/`drone_update`); inline CR/Drone
  state dropdowns (IN-PROGRESS disabled, POSTPONED/CANCELED ConfirmModal, guard
  errors surfaced); clickable Main/Sub project → `project_open_folder`/`folder_open`;
  link → browser; `DashboardRowMenu` (Details nav, Open Folder, Delete+confirm+lock,
  embedded transitions).
- **B6–B9 / C10–C16**: Refresh wiring fixed (`refreshToken`) + 650ms spin; Add
  Project → NEW_PROJECT; Add Year (+) dialog + new `year_create` backend; year
  dropdown from `year_list`; live DateTime clock; search debounce 200ms + name
  highlight + extended haystack; First-Run Setup overlay; Canceled filter tab;
  poll interval 1.5s.
- **F / T17**: sticky table header, row hover, skeleton loading, empty-state CTA.

Deviations (documented): CR/Drone state inline change updates state only and does
NOT auto-move the folder (follows the product-context independence model over PRD
§11.10's folder-move coupling); folder moves remain in the row menu's transitions.
Right-click context menu intentionally not added (prototype/PRD use the ⋮ button).
Windows-only at runtime: Open Folder, link-open, native folder picker (manual path
fallback provided). Verified Linux: svelte-check 0/0, build clean, frontend 87
tests, pytest 1700, py_compile OK.
