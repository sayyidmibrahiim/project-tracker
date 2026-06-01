# Project Tracker DBS — Product Requirements Document

> **Version:** 2.0.0  
> **Last Updated:** 2026-05-17  
> **Author:** Sayyid M. Ibrahim  
> **Status:** Single Source of Truth  
> **Supersedes:** `README.md` and `DESIGN.md`

---

## 1. Purpose

Project Tracker DBS is a Windows desktop application for tracking DBS Change Request (CR) deployment work from preparation through production implementation.

The app is for a single deployment engineer workflow. It must prioritize local-first reliability, fast manual tracking, safe filesystem operations, and automation around Outlook, Teams, project notes, and report export.

`PRD.md` is the only product/source-of-truth document. Do not recreate or depend on `README.md` or `DESIGN.md` for requirements.

---

## 2. Non-Negotiable Constraints

### 2.1 Product Constraints

- All project data stays local.
- No external database.
- No cloud backend.
- No SQLite in MVP.
- Local filesystem is source of truth for project existence, project year, and project folder state.
- `project_data.json` stores metadata only.
- `project_state` must never be stored in JSON.
- Hard delete is forbidden; delete must use Windows Recycle Bin through `send2trash`.
- Internal browser is canceled; all web links open in default OS browser.
- PDF export is canceled; export is CSV only.
- Do not add new dependencies without user confirmation.

### 2.2 Development vs Target Environment

| Area                 | Dev Machine     | Target Machine   |
| -------------------- | --------------- | ---------------- |
| OS                   | Pop!\_OS Linux  | Windows 10+      |
| Shell                | zsh             | PowerShell / CMD |
| Runtime target       | Unit tests only | Full app         |
| Windows integrations | Not executable  | Required         |

Rules:

- Do not run the deprecated PyQt app directly on Linux.
- Do not run `python main.py` on Linux for app testing unless launching the pywebview shell for guarded preview work.
- Unit tests on Linux may cover non-Windows logic: core models, state machines, rules, metadata parsing, settings serialization, scanner logic, and pywebview bridge code that does not require Windows integrations.
- HTML/Tailwind screens may be previewed directly in a browser on Linux. Outlook COM, Teams automation, `os.startfile`, `pyautogui`, `send2trash`, pywebview WebView2 rendering, and PyInstaller Windows build must be manually tested on Windows.
- PyInstaller Windows build must not be attempted from Linux.
- All code paths must use `pathlib.Path`, not string concatenation.
- Windows-specific code should target Windows correctly; do not add Linux fallback behavior unless explicitly requested.
- Paths stored in `settings.json` may use Windows format such as `D:\\WORK\\CR`; do not normalize them into Linux paths when reading/writing settings.
- Do not hardcode timezone, username, or local filesystem path.

---

## 3. Architecture

### 3.1 Application Type

- Python 3.12+ desktop app.
- pywebview shell with HTML/Tailwind CDN frontend.
- Modular monolith.
- Local filesystem + JSON persistence.
- Outlook automation through `win32com.client`.
- Teams desktop/web automation through deep link + clipboard + `pyautogui`.

### 3.2 Layering

```text
UI Layer
  pywebview window + HTML/Tailwind screens + JS bridge

Services Layer
  Project orchestration, scanning, automation, reports

Core Layer
  Models, enums, rules, state machines

Infrastructure Layer
  Filesystem, JSON stores, Outlook, Teams, watchdog
```

Dependency rule:

```text
UI → Services → Core
UI → Infrastructure only through service boundaries when practical
Services → Core + Infrastructure
Core imports no UI, services, or infrastructure
```

### 3.3 Canonical Package Direction

```text
project_tracker/
├── main.py
├── app.py
├── core/
│   ├── enums.py
│   ├── models.py
│   ├── state_machine.py
│   ├── rules.py
│   └── exceptions.py
├── services/
│   ├── project_service.py
│   ├── scanner_service.py
│   ├── email_service.py
│   ├── teams_service.py
│   ├── email_download_service.py
│   ├── second_brain_service.py
│   ├── report_service.py
│   └── notification_service.py
├── infrastructure/
│   ├── metadata_store.py
│   ├── settings_store.py
│   ├── link_bank_store.py
│   ├── filesystem.py
│   ├── outlook_integration.py
│   ├── teams_integration.py
│   └── watchdog_service.py
├── ui/
│   ├── main_window.py
│   ├── dashboard.py
│   ├── project_detail.py
│   ├── report.py
│   ├── second_brain.py
│   ├── automations.py
│   ├── settings.py
│   ├── dialogs/
│   └── widgets/
└── assets/
    ├── email_templates/
    ├── cmd_templates/
    └── icon.ico
```

This layout is a direction, not permission for unrelated refactors. Implementation must be phased and surgical.

---

## 4. Filesystem Model

### 4.1 Root Folder

User chooses one root folder in Settings or first-run setup.

Example:

```text
D:\WORK\CR
```

Root folder contains year folders only.

### 4.2 Year Folder

Project year is derived only from year folder name.

```text
{ROOT_FOLDER}\{YEAR}\
```

Examples:

```text
D:\WORK\CR\2026\
D:\WORK\CR\2027\
```

Rules:

- Dashboard year dropdown shows only year folders that already exist under root folder.
- Adding a year creates year folder and all 4 project state folders.
- Default year suggestion from Add Year is next year.
- If selected year is more than 2 years ahead of current local year, show confirmation warning before creating folders.
- `start_datetime` and `end_datetime` do not determine year folder and must not automatically move a project across years.

### 4.3 Project State Folders

Project folder state is derived from parent state folder only.

```text
{ROOT_FOLDER}\{YEAR}\UAT_PREPARE\{project_name}\
{ROOT_FOLDER}\{YEAR}\PROD_READY\{project_name}\
{ROOT_FOLDER}\{YEAR}\IMPLEMENTED\{project_name}\
{ROOT_FOLDER}\{YEAR}\POSTPONED\{project_name}\
```

Required state folders per year:

