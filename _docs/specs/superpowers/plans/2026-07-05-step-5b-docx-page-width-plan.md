# Step 5b DOCX Page Width Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render DOCX editor content as a centered fixed-width printable page while keeping Markdown and text editors responsive.

**Architecture:** `NotesEditor.svelte` adds one mode class to the existing editor host. Scoped CSS applies fixed page geometry only when `docxPipelineMode` is true. Existing source-contract tests prove DOCX scoping and preserve the non-DOCX `width:100%` rule.

**Tech Stack:** Svelte 5, TypeScript, Tiptap v3, CSS, Node test runner.

## Global Constraints

- Work only on branch `project-details/tiptap-docx-pipeline` from repo root `D:/Ibrahim/Projects/project_tracker`.
- Modify only `frontend/src/lib/components/NotesEditor.svelte` and `frontend/tests/project-details-fase3-fase4.test.mjs`.
- Keep Step 5c image drag-resize out of this round.
- Add no backend, Markdown serialization, extension, dependency, state, or lifecycle changes.
- DOCX page width is fixed `720px`; narrow hosts scroll horizontally instead of shrinking.
- Markdown and text editors retain `width:100%`.
- Never run `npm run build` while Project Tracker may be open.
- Commit only after user manual verification passes.

---

## File Map

- `frontend/tests/project-details-fase3-fase4.test.mjs`: source-contract regression for mode class and scoped page CSS.
- `frontend/src/lib/components/NotesEditor.svelte`: DOCX-only host class and printable-width styles.

### Task 1: Add DOCX Page Contract

**Files:**
- Modify: `frontend/tests/project-details-fase3-fase4.test.mjs:84`
- Modify: `frontend/src/lib/components/NotesEditor.svelte:1081`
- Modify: `frontend/src/lib/components/NotesEditor.svelte:1129`

**Interfaces:**
- Consumes: existing `docxPipelineMode` derived state and Tiptap-mounted `.ne-textarea` class.
- Produces: `ne-docx-page` host class and DOCX-only fixed page layout.

- [ ] **Step 1: Add failing source-contract test**

Add after `NotesEditor exposes a compact shortcuts help popover`:

```javascript
test("NotesEditor scopes fixed printable width to DOCX mode", () => {
  assert.match(
    NE,
    /<div class="ne-editor-host" class:ne-docx-page=\{docxPipelineMode\} bind:this=\{hostEl\}><\/div>/,
  );
  assert.match(
    NE,
    /\.ne-editor-host\.ne-docx-page\s*\{\s*overflow-x:auto;\s*\}/,
  );
  assert.match(
    NE,
    /:global\(\.ne-editor-host\.ne-docx-page \.ne-textarea\)\s*\{[^}]*width:720px;[^}]*max-width:none;[^}]*margin:0 auto;[^}]*box-sizing:border-box;/,
  );
  assert.match(
    NE,
    /:global\(\.ne-editor-host \.ne-textarea\)\s*\{[^}]*width:100%;/,
  );
});
```

- [ ] **Step 2: Run focused test and confirm red state**

Run:

```powershell
node --import ./frontend/tests/register-hooks.mjs --test --test-name-pattern "fixed printable width" ./frontend/tests/project-details-fase3-fase4.test.mjs
```

Expected: one selected test fails because host lacks `class:ne-docx-page`.

- [ ] **Step 3: Add DOCX mode class**

Replace editor host markup with:

```svelte
<div class="ne-editor-host" class:ne-docx-page={docxPipelineMode} bind:this={hostEl}></div>
```

- [ ] **Step 4: Add fixed printable-page CSS**

Place after existing base `.ne-editor-host .ne-textarea` rule:

```css
/* DOCX page: 184.6mm printable width at 96dpi = 698px,
   plus 20px padding and 2px border = 720px border-box. */
.ne-editor-host.ne-docx-page { overflow-x:auto; }
:global(.ne-editor-host.ne-docx-page .ne-textarea) { width:720px; max-width:none; margin:0 auto; box-sizing:border-box; }
```

Do not alter existing `:global(.ne-editor-host .ne-textarea)` base rule; its current `width:100%` declaration must remain.

- [ ] **Step 5: Run focused test and confirm green state**

Run:

```powershell
node --import ./frontend/tests/register-hooks.mjs --test --test-name-pattern "fixed printable width" ./frontend/tests/project-details-fase3-fase4.test.mjs
```

Expected: one selected test passes; non-matching tests are skipped.

- [ ] **Step 6: Run required non-build checks**

Run:

```powershell
npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run check
npm --prefix D:/Ibrahim/Projects/project_tracker/frontend test
```

Expected: svelte-check reports 0 errors and 0 warnings; frontend tests report 0 failures.

- [ ] **Step 7: Stop until user confirms app closed, then build**

After explicit confirmation Project Tracker is closed, run:

```powershell
npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run build
```

Expected: exit code 0. Existing Rollup and chunk-size warnings are allowed. Do not launch app automatically.

### Task 2: Manual Gate and Commit

**Files:**
- Verify: `frontend/src/lib/components/NotesEditor.svelte`
- Verify: `frontend/tests/project-details-fase3-fase4.test.mjs`

**Interfaces:**
- Consumes: rebuilt `web/static` and existing DOCX/Markdown/text editor modes.
- Produces: user-verified Step 5b commit; no Step 5c work.

- [ ] **Step 1: Give exact manual checklist**

Ask user to launch from repo root:

```powershell
D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m main
```

Checklist:

1. Open editable DOCX; confirm page is centered and fixed width.
2. Narrow window below page width; confirm horizontal scrollbar appears and page does not shrink.
3. Test medium and maximized windows; confirm page remains centered.
4. Confirm `100%` table fills editor printable width and matches exported Word width.
5. Open `notes.md` and `.txt`; confirm editor fills available width without forced page or horizontal scrollbar.
6. Toggle fullscreen; confirm fixed DOCX page remains centered and vertical height behavior stays normal.
7. Type, save, wait through DOCX countdown/export, switch files, and use titlebar menus; confirm no slowdown or lock.

- [ ] **Step 2: Wait for user verdict**

Expected pass: user confirms DOCX page geometry and unchanged non-DOCX/runtime behavior.

If abnormality appears, do not commit. Restore only uncommitted Step 5b changes, rebuild baseline after app closes, record symptom in `_docs/session-notes.md`, and stop.

- [ ] **Step 3: Commit only Step 5b files after pass**

Run:

```powershell
git add -- frontend/src/lib/components/NotesEditor.svelte frontend/tests/project-details-fase3-fase4.test.mjs
git diff --cached --check
git commit -m "feat(rte): add DOCX printable page width"
```

Expected: one commit containing only two Step 5b files. Leave unrelated dirty files untouched. Stop before Step 5c.

## Self-Review

- Spec coverage: mode class, fixed `720px` border-box width, centered wide layout, narrow horizontal scroll, fullscreen continuity, non-DOCX `width:100%`, required checks, manual gate, and commit boundary covered.
- Placeholder scan: clear; all code-changing steps contain exact code.
- Name consistency: `docxPipelineMode`, `ne-docx-page`, `ne-editor-host`, and `ne-textarea` match source and test snippets.
- Scope: one production file and one existing test file; Step 5c excluded.
