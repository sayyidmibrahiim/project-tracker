# Requirements Document

## Introduction

Project Tracker DBS has reached a verified Release Candidate (RC) on Linux: the backend
domain, infrastructure stores, services, and the `JsApi` bridge contract are implemented
and verified (453 Linux tests passing), and the Svelte frontend has all six pages with
read paths and several safe mutations wired. This spec captures **only the remaining
deferred functionality** of PRD v3.1 and the safety guards that must accompany it. It does
**not** re-specify already-completed work (read paths, dashboard binding, safe metadata/
notes/CR/Drone/Link Bank mutations, the bridge response contract, or guarded import safety
that already passes).

The deferred work is high-risk by nature: physical folder moves, file create/rename/delete,
project rename/delete, Windows-only Outlook/Teams automation, the scheduler control surface,
the rules engine execution path, persistent automation/notification logs, Second Brain pin/
favorite persistence and note CRUD, and the Windows manual-test-and-packaging gate. Every
runtime-destructive or Windows-only action in this spec must be guarded, draft/preview-first
where applicable, gated behind explicit confirmation UI, tested only against temporary
directories/stores, and surfaced honestly in the UI (no fake success).

This document follows PRD v3.1 (the product/architecture source of truth), `CLAUDE.md`,
and `release-candidate-rules.md`. Where existing `JsApi` methods already satisfy a need, the
requirement names the exact method. Where new bridge methods are required, the requirement
mandates they be added to `project_tracker/web/js_api.py` and wired in `create_js_api()`
**before** the frontend calls them, so no client-side contract is ever invented.

## Glossary

- **System**: The Project Tracker DBS application as a whole (pywebview shell + Svelte
  frontend + Python backend), unless a more specific actor is named.
- **Frontend**: The Svelte + TypeScript UI served from `web/static/`.
- **Bridge**: The typed pywebview channel implemented by `project_tracker/web/js_api.py`
  (`JsApi`), wired by `create_js_api()` in `project_tracker/app_web.py`, and accessed from
  the Frontend only through `frontend/src/lib/bridge.ts` (`callBridge`).
- **Bridge_Response**: The predictable response object every Bridge method returns, of shape
  `{ "ok": boolean, "data": object | null, "error": { "message": string, "code": string } | null }`.
  `ok=true` carries `data`; `ok=false` carries `error` with a stable uppercase `code`.
- **JsApi**: The Python class in `project_tracker/web/js_api.py` exposing Bridge methods.
- **Project_Service / Automation_Service / Scheduler_Service / Second_Brain_Service /
  Notification_Service / Scanner_Service**: Backend services under `project_tracker/services/`.
- **Metadata_Store**: `infrastructure/metadata_store.py`, performing atomic `project_data.json`
  reads/writes.
- **Cache_Db**: `infrastructure/cache_db.py`, the rebuildable SQLite cache/index (never the
  source of truth) that also holds the `notifications` and `automation_rule_logs` tables.
- **Filesystem**: `infrastructure/filesystem.py`, performing `pathlib`-based folder/file
  operations including Recycle Bin delete via `send2trash`.
- **Outlook_Client / Teams_Client**: Windows-only integration wrappers
  (`infrastructure/outlook_client.py`, `infrastructure/teams_client.py`), lazy/guarded by
  `IS_WINDOWS = sys.platform == "win32"`.
- **Folder_State**: A project's folder state derived from its parent state folder. One of
  `UAT_PREPARE`, `PROD_READY`, `IMPLEMENTED`, `POSTPONED`, `CANCELED`. Never stored in
  `project_data.json`.
- **CR_State**: Change Request state. One of `PENDING SUBMISSION`, `PENDING APPROVAL`,
  `APPROVED`, `IN-PROGRESS` (auto only), `FINISHED`, `POSTPONED`, `CANCELED`.
- **Drone_State**: Drone ticket state. One of `UAT`, `PENDING APPROVAL`, `APPROVED`,
  `IN-PROGRESS` (auto only), `FINISHED`, `CANCELED`.
- **REOPEN**: An action (not a persistent state) available from `POSTPONED` or `CANCELED`
  that moves a project folder back to `UAT_PREPARE` and resets CR_State to `PENDING SUBMISSION`.
- **T-10 / T-10 Guard**: The rule that `cr_pending_approval_at <= start_datetime -
timedelta(days=t10_threshold_days)` (default 10 days). Used as a guard for
  `UAT_PREPARE → PROD_READY`.
- **Recycle_Bin**: Windows Recycle Bin destination used via `send2trash`; the only permitted
  deletion mechanism (hard delete forbidden).
