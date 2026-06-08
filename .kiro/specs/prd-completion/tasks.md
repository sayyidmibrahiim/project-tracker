# Implementation Plan: PRD Completion (Release Candidate Deferred Work)

## Overview

This plan completes the deferred functionality of PRD v3.1 on top of the existing,
verified Release Candidate. The work is overwhelmingly **wiring existing `JsApi` methods to
real service logic** through the adapter pattern in `create_js_api()`
(`project_tracker/app_web.py`), plus a small set of **genuinely new** bridge methods that are
added to `project_tracker/web/js_api.py` and wired **before** any frontend call uses them
(Req 1.3).

Tasks are organized as incremental, independently-verifiable **slices** ordered to minimize
risk: frontend + filesystem safety foundations first, then folder/project/file mutations, then
persistence, then the Windows-only integrations, scheduler, and rules engine, and finally the
contract guard and the Windows manual/packaging gate.

Hard rules baked into every slice:

- Backend stays layered: `frontend → bridge only → services → core + infrastructure`.
- No new dependencies; no `js_api.py` signature changes except the proven T-10 optional keyword
  with a default (Task 5.2).
- No `window.pywebview` outside `frontend/src/lib/bridge.ts`.
- All destructive filesystem behavior is exercised **only against `Temp_Root` / `tmp_path`**,
  never real folders; deletion is `send2trash`-only.
- No Outlook/Teams/COM/`pyautogui`/`pyperclip` execution on Linux — guarded/dev-skipped only;
  real execution is Windows-manual.
- Do **not** edit root `CLAUDE.md`, `PRD.md`, or `MIGRATION_PLAN.md`.
- **Verification_Suite** (run after every slice, all four must pass):
  - `rtk npm --prefix frontend run check`
  - `rtk npm --prefix frontend run build`
  - `rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/ -q`
  - `rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m py_compile project_tracker/app_web.py project_tracker/web/js_api.py`

## Tasks

- [x] 1. Frontend safety foundation (bridge resilience + confirmation/disabled UI)
  - [x] 1.1 Harden `callBridge` in `frontend/src/lib/bridge.ts`
    - Add a 30-second timeout wrapper (`Promise.race`) that resolves to
      `{ ok: false, data: null, error: { code: "BRIDGE_TIMEOUT", message } }` on timeout.
    - Add a malformed-response guard: when the raw value is missing `ok`, or is `ok`-shaped but
      lacks consistent `data`/`error`, treat as failed with code `BRIDGE_MALFORMED_RESPONSE`.
    - Preserve existing `BRIDGE_UNAVAILABLE` / `BRIDGE_METHOD_MISSING` / `BRIDGE_CALL_FAILED`
      paths; keep all `window.pywebview` access inside this wrapper only.
    - _Requirements: 1.1, 1.8_
  - [x] 1.2 Write unit tests for `bridge.ts` timeout and malformed handling
    - Cover: timeout fires after 30s (faked timers), malformed/absent response → failed,
      well-formed `ok=false` passthrough, no success state on failure.
    - _Requirements: 1.7, 1.8_
  - [x] 1.3 Create `ConfirmModal.svelte`, `DisabledHint.svelte`, and `folderLocks.ts`
    - `frontend/src/lib/components/ConfirmModal.svelte`: props `title`, `actionLabel`,
      `targetName`, `reversible: boolean | "unknown"`, `onConfirm`, `onCancel`; renders explicit
      "This action is reversible/irreversible" (treat `"unknown"` as irreversible); issues no
      bridge call until `onConfirm`; cancel/dismiss restores prior state.
    - `frontend/src/lib/components/DisabledHint.svelte`: renders a disabled, non-interactive
      control with a message naming the Folder_State lock or the deferred status.
    - `frontend/src/lib/folderLocks.ts`: maps `project_state` → disabled actions (PROD_READY
      disables rename/delete/file-mutations; IMPLEMENTED disables all except notes view), mirroring
      PRD §9.5; backend remains the authoritative guard.
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_
  - [x] 1.4 Write component tests for `ConfirmModal`, `DisabledHint`, `folderLocks`
    - Cover: irreversible rendering for `"unknown"`, confirm vs cancel callback behavior, disabled
      message naming the lock, and `folderLocks` mapping per state.
    - _Requirements: 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

