# Project Details Fase 2 — Icon & Spacing Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Overhaul the visual styling of the Project Details screen: replace raw ASCII icons with inline SVGs, modify box layout structure to remove left-border red accents, increase gap and padding sizes to Notion spacing defaults, and adjust contrast variables.

**Architecture:** Frontend style edits in `ProjectDetails.svelte` plus SVG icon placements. Update regex assertions in `project-details-fase1.test.mjs` to target SVG tag patterns instead of raw ASCII glyphs.

**Tech Stack:** Svelte 5, CSS, SVG inline.

**Reference doc:** `docs/superpowers/specs/2026-06-22-project-details-fase2-design.md`

---

## File Structure

**Modified:**

- `frontend/src/lib/components/ProjectDetails.svelte` — update spacing styles, replace left-border accents, replace ASCII icons with inline SVGs.
- `frontend/tests/project-details-fase1.test.mjs` — update assertions checking for SVGs instead of ASCII.

---

## Task 1: Update assertions for the new SVGs (TDD Red beacons)

We will modify `project-details-fase1.test.mjs` to verify that SVGs are rendered instead of raw ASCII glyphs. Running the tests will fail on these assertions first.

**Files:**

- Modify: `frontend/tests/project-details-fase1.test.mjs`
- Test: `npm test`

- [ ] **Step 1: Edit assertions in `project-details-fase1.test.mjs`**

Find the block:

```js
test("CR Link input mode is shown when cr_link is empty (crLinkEditing gate)", () => {
  assert.match(PD, /crLinkEditing/);
  // Two-state render: one branch for editing (input), one for display (CR number + actions).
  assert.match(PD, /<input[^>]*placeholder="Paste CR link…"/);
});

test("CR Link display mode has copy + open-external + edit controls", () => {
  // Copy uses navigator.clipboard.writeText
  assert.match(PD, /navigator\.clipboard\.writeText\([^)]*cr_link/);
  // Open external uses window.open with noopener/noreferrer
  assert.match(
    PD,
    /window\.open\([^)]+,\s*"_blank",\s*"noopener,noreferrer"\)/,
  );
  // Edit control toggles back to input mode
  assert.match(PD, /crLinkEditing\s*=\s*true/);
});
```

Replace it with assertions checking for SVG nodes with specific title attributes or copy click bindings:

```js
test("CR Link input mode is shown when cr_link is empty (crLinkEditing gate)", () => {
  assert.match(PD, /crLinkEditing/);
  // Two-state render: one branch for editing (input), one for display (CR number + actions).
  assert.match(PD, /<input[^>]*placeholder="Paste CR link…"/);
});

test("CR Link display mode has copy + open-external + edit controls", () => {
  // Copy uses navigator.clipboard.writeText
  assert.match(PD, /navigator\.clipboard\.writeText\([^)]*cr_link/);
  // Open external uses window.open with noopener/noreferrer
  assert.match(
    PD,
    /window\.open\([^)]+,\s*"_blank",\s*"noopener,noreferrer"\)/,
  );
  // Edit control toggles back to input mode
  assert.match(PD, /crLinkEditing\s*=\s*true/);
  // Displays copy, open, and edit icons (as SVG nodes now)
  assert.match(PD, /<svg[^>]*Copy CR link/);
  assert.match(PD, /<svg[^>]*Open CR link in browser/);
  assert.match(PD, /<svg[^>]*Edit CR link/);
});
```

Also find the Command Center header assertion:

```js
test("ProjectDetails exposes onNavigateDashboard prop and a back button", () => {
  assert.match(PD, /onNavigateDashboard/);
  assert.match(PD, /Back to Dashboard/);
});
```

Replace with (requires back button arrow to be an inline SVG instead of `←`):

```js
test("ProjectDetails exposes onNavigateDashboard prop and a back button", () => {
  assert.match(PD, /onNavigateDashboard/);
  assert.match(PD, /Back to Dashboard/);
  assert.match(PD, /<svg[^>]*back-arrow/);
});
```

- [ ] **Step 2: Run tests from `frontend` folder**

```bash
npm test
```

Expected: tests fail on the new SVG regex checks (since `ProjectDetails.svelte` still uses unicode `📋`, `↗`, `✎`, and `←`).

