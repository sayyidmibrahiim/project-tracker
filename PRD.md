# Project Tracker DBS — Product Requirements Document v3.1

> **Version:** 3.1.0  
> **Date:** 2026-06-02  
> **Author:** Sayyid M. Ibrahim  
> **Status:** Single Source of Truth — Supersedes PRD v2.0.0  
> **Primary Runtime Target:** Windows 10/11 Desktop  
> **Stack:** Python 3.12 + pywebview + Svelte + TypeScript + Vite + Tailwind CSS + APScheduler + SQLite (cache)  
> **Prototype Sources (UX Reference Only):** `project_tracker_clean.py`, `project_details_redesign.py`, `report_redesign.py`, `second_brain_redesign.py`, `automations_redesign.py`, `settings_redesign.py`, `UI_FEATURE_DOCUMENTATION.md`

---

<!-- TOC: use offset/limit to read sections, don't full-load -->
<!-- §1 Purpose ~L23  §2 Constraints ~L41  §3 Stack ~L78  §4 Arch ~L143 -->
<!-- §5 DevEnv ~L201  §6 Design ~L214  §7 FS Model ~L305  §8 Data ~L404 -->
<!-- §9 State ~L606  §10 Shell ~L777  §11 Dashboard ~L830  §12 ProjDet ~L998 -->
<!-- §13 SecBrain ~L1179  §14 LinkBank ~L1319  §15 Report ~L1426 -->
<!-- §16 Automations ~L1497  §17 Settings ~L1836  §18 Notifs ~L1913 -->
<!-- §19 Bridge ~L1956  §20 WinInteg ~L2029  §21 JsApi ~L2118 -->
<!-- §22 SQLite ~L2278  §23 FileOps ~L2386  §24 Packaging ~L2436 -->
<!-- §25 Phases ~L2479  §26 Acceptance ~L2622  §28 Calibration ~L2696 -->
<!-- §29 Handoff ~L2710 -->
<!-- §"About" + §27 ADRs archived → _docs/_archive/PRD_history.md -->

---

## 1. Purpose & Product Vision

Project Tracker DBS is a single-user Windows desktop application for managing DBS Change Request (CR) deployment work from UAT preparation through production implementation.

Built for a deployment/support engineer who tracks multiple CR projects, coordinates Outlook and Teams communication, manages deployment evidence, and writes operational notes — all in one local tool.

**Core goals:**

1. Make project state visible and actionable from a single dashboard.
1. Enforce deployment workflow discipline (T-10, state guards, folder transitions).
1. Keep all data local-first, filesystem-based, and recoverable.
1. Automate repetitive Outlook and Teams tasks safely (draft-first by default).
1. Provide a personal knowledge base (Second Brain) and link library (Link Bank).
1. Generate operational reports and export CSV.
1. Work reliably on Windows 10/11 without any cloud or server dependency.

---

## 2. Non-Negotiable Constraints

### 2.1 Data & Storage

- All project data stays local.
- Local filesystem is the canonical source of truth for project existence, year, and folder state.
- `project_data.json` stores metadata only. **`project_state` must never appear in this file.**
- SQLite is a **rebuildable local cache only** — not source of truth. If corrupt or deleted, app rebuilds from filesystem scan.
- `settings.json` stores all app and automation configuration.
- `link_bank.json` stores Link Bank data.
- `notes.md` is primary notes storage per project/subproject.
- Atomic writes: all JSON writes use temp-file-then-replace.
- Hard delete is **forbidden**. Delete uses Windows Recycle Bin via `send2trash`.

### 2.2 Platform

- Windows 10/11 is the production runtime target.

### 2.3 Features

- No cloud sync.
- No external server or web backend.
- No multi-user collaboration.
- No embedded browser (all web links open in default OS browser).
- No hard delete.
- No auto-send Teams messages by default (`teams_auto_send = false`).
- No new dependencies without user confirmation.

### 2.4 Architecture

- `core/` must be pure Python, no platform imports, no UI imports.
- Dependencies flow one direction: `core/ → infrastructure/ → services/ → web/js_api.py → frontend/`.
- All paths use `pathlib.Path`. No manual string path concatenation.
- Windows-specific code wrapped in `IS_WINDOWS = sys.platform == "win32"` guards.

---

## 3. Locked Technology Stack

| Layer                       | Technology                                | Notes                                                  |
| --------------------------- | ----------------------------------------- | ------------------------------------------------------ |
| Desktop Shell               | **pywebview** (serve_folder mode)         | WebView2 on Windows; webkit2gtk on Linux (dev only)    |
| Frontend Framework          | **Svelte + TypeScript**                   | No SvelteKit; plain Svelte with Vite                   |
| Build Tool                  | **Vite**                                  | Output: `web/static/`                                  |
| Styling                     | **Tailwind CSS**                          | Bundled locally; CDN only for dev/prototype fallback   |
| State Management (Frontend) | **Svelte Stores**                         | No XState; state machine logic lives in Python backend |
| Backend / Domain            | **Python 3.12+**                          | Core authority for all business logic                  |
| Persistence (Canonical)     | **Filesystem + JSON**                     | project_data.json, settings.json, link_bank.json       |
| Persistence (Cache/Index)   | **SQLite**                                | Rebuildable from filesystem scan; not source of truth  |
| Background Tasks            | **APScheduler 3.x**                       | Auto IN-PROGRESS, polling jobs, scheduler alarms       |
| Windows Integrations        | pywin32, pythoncom, pyautogui, send2trash | All Windows-guarded                                    |
| Packaging                   | **PyInstaller**                           | Must include Vite build output (`web/static/`)         |
| Future Migration Path       | Tauri v2 + Svelte + Python sidecar        | ADR documented; not MVP                                |

### 3.1 serve_folder Mode

```python
# app_web.py — production mode
webview.start(serve_folder="web/static")

# app_web.py — development mode (Vite dev server)
webview.start(url="http://localhost:5173")  # pass --dev flag
```

### 3.2 Frontend Build Pipeline

```bash
# Development (Linux or Windows)
cd frontend && npm run dev        # Vite dev server on :5173
python app_web.py --dev           # pywebview → localhost:5173

# Production build
cd frontend && npm run build      # outputs to ../web/static/
python app_web.py                 # pywebview → web/static/
```

### 3.3 Dependency Baseline

```text
# Core (locked)
pywebview>=5.0
pywin32>=306
pythoncom (part of pywin32)
pyautogui>=0.9.54
pyperclip>=1.8.2
send2trash>=1.8.3
apscheduler>=3.10.0

# Build
pyinstaller>=6.0.0
vite>=5.0 (npm)
svelte>=5.0 (npm)
typescript>=5.0 (npm)
tailwindcss>=3.4 (npm)

# Optional — requires confirmation before adding
watchdog>=4.0.0
marked.js (npm, for markdown preview)
```

---

## 4. Architecture & Package Structure

```text
project_tracker_dbs/
├── app_web.py                    # Entry point: pywebview init, JsApi wiring
├── core/
│   ├── enums.py                  # CRState, DroneState, FolderState, EventType
│   ├── models.py                 # Dataclasses: Project, SubProject, DroneTicket, HistoryEntry, etc.
│   ├── state_machine.py          # All transition logic + guards (pure Python, no I/O)
│   ├── rules.py                  # T-10 rule, guard checks, validation helpers
│   └── exceptions.py             # Domain exceptions
├── infrastructure/
│   ├── filesystem.py             # pathlib folder ops, scan, rename, create, delete via send2trash
│   ├── metadata_store.py         # project_data.json atomic R/W per project
│   ├── settings_store.py         # settings.json via %APPDATA%/~/ProjectTrackerDBS
│   ├── link_bank_store.py        # link_bank.json R/W
│   ├── cache_db.py               # SQLite: project index, notifications, scheduler, rule logs
│   ├── outlook_client.py         # win32com Outlook wrapper (IS_WINDOWS guarded)
│   └── teams_client.py           # pyautogui Teams deep-link wrapper (IS_WINDOWS guarded)
├── services/
│   ├── project_service.py        # CRUD + state orchestration for projects
│   ├── scanner_service.py        # Filesystem scan → SQLite cache rebuild
│   ├── watchdog_service.py       # Optional: watchdog observer + debounce + event queue push
│   ├── automation_service.py     # Rules Engine: trigger evaluation + action dispatch
│   ├── scheduler_service.py      # APScheduler job management + Scheduler tab entries
│   ├── second_brain_service.py   # Notes search index, file ops, pin/favorite
│   └── report_service.py         # Filter logic + CSV export
├── web/
│   ├── js_api.py                 # JsApi class (all pywebview bridge methods)
│   └── event_queue.py            # thread-safe queue.Queue for background → frontend events
├── frontend/                     # Svelte source (dev only, not included in Python package)
│   ├── src/
│   │   ├── lib/
│   │   │   ├── api/              # Typed wrappers around window.pywebview.api.*
│   │   │   ├── stores/           # Svelte writable/derived stores
│   │   │   ├── components/       # Reusable UI components (Sidebar, Header, Table, Card, etc.)
│   │   │   └── types/            # TypeScript interfaces mirroring Python models
│   │   ├── routes/               # Page-level Svelte components
│   │   └── app.html              # pywebview HTML shell
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts            # outDir: '../web/static'
└── assets/
    ├── icon.ico
    └── email_templates/          # .html / .txt files for Outlook category templates
```

### 4.1 Layer Rules

- `core/` imports nothing from `infrastructure/`, `services/`, `web/`, or `frontend/`.
- `infrastructure/` imports from `core/` only.
- `services/` imports from `core/` and `infrastructure/`.
- `web/js_api.py` imports from `services/` only (never direct infrastructure calls).
- `frontend/` calls Python through `window.pywebview.api.*` only.
- Unit tests on Linux cover `core/`, `infrastructure/` logic, and `services/` without Windows APIs.

---

## 5. Development Environment & Workflow

### 5.1 Windows

```bash
# Full app test
cd frontend && npm run build
python app_web.py

# Windows integration test (Outlook, Teams, file ops)
python -m pytest tests/windows/ -v  # manual verification
```

## 6. Design System & UI Theme

### 6.1 Theme Philosophy

**Utilitarian + Modern Minimalist**

- **Utilitarian**: every element must serve a function; information density is valued; layout is task-oriented.
- **Modern Minimalist**: clean whitespace, subtle depth, consistent spacing, smooth micro-interactions (150–220ms), no decoration without purpose.
- No gradients. No neon. No playful accents.
- High contrast text (WCAG AA minimum).
- The enterprise banking palette from the PyQt6 prototypes is preserved exactly.

### 6.2 Color Palette (Preserved from Prototypes)

```css
/* Primary */
--color-primary: #b91c1c; /* enterprise red — buttons, active accents */
--color-primary-hover: #991b1b; /* red hover state */
--color-active-red: #dc2626; /* active indicators, left-border accents */
--color-error-red: #991b1b; /* error and danger states */

/* Surface */
--color-sidebar-bg: #0a0a0b; /* black chrome sidebar */
--color-surface-dark: #141416; /* dark surface elements */
--color-border-dark: #2c2c30; /* dark border */
--color-nav-active-bg: #231112; /* active nav item bg */
--color-nav-inactive: #b9b9c0; /* inactive nav text/icon */

/* Body Layers (light hierarchy) */
--color-body: #ffffff; /* main content background */
--color-panel: #e6e8eb; /* panel/card backgrounds */
--color-inner-card: #ffffff; /* inner card/content boxes */
--color-outer-layer: #eef0f2; /* outer layer */

/* Text */
--color-text-primary: #171717;
--color-text-strong: #111111;
--color-text-secondary: #6b7280;
--color-text-muted: #a1a1aa;
--color-placeholder: #71717a;

/* Inputs */
--color-input-border: #d7d7dc;
--color-input-bg: #ffffff;

/* Accent (selected states, hover bg) */
--color-accent-pink: #fff1f4;
--color-accent-border: #ffd4df;
--color-accent-strong: #f4a7b9;
```

### 6.3 Typography

- Primary font: `Inter` (load via local asset or Google Fonts during dev).
- Fallback: `Segoe UI`, `sans-serif`.
- Font scale uses Tailwind size classes (`text-xs` through `text-base`).
- Font weight: 700–900 for labels/headings; 600–700 for body content.

### 6.4 Spacing System

- Base unit: 4px (Tailwind default).
- Standard component padding: `p-3` (12px) for inner cards, `p-4` (16px) for panels.
- Tight spacing: `gap-1.5` or `gap-2` between related controls.
- Section spacing: `gap-3` or `gap-4` between cards.

### 6.5 Component Standards