- [x] 2. Checkpoint - Run the Verification_Suite
  - Ensure all four Verification_Suite checks pass; ask the user if questions arise.

- [x] 3. Filesystem safety foundation (Temp_Root guard + atomic-write preservation)
  - [x] 3.1 Add `assert_within(base, target)` guard to `infrastructure/filesystem.py`
    - Raise a domain error when `target` does not resolve strictly within `base`; route every
      create/move/rename/delete helper through it; use `pathlib.Path` for all construction (no
      string concatenation); preserve Windows path strings verbatim.
    - _Requirements: 2.1, 2.3, 2.7, 2.9_
  - [x] 3.2 Add atomic-write failure-preservation path to `infrastructure/metadata_store.py`
    - Reuse the existing temp-file-then-replace write; add an explicit failure path that, when the
      write fails before the replace step, leaves the target file unchanged and returns an error
      indicating the write did not complete. Confirm `project_state` is never serialized.
    - _Requirements: 2.4, 2.5, 2.10_
  - [x] 3.3 Confirm single deletion route through `services/safe_delete_service.py`
    - Ensure `SafeDeleteService.delete_to_trash` is the only deletion path (via `send2trash`) for
      project/subproject/file/note; no hard delete anywhere.
    - _Requirements: 2.2_
  - [x] 3.4 Write property test for Temp_Root containment (**Property 1**)
    - **Property 1: No destructive op escapes Temp_Root** — for any generated target, a
      create/move/rename/delete resolves strictly within `Temp_Root` or is rejected with contents
      unchanged.
    - **Validates: Requirements 2.1, 2.9**
  - [x] 3.5 Write property test for atomic-write preservation (**Property 2**)
    - **Property 2: Atomic write preserves the original** — for any prior content and induced
      pre-replace failure, the target equals its pre-write content.
    - **Validates: Requirements 2.10**
  - [x] 3.6 Write property test for non-serialized `project_state` (**Property 3**)
    - **Property 3: `project_state` is never serialized** — for any `ProjectMetadata`, the written
      JSON contains no `project_state` key.
    - **Validates: Requirements 2.5**
  - [x] 3.7 Write property test for tz-aware datetime round-trip (**Property 4**)
    - **Property 4: Datetimes round-trip tz-aware** — any stored datetime reads back as a
      timezone-aware value with an explicit UTC offset.
    - **Validates: Requirements 2.6**
  - [x] 3.8 Write unit test for Windows path preservation
    - Assert Windows-formatted settings paths are stored verbatim (drive letter + backslashes) with
      no POSIX normalization.
    - _Requirements: 2.7_

- [x] 4. Checkpoint - Run the Verification_Suite
  - Ensure all four Verification_Suite checks pass; ask the user if questions arise.

