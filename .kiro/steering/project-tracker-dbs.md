---
inclusion: always
---

# Project Tracker DBS — Kiro Project Context

This file summarizes project rules for Kiro sessions. It does NOT override the
root instruction sources. When anything here conflicts with the sources below,
the sources win.

## Instruction Source Hierarchy (authoritative)

1. **Root `CLAUDE.md`** (`/CLAUDE.md`) is the PRIMARY project instruction source.
   Always defer to it. Do not edit it.
2. **`PRD.md`** (v3.1) is the PRODUCT and ARCHITECTURE truth. If code, old docs,
   comments, or folder structure conflict with `PRD.md`, report the conflict
   before coding. Do not edit it.
3. **`PROJECT_STATUS.md`** is the MIGRATION truth (phase-by-phase status). Update
   it when a phase/slice completes; do not invent status.
4. **`project_tracker/web/js_api.py` + `tests/`** are the BRIDGE CONTRACT truth.
   Frontend `callBridge(...)` names must map to real `JsApi` methods.
5. **`frontend-polish.md`** is SUPPLEMENTAL guidance only (UI polish). It never
   overrides PRD or the bridge contract.

Do NOT use `project_tracker/CLAUDE.md` (it is not the source; absence is expected).

## Tech Stack (locked — see CLAUDE.md/PRD for detail)

- Backend: Python 3.12+, modular monolith, pywebview desktop shell, APScheduler,
  SQLite as rebuildable cache/index only. Filesystem + `project_data.json` are
  canonical truth. `project_state` is never stored in `project_data.json`.
- Frontend: Svelte + TypeScript + Vite + Tailwind (bundled locally, no CDN).
  Production output served from `web/static/` via pywebview HTTP server mode.
- Windows integrations (Outlook COM, Teams/pyautogui, send2trash, os.startfile)
  are Windows-only, lazy/guarded with `sys.platform == "win32"`, and must import
  without crashing on Linux.

## Architecture Dependency Rules

`frontend -> bridge only -> services -> core + infrastructure`. Core stays pure
domain logic. Frontend owns UI-only state; Python owns domain state and rules.

## Working Discipline

- Work phase by phase. Keep changes surgical. Do not refactor unrelated code.
- Use the `.venv` python by full path; shells do not inherit the venv.
- Verify after every change (see `release-candidate-rules.md`).
- See `manual-test-and-packaging.md` for remaining Windows gates.
