# Design Rules — Project Tracker

## Design Philosophy

Modern minimalist productivity app. Compact, focused, no visual noise.
Every element earns its space. If it doesn't help the user work, it doesn't exist.

## Frameless Window (Required)

pywebview `frameless=True` with custom Svelte titlebar component.

### Titlebar Component (`TitleBar.svelte`)

- Height: 32-36px, flush to top
- CSS: `-webkit-app-region: drag` on titlebar container
- Window controls (minimize, maximize/restore, close): `-webkit-app-region: no-drag`
- Controls call pywebview JS API: `window.pywebview.api.minimize()`, `.maximize()`, `.close()`
- Or direct DOM: `pywebview.windows[0].minimize()` etc.
- Show app icon (small, 16-20px) + app name or current menu title
- Double-click titlebar → maximize/restore toggle
- Maximize icon changes between □ and ⧉ based on window state

### Resize & Drag

- pywebview `resizable=True` handles native resize on Windows WebView2
- Minimum window size: 800×600 (set via pywebview config)
- Test at: 800×600, 1024×768, 1280×720, 1920×1080

### Implementation Priority

1. Get titlebar working with drag + window controls first
2. Then style it to match design system
3. Then integrate with navigation

## Color Palette

Design direction: warm cream canvas, warm coral accents.

```css
:root {
  /* Backgrounds */
  --bg-canvas: #faf9f6; /* warm off-white, main canvas */
  --bg-surface: #ffffff; /* cards, panels, modals */
  --bg-surface-raised: #f5f4f1; /* hover states, secondary surfaces */
  --bg-sidebar: #f0efec; /* sidebar background */
  --bg-inset: #ebeae7; /* input fields, recessed areas */

  /* Text */
  --text-primary: #1a1a1a; /* headings, primary content */
  --text-secondary: #5c5c5c; /* descriptions, secondary info */
  --text-tertiary: #8c8c8c; /* placeholders, disabled, timestamps */
  --text-inverse: #ffffff; /* text on accent backgrounds */

  /* Accent — warm coral */
  --accent: #e8654a; /* primary buttons, active states, links */
  --accent-hover: #d4553b; /* hover on accent */
  --accent-subtle: #fdf0ed; /* accent background tint (tags, badges) */

  /* Borders & Dividers */
  --border-default: #e5e3e0; /* card borders, dividers */
  --border-strong: #d0cec9; /* input borders, focused states */
  --border-accent: #e8654a; /* focused input, active tab indicator */

  /* Status */
  --status-success: #4caf50;
  --status-warning: #f5a623;
  --status-error: #e53935;
  --status-info: #5b9bd5;

  /* Shadows */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.04);
  --shadow-md: 0 2px 8px rgba(0, 0, 0, 0.06);
  --shadow-lg: 0 4px 16px rgba(0, 0, 0, 0.08);
}
```

### Dark Mode (Future)

Not implemented yet. When needed, add `[data-theme="dark"]` overrides.
Do not build dark mode until explicitly requested.

## Typography

```css
:root {
  /* Display/Headings — serif for warmth */
  --font-display: "Source Serif 4", "Georgia", serif;

  /* Body/UI — clean sans-serif */
  --font-body:
    "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;

  /* Code/Mono */
  --font-mono: "JetBrains Mono", "Cascadia Code", "Consolas", monospace;

  /* Scale */
  --text-xs: 0.6875rem; /* 11px — timestamps, badges */
  --text-sm: 0.75rem; /* 12px — secondary text, captions */
  --text-base: 0.8125rem; /* 13px — body text (compact for productivity) */
  --text-md: 0.875rem; /* 14px — emphasized body */
  --text-lg: 1rem; /* 16px — section headers */
  --text-xl: 1.25rem; /* 20px — page titles */
  --text-2xl: 1.5rem; /* 24px — display headings */

  /* Weight */
  --font-normal: 400;
  --font-medium: 500;
  --font-semibold: 600;
}
```

**Font loading:** Bundle Inter and Source Serif 4 via npm packages or self-host in `frontend/static/fonts/`. Do not use Google Fonts CDN in production.

## Spacing

4px base grid. Use multiples of 4px for all spacing.

```css
:root {
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
}
```

Compact spacing for productivity: prefer `--space-2` to `--space-3` gaps.
Cards/panels: `--space-4` padding. Sidebar items: `--space-2` vertical padding.

## Border Radius

```css
:root {
  --radius-sm: 4px; /* buttons, inputs, badges */
  --radius-md: 6px; /* cards, dropdown menus */
  --radius-lg: 8px; /* modals, large panels */
  --radius-full: 9999px; /* pills, avatars */
}
```

## Icons

**Lucide Icons** — already in Svelte ecosystem (`lucide-svelte`).

- Size: 16px for inline/compact, 20px for standard, 24px for primary actions
- Stroke width: 1.5px (default) for clean look
- Color: inherit from parent text color
- Do not mix icon libraries

## Layout Structure

```
┌─────────────────────────────────────────────┐
│ Custom Titlebar (32px)          [—][□][×]   │
├──────────┬──────────────────────────────────┤
│          │                                  │
│ Sidebar  │  Content Area                    │
│ (220px)  │                                  │
│          │  ┌─ Page Header ──────────────┐  │
│ • Menu 1 │  │ Title + Actions            │  │
│ • Menu 2 │  └────────────────────────────┘  │
│ • Menu 3 │                                  │
│ • Menu 4 │  ┌─ Content ─────────────────┐   │
│          │  │                           │   │
│          │  │                           │   │
│          │  └───────────────────────────┘   │
│          │                                  │
├──────────┴──────────────────────────────────┤
│ Status Bar (optional, 24px)                 │
└─────────────────────────────────────────────┘
```

- Sidebar: fixed width 200-240px, collapsible to icon-only (48px)
- Content area: flexible, scroll independently from sidebar
- Page header: sticky top within content area
- Status bar: optional, for background job status, connection state

## Shared Components (Build These First)

These components are used across multiple menus. Build once in `frontend/src/lib/components/`:

1. **TitleBar** — frameless window controls + nav
2. **Sidebar** — menu navigation, collapsible
3. **Button** — variants: primary (accent), secondary (outline), ghost, danger
4. **Input** — text, search, with label and error states
5. **Card** — surface container with optional header/actions
6. **Badge** — status indicators, tags
7. **Modal** — dialog overlay with title + actions
8. **Dropdown** — action menu, select menu
9. **Toast/Notification** — success, error, warning, info
10. **EmptyState** — icon + message + optional action
11. **LoadingSpinner** — inline and full-page variants
12. **DataTable** — sortable, filterable (build when needed for project list)

## Responsive Rules

- No breakpoint-based responsive (this is a desktop app with resizable window)
- Use CSS `min-width`/`max-width` on content containers
- Sidebar collapses to icons at window width < 900px
- Content area uses `max-width: 1200px` + `margin: 0 auto` for readability
- Tables scroll horizontally if too wide

## Animation & Transitions

- Keep minimal — this is a productivity tool, not a showcase
- Sidebar collapse: 200ms ease
- Modal: fade 150ms
- Hover states: 100ms
- Page transitions: none (instant swap)
- Loading: subtle opacity pulse, not spinning wheels everywhere

## Design Consistency Rules

1. Same component = same styling everywhere. No one-off button styles.
2. Colors come from CSS variables only. No hardcoded hex in components.
3. Spacing comes from spacing scale only. No arbitrary pixel values.
4. One icon library only (Lucide). No mixing.
5. Typography scale only. No arbitrary font sizes.
6. If unsure about a design decision → ask user, don't guess.