- **Temp_Root**: A temporary directory/store created for a dev or test run; the only
  filesystem location against which destructive operations may execute during dev/tests.
- **Draft_First**: Default Outlook behavior that creates a draft email rather than sending.
- **Preview_First**: Default Teams behavior that opens a deep link and places message text on
  the clipboard rather than auto-sending.
- **Confirmation_UI**: A frontend modal that states the action, its target, its
  reversibility, and requires explicit user confirmation before a high-risk Bridge call.
- **Disabled_State_Message**: Accurate UI messaging shown when a high-risk action is not
  permitted (by Folder_State lock or because it is deferred/unimplemented).
- **Template_Category**: An Outlook email template category. One of `ACK_UAT`, `ACK_SOP`,
  `APRVL_CR`, `APRVL_SOP`.
- **Automation_Rule_Log**: A persisted execution record written to the SQLite
  `automation_rule_logs` table.
- **Verification_Suite**: The four mandatory checks — `svelte-check`, `vite build`,
  `pytest`, and `py_compile` — that must all pass per change.

---

## Requirements

### Requirement 1: Bridge Contract Integrity for Deferred Actions

**User Story:** As the deployment engineer, I want every new high-risk action to call a real,
wired backend method, so that the UI never reports fake success against a non-existent contract.

#### Acceptance Criteria

1. THE Frontend SHALL invoke deferred-scope backend actions only through `callBridge` in
   `frontend/src/lib/bridge.ts` and SHALL NOT access `window.pywebview` directly outside that
   wrapper.
2. WHERE a deferred action maps to an existing JsApi method, THE Frontend SHALL call that exact
   method name without introducing a new client-side contract.
3. WHERE a deferred action requires a capability not present in JsApi, THE System SHALL add the
   corresponding method to `project_tracker/web/js_api.py` and wire it in `create_js_api()`
   before the Frontend calls it.
4. WHEN a Bridge method completes successfully, THE JsApi SHALL return a Bridge_Response with
   `ok=true` and a non-null `data` object containing the fields defined for that method's
   contract.
5. IF a Bridge method encounters a runtime or service error, THEN THE JsApi SHALL return a
   Bridge_Response with `ok=false` and an `error` object whose `message` is a non-empty
   human-readable string of 1 to 500 characters and whose `code` is a non-empty token of 1 to
   64 characters composed only of uppercase letters, digits, and underscores.
6. IF a Bridge method receives a request for an action that is not yet implemented, THEN THE
   JsApi SHALL return a Bridge_Response with `ok=false` and a `code` that identifies the
   unimplemented action, and SHALL NOT modify any persisted state or perform any partial side
   effect.
7. WHEN the Frontend receives a Bridge_Response with `ok=false`, THE Frontend SHALL display the
   `error.message` text to the user and SHALL NOT render any success indication.
8. IF a Bridge call returns a malformed or absent Bridge_Response, or does not resolve within 30
   seconds, THEN THE Frontend SHALL treat the call as failed and SHALL display an error
   indication rather than a success state.
9. THE System SHALL keep existing JsApi method signatures unchanged unless a signature change is
   proven necessary, and WHERE a signature change is made, THE System SHALL update all affected
   tests and documentation in the same change.

### Requirement 2: Filesystem Safety Invariants for High-Risk Operations

**User Story:** As the deployment engineer, I want all destructive filesystem work to be
provably safe during development and testing, so that no real project data is ever lost.

#### Acceptance Criteria

1. WHEN a folder move, folder rename, file write, file rename, or delete operation executes
   during development or automated tests, THE System SHALL target a path located within the
   Temp_Root directory and SHALL NOT target any real user project folder.
2. WHEN the System deletes a project, subproject, file, or note, THE Filesystem SHALL route the
   deletion to the Recycle_Bin via `send2trash` and SHALL NOT perform an irreversible hard
   delete.
3. THE System SHALL perform all path construction and traversal using `pathlib.Path` objects and
   SHALL NOT use manual string concatenation of path segments.
4. WHEN the System writes `project_data.json` or any JSON store, THE Metadata_Store SHALL first
   write to a temporary file in the same target directory and SHALL atomically replace the
   target file only after the temporary file is completely written.
5. THE System SHALL NOT store `project_state` in `project_data.json`.
6. WHEN the System records or updates any datetime, THE System SHALL store it as an ISO 8601
   string that includes an explicit UTC offset derived from the local OS timezone.
7. WHERE a path value originates from Windows-formatted settings, THE System SHALL preserve the
   original Windows path form, including its drive letter and backslash separators, and SHALL
   NOT normalize or convert it to a POSIX/Linux path form.
