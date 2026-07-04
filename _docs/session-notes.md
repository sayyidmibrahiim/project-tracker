# Session Notes

> Brief recovery ledger. Do not paste transcripts or secrets.
>
> - **DECISIONS.md** → permanent ADRs (why)
> - **PROGRESS.md** → tracking (what's done, what's next)
> - **session-notes.md** → what's active NOW

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