- [ ] **Step 3: Commit**

```bash
git add frontend/tests/project-details-fase1.test.mjs
git commit -m "test(fase2): update assertions for inline SVGs on CR Link & Back button"
```

---

## Task 2: Notion Card Styles Overhaul (Left border removal, spacing, typography)

**Files:**

- Modify: `frontend/src/lib/components/ProjectDetails.svelte`
- Test: `npm run check`

- [ ] **Step 1: Replace Left-border accent in `.pd-section`**

Find the CSS selector `.pd-section` in `ProjectDetails.svelte`:

```css
.pd-section {
  background: var(--color-workspace-panel);
  border: 1px solid var(--color-border);
  border-left: 3px solid var(--color-dbs-red);
  border-radius: 10px;
  box-shadow: var(--shadow-card);
  padding: 14px;
}
```

Replace with clean 1px borders, rounded 8px corners, thin shadow, and gray ink variables:

```css
.pd-section {
  background: var(--color-workspace-panel);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  padding: 18px;
}
```

- [ ] **Step 2: Increase Layout gaps (`.split`, `.pane`)**

Find:

```css
.split {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 12px;
  align-items: start;
}
.pane {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}
```

Replace with expanded gaps:

```css
.split {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}
.pane {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
}
```

- [ ] **Step 3: Soften Typography Contrast**

Find:

```css
.pd-dl-item dt {
  font-size: 9.5px;
  font-weight: 600;
  color: var(--color-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.pd-dl-item dd {
  margin: 0;
  font-size: 12.5px;
  font-weight: 500;
  color: var(--color-ink-strong);
}
.pd-meta-label {
  font-size: 9.5px;
  font-weight: 600;
  color: var(--color-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
```

