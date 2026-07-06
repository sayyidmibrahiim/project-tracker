# Step 1 Toolbar Active-State Retry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore live RTE toolbar active states without slowing save, document switching, typing, or menu navigation.

**Architecture:** Keep existing `rev` counter non-reactive because synchronous `rev++` runs inside the editor-mount `$effect`. Add one toolbar-only Svelte state token updated from a `requestAnimationFrame`-throttled Tiptap transaction listener registered through `queueMicrotask`, after effect dependency tracking ends. Do not change save, load, DOCX, or interaction-lock code.

**Tech Stack:** Svelte 5 runes, TypeScript, Tiptap v3, Node test runner.

## Global Constraints

- Work only on branch `project-details/tiptap-docx-pipeline`; do not touch `main`.
- One behavior only: toolbar active-state refresh.
- Modify only `frontend/src/lib/components/NotesEditor.svelte` and `frontend/tests/project-details-fase3-fase4.test.mjs`.
- Keep `let rev = 0`; never make `rev` reactive.
- No new files beyond this requested plan, abstractions, dependencies, or Python changes.
- Never run `npm run build` while Project Tracker is open.
- Automated green is insufficient; do not commit until user manual verification passes.
- If any menu, save, typing, load, or file-switch regression appears: roll back this uncommitted retry and rebuild baseline immediately.

---

### Task 1: Throttled toolbar-only refresh

**Files:**
- Modify: `frontend/src/lib/components/NotesEditor.svelte:100,483-493,776-801`
- Test: `frontend/tests/project-details-fase3-fase4.test.mjs:39`

**Interfaces:**
- Consumes: Tiptap `transaction` events and browser `queueMicrotask` / `requestAnimationFrame`.
- Produces: `scheduleToolbarRefresh(): void`; `uiTick` dependency consumed only by `isActive()` and `alignIs()`.

- [ ] **Step 1: Write the failing source-contract test**

Add after the existing NotesEditor dispose test:

```js
test("NotesEditor throttles toolbar refresh outside editor-mount effect", () => {
  assert.match(NE, /let rev = 0/);
  assert.doesNotMatch(NE, /let rev = \$state/);
  assert.match(NE, /let uiTick = \$state\(0\)/);
  assert.match(NE, /function scheduleToolbarRefresh\(\)[\s\S]*requestAnimationFrame[\s\S]*uiTick\+\+/);
  assert.match(NE, /queueMicrotask\([\s\S]*instance\.on\("transaction", scheduleToolbarRefresh\)/);
  assert.match(NE, /function isActive\([^)]*\)[^{]*\{\s*void uiTick;/);
  assert.match(NE, /function alignIs\([^)]*\)[^{]*\{\s*void uiTick;/);
  assert.match(NE, /instance\.off\("transaction", scheduleToolbarRefresh\)/);
});
```

- [ ] **Step 2: Run the focused test and confirm RED**

Run from `D:/Ibrahim/Projects/project_tracker/frontend`:

```powershell
node --import ./tests/register-hooks.mjs --test tests/project-details-fase3-fase4.test.mjs
```

Expected: one failure because `uiTick` and `scheduleToolbarRefresh` do not exist.

- [ ] **Step 3: Add one throttled toolbar state token**

Keep `rev` plain and add directly below it:

```ts
  // Non-reactive: Tiptap transaction events fire during mount; Svelte state here can loop.
  let rev = 0;
  let uiTick = $state(0);
  let toolbarRefreshFrame: number | undefined;

  function scheduleToolbarRefresh() {
    if (toolbarRefreshFrame !== undefined) return;
    toolbarRefreshFrame = requestAnimationFrame(() => {
      toolbarRefreshFrame = undefined;
      uiTick++;
    });
  }
```

Do not replace or remove existing plain `rev++` calls; changing all toolbar commands would enlarge blast radius without benefit.

- [ ] **Step 4: Subscribe only toolbar helper calls**

Change helpers to:

```ts
  function isActive(name: string, attrs?: Record<string, unknown>): boolean {
    void uiTick;
    return editor?.isActive(name, attrs) ?? false;
  }

  function alignIs(value: string): boolean {
    void uiTick;
    if (!editor) return false;
    const cur = (editor.getAttributes("paragraph").textAlign as string) || (editor.getAttributes("heading").textAlign as string) || "";
    return cur === value;
  }
```

Do not read `uiTick` in any `$effect`.

- [ ] **Step 5: Register refresh after effect tracking ends**

Replace synchronous transaction/selection listeners:

```ts
    queueMicrotask(() => {
      if (editor !== instance) return;
      instance.on("transaction", scheduleToolbarRefresh);
      scheduleToolbarRefresh();
    });
    instance.on("update", onEditorUpdate);
    editor = instance;
```

In the effect cleanup, before `instance.destroy()`, add:

```ts
      instance.off("transaction", scheduleToolbarRefresh);
      if (toolbarRefreshFrame !== undefined) {
        cancelAnimationFrame(toolbarRefreshFrame);
        toolbarRefreshFrame = undefined;
      }
```

Delete the old `instance.on("selectionUpdate", ...)` listener. Tiptap transaction events already cover selection and content changes; one listener is the smaller path.

- [ ] **Step 6: Run focused test and confirm GREEN**

```powershell
node --import ./tests/register-hooks.mjs --test tests/project-details-fase3-fase4.test.mjs
```

Expected: all tests in the file pass.

- [ ] **Step 7: Run required frontend verification while app remains closed**

```powershell
npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run check
npm --prefix D:/Ibrahim/Projects/project_tracker/frontend test
npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run build
```

Expected: `svelte-check` has 0 errors, frontend tests have 0 failures, build exits 0. No Python test is required because this retry is frontend-only.

- [ ] **Step 8: Stop for manual verification before commit**

Launch from repo root:

```powershell
D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m main
```

User checks, in this order:

1. Open a CR project and switch among `notes.md` and DOCX files repeatedly.
2. Confirm each file loads at baseline speed and save status does not linger.
3. Click bold text; B becomes active immediately. Toggle B on/off and type continuously.
4. Confirm typing latency stays unchanged.
5. Navigate through titlebar menus during and after file switching; navigation remains responsive.

If any regression appears, close app, restore the two Step 1 files to `c94e387`, rebuild baseline, record symptoms, and stop.

- [ ] **Step 9: Commit only after user says Step 1 passed**

```powershell
git add -- frontend/src/lib/components/NotesEditor.svelte frontend/tests/project-details-fase3-fase4.test.mjs _docs/session-notes.md
git commit -m "fix(rte): step 1 — toolbar active states"
```

Do not start Step 2 in the same round.

## Self-Review

- Spec coverage: active states, no effect self-subscription, throttling, cleanup, required checks, manual gate, rollback path covered.
- Placeholder scan: clear; every code and verification step is explicit.
- Type consistency: `uiTick`, `toolbarRefreshFrame`, and `scheduleToolbarRefresh()` names match every step.
- Scope: one production file, one existing test file, no save/load/lock changes.
