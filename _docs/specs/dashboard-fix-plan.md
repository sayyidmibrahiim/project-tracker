# Dashboard Fix Plan — findings A–F

Plan to close the Dashboard audit findings (menu: Dashboard / PRD §11). Planning
only; execution is gated on user approval. Principles: PRD §11 = truth, prototype
(`project_tracker_clean.py` + `approved_dashboard_preview.html`) = visual
reference, no fake data, no dependency changes, no `js_api` signature change
unless proven necessary (with tests+docs in the same slice), Windows-only stays
guarded, verify all gates at the end of each phase.

Legend: **FE** frontend · **BE** backend (+test/contract care) · **WIN**
Windows-only/manual · dep = depends on.

---

## Phase 1 — Backend data foundation (unblocks the real table) — P0

- [ ] **T1. Dashboard parity matrix doc** (docs-only). Write
      `docs/dashboard-parity-matrix.md` (PRD §11 vs prototype vs current) like the
      Automations/Project-Details matrices.
- [ ] **T2. Embed sub-projects + drone tickets in the Dashboard payload** (BE).
      Root cause of finding A1: `DashboardProject` only carries `drone_ticket_count`.
      Extend the dashboard read path so each row exposes its sub-projects and drone
      tickets (`subfolder_name`, `drone_ticket`/link, `drone_state`, `owner`).
      Options: (a) enrich `DashboardProject` (+ `_to_frontend_safe`) from the cache
      `drone_tickets_json` and a subproject scan, or (b) add a
      `dashboard_drone_tickets`/`dashboard_rows` bridge. Prefer (a) to avoid N calls.
      Update `dashboard_service` + DTO + `js_api`/`app_web` mapping + frontend
      `DashboardProject` type + affected pytest. Keep `project_state` out of JSON
      truth rules intact.

## Phase 2 — Real Dashboard table + interactions — P0

- [ ] **T3. Replace fake column mapping with real data** (FE, dep T2). Fix
      `mapProjectToRow`: real sub-projects, real drone tickets/states (multi-line
      stacked rows per prototype), remove `project_name`→subproject and
      `cr_number`→drone fakes (findings A1).
- [ ] **T4. Inline CR/Drone link paste** (FE; bridges `cr_update_link`,
      `drone_update`). Editable cell → paste URL → blur/Enter saves → show extracted
      id → reload row (PRD §11.12, finding A2).
- [ ] **T5. Inline CR/Drone state dropdowns + guard + confirm** (FE; bridges
      `cr_update_state`, `drone_update`). Valid-next-state dropdown; IN-PROGRESS
      disabled; POSTPONED/CANCELED confirmation modal; surface guard failures
      (PRD §11.10/§11.11, finding A3). Reuse `ConfirmModal`.
- [ ] **T6. Complete row action ⋮ menu** (FE; bridges `project_open_folder`/
      `folder_open`, `project_delete`, + navigate). Add Open Project Folder,
      Project Details (navigate to SHOW_EDIT), Delete (Recycle Bin, confirm),
      alongside existing transitions (PRD §11.13, finding A4). Respect locks.
- [ ] **T7. Clickable Main/Sub project → open folder; CR/Drone link → browser**
      (FE; `folder_open`, and an open-URL path) (PRD §11.15, finding A5). WIN runtime.
- [ ] **T8. Fix Refresh wiring + spin animation** (FE). `App.svelte` passes
      `key={refreshKey}` (ignored, not a Svelte keyed attr) so Refresh is a no-op.
      Pass a tracked prop (e.g. `refreshToken`) that Dashboard's `$effect` reads, or
      `bind:this` + call `refresh()`. Add 650ms spin (PRD §11.14, finding B6).

## Phase 3 — Header controls & flows — P1

- [ ] **T9. Wire Add Project → NEW_PROJECT mode** (FE; `App` + `ProjectDetails`).
      Enable the disabled button; navigate to Project Details and open the
      NewProjectForm (PRD §11.8, finding B7).
- [ ] **T10. Add Year (+) dialog + create year folders** (BE+FE). No `year_create`
      bridge exists → add one that creates `{ROOT}/{YEAR}/` + the 5 state folders,
      with the `> current_year+2` confirmation; refresh year list (PRD §11.7,
      finding B8). BE method + tests.
- [ ] **T11. Year dropdown from `year_list`** (FE). Replace hardcoded
      `["2026","2025","2024","all"]` in `Header.svelte` with `year_list` data
      (PRD §11.6, finding C10).
- [ ] **T12. Live DateTime badge** (FE). Replace the hardcoded string with a
      ticking clock formatted per settings (PRD §11.2, finding C11).
- [ ] **T13. Search debounce 200ms + highlight + extend haystack** (FE). Debounce,
      highlight matches, include sub-project/drone once T2/T3 land (PRD §11.5,
      finding C12).
- [ ] **T14. First-Run Setup** (FE + WIN). If `root_folder` unset, show a setup
      panel; set via `settings_update`; native folder picker is Windows-only with a
      manual-path fallback (PRD §11.3, finding C13).
- [ ] **T15. Add "Canceled" filter tab** (FE). Add the missing `Canceled (n)` tab
      (PRD §11.2, finding C14). Note: prototype omits it — confirm keep vs PRD.
- [ ] **T16. Event poll interval 1.5s** (FE, optional). Align `POLL_INTERVAL_MS`
      with PRD §11.3 (currently 5s) — confirm desired (finding C15).

## Phase 4 — Design polish (utilitarian + modern minimalist) — P2

- [ ] **T17. Table polish** (FE). Sticky header on scroll, subtle zebra + row
      hover, per-state colored badges (not all-red), skeleton loading, richer
      empty-state CTA ("Add Project") (finding F).

## Not a gap / out of scope

- **D. Right-click context menu**: not required by PRD or prototype (actions are
  via the ⋮ button). No action unless explicitly requested.
- **KPI Row (PRD §11.2)**: intentionally merged into filter-tabs-with-counts per
  the approved prototype. Keep as-is (optional mini-KPI strip is T17).
- **Schedule/Start-End editing**: no editor exists app-wide; out of Dashboard scope.

## Sequencing & gates

T1 → T2 (BE) → T3 (needs T2) → T4,T5,T6,T7,T8 (FE, parallelizable) → Phase 3 →
Phase 4. After each phase: `svelte-check`, `vite build`, frontend `node --test`,
`pytest`, `py_compile` — all green. Commit per coherent slice.