- [x] 5. Folder state transitions (wire `_ProjectServiceAdapter` + T-10 override + rollback)
  - [x] 5.1 Implement transition logic in `services/project_service.py`
    - Ensure `move_to_prod_ready`, `move_to_implemented`, `postpone_project`, `cancel_project`,
      `resume_project`, `reopen_project` evaluate the documented guards (UAT→PROD_READY conjunction
      incl. T-10), append history entries (source/target/user/UTC timestamp, override flag where
      applicable), set CR_State on postpone/cancel/reopen, and reject disallowed sources and
      IMPLEMENTED→POSTPONED/CANCELED.
    - _Requirements: 4.2, 4.3, 4.4, 4.6, 4.7, 4.8, 4.10_
  - [x] 5.2 Wire `_ProjectServiceAdapter` transition hooks in `create_js_api()` (`app_web.py`)
    - For each existing `folder_*` method: load `AppSettings`, call the matching `ProjectService`
      method, map a blocked `GuardResult` → `ok=false` with joined reasons (T-10 fail emits a T-10
      violation notification), map success `Path` → update Cache_Db before `ok=true`, and wrap the
      physical move so a mid-move failure rolls back with no cache update and returns `ok=false`.
    - Add T-10 manual override as a new **optional keyword (`override_t10: bool = False`)** on the
      relevant path (the only proven-necessary signature change; update tests/docs in this slice).
    - _Requirements: 4.1, 4.5, 4.9, 4.11, 4.12, 1.8_
  - [x] 5.3 Write property test for guard-gated transitions and rollback (**Property 5**)
    - **Property 5: Folder transitions are guard-gated and reversible-on-failure** — a disallowed
      transition leaves state unchanged with `ok=false`; a mid-move failure rolls back with no cache
      update.
    - **Validates: Requirements 4.9, 4.12**
  - [x] 5.4 Write unit tests for each transition against a temp year/state tree
    - Cover T-10 block, T-10 manual override + history flag, move_to_implemented guard failure,
      IMPLEMENTED rejection, and cache update on success (all in `tmp_path`).
    - _Requirements: 4.2, 4.3, 4.4, 4.5, 4.10, 4.11_
  - [x] 5.5 Add gated transition actions to `Dashboard.svelte` (⋮ menu) and `ProjectDetails.svelte`
    - Each transition routed through `ConfirmModal`; T-10 failure surfaces an override confirmation
      path; `ok=false` shows `error.message` and leaves UI unchanged.
    - _Requirements: 3.1, 3.7, 4.1_
  - [x] 5.6 Write component tests for transition gating
    - Confirm no bridge call before confirm; cancel leaves state unchanged; error rendered on
      `ok=false`.
    - _Requirements: 3.1, 3.4, 3.7_

- [x] 6. Checkpoint - Run the Verification_Suite
  - Ensure all four Verification_Suite checks pass; ask the user if questions arise.

- [x] 7. Project rename/delete + subproject delete
  - [x] 7.1 Implement rename validation and delete routing in `services/project_service.py`
    - Use the existing `core` folder-name validator (non-empty, 1–255, forbidden `\ / : * ? " < > |`,
      reserved device names CON/PRN/AUX/NUL/COM1–9/LPT1–9, no trailing space/dot, case-insensitive
      sibling-duplicate check); route deletes to `SafeDeleteService.delete_to_trash`.
    - _Requirements: 5.1, 5.2_
  - [x] 7.2 Wire rename + add `project_delete` + wire `subproject_delete` (`js_api.py` + `app_web.py`)
    - Replace the `None` `rename_project` adapter hook with the real call; add new
      `JsApi.project_delete(project_path)` + adapter routing to `SafeDeleteService`; wire the
      existing `subproject_delete` adapter hook. Reject rename/delete in PROD_READY/IMPLEMENTED;
      update Cache_Db before `ok=true`; on `send2trash` failure leave the folder in place, skip
      cache update, return `ok=false`.
    - _Requirements: 5.3, 5.4, 5.5, 5.6, 5.7, 5.8_
  - [x] 7.3 Write property test for total name validation (**Property 6**)
    - **Property 6: Name validation is total** — any candidate name yields a definite valid/invalid
      result; never accepts forbidden chars, reserved names, trailing space/dot, empty, or >255.
    - **Validates: Requirements 5.1, 6.2**
  - [x] 7.4 Write unit tests for rename/delete/subproject-delete
    - Cover invalid/duplicate name rejection, locked-state rejection, `send2trash` failure
      preserving the folder, and cache update on success (all in `tmp_path`).
    - _Requirements: 5.2, 5.3, 5.5, 5.8_
  - [x] 7.5 Gate rename/delete/subproject-delete in the frontend
    - Route all three through `ConfirmModal` (irreversible styling for deletes); render
      `DisabledHint` naming the state in PROD_READY/IMPLEMENTED.
    - _Requirements: 3.1, 3.5, 5.3, 5.5_

