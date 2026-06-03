CLAUDE.md

This file provides operational guidance to Claude Code when working in this repository.

Product Source of Truth

PRD.md v3.1 is the product and architecture source of truth.

If this file conflicts with PRD.md, report the conflict before coding. Do not silently follow outdated instructions.

PROJECT_STATUS.md tracks implementation progress, verification status, completed phases, blocked items, and next tasks. Update it after each completed phase or meaningful implementation slice.

Current Locked Stack

Backend:

- Python 3.12+
- Modular monolith architecture
- pywebview desktop shell
- APScheduler for local background/scheduled jobs
- SQLite as local rebuildable cache/index only
- Local filesystem + JSON metadata as canonical project source of truth

Frontend:

- Svelte
- TypeScript
- Vite
- Tailwind CSS bundled locally through the frontend build
- Production frontend output must be served by pywebview local HTTP server / serve-folder mode
- Do not use raw file:// loading for production frontend

Windows integrations:

- Outlook COM through pythoncom / win32com
- Teams automation through guarded Windows-only service code
- pyautogui for Teams desktop automation where required
- send2trash for Recycle Bin delete
- os.startfile for Windows file opening

Future migration candidate only:

- Tauri v2 + Svelte + Python sidecar may be considered after MVP stability.
- Do not migrate to Tauri unless explicitly requested by the user.

Commands

Always prefix Claude Code shell commands with rtk, including each command in && chains.

Claude Code shells do not inherit the active venv. Use the full venv path.

Python tests:

rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/ -v
rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/ -q

Frontend commands, once frontend/package.json exists:

rtk npm --prefix frontend install
rtk npm --prefix frontend run build

Run the pywebview app only after the current phase supports it:

rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python main.py

Package for Windows transfer from repository root:

rtk zip -r project_tracker_dbs_v$(date +%Y%m%d).zip . --exclude ".venv/_" "**pycache**/_" "_.pyc" ".git/_" "node_modules/\*"

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
2. Identify files to touch.
3. State the verification criteria.
4. Keep changes surgical.
5. Do not refactor unrelated code.
6. Do not delete legacy/reference files unless explicitly approved.

After coding a phase:

1. Run relevant tests.
2. Run frontend build when applicable.
3. Update PROJECT_STATUS.md.
4. Report changed files.
5. Report commands run.
6. Report what was not tested.
7. Report remaining risks.

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
