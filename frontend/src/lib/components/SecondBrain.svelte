<script lang="ts">
  import { onMount } from "svelte";
  import { callBridge, isPywebviewReady } from "../bridge";
  import type { SecondBrainItem } from "../types";
  import { BridgeErrorCode } from "../types";
  import ConfirmModal from "./ConfirmModal.svelte";

  // ── Tab state ──
  type TabId = "notes" | "linkbank";
  let activeTab: TabId = $state("linkbank");

  // ── Link Bank data ──
  interface LinkItem {
    id: string;
    name: string;
    url: string;
    notes: string;
    category: string;
    archived: string;
  }

  interface LinkBankData {
    categories: string[];
    links: LinkItem[];
  }

  type LoadState = "idle" | "loading" | "error" | "loaded";
  let loadState: LoadState = $state("idle");
  let errorCode: string = $state("");
  let errorMessage: string = $state("");

  let bank: LinkBankData = $state({ categories: [], links: [] });

  // ── Local filters ──
  let searchQuery: string = $state("");
  let categoryFilter: string = $state("all");
  let showArchived: boolean = $state(false);

  // ── Add link form ──
  let addFormOpen: boolean = $state(false);
  let addName: string = $state("");
  let addUrl: string = $state("");
  let addCategory: string = $state("");
  let addNotes: string = $state("");
  let addError: string = $state("");

  // ── Edit state ──
  let editingId: string | null = $state(null);
  let editName: string = $state("");
  let editUrl: string = $state("");
  let editCategory: string = $state("");
  let editNotes: string = $state("");
  let editError: string = $state("");

  // ── Inline action error ──
  let actionError: string = $state("");

  let filteredLinks: LinkItem[] = $derived.by(() => {
    let result = bank.links;
    // Filter archived
    if (!showArchived) {
      result = result.filter((l) => l.archived !== "true");
    }
    // Filter category
    if (categoryFilter !== "all") {
      result = result.filter((l) => l.category === categoryFilter);
    }
    const q = searchQuery.trim().toLowerCase();
    if (q) {
      result = result.filter(
        (l) =>
          l.name.toLowerCase().includes(q) ||
          l.url.toLowerCase().includes(q) ||
          l.notes.toLowerCase().includes(q) ||
          l.category.toLowerCase().includes(q),
      );
    }
    return result;
  });

  // ── Load ──
  async function loadLinkBank() {
    loadState = "loading";
    errorCode = "";
    errorMessage = "";
    actionError = "";

    if (!isPywebviewReady()) {
      errorCode = BridgeErrorCode.BRIDGE_UNAVAILABLE;
      errorMessage = "pywebview bridge is not available. Running outside desktop shell.";
      loadState = "error";
      return;
    }

    const response = await callBridge<LinkBankData>("linkbank_get");
    if (!response.ok) {
      errorCode = response.error.code;
      errorMessage = response.error.message;
      loadState = "error";
      return;
    }

    bank = response.data ?? { categories: [], links: [] };
    loadState = "loaded";
  }

  // ── Add link ──
  async function handleAddLink() {
    addError = "";
    if (!isPywebviewReady()) return;
    const response = await callBridge<LinkItem>("linkbank_add_link", {
      name: addName.trim(),
      url: addUrl.trim(),
      category: addCategory.trim(),
      notes: addNotes.trim(),
    });
    if (!response.ok) {
      addError = response.error.message;
      return;
    }
    // Reset form and reload
    addName = "";
    addUrl = "";
    addCategory = "";
    addNotes = "";
    addFormOpen = false;
    await loadLinkBank();
  }

  // ── Edit link ──
  function startEdit(link: LinkItem) {
    editingId = link.id;
    editName = link.name;
    editUrl = link.url;
    editCategory = link.category;
    editNotes = link.notes;
    editError = "";
  }

  function cancelEdit() {
    editingId = null;
    editError = "";
  }

  async function handleSaveEdit() {
    editError = "";
    if (!isPywebviewReady() || !editingId) return;
    const response = await callBridge<LinkItem>("linkbank_update", {
      id: editingId,
      name: editName.trim(),
      url: editUrl.trim(),
      category: editCategory.trim(),
      notes: editNotes.trim(),
    });
    if (!response.ok) {
      editError = response.error.message;
      return;
    }
    editingId = null;
    await loadLinkBank();
  }

  // ── Archive link ──
  async function handleArchive(linkId: string) {
    actionError = "";
    if (!isPywebviewReady()) return;
    const response = await callBridge<LinkItem>("linkbank_archive_link", linkId);
    if (!response.ok) {
      actionError = response.error.message;
      return;
    }
    await loadLinkBank();
  }

  // ── Notes tab (Second Brain read-only) ──
  type NotesLoadState = "idle" | "loading" | "error" | "loaded";
  let notesLoadState: NotesLoadState = $state("idle");
  let notesErrorCode: string = $state("");
  let notesErrorMessage: string = $state("");
  let notesItems: SecondBrainItem[] = $state([]);
  let notesSearch: string = $state("");
  let selectedItem: SecondBrainItem | null = $state(null);

  // ── Notes CRUD state ──
  // Absolute Second Brain root folder (parent for note creation), from settings_get.
  let secondBrainRoot: string = $state("");
  // Inline action error for pin/favorite/delete.
  let notesActionError: string = $state("");

  // Create note form.
  let createOpen: boolean = $state(false);
  let createFilename: string = $state("");
  let createContent: string = $state("");
  let createError: string = $state("");

  // Edit note (full-content replace via second_brain_note_write).
  let editingNotePath: string | null = $state(null);
  let editContent: string = $state("");
  let editNoteError: string = $state("");

  // Delete confirmation (no bridge call until confirmed).
  let deleteTarget: SecondBrainItem | null = $state(null);

  let filteredNotes: SecondBrainItem[] = $derived.by(() => {
    const q = notesSearch.trim().toLowerCase();
    if (!q) return notesItems;
    return notesItems.filter((n) =>
      n.title.toLowerCase().includes(q) ||
      n.path.toLowerCase().includes(q) ||
      n.item_type.toLowerCase().includes(q),
    );
  });

  async function loadNotes() {
    notesLoadState = "loading";
    notesErrorCode = "";
    notesErrorMessage = "";
    notesActionError = "";
    selectedItem = null;
    editingNotePath = null;

    if (!isPywebviewReady()) {
      notesErrorCode = BridgeErrorCode.BRIDGE_UNAVAILABLE;
      notesErrorMessage = "pywebview bridge unavailable.";
      notesLoadState = "error";
      return;
    }
    // Fetch the configured Second Brain root folder (parent for note creation).
    const settingsResp = await callBridge<{ second_brain_folder?: string }>("settings_get");
    secondBrainRoot = settingsResp.ok ? (settingsResp.data?.second_brain_folder ?? "") : "";

    const resp = await callBridge<SecondBrainItem[]>("second_brain_list");
    if (!resp.ok) {
      notesErrorCode = resp.error.code;
      notesErrorMessage = resp.error.message;
      notesLoadState = "error";
      return;
    }
    notesItems = resp.data ?? [];
    notesLoadState = "loaded";
  }

  async function searchNotes(query: string) {
    notesSearch = query;
    if (!query.trim()) { loadNotes(); return; }
    if (!isPywebviewReady()) return;
    notesLoadState = "loading";
    selectedItem = null;
    const resp = await callBridge<SecondBrainItem[]>("second_brain_search", query);
    if (!resp.ok) {
      notesErrorCode = resp.error.code;
      notesErrorMessage = resp.error.message;
      notesLoadState = "error";
      return;
    }
    notesItems = resp.data ?? [];
    notesLoadState = "loaded";
  }

  async function selectNoteItem(itemId: string) {
    if (!isPywebviewReady()) return;
    const resp = await callBridge<SecondBrainItem>("second_brain_get", itemId);
    selectedItem = resp.ok ? (resp.data ?? null) : null;
    // Leaving a note cancels any in-progress edit of a different note.
    if (!selectedItem || editingNotePath !== selectedItem.path) {
      editingNotePath = null;
      editNoteError = "";
    }
  }

  // ── Create note ──
  function openCreate() {
    createOpen = !createOpen;
    createFilename = "";
    createContent = "";
    createError = "";
  }

  async function handleCreateNote() {
    createError = "";
    if (!isPywebviewReady()) return;
    if (!secondBrainRoot) {
      createError = "No Second Brain folder configured. Set one in Settings first.";
      return;
    }
    const filename = createFilename.trim();
    if (!filename) {
      createError = "Filename is required.";
      return;
    }
    const resp = await callBridge<SecondBrainItem>(
      "second_brain_note_create",
      secondBrainRoot,
      filename,
      createContent,
    );
    if (!resp.ok) {
      createError = resp.error.message;
      return;
    }
    createOpen = false;
    createFilename = "";
    createContent = "";
    await loadNotes();
  }

  // ── Edit / save note (full-content replace) ──
  function startEditNote() {
    if (!selectedItem) return;
    editingNotePath = selectedItem.path;
    // Pre-fill with the preview excerpt. This preview is limited to the first
    // 200 characters; saving overwrites the entire note with the editor content.
    editContent = selectedItem.excerpt ?? "";
    editNoteError = "";
  }

  function cancelEditNote() {
    editingNotePath = null;
    editNoteError = "";
  }

  async function handleSaveNote() {
    editNoteError = "";
    if (!isPywebviewReady() || !editingNotePath) return;
    const resp = await callBridge<SecondBrainItem>(
      "second_brain_note_write",
      editingNotePath,
      editContent,
    );
    if (!resp.ok) {
      editNoteError = resp.error.message;
      return;
    }
    editingNotePath = null;
    await loadNotes();
  }

  // ── Delete note (gated by ConfirmModal — no bridge call until confirm) ──
  function requestDeleteNote(item: SecondBrainItem) {
    notesActionError = "";
    deleteTarget = item;
  }

  function cancelDeleteNote() {
    deleteTarget = null;
  }

  async function confirmDeleteNote() {
    const target = deleteTarget;
    deleteTarget = null;
    if (!target || !isPywebviewReady()) return;
    const resp = await callBridge("second_brain_note_delete", target.path);
    if (!resp.ok) {
      notesActionError = resp.error.message;
      return;
    }
    await loadNotes();
  }

  // ── Pin / favorite toggles (persist; reflect returned state) ──
  // Re-read the list without clearing the current selection (Req 13.x list refresh).
  async function refreshNotesList() {
    if (!isPywebviewReady()) return;
    const resp = await callBridge<SecondBrainItem[]>("second_brain_list");
    if (resp.ok) notesItems = resp.data ?? [];
  }

  async function handleTogglePin(itemId: string) {
    notesActionError = "";
    if (!isPywebviewReady()) return;
    const resp = await callBridge<SecondBrainItem>("second_brain_pin", itemId);
    if (!resp.ok) {
      notesActionError = resp.error.message;
      return;
    }
    if (resp.data && selectedItem?.id === itemId) selectedItem = resp.data;
    await refreshNotesList();
  }

  async function handleToggleFavorite(itemId: string) {
    notesActionError = "";
    if (!isPywebviewReady()) return;
    const resp = await callBridge<SecondBrainItem>("second_brain_favorite", itemId);
    if (!resp.ok) {
      notesActionError = resp.error.message;
      return;
    }
    if (resp.data && selectedItem?.id === itemId) selectedItem = resp.data;
    await refreshNotesList();
  }

  onMount(() => {
    if (activeTab === "linkbank") loadLinkBank();
    else if (activeTab === "notes") loadNotes();
  });

  function onTabSwitch(tab: TabId) {
    activeTab = tab;
    if (tab === "linkbank" && loadState === "idle") loadLinkBank();
    if (tab === "notes" && notesLoadState === "idle") loadNotes();
  }

  // Expose refresh for parent
  export function refresh() {
    if (activeTab === "linkbank") loadLinkBank();
    else if (activeTab === "notes") loadNotes();
  }
