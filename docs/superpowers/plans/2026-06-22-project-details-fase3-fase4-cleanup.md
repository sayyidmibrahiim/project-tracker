# Project Details Fase 3 & 4 — WYSIWYG Notes & Sub-project View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a live, contenteditable WYSIWYG editor for Project Notes with checklist support, bidirectional Markdown conversion, and a customized sub-project detail view featuring date/CR state inheritance from main projects.

**Architecture:** 
- Frontend modifications in `NotesEditor.svelte` (WYSIWYG layout, contenteditable events, HTML-markdown converter) and `ProjectDetails.svelte` (read-only states for sub-project fields, hide sub-project nesting card).
- Backend updates in `app_web.py` to fix folder-state resolution crashes and return sub-project flags with inherited values.
- New test file `project-details-fase3-fase4.test.mjs` verifying WYSIWYG notes and sub-project inheritance.

**Tech Stack:** Svelte 5, TypeScript, Python 3.14 (backend), node:test + pytest.

**Reference doc:** `docs/superpowers/specs/2026-06-22-project-details-fase3-fase4-design.md`

---

## File Structure

**Modified:**
- `frontend/src/lib/components/NotesEditor.svelte` — replace textarea with contenteditable visual editor, add HTML-to-markdown roundtrip and checklist handlers.
- `frontend/src/lib/components/ProjectDetails.svelte` — check `is_subproject` flag on select, disable dates/CR state edits, and hide the sub-projects nesting card.
- `project_tracker/app_web.py` — fix 5 folder-state crash points, detect sub-project paths, and inherit metadata fields from parent projects.

**Created:**
- `frontend/tests/project-details-fase3-fase4.test.mjs` — test suite for HTML-markdown translation, checklist handling, and sub-project inheritance behavior.

---

## Task 1: Fix Backend Folder-State Crashes & Implement Sub-project Inheritance

We will update `app_web.py` to safely resolve `ProjectState` on sub-project folders and merge inherited parent fields in `get_project`/`update_project`.

**Files:**
- Modify: `project_tracker/app_web.py`
- Test: run pytest using virtual environment

- [ ] **Step 1: Replace all raw `ProjectState(path.parent.name)` calls with `_folder_state_for_path(path)`**

Find and replace all 5 occurrences:
- Line 451: `project_state = ProjectState(path.parent.name)`
- Line 505: `project_state = ProjectState(path.parent.name)`
- Line 646: `project_state = ProjectState(path.parent.name)`
- Line 700: `project_state = ProjectState(path.parent.name)`
- Line 800: `current_folder = ProjectState(path.parent.name)`

Replace them with:
`project_state = _folder_state_for_path(path) or ProjectState.UAT_PREPARE` (for lines 451, 505, 646, 700) and `current_folder = _folder_state_for_path(path) or ProjectState.UAT_PREPARE` (for line 800).

- [ ] **Step 2: Add sub-project check and date/CR inheritance in `get_project`**

Find (around lines 444–474):
```python
        def get_project(self, project_path: Path) -> object:
            """Return project detail from MetadataStore + filesystem."""
            path = Path(project_path)
            metadata = self._metadata_store.read(path)
            if metadata is None:
                raise FileNotFoundError(f"Project metadata not found: {path}")

            project_state = ProjectState(path.parent.name)
            drone_tickets = getattr(metadata, "drone_tickets", None) or []
            cr_number = extract_cr_number(metadata.cr_link)

            return {
                "project_name": metadata.project_name or path.name,
                "project_path": str(path),
                "project_state": project_state.value,
                "cr_number": cr_number or "",
                "cr_link": metadata.cr_link or "",
                "cr_state": metadata.cr_state.value,
                "start_datetime": metadata.start_datetime,
                "end_datetime": metadata.end_datetime,
                "t10_status": "N/A",
                "drone_ticket_count": len(drone_tickets),
                "implementation_plan": metadata.implementation_plan,
                "history": [entry.to_dict() for entry in metadata.history],
                "drone_tickets": [
                    {
                        "subfolder_name": t.subfolder_name,
                        "drone_link": t.drone_link,
                        "drone_state": t.drone_state.value,
                        "owner": t.owner,
                    }
                    for t in drone_tickets
                ],
            }
```

