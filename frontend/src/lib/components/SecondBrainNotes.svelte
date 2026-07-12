<script lang="ts">
  /**
   * Second Brain — Notes workspace (Task 8).
   *
   * Three zones: explorer (left) / editor (center) / context shelf (right).
   * The center mounts the shared {@link NotesEditor} UNCHANGED, with the exact
   * Project Details selection contract (interaction lock → flush → stale-guarded
   * load → `{#key}` remount). See _docs/DECISIONS.md D-0007 and the RTE change
   * safety rules in CLAUDE.md — this component never forks the editor.
   */
  import { onDestroy, onMount, tick } from "svelte";
  import { callBridge, getRteFile, isPywebviewReady, rteDocumentOpen, waitForPywebviewReady } from "../bridge";
  import type {
    RteFileContent,
    RteDocumentPayload,
    SecondBrainActivity,
    SecondBrainImage,
    SecondBrainItem,
    SecondBrainRelated,
    SecondBrainSort,
    SecondBrainSource,
    SecondBrainWorkspace,
  } from "../types";
  import NotesEditor from "./NotesEditor.svelte";
  import ConfirmModal from "./ConfirmModal.svelte";
  import { addToast } from "../stores/toastStore";

  type LoadState = "idle" | "loading" | "error" | "loaded";
  type TreeNode = { item: SecondBrainItem; children: TreeNode[] };

  // ── Workspace + selection state ──
  let loadState: LoadState = $state("idle");
  let errorMessage: string = $state("");
  let workspace: SecondBrainWorkspace | null = $state(null);
  let selectedItem: SecondBrainItem | null = $state(null);

  // ── Editor payload for the current selection ──
  let rteContent: RteFileContent | null = $state(null);
  let rteDocPayload: RteDocumentPayload | null = $state(null);
  let imagePreview: SecondBrainImage | null = $state(null);
  let editorLoading: boolean = $state(false);
  let editorError: string = $state("");
  let rteEditorFlush: (() => Promise<boolean>) | undefined;
  // Monotonic guard so a slow load never overwrites a newer selection.
  let loadSeq = 0;

  // ── Command bar / search ──
  let searchText: string = $state("");
  let sortMode: SecondBrainSort = $state("newest");
  let sourceFilter: "" | SecondBrainSource = $state("");
  let typeFilter: string = $state("");
  let dateFilter: string = $state("");
  let searchResults: SecondBrainItem[] | null = $state(null);
  let searchTimer: ReturnType<typeof setTimeout> | undefined;
  let searchSeq = 0;
  let searchInputEl: HTMLInputElement | null = $state(null);

  // ── Explorer interaction state ──
  let expanded: Set<string> = $state(new Set());
  // Personal-only create target (a personal folder path, or null → personal_root).
  let personalCreateTarget: string | null = $state(null);
  let creating: boolean = $state(false);
  let createName: string = $state("");
  let createInputEl: HTMLInputElement | null = $state(null);
  let renamingPath: string | null = $state(null);
  let renameName: string = $state("");
  let pendingRecycle: SecondBrainItem | null = $state(null);

  // ── Context shelf ──
  let related: SecondBrainRelated[] = $state([]);
  let activity: SecondBrainActivity[] = $state([]);

  // ── Derived views ──
  const items = $derived.by<SecondBrainItem[]>(() => workspace?.items ?? []);
  const itemsByPath = $derived.by(() => new Map<string, SecondBrainItem>(items.map((it) => [it.path, it])));
  const pinnedItems = $derived.by(() => items.filter((it) => it.pinned));
  const favoriteItems = $derived.by(() => items.filter((it) => it.favorite));
  const personalTree = $derived.by(() => buildTree(items.filter((it) => it.source === "personal")));
  const projectTree = $derived.by(() => buildTree(items.filter((it) => it.source === "project")));
  const personalMissing = $derived.by(() => !!workspace && workspace.personal_status !== "ready");
  const tagText = $derived.by(() => (selectedItem?.tags ?? []).join(", "));

  /** Nest a flat item list into a folder tree using parent_path. */
  function buildTree(list: SecondBrainItem[]): TreeNode[] {
    const byPath = new Map<string, TreeNode>();
    for (const it of list) byPath.set(it.path, { item: it, children: [] });
    const roots: TreeNode[] = [];
    for (const node of byPath.values()) {
      const parent = node.item.parent_path ? byPath.get(node.item.parent_path) : undefined;
      if (parent) parent.children.push(node);
      else roots.push(node);
    }
    const order = (a: TreeNode, b: TreeNode) => {
      const af = a.item.item_type === "folder" ? 0 : 1;
      const bf = b.item.item_type === "folder" ? 0 : 1;
      return af - bf || a.item.title.localeCompare(b.item.title);
    };
    const sortRec = (nodes: TreeNode[]) => {
      nodes.sort(order);
      for (const n of nodes) sortRec(n.children);
    };
    sortRec(roots);
    return roots;
  }

  function setInteractionLock(locked: boolean) {
    if (typeof window === "undefined") return;
    window.dispatchEvent(new CustomEvent("app:interaction-lock", { detail: { source: "second-brain-rte", locked } }));
  }

  function setRteEditorApi(api: { flushNow: () => Promise<boolean> } | undefined) {
    rteEditorFlush = api?.flushNow;
  }

  async function flushCurrentEditor(): Promise<boolean> {
    if (!rteEditorFlush) return true;
    try {
      return await rteEditorFlush();
    } catch {
      return false;
    }
  }

  // ── Selection contract (mirrors ProjectDetails.selectCrDoc) ──
  async function selectItem(item: SecondBrainItem) {
    setInteractionLock(true);
    const token = ++loadSeq;
    // 2–3: flush the outgoing editor; abort + retain current selection on failure.
    const flushed = await flushCurrentEditor();
    if (flushed === false) {
      if (token === loadSeq) setInteractionLock(false);
      editorError = "Save failed — kept the current document open.";
      return;
    }
    // 4: assign the requested item and clear the old payload.
    selectedItem = item;
    rteContent = null;
    rteDocPayload = null;
    imagePreview = null;
    editorError = "";
    editorLoading = item.open_mode !== "external";
    try {
      if (item.open_mode === "docx") {
        const resp = await rteDocumentOpen(item.path);
        if (token !== loadSeq) return; // 6: stale response ignored
        if (!resp.ok || !resp.data) {
          editorError = resp.ok ? "Empty document payload." : resp.error.message;
          return;
        }
        rteDocPayload = resp.data;
        rteContent = {
          content: resp.data.content_html ?? "",
          format: "docx",
          editable: resp.data.editable,
          capability: resp.data.capability,
          message: resp.data.message,
          saveStrategy: resp.data.saveStrategy,
          supportedEditorFeatures: resp.data.supportedEditorFeatures,
        };
      } else if (item.open_mode === "markdown" || item.open_mode === "text") {
        const resp = await getRteFile(item.path);
        if (token !== loadSeq) return;
        if (!resp.ok) {
          editorError = resp.error.message;
          return;
        }
        rteContent = resp.data;
      } else if (item.open_mode === "image") {
        const resp = await callBridge<SecondBrainImage>("second_brain_image", item.path);
        if (token !== loadSeq) return;
        if (!resp.ok) {
          editorError = resp.error.message;
          return;
        }
        imagePreview = resp.data;
      }
      // open_mode === "external": nothing to load; template offers Open externally.
    } finally {
      if (token === loadSeq) {
        editorLoading = false;
        setInteractionLock(false); // 8: only the current request releases the lock
      }
    }
    void recordOpen(item);
    void loadContext(item, token);
  }

  async function recordOpen(item: SecondBrainItem) {
    // External items load nothing on selection — only a real openExternal()
    // click earns an activity record. Images ARE opened (inline preview), so
    // they still record here same as markdown/text/docx.
    if (item.open_mode === "external") return;
    await callBridge("second_brain_activity_record", item.id, "opened");
  }

  async function loadContext(item: SecondBrainItem, token: number) {
    const [relResp, actResp] = await Promise.all([
      callBridge<SecondBrainRelated[]>("second_brain_related", item.id),
      callBridge<SecondBrainActivity[]>("second_brain_activity_list", item.id),
    ]);
    if (token !== loadSeq) return;
    related = relResp.ok ? (relResp.data ?? []) : [];
    activity = actResp.ok ? (actResp.data ?? []) : [];
  }

  async function loadActivity() {
    if (!selectedItem) return;
    const resp = await callBridge<SecondBrainActivity[]>("second_brain_activity_list", selectedItem.id);
    if (resp.ok) activity = resp.data ?? [];
  }

  // The editor owns the file write; we only stamp saved-state + refresh activity.
  async function onEditorSaved(_notes: string) {
    if (!selectedItem) return;
    await callBridge("second_brain_mark_saved", selectedItem.path);
    void loadActivity();
  }

  function openExternal(item: SecondBrainItem) {
    void callBridge("file_open", item.path);
    void callBridge("second_brain_activity_record", item.id, "opened_externally");
  }

  // ── Search (150 ms debounce + stale-result guard) ──
  function onSearchInput() {
    if (searchTimer) clearTimeout(searchTimer);
    searchTimer = setTimeout(runSearch, 150);
  }

  async function runSearch() {
    const query = searchText.trim();
    if (!query) {
      searchResults = null;
      return;
    }
    const seq = ++searchSeq;
    const resp = await callBridge<SecondBrainItem[]>("second_brain_search", query, {
      sort: sortMode,
      source: sourceFilter,
      item_type: typeFilter,
      date: dateFilter,
    });
    if (seq !== searchSeq) return; // stale search ignored
    searchResults = resp.ok ? (resp.data ?? []) : [];
  }

  function onFiltersChanged() {
    if (searchText.trim()) void runSearch();
  }

  // ── Explorer: folder toggle + create/rename/recycle ──
  // Folders only toggle expansion + move the Personal create target — they never
  // reassign `selectedItem`, so an open (possibly dirty) editor is never unmounted
  // without going through the flush contract in selectItem().
  function onNodeActivate(node: TreeNode) {
    if (node.item.item_type === "folder") {
      const next = new Set(expanded);
      if (next.has(node.item.path)) next.delete(node.item.path);
      else next.add(node.item.path);
      expanded = next;
      if (node.item.source === "personal") personalCreateTarget = node.item.path;
    } else {
      if (node.item.source === "personal") personalCreateTarget = node.item.parent_path;
      void selectItem(node.item);
    }
  }

  async function beginCreate() {
    creating = true;
    createName = "";
    await tick();
    createInputEl?.focus();
  }

  function cancelCreate() {
    creating = false;
    createName = "";
  }

  async function commitCreate() {
    const name = createName.trim();
    // Clear the guard + name synchronously BEFORE the await: unmounting the
    // `{#if creating}` input fires its onblur → commitCreate re-entry, which
    // must see an already-empty createName and no-op (mirrors commitRename).
    creating = false;
    createName = "";
    if (!name) return;
    const target = personalCreateTarget ?? workspace?.personal_root ?? "";
    const resp = await callBridge("second_brain_create", target, name);
    if (!resp.ok) {
      addToast(resp.error.message, "error");
      return;
    }
    await refresh();
  }

  function beginRename(item: SecondBrainItem) {
    renamingPath = item.path;
    renameName = item.title;
  }

  function cancelRename() {
    renamingPath = null;
  }

  async function commitRename() {
    const name = renameName.trim();
    const path = renamingPath;
    renamingPath = null;
    if (!path || !name) return;
    const resp = await callBridge("second_brain_rename", path, name);
    if (!resp.ok) {
      addToast(resp.error.message, "error");
      return;
    }
    await refresh();
  }

  async function confirmRecycle() {
    const item = pendingRecycle;
    pendingRecycle = null;
    if (!item) return;
    const resp = await callBridge("second_brain_recycle", item.path);
    if (!resp.ok) {
      addToast(resp.error.message, "error");
      return;
    }
    if (selectedItem?.path === item.path) {
      selectedItem = null;
      rteContent = null;
      rteDocPayload = null;
      imagePreview = null;
      related = [];
      activity = [];
    }
    await refresh();
  }

  // ── Sidecar metadata: pin / favorite / tags ──
  async function togglePin(item: SecondBrainItem) {
    const resp = await callBridge<SecondBrainItem>("second_brain_pin", item.id);
    if (!resp.ok) {
      addToast(resp.error.message, "error");
      return;
    }
    await refresh();
  }

  async function toggleFavorite(item: SecondBrainItem) {
    const resp = await callBridge<SecondBrainItem>("second_brain_favorite", item.id);
    if (!resp.ok) {
      addToast(resp.error.message, "error");
      return;
    }
    await refresh();
  }

  // Guard so Enter (which also calls .blur() to commit) doesn't double-fire
  // with the resulting onblur re-entry: set true before the await, so the
  // synchronous blur-triggered re-entry no-ops.
  let savingTags = false;
  async function saveTagsFromInput(value: string) {
    if (!selectedItem || savingTags) return;
    savingTags = true;
    try {
      const tags = value.split(",").map((t) => t.trim()).filter(Boolean);
      const resp = await callBridge("second_brain_tags", selectedItem.id, tags);
      if (!resp.ok) {
        addToast(resp.error.message, "error");
        return;
      }
      await refresh();
    } finally {
      savingTags = false;
    }
  }

  // ── Recovery: missing personal-root override ──
  async function browseFolder() {
    const resp = await callBridge<{ path: string | null }>("util_choose_folder");
    if (!resp.ok) {
      addToast(resp.error.message, "error");
      return;
    }
    if (!resp.data?.path) return; // cancelled
    const saved = await callBridge("settings_update", { second_brain_folder: resp.data.path });
    if (!saved.ok) {
      addToast(saved.error.message, "error");
      return;
    }
    await refresh();
  }

  async function useDefaultFolder() {
    const resp = await callBridge("second_brain_use_default_folder");
    if (!resp.ok) {
      addToast(resp.error.message, "error");
      return;
    }
    await refresh();
  }

  // ── Keyboard: Ctrl+F focus · F2 rename · Delete recycle ──
  function onKeydown(e: KeyboardEvent) {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "f") {
      e.preventDefault();
      searchInputEl?.focus();
      return;
    }
    const target = e.target as HTMLElement | null;
    const typing = !!target && (target.tagName === "INPUT" || target.isContentEditable);
    if (typing || !selectedItem) return;
    if (e.key === "F2") {
      e.preventDefault();
      beginRename(selectedItem);
    } else if (e.key === "Delete" && selectedItem.source === "personal") {
      e.preventDefault();
      pendingRecycle = selectedItem;
    }
  }

  // ── Public API (Task 10 shell drives these) ──
  export async function refresh(): Promise<void> {
    loadState = "loading";
    if (!isPywebviewReady() && !(await waitForPywebviewReady())) {
      loadState = "error";
      errorMessage = "pywebview bridge unavailable.";
      return;
    }
    const resp = await callBridge<SecondBrainWorkspace>("second_brain_workspace");
    if (!resp.ok) {
      loadState = "error";
      errorMessage = resp.error.message;
      return;
    }
    workspace = resp.data ?? null;
    loadState = "loaded";
    // Keep the open selection pointing at the freshest metadata without reloading it.
    if (selectedItem && workspace) {
      const updated = workspace.items.find((it) => it.path === selectedItem!.path);
      if (updated) selectedItem = updated;
    }
  }

  export async function flush(): Promise<boolean> {
    return await flushCurrentEditor();
  }

  onMount(() => {
    window.addEventListener("keydown", onKeydown);
    void refresh();
  });

  onDestroy(() => {
    window.removeEventListener("keydown", onKeydown);
    if (searchTimer) clearTimeout(searchTimer);
    setInteractionLock(false);
  });
