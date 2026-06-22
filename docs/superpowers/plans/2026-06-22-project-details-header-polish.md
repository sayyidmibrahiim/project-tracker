# Project Details & Header Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix layout/behavior issues in Project Details (restore Sub Project dropdown, move Back button, restructure Identity box, match Dashboard table parity, fix Notes WYSIWYG) and polish Header (calendar icon, button styling).

**Architecture:** Frontend-only edits to `ProjectDetails.svelte`, `SubProjectTable.svelte`, `NotesEditor.svelte`, `Header.svelte`, and `styles.css`. No backend changes.

**Tech Stack:** Svelte 5, CSS, inline SVG.

**Reference doc:** `docs/superpowers/specs/2026-06-22-project-details-header-polish-design.md`

---

## Task 1: Command Center — restore Sub Project dropdown, remove subtitle, move Back button

**Files:**
- Modify: `frontend/src/lib/components/ProjectDetails.svelte`

- [ ] **Step 1: Remove the standalone `.pd-back-bar` block above the panel-card**

Find (around lines 591-599):
```svelte
<section class="screen active" id="screen-details">
  {#if onNavigateDashboard}
    <div class="pd-back-bar">
      <button type="button" class="pd-back-btn" onclick={() => onNavigateDashboard?.()}>
        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="pd-icon-back"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>
        <span>Back to Dashboard</span>
      </button>
    </div>
  {/if}
  <div class="panel-card" style="flex:0 0 auto;">
```

Replace with:
```svelte
<section class="screen active" id="screen-details">
  <div class="panel-card" style="flex:0 0 auto;">
```

- [ ] **Step 2: Remove subtitle text `compact editing workspace`**

Find (around line 605):
```svelte
        <span class="panel-subtitle">compact editing workspace</span>
```

Delete that line.

- [ ] **Step 3: Add Back button + Sub Project dropdown inside toolbar**

Find (around lines 601-618):
```svelte
    <div class="toolbar">
      <div class="panel-title-row" style="margin:0 18px 0 0;">
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="pd-icon"><rect x="3" y="3" width="7" height="9"></rect><rect x="14" y="3" width="7" height="5"></rect><rect x="14" y="12" width="7" height="9"></rect><rect x="3" y="16" width="7" height="5"></rect></svg>
        <span class="panel-title">Project Command Center</span>
      </div>
      <label class="pd-command-field pd-command-project" for="pd-project-select">
        <span>Project</span>
        <select id="pd-project-select" class="pd-control" value={selectedPath} onchange={(e) => selectProject((e.target as HTMLSelectElement).value)} disabled={filtered.length === 0 || mode === "new"}>
          <option value="">Select project…</option>
          {#each filtered as p}
            <option value={p.project_path}>{p.project_name}</option>
          {/each}
        </select>
      </label>
      <div class="pd-command-spacer"></div>
```

Replace with:
```svelte
    <div class="toolbar">
      <div class="panel-title-row" style="margin:0 18px 0 0;">
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="pd-icon"><rect x="3" y="3" width="7" height="9"></rect><rect x="14" y="3" width="7" height="5"></rect><rect x="14" y="12" width="7" height="9"></rect><rect x="3" y="16" width="7" height="5"></rect></svg>
        <span class="panel-title">Project Command Center</span>
      </div>
      {#if onNavigateDashboard}
        <button type="button" class="pd-command-btn" onclick={() => onNavigateDashboard?.()} title="Back to Dashboard">
          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:inline;vertical-align:middle;margin-right:4px;"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>
          Back
        </button>
      {/if}
      <label class="pd-command-field pd-command-project" for="pd-project-select">
        <span>Project</span>
        <select id="pd-project-select" class="pd-control" value={selectedPath} onchange={(e) => selectProject((e.target as HTMLSelectElement).value)} disabled={filtered.length === 0 || mode === "new"}>
          <option value="">Select project…</option>
          {#each filtered as p}
            <option value={p.project_path}>{p.project_name}</option>
          {/each}
        </select>
      </label>
      <label class="pd-command-field pd-command-project" for="pd-subproject-select">
        <span>Sub Project</span>
        <select id="pd-subproject-select" class="pd-control" bind:value={selectedSubproject} disabled={!selectedPath || subprojects.length === 0 || mode === "new"}>
          <option value="all">All Sub Projects</option>
          {#each subprojects as sp}
            <option value={sp}>{sp}</option>
          {/each}
        </select>
      </label>
      <div class="pd-command-spacer"></div>
```

- [ ] **Step 4: Re-declare `selectedSubproject` state variable**

