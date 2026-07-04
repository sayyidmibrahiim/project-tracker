# Project Tracker — 100% Completion Master Plan

> **For agentic workers:** Each branch below is executed with superpowers:executing-plans (or subagent-driven-development), one branch per session, branched from `main`. Steps use checkbox syntax.

**Goal:** Take Project Tracker from its current state (Pieces A+B merged, RTE follow-up pending verify) to 100% of the agreed scope: Tiptap document pipeline (flow-tiptap.md), Piece C approval automation, Piece D CICD Bitbucket, red-header removal + professional UI polish, docs/PRD/git fully synced.

**Architecture:** Layered monolith (Python 3.12 backend, Svelte 5 + TS frontend, pywebview bridge). Filesystem + `project_data.json` canonical; SQLite rebuildable cache. All work offline-capable (office laptop blocks most internet incl. GitHub/PyPI — everything bundles via PyInstaller).

**Tech stack:** Locked per CLAUDE.md. New allowed: `@tiptap/extension-file-handler` (MIT, npm local build). DOCX export = custom Tiptap JSON → python-docx mapper (free/offline; user decision 2026-07-04). No Tiptap Pro.

## Global constraints

- Branch format `{menu}/{desc}` from `main`; merge only after user manual check + approval; one branch per session.
- Smallest diff: delete > edit > add. Follow existing bridge pattern (`JsApi` methods return `ok()/fail()`, contract guard test must pass).
- No new Python test files (user hard rule — extend existing ones); frontend tests OK to extend. Default verification = run app from repo root: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m main`.
- Design-First Rule (revised by user 2026-07-04): NO separate mockups — make deliberate high-quality design decisions up front, code directly in the app, user tests live, iterate. Visual quality bar is high (user rejects bad layout/colors/resolution/positioning).
- COM on background thread with `pythoncom.CoInitialize()`; never on the pywebview main thread.
- Doc sync per change: behavior → PRD.md + PROGRESS.md; decisions → DECISIONS.md; active state → session-notes.md.

## User decisions locked this session (2026-07-04)

1. **Per-format RTE strategy:** formats Tiptap natively supports (`.md`, `.txt`) keep the existing direct save — no extra flow. Formats it can't save natively (`.docx`) get the flow-tiptap pipeline: Tiptap JSON `source.json` = source of truth, real `.docx` = derived export. (Supersedes the "docx read-only" part of D-0010; D-0007's markdown.ts layer stays for `.md`.)
2. **DOCX engine:** custom Tiptap JSON → python-docx mapper (free, offline, deterministic). Rejected Tiptap Pro (paid, private registry, office network blocks it anyway).
3. **Sequence:** Step 0 (verify+merge current branch) → header redesign → Tiptap/DOCX pipeline → Piece C → Piece D → professional polish → packaging/Windows verify.
4. **Red header:** removed entirely, replaced by the existing white per-page `.page-header` as the only header; red returns to accent-only role.

---

## Sequenced roadmap (branches)

| # | Branch | Scope | Spec |
|---|--------|-------|------|
| 0 | `project-details/rte-interaction-bugs` (current) | User manual verify → commit → merge → docs sync | session-notes.md 2026-07-03 |
| 1 | `general/header-redesign` | Remove red `.app-header`, relocate Dashboard controls, tokenize reds, a11y quick wins, PRD §10.4 rewrite | this plan |
| 2 | `project-details/tiptap-docx-pipeline` | flow-tiptap implementation (docx-only pipeline + image assets for all editors) | `_docs/flow-tiptap.md` |
| 3 | `automations/approval-polling` | Piece C | `_docs/specs/superpowers/specs/2026-07-02-approval-automation-design.md` |
| 4 | `general/cicd-bitbucket` | Piece D | `_docs/specs/superpowers/specs/2026-07-02-cicd-bitbucket-design.md` |
| 5 | `general/professional-polish` | Bug sweep results, color hygiene backlog, a11y, Phase D test failures | this plan |
| 6 | `general/packaging` | PyInstaller build + fresh-Windows verify (PRD Phase H) | PRD §24 |

Each branch ends with: run app verification → docs sync (PROGRESS/session-notes/DECISIONS/PRD as applicable) → user manual checklist → user approval → merge to `main` (branches kept, not deleted — user memory rule).

---

## Branch 0 — Close out current work (no new code)

- [ ] Give user the pending manual checklist (from session-notes 2026-07-03): select notes.md/uat-signoff.docx/prod-lv.docx in CR project, confirm DOCX read-only message, edit+save `.md`, titlebar/header lock during load, reopen project.
- [ ] After user approval: commit the 18 dirty files on `project-details/rte-interaction-bugs` (logical commits: RTE capability backend, frontend format-aware save, tests, docs).
- [ ] Decide `notes.md` (repo root, untracked) — appears to be a stray test artifact from RTE testing; confirm with user then delete or ignore. `_docs/flow-tiptap.md` gets committed as the pipeline spec.
- [ ] Merge to `main`, update PROGRESS.md, session-notes.md.

## Branch 1 — `general/header-redesign` (red header removal + design recondition)

**Problem:** `.app-header` (Header.svelte:94, styles.css:124-135) is a full-width red gradient bar (`#B91C1C→#991B1B`) on every page — violates DESIGN_RULES.md ("red is accent, not page wash", "no gradients"). Page titles are duplicated by each page's white `.page-header`.

