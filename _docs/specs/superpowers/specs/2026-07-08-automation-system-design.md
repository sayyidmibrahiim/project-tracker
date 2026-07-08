# Automation System — Design (Outlook + General Automation)

**Date:** 2026-07-08
**Author:** Sayyid M. Ibrahim (brainstorm), executed by Claude
**Branch base:** `automations/approval-polling` (Piece C backend kept; its PD box UI is replaced here — not merged separately)
**Status:** Approved. Slice 1 implemented; Slices 2–5 pending.
**Supersedes UI of:** `2026-07-02-approval-automation-design.md` (Piece C). The Piece C send/draft/poll/download backbone is reused as-is.

## Context

Piece C shipped approval send/poll/download but its Project Details box structure was rejected. A full brainstorm (user ↔ Grok) defined an Outlook + General Automation system. It is a multi-subsystem epic, decomposed into 5 slices, each spec→build→user-verify→approve.

### Philosophy (locked)
- **Project Details = per-CR operational control center** (quick Send/Draft, status, toggles, Force Check).
- **Automations menu = deep configuration** (Templates, Rules Engine).
- **Logs = its own top-level menu** (8th nav icon) + per-rule right-sidebar drilldown.
- CR is the relational center: a CR selects/overrides templates, not vice-versa.
- Minimize menus: everything email under Outlook, Teams under Teams.

### Locked decisions
1. Build order: **PD box first** (Slice 1), then PlaceholderResolver → Template → Rules → Logs.
2. Piece C: **fold into this design** (keep backend, replace PD UI, no separate merge).
3. Logs: **new top-level menu**; retention = purge when CR reaches FINISHED/CANCELED.
4. `[Send]` (immediate) is confirmed via ConfirmModal (irreversible outward); `[Draft]` is not.

## Reuse (do not rebuild)
- `services/approval_polling_service.py` — send/draft/poll/download `.msg` (Ack/LV).
- `services/email_service.py::render_email_template` — placeholder engine (hard-coded 11 tokens today; Slice 2 replaces with a reflective resolver).
- `services/automation_service.py` — Rules Engine execute + 8 action types + per-rule SQLite log (`automation_rule_logs`). `update_cr_state`/`update_drone_state`/`download_email`/`save_attachment`/`append_history` are **no-op stubs** to be wired in Slices 3–4.
- `automation_rule_logs` + `rules_get_logs` + `RulesActions.svelte` logs panel — foundation for the Logs sidebar.
- `infrastructure/teams_client.py` / `services/teams_service.py` — Teams send/preview.

## Decomposition

| # | Slice | Deliver |
| - | ----- | ------- |
| 1 | **PD Automations section (3-group)** | Correct structure; Outlook group wired to Piece C; CR+Teams groups structural + honest stubs routing to config. |
| 2 | PlaceholderResolver + Template per-CR overrides + editor popup + Test | Reflective resolver + `{`-autocomplete; attachment resolution; Outlook-like editor + CR dropdown; Save/Test/Reset. |
| 3 | Rules Engine goal-driven + wire no-op actions + applies-to + conflict detection + pre-seeded + auto-reply dedup | Goal wizard; scope All/Specific/Filtered CR; conflict warnings; pre-seeded rules; auto-send guard. |
| 4 | Auto Update CR State + Create Drone Ticket + Teams followup wired | Email-pattern → CR state (+History); Jenkins stub stays; Teams followup via template. |
| 5 | Logs top-level menu + right-sidebar + retention | 8th nav; per-module overview + filters; per-rule sidebar; purge on CR terminal. |

## Slice 1 — implemented

Replaces the PD `.pd-section` "Automations" with three groups (CR-only, hidden Non-CR + new-project mode). Header master toggle + terminal-state lock + dimmed `inert` body when effective-OFF (unchanged from Piece C rework). Status dots 🟢🟡🔴⚪ derived from job/eligibility.

- **Automations Outlook**: Send Ack Email / Send LV Email rows — `[Send]` (mode `send`, ConfirmModal), `[Draft]` (mode `draft`, opens Outlook draft, no poll), `[Setting]` (→ Automations), short status label; second line: `Auto-download reply` toggle + `[Force Check Now]` + `[Stop]` (while polling). `[+ Add Email Automation]` stub.
- **Automation CR**: `Auto Update CR State` toggle (persists `auto_update_cr_state`; engine Slice 4) + `[Setting]`; `Create Drone Ticket [Run][Setting]` (Jenkins dev-stub).
- **Automation Teams**: `Auto Followup Ack`, `Auto Followup Approval CR` — `[Send][Draft][Setting]` dev-stubs (Template system Slice 2); `[+ Add Automation Teams]` stub.