Add after `let isSubproject: boolean = $state(false);` (around line 24):
```svelte
  let selectedSubproject: string = $state("all");
```

- [ ] **Step 5: Run check + tests**

```bash
cd "D:/Ibrahim/Projects/project_tracker/frontend"
npm run check
npm test 2>&1 | grep -E "^(not ok|# pass|# fail)"
```
Expected: 0 errors. Tests may fail on assertions referencing old Back button layout — note which.

- [ ] **Step 6: Commit**

```bash
cd "D:/Ibrahim/Projects/project_tracker"
git add frontend/src/lib/components/ProjectDetails.svelte
git commit -m "fix(polish): restore Sub Project dropdown, move Back button into Command Center, remove subtitle"
```

---

## Task 2: Project Identity — remove CR Number row, rename to CR Number, inline CR State

**Files:**
- Modify: `frontend/src/lib/components/ProjectDetails.svelte`

- [ ] **Step 1: Remove CR Number display row**

Find (around line 660):
```svelte
                <div class="pd-dl-item"><dt>CR Number</dt><dd>{detail.cr_number || "—"}</dd></div>
```

Delete that line.

- [ ] **Step 2: Rename "CR Link" label to "CR Number"**

Find (around line 661):
```svelte
                <label class="pd-meta-label" for="meta-cr-link">CR Link</label>
```

Replace with:
```svelte
                <label class="pd-meta-label" for="meta-cr-link">CR Number</label>
```

- [ ] **Step 3: Restructure CR Number + CR State side-by-side**

Find the block from the CR Number label through the CR State feedback block (around lines 661-716). Replace the entire block with a horizontal grid:

```svelte
                <div class="pd-meta-datetime-row">
                  <div class="pd-meta-field">
                    <span class="pd-meta-label">CR Number</span>
                    {#if crLinkEditing && !isSubproject}
                      <input
                        id="meta-cr-link"
                        class="cr-link-input"
                        type="url"
                        placeholder="Paste CR link…"
                        bind:value={crLinkEdit}
                        onblur={saveCrLinkFromInput}
                        disabled={crLinkSaveState === "saving"}
                      />
                      {#if crLinkSaveState === "error"}
                        <span class="cr-link-feedback cr-link-err">✗ {crLinkSaveError}</span>
                      {/if}
                    {:else}
                      <div class="pd-cr-link-display">
                        <span class="pd-cr-link-number">{detail.cr_number || detail.cr_link || "—"}</span>
                        {#if detail.cr_link}
                          <button class="pd-icon-btn" type="button" onclick={copyCrLink} aria-label="Copy CR link">
                            <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" class="pd-icon"><title>Copy CR link</title><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path><rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect></svg>
                            {#if crLinkCopied}<span style="font-size:9.5px;color:var(--tag-green-ink);margin-left:2px;">✓</span>{/if}
                          </button>
                          <button class="pd-icon-btn" type="button" onclick={openCrLink} aria-label="Open CR link in browser">
                            <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" class="pd-icon"><title>Open CR link in browser</title><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
                          </button>
                        {/if}
                        {#if !isSubproject}
                          <button class="pd-icon-btn" type="button" onclick={editCrLink} aria-label="Edit CR link">
                            <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" class="pd-icon"><title>Edit CR link</title><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 1 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>
                          </button>
                        {/if}
                      </div>
                    {/if}
                    {#if isSubproject}
                      <span class="pd-inherited-label">(Inherited from Main Project)</span>
                    {/if}
                  </div>
                  <label class="pd-meta-field" for="meta-cr-state">
                    <span class="pd-meta-label">CR State</span>
                    <select id="meta-cr-state" class="cr-state-select" value={crStateEdit} onchange={(e) => onCrStateChange((e.currentTarget as HTMLSelectElement).value)} disabled={crStateSaveState === "saving" || isSubproject}>
                      {#each legalCrOptionsFor(detail.cr_state) as opt}
                        <option value={opt} disabled={opt === "IN-PROGRESS"}>{opt}</option>
                      {/each}
                    </select>
                    {#if crStateSaveState === "saving"}
                      <span class="cr-link-feedback">
                        <svg class="pd-spinner" xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="2" x2="12" y2="6"></line><line x1="12" y1="18" x2="12" y2="22"></line><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line><line x1="2" y1="12" x2="6" y2="12"></line><line x1="18" y1="12" x2="22" y2="12"></line><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line></svg>
                        Saving…
                      </span>
                    {:else if crStateSaveState === "success"}
                      <span class="cr-link-feedback cr-link-ok">✓ Saved</span>
                    {:else if crStateSaveState === "error"}
                      <span class="cr-link-feedback cr-link-err">✗ {crStateSaveError}</span>
                    {/if}
                  </label>
                </div>
```

