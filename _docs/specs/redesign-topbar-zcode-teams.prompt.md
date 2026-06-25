# REDESIGN PROMPT — Top Bar / App Title (ZCode + Teams aesthetic, DBS brand)

> Paste this ENTIRE file as the first message into Claude Code Desktop (any model
> in your router). It is self-contained. Do not prepend other context.
> Work top-to-bottom. Token-dense by design (cheap for GLM 5.2 / old models).

---

## 0. ROLE

You are a senior frontend engineer + product designer. You redesign the TOP
of one screen of an existing production desktop app to look like a modern,
professional productivity tool (ZCode / Microsoft Teams title bar) while keeping
every existing feature working.

You write real, shipped code — not prototypes. You think like a careful engineer
shipping banking-ops software: every change preserves features, passes tests,
and does not regress fixed bugs. You match the surrounding code's style exactly.

---

## 1. HOW TO WORK (follow exactly — even old models)

1. **Plan before code.** Build a todo list before the first edit. One in-flight task at a time.
2. **Read before edit.** Never edit a file you have not read this session. Match naming, comment density, indentation, quotes.
3. **Never silently override a tested decision.** `grep` `frontend/tests/*.test.mjs` for assertions about any CSS value/class before changing it. If a test locks it, update the test in the SAME change or STOP and ask.
4. **Preserve every feature.** This is a layout/skin change, not a feature cut.
5. **Verify after each logical unit:**
   - `cd frontend && npm test` (node:test — must stay green)
   - `cd frontend && npx svelte-check --threshold error` (0 errors)
6. **Be direct.** State what changed, what passed, what you skipped + why. Show real test output. No hedging.
7. **Don't over-engineer.** Smallest diff achieving the spec. No new deps.
8. **Decide, don't waffle.** Pick the obvious option, state it, proceed. Ask only for genuinely ambiguous product decisions.

---

## 2. NON-NEGOTIABLES

