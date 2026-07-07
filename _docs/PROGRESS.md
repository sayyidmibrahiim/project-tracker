# Progress

> Single status source. Full history: `_docs/_archive/PROJECT_STATUS_history.md`

## Current Work

Phase labels are deprecated for active work. Work now follows `{menu}/{desc}` branches from `main`.

Active branch: `automations/approval-polling`.

Active work: **Automation System epic** (Outlook + General Automation). Spec: `_docs/specs/superpowers/specs/2026-07-08-automation-system-design.md`. 5 slices, PD-box-first; Piece C folded in (backend kept, PD UI replaced). Slices: 1 PD 3-group section · 2 PlaceholderResolver + Template per-CR + editor + Test · 3 Rules Engine goal-wizard + wire no-op actions + conflict detect + pre-seeded · 4 Auto Update CR State + Create Drone (Jenkins stub) + Teams followup · 5 Logs top-level menu + right-sidebar + retention.

**Slice 1 — PD Automations section (3-group)**: implemented, awaiting build gate + user manual check. Replaces the Piece C PD box with three groups (status dots 🟢🟡🔴⚪): **Automations Outlook** (Send Ack/LV rows: `[Send]` confirm→send, `[Draft]`→Outlook draft no-poll, `[Setting]`→Automations, short status label; auto-download toggle + `[Force Check Now]` + `[Stop]`; `[+ Add Email Automation]` stub), **Automation CR** (Auto Update CR State toggle persists flag; Create Drone Ticket `[Run]` Jenkins dev-stub), **Automation Teams** (2 followup rows + `[+ Add]`, dev-stubs). Backend: `send_request(mode)` draft/send split (draft = no poll, records `APPROVAL_DRAFT_OPENED`), `force_check` one-shot inbox scan, `set_auto_update_cr_state`; `ProjectMetadata.auto_update_cr_state` field; `get_status` gains `cr_number`+`auto_update_cr_state`. `[Open Setting]` navigates PD→Automations (`onNavigateAutomations`). CR+Teams groups + Add buttons are honest stubs (backend in Slices 2–4). Prior Piece C rework (approval-tab-removed, Outlook-tab template merge, tri-state `automation_enabled` + `automation_default_enabled` + `approval_auto_download` + `automation_locked`) remains in place beneath this.

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

## Verification (latest — Automation System Slice 1, 2026-07-08)

```
svelte-check: 0 errors, 0 warnings
frontend tests: 182 pass / 0 fail
targeted backend tests: 27 passed (phase_c automation + js_api)
full pytest: 1828 passed, 20 skipped, 6 known baseline failures
build: run after user closes app; app smoke pending
```