- [ ] **Step 4: Run check + tests, commit**

```bash
cd "D:/Ibrahim/Projects/project_tracker/frontend"
npm run check
npm test 2>&1 | grep -E "^(not ok|# pass|# fail)"
cd ..
git add frontend/src/lib/components/ProjectDetails.svelte
git commit -m "fix(polish): restructure Identity — CR Number + CR State inline, remove redundant CR Number row"
```

---

## Task 3: Sub Project Table — Dashboard parity columns, row-click opens folder

**Files:**
- Modify: `frontend/src/lib/components/SubProjectTable.svelte`

- [ ] **Step 1: Update table columns and row-click behavior**

Replace the entire `<div class="sp-table">` block in `SubProjectTable.svelte` with:

```svelte
    <div class="sp-table" role="table" aria-label="Sub projects">
      <div class="sp-tr sp-th" role="row">
        <span>Sub Project</span><span>Drone Ticket</span><span>Drone State</span>
      </div>
      {#each rows as row (row.name)}
        <div class="sp-tr" role="row" class:sp-selected={selectedRow === row.name} onclick={() => onOpenFolder(row.name)} style="cursor:pointer;">
          <span class="sp-name" title={row.name}>{row.name}</span>
          <span class="sp-link" title={row.droneLink}>{row.droneLink || "—"}</span>
          <span class="sp-state">
            {#if row.droneState}
              <select
                class="sp-state-select"
                value={row.droneState}
                onchange={(e) => onChangeDroneState(row.name, (e.currentTarget as HTMLSelectElement).value)}
                disabled={droneStateBusyName === row.name}
                aria-label={`Drone state for ${row.name}`}
              >
                {#each legalDroneOptionsFor(row.droneState) as opt}
                  <option value={opt} disabled={opt === "IN-PROGRESS"}>{opt}</option>
                {/each}
              </select>
            {:else}
              <span class="sp-muted">—</span>
            {/if}
            {#if droneStateErrorName[row.name]}
              <span class="sp-err" role="alert">✗ {droneStateErrorName[row.name]}</span>
            {/if}
          </span>
        </div>
      {/each}
    </div>
```

- [ ] **Step 2: Add `droneLink` back to Row interface**

In the `<script>` section of `SubProjectTable.svelte`, update the `Row` interface:
```ts
  interface Row {
    name: string;
    droneLink: string;
    droneState: string;
  }

  const rows = $derived<Row[]>(
    subprojects.map((name) => {
      const drone = droneTickets.find((t) => (t.subfolder_name ?? "") === name);
      return { name, droneLink: drone?.drone_link ?? "", droneState: drone?.drone_state ?? "" };
    }),
  );
```

- [ ] **Step 3: Update grid template to 3 columns**

In `<style>`, change:
```css
  .sp-tr { display: grid; grid-template-columns: 1fr 1.1fr auto; gap: 8px; align-items: center; padding: 7px 8px; border-top: 1px solid #E5E7EB; font-size: 10px; font-weight: 750; color: var(--color-ink); }
```
to:
```css
  .sp-tr { display: grid; grid-template-columns: 1fr 1.4fr 0.8fr; gap: 8px; align-items: center; padding: 7px 8px; border-top: 1px solid #E5E7EB; font-size: 10px; font-weight: 750; color: var(--color-ink); }
```

Also add:
```css
  .sp-link { font-family: monospace; color: var(--color-dbs-red); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
```

- [ ] **Step 4: Run check + tests, commit**

```bash
cd "D:/Ibrahim/Projects/project_tracker/frontend"
npm run check
npm test 2>&1 | grep -E "^(not ok|# pass|# fail)"
cd ..
git add frontend/src/lib/components/SubProjectTable.svelte
git commit -m "fix(polish): Sub Project table matches Dashboard parity — 3 columns, row-click opens folder"
```

---

## Task 4: Notes — debounced markdown sync + checklist bug fix

**Files:**
- Modify: `frontend/src/lib/components/NotesEditor.svelte`

- [ ] **Step 1: Remove `syncToMarkdown()` from `onEditorInput`**

Find (around lines 141-143):
```ts
  function onEditorInput() {
    syncToMarkdown();
  }
```

Replace with:
```ts
  function onEditorInput() {
    scheduleSave();
  }
```