Replace with:
```python
        def get_project(self, project_path: Path) -> object:
            """Return project detail from MetadataStore + filesystem."""
            path = Path(project_path)
            metadata = self._metadata_store.read(path)
            if metadata is None:
                raise FileNotFoundError(f"Project metadata not found: {path}")

            project_state = _folder_state_for_path(path) or ProjectState.UAT_PREPARE
            
            # Sub-project detection: parent contains project_data.json
            is_subproject = (path.parent / "project_data.json").is_file()
            
            if is_subproject:
                parent_path = path.parent
                parent_meta = self._metadata_store.read(parent_path)
                if parent_meta:
                    metadata.cr_link = parent_meta.cr_link
                    metadata.cr_state = parent_meta.cr_state
                    metadata.start_datetime = parent_meta.start_datetime
                    metadata.end_datetime = parent_meta.end_datetime
                drone_tickets = []
                subprojects_list = []
            else:
                drone_tickets = getattr(metadata, "drone_tickets", None) or []
                subprojects_list = [p.name for p in discover_subproject_paths(path)]

            cr_number = extract_cr_number(metadata.cr_link)

            return {
                "project_name": metadata.project_name or path.name,
                "project_path": str(path),
                "project_state": project_state.value,
                "cr_number": cr_number or "",
                "cr_link": metadata.cr_link or "",
                "cr_state": metadata.cr_state.value,
                "start_datetime": metadata.start_datetime,
                "end_datetime": metadata.end_datetime,
                "t10_status": "N/A",
                "drone_ticket_count": len(drone_tickets),
                "implementation_plan": metadata.implementation_plan,
                "history": [entry.to_dict() for entry in metadata.history] if not is_subproject else [],
                "drone_tickets": [
                    {
                        "subfolder_name": t.subfolder_name,
                        "drone_link": t.drone_link,
                        "drone_state": t.drone_state.value,
                        "owner": t.owner,
                    }
                    for t in drone_tickets
                ],
                "is_subproject": is_subproject,
                "subprojects": subprojects_list
            }
```

- [ ] **Step 3: Modify `update_project` to handle sub-project parent propagation**

Find (around lines 680–706):
```python
        def update_project(self, project_path: Path, data: dict[str, object]) -> object:
            """Update allowed metadata fields and persist. No folder move."""
            path = Path(project_path)
            if not path.is_dir():
                raise FileNotFoundError(f"Project folder not found: {path}")
            metadata = self._metadata_store.read(path)
            if metadata is None:
                raise FileNotFoundError(f"Project metadata not found: {path}")
            if "project_name" in data:
                metadata.project_name = str(data["project_name"])
            if "implementation_plan" in data:
                metadata.implementation_plan = str(data["implementation_plan"])
            if "cr_link" in data:
                metadata.cr_link = str(data["cr_link"])
            if "start_datetime" in data:
                metadata.start_datetime = _parse_optional_datetime(data["start_datetime"])
            if "end_datetime" in data:
                metadata.end_datetime = _parse_optional_datetime(data["end_datetime"])
            metadata.updated_at = local_now()
            self._metadata_store.write(path, metadata)
            project_state = ProjectState(path.parent.name)
            return {
                "project_path": str(path),
                "project_name": metadata.project_name or path.name,
                "project_state": project_state.value,
                "cr_state": metadata.cr_state.value,
            }
```