| Folder        | Meaning                                |
| ------------- | -------------------------------------- |
| `UAT_PREPARE` | Active preparation/editing state       |
| `PROD_READY`  | Ready for production; partially locked |
| `IMPLEMENTED` | Completed/archived; locked             |
| `POSTPONED`   | Paused project; editable and resumable |

### 4.4 Project Folder

One main project folder equals one CR number.

```text
{ROOT_FOLDER}\{YEAR}\{STATE}\{project_name}\
```

Required files inside project folder:

```text
project_data.json
notes.md
```

Template-generated files may also exist, for example:

```text
{CR_NUMBER}_uat_signoff.docx
cmd_onboard.md
cmd_rollback.md
```

### 4.5 Sub Project Folder

A sub project is a subfolder inside a main project folder that represents a script/package/setting/component change related to the same main CR.

Rules:

- Main project and all sub projects share the same CR number.
- Main project may have its own Drone ticket.
- Each sub project may have its own Drone ticket.
- Sub project does not have independent CR state.
- Sub project does not have independent project folder state.
- Sub project is mapped to Drone ticket by `DroneTicket.subfolder_name`.
- Sub project can have its own files and `notes.md`.

Example:

```text
D:\WORK\CR\2026\UAT_PREPARE\PYTHON_A\
├── project_data.json
├── notes.md
├── script_change\
│   ├── notes.md
│   └── update_query.sql
└── package_change\
    ├── notes.md
    └── requirements_change.txt
```

### 4.6 Organizational Folders

Some folders inside a project are organizational and must not be treated as sub projects.

Case-insensitive exclusion list:

```text
doc, docs, document, documents,
bak, backup, before, after,
script, scripts, cicd,
log, logs, temp, tmp, archive
```

Folders matching this list are shown as normal folders/files, not sub projects.

### 4.7 Folder Naming Rules

Project and sub project names must be valid Windows folder names.

Reject:

```text
\ / : * ? " < > |
```

Also reject:

- Empty names.
- Names with trailing space.
- Names with trailing dot.
- Reserved Windows device names: `CON`, `PRN`, `AUX`, `NUL`, `COM1`-`COM9`, `LPT1`-`LPT9`.
- Duplicate folder names in target parent folder.

UI must validate in real time and disable Save while invalid.

---

## 5. Metadata Model

### 5.1 `project_data.json`

