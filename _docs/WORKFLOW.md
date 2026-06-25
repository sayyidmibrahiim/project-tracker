# Workflow — Project Tracker

## Git Branch Convention

```
main (stable, tested)
  ├── feat/{menu}-{desc}        # New feature
  ├── fix/{menu}-{desc}         # Bug fix
  ├── design/{menu}-{desc}      # Design/UI change
  └── refactor/{menu}-{desc}    # Code restructure, no behavior change
```

- Branch from main, merge back to main
- Commit format: `type(scope): description` (conventional commits)
- One logical change per commit
- Delete branch after merge
- Tag releases: `v0.x.0`

## Implementation Discipline

Before coding a phase:

1. Read relevant PRD section
2. Use graphify for codebase understanding
3. Identify files to touch (minimal set)
4. State verification criteria upfront

While coding:

- Keep changes surgical — only touch what's needed
- Do not refactor unrelated code
- Do not delete legacy files without approval
- Reuse existing functions/components (graphify + smart-explore to find them)

After coding:

1. Run relevant tests
2. Run frontend build if frontend changed
3. Generate manual checklist for user
4. Update PROJECT_STATUS.md
5. Refresh graphify if installed
6. Report: changed files, commands run, not tested, remaining risks

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

- [ ] Matches approved design mockup
- [ ] Colors consistent with design system
- [ ] Typography consistent (sizes, weights, fonts)
- [ ] Spacing consistent (4px grid)
- [ ] Icons correct and consistent size

### Responsive

- [ ] Window 800×600 — layout not broken
- [ ] Window 1024×768 — layout comfortable
- [ ] Window 1920×1080 — layout fills space well
- [ ] Sidebar collapse works at narrow width

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
2. Claude creates branch: design/{menu}-{desc}
3. Claude creates mockup (SVG preview or minimal HTML)
4. User reviews → gives feedback
5. Iterate mockup until user says "ok" / "lanjut"
6. Claude codes production Svelte implementation
7. Claude generates manual checklist
8. User runs app, checks checklist
9. User gives feedback → Claude fixes
10. User approves → merge to main
11. Update PROJECT_STATUS.md, PRD.md if behavior changed
```

## Shared Element Protocol

When a shared component (sidebar, button, titlebar, etc.) is approved in one menu:

1. Build it in `frontend/src/lib/components/`
2. Update ALL menus that should use it
3. Generate checklist covering all affected menus
4. User verifies all affected menus