**Design decision (code directly — no mockup, user rule 2026-07-04):**
- Delete the red `.app-header` bar entirely. The white per-page `.page-header` (icon + title + `.page-header-actions`) becomes the single header under the TitleBar.
- Relocate Dashboard-only controls (Year select, ＋ Add Year, Add Project, Refresh) into Dashboard's `.page-header-actions`.
- Relocate the live DateTime badge into the TitleBar right cluster (near avatar) so it stays global.
- Red becomes accent-only: page-header icon tint, active states, danger buttons.

**Tasks:**
- [ ] `Header.svelte`: remove red bar markup; move its Dashboard controls + Refresh into `Dashboard.svelte` `.page-header-actions` (keep bridge calls unchanged); move DateTime badge to `TitleBar.svelte`.
- [ ] `App.svelte`: stop mounting `<Header>` (or reduce Header to the controls-only fragment if reuse is cleaner); keep `app:interaction-lock` behavior intact (it currently disables TitleBar/Header — verify lock still covers relocated controls).
- [ ] `styles.css`: delete `.app-header` rules (124-135), dead grid rule (299), `.page-title` white-on-red styling; adjust `--header-h` usages / layout heights.
- [ ] Token unification (small, in-scope because it's all red-related): replace `#DA1E28` fallbacks (RulesActions:373, SchedulerActions:340, TeamsActions:185), `#DC2626` hardcodes (NewProjectForm:267,279, ProjectDetails:1256), `.btn-danger` `#B5382F/#942D26` → existing `--primary-red`/`--active-red`/new `--danger` tokens.
- [ ] A11y quick wins riding along (header/titlebar area only): `aria-label` on TitleBar icon nav buttons (152-161), non-color active-tab cue (underline/indicator bar), remove `[{debugInfo}]` leak from avatar tooltip (TitleBar:130).
- [ ] Update frontend tests referencing app-header/Header; run `npm run check` + tests + app.
- [ ] Docs: PRD §10.4 rewrite (new header rules), §10.2 app shell layout, DECISIONS.md new **D-0011** (red header removed; page-header is the single header; red = accent only), PROGRESS.md.
- [ ] Manual checklist for user (all pages at 3 window sizes, Dashboard controls, refresh spin, datetime ticking, lock behavior).

## Branch 2 — `project-details/tiptap-docx-pipeline`

Detailed architecture task list: see **Pipeline design** section below (from Plan agent). Summary of fixed points:

- `.md`/`.txt` save path untouched (direct save, 1000ms debounce, markdown.ts stays).
- `.docx` becomes editable: source of truth = Tiptap JSON sidecar; background export → real `.docx` (atomic tmp+`os.replace`); latest-revision-wins coordinator, single `ThreadPoolExecutor(max_workers=1)`; idle ~20s export + flush on doc switch + final export on close; locked-file (Word open) retry with source safe.
- Exporter = new Python module mapping Tiptap JSON → python-docx (paragraph/heading/marks/colors/fonts/align/lists/tasklist/image/table with rowspan+colspan+colwidth/link/hr/codeblock). Legacy `export_to_docx` (htmldocx) stays wired until replaced (D-0010), then removed.
- Image paste (Win+Shift+S → Ctrl+V) for **all** editors: assets saved as files with asset id (MIME sniffed from magic bytes, size cap, traversal guard); no permanent base64. Existing base64 content keeps rendering.
- Capability change: docx → editable, new saveStrategy `docx_pipeline`; msg unchanged (unsupported).
- Save status UX: `Saving… / Saved / Exporting DOCX… / DOCX saved / Export failed — source safe`.
- Migration: first open of existing non-empty .docx without source.json → mammoth HTML import → JSON; external-edit detection via stored mtime/hash of last export.
- Docs: new **D-0012** (per-format strategy + JSON source for docx + python-docx exporter; partially supersedes D-0010), PRD §12/§21.7 updates, PROGRESS.
- Tests: extend `tests/test_phase_e_notes_persistence.py` (docx now editable via pipeline, revision/hash rules, atomic export, locked-file), extend frontend tests (paste-once, no duplicate node, status transitions). No new Python test files if avoidable.

## Branch 3 — `automations/approval-polling` (Piece C)

**Reuse map (verified):** inbox polling loop exists in `services/download_email_service.py` (poll interval, CR-in-subject match, 3h timeout — spec defaults already in `settings.email.download_poll_interval_seconds/download_timeout_hours`); COM threading via `infrastructure/outlook_client._run_on_com_thread`; template rendering `services/email_service.render_email_template` (11 placeholders incl. {CR_NUMBER}); `project_data.json.email_flags` for sent-tracking; event queue + NotificationService + toasts; `OutlookActions.svelte` component ready to adapt; `EmailTemplateDialog.svelte` pattern for template editor.

**To build:**
- [ ] `project_data.json`: new fields `automation_enabled: bool` (default false) + `approval_templates: dict` (keys `uat_approval`/`lv_approval`; fields to/cc/subject/body/mode) in `core/models.py` `ProjectMetadata` (schema-tolerant read).
- [ ] Global defaults `default_approval_templates` + `approval_polling_interval_minutes:5` / `approval_polling_max_hours:3` in `AppSettings` (`core/models.py:502`) + Settings.svelte fields (follow `FORM_FIELDS` pattern).
- [ ] Condition evaluator (pure, in `core/rules.py` or service): UAT button = CR type + ≥1 drone + drone PENDING APPROVAL + cr_link set + CR PENDING SUBMISSION + `uat-signoff.docx` size>0; LV button = CR type + (CR APPROVED and/or drone APPROVED) + `prod-lv.docx` size>0.
- [ ] Outlook client additions: inbox search by subject+received-after (generalize `_check_outlook_for_reply`), **`SaveAs` .msg export** (olMSG format 3) → `_cr-docs/uat-approval.msg` / `_cr-docs/prod-approval.msg` (overwrite).
- [ ] Polling job persistence: new SQLite table `approval_polling_jobs` (job_id, project_path, cr_number, request_type, sent_at, email_subject, status, reply_received_at) in `infrastructure/cache_db.py` (schema + migrate + health_check set update — note PRD §22.5 already specs an `email_jobs` table; align naming with PRD or update PRD). Resume unfinished jobs on startup.
- [ ] APScheduler wiring: poll job per active request at `interval_minutes` via existing `SchedulerService` pattern (or dedicated service mirroring `auto_transition_service`).
- [ ] Bridge methods on `JsApi`: `send_uat_approval_request`, `send_lv_approval_request`, `get_approval_status`, `stop_approval_polling`, `get_approval_template`, `update_approval_template` (contract guard).
- [ ] ProjectDetails header: automation toggle + conditional buttons in `.page-header-actions` (states: hidden/visible/disabled "Waiting for reply…" countdown/"Approval received"/"No reply (timeout)"); Outlook-unavailable tooltip.
- [ ] Automations menu: "Approval Templates" section — two tabs (UAT/LV), fields To/CC/Subject({CR_NUMBER} required)/Body/Mode, preview with real project data (reuse EmailTemplateDialog patterns).
- [ ] Error handling per spec §5 table (Outlook missing, template missing, send fail, COM retry, multi-match→oldest, project deleted, app closed→resume, empty signoff).
- [ ] Tests: spec asks for 3 new test files — **conflict with no-new-Python-test-files rule; extend existing test files instead** (e.g. add approval condition/template/polling tests into existing automation/phase test modules) unless user approves new files.
- [ ] Docs: PRD §16/§21.13/§22 updates, **D-0013**, PROGRESS; manual checklist per spec §6.

## Branch 4 — `general/cicd-bitbucket` (Piece D)

**Reuse:** `appcode.json` `cicd_location`/`cicd_shared_path` + `CICD/` folder already created by `add_appcode` (app_web.py:1183); `_AppCodeServiceAdapter.update_appcode_config`; `os.startfile` open pattern; daemon-thread + event-queue for long ops; toasts.

**To build (greenfield — no subprocess/git code exists):**
- [ ] Git detection: `check_git_installed()` via `shutil.which("git")` + version; bridge `check_git_status` → `{installed, version}`.
- [ ] Clone service: parse Bitbucket HTTP URL → repo name; `git clone -b cicd <url> <CICD>/<repo>` via `subprocess` on background daemon thread; progress + result via event queue; stderr → error toast (auth/network cases per spec §5).
- [ ] Repo browser backend: `list_cicd_repos(appcode)`, `list_repo_files(repo_path)` (recursive tree + `git status --porcelain` parse), `open_repo_file(path)` via os.startfile. Bridge methods wired on `JsApi` + `clone_repo(appcode, clone_url)`.
- [ ] Frontend: **new titlebar menu icon → full-page `CICDBrowser.svelte`** (per spec UI): appcode dropdown, clone URL input + Clone, repo list with status summary, VSCode-like expand/collapse tree (new component — none exists) with M/U/S badges, click → open externally. Empty states: git-not-installed (Software Center instructions + Recheck) and no-repos (Bitbucket steps + clone input).
- [ ] Settings: CICD location switch (per-appcode vs shared root) showing active folder.
- [ ] Tests: extend existing test modules (mock `shutil.which`/subprocess) — same no-new-file caveat as Piece C.
- [ ] Docs: PRD §7.9/§10/§21 updates, **D-0014**, PROGRESS; manual checklist per spec §6.

## Branch 5 — `general/professional-polish` (bug/issue sweep results)

From the audit (agent findings, 2026-07-04):

- [ ] **Color hygiene (BACKLOG 2026-06-29, now approved as one slice):** migrate 216 raw hex literals in 23 components to `:root` CSS vars (ConfirmModal, Dashboard, FileActions, Toast `#22c55e/#ef4444/#f59e0b/#3b82f6`, TitleBar online dot, etc.). Add semantic tokens: `--success/--warning/--info/--danger`.
- [ ] **Workspace surface separation:** `--workspace-bg` `#FFFFFF` → `#F7F7F8` (frontend-polish.md intent) so cards separate from canvas — code directly, user reviews live.
- [ ] **A11y floor (DESIGN_RULES:75-80):** aria-labels on remaining icon-only buttons (NotesEditor emoji triggers 677/681), non-color state cues on `.status-tab/.sb-tab` active states, focus-visible audit.
- [ ] **GlobalPlan metric cards:** fix inverted label/value/icon semantics (GlobalPlan.svelte:135-136); add ARIA to drag-drop board (articles in `role="list"`).
- [ ] **Table min-width:** `.project-table { min-width: 1540px }` (styles.css:224) vs 1366×768 target — responsive column strategy (hide/priority columns at narrow widths); code directly, user reviews live.
- [ ] **Phase D test debt (BACKLOG 2026-06-27):** fix 2 full-suite-only failures in `tests/test_phase_d_app_web_js_api_wiring.py` + `test_phase_d_app_web_svelte_static_serving.py` (test isolation issue).
- [ ] **Avatar initials blocker:** "A" instead of "AA" (PROGRESS blocker — Outlook COM `get_current_user_name` fallback logic; give initials derivation a display_name-based fallback from settings).
- [ ] Docs: PROGRESS blockers cleared, BACKLOG items closed, DESIGN_RULES token table updated.

## Branch 6 — `general/packaging` + Windows verification (PRD Phase H)

- [ ] Full Windows manual verification sweep of pending items (PROGRESS "Pending" table: UX pack, Global Plan, Report, Second Brain, Automations, Settings — all "pending user verify") — produce one consolidated checklist for the user.
- [ ] Outlook COM / Teams pyautogui / send2trash / os.startfile real-Windows tests (PRD §26.5, Open Calibration Items 1-5).
- [ ] `python scripts/package.py` PyInstaller build incl. `web/static/` + `assets/`; fresh-machine test (offline).
- [ ] PRD §28 calibration items resolved or explicitly deferred; PROGRESS "Windows verify"/"Packaging" rows → done.

---

## Documentation & git sync plan (runs through every branch)

- **DECISIONS.md:** D-0011 (header), D-0012 (per-format RTE pipeline + python-docx exporter, partial supersede of D-0010; note D-0007 markdown.ts survives for .md), D-0013 (approval automation storage/polling model), D-0014 (CICD integration model).
- **PRD.md:** §10.4 header rules rewrite; §12/§21.7 RTE + document pipeline; §16/§21.13/§22.5 approval automation (align `email_jobs` vs `approval_polling_jobs` naming); §7.9/§10.1 CICD page; §25 phase table gets a completion addendum mapping Pieces A-D.
- **PROGRESS.md:** roadmap table above mirrored under "Current Work"; update after every merge.
- **session-notes.md:** Now/Next/Blocked each session.
- **Git:** every branch from `main`, `{menu}/{desc}` names, merge after user approval, branches kept after merge (user rule). Commit `_docs/flow-tiptap.md` + this plan (as `_docs/specs/superpowers/plans/2026-07-04-completion-master-plan.md`) in Branch 0.

## Verification approach (every branch)

1. `npm --prefix frontend run check` (0 errors) + `npm --prefix frontend test`.
2. Targeted pytest for touched Python modules (existing files only).
3. Run app from repo root, watch startup/runtime errors: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m main`.
4. FORM CHECKLIST for user manual verification (buttons states, 3+ window sizes, validation, design-token consistency, exact test steps).

---

## Pipeline design (Branch 2 detail)

### Verified constraints the design rests on

- Frontend is served by pywebview's HTTP server rooted at `web/static` — project-folder files are NOT URL-reachable → images display as **base64 data URIs over the bridge** (same as today's `util_choose_image`). No new serving surface.
- `file_list` bridge lists files only → a `.rte/` **subdirectory** is invisible to the Files tab and CR-docs dropdown.
- `discover_drone_paths` would misdetect a root-level dot-folder as a drone → Task 1 guard.
- No shutdown hook exists; `webview.start()` returning in `app_web.run()` is the final-export point.
- Legacy `get_rte_file`/`save_rte_file`/`export_to_docx` stay **untouched** → existing phase-E docx read-only test keeps passing; the pipeline uses new bridge methods.

### On-disk layout

```
<project>/
├── notes.md
├── .rte/assets/<16-hex-id>.png          ← notes.md image assets
└── _cr-docs/
    ├── uat-signoff.docx                 ← derived output (real Word file)
    ├── prod-lv.docx
    └── .rte/
        ├── uat-signoff.source.json      ← source of truth
        ├── prod-lv.source.json
        └── assets/<16-hex-id>.png
```

Rule: `sidecar_dir = document.parent / ".rte"`; `source_path = sidecar_dir / f"{stem}.source.json"`. `source.json` schema v1: `{schema_version, document_id, revision, content_hash (sha256 of canonical dehydrated content), saved_at, document_settings (A4, 20mm margins, Times New Roman 11pt, line 1.15 — matches editor CSS), export: {last_exported_revision, last_exported_hash, export_pending, docx_mtime_ns, docx_size, last_error}, content: <tiptap JSON>}`. Image nodes stored as `{assetId, src: "asset://<id>.<ext>", width, height}` — never data URIs or absolute paths.

**Asset resolution:** docx open → backend hydrates `asset://` → data URI; docx save → backend dehydrates (data-URI-without-assetId swept into new asset file). md → `![alt](.rte/assets/<id>.png)` in the file, hydrated to data URI on load via `rte_asset_read`; existing base64 embeds pass through unchanged.

### Tasks (ordered)

1. **Dot-folder guard** — `infrastructure/filesystem.py`: `discover_drone_paths`/`discover_subproject_paths` skip `child.name.startswith(".")`; `_scaffold_drone` rejects dot-names. Extend existing discovery test.
2. **`infrastructure/docx_writer.py` (new)** — `export_source_to_docx(source, assets_dir, target_docx)` + `DocxTargetLockedError`. Full mapping table resolved (agent design): paragraph/heading→styles+alignment; marks→run props; highlight→raw OXML `w:shd`; fontFamily/fontSize (`px*0.75`→Pt); link→OXML hyperlink rel; lists→`List Bullet/Number` styles (3 depths); taskItem→`☑/☐` prefix (explicit lossy); image→`add_picture(width=Inches(px/96))`, missing asset → placeholder text; table→`add_table`+`Table Grid`, colspan/rowspan via `cell.merge` + occupancy matrix, colwidth px→dxa (`px*15`); hr→bottom-border paragraph; codeBlock→Consolas 10pt shaded; blockquote→indent+italic. Atomic: tmp → re-open validate → `os.replace`; PermissionError → `DocxTargetLockedError`.
3. **`services/rte_document_service.py` (new)** — `RteDocumentService` (singleton via `get_rte_document_service()`): `open_document/save_document/save_image/read_asset/request_export/export_status/flush_all` + `ExportCoordinator` (ThreadPoolExecutor(max_workers=1, "docx-export"), latest-revision-wins: active+pending dicts under a Lock, intermediate revisions dropped). `save_document(payload {content, base_revision, reason: autosave|manual|switch|migration})`: stale revision → `RTE_REVISION_STALE`; identical hash → skip; manual/switch/migration → immediate export request. `save_image`: 15MB cap, MIME by magic bytes only, content-addressed `asset_id = sha256[:16]` (dedupes duplicate paste), returns `{asset_id, src, rel_src, data_uri}`. `read_asset`: name validated by `^[0-9a-f]{16}\.(png|jpe?g|gif|webp)$` (traversal-proof). Export worker pushes `RTE_EXPORT_DONE/LOCKED/FAILED` via `web/event_queue.push_event`; locked → `export_pending=True`, retried on next open. IMPLEMENTED state → read-only.
4. **Bridge** — `web/js_api.py`: `RteDocumentServiceProtocol` + 6 methods `rte_document_open/rte_document_save/rte_image_save/rte_asset_read/rte_export_request/rte_export_status` (fail-not-raise on empty args for contract-guard P7; codes `RTE_OPEN_FAILED/RTE_SAVE_FAILED/RTE_REVISION_STALE/RTE_IMAGE_SAVE_FAILED/RTE_ASSET_READ_FAILED/...`). `app_web.py`: inject service in `create_js_api`; after `webview.start()` returns → `shutdown_rte_document_service(timeout_s=10)` (final export on close; never blocks shutdown).
5. **Frontend contract** — `types.ts`: `RteSaveStrategy += "docx_pipeline"`, new `RteExportState/RteDocumentPayload/RteSaveResult/RteImageSaveResult`. `bridge.ts`: 6 typed helpers.
6. **Editor** — new `frontend/src/lib/extensions/AssetImage.ts` (stock Image + `assetId`/`assetSrc` attrs); paste/drop via **manual `editorProps.handlePaste/handleDrop`** (not FileHandler — explicit consumption, zero new deps): extract image file → `rteImageSave` → insert node with data_uri+assetId (failure → error status, no broken node). Toolbar image insert also routes through `rteImageSave` (fallback to data URI). docx mode in `NotesEditor.svelte`: new props `initialDoc/initialRevision/needsMigration`; content init from JSON; `flush()` docx branch → `rteDocumentSave` with revision tracking; idle export timer `IDLE_EXPORT_MS=20_000` → `rteExportRequest`; 1s status poll only while export active; status labels `Exporting DOCX… / DOCX saved / DOCX locked — will retry / Export failed — source safe`; Ctrl+S = manual reason; `savePendingBeforeDispose` docx branch reason "switch". Pure state logic in new `frontend/src/lib/rteDocxState.ts` (unit-testable). md load hydration: walk doc for `.rte/assets/` srcs → `rteAssetRead`, non-dirty transaction.
7. **markdown.ts** — allow `^\.rte\/assets\/[0-9a-f]{16}\.(png|jpe?g|gif|webp)$` in `sanitizeImgSrc`; `img` attrs += `data-asset-src/data-asset-id`; renderMarkdown emits `data-asset-src` for asset paths; htmlToMarkdown serializes `![alt](<data-asset-src>)` when present, base64 passthrough unchanged.
8. **ProjectDetails.svelte** — `loadCrDocs()`: docx entries become editable/`docx_pipeline` (read-only only when IMPLEMENTED); `selectCrDoc` routes docx → `rteDocumentOpen`; pass `initialDoc/initialRevision/needsMigration` to NotesEditor. Existing flush-before-switch + interaction-lock already cover doc-switch export.
9. **Tests + verify** — extend `tests/test_phase_e_notes_persistence.py` (open/migrate/save/skip/stale/image-validation/traversal/latest-wins-coordinator/locked-target/dehydration-sweep — no new Python test file needed); contract guard auto-covers new methods; extend `frontend/tests/markdown.test.ts` + `project-details-fase3-fase4.test.mjs`; new `frontend/tests/rte-docx-state.test.ts` (frontend new files allowed). 11-step manual checklist (typed in Branch 2 completion): edit docx → source.json appears → idle 20s → open in Word verify fidelity; Win+Shift+S→Ctrl+V in docx and md; Word-lock retry; rapid doc switching; close-app-within-20s; external Word edit → stale re-import; IMPLEMENTED read-only; no `.rte` leaks in Files tab/drones.

### Migration & external-edit rule

- source.json exists + not stale → use it (hydrated). `schema_version > 1` → fail safe.
- Stale check: recorded `docx_mtime_ns/size` vs actual; docx newer than source → user edited in Word → back up source to `.bak`, mammoth re-import (`needs_migration: true`), frontend re-saves as new revision.
- No source.json: empty docx → empty doc; non-empty → mammoth HTML import (`needs_migration: true`), first save becomes revision 1 + first export. mammoth stays as the import path.

### Risks

- htmldocx/`export_to_docx` stay wired (D-0010) — removal is a later decision.
- Dot-folder filter touches drone discovery — full pytest suite is the canary.
- mammoth first-migration drops some fidelity (acceptable: old pipeline was lossy anyway; source.json authoritative afterward).
- 15MB base64 bridge payload fits the 30s bridge timeout; noted in code.
- PyInstaller: no spec change expected (pure-Python modules, deps already bundled).