### Backend (Slice 1)
- `send_request(project_path, kind, mode=None)` — `mode='draft'` opens draft + records `APPROVAL_DRAFT_OPENED`, no job; `mode='send'` sends then polls when auto-download on, else records `APPROVAL_REQUEST_SENT`, no job; `mode=None` falls back to template mode.
- `force_check(project_path, kind)` — one-shot inbox scan for the latest polling job (Windows only); reuses `_match_and_save` (shared with the worker) via `_one_shot_check`; on match → `_on_found` (completed + notify).
- `set_auto_update_cr_state(project_path, enabled)` — persists `ProjectMetadata.auto_update_cr_state` (new field).
- `get_status` payload gains `cr_number` + `auto_update_cr_state`.
- Bridge: `send_uat/lv_approval_request(mode)`, `approval_force_check`, `approval_set_auto_update_cr_state`; `bridge.ts` `approvalSend/approvalForceCheck/approvalSetAutoUpdateCrState`; `ApprovalStatus` gains `cr_number` + `auto_update_cr_state`.
- Frontend: `ProjectDetails.svelte` 3-group markup + handlers + status-dot helpers; `App.svelte` wires `onNavigateAutomations`.

### Known limits (accepted)
- Draft never polls even when auto-download is ON (a draft is not sent yet). Intentional.
- Auto-download-OFF send has no persistent job, so the PD status dot cannot show "sent" after reload (toast covers it).
- `auto_update_cr_state` only persists a flag in Slice 1; the email-pattern engine is Slice 4.
- Force-check may race the worker's `SaveAs` (idempotent overwrite) — benign.

## Reference flows (Slices 2–5) — captured so nothing is lost

- **Placeholder/Template (2):** `PlaceholderResolver(template_text, metadata, settings, extra_context) -> (resolved, unresolved[])`; reflective discovery over `ProjectMetadata`/`DroneTicket`/`AppSettings`; `{FIELD}` / `{NESTED.FIELD}` (e.g. `{DRONE.0.LINK}`); replaces hard-coded `_placeholder_values`/`REQUIRED_PLACEHOLDERS`; attachment resolution (`attachment_template_file` + `EmailSettings.template_folder_path` → `RenderedEmail.attachment_path`). `{`-autocomplete with real value preview + keyboard nav. `Template{id,name,type,base_content{to,cc,subject,body,attachments},cr_overrides{cr_id:{...}}}`. Editor popup + CR dropdown (switch CR = switch content), Save/Test(open real Outlook draft, log "Test Draft Opened")/Reset-to-default. Template list: Name, Type, CR Override Count, Last Modified, Actions.
- **Rules Engine (3):** `+ New Rule` goal wizard (Send New Email / Auto Reply / Download Email / Auto Update Status / Send Teams). Mandatory "Applies to": All CR / Specific CR / Filtered CR. Conflict detection (warn on same trigger+goal+scope). Pre-seeded rules (Ack, LV, Auto Update Status). Auto Reply auto-sends when toggle ON but dedup/rate-limits against double-poll. Wire the 5 no-op actions. `Rule{id,name,goal,enabled,scope{type,cr_ids,filter},trigger{type,config},action{template_id,target_state,condition},is_pre_seeded}`. Test + Logs per rule.
- **CR/Teams (4):** Auto Update CR State from received-email pattern (from/subject/body, editable) → CR transition + History. Create Drone Ticket stays stub pending Jenkins. Teams followup via per-CR template + deeplink.
- **Logs (5):** top-level menu, per-module overview + sub-filters; PD/Rules `Logs` button → right sidebar (chronological, Refresh/Export/Clear); `LogEntry{id,rule_id,cr_id,timestamp,event_type,detail}` (extend `automation_rule_logs` or new table); purge/archive on CR FINISHED/CANCELED.

## Verification (Slice 1)
`pytest tests/test_phase_c_automation_service.py tests/test_phase_c_js_api_automations.py` (27 pass); full `pytest tests` (1828 pass + 6 known baseline fails); `npm run check` 0/0; `npm test` (182 pass); build + app smoke. Manual checklist in `_docs/PROGRESS.md`.