```
Cards:        white bg, 1px border (#E5E7EB), 3px left-border (#B91C1C), rounded-lg, subtle shadow
Panels:       #E6E8EB bg, 1px soft border, rounded-xl
Buttons (primary): #B91C1C bg, white text, rounded-md, hover → #991B1B
Buttons (secondary): white bg, #B91C1C text, 1px #FFD4DF border, hover → #FFF1F4
Tables:       white bg, dark header (#111111), white text, 1px grid lines
Sidebar:      #0A0A0B bg, collapsed/expanded, active item has left-border + #231112 bg
Header:       #B91C1C bg, white title, white datetime badge border, refresh button white bg
Splitters:    visible handle, pink on hover
Scrollbars:   thin (4px), pink accent handle
```

### 6.6 Responsive Behavior

- Avoid fixed major container sizes; use flex/grid with `min-*` readability constraints.
- Use `clamp()` for font sizes where needed.
- Major panels use resizable splitters (CSS resize or library).
- All list/table panels scroll internally; no page-level overflow.
- **Sidebar:** `Sidebar.svelte` implements the **bottom dock** (see §10.3). The name is legacy. There is no persistent left sidebar.
- Header controls use `min-w` to prevent clipping on small screens.
- Empty-area click must clear selection in tables/trees/lists.

---

## 7. Filesystem Model (Source of Truth)

### 7.1 Root Folder

User selects one root folder. All project data lives here.

```
D:\\WORK\\
```

### 7.2 Appcode Folders

Each appcode is a subfolder under the root, containing an `appcode.json` config file.

```
{ROOT}\\{APPCODE}\\
  appcode.json
  CICD\\
  {YEAR}\\
```

- Appcodes are discovered by scanning `{ROOT}/*` for folders containing `appcode.json`.
- User can add multiple appcodes.
- `appcode.json` holds per-appcode config: display name, CICD location preference.
- `CICD/` is created empty (Bitbucket clone helper in Piece D).
- Removing an appcode sends the folder to Recycle Bin.

### 7.3 Year Folders

```
{ROOT}\\{APPCODE}\\{YEAR}\\
```

- Year is derived solely from the year folder name.
- Dashboard year dropdown shows only existing year folders for the selected appcode.
- Creating a year creates `{YEAR}/CR/` + 5 state folders inside CR + `{YEAR}/Non-CR/`.
- Default Add Year suggestion: next calendar year.
- Adding a year >2 years ahead shows a confirmation warning.

### 7.4 CR Project State Folders (5 States, inside CR/)

```
{ROOT}\\{APPCODE}\\{YEAR}\\CR\\UAT_PREPARE\\
{ROOT}\\{APPCODE}\\{YEAR}\\CR\\PROD_READY\\
{ROOT}\\{APPCODE}\\{YEAR}\\CR\\IMPLEMENTED\\
{ROOT}\\{APPCODE}\\{YEAR}\\CR\\POSTPONED\\
{ROOT}\\{APPCODE}\\{YEAR}\\CR\\CANCELED\\
```

State folders exist **only inside `CR/`**. Non-CR projects have no state folders.

### 7.5 CR Project Folder

```
{ROOT}\\{APPCODE}\\{YEAR}\\CR\\{STATE}\\{PROJECT_NAME}\\
```

One folder = one CR scope. `project_type = CR` in `project_data.json`.

Required: `project_data.json`, `notes.md`, `_cr-docs/` (empty in Piece A; Piece B fills with uat-signoff, prod-lv, .msg files).

### 7.6 Drone Folder (was "Sub Project")

```
{ROOT}\\{APPCODE}\\{YEAR}\\CR\\{STATE}\\{PROJECT_NAME}\\{DRONE_NAME}\\
  UAT\\
  PRD\\
  notes.md
```

- Shares the same CR number as parent project.
- **Must** contain `UAT/` and `PRD/` subfolders + own `notes.md`.
- No independent CR state or folder state.
- "Sub project" terminology retired; the term is now "drone" throughout.

### 7.7 Non-CR Project Folder

```
{ROOT}\\{APPCODE}\\{YEAR}\\Non-CR\\{PROJECT_NAME}\\
```

`project_type = NON_CR`. No state folders; state in `project_data.json` (`non_cr_state`).
Non-CR state machine: PLANNING -> IN_PROGRESS -> DONE (with DONE -> IN_PROGRESS reopen).
No CR Number, no Drone Tickets, no `_cr-docs/`.

### 7.8 Organizational Folder Exclusion

Excluded from drone detection: `doc, docs, document, documents, bak, backup, before, after, script, scripts, cicd, log, logs, temp, tmp, archive` + `_cr-docs`.

### 7.9 CICD Folder

`{ROOT}/{APPCODE}/CICD/` (per-appcode, default) or `{ROOT}/CICD/` (shared root, optional).
Configurable via `appcode.json`. Piece A creates empty; Piece D adds clone helper.

### 7.10 Folder Name Validation


## 8. Data Models

### 8.1 `project_data.json` Schema

```json
{
  "$schema": "project_data_v1",
  "project_name": "PAYMENT_MODULE_UPGRADE",
  "start_datetime": "2026-01-15T20:40:00+07:00",
  "end_datetime": "2026-01-16T02:00:00+07:00",
  "cr_link": "https://itsm.example.local/orderDetails?CRNumber=CR202604209900114",
  "cr_state": "APPROVED",
  "cr_state_updated_at": "2026-01-05T09:00:00+07:00",
  "cr_pending_approval_at": "2026-01-05T09:00:00+07:00",
  "drone_tickets": [
    {
      "subfolder_name": null,
      "drone_link": "https://drone.example.local/deployment/D-SSIDBI-159",
      "drone_state": "APPROVED",
      "drone_state_updated_at": "2026-01-05T10:00:00+07:00",
      "owner": "Alice",
      "previous_drone_state_before_canceled": null
    },
    {
      "subfolder_name": "script_change",
      "drone_link": "https://drone.example.local/deployment/D-SSIDBI-160",
      "drone_state": "PENDING APPROVAL",
      "drone_state_updated_at": "2026-01-05T11:00:00+07:00",
      "owner": "Bob"
    }
  ],
  "implementation_plan": "Step 1: Deploy DB scripts\nStep 2: Deploy API",
  "email_flags": {
    "ack_sent": false,
    "approval_sent": false,
    "last_cr_link_when_sent": null
  },
  "history": [
    {
      "timestamp": "2026-01-10T14:30:00+07:00",
      "action": "STATE_CHANGE",
      "detail": "CR: PENDING APPROVAL → APPROVED",
      "user": "Sayyid"
    }
  ],
  "created_at": "2026-01-05T09:00:00+07:00",
  "updated_at": "2026-01-15T20:40:00+07:00"
}
```

**Rules:**

- `project_state` must never appear in this file.
- `subfolder_name: null` = ticket belongs to the main project.
- `owner` is fetched from Outlook contacts (Windows) or free text (fallback).
- `cr_pending_approval_at` records the first time CR reaches `PENDING APPROVAL`; never overwrite.
- `notes.md` is primary notes storage; `notes` JSON field is legacy/not used.
- Corrupt JSON: skip project and warn, never crash.
- Missing known fields: use defaults silently.
- Unknown fields: ignore without error.

### 8.2 Default `project_data.json`

```json
{
  "$schema": "project_data_v1",
  "project_name": "",
  "start_datetime": null,
  "end_datetime": null,
  "cr_link": "",
  "cr_state": "PENDING SUBMISSION",
  "cr_state_updated_at": null,
  "cr_pending_approval_at": null,
  "drone_tickets": [],
  "implementation_plan": "",
  "email_flags": {
    "ack_sent": false,
    "approval_sent": false,
    "last_cr_link_when_sent": null
  },
  "history": [],
  "created_at": null,
  "updated_at": null
}
```

### 8.3 History Entry

```json
{
  "timestamp": "2026-01-10T14:30:00+07:00",
  "action": "STATE_CHANGE",
  "detail": "CR: PENDING APPROVAL → APPROVED",
  "user": "display_name from settings or Windows login"
}
```

- History is append-only and read-only in UI.
- Newest entries displayed first.
- `user` = `settings.display_name` if set; else `os.getenv("USERNAME")` on Windows.
- Never hardcode username.

### 8.4 Datetime Policy

- Store all datetimes as ISO 8601 timezone-aware strings.
- Use local OS timezone dynamically (`datetime.now(tz=timezone.utc).astimezone()`).
- Do not hardcode WIB, UTC+7, or any fixed offset.
- Display format comes from `settings.datetime_format`.

### 8.5 `settings.json`

Stored at `%APPDATA%\ProjectTrackerDBS\settings.json` (Windows) or `~/ProjectTrackerDBS/settings.json` (Linux dev).

```json
{
  "root_folder": "D:\\WORK\\CR",
  "display_name": "",
  "language": "en",
  "datetime_format": "ddd, dd MMM yyyy HH:mm:ss",
  "startup_behavior": "current_year_dashboard",
  "auto_refresh_interval_seconds": 0,
  "t10_threshold_days": 10,
  "second_brain_folder": "%APPDATA%\\ProjectTrackerDBS\\SecondBrain",
  "file_template_folder": "",
  "ui": {
    "sidebar_collapsed": false,
    "last_active_page": "dashboard",
    "last_selected_year": null
  },
  "automation": {
    "outlook": {
      "global_mode": "draft",
      "template_folder_path": "",
      "categories": {
        "ACK_UAT": {
          "to": "",
          "cc": "",
          "subject_template": "[ACK_UAT] {PROJECT_NAME} - {CR_NUMBER}",
          "body_template": "",
          "use_html_file": false,
          "html_file_path": "",
          "attachment_path": "",
          "mode_override": null,
          "conditions": []
        },
        "ACK_SOP": { "...": "..." },
        "APRVL_CR": { "...": "..." },
        "APRVL_SOP": { "...": "..." }
      }
    },
    "teams": {
      "countdown_seconds": 3,
      "teams_auto_send": false,
      "automations": []
    },
    "scheduler": {
      "entries": []
    },
    "rules_engine": {
      "rules": []
    }
  }
}
```

### 8.6 `link_bank.json`

```json
{
  "version": 1,
  "categories": [
    {
      "id": "cat-1",
      "name": "CR & ITSM Tools",
      "archived": false,
      "created_at": "2026-01-01T09:00:00+07:00",
      "updated_at": "2026-01-01T09:00:00+07:00"
    }
  ],
  "links": [
    {
      "id": "link-1",
      "category_id": "cat-1",
      "title": "CR Portal",
      "url": "https://example.local/",
      "tags": ["Portal", "PROD", "Working"],
      "details": "Daily CR work portal.",
      "pinned": false,
      "favorite": false,
      "archived": false,
      "last_opened_at": null,
      "created_at": "2026-01-01T09:00:00+07:00",
      "updated_at": "2026-01-01T09:00:00+07:00"
    }
  ]
}
```

Tags are user-defined free-form strings (hashtags). No fixed list. Stored inline in each link’s `tags` array.

---

## 9. State Machines

### 9.1 CR State Values

| State                | Selectable by User | Notes                                                                      |
| -------------------- | ------------------ | -------------------------------------------------------------------------- |
| `PENDING SUBMISSION` | ✅                 | Default on project creation                                                |
| `PENDING APPROVAL`   | ✅                 | User sets after submitting CR to approver                                  |
| `APPROVED`           | ✅                 | User sets after CR approved in web portal                                  |
| `IN-PROGRESS`        | ❌ Auto only       | Scheduler sets when `now` is within `[start_dt, end_dt]` AND CR=`APPROVED` |
| `FINISHED`           | ✅                 | User sets after deployment work is complete; only from `IN-PROGRESS`       |
| `POSTPONED`          | ✅                 | Moves project folder to `POSTPONED/`                                       |
| `CANCELED`           | ✅                 | Moves project folder to `CANCELED/`                                        |

`REOPEN` is an **action/event**, not a persistent state. It is available when the project folder is in `POSTPONED` or `CANCELED` state.

### 9.2 CR State Transition Diagram

```
PENDING SUBMISSION
    │
    ▼ [user: CR submitted to approver]
PENDING APPROVAL  ────────────────────────────────────────────┐
    │                                                          │
    ▼ [user: CR approved in web portal]                        │
APPROVED                                                       │
    │                                                          │
    ▼ [auto: now enters [start_dt, end_dt] window]             │
IN-PROGRESS  ──────────────────────────────────────────────── │ ← REOPEN available
    │                                                          │   (from POSTPONED/CANCELED folder)
    ▼ [user: deployment complete]                              │   → moves folder to UAT_PREPARE
FINISHED                                                       │   → CR state → PENDING SUBMISSION
                                                               │
From any active state ─────────────────────────────────────── │
    POSTPONED folder (user: project paused) ◄──────────────── │
    CANCELED folder  (user: project closed) ◄──────────────── │
```

### 9.3 Drone State Values

