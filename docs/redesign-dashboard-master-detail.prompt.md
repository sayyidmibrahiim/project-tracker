# REDESIGN PROMPT — Dashboard → Master-Detail (DBS brand)

> Paste this entire file as the first user message into your coding agent
> (Claude Code Desktop / router / any model). It is self-contained. Do not
> prepend other context. Work top-to-bottom. Token-dense by design.

---

## 0. ROLE

You are a senior frontend engineer + product designer. You redesign ONE screen
(the Dashboard) of an existing production desktop app. You write real, shipped
code (not prototypes). You think like a careful engineer who ships banking-ops
software: every change must preserve existing features, pass existing tests,
and not regress fixed bugs.

## 1. HOW TO WORK (decision framework — follow exactly)

This is HOW you behave. Old models: read twice.

1. **Plan before code.** Build a todo list before the first edit. One in-flight
   task at a time.
2. **Read before edit.** Never edit a file you have not read in this session.
   Match the surrounding code's naming, comment density, indentation, quotes.
3. **Never silently override a tested decision.** Before changing any CSS value
   or class, `grep` the test files (`frontend/tests/*.test.mjs`,
   `frontend/tests/*.test.ts`) for assertions about it. If a test locks a value,
   either update the test IN THE SAME CHANGE or STOP and ask. Never break a
   passing test without acknowledging it.
4. **Preserve every feature.** This is a LAYOUT redesign, not a feature cut.
   If you cannot find where a feature lives, search harder — do not delete it.
5. **Verify after each logical unit**, not only at the end:
   - Frontend: `cd frontend && npm test` (node:test, must stay green)
   - Types: `cd frontend && npx svelte-check --threshold error` (0 errors)
   - Backend (only if you touch .py): `cd project_tracker_root && .venv/Scripts/python.exe -m pytest --basetemp=./.pytest-tmp -q`
6. **Be direct in reports.** State what changed, what passed, what you skipped
   and why. No hedging. If a test fails, show the failure.
7. **Don't over-engineer.** Smallest diff that achieves the spec. No new deps.
   No refactors outside the dashboard scope unless required.
8. **Commit decisions, don't ask trivial questions.** Pick the obvious option,
   state it, proceed. Ask only for genuinely ambiguous product decisions.

## 2. NON-NEGOTIABLES

- DO NOT remove or hide any existing feature (full inventory in §6).
- DO NOT regress any of the 7 bug fixes in §7.
- KEEP the fonts: `StyreneB` (sans, body/UI) + `Tiempos Headline`/`Cormorant`
  (serif, display). They are load-bearing for brand voice.
- USE the DBS brand palette (§8). Primary red `#E60000`.
- DO NOT add npm dependencies. Stack is frozen.
- DO NOT touch backend Python unless a handler is genuinely broken (none are).
- DO NOT paste placeholder lorem. Real labels from existing copy.
- TARGET layout = **master-detail** (decided; mockups in §5).

## 3. PROJECT FACTS

- **App:** "Project Tracker DBS". Single-user Windows desktop app (pywebview).
  A DBS deployment/support engineer manages many CR (Change Request) projects:
  UAT→production readiness, Outlook/Teams comms, evidence, notes, folder hygiene.
- **Register:** product UI (design SERVES the work), not marketing. Dense, calm,
  modern, disciplined. NOT decorative SaaS, NOT playful, NOT neon.
- **Stack:** Svelte 5 (runes: `$state`/`$derived`/`$props`/`$effect`), TypeScript,
  Vite. Backend Python; frontend talks via `callBridge(method, ...args)` →
  `window.pywebview`. NEVER call `window.pywebview` directly; always `callBridge`.
- **Locale:** en-GB dates (dock). Keep consistent.
- **Window:** min 960×640, typically wider.
- **Key files:**
  - `frontend/src/lib/components/Dashboard.svelte` (PRIMARY target)
  - `frontend/src/lib/components/Sidebar.svelte` (bottom dock nav)
  - `frontend/src/lib/components/Header.svelte` (top bar)
  - `frontend/src/lib/components/DashboardRowMenu.svelte` (row kebab)
  - `frontend/src/lib/components/ConfirmModal.svelte` (state-change confirm)
  - `frontend/src/lib/dashboardChips.ts` (`stateChipClass`)
  - `frontend/src/styles.css` (global tokens + classes)
  - `frontend/src/lib/types.ts` (DashboardProject, DashboardRowDrone, etc.)
