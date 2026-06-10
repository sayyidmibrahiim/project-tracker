CLAUDE.md

This file provides operational guidance to Claude Code when working in this repository.

Graphify Knowledge Graph (token reduction)

This repo has a graphify knowledge graph at graphify-out/ (gitignored, rebuildable, AST-only — no API cost). Use it to reduce token usage. Does not override PRD.md.

- For codebase questions, run `graphify query "<question>"` instead of grepping/reading raw files. Use `graphify path "<A>" "<B>"` for relationships, `graphify explain "<concept>"` for focused concepts. Returns a scoped subgraph, usually much smaller than raw grep/read.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review when query/path/explain do not surface enough.
- Read raw files only to modify/debug specific code, or when the graph lacks detail.
- After modifying code, run `rtk graphify update .` to refresh the graph (AST-only, no API cost).
- Graph excludes .venv/ and node_modules/ via .gitignore. redesign_ui/ legacy PyQt6 is included as reference; treat it as legacy per Current Project Mode.

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

RTK

Always prefix shell commands with rtk, including each command in && chains.

RTK is a token-optimization wrapper, not a correctness tool. Still run normal verification.

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

Claude Code shells do not inherit the active venv. Use the full venv path.

Python tests:

rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/ -v
rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/ -q

Targeted Python test example:

rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/test_phase_b_stores.py -v

Frontend commands, once frontend/package.json exists:

rtk npm --prefix frontend install
rtk npm --prefix frontend run build

Run pywebview app only when the current phase supports it:

rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python main.py

Package for Windows transfer from repository root:

rtk zip -r project*tracker_dbs_v$(date +%Y%m%d).zip . --exclude ".venv/*" "**pycache**/_" "_.pyc" ".git/\_" "node_modules/\*"

Do not run PyInstaller on Linux. Windows packaging must be done on Windows.

Environment Boundaries

Component Linux dev Windows target
Core logic, filesystem, JSON Unit tests allowed Full app
SQLite cache/index Unit tests allowed Full app
Svelte/Vite frontend build Allowed Allowed
pywebview shell preview Allowed when guarded Full app
PyQt6 UI shell Reference only Deprecated
Outlook COM Stub/skip only Real integration
Teams/pyautogui Stub/skip only Real integration
send2trash, os.startfile Stub/skip only Real integration
PyInstaller Forbidden Allowed

Windows-only imports must be lazy and guarded with sys.platform == "win32".

Outlook, Teams, delete, and file-open services must instantiate without crashing on Linux.

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
-> project_tracker/services/
-> project_tracker/core/
-> project_tracker/infrastructure/

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
4. Update PROJECT_STATUS.md.
5. Report changed files.
6. Report commands run.
7. Report what was not tested.
8. Report remaining risks.

Testing Notes

Linux tests may verify:

- core domain rules
- state machine guards
- JSON serialization
- filesystem scanning logic
- SQLite cache/index rebuild logic
- bridge response formatting
- guarded imports

Windows manual verification is required for:

- Outlook COM
- Teams automation
- send2trash
- os.startfile
- WebView2 behavior
- visual rendering
- packaging
- installer behavior

No test may open blocking dialogs or require manual clicks.

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

<!-- rtk-instructions v2 -->

# RTK (Rust Token Killer) - Token-Optimized Commands

## Golden Rule

**Always prefix commands with `rtk`**. If RTK has a dedicated filter, it uses it. If not, it passes through unchanged. This means RTK is always safe to use.

**Important**: Even in command chains with `&&`, use `rtk`:

```bash
# ❌ Wrong
git add . && git commit -m "msg" && git push

# ✅ Correct
rtk git add . && rtk git commit -m "msg" && rtk git push
```

## RTK Commands by Workflow

### Build & Compile (80-90% savings)

```bash
rtk cargo build         # Cargo build output
rtk cargo check         # Cargo check output
rtk cargo clippy        # Clippy warnings grouped by file (80%)
rtk tsc                 # TypeScript errors grouped by file/code (83%)
rtk lint                # ESLint/Biome violations grouped (84%)
rtk prettier --check    # Files needing format only (70%)
rtk next build          # Next.js build with route metrics (87%)
```

