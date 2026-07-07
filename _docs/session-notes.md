# Session Notes

> Brief recovery ledger. Do not paste transcripts or secrets.
>
> - **DECISIONS.md** → permanent ADRs (why)
> - **PROGRESS.md** → tracking (what's done, what's next)
> - **session-notes.md** → what's active NOW

---

## 2026-07-08 (Automation System epic — Slice 1: PD 3-group section)

**Now:** New epic after user brainstorm (Grok chat) → Outlook + General Automation system, 5 slices, spec `_docs/specs/superpowers/specs/2026-07-08-automation-system-design.md`. Locked: PD-box-first; fold Piece C (backend kept, PD UI replaced); Logs = new top-level menu (Slice 5); `[Send]` confirmed, `[Draft]` not. Slice 1 implemented on `automations/approval-polling`:
- Backend `services/approval_polling_service.py`: `send_request(kind, mode)` — draft opens Outlook draft + `APPROVAL_DRAFT_OPENED`, NO poll job; send delivers then polls when auto-download on; extracted `_match_and_save` + `_one_shot_check`; `force_check(kind)` one-shot inbox scan → `_on_found` on match; `set_auto_update_cr_state`; `get_status` gains `cr_number` + `auto_update_cr_state`.
- `core/models.py`: `ProjectMetadata.auto_update_cr_state: bool` (flag only; email-pattern engine = Slice 4).
- `web/js_api.py`: `send_uat/lv_approval_request(mode)`, `approval_force_check`, `approval_set_auto_update_cr_state` (+ protocol). `bridge.ts` `approvalSend/approvalForceCheck/approvalSetAutoUpdateCrState`; `types.ts` `ApprovalStatus` += `cr_number`,`auto_update_cr_state`.
- `ProjectDetails.svelte`: 3-group markup (Automations Outlook / Automation CR / Automation Teams), status dots 🟢🟡🔴⚪ via `autoDot`/`autoLabel`, ConfirmModal `pendingSend` for `[Send]`, `[Draft]`/`[Force Check]`/`[Stop]`/auto-download toggle, `[Open Setting]`→`onNavigateAutomations`. CR+Teams groups = honest dev-stubs. `App.svelte` wires `onNavigateAutomations`.

**Known limits (accepted):** draft never polls; auto-download-OFF send has no persistent job so PD dot can't show "sent" post-reload (toast covers it); force-check/worker `SaveAs` race is benign (idempotent); `auto_update_cr_state` engine deferred to Slice 4.

**Next:** build (app closed) → user manual checklist Slice 1 → approve → Slice 2 (PlaceholderResolver + Template per-CR + editor popup + Test). No merge to main until user approves.

**Verification:** svelte-check 0/0; frontend 182 pass; targeted pytest 27; full pytest 1828 pass + 6 known baseline fails.

**active_menu:** automations / project-details

---

## 2026-07-06 (Piece C UI rework — Branch 3, after first manual check)

**Now:** User manual check rejected 2 things: (1) new Approval tab (Outlook tab already owns email templates), (2) approval controls squeezed into PD command bar. Rework committed in 3 slices: `ca6be1f1` backend (automation_enabled → `bool|None` inherit `settings.automation_default_enabled`; `approval_auto_download` dict per kind, OFF = send records history but no polling job; `TERMINAL_CR_STATES` FINISHED/POSTPONED/CANCELED force effective off + `automation_locked`; `set_auto_download` + `approval_set_auto_download` bridge), `226c9670` Automations page (Approval tab deleted; SEND AUTOMATION = 2 rows Email Ack (UAT)/Email LV (Prod) opening ApprovalTemplates as kind-preset dialog; SOP rows + EmailTemplateDialog.svelte deleted — `settings.email.categories` data kept, backend outlook_draft/send_email still consumes it; "New-CR automation default" toggle in panel title row), `3dd2c09c` PD (dedicated CR-only "Automations" section bottom-left pane: master toggle + lock hint, always-visible send rows, auto-download toggles, 6 dev-stubs → toast "masih tahap development"; body `inert` + dimmed when off).

