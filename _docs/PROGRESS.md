# Progress

> Single status source. Full history: `_docs/_archive/PROJECT_STATUS_history.md`

## Current Work

Phase labels are deprecated for active work. Work now follows `{menu}/{desc}` branches from `main`.

Active branch: `automations/approval-polling`.

Active work: **Automation System epic** (Outlook + General Automation). Spec: `_docs/specs/superpowers/specs/2026-07-08-automation-system-design.md`. 5 slices, PD-box-first; Piece C folded in (backend kept, PD UI replaced). Slices: 1 PD 3-group section · 2 PlaceholderResolver + Template per-CR + editor + Test · 3 Rules Engine goal-wizard + wire no-op actions + conflict detect + pre-seeded · 4 Auto Update CR State + Create Drone (Jenkins stub) + Teams followup · 5 Logs top-level menu + right-sidebar + retention.

**Slice 1 — PD Automations section (3-group)**: implemented, awaiting build gate + user manual check. Replaces the Piece C PD box with three groups (status dots 🟢🟡🔴⚪): **Automations Outlook** (Send Ack/LV rows: `[Send]` confirm→send, `[Draft]`→Outlook draft no-poll, `[Setting]`→Automations, short status label; auto-download toggle + `[Force Check Now]` + `[Stop]`; `[+ Add Email Automation]` stub), **Automation CR** (Auto Update CR State toggle persists flag; Create Drone Ticket `[Run]` Jenkins dev-stub), **Automation Teams** (2 followup rows + `[+ Add]`, dev-stubs). Backend: `send_request(mode)` draft/send split (draft = no poll, records `APPROVAL_DRAFT_OPENED`), `force_check` one-shot inbox scan, `set_auto_update_cr_state`; `ProjectMetadata.auto_update_cr_state` field; `get_status` gains `cr_number`+`auto_update_cr_state`. `[Open Setting]` navigates PD→Automations (`onNavigateAutomations`). CR+Teams groups + Add buttons are honest stubs (backend in Slices 2–4). Prior Piece C rework (approval-tab-removed, Outlook-tab template merge, tri-state `automation_enabled` + `automation_default_enabled` + `approval_auto_download` + `automation_locked`) remains in place beneath this.

**Slice 2 — PlaceholderResolver + per-CR templates + editor popup + Test**: implemented, awaiting user manual check. New `PlaceholderResolver` (reflective over `ProjectMetadata`/`DroneTicket`/`AppSettings` via `dataclasses.fields`) replaces hard-coded 11-token `_placeholder_values`; supports `{FIELD}`, `{NESTED.FIELD}`, `{DRONE.0.LINK}`; 11 required + 5 optional legacy aliases preserved so existing templates render unchanged; `available_tokens()` feeds the `{`-autocomplete with REAL preview values. Attachment resolution: `RenderedEmail.attachment_path` now computed from `EmailCategorySettings.attachment_template_file` + `EmailSettings.template_folder_path` (missing file → None + warn, render never fails). New `services/template_service.py` (pure merge/list/reset helpers). ApprovalPollingService gains `reset_template`, `list_templates`, `test_template` (opens real Outlook draft + records `APPROVAL_TEST_DRAFT_OPENED`), `autocomplete_tokens`. Bridge: `approval_reset_template`/`approval_list_templates`/`approval_test_template`/`approval_autocomplete_tokens` + bridge.ts wrappers. Frontend: `ApprovalTemplates.svelte` extended — `{` autocomplete dropdown (keyboard nav Arrow/Enter/Tab/Escape, filter-as-you-type), **Test** (open Outlook draft), **Reset to default** buttons; `AutomationsOutlook.svelte` accepts `openTemplateKind` deep-link prop; PD `[Setting]` (Outlook) passes kind → App.svelte `pendingTemplateKind` → Automations → Outlook editor popup. Decision: one project == one CR here, so per-project ≈ per-CR (no separate CR dimension — YAGNI).

