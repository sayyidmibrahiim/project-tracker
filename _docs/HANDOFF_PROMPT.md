# Handoff Prompt — Project Tracker Appcode Structure

Kamu adalah AI agent yang melanjutkan pekerjaan di repo **Project Tracker DBS**.
Repo ada di `D:/Ibrahim/Projects/project_tracker`.
Baca `CLAUDE.md` dulu sebelum melakukan apapun — itu adalah workflow/tooling guardrails yang wajib diikuti.

## WAJIB BACA SEBELUM CODING (Cold Start / Truth Order)

1. `CLAUDE.md` — workflow rules, branch format, tech stack, commands
2. `_docs/WORKFLOW.md` — git branch convention, implementation discipline
3. `_docs/PROGRESS.md` — current tracking
4. `_docs/session-notes.md` — active context: Now / Next / Blocked
5. `_docs/DECISIONS.md` — architectural decisions (baca D-0008)
6. `_docs/ARCHITECTURE.md` — layer structure dan dependency flow
7. `PRD.md` Section 7 — filesystem model (baru di-rewrite untuk appcode structure)

## KONDISI SAAT INI

Branch aktif: `general/appcode-structure` (belum di-merge ke `main`).

**Piece A (Core Folder Structure + CR/Non-CR Project Types) sudah 90% selesai.**
10 dari 12 task done, 50 new tests passing, frontend build clean.
Tapi masih ada yang harus di-fix.

### Yang sudah done (Tasks 1-10 + docs):

- `core/enums.py` — ProjectType(CR|NON_CR), NonCrState(PLANNING|IN_PROGRESS|DONE)
- `core/models.py` — ProjectMetadata +2 fields, AppCodeConfig, ScannedProject updated
- `core/state_machine.py` — Non-CR state machine
- `infrastructure/filesystem.py` — project_type_from_path, discover_appcodes, ensure_appcode_year_structure, discover_drone_paths, _scaffold_drone, scan_appcode_year
- `infrastructure/cache_db.py` — 3 new columns, drone_paths_json, appcode-scoped queries
- `services/project_service.py` — set_non_cr_state, updated path helpers, delete_drone
- `services/dashboard_service.py` — DashboardProject +3 fields, drones renamed
- `web/js_api.py` — AppCodeServiceProtocol, renamed drone methods, appcode-scoped years
- `app_web.py` — create_project 3 types, create_drone, appcode-scoped year adapter
- `frontend/src/lib/types.ts` — new fields, AppCode interface
- `frontend/src/lib/components/DroneTable.svelte` (renamed from SubProjectTable)
- `frontend/src/lib/folderLocks.ts` — drone_delete
- Docs: PRD section 7 rewritten, D-0008, ARCHITECTURE, DESIGN_RULES, PROGRESS, session-notes

### Yang masih harus di-fix (Task 11 — PRIORITY):

**~20 existing test files masih pakai old path scaffold** (`root/year/STATE/project`) dan naming `subproject`. Mereka currently FAIL karena struktur folder berubah jadi `root/appcode/year/CR/STATE/project`. Ini bukan bug di implementation — test scaffolds-nya yang perlu di-update.

File-file test yang perlu di-fix:

- `tests/test_app_web_dashboard_auto_move.py` — path scaffold + _rebuild_cache_for depth
- `tests/test_phase_b_stores.py` — root_folder scaffold
- `tests/test_phase_b_cache_db.py` — CachedProjectRow new fields
- `tests/test_phase_b_cache_mapping.py` — cached_project_row_from_scan new fields
- `tests/test_phase_b_cache_rebuild.py` — rebuild_year_cache to rebuild_appcode_year_cache
- `tests/test_phase_c_dashboard_service.py` — DashboardProject new fields, subprojects to drones
- `tests/test_phase_c_js_api_subproject_file_notes.py` — rename to drone, list_subprojects to list_drones
- `tests/test_phase_c_js_api_project.py` — create_project needs appcode + project_type
- `tests/test_phase_c_js_api_project_mutations.py` — same
- `tests/test_phase_c_scanner_service.py` — scan_year to scan_appcode_year
- `tests/test_project_rename_delete.py` — path scaffold + delete_subproject to delete_drone
- `tests/test_project_service_reopen.py` — path scaffold
- `tests/test_project_transitions_unit.py` — path scaffold
- `tests/test_project_transitions_property.py` — path scaffold
- `tests/test_project_file_operations.py` — path scaffold
- `tests/test_year_create.py` — create_year now appcode-scoped
- `tests/test_phase_e_cr_state_guarded.py` — path scaffold
- `tests/test_phase_f_drone_state_guarded.py` — path scaffold
- `tests/test_phase_g_project_create_update.py` — create_project new params
- `tests/test_phase_d_app_web_project_details_read_wiring.py` — subproject_list to drone_list
- `tests/test_phase_d_app_web_project_service_adapter.py` — path scaffold + new params

Frontend tests:
- `frontend/tests/components.test.mjs` — SubProjectTable to DroneTable
- `frontend/tests/project-details-fase3-fase4.test.mjs` — sub-projects to drones
- `frontend/tests/project-actions.test.mjs` — onSubprojectsChanged to onDronesChanged

