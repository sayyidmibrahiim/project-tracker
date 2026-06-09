# Automations Parity Matrix

Audit of the Automations page against PRD §16 and the PyQt prototype, mapped to
current Svelte behavior. This matrix is the basis for selecting one bounded,
high-value implementation slice (see "Selected implementation target").

Sources:

- `PRD.md` §16 (lines 1530–1868) — product + behavior source of truth.
- `redesign_ui/automations_redesign.py` + `redesign_ui/UI_FEATURE_DOCUMENTATION.md`
  — UX reference only.
- `frontend/src/lib/components/Automations.svelte` (tab dispatcher).
- `frontend/src/lib/components/OutlookActions.svelte` (project-scoped Outlook).
- `frontend/src/lib/components/TeamsActions.svelte`.
- `frontend/src/lib/components/SchedulerActions.svelte`.
- `frontend/src/lib/components/RulesActions.svelte`.

| Requirement                               | PRD §16 behavior                                                                    | PyQt prototype intent                          | Current Svelte behavior                                                                  | Status              | Chosen fix                                                                                  |
| ----------------------------------------- | ----------------------------------------------------------------------------------- | ---------------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------- | ------------------------------------------------------------------------------------------- |
| Tab order                                 | §16.2 tab bar `[Outlook] [Teams] [Scheduler] [Rules Engine]`                         | Same order in `QTabWidget`                     | Rules, Outlook, Teams, Scheduler; defaults to Rules                                      | gap                 | Reorder dispatcher to Outlook, Teams, Scheduler, Rules Engine; default to Outlook           |
| Outlook two-column send/download layout   | §16.3 SEND AUTOMATION (left) + DOWNLOAD AUTOMATION (right); metrics row              | Two cards with send/download tables + logs     | Placeholder hero only on Automations page; project-scoped `OutlookActions` lives in PD   | gap                 | Add Automations Outlook scaffold: KPI row, two columns, logs, honest guarded action states  |
| Outlook KPI/metrics row                   | §16.3 `[Send Categories][Download Jobs][HTML Templates][On Going ACK][On Going Tech LV]` | Metrics row exists                          | Absent on Automations page                                                               | gap                 | Render the 5 PRD KPI tiles with current static/derived counts                               |
| Send categories                           | §16.3 ACK_UAT, ACK_SOP, APRVL_CR, APRVL_SOP                                          | 4-row send table                               | Absent on Automations page                                                               | gap                 | Render 4 PRD categories with purpose/conditions + Edit Template entry                       |
| Email Template Dialog flow                | §16.3 2-column dialog: category/to/cc/subject/body/attachment/mode/conditions/log    | `EmailTemplateDialog`                           | Implemented: `EmailTemplateDialog.svelte`, opened from Edit Template; loads/saves settings | done                | Persist via existing `settings_get`/`settings_update` (`email.categories[code]`); per-category send log deferred |
| Downloaded Emails dialog                  | §16.3 dialog lists subject/from/CR/date/tag, newest first, search/sort, expandable   | MessageBox placeholder                          | Absent from Automations page                                                             | gap (next slice)    | Add `Downloaded Emails` button calling real `outlook_download_emails`; full dialog next slice |
| Teams two-column layout                   | §16.4 automation (left) + status (right)                                            | Two-column layout + dialog                      | Single message form, preview-first, auto-send guarded                                    | partial             | Defer; safety already present                                                               |
| Teams Automation Dialog / preview / send  | §16.4 dialog with rules; preview default; auto-send gated + cancelable countdown     | `TeamsAutomationDialog`                          | Preview/send controls present; no saved-automation dialog/countdown                      | partial             | Defer after Outlook scaffold                                                                |
| `teams_auto_send=false` default           | §16.4 send-immediately only when `teams_auto_send = true`                            | Preview First mode                              | `TeamsActions` disables Send unless setting true                                         | done                | No change                                                                                   |
| Scheduler KPI row                         | §16.5 `[Due Soon][Overdue][Paused][Total Entries]`                                  | KPI row exists                                  | Status bar + entry cards, no KPI row                                                     | gap (deferred)      | Total/Paused derivable from entry `status`; Due Soon/Overdue need a next-run timestamp not in the entry payload — deferred (needs a backend serialized field) |
| Scheduler CRUD/status/action confirmation | §16.5 add/edit/pause/delete/run; Outlook/Teams channels need extra confirmation      | Table + Add Reminder                            | CRUD present; risky-channel trigger AND delete now gated behind ConfirmModal             | done                | Delete confirmation added (ConfirmModal, irreversible); arming issues no bridge call        |
| Rules Engine CRUD                         | §16.6 rule editor with info/trigger/conditions/actions                              | Table + Add Rule                                | CRUD present, limited trigger/condition editor                                           | partial             | Defer; already high-value enough                                                            |
| Rule execution logs                       | §16.6 latest 20 execution log                                                       | Static log textarea                             | Per-rule logs view exists                                                                | partial             | Defer global latest-20 log                                                                  |
| Ordered rule actions                      | §16.6 actions run top-to-bottom, log each, configurable skip-on-error               | Action list implied                             | Ordered UI + backend halt/continue execution present                                     | done                | No change                                                                                   |
| Draft-first Outlook                       | §16.3 draft default; send-immediately requires confirmation                         | Draft Only default                              | Project-scoped `OutlookActions` is draft-first; Automations page had no Outlook surface  | partial             | Scaffold Automations Outlook page with draft-first copy; send-config deferred with reason   |
| Preview-first Teams                       | §16.4 preview default; send gated                                                   | Preview First default                           | Implemented in `TeamsActions`                                                            | done                | No change                                                                                   |
| Windows-only guarded behavior             | §16.3–16.6 COM/pyautogui Windows-only, lazy/guarded                                 | Prototype is visual only                        | Backend/frontend report dev-skipped/off-Windows; imports guarded                         | done                | Preserve; new scaffold must not claim execution on Linux                                    |