| State              | Selectable by User | Notes                                                                      |
| ------------------ | ------------------ | -------------------------------------------------------------------------- |
| `UAT`              | ✅                 | Default on drone ticket creation                                           |
| `PENDING APPROVAL` | ✅                 | User sets after submitting Drone for approval                              |
| `APPROVED`         | ✅                 | User sets after Drone approved                                             |
| `IN-PROGRESS`      | ❌ Auto only       | Scheduler sets when `now` enters `[start_dt, end_dt]` AND Drone=`APPROVED` |
| `FINISHED`         | ✅                 | User sets after deployment; only from `IN-PROGRESS`                        |
| `POSTPONED`        | ❌ Auto only       | Mirrors CR/project postponement                                            |
| `CANCELED`         | ✅                 | Ticket canceled                                                            |

**Rules:**

- Drone cannot change state if `drone_link` is empty.
- `UAT` is default on creation.
- `FINISHED` only from `IN-PROGRESS`.
- User cannot set Drone state to `CANCELED` unless CR state is already `CANCELED`.
- When CR state becomes `POSTPONED` or `CANCELED`, all Drone tickets become `POSTPONED`/`CANCELED` and each ticket stores its prior state in `previous_drone_state_before_canceled`.
- When a `POSTPONED` or `CANCELED` project is reopened, CR returns to `PENDING SUBMISSION` and Drone tickets restore their stored pre-pause states.
- When a Drone link changes, that Drone ticket state resets to `UAT`.
- Every state change updates `drone_state_updated_at`.

### 9.4 Project Folder State Transitions

#### `UAT_PREPARE → PROD_READY` (Auto)

Triggered automatically by the scheduler when:

- `cr_state = APPROVED`
- All drone tickets `drone_state = APPROVED` (or no drone tickets exist)
- T-10 guard passes

If T-10 fails but other conditions pass:

- Auto move is **blocked**.
- Notification: `"T-10 violation: CR {number} missed threshold. Manual review required."`
- User can manually override via confirmation dialog.

Guards also checked at manual transition:

- `start_datetime` exists and is not backdated.
- `end_datetime` exists and `end_datetime > start_datetime`.
- `cr_link` exists.

#### `PROD_READY → IMPLEMENTED` (Auto)

Triggered automatically when:

- `cr_state = FINISHED`
- All drone tickets `drone_state = FINISHED`
- Project is currently in `PROD_READY`

#### `Any → POSTPONED` (Manual)

Available from: `UAT_PREPARE`, `PROD_READY` (with confirmation), `CANCELED`.  
**Not available** from: `IMPLEMENTED`.

CR state is set to `POSTPONED`. Folder physically moves to `POSTPONED/`.

#### `Any → CANCELED` (Manual)

Available from: `UAT_PREPARE`, `PROD_READY` (with confirmation), `POSTPONED`.  
**Not available** from: `IMPLEMENTED`.

Requires confirmation. CR state is set to `CANCELED`. Folder moves to `CANCELED/`.

#### `POSTPONED or CANCELED → UAT_PREPARE` (REOPEN — Manual)

User triggers REOPEN:

1. History entry records: `"REOPEN: project moved from {old_folder_state} to UAT_PREPARE"`.
1. Folder physically moves to `UAT_PREPARE/`.
1. CR state → `PENDING SUBMISSION`.
1. `cr_state_updated_at` updated.

### 9.5 Folder State Locking Rules

|                       | UAT_PREPARE | PROD_READY                    | IMPLEMENTED | POSTPONED     | CANCELED |
| --------------------- | ----------- | ----------------------------- | ----------- | ------------- | -------- |
| Edit metadata         | ✅          | Partial                       | ❌          | ✅            | ✅       |
| Edit files            | ✅          | Partial                       | ❌          | ✅            | ✅       |
| Add/edit notes        | ✅          | ✅                            | View only   | ✅            | ✅       |
| Rename project        | ✅          | ❌                            | ❌          | ✅            | ✅       |
| Delete project        | ✅          | ❌                            | ❌          | ✅            | ✅       |
| Change CR/Drone state | ✅          | Limited                       | ❌          | ❌            | ❌       |
| Move folder state     | ✅          | To IMPLEMENTED/POSTPONED only | ❌          | Resume/Cancel | Reopen   |

**PROD_READY Partial Lock:** editing metadata, renaming, destructive file ops, and delete are all disabled. Viewing, notes/evidence editing, CR/Drone progression needed for deployment, and moving to IMPLEMENTED or POSTPONED are allowed.

### 9.6 T-10 Rule

```python
# Guard: CR must have reached PENDING APPROVAL at least t10_threshold_days before start_datetime
cr_pending_approval_at <= start_datetime - timedelta(days=t10_threshold_days)
```

Default threshold: 10 days (configurable in Settings).

- Uses `cr_pending_approval_at`, not `cr_state_updated_at`.
- If `cr_pending_approval_at` is missing and CR is beyond `PENDING SUBMISSION`: warn that T-10 cannot be proven.
- Dashboard highlights row in warning color when today passes the T-10 deadline and CR has not yet reached `PENDING APPROVAL`.
- `UAT_PREPARE → PROD_READY` is blocked if T-10 fails (manual override with confirmation allowed).

### 9.7 Auto IN-PROGRESS (APScheduler)

APScheduler checks active projects every 60 seconds.

Condition: `start_datetime ≤ now ≤ end_datetime`

Action:

- CR with state `APPROVED` → set to `IN-PROGRESS`
- All Drone tickets with state `APPROVED` → set to `IN-PROGRESS`
- Write metadata atomically.
- Append history entries.
- Push notification to frontend event queue.

### 9.8 CR/Drone Link Parsing

- User pastes full URL into CR or Drone field.
- Store full URL unchanged in `cr_link` / `drone_link`.
- Extract friendly identifier for display:
  - CR: `CRNumber=CR202604209900114` → display `CR202604209900114 ↗`
  - Drone: `/D-SSIDBI-159` → display `D-SSIDBI-159 ↗`
- If extraction fails: display shortened safe URL text.
- When pasted into empty field: validate URL-like, store, display extracted.
- When CR link pasted: auto-set state to `PENDING SUBMISSION` if state was empty.
- Click always opens full URL in default OS browser.
- History entry on save, not on each keystroke.

---

## 10. Global Shell & Navigation

### 10.1 Navigation Pages

```
1. Dashboard
2. Project Details
3. Second Brain  (contains: Notes, Link Bank)
4. Report
5. Automations   (contains: Outlook, Teams, Scheduler, Rules Engine)
6. Settings
```

Notifications are **not** a separate page — they are opened from the bottom dock notification button/popover and remain reachable on all pages.

### 10.2 App Shell Layout

> Updated 2026-07-04 (D-0011). Supersedes the red header and (per D-0005) the bottom dock.

```
┌─────────────────────────────────────────────────────────┐
│ TITLEBAR (dark chrome): avatar · search · nav icons ·   │
│           live clock · notifications · help · win ctrls │
├─────────────────────────────────────────────────────────┤
│ PAGE CONTENT (white body)                                │
│  ┌───────────────────────────────────────────────────┐   │
│  │ PAGE HEADER (white): icon + title | page actions  │   │
│  └───────────────────────────────────────────────────┘   │
│  page panels / tables / editors                           │
└─────────────────────────────────────────────────────────┘
```

### 10.3 TitleBar Navigation Rules (D-0005)

- Navigation lives in the frameless custom TitleBar (dark chrome `#0A0A0B`), not a sidebar or dock.
- 7 icon nav buttons: Dashboard, Project Details, Second Brain, Report, Automations, Global Plan, Settings. Each has an `aria-label` and a tooltip on hover.
- Active nav item: `#231112` background + `#DC2626` icon color + small red indicator bar under the icon (non-color cue).
- Live clock in the right cluster: `ddd, dd MMM yyyy HH:mm:ss` (en-GB, ticking; hidden below 1100px width).
- Notification bell with unread badge opens a compact popover (newest first, per-item dismiss + dismiss all).
- Window controls (minimize / maximize-restore / close) via Python bridge.

### 10.4 Page Header Rules

The red full-width header was removed 2026-07-04 (D-0011). Red is an accent color only — never a page wash.

- Each page renders one white `.page-header` strip under the TitleBar: left = red-tinted page icon + bold title; right = `.page-header-actions` with page-specific controls.
- Dashboard actions: filter dropdowns (CR State / Appcode / Project Type + Clear + project count) · divider · Year select + Add Year (＋, popover) · Add Project · Refresh (spinning icon on click).
- Other pages keep their own contextual actions (e.g. Report filters, Project Details Back/selectors).
- Refresh lives on the pages that need it (Dashboard); there is no global refresh bar.

---

## 11. Dashboard — User Flows & Components

### 11.1 Purpose

Primary daily overview of all projects for the selected year. Entry point for all project operations.

### 11.2 Layout

```
Header: "Dashboard." | DateTime | [Year ▾] [Search] [+ Add Project] [🔄]
─────────────────────────────────────────────────────────────────────────
KPI Row:   [Total CR] [UAT Prepare] [PROD Ready] [Implemented] [Postponed]
─────────────────────────────────────────────────────────────────────────
Filter Row: [All (n)] [UAT Prepare (n)] [PROD Ready (n)] [Implemented (n)]
            [Postponed (n)] [Canceled (n)]          ... [N project(s)]
─────────────────────────────────────────────────────────────────────────
Project Table (scrollable, full height)
```

### 11.3 User Flow — Initial Load

```
App opens
  → Load settings.json
    → If root_folder unset → show First Run Setup dialog (choose root folder)
  → Read last_selected_year from settings.ui
  → Scan filesystem for year folders
  → Populate year dropdown
  → Load projects for selected year from SQLite cache (or scan if cache empty)
  → Render KPI cards + table
  → Start APScheduler background tasks
  → Begin event polling (1.5s interval)
```

### 11.4 User Flow — Filter by Folder State

```
User clicks filter tab (e.g. "PROD Ready")
  → Filter table in-memory (no rescan)
  → Update project count label
  → Table renders filtered rows only
  → Clicking "All" shows all folder states
```

### 11.5 User Flow — Search

```
User types in search field
  → Debounce 200ms
  → Filter visible rows by: project name, subproject name, CR number, drone ticket
  → Matches highlight
  → Clears on empty input
```

### 11.6 User Flow — Change Year

```
User selects year from dropdown
  → Trigger filesystem scan for that year
  → Rebuild SQLite cache for that year
  → Render new table
  → Save last_selected_year to settings.ui
```

### 11.7 User Flow — Add Year

```
User clicks + beside year dropdown
  → Dialog: "Create year folder?" with year input (default: next year)
  → If year > current_year + 2 → confirmation warning shown
  → Confirm → create {ROOT}/{YEAR}/ and 5 state folders
  → Refresh year dropdown → select new year
```

### 11.8 User Flow — Add Project

```
User clicks "+ Add Project"
  → Navigate to Project Details in NEW_PROJECT mode
  → (see Section 12 for full flow)
```

### 11.9 User Flow — Open Project Details

```
User clicks Details button in row action menu
  → Navigate to Project Details in SHOW_EDIT mode
  → Load selected project
```

### 11.10 User Flow — Change CR State (Inline)

```
User clicks CR State dropdown in table row
  → Show valid next states for current state
  → IN-PROGRESS shown as disabled/label (auto only)
  → User selects state
  → If POSTPONED: confirmation modal ("Move project to POSTPONED?")
  → If CANCELED: confirmation modal ("Mark as Canceled? This moves project to CANCELED folder.")
  → Backend validates transition + guard
  → On success: update row, history entry, notification
  → On failure: show specific guard failure message
```

### 11.11 User Flow — Change Drone State (Inline)

Same pattern as CR State inline change.

```
  → If all Drones + CR reach APPROVED → auto move folder to PROD_READY
  → Notification: "Project moved to PROD_READY."
  → Row folder state badge updates
```

### 11.12 User Flow — Inline CR/Drone Link Paste

```
User clicks CR Number cell or Drone Ticket cell
  → Cell becomes editable inline input
  → User pastes full URL
  → On blur/Enter: store URL, display extracted identifier
  → Multiple rows can be bulk-pasted in sequence
  → History entry after each committed save
```

### 11.13 User Flow — Row Action Menu (⋮)

```
User clicks ⋮ button
  → Popup menu shows:
    - Open Project Folder (opens Windows Explorer)
    - Project Details
    - Move to PROD_READY (if UAT_PREPARE + guards)
    - Move to Implemented (if PROD_READY + guards)
    - Postpone
    - Cancel
    - Reopen (if POSTPONED or CANCELED)
    - Delete (Recycle Bin, confirmation required)
  → Each action validates server-side
```

### 11.14 User Flow — Refresh

```
User clicks 🔄
  → Rescan selected year from filesystem
  → Rebuild SQLite cache
  → Refresh table + KPI
  → Refresh icon spins (650ms animation)
```

### 11.15 Table Columns

