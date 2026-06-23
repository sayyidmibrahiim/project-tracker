# FRAMELESS WINDOW PROMPT — Custom Title Bar (ZCode / Teams style, DBS brand)

> Paste this ENTIRE file as the first message into Claude Code Desktop (any model
> in your router). Self-contained. Do not prepend other context. Work top-to-bottom.

---

## 0. ROLE

You are a senior full-stack desktop-app engineer (Python pywebview backend + Svelte frontend). You convert a standard Windows-windowed app into a **frameless window** with a **custom-drawn title bar** that maximizes the dashboard's features into the top chrome — exactly like the ZCode and Microsoft Teams desktop apps.

You write real, shipped code. You think like an engineer shipping banking-ops software: every change preserves features, passes tests, does not regress fixed bugs, and works on the real runtime (pywebview 6.2.1 / Windows 11). You match surrounding code style exactly.

---

## 1. HOW TO WORK (follow exactly)

1. **Plan before code.** Todo list first; one in-flight item.
2. **Read before edit.** Never edit a file unread this session. Match naming/comments/indent/quotes.
3. **Never silently override a tested decision.** `grep frontend/tests/*.test.mjs` + `frontend/tests/*.test.ts` for assertions on any class/CSS before changing. If locked, update test in the SAME change or STOP and ask.
4. **Preserve every feature.** This is a window-chrome + layout change, NOT a feature cut. Dashboard features (§9) must all still work.
5. **Verify after each logical unit:**
   - Backend: `cd project_tracker_root && .venv/Scripts/python.exe -m pytest --basetemp=./.pytest-tmp -q`
   - Frontend: `cd frontend && npm test` (node:test) + `cd frontend && npx svelte-check --threshold error`
   - Smoke: `cd frontend && npm run dev` and visually load the page (the UI must render; the bridge is mocked outside the desktop shell — graceful degradation, not crashes).
6. **Be direct.** State what changed/passed/skipped + why. Show real output. No hedging.
7. **Smallest diff achieving the spec.** No new deps.
8. **Decide, don't waffle.** Pick the obvious option, state it, proceed.

---

## 2. THE GOAL (one paragraph)

Remove the **native Windows title bar** and replace it with a **custom title bar drawn in the webview** — a single slim bar at the very top of the window that holds: the DBS logo, the app wordmark, the primary navigation tabs, the global search, the Add-Project action, AND the window-control buttons (minimize / maximize-restore / close). This is the ZCode/Teams pattern: the app looks "fullscreen / borderless" because the OS chrome is gone and the app owns the top edge. The dashboard's header/controls get folded UP into this bar so the top of the app is dense, branded, and professional.

---

## 3. NON-NEGOTIABLES