Stored in main project folder only.

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
      "drone_state_updated_at": "2026-01-05T10:00:00+07:00"
    },
    {
      "subfolder_name": "script_change",
      "drone_link": "https://drone.example.local/deployment/D-SSIDBI-160",
      "drone_state": "PENDING APPROVAL",
      "drone_state_updated_at": "2026-01-05T11:00:00+07:00"
    }
  ],
  "notes": "Legacy short note. notes.md is primary note storage.",
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
      "user": "sayyid"
    }
  ],
  "created_at": "2026-01-05T09:00:00+07:00",
  "updated_at": "2026-01-15T20:40:00+07:00"
}
```

Rules:

- `project_state` must not exist.
- `project_name` should match folder name after rename.
- `cr_state_updated_at` updates on every CR state change.
- `cr_pending_approval_at` records first time CR reaches `PENDING APPROVAL`; used for T-10.
- `cr_pending_approval_at` should not be overwritten by later CR states.
- If old data has no `cr_pending_approval_at`, use fallback logic in warnings and ask user to repair if T-10 cannot be proven.
- Each `DroneTicket` may map to main project with `subfolder_name = null` or to sub project with `subfolder_name = "folder_name"`.
- If `subfolder_name` points to a missing folder, show warning but do not crash.
- `notes` is legacy/short-note field; primary notes live in `notes.md`.
- `history` is unlimited and read-only in UI.
- Missing fields in known schema are defaulted.
- Unknown schema must skip/warn without crashing.
- Corrupt JSON must skip/warn without crashing.

### 5.2 Default Metadata

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
  "notes": "",
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

### 5.3 Datetime Policy

- Store datetimes as ISO 8601 timezone-aware strings.
- Use local OS timezone dynamically for `now`.
- Do not hardcode WIB, UTC+7, or any fixed offset.
- Display format is configurable in Settings.

### 5.4 History Entry

Every meaningful action appends history.

Fields:

| Field       | Description                                             |
| ----------- | ------------------------------------------------------- |
| `timestamp` | Local OS timezone-aware timestamp                       |
| `action`    | Machine-friendly action name                            |
| `detail`    | Human-readable activity detail                          |
| `user`      | `settings.display_name` if set; otherwise Windows login |

History is read-only and sorted newest-first in UI.

---

## 6. App Config Model

All app-level config is stored under:

```text
%APPDATA%\ProjectTrackerDBS\
```

### 6.1 Required App Config Files/Folders

```text
%APPDATA%\ProjectTrackerDBS\settings.json
%APPDATA%\ProjectTrackerDBS\link_bank.json
%APPDATA%\ProjectTrackerDBS\SecondBrain\
```

### 6.2 `settings.json`

```json
{
  "root_folder": "D:\\WORK\\CR",
  "display_name": "",
  "language": "en",
  "datetime_format": "ddd, dd MMM yyyy HH:mm",
  "t10_threshold_days": 10,
  "auto_refresh_interval": "off",
  "theme": "dark",
  "startup_behavior": "current_year_dashboard",
  "second_brain_folder": "%APPDATA%\\ProjectTrackerDBS\\SecondBrain",
  "file_template_folder": "",
  "automation_rules": [
    {
      "name": "Require approved CR",
      "description": "Reusable condition group example",
      "warning_only": false,
      "conditions": [
        {
          "type": "cr_state",
          "operator": "equals",
          "value": "APPROVED"
        }
      ]
    }
  ],
  "email": {
    "global_mode": "draft",
    "template_folder_path": "",
    "download_poll_interval_seconds": 10,
    "download_timeout_hours": 3,
    "categories": {
      "ACK_UAT": {
        "to": "",
        "cc": "",
        "subject_template": "",
        "body_template": "",
        "attachment_template_file": "",
        "mode_override": null,
        "conditions": []
      },
      "ACK_SOP": {
        "to": "",
        "cc": "",
        "subject_template": "",
        "body_template": "",
        "attachment_template_file": "",
        "mode_override": null,
        "conditions": []
      },
      "APRVL_CR": {
        "to": "",
        "cc": "",
        "subject_template": "",
        "body_template": "",
        "attachment_template_file": "",
        "mode_override": null,
        "conditions": []
      },
      "APRVL_SOP": {
        "to": "",
        "cc": "",
        "subject_template": "",
        "body_template": "",
        "attachment_template_file": "",
        "mode_override": null,
        "conditions": []
      }
    }
  },
  "teams": {
    "countdown_seconds": 3,
    "teams_auto_send": false,
    "automations": [
      {
        "name": "Default approval request",
        "target_email": "",
        "target_group": "",
        "mentions": [],
        "message_template": "Hi, mohon approval untuk deployment {PROJECT_NAME} dengan Drone ticket {DRONE_TICKET}.",
        "attachment_paths": [],
        "conditions": []
      }
    ]
  }
}
```

Settings rule: if a behavior can reasonably be dynamic without breaking safety, put it in Settings.

Settings UI must expose at minimum:

- Root folder.
- Display name.
- Language.
- Datetime format.
- T-10 threshold days.
- Auto-refresh setting.
- Theme.
- Startup behavior.
- Second Brain folder.
- File template folder.
- Email global mode.
- Email template folder.
- Email poll interval and timeout.
- Email category templates and conditions.
- Automation Rules condition groups.
- Teams global countdown.
- Teams auto-send toggle.
- Teams automation entries.

Settings changes should apply immediately when safe. Otherwise show restart-required message.

Settings UI must include per-section Restore Defaults with confirmation before reset.

### 6.3 `link_bank.json`

Stored at `%APPDATA%\ProjectTrackerDBS\link_bank.json`.

```json
{
  "categories": ["CR & ITSM Tools", "Drone & Deployment", "Personal"],
  "links": [
    {
      "name": "CR Portal",
      "url": "https://example.local/",
      "notes": "Work support link",
      "category": "CR & ITSM Tools"
    }
  ]
}
```

Rules:

- Link Bank belongs inside Second Brain, not as separate navigation item.
- Links open in default OS browser.
- Search must be case-insensitive over name, URL, and notes.
- Categories are user-editable.

---

## 7. State Machines

### 7.1 CR State Values

```text
PENDING SUBMISSION
PENDING APPROVAL
APPROVED
IN-PROGRESS
FINISHED
CANCELED
REOPEN
```

### 7.2 CR State Flow

Normal flow:

```text
PENDING SUBMISSION → PENDING APPROVAL → APPROVED → IN-PROGRESS → FINISHED
```

Special flows:

```text
PENDING APPROVAL → REOPEN → PENDING SUBMISSION
APPROVED          → REOPEN → PENDING SUBMISSION
Any non-FINISHED/non-IMPLEMENTED eligible state → CANCELED → POSTPONED folder
```

Rules:

- CR cannot change state if `cr_link` is empty, except while creating initial empty project metadata.
- `PENDING SUBMISSION` is default.
- User may manually set `PENDING APPROVAL` and `APPROVED` if guards pass.
- `IN-PROGRESS` is automatic only.
- User may manually set `FINISHED` only from `IN-PROGRESS`.
- `REOPEN` is selectable only from `APPROVED` or `PENDING APPROVAL`.
- REOPEN moves project folder to `UAT_PREPARE`.
- After REOPEN event, the CR returns to `PENDING SUBMISSION` as next working state.
- REOPEN must still be recorded in history as event/action.
- If implementation needs to display `REOPEN` briefly, it must not leave project permanently stuck in `REOPEN`; the actionable state after reopen is `PENDING SUBMISSION`.
- `CANCELED` moves project folder to `POSTPONED`.
- Every CR state change updates `cr_state_updated_at`.
- First transition into `PENDING APPROVAL` sets `cr_pending_approval_at` if not already set.

### 7.3 Drone State Values

```text
UAT
PENDING APPROVAL
APPROVED
IN-PROGRESS
FINISHED
CANCELED
```

### 7.4 Drone State Flow

```text
UAT → PENDING APPROVAL → APPROVED → IN-PROGRESS → FINISHED
```

Special flow:

```text
Any active drone state → CANCELED
```

Rules:

- Drone cannot change state if `drone_link` is empty.
- `UAT` is default.
- User may manually set `PENDING APPROVAL` and `APPROVED` if guards pass.
- `IN-PROGRESS` is automatic only.
- User may manually set `FINISHED` only from `IN-PROGRESS`.
- Every drone state change updates that ticket's `drone_state_updated_at`.

### 7.5 Project Folder State Transitions

#### 7.5.1 `UAT_PREPARE → PROD_READY`

All guards must pass:

- `start_datetime` exists.
- `end_datetime` exists.
- `end_datetime > start_datetime`.
- `start_datetime` is not backdated at transition time.
- `end_datetime` is not backdated at transition time.
- `cr_link` exists.
- `cr_state = APPROVED`.
- If drone tickets exist, all required drone tickets are `APPROVED`.
- T-10 rule passes.

If any guard fails, show a modal listing each failed guard and block transition.

#### 7.5.2 `PROD_READY → IMPLEMENTED`

All guards must pass:

- Local OS `now` is inside `[start_datetime, end_datetime]`.
- `cr_state = FINISHED`.
- If drone tickets exist, all required drone tickets are `FINISHED`.

`IMPLEMENTED` is locked after transition.

#### 7.5.3 Any Eligible State → `POSTPONED`

Rules:

- Allowed from `UAT_PREPARE`.
- Allowed from `PROD_READY` only through explicit Postpone/Cancel action with confirmation.
- Not allowed from `IMPLEMENTED`.
- Resume from `POSTPONED` always moves project back to `UAT_PREPARE`.
- CR `CANCELED` moves folder to `POSTPONED`.

### 7.6 Locking Rules

| Folder State  | Edit Metadata | Edit Files | Add Notes | Rename | Delete | Change CR/Drone State |       Move Folder State |
| ------------- | ------------: | ---------: | --------: | -----: | -----: | --------------------: | ----------------------: |
| `UAT_PREPARE` |           Yes |        Yes |       Yes |    Yes |    Yes |                   Yes |                     Yes |
| `POSTPONED`   |           Yes |        Yes |       Yes |    Yes |    Yes |                   Yes | Resume to `UAT_PREPARE` |
| `PROD_READY`  |       Partial |    Partial |       Yes |     No |     No |               Limited | Implement/Postpone only |
| `IMPLEMENTED` |            No |         No | View only |     No |     No |                    No |                      No |

`PROD_READY` partial lock means:

- Do not allow rename project/sub project.
- Do not allow delete project/sub project.
- Do not allow destructive file operations.
- Do allow viewing all details.
- Do allow notes/history viewing and safe notes append/edit if needed for execution evidence.
- Do allow CR/Drone state progression needed to finish deployment.
- Do allow move to `IMPLEMENTED` after guards pass.
- Do allow Postpone/Cancel only with confirmation.

`IMPLEMENTED` lock means all editing/deleting/postponing controls hidden or disabled.

### 7.7 T-10 Rule

Requirement: CR must reach at least `PENDING APPROVAL` no later than configured threshold days before `start_datetime`.

Default threshold: 10 days.

Canonical calculation:

```text
cr_pending_approval_at <= start_datetime - t10_threshold_days
```

Rules:

- Use `cr_pending_approval_at`, not `cr_state_updated_at`, for T-10 proof.
- If `cr_pending_approval_at` missing and CR is already beyond `PENDING SUBMISSION`, show warning that old data cannot prove T-10.
- Dashboard highlights row when current date passes T-10 deadline and CR has not reached `PENDING APPROVAL`.
- Transition `UAT_PREPARE → PROD_READY` is blocked if T-10 condition fails or cannot be proven.

### 7.8 Auto `IN-PROGRESS`

Background QTimer checks active projects periodically.

Default tick: 60 seconds.

If local OS `now` is inside `[start_datetime, end_datetime]`:

- CR with `APPROVED` becomes `IN-PROGRESS` automatically.
- Drone ticket with `APPROVED` becomes `IN-PROGRESS` automatically.
- Metadata is written atomically.
- History entries are appended.
- UI refreshes through the pywebview JS bridge or equivalent main-thread-safe notification path.
- Notification is created.

---

## 8. Link Parsing and Display

### 8.1 CR Link

User pastes full CR URL into CR field.

App stores full URL in `cr_link`.

UI displays formatted CR number extracted from URL when possible.

Example display:

```text
CR202604209900114 ↗
```

Click opens stored `cr_link` in default browser.

If extraction fails, display shortened URL or host/path safely, but keep full URL stored.

### 8.2 Drone Link

User pastes full Drone URL into Drone field.

App stores full URL in `drone_link`.

UI displays formatted Drone ticket extracted from URL when possible.

Example display:

```text
D-SSIDBI-159 ↗
```

Click opens stored `drone_link` in default browser.

### 8.3 Empty Field Paste Behavior

When field is empty and user pastes CR/Drone link:

- Validate that pasted value is URL-like.
- Store original full URL.
- Immediately display extracted CR/Drone identifier if possible.
- Keep clickable behavior.
- Add history entry after Save, not on every paste keystroke.

---

## 9. App Navigation and Windows

Navigation items:

1. Main Dashboard
2. Project Details
3. Report
4. Second Brain
5. Automations
6. Settings

Notifications is not a separate page. It is a persistent panel visible across all windows, attached to main layout/sidebar.

Link Bank is not a separate page. It is a mode/tab inside Second Brain.

---

## 10. User Flows

### 10.1 App Startup

```text
App opens
  → Load settings.json from %APPDATA%\ProjectTrackerDBS\
    → If root_folder unset: show setup dialog to choose root folder
    → Save settings
  → Scan filesystem
  → Load dashboard for current year if folder exists, otherwise prompt/create
  → Start watchdog observer
  → Start auto IN-PROGRESS timer
