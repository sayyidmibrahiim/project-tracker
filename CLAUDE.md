CLAUDE.md

This file provides operational guidance to Claude Code when working in this repository.

Graphify Knowledge Graph (token reduction, worktree-safe)

Main graph lives at `D:/Ibrahim/Projects/project_tracker/graphify-out/graph.json`. Claude may run inside `.claude/worktrees/*`; if `./graphify-out/graph.json` is missing, do **not** say graphify is unavailable. Always check the absolute graph path first.

- Run graphify commands from `D:/Ibrahim/Projects/project_tracker`, not from a worktree.
- For codebase questions, use `graphify query "<question>"` first when the graph exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts.
- Use `claude-mem:smart-explore` after graphify for exact code structure lookup.
- Read `graphify-out/GRAPH_REPORT.md` only for broad architecture review or when query/path/explain do not surface enough.
- Read raw files only to modify/debug specific code, when graphify lacks detail, or when graphify is not installed.
- To refresh after modifying code or documentation, run `graphify D:/Ibrahim/Projects/project_tracker --update` or run `graphify update .` from `D:/Ibrahim/Projects/project_tracker`.
- Graph excludes `.venv/` and `node_modules/` via `.gitignore`. `redesign_ui/` legacy PyQt6 is reference only; treat it as legacy per Current Project Mode.

Highest Priority Rule

PRD.md v3.1 is the product and architecture source of truth.

If CLAUDE.md, current code, old docs, comments, or existing folder structure conflict with PRD.md, report the conflict before coding. Do not silently follow outdated instructions.

Do not implement the whole PRD in one pass. Work phase by phase, with explicit verification after each phase.

Current Project Mode

Current migration direction:

- Old PyQt6 UI and old static HTML UI are legacy/reference.
- New production UI uses Svelte + TypeScript + Vite + Tailwind.
- Backend/domain remains Python 3.12+.
- Desktop shell remains pywebview.
- SQLite is approved only as a rebuildable local cache/index.
- Filesystem + project_data.json remain canonical source of truth.
- Windows automation remains Python-based.

Locked Tech Stack

Backend:

- Python 3.12+
- Modular monolith
- pywebview desktop shell
- APScheduler for local scheduled/background jobs
- SQLite as local rebuildable cache/index only
- Local filesystem + JSON metadata as canonical source of truth

Frontend:

- Svelte
- TypeScript
- Vite
- Tailwind CSS bundled locally through frontend build
- Production frontend output must be served by pywebview local HTTP server / serve-folder mode
- Do not use raw file:// loading for production frontend
- Do not use Tailwind CDN as production strategy
- Do not use Vanilla JS as production state-management strategy

Windows integrations:

- Outlook COM through pythoncom / win32com
- Teams automation through guarded Windows-only service code
- pyautogui for Teams desktop automation where required
- send2trash for Recycle Bin delete
- os.startfile for Windows file opening

Future migration candidate only:

- Tauri v2 + Svelte + Python sidecar may be considered after MVP stability.
- Do not migrate to Tauri unless explicitly requested by the user.

Available Tools, MCPs, Skills, and Plugins

Use available tools intentionally. Do not invoke unrelated skills just to satisfy a checklist.

MCP Servers

context7

Purpose:

- Fetch current documentation for libraries, frameworks, APIs, and config patterns.

Use context7 before changing or implementing:

- Svelte
- Vite
- Tailwind
- pywebview
- PyInstaller
- APScheduler
- SQLite-related Python APIs if uncertain
- Any unfamiliar or version-sensitive library behavior

Required workflow:

1. Resolve the library ID.
2. Query the relevant docs.
3. Apply only the documented behavior.
4. Mention which docs were consulted in the final implementation summary.

Do not rely on memory for version-sensitive library setup.

Memory / Agent Memory

Use memory tools when available for cross-session project continuity.

Use memory recall when:

