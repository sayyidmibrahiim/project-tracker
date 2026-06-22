---
target: Dashboard
total_score: 20
p0_count: 1
p1_count: 3
timestamp: 2026-06-21T16-26-16Z
slug: frontend-src-lib-components-dashboard-svelte
---

#### Design Health Score

| #         | Heuristic                       | Score     | Key Issue                                                                                                                            |
| --------- | ------------------------------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| 1         | Visibility of System Status     | 2         | Loading/error exists, but current Dashboard cannot render due Svelte compile error.                                                  |
| 2         | Match System / Real World       | 2         | Icons/symbols feel ad-hoc: ＋, ⚠, ↗, ⋮, 🔒. Not professional productivity vocabulary.                                                |
| 3         | User Control and Freedom        | 3         | Filters/reset and row menu exist. Good baseline.                                                                                     |
| 4         | Consistency and Standards       | 2         | Table chrome, group headers, command metrics, action symbols feel stitched from different systems.                                   |
| 5         | Error Prevention                | 3         | Destructive state/delete confirmation exists. Good.                                                                                  |
| 6         | Recognition Rather Than Recall  | 2         | Too many small controls depend on table headers and symbolic cues. Removing headers requires stronger row layout labels/affordances. |
| 7         | Flexibility and Efficiency      | 2         | Dense inline edit good; visual hierarchy slows scanning.                                                                             |
| 8         | Aesthetic and Minimalist Design | 1         | Metric cards + table group header + table box create unnecessary chrome. User is right: clutter hurts pro feel.                      |
| 9         | Error Recovery                  | 2         | Error panels exist, but current compile error blocks UI entirely.                                                                    |
| 10        | Help and Documentation          | 1         | No contextual guidance for dense inline editing.                                                                                     |
| **Total** |                                 | **20/40** | **Acceptable foundation, major visual/professional polish needed.**                                                                  |

#### Anti-Patterns Verdict

**LLM assessment**: Dashboard has solid operational intent, but current surface reads like a prototype-heavy admin table, not a calm productivity app. Main causes: unnecessary summary metric strip, double table headers, boxed table container, saturated red everywhere, inconsistent symbols.

**Deterministic scan**: 1 advisory in `frontend/src/lib/components/Dashboard.svelte:608`: undocumented literal shadow color `rgba(0,0,0,.10)`. Minor design-system drift.

**Browser evidence**: Viewable target failed before visual critique. Vite reports `Dashboard.svelte:396:65 {#if ...} block cannot be in attribute value`. No reliable rendered Dashboard overlay.

#### Overall Impression

User critique is correct. Dashboard has useful data density, but chrome is doing too much. Remove redundant framing and switch to Notion-like quiet productivity: fewer boxes, quieter borders, cleaner symbols, stronger spacing rhythm.

#### What's Working

1. Inline editing is the right product pattern for this workflow. No modal-first laziness.
2. Local-first risk controls exist: destructive state/delete paths have confirmation.
3. Status tabs are useful; they should stay, but visually quieter.

#### Priority Issues

**[P0] Build-blocking Svelte syntax**

- **Why it matters**: Dashboard cannot render; any visual critique is secondary until fixed.
- **Fix**: Replace invalid `{#if ...}` fragments inside attributes/content with normal expressions.
- **Suggested command**: `/impeccable harden Dashboard`

**[P1] Redundant dashboard chrome**

- **Why it matters**: Metric cards, group headers, and outer table box make app feel like generated admin dashboard, not productivity workspace.
- **Fix**: Remove metric card strip, remove PROJECT/SCHEDULE/DRONE/CR/ACTION group row, remove direct table container border/padding/shadow.
- **Suggested command**: `/impeccable distill Dashboard`

**[P1] Icon/symbol vocabulary is unprofessional**

- **Why it matters**: Mixed symbols (＋, ⚠, ↗, ⋮, 🔒) look inconsistent and toy-like.
- **Fix**: Use one restrained icon vocabulary: text labels where possible; otherwise simple professional glyphs with aria-label/title. Avoid emoji.
- **Suggested command**: `/impeccable polish Dashboard`

**[P1] Tone mismatch: banking ops vs Notion-like productivity**

- **Why it matters**: Current UI feels boxed, loud, and admin-ish. Notion-like productivity needs quiet surfaces, crisp type, low ornament, visible structure without containers everywhere.
- **Fix**: White workspace, hairline separators, minimal hover states, red only for primary/action/state, reduce shadows.
- **Suggested command**: `/impeccable quieter Dashboard`

**[P2] Design-system drift**

- **Why it matters**: Literal colors/shadows accumulate into inconsistent UI.
- **Fix**: Use existing DESIGN.md shadow/color tokens.
- **Suggested command**: `/impeccable audit Dashboard`

#### Persona Red Flags

**Alex — power user**: Inline edit is good, but visual noise slows scanning. Too many boxes and headers reduce throughput.

**Sam — accessibility-dependent user**: Emoji/symbol-only controls need better accessible names. Compile error blocks all access.

**DBS deployment engineer**: Needs fast CR scan. Summary cards and group headers steal vertical space from actual projects.

#### Minor Observations

- Status tabs can stay but should look like quiet segmented filters, not dashboard widgets.
- Red state selects may be too loud when repeated across every row.
- Row action menu icon should become a professional kebab/More control with clearer menu labels.

#### Questions to Consider

- What if Dashboard becomes closer to a clean workspace list than a table-in-card dashboard?
- Should red mean only action/risk/current state, not repeated row decoration?
- Can project rows carry context through spacing and labels instead of extra header bands?