- **Run app:** `cd frontend && npm run dev` (Vite). pywebview bridge is mocked
  when not in the desktop shell — UI still renders.

## 4. CURRENT DASHBOARD ANATOMY (what exists today)

Top→bottom:

1. **Header** (`Header.svelte`): page title "Dashboard." + year `<select>` +
   `+` add-year (popover) + search input + "Add Project" button + refresh.
2. **Status filter bar** (inside Dashboard): tabs All / UAT Prepare / Prod Ready
   / Implemented / Postponed / Canceled — each with a count badge; a "Clear"
   button; a project count.
3. **Error banner**: pink/red, conditional.
4. **Table card** (horizontal scroll, min-width 1450px). 10 columns:

| #   | Header       | Content                                                       |
| --- | ------------ | ------------------------------------------------------------- |
| 1   | No           | row index                                                     |
| 2   | Project      | name button (open folder) + "project folder · {year}"         |
| 3   | Sub Project  | per-drone subproject name buttons (open subfolder)            |
| 4   | Start        | `<input type=datetime-local>` inline edit                     |
| 5   | End          | `<input type=datetime-local>` inline edit                     |
| 6   | Drone Ticket | per-drone: ticket id label + copy + open-link, OR paste input |
| 7   | Drone State  | per-drone coral `<select>` (custom caret)                     |
| 8   | CR Number    | cr label + copy + open-link, OR paste input                   |
| 9   | CR State     | coral `<select>` (custom caret); guarded until CR link set    |
| 10  | More         | `DashboardRowMenu` kebab (Project Details, Delete)            |

5. **Bottom dock** (`Sidebar.svelte`): icon+label pills (Dashboard, Project
   Details, Second Brain, Report, Automations, Settings, Notifications) with
   unread badge; auto-hides on idle, reappears; notifications popover.

## 5. TARGET: MASTER-DETAIL LAYOUT

Convert the 10-column horizontal-scroll table into a **slim master list + a
contextual detail panel**. No information loss — same fields, reorganized.

### 5.1 ASCII — default (a row selected)

```
┌─ HEADER ─────────────────────────────────────────────────────────────┐
│ ▌ Dashboard.        [ Year: 2026 ▾ ]  [+ ]   [⌕ search…]  [+ Project] ⟳ │
├──────────────────────────────────────────────────────────────────────┤
│ [All 12] [UAT 3] [Prod 4] [Impl 2] [Postp 1] [Canc 0]   Clear   12 of 12│
├──────────────────────────────┬───────────────────────────────────────┤
│ MASTER LIST (left ~38%)      │ DETAIL PANEL (right ~62%)              │
│  No  Project        State    │ ───────────────────────────────────── │
│  1   Acme Migration  UAT  ▸  │ Acme Migration            📂 open      │
│  2   Banking Portal  PROD    │ project folder · 2026                 │
│  3   CRM Rollout     PEND    │ ───────────────────────────────────── │
│  4   Data Lake       UAT     │ ▸ Subprojects                          │
│  5   …                         deploy    📂 open                       │
│                              │ ───────────────────────────────────── │
│  (click row → select ▸,      │ ▸ Drone Ticket                         │
│   detail fills right)        │  D-SSIDBI-159   ⧉ copy  ↗ open         │
│                              │  State: [ PENDING APPROVAL ▾ ]         │
│                              │ ───────────────────────────────────── │
│                              │ ▸ CR                                   │
│                              │  CR2026042099   ⧉ copy  ↗ open         │
│                              │  State: [ UAT ▾ ]                      │
│                              │ ───────────────────────────────────── │
│                              │ ▸ Schedule                             │
│                              │  Start: 2026-06-01 14:00               │
│                              │  End:   2026-06-15 18:00               │
├──────────────────────────────┴───────────────────────────────────────┤
│        ⌂ Dashboard   ▧ Project Details   ✦ Second Brain   …  ●Notif    │  ← DOCK (bottom)
└──────────────────────────────────────────────────────────────────────┘
```