## Selected implementation target

Per the spec's selection rule (missing user-visible PRD flow + safety-critical +
backend-supported + Linux-testable + no new deps), implement the smallest
high-value visible gap:

1. **Fix Automations tab order/default to PRD §16.2** (Outlook, Teams, Scheduler,
   Rules Engine; default Outlook).
2. **Add an Automations Outlook workspace scaffold** (`AutomationsOutlook.svelte`)
   with the §16.3 KPI row, two-column SEND/DOWNLOAD layout, send-category table,
   download-jobs table, per-column logs, draft-first safety copy, and the
   `Downloaded Emails` action wired to the real `outlook_download_emails` bridge
   method (guarded; browser preview stays read-only).

Deferred to explicit follow-up slices (each surfaced in-UI with an honest reason,
never hidden as done):

- Full searchable Downloaded Emails dialog.
- Per-category email send log (latest 10) inside the Email Template Dialog.
- Custom send categories beyond the four PRD-fixed codes.
- Teams Automation Dialog + cancelable countdown.
- Scheduler KPI row (Due Soon/Overdue require a next-run timestamp field that the entry payload does not yet serialize).
- Rules Engine trigger/condition editor depth + latest-20 global log.

### Slice 2 update (Email Template Dialog)

`EmailTemplateDialog.svelte` implements PRD §16.3: a modal with the left template
column (read-only category code, To, CC, Subject, Body, Attachment, Automation
Mode with draft-first default, and the 11 placeholder chips that insert at the
caret) and the right column (conditions grid using the backend-supported
`equals/not_equals/contains/exists` operators over
`project_name/cr_number/cr_link/cr_state/drone_count/implementation_plan`, a live
condition preview, and a deferred per-category log). It loads via `settings_get`
and saves via `settings_update` with a full-object round-trip that mutates only
`email.categories[code]` — no new bridge contract, no `js_api` signature change.
"+ Add Category" is an honest deferral (the four categories are fixed by the
settings model). Opened from the Outlook tab's Edit Template buttons.

## Constraints honored

- No backend/bridge signature changes in this slice.
- No new dependencies.
- No business logic moved into Svelte (UI state + display + disabled/deferred copy only).
- No Windows execution claimed on Linux; Outlook COM remains Windows-only/guarded.
- `outlook_download_emails` is a real `JsApi` method (`project_tracker/web/js_api.py`),
  so no API contract is invented.