- [x] 8. Checkpoint - Run the Verification_Suite
  - Ensure all four Verification_Suite checks pass; ask the user if questions arise.

- [x] 9. File management (create / create-from-template / open / rename / delete)
  - [x] 9.1 Add file helpers + name validation to `infrastructure/filesystem.py`
    - Implement create, create-from-template, rename, and delete-target helpers behind
      `assert_within`; validate names (1–255, forbidden `< > : " / \ | ? *`, reserved device names);
      all failures leave folder contents in their pre-operation state.
    - _Requirements: 6.2, 6.3, 6.9_
  - [x] 9.2 Add `_FileServiceAdapter` + new file methods (`js_api.py` + `app_web.py`)
    - Add `file_create(path, filename)`, `file_create_from_template(path, template_name)`,
      `file_rename(filepath, new_name)`, `file_delete(filepath)` and wire a new `_FileServiceAdapter`;
      reject existing names; route delete to `SafeDeleteService`; wire `file_open` to guarded
      `os.startfile` on Windows and a dev-skipped Bridge_Response off-Windows (no `os.startfile`).
      Enforce locks: create/rename/delete disabled in PROD_READY/IMPLEMENTED; notes editable in
      PROD_READY; notes view-only (reject edits) in IMPLEMENTED.
    - _Requirements: 6.1, 6.4, 6.5, 6.6, 6.7, 6.8, 6.10, 6.11, 6.12_
  - [x] 9.3 Write unit tests for file operations
    - Cover invalid/duplicate name rejection, off-Windows open dev-skip (no `os.startfile`),
      `send2trash`/filesystem failure preservation, and lock enforcement (all in `tmp_path`).
    - _Requirements: 6.3, 6.5, 6.7, 6.9, 6.10_
  - [x] 9.4 Gate file actions in the frontend (Project Details files area)
    - Route rename/delete through `ConfirmModal`; render `DisabledHint` for disabled states; show
      `error.message` on `ok=false`.
    - _Requirements: 3.1, 3.5, 6.10_

- [x] 10. Checkpoint - Run the Verification_Suite
  - Ensure all four Verification_Suite checks pass; ask the user if questions arise.

- [x] 11. Persistent automation and notification logs
  - [x] 11.1 Ensure `notifications` + `automation_rule_logs` schemas in `infrastructure/cache_db.py`
    - Confirm both tables are created on init and recreated on rebuild without becoming a source of
      truth.
    - _Requirements: 12.1, 12.8_
  - [x] 11.2 Persist notifications in `services/notification_service.py`
    - Persist on create and on dismiss; load all persisted notifications on startup preserving
      dismissed state; on write failure surface an error and retain prior persisted state without
      partial update.
    - _Requirements: 12.4, 12.5, 12.6, 12.7_
  - [x] 11.3 Persist rule executions in `services/automation_service.py`
    - Write each rule execution result (rule id, outcome status, timestamp) to
      `automation_rule_logs`; on write failure retain the in-memory result and surface an error.
    - _Requirements: 12.2, 12.3_
  - [x] 11.4 Write unit tests for log/notification persistence
    - Cover survive-restart load, dismissed-state persistence, and write-failure handling using a
      temp SQLite cache.
    - _Requirements: 12.3, 12.5, 12.6, 12.7, 12.8_

- [x] 12. Checkpoint - Run the Verification_Suite
  - Ensure all four Verification_Suite checks pass; ask the user if questions arise.

