# Automations Parity Slice Design

## Purpose

Execute the first bounded slice from `master-prompt.md`: audit the Automations page against `PRD.md` v3.1 section 16 and `redesign_ui/automations_redesign.py`, then implement one small, high-value gap only after the parity matrix identifies it.

## Sources of truth

1. `PRD.md` v3.1 section 16 is authoritative for product behavior.
2. `CLAUDE.md` is authoritative for operating constraints.
3. `redesign_ui/automations_redesign.py` and `redesign_ui/UI_FEATURE_DOCUMENTATION.md` are UX references only.
4. Current Svelte/Python/tests/docs describe implementation reality.

If any current code, status doc, or prototype behavior conflicts with PRD, report the contradiction before production code changes.

## Scope

This slice covers Automations only:

- Outlook tab
- Teams tab
- Scheduler tab
- Rules Engine tab
- Related frontend components and bridge/service tests only when needed for the selected gap
- `PROJECT_STATUS.md` status update after verification

The slice must not attempt full PRD completion. It must select one bounded implementation target after audit.

## Out of scope

- Real Windows Outlook COM execution
- Real Teams `pyautogui` execution
- PyInstaller packaging
- Windows release claims
- New dependencies
- Production PyQt work
- Full-app UI parity in one pass

## Required parity matrix

Create an Automations matrix with these columns:

| Requirement | PRD §16 behavior | PyQt prototype intent | Current Svelte behavior | Status | Chosen fix |
| ----------- | ---------------- | --------------------- | ----------------------- | ------ | ---------- |

Rows must cover at least:

- Tab order: Outlook, Teams, Scheduler, Rules Engine
- Outlook two-column send/download layout
- Email Template Dialog flow
- Downloaded Emails dialog
- Teams two-column layout
- Teams Automation Dialog / preview / send flow
- `teams_auto_send=false` default safety
- Scheduler KPI row
- Scheduler CRUD/status/action confirmation
- Rules Engine CRUD
- Rule execution logs
- Ordered rule actions
- Draft-first Outlook behavior
- Preview-first Teams behavior
- Windows-only guarded behavior

## Implementation selection rule

After matrix completion, choose the smallest high-value gap using this priority:

1. Missing user-visible flow from PRD §16.
2. Safety-critical behavior: draft-first, preview-first, confirmation/disabled state.
3. Backend/bridge already supports it or can support it with minimal code.
4. Testable on Linux without Windows APIs.
5. Does not add dependencies.

Likely candidates:

- Email Template Dialog frontend flow if absent or incomplete.
- Downloaded Emails dialog if absent or placeholder-only.
- Teams Automation Dialog preview/send safety copy if absent or incomplete.
- Scheduler action confirmation/persistence polish if incomplete.
- Rules per-rule logs/action ordering UI if incomplete.

The actual target must come from the matrix, not guesswork.

## Architecture

Frontend state remains UI-only:

- active tab
- dialog open/close state
- selected row/rule/entry
- draft form values
- loading/error/saved statuses

Python remains owner of:

- automation settings persistence
- scheduler entries
- rule evaluation and logs
- Outlook/Teams execution boundaries
- Windows-only guards

The Svelte Automations page may call only typed bridge methods through `callBridge`. Do not put business rules in Svelte beyond display, validation hints, and disabled-state messages.

## Data flow

1. Automations page loads `automation_overview` through bridge.
2. UI renders tabs and data from `AutomationOverview`.
3. User opens selected dialog/flow.
4. Save/preview/action calls existing bridge method if available.
5. Bridge returns `BridgeResponse`.
6. UI shows loading/success/error state.
7. On success, page refreshes overview.

For Windows-only actions, Linux behavior must remain guarded/skipped or preview-only with clear status. Do not claim execution happened on Linux.

## Error handling and safety

- All destructive or high-risk automation actions require confirmation or accurate disabled/deferred state.
- Outlook send-immediately must not run without confirmation.
- Teams send-immediately must remain gated by `teams_auto_send=true` and cancelable countdown when implemented.
- Bridge errors must show user-readable messages.
- Windows-only APIs must remain lazy-imported and guarded.

## Testing and verification

Minimum verification after implementation:

- `rtk npm --prefix frontend run build` if frontend changed.
- Existing targeted frontend tests when relevant.
- Relevant Python tests if bridge/backend changed.
- `rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m py_compile project_tracker/app_web.py project_tracker/web/js_api.py` if bridge/backend touched.

Report commands run, skipped checks, and Windows-only unverified gates.

## Documentation

Update `PROJECT_STATUS.md` with:

- Automations parity slice completed or audited.
- Implemented gap.
- Linux verification result.
- Windows-only gates still pending.

Do not update `PRD.md` unless user explicitly approves a PRD change.

## Approval gate

Implementation may start only after the user approves this design/spec and an implementation plan is created with `superpowers:writing-plans`.
