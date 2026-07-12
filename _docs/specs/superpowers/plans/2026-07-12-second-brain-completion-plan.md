# Second Brain Completion Implementation Plan

> **Execution mode:** implement sequentially on `second-brain/complete-menu`. Use `superpowers:executing-plans`; do not use parallel agents because this repository forbids multiple sessions on one working tree.

**Goal:** Finish Second Brain Notes and Link Bank according to the approved design, with zero-config Personal Notes, complete Project Documents indexing, exact Project Details editor parity, safe filesystem operations, and JSON/CSV Link Bank workflows.

**Approved design:** `_docs/specs/superpowers/specs/2026-07-12-second-brain-completion-design.md`

**Architecture:** `SecondBrainService` owns a cached filesystem index while files remain canonical. `LinkBankService` owns Link Bank rules over atomic `link_bank.json`. SQLite stores only capped disposable activity. Frontend becomes a thin shell plus Notes and Link Bank workspaces; `NotesEditor.svelte` is reused unchanged.

**Stack:** Python 3.12+, pathlib/sqlite3/csv/json stdlib, Svelte 5 + TypeScript, existing Tiptap v3 NotesEditor, pywebview/WebView2.

---

## 1. Locked Decisions

1. Personal Notes default: `Documents\Project Tracker\Second Brain`.
2. Settings can override to an external folder.
3. Existing override is preserved; it is not independently moved.
4. Notes is initial Second Brain tab.
5. Second Brain mounts the existing `NotesEditor.svelte` directly.
6. Editor load/save/flush/capability/DOCX behavior mirrors Project Details exactly.
7. Do not edit `NotesEditor.svelte`, `frontend/src/lib/extensions/*`, or `frontend/src/lib/markdown.ts` in this scope.
8. Project Documents edits original eligible files; no copy/import layer.
9. Project Documents covers CR, Non-CR, and Drone trees.
10. Exclude all CICD, `.git`, `.rte`, hidden paths, `project_data.json`, `appcode.json`, `.project_tracker_index.json`, and Personal Notes duplicate paths.
11. Project `IMPLEMENTED` lock follows existing Project Details capability behavior.
12. Link Bank supports JSON and CSV import/export.
13. Link/category removal is soft archive only; no hard delete.
14. Filesystem content and `link_bank.json` are canonical. SQLite remains rebuildable convenience state.
15. No new runtime dependency.

---

## 2. Safety and Workflow Gates

- Work only on `second-brain/complete-menu`, directly based on `main`.
- Run commands only from `D:/Ibrahim/Projects/project_tracker`.
- TDD per task: focused RED → smallest implementation → focused GREEN → commit.
- Preserve legacy bridge methods while adding the new surface.
- Every bridge response stays `{ok, data, error}`.
- Do not run full backend tests unless user explicitly requests them.
- Do not run `npm run build` while Project Tracker is open.
- After a build, restart before live testing because `web/static` is gitignored.
- Leave `.harness-mem/` and unrelated untracked files unstaged.
- Code-complete is not slice-complete. User live verification and explicit merge approval remain mandatory.

---

## 3. Target File Map

| File | Responsibility |
| --- | --- |
| `services/bootstrap_service.py` | Default Personal Notes creation without overriding external configuration. |
| `services/second_brain_service.py` | Personal/Project index, metadata, filters, related notes, guarded CRUD, preview, activity hooks. |
| `services/link_bank_service.py` | New Link Bank business service, archive/restore, open, JSON/CSV import/export. |
| `infrastructure/cache_db.py` | Capped `second_brain_activity` table and methods. |
| `infrastructure/link_bank_store.py` | Backward-compatible archived-category schema and atomic persistence. |
| `web/js_api.py` | Expanded protocols and bridge facades. |
| `app_web.py` | Service wiring; remove obsolete inline/provider business logic. |
| `frontend/src/lib/types.ts` | Second Brain and Link Bank DTOs. |
| `frontend/src/lib/components/SecondBrain.svelte` | Thin page shell, tabs, active refresh. |
| `frontend/src/lib/components/SecondBrainNotes.svelte` | New explorer/editor/context workspace. |
| `frontend/src/lib/components/LinkBank.svelte` | New category/list/detail workspace. |
| `frontend/tests/second-brain-completion.test.mjs` | New source/integration contracts. |
| Existing focused Python tests | Extend existing coverage; do not create overlapping backend test files. |
| `PRD.md`, `_docs/DECISIONS.md`, `_docs/PROGRESS.md`, `_docs/session-notes.md` | Product truth and completion state. |