- DO NOT remove/hide any existing feature (inventory in §9).
- DO NOT regress the 7 bug fixes (§10).
- KEEP fonts: `StyreneB` (sans) + `Tiempos Headline`/`Cormorant` (serif). Load-bearing.
- USE the DBS palette (§7). Primary red `#E60000`.
- DBS logo as **inline SVG** (§8). Do NOT use an external image file.
- The window MUST remain draggable (pywebview `easy_drag` or a custom drag region). The whole title bar (left of the window controls) must act as a drag handle.
- Window controls (min/max/close) MUST actually work via pywebview `Window` methods — no fake/no-op buttons.
- Close should respect existing shutdown (don't bypass app teardown). Maximize on an already-maximized window = restore. Double-click the title bar = toggle maximize.
- DO NOT add npm or pip dependencies. pywebview 6.2.1 already supports frameless.
- KEEP the bottom dock (`Sidebar.svelte`) functional. The top title bar becomes primary nav; the dock stays as secondary/ambient nav. Do NOT delete the dock.

---

## 4. PROJECT FACTS

- **App:** "Project Tracker DBS". Single-user Windows desktop app (pywebview 6.2.1). A DBS engineer manages Change-Request projects (UAT→production, comms, evidence, folders).
- **Register:** product UI. Dense, calm, modern, professional. Not decorative SaaS, not playful, not neon.
- **Frontend:** Svelte 5 runes (`$state`/`$derived`/`$props`/`$effect`), TypeScript, Vite. Talks to Python via `callBridge(method, ...args)` → `window.pywebview.api.<method>`. NEVER touch `window.pywebview` directly in components; always go through `callBridge`/`bridge.ts`.
- **Backend:** Python. Window created in `project_tracker/app_web.py:1568` via `webview.create_window(...)`. Bridge methods live in `project_tracker/web/js_api.py` (class `JsApi`, ~186 methods). pywebview `Window` object is returned by `create_window` and has: `minimize`, `maximize`, `restore`, `destroy`, `toggle_fullscreen`, `on_top`, events.
- **Window:** currently `width=1200, height=760, min_size=(960, 640)`, titled "Project Tracker DBS". Standard framed window today.
- **OS:** Windows 11.

### Current app shell (App.svelte)

- `<Sidebar>` = bottom dock (brand "PT" mark + 6 nav items + Notifications button w/ unread badge + popover). Auto-hides on idle, reappears.
- `<main class="main">` → `<Header>` + active screen component.

### Current Header (Header.svelte)

- `<header class="app-header">`: 2-col grid — title (red 4px divider + `<h1>` per-page title) + actions (year select, add-year `+` popover, search shell, Add Project, refresh button). `headerConfig` toggles which controls show per page.

---

## 5. TARGET LAYOUT (ASCII)

### 5.1 Maximized/restored — custom title bar owns the top edge

```
┌── CUSTOM TITLE BAR (~40px, frameless, drag region) ────────────────────────────────┐
│ [◆] Project Tracker DBS   Dashboard  Project Details  Report  Automations   ⌕…  ➕  │ ▁ □ ✕
│  logo  wordmark            ↑ nav tabs (primary nav)            search  add-proj    min max close
└──────────────────────────── hairline bottom border ──────────────────────────────────┘
┌── PAGE SUB-HEADER (refactored Header.svelte; only dashboard/project-detail) ────────┐
│ ▌ Dashboard.        [Year: 2026 ▾] [+ Add Year]                              ⟳ Refresh │
│   red accent         page-specific controls                                              │
└──────────────────────────────────────────────────────────────────────────────────────┘
┌── CONTENT ─────────────────────────────────────────────────────────────────────────┐
│  [All 12] [UAT 3] [Prod 4] …  status tabs + dashboard table…                            │
```

### 5.2 Layout rules

- **Title bar (NEW `TitleBar.svelte`)**, rendered in `App.svelte` as the FIRST child, full-width, sticky at top, ~40px tall, `frameless` app has no OS chrome above it so this IS the top of the window.
- **Left cluster:** DBS logo (§8, ~20px, click → Dashboard) + wordmark "Project Tracker **DBS**" ("DBS" in `--dbs-red`, rest in `--ink`, font-size ~13px, font-weight 800).
- **Center nav tabs:** the 6 pages from Sidebar's `navItems` (Dashboard, Project Details, Second Brain, Report, Automations, Settings). Flat text tabs; active = `--dbs-red` text + 2px bottom indicator; inactive = `--muted`; hover = `--ink`. Reuse `onNavigate`.
- **Right cluster:** global search input (slim, ~180px, magnifier icon) + "Add Project" button (`--dbs-red` primary). Both always visible (search may be no-op on non-dashboard pages, that's fine).
- **Far-right window controls:** three buttons `▁ □ ✕` (minimize / maximize-restore / close). On Windows they are square (~40px wide × full bar height), with the close button turning `--dbs-red` on hover. The maximize icon toggles between □ (restore) and ❐ (maximize) depending on window state.
- **Drag region:** the entire title bar LEFT of the window controls is a drag handle (pywebview `easy_drag` via `-webkit-app-region: drag` equivalent, or the `easy_drag=True` flag). The buttons/tabs/inputs in the bar must NOT be draggable (they need clicks): use `-webkit-app-region: no-drag` on interactive elements, or `easy_drag=False` + a dedicated drag strip. PICK ONE and state it.
- **Page sub-header (`Header.svelte`, refactored):** below the title bar. Red accent + per-page h1 title (left) + page-specific controls (year, add-year popover, refresh) on the right. The global search and Add-Project MOVED UP to the title bar, so remove them from here.
- **Double-click title bar (not on a control) = toggle maximize.**
- **Content area** unchanged.

### 5.3 Frameless interplay

- The app's outer container (`<body>` / `#app`) must have NO top padding for the old native bar — the custom title bar is the top edge now.
- Rounded corners on the window are not required (Windows frameless = square). If you want subtle 8px top corners, fine, but not required.
- Do NOT draw fake window-resize borders; pywebview frameless windows are still resizable via OS hit-testing on Windows when `frameless=True` is set with EdgeChromium/MSHTML — verify this on the target. If resize stops working, set a thin 4px CSS resize edge using `resize: horizontal/vertical` is NOT a thing in web — so rely on pywebview. If resize is lost, document it as a known limitation and offer `easy_drag` only.

---

## 6. EXECUTION PLAN (ordered)

### Backend (pywebview) — `project_tracker/app_web.py` + `project_tracker/web/js_api.py`

1. **Make the window frameless.** In `app_web.py:1568` `webview.create_window(...)`, add `frameless=True` and `easy_drag=True`. Keep `width/height/min_size/title/js_api/http_server`. The window object returned by `create_window` must be captured (`window = webview.create_window(...)`).

2. **Expose window-control bridge methods.** pywebview 6.x lets you call `window.minimize/maximize/restore/destroy`. But `js_api` methods don't get the window by default. Two clean approaches — PICK ONE and state it:
   - **(A) `window.expose(...)`** — after creating the window, define module-level functions `win_minimize()`, `win_toggle_maximize()`, `win_close()` that operate on a captured window reference, then `window.expose(win_minimize, win_toggle_maximize, win_close)`. These become callable from JS as `window.pywebview.api.win_minimize()` etc. (RECOMMENDED for pywebview 6.x).
   - **(B) Pass the window into `JsApi`** — store the window on the JsApi instance after creation (`api._window = window`) and add `window_minimize`, `window_toggle_maximize`, `window_close` methods. Be careful: pywebview calls js_api methods on a thread; window ops should be safe.
     Each bridge method returns `{"ok": True}` (or `{"ok": False, "error": {...}}` on failure) consistent with the existing `ok()`/`fail()` helpers in `js_api.py`.

3. **Toggle-maximize logic:** call `window.state` to read current state; if maximized → `restore()`, else → `maximize()`. Wrap in try/except, return fail on error.

4. **Close:** prefer the app's existing shutdown path if one exists (search `js_api.py` / `app_web.py` for existing teardown / on_closing). If none, `window.destroy()` is acceptable. Do NOT bypass DB flush or pending-save prompts if any exist.

5. **Window state sync (optional but professional):** push maximize/restore state changes to the frontend so the title-bar icon can update. Use `window.events` / an `on_loaded`-style hook or `evaluate_js` to call a global like `window.__setWinState(state)`. If too risky, skip and just optimistically toggle the icon on click + verify on next focus. State your choice.

### Frontend — new `TitleBar.svelte` + refactor `Header.svelte` + wire `App.svelte`

6. **Create `frontend/src/lib/components/TitleBar.svelte`.** Props: `currentPage`, `onNavigate`, `searchQuery`, `onSearchChange`, `onAddProject`. Internal state: `winState: "normal" | "maximized"`. Contains: logo SVG + wordmark + 6 nav tabs + search + Add Project + window controls. All interactive elements marked `-webkit-app-region: no-drag`.

7. **`bridge.ts` — add window-control wrappers.** Mirror `callBridge<T>("win_minimize")`, `callBridge<T>("win_toggle_maximize")`, `callBridge<T>("win_close")`. They must degrade gracefully (no crash) when NOT in pywebview (dev browser): return `{ok:false, error:"window controls require the desktop app"}` — same pattern as existing `isPywebviewReady()` checks.

8. **Refactor `Header.svelte`** → "page sub-header": red accent + h1 title (left) + year/add-year/refresh (right). Remove the global search + Add-Project (moved to title bar). Keep `headerConfig`, `triggerRefresh`, add-year logic intact.

9. **Wire `App.svelte`:** render `<TitleBar>` as the first child (above `<main>`), then `<main>` → `<Header>` (sub-header) → screen. Pass props. Remove the now-redundant `<Header>` global controls.

10. **`Sidebar.svelte` (dock):** leave functional. Optionally make the dock brand "PT" button also navigate to dashboard (it already does). No deletion.

11. **CSS `styles.css`:** re-anchor `:root` to the DBS palette (§7). Add `.titlebar`, `.titlebar-tab`, `.winctrl`, title-bar drag rules. Ensure `body/#app` has no native-bar padding. Keep all compatibility aliases resolving.

### Tests

12. **Update existing tests** that assert `.app-header` structure / `.combo` / `.search-shell` / nav markup to match the new structure. KEEP §10 bug-lock tests green.

13. **Add tests:** (a) `TitleBar.svelte` renders logo + wordmark + 6 tabs + 3 window controls; (b) window-control handlers call `callBridge` with the right method name (mock `callBridge`); (c) the title bar is marked as a drag region.

### Verify

14. Run §1.5 verifications. Fix until green.

### Report

15. Output §13.

---

## 7. DESIGN TOKENS — DBS brand (`styles.css :root`)

```css
:root {
  --dbs-red: #e60000; /* logo tile, wordmark accent, active tab, close-hover */
  --dbs-red-hover: #b30000;
  --dbs-red-soft: #fdecec;
  --ink: #1e1e1e; /* DBS black — primary text */
  --ink-soft: #4a4a4a;
  --muted: #6e6e6e; /* inactive nav */
  --muted-soft: #9a9a9a;
  --hairline: #e5e5e5;
  --surface: #ffffff; /* title bar bg */
  --surface-raised: #fafafa;
  --surface-dark: #1e1e1e; /* dock */
  --on-dark: #ffffff;

  --danger: #b5382f; /* keep distinct from brand red */
  --danger-hover: #942d26;

  --font-display:
    "Tiempos Headline", "Cormorant Garamond", "Times New Roman", serif;
  --font:
    "StyreneB", "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    sans-serif;

  --r-sm: 6px;
  --r-md: 8px;
  --r-lg: 12px;
  --r-pill: 9999px;
  --titlebar-h: 40px;
}
```

- Title bar background = white (`--surface`); single hairline bottom border. LIGHT and FLAT (ZCode/Teams light variant), not dark/busy.
- Body text `--ink` on `--surface` is ≥12:1. Don't use `--muted` for body.
- Keep ALL existing compatibility aliases (`--primary-red`, `--canvas`, `--color-dbs-red`, …) resolving to the new DBS values.

---

## 8. DBS LOGO — inline SVG (no image file)

Red rounded tile + white 5-point star, ~20px. Use exactly:

```html
<svg
  width="20"
  height="20"
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

- Wrap in a clickable element → `onNavigate("dashboard")`.

---

## 9. FEATURE INVENTORY — PRESERVE EVERY ONE

| Feature                                              | Source                                                             |
| ---------------------------------------------------- | ------------------------------------------------------------------ |
| Per-page h1 title                                    | Header.svelte `headerConfig[currentPage].title`                    |
| Year `<select>` filter                               | Header.svelte `.combo`, `handleYearInput`                          |
| Add-year `+` + popover                               | Header.svelte `toggleAddYear`, `submitAddYear`, `.header-year-pop` |
| Search (200ms debounce)                              | (moves to TitleBar) `handleSearchInput`                            |
| "Add Project"                                        | (moves to TitleBar) `onAddProject`                                 |
| Refresh (650ms spin)                                 | Header.svelte `triggerRefresh`                                     |
| `showDashboardControls` gating                       | Header.svelte prop                                                 |
| Nav to all 6 pages                                   | Sidebar.svelte `navItems` + `onNavigate` (now also in TitleBar)    |
| Notifications dock button + badge + popover          | Sidebar.svelte                                                     |
| Bottom dock (icon+label, auto-hide)                  | Sidebar.svelte — KEEP                                              |
| Dashboard table inline edits (drone/CR/dates/states) | Dashboard.svelte                                                   |

---

## 10. BUG-FIX LOCK-IN — DO NOT REGRESS

1. Subproject open works (`_FileServiceAdapter.open_folder` → `filesystem.open_folder`; `folder_open` no raise).
2. Drone ticket ID shown not "Drone Link" (regex `/(D-[A-Z0-9-]+)(?=\/|$|\?|#)/`).
3. Copy button per-control (`copiedKey` keyed `path:column:idx`).
4. State dropdowns `appearance:none` + custom caret + light `<option>` (test "state dropdowns are custom-styled with a caret" green; Dashboard AND ProjectDetails).
5. Dock labels always visible (icon + inline text).
6. No caret/text overlap on state selects.
7. Paste inputs say "Paste Drone link…" / "Paste CR link…".

Also keep: `--danger` ≠ brand red; no side-stripe accent borders; `.dock-hover-zone` `pointer-events:none`.

---

## 11. CODE CONVENTIONS

- Svelte 5 runes only. `<script lang="ts">`. Scoped `<style>`.
- Inline SVG, stroke=currentColor, 12–14px.
- `callBridge<T>(method, ...args)` → `{ok, data?, error?}`. Check `ok`. Graceful when not in pywebview (use `isPywebviewReady()`).
- Python: PEP 8, type hints, docstrings matching surrounding `JsApi` methods, `ok()`/`fail()` helpers from js_api.
- Comments explain WHY. Match surrounding density.

---

## 12. ANTI-PATTERNS — auto-fail

- Keeping the native title bar (must be frameless).
- Window controls that don't actually call pywebview (fake buttons).
- A dark/busy/gradient title bar (reference is light, flat, calm).
- External image for the logo (must be inline SVG).
- Making the whole bar non-draggable (must drag the window).
- Making nav tabs/inputs draggable (must be clickable → `no-drag`).
- Deleting the bottom dock or any §9 feature.
- Danger colored with brand red.
- Eyebrow kickers, gradient text, glassmorphism, side-stripe accents, identical card grids, numbered section scaffolding.
- Adding deps.

---

## 13. REPORT FORMAT (final message)

```
## Done
### Verification
- backend tests: <N>/<M> pass
- frontend tests: <N>/<M> pass
- svelte-check: <N> errors
- dev smoke: <renders? frameless? drag? min/max/close work?>
### What changed (per file)
- <file>: <one-line>
### Window controls wiring
- approach (A expose / B jsapi): <choice>
- drag mechanism: <easy_drag / custom region>
- state sync: <yes — how / no — why>
### Preserved features (§9)
- all confirmed / <missing + why>
### Bug-lock (§10)
- all 7 intact / <regressions>
### Known limitations
- <e.g. resize-on-frameless, state sync caveat>
### Decisions I made
- <each fork resolved>
```

---

## 14. SANITY SELF-CHECK (answer first, 1 line each)

- Which Python function creates the window? (webview.create_window in app_web.py:1568)
- Which flag makes it frameless? (frameless=True)
- How does JS call a window control? (callBridge("win_minimize") → window.pywebview.api.win_minimize)
- Must interactive bar elements be draggable? (No — no-drag)
- Name one feature you must NOT delete. (bottom dock / any §9)

If you can't answer all five, re-read this prompt.
