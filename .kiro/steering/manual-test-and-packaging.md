---
inclusion: always
---

# Manual Test and Packaging Gates

This file summarizes the remaining Windows gates. Authoritative detail lives in
root `CLAUDE.md`, `PRD.md`, and `docs/release-candidate-manual-test-plan.md`.

## Why these are gates

Linux automated tests (`svelte-check`, `vite build`, `pytest`, `py_compile`)
verify core domain logic, bridge response shapes, and guarded imports. They do
NOT verify Windows-only runtime behavior. Passing Linux checks is necessary but
NOT sufficient for release.

## Windows Manual Test Gate (required before packaging)

Must be performed on Windows with a disposable test root (never real project
folders):

- WebView2 window opens; Svelte UI loads from bundled `web/static/` (no raw
  `file://` production loading).
- Settings save/reload root paths without Linux path normalization (Windows
  paths stay Windows paths).
- Page checks: Dashboard, Project Details, Report, Settings, Second Brain,
  Automations.
- Mutation checks: CR Link save, Notes save, Drone CRUD, guarded CR state,
  guarded Drone state, Link Bank add/edit/archive.
- Deferred checks confirmed still deferred/disabled: folder transitions, file
  open/write/delete, Outlook/Teams/COM, scheduler real controls.

See `docs/release-candidate-manual-test-plan.md` for the full checklist.

## Packaging Gate

- Packaging is done ONLY on Windows, and ONLY after the manual RC test passes.
- Do not run PyInstaller (or any Windows packager) on Linux.
- Build the frontend first (`npm --prefix frontend run build`).
- Confirm WebView2 availability and that settings/config/data land in intended
  Windows app-data locations.
- Confirm no secrets or machine-specific paths are bundled.
- Do not add dependencies to enable packaging without explicit user approval.

## Ordering

1. Linux automated baseline green.
2. Windows manual RC test passes.
3. Packaging session on Windows.