8. IF the Cache_Db is missing, deleted, or fails an integrity check, THEN THE System SHALL
   rebuild it from the Filesystem and JSON stores and SHALL continue to treat the Filesystem and
   JSON stores as the source of truth.
9. IF a folder move, folder rename, file write, file rename, or delete operation is requested
   during development or automated tests with a target path outside the Temp_Root directory,
   THEN THE System SHALL reject the operation, SHALL leave all filesystem contents unchanged, and
   SHALL return an error indicating the target path is outside the permitted Temp_Root.
10. IF an atomic temp-file-then-replace write to `project_data.json` or any JSON store fails
    before the replace step completes, THEN THE Metadata_Store SHALL preserve the existing target
    file unchanged and SHALL return an error indicating the write did not complete.

### Requirement 3: High-Risk Action Confirmation and Disabled-State Messaging

**User Story:** As the deployment engineer, I want clear confirmation prompts and honest
disabled states for risky actions, so that I never trigger an irreversible change by accident.

#### Acceptance Criteria

1. WHEN the user initiates a folder transition, project rename, project delete, subproject
   delete, file rename, file delete, Outlook send, or Teams auto-send, THE Frontend SHALL present
   a Confirmation_UI and SHALL NOT issue the Bridge call until the user explicitly confirms.
2. THE Confirmation_UI SHALL state the action name, the target name or path, and an explicit
   binary statement of whether the action is reversible or irreversible.
3. WHERE the reversibility of an action cannot be determined, THE Confirmation_UI SHALL present
   the action as irreversible.
4. IF the user cancels or dismisses the Confirmation_UI, THEN THE Frontend SHALL NOT issue the
   Bridge call and SHALL leave the prior UI state unchanged.
5. WHERE a high-risk action is disabled by a Folder_State locking rule, THE Frontend SHALL render
   the control as disabled and non-interactive and SHALL display a Disabled_State_Message naming
   the Folder_State locking rule that makes the action unavailable.
6. WHERE a high-risk capability is deferred and not yet implemented, THE Frontend SHALL display a
   Disabled_State_Message indicating the capability is not yet available and SHALL NOT call any
   Bridge method.
7. IF a high-risk Bridge call returns `ok=false`, THEN THE Frontend SHALL display the returned
   error message, SHALL leave the prior UI state unchanged, and SHALL reflect that no partial
   mutation was applied.

### Requirement 4: Folder State Transitions

**User Story:** As the deployment engineer, I want to move projects between deployment states,
so that the folder structure reflects real deployment progress under enforced guards.

#### Acceptance Criteria

1. WHEN the user confirms a move from `UAT_PREPARE` to `PROD_READY`, THE Frontend SHALL call
   `folder_move_to_prod_ready`, and THE Project_Service SHALL physically move the project folder
   via the Metadata_Store and Filesystem only if all state-machine guards pass.
2. THE Project_Service SHALL evaluate the `UAT_PREPARE → PROD_READY` guards as the conjunction
   of: `start_datetime` exists and is not earlier than the current system date; `end_datetime`
   exists and `end_datetime > start_datetime`; `cr_link` is present; `cr_state = APPROVED`; all
   Drone tickets are `APPROVED`; and the T-10 Guard passes.
3. IF the T-10 Guard fails while all other `UAT_PREPARE → PROD_READY` guards pass, THEN THE
   Project_Service SHALL block the automatic move, SHALL leave the project in `UAT_PREPARE`, and
   THE Notification_Service SHALL emit a T-10 violation notification.
4. WHEN the user confirms a manual T-10 override after a T-10 failure, THE Project_Service SHALL
   perform the `UAT_PREPARE → PROD_READY` move and SHALL append a history entry recording the
   source state, target state, acting user, UTC timestamp, and an override flag.
5. WHEN the user confirms a move from `PROD_READY` to `IMPLEMENTED`, THE Frontend SHALL call
   `folder_move_to_implemented`, and THE Project_Service SHALL perform the move only if
   `cr_state = FINISHED` and all Drone tickets are `FINISHED`; otherwise it SHALL leave the
   project in `PROD_READY` and return a Bridge_Response with `ok=false`.
6. WHEN the user confirms postponing a project, THE Frontend SHALL call `folder_postpone`, and
   THE Project_Service SHALL move the folder to `POSTPONED`, set CR_State to `POSTPONED`, and
   append a history entry recording source state, target state, acting user, and UTC timestamp.
7. WHEN the user confirms canceling a project, THE Frontend SHALL call `folder_cancel`, and THE
   Project_Service SHALL move the folder to `CANCELED`, set CR_State to `CANCELED`, and append a
   history entry recording source state, target state, acting user, and UTC timestamp.