### Test (60-99% savings)

```bash
rtk cargo test          # Cargo test failures only (90%)
rtk go test             # Go test failures only (90%)
rtk jest                # Jest failures only (99.5%)
rtk vitest              # Vitest failures only (99.5%)
rtk playwright test     # Playwright failures only (94%)
rtk pytest              # Python test failures only (90%)
rtk rake test           # Ruby test failures only (90%)
rtk rspec               # RSpec test failures only (60%)
rtk test <cmd>          # Generic test wrapper - failures only
```

### Git (59-80% savings)

```bash
rtk git status          # Compact status
rtk git log             # Compact log (works with all git flags)
rtk git diff            # Compact diff (80%)
rtk git show            # Compact show (80%)
rtk git add             # Ultra-compact confirmations (59%)
rtk git commit          # Ultra-compact confirmations (59%)
rtk git push            # Ultra-compact confirmations
rtk git pull            # Ultra-compact confirmations
rtk git branch          # Compact branch list
rtk git fetch           # Compact fetch
rtk git stash           # Compact stash
rtk git worktree        # Compact worktree
```

Note: Git passthrough works for ALL subcommands, even those not explicitly listed.

### GitHub (26-87% savings)

```bash
rtk gh pr view <num>    # Compact PR view (87%)
rtk gh pr checks        # Compact PR checks (79%)
rtk gh run list         # Compact workflow runs (82%)
rtk gh issue list       # Compact issue list (80%)
rtk gh api              # Compact API responses (26%)
```

### JavaScript/TypeScript Tooling (70-90% savings)

```bash
rtk pnpm list           # Compact dependency tree (70%)
rtk pnpm outdated       # Compact outdated packages (80%)
rtk pnpm install        # Compact install output (90%)
rtk npm run <script>    # Compact npm script output
rtk npx <cmd>           # Compact npx command output
rtk prisma              # Prisma without ASCII art (88%)
```

### Files & Search (60-75% savings)

```bash
rtk ls <path>           # Tree format, compact (65%)
rtk read <file>         # Code reading with filtering (60%)
rtk grep <pattern>      # Search grouped by file (75%). Format flags (-c, -l, -L, -o, -Z) run raw.
rtk find <pattern>      # Find grouped by directory (70%)
```

### Analysis & Debug (70-90% savings)

```bash
rtk err <cmd>           # Filter errors only from any command
rtk log <file>          # Deduplicated logs with counts
rtk json <file>         # JSON structure without values
rtk deps                # Dependency overview
rtk env                 # Environment variables compact
rtk summary <cmd>       # Smart summary of command output
rtk diff                # Ultra-compact diffs
```

### Infrastructure (85% savings)

```bash
rtk docker ps           # Compact container list
rtk docker images       # Compact image list
rtk docker logs <c>     # Deduplicated logs
rtk kubectl get         # Compact resource list
rtk kubectl logs        # Deduplicated pod logs
```

### Network (65-70% savings)

```bash
rtk curl <url>          # Compact HTTP responses (70%)
rtk wget <url>          # Compact download output (65%)
```

### Meta Commands

```bash
rtk gain                # View token savings statistics
rtk gain --history      # View command history with savings
rtk discover            # Analyze Claude Code sessions for missed RTK usage
rtk proxy <cmd>         # Run command without filtering (for debugging)
rtk init                # Add RTK instructions to CLAUDE.md
rtk init --global       # Add RTK to ~/.claude/CLAUDE.md
```

## Token Savings Overview

| Category         | Commands                       | Typical Savings |
| ---------------- | ------------------------------ | --------------- |
| Tests            | vitest, playwright, cargo test | 90-99%          |
| Build            | next, tsc, lint, prettier      | 70-87%          |
| Git              | status, log, diff, add, commit | 59-80%          |
| GitHub           | gh pr, gh run, gh issue        | 26-87%          |
| Package Managers | pnpm, npm, npx                 | 70-90%          |
| Files            | ls, read, grep, find           | 60-75%          |
| Infrastructure   | docker, kubectl                | 85%             |
| Network          | curl, wget                     | 65-70%          |

Overall average: **60-90% token reduction** on common development operations.

<!-- /rtk-instructions -->