```

### 10.2 Navigation

```text
User clicks sidebar item
  → QStackedWidget switches active window
  → Notification panel stays visible and is not recreated
```

### 10.3 Dashboard Filter

```text
User opens Main Dashboard
  → Table shows all projects for selected year
  → State tabs filter in memory
  → Search filters by project/subproject name with 200ms debounce
  → Year dropdown shows existing year folders only
  → Selecting year rescans that year
```

### 10.4 Add Year

```text
User clicks + beside year dropdown
  → Popover/dropdown defaults to next year
  → User picks year
  → If year > current year + 2: confirmation warning
  → Create {YEAR}\UAT_PREPARE, PROD_READY, IMPLEMENTED, POSTPONED
  → Refresh year dropdown
```

### 10.5 Dashboard Row Actions

For each project/sub project row:

- Click project/sub project name: open folder in Windows File Explorer.
- Click CR/Drone display value: open stored link in default browser.
- Click Details: navigate to Project Details.
- Change CR/Drone state via inline dropdown if transition is valid.
- Open action menu: Details, Move to `PROD_READY`, Postpone, Delete, Open Folder.

Invalid transitions must be disabled or blocked with clear reason.

### 10.6 Add New Project

```text
User clicks Add Project
  → Project Details opens in NEW_PROJECT mode
  → Only Project Name field required
  → Real-time Windows folder name validation
  → Save disabled until valid
  → Save creates {root}\{year}\UAT_PREPARE\{project_name}\
  → Create project_data.json defaults
  → Create notes.md
  → Create default command template files if configured
  → Refresh Dashboard and highlight new row
