# Project Tracker

Desktop productivity app. Svelte+TS+Vite+Tailwind frontend, Python 3.12+ backend, pywebview frameless shell, SQLite cache.

## Cold Start / Truth Order

Read `CLAUDE.md` first, then read project state in this order before coding:

1. `_docs/WORKFLOW.md` — workflow rules, doc sync rule
2. `_docs/PROGRESS.md` — current tracking
3. `_docs/session-notes.md` — active context: Now / Next / Blocked
4. `_docs/DECISIONS.md` — architectural decisions `D-XXXX`
5. `_docs/ARCHITECTURE.md` — layer structure and dependency flow
6. `_docs/DESIGN_RULES.md` — design tokens and components
7. `PRD.md` — product requirements reference, not latest coding status
8. This file — workflow/tooling guardrails
9. `_reference/` HTML prototype — legacy visual reference only; do not override implemented decisions

`PRD.md` is blueprint. `_docs/` is actual state. Do not assume PRD equals latest implementation.

Implemented decisions beat `_reference/` for finished areas, especially frameless window titlebar, Dashboard, and Project Details.

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

# Full tests (only when explicitly requested)
D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/ -v

# Frontend build (only when explicitly requested or packaging)
npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run build

# Default simple verification: run app, watch startup/runtime errors, fix surfaced issues
D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m main

# Package
D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe scripts/package.py
```

## Repo-Root Guard

All app/tests/build/runtime verification commands run from `D:/Ibrahim/Projects/project_tracker`, never worktrees.
Write/Edit target repo-root paths, never `.claude/worktrees/*/...`.
PreToolUse hook enforces this — if it fires, switch to the command shown in error.

## Threading (Mandatory)

`pywebview.start()` → main thread. COM calls → background thread with `pythoncom.CoInitialize()/CoUninitialize()`.

## Headroom

Setup Headroom:

- Status: Installed in repo venv; proxy runs at Start/manual launch
- Proxy URL: `http://localhost:8787`
- Use a local proxy for Start/Stop, or an external Docker sidecar like `http://headroom:8787`.
- Install then click Start:

```bash
pip install "headroom-ai[proxy]"
```

## Integration Routing

- **caveman:** response style only; ultra is session-level, not product behavior.
- **context-mode:** owns tool/CLI output compression + in-session continuity; do not add duplicate compression hooks.
- **claude-mem:** active cross-session recall. Memory untuk DECISIONS & context lintas sesi saja, bukan dump semua.
- **Headroom:** optional local proxy at `http://localhost:8787`; source code remains authority.
- **RTK:** manual-only on native Windows (`rtk ...`); do not claim auto-rewrite outside WSL/Unix shell.

Full routing → `.claude/rules/integration-routing.md` and `_docs/SKILL_ROUTING.md`.

## Session vs Turn

Read `_docs/PROGRESS.md` + `git status` = **once per session**, not every turn.

## Session Lifecycle

| Phase           | Actions                                                                                                     |
| --------------- | ----------------------------------------------------------------------------------------------------------- |
| **Start**       | Once per session: read cold-start docs in truth order → git status                                           |
| **Before code** | Use native search/read tools before code changes; keep lookup scoped to the files needed                    |
| **After code**  | Run app for simple verification → fix surfaced errors → update docs → generate manual checklist for user    |
| **End**         | Report: changed files, verification run, not tested, next task. Save stable decisions to memory.            |

## Branch Workflow

`main` is the only stable base branch. Every feature/fix branch is created directly from `main` using `{menu}/{desc}`.

### Branch format: `{menu}/{desc}`

| Prefix             | Scope                            |
| ------------------ | -------------------------------- |
| `dashboard/`       | Dashboard view (PRD §11)         |
| `project-details/` | Project Details view (PRD §12)   |
| `second-brain/`    | Second Brain view (PRD §13)      |
| `report/`          | Report view (PRD §15)            |
| `automations/`     | Automations view (PRD §16)       |
| `settings/`        | Settings view (PRD §17)          |
| `general/`         | Cross-menu / infra / shared work |

Examples:

- RTE bugs in Project Details → `project-details/rte-bugs`
- Dashboard responsive fix → `dashboard/fix-responsive`
- Cross-provider branch rule docs → `general/branch-rule`

### Rules

- Read-only/audit = no branch. User-level settings = no repo branch.
- Branch from `main`; merge back to `main` only after user manual check + approval.
- Code done ≠ slice done — slice done only after user manual verification + merge approval.
- After merge → update \_docs/PROGRESS.md. If behavior changed → update PRD.md too.
- Delete branch after merge. Keep `main` as the single source of truth.
- **NEVER run two AI sessions on the same working tree** — parallel sessions can `git reset --hard` each other's uncommitted work. One branch per session, one session per branch.

### Cross-provider rule (ALL AI agents — Claude, opencode, Cursor, etc.)

This branching rule is **binding for every AI agent regardless of provider/model**. It is recorded in: `CLAUDE.md` (here), `_docs/WORKFLOW.md`, and `_docs/FILE_ROUTING.md`. If you are any AI agent starting work in this repo: read this section first, branch directly from `main` using `{menu}/{desc}`, and never touch another session's branch.

## Smallest Diff

Delete > edit > add. No new file, abstraction, config, or dependency unless existing place cannot hold it.
File ownership/routing → `_docs/FILE_ROUTING.md`; workflow detail → `_docs/WORKFLOW.md`.

## PRD Section Routing

Use `_docs/session-notes.md`, `_docs/PROGRESS.md`, and `_docs/DECISIONS.md` first to determine current menu/state. Use PRD sections only as behavior reference after confirming they still match actual docs.

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

`_reference/`, active worktrees, active branches, PRD.md product rules.

## On-Demand Detail Files

Read ONLY when task requires — do not load every session:

| File                     | When to read                                              |
| ------------------------ | --------------------------------------------------------- |
| `_docs/TECH_STACK.md`    | Tech decisions, dependency questions, platform details    |
| `_docs/DESIGN_RULES.md`  | Any frontend/UI/design work                               |
| `_docs/ARCHITECTURE.md`  | Backend structure, layer rules, bridge, persistence model |
| `_docs/WORKFLOW.md`      | Git ops, implementation checklist, testing strategy       |
| `_docs/SKILL_ROUTING.md` | Choosing which skills/plugins to invoke                   |
