# PROMPT: Audit Gap + Fix — AS-IS Prototype Parity (Production-grade)

> **Copy-paste seluruh blok di bawah garis ke Claude Code.**
> Jangan ringkas. Tiap baris adalah kontrak, bukan saran.

---

## ROLL META

You are a senior full-stack engineer (Python + Svelte 5 + TypeScript + pywebview) working inside the `project_tracker` repo on branch `prd-v31-migration`.

**Hard sources of truth, in priority order — read these BEFORE you write any code:**

1. `PRD.md` v3.1 — product & business truth (state machines, folder states, validation rules G1/R3/R4/H-10).
2. `redesign_ui/project_tracker_dbs_full_prototype_v2_AS_IS_PY_INJECTED.html` — the **VISUAL & LAYOUT contract**. Every screen, panel, toolbar, control, chip, table column, metric card, and dialog below MUST exist with the same placement and visual weight.
3. `project_tracker/web/js_api.py` — the **API/bridge contract**. Real method names live here.
4. `PROJECT_STATUS.md` + `MIGRATION_PLAN.md` — phase gates. Do NOT cross phase boundaries without explicit user approval.
5. `CLAUDE.md` + `frontend-polish.md` — repo rules & visual direction.

**Your job:** The Svelte frontend has already been ported to the AS-IS chrome (tokens, sidebar, header), but a full gap audit shows it is NOT at parity — multiple controls are inert, several screens are thin shells, and a number of prototype features have no backing bridge yet. Close every gap so that **every control in the prototype is a real, working production feature** (no toast-only stubs, no "coming soon"), while honoring PRD state-machine validation and the existing pywebview bridge.

**Operating rules (non-negotiable):**

- **Ask before you build new backend scope.** If a prototype control needs a bridge method that does NOT exist in `js_api.py`, STOP and ask the user whether to (a) implement the new service+bridge now, or (b) defer it. Do not silently invent endpoints. Do not silently drop the control.
- **Never bypass a state-machine guard.** CR/Drone/Folder transitions go through the real validators (`validate_cr_transition`, `validate_cr_approved_requires_drones`, `drones_blocking_finish`, `REOPEN_ALLOWED_FOLDER_STATES`, etc.). Surfacing a guard rejection = a visible error banner, never a silent no-op.
- **No static HTML, no vanilla-JS state, no CDN, no new runtime deps** without explicit approval. Frontend = Svelte 5 runes + TS + Vite, bundled to `web/static/`. Backend = pywebview bridge.
- **Preserve what works.** Do not rewrite components that already function. Edit in place. The bridge is the contract; do not change a method's signature without updating every caller and test.
- **Filesystem is source of truth.** SQLite cache is rebuildable only. Notes primary store is `notes.md`. Project existence/state derives from folder paths.
- **Windows-only at runtime** (`os.startfile`, `send2trash`, real Outlook COM, real Teams) stays lazy/guarded and must not crash on Linux dev.

---

## PART A — Architecture & Tokens (high-level, do not deviate)

### A1. App shell — match prototype DOM exactly

- `.app-shell` (flex): `<aside.sidebar>` + `<main.main>`.
- Sidebar (`.sidebar`, char `#0A0A0B`, border-right `#2C2C30`, expanded `160px` / collapsed `52px`): brand row → `.nav` (6 buttons: Dashboard ◔, Project Details ▣, Second Brain ◆, Report ▤, Automations ⚙, Settings ◌) → `.sidebar-fill` containing the **Notifications panel** (always visible when expanded, hidden when collapsed) → `.collapse-btn` at the bottom toggling `.collapsed`.
- `<header.app-header>` is DBS red `#B91C1C`, 3-column grid: left page title (`Dashboard.` etc with `.page-title-divider`), center live clock badge, right action cluster (Year combo, search shell, filter combo, Add Project `.btn-black`, refresh `.btn-refresh`). The header config is **per-page** — Dashboard/Details are `rich` (search+filter+add); SecondBrain/Report/Automations/Settings are NOT rich (hide action cluster). See prototype `headerConfig`.
- Live clock updates every 1s, format `Mon, 01 Jun 2026 14:32:11`.

