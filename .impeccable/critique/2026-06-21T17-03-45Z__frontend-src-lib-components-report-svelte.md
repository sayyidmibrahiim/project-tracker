---
target: Report Menu
total_score: 18
p0_count: 0
p1_count: 2
p2_count: 2
p3_count: 1
timestamp: 2026-06-21T17-03-45Z
slug: frontend-src-lib-components-report-svelte
---

## Design Health Score

| #         | Heuristic                       | Score     | Key Issue                                                                                          |
| --------- | ------------------------------- | --------- | -------------------------------------------------------------------------------------------------- |
| 1         | Visibility of System Status     | 2         | Barebones loading/error banners; no row count, no filtered-total indicator, no export confirmation |
| 2         | Match System / Real World       | 2         | Domain jargon (CR State, Folder State) unexplained; Drone State column is cryptic                  |
| 3         | User Control and Freedom        | 3         | Clear button and filter resets work well; filter state does not persist across navigation          |
| 4         | Consistency and Standards       | 2         | Button heights inconsistent (30px vs 26px); metric labels use underscored state names              |
| 5         | Error Prevention                | 1         | No confirmation before CSV export; no guardrails on filter state                                   |
| 6         | Recognition Rather Than Recall  | 3         | All controls visible with labels; search icon present; metric cards show counts                    |
| 7         | Flexibility and Efficiency      | 2         | No table sorting, no keyboard shortcuts for filters, no column customization                       |
| 8         | Aesthetic and Minimalist Design | 2         | Side-stripe borders on metric cards and panel; 5 identical metric cards add visual noise           |
| 9         | Error Recovery                  | 1         | Error state shows message but no retry action                                                      |
| 10        | Help and Documentation          | 0         | Zero tooltips, no contextual help, no explanation of domain terms                                  |
| **Total** |                                 | **18/40** | **Poor**                                                                                           |

## Anti-Patterns Verdict

Side-stripe borders on metric-card and panel-card.accent are the primary AI slop tell. 5-card identical metric grid is second-order AI pattern. Detector confirmed 2 warnings (side-tab, layout-transition) and 37 advisory design-system drift items.

## Priority Issues

1. [P1] Side-stripe borders — remove border-left: 3px from metric-card and panel-card.accent
2. [P1] 5 redundant metric cards — replace with compact summary strip or remove
3. [P2] Search input width animation causes layout thrash — use transform or remove
4. [P2] Metric labels use raw state names (UAT_PREPARE) — map to human-readable text
5. [P3] No table sorting or row count — add sortable headers and result count

## Persona Red Flags

- Alex: No keyboard shortcuts, no table sorting, no bulk selection
- Sam: Labels not associated with inputs, no aria-sort, no aria-live for loading
- Riley: No retry on error, no pagination for large datasets, empty state lacks guidance