- The task references previous decisions.
- The task depends on prior migration status.
- The task asks “continue from last time.”
- The project status is unclear.

Use memory save only for stable project decisions, such as:

- Approved tech stack decisions.
- Approved architecture decisions.
- Migration phase status.
- User-confirmed constraints.

Do not save secrets, credentials, machine-specific private paths beyond what already exists in repository docs, or sensitive personal information.

Prompts / Prompt Library

Use prompts.chat tools only when explicitly useful for reusable prompts or reusable project instructions.

Do not upload private project code, secrets, credentials, proprietary content, or internal business data to external prompt libraries unless the user explicitly approves.

RTK (optional, only if installed)

RTK is a Linux-oriented token-optimization CLI proxy. It is NOT required on Windows and may not be installed on this machine.

- If the `rtk` command is available, you may prefix shell commands with `rtk` (including each command in && chains) to reduce token usage.
- If `rtk` is NOT installed, run all commands directly WITHOUT the `rtk` prefix. Do not attempt to install it just to satisfy these instructions.
- RTK is a token-optimization wrapper, not a correctness tool. Still run normal verification.
- All command examples in this file that show a leading `rtk` are optional: drop the `rtk` prefix if the tool is absent.

Skill Routing Rules

Use skills when they are relevant. Before any non-trivial task, choose the smallest useful skill set.

Planning and Architecture

Use these before broad or architectural changes:

- writing-plans
- brainstorming
- fullstack-dev-skills:python-pro
- legacy-modernizer
- harness-plan, if available

Use for:

- Migration planning
- Phase planning
- Architecture decisions
- PRD-to-code gap analysis
- Multi-file refactor planning

Do not code before plan approval when the user asks for audit/plan first.

Python Backend Work

Use:

- fullstack-dev-skills:python-pro
- test-driven-development
- systematic-debugging for bugs
- verification-before-completion

Use for:

- Core domain models
- State machines
- Filesystem services
- Metadata stores
- SQLite cache/index
- APScheduler jobs
- pywebview bridge backend
- Windows integration wrappers

Frontend Work

Use:

- frontend-design
- Svelte-related frontend skill if available
- context7 for current Svelte/Vite/Tailwind docs
- test-driven-development where practical
- verification-before-completion

Use for:

- Svelte component structure
- Vite setup
- Tailwind setup
- Frontend stores
- Dashboard UI
- Project Details UI
- Second Brain UI
- Automations UI
- Settings UI

Frontend rule:

- Svelte components own UI state only.
- Domain state and business rules stay in Python services.

Debugging

Use:

- systematic-debugging

Required behavior:

1. Reproduce or identify the failing behavior.
2. Inspect logs/errors.
3. Form a hypothesis.
4. Make the smallest fix.
5. Verify.
6. Do not patch randomly.

Testing and Verification

Use:

- test-driven-development
- verification-before-completion
- verify
- harness-review, if available

Required after implementation:

- Run relevant Python tests.
- Run frontend build when frontend changed.
- Report commands run.
- Report what was not tested.
- Update PROJECT_STATUS.md.

Code Review and Safety

Use:

- code-review
- security-reviewer for security-sensitive code
- secure-code-guardian for risky file/OS/automation changes

Use for:

- Destructive operations
- File delete/move behavior
- COM automation
- Teams automation
- Shell command execution
- Settings persistence
- Path handling
- Packaging

Simplification

Use:

- simplify

Use only after a working implementation exists, and only for the changed area.

Do not refactor unrelated code.

Harness Skills

If available, use harness skills as follows:

- harness-setup for repository/setup alignment.
- harness-plan for phase planning.
- harness-work for implementing approved phase work.
- harness-review for reviewing changes.
- harness-progress for progress tracking.
- harness-release only for packaging/release work.

Harness skills do not override PRD.md.

Project Execution Skills

If available, use project execution skills as follows:

- discovery:create-epic-discovery for unclear requirements.
- planning:create-implementation-plan for each major phase.
- execution:execute-ticket for approved implementation slices.
- execution:complete-ticket only after verification.
- retrospectives:complete-sprint or complete-epic only when explicitly requested.

Commands

This is a Windows machine. Use Windows paths (backslashes) and the Windows venv interpreter. Claude Code shells do not inherit the active venv; use the full venv path or activate it first. See WINDOWS_SETUP.md for first-time bootstrap (create venv, install deps, build frontend).

One-time setup (PowerShell, from repository root):

py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm --prefix frontend install
npm --prefix frontend run build

Python tests:

.\.venv\Scripts\python.exe -m pytest tests/ -v
.\.venv\Scripts\python.exe -m pytest tests/ -q

Targeted Python test example:

.\.venv\Scripts\python.exe -m pytest tests/test_phase_b_stores.py -v

Frontend commands:

npm --prefix frontend install
npm --prefix frontend run build

Run the desktop app (pywebview, from repository root):

.\.venv\Scripts\python.exe -m main

The production frontend is served from web/static/ (built by `npm --prefix frontend run build`). A prebuilt web/static/ is included in this copy, so the app runs immediately after installing Python deps. Rebuild it whenever frontend source changes.

Package for Windows release with PyInstaller (allowed on this machine):

.\.venv\Scripts\python.exe scripts\package.py

PyInstaller now runs on this Windows machine. The legacy "do not run PyInstaller on Linux" rule no longer applies here, since this is the Windows target.

Environment Boundaries

This is now the Windows target machine, so all integrations are LIVE and fully testable. The Windows-only code paths that were stubbed/skipped during Linux development now run for real.

Component — status on this Windows machine:

- Core logic, filesystem, JSON — Full app + unit tests
- SQLite cache/index — Full app + unit tests
- Svelte/Vite frontend build — Full build
- pywebview shell — Full app (real WebView2 rendering)
- PyQt6 UI shell — Reference only / deprecated (do not develop)
- Outlook COM — Real integration (live)
- Teams / pyautogui — Real integration (live)
- send2trash, os.startfile — Real integration (live)
- PyInstaller — Allowed (Windows packaging runs here)

Windows-only imports are still guarded with sys.platform == "win32" by design; keep those guards intact for cross-platform correctness even though they now resolve true.

The "must instantiate without crashing on Linux" rule was a Linux-dev safety constraint. Keep the guarded/lazy-import structure (do not rip it out), but on this machine these services are expected to actually work, not stub out.

Do not add dependencies without explicit user confirmation, except dependencies already approved in PRD.md v3.1.

Use pathlib.Path; never use string path concatenation.

Keep Windows-formatted paths in settings JSON as Windows paths. Do not normalize them into Linux paths.

Threading Rule — Mandatory

pywebview.start() must run on the main thread.

All COM calls must run on a background thread and must initialize COM inside that thread.

import threading
import pythoncom
def \_com_task():
pythoncom.CoInitialize()
try:
pass
finally:
pythoncom.CoUninitialize()
threading.Thread(target=\_com_task, daemon=True).start()

Frontend Rules

Production UI must be implemented in Svelte + TypeScript + Vite.

Do not build new production screens with raw HTML + Tailwind CDN + Vanilla JS.

Small isolated JavaScript utilities are allowed only when they do not become application state management.

Frontend source should live under frontend/.

Vite build output should be served by pywebview through the configured static output folder described in PRD.md.

Tailwind must be bundled locally through the frontend build. Do not rely on CDN for production.

Before changing frontend build configuration, use context7 to check current Svelte/Vite/Tailwind documentation.

Python ↔ Frontend Bridge Rules

The frontend communicates with Python through the typed pywebview bridge.

The Python bridge/API layer must return predictable response objects.

Business/domain logic belongs in Python services, not in Svelte components.

Frontend state is UI-only state:

- active page
- selected row/project/link/note
- search/filter form state
- modal open/close state
- loading and error states
- draft form values