### A2. Design tokens — already ported to `frontend/src/styles.css`; keep them

- Red: `--primary-red #B91C1C`, `--red-hover #991B1B`, `--active-red #DC2626`. Soft pink surfaces for hover/secondary. Charcoal chrome `#0A0A0B`/`#141416`. Workspace white. Hairline `#E5E7EB`. Body font size 11px. Control height 26px. Header height 58px.
- State chips use the AS-IS solid red `.state-combo` / `.cr-state-select` look (red fill, white ink) — but they are now **proper dropdowns** (see B-DSH-3).
- Keep the dual alias system (`--color-*` compatibility aliases for older Svelte code) intact.

### A3. Bridge contract — front the existing methods

The frontend MUST use the typed wrapper in `frontend/src/lib/bridge.ts`:

- `callBridge<T>(method, ...args)` → `{ ok, data?, error? }`.
- `isPywebviewReady()` / `waitForPywebviewReady()` — call before first data load to avoid the startup race.
- Event polling at 1.5s (`poll_events`) → re-fetch notifications/dashboard on `AUTO_MOVE`/`NOTIFICATION`.

### A4. Verification gates (run after EVERY slice, no exceptions)

1. `npm --prefix frontend run check` — 0 errors, 0 warnings.
2. `npm --prefix frontend test` — all green (add/adjust tests for changed behavior).
3. `npm --prefix frontend run build` — Vite clean → `web/static/`.
4. `python -m pytest tests/ -q` (or the targeted phase subset) — green.
5. `python -m py_compile` over touched Python files.
6. Manual Windows WebView2 smoke is the user's gate; flag anything Windows-only you could not exercise.

---

## PART B — Per-screen gap audit & fix (the actual work)

For EACH screen below: (1) diff the prototype markup against the current Svelte component, (2) list concrete gaps, (3) fix them, (4) verify. Report a parity matrix at the end.

### B-DASH — Dashboard (`screen-dashboard`)

**Prototype contract:** filter tab row (All/UAT Prepare/Prod Ready/Implemented/Postponed with live counts + project count on the right) → table card "CR - Project Summary Table" → grid table with columns: No · Main Project · Sub Project · Start Datetime · End Datetime · Drone Ticket · Drone State · CR Number · CR State · ⋮. Rows are stack-lines so one project row shows its subprojects stacked; date cells render `Fri, 22 May 2026 / 00:00:00`; drone ticket & CR number are inline editable; ⋮ opens the row menu.

**Known gaps to verify & fix:**

- **B-DSH-1** Filter tab counts must be REAL (from `dashboard_data`/`dashboard_summary`), including Canceled. The trailing `{n} project(s)` must reflect the active tab.
- **B-DSH-2** Inline CR Number + Drone Ticket paste must call `cr_update_link` / `drone_add` / `drone_update` and append a history entry. Placeholder drone rows align with subprojects so a subproject without a ticket still shows a paste target.
- **B-DSH-3 — STATE CONTROL IS A DROPDOWN, not click-to-cycle.** Replace the prototype's click-to-cycle `.state-combo` with an accessible `<select>` (or custom listbox with keyboard nav) styled to look like the red AS-IS chip. The option list is the intersection of (PRD-legal transitions from the current state) — i.e. feed current state through the validator and only show reachable states. On change, call `cr_update_state` / `drone_update` (or `folder_reopen` when REOPEN is selected from POSTPONED/CANCELED). If the backend rejects (G1/R4), show the reason in the existing `actionError` banner and revert the select. REOPEN only appears when `cr_state` ∈ {POSTPONED, CANCELED}.
- **B-DSH-4** ⋮ row menu = **Project Details + Delete only** (per latest status; folder transitions are driven by the state dropdowns + auto-move engine). Delete uses `ConfirmModal` + lock check + `project_delete`.
- **B-DSH-5** Add Year button in the empty state MUST be wired (currently inert) — route to Header's Add-Year dialog, calling `year_create`.
- **B-DSH-6** Search debounce 200ms, name highlight, refresh spin 650ms via `refreshToken`. Keep these.

