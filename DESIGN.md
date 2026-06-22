---
name: Project Tracker DBS
description: Local-first desktop operations workspace for DBS CR deployment tracking.
colors:
  dbs-red: "#B91C1C"
  dbs-red-hover: "#991B1B"
  active-red: "#DC2626"
  black-chrome: "#0A0A0B"
  dark-surface: "#141416"
  dark-border: "#2C2C30"
  workspace-white: "#FFFFFF"
  panel-grey: "#E6E8EB"
  outer-layer: "#EEF0F2"
  hairline: "#E5E7EB"
  input-border: "#D7D7DC"
  ink: "#171717"
  ink-strong: "#111111"
  muted: "#6B7280"
  muted-light: "#A1A1AA"
  soft-pink: "#FFF1F4"
  soft-pink-border: "#FFD4DF"
  success-bg: "#DCFCE7"
  success-ink: "#166534"
  warning-bg: "#FEF3C7"
  warning-ink: "#92400E"
  danger-bg: "#FEE2E2"
  danger-ink: "#991B1B"
typography:
  display:
    fontFamily: "Inter, Segoe UI, Arial, sans-serif"
    fontSize: "22px"
    fontWeight: 900
    lineHeight: 1
    letterSpacing: "1px"
  title:
    fontFamily: "Inter, Segoe UI, Arial, sans-serif"
    fontSize: "12px"
    fontWeight: 900
    lineHeight: 1.2
  body:
    fontFamily: "Inter, Segoe UI, Arial, sans-serif"
    fontSize: "11px"
    fontWeight: 750
    lineHeight: 1.4
  label:
    fontFamily: "Inter, Segoe UI, Arial, sans-serif"
    fontSize: "10px"
    fontWeight: 900
    letterSpacing: "0.2px"
rounded:
  xs: "3px"
  sm: "4px"
  md: "5px"
  lg: "7px"
  xl: "8px"
  dock: "18px"
spacing:
  xs: "4px"
  sm: "6px"
  md: "8px"
  lg: "12px"
  xl: "14px"
  screen: "14px"
components:
  button-primary:
    backgroundColor: "{colors.dbs-red}"
    textColor: "{colors.workspace-white}"
    rounded: "{rounded.md}"
    padding: "0 16px"
    height: "30px"
  button-secondary:
    backgroundColor: "{colors.workspace-white}"
    textColor: "{colors.dbs-red}"
    rounded: "{rounded.md}"
    padding: "0 10px"
    height: "26px"
  input:
    backgroundColor: "{colors.workspace-white}"
    textColor: "{colors.ink-strong}"
    rounded: "{rounded.md}"
    padding: "4px 8px"
    height: "26px"
  panel-card:
    backgroundColor: "{colors.workspace-white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: "12px"
  state-select:
    backgroundColor: "{colors.dbs-red}"
    textColor: "{colors.workspace-white}"
    rounded: "{rounded.lg}"
    padding: "0 8px"
    height: "24px"
---

# Design System: Project Tracker DBS

## 1. Overview

**Creative North Star: "Operations Desk"**

Project Tracker DBS uses a compact, modern operations-desk system: dense controls, strong hierarchy, banking-red emphasis, and black chrome navigation framing a white work surface. The UI should feel like a serious productivity app that stays out of the operator's way while keeping project state, dates, links, and risky actions visible.

The system rejects decorative SaaS dashboards, playful gradients, neon/terminal novelty, generic AI-generated card grids, marketing-page drama, and raw prototype roughness. Polish comes from spacing, alignment, predictable states, and contrast — not decoration.

**Key Characteristics:**

- Compact information density with readable 10–12px operational typography.
- DBS Red used for primary actions, active states, and state controls only.
- Black Chrome reserved for global navigation, dock chrome, and strong command buttons.
- White workspace surfaces nested inside Panel Grey operational frames.
- Fast 150–180ms interaction feedback; no ornamental choreography.

## 2. Colors

The palette is DBS Red + Black Chrome over layered white/grey work surfaces: restrained, high-contrast, enterprise, and action-first.

### Primary

- **DBS Red**: Primary actions, active status tabs, state selects, selected outlines, and key icons. Use sparingly so it remains an action signal.
- **DBS Red Hover**: Hover/active depth for primary controls and destructive confirmations.
- **Active Red**: Small active indicators, focus rings, dock badges, and high-visibility status accents.

### Secondary

- **Soft Pink Surface**: Low-intensity selected/hover background for list rows, secondary buttons, and non-blocking error/warning panels.
- **Soft Pink Border**: Secondary button borders and selected-row hairlines where a full red fill would be too loud.

### Neutral

- **Black Chrome**: Sidebar/dock shell, command buttons, and dark notification surfaces.
- **Dark Surface**: Hover/secondary dark chrome and notification panel depth.
- **Panel Grey**: Operational panel frames and table cards.
- **Workspace White**: Main app content and card interior surfaces.
- **Ink Strong**: Table headers, strong labels, and dense text that must survive small sizes.
- **Muted / Muted Light**: Metadata and helper text only; never primary content.
- **Hairline / Input Border**: Standard border vocabulary for cards, forms, tables, and list boxes.

### Named Rules

**The Red Means Action Rule.** DBS Red is for action, selection, and state. Do not use it as decorative wash or section flavor.

**The Chrome Frames Work Rule.** Black Chrome belongs to app chrome and command moments, not normal content cards.

## 3. Typography