Replace with (propagates updates to parent project metadata if it's a subproject):
```python
        def update_project(self, project_path: Path, data: dict[str, object]) -> object:
            """Update allowed metadata fields and persist. No folder move."""
            path = Path(project_path)
            if not path.is_dir():
                raise FileNotFoundError(f"Project folder not found: {path}")
            metadata = self._metadata_store.read(path)
            if metadata is None:
                raise FileNotFoundError(f"Project metadata not found: {path}")
            
            is_subproject = (path.parent / "project_data.json").is_file()

            if "project_name" in data:
                metadata.project_name = str(data["project_name"])
            if "implementation_plan" in data:
                metadata.implementation_plan = str(data["implementation_plan"])
            
            # If dates or CR details are updated on a sub-project, propagate to parent
            if is_subproject:
                parent_path = path.parent
                parent_meta = self._metadata_store.read(parent_path)
                if parent_meta:
                    if "cr_link" in data:
                        parent_meta.cr_link = str(data["cr_link"])
                    if "start_datetime" in data:
                        parent_meta.start_datetime = _parse_optional_datetime(data["start_datetime"])
                    if "end_datetime" in data:
                        parent_meta.end_datetime = _parse_optional_datetime(data["end_datetime"])
                    parent_meta.updated_at = local_now()
                    self._metadata_store.write(parent_path, parent_meta)
            else:
                if "cr_link" in data:
                    metadata.cr_link = str(data["cr_link"])
                if "start_datetime" in data:
                    metadata.start_datetime = _parse_optional_datetime(data["start_datetime"])
                if "end_datetime" in data:
                    metadata.end_datetime = _parse_optional_datetime(data["end_datetime"])
            
            metadata.updated_at = local_now()
            self._metadata_store.write(path, metadata)
            
            project_state = _folder_state_for_path(path) or ProjectState.UAT_PREPARE
            return {
                "project_path": str(path),
                "project_name": metadata.project_name or path.name,
                "project_state": project_state.value,
                "cr_state": metadata.cr_state.value,
            }
```

- [ ] **Step 4: Run python tests using virtual environment to verify no crashes**

```bash
"D:/Ibrahim/Projects/project_tracker/.venv/Scripts/pytest" "D:/Ibrahim/Projects/project_tracker/tests/test_core_enums.py" -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add project_tracker/app_web.py
git commit -m "fix(fase4): resolve backend crashes on subproject paths & inherit metadata from parent"
```

---

## Task 2: Implement Sub-project Detail View UI (Fase 4)

We will modify `ProjectDetails.svelte` to check the `is_subproject` flag and adapt fields.

**Files:**
- Modify: `frontend/src/lib/components/ProjectDetails.svelte`
- Test: `npm test`

- [ ] **Step 1: Declare `isSubproject` state variable**

Add declaration in script (around line 24):
```svelte
  let isSubproject: boolean = $state(false);
```

- [ ] **Step 2: Set `isSubproject` state on project selection**

In `selectProject` find:
```svelte
    detail = dResp.ok ? (dResp.data ?? null) : null;
    subprojects = spResp.ok ? (spResp.data ?? []) : [];
```
Replace with:
```svelte
    detail = dResp.ok ? (dResp.data ?? null) : null;
    isSubproject = detail ? (detail as any).is_subproject || false : false;
    subprojects = spResp.ok ? (spResp.data ?? []) : [];
```

- [ ] **Step 3: Disable / Read-only fields in Template when `isSubproject` is true**

Find `crStateEdit` select block:
```svelte
                    <select id="meta-cr-state" class="cr-state-select" value={crStateEdit} onchange={(e) => onCrStateChange((e.currentTarget as HTMLSelectElement).value)} disabled={crStateSaveState === "saving"}>
```
Replace with (disabled if subproject):
```svelte
                    <select id="meta-cr-state" class="cr-state-select" value={crStateEdit} onchange={(e) => onCrStateChange((e.currentTarget as HTMLSelectElement).value)} disabled={crStateSaveState === "saving" || isSubproject}>
```

Find CR Link `input` and buttons block:
```svelte
                {#if crLinkEditing}
                  <input
                    id="meta-cr-link"
                    class="cr-link-input"
                    type="url"
                    placeholder="Paste CR link…"
                    bind:value={crLinkEdit}
                    onblur={saveCrLinkFromInput}
                    disabled={crLinkSaveState === "saving"}
                  />
```
Replace input and buttons display to disable editing if subproject:
```svelte
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
```

Find the Start/End datetime inputs in Schedule block:
```svelte
                <div class="pd-meta-datetime-row">
                  <label class="pd-meta-field" for="meta-start">
                    <span class="pd-meta-label">Start datetime</span>
                    <input id="meta-start" class="cr-link-input" type="datetime-local" bind:value={metaStartEdit} onblur={saveMetadataIfChanged} disabled={metaSaveState === "saving"} />
                  </label>
                  <label class="pd-meta-field" for="meta-end">
                    <span class="pd-meta-label">End datetime</span>
                    <input id="meta-end" class="cr-link-input" type="datetime-local" bind:value={metaEndEdit} onblur={saveMetadataIfChanged} disabled={metaSaveState === "saving"} />
                  </label>
                </div>
```
Replace with (disabled inputs if subproject + show inherited label):
```svelte
                <div class="pd-meta-datetime-row">
                  <label class="pd-meta-field" for="meta-start">
                    <span class="pd-meta-label">Start datetime</span>
                    <input id="meta-start" class="cr-link-input" type="datetime-local" bind:value={metaStartEdit} onblur={saveMetadataIfChanged} disabled={metaSaveState === "saving" || isSubproject} />
                  </label>
                  <label class="pd-meta-field" for="meta-end">
                    <span class="pd-meta-label">End datetime</span>
                    <input id="meta-end" class="cr-link-input" type="datetime-local" bind:value={metaEndEdit} onblur={saveMetadataIfChanged} disabled={metaSaveState === "saving" || isSubproject} />
                  </label>
                </div>
                {#if isSubproject}
                  <span class="pd-inherited-label">(Inherited from Main Project)</span>
                {/if}
```

Disable explicit schedule save button:
```svelte
                  <button class="cr-link-save-btn" onclick={saveMetadata} disabled={metaSaveState === "saving" || metadataUnchanged(detail)}>{#if metaSaveState === "saving"}⏳ Saving…{:else}Save identity + schedule{/if}</button>
```
Replace:
```svelte
                  <button class="cr-link-save-btn" onclick={saveMetadata} disabled={metaSaveState === "saving" || metadataUnchanged(detail) || isSubproject}>{#if metaSaveState === "saving"}⏳ Saving…{:else}Save identity + schedule{/if}</button>
```

- [ ] **Step 4: Hide the "Sub Project (DRONE)" box card when `isSubproject` is true**

Find:
```svelte
            <div class="pd-section">
              <div class="pd-section-head">
                <h4 class="pd-section-title">Sub Project (DRONE)</h4>
```
Replace:
```svelte
            {#if !isSubproject}
              <div class="pd-section">
                <div class="pd-section-head">
                  <h4 class="pd-section-title">Sub Project (DRONE)</h4>
                  <div class="pd-inline-create">
                    <input class="pd-control" placeholder="Sub project name…" bind:value={newSubprojectName} disabled={subprojectBusy} />
                    <button class="pd-command-btn" type="button" onclick={addSubproject} disabled={subprojectBusy || !newSubprojectName.trim()}>Add Sub Project</button>
                  </div>
                </div>
                <SubProjectTable
                  {subprojects}
                  droneTickets={detail.drone_tickets}
                  selectedRow={selectedSubprojectRow}
                  droneStateBusyName={droneStateBusyName}
                  droneStateErrorName={droneStateErrorName}
                  onSelectRow={onSelectSubprojectRow}
                  onChangeDroneState={onChangeSubprojectDroneState}
                  onOpenFolder={openSubprojectFolder}
                  {legalDroneOptionsFor}
                />
                {#if selectedSubprojectRowDetail}
                  {@const ticket = selectedSubprojectRowDetail.ticket}
                  <div class="pd-drone-detail">
                    <h5 class="pd-drone-detail-title">{selectedSubprojectRow} · Drone Ticket</h5>
                    <label class="pd-meta-field" for="row-drone-link">
                      <span class="pd-meta-label">Drone URL</span>
                      <input
                        id="row-drone-link"
                        class="cr-link-input"
                        type="url"
                        placeholder="Paste drone URL…"
                        value={droneLinkEdit}
                        oninput={(e) => (droneLinkEdit = (e.currentTarget as HTMLInputElement).value)}
                        onblur={saveDroneLinkFromPanel}
                        disabled={droneLinkBusy}
                      />
                    </label>
                    {#if !ticket}
                      <button class="cr-link-save-btn" type="button" onclick={addDroneForSelectedRow} disabled={droneLinkBusy || !droneLinkEdit.trim()}>Add Drone Ticket</button>
                    {/if}
                    {#if droneLinkError}
                      <span class="cr-link-feedback cr-link-err">✗ {droneLinkError}</span>
                    {/if}
                  </div>
                {/if}
                {#if subprojectFeedback}
                  <p class:cr-link-ok={subprojectFeedbackKind === "success"} class:cr-link-err={subprojectFeedbackKind === "error"} class="cr-link-feedback">{subprojectFeedbackKind === "success" ? "✓" : "✗"} {subprojectFeedback}</p>
                {/if}
              </div>
            {/if}
```

Add CSS for the new label in `<style>` block:
```css
  .pd-inherited-label { font-size: 10px; color: var(--color-muted); font-style: italic; margin-top: 2px; }
```

- [ ] **Step 5: Run tests + type check**

```bash
npm run check
npm test
```
Expected: 0 warnings, tests pass (except pre-existing & new Task 3/4 tests).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/components/ProjectDetails.svelte
git commit -m "feat(fase4): disable scheduling/CR edits and hide sub-project table card on sub-project details view"
```

---

## Task 3: Contenteditable WYSIWYG Notes Editor (Fase 3)

We will modify `NotesEditor.svelte` to implement contenteditable direct editor and HTML-markdown round-trip.

**Files:**
- Modify: `frontend/src/lib/components/NotesEditor.svelte`
- Test: `npm test`

- [ ] **Step 1: Replace textarea & preview markup with a single contenteditable div**

Read `NotesEditor.svelte` lines 140–220 first:
```svelte
  // ...
```

Let's read lines 150-182:
```svelte
  // ...
```

We will replace the layout (lines 140–182):
```svelte
  {#if mode === "edit"}
    <textarea
      class="ne-textarea"
...
  <div class="ne-status" ...>
```
With a single visual editor:
```svelte
  <div
    class="ne-textarea ne-editor-area"
    contenteditable="true"
    bind:this={editorEl}
    oninput={onEditorInput}
    onblur={onEditorBlur}
    placeholder="Write project notes (autosaves to notes.md)…"
  ></div>
```

- [ ] **Step 2: Add `htmlToMarkdown` and `markdownToHtml` roundtrip logic**

Add utility function in script section of `NotesEditor.svelte`:
```ts
  function htmlToMarkdown(html: string): string {
    if (!html) return "";
    let md = html;
    
    // Replace blocks
    md = md.replace(/<h1>(.*?)<\/h1>/gi, "# $1\n\n");
    md = md.replace(/<h2>(.*?)<\/h2>/gi, "## $1\n\n");
    md = md.replace(/<h3>(.*?)<\/h3>/gi, "### $1\n\n");
    md = md.replace(/<blockquote>(.*?)<\/blockquote>/gi, "> $1\n\n");
    
    // Checkbox mapping
    md = md.replace(/<div class="ne-todo-item"><input type="checkbox"[^>]*checked[^>]*>\s*<span>(.*?)<\/span><\/div>/gi, "- [x] $1\n");
    md = md.replace(/<div class="ne-todo-item"><input type="checkbox"[^>]*>\s*<span>(.*?)<\/span><\/div>/gi, "- [ ] $1\n");
    
    // List mapping
    md = md.replace(/<li>(.*?)<\/li>/gi, "- $1\n");
    md = md.replace(/<ul[^>]*>/gi, "").replace(/<\/ul>/gi, "\n");
    
    // Inline replacements
    md = md.replace(/<strong>(.*?)<\/strong>/gi, "**$1**");
    md = md.replace(/<b>(.*?)<\/b>/gi, "**$1**");
    md = md.replace(/<em>(.*?)<\/em>/gi, "*$1*");
    md = md.replace(/<i>(.*?)<\/i>/gi, "*$1*");
    md = md.replace(/<code>(.*?)<\/code>/gi, "`$1`");
    md = md.replace(/<a href="([^"]*)"[^>]*>(.*?)<\/a>/gi, "[$2]($1)");
    
    // Strip other paragraph / div tags
    md = md.replace(/<p>(.*?)<\/p>/gi, "$1\n\n");
    md = md.replace(/<div[^>]*>(.*?)<\/div>/gi, "$1\n");
    md = md.replace(/<br\s*\/?>/gi, "\n");
    
    // Clean multiple consecutive newlines
    md = md.replace(/\n{3,}/g, "\n\n");
    return md.trim();
  }
```

We will also use the existing `renderMarkdown` function from `markdown.ts` (which is imported on line 21) to translate Markdown back to rich HTML when project details load:
```ts
  let editorEl = $state<HTMLDivElement | null>(null);

  // Sync state on notes load:
  $effect(() => {
    if (editorEl) {
      editorEl.innerHTML = renderMarkdown(text);
    }
  });
```

- [ ] **Step 3: Implement formatting commands in Toolbar**

Replace formatting toolbar buttons to use `document.execCommand` and Svelte-driven selections.
Find toolbar buttons (lines 146-160):
```svelte
      <button type="button" class="ne-tbtn" title="Bold" onclick={() => surround("**", "**")}><strong>B</strong></button>
      <button type="button" class="ne-tbtn" title="Italic" onclick={() => surround("*", "*")}><em>I</em></button>
      <button type="button" class="ne-tbtn" title="Heading 1" onclick={() => prefixLine("# ")}>H1</button>
      <button type="button" class="ne-tbtn" title="Heading 2" onclick={() => prefixLine("## ")}>H2</button>
      <button type="button" class="ne-tbtn" title="Inline code" onclick={() => surround("`", "`")}>Code</button>
      <button type="button" class="ne-tbtn" title="Bulleted list" onclick={() => prefixLine("- ")}>List</button>
      <button type="button" class="ne-tbtn" title="Quote" onclick={() => prefixLine("> ")}>Quote</button>
      <button type="button" class="ne-tbtn" title="Link" onclick={() => surround("[", "](https://)")}>Link</button>
```

Replace with:
```svelte
      <button type="button" class="ne-tbtn" title="Bold" onclick={() => format('bold')}><strong>B</strong></button>
      <button type="button" class="ne-tbtn" title="Italic" onclick={() => format('italic')}><em>I</em></button>
      <button type="button" class="ne-tbtn" title="Heading 1" onclick={() => format('formatBlock', '<h1>')}>H1</button>
      <button type="button" class="ne-tbtn" title="Heading 2" onclick={() => format('formatBlock', '<h2>')}>H2</button>
      <button type="button" class="ne-tbtn" title="Inline code" onclick={formatCode}>Code</button>
      <button type="button" class="ne-tbtn" title="Bulleted list" onclick={() => format('insertUnorderedList')}>List</button>
      <button type="button" class="ne-tbtn" title="Quote" onclick={() => format('formatBlock', '<blockquote>')}>Quote</button>
      <button type="button" class="ne-tbtn" title="Link" onclick={formatLink}>Link</button>
      <button type="button" class="ne-tbtn" title="Checklist" onclick={formatChecklist}>Todo</button>
```

Add these helper formatting functions to `<script>`:
```ts
  function format(command: string, value: string = "") {
    document.execCommand(command, false, value);
    syncToMarkdown();
  }

  function formatCode() {
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0) return;
    const range = sel.getRangeAt(0);
    const code = document.createElement("code");
    code.textContent = range.toString();
    range.deleteContents();
    range.insertNode(code);
    syncToMarkdown();
  }

  function formatLink() {
    const url = prompt("Enter URL:");
    if (url) format("createLink", url);
  }

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

  function syncToMarkdown() {
    if (editorEl) {
      text = htmlToMarkdown(editorEl.innerHTML);
      scheduleSave();
    }
  }

  function onEditorInput() {
    syncToMarkdown();
  }

  function onEditorBlur() {
    if (status === "pending") flush();
  }

  function bindCheckboxListeners() {
    if (!editorEl) return;
    const boxes = editorEl.querySelectorAll(".ne-todo-checkbox");
    boxes.forEach(box => {
      box.removeEventListener("change", syncToMarkdown);
      box.addEventListener("change", syncToMarkdown);
    });
  }

  $effect(() => {
    if (editorEl) {
      bindCheckboxListeners();
    }
  });