- [x] 13. Second Brain note CRUD + pin/favorite persistence
  - [x] 13.1 Add sidecar index + note CRUD logic to `services/second_brain_service.py`
    - Persist `{ item_id: { pinned, favorite } }` to an atomic sidecar
      `{second_brain_folder}/.project_tracker_index.json`; restore on startup; implement
      `create_note` (reject existing name), `write_note` (atomic temp-then-replace, original
      retained on failure), `delete_note` (`send2trash`); keep the search index consistent on next
      list/search; on persistence failure leave prior metadata/contents unchanged.
    - _Requirements: 13.1, 13.2, 13.3, 13.5, 13.6, 13.8, 13.9_
  - [x] 13.2 Add note methods + wire pin/favorite adapters (`js_api.py` + `app_web.py`)
    - Add `second_brain_note_create(parent, filename, content)`,
      `second_brain_note_write(filepath, content)`, `second_brain_note_delete(filepath)`; wire the
      existing `second_brain_pin` / `second_brain_favorite` adapters to the durable store.
    - _Requirements: 13.4, 13.7_
  - [x] 13.3 Write property test for pin/favorite round-trip (**Property 9**)
    - **Property 9: Pin/favorite persistence round-trips** — after any sequence of toggles, the
      restored state after reload equals the last toggled state.
    - **Validates: Requirements 13.1, 13.2, 13.3**
  - [x] 13.4 Write unit tests for note CRUD
    - Cover existing-name rejection, atomic-write preservation on failure, `send2trash` routing, and
      index update on create/edit/delete (in `tmp_path`).
    - _Requirements: 13.5, 13.6, 13.8, 13.9_
  - [x] 13.5 Add Notes CRUD + persistent toggles to `SecondBrain.svelte`
    - Create/edit/save/delete (delete gated by `ConfirmModal`); pin/favorite toggles persist; show
      `error.message` on failure.
    - _Requirements: 3.1, 13.4, 13.7_

- [x] 14. Checkpoint - Run the Verification_Suite
  - Ensure all four Verification_Suite checks pass; ask the user if questions arise.

- [ ] 15. Windows integration guarding + Outlook automation
  - [x] 15.1 Harden guarding + COM thread pattern in `outlook_client.py` and `teams_client.py`
    - Keep `IS_WINDOWS = sys.platform == "win32"`; ensure all `win32com`/`pythoncom`/`pyautogui`/
      `pyperclip` imports are lazy inside `IS_WINDOWS` branches so modules import cleanly on Linux;
      off-Windows calls return a dev-skipped Bridge_Response; COM runs on a background thread with
      `CoInitialize`/`CoUninitialize` in try/finally and never leaves COM initialized on error.
      No dependency changes.
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_
  - [x] 15.2 Reuse `EmailService` rendering/conditions + download path
    - Confirm `EmailService.render_email_template(metadata, category, settings)` resolves all
      placeholders for `ACK_UAT`/`ACK_SOP`/`APRVL_CR`/`APRVL_SOP`, aborts on an unresolved required
      placeholder (naming it), and evaluates Template_Category conditions (skip when unmet); confirm
      `download_email_service.py` stores attachments under the project folder.
    - _Requirements: 8.4, 8.5, 8.6, 8.8_
  - [x] 15.3 Add `outlook_*` methods + adapters (`js_api.py` + `app_web.py`)
    - Add `outlook_draft_email(category_code, project_path)` (Draft_First, no send),
      `outlook_send_email(category_code, project_path)` (called only after frontend confirmation),
      `outlook_get_contacts(query)` (Windows contacts; dev fallback off-Windows),
      `outlook_download_emails(project_path, …)` (guarded; dev-skipped off-Windows); runtime failure
      → `ok=false` without claiming drafted/sent.
    - _Requirements: 8.1, 8.2, 8.3, 8.7, 8.9_
  - [x] 15.4 Write property test for off-Windows guarding (**Property 10**)
    - **Property 10: Off-Windows guard never executes native automation** — for any Outlook/Teams
      call on a non-Windows platform, no COM/`pyautogui`/`pyperclip` is invoked and a dev-skipped
      response is returned.
    - **Validates: Requirements 7.2, 9.6**
  - [x] 15.5 Write unit tests for Outlook draft/send/contacts/download
    - Cover unresolved-placeholder abort, unmet-condition skip, dev fallback contact off-Windows,
      and dev-skipped download off-Windows.
    - _Requirements: 8.5, 8.6, 8.7, 8.8_
  - [x] 15.7 Add Outlook actions to the frontend (draft default; send gated)
    - Draft is default; send routed through `ConfirmModal`; cancel retains the draft; `ok=false`
      shows the error without success indication.
    - _Requirements: 3.1, 8.1, 8.2, 8.3, 8.9_

