# Progress

> Single status source. Full history: `_docs/_archive/PROJECT_STATUS_history.md`

## Current Work

Phase labels are deprecated for active work. Work now follows `{menu}/{desc}` branches from `main`.

Active branch: `second-brain/complete-menu`. Second Brain completion Tasks 1–10 and final review-fix rounds are implemented. Automated Task 11 gate and production build are green; app relaunched for the mandatory user live checklist. No merge until live checks pass and user explicitly approves. D-0017.

**Second Brain completion (`second-brain/complete-menu`)**: zero-config Personal Notes defaults to `Documents\Project Tracker\Second Brain` while existing external overrides stay untouched. One cached filesystem index covers Personal plus eligible CR/Non-CR/Drone files and excludes CICD/internal/default metadata. Notes mounts Project Details `NotesEditor.svelte` unchanged; Personal supports guarded structural CRUD, while Project Documents disables create/rename/recycle but retains the shared editor's file capability and project-state locks. Pin/favorite/tags persist in atomic hidden sidecar metadata; activity is capped disposable SQLite cache. Link Bank now uses `LinkBankService` over atomic `link_bank.json`, stable IDs, soft archive/restore, and JSON/CSV export plus preview-confirmed atomic merge import. Production build is green; live verification remains open and branch is not merged.

**RTE height fix (2026-07-13, `971079b`)**: Second Brain RTE textarea was too short — didn't fill the editor column (empty space hung below). Root cause: `NotesEditor.svelte:1137` `.ne-root` is `display:flex` only with no `flex:1`/`min-height:0`, so it took content-height and the shared `.ne-textarea` cap (`max-height:300px` at line 1185) stayed in effect. Fix: scoped override in `SecondBrainNotes.svelte` `<style>` chaining `.sb-editor .ne-root -> .ne-editor-host -> .ne-textarea` to `flex:1 1 auto` with `max-height:none`. Selector `.sb-editor` only exists in `SecondBrainNotes.svelte`, so Project Details / other menus keep the 300px cap. Single file, +6 lines; NotesEditor.svelte, ProjectDetails.svelte, styles.css untouched. User manual PASS.

**Root folder bootstrap + appcode first-run (`general/root-folder-bootstrap`)**: user-verified and merged to `main` 2026-07-11. Backend `bootstrap_root()` runs before `create_js_api`: `root_folder=None` creates `Path.home()/Documents/Project Tracker`; non-default existing roots are force-moved to that default path; in-root absolute paths are rewritten in `settings.json`, `appcode.json` `cicd_shared_path`, and SQLite `notifications`/`approval_polling_jobs`; rebuildable cache tables (`project_index`, `drone_tickets`, `scan_warnings`) are cleared and rescanned; missing old roots create an empty default and clear cache; migration failure keeps the old root. `SettingsStore.write()` no longer creates legacy `{root}/{year}/{states}` folders. Frontend replaces FirstRunSetup with AppcodeSetup (min 1 appcode, no skip); existing `appcode_add` creates full worktree (`appcode.json`, `CICD/`, `{YEAR}/CR/{5 states}/Non-CR/`). Root Folder field removed from Settings; WelcomeGuide deleted after it overlapped first-run appcode popup. Verification: `test_bootstrap_service.py` 17 passed; related backend 23 passed; frontend 188 passed; svelte-check 0 errors/13 known warnings; build clean (chunk-size warning only); user confirmed all manual checks pass.

**Native window + responsive fixes (`general/window-responsive-fixes`)**: user-verified and merged to `main` 2026-07-11. Empty titlebar chrome now enters the Windows native caption loop for reliable drag + Aero Snap; second click and caption button toggle the real WinForms maximize/restore state; interactive chrome remains guarded. Edge/corner resize stays OS-owned with a 960×640 minimum and is disabled while maximized. Frameless `WM_NCCALCSIZE` removes the top frame, while `WM_GETMINMAXINFO` uses the active monitor's work area so maximization never covers a non-autohide taskbar. Responsive shell breakpoints align at ≤1024px. Dashboard's wide grid exposes panel-owned horizontal scrolling at minimum width without body overflow. D-0015.

