# Piece C Design — Approval Automation (Email Polling + .msg Auto-download)

**Date:** 2026-07-02
**Author:** Sayyid M. Ibrahim
**Branch:** `automations/approval-polling` (branch from `main` after Piece A + B merge)
**Status:** Approved (pending implementation)
**Dependencies:** Piece A (project types, states, _cr-docs/) + Piece B (uat-signoff, prod-lv files exist)

---

## Context

Piece A created the folder structure + state machine. Piece B created the editable sign-off documents. Piece C adds the approval automation: conditional send-request buttons, email polling for replies, and auto-download of reply `.msg` files into `_cr-docs/`.

## Section 1: Automation Toggle & Conditional Buttons

### Automation on/off toggle

Project Details gets an automation toggle (on/off switch). When ON: app evaluates conditions and shows conditional buttons. When OFF: no buttons, no polling.

### "Send Request UAT Approval" button conditions (ALL must be true)

- Project type = CR
- At least 1 drone ticket exists
- Drone state = PENDING APPROVAL
- CR number exists (cr_link not empty)
- CR state = PENDING SUBMISSION
- `uat-signoff` file exists AND size > 0 bytes

### "Send Request LV" button conditions (ALL must be true)

- Project type = CR
- CR state = APPROVED AND/OR drone state = APPROVED (not every CR has a drone)
- `prod-lv` file exists AND size > 0 bytes

### Button behavior when clicked

1. Send email using project's approval template
2. Record: sent timestamp, CR number, email subject
3. Start polling for reply
4. Button → "Waiting for reply..." (disabled, countdown)
5. Reply found → auto-download .msg → "Approval received"
6. Timeout → "No reply received (timeout)"


## Section 2: Email Templates

Per-project in `project_data.json` — new field `approval_templates: dict`. Two keys: `uat_approval` and `lv_approval`. Each has: to, cc, subject (must contain {CR_NUMBER}), body, mode (draft/send).

Template editor in Automation menu: edit both templates, use placeholders ({CR_NUMBER}, {PROJECT_NAME}, {DRONE_NAME}, {START_DATETIME}, {END_DATETIME}), preview with real data.

Default templates: if project has no custom template, use global defaults from `settings.json` (`default_approval_templates`).

## Section 3: Email Polling

### Settings (global in settings.json)

- `approval_polling_interval_minutes: int = 5` (default 5 min)
- `approval_polling_max_hours: int = 3` (default 3 hours)
- Both configurable in Settings menu

### Polling mechanism

1. After sending: record `sent_at`, `cr_number`, `email_subject`
2. APScheduler job: every `interval_minutes` minutes
3. Poll Outlook inbox (COM, background thread with `pythoncom.CoInitialize()`):
   - Search: subject contains `cr_number` AND received datetime > `sent_at`
   - Found: download as .msg to `_cr-docs/`, stop polling, notification + toast
4. Max duration: `max_hours` from `sent_at`. Exceeded: stop, "timeout" notification

### Email matching: CR number in subject + timestamp

- Sent email subject template must include `{CR_NUMBER}` placeholder
- Polling searches inbox for emails with matching CR number in subject
- Only matches emails received AFTER request was sent
- Simple, fast, no Outlook thread API needed

### .msg download

- UAT approval reply -> `_cr-docs/uat-approval.msg`
- LV approval reply -> `_cr-docs/prod-approval.msg`
- Outlook COM `SaveAs` method (.msg format). If file exists, overwrite.

### Job state

`ApprovalPollingJob` (job_id, project_path, cr_number, request_type, sent_at, email_subject, status, reply_received_at). Persisted in SQLite table `approval_polling_jobs` — resumes on app restart.

## Section 4: Bridge & Frontend

New bridge methods: `send_uat_approval_request`, `send_lv_approval_request`, `get_approval_status`, `stop_approval_polling`, `get_approval_template`, `update_approval_template`.

Frontend: ProjectDetails (toggle + buttons + status), Automations/Settings (template editor + polling config).

## Section 5: Error Handling

| Edge case | Handling |
|-----------|----------|
| Outlook not available | Button disabled, "Outlook not configured" tooltip |
| Template missing | Use global default; if no default, button disabled |
| Email send fails | Error toast, polling not started |
| Polling: Outlook COM error | Retry next interval, log warning |
| Multiple matching emails | Download first match (oldest reply) |
| Project deleted while polling | Job cancelled on next scan |
| App closed while polling | Jobs resume on startup (persisted in SQLite) |
| uat-signoff empty (0 bytes) | Button not shown (condition not met) |

## Section 6: Testing

- `tests/test_approval_conditions.py` — button condition evaluation
- `tests/test_approval_template.py` — template storage + placeholder rendering
- `tests/test_approval_polling.py` — polling logic (mock Outlook COM)

Manual: create CR + drone -> set states -> fill uat-signoff -> verify button -> click -> verify email sent + polling -> simulate reply -> verify .msg downloaded -> verify timeout.

## Out of Scope

- CICD Bitbucket integration (Piece D)
- Multi-file RTE dropdown (Piece B — already done)