**Slice 3 — Rules Engine goal-driven + wire no-op actions + scope + conflict + pre-seeded**: implemented, awaiting user manual check. `AutomationService` ctor gains `metadata_store` injection slot; 5 no-op handlers wired to real services — `_handle_update_cr_state`/`_handle_update_drone_state` validate via `core/state_machine` (DEFAULT AMAN: illegal transition → skip+log, never force; no target_state/project_path/metadata → skip), `_handle_append_history` writes `HistoryEntry`, `_handle_download_email`/`_handle_save_attachment` stay guarded no-op (Slice 4 wires real paths). `_RulesAdapter` gains `detect_conflicts()` (trigger+goal+scope signature; WARNING only, never blocks) + `seed_defaults()` (3 pre-seeded rules DISABLED by default: Send UAT Ack, Send LV Ack, Auto Update CR State; idempotent by `is_pre_seeded`+name). `rules_conflict_key()` module-level in `automation_service.py` (pure, testable, no webview dep). Bridge: `rules_detect_conflicts` + `rules_seed_defaults` (seed called at app `run()` start, not on every `create_js_api` — keeps test factories seed-free). `RulesServiceProtocol` extended. Frontend `RulesActions.svelte`: goal wizard (5 goals drive default action set), scope picker (All/Specific CR with cr_ids comma-list), conflict badge + pre-seeded badge in rule cards. PD deep-links: `[+ Add Email Automation]`→rules preset `send_email`; CR `[Setting]`→rules preset `auto_update_status`; `[+ Add Automation Teams]`→rules preset `send_teams` (via `onNavigateAutomations(kind, goal)` → App.svelte `pendingRuleGoal` → Automations rules tab → RulesActions form open with preset). **DEFERRED to Slice 4**: auto-reply dedup/rate-limit — the auto-reply send path lives in the Slice 4 engine; building dedup now = YAGNI (no sender yet).

2026-07-04 incident: post-manual-check fix round (active states, 5s countdown, hidden `.rte`, help popover, WYSIWYG page + resize) **rolled back in full** — user reported all editor behavior abnormal. Pipeline returned to first-manual-check state; fixes were later re-applied one at a time with user verify between each. See session-notes rollback entry + CLAUDE.md/AGENTS.md "RTE Change Safety".

Fix round v2 (steps 0–7, one behavior per round, user manual verify each): **complete 2026-07-06**. Step 0 watchdog `c94e387`, step 1 toolbar active states `65202cf`, steps 2–5b (5s idle countdown, hidden `.rte`, help popover, Narrow margins + clamp, WYSIWYG page + zoom) committed earlier, step 5c image drag-resize `4ca0abd`, step 6 SVG toolbar icons `b1cf0dc`, step 7 default TNR 18px↔13.5pt + per-file toolbar font/size memory `37d8ca7`. PRD §12.12 synced. **Branch merged to `main` 2026-07-06** (user approved; branch kept per user rule).

Piece B RTE format-aware follow-up: **user-verified and merged 2026-07-04** (`.md`/`.txt` editable, `.docx` read-only pending pipeline, interaction lock).

Previous completed area remains fixed: frameless titlebar, Dashboard, and Project Details layout decisions are implemented and should not be overwritten by `_reference/`.

## Roadmap to 100% (approved 2026-07-04)

Master plan: `_docs/specs/superpowers/plans/2026-07-04-completion-master-plan.md`.

| # | Branch | Scope | Status |
| - | ------ | ----- | ------ |
| 0 | `project-details/rte-interaction-bugs` | User verify RTE follow-up → commit → merge | ✅ Merged 2026-07-04 |
| 1 | `general/header-redesign` | Remove red `.app-header`, page-header becomes single header, red token unification, a11y | ✅ Merged 2026-07-04 |
| 2 | `project-details/tiptap-docx-pipeline` | flow-tiptap: docx source.json + python-docx export + image assets (paste Win+Shift+S) | ✅ Merged 2026-07-06 (incl. fix round v2 steps 0–7) |
| 3 | `automations/approval-polling` | Piece C approval automation (spec 2026-07-02) | Implemented, awaiting user manual check |
| 4 | `general/cicd-bitbucket` | Piece D CICD integration (spec 2026-07-02) | Planned |
| 5 | `general/professional-polish` | Color hygiene, a11y floor, responsive table, Phase D test debt, avatar initials | Planned |
| 6 | `general/packaging` | Windows verify sweep + PyInstaller (PRD Phase H) | Planned |