| Column         | Content                                                                    | Editable Inline |
| -------------- | -------------------------------------------------------------------------- | --------------- |
| No             | Row number                                                                 | ❌              |
| Main Project   | Project name (click → open folder)                                         | ❌              |
| Sub Project    | Sub project name(s) (click → open sub folder)                              | ❌              |
| Start DateTime | `datetime-local` inline editor, saved as timezone-aware ISO local datetime | ✅              |
| End DateTime   | `datetime-local` inline editor, saved as timezone-aware ISO local datetime | ✅              |
| Drone Ticket   | Extracted ID + link icon (click → browser)                                 | ✅ (paste URL)  |
| Drone State    | Inline state dropdown                                                      | ✅              |
| CR Number      | Extracted ID + link icon (click → browser)                                 | ✅ (paste URL)  |
| CR State       | Inline state dropdown                                                      | ✅              |
| Actions        | ⋮ menu                                                                     | —               |

---

## 12. Project Details — User Flows & Components

### 12.1 Purpose

Operational workspace for one project: edit metadata, manage CR/Drone links, manage sub-projects, manage files, write notes, review history.

### 12.2 Modes

**NEW_PROJECT mode:** creating a brand new project.  
**SHOW_EDIT mode:** viewing/editing an existing project.

### 12.3 Header

```
Header: "Project Details." | DateTime | [Year ▾] [Project ▾] [Sub Project ▾] [Search] [+ Add Project] [🔄]
```

### 12.4 User Flow — NEW_PROJECT Mode

```
User arrives from "+ Add Project"
  → Form shows minimal required fields:
    - Project Name (realtime Windows folder name validation)
    - Year (pre-selected from dashboard)
    - Start DateTime
    - End DateTime
    - CR Link (optional at creation)
    - First Drone Link + Drone Owner (optional at creation)
    - Implementation Plan (optional)
  → Save disabled while project name is invalid
  → User fills fields → clicks Save
    → Create folder: {ROOT}/{YEAR}/UAT_PREPARE/{PROJECT_NAME}/
    → Create project_data.json with defaults
    → Create notes.md (empty)
    → Append history: "Project created"
    → Navigate to SHOW_EDIT mode for new project
    → Dashboard row added
  → Cancel → return to Dashboard, no files created
```

### 12.5 User Flow — SHOW_EDIT Mode Layout

```
┌───────────────────────────────────────────────────────────────────────┐
│ Project Command Center: [Project ▾]  [Sub Project ▾]  [Open] [Delete] │
├────────────────────────┬──────────────────────────────────────────────┤
│  LEFT COLUMN           │  RIGHT COLUMN                                 │
│                        │                                               │
│  Project Identity      │  Files                                        │
│  ─────────────────     │  ──────                                       │
│  Project Name          │  [Add File] [From Template]                   │
│  CR Number             │  file list                                     │
│  Drone Ticket(s)       │                                               │
│  CR State              │  Notes (markdown)                             │
│  Drone State           │  ──────                                       │
│  Owner                 │  [Undo] [Redo] [B][I][H1][H2][Code][Link]... │
│                        │  textarea (autosave 1000ms)                   │
│  Schedule              │                                               │
│  ─────────────────     │  Activity History                             │
│  Start DateTime        │  ─────────────                                │
│  End DateTime          │  read-only list, newest first                 │
│                        │                                               │
│  Sub Projects          │                                               │
│  ─────────────────     │                                               │
│  [Add Sub Project]     │                                               │
│  sub project table     │                                               │
│                        │                                               │
└────────────────────────┴──────────────────────────────────────────────┘
```

### 12.6 User Flow — Edit CR Link

```
User clicks CR Number field
  → Becomes editable input
  → User pastes full URL
  → On blur/Enter:
    → Extract CR number for display
    → Auto-set CR state to PENDING SUBMISSION if currently empty
    → Save to project_data.json
    → Append history: "CR link updated"
```

### 12.7 User Flow — Change CR State (Project Details)

```
User clicks CR State dropdown
  → Shows valid selectable states (not IN-PROGRESS)
  → User selects new state
  → Backend validates transition guard
  → On failure → show modal listing each failed guard
  → On success:
    → Update cr_state + cr_state_updated_at
    → If first PENDING APPROVAL → set cr_pending_approval_at
    → Append history
    → If auto-PROD_READY conditions now met → trigger folder move
    → If POSTPONED/CANCELED → move folder
    → UI updates folder state badge
```

### 12.8 User Flow — Add Drone Ticket

```
User clicks "+ Add Drone Ticket"
  → Dialog: drone link input + subfolder mapping (main project or sub project) + owner picker
  → Owner picker: search Outlook contacts (Windows COM) or free text fallback
  → Confirm → add to drone_tickets array → save JSON
  → Append history: "Drone ticket added: {extracted_id}"
```

### 12.9 User Flow — Add Sub Project

```
User clicks "+ Add Sub Project"
  → Inline or dialog: enter sub project folder name
  → Realtime folder name validation
  → Confirm → create subfolder → add notes.md inside
  → Sub project appears in sub project table
  → User can now map a Drone ticket to the new sub project
```

### 12.10 User Flow — Sub Project Table

```
Columns: Sub Project | Drone Ticket | Drone State | Owner | Actions
Actions: Open Folder | Delete (Recycle Bin) | Rename (if not locked)
Drone State editable inline → same guard flow as main project
Drone Ticket editable inline → paste URL → extract + store
```

### 12.11 User Flow — File Management

```
User views file list (main project files only; sub project files not shown in main list)

Add File from Template:
  → Browse file_template_folder
  → Select template
  → Create copy: {CR_NUMBER}_{template_filename} in project folder
  → Open file with default OS app

Add Manual File:
  → Input filename (with or without extension)
  → Choose file type if no extension given
  → Create empty file
  → Open with default OS app

Open File: → os.startfile (Windows)
Delete File: → confirmation → send2trash (Recycle Bin)
Rename File: → inline rename → save

Note: all file ops disabled in PROD_READY and IMPLEMENTED states (except Add/Edit Notes)
```

### 12.12 User Flow — Notes & CR Docs (RTE, D-0007/D-0010/D-0012)

Per-format strategy (D-0012, 2026-07-04): formats Tiptap saves natively write
directly; `.docx` uses the document pipeline (JSON source of truth + derived
Word export).

```
notes.md / .txt (direct save):
  → Tiptap editor; autosave 1000ms after last keystroke
  → "Saving..." / "Saved" indicator; Ctrl+S = immediate save
  → .md serializes to Markdown, .txt to plain text (atomic write)

uat-signoff.docx / prod-lv.docx (pipeline):
  → Editable in Tiptap; source of truth = _cr-docs/.rte/<name>.source.json
    (Tiptap JSON + revision + content hash)
  → Autosave 1000ms saves JSON only; identical content is skipped (hash)
  → Real .docx regenerated in the background (custom Tiptap-JSON→python-docx
    exporter): on Ctrl+S, on doc switch, after 5s idle, and on app close
  → Status shows a countdown ("Saved — DOCX in 5s") until the idle export fires
  → Max 1 export worker; latest revision wins; atomic tmp→replace
  → Page = A4 with Word "Narrow" margins (12.7mm); the editor area is exactly
    the printable width (WYSIWYG bounds), and the exporter clamps images/
    tables that exceed it so exported content is never cut off
  → Images drag-resize via corner handle; tables drag-resize per column edge
  → .rte sidecar folders are hidden (Windows hidden attribute)
  → .docx open in Word (locked): status "DOCX locked — will retry",
    old file untouched, retried on next open — source is always safe
  → .docx edited directly in Word: re-imported on next open (stale check)
  → First open of a legacy non-empty .docx migrates via mammoth HTML import

Images (all rich editors):
  → Win+Shift+S screenshot → Ctrl+V pastes into the editor (also drag-drop)
  → Bytes stored once as content-addressed asset files in .rte/assets/
    (magic-byte validation, 15 MB cap); never permanent base64
  → notes.md references assets as ![alt](.rte/assets/<id>.<ext>);
    resized images round-trip as inline <img … width> HTML

Toolbar: toggle buttons reflect the active format at the cursor (red active
state); a "?" popover lists shortcuts & tips (Ctrl+S export, screenshot paste,
drag-resize, 5s export timing).

Locking: IMPLEMENTED project state = all docs read-only (unchanged).
.msg files stay open-externally (unchanged).
```

### 12.13 User Flow — REOPEN

```
User is in POSTPONED or CANCELED project
  → REOPEN button visible in action menu or header
  → Confirmation dialog: "Move project back to UAT_PREPARE?"
  → Confirm:
    → Move folder from POSTPONED/CANCELED to UAT_PREPARE
    → Set CR state to PENDING SUBMISSION
    → Append history: "REOPEN: moved from {old_state} to UAT_PREPARE"
    → Notification sent
    → UI refreshes
```

---

## 13. Second Brain — User Flows & Components

### 13.1 Purpose

Local personal knowledge workspace: markdown notes, project documents discovery, operational playbooks, and reusable link library.

### 13.2 Header

```
Header: "Second Brain." | DateTime | [🔄]
Tab Bar: [Notes] [Link Bank]
```

Tab bar follows the pill-style pattern from `second_brain_redesign.py`.

### 13.3 Notes Tab Layout

```
┌──────────────────────────┬─────────────────────────────────────────────┐
│  LEFT: Notes & Documents │  RIGHT: Editor / Preview                     │
│                          │                                               │
│  [Search...] [📅] [Sort] │  Metadata: Title | Tags                      │
│  [Add Folder][Add File]  │  Breadcrumb + document state indicator        │
│  [Filter ▾]              │  State: [Editable][Image][External]           │
│  ─────────────────────── │  Mode: [Edit][Preview]                        │
│  ▶ Search Results        │  Toolbar: [Undo][Redo][B][I][U][H1][H2]...   │
│  ▶ Pinned                │        [Code][Link][HR][Quote] ... [Pin][⭐] │
│  ▶ Favorites             │  ─────────────────────────────────────────── │
│  ▶ Second Brain Notes    │  Editor/Preview content (stretchable)         │
│    ▶ Daily               │  ─────────────────────────────────────────── │
│    ▶ UAT                 │  Backlinks / Related Notes                    │
│  ▶ Project Documents     │  ─────────────────────────────────────────── │
│    (all project files)   │  Recent Activity                              │
│                          │                                               │
└──────────────────────────┴─────────────────────────────────────────────┘
Flow Status: [Ready · select note or search]
```

### 13.4 Supported File Modes

| Extensions                                                                                                                                                    | Mode                             |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------- |
| `.md`, `.txt`, `.py`, `.sh`, `.ps1`, `.sql`, `.json`, `.csv`, `.log`, `.yml`, `.yaml`, `.xml`, `.toml`, `.ini`, `.cfg`, `.env`, `.ts`, `.js`, `.html`, `.css` | Editable in-app                  |
| `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`                                                                                                                       | Preview only in-app              |
| `.pdf`, `.docx`, `.xlsx`, `.zip`, and all others                                                                                                              | Open externally (default OS app) |

### 13.5 User Flow — Browse Notes Tree

```
User opens Second Brain → Notes tab
  → Tree renders: Pinned | Favorites | Second Brain Notes | Project Documents
  → Project Documents shows all files in all project/subproject paths under root_folder
  → User expands folders
  → User clicks a file
    → Editable file → load in editor
    → Image file → show inline preview
    → External file → show "Open with default app" message + button
```

### 13.6 User Flow — Search Notes

```
User types in search field
  → Debounce 150ms
  → Query runs against in-memory precomputed index (title, body, tags, path, content)
  → Results appear under "Search Results" group in tree (above other groups)
  → Date filter: user clicks 📅 → unclipped popup calendar → sets YYYYMMDD filter
  → Sort: Newest | Oldest | A-Z | Type
  → User clicks result → open in editor
  → Clearing search removes "Search Results" group from tree
```

### 13.7 User Flow — Create Note/Folder

```
User clicks Add Folder:
  → If item selected in tree → create child folder
  → If nothing selected → create root folder in Second Brain path
  → Inline rename starts immediately in tree
  → Enter or click-out commits name

User clicks Add File:
  → Create new empty file with selected type (default: .md)
  → Inline rename starts in tree
  → On commit: determine open_mode from extension
  → Load into editor (if editable)
```

### 13.8 User Flow — Pin / Favorite

```
User opens a note
  → Clicks Pin button in editor toolbar
    → Note appears under "Pinned" group in tree
    → Pin indicator visible on tree item
  → Clicks Favorite (⭐) button
    → Note appears under "Favorites" group in tree
Pin/Favorite status stored in note metadata (SQLite or frontmatter in .md)
```

### 13.9 User Flow — Markdown Edit/Preview

