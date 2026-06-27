---
name: design-review
description: Compare a Project Tracker UI slice against DESIGN.md, SPEC, and live implementation; report gaps only, not preferences.
user-invocable: true
---

# Design Review

Use after UI implementation and before user checklist.

Inputs: menu/feature name, SPEC path if present, changed files.

Steps:
1. Read `_docs/DESIGN_RULES.md` and relevant `_specs/SPEC-*.md`.
2. Inspect changed Svelte/CSS files only.
3. Compare visual tokens, layout, states, responsive behavior, and shared-component propagation.
4. Report only mismatches that need action.

Output format:

```text
path:line: severity: gap. fix.
```

Do not propose new visual direction. Do not edit files.