**Known quirks:** legacy `automation_enabled: false` reads as explicit OFF (no inherit-reset UI — add if user asks). `ApprovalStatus.automation_enabled` is now the EFFECTIVE value. `OutlookActions.svelte` remains an orphan (pre-existing, untouched). Send not enabled-gated server-side (pre-existing, UI-gated).

**Next:** User closes app → `npm run build` → user manual checklist (delivered in session) → docs commit → merge only after approval.

**Verification:** svelte-check 154 files 0/0; frontend tests 182 pass; targeted pytest 27 pass; full pytest 1825 passed / 20 skipped / 6 known baseline failures (extra 7th failure earlier was TEMP-path-too-long from sandbox tmp dir, not code).

**active_menu:** automations

---

## 2026-07-06 (Piece C implemented — Branch 3)

**Now:** Branch 3 `automations/approval-polling` implemented through automated verification. Scope: `ProjectMetadata.automation_enabled` + `approval_templates`, default approval templates/settings fields, SQLite `approval_polling_jobs`, `ApprovalPollingService` with Outlook send/draft + reply polling + startup resume + shutdown hook, JsApi/bridge wrappers, Project Details approval toggle/UAT/LV controls, Automations Approval Templates editor.

**Next:** User closes Project Tracker app → run frontend build → user manual checklist. No merge until manual pass + explicit merge approval.

**Blocked:** Build intentionally not run yet because RTE safety rule forbids `npm run build` while app may be open. Full pytest still has 6 known baseline failures outside Piece C (`test_phase_c_js_api_project.py` x3, `test_phase_d_app_web_project_service_adapter.py` x1, `test_year_create.py` x2).

**Verification:** `npm --prefix frontend run check` 0/0; frontend node tests 123 pass; targeted pytest 53 pass; full pytest 1821 passed / 20 skipped / 6 known baseline failures; app smoke alive after 15s with empty stdout/stderr.

**active_menu:** automations

---

## 2026-07-06 (Branch 3 plan ready — Piece C)

**Now:** Branch 2 merged to main. Branch 3 `automations/approval-polling` created; detailed executable plan committed at `_docs/specs/superpowers/plans/2026-07-06-piece-c-approval-polling-plan.md` (written to be executed verbatim by ANY model — full code per task, locked design decisions, no room for improvisation). Spec = `_docs/specs/superpowers/specs/2026-07-02-approval-automation-design.md`.

**Next:** Execute the plan task-by-task with superpowers:executing-plans on this branch (Tasks 1–8: models → cache_db → service → bridge → frontend wrappers → PD controls → template editor/settings → verify+docs+gates). Rules binding: no new Python test files; follow plan anchors exactly; STOP if an anchor is missing; build gate + manual gate before commit of the final slice; no merge without user approval.

**Blocked:** None.

**active_menu:** automations

---

## 2026-07-06 (fix round v2 complete — Branch 2)

**Now:** Fix round v2 steps 0–7 all committed after per-step user manual verification. This session: step 5c image drag-resize `4ca0abd` (handle CSS reworked once after "gaudy" feedback: 8px, 1px border, subtle shadow); step 6 SVG toolbar icons `b1cf0dc` (18 buttons, lucide-style inline SVG, 13px stroke-2, currentColor; link 🔗 included); step 7 `37d8ca7` default TNR 18px editor ↔ 13.5pt exporter + fixes from manual feedback: SIZES must be strings (`bind:value` strict equality made the size select blank) and per-file last font/size memory via module-scope `Map<targetFile, {font,size}>` (session-scoped; `initialFileKey = untrack(() => targetFile)` avoids `state_referenced_locally` warning). Docs synced: PRD §12.12, PROGRESS.

**User rule 2026-07-06:** default session skills = using-superpowers + ponytail full + caveman full (recorded in CLAUDE.md/AGENTS.md §"Default Session Skills"; those files stay uncommitted — user-owned edits present).

**Next:** User decides merge Branch 2 → main. After merge: Branch 3 `automations/approval-polling` (Piece C). Optional follow-up if requested: persist per-file font/size to disk (currently session-scoped).

