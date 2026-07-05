# Editor Zoom Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add DOCX gray workspace and Word-like 100–500% zoom for all supported editor formats in separate verified rounds.

**Architecture:** Keep behavior inside `NotesEditor.svelte`: existing host owns overflow, zoom custom property, controls, and input handlers. Existing source-contract test file guards exact behavior. No new modules, dependencies, persistence, or content transformations.

**Tech Stack:** Svelte 5, TypeScript, Tiptap v3, CSS `zoom`, Node test runner.

## Global Constraints

- Work only on branch `project-details/tiptap-docx-pipeline` from repo root.
- Modify only `frontend/src/lib/components/NotesEditor.svelte` and `frontend/tests/project-details-fase3-fase4.test.mjs`.
- Execute Task 1 and Task 2 as separate rounds with user manual verification and commit between them.
- Never run frontend build while Project Tracker may be open.
- Preserve fixed DOCX `720px` page and non-DOCX base `width:100%`.
- Add no backend, Markdown, extension, dependency, storage, or export changes.

---

### Task 1: DOCX Gray Workspace

**Files:**
- Modify: `frontend/tests/project-details-fase3-fase4.test.mjs`
- Modify: `frontend/src/lib/components/NotesEditor.svelte`

**Interfaces:**
- Consumes: existing `.ne-editor-host.ne-docx-page` selector and design token `--main-panel-bg`.
- Produces: gray DOCX-only workspace around unchanged white `720px` page.

- [ ] Add failing source-contract test:

```javascript
test("NotesEditor gives DOCX page a neutral workspace", () => {
  assert.match(
    NE,
    /\.ne-editor-host\.ne-docx-page\s*\{[^}]*overflow-x:auto;[^}]*box-sizing:border-box;[^}]*padding:12px;[^}]*background:var\(--main-panel-bg\);[^}]*border-radius:6px;/,
  );
  assert.match(
    NE,
    /:global\(\.ne-editor-host\.ne-docx-page \.ne-textarea\)\s*\{[^}]*width:720px;[^}]*background:var\(--color-workspace-panel\);/,
  );
});
```

- [ ] Run focused red test:

```powershell
node --import ./frontend/tests/register-hooks.mjs --test --test-name-pattern "neutral workspace" ./frontend/tests/project-details-fase3-fase4.test.mjs
```

Expected: fail because workspace declarations are absent.

- [ ] Replace DOCX workspace rules with:

```css
.ne-editor-host.ne-docx-page { overflow-x:auto; box-sizing:border-box; padding:12px; background:var(--main-panel-bg); border-radius:6px; }
:global(.ne-editor-host.ne-docx-page .ne-textarea) { width:720px; max-width:none; margin:0 auto; box-sizing:border-box; background:var(--color-workspace-panel); }
```

- [ ] Run focused green test, svelte-check, and full frontend tests.
- [ ] After app-closed confirmation, build.
- [ ] User verifies gray workspace at three widths plus DOCX/Markdown/text regression.
- [ ] After pass, commit only two target files:

```powershell
git add -- frontend/src/lib/components/NotesEditor.svelte frontend/tests/project-details-fase3-fase4.test.mjs
git diff --cached --check
git commit -m "feat(rte): add DOCX page workspace"
```

### Task 2: Cross-Format Editor Zoom

**Files:**
- Modify: `frontend/tests/project-details-fase3-fase4.test.mjs`
- Modify: `frontend/src/lib/components/NotesEditor.svelte`

**Interfaces:**
- Consumes: existing editor host, `onKeydown`, derived `capability`, and toolbar action cluster.
- Produces: session-only `zoomPercent`, controls, editor-scoped wheel/keyboard shortcuts, and inherited `--ne-zoom` CSS value.

- [ ] Add failing source-contract test covering:

```javascript
test("NotesEditor supports Word-like cross-format zoom", () => {
  assert.match(NE, /const ZOOM_MIN = 100/);
  assert.match(NE, /const ZOOM_MAX = 500/);
  assert.match(NE, /const ZOOM_STEP = 25/);
  assert.match(NE, /let zoomPercent = \$state\(100\)/);
  assert.match(NE, /function setZoom\([^)]*\)[\s\S]*Math\.min\(ZOOM_MAX, Math\.max\(ZOOM_MIN/);
  assert.match(NE, /function onZoomWheel\(e: WheelEvent\)[\s\S]*e\.ctrlKey[\s\S]*e\.preventDefault\(\)/);
  assert.match(NE, /e\.key === "\+" \|\| e\.key === "="/);
  assert.match(NE, /e\.key === "-"/);
  assert.match(NE, /aria-label="Zoom out"/);
  assert.match(NE, /aria-label="Reset zoom to 100%"/);
  assert.match(NE, /aria-label="Zoom in"/);
  assert.match(NE, /capability !== "unsupported"/);
  assert.match(NE, /--ne-zoom/);
  assert.match(NE, /zoom:var\(--ne-zoom, 1\)/);
});
```

- [ ] Run focused red test.
- [ ] Add constants and state:

```typescript
const ZOOM_MIN = 100;
const ZOOM_MAX = 500;
const ZOOM_STEP = 25;
let zoomPercent = $state(100);
```

- [ ] Add minimal helpers:

```typescript
function setZoom(next: number) {
  zoomPercent = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, next));
}
function zoomIn() { setZoom(zoomPercent + ZOOM_STEP); }
function zoomOut() { setZoom(zoomPercent - ZOOM_STEP); }
function onZoomWheel(e: WheelEvent) {
  if (!e.ctrlKey) return;
  e.preventDefault();
  if (e.deltaY < 0) zoomIn();
  else if (e.deltaY > 0) zoomOut();
}
```

- [ ] Extend `onKeydown` after existing Ctrl+S branch. Require `hostEl?.contains(e.target as Node)` before zoom handling. Prevent default and call `zoomIn()` for `+`/`=`, `zoomOut()` for `-`.

- [ ] Add host binding:

```svelte
<div class="ne-editor-host" class:ne-docx-page={docxPipelineMode} style={`--ne-zoom:${zoomPercent / 100}`} onwheel={onZoomWheel} bind:this={hostEl}></div>
```

- [ ] Add controls before help button when `capability !== "unsupported"`: minus, percentage reset, plus; disable minus at `100` and plus at `500`.
- [ ] Add compact control CSS and apply `zoom:var(--ne-zoom, 1)` to base `.ne-textarea`.
- [ ] Run focused green test, svelte-check, and full frontend tests.
- [ ] After app-closed confirmation, build.
- [ ] User verifies controls, wheel, keyboard, 100/125/250/500%, all formats, fullscreen, and regressions.
- [ ] After pass, commit only two target files:

```powershell
git add -- frontend/src/lib/components/NotesEditor.svelte frontend/tests/project-details-fase3-fase4.test.mjs
git diff --cached --check
git commit -m "feat(rte): add cross-format editor zoom"
```

## Self-Review

- Two behavior rounds have separate tests, builds, manual gates, and commits.
- Zoom is bounded `100..500`, step `25`, session-only, and unsupported MSG excluded.
- Zoom changes rendering only; persistence/export paths remain untouched.
- No placeholders, new files, dependencies, or speculative persistence.