- [ ] **Step 2: Update `scheduleSave` to convert HTML→Markdown on timer fire**

Find (around lines 46-50):
```ts
  function scheduleSave() {
    status = "pending";
    if (timer) clearTimeout(timer);
    timer = setTimeout(flush, AUTOSAVE_MS);
  }
```

Replace with:
```ts
  function scheduleSave() {
    status = "pending";
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => {
      if (editorEl) text = htmlToMarkdown(editorEl.innerHTML);
      flush();
    }, AUTOSAVE_MS);
  }
```

- [ ] **Step 3: Update `onEditorBlur` to convert before flush**

Find (around lines 145-147):
```ts
  function onEditorBlur() {
    if (status === "pending") flush();
  }
```

Replace with:
```ts
  function onEditorBlur() {
    if (editorEl) text = htmlToMarkdown(editorEl.innerHTML);
    if (status === "pending" || timer) {
      if (timer) { clearTimeout(timer); timer = undefined; }
      flush();
    }
  }
```

- [ ] **Step 4: Fix checklist insertion — ensure cursor is inside editor**

Find `formatChecklist` (around lines 192-203):
```ts
  function formatChecklist() {
    const html = `<div class="ne-todo-item"><input type="checkbox" class="ne-todo-checkbox" /> <span>Todo item</span></div>`;
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0) return;
    const range = sel.getRangeAt(0);
    const fragment = range.createContextualFragment(html);
    range.insertNode(fragment);
    
    // Bind change listener on newly created checkbox
    setTimeout(bindCheckboxListeners, 50);
    syncToMarkdown();
  }
```

Replace with:
```ts
  function formatChecklist() {
    if (!editorEl) return;
    editorEl.focus();
    const html = `<div class="ne-todo-item"><input type="checkbox" class="ne-todo-checkbox" /> <span>Todo item</span></div>`;
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0) {
      editorEl.insertAdjacentHTML("beforeend", html);
    } else {
      const range = sel.getRangeAt(0);
      if (!editorEl.contains(range.commonAncestorContainer)) {
        editorEl.insertAdjacentHTML("beforeend", html);
      } else {
        const fragment = range.createContextualFragment(html);
        range.insertNode(fragment);
      }
    }
    editorEl.focus();
    setTimeout(bindCheckboxListeners, 50);
    scheduleSave();
  }
```

- [ ] **Step 5: Run check + tests, commit**

```bash
cd "D:/Ibrahim/Projects/project_tracker/frontend"
npm run check
npm test 2>&1 | grep -E "^(not ok|# pass|# fail)"
cd ..
git add frontend/src/lib/components/NotesEditor.svelte
git commit -m "fix(polish): debounced markdown sync prevents cursor jump; checklist insertion stays inside editor"
```

---

## Task 5: Header — calendar icon + button polish

**Files:**
- Modify: `frontend/src/lib/components/Header.svelte`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Replace clock glyph with calendar SVG in Header.svelte**

Find (around lines 121-130):
```svelte
    <div class="date-time-badge" aria-label={`Current date and time: ${nowText.date} ${nowText.time}`}>
      <span class="datetime-glyph" aria-hidden="true">
        <span class="datetime-glyph-top"></span>
        <span class="datetime-glyph-hand"></span>
      </span>
      <span class="datetime-copy">
        <span class="datetime-date">{nowText.date}</span>
        <span class="datetime-time">{nowText.time}</span>
      </span>
    </div>
```

Replace with:
```svelte
    <div class="date-time-badge" aria-label={`Current date and time: ${nowText.date} ${nowText.time}`}>
      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="datetime-icon"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>
      <span class="datetime-copy">
        <span class="datetime-date">{nowText.date}</span>
        <span class="datetime-time">{nowText.time}</span>
      </span>
    </div>
```

- [ ] **Step 2: Replace search icon glyph with SVG**

Find (around line 158):
```svelte
        <span class="search-icon">⌕</span>
```

Replace with:
```svelte
        <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="search-icon"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
```

- [ ] **Step 3: Replace refresh button glyph with SVG**

Find (around line 163):
```svelte
    <button class="refresh-button" title="Refresh Data" onclick={triggerRefresh}><span class:spinning>↻</span></button>
```

Replace with:
```svelte
    <button class="refresh-button" title="Refresh Data" onclick={triggerRefresh}><svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class:spinning><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg></button>
```

- [ ] **Step 4: Replace Add Project button text with SVG + text**

Find (around line 161):
```svelte
      <button class="btn-black" class:hidden={!cfg.add} onclick={() => onAddProject()}>＋ Add Project</button>
```