8. WHEN the user confirms reopening a `POSTPONED` or `CANCELED` project, THE Frontend SHALL call
   `folder_reopen`, and THE Project_Service SHALL move the folder to `UAT_PREPARE`, set CR_State
   to `PENDING SUBMISSION`, update `cr_state_updated_at`, and append a REOPEN history entry
   recording source state, target state, acting user, and UTC timestamp.
9. IF a folder transition is requested from a Folder_State that the state machine does not permit
   as a source, THEN THE Project_Service SHALL reject the transition, leave the project
   unchanged, and return a Bridge_Response with `ok=false`.
10. WHILE a project is in `IMPLEMENTED`, THE System SHALL reject `POSTPONED` and `CANCELED`
    transition requests for that project and return a Bridge_Response with `ok=false`.
11. WHEN a folder transition completes successfully, THE System SHALL update the Cache_Db before
    returning a Bridge_Response with `ok=true` so the dashboard reflects the new Folder_State on
    next read.
12. IF the physical folder move or Metadata_Store write fails after the guards pass, THEN THE
    Project_Service SHALL roll back to the pre-move state with no partial change, SHALL NOT update
    the Cache_Db, and SHALL return a Bridge_Response with `ok=false`.

### Requirement 5: Project Rename and Delete

**User Story:** As the deployment engineer, I want to rename and delete projects safely, so that
I can correct names and remove obsolete projects without losing recoverability.

#### Acceptance Criteria

1. WHEN the user confirms a project rename, THE Frontend SHALL call `project_rename`, and THE
   Project_Service SHALL validate the new name as non-empty, 1 to 255 characters, free of the
   characters `\ / : * ? " < > |`, not a Windows reserved device name (CON, PRN, AUX, NUL,
   COM1–COM9, LPT1–LPT9), and without a trailing space or dot before renaming.
2. IF a project rename target name is invalid, or case-insensitively duplicates an existing
   sibling folder name, THEN THE Project_Service SHALL reject the rename, leave the folder
   unchanged, and return a Bridge_Response with `ok=false` whose error identifies the failed
   rule.
3. WHILE a project is in `PROD_READY` or `IMPLEMENTED`, THE System SHALL disable project rename
   and display a Disabled_State_Message naming the current state.
4. WHEN the user confirms a project delete, THE Project_Service SHALL move the project folder to
   the Recycle_Bin via `send2trash` through a JsApi project-delete method wired in
   `create_js_api()` and return a Bridge_Response with `ok=true` on success.
5. WHILE a project is in `PROD_READY` or `IMPLEMENTED`, THE System SHALL disable project delete
   and display a Disabled_State_Message naming the current state.
6. WHEN a project rename or delete completes successfully, THE System SHALL update the Cache_Db
   before returning `ok=true` so the dashboard reflects the change on next read.
7. WHEN the user confirms a subproject delete, THE Frontend SHALL call `subproject_delete`, and
   THE Project_Service SHALL move the subproject folder to the Recycle_Bin via `send2trash` and
   return `ok=true` on success.
8. IF `send2trash` fails during a project or subproject delete, THEN THE Project_Service SHALL
   leave the folder in place, SHALL NOT update the Cache_Db, and SHALL return a Bridge_Response
   with `ok=false`.

### Requirement 6: File Management

**User Story:** As the deployment engineer, I want to create, open, rename, and delete project
files, so that I can manage deployment evidence within the tool.

#### Acceptance Criteria

1. WHEN the user requests creating a file from a template, THE System SHALL create the file in
   the target project or subproject folder through a JsApi file-create-from-template method wired
   in `create_js_api()`.
2. WHEN the user requests creating a manual file, THE System SHALL create the file in the target
   folder through a JsApi file-create method wired in `create_js_api()`, validating the file name
   as non-empty, 1 to 255 characters, free of the characters `< > : " / \ | ? *`, and not a
   Windows reserved device name.
3. IF a file-create request specifies an invalid name or a name that already exists in the target
   folder, THEN THE System SHALL not create or overwrite a file and SHALL return a Bridge_Response
   with `ok=false`.
4. WHEN the user opens a file externally, THE Frontend SHALL call `file_open`, and THE file
   service SHALL open the file through the guarded OS open path.
5. WHERE the platform is not Windows, THE file service SHALL return a dev-skipped Bridge_Response
   for external open and SHALL NOT invoke `os.startfile`.
6. WHEN the user confirms a file rename, THE System SHALL rename the file through a JsApi
   file-rename method wired in `create_js_api()`, validating the new name against the same rules
   as file creation.