Replace with soft color variables (#6B7280 for labels, #1F2937 for active values):

```css
.pd-dl-item dt {
  font-size: 9.5px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.pd-dl-item dd {
  margin: 0;
  font-size: 12.5px;
  font-weight: 500;
  color: #1f2937;
}
.pd-meta-label {
  font-size: 9.5px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
```

- [ ] **Step 4: Verify type check**

```bash
npm run check
```

Expected: 0 errors, 0 warnings.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/components/ProjectDetails.svelte
git commit -m "style(fase2): overhaul card styles to Notion-like minimalist layout

Removes high-contrast left-border accents in favor of clean 1px light-gray
borders. Expands gaps to 16px/14px, card padding to 18px, and softens label
typography contrast to gray-500."
```

---

## Task 3: Replace ASCII/Unicode Glyphs with Inline SVGs

We will replace the unicode icons in the HTML with standard, thin-stroke inline SVGs.

**Files:**

- Modify: `frontend/src/lib/components/ProjectDetails.svelte`
- Test: `npm test`

- [ ] **Step 1: Replace `▣` in Command Center Title**

Find:

```svelte
      <div class="panel-title-row" style="margin:0 18px 0 0;"><span class="panel-title-icon">▣</span><span class="panel-title">Project Command Center</span><span class="panel-subtitle">compact editing workspace</span></div>
```

Replace with inline grid SVG:

```svelte
      <div class="panel-title-row" style="margin:0 18px 0 0;">
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="pd-icon"><rect x="3" y="3" width="7" height="9"></rect><rect x="14" y="3" width="7" height="5"></rect><rect x="14" y="12" width="7" height="9"></rect><rect x="3" y="16" width="7" height="5"></rect></svg>
        <span class="panel-title">Project Command Center</span>
        <span class="panel-subtitle">compact editing workspace</span>
      </div>
```

- [ ] **Step 2: Replace `←` in Back to Dashboard button**

Find:

```svelte
        <span class="pd-back-arrow" aria-hidden="true">←</span>
```

Replace with inline arrow-left SVG:

```svelte
        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="pd-icon-back"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>
```

Update CSS in style block for `.pd-icon-back`:

```css
.pd-icon-back {
  stroke: var(--color-ink);
  margin-right: 4px;
}
.pd-back-btn:hover .pd-icon-back {
  stroke: var(--color-dbs-red);
}
```

- [ ] **Step 3: Replace `📋`, `↗`, and `✎` in CR Link display row**

Find:

```svelte
                    <button class="pd-icon-btn" type="button" title="Copy CR link" onclick={copyCrLink} aria-label="Copy CR link">📋{#if crLinkCopied} ✓{/if}</button>
                    <button class="pd-icon-btn" type="button" title="Open CR link in browser" onclick={openCrLink} aria-label="Open CR link in browser">↗</button>
                    <button class="pd-icon-btn" type="button" title="Edit CR link" onclick={editCrLink} aria-label="Edit CR link">✎</button>
```

Replace buttons content with title-equipped inline SVGs (retaining Svelte callbacks/conditions):

```svelte
                    <button class="pd-icon-btn" type="button" onclick={copyCrLink} aria-label="Copy CR link">
                      <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" class="pd-icon"><title>Copy CR link</title><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path><rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect></svg>
                      {#if crLinkCopied}<span style="font-size:9.5px;color:var(--tag-green-ink);margin-left:2px;">✓</span>{/if}
                    </button>
                    <button class="pd-icon-btn" type="button" onclick={openCrLink} aria-label="Open CR link in browser">
                      <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" class="pd-icon"><title>Open CR link in browser</title><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
                    </button>
                    <button class="pd-icon-btn" type="button" onclick={editCrLink} aria-label="Edit CR link">
                      <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" class="pd-icon"><title>Edit CR link</title><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 1 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>
                    </button>
```

- [ ] **Step 4: Replace warning/spinner indicators in other feedbacks**

Find detail loading banner (warning icon):

```svelte
      {:else if detailState === "error"}
        <div class="dashboard-banner banner-error"><span class="banner-icon">⚠</span><div><p class="banner-title">Detail load failed</p><p class="banner-detail">{errorCode}: {errorMessage}</p></div></div>
```

Replace `<span class="banner-icon">⚠</span>` with inline warning triangle SVG:

```svelte
        <span class="banner-icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="pd-icon"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
        </span>
```

Do the same for `listState === "error"` loading banner.

Find CR State saving state spinner (around lines 672–678):

```svelte
                {#if crStateSaveState === "saving"}
                  <span class="cr-link-feedback">⏳ Saving…</span>
```

Replace with inline spinner SVG:

```svelte
                {#if crStateSaveState === "saving"}
                  <span class="cr-link-feedback">
                    <svg class="pd-spinner" xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="2" x2="12" y2="6"></line><line x1="12" y1="18" x2="12" y2="22"></line><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line><line x1="2" y1="12" x2="6" y2="12"></line><line x1="18" y1="12" x2="22" y2="12"></line><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line></svg>
                    Saving…
                  </span>
```

Add CSS for the spinner rotation in `<style>`:

```css
.pd-spinner {
  animation: spin 1s linear infinite;
  display: inline-block;
  vertical-align: middle;
  margin-right: 4px;
}
@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
```

- [ ] **Step 5: Run tests — check if Fase 2 assertions turn GREEN**

```bash
npm test
```

Expected: `project-details-fase1.test.mjs` is now 100% GREEN (all SVG assertions match). Parity check has only the pre-existing error.

- [ ] **Step 6: Run type check**

```bash
npm run check
```

Expected: 0 errors, 0 warnings.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/lib/components/ProjectDetails.svelte
git commit -m "feat(fase2): replace ASCII/Unicode glyphs with inline SVGs

Replaces legacy glyphs (copy, external link, pencil, warning triangle,
hourglass spinner) with thin-stroke, clean inline SVGs. Spinner gains smooth
infinite CSS rotation animation."
```

---

## Task 4: Final verification

Verify everything remains completely green.

**Files:** none (verification only)

- [ ] **Step 1: Run full test suite**

```bash
npm test
```

Expected: 1 fail / 136 pass (only pre-existing parity failure).

- [ ] **Step 2: Run type check**

```bash
npm run check
```

Expected: 0 errors, 0 warnings.

- [ ] **Step 3: Run production build**

```bash
npm run build
```

Expected: build succeeds.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-22-project-details-fase2-cleanup.md`. Two execution options:

1. **Subagent-Driven** - fresh subagent per task, review between tasks (Not available - platform disabled subagents)
2. **Inline Execution** (recommended) - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?** (Answer with "2" to proceed in this session)