Replace with:
```svelte
      <button class="btn-black" class:hidden={!cfg.add} onclick={() => onAddProject()}>
        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="display:inline;vertical-align:middle;margin-right:4px;"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
        Add Project
      </button>
```

- [ ] **Step 5: Polish CSS for header buttons in styles.css**

Find `.btn-black` rule (around line 344 in styles.css):
```css
.btn-black { background: var(--black-chrome); color: #fff; border-color: var(--black-chrome); padding: 0 16px; box-shadow: var(--shadow-button); }
```

Replace with:
```css
.btn-black { background: #fff; color: var(--text-strong); border: 1px solid var(--soft-white-border); padding: 0 14px; box-shadow: none; transition: border-color .15s ease, color .15s ease; }
.btn-black:hover { border-color: var(--primary-red); color: var(--primary-red); }
```

Find `.refresh-button` rule (around line 352):
```css
.refresh-button, .btn-refresh { width: 28px; min-width: 28px; height: 26px; background: #fff; color: var(--primary-red); border-color: var(--black-chrome); box-shadow: 0 2px 9px rgba(0,0,0,.30); font-size: 15px; padding: 0; }
```

Replace with:
```css
.refresh-button, .btn-refresh { width: 30px; min-width: 30px; height: 28px; background: #fff; color: var(--text-strong); border: 1px solid var(--soft-white-border); box-shadow: none; padding: 0; display: inline-flex; align-items: center; justify-content: center; transition: border-color .15s ease, color .15s ease; }
.refresh-button:hover, .btn-refresh:hover { border-color: var(--primary-red); color: var(--primary-red); }
```

Find `.search-shell .search-icon` rule (around line 326):
```css
.search-shell .search-icon, .header-search .search-icon { position: absolute; left: 8px; top: 5px; font-weight: 900; color: var(--text-strong); pointer-events: none; }
```

Replace with:
```css
.search-shell .search-icon, .header-search .search-icon { position: absolute; left: 8px; top: 5px; color: var(--text-secondary); pointer-events: none; }
```

- [ ] **Step 6: Run check + tests, commit**

```bash
cd "D:/Ibrahim/Projects/project_tracker/frontend"
npm run check
npm test 2>&1 | grep -E "^(not ok|# pass|# fail)"
cd ..
git add frontend/src/lib/components/Header.svelte frontend/src/styles.css
git commit -m "fix(polish): calendar SVG icon, Notion-like button styling for header"
```

---

## Task 6: Update test assertions + final verification

**Files:**
- Modify: `frontend/tests/project-details-fase1.test.mjs`

- [ ] **Step 1: Update assertions for Back button now in toolbar (not pd-back-bar)**

Find in `project-details-fase1.test.mjs`:
```js
  assert.match(PD, /<svg[^>]*pd-icon-back/);
```

Replace with:
```js
  assert.match(PD, /Back to Dashboard|Back"/);
```

- [ ] **Step 2: Run full suite + build**

```bash
cd "D:/Ibrahim/Projects/project_tracker/frontend"
npm run check
npm test 2>&1 | tail -10
npm run build 2>&1 | tail -5
```
Expected: 0 errors, all tests pass (except pre-existing parity if any), build succeeds.

- [ ] **Step 3: Commit**

```bash
cd "D:/Ibrahim/Projects/project_tracker"
git add frontend/tests/project-details-fase1.test.mjs
git commit -m "test(polish): update assertions for Back button in toolbar"
```

---

## Self-Review

**Spec coverage:**
- 1.1 Sub Project dropdown restored → Task 1 Step 3 ✓
- 1.2 Subtitle removed → Task 1 Step 2 ✓
- 1.3 Back button moved to toolbar → Task 1 Steps 1+3 ✓
- 2.1 CR Number row removed → Task 2 Step 1 ✓
- 2.2 CR Link → CR Number label → Task 2 Step 2 ✓
- 2.3 CR State inline → Task 2 Step 3 ✓
- 3.1 Table columns parity → Task 3 Step 1 ✓
- 3.2 Actions column removed → Task 3 Step 1 ✓
- 3.3 Row-click opens folder → Task 3 Step 1 ✓
- 4.1 Debounced sync → Task 4 Steps 1-3 ✓
- 4.2 execCommand preserved → already in place ✓
- 4.3 Checklist bug fix → Task 4 Step 4 ✓
- 5.1 Calendar icon → Task 5 Step 1 ✓
- 5.2 Button polish → Task 5 Steps 2-5 ✓

No gaps. No placeholders. Type consistency verified.