---

## 4. Execution Order

### Task 1 — Bootstrap the Default Personal Notes Folder

**Files**
- Modify `services/bootstrap_service.py`
- Extend `tests/test_bootstrap_service.py`

**Contracts**
- `default_second_brain(root: Path) -> Path`
- `ensure_second_brain_folder(settings: AppSettings, root: Path) -> bool`

**Implementation**
1. Add default helper returning `<root>/Second Brain`.
2. On every successful bootstrap path, assign/create it only when `second_brain_folder is None`.
3. Preserve an existing configured override exactly.
4. Do not alter settings in migration-failure paths.

**Tests**
- Fresh settings create default root and Second Brain folder.
- Existing default root repairs an unset Second Brain folder.
- Existing external override remains unchanged and no default duplicate is created.
- Root migration rules remain green.

**Verify**
```powershell
D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_bootstrap_service.py -v
```

**Commit:** `feat(second-brain): bootstrap default notes folder`

---

### Task 2 — Build the Personal and Project Filesystem Index

**Files**
- Modify `services/second_brain_service.py`
- Modify `app_web.py`
- Extend `tests/test_phase_g_second_brain_index.py`
- Extend `tests/test_phase_c_second_brain_service.py`

**DTO: `SecondBrainItem`**
- Existing: `id`, `title`, `path`, `item_type`, `updated_at`, `pinned`, `favorite`, `excerpt`
- Add: `source`, `relative_path`, `tree_path`, `parent_path`, `open_mode`, `file_format`, `project_path`, `project_state`, `appcode`, `year`, `project_name`, `drone_name`, `locked`, `tags`, `match_reason`

**Workspace contract**
```text
workspace() -> {
  items, warnings, personal_root, project_root,
  personal_status: ready|unset|missing|invalid|unreadable
}
```

**Implementation**
1. Replace the old personal-only provider with a service-owned cached index.
2. Scan Personal Notes using guarded `os.walk`; include actual folder nodes.
3. Discover projects through existing `discover_appcodes` + `scan_appcode_year`.
4. Build distinct tree paths:
   - CR: `appcode/year/CR/state/project/...`
   - Non-CR: `appcode/year/Non-CR/project/...`
   - Drone remains within its project hierarchy and receives `drone_name` context.
5. Stable project identity excludes mutable CR state, so IDs survive state-folder moves.
6. Read safe text files up to 1 MiB in full for search; keep excerpt display-only and capped at 200 characters.
7. One unreadable file/path adds a warning without failing the rest of the index.
8. Classify Markdown/text/DOCX/image/external modes.
9. Exclude every locked internal/default path listed in §1.
10. Remove `_second_brain_items_provider` from `app_web.py`; inject settings root, Personal folder, and existing `MetadataStore` into the service.

**Tests**
- Personal hierarchy and Project hierarchy both render.
- CR, Non-CR, and Drone files carry correct context/tree path.
- CICD/internal/metadata/hidden paths never appear.
- Personal root is not duplicated in Project Documents.
- Text after character 200 is searchable.
- Unreadable file produces warning while readable files remain.
- Project item ID survives UAT_PREPARE → PROD_READY move.
- Missing external override is reported, not replaced.

**Verify**
```powershell
D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_phase_g_second_brain_index.py tests/test_phase_c_second_brain_service.py -v
```

**Commit:** `feat(second-brain): index personal and project documents`

---

### Task 3 — Add Tags, Filtered Search, and Related Notes

**Files**
- Modify `services/second_brain_service.py`
- Extend `tests/test_phase_c_second_brain_service.py`
- Extend `tests/test_second_brain_pin_favorite_property.py`

**Contracts**
- `set_tags(item_id: str, tags: list[str]) -> SecondBrainItem`
- `search(query, date_filter="", sort="newest", type_filter="all", source_filter="all")`
- `related(item_id: str, limit: int = 20)` returning `{item, reason, score}` rows
- Public `invalidate()`

**Implementation**
1. Upgrade `.project_tracker_index.json` to version 2 while reading version 1.
2. Persist normalized case-insensitive-deduplicated tags beside pin/favorite flags.
3. Search title, filename/path, complete indexed content, tags, and project context.
4. Apply date/type/source filters before sorting.
5. Sort newest, oldest, A–Z, or type with timezone-aware fallback.
6. Rank related items by wiki link, shared tag, same Drone, then same project.
7. Reload the correct sidecar when Settings changes the Personal override.

