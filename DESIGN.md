---
name: Project Tracker DBS
description: Desktop CR deployment tracker — dense data UI, dark chrome shell, white canvas, red accent
colors:
  primary: "#b91c1c"
  neutral-chrome: "#0a0a0b"
  neutral-surface: "#141416"
  neutral-canvas: "#ffffff"
  neutral-card: "#ffffff"
  neutral-border: "#e5e7eb"
  neutral-input-border: "#d7d7dc"
  ink-strong: "#111111"
  ink-primary: "#171717"
  ink-secondary: "#6b7280"
  ink-muted: "#a1a1aa"
  soft-surface: "#fff1f4"
  soft-border: "#ffd4df"
  row-alt: "#fafafa"
typography:
  display:
    fontFamily: "Inter, 'Segoe UI', Arial, sans-serif"
    fontSize: "20px"
    fontWeight: 900
    lineHeight: 1
    letterSpacing: "0.5px"
  title:
    fontFamily: "Inter, 'Segoe UI', Arial, sans-serif"
    fontSize: "11px"
    fontWeight: 900
    lineHeight: 1.2
    letterSpacing: "0.3px"
  body:
    fontFamily: "Inter, 'Segoe UI', Arial, sans-serif"
    fontSize: "13px"
    fontWeight: 700
    lineHeight: 1.4
  label:
    fontFamily: "Inter, 'Segoe UI', Arial, sans-serif"
    fontSize: "9px"
    fontWeight: 900
    lineHeight: 1
    letterSpacing: "0.2px"
rounded:
  xs: "4px"
  sm: "5px"
  md: "7px"
  lg: "10px"
  card: "6px"
  dialog: "8px"
  full: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
components:
  button-primary:
    backgroundColor: "#b91c1c"
    textColor: "#ffffff"
    rounded: "{rounded.md}"
    padding: "0 16px"
    height: "30px"
  button-secondary:
    backgroundColor: "#ffffff"
    textColor: "#b91c1c"
    rounded: "{rounded.md}"
    padding: "0 10px"
    height: "26px"
  input-text:
    backgroundColor: "#ffffff"
    textColor: "#111111"
    rounded: "{rounded.md}"
    padding: "4px 9px"
    height: "26px"
  table-header:
    backgroundColor: "#111111"
    textColor: "#ffffff"
    rounded: "0"
    padding: "7px 6px"
  state-chip-approved:
    backgroundColor: "#15803d"
    textColor: "#ffffff"
    rounded: "7px"
    padding: "0 8px"
    height: "24px"
  state-chip-pending:
    backgroundColor: "#b45309"
    textColor: "#ffffff"
    rounded: "7px"
    padding: "0 8px"
    height: "24px"
  state-chip-negative:
    backgroundColor: "#b91c1c"
    textColor: "#ffffff"
    rounded: "7px"
    padding: "0 8px"
    height: "24px"
---

# Design System: Project Tracker DBS

## 1. Overview

**Creative North Star: "The Red Binder"**

A paper-native metaphor. A white project folder on a desk, tabbed with a single red divider — the DBS red mark that says "this one is active." The dark chrome shell is the binder's cover; the white canvas is the page you're reading. Information is laid out like a well-kept dossier: tabular, scannable, annotated in red only where it matters.

The system is designed for a single deployment engineer who spends hours in this tool every day. Every pixel earns its place. The interface does not decorate — it informs. Tables are dense, headers are dark, cells align to a grid. Red is punctuation, not a wash. Pink tints mark selection and hover as subtle feedback.

**Key Characteristics:**
- Dense but scannable. Tabular data is the default; cards are the exception.
- Dark chrome shell frames a white work surface — never inverted.
- Single red accent. Applied to ≤10% of any screen.
- No unnecessary shadows. Flat at rest, lift on interaction.
- Desktop-native, not web-wrapped. No browser chrome, no gradient hero metrics.

## 2. Colors

The palette is restrained: a dark chrome frame, a white work surface, and one red accent. All other colors are muted neutrals or functional tints.

### Primary
- **DBS Red** (`#b91c1c` / `oklch(0.45 0.18 25)`): The sole accent. Primary action buttons, active navigation, important state indicators, folder status markers. Never a page wash or background tint.

### Neutral
- **Black Chrome** (`#0a0a0b`): The titlebar, window chrome, and sidebar dock. The frameless shell's frame.
- **Surface Dark** (`#141416`): Dark panel backgrounds within the chrome. Hover surfaces over chrome.
- **Dark Border** (`#2c2c30`): Dividers inside dark chrome areas.
- **Canvas White** (`#ffffff`): The main workspace background. Every page, table, card, and form sits on white.
- **Card White** (`#ffffff`): Panel and container backgrounds. Same as canvas — no nested surface tint.
- **Light Border** (`#e5e7eb`): Column dividers, table row borders, page header underlines. Every structural line in the work area.
- **Input Border** (`#d7d7dc`): Text inputs, selects, textareas at rest. Slightly darker than light-border to distinguish interactive edges.
- **Ink Strong** (`#111111`): Primary heading text, table headers, emphasized labels.
- **Ink Primary** (`#171717`): Body text, cell content, control labels.
- **Ink Secondary** (`#6b7280`): Secondary information, metadata, helper text, dates.
- **Ink Muted** (`#a1a1aa`): Disabled text, placeholders, non-essential hints.

