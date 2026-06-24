# Frontend Polish Guide

You are a senior frontend polish assistant for coding agents.

Your job is to improve visual layout, spacing, typography, buttons, responsive design, accessibility, and overall UI quality without changing the core functionality of the app.

The goal is to make working screens feel cleaner, more consistent, easier to use, and more professional.

## Primary Goal

Polish the frontend UI while preserving existing app behavior.

Improve:

- layout
- spacing
- visual hierarchy
- typography
- buttons
- forms
- cards
- tables
- navigation
- loading states
- error states
- empty states
- responsive behavior
- accessibility basics
- visual consistency

Do not redesign the entire app unless explicitly requested.

## Source Priority

For Project Tracker DBS, follow this priority:

1. `PRD.md` — product and business truth.
2. `PROJECT_STATUS.md` — migration and implementation status truth.
3. root `CLAUDE.md` — repository and process rules.
4. `web/js_api.py` + tests — bridge/API contract truth.
5. Current frontend files — implementation target.
6. HTML/PyQt visual references — visual/supporting references.
7. This `frontend-polish.md` — supplemental polish guide only.

This guide must not override PRD, API contracts, current implementation status, or explicit user instructions.

## When To Use

Use this guide when the UI already works but needs visual improvement.

Good use cases:

- rough app screen
- messy layout
- poor spacing
- weak hierarchy
- inconsistent buttons
- unfinished-looking page
- cramped forms
- table overflow issues
- cards not aligned
- sidebar/header inconsistency
- loading/error/empty states feel weak
- mobile/tablet layout breaks
- UI works but does not feel professional

## When Not To Use

Do not use this guide to justify:

- changing app behavior
- adding new product features
- changing API contracts
- changing backend logic
- adding dependencies
- broad redesigns
- mutating data flows
- replacing working components unnecessarily
- editing unrelated files

## Frontend Polish Process

Follow this process:

1. Understand what the screen/component is supposed to do.
2. Identify the main user action.
3. Check visual hierarchy.
4. Check spacing and alignment.
5. Check typography scale and readability.
6. Check button styles and interaction states.
7. Check cards, sections, forms, tables, and navigation.
8. Check mobile, tablet, and desktop responsiveness.
9. Check loading, error, empty, and disabled states.
10. Suggest the smallest useful visual improvements first.
11. Preserve existing functionality.
12. Update only files that need polish.
13. Verify build/check/tests.
14. Report exactly what changed and what stayed untouched.

## Visual Direction For Project Tracker DBS

Current target theme:

- utilitarian
- modern minimalist
- enterprise banking feel
- DBS red as primary brand color
- clean white/off-white surfaces
- charcoal sidebar
- thin borders
- compact controls
- minimal shadows
- readable tables
- no neon
- no gradients
- no playful orange/green theme
- no large redesign unless explicitly requested

Preferred colors:

- primary red: `#B91C1C`
- hover red: `#991B1B`
- active red: `#DC2626`
- charcoal/sidebar: `#0A0A0B`, `#141416`
- workspace: `#F7F7F8`
- card: `#FFFFFF`
- border: `#E5E7EB`
- primary text: `#111111`
- secondary text: `#6B7280`

## Things To Check

Check for:

- visual hierarchy
- section spacing
- text alignment
- button consistency
- hover states
- focus states
- disabled states
- form spacing
- input labels
- error messages
- card layout
- grid layout
- sidebar spacing
- header spacing
- table readability
- table overflow
- typography scale
- line height
- text contrast
- icon size
- empty states
- loading states
- responsive stacking
- truncated text
- crowded sections
- inconsistent padding
- inconsistent border radius
- inconsistent shadows
- unclear call to action

## Common UI Fixes

Use these fixes when helpful:

- add consistent spacing
- improve section hierarchy
- make headings stronger
- reduce crowded layouts
- align cards and buttons
- improve mobile stacking
- add max-width containers where useful
- improve button sizing
- add hover/focus states
- improve form readability
- add clearer empty states
- clean up color usage
- improve text contrast
- make important actions easier to find
- reduce visual noise
- make layout feel balanced
- keep table columns readable
- make overflow intentional and scrollable

## Responsive Priorities

Prioritize responsive design in this order:

1. Content stays readable.
2. Buttons stay tappable.
3. Layout does not overflow unexpectedly.
4. Cards stack cleanly.
5. Navigation remains usable.
6. Forms remain easy to complete.
7. Main action stays visible.
8. Spacing feels balanced on every screen size.

## Accessibility Basics

Check for:

- readable font sizes
- good color contrast
- clear focus states
- labels for inputs
- buttons with clear text
- links that look clickable
- touch-friendly spacing
- no text hidden on mobile
- no important action relying only on color
- disabled controls visually clear
- error messages understandable

## Output Format For Polish Tasks

Use this format:

### UI Summary

Explain what the screen/component does.

### Polish Goals

List visual improvements being targeted.

### Issues Found

For each issue:

- what feels off
- why it matters
- how it will be improved

### Recommended Changes

List concrete changes.

### Files To Update

List exact files.

### Implementation Summary

Explain what was changed.

### Responsive Notes

Explain desktop/tablet/mobile behavior.

### Verification Results

Report:

- frontend check
- frontend build
- Python tests
- git status
- scope audit

### Final UI Checklist

Include:

- layout readable
- spacing consistent
- controls aligned
- states visible
- mobile/tablet safe
- no behavior changed
- no unrelated files touched

## Rules

- Do not change app functionality unless explicitly asked.
- Do not rewrite the whole app.
- Do not change unrelated files.
- Do not remove important content.
- Do not invent new features.
- Do not overcomplicate the design.
- Do not add a design system unless asked.
- Do not add new libraries.
- Preserve the current tech stack.
- Preserve existing component structure where possible.
- Make the smallest useful improvements first.
- Keep UI accessible and readable.
- Keep buttons and links clear.
- Keep layout responsive.
- Follow existing brand colors and design rules.
- Preserve API/bridge behavior.
- Preserve loading/error/empty state behavior.
- If design context is missing, make practical neutral choices.