### 5.2 ASCII — nothing selected (empty detail)

```
│ MASTER LIST                  │ Select a project to see details.       │
│  1 Acme Migration  UAT       │                                        │
│  2 Banking Portal PROD       │   ( calm empty state, DBS red accent ) │
```

### 5.3 ASCII — multiple drone/sub rows (detail expands)

A project with 2 drone subprojects shows BOTH under "Subprojects" and BOTH
drone tickets under "Drone Ticket" (each with its own State select). The
detail panel scrolls vertically. Master list is independent.

### 5.4 Rules

- Master list columns: **No, Project (name + year subtitle), State (project
  state chip via `stateChipClass`), More (kebab `DashboardRowMenu`)**.
- Clicking any master row selects it (`selectedPath: string | null`) and
  populates the detail panel. Selected row gets a visible selected style
  (DBS red left border-bar OR filled row — your call, but on-brand).
- Detail panel sections (collapsible `<details>`-like or always-open cards —
  your call; prefer always-open for ops speed): Subprojects, Drone Ticket,
  CR, Schedule. Reuse the EXACT existing inputs/selects/handlers — only the
  containing markup changes.
- Keep ALL inline edit behavior: paste inputs save on blur; datetime inputs
  save on change; state selects confirm via `ConfirmModal` on risky transitions.
- Preserve the `isSaving(...)` per-cell spinner feedback.
- Detail panel empty state when `selectedPath` is null or row filtered out.
- Responsive: below ~1100px, stack detail UNDER the master list (single column).

## 6. FEATURE INVENTORY — PRESERVE EVERY ONE

Before you finish, confirm each still works. If any is gone, you failed.

| Feature                                               | Source in current code                                                 |
| ----------------------------------------------------- | ---------------------------------------------------------------------- |
| Status filter tabs + counts + Clear                   | `Dashboard.svelte` `.dashboard-status-bar`, `summary.by_project_state` |
| Project count text                                    | `.project-count`                                                       |
| Open project folder (name click)                      | `openFolder()` → `callBridge("project_open_folder")`                   |
| Open subproject folder                                | `openSubfolder()` → `callBridge("folder_open")`                        |
| Start datetime inline edit                            | `<input type=datetime-local>` → save handler                           |
| End datetime inline edit                              | same                                                                   |
| Drone ticket: paste link                              | `saveDroneLink()` on blur                                              |
| Drone ticket: copy (per-control key)                  | `copyRichLink(url,label,key)` — key = `path:drone:idx`                 |
| Drone ticket: open link                               | `<a href>` external                                                    |
| Drone ticket: ID label from extracted `drone_ticket`  | `{d.drone_ticket \|\| "Drone Link"}`                                   |
| Drone state select + legal options                    | `onDroneStateChange`, `legalDroneOptionsFor`                           |
| Drone state "Add ticket first" guard                  | disabled `<select>` when `existingIndex<0`                             |
| CR number: paste/copy/open                            | `saveCrLink`, `copyRichLink`, `<a>`                                    |
| CR state select + legal options                       | `onCrStateChange`, `legalCrOptionsFor`                                 |
| CR state "Add CR Link First" guard                    | disabled when no `cr_link`                                             |
| State-change confirm (REOPEN etc.)                    | `pendingState` → `ConfirmModal`                                        |
| Row kebab: Project Details, Delete                    | `DashboardRowMenu.svelte`                                              |
| Loading skeletons                                     | `.dash-skel-bar`                                                       |
| Error banner                                          | `.dash-action-error`                                                   |
| Empty state (no projects) with Add Year + Add Project | existing empty branch                                                  |
| Year filter + add-year popover                        | `Header.svelte`                                                        |
| Search (debounced)                                    | `Header.svelte` `handleSearchInput`                                    |
| Add Project                                           | `Header.svelte` `onAddProject`                                         |
| Refresh                                               | `Header.svelte` `triggerRefresh`                                       |
| Dock nav (icon+label, always visible)                 | `Sidebar.svelte`                                                       |
| Notifications dock popover + unread badge             | `Sidebar.svelte`                                                       |

## 7. BUG-FIX LOCK-IN — DO NOT REGRESS