**Titlebar selection-leak follow-up (`general/window-titlebar-selection`)**: user-verified and merged to `main` 2026-07-11. Root cause: second caption mousedown toggled maximize/restore without canceling WebView's default text-selection action; layout reflow could select the live clock, search placeholder, Dashboard heading, or first table text now under the pointer. `TitleBar.svelte` now calls `event.preventDefault()` after the interactive-child guard and before double-click handling, so caption gestures cannot select page text while search/input interaction remains native. Regression test observed RED then GREEN (27/27); full frontend 188/188; svelte-check 0 errors / 13 known warnings; production build clean (256 modules); user confirmed no selection regression and prior window behavior remains intact.

Active work: **Automation System epic** (Outlook + General Automation). Spec: `_docs/specs/superpowers/specs/2026-07-08-automation-system-design.md`. 5 slices, PD-box-first; Piece C folded in (backend kept, PD UI replaced). Slices: 1 PD 3-group section · 2 PlaceholderResolver + Template per-CR + editor + Test · 3 Rules Engine goal-wizard + wire no-op actions + conflict detect + pre-seeded · 4 Auto Update CR State + Create Drone (Jenkins stub) + Teams followup · 5 Logs top-level menu + right-sidebar + retention.

**Slice 1 — PD Automations section (3-group)**: implemented, awaiting build gate + user manual check. Replaces the Piece C PD box with three groups (status dots 🟢🟡🔴⚪): **Automations Outlook** (Send Ack/LV rows: `[Send]` confirm→send, `[Draft]`→Outlook draft no-poll, `[Setting]`→Automations, short status label; auto-download toggle + `[Force Check Now]` + `[Stop]`; `[+ Add Email Automation]` stub), **Automation CR** (Auto Update CR State toggle persists flag; Create Drone Ticket `[Run]` Jenkins dev-stub), **Automation Teams** (2 followup rows + `[+ Add]`, dev-stubs). Backend: `send_request(mode)` draft/send split (draft = no poll, records `APPROVAL_DRAFT_OPENED`), `force_check` one-shot inbox scan, `set_auto_update_cr_state`; `ProjectMetadata.auto_update_cr_state` field; `get_status` gains `cr_number`+`auto_update_cr_state`. `[Open Setting]` navigates PD→Automations (`onNavigateAutomations`). CR+Teams groups + Add buttons are honest stubs (backend in Slices 2–4). Prior Piece C rework (approval-tab-removed, Outlook-tab template merge, tri-state `automation_enabled` + `automation_default_enabled` + `approval_auto_download` + `automation_locked`) remains in place beneath this.

**Slice 2 — PlaceholderResolver + per-CR templates + editor popup + Test**: implemented, awaiting user manual check. New `PlaceholderResolver` (reflective over `ProjectMetadata`/`DroneTicket`/`AppSettings` via `dataclasses.fields`) replaces hard-coded 11-token `_placeholder_values`; supports `{FIELD}`, `{NESTED.FIELD}`, `{DRONE.0.LINK}`; 11 required + 5 optional legacy aliases preserved so existing templates render unchanged; `available_tokens()` feeds the `{`-autocomplete with REAL preview values. Attachment resolution: `RenderedEmail.attachment_path` now computed from `EmailCategorySettings.attachment_template_file` + `EmailSettings.template_folder_path` (missing file → None + warn, render never fails). New `services/template_service.py` (pure merge/list/reset helpers). ApprovalPollingService gains `reset_template`, `list_templates`, `test_template` (opens real Outlook draft + records `APPROVAL_TEST_DRAFT_OPENED`), `autocomplete_tokens`. Bridge: `approval_reset_template`/`approval_list_templates`/`approval_test_template`/`approval_autocomplete_tokens` + bridge.ts wrappers. Frontend: `ApprovalTemplates.svelte` extended — `{` autocomplete dropdown (keyboard nav Arrow/Enter/Tab/Escape, filter-as-you-type), **Test** (open Outlook draft), **Reset to default** buttons; `AutomationsOutlook.svelte` accepts `openTemplateKind` deep-link prop; PD `[Setting]` (Outlook) passes kind → App.svelte `pendingTemplateKind` → Automations → Outlook editor popup. Decision: one project == one CR here, so per-project ≈ per-CR (no separate CR dimension — YAGNI).

