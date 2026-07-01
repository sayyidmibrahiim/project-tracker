<script lang="ts">
  import { onMount } from "svelte";
  import { callBridge, isPywebviewReady } from "../bridge";
  import type { SecondBrainItem } from "../types";
  import { BridgeErrorCode } from "../types";
  import ConfirmModal from "./ConfirmModal.svelte";
  import { addToast } from "../stores/toastStore";

  type TabId = "notes" | "linkbank";
  let activeTab: TabId = $state("linkbank");

  interface LinkItem { id: string; name: string; url: string; notes: string; details?: string; tags?: string; category: string; archived: string; pinned?: string; favorite?: string; }
  interface LinkBankData { categories: string[]; links: LinkItem[]; }

  type LoadState = "idle" | "loading" | "error" | "loaded";
  let loadState: LoadState = $state("idle");
  let errorCode: string = $state("");
  let errorMessage: string = $state("");
  let bank: LinkBankData = $state({ categories: [], links: [] });
  let searchQuery: string = $state("");
  let categoryFilter: string = $state("all");
  let showArchived: boolean = $state(false);
  let addFormOpen: boolean = $state(false);
  let addName: string = $state("");
  let addUrl: string = $state("");
  let addCategory: string = $state("");
  let addNotes: string = $state("");
  let addError: string = $state("");
  let editingId: string | null = $state(null);
  let editName: string = $state("");
  let editUrl: string = $state("");
  let editCategory: string = $state("");
  let editNotes: string = $state("");
  let editTags: string = $state("");
  let editError: string = $state("");
  let actionError: string = $state("");
  let selectedLinkId: string = $state("");
  let newCategoryName: string = $state("");
  let renameCategoryFrom: string = $state("");
  let renameCategoryTo: string = $state("");
  let bankActionError: string = $state("");
  let importing: boolean = $state(false);
  let fileInputEl: HTMLInputElement | null = $state(null);

  let filteredLinks: LinkItem[] = $derived.by(() => {
    let result = bank.links;
    if (!showArchived) result = result.filter((l) => l.archived !== "true");
    if (categoryFilter !== "all") result = result.filter((l) => l.category === categoryFilter);
    const q = searchQuery.trim().toLowerCase();
    if (q) result = result.filter((l) => `${l.name} ${l.url} ${l.notes} ${l.details ?? ""} ${l.tags ?? ""} ${l.category}`.toLowerCase().includes(q));
    return result;
  });
  let selectedLink: LinkItem | null = $derived(filteredLinks.find((l) => l.id === selectedLinkId) ?? filteredLinks[0] ?? null);

  async function loadLinkBank() {
    loadState = "loading"; errorCode = ""; errorMessage = ""; actionError = "";
    if (!isPywebviewReady()) { errorCode = BridgeErrorCode.BRIDGE_UNAVAILABLE; errorMessage = "pywebview bridge is not available. Running outside desktop shell."; loadState = "error"; return; }
    const response = await callBridge<LinkBankData>("linkbank_get");
    if (!response.ok) { errorCode = response.error.code; errorMessage = response.error.message; loadState = "error"; return; }
    bank = response.data ?? { categories: [], links: [] };
    loadState = "loaded";
  }

  async function handleAddLink() {
    addError = "";
    if (!isPywebviewReady()) return;
    const response = await callBridge<LinkItem>("linkbank_add_link", { name: addName.trim(), url: addUrl.trim(), category: addCategory.trim(), details: addNotes.trim(), notes: addNotes.trim() });
    if (!response.ok) { addError = response.error.message; return; }
    addName = ""; addUrl = ""; addCategory = ""; addNotes = ""; addFormOpen = false;
    selectedLinkId = response.data?.id ?? "";
    await loadLinkBank();
  }
  function startEdit(link: LinkItem) { editingId = link.id; editName = link.name; editUrl = link.url; editCategory = link.category; editNotes = link.details ?? link.notes; editTags = link.tags ?? ""; editError = ""; }
  function cancelEdit() { editingId = null; editError = ""; }
  async function handleSaveEdit() {
    editError = "";
    if (!isPywebviewReady() || !editingId) return;
    const response = await callBridge<LinkItem>("linkbank_update", { id: editingId, name: editName.trim(), url: editUrl.trim(), category: editCategory.trim(), details: editNotes.trim(), notes: editNotes.trim(), tags: editTags.trim() });
    if (!response.ok) { editError = response.error.message; return; }
    editingId = null;
    await loadLinkBank();
  }
  async function handleArchive(linkId: string) {
    actionError = "";
    if (!isPywebviewReady()) return;
    const response = await callBridge<LinkItem>("linkbank_archive_link", linkId);
    if (!response.ok) { actionError = response.error.message; return; }
    await loadLinkBank();
  }
  async function createCategory() {
    actionError = "";
    const name = newCategoryName.trim();
    if (!name || !isPywebviewReady()) return;
    const response = await callBridge<LinkBankData>("linkbank_category_create", name);
    if (!response.ok) { actionError = response.error.message; return; }
    newCategoryName = ""; categoryFilter = name; await loadLinkBank();
  }
  async function archiveCurrentCategory() {
    actionError = "";
    if (categoryFilter === "all" || !isPywebviewReady()) return;
    const response = await callBridge<LinkBankData>("linkbank_category_archive", categoryFilter);
    if (!response.ok) { actionError = response.error.message; return; }
    categoryFilter = "all"; await loadLinkBank();
  }
  async function toggleLinkFlag(link: LinkItem, flag: "pinned" | "favorite") {
    const next = link[flag] === "true" ? "false" : "true";
    const response = await callBridge<LinkItem>("linkbank_update", { id: link.id, [flag]: next });
    if (!response.ok) { actionError = response.error.message; return; }
    await loadLinkBank();
  }

  async function handleRestoreLink(link: LinkItem) {
    bankActionError = "";
    if (!isPywebviewReady()) return;
    const response = await callBridge<LinkItem>("linkbank_update", { id: link.id, archived: "false" });
    if (!response.ok) { bankActionError = response.error.message; return; }
    await loadLinkBank();
  }
  async function handleRenameCategory(oldName: string, newName: string) {
    bankActionError = "";
    if (!isPywebviewReady() || !oldName || !newName.trim()) return;
    const response = await callBridge<unknown>("linkbank_category_rename", oldName, newName.trim());
    if (!response.ok) { bankActionError = response.error.message; return; }
    renameCategoryFrom = ""; renameCategoryTo = ""; categoryFilter = newName.trim();
    await loadLinkBank();
  }
  async function handleExportBank() {
    bankActionError = "";
    if (!isPywebviewReady()) return;
    const response = await callBridge<unknown>("linkbank_export");
    if (!response.ok) { bankActionError = response.error.message; return; }
    const data = JSON.stringify(response.data ?? {}, null, 2);
    const suggested = `link_bank_${new Date().toISOString().slice(0, 10)}.json`;
    const saveResp = await callBridge<{ written: boolean; path: string | null }>("util_save_file", suggested, data);
    if (saveResp.ok && saveResp.data?.written && saveResp.data.path) {
      addToast(`Link bank exported: ${saveResp.data.path}`, "success", 4000);
    } else {
      const blob = new Blob([data], { type: "application/json;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url; anchor.download = suggested; anchor.click();
      URL.revokeObjectURL(url);
      addToast("Link bank exported via browser", "success", 4000);
    }
  }
  function triggerImport() { bankActionError = ""; fileInputEl?.click(); }
  async function handleImportFile(event: Event) {
    bankActionError = "";
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = "";
    if (!file) return;
    try {
      const text = await file.text();
      const parsed = JSON.parse(text);
      importing = true;
      const response = await callBridge<unknown>("linkbank_import", parsed);
      importing = false;
      if (!response.ok) { bankActionError = response.error.message; return; }
      await loadLinkBank();
    } catch (err) {
      importing = false;
      bankActionError = err instanceof Error ? err.message : "Invalid link bank file.";
    }
  }
  async function copyLinkUrl(link: LinkItem) {
    try { await navigator.clipboard?.writeText(link.url); actionError = "Copied URL."; }
    catch { actionError = "Copy failed. Select and copy the URL manually."; }
  }

  type NotesLoadState = "idle" | "loading" | "error" | "loaded";
  let notesLoadState: NotesLoadState = $state("idle");
  let notesErrorCode: string = $state("");
  let notesErrorMessage: string = $state("");
  let notesItems: SecondBrainItem[] = $state([]);
  let notesSearch: string = $state("");
  let notesSort: "updated" | "az" | "type" = $state("updated");
  let notesTypeFilter: "all" | "md" | "txt" = $state("all");
  let notesDateFilter: string = $state("");
  let selectedItem: SecondBrainItem | null = $state(null);
  let secondBrainRoot: string = $state("");
  let notesActionError: string = $state("");
  let createOpen: boolean = $state(false);
  let createKind: "file" | "folder" = $state("file");
  let createFilename: string = $state("");
  let createContent: string = $state("");
  let createError: string = $state("");
  let editingNotePath: string | null = $state(null);
  let editContent: string = $state("");
  let editNoteError: string = $state("");
  let noteEditorEl: HTMLTextAreaElement | null = $state(null);
  let deleteTarget: SecondBrainItem | null = $state(null);

  let filteredNotes: SecondBrainItem[] = $derived.by(() => {
    const q = notesSearch.trim().toLowerCase();
    let rows = notesItems;
    if (q) rows = rows.filter((n) => n.title.toLowerCase().includes(q) || n.path.toLowerCase().includes(q) || (n.excerpt ?? "").toLowerCase().includes(q));
    if (notesTypeFilter !== "all") {
      rows = rows.filter((n) => n.path.toLowerCase().endsWith(`.${notesTypeFilter}`));
    }
    if (notesDateFilter) {
      rows = rows.filter((n) => (n.updated_at ?? "").slice(0, 10) === notesDateFilter);
    }
    const sorted = [...rows];
    if (notesSort === "az") sorted.sort((a, b) => a.title.localeCompare(b.title));
    else if (notesSort === "type") sorted.sort((a, b) => a.item_type.localeCompare(b.item_type) || a.title.localeCompare(b.title));
    else sorted.sort((a, b) => (b.updated_at ?? "").localeCompare(a.updated_at ?? ""));
    return sorted;
  });
  let pinnedNotes: SecondBrainItem[] = $derived(filteredNotes.filter((n) => n.pinned));
  let favoriteNotes: SecondBrainItem[] = $derived(filteredNotes.filter((n) => n.favorite && !n.pinned));
  let regularNotes: SecondBrainItem[] = $derived(filteredNotes.filter((n) => !n.pinned && !n.favorite));

  async function loadNotes() {
    notesLoadState = "loading"; notesErrorCode = ""; notesErrorMessage = ""; notesActionError = ""; selectedItem = null; editingNotePath = null;
    if (!isPywebviewReady()) { notesErrorCode = BridgeErrorCode.BRIDGE_UNAVAILABLE; notesErrorMessage = "pywebview bridge unavailable."; notesLoadState = "error"; return; }
    const settingsResp = await callBridge<{ second_brain_folder?: string }>("settings_get");
    secondBrainRoot = settingsResp.ok ? (settingsResp.data?.second_brain_folder ?? "") : "";
    const resp = await callBridge<SecondBrainItem[]>("second_brain_list");
    if (!resp.ok) { notesErrorCode = resp.error.code; notesErrorMessage = resp.error.message; notesLoadState = "error"; return; }
    notesItems = resp.data ?? [];
    notesLoadState = "loaded";
  }
  async function searchNotes(query: string) {
    notesSearch = query;
    if (!query.trim()) { loadNotes(); return; }
    if (!isPywebviewReady()) return;
    notesLoadState = "loading"; selectedItem = null;
    const resp = await callBridge<SecondBrainItem[]>("second_brain_search", query);
    if (!resp.ok) { notesErrorCode = resp.error.code; notesErrorMessage = resp.error.message; notesLoadState = "error"; return; }
    notesItems = resp.data ?? [];
    notesLoadState = "loaded";
  }
  async function selectNoteItem(itemId: string) {
    if (!isPywebviewReady()) return;
    const resp = await callBridge<SecondBrainItem>("second_brain_get", itemId);
    selectedItem = resp.ok ? (resp.data ?? null) : null;
    if (!selectedItem || editingNotePath !== selectedItem.path) { editingNotePath = null; editNoteError = ""; }
  }
  function openCreate(kind: "file" | "folder") { createKind = kind; createOpen = true; createFilename = ""; createContent = ""; createError = ""; }
  function closeCreate() { createOpen = false; createFilename = ""; createContent = ""; createError = ""; }
  async function handleCreateItem() {
    createError = "";
    if (!isPywebviewReady()) return;
    if (!secondBrainRoot) { createError = "No Second Brain folder configured. Set one in Settings first."; return; }
    const filename = createFilename.trim();
    if (!filename) { createError = createKind === "folder" ? "Folder name is required." : "Filename is required."; return; }
    const resp = createKind === "folder"
      ? await callBridge<string>("second_brain_folder_create", secondBrainRoot, filename)
      : await callBridge<string>("second_brain_file_create", secondBrainRoot, filename, createContent);
    if (!resp.ok) { createError = resp.error.message; return; }
    closeCreate();
    await loadNotes();
  }
  function startEditNote() { if (!selectedItem) return; editingNotePath = selectedItem.path; editContent = selectedItem.excerpt ?? ""; editNoteError = ""; }
  function cancelEditNote() { editingNotePath = null; editNoteError = ""; }
  async function handleSaveNote() {
    editNoteError = "";
    if (!isPywebviewReady() || !editingNotePath) return;
    const resp = await callBridge<SecondBrainItem>("second_brain_note_write", editingNotePath, editContent);
    if (!resp.ok) { editNoteError = resp.error.message; return; }
    editingNotePath = null;
    await loadNotes();
  }
  function insertMarkdown(before: string, after = "", fallback = "text") {
    if (!noteEditorEl) return;
    const start = noteEditorEl.selectionStart ?? editContent.length;
    const end = noteEditorEl.selectionEnd ?? start;
    const selected = editContent.slice(start, end) || fallback;
    editContent = `${editContent.slice(0, start)}${before}${selected}${after}${editContent.slice(end)}`;
    queueMicrotask(() => {
      noteEditorEl?.focus();
      const pos = start + before.length + selected.length;
      noteEditorEl?.setSelectionRange(pos, pos);
    });
  }
  function requestDeleteNote(item: SecondBrainItem) { notesActionError = ""; deleteTarget = item; }
  function cancelDeleteNote() { deleteTarget = null; }
  async function confirmDeleteNote() {
    const target = deleteTarget; deleteTarget = null;
    if (!target || !isPywebviewReady()) return;
    const resp = await callBridge("second_brain_note_delete", target.path);
    if (!resp.ok) { notesActionError = resp.error.message; return; }
    await loadNotes();
  }
  async function refreshNotesList() { if (!isPywebviewReady()) return; const resp = await callBridge<SecondBrainItem[]>("second_brain_list"); if (resp.ok) notesItems = resp.data ?? []; }
  async function handleTogglePin(itemId: string) { notesActionError = ""; if (!isPywebviewReady()) return; const resp = await callBridge<SecondBrainItem>("second_brain_pin", itemId); if (!resp.ok) { notesActionError = resp.error.message; return; } if (resp.data && selectedItem?.id === itemId) selectedItem = resp.data; await refreshNotesList(); }
  async function handleToggleFavorite(itemId: string) { notesActionError = ""; if (!isPywebviewReady()) return; const resp = await callBridge<SecondBrainItem>("second_brain_favorite", itemId); if (!resp.ok) { notesActionError = resp.error.message; return; } if (resp.data && selectedItem?.id === itemId) selectedItem = resp.data; await refreshNotesList(); }

  onMount(() => { if (activeTab === "linkbank") loadLinkBank(); else loadNotes(); });
  function onTabSwitch(tab: TabId) { activeTab = tab; if (tab === "linkbank" && loadState === "idle") loadLinkBank(); if (tab === "notes" && notesLoadState === "idle") loadNotes(); }
  export function refresh() { if (activeTab === "linkbank") loadLinkBank(); else loadNotes(); }
</script>

<section class="screen active" id="screen-secondbrain">
  <div class="page-header">
    <div class="page-header-left">
      <span class="page-header-icon"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg></span>
      <h2 class="page-header-title">Second Brain</h2>
    </div>
    <div class="page-header-actions">
      <div class="tab-buttons"><button class="status-tab" class:active={activeTab === "notes"} onclick={() => onTabSwitch("notes")}>Notes</button><button class="status-tab" class:active={activeTab === "linkbank"} onclick={() => onTabSwitch("linkbank")}>Link Bank</button></div>
    </div>
  </div>

  {#if activeTab === "notes"}
    <div class="page-stack">
      <div class="toolbar"><div class="search-shell"><span class="search-icon">⌕</span><input class="input" placeholder="Search notes…" value={notesSearch} oninput={(e) => searchNotes((e.target as HTMLInputElement).value)} /></div><input class="input small" type="date" bind:value={notesDateFilter} title="Filter by updated date" /><select class="combo" bind:value={notesSort} title="Sort"><option value="updated">Sort: Newest</option><option value="az">Sort: A-Z</option><option value="type">Sort: Type</option></select><select class="combo" bind:value={notesTypeFilter} title="Type filter"><option value="all">All types</option><option value="md">.md</option><option value="txt">.txt</option></select><button class="btn-secondary" onclick={() => { notesSearch=""; notesDateFilter=""; notesTypeFilter="all"; searchNotes(""); }}>Clear</button><button class="btn-secondary" onclick={() => openCreate("folder")}>Add Folder</button><button class="btn-primary" onclick={() => createOpen ? closeCreate() : openCreate("file")}>{createOpen ? "Cancel" : "Add File"}</button></div>
      {#if createOpen}<div class="panel-card accent"><div class="form-grid"><input class="input" placeholder={createKind === "folder" ? "Folder name *" : "Filename (e.g. idea.md, script.py, query.sql) *"} bind:value={createFilename} />{#if createKind === "file"}<textarea class="textarea" placeholder="Initial file content" bind:value={createContent}></textarea>{/if}<button class="btn-primary" onclick={handleCreateItem}>Create {createKind === "folder" ? "Folder" : "File"}</button>{#if createError}<span class="error-text">{createError}</span>{/if}</div></div>{/if}
      {#if notesActionError}<div class="dashboard-banner banner-error"><span>{notesActionError}</span></div>{/if}
      {#if notesLoadState === "loading"}<div class="dashboard-banner banner-loading"><span class="banner-icon">◌</span><span>Loading notes…</span></div>{:else if notesLoadState === "error"}<div class="dashboard-banner banner-error"><span class="banner-icon">⚠</span><div><p class="banner-title">Notes unavailable</p><p class="banner-detail">{notesErrorCode}: {notesErrorMessage}</p></div></div>{:else}
        <div class="splitter"><div class="pane tree-pane"><div class="panel-card accent"><div class="panel-title-row"><span class="panel-title-icon">▤</span><span class="panel-title">Second Brain Tree</span><span class="panel-subtitle">{filteredNotes.length} items</span></div><div class="tree"><strong>Pinned</strong>{#each pinnedNotes as item}<button class="tree-row" class:selected={selectedItem?.id === item.id} onclick={() => selectNoteItem(item.id)}>◆ {item.title}</button>{/each}<strong>Favorites</strong>{#each favoriteNotes as item}<button class="tree-row" class:selected={selectedItem?.id === item.id} onclick={() => selectNoteItem(item.id)}>★ {item.title}</button>{/each}<strong>Second Brain Notes</strong>{#each regularNotes as item}<button class="tree-row" class:selected={selectedItem?.id === item.id} onclick={() => selectNoteItem(item.id)}>▸ {item.title}</button>{/each}<strong>Project Documents</strong><span class="tree-empty">Indexed from configured folders</span></div></div></div><div class="split-handle"></div><div class="pane"><div class="panel-card accent editor-card"><div class="panel-title-row"><span class="panel-title-icon">✎</span><span class="panel-title">Notes</span><span class="panel-subtitle">markdown workspace</span></div>{#if !selectedItem}<div class="table-empty">Select a note</div>{:else}<input class="input" value={selectedItem.title} readonly /><input class="input" value={selectedItem.path} readonly /><div class="toolbar compact"><button class="btn-tiny" onclick={startEditNote}>Edit</button><button class="btn-tiny" onclick={cancelEditNote}>Preview</button><button class="btn-tiny" onclick={() => insertMarkdown("**", "**", "bold text")}>B</button><button class="btn-tiny" onclick={() => insertMarkdown("*", "*", "italic text")}><em>I</em></button><button class="btn-tiny" onclick={() => insertMarkdown("# ", "", "Heading")}>H1</button><button class="btn-tiny" onclick={() => insertMarkdown("## ", "", "Heading")}>H2</button><button class="btn-tiny" onclick={() => insertMarkdown("`", "`", "code")}>Code</button><button class="btn-tiny" onclick={() => insertMarkdown("> ", "", "quote")}>Quote</button><button class="btn-tiny" onclick={() => insertMarkdown("[", "](https://example.local/)", "link text")}>Link</button></div>{#if editingNotePath === selectedItem.path}<textarea class="textarea note-editor" bind:this={noteEditorEl} bind:value={editContent}></textarea><div class="toolbar"><button class="btn-primary" onclick={handleSaveNote}>Save</button><button class="btn-secondary" onclick={cancelEditNote}>Cancel</button></div>{#if editNoteError}<span class="error-text">{editNoteError}</span>{/if}{:else}<div class="preview-box">{selectedItem.excerpt || "No preview."}</div><div class="toolbar"><button class="btn-secondary" onclick={() => handleTogglePin(selectedItem!.id)}>{selectedItem.pinned ? "Unpin" : "Pin"}</button><button class="btn-secondary" onclick={() => handleToggleFavorite(selectedItem!.id)}>{selectedItem.favorite ? "Unfavorite" : "Favorite"}</button>{#if selectedItem.item_type === "note"}<button class="btn-primary" onclick={startEditNote}>Edit</button>{/if}<button class="btn-danger" onclick={() => requestDeleteNote(selectedItem!)}>Delete</button></div>{/if}{/if}</div><div class="split mini-split"><div class="panel-card"><div class="panel-title-row"><span class="panel-title">Backlinks</span></div><div class="table-empty">No backlinks indexed.</div></div><div class="panel-card"><div class="panel-title-row"><span class="panel-title">Recent Activity</span></div><div class="table-empty">No recent activity.</div></div></div></div></div>
      {/if}
    </div>
    {#if deleteTarget}<ConfirmModal title="Delete Second Brain note" actionLabel="Delete note" targetName={deleteTarget.path} reversible={false} onConfirm={confirmDeleteNote} onCancel={cancelDeleteNote} />{/if}
  {:else}
    {#if loadState === "loading"}<div class="dashboard-banner banner-loading"><span class="banner-icon">◌</span><span>Loading link bank…</span></div>{:else if loadState === "error"}<div class="dashboard-banner banner-error"><span class="banner-icon">⚠</span><div><p class="banner-title">Link Bank unavailable</p><p class="banner-detail">{errorCode}: {errorMessage}</p></div></div>{:else}
      <div class="category-grid link-bank-grid"><div class="panel-card accent"><div class="panel-title-row"><span class="panel-title-icon">▤</span><span class="panel-title">Link Categories</span><span class="panel-subtitle">{bank.categories.length} groups</span></div><div class="toolbar vertical-tools"><select class="combo" bind:value={categoryFilter}><option value="all">All Categories</option>{#each bank.categories as cat}<option value={cat}>{cat}</option>{/each}</select><div class="field-row"><input class="input" placeholder="New category…" bind:value={newCategoryName} /><button class="btn-secondary" onclick={createCategory}>Add</button></div>{#if categoryFilter !== "all"}<div class="field-row"><input class="input" placeholder="Rename category to…" bind:value={renameCategoryTo} /><button class="btn-secondary" onclick={() => handleRenameCategory(categoryFilter, renameCategoryTo)} disabled={!renameCategoryTo.trim()}>Rename</button></div>{/if}<button class="btn-secondary" onclick={archiveCurrentCategory} disabled={categoryFilter === "all"}>Archive Category</button><div class="search-shell"><span class="search-icon">⌕</span><input class="input" placeholder="Search title, link, tags, details…" bind:value={searchQuery} /></div><label class="check-row"><input type="checkbox" bind:checked={showArchived} /> Show archived</label><div class="field-row"><button class="btn-secondary" onclick={handleExportBank}>Export JSON</button><button class="btn-secondary" onclick={triggerImport} disabled={importing}>{importing ? "Importing…" : "Import JSON"}</button></div>{#if bankActionError}<span class="error-text">{bankActionError}</span>{/if}<button class="btn-primary" onclick={() => { addFormOpen = !addFormOpen; addError = ""; }}>{addFormOpen ? "Cancel" : "+ Add Link"}</button><input type="file" accept=".json,application/json" bind:this={fileInputEl} onchange={handleImportFile} style="display:none" /></div><div class="list-box">{#each filteredLinks as link}<button class="link-row" class:active={selectedLink?.id === link.id} onclick={() => selectedLinkId = link.id}><strong>{link.name}</strong><span>{link.category || "Uncategorized"}{link.pinned === "true" ? " · pinned" : ""}{link.favorite === "true" ? " · favorite" : ""}{link.archived === "true" ? " · archived" : ""}</span></button>{:else}<div class="table-empty">No links found.</div>{/each}</div></div><div class="split-handle"></div><div class="panel-card accent"><div class="panel-title-row"><span class="panel-title-icon">◆</span><span class="panel-title">Add/Edit Link</span><span class="panel-subtitle">category-first link workspace</span></div>{#if actionError}<div class="dashboard-banner banner-error"><span>{actionError}</span></div>{/if}{#if addFormOpen}<div class="form-grid"><input class="input" placeholder="Title *" bind:value={addName} /><input class="input" placeholder="URL (https://...) *" bind:value={addUrl} /><input class="input" placeholder="Category" bind:value={addCategory} /><textarea class="textarea" placeholder="Description / details" bind:value={addNotes}></textarea><button class="btn-primary" onclick={handleAddLink}>Save Link</button>{#if addError}<span class="error-text">{addError}</span>{/if}</div>{:else if selectedLink}{#if editingId === selectedLink.id}<div class="form-grid"><input class="input" bind:value={editName} /><input class="input" bind:value={editUrl} /><input class="input" bind:value={editCategory} /><input class="input" placeholder="Tags, comma separated" bind:value={editTags} /><textarea class="textarea" bind:value={editNotes}></textarea><button class="btn-primary" onclick={handleSaveEdit}>Save</button><button class="btn-secondary" onclick={cancelEdit}>Cancel</button>{#if editError}<span class="error-text">{editError}</span>{/if}</div>{:else}<div class="link-detail"><h3>{selectedLink.name}</h3><a href={selectedLink.url} target="_blank" rel="noopener">{selectedLink.url}</a><p>{selectedLink.details || selectedLink.notes || "No details."}</p><span>{selectedLink.category || "Uncategorized"}</span>{#if selectedLink.tags}<div class="badge-row">{#each selectedLink.tags.split(",").filter(Boolean) as tag}<span class="badge">{tag.trim()}</span>{/each}</div>{/if}<div class="toolbar"><button class="btn-primary" onclick={() => startEdit(selectedLink!)}>Edit</button><button class="btn-secondary" onclick={() => copyLinkUrl(selectedLink!)}>Copy URL</button><button class="btn-secondary" onclick={() => toggleLinkFlag(selectedLink!, "pinned")}>{selectedLink.pinned === "true" ? "Unpin" : "Pin"}</button><button class="btn-secondary" onclick={() => toggleLinkFlag(selectedLink!, "favorite")}>{selectedLink.favorite === "true" ? "Unfavorite" : "Favorite"}</button>{#if selectedLink.archived !== "true"}<button class="btn-secondary" onclick={() => handleArchive(selectedLink!.id)}>Archive</button>{:else}<button class="btn-secondary" onclick={() => handleRestoreLink(selectedLink!)}>Restore</button>{/if}</div></div>{/if}{:else}<div class="table-empty">Select or add a link.</div>{/if}</div></div>
    {/if}
  {/if}
</section>

<style>
  .tab-buttons, .toolbar { display:flex; align-items:center; gap:6px; flex-wrap:wrap; }
  .small { width:130px; }
  .tree-pane { flex:0 0 290px; }
  .tree { display:flex; flex-direction:column; gap:4px; font-size:10px; }
  .tree strong { margin-top:6px; color:var(--primary-red); text-transform:uppercase; letter-spacing:.25px; }
  .tree-row { text-align:left; border:0; background:transparent; border-radius:4px; padding:5px 6px; font-size:11px; font-weight:750; cursor:pointer; color:var(--color-ink); }
  .tree-row:hover, .tree-row.selected { background:var(--soft-red-surface); color:var(--primary-red); }
  .tree-empty { color:var(--color-muted); padding:4px 6px; }
  .editor-card { min-height:360px; }
  .compact { margin:6px 0; }
  .note-editor { min-height:190px; }
  .preview-box { min-height:190px; border:1px solid var(--border-soft); background:#fff; border-radius:6px; padding:10px; white-space:pre-wrap; color:var(--color-muted); }
  .mini-split { margin-top:8px; }
  .link-bank-grid { flex:1; min-height:0; }
  .vertical-tools { align-items:stretch; flex-direction:column; }
  .field-row { display:flex; gap:6px; align-items:center; }
  .field-row .input { flex:1; min-width:0; }
  .check-row { display:flex; gap:6px; align-items:center; font-size:10px; font-weight:800; color:var(--color-muted); }
  .link-row { display:flex; flex-direction:column; gap:2px; width:100%; border:0; border-bottom:1px solid var(--border-soft); background:transparent; padding:8px 10px; text-align:left; cursor:pointer; }
  .link-row:hover, .link-row.active { background:var(--soft-red-surface); }
  .link-row strong { color:var(--color-ink); font-size:11px; }
  .link-row span { color:var(--color-muted); font-size:10px; }
  .link-detail h3 { margin:0 0 6px; font-size:14px; }
  .link-detail a { color:var(--primary-red); font-weight:800; word-break:break-all; }
  .link-detail p { color:var(--color-muted); line-height:1.4; }
  .error-text { color:var(--primary-red); font-weight:800; font-size:10px; }
</style>