```

- [ ] **Step 4: Update styles in `<style>` block**

Replace `.ne-textarea` rules and add `.ne-todo-item` / `.ne-todo-checkbox`:
```css
  .ne-textarea { width:100%; min-height:120px; max-height:300px; padding:10px; background:var(--color-workspace-panel); border:1px solid #D7DCE2; border-radius:6px; font-size:12px; font-family:var(--font); color:var(--color-ink); resize:vertical; outline:none; line-height:1.5; overflow-y:auto; }
  .ne-textarea:focus { border-color:var(--color-dbs-red); }
  .ne-todo-item { display: flex; align-items: center; gap: 6px; margin: 4px 0; }
  .ne-todo-checkbox { width: 14px; height: 14px; cursor: pointer; }
```

- [ ] **Step 5: Run tests + check**

```bash
npm run check
npm test
```
Expected: 0 errors, 0 warnings.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/components/NotesEditor.svelte
git commit -m "feat(fase3): replace raw markdown notes text area with visual contenteditable WYSIWYG editor"
```

---

## Task 4: New test suite and Final verification (Fase 3 & 4)

We will write `frontend/tests/project-details-fase3-fase4.test.mjs` verifying WYSIWYG notes and sub-project inheritance.

**Files:**
- Create: `frontend/tests/project-details-fase3-fase4.test.mjs`
- Test: `npm test`

- [ ] **Step 1: Write `project-details-fase3-fase4.test.mjs`**

Create:
```js
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PD = readFileSync(resolve(__dirname, "../src/lib/components/ProjectDetails.svelte"), "utf8");
const NE = readFileSync(resolve(__dirname, "../src/lib/components/NotesEditor.svelte"), "utf8");

test("NotesEditor uses contenteditable instead of textarea for WYSIWYG", () => {
  assert.match(NE, /contenteditable="true"/);
  assert.doesNotMatch(NE, /<textarea/);
});

test("NotesEditor converts HTML checkboxes to markdown and vice-versa", () => {
  assert.match(NE, /htmlToMarkdown/);
  assert.match(NE, /ne-todo-checkbox/);
  assert.match(NE, /- \[ \]/);
  assert.match(NE, /- \[x\]/);
});

test("ProjectDetails disables CR and schedule inputs for sub-projects", () => {
  assert.match(PD, /isSubproject/);
  assert.match(PD, /disabled=\{[^}]*isSubproject\}/);
  assert.match(PD, /pd-inherited-label/);
});
```

- [ ] **Step 2: Run all tests**

```bash
npm test
```
Expected: all tests pass (except pre-existing parity failure).

- [ ] **Step 3: Run production build**

```bash
npm run build
```
Expected: build succeeds.

- [ ] **Step 4: Commit tests**

```bash
git add frontend/tests/project-details-fase3-fase4.test.mjs
git commit -m "test(fase3-fase4): add tests for contenteditable WYSIWYG notes & subproject inheritance"
```

---

## Execution Handoff

Plan complete. Answer with "2" to proceed with Inline Execution.