**Slice 3 — Rules Engine goal-driven + wire no-op actions + scope + conflict + pre-seeded**: implemented, awaiting user manual check. `AutomationService` ctor gains `metadata_store` injection slot; 5 no-op handlers wired to real services — `_handle_update_cr_state`/`_handle_update_drone_state` validate via `core/state_machine` (DEFAULT AMAN: illegal transition → skip+log, never force; no target_state/project_path/metadata → skip), `_handle_append_history` writes `HistoryEntry`, `_handle_download_email`/`_handle_save_attachment` stay guarded no-op (Slice 4 wires real paths). `_RulesAdapter` gains `detect_conflicts()` (trigger+goal+scope signature; WARNING only, never blocks) + `seed_defaults()` (3 pre-seeded rules DISABLED by default: Send UAT Ack, Send LV Ack, Auto Update CR State; idempotent by `is_pre_seeded`+name). `rules_conflict_key()` module-level in `automation_service.py` (pure, testable, no webview dep). Bridge: `rules_detect_conflicts` + `rules_seed_defaults` (seed called at app `run()` start, not on every `create_js_api` — keeps test factories seed-free). `RulesServiceProtocol` extended. Frontend `RulesActions.svelte`: goal wizard (5 goals drive default action set), scope picker (All/Specific CR with cr_ids comma-list), conflict badge + pre-seeded badge in rule cards. PD deep-links: `[+ Add Email Automation]`→rules preset `send_email`; CR `[Setting]`→rules preset `auto_update_status`; `[+ Add Automation Teams]`→rules preset `send_teams` (via `onNavigateAutomations(kind, goal)` → App.svelte `pendingRuleGoal` → Automations rules tab → RulesActions form open with preset). **DEFERRED to Slice 4**: auto-reply dedup/rate-limit — the auto-reply send path lives in the Slice 4 engine; building dedup now = YAGNI (no sender yet).

**Slice 4 — Auto Update CR State engine + Teams followup wired + auto-reply dedup**: implemented, awaiting user manual check. New `services/cr_state_engine.py`: pattern-gated email → CR transition. **DEFAULT AMAN: no patterns configured → engine NO-OP**; only user-set `from`/`subject`/`body` regex patterns (stored per-project in new `ProjectMetadata.auto_update_patterns` dict `{"from","subject","body","target_state"}`) trigger; all patterns must match (AND); invalid regex → no-match + warn; pattern match + legal transition (`core/state_machine.validate_cr_transition`) → state change + `AUTO_UPDATE_CR_STATE` History; pattern match + illegal transition → `AUTO_UPDATE_CR_STATE_BLOCKED` History + skip (never force). Engine wired into `ApprovalPollingService._on_found` (reply-received hook): reads metadata, runs engine, persists on transition; engine errors are swallowed (never break reply handling). Create Drone Ticket **STAYS stub** (Jenkins API deferred). Teams followup wired: PD Teams `[Draft]`→`teams_preview_message` (resolved followup text from CR+project_name), `[Send]`→ConfirmModal→`teams_send_message`, `[Setting]`→deep-link rules preset `send_teams`. Auto-reply dedup (Slice 3 deferred item): `AutomationService.execute_rule` checks `_recently_fired(rule_id, cr_id)` within 1h window for `goal='auto_reply'` rules → skip+log via `automation_rule_logs` cache; fail-open on cache error (rather over-send than block real reply).