```
User is in Edit mode (default):
  → Textarea is editable
  → Toolbar inserts markdown syntax at cursor
  → Autosave: 1000ms debounce → write to .md file
  → Status shows "Saving..." / "Saved"

User clicks Preview:
  → Content rendered as HTML via marked.js
  → Textarea becomes read-only
  → Switch back to Edit to continue writing
```

### 13.10 Backlinks & Related Notes

```
Below editor, Related Notes panel shows:
  → Same tag matches
  → Wiki-style [[NoteTitle.md]] references
  → Same project file context
→ Click related item → open in editor
Production: built from tags, note titles, links, file metadata
Prototype: static examples
```

### 13.11 Recent Activity

```
Recent Activity panel shows last-touched notes/files:
  → Edited note
  → Opened document
  → Created note
→ Click to resume work
Production: local activity history stored in SQLite
```

---

## 14. Link Bank — User Flows & Components

### 14.1 Purpose

Reusable work link library grouped by category with search, tags, and quick copy.

### 14.2 Layout

```
┌──────────────────────────────┬────────────────────────────────────────────┐
│  LEFT: Categories            │  RIGHT: Link Content                        │
│                              │                                              │
│  [Search...] [📅] [Sort ▾]  │  Add/Edit Link Panel                         │
│  [+ Category] [Rename] [📦] │  ────────────────────────────────────────── │
│  [Filter ▾]                  │  Title | URL | Tags | Description           │
│  ─────────────────────────── │           [Pin] [⭐] [Save]                 │
│  PROD · 3 links              │  ────────────────────────────────────────── │
│  UAT · 3 links               │  "PROD" Category Header                      │
│  CR & ITSM Tools · 2 links   │  [Search within category...] [Sort ▾]       │
│  Personal · 0 links          │  [Copy URL] [Edit] [Remove]                 │
│  Archived · 4 links          │  ────────────────────────────────────────── │
│                              │  ┌──────────────────┬─────────────────────┐ │
│                              │  │  Link List       │  Selected Link      │ │
│                              │  │  ─────────────── │  Detail Panel       │ │
│                              │  │  compact cards   │                     │ │
│                              │  └──────────────────┴─────────────────────┘ │
└──────────────────────────────┴────────────────────────────────────────────┘
```

### 14.3 User Flow — Browse Links

```
User opens Second Brain → Link Bank tab
  → Category list renders on left
  → Clicking empty area deselects category
  → Click category → right panel shows links for that category
  → Links shown as compact cards (title, tags/badges, Last modified)
  → Click a link card → Selected Link Detail panel updates
    → Shows: URL (clickable), tags, details, category, path, date, status
  → Click URL in detail panel → opens in default OS browser
  → Click Copy URL → copies to clipboard
```

### 14.4 User Flow — Add Link

```
User fills Add/Edit Link panel:
  → Link Title, Link (URL), Tags (comma-separated hashtags), Description
  → Right side: Description textarea
  → Bottom-right: [Pin] [⭐] [Save]
  → Click Save → add new link to selected category
  → Prototype: in-memory; Production: save to link_bank.json
```

### 14.5 User Flow — Edit Link

```
User selects a link card
  → Clicks Edit in action toolbar
  → Selected link data populates Add/Edit Link panel
  → User modifies fields → clicks Save (same button)
  → Link card updates
```

### 14.6 User Flow — Archive Link/Category

```
User selects link → clicks Remove → confirmation → link archived
User right-clicks category → Archive → confirmation → category + links hidden
Archived items visible in "Archived" section → user can Restore
Hard delete not available; archive is the soft delete
```

### 14.7 User Flow — Search Links

```
User types in left panel search field
  → Case-insensitive, searches: title, URL, tags, details, category
  → Date filter available (same calendar popup pattern)
  → Sort: Newest | Oldest | A-Z | Favorite | Pinned
  → Results show across categories
  → Clicking result selects its category and highlights link
```

### 14.8 User Flow — Import/Export

```
Export: → choose local file path → save link_bank.json or CSV
Import: → browse local file → validate format → merge with confirmation
```

### 14.9 Link Card Content

Each compact card shows:

- Title (bold)
- Tag badges (user-defined hashtags)
- Last modified timestamp (bottom-right, muted)

Selected Link Detail shows full: URL, tags, details, category, path, date, status.

### 14.10 Link Bank Badges

Tags are user-defined free-form strings. No fixed list. Initial suggestions include: `PROD`, `UAT`, `SOP`, `Portal`, `Dashboard`, `Working`, `Login Needed`, `Internal Only`. User can add/remove any tag.

---

## 15. Report — User Flows & Components

### 15.1 Purpose

Searchable, filterable, export-ready view of all projects and deployment status.

### 15.2 Layout

```
Header: "Report." | DateTime | [🔄]
─────────────────────────────────────────────────────────────────
Filter Row: [Year ▾] [Month ▾] [Folder State ▾] [CR State ▾] [Drone State ▾]
            [Search...] [Clear]                              [Export CSV]
─────────────────────────────────────────────────────────────────
KPI Cards: [Total CR] [UAT Prepare] [PROD Ready] [Implemented] [Postponed]
─────────────────────────────────────────────────────────────────
Chart Summaries: [CR States] [Drone States] [Monthly Activity]
(each has labeled summary rows, not chart.js — utilitarian style)
─────────────────────────────────────────────────────────────────
Report Table (scrollable, full height with vertical scrollbar)
```

### 15.3 User Flow — Filter & Search

```
User adjusts Year/Month/State filters
  → Table updates immediately (in-memory filter from loaded data)
  → KPI cards update to match current filter

User types in Search
  → Debounce 200ms
  → Filter by: project name, sub project, CR number, drone ticket
  → Results shown inline

User clicks Clear
  → All filters reset to defaults
  → Search cleared
```

### 15.4 User Flow — Export CSV

```
User clicks "Export CSV"
  → Python opens save dialog (pywebview file dialog or OS dialog)
  → User chooses output path + filename
  → Export runs in background
  → Notification on success: "CSV exported to {path}"
  → CSV uses Python standard csv library; Excel-compatible (UTF-8 BOM)
  → Export respects active filter set
```

### 15.5 Report Table Columns

| Column                 |
| ---------------------- |
| No                     |
| Main Project           |
| Sub Project            |
| Year                   |
| Folder State           |
| Start DateTime         |
| End DateTime           |
| CR Number (display)    |
| CR State               |
| Drone Ticket (display) |
| Drone State            |
| T-10 Status            |
| Last Updated           |

---

## 16. Automations — User Flows & Components

### 16.1 Purpose

Safe, configurable automation of Outlook email, Teams messages, scheduled alarms, and general trigger-condition-action rules.

### 16.2 Layout

```
Header: "Automations." | DateTime | [🔄]
Tab Bar: [Outlook] [Teams] [Scheduler] [Rules Engine]
─────────────────────────────────────────────────────────────────
[Tab content area]
```

---

### 16.3 Outlook Tab

#### Purpose

Manage outbound Outlook email templates (ACK_UAT, ACK_SOP, APRVL_CR, APRVL_SOP) and download email jobs.

#### Layout

```
┌──────────────────────────────────────┬──────────────────────────────────────┐
│  SEND AUTOMATION                     │  DOWNLOAD AUTOMATION                  │
│  ────────────────────────────────    │  ────────────────────────────────     │
│  Hint: Double-click row to edit      │  Relation to Send categories          │
│  [CATEGORY | PURPOSE | CONDITIONS]   │  [CATEGORY | DETAILS] table           │
│  4 rows                              │  2 rows                               │
│                   [+ Add Category]   │              [Downloaded Emails ▶]   │
│  ──────────────────────────────────  │  ──────────────────────────────────   │
│  Send Automation Log                 │  Download Tool Log                    │
└──────────────────────────────────────┴──────────────────────────────────────┘

Metrics Row: [Send Categories] [Download Jobs] [HTML Templates] [On Going ACK] [On Going Tech LV]
```

#### User Flow — View and Edit Send Category

```
User double-clicks a send category row (e.g. ACK_UAT)
  → Email Template Dialog opens (full-screen dialog)

Dialog layout (2-column):
  LEFT:
    - Category Code (editable)
    - To, CC (email fields)
    - Subject template with placeholders
    - Body textarea (or HTML file option)
    - Attachment field + Browse
    - Automation Mode: [Draft Only] [Send Immediately]
    - Placeholder chips (click to insert): {PROJECT_NAME} {CR_NUMBER} {CR_LINK} etc.

  RIGHT:
    - Active Conditions (condition grid: CR State op value, Drone State op value, Project Pattern)
    - Condition Preview (live display of rule as text)
    - Email Automation Log (scrollable, latest 10 entries)

  Footer: [Cancel] [Save]
```

#### Email Template Placeholders

```
{PROJECT_NAME}  {CR_NUMBER}    {CR_LINK}         {CR_STATE}
{DRONE_TICKET}  {DRONE_LINK}   {DRONE_STATE}     {START_DATETIME}
{END_DATETIME}  {IMPLEMENTATION_PLAN}             {DISPLAY_NAME}
```

#### User Flow — Send Email (from Project Details or Automations)

```
User triggers email from project context (Project Details or Rules Engine action):
  → Select category (ACK_UAT, etc.)
  → Backend resolves placeholders from project_data.json
  → If mode = draft:
    → Outlook COM creates draft in Outbox
    → Dialog shows preview
    → User reviews and clicks Send in Outlook
  → If mode = send:
    → Confirmation dialog: "Send now to {to}?"
    → Confirm → COM sends immediately
  → email_flags updated (visual indicator only)
  → History entry appended
  → Notification created
```

#### User Flow — Downloaded Emails Dialog

```
User clicks "Downloaded Emails"
  → Dialog opens showing all downloaded reply emails:
    - Subject, From, CR Number, Date, Tag/Category
  → Sorted newest first by default
  → Search and sort available
  → Click email card → expand details
  → Close button
```

#### Email Category Conditions

Each category can define conditions using operators:

| Field                | Operators                                                                      |
| -------------------- | ------------------------------------------------------------------------------ |
| CR State             | eq, nq, contains, not contains, starts_with, ends_with, is_empty, is_not_empty |
| Drone State          | (same)                                                                         |
| Project Name pattern | (same)                                                                         |

If conditions are defined, email action only executes when all conditions pass.

---

### 16.4 Teams Tab

#### Purpose

Configure and trigger Teams message automations (deep link + clipboard paste by default).

#### Layout

```
┌──────────────────────────────────────────┬────────────────────────┐
│  LEFT: Teams Message Automation          │  RIGHT: Teams Status   │
│                                          │                        │
│  Purpose text area                       │  [Saved Automation]    │
│  Webhook URL                             │  [Active Automation]   │
│  Attachment (optional)                   │  [Deactive Automation] │
│  Automation Mode: [Preview][Send Now]    │  [Last Trigger]        │
│                                          │                        │
│  Saved Automations Table:                │                        │
│  NAME | PURPOSE | MODE | ACTIVE | DATE   │                        │
│  3 rows  [Open Teams Automation ▶]       │                        │
│                                          │                        │
│  Teams Automation Log                    │                        │
└──────────────────────────────────────────┴────────────────────────┘
```

#### User Flow — Create/Edit Teams Automation

```
User clicks "Open Teams Automation" or double-clicks row
  → Teams Automation Dialog opens (full-screen dialog)

Dialog layout (2-column):
  LEFT:
    - Automation Purpose
    - Webhook URL
    - Attachment path + Browse
    - Automation Mode: [Preview First (default)] [Send Immediately]
    - Message Body textarea

  RIGHT:
    - Rules section
    - [+ Add Rules] button
    - Rules list (scrollable):
      Each rule row: [index] [Field ▾] [Condition ▾] [Value/Pattern]
      Fields: CR State, Drone State, Project State, Is File Exist
      Conditions: conditions, equals, is not equals, true, false

  Footer: [Delete] [Cancel] [Save]
```

#### User Flow — Send Teams Message (from Automation or Rules Engine)

```
User triggers Teams message:
  → If mode = preview:
    → App opens Teams desktop app or web via deep link
    → Message pasted to clipboard
    → User manually sends in Teams
  → If mode = send immediately AND teams_auto_send = true:
    → Countdown (configurable, default 3s) shows
    → User can cancel during countdown
    → After countdown: pyautogui pastes and presses Enter
    → pyautogui.FAILSAFE = True (mouse to top-left corner aborts)
  → History entry appended
  → Notification created
```

---

### 16.5 Scheduler Tab

#### Purpose

Alarm and reminder entries with notes. Each entry can trigger in-app notification, Outlook email, or Teams message (in-app is default; email/Teams require user confirmation).

#### Layout

```
KPI Row: [Due Soon] [Overdue] [Paused] [Total Entries]
─────────────────────────────────────────────────────────────────
Table: RULE | PROJECT FILTER | STATE FILTER | SCHEDULE | CHANNEL | STATUS
                                              [Import Rule] [+ Add Reminder]
─────────────────────────────────────────────────────────────────
```