7. IF a file-rename target name is invalid or already exists in the target folder, THEN THE
   System SHALL leave the file unchanged and SHALL return a Bridge_Response with `ok=false`.
8. WHEN the user confirms a file delete, THE System SHALL move the file to the Recycle_Bin via
   `send2trash` through a JsApi file-delete method wired in `create_js_api()`.
9. IF a filesystem or `send2trash` operation fails during file create, rename, or delete, THEN
   THE System SHALL leave the target folder contents in their pre-operation state and SHALL return
   a Bridge_Response with `ok=false`.
10. WHILE a project is in `PROD_READY` or `IMPLEMENTED`, THE System SHALL disable file create,
    rename, and delete and display a Disabled_State_Message stating the action is disabled in the
    current state.
11. WHERE the target file is a note, THE System SHALL allow note editing in `PROD_READY` while
    keeping other file mutations disabled.
12. WHILE a project is in `IMPLEMENTED`, THE System SHALL present notes as view-only and SHALL
    reject note edit submissions without persisting them.

### Requirement 7: Windows Integration Guarding (Outlook and Teams)

**User Story:** As the deployment engineer, I want Windows-only integrations to load safely on
Linux and run only with explicit approval, so that development never triggers real COM or GUI
automation.

#### Acceptance Criteria

1. WHEN the Outlook_Client or Teams_Client module is imported on a non-Windows platform
   (`sys.platform != "win32"`), THE System SHALL complete the import without raising any
   exception (including ImportError) and without requiring any Windows-only dependency to be
   installed.
2. WHERE the runtime platform is not Windows (`sys.platform != "win32"`), THE Outlook_Client and
   Teams_Client SHALL return a Bridge_Response whose status indicates the action was skipped in a
   non-Windows environment, and SHALL NOT execute any COM, `pyautogui`, or `pyperclip` action.
3. THE System SHALL place every Windows-only import (COM, `pyautogui`, `pyperclip`) inside lazy
   code paths that are reached only when `IS_WINDOWS` (`sys.platform == "win32"`) evaluates to
   true.
4. WHEN a COM call executes on Windows, THE System SHALL run that call on a background thread that
   calls CoInitialize before any COM access and CoUninitialize before the thread terminates,
   including when the COM call raises an error.
5. IF a COM call on Windows raises an error, THEN THE System SHALL return a Bridge_Response whose
   status indicates failure with an error indication describing the failure, SHALL NOT leave COM
   initialized on the background thread, and SHALL NOT alter any other system state.
6. THE System SHALL NOT add, remove, or upgrade any dependency outside the PRD v3.1 approved
   baseline to enable Outlook or Teams integration.

### Requirement 8: Outlook Email Automation

**User Story:** As the deployment engineer, I want to draft and optionally send Outlook emails
from templates, so that I can communicate CR progress quickly while defaulting to safe drafts.

#### Acceptance Criteria

1. WHEN the user requests an Outlook email action, THE System SHALL default to Draft_First and
   create a draft email through a JsApi Outlook-draft method wired in `create_js_api()` without
   transmitting the email.
2. WHEN the user requests sending an Outlook email, THE Frontend SHALL present a Confirmation_UI
   and SHALL call a JsApi Outlook-send method only after explicit confirmation.
3. IF the user cancels or dismisses the send Confirmation_UI, THEN THE System SHALL NOT send the
   email and SHALL retain the existing draft.
4. THE System SHALL support the Template_Category values `ACK_UAT`, `ACK_SOP`, `APRVL_CR`, and
   `APRVL_SOP`, resolving the placeholders `{PROJECT_NAME}`, `{CR_NUMBER}`, `{CR_LINK}`,
   `{CR_STATE}`, `{DRONE_TICKET}`, `{DRONE_LINK}`, `{DRONE_STATE}`, `{START_DATETIME}`,
   `{END_DATETIME}`, `{IMPLEMENTATION_PLAN}`, and `{DISPLAY_NAME}` from project metadata.
5. IF a required placeholder cannot be resolved from project metadata, THEN THE System SHALL abort
   composition and return a Bridge_Response with `ok=false` identifying the unresolved
   placeholder.
6. WHERE a Template_Category defines conditions, THE System SHALL evaluate those conditions before
   composing the email, and IF the conditions are not met THEN THE System SHALL skip composition
   and return a skipped Bridge_Response indicating the reason.
7. WHEN the user requests a contacts lookup on Windows, THE Outlook_Client SHALL return contacts
   whose display name or email matches the lookup term, and WHERE the platform is not Windows, THE
   Outlook_Client SHALL return a dev fallback contact.