### Tint
- **Soft Pink Surface** (`#fff1f4`): Row hover, item selection, active tab highlights. Never a bulk surface.
- **Soft Pink Border** (`#ffd4df`): Hover borders for secondary/icon buttons. Companion to the tint surface.
- **Row Alt** (`#fafafa`): Alternating table row background. Minimal tint — barely perceptible.

### Functional
- **Green Approved** (`#15803d`): "APPROVED" / "FINISHED" state chip background.
- **Amber Pending** (`#b45309`): "PENDING SUBMISSION" / "PENDING APPROVAL" state chip background.
- **Red Negative** (`#b91c1c`): "CANCELED" / "POSTPONED" state chip background. Same as primary red.
- **Gray Neutral** (`#6b7280`): Neutral state chip background.
- **Blue Active** (`#2563eb`): "IN-PROGRESS" / "UAT" state chip background.

### Tag / Pill Colors
- **Info Pill** (`#eef2ff` bg, `#c7d2fe` border, `#3730a3` text): Informational tags (schedule type, channel).
- **Warning Pill** (`#fef3c7` bg, `#fde68a` border, `#92400e` text): Warning/caution tags.
- **Success Pill** (`#dcfce7` bg, `#86efac` border, `#166534` text): Success/active tags.
- **Muted Pill** (`#f3f4f6` bg, `#d7dce2` border, `#6b7280` text): Default/neutral tags.

### Scrim
- **Modal Backdrop** (`rgba(17, 24, 39, 0.45)`): Dark semi-transparent overlay behind dialogs and modals.

### Named Rules
**The Red Index Tab Rule.** The primary red is used on ≤10% of any given screen. Its rarity is the point — red means "look here." A page where red is common has no signal left.

**The White Desk Rule.** The workspace is always white. No tinted page backgrounds, no dark mode toggle. The chrome frame is dark, the work surface is white — never inverted. The white surface is the table where work happens.

## 3. Typography

**Body Font:** Inter, "Segoe UI", Arial, sans-serif (one family across the entire UI)

**Character:** Single sans-serif stack. Inter brings a compact, legible, technical feel — appropriate for a data-dense tool where engineers scan for information. No serifs, no display faces. Weight is used for hierarchy: 400 (body), 700–750 (secondary), 800 (controls), 900 (headings, labels, emphasis).

### Hierarchy
- **Display** (900, 20px, 1.0): Page title in the header. Single use per screen.
- **Title** (900, 11px, 1.2): Panel titles, section headings within pages. Letter-spacing 0.3px.
- **Body** (700, 13px, 1.4): Default text weight. Table cells, form labels, paragraph content. Max line length 75ch.
- **Label** (900, 9–10px, 1.0): Table column headers, field labels, status indicators, button text. Compact and dense. Set in uppercase for column headers.
- **Data** (800–900, 10–12px, 1.05): Table cell values, state selectors, inline-edited fields. Dense data weight — stronger weight over bigger size.

### Named Rules
**The Density Rule.** Stronger weight over bigger size. A 10px label at weight 900 is preferred over a 14px label at weight 400. More information fits without scrolling.

## 4. Elevation

Flat by default, layered on interaction. Surfaces are flat at rest — no card shadows, no box-shadow depth. The dark chrome shell provides the only tonal depth separation: the window frame is black chrome, the workspace is white.

Shadows appear only in response to state:
- **Buttons lift** on hover (translateY -1px) paired with a `box-shadow`.
- **Modals and dialogs** cast a shadow (`--shadow-panel`, `--shadow-card`) to separate from the workspace.
- **Popovers and notifications** use stronger shadows for urgency (`--shadow-notif`).
- **Table containers** have an inner shadow when scrollable, indicating there's more content.

### Shadow Vocabulary
- **Panel Shadow** (`0 3px 14px rgba(0,0,0,0.24)`): Side-panel cards, setting sections. Moderate separation.
- **Card Shadow** (`0 6px 25px rgba(0,0,0,0.20)`): Modals, dialogs, popovers. Strong separation from workspace.
- **Button Shadow** (`0 3px 10px rgba(0,0,0,0.40)`): Primary action buttons. Glow on hover.
- **Notification Shadow** (`0 10px 35px rgba(0,0,0,0.95)`): Toasts, alerts, notifications. Highest urgency.

### Named Rules
**The Flat-By-Default Rule.** Surfaces are flat at rest. Shadows appear only as a response to state (hover, focus, modal open). A panel with a constant shadow is a design failure — that's what borders are for.

## 5. Components