#### User Flow — Add Scheduler Entry

```
User clicks "+ Add Reminder"
  → Dialog / form:
    - Name (alarm title)
    - Notes (alarm message/content, markdown supported)
    - Schedule Type: One-time | Daily | Weekly | Monthly | Custom Cron
    - Schedule Config: datetime picker or cron expression
    - Project Filter: optional (bind alarm to a specific project)
    - State Filter: optional (only trigger when project is in certain CR/folder state)
    - Channels (multi-select):
        ☑ In-app Notification (default, always on)
        ☐ Outlook Email (requires: To, Subject, Body in sub-form)
        ☐ Teams Message (requires: webhook or message content)
    - Confirm Outlook/Teams channels: additional confirmation step before saving
  → Save → entry added to scheduler table → APScheduler job created
```

#### User Flow — Alarm Triggers

```
APScheduler fires at scheduled time:
  → Evaluate project filter (if any)
  → Evaluate state filter (if any)
  → If conditions met:
    → In-app: push notification event to frontend event queue
    → Outlook (if configured): COM creates draft or sends email
    → Teams (if configured): deep link + clipboard + optional countdown
  → Update last_triggered_at in SQLite
  → Log execution result to SQLite automation_rule_logs
  → Mark as completed if one-time entry
```

#### User Flow — Edit / Pause / Delete Entry

```
User clicks row action:
  → Edit → opens same dialog pre-filled
  → Pause/Resume → toggles status in SQLite, APScheduler pauses job
  → Delete → confirmation → remove from SQLite + APScheduler
```

---

### 16.6 Rules Engine Tab

#### Purpose

General trigger → condition → action automation. Handles inbound monitoring (email polling), state-based triggers, and multi-action workflows.

#### Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Rules Engine                                                           │
│  ─────────────────────────────────────────────────────────────────────  │
│  RULE | TRIGGER | CONDITIONS | ACTIONS | ENABLED | LAST RUN            │
│  [+ Add Rule]                                                           │
│  ─────────────────────────────────────────────────────────────────────  │
│  Rule Execution Log (latest 20 entries)                                 │
└─────────────────────────────────────────────────────────────────────────┘
```

#### User Flow — Create Rule

```
User clicks "+ Add Rule"
  → Rule Editor Dialog:

    SECTION: Rule Info
      - Rule Name
      - Enabled toggle

    SECTION: Trigger
      - Trigger Type: [Schedule ▾]
          Schedule: run every X minutes/hours
      - (Future: CR State Changed, Drone State Changed, Folder Changed)

    SECTION: Conditions (all must be true to execute actions)
      - [+ Add Condition]
      - Each condition row:
          [Field ▾] [Operator ▾] [Value]
          Fields: email_subject | email_from | email_body | email_to |
                  attachment_name | cr_number | cr_state | drone_state
          Operators: contains | equals | starts_with | ends_with | matches_regex
          Value: text input (supports {CR_NUMBER} placeholder)

    SECTION: Actions (ordered list, run top-to-bottom)
      - [+ Add Action]
      - Each action row:
          [Action Type ▾] [params...]

          Action Types:
            download_email → save email body to project folder
            save_attachment → save attachment to project folder
            update_cr_state → [new state ▾] (for matching project)
            update_drone_state → [subfolder ▾] [new state ▾]
            send_outlook_email → [category ▾] (uses Outlook templates)
            send_teams_message → [automation ▾]
            in_app_notification → [message text]
            append_history → [entry text]

    Footer: [Cancel] [Save]
```

#### User Flow — Rule Execution

```
APScheduler fires rule at configured interval:
  → Evaluate all conditions against email inbox (via Outlook COM, Windows-guarded)
  → If all conditions pass:
    → Execute actions in order
    → Each action result logged
    → On error: log failure, skip to next action (configurable)
  → Write execution result to SQLite automation_rule_logs
  → Push in-app notification if action includes one
```

#### Use Case Example (Download Email Approval)

```
Rule: "Download Approval Email for SOP CR"
Trigger: Schedule every 5 minutes
Conditions:
  - email_subject contains: "{CR_NUMBER}"
  - email_from contains: "@example.com"
  - email_body contains: "approved"
Actions:
  1. download_email → save to project folder
  2. save_attachment → save all attachments to project folder
  3. update_cr_state → APPROVED
  4. in_app_notification → "Approval email received for {CR_NUMBER}"
  5. send_teams_message → "ACK_TO_TEAMS" automation
```

---

## 17. Settings — User Flows & Components

### 17.1 Purpose

Configure app behavior, storage paths, display preferences, automation defaults, and access help documentation.

### 17.2 Layout

```
Header: "Settings." | DateTime | [🔄]
─────────────────────────────────────────────────────────────────
Body (50/50 split, resizable splitter):
  LEFT: Settings Forms          RIGHT: Help Center (document reader)
  ─────────────────────────     ─────────────────────────────────
  General card                  [Search help topics...]
  Behavior card                 ─────────────────────────────────
  Paths card                    Help Guide content (scrollable)
  [Save Settings]
```

### 17.3 User Flow — Edit Settings

```
User opens Settings
  → Left panel shows 3 cards: General, Behavior, Paths
  → Fields are editable
  → Changes are staged (not auto-saved)
  → User clicks "Save Settings"
    → Validate all fields
    → Write to settings.json
    → Apply changes that can be hot-reloaded
    → Show "Settings saved" toast notification
    → If restart-required change: show warning toast
```

### 17.4 Settings Fields

#### General Card

| Field           | Type                 | Default                     |
| --------------- | -------------------- | --------------------------- |
| Root Folder     | Text + Browse button | —                           |
| Display Name    | Text input           | empty                       |
| Language        | Dropdown: en, id     | en                          |
| Datetime Format | Text input           | `ddd, dd MMM yyyy HH:mm:ss` |

#### Behavior Card

| Field                 | Type                                                            | Default                |
| --------------------- | --------------------------------------------------------------- | ---------------------- |
| T-10 Threshold Days   | Spinner                                                         | 10                     |
| Auto Refresh Interval | Dropdown: off, 15s, 30s, 1min                                   | off                    |
| Startup Behavior      | Dropdown: current_year_dashboard, project_details, second_brain | current_year_dashboard |

#### Paths Card

| Field                | Type                 | Default                                   |
| -------------------- | -------------------- | ----------------------------------------- |
| Second Brain Folder  | Text + Browse button | `%APPDATA%\ProjectTrackerDBS\SecondBrain` |
| File Template Folder | Text + Browse button | empty                                     |

**Note:** Automation settings (email categories, Teams configs, Rules Engine) are managed within the Automations page, not Settings. Theme is fixed (Utilitarian + Modern Minimalist, single enterprise palette) — no theme switcher.

### 17.5 Help Center Panel

```
- Search field (case-insensitive search over help topics)
- Topics: General Settings, Behavior, Paths, Notifications, Automations,
          Project Details, Report, Responsive UI, Troubleshooting,
          Future Documentation
- Each topic: title + description paragraph
- Style: white document-reader background, left-bordered topic cards
- Content: local markdown or hardcoded HTML; no PDF dependency
```

---

## 18. Notifications System

### 18.1 Purpose

Lightweight operational alerts visible at all times without leaving the current page.

### 18.2 Notification Panel (Bottom Dock)

Notifications are accessible from the bottom dock (see §10.3). A dock button with unread badge shows the notification count. Click/hover opens a compact popover above the dock.

```
DOCK NOTIFICATION BUTTON:
  Bell icon button with unread count badge
  Hover/click → compact popover above dock

POPOVER:
  Scrollable list of notification cards (newest first)
  Empty state: "No notifications yet."
  Close when cursor leaves popover
```

### 18.3 Notification Types

| Type                   | Trigger                                                    |
| ---------------------- | ---------------------------------------------------------- |
| State Transition       | CR/Drone state changed (auto or manual)                    |
| Folder Move            | Project moved to PROD_READY/IMPLEMENTED/POSTPONED/CANCELED |
| T-10 Warning           | Today passes T-10 deadline for PENDING APPROVAL            |
| Auto IN-PROGRESS       | Scheduler sets IN-PROGRESS                                 |
| Email Draft/Send       | Outlook email created/sent                                 |
| Teams Paste            | Teams message pasted                                       |
| Rules Engine Execution | Rule triggered and actions completed                       |
| Scheduler Alarm        | Scheduled alarm fires                                      |
| CSV Export             | Export completed successfully                              |
| Filesystem Warning     | Corrupt JSON, missing folder mapping                       |
| Download Email         | Reply email received and downloaded                        |

### 18.4 Notification Storage

- Active session notifications: in-memory (cleared on app restart).
- Notification history: SQLite `notifications` table (persistent).
- MVP may use in-memory only; persistent history is Phase H addition.

---

## 19. Python ↔ Svelte Communication

### 19.1 Bridge Pattern

Frontend calls Python through the `JsApi` class registered with pywebview:

```javascript
// Svelte frontend call pattern
const result = await window.pywebview.api.methodName(payload);
// result: { ok: boolean, data: any, warnings: string[], error: ErrorObj | null }
```

### 19.2 Standard Bridge Response Shape

```typescript
interface BridgeResponse<T> {
  ok: boolean;
  data: T | null;
  warnings: string[];
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
  } | null;
}
```

Every bridge method returns this shape. Never return raw Python exceptions. Never expose stack traces.

### 19.3 Background Event Push (Event Queue Pattern)

Background threads (APScheduler, Outlook COM, Rules Engine) push events to a `queue.Queue`. Frontend polls this queue every ~1.5 seconds:

```python
# web/event_queue.py
import queue
_event_queue: queue.Queue = queue.Queue()

def push(event: dict) -> None:
    _event_queue.put_nowait(event)

def drain() -> list[dict]:
    events = []
    while not _event_queue.empty():
        try:
            events.append(_event_queue.get_nowait())
        except queue.Empty:
            break
    return events
```

```javascript
// Svelte polling store (frontend)
setInterval(async () => {
  const { data: events } = await window.pywebview.api.app_get_pending_events();
  events?.forEach((event) => handleEvent(event));
}, 1500);
```

For high-priority events (auto IN-PROGRESS, alarm fires), Python may also use `webview.windows[0].evaluate_js()` from a main-thread-safe context as a secondary push channel.

### 19.4 Event Payload Structure

```python
{
  "type": "AUTO_IN_PROGRESS" | "FOLDER_MOVED" | "NOTIFICATION" | "SCAN_COMPLETE" | ...,
  "payload": { ... },
  "timestamp": "ISO8601"
}
```

---

## 20. Windows Integrations (Guarded)

All Windows integrations are wrapped in `IS_WINDOWS = sys.platform == "win32"` guards. Non-Windows dev environment receives graceful mock/log responses.

### 20.1 Outlook COM

```python
# infrastructure/outlook_client.py
import sys
IS_WINDOWS = sys.platform == "win32"

def create_draft_email(to, cc, subject, body, attachment_path=None):
    if not IS_WINDOWS:
        print(f"[DEV] Would create Outlook draft to {to}: {subject}")
        return
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        mail = outlook.CreateItem(0)
        mail.To = to
        mail.CC = cc
        mail.Subject = subject
        mail.Body = body
        if attachment_path:
            mail.Attachments.Add(str(attachment_path))
        mail.Display()  # draft mode
        # mail.Send()  # send mode
    finally:
        pythoncom.CoUninitialize()
```

Outlook COM must run in a **background thread**, not the main thread. `CoInitialize`/`CoUninitialize` called per thread.

### 20.2 Teams Integration

```python
# infrastructure/teams_client.py
def send_teams_message(message, webhook_url=None):
    if not IS_WINDOWS:
        print(f"[DEV] Would send Teams: {message[:80]}")
        return
    import pyperclip, pyautogui, webbrowser
    pyautogui.FAILSAFE = True
    pyperclip.copy(message)
    webbrowser.open(f"msteams://")  # deep link
    # countdown → paste if auto_send enabled
```

### 20.3 File/Folder Operations

```python
def open_folder(path: Path):
    if IS_WINDOWS:
        import os
        os.startfile(str(path))
    else:
        print(f"[DEV] Would open folder: {path}")

def send_to_recycle_bin(path: Path):
    import send2trash
    send2trash.send2trash(str(path))
    # Works on both Windows and Linux (for dev testing)
```

### 20.4 Outlook Contacts

```python
def get_contacts() -> list[dict]:
    if not IS_WINDOWS:
        return [{"name": "Dev User", "email": "dev@example.local"}]
    import pythoncom, win32com.client
    pythoncom.CoInitialize()
    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        namespace = outlook.GetNamespace("MAPI")
        contacts_folder = namespace.GetDefaultFolder(10)  # olFolderContacts
        return [
            {"name": c.FullName, "email": c.Email1Address}
            for c in contacts_folder.Items
            if hasattr(c, "FullName")
        ]
    finally:
        pythoncom.CoUninitialize()
