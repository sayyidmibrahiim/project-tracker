# Frontend — Project Tracker

Svelte + TypeScript + Vite + Tailwind CSS v4. Output → `../web/static/`.

## Stack

- Svelte (plain, NOT SvelteKit). Components in `src/lib/components/`.
- Tailwind v4 via PostCSS. Theme tokens in `src/styles.css` `:root` CSS vars.
- `@theme` aliasing = DEFERRED. Use CSS vars directly.
- TypeScript strict mode preferred.

## Commands

```bash
npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run build    # production
npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run check    # svelte-check (MUST pass)
npm --prefix D:/Ibrahim/Projects/project_tracker/frontend test         # node --test
```

## Rules

- `svelte-check` MUST pass (0 errors) before commit.
- Bridge calls go through `src/lib/bridge.ts` only, never raw `window.pywebview`.
- UI state (selected row, modal open) = Svelte. Domain state = Python backend.
- Design tokens: read `src/styles.css` `:root`, match `_docs/DESIGN_RULES.md`.
- DBS red `#B91C1C` = accent only, not dominant. Dark chrome header, white canvas.