**Tests**
- Tags persist across restart and remain searchable.
- Search filters and `match_reason` are correct.
- Wiki/tag/project/Drone reasons and rank are deterministic.
- Switching external override cannot leak metadata from the old folder.

**Verify**
```powershell
D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_phase_c_second_brain_service.py tests/test_second_brain_pin_favorite_property.py tests/test_phase_g_second_brain_index.py -v
```

**Commit:** `feat(second-brain): add metadata search and related notes`

---

### Task 4 — Complete Guarded Personal CRUD and Notes Bridge

**Files**
- Modify `services/second_brain_service.py`
- Modify `web/js_api.py`
- Modify `app_web.py`
- Extend `tests/test_second_brain_note_crud.py`
- Extend `tests/test_phase_c_js_api_second_brain.py`
- Extend `tests/test_phase_c_js_api_second_brain_create.py`

**Service contracts**
- `rename_item`, `recycle_item`, `read_image`, `mark_saved`, `use_default_folder`, `refresh`

**Bridge additions**
- `second_brain_workspace`
- expanded `second_brain_search`
- `second_brain_tags`, `second_brain_related`
- `second_brain_rename`, `second_brain_recycle`
- `second_brain_image`, `second_brain_mark_saved`
- `second_brain_use_default_folder`, `second_brain_refresh`

**Implementation**
1. Reuse existing Windows filename/traversal/duplicate guards.
2. Create only approved text-like file types; defaulting to `.md` belongs in frontend.
3. Rename/recycle only Personal items.
4. Transfer descendant sidecar metadata when a Personal folder is renamed.
5. Route recycle through existing `send2trash` helper.
6. Return image preview only for indexed image items.
7. `mark_saved` invalidates and reloads full-content search after shared RTE autosave.
8. `use_default_folder` updates Settings only after creating the default folder.
9. Preserve all legacy list/get/pin/favorite/create/write/delete bridge methods and error codes.
10. Add a Settings folder setter when wiring `SecondBrainService`.

**Tests**
- Folder rename transfers descendant pin/favorite/tags.
- Project rename/recycle rejects with clear Personal-only error.
- Traversal/reserved/duplicate names remain blocked.
- Image preview is index/type guarded.
- `mark_saved` replaces stale search content.
- Use-default creates and persists the correct path.
- Every new facade forwards exact arguments and returns standard envelope.

**Verify**
```powershell
D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_second_brain_note_crud.py tests/test_phase_c_js_api_second_brain.py tests/test_phase_c_js_api_second_brain_create.py tests/test_phase_g_second_brain_index.py -v
```

**Commit:** `feat(second-brain): complete guarded notes operations`

---

### Task 5 — Persist Capped Recent Activity

**Files**
- Modify `infrastructure/cache_db.py`
- Modify `services/second_brain_service.py`
- Modify `services/bootstrap_service.py`
- Modify `web/js_api.py`
- Modify `app_web.py`
- Extend cache/service/facade/bootstrap tests

**Contracts**
- `SecondBrainActivityRow(id, item_id, path, title, source, action, timestamp)`
- `CacheDb.append_second_brain_activity`, `list_second_brain_activity`, `clear_second_brain_activity`
- `SecondBrainService.record_activity`, `list_activity`
- `second_brain_activity_record`, `second_brain_activity_list`

**Implementation**
1. Add `second_brain_activity` SQLite table and health-check expectation.
2. Supported actions: opened, created, edited, renamed, recycled, opened_externally.
3. Store newest-first by timestamp then ID; cap at 200.
4. Repeated opens for the same item update/dedupe one row and still move to newest position.
5. Hook successful create/rename/recycle/mark_saved only after mutation succeeds.
6. Frontend records opened/opened_externally.
7. Clear activity during both whole-root migration and orphan-root reset.

**Tests**
- Dedupe, newest ordering, and cap.
- Health check includes new table.
- Mutation hooks never log failed operations.
- Bridge delegation.
- Root migration/orphan reset clears disposable activity.

**Verify**
```powershell
D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_phase_b_cache_db.py tests/test_phase_c_second_brain_service.py tests/test_phase_c_js_api_second_brain.py tests/test_bootstrap_service.py -v
```

**Commit:** `feat(second-brain): persist recent activity`

---

### Task 6 — Move Link Bank Rules into a Service

