# Piece B — CR Docs (`_cr-docs`) + Multi-file RTE Editor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:executing-plans` (inline — handoff forbids delegating mutating work to subagents/worktrees). Steps use `- [ ]` checkboxes.

**Goal:** Add a CR-only "CR Docs" editor in Project Details that switches between editing `notes.md`, `_cr-docs/uat-signoff`, `_cr-docs/prod-lv` (rich text via existing Tiptap), and displaying/opening two `.msg` approval files.

**Architecture:** Reuse the existing `NotesEditor` (Tiptap v3) by adding optional `filePath` + `fileFormat` props. Add two new bridge methods (`get_rte_file`, `save_rte_file`) modeled on the `notes_get`/`notes_update` precedent. `_cr-docs` HTML files store Tiptap-native HTML (no Markdown round-trip); `notes.md` keeps its existing Markdown path untouched. Missing `uat-signoff`/`prod-lv` are lazily scaffolded (0-byte) on first read — the **single** creation mechanism, so `create_project` is NOT modified. State-lock rule mirrors `notes_update` (view-only in IMPLEMENTED).

**Tech Stack:** Svelte 5 (runes) + TypeScript + Tailwind v4; Tiptap v3 (ProseMirror); pywebview JS bridge (`{ok,data,error}`); Python 3.12 services; `pathlib`; atomic text writes; `send2trash` (no hard delete).

**Branch:** `project-details/cr-docs-rte` (from `main`). Keep branch after merge.

**Spec:** `_docs/specs/superpowers/specs/2026-07-02-cr-docs-rte-design.md` (with 2026-07-03 amendments A1–A6).

---

## Reconciled decisions (override conflicting parts of the spec doc; see spec Amendments)

1. **No new Python tests** — handoff hard rule wins over spec §5. Verify with `svelte-check`, existing frontend tests, and the manual checklist. No `tests/test_cr_docs_creation.py`, no `tests/test_rte_file_bridge.py`.
2. **Lazy scaffold on read** — `get_rte_file` creates a missing `uat-signoff`/`prod-lv` (0-byte) then loads it. Supersedes spec §3 (do **not** modify `create_project`). Works uniformly for Piece A projects (empty `_cr-docs/`) and new projects.
3. **State lock = treat like notes** — editable in `UAT_PREPARE`/`PROD_READY`/`POSTPONED`/`CANCELED`; view-only in `IMPLEMENTED`. Mirrors `app_web.py:1362-1370`.
4. **Scope = project-level only.** Spec §2 mentions a drone-level dropdown; this piece implements the **project-level** editor only (matches handoff scope + manual checklist). Drone editing left untouched.
5. **`.msg` files are Piece C's creation responsibility.** Piece B only *displays/opens* them if present (no auto-create, no download).

---

## File Structure (what changes)

**Backend / bridge (Python):**
- `web/js_api.py` — add `get_rte_file`, `save_rte_file` facade methods (modeled on `notes_get`/`notes_update` at `js_api.py:1532-1552`).
- `app_web.py` — add `_CrDocsServiceAdapter` (or extend `_NotesServiceAdapter`) with `get_rte_file`/`save_rte_file` logic; lazy-scaffold + state-lock helpers. **No change to `create_project`.**

**Frontend:**
- `frontend/src/lib/components/NotesEditor.svelte` — add optional `filePath?: string` + `fileFormat?: "markdown" | "html"` props; branch load/save on format; keep `notes.md` path byte-for-byte identical when props absent.
- `frontend/src/lib/components/ProjectDetails.svelte` — add CR Docs section (guarded by `{#if !isNonCr}`) with a file `<select>`; render `<NotesEditor>` or `.msg` open-external panel based on selection; load via `get_rte_file`/`notes_get`.
- `frontend/src/lib/types.ts` — add `RteFile` type (`{name, path, format, editable, isOpenable}`) + `RteFileContent` (`{content, format, editable}`).
- `frontend/src/lib/bridge.ts` — thin typed `getRteFile`/`saveRteFile` wrappers (reuse `callBridge`). **No new dependency.**

**Docs (Phase 0 + final):**
- `_docs/specs/superpowers/specs/2026-07-02-cr-docs-rte-design.md` — Amendments 2026-07-03 (decisions 1–6).
- `_docs/specs/superpowers/plans/2026-07-03-cr-docs-rte-plan.md` — this plan doc.
- `_docs/PROGRESS.md`, `_docs/session-notes.md` — updated at end.