Locked decisions 2026-07-04: per-format RTE strategy (md/txt direct; docx pipeline), python-docx exporter (free/offline — office network blocks paid/online deps), red header removed (page-header is the only header), sequence pipeline → C → D.

## Active Blockers

- Windows-only runtime (Outlook COM, Teams pyautogui, os.startfile, PyInstaller) not yet verified — requires manual Windows testing.
- Avatar initials show "A" (single-part Windows username) instead of "AA" (Azzahra Ara) — Outlook COM not fully configured.

## Pending

| Area                | Status                  |
| ------------------- | ----------------------- |
| UX feature pack     | Done, pending user verify |
| Global App Plan     | Done, pending user verify |
| Report              | Done, pending user verify |
| Second Brain        | Done, pending user verify |
| Automations         | Done, pending user verify |
| Settings            | Done, pending user verify |
| Piece B CR docs RTE | ✅ User-verified + merged 2026-07-04 |
| Windows verify      | Not started (needs real Windows) |
| Packaging           | Not started |

## Last 4 Completed Slices

1. **Piece B CR Docs + .docx + Logging** (2026-07-03, branch `project-details/cr-docs-rte`): CR-only "Notes & CR Docs" section in Project Details with `<select>` dropdown (notes.md / uat-signoff.docx / prod-lv.docx / .msg). .docx storage via mammoth + htmldocx + python-docx. Export to Word button. Tiptap freeze fix (serialize at save-time, not per-keystroke). Professional AppData logging (backend + frontend activity). Multiple nav/lifecycle fixes. Known: RTE interaction bugs remain for follow-up.
2. **Piece A Appcode + CR/Non-CR structure** (2026-07-02, branch `general/appcode-structure-audit`): Dashboard 3 multi-select checklist filters; Add Project CR/Non-CR; appcode_add; Non-CR identity; Drone rename; lazy drone creation.
3. **UX feature pack** (2026-07-01, branch `general/ux-features`): Toast system, GlobalPlan/Report/SecondBrain inline feedback → toast store, Settings autosave, Undo toasts, TitleBar keyboard-shortcut popover, WelcomeGuide overlay.
4. **Production-readiness pass** (2026-07-01, branch `general/global-plan`): cross-menu fix sweep. Global Plan, Scheduler, Rules, Report, Second Brain, Link Bank, Settings improvements.

## Verification (latest — Automation System Slice 3, 2026-07-08)

```
svelte-check: 0 errors, 4 warnings (a11y non-interactive <li> onclick on autocomplete items — cosmetic)
frontend tests: 182 pass / 0 fail
targeted backend tests: 57 passed (phase_c automation + js_api + email render + resolver + slice3 handlers + conflict-key)
full pytest: 1850 passed, 20 skipped, 6 known baseline failures (no new fails)
build: ✓ (app was closed)
app smoke: ✓ clean
```

Slice 3 manual checklist (for user):
- [ ] Automations → Rules tab: 3 pre-seeded rules appear DISABLED (Send UAT Ack, Send LV Ack, Auto Update CR State), "seed" badge.
- [ ] `+ New rule` → pick Goal → action set auto-fills for that goal (e.g. Send New Email → send_outlook_email).
- [ ] "Applies to": All / Specific CR (enter CR IDs) saved + reloaded.
- [ ] Create 2 enabled rules with same trigger+goal+scope → both get "⚠ conflict" badge (warning, not blocked).
- [ ] Edit a rule with `update_cr_state` action → Execute with legal target_state → CR state changes + History entry; illegal target → skipped + logged (no force).
- [ ] PD `[+ Add Email Automation]` → Rules tab opens with form preset goal=send_email.
- [ ] PD CR group `[Setting]` → Rules tab opens with form preset goal=auto_update_status.
- [ ] PD `[+ Add Automation Teams]` → Rules tab opens with form preset goal=send_teams.

(Slice 2 manual checklist still applies — both slices shipped.)