**Files**
- Create `services/link_bank_service.py`
- Modify `infrastructure/link_bank_store.py`
- Modify `web/js_api.py`
- Modify `app_web.py`
- Extend `tests/test_phase_f_linkbank_stable_ids.py`
- Extend `tests/test_phase_c_js_api_settings_linkbank.py`
- Extend `tests/test_phase_d_app_web_linkbank_wiring.py`

**Contracts**
- Existing CRUD protocol remains compatible.
- Add `restore_link`, `category_restore`, `open_link`, `export_file`, `preview_import`, `merge_import`.
- Add bridge methods with matching `linkbank_*` names.

**Persistence**
- `LinkBank` adds `archived_categories` with legacy-file normalization.
- Normalize booleans to `"true"|"false"`.
- Continue using atomic `LinkBankStore.write`.

**Import/export rules**
1. JSON retains complete canonical data.
2. CSV columns: `id,name,url,category,tags,description,pinned,favorite,archived,created_at,updated_at`.
3. Preview returns add/update/conflict/invalid counts and skipped rows without writing.
4. Matching stable ID updates unless its URL belongs to another ID.
5. New ID + unique normalized URL adds.
6. Same URL under another ID conflicts and is skipped.
7. Duplicate IDs/URLs inside one import conflict and are skipped.
8. Categories merge case-insensitively while preserving canonical spelling.
9. Archived categories and their links remain archived after JSON restore.
10. Malformed input performs no write.
11. Confirmed merge writes once atomically.

**Other behavior**
- Validate non-empty name and HTTP(S) URL.
- Category/link archive and restore update timestamps.
- OS browser open occurs only through the service with an injected opener in tests.
- Delete the inline `_LinkBankAdapter`; wire `LinkBankService` around the existing store.

**Tests**
- Legacy schema and stable IDs.
- Link/category archive and restore.
- Case-insensitive category behavior.
- JSON/CSV complete export.
- Preview/merge add, update, conflict, invalid, duplicate, archived-category, and no-write cases.
- Browser opener injection.
- New facades and real `app_web` wiring.

**Verify**
```powershell
D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_phase_f_linkbank_stable_ids.py tests/test_phase_c_js_api_settings_linkbank.py tests/test_phase_d_app_web_linkbank_wiring.py -v
```

**Commit:** `feat(second-brain): complete link bank service`

---

### Task 7 — Define Frontend DTOs

**Files**
- Modify `frontend/src/lib/types.ts`
- Create `frontend/tests/second-brain-completion.test.mjs`

**Types**
- `SecondBrainSource`, `SecondBrainOpenMode`, `SecondBrainPersonalStatus`, `SecondBrainSort`
- Complete `SecondBrainItem`, `SecondBrainWorkspace`, `SecondBrainRelated`, `SecondBrainActivity`, `SecondBrainImage`
- `LinkItem`, `LinkBankData`, `LinkImportPreview`, `LinkImportResult`, `LinkExportPayload`

**Rules**
- Match Python names exactly.
- Do not weaken existing `RteFileContent`, `RteDocumentPayload`, capability, feature, or save-strategy types.
- Keep legacy-compatible optional Link description mapping because canonical storage uses details/notes.

**Tests**
- Source contracts assert all required DTO names/fields.
- Type checker has no new errors.

**Verify**
```powershell
node --test frontend/tests/second-brain-completion.test.mjs
npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run check
```

**Commit:** `feat(second-brain): define frontend workspace contracts`

---

### Task 8 — Build `SecondBrainNotes.svelte`

**Files**
- Create `frontend/src/lib/components/SecondBrainNotes.svelte`
- Extend `frontend/tests/second-brain-completion.test.mjs`

**Public component API**
- `refresh(): Promise<void>`
- `flush(): Promise<boolean>`

**Layout**
- Command bar: search, date, type, source, sort.
- Explorer width: `clamp(260px, 24vw, 340px)`.
- Sections: Search Results, Pinned, Favorites, Personal Notes, Project Documents.
- Right: source ribbon, editor/image/external state, Related/Activity shelf.
- Recursive tree stays local; no one-use shared abstraction.

**Selection contract — mirror Project Details**
1. Set `second-brain-rte` interaction lock.
2. Await current editor `flushNow()`.
3. Abort and retain current editor/selection when flush returns false.
4. Assign requested item and clear old payload.
5. DOCX → `rteDocumentOpen`; other supported text → `getRteFile`; image → guarded Second Brain bridge.
6. Ignore stale async response using monotonically increasing request token.
7. Mount unchanged `NotesEditor` under `{#key selectedItem.path}` with all Project Details-equivalent props.
8. Release lock only for the current request.
9. `onSaved` calls `second_brain_mark_saved`; do not save excerpts or duplicate editor logic.