### B-DET — Project Details (`screen-details`)

**Prototype contract:** top toolbar card "Project Command Center" (Project selector · Sub Project selector · `Open` · `Delete`). Body is a 50/50 split:

- **Left pane:** Project Identity (Name, CR Number, Drone Ticket, CR State, Drone State) → Schedule (Start/End datetime) → Sub Projects (mini-table: Sub Project · Drone Ticket · Drone State, with `+ Add Sub Project`).
- **Right pane:** Files (`+ Add File`, `◇ From Template`, list box) → Notes (Edit/Preview/B/I/Link toolbar + markdown textarea, autosave to `notes.md`) → Activity History (audit trail list).

**Known gaps to verify & fix:**

- **B-DET-1** Identity edits call `project_update` (name, cr_number, drone, schedule, implementation_plan). Save button labelled `Save identity + schedule`.
- **B-DET-2** Sub Projects: `subproject_create`, drone ticket per row via `drone_add`/`drone_update`, drone state dropdown (same B-DSH-3 rules).
- **B-DET-3** Files: `file_create`, `file_create_from_template`, `file_delete`, `file_open`, `file_rename`. Unsupported file types open with Windows default; text-like files edit in-app (note the muted hint).
- **B-DET-4** Notes autosave → `notes_get` / `notes_update` writing to `notes.md` (NOT the legacy JSON field). Markdown preview uses existing `lib/markdown.ts`.
- **B-DET-5** Activity History from real history entries (STATE_CHANGE / UPDATED / NOTE).

### B-SB — Second Brain (`screen-secondbrain`)

Two stacks: **Notes** and **Link Bank** (tab buttons `.sb-tab`).

**Notes stack gaps:**

- **B-SB-1** Pinned / Favorites / Second Brain Notes / Project Documents tree groups — drive from `second_brain_list` metadata + pin/favorite flags (`second_brain_pin`, `second_brain_favorite`).
- **B-SB-2** "Add Folder" is currently inert. → requires new bridge (ASK): `second_brain_folder_create`. Until approved, leave disabled with a tooltip stating why — do not leave it as a no-op.
- **B-SB-3** "Add File" → `second_brain_note_create` (already wired) — but also support non-`.md` text files; the prototype filter lists `.md/.txt/.py/.sql/.json`. Map each to a create path or ASK for the generic `second_brain_file_create` bridge.
- **B-SB-4** Editor toolbar (Bold/Italic/H1/H2/Code/Link/Quote) must insert markdown into the textarea and persist via `second_brain_note_write`. Backlinks/Recent Activity can be best-effort from tags + history.

**Link Bank stack gaps (biggest divergence from prototype):**
The prototype Link Bank is a category-first 3-pane workspace: left categories list, middle quick-edit form, right link detail list + selected-link detail. Current `SecondBrain.svelte` only does flat CRUD.

- **B-SB-5** Category management — **Add / Rename / Archive category**. Requires new bridges (ASK): `linkbank_category_create`, `linkbank_category_rename`, `linkbank_category_archive`. Current store: `link_bank.json`.
- **B-SB-6** **Import / Export links** (toolbar `⇪ Import` / `⇩ Export`). Requires new bridges (ASK): `linkbank_import`, `linkbank_export`. Decide format (JSON) and confirm with user.
- **B-SB-7** Per-link **Pin / Favorite toggle** with badge rewrite (`pinLinkBtn`/`favoriteLinkBtn`). Likely needs a `linkbank_pin`/`linkbank_favorite` bridge or an extension of `linkbank_update` — ASK which.
- **B-SB-8** **Date filter button** cycling `All dates | 20260529 | …` (left category search) + dual sort dropdowns (Newest/Oldest/A-Z/Favorite/Pinned) kept in sync between left search sort and right detail sort.
- **B-SB-9** **Copy URL** (`navigator.clipboard`), **Edit**, **Remove/Archive** (`linkbank_archive_link`) — Remove currently archives; confirm whether a hard `linkbank_delete` is also wanted (ASK).
- **B-SB-10** Search haystack = title + url + details + category + path + tags. "Search Results" pseudo-category when a query is active.

