# Progress

> Single status source. Full history: `_docs/_archive/PROJECT_STATUS_history.md`

## Current Work

Phase labels are deprecated for active work. Work now follows `{menu}/{desc}` branches from `main`.

Active branch: `automations/approval-polling`.

Active slice: **Piece C approval automation (roadmap #3, D-0013)** — implemented + UI rework after first user manual check, awaiting build gate + user manual re-check. Rework 2026-07-06 (user feedback): Approval tab deleted — template editor merged into Outlook tab SEND AUTOMATION (2 rows: Email Ack (UAT)=uat, Email LV (Prod)=lv; ACK_SOP/APRVL_SOP UI rows deleted, EmailTemplateDialog.svelte deleted, `settings.email.categories` data kept for outlook_draft/send_email); Project Details approval controls moved from command bar into dedicated CR-only "Automations" section (master toggle + lock hint, always-visible UAT/LV send rows, auto-download reply toggles, 6 dev-stub controls with toast). New fields: `automation_enabled` tri-state (null = inherit new `settings.automation_default_enabled`, toggled in Outlook tab), `approval_auto_download` per kind (OFF = send without polling job), `automation_locked` when CR State is FINISHED/POSTPONED/CANCELED. Migration quirk: legacy `automation_enabled: false` = explicit OFF, no inherit-reset UI. Base features unchanged: Outlook draft/send, SQLite polling jobs with resume, CR-number subject matching, `.msg` save to `_cr-docs/`, Settings polling interval/max fields.

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

## Verification (latest — Piece C UI rework 2026-07-06)

```
svelte-check: 0 errors, 0 warnings
frontend tests: 182 pass / 0 fail
targeted backend tests: 27 passed (phase_c automation/js_api + bridge contract)
full pytest: 1825 passed, 20 skipped, 6 known baseline failures
build: not run yet — waiting for user to close app before `npm run build`
```