```

### 10.7 Project Details — SHOW/EDIT

```text
User clicks Details
  → Project Details opens in SHOW_EDIT mode
  → Load selected main project/sub project context
  → Lock/edit behavior follows folder state
```

Main project context shows:

- Main project info.
- CR link/state.
- Start/end datetime.
- All sub projects.
- Drone ticket mapping for main project and sub projects.
- Main folder files excluding files inside sub project folders.
- Main `notes.md`.
- Project history.

Sub project context shows:

- Sub project info.
- Parent main project info.
- Same CR number/link inherited from main project.
- Drone ticket mapped to that sub project.
- Sub project files.
- Sub project `notes.md`.
- Relevant project/sub project history.

Available actions depending on lock state:

- Open root folder.
- Rename project/sub project.
- Edit CR link/state.
- Add/edit Drone tickets.
- Add sub project from main project context.
- Delete project/sub project.
- Edit start/end datetime.
- Add/delete files.
- Add file from template.
- Add manual file.
- Edit notes.
- View history.

### 10.8 Add Sub Project

```text
User opens main project details
  → Click Add Sub Project
  → Enter folder name
  → Validate Windows folder name
  → Create subfolder
  → Create subproject notes.md
  → Refresh subproject list
```

### 10.9 Add Drone Ticket

```text
User opens project details
  → Click Add Drone Ticket
  → Select mapping: main project or sub project folder
  → Paste Drone link
  → Store full link
  → Display extracted ticket identifier
  → Default drone_state = UAT
  → Append history
```

### 10.10 Add File from Template

```text
User clicks Add File from Template
  → App lists files from configured template folders
  → User selects template
  → App copies template into current project/sub project folder
  → New filename prefix = {CR_NUMBER}_{template_filename}
  → App opens file using default Windows application
  → Refresh file list
```

### 10.11 Add Manual File

```text
User clicks Add Manual File
  → Input file name
  → If extension exists: use it
  → If no extension: user chooses format
  → Create empty file
  → Open with default Windows application
  → Refresh file list
```

### 10.12 Notes Editing

Project and sub project notes use `notes.md` as primary storage.

```text
User types in built-in notes editor
  → Debounce 1000ms
  → Auto-save to notes.md
  → Show saved status
```

JSON `notes` remains for legacy/short note compatibility, not primary note editor storage.

### 10.13 REOPEN

```text
User selects REOPEN from CR state dropdown
  → Only available from APPROVED or PENDING APPROVAL
  → Confirm modal
  → Move project folder to UAT_PREPARE
  → Record REOPEN history event
  → Set next working CR state to PENDING SUBMISSION
  → Update timestamps
  → Refresh Dashboard
  → Create notification
```

History detail should preserve old state:

```text
REOPEN: {old_state} → REOPEN, project reverted to UAT_PREPARE; next state PENDING SUBMISSION
```

### 10.14 Move to PROD_READY

```text
User clicks Move to PROD_READY
  → Run all guards
  → If failed: show guard checklist and block
  → If passed: confirm
  → Move folder to PROD_READY
  → Append history
  → Refresh Dashboard
```

### 10.15 Postpone

```text
User clicks Postpone
  → Not available for IMPLEMENTED
  → Confirm
  → Move folder to POSTPONED
  → Append history
  → Refresh Dashboard
```

Resume:

```text
User clicks Resume from POSTPONED
  → Confirm
  → Move folder to UAT_PREPARE
  → Append history
  → Refresh Dashboard
```

### 10.16 Delete

```text
User clicks Delete
  → Not available for IMPLEMENTED
  → Confirm that folder goes to Recycle Bin
  → send2trash(project_or_subproject_path)
  → Refresh Dashboard
  → Create notification
```

Deleting a main project deletes/moves whole main project folder to Recycle Bin. Deleting sub project moves only sub project folder.

### 10.17 CR CANCELED

```text
User sets CR state to CANCELED
  → Confirm
  → Update CR state/history
  → Move project folder to POSTPONED
  → Refresh Dashboard
  → Create notification