**Display Font:** Inter, Segoe UI, Arial, sans-serif  
**Body Font:** Inter, Segoe UI, Arial, sans-serif  
**Label/Mono Font:** none

**Character:** Single-family, compact, high-weight typography. The system uses weight and case more than size to create hierarchy, because this is dense product UI, not brand storytelling.

### Hierarchy

- **Display** (900, 22px, line-height 1): Page titles in the red header only.
- **Headline** (900, 18px, line-height 1): Metric values and high-signal counts.
- **Title** (900, 11–12px, line-height 1.2): Panel titles, table card headings, modal headings.
- **Body** (650–800, 10–11px, line-height 1.35–1.4): Operational labels, row content, helper copy, and forms.
- **Label** (900, 9–10px, uppercase when needed): Table headers, field labels, compact status labels.

### Named Rules

**The Weight Carries Hierarchy Rule.** Use 750–900 weight before increasing type size. Large typography belongs only to page title and key metrics.

**The Product Font Rule.** Do not introduce decorative display fonts into labels, buttons, tables, or form controls.

## 4. Elevation

Elevation is layered utility: tonal panels and borders create most structure, while shadows are used to lift chrome, panels, popovers, dialogs, and table containers. Shadows should read as functional separation, not glossy decoration.

### Shadow Vocabulary

- **Header Shadow** (`0 5px 20px rgba(0,0,0,.50)`): Red app header separation.
- **Panel Shadow** (`0 3px 14px rgba(0,0,0,.24)`): Default card/panel lift.
- **Card Shadow** (`0 6px 25px rgba(0,0,0,.20)`): Larger table and workspace containers.
- **Inner Shadow** (`0 5px 18px rgba(0,0,0,.36)`): Nested scroll/table surfaces needing depth inside panels.
- **Notification Shadow** (`0 10px 35px rgba(0,0,0,.95)`): Dark floating notification surfaces.
- **Button Shadow** (`0 3px 10px rgba(0,0,0,.40)`): Primary and command buttons.

### Named Rules

**The Layer Before Lift Rule.** Use background, border, and spacing first. Add shadow only when a surface must visually separate from a neighboring layer.

## 5. Components

### Buttons

- **Shape:** Compact rectangle with gentle radius (5px; tiny buttons 4px).
- **Primary:** DBS Red background, white text, 30px height, 0 16px padding, 900 weight, hover to DBS Red Hover with -1px translate.
- **Secondary:** White background, DBS Red text, Soft Pink border, 26px height, hover to Soft Pink Surface.
- **Black Command:** Black Chrome background, white text, used for strong app-level actions such as Add Project.
- **Danger:** Red family fill with explicit confirmation before destructive bridge calls.
- **Focus:** Visible 2px Active Red outline via global `:focus-visible`.

### Chips

- **Style:** Filled semantic chips for success/warning/danger; DBS Red-filled status pills for neutral/actionable states.
- **State:** State selects are intentionally strong: DBS Red fill, white text, 24px min-height, centered 900-weight text.

### Cards / Containers

- **Corner Style:** 7–8px radius for cards and frames.
- **Background:** White inner card inside Panel Grey frame; table scroll surface remains white.
- **Shadow Strategy:** Panel Shadow or Card Shadow depending on surface scale.
- **Border:** 1px Hairline/Soft White Border. Accent cards may use a 3px DBS Red left edge only where existing app parity requires it.
- **Internal Padding:** 12px for panel cards, 14px for table cards, 8px for nested status/list interiors.

### Inputs / Fields

- **Style:** White background, Input Border stroke, 5px radius, 26px height, 750 weight, compact padding.
- **Focus:** Border shifts to 2px DBS Red; no glow, no animated outline.
- **Error / Disabled:** Error panels use Soft Pink Surface + DBS Red border/text. Disabled controls must remain readable, not pale grey.

### Navigation

- **Sidebar/Dock:** Black Chrome shell with compact icon buttons, white active text, DBS Red active border/badge, and short hover movement only where already implemented.
- **Header:** DBS Red band with white page title and compact controls. Dashboard controls live in the header; page content stays task-focused.
- **Tables:** Dark Ink Strong table headers with white uppercase 9px labels, visible grid lines, sticky/scrollable operational surfaces.

### Confirmation Dialog

Confirmation UI is a risk-control component. It must state the action, target, and reversibility, then keep bridge calls outside the dialog until the user confirms.

## 6. Do's and Don'ts

### Do:

- **Do** use DBS Red for primary actions, current state, selected rows, and state controls.
- **Do** preserve compact 10–12px operational typography with high font weight for readability.
- **Do** keep tables and lists visibly structured; this app manages CR operations, not marketing content.
- **Do** use visible focus rings and keep WCAG AA contrast for text, placeholders, and disabled states.
- **Do** keep animations short (150–180ms) and tied to state feedback.
- **Do** use native/product-standard controls where possible; predictability beats novelty.

### Don't:

- **Don't** use decorative SaaS dashboards, playful gradients, neon/terminal novelty, generic AI-generated card grids, marketing-page drama, or raw prototype roughness.
- **Don't** add gradient text, glassmorphism, hero-metric templates, or identical decorative card grids.
- **Don't** introduce new palette hues unless a real semantic state needs them.
- **Don't** make inactive states full-saturation red.
- **Don't** use modals as the first solution when inline editing or progressive disclosure already works.
- **Don't** weaken density by inflating spacing or typography beyond what the workflow needs.
