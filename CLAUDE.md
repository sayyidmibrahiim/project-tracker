# Project Tracker

Desktop productivity app. Svelte+TS+Vite+Tailwind frontend, Python 3.12+ backend, pywebview frameless shell, SQLite cache.

## Truth Order

1. User's latest instruction — current pivot when explicit
2. PRD.md — product behavior/rules source of truth
3. PROJECT_STATUS.md — progress, gaps, parity
4. This file — workflow/tooling rules
5. `_reference/` HTML prototype — visual/layout reference for AS-IS parity

## Active Menu

Work ONE menu at a time. Current menu stays active until user explicitly approves switching.
Shared element approved in one menu → update across all menus that use it.

## Tech Stack (Locked)

- **Frontend:** Svelte, TypeScript, Vite, Tailwind (local build only, no CDN)
- **Backend:** Python 3.12+, layered monolith
- **Desktop:** pywebview frameless + custom titlebar, WebView2
- **Data:** Filesystem + `project_data.json` = canonical. SQLite = rebuildable cache only.
- **Jobs:** APScheduler (in-process)
- **Windows:** Outlook COM (background thread), Teams/pyautogui, send2trash, os.startfile
- **No:** Tauri (unless explicitly requested), PyQt6 (legacy/reference only), Vanilla JS state management

Full details → read `_docs/TECH_STACK.md` when making tech decisions.

## Commands

```bash
# Run app (always from repo root, always repo-root venv)
D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m main

# Tests
D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/ -v

# Frontend build
npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run build

# Package
D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe scripts/package.py

# Graphify (from repo root only)
graphify query "<question>"
graphify update .
```

## Repo-Root Guard

All app/tests/build/graphify run from `D:/Ibrahim/Projects/project_tracker`, never worktrees.
Write/Edit target repo-root paths, never `.claude/worktrees/*/...`.
PreToolUse hook enforces this — if it fires, switch to the command shown in error.

## Threading (Mandatory)

`pywebview.start()` → main thread. COM calls → background thread with `pythoncom.CoInitialize()/CoUninitialize()`.

## Graphify

Graph: `D:/Ibrahim/Projects/project_tracker/graphify-out/graph.json`. Always check absolute path (worktrees won't have it locally).
Use `graphify query/path/explain` before raw file reads. Refresh after code changes.

## Session Lifecycle

| Phase           | Actions                                                                                                    |
| --------------- | ---------------------------------------------------------------------------------------------------------- |
| **Start**       | Recall memory → read PROJECT_STATUS.md → git status → graphify check                                       |
| **Before code** | graphify first → smart-explore for code lookup                                                             |
| **After code**  | Test/build changed area → update PROJECT_STATUS.md → refresh graphify → generate manual checklist for user |
| **End**         | Report: changed files, tests run, not tested, next task. Save stable decisions to memory.                  |

## Branch Workflow

Every change = new branch from main: `{type}/{menu}-{desc}`.
Types: `feat/` `fix/` `design/` `refactor/`. Merge only after user manual check + approval.
After merge → update PROJECT_STATUS.md. If behavior changed → update PRD.md too.

## Design-First Rule

Any UI work → mockup/preview first → user approves → code → manual checklist → user tests → fix → approve.
Read `_docs/DESIGN_RULES.md` for design system when doing frontend.

## Slice Completion Checklist (Mandatory)

Every completed slice → produce FORM CHECKLIST for user:
- Buttons: all states (default, hover, active, disabled, loading)
- Responsive: test at 3+ window sizes
- Input/validation: required fields, edge cases, error messages
- Consistency: matches `_docs/DESIGN_RULES.md` tokens
- Way to test: exact steps user follows to verify

## Documentation Sync

Product behavior change → PRD.md + PROJECT_STATUS.md. Progress change → PROJECT_STATUS.md.
Workflow/tooling change → CLAUDE.md. Stable decision → save memory.

## Do Not Touch Without Approval

`graphify-out/`, `_reference/`, active worktrees, active branches, PRD.md product rules.

## On-Demand Detail Files

Read ONLY when task requires — do not load every session:

| File                     | When to read                                              |
| ------------------------ | --------------------------------------------------------- |
| `_docs/TECH_STACK.md`    | Tech decisions, dependency questions, platform details    |
| `_docs/DESIGN_RULES.md`  | Any frontend/UI/design work                               |
| `_docs/ARCHITECTURE.md`  | Backend structure, layer rules, bridge, persistence model |
| `_docs/WORKFLOW.md`      | Git ops, implementation checklist, testing strategy       |
| `_docs/SKILL_ROUTING.md` | Choosing which skills/plugins to invoke                   |