These 7 were just fixed. Your redesign must keep them fixed. Each has a test
or a concrete code expectation — honor it.

1. **Subproject open works** — `_FileServiceAdapter.open_folder` delegates to
   `filesystem.open_folder` (`project_tracker/app_web.py`). `folder_open` bridge
   must NOT raise `'NoneType' object is not callable`.
2. **Drone ticket ID shown, not "Drone Link"** — `extract_drone_ticket`
   (`project_tracker/core/rules.py`) regex `/(D-[A-Z0-9-]+)(?=\/|$|\?|#)/` matches
   trailing-segment URLs. Label uses `{d.drone_ticket || "Drone Link"}`.
3. **Copy button is per-control** — state is `copiedKey` (keyed
   `path:column:idx`), NOT a shared URL compare. Only the clicked icon flips.
4. **State dropdowns are `appearance:none` + custom caret + light `<option>`** —
   coral chip stays readable; popup is white bg / ink text. Test
   `dashboard-inline-edit.test.mjs` "state dropdowns are custom-styled with a
   caret" must pass. Applies to BOTH Dashboard AND ProjectDetails.
5. **Dock labels always visible** (icon + inline text), NOT hover-only.
6. **No caret/text overlap** on state selects (custom caret right-aligned).
7. **Paste inputs** say "Paste Drone link…" / "Paste CR link…".

ALSO keep these earlier design fixes:

- `--danger` token separate from coral for destructive actions.
- No side-stripe accent borders (`border-left:3px` accent is banned).
- Header has NO decorative datetime badge (removed).
- `.dock-hover-zone` is `pointer-events:none` (dock itself `auto`).

## 8. DESIGN TOKENS — DBS BRAND (re-anchor styles.css)

You may re-token freely but anchor on these. Keep OKLCH-friendly but hex is fine.

```css
:root {
  /* DBS brand */
  --dbs-red: #e60000; /* PRIMARY — CTAs, active nav, brand mark */
  --dbs-red-hover: #b30000; /* hover/active on red */
  --dbs-red-soft: #fdecec; /* red tint background (chips, focus wash) */
  --ink: #1e1e1e; /* DBS black — primary text */
  --ink-soft: #4a4a4a; /* secondary text */
  --muted: #6e6e6e; /* tertiary / captions */
  --muted-soft: #9a9a9a; /* placeholders, disabled text */
  --hairline: #e5e5e5; /* borders */
  --hairline-soft: #efefef;
  --surface: #ffffff; /* clean white canvas — modern productivity look */
  --surface-raised: #fafafa; /* cards, detail panel */
  --surface-sunken: #f4f4f4; /* master list zebra / inputs */
  --surface-dark: #1e1e1e; /* dock */
  --on-dark: #ffffff;

  /* semantic — keep danger distinct from brand red */
  --danger: #b5382f; /* delete/send/irreversible (cooler than dbs-red) */
  --danger-hover: #942d26;
  --success: #1e6b36; /* text */
  --success-bg: #e2f5e7;
  --warning-ink: #87590b; /* text */
  --warning-bg: #fdf2d0;
  --info-ink: #3a4a7a;
  --info-bg: #e6ecf5;

  /* fonts — DO NOT CHANGE */
  --font-display:
    "Tiempos Headline", "Cormorant Garamond", "Times New Roman", serif;
  --font:
    "StyreneB", "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    sans-serif;

  /* radii scale (snap everything to this) */
  --r-xs: 4px;
  --r-sm: 6px;
  --r-md: 8px;
  --r-lg: 12px;
  --r-pill: 9999px;
}
```

Design notes:

- Body canvas = clean white (`#FFFFFF`). The previous warm cream (`#faf9f5`) is
  RETIRED for this redesign — user wants a modern productivity look.
- DBS red is the ONE brand accent. Use it for: primary CTA, active dock item,
  selected master row indicator, focus ring. NOT for every state chip.