**Blocked:** None new. Known nonblocking pre-commit pytest fail `test_project_list_returns_converted_rows` (pre-existing on main, queued Branch 5).

**Verification:** svelte-check 154 files 0/0; frontend tests 121 pass; phase E pytest 27 pass (TEMP redirect for stale `pytest-current` lock); builds ok; user manual `pass` on steps 5c/6/7.

**active_menu:** project-details

---

## 2026-07-04 (rollback — Branch 2 fix round)

**Issue:** After the first manual check, a 5-part fix round was shipped as one bundle (toolbar `rev` → `$state` active states; idle export 20s→5s + countdown; hidden `.rte` attribute; "?" help popover; Narrow 12.7mm margins + 720px WYSIWYG page width + export clamp + AssetImage resize NodeView + `<img width>` markdown round-trip). User reported **"semua behavior jadi gak normal"** → full rollback to `9882694` code state (commits `e80996d` partial + `a30c512` reverted; user's `.codex/` + `AGENTS.md` kept). Binding lessons recorded in CLAUDE.md + AGENTS.md §"RTE Change Safety".

**Root-cause status:** NOT yet identified — exact symptoms not specified. Suspect ranking to test ONE at a time (each with user verify before the next): (1) AssetImage NodeView (touches every editor incl. notes.md — biggest blast radius); (2) reactive `rev` re-render per transaction; (3) 720px docx page width; (4) environment mismatch — `web/static` rebuilt mid-session while app open / branch switched (web/static is gitignored, does not follow checkout); (5) hidden-attr + countdown (cosmetic, unlikely).

**Update 2026-07-05:** User confirmed app normal again after rollback + rebuild + restart. Symptoms identified: RTE slow-load + titlebar nav frozen (the `app:interaction-lock` held the whole shell while RTE load hung) — consistent with the stale-`web/static`/lock-without-failsafe hypothesis. Fix round v2 is delegated to Codex desktop via the step-by-step prompt at `_docs/specs/superpowers/plans/2026-07-05-codex-fix-round-v2-prompt.md` (steps 0–7, ONE behavior per step, user verify between; step 0 = interaction-lock watchdog; new points: SVG toolbar icons, default TNR 18px↔13.5pt).

**Update 2026-07-05 (Step 1 failed):** Step 0 passed manual verification and was committed as `c94e387`. Step 1 (`rev` changed to `$state(0)` for toolbar active states) failed manual verification: menu navigation became unusable, save/loading became very slow, and file switching became very slow. Step 1 was still uncommitted, was rolled back immediately, and the baseline bundle was rebuilt. Root cause: the editor-mount `$effect` contains synchronous `rev++` calls; once `rev` became `$state`, those read+write operations subscribed the effect to its own state and repeatedly invalidated/recreated the editor. Retry must keep `rev` non-reactive and use a separately throttled toolbar-only state update outside effect tracking.

**Update 2026-07-05 (Step 1 retry ready):** Retry keeps `rev` non-reactive and adds `uiTick` as a toolbar-only state token. Tiptap `transaction` listener is registered from `queueMicrotask()` and throttled by `requestAnimationFrame`, so the editor-mount `$effect` does not subscribe to toolbar refresh state. Automated verification passed: focused Project Details frontend test, `npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run check`, `npm --prefix D:/Ibrahim/Projects/project_tracker/frontend test`, and `npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run build`. Awaiting user manual verification before commit.

**Update 2026-07-05 (Step 1 committed + Step 1.5 in progress):** User manually verified Step 1 retry and it was committed as `65202cf`. Follow-up diagnosis on `D:\Ibrahim\WORK\SSID\2026\CR\UAT_PREPARE\popopopopopopop\_cr-docs\uat-signoff.docx` found a stale-DOCX migration loop: `open_document()` backed up the old source sidecar but left `source.json` in place, so the frontend migration save used `base_revision: 0` while backend still loaded revision 27 and raised `StaleRevisionError`. Step 1.5 minimal fix deletes the stale sidecar after backing it up; regression test added in `tests/test_phase_e_notes_persistence.py`.

**Update 2026-07-05 (Step 1.5 retry):** Manual test still froze after DOCX migration/import: backend log showed `RTE_REVISION_STALE` spam (`Revision 0 is stale (stored 1)`) and frontend log showed hundreds of `rte_document_save` starts. Root cause: `NotesEditor` called `flush("migration")` synchronously inside editor-mount/path `$effect`; `flush()` reads/writes Svelte state (`migrationPending`, `docRevision`, `status`), subscribing the effect and recreating the editor/save loop. Minimal frontend fix now computes local `shouldMigrate` and queues migration flush via `queueMicrotask()` outside effect tracking. Source-contract test added in `frontend/tests/project-details-fase3-fase4.test.mjs`.

**Next:** Finish Step 1.5 retry verification after app closes (`npm run build` must not run while app is open), then user manually verifies `uat-signoff.docx` load/save/file-switch/menu responsiveness. If pass → commit Step 1.5 only. If fail → rollback uncommitted Step 1.5 and rebuild baseline. After all RTE steps pass, merge Branch 2 → Branch 3 `automations/approval-polling` (Piece C).

---

## 2026-07-04 (later — Branch 2)

Branch aktif: `project-details/tiptap-docx-pipeline` (Branch 1 header-redesign merged to main after user verify).

**Now:** DOCX pipeline (D-0012) implemented end-to-end: dot-folder drone guard; `infrastructure/docx_writer.py` (Tiptap JSON→python-docx, full mapping table, atomic replace, DocxTargetLockedError); `services/rte_document_service.py` (source.json store, revision/hash, stale-revision reject, IMPLEMENTED lock, mammoth migration + external-Word-edit stale rule, content-addressed image assets, ExportCoordinator single worker latest-revision-wins); 6 bridge methods `rte_document_open/save, rte_image_save, rte_asset_read, rte_export_request/status` + shutdown flush in app_web; frontend AssetImage extension, paste/drop upload, docx_pipeline editor mode (idle 20s export, 1s poll while exporting, status labels), markdown.ts `.rte/assets` round-trip; ProjectDetails routes docx via pipeline (editable unless IMPLEMENTED).

**Next:** User manual verify pipeline checklist → merge → Branch 3 `automations/approval-polling` (Piece C).

**Blocked:** 6 pre-existing test failures on main (year_create, project_list — fail identically on main; queued for Branch 5). Stray `notes.md` created at repo root by app/pytest run — Branch 5.

**Verification:** svelte-check 154 files 0/0; frontend tests 164 pass; pytest full suite 1809 pass / 6 pre-existing fails (identical on main); app smoke 14s clean; build ok.

**active_menu:** project-details

---

## 2026-07-04 (Branch 1)

Branch aktif: `general/header-redesign` (Branch 1 of master plan; Branch 0 merged to main same day).

**Now:** Header redesign implemented: red `.app-header` deleted (Header.svelte removed), Dashboard controls (Year/Add Year/Add Project/Refresh) moved into Dashboard `.page-header-actions` with portal-style Add-Year popover; live clock (`ddd, dd MMM yyyy HH:mm:ss`) added to TitleBar right cluster; nav icons got aria-labels + red active-indicator bar; avatar debug tooltip removed; red tokens unified (`#DA1E28` fallbacks, `.btn-danger` `#B5382F/#942D26`, `#DC2626` hardcodes → tokens). PRD §10.2–10.4 rewritten (also aligned stale dock text to D-0005 TitleBar). D-0011 recorded. Fixed stale WSL `core.hooksPath` in .git/config; pre-commit gains one svelte-check retry vs transient esbuild OOM; retired graphify post-commit/post-checkout hooks deleted (D-0009).

**Next:** User manual verify header redesign (checklist delivered) → merge to main → Branch 2 `project-details/tiptap-docx-pipeline`.

**Blocked:** Branch 1 merge awaits user manual verification.

**Verification:** svelte-check 152 files 0/0; frontend tests 156 pass / 0 fail; app smoke 14s clean (no stderr); `npm run build` ok (pre-existing chunk-size warning).

**Master plan (earlier today):** `_docs/specs/superpowers/plans/2026-07-04-completion-master-plan.md` approved (7 branches). Locked: per-format RTE strategy (md/txt direct; docx = source.json + python-docx export), free/offline exporter (office network blocks GitHub/PyPI/paid registries), no-mockup design rule.

**active_menu:** general (header shell)

---

## 2026-07-03

Branch aktif: `project-details/rte-interaction-bugs`.

**Now:** Piece B RTE format-aware follow-up implemented in code. Project Details no longer shows `Export to Word` for active RTE files. Backend now returns RTE capability metadata; `.md` saves Markdown, `.txt` saves UTF-8 plain text, `.docx` is read-only until safe source-sync adapter exists, `.msg` is unsupported/open externally. CR doc dropdown flushes active editor via `flushNow()` before file switch. App-level `app:interaction-lock` disables TitleBar/Header during RTE load/flush.

**Next:** User manual verify CR project flow: select `notes.md`/`uat-signoff.docx`/`prod-lv.docx`, confirm DOCX read-only, edit/save `.md`, test titlebar/header lock during load, reopen project.

**Blocked:** Full DOCX editable source-sync engine intentionally deferred.

**Changed files:** `app_web.py`, `web/js_api.py`, `frontend/src/App.svelte`, `frontend/src/lib/activityLogger.ts`, `frontend/src/lib/bridge.ts`, `frontend/src/lib/types.ts`, `frontend/src/lib/markdown.ts`, `frontend/src/lib/components/Header.svelte`, `frontend/src/lib/components/NotesEditor.svelte`, `frontend/src/lib/components/ProjectDetails.svelte`, `frontend/src/lib/components/TitleBar.svelte`, `frontend/tests/components.test.mjs`, `frontend/tests/markdown.test.ts`, `frontend/tests/project-details-fase3-fase4.test.mjs`, `tests/test_phase_e_notes_persistence.py`, `_docs/PROGRESS.md`, `_docs/DECISIONS.md`, `_docs/session-notes.md`.

**Verification:** `npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run test` = 155 pass / 0 fail. `npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run check` = 0 errors / 0 warnings. `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_phase_e_notes_persistence.py -v` = 13 pass / 0 fail. `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_bridge_contract_guard.py -v` = 3 pass / 0 fail when `TEMP/TMP` point at job tmp to avoid stale Windows pytest-current cleanup lock. `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m main` smoke = no stdout/stderr traceback captured before 12s stop.

**active_menu:** project-details

---

## 2026-07-02

Tooling update: Code graph integration retired by user request. Active docs/settings use native search/read tools for code lookup. Headroom installed in repo venv and setup reference added with proxy URL `http://localhost:8787` and install command `pip install "headroom-ai[proxy]"`. Global `ANTHROPIC_BASE_URL` remains routed to `http://127.0.0.1:20128/v1`; Headroom proxy uses `8787`.

**Now:** Piece A UI/UX implemented on `general/appcode-structure-audit`; manual-check bugs fixed. Dashboard: 3 multi-select checklist dropdowns (CR State / Appcode / Project Type) use fixed-position menu/scrim so header overflow cannot clip list; 2-line project metadata (`Type · Appcode · time · full date`); Non-CR rows render safe (no CR/Drone edit). Add Project form: CR/Non-CR radio, appcode placeholder dropdown + inline `+` create (`appcode_list`/`appcode_add`), start/end datetime only; no CR link / implementation plan; never sends `drone_name`. Project Details: `isSubproject` → `isNonCr`; Non-CR shows state dropdown (`set_non_cr_state`), hides CR/Drone sections, keeps schedule editable. Backend `create_project` persists optional start/end and ignores `drone_name` (lazy drone). `appcode_add` creates current-year `CR/{states}` and `Non-CR`; appcode discovery includes manual folders with year subfolders (e.g. SSID). Drone copy rename (`Sub Project` → `Drone`) across Dashboard/ProjectDetails/DroneTable.

Cross-menu fix sweep (one-time branch scope override approved by user):

- Global Plan: productionized as official menu 7, native HTML5 drag/drop (status + reorder), seeded all 17 audit backlog items.
- Automations: scheduler `project_provider` now real (was `lambda: []`); added `scheduler_entry_trigger` bridge + UI target entry; metrics derived from real entries (no more hardcoded `0`); rules Execute exposed separately from preview Evaluate.
- Report: Month + Drone State filters; CR/Drone/Monthly summary cards; expanded table columns (#, CR Number, T-10, Last Updated); native save-dialog CSV with UTF-8 BOM, Blob fallback.
- Second Brain: wired search/sort/type/date filters to real filesystem notes; added Link Bank export/import/rename/restore.
- Settings: removed Theme switch (PRD = fixed theme); added T-10/numeric validation, trailing-slash guard, restart-required notice.

**Next:** Piece A merged to `main`. Plan Piece B (`project-details/cr-docs-rte`): `_cr-docs` editable files + multi-file RTE editor dropdown.

**Blocked:** None in startup. Windows manual verification needed for real filesystem/create/move flows.

**active_menu:** main; next branch `project-details/cr-docs-rte`

**Changed files:** `frontend/src/lib/components/NewProjectForm.svelte`, `frontend/src/lib/components/Dashboard.svelte`, `frontend/src/lib/components/ProjectDetails.svelte`, `frontend/src/lib/components/DroneTable.svelte`, `frontend/src/lib/components/Report.svelte`, `frontend/src/lib/types.ts`, `app_web.py`, plus updated assertions in `frontend/tests/components.test.mjs`, `frontend/tests/as-is-prototype-parity.test.mjs`, `frontend/tests/dashboard-inline-edit.test.mjs`, `frontend/tests/project-details-fase1.test.mjs`, `frontend/tests/project-details-fase3-fase4.test.mjs`, `_docs/PROGRESS.md`, `_docs/session-notes.md`.

**Verification:** `npm --prefix frontend run check` = 0 errors/0 warnings; `npm --prefix frontend test` = 149 pass/0 fail; `npm --prefix frontend run build` = ok; `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m main` startup clean. No new Python test files by user hard rule; Python tests intentionally skipped.

---

## 2026-07-01

Branch aktif: `general/ux-features`
File diubah: App.svelte, Dashboard.svelte, ProjectDetails.svelte, Settings.svelte, EmailTemplateDialog.svelte, GlobalPlan.svelte, Report.svelte, SecondBrain.svelte, TitleBar.svelte, Toast.svelte (new), WelcomeGuide.svelte (new), toastStore.ts (new)
Keputusan teknis: toast store with undo action support; Settings autosave 1500ms debounce; undo toasts 5s timeout; onboarding once-and-never via localStorage
Verifikasi: build passes (pre-existing warnings only)

---

## 2026-06-29

Branch aktif: `design/titlebar`
File diubah: TitleBar.svelte (new), Sidebar.svelte → .bak, all 6 menu pages (page-header), Dashboard/ProjectDetails/SubProjectTable (3-icon CR/Drone), app_web.py, web/js_api.py, infrastructure/outlook_client.py, styles.css, App.svelte, Header.svelte, bridge.ts, various config/docs
Keputusan teknis: D-0005 (TitleBar replaces Sidebar), D-0006 (3-icon pattern for all CR/Drone inputs)
Verifikasi: svelte-check 0 errors, vite build clean

---

## 2026-06-27

Branch aktif: `chore/bootstrap-tooling`
File diubah: bootstrap tooling/config docs only
Design approved: none
Keputusan teknis: context-mode owns tool-output compression; claude-mem owns cross-session recall; agentmemory disabled to avoid duplicate capture/injection; retired code graph integration no longer used; RTK manual-only on native Windows.
Smoke: plugin list OK; retired code graph integration was degraded/noisy; RTK OK.
Blocked: Windows manual product verification remains separate from bootstrap.