**Interactions**
- 150 ms debounced search with stale-result guard.
- Folder selection controls Personal create target.
- Inline create/rename: Enter commits, Escape cancels, F2 renames.
- Delete key opens Recycle confirmation for Personal items only.
- Ctrl+F focuses search.
- Pin/favorite/tags update sidecar metadata.
- Missing override exposes Browse folder and Use default folder.
- Images preview inline; unsupported files show reason and Open externally.
- Activity missing targets remain visible but disabled.

**Tests**
- Direct `NotesEditor.svelte` import and mount.
- No textarea/alternate Markdown toolbar/editor fork.
- Flush occurs before selection assignment/load.
- Stale-load and stale-search guards exist.
- All approved explorer/recovery/context/keyboard labels exist.
- Scoped CSS uses existing tokens, required widths, reduced motion, and responsive context shelf.

**Verify**
```powershell
node --test frontend/tests/second-brain-completion.test.mjs
npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run check
```

**Commit:** `feat(second-brain): build notes explorer workspace`

---

### Task 9 — Build `LinkBank.svelte`

**Files**
- Create `frontend/src/lib/components/LinkBank.svelte`
- Extend `frontend/tests/second-brain-completion.test.mjs`

**Public component API**
- `refresh(): Promise<void>`

**Layout**
- Category rail: All, Pinned, Favorites, active categories with counts, Archived, archived categories.
- Workspace toolbar: date, sort, Add, Import, Export JSON, Export CSV.
- Compact link list plus selected-link/add/edit detail pane.
- At ≤1200 px available width, list/detail stack while category rail remains.

**Behavior**
- Add/Edit reuse detail pane.
- Name and URL required; backend remains authoritative validator.
- Open through `linkbank_open`, never raw target-blank navigation.
- Copy uses clipboard with WebView fallback.
- Pin/favorite update through existing update facade.
- Link/category archive and restore use confirmation; no delete action.
- Hidden file input accepts JSON/CSV.
- Import must call preview before merge and show add/update/conflict/invalid summary.
- Cancelled or malformed import writes nothing.
- Export payload goes through native `util_save_file`.

**Tests**
- Every service facade is referenced.
- No delete or target-blank behavior.
- Preview appears before merge.
- JSON/CSV/native-save paths exist.
- Category/list/detail and responsive stack contracts exist.
- Token-only scoped colors; reduced-motion support.

**Verify**
```powershell
node --test frontend/tests/second-brain-completion.test.mjs
npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run check
```

**Commit:** `feat(second-brain): build link bank workspace`

---

### Task 10 — Replace the Monolith with a Thin Shell

**Files**
- Replace `frontend/src/lib/components/SecondBrain.svelte`
- Extend `frontend/tests/second-brain-completion.test.mjs`
- Update `frontend/tests/as-is-prototype-parity.test.mjs` for split components

**Implementation**
1. Keep existing white page header and icon.
2. Default active tab to Notes; tab state is component-session-only.
3. Mount Notes once so editor state is not discarded.
4. Lazy-mount Link Bank on first selection, then preserve its state.
5. Before Notes → Link Bank, await `notesPanel.flush()` and abort on false.
6. Refresh button routes only to active child.
7. Add accessible tablist/tab/tabpanel relationships and visible focus.
8. Delete all old inline Notes/Link Bank state, bridge calls, textarea editor, and styles from the shell.

**Tests**
- Thin child imports.
- Notes-default state.
- Tab-switch flush and active-child refresh.
- No business bridge calls or editor implementation in shell.
- Existing page-title/prototype contracts follow the split sources.
- No hard-coded hex colors in the three Second Brain components.

**Verify**
```powershell
node --test frontend/tests/second-brain-completion.test.mjs
npm --prefix D:/Ibrahim/Projects/project_tracker/frontend test
npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run check
```

Expected: all frontend tests pass; `svelte-check` has 0 errors and no warning increase over the 13-warning baseline.

**Commit:** `feat(second-brain): integrate completed menu workspace`

---

### Task 11 — Completion Gate, Documentation, and User Verification

#### 11.1 Automated gate