8. WHEN the user requests downloading reply emails or attachments on Windows, THE System SHALL
   retrieve them through the guarded Outlook_Client and store attachments under the target project
   folder; WHERE the platform is not Windows, THE System SHALL return a dev-skipped Bridge_Response
   indicating the action is unavailable.
9. IF an Outlook action fails at runtime, THEN THE System SHALL return a Bridge_Response with
   `ok=false` and surface the error in the UI without claiming the email was drafted or sent.

### Requirement 9: Teams Message Automation

**User Story:** As the deployment engineer, I want to send Teams messages via deep link and
clipboard by default, so that automated sending never happens without my explicit opt-in.

#### Acceptance Criteria

1. WHEN the user requests a Teams message action, THE System SHALL default to Preview_First by
   opening the Teams deep link and placing the message text on the clipboard through a JsApi Teams
   method wired in `create_js_api()`, and SHALL NOT trigger any automated keystroke or send
   action.
2. THE System SHALL initialize `teams_auto_send` to `false` whenever the setting is absent or
   unset.
3. WHERE `teams_auto_send` is `true` AND the user confirms auto-send through a confirmation UI,
   THE Teams_Client SHALL perform `pyautogui` auto-send on Windows only after a visible countdown
   equal to `countdown_seconds`, where `countdown_seconds` defaults to `3` and is constrained to
   an integer from `1` to `60` inclusive.
4. IF `countdown_seconds` is missing, non-integer, or outside the `1` to `60` inclusive range,
   THEN THE Teams_Client SHALL substitute the default value of `3` and SHALL proceed using that
   value.
5. WHILE the `pyautogui` FAILSAFE is enabled and triggered during the countdown or send, THE
   Teams_Client SHALL abort the auto-send, SHALL NOT dispatch the message, and SHALL return a
   Bridge_Response with `ok=false` indicating the send was cancelled.
6. WHILE the platform is not Windows (`sys.platform != "win32"`), THE Teams_Client SHALL return a
   dev-skipped Bridge_Response with `ok=true` and a skipped indicator, and SHALL NOT import or
   execute any `pyautogui` action.
7. IF a Teams action fails at runtime, THEN THE System SHALL return a Bridge_Response with
   `ok=false`, SHALL surface an error indication describing the failure in the UI, and SHALL leave
   `teams_auto_send` and the user's draft message unchanged.

### Requirement 10: Scheduler Control Surface

**User Story:** As the deployment engineer, I want frontend scheduler controls backed by real
APScheduler entries, so that I can manage alarms and automatic transitions safely.

#### Acceptance Criteria

1. THE Frontend SHALL render scheduler controls bound to `scheduler_status`, `scheduler_start`,
   `scheduler_stop`, and `scheduler_run_once`, displaying the running state as reported by
   `scheduler_status`.
2. WHEN the user creates a scheduler entry, THE System SHALL persist the entry through a JsApi
   scheduler-entry-create method wired in `create_js_api()` and SHALL store it under
   `settings.automation.scheduler.entries`.
3. WHEN the user edits or deletes a scheduler entry, THE System SHALL persist the change through
   the corresponding JsApi scheduler-entry method wired in `create_js_api()`.
4. IF a scheduler entry create, edit, or delete fails validation or persistence, THEN THE System
   SHALL reject the operation, retain the prior entry state, and surface an error indication in
   the UI.
5. WHEN the user pauses or resumes a scheduler entry, THE Scheduler_Service SHALL pause or resume
   the corresponding APScheduler job and persist the entry state.
6. WHEN a scheduler entry with an in-app channel triggers, THE System SHALL deliver the alarm
   through the Notification_Service.
7. WHERE a scheduler entry channel is Outlook or Teams, THE Frontend SHALL require a
   Confirmation_UI before the entry triggers a real Outlook or Teams action.
8. IF the user declines or dismisses the Confirmation_UI for an Outlook or Teams scheduler
   channel, THEN THE System SHALL NOT trigger the Outlook or Teams action.
9. WHEN a scheduler alarm triggers, THE Scheduler_Service SHALL apply the entry's project and
   state filters and SHALL act only on matching projects.
10. IF a triggered scheduler alarm matches no project after applying its filters, THEN THE
    Scheduler_Service SHALL take no action and SHALL record that no project matched.
11. THE Scheduler_Service SHALL preserve the existing 60-second auto IN-PROGRESS evaluation for CR
    and Drone tickets within their deployment window.

### Requirement 11: Rules Engine Persistence and Execution