**Slice 5 — Logs top-level menu + right-sidebar + retention**: implemented, awaiting user manual check. New `automation_logs` table (clean separation; `automation_rule_logs` untouched) + `AutomationLogRow`, `append_log`, `list_logs(module/cr_id/rule_id)`, `purge_logs_for_cr`, `clear_all_logs`, `clear_rule_logs`. `CacheDb` schema validation updated; cache tests updated. Bridge: `logs_list`, `logs_clear`, `rules_clear_logs`; `_RulesAdapter` exposes `list_logs`, `clear_logs`, `clear_rule_logs`. Retention hook in `_ProjectServiceAdapter._run_transition`: after successful move, if CR state FINISHED/CANCELED, purge `automation_logs` rows for that CR (POSTPONED kept because reversible). Frontend: 8th top-level nav **Logs** (App `PageId`, validPages, TitleBar `navItems`+icon, new `Logs.svelte` overview page with module cards + filters + Refresh/Clear). Rules `Logs` upgraded to right-sidebar drawer with Refresh/Export(JSON)/Clear/Close. PD Automations header gets `[Logs]` button → opens Logs page filtered by CR. **Decision:** right-sidebar implemented for Rules; PD uses top-level Logs filtered by CR (per-project, not per-rule), smallest correct diff.

**Piece D v2 — CICD Workbench (branch `general/cicd-bitbucket`)**: backend + UI rebuilt after manual-check rejection of the basic v1 page (flow/UI/scope). Awaiting user manual check. **Link-only clone flow**: user pastes a Bitbucket URL only; backend `parse_clone_url` derives the appcode candidate, `cicd_preview_link` shows repo/appcode/target/warnings, `cicd_clone_from_link(clone_url, appcode_override, confirm_create)` matches an existing appcode (case-insensitive, preserves on-disk spelling) or — only after ConfirmModal — creates the full D-0008 tree via the existing `add_appcode` path, then clones `git clone -b cicd --single-branch`. Same-remote existing repo returns `status:"exists"` (no re-clone); different-remote blocks. Backend-owned safety: **repo IDs** are `base64url({appcode,repo})` (frontend never sends write paths); every resolved path is asserted inside the appcode CICD dir; file read/save rejects absolute/`..`/`.git`/binary/>1 MiB, is UTF-8 only, hash-guarded (`STALE_FILE`), atomic temp-write, and blocked unless branch==`cicd`; `run_git` uses `shell=False` + list args + `CREATE_NO_WINDOW` + `GIT_TERMINAL_PROMPT=0` + timeouts. **Safe git actions** (`cicd_git_action` allowlist): stage/unstage/commit-selected (message required), pull `--ff-only` (blocked when dirty), push `origin cicd` (never force, ConfirmModal), sync (behind→pull, ahead→push, equal→no-op, dirty/diverged→block), refresh. Bridge: `cicd_preview_link`/`cicd_clone_from_link`/`cicd_job`/`cicd_workspace`/`cicd_repo_status`/`cicd_list_files`/`cicd_file_read`/`cicd_file_save`/`cicd_git_action` + typed `bridge.ts` wrappers. **UI**: `CICDBrowser.svelte` rebuilt as a VSCode-like Red-Binder workbench — clone bar + preview card, Explorer (appcode select + repos + file tree), Editor (`CICDCodeEditor.svelte` = **CodeMirror 6**, locally bundled, no CDN — user-approved dep 2026-07-09; YAML/JSON/JS/TS/Python/Markdown by extension, Ctrl+S save, dirty dot, stale-reload banner, read-only card for binary/large/non-cicd), Source Control (branch pill, ahead/behind, changed-file checkboxes, commit/push/pull/sync, output tail); responsive 3-pane ≥1360 / 2-pane 960–1359 / single-column tabs <960. Fix: `app_web` now imports pywebview lazily (module attr) so headless imports stay webview-free (CICD test suite exposed the latent contract break). D-0014. Create Drone Ticket (Jenkins) still out of scope. Superseded v1 note below.