</script>

<section class="sb-notes" aria-label="Second Brain notes workspace">
  <div class="sb-command">
    <div class="sb-search">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
      <input
        bind:this={searchInputEl}
        class="sb-input"
        type="search"
        placeholder="Search notes & documents… (Ctrl+F)"
        bind:value={searchText}
        oninput={onSearchInput}
      />
    </div>
    <label class="sb-field">
      <span>Date</span>
      <input class="sb-control" type="month" bind:value={dateFilter} onchange={onFiltersChanged} />
    </label>
    <label class="sb-field">
      <span>Type</span>
      <select class="sb-control" bind:value={typeFilter} onchange={onFiltersChanged}>
        <option value="">All types</option>
        <option value="note">Notes</option>
        <option value="document">Documents</option>
        <option value="image">Images</option>
        <option value="folder">Folders</option>
      </select>
    </label>
    <label class="sb-field">
      <span>Source</span>
      <select class="sb-control" bind:value={sourceFilter} onchange={onFiltersChanged}>
        <option value="">All sources</option>
        <option value="personal">Personal</option>
        <option value="project">Project</option>
      </select>
    </label>
    <label class="sb-field">
      <span>Sort</span>
      <select class="sb-control" bind:value={sortMode} onchange={onFiltersChanged}>
        <option value="newest">Newest</option>
        <option value="oldest">Oldest</option>
        <option value="az">A–Z</option>
        <option value="type">Type</option>
      </select>
    </label>
  </div>

  <div class="sb-body">
    <!-- ── Explorer ── -->
    <aside class="sb-explorer">
      {#if loadState === "loading"}
        <p class="sb-muted">Loading workspace…</p>
      {:else if loadState === "error"}
        <div class="sb-banner-error">
          <p class="sb-banner-title">Workspace failed to load</p>
          <p class="sb-muted">{errorMessage}</p>
        </div>
      {:else}
        {#if workspace?.warnings?.length}
          {#each workspace.warnings as warning}
            <p class="sb-warn">{warning}</p>
          {/each}
        {/if}

        {#if searchResults !== null}
          <div class="sb-section">
            <div class="sb-section-head"><h3 class="sb-section-title">Search Results</h3><span class="sb-count">{searchResults.length}</span></div>
            {#if searchResults.length === 0}
              <p class="sb-muted">No matches.</p>
            {:else}
              {#each searchResults as item}
                <button class="sb-row" class:selected={selectedItem?.path === item.path} type="button" onclick={() => selectItem(item)}>
                  <span class="sb-row-title">{item.title}</span>
                  {#if item.match_reason}<span class="sb-row-reason">{item.match_reason}</span>{/if}
                </button>
              {/each}
            {/if}
          </div>
        {/if}

        <div class="sb-section">
          <div class="sb-section-head">
            <h3 class="sb-section-title">Pinned</h3><span class="sb-count">{pinnedItems.length}</span>
          </div>
          {#if pinnedItems.length === 0}
            <p class="sb-muted">Nothing pinned.</p>
          {:else}
            {#each pinnedItems as item}
              <button class="sb-row" class:selected={selectedItem?.path === item.path} type="button" onclick={() => selectItem(item)}>
                <span class="sb-pin-mark" aria-hidden="true">◆</span><span class="sb-row-title">{item.title}</span>
              </button>
            {/each}
          {/if}
        </div>

        <div class="sb-section">
          <div class="sb-section-head"><h3 class="sb-section-title">Favorites</h3><span class="sb-count">{favoriteItems.length}</span></div>
          {#if favoriteItems.length === 0}
            <p class="sb-muted">No favorites.</p>
          {:else}
            {#each favoriteItems as item}
              <button class="sb-row" class:selected={selectedItem?.path === item.path} type="button" onclick={() => selectItem(item)}>
                <span class="sb-fav-mark" aria-hidden="true">★</span><span class="sb-row-title">{item.title}</span>
              </button>
            {/each}
          {/if}
        </div>

        <div class="sb-section">
          <div class="sb-section-head">
            <h3 class="sb-section-title">Personal Notes</h3>
            <button class="sb-mini-btn" type="button" disabled={personalMissing} onclick={beginCreate} title="New note in the selected folder">+ New</button>
          </div>
          {#if personalMissing}
            <div class="sb-recovery">
              <p class="sb-muted">Personal notes folder is not set or unreadable ({workspace?.personal_status}).</p>
              <div class="sb-recovery-actions">
                <button class="sb-mini-btn" type="button" onclick={browseFolder}>Browse folder</button>
                <button class="sb-mini-btn" type="button" onclick={useDefaultFolder}>Use default folder</button>
              </div>
            </div>
          {:else}
            {#if creating}
              <input
                bind:this={createInputEl}
                class="sb-inline-input"
                placeholder="New note name…"
                bind:value={createName}
                onkeydown={(e) => { if (e.key === "Enter") commitCreate(); else if (e.key === "Escape") cancelCreate(); }}
                onblur={commitCreate}
              />
            {/if}
            {#if personalTree.length === 0 && !creating}
              <p class="sb-muted">No personal notes yet.</p>
            {:else}
              {#each personalTree as node}{@render treeNode(node, 0)}{/each}
            {/if}
          {/if}
        </div>

        <div class="sb-section">
          <div class="sb-section-head"><h3 class="sb-section-title">Project Documents</h3></div>
          {#if projectTree.length === 0}
            <p class="sb-muted">No indexed project documents.</p>
          {:else}
            {#each projectTree as node}{@render treeNode(node, 0)}{/each}
          {/if}
        </div>
      {/if}
    </aside>

    <!-- ── Editor / preview ── -->
    <main class="sb-editor">
      {#if !selectedItem || selectedItem.item_type === "folder"}
        <div class="sb-empty">
          <p class="sb-empty-title">Select a note or document</p>
          <p class="sb-muted">Pick an item from the explorer to open it here.</p>
        </div>
      {:else}
        <div class="sb-ribbon">
          <span class="sb-source-badge" class:project={selectedItem.source === "project"}>{selectedItem.source === "project" ? "Project" : "Personal"}</span>
          <span class="sb-ribbon-title" title={selectedItem.path}>{selectedItem.title}</span>
          {#if selectedItem.locked}<span class="sb-lock">Read-only</span>{/if}
          <div class="sb-ribbon-actions">
            <button class="sb-mini-btn" type="button" onclick={() => selectedItem && togglePin(selectedItem)}>{selectedItem.pinned ? "Unpin" : "Pin"}</button>
            <button class="sb-mini-btn" type="button" onclick={() => selectedItem && toggleFavorite(selectedItem)}>{selectedItem.favorite ? "Unfavorite" : "Favorite"}</button>
            <button class="sb-mini-btn" type="button" onclick={() => selectedItem && beginRename(selectedItem)} title="Rename (F2)">Rename</button>
          </div>
        </div>
        <label class="sb-tags">
          <span>Tags</span>
          <input
            class="sb-inline-input"
            placeholder="comma, separated, tags"
            value={tagText}
            onkeydown={(e) => { if (e.key === "Enter") { saveTagsFromInput((e.currentTarget as HTMLInputElement).value); (e.currentTarget as HTMLInputElement).blur(); } }}
            onblur={(e) => saveTagsFromInput((e.currentTarget as HTMLInputElement).value)}
          />
        </label>

        {#if editorError}
          <p class="sb-banner-error">{editorError}</p>
        {/if}

        {#if selectedItem.open_mode === "external"}
          <div class="sb-external">
            <p class="sb-muted">This file type ({selectedItem.file_format || "unknown"}) can’t be edited here.</p>
            <button class="sb-mini-btn" type="button" onclick={() => selectedItem && openExternal(selectedItem)}>Open externally</button>
          </div>
        {:else if selectedItem.open_mode === "image"}
          {#if editorLoading}
            <p class="sb-muted">Loading preview…</p>
          {:else if imagePreview?.data_uri}
            <div class="sb-image-wrap">
              <img class="sb-image" src={imagePreview.data_uri} alt={imagePreview.name ?? selectedItem.title} />
            </div>
          {:else}
            <div class="sb-external">
              <p class="sb-muted">Preview unavailable.</p>
              <button class="sb-mini-btn" type="button" onclick={() => selectedItem && openExternal(selectedItem)}>Open externally</button>
            </div>
          {/if}
        {:else if editorLoading || !rteContent}
          <p class="sb-muted">Loading document…</p>
        {:else}
          {#key selectedItem.path}
            <NotesEditor
              onReady={setRteEditorApi}
              projectPath={selectedItem.project_path ?? ""}
              filePath={selectedItem.path}
              fileFormat={rteContent.format}
              initialNotes={rteContent.content}
              editable={rteContent.editable}
              capability={rteContent.capability ?? (rteContent.editable ? "editable" : "read_only")}
              saveStrategy={rteContent.saveStrategy ?? "none"}
              supportedEditorFeatures={rteContent.supportedEditorFeatures}
              message={rteContent.message}
              initialDoc={rteDocPayload?.content ?? null}
              initialRevision={rteDocPayload?.revision ?? 0}
              needsMigration={rteDocPayload?.needs_migration ?? false}
              onSaved={onEditorSaved}
            />
          {/key}
        {/if}
      {/if}
    </main>

    <!-- ── Context shelf ── -->
    <aside class="sb-shelf">
      <div class="sb-section">
        <div class="sb-section-head"><h3 class="sb-section-title">Related</h3><span class="sb-count">{related.length}</span></div>
        {#if related.length === 0}
          <p class="sb-muted">No related items.</p>
        {:else}
          {#each related as row}
            <button class="sb-row" type="button" onclick={() => selectItem(row.item)}>
              <span class="sb-row-title">{row.item.title}</span>
              <span class="sb-row-reason">{row.reason.replaceAll("_", " ")}</span>
            </button>
          {/each}
        {/if}
      </div>

      <div class="sb-section">
        <div class="sb-section-head"><h3 class="sb-section-title">Activity</h3><span class="sb-count">{activity.length}</span></div>
        {#if activity.length === 0}
          <p class="sb-muted">No activity yet.</p>
        {:else}
          <ol class="sb-activity">
            {#each activity as row}
              {@const known = itemsByPath.has(row.path)}
              <li>
                <button class="sb-activity-row" type="button" disabled={!known} title={known ? "Open" : "Target no longer available"} onclick={() => { const t = itemsByPath.get(row.path); if (t) selectItem(t); }}>
                  <span class="sb-activity-action">{row.action.replaceAll("_", " ")}</span>
                  <span class="sb-row-title">{row.title}</span>
                  <time>{row.timestamp}</time>
                </button>
              </li>
            {/each}
          </ol>
        {/if}
      </div>
    </aside>
  </div>
</section>

{#snippet treeNode(node: TreeNode, depth: number)}
  <div class="sb-tree-node">
    {#if renamingPath === node.item.path}
      <input
        class="sb-inline-input"
        style="margin-left:{depth * 12}px"
        bind:value={renameName}
        onkeydown={(e) => { if (e.key === "Enter") commitRename(); else if (e.key === "Escape") cancelRename(); }}
        onblur={commitRename}
      />
    {:else}
      <button
        class="sb-row"
        class:selected={node.item.item_type === "folder" ? personalCreateTarget === node.item.path : selectedItem?.path === node.item.path}
        style="padding-left:{8 + depth * 12}px"
        type="button"
        onclick={() => onNodeActivate(node)}
      >
        <span class="sb-row-icon" aria-hidden="true">
          {#if node.item.item_type === "folder"}{expanded.has(node.item.path) ? "▾" : "▸"}{:else}·{/if}
        </span>
        <span class="sb-row-title">{node.item.title}</span>
      </button>
    {/if}
    {#if node.item.item_type === "folder" && expanded.has(node.item.path)}
      {#each node.children as child}{@render treeNode(child, depth + 1)}{/each}
    {/if}
  </div>
{/snippet}

{#if pendingRecycle}
  <ConfirmModal
    title="Move to recycle bin?"
    actionLabel="Recycle note"
    targetName={pendingRecycle.title}
    reversible={true}
    onConfirm={confirmRecycle}
    onCancel={() => (pendingRecycle = null)}
  />
{/if}

<style>
  .sb-notes { display:flex; flex-direction:column; gap:12px; min-height:0; flex:1; }
  .sb-command { display:flex; align-items:flex-end; gap:10px; flex-wrap:wrap; }
  .sb-search { display:flex; align-items:center; gap:7px; flex:1 1 260px; min-width:200px; height:30px; padding:0 10px; border:1px solid var(--color-input-border); border-radius:7px; background:var(--color-workspace-panel); color:var(--color-muted); }
  .sb-search:focus-within { border-color:var(--color-dbs-red); color:var(--color-ink); }
  .sb-input { flex:1; min-width:0; border:0; background:transparent; color:var(--color-ink); font-size:12.5px; font-weight:600; outline:none; }
  .sb-field { display:flex; flex-direction:column; gap:4px; }
  .sb-field span { font-size:9.5px; font-weight:700; color:var(--color-muted); text-transform:uppercase; letter-spacing:0.05em; }
  .sb-control { height:30px; border:1px solid var(--color-input-border); border-radius:6px; background:var(--color-workspace-panel); color:var(--color-ink); font-size:12px; font-weight:600; padding:0 8px; outline:none; }
  .sb-control:focus { border-color:var(--color-dbs-red); }

  .sb-body { flex:1; min-height:0; display:grid; grid-template-columns:clamp(260px, 24vw, 340px) minmax(0, 1fr) clamp(240px, 22vw, 320px); gap:14px; align-items:stretch; }

  .sb-explorer, .sb-editor, .sb-shelf { min-width:0; min-height:0; background:var(--color-workspace-panel); border:1px solid var(--color-border); border-radius:8px; box-shadow:0 1px 3px rgba(0,0,0,0.05); overflow-y:auto; }
  .sb-explorer, .sb-shelf { padding:12px; display:flex; flex-direction:column; gap:14px; }
  .sb-editor { padding:16px; display:flex; flex-direction:column; gap:12px; }

  .sb-section { display:flex; flex-direction:column; gap:5px; }
  .sb-section-head { display:flex; align-items:center; justify-content:space-between; gap:8px; }
  .sb-section-title { margin:0; font-family:var(--font-display); font-size:11px; font-weight:800; text-transform:uppercase; letter-spacing:0.06em; color:var(--color-muted); }
  .sb-count { font-size:10px; font-weight:800; color:var(--color-muted-light); }

  .sb-row { display:flex; align-items:center; gap:7px; width:100%; text-align:left; border:0; background:transparent; border-radius:6px; padding:6px 8px; font-size:12px; font-weight:650; color:var(--color-ink); cursor:pointer; transition:background 0.12s, color 0.12s; }
  .sb-row:hover, .sb-row.selected { background:var(--color-soft-pink-surface); color:var(--color-dbs-red); }
  .sb-row-title { flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .sb-row-reason { flex:0 0 auto; font-size:9.5px; font-weight:800; text-transform:uppercase; letter-spacing:0.04em; color:var(--color-muted-light); }
  .sb-row-icon, .sb-pin-mark, .sb-fav-mark { flex:0 0 auto; font-size:11px; color:var(--color-muted); }
  .sb-pin-mark, .sb-fav-mark { color:var(--color-dbs-red); }
  .sb-tree-node { display:flex; flex-direction:column; }

  .sb-mini-btn { height:24px; padding:0 9px; border:1px solid var(--color-border); border-radius:6px; background:var(--color-workspace-panel); color:var(--color-ink); font-size:11px; font-weight:700; cursor:pointer; white-space:nowrap; }
  .sb-mini-btn:hover:not(:disabled) { border-color:var(--color-dbs-red); color:var(--color-dbs-red); }
  .sb-mini-btn:disabled { opacity:0.5; cursor:not-allowed; }

  .sb-inline-input { width:100%; height:26px; padding:0 8px; border:1px solid var(--color-dbs-red); border-radius:6px; background:var(--color-workspace-panel); color:var(--color-ink); font-size:12px; font-weight:600; outline:none; }

  .sb-muted { margin:0; font-size:11px; font-weight:500; color:var(--color-muted); line-height:1.5; }
  .sb-warn { margin:0; padding:6px 8px; font-size:10.5px; font-weight:700; color:var(--tag-amber-ink); background:var(--tag-amber-bg); border-radius:6px; }
  .sb-banner-error { margin:0; padding:8px 10px; font-size:11px; font-weight:700; color:var(--tag-red-ink); background:var(--tag-red-bg); border-radius:6px; }
  .sb-banner-title { margin:0 0 2px; font-weight:800; }

  .sb-recovery { display:flex; flex-direction:column; gap:8px; padding:10px; border:1px dashed var(--color-border); border-radius:7px; background:var(--color-workspace); }
  .sb-recovery-actions { display:flex; gap:8px; flex-wrap:wrap; }

  .sb-ribbon { display:flex; align-items:center; gap:10px; flex-wrap:wrap; padding-bottom:8px; border-bottom:1px solid var(--color-hairline); }
  .sb-source-badge { flex:0 0 auto; padding:2px 8px; border-radius:999px; font-size:9.5px; font-weight:900; text-transform:uppercase; letter-spacing:0.05em; background:var(--color-soft-pink-surface); color:var(--color-dbs-red); border:1px solid var(--color-soft-pink-border); }
  .sb-source-badge.project { background:var(--tag-green-bg); color:var(--tag-green-ink); border-color:var(--tag-green-bg); }
  .sb-ribbon-title { flex:1; min-width:0; font-size:14px; font-weight:800; color:var(--color-ink-strong); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .sb-lock { flex:0 0 auto; font-size:10px; font-weight:800; color:var(--tag-amber-ink); }
  .sb-ribbon-actions { display:flex; gap:6px; flex-wrap:wrap; }

  .sb-tags { display:flex; align-items:center; gap:8px; }
  .sb-tags span { flex:0 0 auto; font-size:9.5px; font-weight:800; text-transform:uppercase; letter-spacing:0.05em; color:var(--color-muted); }
  .sb-tags .sb-inline-input { border-color:var(--color-input-border); }
  .sb-tags .sb-inline-input:focus { border-color:var(--color-dbs-red); }

  .sb-empty, .sb-external { display:flex; flex-direction:column; gap:8px; align-items:flex-start; }
  .sb-empty { align-items:center; justify-content:center; flex:1; text-align:center; }
  .sb-empty-title { margin:0; font-size:14px; font-weight:800; color:var(--color-ink-strong); }
  .sb-external { padding:12px; border:1px dashed var(--color-border); border-radius:7px; background:var(--color-workspace); }

  .sb-image-wrap { display:flex; justify-content:center; padding:10px; border:1px solid var(--color-hairline); border-radius:7px; background:var(--color-workspace); }
  .sb-image { max-width:100%; height:auto; border-radius:4px; }

  .sb-activity { list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:4px; }
  .sb-activity-row { display:grid; grid-template-columns:auto 1fr auto; align-items:center; gap:6px; width:100%; text-align:left; border:0; background:transparent; border-radius:6px; padding:5px 7px; font-size:11px; color:var(--color-ink); cursor:pointer; }
  .sb-activity-row:hover:not(:disabled) { background:var(--color-soft-pink-surface); color:var(--color-dbs-red); }
  .sb-activity-row:disabled { opacity:0.55; cursor:default; }
  .sb-activity-action { font-size:9px; font-weight:800; text-transform:uppercase; letter-spacing:0.04em; color:var(--color-muted-light); }
  .sb-activity-row time { font-size:9.5px; color:var(--color-muted); }

  /* Responsive: collapse the context shelf under the editor, then the explorer. */
  @media (max-width:1180px) {
    .sb-body { grid-template-columns:clamp(260px, 24vw, 340px) minmax(0, 1fr); }
    .sb-shelf { grid-column:1 / -1; flex-direction:row; flex-wrap:wrap; }
    .sb-shelf .sb-section { flex:1 1 240px; }
  }
  @media (max-width:900px) {
    .sb-body { grid-template-columns:1fr; }
    .sb-explorer, .sb-shelf { grid-column:auto; }
  }

  @media (prefers-reduced-motion:reduce) {
    .sb-row, .sb-activity-row { transition:none; }
  }
</style>