- [ ] 16. Checkpoint - Run the Verification_Suite
  - Ensure all four Verification_Suite checks pass; ask the user if questions arise.

- [ ] 17. Teams message automation
  - [x] 17.1 Implement preview/send + countdown + failsafe in `teams_service.py` / `teams_client.py`
    - Preview-First (deep link + clipboard, no keystroke); initialize `teams_auto_send=false` when
      absent; auto-send only when `teams_auto_send=true` after a visible countdown
      (`countdown_seconds` default 3, clamped 1–60, invalid→3); `pyautogui.FAILSAFE` abort →
      `ok=false`; off-Windows dev-skipped (no `pyautogui`); runtime failure leaves auto-send + draft
      unchanged.
    - _Requirements: 9.2, 9.3, 9.4, 9.5, 9.6, 9.7_
  - [x] 17.2 Add `teams_preview_message` + `teams_send_message` methods + adapters (`js_api.py` + `app_web.py`)
    - `teams_preview_message(...)` default Preview_First; `teams_send_message(...)` only when
      enabled + confirmed.
    - _Requirements: 9.1_
  - [x] 17.3 Write unit tests for Teams preview/send
    - Cover `teams_auto_send` default false, countdown clamp/invalid→3, FAILSAFE abort → `ok=false`,
      and off-Windows dev-skip with no `pyautogui` invocation.
    - _Requirements: 9.2, 9.3, 9.4, 9.5, 9.6_
  - [ ] 17.4 Add Teams actions to the frontend (preview default; auto-send gated)
    - Preview is default; auto-send routed through `ConfirmModal` and only offered when
      `teams_auto_send=true`.
    - _Requirements: 3.1, 9.1, 9.3_

- [ ] 18. Checkpoint - Run the Verification_Suite
  - Ensure all four Verification_Suite checks pass; ask the user if questions arise.

- [ ] 19. Scheduler control surface
  - [x] 19.1 Extend `services/scheduler_service.py` for entry CRUD + job management + filters
    - Persist entries under `settings.automation.scheduler.entries`; register/pause/resume/remove
      APScheduler jobs; on trigger apply project + state filters (act only on matches; no-match →
      record + no action); deliver in-app alarms via `NotificationService`; preserve the existing
      60-second auto IN-PROGRESS evaluation; validation/persistence failure → reject + retain prior.
    - _Requirements: 10.2, 10.3, 10.4, 10.5, 10.6, 10.9, 10.10, 10.11_
  - [ ] 19.2 Add `scheduler_entry_*` methods + adapters (`js_api.py` + `app_web.py`) - Add `scheduler_entry_list`, `scheduler_entry_create(data)`, `scheduler_entry_update(entry_id,
data)`, `scheduler_entry_delete(entry_id)`, `scheduler_entry_toggle(entry_id, enabled)`; signal
        that Outlook/Teams-channel entries require frontend confirmation before triggering, and do not
        trigger those actions when declined. - _Requirements: 10.7, 10.8_
  - [ ] 19.3 Write unit tests for scheduler entries
    - Cover create/edit/delete validation + persistence, pause/resume, filter match/no-match
      recording, and preservation of the 60-second auto IN-PROGRESS job.
    - _Requirements: 10.4, 10.5, 10.9, 10.10, 10.11_
  - [ ] 19.4 Bind scheduler controls in `Automations.svelte` (Scheduler tab)
    - Bind to `scheduler_status`/`scheduler_start`/`scheduler_stop`/`scheduler_run_once`; add an
      entry table with add/edit/delete/pause; gate Outlook/Teams channels with `ConfirmModal`.
    - _Requirements: 3.1, 10.1, 10.7_