**Piece D v1 (superseded by v2 above)**: initial basic page — appcode dropdown + clone URL + repo list + file tree + open-external. Rejected on manual check (appcode-first flow, unpolished UI, no editing/git). New 9th top-level nav **CICD** (git-branch icon) → full-page `CICDBrowser.svelte`. New `services/cicd_service.py` (stdlib `subprocess`/`shutil` only — no new dep, per office-offline constraint; **first subprocess in the app**, sets `CREATE_NO_WINDOW` precedent so git never flashes a console): `check_git()` detection, `parse_repo_name`, `parse_porcelain` (XY→modified/untracked/staged), `build_file_tree` (recursive, `.git` skipped, dirs-first), and `CicdService` that clones branch `cicd` on a **daemon thread** (`git clone -b cicd --single-branch`) with a poll-able job dict (`start_clone`→`clone_status`), plus `list_repos` (per-repo status summary) + `list_files`. Bridge: `CicdServiceProtocol` + `cicd_git_status`/`cicd_clone`/`cicd_clone_status`/`cicd_list_repos`/`cicd_list_files`; nested `_CicdServiceAdapter` in `create_js_api` reuses `_AppCodeServiceAdapter.get_appcode_config` to resolve each appcode's CICD dir (`per_appcode` → `{appcode}/CICD`, `shared_root` → `AppCodeConfig.cicd_shared_path`). Frontend polls `cicd_clone_status` every 1.2s (mirrors the RTE export poll), toasts on done/error; file click reuses the existing `file_open` bridge (no new `open_repo_file`); file badges use `.dot-waiting` (orange = modified) / `.dot-done` (green = untracked/staged). **DEFAULT AMAN:** git absent → install-steps empty state + Recheck (never crash); non-git folder / porcelain failure → files shown without status; clone into an existing folder → rejected before spawning. CICD-location switch (per-appcode ↔ shared root) lives on the CICD page via `appcode_update_config` (config is per-appcode, not global Settings). **Deviations from spec (deliberate):** config UI on CICD page not Settings; reuse `file_open`; ONE consolidated `tests/test_cicd_service.py` not three; folder names strip `.git` + clone adds `--single-branch`; directory nodes carry no aggregate badge (files only). D-0014 recorded. Create Drone Ticket (Jenkins) remains out of scope.

2026-07-04 incident: post-manual-check fix round (active states, 5s countdown, hidden `.rte`, help popover, WYSIWYG page + resize) **rolled back in full** — user reported all editor behavior abnormal. Pipeline returned to first-manual-check state; fixes were later re-applied one at a time with user verify between each. See session-notes rollback entry + CLAUDE.md/AGENTS.md "RTE Change Safety".

Fix round v2 (steps 0–7, one behavior per round, user manual verify each): **complete 2026-07-06**. Step 0 watchdog `c94e387`, step 1 toolbar active states `65202cf`, steps 2–5b (5s idle countdown, hidden `.rte`, help popover, Narrow margins + clamp, WYSIWYG page + zoom) committed earlier, step 5c image drag-resize `4ca0abd`, step 6 SVG toolbar icons `b1cf0dc`, step 7 default TNR 18px↔13.5pt + per-file toolbar font/size memory `37d8ca7`. PRD §12.12 synced. **Branch merged to `main` 2026-07-06** (user approved; branch kept per user rule).

Piece B RTE format-aware follow-up: **user-verified and merged 2026-07-04** (`.md`/`.txt` editable, `.docx` read-only pending pipeline, interaction lock).

Previous completed area remains fixed: frameless titlebar, Dashboard, and Project Details layout decisions are implemented and should not be overwritten by `_reference/`.

## Verification (latest — Second Brain automated gate, 2026-07-13)

```
focused backend: 301 passed
Second Brain frontend contract: 93 passed / 0 failed
full frontend suite: 281 passed / 0 failed
svelte-check: 0 errors, 13 known a11y warnings
focused Python compile: ✓
git diff --check: ✓
production build: ✓ (256 modules; known a11y/chunk-size warnings only)
user live checklist: pending
```

## Roadmap to 100% (approved 2026-07-04)

Master plan: `_docs/specs/superpowers/plans/2026-07-04-completion-master-plan.md`.