```

---

## 21. JsApi Bridge Contract

All methods callable from Svelte frontend via `window.pywebview.api.*`.

### 21.1 App & Events

| Method                   | Params           | Returns                               |
| ------------------------ | ---------------- | ------------------------------------- |
| `app_get_status`         | —                | App status, version, settings summary |
| `app_get_pending_events` | —                | List of queued background events      |
| `util_get_fs_years`      | —                | List of year folder names from root   |
| `util_open_url`          | `url: str`       | Opens in default browser              |
| `util_open_folder`       | `path: str`      | Opens in Windows Explorer             |
| `util_choose_folder`     | `title: str`     | OS folder dialog, returns path        |
| `util_choose_file`       | `title, filters` | OS file dialog, returns path          |
| `util_scan_refresh`      | `year: str`      | Rescans year folder, rebuilds cache   |

### 21.2 Years

| Method        | Params      | Returns                        |
| ------------- | ----------- | ------------------------------ |
| `year_list`   | —           | Existing year folders          |
| `year_create` | `year: int` | Creates year + 5 state folders |

### 21.3 Projects

| Method                | Params                   | Returns                          |
| --------------------- | ------------------------ | -------------------------------- |
| `project_list`        | `year, filters`          | Filtered project list from cache |
| `project_create`      | `data: dict`             | Creates project folder + files   |
| `project_get`         | `project_path`           | Full project metadata            |
| `project_update`      | `project_path, data`     | Update metadata fields           |
| `project_delete`      | `project_path`           | Recycle Bin via send2trash       |
| `project_rename`      | `project_path, new_name` | Rename folder + update JSON      |
| `project_open_folder` | `project_path`           | os.startfile                     |

### 21.4 CR & Drone State

| Method               | Params                                | Returns                                    |
| -------------------- | ------------------------------------- | ------------------------------------------ |
| `cr_update_link`     | `project_path, cr_link`               | Store URL, extract CR number, update state |
| `cr_update_state`    | `project_path, new_state`             | Validate + set CR state                    |
| `cr_reopen`          | `project_path`                        | REOPEN action                              |
| `drone_add`          | `project_path, data`                  | Add drone ticket                           |
| `drone_update_link`  | `project_path, subfolder, drone_link` | Store URL, extract                         |
| `drone_update_state` | `project_path, subfolder, new_state`  | Validate + set Drone state                 |
| `drone_delete`       | `project_path, subfolder`             | Remove drone ticket                        |

### 21.5 Folder Transitions

| Method                    | Params         | Returns                                     |
| ------------------------- | -------------- | ------------------------------------------- |
| `folder_move_prod_ready`  | `project_path` | Guard check + folder move                   |
| `folder_move_implemented` | `project_path` | Guard check + folder move                   |
| `folder_postpone`         | `project_path` | Confirmation required → move                |
| `folder_cancel`           | `project_path` | Confirmation required → move                |
| `folder_reopen`           | `project_path` | Confirmation required → move to UAT_PREPARE |

### 21.6 Sub Projects & Files

| Method                      | Params                         | Returns                       |
| --------------------------- | ------------------------------ | ----------------------------- |
| `subproject_list`           | `project_path`                 | List sub project folders      |
| `subproject_create`         | `project_path, name`           | Create subfolder + notes.md   |
| `subproject_rename`         | `project_path, name, new_name` | Rename                        |
| `subproject_delete`         | `project_path, name`           | Recycle Bin                   |
| `file_list`                 | `path`                         | Files in path (not recursive) |
| `file_create_from_template` | `path, template_name`          | Copy template → project       |
| `file_create_manual`        | `path, filename`               | Create empty file             |
| `file_open`                 | `filepath`                     | os.startfile                  |
| `file_delete`               | `filepath`                     | Recycle Bin                   |
| `file_rename`               | `filepath, new_name`           | Rename                        |

### 21.7 Notes

| Method                | Params                                          | Returns                                             |
| --------------------- | ----------------------------------------------- | --------------------------------------------------- |
| `notes_get`           | `project_path`                                  | Content of notes.md                                  |
| `notes_update`        | `project_path, notes`                           | Atomic write to notes.md                             |
| `get_rte_file`        | `file_path`                                     | Content + capability metadata (md/txt/html/msg)      |
| `save_rte_file`       | `file_path, content`                            | Atomic save for natively-supported formats           |
| `rte_document_open`   | `file_path`                                     | Tiptap JSON source + revision + export state (docx)  |
| `rte_document_save`   | `file_path, {content, base_revision, reason}`   | New revision; `RTE_REVISION_STALE` on conflict       |
| `rte_image_save`      | `file_path, data_b64`                           | `{asset_id, src, rel_src, data_uri}`                 |
| `rte_asset_read`      | `file_path, src`                                | `{data_uri}` (traversal-guarded)                     |
| `rte_export_request`  | `file_path`                                     | Queue background DOCX export (latest revision wins)  |
| `rte_export_status`   | `file_path`                                     | `{state, revision, last_exported_revision, …}`       |

### 21.8 Report

| Method              | Params                 | Returns                       |
| ------------------- | ---------------------- | ----------------------------- |
| `report_get_data`   | `filters: dict`        | Filtered project + state data |
| `report_export_csv` | `filters, output_path` | Write CSV, return success     |

### 21.9 Second Brain

| Method                | Params                           | Returns                    |
| --------------------- | -------------------------------- | -------------------------- |
| `brain_get_tree`      | `path`                           | Folder/file tree structure |
| `brain_search`        | `query, date_filter, sort`       | Search results list        |
| `brain_create_folder` | `parent_path, name`              | Create folder              |
| `brain_create_file`   | `parent_path, filename, content` | Create file                |
| `brain_read_file`     | `filepath`                       | File content               |
| `brain_save_file`     | `filepath, content`              | Atomic write               |
| `brain_delete`        | `path`                           | Recycle Bin                |
| `brain_rename`        | `path, new_name`                 | Rename                     |
| `brain_pin`           | `filepath, pinned: bool`         | Update pin metadata        |
| `brain_favorite`      | `filepath, favorite: bool`       | Update favorite metadata   |

### 21.10 Link Bank

| Method                  | Params                     | Returns                   |
| ----------------------- | -------------------------- | ------------------------- |
| `link_get_all`          | —                          | All categories + links    |
| `link_category_create`  | `name`                     | New category              |
| `link_category_rename`  | `category_id, new_name`    | Rename                    |
| `link_category_archive` | `category_id`              | Archive                   |
| `link_create`           | `data`                     | New link                  |
| `link_update`           | `link_id, data`            | Update link               |
| `link_archive`          | `link_id`                  | Soft delete               |
| `link_restore`          | `link_id`                  | Restore from archive      |
| `link_search`           | `query, date_filter, sort` | Search results            |
| `link_export`           | `output_path, format`      | JSON or CSV export        |
| `link_import`           | `file_path`                | Import + validate + merge |

### 21.11 Notifications

| Method                     | Params            | Returns              |
| -------------------------- | ----------------- | -------------------- |
| `notification_list`        | `limit`           | Recent notifications |
| `notification_dismiss`     | `notification_id` | Dismiss one          |
| `notification_dismiss_all` | —                 | Dismiss all          |

### 21.12 Settings

| Method                      | Params    | Returns                        |
| --------------------------- | --------- | ------------------------------ |
| `settings_get`              | —         | Full settings.json content     |
| `settings_save`             | `data`    | Validate + write settings.json |
| `settings_restore_defaults` | `section` | Reset section to defaults      |

### 21.13 Automations

| Method                          | Params                              | Returns                            |
| ------------------------------- | ----------------------------------- | ---------------------------------- |
| `outlook_get_categories`        | —                                   | Email categories config            |
| `outlook_save_category`         | `data`                              | Save/update category               |
| `outlook_send_email`            | `category_code, project_path, mode` | Create draft or send               |
| `outlook_get_downloaded_emails` | —                                   | Downloaded email list              |
| `outlook_get_contacts`          | —                                   | Outlook contacts (Windows-guarded) |
| `teams_get_automations`         | —                                   | Teams automation list              |
| `teams_save_automation`         | `data`                              | Save/update automation             |
| `teams_send_message`            | `automation_id, project_path`       | Deep link + paste                  |
| `scheduler_list`                | —                                   | All scheduler entries              |
| `scheduler_create`              | `data`                              | Create + register APScheduler job  |
| `scheduler_update`              | `entry_id, data`                    | Update + reschedule                |
| `scheduler_delete`              | `entry_id`                          | Remove + cancel APScheduler job    |
| `scheduler_toggle`              | `entry_id, enabled`                 | Pause/resume job                   |
| `rules_list`                    | —                                   | All rules                          |
| `rules_create`                  | `data`                              | Create rule                        |
| `rules_update`                  | `rule_id, data`                     | Update rule                        |
| `rules_delete`                  | `rule_id`                           | Delete rule                        |
| `rules_toggle`                  | `rule_id, enabled`                  | Enable/disable rule                |
| `rules_get_logs`                | `rule_id, limit`                    | Execution log entries              |

---

## 22. SQLite Cache Schema

SQLite is a **rebuildable local cache**. If the database file is deleted or corrupt, the app rebuilds from filesystem scan. SQLite is never the authoritative source of data.

Database file: `%APPDATA%\ProjectTrackerDBS\cache.db`

### 22.1 `project_index`

Rebuilt on every full scan. Used for fast dashboard queries and report filtering.

```sql
CREATE TABLE project_index (
    path TEXT PRIMARY KEY,          -- absolute project folder path
    name TEXT NOT NULL,
    year TEXT NOT NULL,
    folder_state TEXT NOT NULL,     -- UAT_PREPARE | PROD_READY | IMPLEMENTED | POSTPONED | CANCELED
    cr_link TEXT,
    cr_number TEXT,                 -- extracted display identifier
    cr_state TEXT,
    cr_pending_approval_at TEXT,    -- ISO8601
    start_datetime TEXT,
    end_datetime TEXT,
    drone_tickets_json TEXT,        -- JSON array
    t10_status TEXT,               -- PASS | FAIL | UNKNOWN
    updated_at TEXT,
    scanned_at TEXT DEFAULT (datetime('now'))
);
```

### 22.2 `notifications`

```sql
CREATE TABLE notifications (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    project_path TEXT,
    dismissed INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);
```

### 22.3 `scheduler_entries`

```sql
CREATE TABLE scheduler_entries (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    notes TEXT,
    schedule_type TEXT NOT NULL,   -- one_time | daily | weekly | monthly | cron
    schedule_config TEXT,          -- JSON
    project_filter TEXT,
    state_filter TEXT,
    channels TEXT NOT NULL,        -- JSON array: ["in_app", "outlook_email", "teams"]
    channel_configs TEXT,          -- JSON
    enabled INTEGER DEFAULT 1,
    status TEXT DEFAULT 'active',  -- active | paused | completed
    last_triggered_at TEXT,
    next_trigger_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
```

### 22.4 `automation_rule_logs`

```sql
CREATE TABLE automation_rule_logs (
    id TEXT PRIMARY KEY,
    rule_id TEXT NOT NULL,
    rule_name TEXT,
    trigger_type TEXT,
    conditions_passed INTEGER,
    actions_executed TEXT,         -- JSON array
    success INTEGER DEFAULT 1,
    error_message TEXT,
    timestamp TEXT DEFAULT (datetime('now'))
);
```

### 22.5 `email_jobs`

```sql
CREATE TABLE email_jobs (
    id TEXT PRIMARY KEY,
    rule_id TEXT,
    cr_number TEXT,
    project_path TEXT,
    started_at TEXT,
    completed_at TEXT,
    status TEXT DEFAULT 'active',  -- active | completed | timeout | stopped
    emails_downloaded INTEGER DEFAULT 0,
    attachments_saved INTEGER DEFAULT 0,
    notes TEXT
);
```

### 22.6 Rebuild Trigger

SQLite is rebuilt from filesystem scan when:

- App starts and `project_index` table is empty.
- User clicks Refresh.
- `cache.db` is missing or corrupt (detected on `pragma integrity_check`).

---

## 23. File Operations & Data Safety

### 23.1 Atomic Write Pattern

```python
# All JSON writes
import tempfile, shutil
def atomic_write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)  # atomic on most OS/filesystems
```

### 23.2 Delete Safety

```python
# Always Recycle Bin, never os.remove
import send2trash
send2trash.send2trash(str(path))
```

Show confirmation before every delete. Disable delete in `PROD_READY` and `IMPLEMENTED` states.

### 23.3 Error Handling Rules

| Error                              | Behavior                                                          |
| ---------------------------------- | ----------------------------------------------------------------- |
| Corrupt `project_data.json`        | Skip project + warning notification; do not crash                 |
| Missing `project_data.json`        | Show project with defaults + warning                              |
| Missing subfolder for Drone ticket | Show mapping warning inline; do not crash                         |
| JSON write failure                 | Retry once → show error toast                                     |
| OS permission denied               | User-readable message; do not crash                               |
| Windows COM unavailable            | Graceful fallback message; show “Windows only” label              |
| SQLite corrupt                     | Rebuild from filesystem scan                                      |
| Year >2 ahead                      | Confirmation warning, not hard block                              |
| T-10 violation                     | Block auto move + notification; manual override with confirmation |

### 23.4 Filesystem Change Detection

MVP approach:

- **Manual Refresh button** (always available).
- **Auto refresh polling**: if `auto_refresh_interval_seconds > 0` in settings → scan + rebuild cache at that interval using APScheduler.

Optional (requires confirmation before adding dependency):

- **watchdog** file system observer for near-realtime change detection.

---

## 24. Packaging & Deployment

### 24.1 Build Steps

```bash
# Step 1: Build Svelte frontend
cd frontend
npm run build
# Output: ../web/static/