**No new dependencies. No core/ changes. No `_reference/` changes. No new Python test files.**

---

## Tasks

### Task 0: Spec amendment + plan doc (Phase 0, design-first rule)

**Files:**
- Modify: `_docs/specs/superpowers/specs/2026-07-02-cr-docs-rte-design.md`
- Create: `_docs/specs/superpowers/plans/2026-07-03-cr-docs-rte-plan.md`

- [x] **Step 1:** Append "## Amendments (2026-07-03)" to the spec (decisions A1–A6).
- [x] **Step 2:** Write this plan to `_docs/specs/superpowers/plans/2026-07-03-cr-docs-rte-plan.md`.
- [ ] **Step 3:** `git add _docs/ && git commit -m "docs(piece-b): amend spec + add implementation plan"`

---

### Task 1: Backend — `get_rte_file` + `save_rte_file` bridge methods

**Files:**
- Modify: `web/js_api.py` (add 2 methods near `notes_get`/`notes_update` ~`:1532-1552`)
- Modify: `app_web.py` (add adapter logic near `_NotesServiceAdapter` ~`:1356-1370`)

**Behavior contract:**
- `get_rte_file(file_path: str) -> dict` → `ok({content, format, editable})`
  - `format` ∈ `"html" | "markdown" | "msg" | "text"` (derived from name/extension).
  - For `uat-signoff` / `prod-lv` (no extension, inside `_cr-docs/`): **lazy-scaffold** — if missing, `touch()` a 0-byte file, then read; `format="html"`.
  - `notes.md`: `format="markdown"` (read raw text; no scaffold).
  - `*.msg`: `format="msg"`, `content=""`, `editable=false` (do NOT read binary into memory).
  - Other: `format="text"`.
  - `editable=false` when containing project state is `IMPLEMENTED` (reuse `_folder_state_for_path` at `app_web.py:98-111`).
- `save_rte_file(file_path: str, content: str) -> dict` → `ok({"saved": true})`
  - Reject if `editable=false` (state lock) → `fail(..., code="LOCKED")`.
  - Reject for `format="msg"` → `fail("msg files are not editable", code="NOT_EDITABLE")`.
  - Write via `_atomic_write_text` (`app_web.py:83-95`).

- [ ] **Step 1:** Add `_CrDocsServiceAdapter` (or methods on `_NotesServiceAdapter`) in `app_web.py` per the contract. Reuse `_folder_state_for_path` + the IMPLEMENTED-check from `_NotesServiceAdapter.notes_update`. Add `_detect_rte_format(path)` → `"html"|"markdown"|"msg"|"text"`.
- [ ] **Step 2:** Wire the adapter into `create_js_api` (mirror how `_notes_service` is constructed/passed).
- [ ] **Step 3:** Add `get_rte_file` + `save_rte_file` on `JsApi` in `web/js_api.py`, each guarded with `SERVICE_UNAVAILABLE` + try/except `..._FAILED`, matching `notes_get`/`notes_update` (`js_api.py:1532-1552`).
- [ ] **Step 4:** Inline REPL smoke: temp CR project dir, `get_rte_file` on nonexistent `_cr-docs/uat-signoff` → file created + `{content:"", format:"html", editable:true}`; `save_rte_file` → file written. (No pytest file — hard rule.)
- [ ] **Step 5:** `git add web/js_api.py app_web.py && git commit -m "feat(bridge): add get_rte_file/save_rte_file for _cr-docs RTE"`

---