```

---

## 11. Main Dashboard Requirements

Dashboard is primary tracking window.

Must show:

- Active year selector.
- Add Year button.
- Add Project button.
- State filters for `UAT_PREPARE`, `PROD_READY`, `IMPLEMENTED`, `POSTPONED`.
- Search by project/sub project name.
- Summary counts by state.
- Table/list of main projects and sub projects.

Each row should expose:

- Project/sub project name.
- Folder state.
- CR number display and link action.
- CR state badge/dropdown.
- Drone ticket display and link action.
- Drone state badge/dropdown.
- Start/end datetime.
- T-10 warning indicator.
- Details/action button.

Dashboard must not require full rescan for simple in-memory filters.

---

## 12. Project Details Requirements

Project Details has two modes.

### 12.1 NEW_PROJECT Mode

Triggered only from Add Project.

Required:

- Minimal form.
- Project Name field.
- Realtime folder validation.
- Save creates folder and default metadata.
- Cancel returns without creating files.

### 12.2 SHOW_EDIT Mode

Triggered from Dashboard Details or navigation.

Required:

- Project/sub project selector.
- Header showing selected context.
- Parent info when viewing sub project.
- Main project info when viewing main project.
- CR link/state editor according to lock rules.
- Drone ticket list and mapping.
- Start/end datetime editor according to lock rules.
- Sub project management for main project.
- File list for selected context.
- Notes editor backed by `notes.md`.
- Read-only history panel.

File list rule:

- If viewing main project, show files directly under main project folder only.
- Do not include files inside sub project folders.
- Organizational folders are normal folders, not sub projects.

---

## 13. Report Requirements

Report window shows project analytics and CSV export.

Required filters:

- Year.
- Month.
- Folder state.
- CR state.
- Drone state.
- Search text.

Required information:

- Total CR count by selected filter.
- Count by date/month/year.
- Count by project folder state.
- Count by CR state.
- Count by Drone state.
- Table of matching projects/sub projects.

Export:

- CSV only.
- Use Python standard `csv` library.
- User chooses output path through save dialog.
- CSV must be readable by Excel.

No PDF export in MVP.

---

## 14. Second Brain Requirements

Second Brain has two modes/tabs: Notes and Link Bank.

### 14.1 Notes Mode

Storage root default:

```text
%APPDATA%\ProjectTrackerDBS\SecondBrain\
```

Requirements:

- Free folder structure.
- Create folder.
- Rename folder.
- Delete folder through Recycle Bin.
- Create `.md` note.
- Rename note.
- Delete note through Recycle Bin.
- Built-in markdown editor.
- Auto-save with 1000ms debounce.
- Optional preview uses browser-native HTML rendering or plain text unless a markdown dependency is approved.
- Markdown toolbar inserts syntax for bold, italic, underline intent, H1, H2, code, link, horizontal rule, and quote.
- Smart tags or tag text support inside note content.
- Search by pattern, case-insensitive partial match.
- Filter notes by date.
- Can also show/search project/sub project notes and files.

All notes created by Second Brain must be `.md`.

### 14.2 Link Bank Mode

Requirements:

- Add/edit/delete categories.
- Add/edit/delete links.
- Fields: name, URL, notes, category.
- Group links by category.
- Open link in default browser.
- Search case-insensitive by name, URL, notes.
- Stored in `link_bank.json`.

---

## 15. Automations Requirements

Automations window has four MVP modes/tabs:

1. Email
2. Teams
3. Download Email
4. Automation Rules

Automation Rules is shared rule management for reusable conditions used by Email, Teams, and Download Email jobs.

### 15.1 Email Automation

Uses Outlook desktop through `win32com.client`.

Email can be draft or send depending on settings.

Default mode: draft.

Flags:

- `ack_sent`
- `approval_sent`
- `last_cr_link_when_sent`

Flags are visual indicators only. They must not block user from generating another draft/send.

#### 15.1.1 Email Categories

| Category    | Purpose                                                                       | Active Conditions                                                          |
| ----------- | ----------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| `ACK_UAT`   | Ask manager acknowledgement for non-SOP/per-application UAT/package readiness | CR `PENDING SUBMISSION`; Drone `PENDING APPROVAL` for projects using Drone |
| `ACK_SOP`   | Ask acknowledgement for routine weekly SOP                                    | CR `PENDING SUBMISSION`; Drone ignored                                     |
| `APRVL_CR`  | Ask technical approval after PROD execution for non-SOP/per-application work  | CR `IN-PROGRESS`; Drone `IN-PROGRESS` for projects using Drone             |
| `APRVL_SOP` | Ask technical approval for routine weekly SOP closure                         | CR `IN-PROGRESS`; Drone ignored                                            |

If project has no Drone ticket, Drone condition is treated as passed where applicable.

#### 15.1.2 Editable Template Settings

Each email category must allow editing:

- To.
- CC.
- Subject template.
- Body template.
- Attachment template/file.
- Draft/send override.
- Conditions.

Editable conditions may involve only:

- CR state.
- Drone state.
- Existence of specified file in project/sub project folder.

#### 15.1.3 Placeholders

Supported placeholders:

```text
{PROJECT_NAME}
{SUBPROJECT_NAME}
{CR_NUMBER}
{CR_LINK}
{DRONE_TICKET}
{DRONE_LINK}
{START}
{END}
{CR_STATE}
{DRONE_STATE}
{YEAR}
{USER}
{IMPLEMENTATION_PLAN}
```

### 15.2 Teams Automation

Default behavior is paste-only, not auto-send.

Requirements:

- User can add/edit/delete Teams automation entries.
- Each entry has name, target email/group, mentions, message template, attachment paths, and conditions.
- Conditions may involve CR state, Drone state, folder state, and file existence.
- Countdown seconds is configurable globally.
- `teams_auto_send` default false globally.
- If false: app opens Teams target and pastes message only.
- If true: app pastes message and presses Enter after countdown.
- User can cancel during countdown.
- `pyautogui.FAILSAFE = True`.
- Locked/sleeping screen or missing target should abort safely.

### 15.3 Download Email Automation

Triggered after selected email draft/send is created.

Purpose: wait for Outlook reply email related to CR, save it to project folder, and notify user.

Rules:

- Runs in background thread, not UI thread.
- Poll interval default: 10 seconds.
- Timeout default: 3 hours.
- Match reply by CR number in subject and/or configured matching rule.
- Active job shows CR number, project name, start time, progress/elapsed indicator, and Stop action.
- On match: save email and attachments to project folder.
- On success: mark job completed and create notification.
- On timeout: mark job timeout and create warning notification.
- User can stop active job; stopped job is kept in job history.
- Active and historical jobs visible in Automations window.

### 15.4 Automation Rules

Automation Rules is shared configuration for conditions used by Email, Teams, and Download Email jobs.

Requirements:

- User can add/edit/delete named condition groups.
- Condition group can be reused by Email template or Teams automation.
- Conditions may check CR state, Drone state, folder state, project name pattern, SOP/non-SOP pattern, and file existence.
- Conditions must show human-readable pass/fail result before automation runs.
- Failed required conditions block automation unless user explicitly marks condition group as warning-only.
- Condition changes are saved to `settings.json`.

---

## 16. Notifications Requirements

Notifications are persistent panel attached to all windows, not separate navigation page.

Notification sources:

- T-10 warning.
- Auto `IN-PROGRESS`.
- Watchdog folder rename/move/delete.
- Email draft/send completed.
- Email reply received.
- Email download timeout.
- Schema/corrupt JSON warning.
- System/config warnings.

Notification fields:

| Field          | Description                                            |
| -------------- | ------------------------------------------------------ |
| `id`           | Unique id                                              |
| `type`         | Notification type                                      |
| `title`        | Short title                                            |
| `message`      | Full message                                           |
| `timestamp`    | Local timestamp                                        |
| `project_path` | Optional related project                               |
| `dismissed`    | In-memory or persisted depending future implementation |

Panel behavior:

- Visible on all main windows.
- Attached to persistent sidebar/layout and not recreated during navigation.
- Shows latest 3 notifications by default.
- Shows total count when more than 3 notifications exist.
- Card click opens detail dialog.
- Detail dialog can close, dismiss, or go to project if applicable.
- Dismiss removes notification from active panel.
- Close keeps notification active.

MVP can keep notifications in memory during one app session unless persistence is explicitly added later.

---

## 17. Watchdog, Concurrency, and Data Safety

### 17.1 Watchdog

Use `watchdog` to detect filesystem changes under root folder.

Safety requirements:

1. Debounce filesystem events by at least 300ms.
2. Watchdog thread must communicate to UI through a main-thread-safe pywebview bridge or queued notification path.
3. JSON reads/writes must retry on temporary file lock.
4. If folder is renamed/moved externally while app has it loaded, app must remap path before saving.
5. External delete removes item from in-memory dashboard and creates notification.
6. External move between state folders updates derived project state.

### 17.2 Atomic Writes

All JSON writes use temp file then replace.

```text
project_data.json.tmp → project_data.json
settings.json.tmp → settings.json
link_bank.json.tmp → link_bank.json
```

### 17.3 Error Handling

- Missing `project_data.json`: project still appears with default metadata and warning if needed.
- Corrupt JSON: skip affected project and notify/warn; app must not crash.
- Unknown schema: skip/warn; app must not crash.
- Missing subfolder referenced by Drone ticket: warn; app must not crash.
- Locked file: retry before warning.
- Existing target folder during move/rename: block and show error.

---

## 18. Dependencies

Locked baseline dependencies:

```text
pywebview>=5.0
pywin32>=306
pyinstaller>=6.0.0
pyautogui>=0.9.54
pyperclip>=1.8.2
send2trash>=1.8.3
watchdog>=4.0.0
```

Rules:

- Do not add dependency without user confirmation.
- Do not add Qt or browser-engine packages.
- Do not add PDF library.
- Markdown preview should use browser-native HTML rendering or plain text unless user approves markdown dependency.

---

## 19. Packaging

Target packaging is Windows only.

Production direction:

```powershell
pyinstaller --name "ProjectTrackerDBS" --onedir --windowed --icon=assets/icon.ico --add-data "assets;assets" project_tracker/main.py
```

Rules:

- Do not attempt Windows PyInstaller build from Linux.
- Build verification belongs on Windows target machine.
- Source code can be unit-tested on Linux only for platform-independent logic.

---

## 20. MVP Scope

All listed product features are MVP:

- Main Dashboard.
- Project Details.
- Report.
- Second Brain Notes.
- Link Bank inside Second Brain.
- Automations: Email, Teams, Download Email, Automation Rules.
- Settings.
- Persistent notification panel.
- Watchdog filesystem sync.
- Auto `IN-PROGRESS`.
- T-10 warning/blocking.
- CSV export.
- Windows packaging direction.

MVP does not include:

- Cloud sync.
- External DB.
- SQLite cache.
- Multi-user collaboration.
- PDF export.
- Internal browser/WebEngine.
- Linux runtime support for the desktop app.

---

## 21. Implementation Protocol

Implementation must happen in phases. Do not move to next phase until current phase is verified.

Current instruction priority: finish PRD first before writing more Python code.

### Phase 0 — PRD Finalization

- `PRD.md` is complete single source of truth.
- `README.md` and `DESIGN.md` are not used as requirements.
- User approves PRD direction.

### Phase A — Core Domain

- Enums and dataclasses.
- `cr_pending_approval_at`.
- `DroneTicket.subfolder_name`.
- REOPEN event semantics.
- CR CANCELED → POSTPONED rule.
- POSTPONED → UAT_PREPARE resume rule.
- T-10 based on `cr_pending_approval_at`.
- Folder-name validation.
- Organizational folder exclusion.
- Settings `display_name` and current user helper.

Verify with unit tests only.

### Phase B — Filesystem and Stores

- MetadataStore atomic read/write.
- SettingsStore AppData path.
- LinkBankStore.
- Notes file handling.
- Scanner and schema fallback.
- Watchdog service skeleton with debounce/signals.

Verify with unit tests where possible.

### Phase C — Main UI Structure

- MainWindow shell.
- Sidebar navigation.
- Persistent notification panel.
- QStackedWidget pages.
- Dashboard read-only scan display.

Verify manually on Windows.

### Phase D — Project Dashboard and Details

- Add Project.
- Add Year.
- Dashboard actions.
- Project Details NEW/SHOW_EDIT modes.
- File management.
- Notes editor.
- History panel.
- Locking behavior.

Verify manually on Windows plus core unit tests.

### Phase E — State Transitions and Automation Hooks

- Move to `PROD_READY`.
- Move to `IMPLEMENTED`.
- Postpone/resume.
- Cancel.
- REOPEN.
- Auto `IN-PROGRESS`.
- Notifications.

Verify with unit tests for rules and manual Windows tests for filesystem/UI.

### Phase F — Second Brain, Report, Automations

- Second Brain notes.
- Link Bank.
- Report and CSV export.
- Email automation.
- Teams automation.
- Download Email jobs.
- Automation Rules.
- Settings UI completion.

Verify manually on Windows; unit-test serializable settings/stores.

---

## 22. Acceptance Criteria

### 22.1 Core/Data

| #   | Criteria                                                                                |
| --- | --------------------------------------------------------------------------------------- |
| 1   | Project folder state is always derived from folder path.                                |
| 2   | `project_state` never appears in `project_data.json`.                                   |
| 3   | Year is derived from year folder only.                                                  |
| 4   | `DroneTicket.subfolder_name = null` loads old data without crash.                       |
| 5   | Missing subfolder mapping shows warning without crash.                                  |
| 6   | `cr_pending_approval_at` is stored and used for T-10.                                   |
| 7   | History uses display name or Windows login, never hardcoded username.                   |
| 8   | Unknown/corrupt JSON warns/skips without app crash.                                     |
| 9   | Atomic writes use temp-then-replace.                                                    |
| 10  | Windows folder name validation rejects invalid names/reserved names/trailing dot/space. |

### 22.2 State Rules

| #   | Criteria                                                                     |
| --- | ---------------------------------------------------------------------------- |
| 1   | `UAT_PREPARE → PROD_READY` blocked unless all guards pass.                   |
| 2   | T-10 violation highlights dashboard and blocks `PROD_READY`.                 |
| 3   | Auto `IN-PROGRESS` changes CR/Drone only during execution window.            |
| 4   | `FINISHED` can be manually set only from `IN-PROGRESS`.                      |
| 5   | REOPEN available only from `APPROVED`/`PENDING APPROVAL`.                    |
| 6   | REOPEN moves folder to `UAT_PREPARE` and next state is `PENDING SUBMISSION`. |
| 7   | CR `CANCELED` moves project to `POSTPONED`.                                  |
| 8   | `POSTPONED` resumes only to `UAT_PREPARE`.                                   |
| 9   | `PROD_READY` partial lock works.                                             |
| 10  | `IMPLEMENTED` full lock works.                                               |

### 22.3 UI/User Flow

| #   | Criteria                                                                        |
| --- | ------------------------------------------------------------------------------- |
| 1   | Dashboard year dropdown shows existing year folders only.                       |
| 2   | Add Year creates four required state folders.                                   |
| 3   | Add Project opens NEW_PROJECT mode with only required fields.                   |
| 4   | Details opens SHOW_EDIT mode and respects selected project/sub project.         |
| 5   | Main project file list excludes sub project files.                              |
| 6   | Organizational folders do not appear as sub projects.                           |
| 7   | CR/Drone pasted links display as extracted ticket numbers and remain clickable. |
| 8   | Project/sub project names open Explorer.                                        |
| 9   | CR/Drone values open default browser.                                           |
| 10  | Notification panel remains visible across windows.                              |

### 22.4 Feature Areas

| #   | Criteria                                                              |
| --- | --------------------------------------------------------------------- |
| 1   | Notes save to `notes.md` with debounce.                               |
| 2   | Second Brain creates and edits `.md` notes.                           |
| 3   | Link Bank stores categories and links in `link_bank.json`.            |
| 4   | Report filters by year/month/state and exports CSV.                   |
| 5   | Email templates are editable and saved to settings.                   |
| 6   | Email draft/send uses Outlook and latest project data.                |
| 7   | Email flags are visual only and do not block repeat draft.            |
| 8   | Teams automation defaults to paste-only.                              |
| 9   | Download Email polls every 10s up to 3h and notifies success/timeout. |
| 10  | Automation Rules can be saved and reused by Email/Teams automations.  |
| 11  | Watchdog external changes update UI without crash.                    |

### 22.5 Platform

| #   | Criteria                                                          |
| --- | ----------------------------------------------------------------- |
| 1   | Linux dev only runs platform-independent unit tests.              |
| 2   | Windows manual test covers UI and integrations.                   |
| 3   | PyInstaller build is documented for Windows and not run on Linux. |
| 4   | No WebEngine/internal browser dependency exists.                  |
| 5   | No PDF dependency exists.                                         |

---

## 23. Explicit Non-Goals

- No design-system/pixel-perfect/color spec in PRD.
- No cloud sync.
- No multi-user conflict resolution.
- No database-backed source of truth.
- No PDF export.
- No embedded browser.
- No Linux runtime support for this Windows desktop app.
- No automatic sending to Teams unless user explicitly enables `teams_auto_send`.
- No destructive hard delete.

---

## 24. Final Locked Decisions

This PRD locks the following product decisions for MVP implementation:

1. `PRD.md` is the only source of truth.
2. Filesystem folder path is the source of truth for project existence, year, and folder state.
3. `project_data.json` stores metadata only and never stores `project_state`.
4. Main project and sub projects share one CR number.
5. Main project and each sub project may have separate Drone tickets.
6. `PROD_READY` is partially locked; `IMPLEMENTED` is fully locked.
7. T-10 uses `cr_pending_approval_at`.
8. REOPEN moves project to `UAT_PREPARE`, records REOPEN history, then returns CR working state to `PENDING SUBMISSION`.
9. CR `CANCELED` moves project to `POSTPONED`.
10. `POSTPONED` resumes only to `UAT_PREPARE`.
11. Primary notes storage is `notes.md`; JSON `notes` remains legacy/short-note compatibility.
12. Notifications are a persistent panel, not a standalone page.
13. Link Bank lives inside Second Brain.
14. All listed windows/features are MVP.
15. CSV export only; PDF export is not allowed.
16. Default browser only; embedded browser/WebEngine is not allowed.
17. Teams automation is paste-only by default unless `teams_auto_send` is enabled.
18. Windows is the runtime target; Linux is only for platform-independent unit tests.

---

## 25. Implementation Handoff Rule

Implementation may start only after user approves this PRD direction.

When implementation starts:

1. Follow phase order in Section 21.
2. Do not skip verification gates between phases.
3. Do not add dependencies without confirmation.
4. Do not run Windows-only app/integration flows on Linux.
5. Keep changes surgical and traceable to this PRD.
6. If implementation discovers conflict between code and PRD, update/confirm PRD before coding around it.

---

## 26. Non-Blocking Runtime Calibration

Some values depend on real office URLs/messages and should be calibrated during Windows manual testing, without changing product scope:

1. CR number extraction pattern from real ITSM URLs.
2. Drone ticket extraction pattern from real Drone URLs.
3. Outlook reply matching pattern from real email subjects.
4. Whether in-memory notifications are enough for MVP or persistence is needed later.
5. Whether browser-native markdown preview is enough or a markdown dependency needs explicit approval.

---

## 27. PRD Completion Statement

This document is complete enough to guide Phase A implementation.

Any new product behavior, dependency, state transition, storage rule, or automation mode discovered after this point must be added to `PRD.md` first, then implemented in code after approval.
