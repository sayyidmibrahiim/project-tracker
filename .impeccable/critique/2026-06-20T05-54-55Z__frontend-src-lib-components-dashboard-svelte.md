---
target: Dashboard
total_score: 21
p0_count: 0
p1_count: 3
timestamp: 2026-06-20T05-54-55Z
slug: frontend-src-lib-components-dashboard-svelte
---

#### Design Health Score

| #         | Heuristic                       | Score     | Key Issue                                                                                                                                    |
| --------- | ------------------------------- | --------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| 1         | Visibility of System Status     | 2         | Loading skeleton + per-cell spinners exist, but success confirmation is weak and the desktop-bridge failure dominates the visible dev state. |
| 2         | Match System / Real World       | 3         | CR/Drone language matches the operator domain; empty/error copy still leaks implementation language.                                         |
| 3         | User Control and Freedom        | 2         | Filters and destructive confirms exist; dock auto-hide and hidden row menu make recovery/navigation less obvious.                            |
| 4         | Consistency and Standards       | 2         | Dashboard mixes global tokens, component-local aliases, literal rgba, and intentional AS-IS exceptions.                                      |
| 5         | Error Prevention                | 3         | Legal dropdown options, disabled auto-only states, confirms for destructive state changes.                                                   |
| 6         | Recognition Rather Than Recall  | 2         | Header actions visible; bottom dock is icon-first/auto-hidden, row actions are compact, inline edit affordances are subtle.                  |
| 7         | Flexibility and Efficiency      | 2         | Dense inline editing helps experts; no visible keyboard shortcut/bulk path.                                                                  |
| 8         | Aesthetic and Minimalist Design | 2         | Strong operational density, but nested frames + heavy shadows + huge table create visual noise.                                              |
| 9         | Error Recovery                  | 2         | Error banner appears, but `BRIDGE_UNAVAILABLE` style detail gives no user-level recovery.                                                    |
| 10        | Help and Documentation          | 1         | No contextual help for state rules, disabled IN-PROGRESS, link reset behavior, or empty project setup inside Dashboard.                      |
| **Total** |                                 | **21/40** | **Acceptable — useful foundation, significant UX cleanup needed.**                                                                           |

#### Anti-Patterns Verdict

**LLM assessment:** Not generic SaaS/AI slop. It reads as a real internal operations table. Failure mode is different: legacy admin/prototype density. The design has purpose, but the surface stacks too many frames, shadows, borders, and tiny labels, so the first impression is "busy tool" more than "modern productivity app."

**Deterministic scan:** CLI detector found 2 advisory design-token drift findings in `frontend/src/lib/components/Dashboard.svelte`: line 593 `rgba(45,61,52,.16)`, line 599 `rgba(45,61,52,.35)`. Browser detector found 15 issues: repeated `gpt-thin-border-wide-shadow`, `nested-cards` on `.table-scroll`, `low-contrast` on `.empty-sub`, `tiny-text`, `line-length`, `overused-font`/`single-font`, and `layout-transition`.

**False positives / context:** Single-font and most tiny-text findings are acceptable for this product because `DESIGN.md` explicitly defines compact single-family product UI. Some shadow findings are intentional tokens. But `nested-cards`, low contrast, long error copy, and literal color drift are real.

**Visual overlays:** Injection succeeded in the preview page and console reported the detector issues above. Overlay was browser-visible during the run. Live server stopped after capture.

#### Overall Impression

Dashboard is functional and domain-dense, but not yet visually calm. Biggest opportunity: reduce container/shadow noise and make the primary workflow hierarchy obvious before touching feature logic.

#### What's Working

1. **Workflow state is close to work item.** CR state, Drone state, CR link, Drone link, dates, and actions live in-row where operators need them.
2. **Risky transitions have guardrails.** Destructive state changes route through `ConfirmModal`; invalid/auto states are disabled.
3. **Brand contract is mostly intact.** DBS Red + Black Chrome + compact operations desk language matches `PRODUCT.md`/`DESIGN.md`.