### Buttons
- **Shape:** Gently curved edges (7px radius).
- **Primary:** DBS Red (`#b91c1c`) background, white text. Border on hover. Height 30px. Padding 0 16px. Lifts on hover (translateY -1px + shadow).
- **Secondary:** White background, DBS Red text, soft-pink border. Height 26px, padding 0 10px. Slimmer than primary — supporting action.
- **Icon button:** 26×26px square. White background, light border. Red on hover with pink tint background.
- **Danger:** Dark red (`#b5382f`) background, white text. Deletive/destructive actions only. Height 30px.
- **Refresh:** 30×28px, icon-only. Light border, lifts on hover.
- **Disabled:** No shadow, reduced opacity (~0.55–0.72). Cursor not-allowed.

### State Chips
- **Style:** Rounded (7px radius), colored background, white text. Height 24–26px. Compact — 10px font at weight 900.
- **Approved:** Green (`#15803d`) background.
- **Pending:** Amber (`#b45309`) background.
- **Negative/Canceled:** Red (`#b91c1c`) background.
- **Neutral:** Gray (`#6b7280`) background.
- **Active/In-Progress:** Blue (`#2563eb`) background.

### Inputs & Fields
- **Style:** 26px height, 1px border (`--input-border: #d7d7dc`), 7px radius. White background, weight 800 text.
- **Focus:** Border swaps to DBS Red + 2px red-tinted box-shadow ring. No layout shift.
- **Hover:** Border darkens to `--text-strong`.
- **Disabled:** Reduced opacity, cursor not-allowed. The companion `DisabledHint` explains why.
- **Select (combo):** Same base, with a custom chevron arrow via `background-image`.

### Navigation Tabs
- **Style:** Height 28px. White background, light border. Weight 850.
- **Default:** Gray border, dark text.
- **Hover:** Pink tint surface + red border.
- **Active:** Red background, white text. Weight 900.

### Tables
- **Style:** Full-bleed grid within a scrollable container. Dark header row (`--text-strong` background), white header text (9px, uppercase, weight 900). Alternating row tint (`--row-alt: #fafafa`). 1px light borders between cells.
- **Rows:** Height varies with content (min ~88px on dashboard). Hover highlights entire row in soft pink.
- **Cells:** Left-aligned content by default; centered for numbers, dates, and action icons.
- **Inline editing:** Inputs within cells use the same input tokens. Datetime-local pickers are styled to match.

### Cards / Containers
- **Style:** 7px radius, white background, 1px `--light-border`. No shadow at rest.
- **Accent variant:** Left border is omitted (`border-left: none`). Accent is conveyed through title icon color (red), not a colored stripe.
- **Padding:** 12px. Content gap: 10px.

### Dialogs
- **Style:** Centered modal over a dark semi-transparent backdrop (`rgba(0,0,0,0.46)`). 10px radius, panel-bg background. Strong shadow. Max width 760px, max height 88vh.

### Confirm Modal
- **Style:** Compact dialog for state transitions. Title, target name, action label. White background, full border, no left stripe. One confirm + one cancel button. The confirm button uses the primary red style for destructive actions, a neutral style for safe ones.

## 6. Do's and Don'ts

### Do:
- **Do** use DBS red as accent only — ≤10% of any screen.
- **Do** keep the workspace white. Dark chrome is the frame, white is the desk.
- **Do** use weight for hierarchy (900 for headings, 800 for controls, 700 for body). Stronger weight over bigger size.
- **Do** use the full-bleed table as the default data container. Cards are the exception.
- **Do** show shadows only on interaction (hover, focus, modal state). Flat at rest.
- **Do** use the pink tint (`--soft-pink-surface`) for selection/hover highlights only.
- **Do** label disabled controls with a visible reason (use `DisabledHint` or inline text).
- **Do** respect `prefers-reduced-motion`: suppress animations, show instant transitions.
- **Do** use sentence case for buttons and labels: "Save changes", "Open folder", "Add project".
- **Do** support keyboard shortcuts for power users: `Ctrl+R` to refresh, `Ctrl+F` to focus search, `Ctrl+P` to add a project.

### Don't:
- **Don't** use red as a page wash or background tint.
- **Don't** use `border-left` or `border-right` greater than 1px as a colored accent stripe on cards or list items. Use full borders, background tints, or nothing.
- **Don't** use gradient text (`background-clip: text`) anywhere.
- **Don't** use glassmorphism (blur + transparency as decoration).
- **Don't** put hero-metric templates (big number, small label, supporting stats, accent gradient) — this is a data tool, not a SaaS marketing page.
- **Don't** use an all-caps tracked "eyebrow" label above section headings.
- **Don't** nest cards beyond 2 levels.
- **Don't** use dark mode in the workspace. Chrome is dark, surface is white — never inverted.
- **Don't** add motion without a `prefers-reduced-motion` fallback.
- **Don't** use raw hex values in component `<style>` blocks; always reference CSS variables defined in `styles.css`.