### B-REP — Report (`screen-report`)

**Prototype contract:** filter row (Year · Folder State · CR State · search · Clear · `Export CSV`) → 5 metric cards (Total CR, UAT_PREPARE, PROD_READY, IMPLEMENTED, POSTPONED) → report table (Year · Project · Folder State · CR State · Drone State · Start · End).

- **B-REP-1** Filters + counts from `report_filter_projects` / `dashboard_summary`. CSV via `report_export_csv` (Windows save dialog).
- **B-REP-2** Metric cards reflect real counts for the selected year/filter.

### B-AUTO — Automations (`screen-automations`) — **currently a 49-line shell, biggest build**

Three stacks: **Outlook** · **Teams** · **Reminder** (`.sb-tab`).

**Outlook stack (splitter):**

- **B-AUTO-1** Left: "Outlook Send Automation" table (Category · Purpose · Conditions) with dbl-click → Outlook Automation Editor DIALOG (`.dialog-backdrop`/`.dialog`): CR State, Drone State, Project Name Pattern, Body Template (textarea), HTML body checkbox, Preview, Save Template. Right: "Send Log" list.
- **B-AUTO-2** Right pane: "Outlook Download Automation" table (Name · Folder · Status) + "Downloaded Email" button + "Download Log".
- **B-AUTO-3** Backend wiring: `outlook_draft_email` (draft-first default), `outlook_send_email` (explicit confirm only), `outlook_download_emails`, `outlook_get_contacts`. Template CRUD requires new bridges (ASK): `outlook_list_templates`, `outlook_save_template`, `automation_template_create`.

**Teams stack (split 7/3):**

- **B-AUTO-4** Left: "Teams Message Automation" table (Active checkbox · Name · Target · Template) + `Open Automation` (deep link + clipboard + countdown, preview-first default). Right: Teams Status metric cards (Saved / Active automation counts).
- **B-AUTO-5** Backend wiring: `preview_message` (Teams preview/paste-first), guarded auto-send only with explicit confirmation. Persistence of automation rows requires new bridge (ASK): `teams_list_automations` + a save/toggle — confirm data store with user.

**Reminder stack:**

- **B-AUTO-6** Metric row (Due Soon / Overdue / Postponed / Reminder Rules) + "Reminder Rules" table (Rule · Condition · Action) with `Import Rule` / `+ Add Reminder`.
- **B-AUTO-7** Backend wiring: `scheduler_*` (entry create/update/delete/toggle, run*once, start/stop, status) + `rules*\*`(create/update/delete/toggle/list) +`automation_evaluate_rule`/`automation_evaluate_all`. H-10 reminder lives in `core/rules.py` (`compute_h10`/`h10_reminder_due`, `h10_reminder_days` setting).

### B-SET — Settings (`screen-settings`)

**Prototype contract:** splitter — left: General (Display Name, Language, Datetime Format, Theme) + Behavior (T-10 Threshold Days, Auto Refresh, Startup Behavior) + Paths (Root Folder, Second Brain Folder, File Template Folder, each with Browse). Right: Help Center (search + local help content).

- **B-SET-1** Load/save via `settings_get` / `settings_set`-equivalent. Browse buttons open native folder picker (`folder_open`/`os.startfile` guarded) with manual-path fallback.
- **B-SET-2** Help Center search over local help content.

---

## PART C — Mandatory behavior & accessibility