**Pattern perubahan path scaffold:**
```python
# OLD:
root = tmp_path / "CR"
project = root / "2026" / ProjectState.UAT_PREPARE.value / "MYPROJECT"

# NEW:
root = tmp_path / "WORK"
appcode = root / "MYAPP"
appcode.mkdir(parents=True)
(appcode / "appcode.json").write_text('{"display_name":"MYAPP"}', encoding="utf-8")
project = appcode / "2026" / "CR" / ProjectState.UAT_PREPARE.value / "MYPROJECT"
```


## SKILL YANG WAJIB DIPAKAI

Repository ini pakai **superpowers skills**. Sebelum melakukan apapun, check skill yang relevan:

### Untuk fix existing tests (Task 11):
- **`superpowers:executing-plans`** atau **`superpowers:subagent-driven-development`** — execute sisa plan task-by-task
- **`superpowers:test-driven-development`** — fix tests mengikuti TDD pattern
- **`superpowers:verification-before-completion`** — verify all tests pass sebelum declare done

### Untuk mulai Piece B, C, D (setelah A merge):
- **`superpowers:brainstorming`** — WAJIB pertama, untuk design spec baru. Jangan langsung coding.
- **`superpowers:writing-plans`** — setelah spec approved, buat implementation plan
- **`superpowers:subagent-driven-development`** — execute plan task-by-task

### Untuk debugging:
- **`superpowers:systematic-debugging`** — jangan guess, root-cause dulu

### Branch rule (CLAUDE.md):
- Branch dari `main` pakai format `{menu}/{desc}`
- Piece A: `general/appcode-structure` (current)
- Piece B: `project-details/cr-docs-rte`
- Piece C: `automations/approval-polling`
- Piece D: `general/cicd-bitbucket`
- **NEVER run two AI sessions on the same working tree**

## TEMPAT FILE SPEC + PLAN

### Piece A (done — untuk reference):
- **Spec:** `_docs/specs/superpowers/specs/2026-07-01-appcode-cr-structure-design.md`
- **Plan:** `_docs/specs/superpowers/plans/2026-07-01-appcode-cr-structure.md`

### Piece B (_cr-docs + multi-file RTE editor) — SPEC ADA (plan belum ada):
- Scope: `_cr-docs/` folder berisi 4 file: `uat-signoff` (rich-text editable in-app), `prod-lv` (same), 2x `.msg` (manager approval emails). RTE di Project Details punya dropdown untuk switch antara notes, uat-signoff, prod-lv, dan file lain di folder.
- Dependencies: Piece A (folder structure ada, `_cr-docs/` created empty)
- **Spec:** `_docs/specs/superpowers/specs/2026-07-02-cr-docs-rte-design.md`
- Plan: belum ada, buat pakai `superpowers:writing-plans`
- **Spec:** `_docs/specs/superpowers/specs/2026-07-02-approval-automation-design.md`
- Plan: belum ada, buat pakai `superpowers:writing-plans`
- **Spec:** `_docs/specs/superpowers/specs/2026-07-02-cicd-bitbucket-design.md`
- Plan: belum ada, buat pakai `superpowers:writing-plans`
- Build: brainstorm dulu → spec → plan → implement
- Branch: `project-details/cr-docs-rte`

### Piece C (Approval automation) — SPEC ADA (plan belum ada):
- Scope: Project Details automation on/off toggle. Conditional "Send Request UAT Approval" button (muncul ketika: drone exists + drone state Pending Approval + CR number exists + CR state Pending Submission + uat-signoff non-empty). "Send Request LV" button (CR state Approved AND/OR drone state Approved + prod-lv non-empty). Setelah kirim: poll email reply setiap 5 menit (default), max 3 jam (configurable). Auto-download reply `.msg` ke `_cr-docs/`.
- Dependencies: Piece A + Piece B
- Build: brainstorm dulu → spec → plan → implement
- Branch: `automations/approval-polling`

### Piece D (CICD Bitbucket integration) — SPEC ADA (plan belum ada):
- Scope: Git CLI detection + install guidance. Bitbucket clone helper (paste HTTP URL → app clones `cicd` branch). In-app repo file browser (VSCode-like tree, klik file → buka di VSCode/Notepad++/default app). CICD folder configurable per-appcode atau shared root.
- Dependencies: Piece A saja (bisa paralel dengan B/C)
- Build: brainstorm dulu → spec → plan → implement
- Branch: `general/cicd-bitbucket`

## COMMANDS (dari CLAUDE.md)

```bash
# Run app
D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m main

# Full tests
D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/ -v

# Frontend build
npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run build

# Frontend check
npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run check
```

## KEY RULES

- **Repo-Root Guard:** semua run dari `D:/Ibrahim/Projects/project_tracker`, never worktrees
- **Smallest Diff:** Delete > edit > add. No new file/abstraction/config/dependency unless existing place cannot hold it
- **No hard delete:** `send2trash` only
- **`core/` pure Python:** no UI, no I/O imports
- **Bridge returns `{ success, data, error }`**
- **`_reference/` is legacy:** DO NOT TOUCH
- **Documentation Sync:** product behavior change → PRD.md + PROGRESS.md
- **Design-First:** any UI work → mockup/preview first → user approves → code
Setelah fix, run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/ -v`

### Setelah Task 11 selesai:

1. Run app: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m main`
2. User manual verify + approve
3. Merge `general/appcode-structure` ke `main`
4. Update `_docs/PROGRESS.md`
5. Delete branch