#### Priority Issues

**[P1] Surface stack too heavy**

- **Why it matters:** `filter-frame → table-card → table-scroll → project-table` creates nested-card noise. Users must parse chrome before data.
- **Fix:** Collapse one wrapper layer, remove one shadow level, keep only table-card or table-scroll as the elevated container. Make table header/body the visual anchor.
- **Suggested command:** `/impeccable distill Dashboard surface stack`

**[P1] Empty/error state looks like failure, not recovery**

- **Why it matters:** In preview the main visible Dashboard state is `Dashboard unavailable` + `BRIDGE_UNAVAILABLE` + "No data". This teaches nothing and exposes implementation detail.
- **Fix:** Replace with operator-language recovery: "Desktop bridge unavailable — open in Project Tracker app"; keep one state, not banner plus table error. For true empty state, explain Add Year/Add Project sequence.
- **Suggested command:** `/impeccable clarify Dashboard empty and bridge error states`

**[P1] Horizontal table overload**

- **Why it matters:** `min-width:1540px` forces horizontal scanning for the core workflow. Fine for a power table, but not for the only Dashboard view.
- **Fix:** Keep dense table, but group columns into fixed essentials + scrollable operational details, or split CR/Drone link metadata into secondary row. Make first 4–5 fields readable without horizontal hunting.
- **Suggested command:** `/impeccable layout Dashboard table`

**[P2] Dock discoverability is weak**

- **Why it matters:** Navigation sits at bottom with opacity `.08` until hover. On first view, users may not realize primary navigation exists. Keyboard/screen reader sees it; visual user may miss it.
- **Fix:** Keep dock if desired, but add a persistent small active marker/handle, label on focus, and stronger idle opacity. Add reduced-motion handling.
- **Suggested command:** `/impeccable polish Dashboard dock navigation`

**[P2] Design-token drift + contrast debt**

- **Why it matters:** Literal rgba values outside `DESIGN.md` plus low-contrast `--text-muted` on white will spread inconsistent greys and fail WCAG AA in empty/helper text.
- **Fix:** Add sanctioned alpha/border tokens or replace rgba with existing `hairline/input-border`; bump `.empty-sub` from `--text-muted` to `--text-secondary` or stronger.
- **Suggested command:** `/impeccable audit Dashboard colors and contrast`

#### Persona Red Flags

**Alex (Power User)**

- Inline edits are efficient, but no visible bulk edit, shortcut hints, or keyboard-first path for row actions.
- Horizontal scroll across 1540px table slows repeated CR/Drone updates.
- Auto-hidden dock adds pointer travel/guessing instead of instant navigation.

**Sam (Accessibility-Dependent User)**

- Focus ring exists globally, good. But state meaning is carried by red-heavy selects and compact labels; helper text contrast fails on `.empty-sub`.
- Dock is visually near-invisible at rest (`opacity: .08`), problematic for low-vision users.
- Error state includes technical code, not plain recovery.

**Jordan (First-Timer)**

- "Drone", "CR", "IN-PROGRESS disabled", and REOPEN behavior are unexplained.
- Empty state gives Add Project/Add Year buttons, but not sequence or why year matters.
- Icon dock labels are hidden until hover/focus.

#### Minor Observations

- `stateChipClass` is imported and applied, then overridden to solid red for AS-IS parity; this reads as implementation drift.
- `BRIDGE_UNAVAILABLE` is useful to devs, bad as primary UX copy.
- `border-left:3px` accent appears in global card patterns despite impeccable ban; current `DESIGN.md` preserves it for AS-IS parity, but future work should avoid spreading it.
- Date inputs are compact but visually quiet; users may not realize dates are editable until focus.

#### Questions to Consider

- What if Dashboard had two layers only: status filters + one strong data surface?
- Which columns must be visible at all times for a deployment engineer under pressure?
- Should the dock be delightful, or should it be boring and always discoverable?
- Is AS-IS parity still more important than WCAG/modern productivity polish for Dashboard chrome?
