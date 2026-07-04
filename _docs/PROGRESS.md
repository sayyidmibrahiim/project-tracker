# Progress

> Single status source. Full history: `_docs/_archive/PROJECT_STATUS_history.md`

## Current Work

Phase labels are deprecated for active work. Work now follows `{menu}/{desc}` branches from `main`.

Active branch: `general/header-redesign`.
Active slice: **Header redesign (roadmap #1)** — remove red `.app-header` bar, per-page white `.page-header` becomes the single header, Dashboard controls relocate into its page-header, DateTime badge moves to TitleBar, red token unification + a11y quick wins.

Piece B RTE format-aware follow-up: **user-verified and merged 2026-07-04** (`.md`/`.txt` editable, `.docx` read-only pending pipeline, interaction lock).

Previous completed area remains fixed: frameless titlebar, Dashboard, and Project Details layout decisions are implemented and should not be overwritten by `_reference/`.

## Roadmap to 100% (approved 2026-07-04)

Master plan: `_docs/specs/superpowers/plans/2026-07-04-completion-master-plan.md`.

| # | Branch | Scope | Status |
| - | ------ | ----- | ------ |
| 0 | `project-details/rte-interaction-bugs` | User verify RTE follow-up → commit → merge | ✅ Merged 2026-07-04 |
| 1 | `general/header-redesign` | Remove red `.app-header`, page-header becomes single header, red token unification, a11y | Active |
| 2 | `project-details/tiptap-docx-pipeline` | flow-tiptap: docx source.json + python-docx export + image assets (paste Win+Shift+S) | Planned |
| 3 | `automations/approval-polling` | Piece C approval automation (spec 2026-07-02) | Planned |
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

## Verification (latest)

```
svelte-check: 0 errors, 0 warnings
frontend tests: 155 pass / 0 fail
RTE backend capability tests: 13 pass / 0 fail
bridge contract guard: 3 pass / 0 fail
app startup: no stdout/stderr traceback captured before 12s smoke was stopped
```