- [ ] 20. Checkpoint - Run the Verification_Suite
  - Ensure all four Verification_Suite checks pass; ask the user if questions arise.

- [ ] 21. Rules engine persistence and execution
  - [x] 21.1 Implement execution engine in `services/automation_service.py`
    - Execute trigger → condition → action in order; skip actions when conditions unmet; support
      exactly the 8 action types (`download_email`, `save_attachment`, `update_cr_state`,
      `update_drone_state`, `send_outlook_email`, `send_teams_message`, `in_app_notification`,
      `append_history`); reuse Windows guarding + Draft_First/Preview_First for Outlook/Teams
      actions; write an `automation_rule_logs` row per execution; halt on first action failure,
      recording completed actions + the failure, and return `ok=false`.
    - _Requirements: 11.3, 11.4, 11.5, 11.6, 11.7, 11.8, 11.9_
  - [ ] 21.2 Add `rules_*` methods + adapters (`js_api.py` + `app_web.py`)
    - Add `rules_create(data)`, `rules_update(rule_id, data)`, `rules_delete(rule_id)`,
      `rules_toggle(rule_id, enabled)`, `rules_get_logs(rule_id, limit)`; persist under
      `settings.automation.rules_engine.rules`; reject incomplete/unsupported definitions leaving the
      store unchanged.
    - _Requirements: 11.1, 11.2_
  - [ ] 21.3 Write property test for action ordering halt-on-failure (**Property 8**)
    - **Property 8: Rule action ordering halts on failure** — actions execute in order, stop at the
      first failure, with completed actions and the failure recorded in `automation_rule_logs`.
    - **Validates: Requirements 11.8, 11.9**
  - [ ] 21.4 Write unit tests for rules CRUD + execution
    - Cover invalid/unsupported-definition rejection, unmet-condition skip, each action type, and
      log writing.
    - _Requirements: 11.2, 11.4, 11.5, 11.7_
  - [ ] 21.5 Add Rules CRUD + logs view to `Automations.svelte` (Rules tab)
    - Create/edit/delete/toggle + logs view; Outlook/Teams actions gated by `ConfirmModal`.
    - _Requirements: 3.1, 11.1_

- [ ] 22. Checkpoint - Run the Verification_Suite
  - Ensure all four Verification_Suite checks pass; ask the user if questions arise.

- [ ] 23. Bridge-contract integrity guard
  - [ ] 23.1 Reconcile frontend `callBridge` names against `create_js_api()` methods
    - Enumerate every `callBridge("…")` literal; ensure each maps to a real `JsApi` attribute on the
      object returned by `create_js_api()`; fix any drift (no invented contracts; no
      `window.pywebview` outside `bridge.ts`).
    - _Requirements: 1.1, 1.2, 1.3_
  - [ ] 23.2 Write the bridge-contract guard test
    - Assert every frontend `callBridge` name exists on the `create_js_api()` object and fail on any
      mismatch.
    - _Requirements: 1.2, 1.3_
  - [ ] 23.3 Write property test for universal Bridge_Response shape (**Property 7**)
    - **Property 7: Bridge_Response shape is universal** — every `JsApi` method returns a dict with
      an `ok` boolean; `ok=false` always carries an `error` whose `code` matches `^[A-Z0-9_]{1,64}$`.
    - **Validates: Requirements 1.4, 1.5, 1.6**