```powershell
D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_bootstrap_service.py tests/test_phase_g_second_brain_index.py tests/test_phase_c_second_brain_service.py tests/test_second_brain_note_crud.py tests/test_second_brain_pin_favorite_property.py tests/test_phase_c_js_api_second_brain.py tests/test_phase_c_js_api_second_brain_create.py tests/test_phase_b_cache_db.py tests/test_phase_f_linkbank_stable_ids.py tests/test_phase_c_js_api_settings_linkbank.py tests/test_phase_d_app_web_linkbank_wiring.py -v
node --test frontend/tests/second-brain-completion.test.mjs
npm --prefix D:/Ibrahim/Projects/project_tracker/frontend test
npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run check
D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m py_compile services/bootstrap_service.py services/second_brain_service.py services/link_bank_service.py infrastructure/cache_db.py infrastructure/link_bank_store.py web/js_api.py app_web.py
git diff --check
```

Required result: focused backend and all frontend tests pass; `svelte-check` 0 errors; Python compile and diff check clean.

#### 11.2 Documentation sync

Update:
- `PRD.md` §§13, 14, 17.4, 21.9, 21.10, Phase F, and resolved CSV calibration item.
- `_docs/DECISIONS.md`: add D-0017 for default/override, shared editor, filesystem index, disposable activity, and LinkBankService JSON/CSV rules.
- `_docs/PROGRESS.md`: branch implemented + automated verified + user live gate pending.
- `_docs/session-notes.md`: Now/Next/Blocked and `active_menu: second-brain`.
- Cross-session memory with the same decision/state if integration is available; do not use `.harness-mem/` as substitute.

**Commit:** `docs(second-brain): record completion verification`

#### 11.3 Production build gate

1. Check whether Project Tracker is running.
2. If running, stop and ask user to close it; never terminate it silently.
3. After user confirms closure and approves build:

```powershell
npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run build
```

4. Restart only from repo root:

```powershell
D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m main
```

#### 11.4 Mandatory live checklist

**Default/override**
- [ ] Fresh unset configuration creates default Personal Notes.
- [ ] External override remains unchanged.
- [ ] Missing override recovery actions work.

**Explorer/data**
- [ ] Personal, CR, Non-CR, and Drone hierarchy correct.
- [ ] CICD/internal/default metadata never appears.
- [ ] Full-content/tag/path search and all filters/sorts work.
- [ ] Personal create/rename/recycle validation works; Project mutation stays disabled.
- [ ] Pin/favorite/tags persist across restart/rename.
- [ ] Related reasons and activity behavior correct.
- [ ] Image and unsupported external-open modes work.

**Exact NotesEditor parity**
- [ ] Toolbar, formatting, autosave/status, undo/redo, links, images, tables, zoom, fullscreen match Project Details.
- [ ] Plain-text capability matches.
- [ ] DOCX migration/revision/export path matches.
- [ ] IMPLEMENTED lock/read-only behavior matches.
- [ ] Rapid A→B→A switching never crosses content.
- [ ] Save failure blocks file/tab switch and preserves current editor.

**Link Bank**
- [ ] Category/link add/edit/search/pin/favorite/archive/restore persist.
- [ ] OS-browser open and Copy URL work.
- [ ] JSON/CSV export correct.
- [ ] Import preview/cancel/confirm/conflict/invalid/malformed flows correct and atomic.

**Responsive/control states**
- [ ] 960×640, 1024×768, 1280×720, and 1920×1080 usable without body overflow.
- [ ] Link list/detail stacks only at narrow width; Related/Activity become two columns at wide width.
- [ ] Buttons show default, hover, focus, active, disabled, loading, success, and error states.
- [ ] Ctrl+F, F2, Delete, Enter, Escape, tab order, focus rings, and reduced motion work.
- [ ] Design tokens match `_docs/DESIGN_RULES.md`.

#### 11.5 Fix and merge policy

- Fix one failed behavior per round.
- Add focused RED regression, apply smallest fix, run GREEN, rebuild only with app closed, then user retests.
- Shared RTE files remain off-limits without new approval.
- Do not mark the slice complete or merge until every live item passes and user explicitly approves merge.
- After approval: update tracking/memory, rerun final focused gates, commit tracking, merge to `main`, keep branch unless user asks deletion.

---

## 5. Final Definition of Done

- Approved design fully represented in code and PRD.
- No alternate Second Brain editor exists.
- No excerpt-based editor/save path remains.
- Default and external override paths both safe.
- Project Documents includes intended user files and excludes CICD/app internals.
- Link Bank JSON/CSV workflows are previewed and atomic.
- Automated gates green.
- User live checklist green at all required sizes.
- Explicit merge approval received.