**User Story:** As the deployment engineer, I want to define rules that run trigger-condition-
action sequences, so that repetitive automation runs consistently and is logged.

#### Acceptance Criteria

1. WHEN the user creates, edits, or deletes a rule, THE System SHALL persist the change to
   `settings.automation.rules_engine.rules` through a JsApi rule-CRUD method wired in
   `create_js_api()`.
2. IF a rule create or edit request is incomplete or specifies an unsupported trigger, condition,
   or action type, THEN THE System SHALL reject the request, leave the persisted rules unchanged,
   and return a Bridge_Response with `ok=false`.
3. WHEN a rule is evaluated, THE Automation_Service SHALL execute the rule as trigger, then
   condition, then action, in that order.
4. IF a rule's condition is not satisfied, THEN THE Automation_Service SHALL NOT execute the
   rule's actions.
5. THE Automation_Service SHALL support exactly the action types `download_email`,
   `save_attachment`, `update_cr_state`, `update_drone_state`, `send_outlook_email`,
   `send_teams_message`, `in_app_notification`, and `append_history`.
6. WHERE an action type performs an Outlook or Teams operation, THE Automation_Service SHALL apply
   the same Windows guarding and Draft_First/Preview_First defaults defined for Outlook and Teams
   automation.
7. WHEN a rule executes, THE Automation_Service SHALL write an Automation_Rule_Log entry to the
   SQLite `automation_rule_logs` table recording the rule identifier, outcome status, and
   timestamp.
8. WHEN multiple actions are defined for a rule, THE Automation_Service SHALL execute them in
   their defined order.
9. IF a rule action fails at runtime, THEN THE Automation_Service SHALL halt execution of the
   remaining actions, record the failure and the actions that completed in the Automation_Rule_Log,
   surface an error indication, and return a Bridge_Response with `ok=false`.

### Requirement 12: Persistent Automation and Notification Logs

**User Story:** As the deployment engineer, I want automation logs and notifications stored
durably, so that history survives application restarts and is auditable.

#### Acceptance Criteria

1. WHEN the Cache_Db is initialized, THE Cache_Db SHALL provide an `automation_rule_logs` table
   and a `notifications` table, each with its defined schema present and queryable.
2. WHEN the Automation_Service completes execution of a rule, THE System SHALL persist the
   execution result, including rule identifier, outcome status, and execution timestamp, to the
   `automation_rule_logs` table within 2 seconds of completion.
3. IF persisting an automation rule execution result to the `automation_rule_logs` table fails,
   THEN THE System SHALL retain the in-memory result and surface an error indication that the log
   write failed.
4. WHEN the Notification_Service creates a notification, THE System SHALL persist the notification,
   including its content, creation timestamp, and dismissed state, to the `notifications` table
   within 2 seconds of creation.
5. WHEN the application restarts, THE System SHALL load all persisted notifications from the
   `notifications` table, preserving each notification's previously stored dismissed state, so
   that prior notifications remain available with their correct state.
6. WHEN the user dismisses a notification, THE System SHALL persist the dismissed state for that
   notification to the `notifications` table within 2 seconds of the dismiss action.
7. IF persisting a notification create or dismiss operation to the `notifications` table fails,
   THEN THE System SHALL surface an error indication that the notification write failed and SHALL
   retain the prior persisted state without partial update.
8. WHEN the Cache_Db is rebuilt from initialization, THE System SHALL recreate the
   `automation_rule_logs` and `notifications` table schemas without requiring these tables to
   serve as the source of truth for project data.

### Requirement 13: Second Brain Pin/Favorite Persistence and Note CRUD

**User Story:** As the deployment engineer, I want durable pin/favorite metadata and full note
management in Second Brain, so that my knowledge base persists and is editable.

#### Acceptance Criteria

1. WHEN the user pins or favorites a Second Brain item, THE Frontend SHALL call `second_brain_pin`
   or `second_brain_favorite`, and THE Second_Brain_Service SHALL write the pin/favorite metadata
   to durable storage under the Second Brain folder before returning a success response to the
   caller.
2. IF persisting pin/favorite metadata fails, THEN THE Second_Brain_Service SHALL leave any
   previously persisted metadata unchanged and return a response indicating the persistence
   failure to the caller.
3. WHEN the application restarts, THE Second_Brain_Service SHALL restore all previously persisted
   pin and favorite metadata so that each restored item reflects the same pin and favorite state
   recorded before shutdown.
4. WHEN the user creates a Second Brain note with a unique target name, THE System SHALL create
   the note file under the Second Brain folder through a JsApi note-create method wired in
   `create_js_api()` and return a success response identifying the created note.