</script>

<div class="secondbrain-screen">
  <!-- ── Tab bar ── -->
  <div class="sb-tab-bar">
    <button
      class="sb-tab"
      class:active={activeTab === "notes"}
      onclick={() => onTabSwitch("notes")}
    >Notes</button>
    <button
      class="sb-tab"
      class:active={activeTab === "linkbank"}
      onclick={() => onTabSwitch("linkbank")}
    >Link Bank</button>
  </div>

  <!-- ── Notes tab (Second Brain read-only with search) ── -->
  {#if activeTab === "notes"}
    <div class="sb-notes-panel">
      <!-- Search bar -->
      <div class="sb-notes-toolbar">
        <div class="header-search">
          <span class="search-icon">⌕</span>
          <input
            class="header-input"
            placeholder="Search notes… (type to search)"
            value={notesSearch}
            oninput={(e) => searchNotes((e.target as HTMLInputElement).value)}
          />
        </div>
        <span class="project-count">{filteredNotes.length} item(s)</span>
        <button class="lb-add-btn" onclick={openCreate}>
          {createOpen ? "Cancel" : "+ New Note"}
        </button>
      </div>

      <!-- Create note form -->
      {#if createOpen}
        <div class="lb-add-form">
          {#if !secondBrainRoot}
            <span class="lb-form-error">No Second Brain folder configured. Set one in Settings to create notes.</span>
          {:else}
            <span class="sb-create-parent">in {secondBrainRoot}</span>
            <input class="lb-form-input" placeholder="Filename (e.g. idea.md) *" bind:value={createFilename} />
            <textarea class="sb-create-content" placeholder="Note content (optional)" bind:value={createContent}></textarea>
            <button class="lb-form-submit" onclick={handleCreateNote}>Create</button>
          {/if}
          {#if createError}
            <span class="lb-form-error">{createError}</span>
          {/if}
        </div>
      {/if}

      <!-- Notes action error -->
      {#if notesActionError}
        <div class="lb-inline-error">{notesActionError}</div>
      {/if}

      {#if notesLoadState === "loading"}
        <div class="dashboard-banner banner-loading"><span class="banner-icon">◌</span><span>Loading notes…</span></div>
      {:else if notesLoadState === "error"}
        <div class="dashboard-banner banner-error"><span class="banner-icon">⚠</span><div><p class="banner-title">Notes unavailable</p><p class="banner-detail">{notesErrorCode}: {notesErrorMessage}</p></div></div>
      {:else}
        <div class="sb-notes-body">
          <!-- Left: note list -->
          <div class="sb-notes-list">
            {#if filteredNotes.length === 0}
              <div class="table-empty"><p class="empty-title">No notes found</p><p class="empty-sub">{notesItems.length === 0 ? "No Second Brain items indexed yet. Configure a Second Brain folder in Settings and add files." : "No items match your search."}</p></div>
            {:else}
              {#each filteredNotes as item}
                <button class="sb-note-row" class:selected={selectedItem?.id === item.id} onclick={() => selectNoteItem(item.id)}>
                  <span class="sb-note-icon">{item.pinned ? "◆" : item.favorite ? "★" : "▸"}</span>
                  <div class="sb-note-info">
                    <span class="sb-note-title">{item.title}</span>
                    <span class="sb-note-meta">{item.item_type} · {item.path}</span>
                  </div>
                </button>
              {/each}
            {/if}
          </div>

          <!-- Right: detail panel -->
          <div class="sb-note-detail">
            {#if !selectedItem}
              <div class="table-empty"><p class="empty-title">Select a note</p><p class="empty-sub">Click a note from the list to view details.</p></div>
            {:else}
              <div class="sb-note-card">
                <div class="sb-note-card-head">
                  <span class="sb-note-card-accent"></span>
                  <div style="flex:1;min-width:0;">
                    <h4 class="sb-note-card-title">{selectedItem.title}</h4>
                    <p class="sb-note-card-path">{selectedItem.path}</p>
                  </div>
                </div>
                <dl class="sb-note-grid">
                  <div class="pd-dl-item"><dt>Type</dt><dd>{selectedItem.item_type}</dd></div>
                  <div class="pd-dl-item"><dt>Updated</dt><dd>{selectedItem.updated_at ? new Date(selectedItem.updated_at).toLocaleString("en-GB") : "—"}</dd></div>
                  <div class="pd-dl-item"><dt>Flags</dt><dd>{selectedItem.pinned ? "📌 Pinned " : ""}{selectedItem.favorite ? "★ Favorite" : ""}{!selectedItem.pinned && !selectedItem.favorite ? "—" : ""}</dd></div>
                </dl>

                <!-- Pin / favorite toggles (persist) -->
                <div class="sb-note-actions">
                  <button class="lb-action-btn" onclick={() => handleTogglePin(selectedItem!.id)}>
                    {selectedItem.pinned ? "📌 Unpin" : "📌 Pin"}
                  </button>
                  <button class="lb-action-btn" onclick={() => handleToggleFavorite(selectedItem!.id)}>
                    {selectedItem.favorite ? "★ Unfavorite" : "★ Favorite"}
                  </button>
                  {#if selectedItem.item_type === "note" && editingNotePath !== selectedItem.path}
                    <button class="lb-action-btn" onclick={startEditNote}>✎ Edit</button>
                  {/if}
                  <button class="lb-action-btn lb-action-archive" onclick={() => requestDeleteNote(selectedItem!)}>Delete</button>
                </div>

                {#if editingNotePath === selectedItem.path}
                  <!-- Full-content edit (overwrites the note via second_brain_note_write) -->
                  <div class="sb-edit-block">
                    <p class="sb-edit-caveat">
                      ⚠ Preview is limited to the first 200 characters. Saving overwrites the entire
                      note with the text below.
                    </p>
                    <textarea class="sb-edit-textarea" bind:value={editContent}></textarea>
                    <div class="sb-edit-actions">
                      <button class="lb-form-submit" onclick={handleSaveNote}>Save</button>
                      <button class="lb-form-cancel" onclick={cancelEditNote}>Cancel</button>
                    </div>
                    {#if editNoteError}
                      <span class="lb-form-error">{editNoteError}</span>
                    {/if}
                  </div>
                {:else if selectedItem.excerpt}
                  <div class="sb-note-excerpt">{selectedItem.excerpt}</div>
                {/if}
              </div>
            {/if}
          </div>
        </div>
      {/if}
    </div>

    {#if deleteTarget}
      <ConfirmModal
        title="Delete Second Brain note"
        actionLabel="Delete note"
        targetName={deleteTarget.path}
        reversible={false}
        onConfirm={confirmDeleteNote}
        onCancel={cancelDeleteNote}
      />
    {/if}

  <!-- ── Link Bank tab ── -->
  {:else}
    {#if loadState === "loading"}
      <div class="dashboard-banner banner-loading">
        <span class="banner-icon">◌</span>
        <span>Loading link bank…</span>
      </div>
    {:else if loadState === "error"}
      <div class="dashboard-banner banner-error">
        <span class="banner-icon">⚠</span>
        <div>
          <p class="banner-title">Link Bank unavailable</p>
          <p class="banner-detail">{errorCode}: {errorMessage}</p>
        </div>
      </div>
    {:else}
      <!-- Toolbar -->
      <div class="lb-toolbar">
        <div class="lb-toolbar-left">
          <select class="header-combo" bind:value={categoryFilter}>
            <option value="all">All Categories</option>
            {#each bank.categories as cat}
              <option value={cat}>{cat}</option>
            {/each}
          </select>
          <div class="header-search">
            <span class="search-icon">⌕</span>
            <input
              class="header-input"
              placeholder="Search links…"
              bind:value={searchQuery}
            />
          </div>
          <label class="lb-archived-toggle">
            <input type="checkbox" bind:checked={showArchived} />
            <span>Show archived</span>
          </label>
        </div>
        <div class="lb-toolbar-right">
          <span class="project-count">{filteredLinks.length} link(s)</span>
          <button class="lb-add-btn" onclick={() => { addFormOpen = !addFormOpen; addError = ""; }}>
            {addFormOpen ? "Cancel" : "+ Add Link"}
          </button>
        </div>
      </div>

      <!-- Action error -->
      {#if actionError}
        <div class="lb-inline-error">{actionError}</div>
      {/if}

      <!-- Add link form -->
      {#if addFormOpen}
        <div class="lb-add-form">
          <input class="lb-form-input" placeholder="Name *" bind:value={addName} />
          <input class="lb-form-input" placeholder="URL (https://...) *" bind:value={addUrl} />
          <input class="lb-form-input" placeholder="Category" bind:value={addCategory} />
          <input class="lb-form-input" placeholder="Notes" bind:value={addNotes} />
          <button class="lb-form-submit" onclick={handleAddLink}>Add</button>
          {#if addError}
            <span class="lb-form-error">{addError}</span>
          {/if}
        </div>
      {/if}

      <!-- Link list -->
      <div class="lb-list">
        {#if filteredLinks.length === 0}
          <div class="table-empty">
            <p class="empty-title">No links found</p>
            <p class="empty-sub">
              {bank.links.length === 0 ? "No links in link bank yet. Use '+ Add Link' to create one." : "Adjust filters to see results."}
            </p>
          </div>
        {:else}
          {#each filteredLinks as link (link.id)}
            <article class="lb-card" class:lb-card-archived={link.archived === "true"}>
              <span class="lb-card-accent"></span>
              <div class="lb-card-body">
                {#if editingId === link.id}
                  <!-- Edit mode -->
                  <div class="lb-edit-form">
                    <input class="lb-form-input" placeholder="Name" bind:value={editName} />
                    <input class="lb-form-input" placeholder="URL" bind:value={editUrl} />
                    <input class="lb-form-input" placeholder="Category" bind:value={editCategory} />
                    <input class="lb-form-input" placeholder="Notes" bind:value={editNotes} />
                    <div class="lb-edit-actions">
                      <button class="lb-form-submit" onclick={handleSaveEdit}>Save</button>
                      <button class="lb-form-cancel" onclick={cancelEdit}>Cancel</button>
                    </div>
                    {#if editError}
                      <span class="lb-form-error">{editError}</span>
                    {/if}
                  </div>
                {:else}
                  <!-- Display mode -->
                  <div class="lb-card-top">
                    <h4 class="lb-card-title">
                      <a href={link.url} target="_blank" rel="noopener" class="lb-link">{link.name}</a>
                    </h4>
                    {#if link.category}
                      <span class="lb-category-badge">{link.category}</span>
                    {/if}
                    {#if link.archived === "true"}
                      <span class="lb-archived-badge">Archived</span>
                    {/if}
                  </div>
                  {#if link.url}
                    <p class="lb-card-url">{link.url}</p>
                  {/if}
                  {#if link.notes}
                    <p class="lb-card-notes">{link.notes}</p>
                  {/if}
                  <div class="lb-card-actions">
                    <button class="lb-action-btn" onclick={() => startEdit(link)}>Edit</button>
                    {#if link.archived !== "true"}
                      <button class="lb-action-btn lb-action-archive" onclick={() => handleArchive(link.id)}>Archive</button>
                    {/if}
                  </div>
                {/if}
              </div>
            </article>
          {/each}
        {/if}
      </div>
    {/if}
  {/if}
</div>

<style>
  /* ── Screen ── */
  .secondbrain-screen {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    padding: 14px;
    gap: 12px;
    overflow: hidden;
  }

  /* ── Tab bar ── */
  .sb-tab-bar {
    display: flex;
    gap: 4px;
    flex: 0 0 auto;
    background: var(--color-workspace-panel);
    border: 1px solid #D7DCE2;
    border-radius: 8px;
    padding: 6px;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.30);
  }
  .sb-tab {
    height: 28px;
    border-radius: 5px;
    padding: 0 16px;
    background: transparent;
    border: 1px solid transparent;
    color: var(--color-ink);
    font-weight: 850;
    font-size: 11px;
    cursor: pointer;
    transition: background 0.15s ease, color 0.15s ease;
  }
  .sb-tab:hover {
    background: var(--color-soft-pink-surface);
    color: var(--color-dbs-red);
  }
  .sb-tab.active {
    background: var(--color-dbs-red);
    color: #fff;
    font-weight: 900;
  }

  /* ── Notes panel ── */
  .sb-notes-panel {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
    overflow: hidden;
  }
  .sb-notes-toolbar {
    display: flex;
    align-items: center;
    gap: 8px;
    flex: 0 0 auto;
    background: var(--color-workspace-panel);
    border: 1px solid #D7DCE2;
    border-radius: 8px;
    padding: 10px 12px;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.30);
  }
  .sb-notes-body {
    flex: 1;
    min-height: 0;
    display: grid;
    grid-template-columns: 260px 1fr;
    gap: 8px;
  }
  @media (max-width: 900px) {
    .sb-notes-body { grid-template-columns: 1fr; }
  }
  .sb-notes-list {
    background: #fff;
    border: 1px solid #D7DCE2;
    border-radius: 8px;
    box-shadow: var(--shadow-card);
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 6px;
  }
  .sb-note-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 10px;
    border: 0;
    border-left: 3px solid transparent;
    border-radius: 5px;
    background: transparent;
    cursor: pointer;
    text-align: left;
    font-size: 11px;
    font-weight: 750;
    color: var(--color-ink);
    transition: background 0.12s;
    width: 100%;
  }
  .sb-note-row:hover { background: var(--color-workspace-panel); }
  .sb-note-row.selected { background: var(--color-soft-pink-surface); border-left-color: var(--color-dbs-red); font-weight: 900; }
  .sb-note-icon { font-size: 12px; flex: 0 0 auto; width: 16px; text-align: center; }
  .sb-note-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
  .sb-note-title { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 800; }
  .sb-note-meta { font-size: 9px; color: var(--color-muted); font-weight: 650; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  .sb-note-detail { overflow-y: auto; display: flex; flex-direction: column; gap: 8px; min-height: 0; }
  .sb-note-card {
    background: #fff;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    box-shadow: var(--shadow-subtle);
    padding: 14px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    flex: 0 0 auto;
  }
  .sb-note-card-head { display: flex; align-items: center; gap: 10px; }
  .sb-note-card-accent { width: 4px; min-width: 4px; height: 28px; border-radius: 2px; background: var(--color-dbs-red); }
  .sb-note-card-title { margin: 0; font-size: 14px; font-weight: 900; color: var(--color-ink); }
  .sb-note-card-path { margin: 2px 0 0; font-size: 10px; color: var(--color-muted); font-weight: 650; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .sb-note-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 0; }
  @media (max-width: 700px) { .sb-note-grid { grid-template-columns: 1fr; } }

  /* ── Notes CRUD ── */
  .sb-note-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 4px;
  }
  .sb-note-excerpt {
    margin-top: 8px;
    padding: 10px;
    background: var(--color-workspace-panel);
    border: 1px solid #E5E7EB;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 650;
    color: var(--color-muted);
    white-space: pre-wrap;
    word-break: break-word;
    line-height: 1.4;
  }
  .sb-edit-block {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-top: 8px;
  }
  .sb-edit-caveat {
    margin: 0;
    font-size: 10px;
    font-weight: 800;
    color: var(--color-dbs-red);
    line-height: 1.35;
  }
  .sb-edit-textarea {
    min-height: 160px;
    padding: 8px;
    border: 1px solid #D7DCE2;
    border-radius: 6px;
    font-family: inherit;
    font-size: 11px;
    font-weight: 650;
    color: var(--color-ink);
    resize: vertical;
    line-height: 1.4;
  }
  .sb-edit-textarea:focus { outline: none; border-color: var(--color-dbs-red); }
  .sb-edit-actions { display: flex; gap: 6px; }
  .sb-create-parent {
    flex: 1 1 100%;
    font-size: 10px;
    font-weight: 750;
    color: var(--color-muted);
    word-break: break-all;
  }
  .sb-create-content {
    flex: 1 1 100%;
    min-height: 80px;
    padding: 8px;
    border: 1px solid #D7DCE2;
    border-radius: 5px;
    font-family: inherit;
    font-size: 11px;
    font-weight: 650;
    color: var(--color-ink);
    resize: vertical;
    line-height: 1.4;
  }
  .sb-create-content:focus { outline: none; border-color: var(--color-dbs-red); }

  /* ── Link Bank Toolbar ── */
  .lb-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    flex: 0 0 auto;
    background: var(--color-workspace-panel);
    border: 1px solid #D7DCE2;
    border-radius: 8px;
    padding: 10px 12px;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.30);
  }
  .lb-toolbar-left {
    display: flex;
    align-items: center;
    gap: 7px;
  }
  .lb-toolbar-right {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  /* ── Link list ── */
  .lb-list {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding-right: 2px;
  }

  /* ── Link card ── */
  .lb-card {
    background: #fff;
    border: 1px solid #E5E7EB;
    border-left: 3px solid var(--color-dbs-red);
    border-radius: 8px;
    box-shadow: var(--shadow-subtle);
    padding: 10px 12px;
    display: flex;
    gap: 10px;
    align-items: flex-start;
    transition: box-shadow 0.15s ease;
  }
  .lb-card:hover {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  }
  .lb-card-accent {
    width: 3px;
    min-width: 3px;
    height: 16px;
    border-radius: 2px;
    background: var(--color-dbs-red);
    margin-top: 2px;
  }
  .lb-card-body {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  .lb-card-top {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }
  .lb-card-title {
    margin: 0;
    font-size: 12px;
    font-weight: 900;
  }
  .lb-link {
    color: var(--color-dbs-red);
    text-decoration: none;
  }
  .lb-link:hover { text-decoration: underline; }
  .lb-category-badge {
    display: inline-flex;
    align-items: center;
    height: 18px;
    padding: 0 7px;
    border-radius: 999px;
    background: var(--color-workspace-panel);
    border: 1px solid #D7DCE2;
    font-size: 9px;
    font-weight: 800;
    color: var(--color-muted);
  }
  .lb-card-url {
    margin: 0;
    font-size: 10px;
    color: var(--color-muted);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-weight: 750;
  }
  .lb-card-notes {
    margin: 0;
    font-size: 10px;
    font-weight: 700;
    color: var(--color-muted-light);
    line-height: 1.35;
  }

  /* ── Add link button + form ── */
  .lb-add-btn {
    height: 28px;
    padding: 0 12px;
    border-radius: 5px;
    background: var(--color-dbs-red);
    color: #fff;
    border: 0;
    font-size: 11px;
    font-weight: 850;
    cursor: pointer;
    transition: opacity 0.15s ease;
  }
  .lb-add-btn:hover { opacity: 0.88; }

  .lb-add-form {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    flex: 0 0 auto;
    background: #fff;
    border: 1px solid #D7DCE2;
    border-radius: 8px;
    padding: 10px 12px;
    box-shadow: var(--shadow-subtle);
  }
  .lb-edit-form {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
  }
  .lb-form-input {
    height: 26px;
    padding: 0 8px;
    border: 1px solid #D7DCE2;
    border-radius: 5px;
    font-size: 11px;
    font-weight: 700;
    color: var(--color-ink);
    flex: 1 1 140px;
    min-width: 0;
  }
  .lb-form-input:focus {
    outline: none;
    border-color: var(--color-dbs-red);
  }
  .lb-form-submit {
    height: 26px;
    padding: 0 12px;
    border-radius: 5px;
    background: var(--color-dbs-red);
    color: #fff;
    border: 0;
    font-size: 11px;
    font-weight: 850;
    cursor: pointer;
  }
  .lb-form-submit:hover { opacity: 0.88; }
  .lb-form-cancel {
    height: 26px;
    padding: 0 12px;
    border-radius: 5px;
    background: transparent;
    color: var(--color-muted);
    border: 1px solid #D7DCE2;
    font-size: 11px;
    font-weight: 800;
    cursor: pointer;
  }
  .lb-form-cancel:hover { background: var(--color-workspace-panel); }
  .lb-form-error {
    flex: 1 1 100%;
    font-size: 10px;
    font-weight: 800;
    color: var(--color-dbs-red);
  }

  /* ── Archived toggle / badge ── */
  .lb-archived-toggle {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 10px;
    font-weight: 800;
    color: var(--color-muted);
    cursor: pointer;
    white-space: nowrap;
  }
  .lb-archived-badge {
    display: inline-flex;
    align-items: center;
    height: 18px;
    padding: 0 7px;
    border-radius: 999px;
    background: #F1F3F5;
    border: 1px solid #D7DCE2;
    font-size: 9px;
    font-weight: 800;
    color: var(--color-muted-light);
  }
  .lb-card-archived { opacity: 0.6; }

  /* ── Card actions ── */
  .lb-card-actions {
    display: flex;
    gap: 6px;
    margin-top: 4px;
  }
  .lb-edit-actions {
    display: flex;
    gap: 6px;
  }
  .lb-action-btn {
    height: 22px;
    padding: 0 10px;
    border-radius: 4px;
    background: transparent;
    color: var(--color-muted);
    border: 1px solid #D7DCE2;
    font-size: 10px;
    font-weight: 800;
    cursor: pointer;
    transition: background 0.12s ease, color 0.12s ease;
  }
  .lb-action-btn:hover {
    background: var(--color-soft-pink-surface);
    color: var(--color-dbs-red);
    border-color: var(--color-dbs-red);
  }
  .lb-action-archive:hover {
    background: var(--color-soft-pink-surface);
  }

  /* ── Inline error banner ── */
  .lb-inline-error {
    flex: 0 0 auto;
    padding: 8px 12px;
    border-radius: 6px;
    background: var(--color-soft-pink-surface);
    border: 1px solid var(--color-dbs-red);
    font-size: 11px;
    font-weight: 800;
    color: var(--color-dbs-red);
  }
</style>