Python owns:

- project state machine
- folder transitions
- metadata writes
- scanner
- SQLite cache/index rebuild
- watchdog events
- Outlook/Teams automation
- scheduler jobs
- notification persistence

Persistence Model

Canonical source of truth:

- Filesystem determines project existence.
- Year folder determines project year.
- Parent state folder determines project folder state.
- project_data.json stores project metadata only.
- project_state must never be stored in project_data.json.

SQLite rule:

- SQLite is approved only as a local rebuildable cache/index.
- SQLite must never become the canonical source of truth for project existence, year, folder state, or project metadata.
- If the SQLite database is deleted or corrupted, the app must be able to rebuild it from filesystem + JSON + local note/link files.

Atomic JSON writes must use the metadata store atomic write mechanism.

Hard delete is forbidden. Deletion must use Recycle Bin via send2trash on Windows.

Datetimes must be ISO 8601 timezone-aware using the local OS timezone.

Legacy / Reference Code Rules

PyQt6 files are legacy/reference only.

Do not add new production PyQt6 UI code.

Do not copy PyQt6 implementation code into production.

Use PyQt6 prototype files only to understand:

- user flows
- screen components
- interactions
- menu behavior
- feature intent

Old frontend/\*.html files are legacy/reference unless verified as part of the new Svelte frontend.

Do not claim a screen is migrated until it is connected to real data, verified, and tracked in PROJECT_STATUS.md.

Do not delete legacy PyQt6/reference files unless explicitly approved by the user.

Architecture Direction

Target architecture:

frontend/ Svelte UI
-> pywebview JsApi bridge
-> services/
-> core/
-> infrastructure/

Dependency rules:

frontend -> bridge only
bridge -> services
services -> core + infrastructure
infrastructure -> core when needed
core -> no UI, no services, no infrastructure

Core layer must remain pure domain logic.

Services layer coordinates use cases.

Infrastructure layer owns filesystem, JSON stores, SQLite cache, settings, link bank, watchdog, Outlook, Teams, and OS integrations.

Implementation Discipline

Do not implement the whole PRD in one pass.

Work phase by phase.

Before coding a phase:

1. Read the relevant PRD section.
2. Use relevant planning/architecture skill for non-trivial tasks.
3. Use context7 for version-sensitive library/framework work.
4. Identify files to touch.
5. State verification criteria.
6. Keep changes surgical.
7. Do not refactor unrelated code.
8. Do not delete legacy/reference files unless explicitly approved.

After coding a phase:

1. Run relevant tests.
2. Run frontend build when applicable.
3. Use verification skill/checklist when available.
4. If the `graphify` CLI is installed, run `graphify update .` to refresh the knowledge graph (skip if not installed).
5. Update PROJECT_STATUS.md.
6. Report changed files.
7. Report commands run.
8. Report what was not tested.
9. Report remaining risks.

Testing Notes

Automated tests (run on this Windows machine) verify:

- core domain rules
- state machine guards
- JSON serialization
- filesystem scanning logic
- SQLite cache/index rebuild logic
- bridge response formatting
- guarded imports

Windows live verification (now runnable here, previously only on the Windows target):

- Outlook COM
- Teams automation
- send2trash
- os.startfile
- WebView2 behavior
- visual rendering
- packaging
- installer behavior

No automated test may open blocking dialogs or require manual clicks.

Current First Safe Workflow

When starting a new session, do this first unless the user gives a narrower task:

1. Read PRD.md.
2. Read CLAUDE.md.
3. Read PROJECT_STATUS.md if it exists.
4. Inspect repository tree.
5. Report contradictions before coding.
6. Work only on the approved phase/task.

For the current migration, the first safe task is:

- Phase 0: align CLAUDE.md, create/update PROJECT_STATUS.md, create/update MIGRATION_PLAN.md, and audit repository readiness.

