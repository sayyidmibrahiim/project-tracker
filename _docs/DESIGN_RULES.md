# Design Rules — Project Tracker

Source of truth: `frontend/src/styles.css` `:root`. Do not invent tokens here.

## Direction

Desktop productivity app: dense, calm, Windows-native. Dark chrome shell + white work canvas. DBS red is an accent/punctuation color — not a page wash.

## Active Tokens (from `styles.css`)

```css
:root {
  --black-chrome: #0a0a0b;
  --surface-dark: #141416;
  --dark-border: #2c2c30;
  --main-bg: #ffffff;
  --card-white: #ffffff;
  --light-border: #e5e7eb;
  --input-border: #d7d7dc;
  --text-primary: #171717;
  --text-strong: #111111;
  --text-secondary: #6b7280;
  --text-muted: #a1a1aa;
  --primary-red: #b91c1c;
  --red-hover: #991b1b;
  --active-red: #dc2626;
  --soft-pink-surface: #fff1f4;
  --soft-pink-border: #ffd4df;
  --font: Inter, "Segoe UI", Arial, sans-serif;
  --header-h: 58px;
  --control-h: 26px;
}
```

## Color Use

- Dark chrome: title/header/sidebar/navigation only.
- White canvas: main workspace, cards, tables, forms.
- DBS red `#B91C1C`: primary action, active state, important status, 1–2 accents per panel.
- Soft pink tokens: selected/active background tints, not bulk surfaces.
- Borders: use `--light-border`/`--input-border`; avoid heavy boxes.

## Typography

- Use `--font` everywhere: Inter → Segoe UI → Arial.
- No serif display stack in active design.
- Compact data UI: 12–14px body/control text; stronger weight over bigger size.
- Buttons sentence case, action verbs: `Save changes`, `Open folder`, `Add project`.

## Layout

- Desktop-first. Minimum practical window: 800×600.
- Test: 800×600, 1024×768, 1280×720, 1920×1080.
- Data-heavy screens: tables/lists stay dense; detail panels reduce columns.
- Avoid card nesting beyond 2 levels.
- Prefer shared components over per-menu copy-paste.

## Shared Elements

| Element           | Components                                                                                       |
| ----------------- | ------------------------------------------------------------------------------------------------ |
| Shell chrome      | `Header.svelte`, `Sidebar.svelte`                                                                |
| Primary data view | `Dashboard.svelte`, `ProjectDetails.svelte`, `Report.svelte`                                     |
| Actions           | `ProjectActions.svelte`, `ProjectTransitions.svelte`, `FileActions.svelte`                       |
| Automation panels | `RulesActions.svelte`, `SchedulerActions.svelte`, `TeamsActions.svelte`, `OutlookActions.svelte` |
| Dialogs/hints     | `ConfirmModal.svelte`, `DisabledHint.svelte`, `EmailTemplateDialog.svelte`                       |
| Editors/forms     | `NewProjectForm.svelte`, `NotesEditor.svelte`, `Settings.svelte`                                 |

## Accessibility Floor

- Clickable non-button elements need keyboard path and focus style.
- Disabled controls must explain why via `DisabledHint` or visible text.
- Respect reduced motion.
- Color never sole state indicator; text label still required.

## Tailwind v4

Current source = CSS vars in `styles.css`. `@theme` migration deferred. If added later, alias to existing vars only:

```css
@theme {
  --color-dbs-red: var(--primary-red);
}
```

No big-bang token rename without menu-by-menu approval.
