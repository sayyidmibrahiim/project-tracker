# Project Tracker

Desktop productivity app. Svelte+TS+Vite+Tailwind frontend, Python 3.12+ backend, pywebview frameless shell, SQLite cache.

## Truth Order

1. User's latest instruction — current pivot when explicit
2. PRD.md — product behavior/rules source of truth (read via offset/limit per section, never full-load; see TOC comments at top of PRD.md)
3. \_docs/PROGRESS.md — progress, gaps, parity
4. This file — workflow/tooling rules
5. `_reference/` HTML prototype — visual/layout reference for AS-IS parity

## Active Menu

Work ONE menu at a time. Current menu stays active until user explicitly approves switching.
Shared element approved in one menu → update across all menus that use it.

## Tech Stack (Locked)

- **Frontend:** Svelte, TypeScript, Vite, Tailwind (local build only, no CDN)
- **Backend:** Python 3.12+, layered monolith
- **Desktop:** pywebview frameless + custom titlebar, WebView2
- **RTE:** NotesEditor editing core = Tiptap v3 (ProseMirror); `frontend/src/lib/markdown.ts` remains the Markdown↔HTML load/serialize layer for the `notes.md` contract (see DECISIONS.md D-0007)
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

## Integration Routing

- **caveman:** response style only; ultra is session-level, not product behavior.
- **context-mode:** owns tool/CLI output compression + in-session continuity; do not add duplicate compression hooks.
- **claude-mem:** active cross-session recall. Memory untuk DECISIONS & context lintas sesi saja, bukan dump semua.
- **graphify:** on-demand graph for blast radius/cross-file lookup; source code remains authority.
- **RTK:** manual-only on native Windows (`rtk ...`); do not claim auto-rewrite outside WSL/Unix shell.

Full routing → `.claude/rules/integration-routing.md` and `_docs/SKILL_ROUTING.md`.

## Session vs Turn

Read `_docs/PROGRESS.md` + `git status` = **once per session**, not every turn.
`graphify` → only before code lookups / blast-radius checks, not every turn.

## Session Lifecycle

| Phase           | Actions                                                                                                     |
| --------------- | ----------------------------------------------------------------------------------------------------------- |
| **Start**       | Once per session: recall memory → read \_docs/PROGRESS.md → git status                                      |
| **Before code** | Use graphify before code lookup/blast-radius checks, not every turn                                         |
| **After code**  | Test/build changed area → update \_docs/PROGRESS.md → refresh graphify → generate manual checklist for user |
| **End**         | Report: changed files, tests run, not tested, next task. Save stable decisions to memory.                   |

## Branch Workflow

The app has **6 menus** + **1 general** = 7 long-lived base branches. Every fix/feature lives on a **sub-branch** off the relevant base branch — never commit product code directly onto a base branch.

### 7 base branches (long-lived, branch off `main`)

| Base branch | Menu | Scope |
| ----------- | ---- | ----- |
| `menu/dashboard` | Dashboard | Dashboard view (PRD §11) |
| `menu/project-details` | Project Details | Project Details view (PRD §12) |
| `menu/second-brain` | Second Brain | Second Brain view (PRD §13) |
| `menu/report` | Report | Report view (PRD §15) |
| `menu/automations` | Automations | Automations view (PRD §16) |
| `menu/settings` | Settings | Settings view (PRD §17) |
| `general/main` | — | Cross-menu / infra / shared work |

### Sub-branch naming: `{type}/{menu}-{desc}` off the menu's base branch

- `type` ∈ `feat` `fix` `design` `refactor` `chore`
- `menu` ∈ `dashboard` `project-details` `second-brain` `report` `automations` `settings` (or `general` for cross-menu)
- Example: fix a RTE bug in Project Details → `fix/project-details-rte-tiptap` off `menu/project-details`.

### Rules

- Read-only/audit = no branch. Docs-only = `chore/` branch. User-level settings = no repo branch.
- **NEVER run two AI sessions on the same working tree** — parallel sessions `git reset --hard` each other's uncommitted work. One branch per session, one session per branch.
- Merge only after user manual check + approval. Code done ≠ slice done — slice done only after user manual verification + merge approval.
- After merge → update \_docs/PROGRESS.md. If behavior changed → update PRD.md too.
- Delete sub-branch after merge. Keep the 7 base branches.

### Cross-provider rule (ALL AI agents — Claude, opencode, Cursor, etc.)

This branching rule is **binding for every AI agent regardless of provider/model**. It is recorded in: `CLAUDE.md` (here), `_docs/WORKFLOW.md`, and `_docs/FILE_ROUTING.md`. If you are any AI agent starting work in this repo: read this section first, always branch off the correct menu base branch, and never touch another session's branch.

## Smallest Diff

Delete > edit > add. No new file, abstraction, config, or dependency unless existing place cannot hold it.
File ownership/routing → `_docs/FILE_ROUTING.md`; workflow detail → `_docs/WORKFLOW.md`.

## PRD Section Routing

Dashboard → PRD §11. Project Details → §12. Drone/CR state → §9. Folder state/filesystem → §7. Global shell/navigation → §10.

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

Product behavior change → PRD.md + \_docs/PROGRESS.md. Progress change → \_docs/PROGRESS.md.
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