Do not start production code implementation before Phase 0 is approved.

<!-- rtk-note (windows) -->

# RTK (optional, Linux tooling)

RTK (Rust Token Killer) is a Linux-oriented token-optimization CLI. The full RTK command reference that previously lived here has been removed because RTK is typically not installed on Windows.

- If `rtk` IS installed on this machine, you may prefix commands with it to reduce token usage (see the RTK section above). It passes commands through unchanged when it has no dedicated filter, so it is safe.
- If `rtk` is NOT installed (the normal Windows case), run every command directly without the `rtk` prefix. Do not install RTK solely to follow these instructions.

<!-- /rtk-note -->

## Vibe-Code Menu Workflow

Work **one menu at a time**. Current menu stays active until the user explicitly approves switching menus.

## Repo-Root Execution Guard (hard rule)

The real project root is `D:/Ibrahim/Projects/project_tracker`. The user launches the app and runs full test/build commands from this root, never from a `.claude/worktrees/*` checkout.

- Always run app/tests/build/graphify against `D:/Ibrahim/Projects/project_tracker`.
- If Claude is invoked from `.claude/worktrees/*`, do **not** run the app there for runtime comparison; it may compare a stale/different UI and waste tokens.
- All runtime verification must use the same command the user uses:
  `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m main`
- Python tests must use the repo-root venv:
  `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/ ...`
- Frontend commands must run from repo root or target repo root:
  `npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run check|test|build`
- Graphify commands must run from `D:/Ibrahim/Projects/project_tracker`, not from a worktree.
- Config/docs edits (`CLAUDE.md`, `PROJECT_STATUS.md`, `.claude/settings.json`) must target repo-root files, not worktree copies.
- Write/Edit paths for this project must target `D:/Ibrahim/Projects/project_tracker/...`, never `.claude/worktrees/*/...`.

A PreToolUse hook in `.claude/settings.json` calls `scripts/claude_root_guard.py` and blocks wrong-root app/test/build/graphify commands plus worktree file edits. If it fires, switch to the repo-root command shown in the error. Do not fight the guard.

A SessionStart hook injects this reminder into new sessions so future sessions inherit the rule without the user repeating it.

### Truth order

1. User latest instruction — current pivot direction when explicit.
2. `PRD.md` — product behavior/rules source of truth.
3. `PROJECT_STATUS.md` — progress, known gaps, parity status.
4. `CLAUDE.md` — workflow/tooling/agent rules.
5. `contoh_UI/project_tracker_dbs_full_prototype_v2_AS_IS_PY_INJECTED.html` — visual/layout reference for AS-IS parity.

### Session lifecycle

- **Start**: read `PROJECT_STATUS.md`, check git/worktree status, check graphify absolute path, recall memory for latest decisions.
- **During**: invoke only relevant skills/plugins; do not run random skill checklists.
- **Before code**: graphify first when graph exists → `claude-mem:smart-explore` for precise code lookup.
- **After code**: run tests/build/app checks for changed area, update `PROJECT_STATUS.md`, refresh graphify when available.
- **End**: prune stale clean `.claude/worktrees/agent-*` after inspection, report changed files/tests/remaining gaps/next step.

### Do not touch without approval

- `graphify-out/`
- `contoh_UI/`
- active harness worktrees
- active Claude worktrees
- active feature branches
- `PRD.md` product rules

### Documentation sync

- Product behavior/rule/user-flow change → update `PRD.md` and `PROJECT_STATUS.md`.
- Progress/parity/pivot change → update `PROJECT_STATUS.md`.
- Workflow/tooling/agent rule change → update `CLAUDE.md`.
- Stable cross-session decision → save memory when appropriate.
- If docs conflict, report conflict before coding.

### Prompt templates

Use these prompt templates by replacing bracketed fields.

#### Start or continue menu