- **C1** Every control that mutates state shows loading spinner while pending, surfaces backend errors in a banner (not a silent revert), and disables itself during the request.
- **C2** All dropdowns/selects are keyboard accessible (arrow keys, Esc to close), show focus ring (`*:focus-visible` already defined), and trap no broken focus.
- **C3** No `alert()`/`prompt()`/`confirm()` — use the existing `ConfirmModal` / banner / toast components.
- **C4** Empty states use `.table-empty` with a real CTA (e.g. "No projects — Add Project"), never a blank panel.
- **C5** Responsive: at `max-width: 1360px` the splitters collapse to single column and the handle hides (already in CSS) — verify each screen still reads correctly.

---

## PART D — Execution protocol (how you work)

1. **Read** the 5 source-of-truth files. Produce a 1-page **gap matrix** (screen · gap id · current state · target · bridge method · new-backend-needed Y/N) and show it to the user BEFORE coding.
2. **For every gap with new-backend-needed = Y**, ASK the user (batch them into one question list) whether to implement the backend now or defer. Do not proceed on those until answered.
3. **Work gap-by-gap**, smallest useful unit first. After each gap: run the gates in A4, report pass/fail with actual output (no "should work").
4. **Update `PROJECT_STATUS.md`** after each verified slice (the repo convention).
5. **Do not commit or push** unless the user asks. Do not delete legacy/reference files.
6. When you believe parity is reached, produce the final **parity matrix** (all gap ids → status: FIXED / DEFERRED-with-reason / BLOCKED) and the gate output.

---

## PART E — Open questions you MUST ask the user before/while working

(Present these as a single batched question list at the start.)

1. **Backend scope for "all real":** For the ~14 prototype features whose bridge does not exist (`linkbank_delete`, `linkbank_category_create/rename/archive`, `linkbank_import/export`, `second_brain_folder_create`, `second_brain_file_create`, `teams_send/preview/list_automations`, `outlook_list_templates/save_template`, `automation_template_create`) — implement all now, or defer a named subset? Note these cross PRD phase boundaries; confirm you accept the phase-scope expansion.
2. **Link Bank Remove vs Archive:** Hard delete (`linkbank_delete`) in addition to archive?
3. **Link Bank Import/Export format:** JSON? Per-category JSON? Confirm before building.
4. **Outlook template store:** New file (e.g. `outlook_templates.json` under app data) or reuse an existing store?
5. **Teams automation persistence store:** New JSON file or extend scheduler entries?
6. **State dropdown trigger styling:** keep the solid red AS-IS chip as the closed-state trigger (recommended), or switch to a native-select look?

---

## DESIGN RECOMMENDATIONS (optional enhancements — confirm before adopting)

These are NOT in the prototype; propose them, get a yes/no, then implement only if approved:

- **R-1 Skeleton + optimistic UI** on Dashboard table load (skeleton rows while `dashboard_data` resolves; optimistic chip update with rollback on validator rejection) — improves perceived performance without changing contract.
- **R-2 Inline validation hints** on state dropdowns: grey out illegal-but-reachable options with a tooltip explaining the blocker (e.g. "CR cannot be APPROVED until all drones are APPROVED — G1") instead of only surfacing the error post-call.
- **R-3 Keyboard shortcuts:** `Ctrl+K` focus global search, `Esc` close dialogs/menus, `/` focus search on the active screen.
- **R-4 Sticky filter bar + sticky table header** on Dashboard & Report for long lists (partially present — make it consistent).
- **R-5 Empty-state CTAs wired** to the real create flow (Dashboard empty → Add Project; Link Bank empty → Add Link).
- **R-6 Toast queue** instead of single toast overwrite, so concurrent confirmations (e.g. bulk state changes) don't eat each other.
- **R-7 Audit-log viewer** for Activity History with filter-by-type (STATE/NOTE/UPDATED) — current list is flat.

If any recommendation is declined, leave it out — do not sneak it in.