# Step 2: PyInstaller (Windows only)
pyinstaller \
  --name "ProjectTrackerDBS" \
  --onedir \
  --windowed \
  --icon=assets/icon.ico \
  --add-data "web/static;web/static" \
  --add-data "assets;assets" \
  app_web.py
```

### 24.2 Rules

- PyInstaller build only from Windows.
- Do not attempt Windows build from Linux.
- `web/static/` (Vite build output) must be included in PyInstaller `--add-data`.
- `assets/` must be included (icon, email templates).
- WebView2 runtime must be present on target Windows machine (bundled or prerequisite installer).
- Verify WebView2, Outlook COM, Teams integration, send2trash, os.startfile, and pywebview loading manually on Windows.

### 24.3 AppData on Fresh Install

On first run:

1. Create `%APPDATA%\ProjectTrackerDBS\` directory if not exists.
1. Create default `settings.json`.
1. Create default `link_bank.json`.
1. Create `SecondBrain\` directory.
1. Create `cache.db` SQLite database.
1. Show First Run Setup dialog: choose root folder.

---

## 25. Implementation Phases

Do not move to the next phase until the current phase is verified.

### Phase 0 — PRD Lock

- User approves this PRD.
- This file replaces all previous PRD versions.

### Phase A — Core Domain

Build: `core/enums.py`, `core/models.py`, `core/state_machine.py`, `core/rules.py`, `core/exceptions.py`

Cover:

- All enum values (CRState, DroneState, FolderState).
- State transition guards (pure Python, no I/O).
- T-10 rule calculation.
- Folder name validator.
- CR/Drone link extractor.
- Organizational folder exclusion logic.
- History entry model.

Verify: unit tests pass on Linux. Zero Windows API imports in `core/`.

### Phase B — Infrastructure & Stores

Build: `infrastructure/filesystem.py`, `metadata_store.py`, `settings_store.py`, `link_bank_store.py`, `cache_db.py`

Cover:

- AppData path resolution (Windows + Linux fallback).
- Atomic JSON read/write.
- SQLite schema creation + rebuild logic.
- Filesystem scanner (scan year → state folders → projects → sub projects).
- Folder create/rename/delete (send2trash).
- `outlook_client.py` and `teams_client.py` stubs (IS_WINDOWS guarded).

Verify: unit tests for stores and scanner with temp filesystem fixtures.

### Phase C — Services & Event Queue

Build: all `services/`, `web/event_queue.py`, `web/js_api.py`

Cover:

- Project service orchestrates state machine + stores.
- Scanner service populates SQLite cache.
- Automation service evaluates rules.
- Scheduler service manages APScheduler jobs.
- Second Brain service: search index + file ops.
- Report service: filter logic + CSV writer.
- All JsApi bridge methods (returning standard BridgeResponse).
- Event queue push/drain.

Verify: unit tests for services using mocked infrastructure. Bridge response shape tests.

### Phase D — Svelte Frontend Shell

Build: Svelte app structure, app shell, sidebar, header, notification panel, router.

Cover:

- `app.html` + Vite config.
- Svelte stores: `projectsStore`, `settingsStore`, `notificationsStore`, `currentPageStore`.
- Sidebar component: nav items, collapse/expand, notification panel.
- Header component: title, datetime, actions.
- Event polling: `setInterval(1500)` → `get_pending_events()`.
- TypeScript types mirroring Python models.
- `window.pywebview.api.*` typed wrappers.

Verify: browser preview on Linux matches prototype visual. pywebview preview where safe on Windows.

### Phase E — Dashboard & Project Details

Build: Dashboard page, Project Details (NEW + SHOW_EDIT modes).

Cover:

- Year selector + Add Year.
- KPI cards + state filter tabs.
- Project table: columns, inline editing, row actions.
- Search + debounce.
- Add Project flow.
- CR/Drone link paste + extract + state change flows.
- Auto PROD_READY trigger on state change.
- Sub project table + Drone ticket management.
- File management.
- Notes autosave (marked.js for preview).
- History panel.
- REOPEN flow.
- All locking rules applied.

Verify: fixture-based + manual Windows testing.

### Phase F — Second Brain, Link Bank, Report

Build: Second Brain Notes tab, Link Bank tab, Report page.

Cover:

- Notes tree: Pinned, Favorites, Second Brain Notes, Project Documents.
- Notes search index: in-memory precomputed, debounced, date-filterable.
- Notes CRUD: create, read, edit, delete (Recycle Bin), rename, pin, favorite.
- markdown.js integration for preview.
- Link Bank: category CRUD, link CRUD, search, archive/restore, import/export.
- Report: filters, summary rows, table, CSV export with file dialog.

Verify: search behavior, persistence, CSV output format.

### Phase G — Automations

Build: Outlook tab, Teams tab, Scheduler tab, Rules Engine tab.

Cover:

- Email Template Dialog (full Outlook category editor).
- Outlook COM draft/send (Windows manual test).
- Downloaded Emails dialog.
- Teams Automation Dialog (rules, message, mode).
- Teams deep link + paste (Windows manual test).
- Scheduler: APScheduler jobs, alarm entries, all 3 channels.
- Rules Engine: trigger→condition→action editor, execution logs.

Verify: all Windows integrations manual-tested on Windows 10/11.

### Phase H — Settings & Packaging

Build: Settings page, Help Center, PyInstaller config.

Cover:

- Settings form: General, Behavior, Paths.
- Help Center: search + topic cards.
- Settings save/validate/persist.
- First Run Setup dialog.
- PyInstaller build on Windows including `web/static/` and `assets/`.
- Fresh Windows machine installation test.

Verify: app installs and runs on clean Windows machine.

---

## 26. Acceptance Criteria

### 26.1 Core Data

| #   | Criteria                                                                                    |
| --- | ------------------------------------------------------------------------------------------- |
| 1   | `project_state` never appears in `project_data.json`.                                       |
| 2   | Folder path is the sole source of project year and folder state.                            |
| 3   | Corrupt JSON never crashes the app.                                                         |
| 4   | All JSON writes are atomic (temp-file-then-replace).                                        |
| 5   | Delete uses Recycle Bin only (`send2trash`).                                                |
| 6   | `cr_pending_approval_at` is set on first PENDING APPROVAL transition and never overwritten. |
| 7   | T-10 uses `cr_pending_approval_at` for calculation.                                         |
| 8   | Missing subfolder mapping for Drone ticket shows warning without crash.                     |
| 9   | SQLite deletion triggers rebuild from filesystem without data loss.                         |
| 10  | Settings persist across app restarts under app data folder.                                 |

### 26.2 State Machine

| #   | Criteria                                                                                   |
| --- | ------------------------------------------------------------------------------------------ |
| 1   | `UAT_PREPARE → PROD_READY` auto-triggers when CR+all Drones = APPROVED and T-10 passes.    |
| 2   | T-10 failure blocks auto move + notification shown; manual override requires confirmation. |
| 3   | `IN-PROGRESS` is set automatically by scheduler; not available in user dropdown.           |
| 4   | `FINISHED` is settable only from `IN-PROGRESS`.                                            |
| 5   | `PROD_READY → IMPLEMENTED` auto-triggers when CR+all Drones = FINISHED.                    |
| 6   | REOPEN moves folder to `UAT_PREPARE` and sets CR to `PENDING SUBMISSION`.                  |
| 7   | POSTPONED/CANCELED both get their own separate project folders.                            |
| 8   | `PROD_READY` partial lock prevents rename, delete, and destructive file ops.               |
| 9   | `IMPLEMENTED` fully locks all editing, deleting, and state changes.                        |
| 10  | Drone state `IN-PROGRESS` is auto only; not selectable by user.                            |

### 26.3 User Interface

| #   | Criteria                                                                        |
| --- | ------------------------------------------------------------------------------- |
| 1   | Production UI uses pywebview + Svelte + TypeScript + Vite + Tailwind (no PyQt). |
| 2   | Sidebar/header are visually consistent across all 6 pages.                      |
| 3   | Notification panel persists and is not recreated during page navigation.        |
| 4   | Dashboard year dropdown shows only existing year folders.                       |
| 5   | CR/Drone link paste displays extracted identifier; click opens default browser. |
| 6   | Inline CR/Drone editing in dashboard table works for bulk paste workflows.      |
| 7   | Empty-area click clears table/tree/list selection.                              |
| 8   | Search inputs are debounced and provide visible feedback.                       |
| 9   | All content panels scroll internally without page-level overflow.               |
| 10  | UI is usable on both laptop (1366×768) and external monitor (1920×1080).        |

### 26.4 Features

| #   | Criteria                                                                        |
| --- | ------------------------------------------------------------------------------- |
| 1   | Dashboard scans filesystem and displays projects with correct states.           |
| 2   | Notes autosave to `notes.md` with 1000ms debounce and status indicator.         |
| 3   | Second Brain file tree shows both Second Brain Notes and Project Documents.     |
| 4   | Second Brain search returns results across notes, filenames, content, and tags. |
| 5   | Link Bank CRUD persists in `link_bank.json`.                                    |
| 6   | Report CSV export respects active filters and is Excel-compatible.              |
| 7   | Outlook email creates draft by default; send only after confirmation.           |
| 8   | Teams automation defaults to paste-only mode.                                   |
| 9   | Scheduler entries persist across restarts and trigger at configured times.      |
| 10  | Rules Engine executes ordered actions on condition match.                       |

### 26.5 Platform & Safety

| #   | Criteria                                                                   |
| --- | -------------------------------------------------------------------------- |
| 1   | Windows-only integrations fail gracefully on Linux with log/stub behavior. |
| 2   | PyInstaller build includes `web/static/` and `assets/`.                    |
| 3   | App runs on clean Windows 10/11 without internet connection.               |
| 4   | No PDF library added.                                                      |
| 5   | No external DB or cloud service used.                                      |

---

## 27. Architecture Decision Records (ADRs)

> Archived to `_docs/_archive/PRD_history.md`. ADR-001 through ADR-005 (Svelte, SQLite cache, APScheduler, Event Queue, Tauri future) — all status Locked/Future.

---

## 28. Open Calibration Items

These are runtime-calibration items confirmed during Windows manual testing. They do not change product scope — only specific values/patterns.

| #   | Item                                                               | When to Calibrate    |
| --- | ------------------------------------------------------------------ | -------------------- |
| 1   | CR number extraction regex from real ITSM URL pattern              | Phase E Windows test |
| 2   | Drone ticket extraction regex from real Drone URL pattern          | Phase E Windows test |
| 3   | Outlook reply subject pattern for Rules Engine matching            | Phase G Windows test |
| 4   | Teams deep link format for target group/channel                    | Phase G Windows test |
| 5   | Outlook COM contacts folder structure (different Outlook versions) | Phase G Windows test |
| 6   | Whether notification history in-memory is sufficient for MVP       | Phase H review       |
| 7   | Whether watchdog is needed or auto-refresh polling is sufficient   | Phase E review       |
| 8   | Whether Link Bank import should support CSV in addition to JSON    | Phase F review       |

---

## 29. Implementation Handoff Rules

1. This PRD is the single source of truth. `README.md` and previous `PRD.md` versions are superseded.
1. Implementation follows the phase order in Section 25. Do not skip verification gates.
1. Changes to product behavior, state transitions, or data models must be reflected in this PRD first, then implemented.
1. Do not add dependencies without user confirmation (see Section 3.3 baseline).
1. Do not run Windows-only integrations on Linux.
1. Do not add speculative features beyond what is documented here.
1. If a UI prototype file and this PRD disagree, this PRD is authoritative.
1. Every change is surgical: touch only what the current phase requires.
1. PyQt6 prototype files stay in a reference directory and are never imported by production code.