```text
/goal lanjut [MENU] sampai sesuai ekspektasi gw.

Context:
- Current menu: [MENU]
- Goal now: [TARGET]
- Visual reference: contoh_UI/project_tracker_dbs_full_prototype_v2_AS_IS_PY_INJECTED.html
- Logic/rules source: PRD.md
- Progress source: PROJECT_STATUS.md
- Important user preference: [PREFERENCE]

Rules:
- Satu menu only.
- Use graphify first from D:/Ibrahim/Projects/project_tracker.
- Use claude-mem:smart-explore for code lookup.
- Update PROJECT_STATUS.md after each slice.
- Update PRD.md only if behavior/rule changes.
- Update CLAUDE.md only if workflow/tooling changes.
- Run relevant tests/build/app.
- Report changed files, tests, remaining gaps, next slice.
```

#### Fix error

```text
/goal fix error di [MENU].

Context:
- Current menu: [MENU]
- What I was doing: [ACTION_BEFORE_ERROR]
- Expected result: [EXPECTED]
- Actual result/error:
[PASTE_ERROR_OR_LOG]

Rules:
- Jangan tebak.
- Reproduce or locate failing path first.
- Use graphify first from D:/Ibrahim/Projects/project_tracker.
- Use claude-mem:smart-explore for failing files only.
- Find root cause, make smallest fix, verify.
- Do not weaken tests.
- Update PROJECT_STATUS.md if status/risk changes.
```

#### Pivot / change direction

```text
/goal pivot [MENU].

New direction:
[PERUBAHAN]

Context:
- Old direction: [OLD_DIRECTION]
- New expectation: [NEW_EXPECTATION]
- Keep: [WHAT_STAYS]
- Drop/change: [WHAT_CHANGES]

Rules:
- Stop old path first.
- Compare new direction vs PRD.md, PROJECT_STATUS.md, CLAUDE.md, current code.
- If product behavior/rule changes, update PRD.md + PROJECT_STATUS.md.
- If only visual/progress changes, update PROJECT_STATUS.md.
- If workflow/tooling changes, update CLAUDE.md.
- Keep change bounded to [MENU].
- Use graphify first, then smart-explore.
- Run tests/build/app.
```

#### Resume new session

```text
/goal resume Project Tracker vibe-code.

Context:
- I am working one menu at a time.
- Last/current menu should be read from PROJECT_STATUS.md.
- Graphify root: D:/Ibrahim/Projects/project_tracker.

Rules:
- Read PROJECT_STATUS.md first.
- Read CLAUDE.md workflow rules.
- Use graphify absolute path, not current worktree path.
- Recall memory for latest decisions.
- Check git/worktree status.
- Report active menu, last completed slice, dirty files, next safest task.
- Ask if I want to continue current menu or switch.
```

#### Wrap up session

```text
/goal wrap up current vibe-code session.

Context:
- Current menu: [MENU]
- Done this session: [DONE]
- Known gaps: [GAPS]

Rules:
- Update PROJECT_STATUS.md.
- Save stable memory if needed.
- Refresh graphify if available.
- Inspect/prune stale clean agent worktrees only after inspection.
- Do not stash/commit unless I say so.
- Report branch, dirty files, tests run, not tested, next prompt.
```

#### Final review before switching menu

```text
/goal final review [MENU] before pindah menu.

Rules:
- Compare against PRD behavior.
- Compare against AS-IS visual reference.
- Use graphify first.
- Run relevant tests/build/app.
- List DONE / NOT DONE / USER VISUAL CHECK NEEDED / RISK / NEXT MENU READY.
- Update PROJECT_STATUS.md.
```

#### Project hygiene cleanup

```text
/goal clean project hygiene. No feature work.

Rules:
- Inspect git status, worktrees, untracked files, graphify health.
- Remove only stale clean agent worktrees, temp folders, manual logs.
- Do not delete source files, graphify-out, contoh_UI, active branches, active worktrees.
- Do not change product behavior.
- Report removed items, kept risky items, remaining dirty files.
```