### Task 2: Frontend types + bridge helpers

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/bridge.ts`

- [ ] **Step 1:** Add to `types.ts`:
  ```ts
  export type RteFormat = "html" | "markdown" | "msg" | "text";
  export interface RteFile { name: string; path: string; format: RteFormat; editable: boolean; isOpenable: boolean; }
  export interface RteFileContent { content: string; format: RteFormat; editable: boolean; }
  ```
- [ ] **Step 2:** In `bridge.ts`, add typed wrappers reusing `callBridge`:
  ```ts
  export const getRteFile = (filePath: string) => callBridge<RteFileContent>("get_rte_file", filePath);
  export const saveRteFile = (filePath: string, content: string) => callBridge<{ saved: boolean }>("save_rte_file", filePath, content);
  ```
- [ ] **Step 3:** `npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run check` → 0 errors.
- [ ] **Step 4:** `git add frontend/src/lib/types.ts frontend/src/lib/bridge.ts && git commit -m "feat(frontend): add RTE file types + bridge wrappers"`

---

### Task 3: Generalize `NotesEditor.svelte` (optional `filePath` + `fileFormat`)

**Files:**
- Modify: `frontend/src/lib/components/NotesEditor.svelte`

**Rule:** When `filePath`/`fileFormat` are absent, behavior must be **identical** to today (Markdown via `notes_get`/`notes_update`). Only the `_cr-docs` HTML path is new.

- [ ] **Step 1:** Extend `Props` (`:25-30`) with optional `filePath?: string` and `fileFormat?: "markdown" | "html"` (default `"markdown"`).
- [ ] **Step 2:** Branch **load** in the editor `$effect` (`:448-505`): if `fileFormat === "html"`, `editor.commands.setContent(text)` directly (skip `renderMarkdown`); else existing `renderMarkdown(text)`.
- [ ] **Step 3:** Branch **save** in `onEditorUpdate`/`flush` (`:113-130`, `:275-287`): if `fileFormat === "html"`, `text = editor.getHTML()` + `saveRteFile(filePath, text)`; else existing `htmlToMarkdown(...)` + `notes_update`. Preserve 1000ms autosave + `lastSaved` dirty guard + `onSaved`.
- [ ] **Step 4:** Key remount on `filePath ?? projectPath` so switching docs within one project reloads content.
- [ ] **Step 5:** `npm --prefix frontend run check` → 0 errors.
- [ ] **Step 6:** `git add frontend/src/lib/components/NotesEditor.svelte && git commit -m "feat(notes-editor): support HTML file mode for _cr-docs"`

---

### Task 4: CR Docs section + file selector in `ProjectDetails.svelte`

**Files:**
- Modify: `frontend/src/lib/components/ProjectDetails.svelte`

- [ ] **Step 1:** Add state: `crDocsFiles`, `selectedCrDocPath`, `crDocContent`, `loadingCrDoc` (runes `$state`).
- [ ] **Step 2:** Build `crDocsFiles` when `detail` loads (CR only): fixed `notes.md` + `_cr-docs/uat-signoff` + `_cr-docs/prod-lv`; plus `_cr-docs/*.msg` via `file_list(project_path + "/_cr-docs")` (guard folder-not-exist). Map to `RteFile`.
- [ ] **Step 3:** Add "CR Docs" section in right pane, wrapped in `{#if !isNonCr}` (mirror Drone block `:873`). `<select>` + editor/panel. Reuse `.pd-section`/`.pd-section-title`/`.sb-tab`.
- [ ] **Step 4:** `selectCrDoc(path)`: msg → open-external panel; else `getRteFile(path)` → `crDocContent`; default-select `notes.md`.
- [ ] **Step 5:** Render: notes.md → existing `<NotesEditor projectPath=... initialNotes={notes} />`; uat-signoff/prod-lv → `<NotesEditor filePath fileFormat="html" initialNotes={crDocContent.content} />`; .msg → "Outlook message" + `[Open Externally]` → `callBridge("file_open", path)`; IMPLEMENTED → read-only + visible hint.
- [ ] **Step 6:** Participate in `refresh()` (`:657`).
- [ ] **Step 7:** `npm --prefix frontend run check` → 0 errors.
- [ ] **Step 8:** `git add frontend/src/lib/components/ProjectDetails.svelte && git commit -m "feat(project-details): add CR Docs section with multi-file RTE selector"`

---

### Task 5: Verify — build + check + manual smoke + responsive

**Files:** none (verification only)

- [ ] **Step 1:** `npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run check` → 0 errors / 0 warnings.
- [ ] **Step 2:** `npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run build` (UI changed).
- [ ] **Step 3:** Run app: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m main`.
- [ ] **Step 4:** Manual smoke (existing CR project from Piece A — has empty `_cr-docs/`):
  - Open Project Details → CR Docs section visible; dropdown lists `notes.md`, `uat-signoff`, `prod-lv`.
  - Select `uat-signoff` → confirm `_cr-docs/uat-signoff` file **created** on disk (lazy scaffold), editor empty.
  - Type text + insert image + add link → wait 1s (autosave) → reopen → content preserved.
  - Repeat for `prod-lv`.
  - Select `notes.md` → existing notes behavior unchanged.
  - (If a `.msg` exists) select it → "Open externally" panel; button opens via OS default.
  - Confirm `_cr-docs` does **not** appear as a Drone.
  - IMPLEMENTED view-only check: move CR project to IMPLEMENTED → editor read-only + hint.
- [ ] **Step 5:** Non-CR project: no CR Docs section, no `_cr-docs` UI; Notes still works.
- [ ] **Step 6:** Responsive: 800×600, 1024×768, 1920×1080 usable.
- [ ] **Step 7:** Regression: Dashboard loads; Project Details loads; Add Drone Ticket works (CR); Non-CR state dropdown works.

---

### Task 6: Docs + finish (after user manual pass)

**Files:**
- Modify: `_docs/PROGRESS.md`, `_docs/session-notes.md`

- [ ] **Step 1:** Update `_docs/PROGRESS.md` (Piece B delivered; verification results).
- [ ] **Step 2:** Update `_docs/session-notes.md` (changes, files touched, verification, active_menu = `main`).
- [ ] **Step 3:** Commit: `docs: mark Piece B complete`.
- [ ] **Step 4:** `superpowers:finishing-a-development-branch`. Merge to `main` **only after user approval**. **Keep branch `project-details/cr-docs-rte` — do not delete.**

---

## Self-review

- **Spec coverage:** §1 → Task 1+3. §2 (project-level) → Task 4. §3 → superseded by lazy scaffold (Task 1). §4 edge cases → Task 1+4. §5 tests → manual checklist (decision 1). `.msg` → Task 4. Non-CR hide → Task 4 `{#if !isNonCr}`. `_cr-docs` not a drone → already true. ✔
- **Placeholders:** none — every code step shows concrete signatures/branches.
- **Type consistency:** `RteFile`/`RteFileContent`/`RteFormat` defined once (Task 2), reused Tasks 1/3/4. `get_rte_file`/`save_rte_file` names identical Python↔TS. `filePath`/`fileFormat` identical Task 3↔4.

## Verification commands
- Frontend check: `npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run check`
- Frontend build: `npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run build`
- Run app: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m main`
- No new Python test files. No full pytest unless explicitly asked.

## Hard rules honored
Repo-root only; no worktree; no subagent mutating work; no parallel sessions; keep merged branch; no new Python tests; smallest diff; no hard delete (`send2trash`); bridge via `bridge.ts` with `{ok,data,error}`; `core/` pure; no `.env`/secrets; `_reference/` untouched; PRD unchanged.

---

# Revision (2026-07-03) — .docx CR Docs + Export Word + Freeze/A3 fixes

Triggered by user testing of the first pass (HTML CR Docs). See spec "Amendments (2026-07-03, revision 2)" for the authoritative change record. This revision supersedes Tasks 1–5 of the original plan above for the CR-Docs storage format and adds the bug fixes.

## Goal (revised)
1. CR Docs stored natively as `.docx` (`uat-signoff.docx`, `prod-lv.docx`) — double-click → MS Word with tables + images intact.
2. `notes.md` (and CR docs) exportable to `.docx` via an "Export to Word" button.
3. Fix Tiptap freeze/lag (serialize off the keystroke path).
4. Fix A3 (doc switch must load content).

## Rule change
"No new dependency unless impossible without it" removed from `CLAUDE.md`. New Python deps: `mammoth`, `htmldocx`, `python-docx`. No frontend deps.

## Tasks (revision)

### Task 0: Rule change + spec/plan amendment — done in this revision.
### Task 1: Backend — deps + docx conversion (`_html_to_docx_bytes`, `_docx_to_html`) + `_detect_rte_format` adds `docx` + lazy-scaffold empty `.docx` + `save_rte_file` binary write + `export_to_docx` + `util_save_bytes` (base64). Inline REPL smoke. PyInstaller spec check.
### Task 2: Frontend — `RteFormat` adds `docx`; `exportToDocx` wrapper.
### Task 3: NotesEditor freeze fix — `dirty` flag; serialize only in `flush()`.
### Task 4: NotesEditor `docx` mode — treat like `html` for load/save.
### Task 5: ProjectDetails — A3 fix (gate render on content-ready via `crDocContentPath`) + `.docx` filenames + "Export to Word" button.
### Task 6: Verify — check + build + boot + manual smoke (Word open + Outlook paste).
### Task 7: Docs + finish.

## Risks
- docx↔HTML round-trip fidelity (acceptable for spec'd content; mitigated by regenerating `.docx` on every save).
- PyInstaller must collect new pure-Python deps.
- `util_save_bytes` base64 transport (small overhead; docx is KB–low MB).