| # | Branch | Scope | Status |
| - | ------ | ----- | ------ |
| 0 | `project-details/rte-interaction-bugs` | User verify RTE follow-up → commit → merge | ✅ Merged 2026-07-04 |
| 1 | `general/header-redesign` | Remove red `.app-header`, page-header becomes single header, red token unification, a11y | ✅ Merged 2026-07-04 |
| 2 | `project-details/tiptap-docx-pipeline` | flow-tiptap: docx source.json + python-docx export + image assets (paste Win+Shift+S) | ✅ Merged 2026-07-06 (incl. fix round v2 steps 0–7) |
| 3 | `automations/approval-polling` | Piece C approval automation + Automation System epic Slices 1–5 | ✅ Merged 2026-07-08 |
| 4 | `general/cicd-bitbucket` | Piece D CICD Workbench v2 (link-only clone, editing, safe git) | Merged to `main` 2026-07-09 (manual check passed) |
| 4a | `general/window-responsive-fixes` | Native frameless window behavior + responsive/table overflow fixes | ✅ Merged 2026-07-11 (user-verified; branch kept) |
| 5 | `general/professional-polish` | Remaining color hygiene, a11y floor, Phase D test debt, avatar initials | Planned |
| 6 | `general/packaging` | Windows verify sweep + PyInstaller (PRD Phase H) | Planned |

Locked decisions 2026-07-04: per-format RTE strategy (md/txt direct; docx pipeline), python-docx exporter (free/offline — office network blocks paid/online deps), red header removed (page-header is the only header), sequence pipeline → C → D.

## Active Blockers

- Windows-only integrations (Outlook COM, Teams pyautogui, os.startfile, PyInstaller) not yet verified — requires separate manual Windows testing. Native shell/window behavior is verified.
- Avatar initials show "A" (single-part Windows username) instead of "AA" (Azzahra Ara) — Outlook COM not fully configured.

## Pending

| Area                | Status                  |
| ------------------- | ----------------------- |
| UX feature pack     | Done, pending user verify |
| Global App Plan     | Done, pending user verify |
| Report              | Done, pending user verify |
| Second Brain        | Implemented + automated/build green; user live gate pending |
| Automations         | Done, pending user verify |
| Settings            | Done, pending user verify |
| Piece B CR docs RTE | ✅ User-verified + merged 2026-07-04 |
| Windows integrations verify | Not started (needs separate live checks) |
| Packaging           | Not started |

## Last 4 Completed Slices

1. **Piece B CR Docs + .docx + Logging** (2026-07-03, branch `project-details/cr-docs-rte`): CR-only "Notes & CR Docs" section in Project Details with `<select>` dropdown (notes.md / uat-signoff.docx / prod-lv.docx / .msg). .docx storage via mammoth + htmldocx + python-docx. Export to Word button. Tiptap freeze fix (serialize at save-time, not per-keystroke). Professional AppData logging (backend + frontend activity). Multiple nav/lifecycle fixes. Known: RTE interaction bugs remain for follow-up.
2. **Piece A Appcode + CR/Non-CR structure** (2026-07-02, branch `general/appcode-structure-audit`): Dashboard 3 multi-select checklist filters; Add Project CR/Non-CR; appcode_add; Non-CR identity; Drone rename; lazy drone creation.
3. **UX feature pack** (2026-07-01, branch `general/ux-features`): Toast system, GlobalPlan/Report/SecondBrain inline feedback → toast store, Settings autosave, Undo toasts, TitleBar keyboard-shortcut popover, WelcomeGuide overlay.
4. **Production-readiness pass** (2026-07-01, branch `general/global-plan`): cross-menu fix sweep. Global Plan, Scheduler, Rules, Report, Second Brain, Link Bank, Settings improvements.

## Verification — Automation System Slice 5 (2026-07-08)

```
svelte-check: 0 errors, 4 warnings (a11y autocomplete <li> — cosmetic)
frontend tests: 182 pass / 0 fail
targeted backend tests: 78 passed (incl. automation_logs + cache schema + rules + CR state engine)
full pytest: 1864 passed, 20 skipped, 6 known baseline failures (no new fails)
build: ✓ (app was closed)
app smoke: ✓ clean
```