- DO NOT remove or hide any existing header feature (full inventory in §7).
- DO NOT regress the 7 bug fixes in §8.
- KEEP the fonts: `StyreneB` (sans, UI/body) + `Tiempos Headline` / `Cormorant` (serif, display). Load-bearing.
- USE the DBS brand palette (§5). Primary red `#E60000`.
- The DBS logo (§6) MUST appear in the top bar — recreate as inline SVG, do NOT use an external image file.
- DO NOT add npm dependencies. Stack frozen.
- DO NOT touch backend Python.
- TARGET = a persistent **app title bar at the very top** (like ZCode/Teams) + a cleaner nav treatment. NOT a redesign of the dashboard table itself (that's a separate task).

---

## 3. PROJECT FACTS

- **App:** "Project Tracker DBS". Single-user Windows desktop app (pywebview). A DBS engineer manages many Change-Request projects: UAT → production readiness, comms, evidence, folder hygiene.
- **Register:** product UI (design SERVES the work). Dense, calm, modern, disciplined. NOT decorative SaaS, NOT playful, NOT neon.
- **Stack:** Svelte 5 runes (`$state`/`$derived`/`$props`/`$effect`), TypeScript, Vite. Talks to Python via `callBridge(method, ...args)` → `window.pywebview`. NEVER call `window.pywebview` directly.
- **Window:** min 960×640, typically wider.

### Current app shell (App.svelte)

- `<Sidebar>` = bottom dock nav (icon + inline label pills), auto-hides on idle, reappears. Contains brand mark "PT", 6 nav items (Dashboard, Project Details, Second Brain, Report, Automations, Settings) + Notifications button with unread badge + notifications popover.
- `<main class="main">` = content area; renders `<Header>` then the active screen component.

### Current Header (Header.svelte) — the thing you are redesigning

- `<header class="app-header">` is a 2-column CSS grid: title (left) + actions (right).
- Left: `page-title-divider` (4px red bar) + `<h1 class="page-title">` = per-page title ("Dashboard.", "Project Details.", etc.).
- Right (only when `cfg.rich`, i.e. dashboard + project-detail): year `<select class="combo">` + add-year `+` button (opens `.header-year-pop` popover with number input + warn/err + Cancel/Create) + search shell (`.search-shell` with SVG icon + `<input class="input">`) + "Add Project" `.btn-black` + refresh button (`.refresh-button` with spinning SVG).
- `headerConfig` per page: which controls show. dashboard & project-detail are "rich"; the other 4 pages are bare (just title + refresh).
- Handlers (KEEP ALL): `triggerRefresh`, `toggleAddYear`, `submitAddYear`, `handleYearInput`, `handleSearchInput` (200ms debounce), `onAddProject`.

---

## 4. TARGET: ZCode / Teams-style app title bar

### 4.1 Reference analysis (what "professional" means here)

**ZCode top bar (reference 1):** full-width fixed-height horizontal bar, split into 3 zones:

- LEFT: app logo/icon (small) + app wordmark name.
- CENTER: navigation tabs (flat, text labels; active = subtle filled/underlined pill, inactive = muted). No heavy borders.
- RIGHT: a slim search input + a few action icons.
- Aesthetic: flat, calm, single hairline border at the BOTTOM separating it from content. No gradients, no shadows, no heavy chrome. Clean IDE/tool feel.

**Microsoft Teams title bar (reference 2):** slim (~28–32px) horizontal bar:

- LEFT: app logo + app name.
- CENTER/RIGHT: search bar, then window-control area.
- Color: dark OR light depending on theme, but always a SINGLE solid tone, never busy.
- Aesthetic: minimal, quiet, lets the content breathe. The bar is a frame, not a feature.

**Common principles to apply (both refs):**

1. The top bar is PERSISTENT — always visible regardless of page.
2. Logo + app name on the far LEFT. This is the app's identity, always there.
3. A slim search and/or action cluster on the RIGHT.
4. The bar is FLAT: one solid background, one hairline bottom border, no shadows/gradients.
5. Height is modest (~44–48px for a desktop app, not 64+). Dense.
6. Per-page title ("Dashboard.") moves BELOW the bar or becomes the first nav tab's label — it is NOT the bar's main content.

### 4.2 Target layout (ASCII)

```
┌─ APP TITLE BAR (persistent, ~46px) ──────────────────────────────────────────┐
│ [◆] Project Tracker DBS    Dashboard   Project Details   Report   Automations │
│  logo  wordmark      ↑ nav tabs (center-left)            [⌕ search]  [+ Proj] │
└──────────────────────────────────────────────── hairline bottom border ───────┘
┌─ PAGE SUB-HEADER (only on dashboard/project-detail) ──────────────────────────┐
│   Dashboard.         [Year: 2026 ▾] [+ Add Year]                  ⟳ Refresh    │
│   ▌ (red accent)     (page-specific controls)                                  │
└───────────────────────────────────────────────────────────────────────────────┘
┌─ CONTENT (status tabs, table, etc.) ──────────────────────────────────────────┐
│   [All 12] [UAT 3] [Prod 4] …                                                  │
```

### 4.3 Rules

- **App title bar (NEW, persistent):** spans full width, always on top. Contains:
  - LEFT: DBS logo SVG (§6, ~22px) + wordmark "Project Tracker DBS" (the "DBS" in DBS red `#E60000`, rest in ink). Clicking it navigates to Dashboard.
  - CENTER-LEFT: horizontal nav tabs for the 6 pages (Dashboard, Project Details, Second Brain, Report, Automations, Settings). Active tab = DBS red text + a 2px bottom indicator bar; inactive = `--muted` text, no indicator. Hover = ink text. Flat, no card backgrounds. This REUSES the `navItems` array and `onNavigate` from Sidebar.
  - RIGHT: search input (slim, only meaningful on dashboard/project-detail but may always render) + "Add Project" primary button (DBS red). Keep the year/add-year + refresh in the PAGE SUB-HEADER (below), not the top bar — they are page-specific.
- **Page sub-header (REFACTORED existing Header.svelte):** below the app bar. Shows: red accent divider + page title (h1, serif) on the left; page-specific controls (year select, add-year popover, refresh) on the right. Only present where `cfg.rich` is true; on bare pages, just the title (or omit entirely if the nav tab already labels the page — your call, state it).
- **Bottom dock (`Sidebar.svelte`):** KEEP the dock as-is for now (icon+label pills, auto-hide, notifications popover). Do NOT delete it — some users may rely on it; the top nav tabs and the dock can coexist. Just make sure the top bar is the PRIMARY nav now.
- **Window controls:** pywebview already provides native window controls — do NOT add fake minimize/maximize/close buttons.
- Colors: top bar background = `--surface` (white) OR a very subtle `--surface-raised`; bottom hairline = `--hairline`. Do NOT make the bar dark/colored — ZCode/Teams light variant is the reference.

---

## 5. DESIGN TOKENS — DBS brand (re-anchor styles.css `:root`)

```css
:root {
  /* DBS brand */
  --dbs-red: #e60000; /* PRIMARY — logo, wordmark accent, active tab, CTA */
  --dbs-red-hover: #b30000;
  --dbs-red-soft: #fdecec; /* red wash for hover/focus on nav */
  --ink: #1e1e1e; /* primary text */
  --ink-soft: #4a4a4a;
  --muted: #6e6e6e; /* inactive nav, captions */
  --muted-soft: #9a9a9a; /* placeholders */
  --hairline: #e5e5e5;
  --hairline-soft: #efefef;
  --surface: #ffffff; /* top bar + canvas */
  --surface-raised: #fafafa;
  --surface-sunken: #f4f4f4;
  --surface-dark: #1e1e1e; /* dock */
  --on-dark: #ffffff;

  /* semantic — danger stays distinct from brand red */
  --danger: #b5382f;
  --danger-hover: #942d26;

  /* fonts — DO NOT CHANGE */
  --font-display:
    "Tiempos Headline", "Cormorant Garamond", "Times New Roman", serif;
  --font:
    "StyreneB", "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    sans-serif;

  --r-sm: 6px;
  --r-md: 8px;
  --r-lg: 12px;
  --r-pill: 9999px;
  --bar-h: 46px; /* app title bar height */
}
```

- Keep ALL existing compatibility aliases in styles.css working (many components reference `--primary-red`, `--canvas`, `--color-dbs-red`, etc.). Re-anchor them to the new DBS values, don't delete them.
- Body text `--ink` on `--surface` is ≥12:1 — do not use `--muted` for body copy.

---

## 6. DBS LOGO — recreate as inline SVG (do NOT use an image file)

The logo from the user's reference: a **hexagonal/clipped-square container in DBS red `#E60000`**, containing a **white 5-point star (asterisk/flower) mark** — minimalist, modern, corporate-tech.

Recreate as an inline SVG, ~22px, used in the top bar. Use this exact markup (red rounded-square tile + white star):

```html
<svg
  width="22"
  height="22"
  viewBox="0 0 24 24"
  fill="none"
  xmlns="http://www.w3.org/2000/svg"
  aria-hidden="true"
>
  <rect width="24" height="24" rx="5" fill="#E60000"></rect>
  <path
    d="M12 4 L13.6 9.2 L18.8 7.6 L15.2 11.8 L19.6 15.2 L14.2 14.6 L13.8 20 L12 15.2 L10.2 20 L9.8 14.6 L4.4 15.2 L8.8 11.8 L5.2 7.6 L10.4 9.2 Z"
    fill="#FFFFFF"
  ></path>
</svg>
```

- The white star is a stylized 5-point bloom inside the red tile. If a reviewer says it doesn't match DBS exactly, keep the red-tile + white-star concept (it reads as "DBS" instantly) — exact geometric fidelity to the official mark is not required; brand-recognition is.
- Wrap it in a clickable element that navigates to Dashboard.

---

## 7. FEATURE INVENTORY — PRESERVE EVERY ONE

Before you finish, confirm each still works. If any is gone, you failed.

| Feature                                                                      | Source                                                             |
| ---------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| Per-page title (h1)                                                          | Header.svelte `headerConfig[currentPage].title`                    |
| Year `<select>` filter                                                       | Header.svelte `.combo`, `handleYearInput`                          |
| Add-year `+` button + popover (input, warn, err, Cancel/Create)              | Header.svelte `toggleAddYear`, `submitAddYear`, `.header-year-pop` |
| Search input (200ms debounce)                                                | Header.svelte `.search-shell`, `handleSearchInput`                 |
| "Add Project" primary action                                                 | Header.svelte `.btn-black` → `onAddProject`                        |
| Refresh button (650ms spin)                                                  | Header.svelte `.refresh-button`, `triggerRefresh`                  |
| `showDashboardControls` (year/search/add only on dashboard + project-detail) | Header.svelte prop                                                 |
| Nav to all 6 pages                                                           | Sidebar.svelte `navItems` + `onNavigate`                           |
| Notifications dock button + unread badge + popover                           | Sidebar.svelte                                                     |
| Bottom dock (icon+label, auto-hide)                                          | Sidebar.svelte — KEEP, do not delete                               |

The app title bar must surface: logo → Dashboard, wordmark → Dashboard, the 6 nav tabs → `onNavigate(id)`, search → `onSearchChange`, Add Project → `onAddProject`.

---

## 8. BUG-FIX LOCK-IN — DO NOT REGRESS

1. Subproject open works (`_FileServiceAdapter.open_folder` delegates to `filesystem.open_folder`; `folder_open` bridge must not raise).
2. Drone ticket ID shown, not "Drone Link" (`extract_drone_ticket` regex `/(D-[A-Z0-9-]+)(?=\/|$|\?|#)/`; label `{d.drone_ticket || "Drone Link"}`).
3. Copy button is per-control (`copiedKey` keyed `path:column:idx`, not shared URL).
4. State dropdowns are `appearance:none` + custom caret + light `<option>` (test `dashboard-inline-edit.test.mjs` "state dropdowns are custom-styled with a caret" must pass; applies to Dashboard AND ProjectDetails).
5. Dock labels always visible (icon + inline text), NOT hover-only.
6. No caret/text overlap on state selects (custom caret right-aligned).
7. Paste inputs say "Paste Drone link…" / "Paste CR link…".

Also keep: `--danger` token separate from brand red; no side-stripe accent borders; `.dock-hover-zone` is `pointer-events:none`.

---

## 9. CODE CONVENTIONS (match exactly)

- Svelte 5 runes only (`$state`, `$derived`, `$props`, `$effect`). No `export let`, no `on:click` (use `onclick=`).
- `<script lang="ts">`. Scoped `<style>` per component; global tokens in `styles.css`.
- Inline SVG icons (stroke=currentColor), 12–14px. Reuse existing SVGs.
- `callBridge<T>(method, ...args)` → `{ok, data?, error?}`. Check `ok`.
- Comments match surrounding density (JSDoc on components + `//` for non-obvious logic). Explain WHY.

---

## 10. EXECUTION STEPS (do in order)

1. **Read** `App.svelte`, `Header.svelte`, `Sidebar.svelte`, `styles.css`, `frontend/tests/dashboard-inline-edit.test.mjs`, `frontend/tests/components.test.mjs`. Build a feature map.
2. **Todo list**, one item per step below; one in-flight at a time.
3. **Re-token** `styles.css` `:root` to the DBS palette (§5). Keep all compatibility aliases resolving.
4. **Create the app title bar component.** Options:
   - (A) New component `TopBar.svelte` rendered in App.svelte above `<main>` — cleanest separation. (RECOMMENDED)
   - (B) Fold it into `Header.svelte`. (Only if you have a strong reason.)
     Pick (A). It takes `currentPage`, `onNavigate`, `searchQuery`, `onSearchChange`, `onAddProject`. Contains: logo (§6 SVG) + wordmark + 6 nav tabs + search + Add Project.
5. **Refactor `Header.svelte`** into a "page sub-header": red accent + h1 title (left) + page-specific controls (year, add-year popover, refresh) on the right. Keep the add-year popover logic intact. This now only shows the page-specific cluster; the global search/Add-Project moved up to the title bar.
6. **Wire in `App.svelte`**: render `<TopBar>` once at the top, then `<main>` → `<Header>` (sub-header) → screen. Pass the right props.
7. **Update `Sidebar.svelte`** only if needed to avoid nav duplication confusion — but KEEP the dock functional. (The top tabs are primary nav now; dock is secondary/ambient. No code deletion.)
8. **Responsive**: at <1100px, collapse nav tabs to an overflow "More ▾" menu OR hide labels. At <768px, consider hiding the wordmark, keep logo + a compact nav. State your choice.
9. **Update tests**: any assertion on `.app-header` structure / `.combo` / `.search-shell` / nav markup — update them to match the new structure. KEEP all §8 bug-lock tests green. Add a test asserting the app title bar exists with logo + wordmark + nav tabs.
10. **Verify** (§1.5). Fix until green.
11. **Report** (§12).

---

## 11. ANTI-PATTERNS — auto-fail

- Side-stripe accent borders (`border-left:>1px` colored).
- Gradient text (`background-clip:text` + gradient).
- Glassmorphism / decorative blur.
- Eyebrow kickers (tiny uppercase tracked label above every section).
- Numbered section markers as scaffolding.
- Dark/colored/busy top bar (reference is the LIGHT, flat ZCode/Teams variant).
- External image for the logo (must be inline SVG).
- Removing a feature to "clean up" (see §7).
- Danger colored with brand red.
- Nav tabs with heavy card backgrounds or shadows.

---

## 12. REPORT FORMAT (final message)

```
## Done
### Verification
- frontend tests: <N>/<M> pass
- svelte-check: <N> errors
### What changed (per file)
- <file>: <one-line>
### Preserved features (§7 checklist)
- all confirmed / <missing + why>
### Bug-lock (§8)
- all 7 intact / <regressions>
### Deferred / flagged
- <skipped + reason>
### Decisions I made
- nav overflow behavior at <breakpoint>: <choice>
- page sub-header on bare pages: <choice>
```

---

## 13. SANITY SELF-CHECK (answer in your first reply, 1 line each)

- Which file is the PRIMARY new artifact? (TopBar.svelte)
- What color is the DBS logo tile? (#E60000)
- Where does the per-page h1 title live now? (page sub-header, below the title bar)
- Name one feature you must NOT delete. (bottom dock / any §7 item)
- Must the logo be an image file? (No — inline SVG)

If you cannot answer all five, re-read this prompt.