- [ ] 24. Checkpoint - Run the Verification_Suite
  - Ensure all four Verification_Suite checks pass; ask the user if questions arise.

- [x] 25. Windows manual test gate + packaging prep
  - [x] 25.1 Author/refresh the manual-test and packaging docs
    - Write/update `docs/release-candidate-manual-test-plan.md`,
      `docs/windows-manual-test-checklist.md`, and `docs/packaging-readiness.md` covering: WebView2
      load from bundled `web/static/`, Windows-path preservation, the six page checks, deferred
      high-risk action confirmation/disabled-state checks, and the block-packaging-on-failure rule.
      Document that the gate runs only against a disposable test root. (Doc task; Linux-authorable.)
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6_
  - [x] 25.2 Add Windows-only PyInstaller spec + non-Windows refuse guard
    - Create the PyInstaller spec bundling `web/static/` + `assets/`; add a platform guard that
      refuses to package (with a clear "unsupported on this platform" indication) when not on
      Windows; require explicit user approval before any dependency change. **Running PyInstaller is
      Windows-manual and NOT Linux-executable** — only the spec/guard files are created here.
    - _Requirements: 14.7, 14.8, 14.9, 14.10_

- [ ] 26. Final checkpoint - Run the full Verification_Suite
  - Ensure all four Verification_Suite checks pass; confirm Windows-only runtime behavior is
    explicitly listed as not verified (deferred to the manual Windows gate); ask the user if
    questions arise.

## Notes

- Tasks marked with `*` are optional test sub-tasks and can be skipped for a faster MVP; core
  implementation and wiring tasks are never optional.
- Task 25.2's PyInstaller execution and Task 25.1's manual gate execution are **Windows-only /
  manual** and not Linux-executable; only their artifacts (docs, spec, platform guard) are produced
  on Linux.
- Each slice references specific sub-requirement clauses for traceability and ends with a
  Verification_Suite checkpoint.
- Property tests map to design Correctness Properties: P1–P4 (slice 3), P5 (slice 5), P6 (slice 7),
  P9 (slice 13), P10 (slice 15), P8 (slice 21), P7 (slice 23). All destructive tests run only
  against `Temp_Root` / `tmp_path` and clean up; Windows-only tests assert guarded/dev-skipped
  behavior on Linux.
- New `JsApi` methods are added and wired in `create_js_api()` **before** any frontend call
  (Req 1.3). The only signature change is the optional `override_t10` keyword (Task 5.2), per the
  proven-necessary exception in Req 1.8.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.3", "3.1", "3.2", "3.3"] },
    {
      "id": 1,
      "tasks": [
        "1.2",
        "1.4",
        "3.4",
        "3.5",
        "3.6",
        "3.7",
        "3.8",
        "5.1",
        "11.1",
        "15.1",
        "25.1",
        "25.2"
      ]
    },
    {
      "id": 2,
      "tasks": [
        "5.2",
        "7.1",
        "9.1",
        "11.2",
        "11.3",
        "13.1",
        "15.2",
        "17.1",
        "19.1"
      ]
    },
    { "id": 3, "tasks": ["7.2", "5.3", "5.4", "5.5", "5.6", "11.4", "21.1"] },
    { "id": 4, "tasks": ["9.2", "7.3", "7.4", "7.5"] },
    { "id": 5, "tasks": ["13.2", "9.3", "9.4"] },
    { "id": 6, "tasks": ["15.3", "13.3", "13.4", "13.5"] },
    { "id": 7, "tasks": ["17.2", "15.4", "15.5", "15.7"] },
    { "id": 8, "tasks": ["19.2", "17.3", "17.4"] },
    { "id": 9, "tasks": ["21.2", "19.3", "19.4"] },
    { "id": 10, "tasks": ["21.3", "21.4", "21.5", "23.1"] },
    { "id": 11, "tasks": ["23.2", "23.3"] }
  ]
}
```