Slice 5 manual checklist (for user):
- [ ] TitleBar shows 8 nav items including **Logs** icon; clicking it opens Logs page.
- [ ] Logs page shows overview cards (All/Outlook/Teams/CR Automation/Rules Engine), module filter, CR filter, Refresh, Clear all.
- [ ] Rules tab → click a rule's `Logs` → right sidebar opens; Refresh/Export/Clear/Close work.
- [ ] PD Automations header `[Logs]` → opens Logs page filtered by that CR.
- [ ] Retention: transition CR to FINISHED/CANCELED → `automation_logs` entries for that CR purge; `automation_rule_logs` remains untouched.

Combined manual checklist — Slices 2–5:
- [ ] Slice 2: Template `{` autocomplete real values + keyboard nav; Save/Test/Reset; PD Outlook `[Setting]` deep-links editor; legacy placeholders still render; attachment path works.
- [ ] Slice 3: Pre-seeded rules disabled; goal wizard + Applies-to scope; conflict warning; wired update_cr_state mutates legally and skips illegally; PD add buttons preset rules.
- [ ] Slice 4: Auto-update CR state no-op without patterns; pattern match transitions only legal states; Teams Draft/Send/Setting wired; auto-reply dedup skips repeat within 1h.
- [ ] Slice 5: Logs nav/page/sidebar/retention all work.

### Piece D v2 — CICD Workbench (branch `general/cicd-bitbucket`, 2026-07-09)

```
svelte-check: 0 errors, 4 warnings (pre-existing a11y <li> — cosmetic), 174 files
frontend tests: 185 pass / 0 fail (CICD v2 source-contract + CodeMirror editor contract)
targeted backend tests: tests/test_cicd_service.py 51 passed
full pytest: 1915 passed, 20 skipped, 6 known baseline failures (test_phase_c_js_api_project x3, test_phase_d_app_web_project_service_adapter x1, test_year_create x2) — NO new fails
build: ✓ (app closed 2026-07-09; CodeMirror bundles locally; pre-existing >500 kB chunk warning only)
app smoke: not yet run for v2 — user restarts app after fresh build
```

Commits (v2): `cf7024f0` preview+appcode-resolve · `b0323ebd` clone-from-link+auto-create · `19c919cc` safe status/workspace · `29295b5b` file read/save · `280f76ec` safe git actions · `72d7a417` link-only workbench UI + CodeMirror + SCM · `61a6ecab` lazy pywebview import fix.

Piece D v2 manual checklist (for user — after `npm run build` + app restart):
- [ ] **Flow**: paste a Bitbucket clone link only (no appcode dropdown first); preview card shows repo + appcode + target path.
- [ ] Existing appcode auto-detected (case-insensitive); clone lands in `{appcode}/CICD/{repo}`.
- [ ] Missing appcode → ConfirmModal "Create & Clone"; confirms → full year/CR/Non-CR tree + appcode.json created, then clone.
- [ ] Candidate with a separator (e.g. `wgid-cicd`) → editable Appcode-name field appears before clone.
- [ ] Same-remote existing repo → selects (no re-clone); different-remote → clear block message.
- [ ] **UI** at ≥1360 (3 panes: Explorer/Editor/Source Control), ~1100 (Explorer + right group), <900 (single-column tabs) — no broken overflow; white canvas, red accent only, keyboard focus visible.
- [ ] **Editor**: open a text file (YAML/JSON/…), edit, Ctrl+S saves; dirty dot appears/clears.
- [ ] Binary/large file → read-only card with Open External.
- [ ] Change the file outside the app then save → stale banner with Reload / Open External.
- [ ] File on a non-`cicd` branch → read-only banner; save blocked.
- [ ] **Git**: changed files listed with badges; commit selected only (message required); Push asks confirmation and never force-pushes; Pull ff-only (blocked when dirty); Sync handles ahead/behind/equal/dirty/diverged.

Build must be run while the app is CLOSED; user restarts the app before manual testing.
