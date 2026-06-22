---
target: Dashboard
total_score: 25
p0_count: 0
p1_count: 3
timestamp: 2026-06-20T07-17-27Z
slug: frontend-src-lib-components-dashboard-svelte
---

#### Design Health Score

| #         | Heuristic                       | Score     | Key Issue                                                                                                          |
| --------- | ------------------------------- | --------- | ------------------------------------------------------------------------------------------------------------------ |
| 1         | Visibility of System Status     | 2         | Error/loading exist, but no real inline save-success trail or scan/refresh progress.                               |
| 2         | Match System / Real World       | 3         | DBS ops vocabulary fits; dashboard still exposes technical bridge-unavailable wording in preview/runtime fallback. |
| 3         | User Control and Freedom        | 2         | Filters/search/year exist; no obvious clear-search/reset-filter affordance inside Dashboard.                       |
| 4         | Consistency and Standards       | 3         | Strong token system; some custom dock/overlay behavior feels non-standard for dense ops work.                      |
| 5         | Error Prevention                | 3         | Destructive state changes guarded; datetime/link blur-save can commit accidentally.                                |
| 6         | Recognition Rather Than Recall  | 2         | Header/search/actions visible; icon-only dock + row menu hide meanings until hover/focus.                          |
| 7         | Flexibility and Efficiency      | 3         | Bulk paste/link editing supports power workflow; no explicit keyboard shortcuts/batch ops visible.                 |
| 8         | Aesthetic and Minimalist Design | 2         | Dense table appropriate, but header/table/dock compete; KPI row missing despite PRD.                               |
| 9         | Error Recovery                  | 2         | Error banners exist; recovery paths are generic.                                                                   |
| 10        | Help and Documentation          | 1         | No contextual dashboard help/tooltips beyond title attrs.                                                          |
| **Total** |                                 | **25/40** | **Acceptable — strong ops foundation, redesign needed for hierarchy/clarity.**                                     |

#### Anti-Patterns Verdict

**LLM assessment:** Does not look like generic SaaS AI slop. It looks like a serious legacy-ops port: dense, red/black banking identity, real controls. Main product slop is not decoration; it is hierarchy debt — every control feels equally important, and the dashboard table dominates before giving the user a quick operational read.

**Deterministic scan:** CLI detector on `frontend/src/lib/components/Dashboard.svelte` returned `[]`. Browser overlay found 4 classes: tiny text, body text near viewport edge in the fallback message, overused/single Inter font, and layout-property transition (`width/min-width`) from global chrome. Single-font is acceptable for product UI; tiny text is intentional but needs contrast/weight discipline.

**Visual overlays:** Injection succeeded in the preview page; overlay reported findings in the `[Human]` tab. Screenshot timed out; snapshot/inspect still worked.

#### Overall Impression

Dashboard has the right operating-room density but wrong top-level read. It jumps straight to a 1320px table and bridge/error state without a command summary. Best redesign: keep compact AS-IS table, but introduce an operational command strip + KPI/readiness band above it, then make the table less visually punitive.

#### What's Working

1. **Real workflow wiring:** Dashboard owns live pywebview bridge calls, search/filter, inline link/datetime/state edits, legal state options, and confirmation guards.
2. **Strong identity:** DBS red + black chrome creates enterprise seriousness; not toy/SaaS.
3. **Efficient row-level editing:** Blur/Enter link paste and state selects support repeated CR/drone updates without leaving the table.

#### Priority Issues

**[P1] Missing PRD KPI row / weak operational summary**

- Why: PRD §11.2 calls for KPI Row before Filter Row. Current UI goes status tabs → table; in bridge-unavailable/error state even status tabs vanish, leaving only table shell.
- Fix: Add compact Dashboard Command Summary: Total CR, UAT Prepare, PROD Ready, Implemented, Postponed/Canceled, Needs Attention/T-10 if available. Use existing counts; no new backend unless adding risk metric.
- Suggested command: `/impeccable shape Dashboard`

**[P1] Table is structurally correct but visually too heavy**

- Why: dark full grid (`#111` borders/header), 1320px min-width, 10 columns, 78–132px rows. Good for parity, but all cells compete; scan path is harsh.
- Fix: Preserve AS-IS density, but redesign hierarchy: sticky first project column, softer internal row dividers, stronger grouped column bands (Project / Schedule / Drone / CR / Actions), reduce black grid to header + group separators.
- Suggested command: `/impeccable layout Dashboard`

**[P1] Inline edits can commit accidentally**

- Why: datetime and link fields save on blur; user can tab/click away and mutate project data without explicit confirmation. Fine for low-risk link paste, riskier for deployment Start/End.
- Fix: Add dirty/saved micro-state per edited cell; for Start/End use Enter-to-save + Esc-to-revert, or a tiny ✓/↩ affordance visible on dirty state. Keep blur-save only for link paste if user wants speed.
- Suggested command: `/impeccable harden Dashboard`

**[P2] Dock nav hides recognition during primary work**

- Why: bottom icon-only dock is elegant but not standard for dense Windows ops. Labels are hover/focus only; notification panel is away from sidebar mental model.
- Fix: For Dashboard, keep bottom dock but add persistent mini labels or current-page text; ensure hover auto-hide never covers last table row/action menu; notification badge should not steal focus from table workflow.
- Suggested command: `/impeccable clarify Dashboard`

**[P2] Empty/error/recovery state reads like dev fallback, not product recovery**

- Why: “Open in Project Tracker desktop app” is accurate in browser preview, but production recovery should say what to do: refresh, check root folder, rebuild cache, open settings.
- Fix: Use a Dashboard recovery panel with 2–3 actions: Refresh Dashboard, Open Settings, Choose Root Folder if unset. Keep desktop-shell copy only for non-pywebview dev.
- Suggested command: `/impeccable onboard Dashboard`

#### Persona Red Flags

**Alex — Power User:** Bulk paste is good, but no visible shortcuts, batch select, clear filter, or edit commit model. 10-column table forces horizontal scroll; repetitive edits need keyboard-first flow.

**Sam — Accessibility-dependent:** Native selects/inputs help. Risks: 10–11px text, icon-only dock, state meaning carried by red fill, title-only tooltips not screen-reader-helpful, blur-save can surprise keyboard users.

**DBS deployment engineer:** Needs “what needs my attention today?” before “all columns.” Current dashboard answers “what exists,” not “what must I act on next.” Add readiness/blocked/approaching-window slices.

#### Minor Observations

- Product UI single Inter font is fine; detector false-positive.
- Tiny text is acceptable for ops density only if contrast stays high and critical labels remain ≥11–12px.
- Header action area at tablet width fits tightly; inspect shows grid compresses to `180px 230px 313px`.
- Browser preview cannot show loaded real rows because pywebview bridge absent; design critique used source + fallback UI + PRD.

#### Questions to Consider

- Should Dashboard optimize for “daily triage” first, or “spreadsheet-like bulk editing” first?
- Should Start/End edits be fast blur-save, or safer explicit save/revert?
- Is AS-IS black grid sacred, or can we soften it while preserving the same column/table contract?
