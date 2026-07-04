# Workflow — Project Tracker

## Git Branch Convention

Full rule lives in [CLAUDE.md §Branch Workflow](../CLAUDE.md#branch-workflow) — this is the binding cross-provider summary.

`main` is the only stable base branch. Every feature/fix branch is created directly from `main` using `{menu}/{desc}`.

```
dashboard/{desc}          # Dashboard (PRD §11)
project-details/{desc}    # Project Details (PRD §12)
second-brain/{desc}       # Second Brain (PRD §13)
report/{desc}             # Report (PRD §15)
automations/{desc}        # Automations (PRD §16)
settings/{desc}           # Settings (PRD §17)
general/{desc}            # cross-menu / infra / shared
```

Examples:

- `project-details/rte-bugs`
- `dashboard/fix-responsive`
- `general/branch-rule`

- Branch from `main`, merge back to `main`.
- Commit format: `type(scope): description` (conventional commits).
- One logical change per commit.
- **NEVER run two AI sessions on the same working tree** — parallel sessions can `git reset --hard` each other's uncommitted work. One branch per session.
- Delete branch after merge. Keep `main` as the single source of truth.
- Tag releases: `v0.x.0`

### Cross-provider rule (binding for ALL AI agents)

This branching rule applies to **every AI agent regardless of provider/model** (Claude, opencode, Cursor, Gemini, etc.). Read CLAUDE.md §Branch Workflow before starting. Branch directly from `main` using `{menu}/{desc}`. Never touch another session's branch.

## Implementation Discipline

Before coding a phase:

1. Read relevant PRD section
2. Use native search/read tools for codebase understanding
3. Identify files to touch (minimal set)
4. State verification criteria upfront

While coding:

- Keep changes surgical — only touch what's needed
- Do not refactor unrelated code
- Do not delete legacy files without approval
- Reuse existing functions/components; search first, then read only the needed files

After coding:

1. Run relevant tests
2. Run frontend build if frontend changed
3. Generate manual checklist for user
4. Update \_docs/PROGRESS.md
5. Report: changed files, commands run, not tested, remaining risks

## Done Gate

Code selesai ≠ slice selesai (see [CLAUDE.md §Branch Workflow](../CLAUDE.md#branch-workflow)). Slice selesai HANYA setelah user manual verify + approve merge.

## Verification Matrix

Run targeted verification based on change type (JANGAN full suite by default):

| Change Type                  | Verification Command                                                  |
| ---------------------------- | --------------------------------------------------------------------- |
| Frontend-only (Svelte/TS)    | `npm --prefix frontend run build` + `npm --prefix frontend run check` |
| Backend-only (Python)        | `pytest tests/ -v -k <related_test_file_or_pattern>`                  |
| Bridge (services ↔ frontend) | Contract tests: `pytest tests/ -v -k "test_bridge"`                   |
| UI/Dock/Design change        | Manual checklist (generate and hand to user)                          |
| Full suite                   | On-demand only: `/fullcheck` or explicit `pytest tests/ -v`           |

> Full suite is NOT the default. Only run full suite when explicitly requested (`/fullcheck`) or when a change touches both frontend and backend in non-trivial ways.

## Testing Strategy

### Automated (run on this machine)

- Core domain rules, state machine guards
- JSON serialization
- Filesystem scanning logic
- SQLite cache rebuild logic
- Bridge response formatting
- Guarded imports

### Manual (user checks with checklist)

- Visual rendering, layout, spacing
- Button clicks, input fields, form submissions
- Responsive behavior (resize window)
- Hover/focus states
- Loading/error/empty states
- Real data display
- Keyboard navigation
- Console errors in DevTools

### Test Data Rules

- Manual testing: use real project data from filesystem
- Automated tests: use controlled test data (predictable, repeatable)
- No dummy/placeholder data in production UI
- Scanner runs at startup → real data in UI

## Manual Checklist Template

Generate this after every code completion:

```markdown
## Manual Check — [Menu Name] — [Date]

### Functional

- [ ] All buttons clickable and trigger correct action
- [ ] Input fields: type, clear, submit work
- [ ] Data displayed = real data from backend
- [ ] Loading state shows during data fetch
- [ ] Error state shows on failure
- [ ] Empty state shows when no data

### Visual

- [ ] Matches design system + approved design direction
- [ ] Colors consistent with design system
- [ ] Typography consistent (sizes, weights, fonts)
- [ ] Spacing consistent (4px grid)
- [ ] Icons correct and consistent size

### Responsive

- [ ] Window 800×600 — layout not broken
- [ ] Window 1024×768 — layout comfortable
- [ ] Window 1920×1080 — layout fills space well
- [ ] Bottom dock auto-hide/reveal works at all widths (legacy sidebar behavior is bottom dock)

### Interaction

- [ ] Hover states on interactive elements
- [ ] Focus states visible (keyboard nav)
- [ ] Tab order logical
- [ ] Escape closes modals/dropdowns
- [ ] No console errors in DevTools

### Regression (if shared component changed)

- [ ] Other menus using this component still work
- [ ] List affected menus: \_\_\_
```

## Design-First Workflow (UI Tasks)

```
1. User requests UI work
2. Claude creates branch: {menu}/{desc}
3. Claude makes deliberate design decisions up front (DESIGN_RULES tokens,
   layout, spacing, hierarchy, responsive 3+ sizes) — NO separate mockup
   (user rule 2026-07-04: mockups burn tokens; quality bar stays high)
4. Claude codes production Svelte implementation directly
5. Claude generates manual checklist
6. User runs app, checks checklist
7. User gives feedback → Claude fixes (visual iteration is normal)
8. User approves → merge to main
9. Update _docs/PROGRESS.md, PRD.md if behavior changed
```

## Shared Element Protocol

When a shared component (sidebar, button, titlebar, etc.) is approved in one menu:

1. Build it in `frontend/src/lib/components/`
2. Update ALL menus that should use it
3. Generate checklist covering all affected menus
4. User verifies all affected menus