5. IF a note-create request targets a name that already exists under the Second Brain folder, THEN
   THE System SHALL not overwrite the existing file and SHALL return a response indicating the
   create failure.
6. WHEN the user writes or edits a Second Brain note, THE System SHALL persist the full content
   using an atomic write (write to a temporary file then replace the target) through a JsApi
   note-write method wired in `create_js_api()`, such that the original file content is retained
   unchanged if the write does not complete.
7. WHEN the user confirms deleting a Second Brain note through a confirmation UI, THE System SHALL
   move the note to the Recycle_Bin via `send2trash` through a JsApi note-delete method wired in
   `create_js_api()` and return a success response.
8. IF a note create, write, or delete operation fails, THEN THE System SHALL return a response
   indicating the failure and SHALL leave the Second Brain folder contents in their pre-operation
   state.
9. WHEN a Second Brain note is created, edited, or deleted, THE Second_Brain_Service SHALL update
   its search index so that the next `second_brain_list` or `second_brain_search` read reflects
   the current set of notes and their current content.

### Requirement 14: Windows Manual Test Gate and Packaging

**User Story:** As the release owner, I want a Windows manual test gate and Windows-only
packaging, so that the Release Candidate is verified on its target platform before distribution.

#### Acceptance Criteria

1. THE System SHALL require the Windows manual test gate to pass before any packaging step begins,
   executing the gate exclusively against a disposable test root and never against real project
   folders.
2. WHEN the Windows manual test gate runs, THE System SHALL verify that the WebView2 window loads
   the bundled Svelte output from `web/static/` via the pywebview HTTP server mode and not via raw
   `file://` production loading.
3. WHEN the Windows manual test gate runs, THE System SHALL verify that root paths saved through
   Settings are reloaded as the identical Windows path strings, with no Linux-style path
   normalization applied.
4. WHEN the Windows manual test gate runs, THE System SHALL verify that each of the six page
   checks (Dashboard, Project Details, Report, Settings, Second Brain, Automations) loads without
   runtime or bridge errors.
5. WHEN the Windows manual test gate runs, THE System SHALL confirm that each deferred high-risk
   action (folder transitions, file open/write/delete, Outlook/Teams/COM, scheduler real
   controls) presents a confirmation step before execution and displays an accurate disabled-state
   message while deferred.
6. IF any check in the Windows manual test gate fails, THEN THE System SHALL block all packaging
   steps and provide an indication identifying which check failed.
7. WHILE running on Windows, THE System SHALL perform PyInstaller packaging only after the Windows
   manual test gate has passed.
8. IF the host platform is not Windows, THEN THE System SHALL NOT run PyInstaller or any Windows
   packager, and SHALL provide an indication that packaging is unsupported on the current
   platform.
9. WHEN packaging on Windows, THE System SHALL include the Vite build output (`web/static/`) and
   `assets/` in the package.
10. IF packaging would require adding, removing, or upgrading any dependency, THEN THE System SHALL
    NOT proceed without explicit user approval.

### Requirement 15: Per-Change Verification

**User Story:** As the release owner, I want every change verified by the standard suite, so that
the Release Candidate stays green throughout deferred-work completion.

#### Acceptance Criteria

1. WHEN a change to deferred-scope code is completed, THE System SHALL run all four
   Verification_Suite checks (`svelte-check`, `vite build`, `pytest`, and `py_compile`) and SHALL
   consider the change complete only if every check reports zero errors and zero failures (success
   exit status) before any subsequent change is started.
2. WHEN automated tests exercise destructive filesystem behavior, THE tests SHALL perform all
   create, write, move, rename, and delete operations exclusively within a Temp_Root directory and
   SHALL NOT read, write, move, rename, or delete any real user folder, real project folder, or
   `project_data.json`.
3. WHEN an automated test that created a Temp_Root completes (whether it passes or fails), THE
   tests SHALL remove the Temp_Root and its contents so that no residual test artifacts remain on
   the filesystem.
4. WHEN automated tests exercise Windows-only integrations on Linux, THE tests SHALL assert that
   each integration is reported as guarded and dev-skipped, and SHALL NOT invoke any real COM,
   `pyautogui`, or `pyperclip` action.
5. IF any of the four Verification_Suite checks reports one or more errors or failures, or cannot
   be executed to completion, THEN THE System SHALL treat the change as incomplete and SHALL NOT
   report the affected feature as working.
6. WHEN reporting completion of a change, THE System SHALL report the exact list of
   Verification_Suite commands that were run with their pass/fail outcome, and SHALL explicitly
   state what was not verified, including Windows-only runtime behavior that requires the manual
   Windows test gate.