- Danger (delete/send) = `--danger` (#B5382F), distinct from brand red. Never
  make delete look like a primary CTA.
- Body text `--ink` on `--surface` is high contrast (≥12:1). Don't use `--muted`
  for body copy.
- Spacing: reuse `--spacing-xs/sm/md/lg/xl` (8/12/16/24/32).

## 9. CODE CONVENTIONS (match exactly)

- Svelte 5 runes only: `let x = $state(...)`, `$derived(...)`, `$props()`,
  `$effect(...)`. No `export let` / `on:click` (use `onclick=`).
- TypeScript in `<script lang="ts">`.
- Scoped styles in `<style>` per component. Global tokens in `styles.css`.
- Inline SVG icons (stroke=currentColor), 12–14px. Reuse existing SVGs from
  Header/Dashboard — don't invent new icon libraries.
- `callBridge<T>(method, ...args)` returns `{ok, data?, error?}`. Check `ok`.
- Comments: match surrounding density (these files use JSDoc on components +
  inline `//` for non-obvious logic). Explain WHY, not WHAT.
- No emoji as functional icons (the dock already moved to SVG — keep that).

## 10. EXECUTION STEPS (do in order)

1. **Read** `Dashboard.svelte`, `Header.svelte`, `Sidebar.svelte`,
   `DashboardRowMenu.svelte`, `ConfirmModal.svelte`, `dashboardChips.ts`,
   `types.ts`, and the global `styles.css`. Build a feature map in your head.
2. **Todo list** with one item per section below; one in-flight at a time.
3. **Re-token** `styles.css` `:root` to the DBS palette in §8. Update the
   alias map (the file has ~30 `--*-red`/`--canvas` compatibility aliases).
   Keep aliases working — many components reference them.
4. **Reskin** dock + header to DBS red/white (fonts unchanged).
5. **Restructure Dashboard.svelte** into master-detail per §5:
   - Add `let selectedPath: string | null = $state(null);`
   - Derive `selected = $derived(projects.find(p => p.project_path === selectedPath))`.
   - Render master list (slim) + detail panel side by side in a CSS grid
     `grid-template-columns: minmax(320px, 38fr) 1fr;` gap 12px.
   - Move each existing cell's markup into the right detail section. REUSE the
     same handlers, same `isSaving` keys, same ConfirmModal wiring.
   - Empty state when `!selected`.
6. **Responsive**: `@media (max-width:1100px){ grid→1 column, detail below }`.
7. **Update tests** that assert on layout/CSS:
   - `frontend/tests/dashboard-inline-edit.test.mjs` — re-assert the columns you
     kept and the new structure; KEEP the §7 bug-lock tests green.
   - Add a test asserting master-detail grid exists + detail empty state.
8. **Verify** (§1.5). Fix until green.
9. **Report** (§12).

## 11. ANTI-PATTERNS — DO NOT PRODUCE (auto-fail)

- Side-stripe accent borders (`border-left:>1px` colored on cards/list/alerts).
- Gradient text (`background-clip:text` + gradient).
- Glassmorphism / decorative blur cards.
- Eyebrow kickers (tiny uppercase tracked label above every section).
- Numbered section markers (01/02/03) as default scaffolding.
- Identical card grids with icon+heading+text repeated.
- Cream/sand/paper warm-neutral body bg (we are on clean white now).
- Coral-everywhere (danger ≠ brand; don't color delete/send with `--dbs-red`).
- Text overflow at narrow widths — test headings at 960px.
- Removing a feature to "clean up" — that's a fail (see §6).

## 12. REPORT FORMAT (final message)

End with exactly this structure:

```
## Done
### Verification
- frontend tests: <N>/<M> pass
- svelte-check: <N> errors
- backend tests (if touched): <N>/<M> pass
### What changed (per file)
- <file>: <one-line>
### Preserved features (§6 checklist)
- all confirmed / <list any missing + why>
### Bug-lock (§7)
- all 7 intact / <regressions>
### Deferred / flagged
- <anything you skipped + reason>
### Follow-ups for user
- <genuinely ambiguous decisions you made>
```

---

## 13. SANITY SELF-CHECK BEFORE YOU START

Answer these in your first reply (1 line each), then begin:

- Which file is the primary target? (Dashboard.svelte)
- How many features must be preserved? (count from §6)
- What is the brand primary red? (#E60000)
- Name one bug you must NOT regress. (any of §7)
- Which layout are you building? (master-detail)

If you cannot answer all five, re-read this prompt.
