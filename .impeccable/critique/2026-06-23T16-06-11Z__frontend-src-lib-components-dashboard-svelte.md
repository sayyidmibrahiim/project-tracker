---
target: Dashboard
total_score: 26
p0_count: 0
p1_count: 2
timestamp: 2026-06-23T16-06-11Z
slug: frontend-src-lib-components-dashboard-svelte
---

# Design Health Score

| #         | Heuristic                       | Score     | Key Issue                                                                                                                               |
| --------- | ------------------------------- | --------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| 1         | Visibility of System Status     | 3         | Loader/skeleton states and saving spinners exist. Tab counts are live.                                                                  |
| 2         | Match System / Real World       | 3         | Uses clear banking ops terms (UAT, CR, Drone). But placeholder text "( calm empty state, DBS red accent )" breaks real-world match.     |
| 3         | User Control and Freedom        | 3         | Easy row selection, clear filter reset, back buttons, but mobile layout makes back navigation clunky when both columns stack.           |
| 4         | Consistency and Standards       | 2         | Radius values vary (3px, 5px, 7px, 8px, 12px) violating standard scale. Hardcoded white backgrounds conflict with design system tokens. |
| 5         | Error Prevention                | 3         | Confirm modal gates destructive states (Cancel, Postpone, Reopen). G1 rules check for dependencies.                                     |
| 6         | Recognition Rather Than Recall  | 3         | Dense table is scannable, search highlights hits. But inline input fields lack explicit visual labels or inline hints.                  |
| 7         | Flexibility and Efficiency      | 3         | Master-detail reduces navigation hops, inline inputs are fast. But small touch targets (24-28px) hurt efficiency on touch screens.      |
| 8         | Aesthetic and Minimalist Design | 2         | Clean master-detail, but the inline edit fields have different borders/styling. The empty state helper text is a visual slop tell.      |
| 9         | Error Recovery                  | 3         | `actionError` alert bar handles errors, but inline inputs remain disabled/frozen during failure until reload.                           |
| 10        | Help and Documentation          | 1         | No inline guides or tooltips explain what CR next states mean (e.g. why IN-PROGRESS is blocked).                                        |
| **Total** |                                 | **26/40** | **Acceptable foundation, needs visual/professional polish.**                                                                            |

# Audit Health Score

| #         | Dimension         | Score     | Key Finding                                                                                                                  |
| --------- | ----------------- | --------- | ---------------------------------------------------------------------------------------------------------------------------- |
| 1         | Accessibility     | 2         | Form inputs lack linked labels (WCAG AA violation). Missing interactive ARIA roles.                                          |
| 2         | Performance       | 3         | Svelte 5 reactive flow, smooth transitions, uses prefers-reduced-motion media query.                                         |
| 3         | Responsive Design | 2         | Stacks to 1 column below 1100px, but touch targets (24px, 28px) are too small.                                               |
| 4         | Theming           | 2         | Hardcoded values (7px, 5px, 3px border-radius; literal `#fff` background, `#181715` color).                                  |
| 5         | Anti-Patterns     | 2         | Placeholder text "( calm empty state, DBS red accent )" left in empty state. Too many custom button/input radius variations. |
| **Total** |                   | **12/20** | **Acceptable, significant work needed.**                                                                                     |

# Anti-Patterns Verdict

**Fail.** While the layout is structural and clean, it retains a glaring placeholder: `( calm empty state, DBS red accent )` is printed literally in the empty state. Additionally, the border-radius values deviate from the design system scale with random 7px, 5px, and 3px settings.

**LLM assessment**: The master-detail layout is the correct operational choice. However, the custom input borders and hardcoded white backgrounds make parts of the interface feel raw and disconnected from the dark-chrome header/sidebar system.

**Deterministic scan**: The automated detector found 5 border-radius violations (7px, 5px, 3px) in CSS rules that drift from `DESIGN.md`.

# Overall Impression

The new master-detail layout is highly functional and much cleaner than the old multi-column table. However, it requires a precision pass to replace hardcoded assets, establish proper form labels, and delete developer placeholder texts.

# What's Working

1. **Master-Detail Layout**: Great density on desktop, making project management fast.
2. **Reduced Motion**: Proper Svelte bindings to respect system motion preferences.
3. **Runes usage**: Clean reactive state using Svelte 5 runes.

# Priority Issues

**[P1] Form fields lack accessible labels**

- **Why it matters**: `datetime-local` and text inputs lack `<label>` associations. Screen reader users cannot identify fields.
- **Fix**: Wrap inputs in `<label>` or associate them with `id`/`for` attributes.
- **Suggested command**: `/impeccable audit Dashboard`

**[P1] Developer placeholder text in empty state**

- **Why it matters**: Printing `( calm empty state, DBS red accent )` makes the app feel like a draft.
- **Fix**: Remove the placeholder sentence; style the empty card with clean layout.
- **Suggested command**: `/impeccable polish Dashboard`

**[P2] Hardcoded border-radius values**

- **Why it matters**: Deviates from the `rounded` scale defined in `DESIGN.md` (e.g., 8px md, 6px sm).
- **Fix**: Map 7px/5px/3px to design system tokens.
- **Suggested command**: `/impeccable layout Dashboard`

**[P2] Touch targets are too small on mobile**

- **Why it matters**: Kebab menus (28px) and icon buttons (24px) cause misclicks.
- **Fix**: Increase touch target container pads to hit >=40px while preserving visual alignment.
- **Suggested command**: `/impeccable adapt Dashboard`

# Persona Red Flags

- **Alex (Power User)**: Smaller touch targets slow navigation on tablet screens.
- **Jordan (First-Timer)**: The placeholder text `( calm empty state, DBS red accent )` makes the UI look broken or incomplete.
- **Sam (Accessibility)**: Screen readers cannot label the inline datetime-local editors or link input fields due to lack of associated label elements.

# Minor Observations

- Active status filter tabs would benefit from segmented control styling rather than plain buttons.
- The red hover states on inline buttons are solid but could be softer to reduce color noise.

# Questions to Consider

- What if the empty state provided a direct "Select a project" callout rather than static text?
- Should the mobile layout hide the details panel until a row is tapped, instead of stacking?
