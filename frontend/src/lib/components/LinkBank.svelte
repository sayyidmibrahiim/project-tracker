<script lang="ts">
  /**
   * Second Brain — Link Bank workspace (Task 9).
   *
   * Category rail (All / Pinned / Favorites / active categories / Archived /
   * archived categories) + compact link list + selected-link/add/edit detail
   * pane. Archive/restore (link and category) are confirmation-gated through
   * ConfirmModal; nothing is ever hard-removed. Links open exclusively through
   * the `linkbank_open` bridge (never raw anchor navigation). Import always
   * previews before merge; export goes through the native `util_save_file` dialog.
   * See _docs/specs/superpowers/specs/2026-07-12-second-brain-completion-design.md
   * §6.3 / §15 / §16.
   */
  import { onMount } from "svelte";
  import { callBridge, isPywebviewReady, waitForPywebviewReady } from "../bridge";
  import type {
    LinkBankData,
    LinkExportPayload,
    LinkImportPreview,
    LinkImportResult,
    LinkItem,
  } from "../types";
  import ConfirmModal from "./ConfirmModal.svelte";
  import { addToast } from "../stores/toastStore";

  type LoadState = "idle" | "loading" | "error" | "loaded";
  type DetailMode = "view" | "add" | "edit";
  type SortMode = "newest" | "oldest" | "az" | "favorite" | "pinned";
  type PendingAction =
    | { kind: "archive-link"; link: LinkItem }
    | { kind: "restore-link"; link: LinkItem }
    | { kind: "archive-category"; name: string }
    | { kind: "restore-category"; name: string };

  const EMPTY_BANK: LinkBankData = { categories: [], archived_categories: [], links: [] };

  // ── Workspace state ──
  let loadState: LoadState = $state("idle");
  let errorMessage: string = $state("");
  let bank: LinkBankData = $state(EMPTY_BANK);

  // ── Category rail + filters ──
  let categoryFilter: string = $state("all");
  let searchQuery: string = $state("");
  let dateFilter: string = $state("");
  let sortMode: SortMode = $state("newest");
  let newCategoryName: string = $state("");
  let renamingCategory: boolean = $state(false);
  let renameCategoryValue: string = $state("");

  // ── Selection + detail pane ──
  let selectedLinkId: string = $state("");
  let detailMode: DetailMode = $state("view");
  let formName: string = $state("");
  let formUrl: string = $state("");
  let formCategory: string = $state("");
  let formTags: string = $state("");
  let formDetails: string = $state("");
  let formError: string = $state("");
  let saving: boolean = $state(false);

  // ── Confirmation gate (archive/restore link/category) ──
  let pendingAction: PendingAction | null = $state(null);
  let actionBusy: boolean = $state(false);

  // ── Import/export ──
  let fileInputEl: HTMLInputElement | null = $state(null);
  let importPreview: LinkImportPreview | null = $state(null);
  let pendingImportPayload: { format: "json" | "csv"; content: string } | null = $state(null);
  let importBusy: boolean = $state(false);
  let exporting: boolean = $state(false);

  // ── Derived views ──
  const activeCategories = $derived.by(() => bank.categories);
  const archivedCategories = $derived.by(() => bank.archived_categories);
  const allCategoryNames = $derived.by(() => [...bank.categories, ...bank.archived_categories]);
  const isArchivedCategory = $derived.by(() => bank.archived_categories.includes(categoryFilter));
  const isCategoryRow = $derived.by(
    () => categoryFilter !== "all" && categoryFilter !== "pinned" && categoryFilter !== "favorites" && categoryFilter !== "archived",
  );

  const allCount = $derived.by(() => bank.links.filter((l) => l.archived !== "true").length);
  const pinnedCount = $derived.by(() => bank.links.filter((l) => l.archived !== "true" && l.pinned === "true").length);
  const favoriteCount = $derived.by(() => bank.links.filter((l) => l.archived !== "true" && l.favorite === "true").length);
  const archivedCount = $derived.by(() => bank.links.filter((l) => l.archived === "true").length);

  function countActive(cat: string): number {
    return bank.links.filter((l) => l.category === cat && l.archived !== "true").length;
  }
  function countArchived(cat: string): number {
    return bank.links.filter((l) => l.category === cat && l.archived === "true").length;
  }

  const filteredLinks = $derived.by<LinkItem[]>(() => {
    let rows = bank.links;
    if (categoryFilter === "all") rows = rows.filter((l) => l.archived !== "true");
    else if (categoryFilter === "pinned") rows = rows.filter((l) => l.archived !== "true" && l.pinned === "true");
    else if (categoryFilter === "favorites") rows = rows.filter((l) => l.archived !== "true" && l.favorite === "true");
    else if (categoryFilter === "archived") rows = rows.filter((l) => l.archived === "true");
    else if (isArchivedCategory) rows = rows.filter((l) => l.category === categoryFilter && l.archived === "true");
    else rows = rows.filter((l) => l.category === categoryFilter && l.archived !== "true");

    const q = searchQuery.trim().toLowerCase();
    if (q) {
      rows = rows.filter((l) =>
        `${l.name} ${l.url} ${l.category} ${l.tags} ${l.details || l.notes}`.toLowerCase().includes(q),
      );
    }
    if (dateFilter) rows = rows.filter((l) => l.updated_at.slice(0, 10) === dateFilter);

    const sorted = [...rows];
    if (sortMode === "newest") sorted.sort((a, b) => b.updated_at.localeCompare(a.updated_at));
    else if (sortMode === "oldest") sorted.sort((a, b) => a.updated_at.localeCompare(b.updated_at));
    else if (sortMode === "az") sorted.sort((a, b) => a.name.localeCompare(b.name));
    else if (sortMode === "favorite") sorted.sort((a, b) => Number(b.favorite === "true") - Number(a.favorite === "true"));
    else sorted.sort((a, b) => Number(b.pinned === "true") - Number(a.pinned === "true"));
    return sorted;
  });

  const selectedLink = $derived.by<LinkItem | null>(() => bank.links.find((l) => l.id === selectedLinkId) ?? null);

  // ── Public API (Task 10 shell drives this) ──
  export async function refresh(): Promise<void> {
    loadState = "loading";
    errorMessage = "";
    if (!isPywebviewReady() && !(await waitForPywebviewReady())) {
      loadState = "error";
      errorMessage = "pywebview bridge unavailable.";
      return;
    }
    const resp = await callBridge<LinkBankData>("linkbank_get");
    if (!resp.ok) {
      loadState = "error";
      errorMessage = resp.error.message;
      return;
    }
    bank = resp.data ?? EMPTY_BANK;
    loadState = "loaded";
    if (selectedLinkId && !bank.links.some((l) => l.id === selectedLinkId)) {
      selectedLinkId = "";
      detailMode = "view";
    }
  }

  // ── Category rail selection ──
  function selectCategory(name: string) {
    categoryFilter = name;
    renamingCategory = false;
  }

  function selectLink(link: LinkItem) {
    selectedLinkId = link.id;
    detailMode = "view";
  }

  // ── Add / Edit (shared detail-pane form) ──
  function beginAdd() {
    detailMode = "add";
    formName = "";
    formUrl = "";
    formCategory = isCategoryRow ? categoryFilter : "";
    formTags = "";
    formDetails = "";
    formError = "";
  }

  function beginEdit(link: LinkItem) {
    detailMode = "edit";
    formName = link.name;
    formUrl = link.url;
    formCategory = link.category;
    formTags = link.tags;
    formDetails = link.details || link.notes;
    formError = "";
  }

  function cancelForm() {
    detailMode = "view";
    formError = "";
  }

  async function handleSaveLink() {
    formError = "";
    const name = formName.trim();
    const url = formUrl.trim();
    if (!name || !url) {
      formError = "Name and URL are required.";
      return;
    }
    saving = true;
    const payload = {
      name,
      url,
      category: formCategory.trim(),
      tags: formTags.trim(),
      details: formDetails.trim(),
      notes: formDetails.trim(),
    };
    const resp =
      detailMode === "edit"
        ? await callBridge<LinkItem>("linkbank_update", { id: selectedLinkId, ...payload })
        : await callBridge<LinkItem>("linkbank_add_link", payload);
    saving = false;
    if (!resp.ok) {
      formError = resp.error.message;
      return;
    }
    if (resp.data) selectedLinkId = resp.data.id;
    detailMode = "view";
    await refresh();
  }

  // ── Pin / favorite (existing update facade) ──
  async function togglePin(link: LinkItem) {
    const resp = await callBridge<LinkItem>("linkbank_update", {
      id: link.id,
      pinned: link.pinned === "true" ? "false" : "true",
    });
    if (!resp.ok) {
      addToast(resp.error.message, "error");
      return;
    }
    await refresh();
  }

  async function toggleFavorite(link: LinkItem) {
    const resp = await callBridge<LinkItem>("linkbank_update", {
      id: link.id,
      favorite: link.favorite === "true" ? "false" : "true",
    });
    if (!resp.ok) {
      addToast(resp.error.message, "error");
      return;
    }
    await refresh();
  }

  // ── Open / copy ──
  async function openLink(link: LinkItem) {
    const resp = await callBridge<LinkItem>("linkbank_open", link.id);
    if (!resp.ok) addToast(resp.error.message, "error");
  }

  function legacyCopy(text: string): boolean {
    if (typeof document === "undefined") return false;
    const el = document.createElement("textarea");
    el.value = text;
    el.setAttribute("readonly", "");
    el.style.position = "fixed";
    el.style.opacity = "0";
    document.body.appendChild(el);
    el.select();
    el.setSelectionRange(0, text.length);
    let copied = false;
    try {
      copied = document.execCommand("copy");
    } catch {
      copied = false;
    }
    document.body.removeChild(el);
    return copied;
  }

  async function copyLinkUrl(link: LinkItem) {
    let copied = false;
    try {
      if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(link.url);
        copied = true;
      }
    } catch {
      copied = false;
    }
    if (!copied) copied = legacyCopy(link.url);
    addToast(copied ? "Copied URL" : "Copy failed. Select and copy the URL manually.", copied ? "success" : "error");
  }

  // ── Category management ──
  async function createCategory() {
    const name = newCategoryName.trim();
    if (!name) return;
    const resp = await callBridge<LinkBankData>("linkbank_category_create", name);
    if (!resp.ok) {
      addToast(resp.error.message, "error");
      return;
    }
    newCategoryName = "";
    categoryFilter = name;
    await refresh();
  }

  function beginRenameCategory() {
    renamingCategory = true;
    renameCategoryValue = categoryFilter;
  }

  function cancelRenameCategory() {
    renamingCategory = false;
    renameCategoryValue = "";
  }

  async function commitRenameCategory() {
    // Escape-cancel blur race: Escape → cancelRenameCategory() already cleared
    // renamingCategory; the re-render removing the focused input then fires a
    // native blur → this re-entrant call must no-op (mirrors commitCreate).
    if (!renamingCategory) return;
    const next = renameCategoryValue.trim();
    renamingCategory = false;
    renameCategoryValue = "";
    if (!next || next === categoryFilter) return;
    const resp = await callBridge<LinkBankData>("linkbank_category_rename", categoryFilter, next);
    if (!resp.ok) {
      addToast(resp.error.message, "error");
      return;
    }
    categoryFilter = next;
    await refresh();
  }

  // ── Confirmation-gated archive/restore (link + category) ──
  function requestArchiveLink(link: LinkItem) {
    pendingAction = { kind: "archive-link", link };
  }

  function requestRestoreLink(link: LinkItem) {
    pendingAction = { kind: "restore-link", link };
  }

  function requestArchiveCategory(name: string) {
    pendingAction = { kind: "archive-category", name };
  }

  function requestRestoreCategory(name: string) {
    pendingAction = { kind: "restore-category", name };
  }

  function cancelPendingAction() {
    pendingAction = null;
  }

  async function confirmPendingAction() {
    const action = pendingAction;
    pendingAction = null;
    if (!action) return;
    actionBusy = true;
    const resp =
      action.kind === "archive-link"
        ? await callBridge<LinkItem>("linkbank_archive_link", action.link.id)
        : action.kind === "restore-link"
          ? await callBridge<LinkItem>("linkbank_restore_link", action.link.id)
          : action.kind === "archive-category"
            ? await callBridge<LinkBankData>("linkbank_category_archive", action.name)
            : await callBridge<LinkBankData>("linkbank_category_restore", action.name);
    actionBusy = false;
    if (!resp.ok) {
      addToast(resp.error.message, "error");
      return;
    }
    await refresh();
  }

  // ── Import (preview → confirm → atomic merge; cancel/malformed write nothing) ──
  function triggerImport() {
    fileInputEl?.click();
  }

  function detectImportFormat(name: string): "json" | "csv" {
    return name.toLowerCase().endsWith(".csv") ? "csv" : "json";
  }

  async function handleImportFile(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = "";
    if (!file) return;
    const format = detectImportFormat(file.name);
    const content = await file.text();
    const resp = await callBridge<LinkImportPreview>("linkbank_import_preview", format, content);
    if (!resp.ok) {
      addToast(resp.error.message, "error");
      return;
    }
    importPreview = resp.data;
    pendingImportPayload = { format, content };
  }

  function cancelImport() {
    importPreview = null;
    pendingImportPayload = null;
  }

  async function confirmImportMerge() {
    const payload = pendingImportPayload;
    if (!payload) return;
    importBusy = true;
    const resp = await callBridge<LinkImportResult>("linkbank_import_merge", payload.format, payload.content);
    importBusy = false;
    importPreview = null;
    pendingImportPayload = null;
    if (!resp.ok) {
      addToast(resp.error.message, "error");
      return;
    }
    addToast(
      `Imported: ${resp.data?.added ?? 0} added, ${resp.data?.updated ?? 0} updated, ${resp.data?.conflicts ?? 0} conflicts skipped`,
      "success",
      4000,
    );
    await refresh();
  }

  // ── Export (native save dialog) ──
  async function exportBank(fmt: "json" | "csv") {
    exporting = true;
    const resp = await callBridge<LinkExportPayload>("linkbank_export_file", fmt);
    if (!resp.ok) {
      exporting = false;
      addToast(resp.error.message, "error");
      return;
    }
    const payload = resp.data;
    const saveResp = await callBridge<{ path: string | null; written: boolean }>(
      "util_save_file",
      payload?.suggested_name ?? `link-bank.${fmt}`,
      payload?.content ?? "",
    );
    exporting = false;
    if (saveResp.ok && saveResp.data?.written) {
      addToast(`Exported: ${saveResp.data.path}`, "success", 4000);
    } else if (saveResp.ok) {
      addToast("Export cancelled.", "info");
    } else {
      addToast(saveResp.error.message, "error");
    }
  }

  onMount(() => {
    void refresh();
  });
</script>

<section class="lb-shell" aria-label="Link Bank workspace">
  <!-- ── Category rail ── -->
  <aside class="lb-rail">
    <button type="button" class="lb-rail-item" class:selected={categoryFilter === "all"} onclick={() => selectCategory("all")}>
      <span class="lb-row-title">All</span><span class="lb-count">{allCount}</span>
    </button>
    <button type="button" class="lb-rail-item" class:selected={categoryFilter === "pinned"} onclick={() => selectCategory("pinned")}>
      <span class="lb-row-title">Pinned</span><span class="lb-count">{pinnedCount}</span>
    </button>
    <button type="button" class="lb-rail-item" class:selected={categoryFilter === "favorites"} onclick={() => selectCategory("favorites")}>
      <span class="lb-row-title">Favorites</span><span class="lb-count">{favoriteCount}</span>
    </button>

    <div class="lb-rail-divider">Categories</div>
    {#each activeCategories as cat}
      <button type="button" class="lb-rail-item" class:selected={categoryFilter === cat} onclick={() => selectCategory(cat)}>
        <span class="lb-row-title">{cat}</span><span class="lb-count">{countActive(cat)}</span>
      </button>
    {:else}
      <p class="lb-muted">No categories yet.</p>
    {/each}
    <div class="lb-rail-add">
      <input
        class="lb-inline-input"
        placeholder="New category…"
        bind:value={newCategoryName}
        onkeydown={(e) => { if (e.key === "Enter") createCategory(); }}
      />
      <button type="button" class="lb-btn" disabled={!newCategoryName.trim()} onclick={createCategory}>Add</button>
    </div>

    <div class="lb-rail-divider">Archived</div>
    <button type="button" class="lb-rail-item" class:selected={categoryFilter === "archived"} onclick={() => selectCategory("archived")}>
      <span class="lb-row-title">Archived</span><span class="lb-count">{archivedCount}</span>
    </button>
    {#each archivedCategories as cat}
      <button type="button" class="lb-rail-item" class:selected={categoryFilter === cat} onclick={() => selectCategory(cat)}>
        <span class="lb-row-title">{cat}</span><span class="lb-count">{countArchived(cat)}</span>
      </button>
    {/each}
  </aside>

  <!-- ── Workspace ── -->
  <div class="lb-workspace">
    <div class="lb-toolbar">
      <div class="lb-search">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
        <input class="lb-input" type="search" placeholder="Search title, URL, category, tags, details…" bind:value={searchQuery} />
      </div>
      <label class="lb-field">
        <span>Date</span>
        <input class="lb-control" type="date" bind:value={dateFilter} />
      </label>
      <label class="lb-field">
        <span>Sort</span>
        <select class="lb-control" bind:value={sortMode}>
          <option value="newest">Newest</option>
          <option value="oldest">Oldest</option>
          <option value="az">A–Z</option>
          <option value="favorite">Favorite first</option>
          <option value="pinned">Pinned first</option>
        </select>
      </label>
      <button type="button" class="lb-btn lb-btn-primary" onclick={beginAdd}>+ Add link</button>
      <button type="button" class="lb-btn" disabled={importBusy} onclick={triggerImport}>{importBusy ? "Importing…" : "Import"}</button>
      <input
        type="file"
        accept=".json,.csv,application/json,text/csv"
        bind:this={fileInputEl}
        onchange={handleImportFile}
        style="display:none"
      />
      <button type="button" class="lb-btn" class:is-loading={exporting} disabled={exporting} onclick={() => exportBank("json")}>
        {exporting ? "Exporting…" : "Export JSON"}
      </button>
      <button type="button" class="lb-btn" class:is-loading={exporting} disabled={exporting} onclick={() => exportBank("csv")}>
        {exporting ? "Exporting…" : "Export CSV"}
      </button>
    </div>

    {#if importPreview}
      <div class="lb-import-summary" role="status">
        <p class="lb-import-counts">
          <span>Add {importPreview.add}</span>
          <span>Update {importPreview.update}</span>
          <span>Conflicts {importPreview.conflict}</span>
          <span>Invalid {importPreview.invalid}</span>
        </p>
        <div class="lb-import-actions">
          <button type="button" class="lb-btn lb-btn-primary" class:is-loading={importBusy} disabled={importBusy} onclick={confirmImportMerge}>
            {importBusy ? "Importing…" : "Confirm import"}
          </button>
          <button type="button" class="lb-btn" disabled={importBusy} onclick={cancelImport}>Cancel</button>
        </div>
      </div>
    {/if}

    {#if isCategoryRow}
      <div class="lb-category-bar">
        {#if renamingCategory}
          <input
            class="lb-inline-input"
            bind:value={renameCategoryValue}
            onkeydown={(e) => { if (e.key === "Enter") commitRenameCategory(); else if (e.key === "Escape") cancelRenameCategory(); }}
            onblur={commitRenameCategory}
          />
        {:else}
          <span class="lb-category-name">{categoryFilter}{isArchivedCategory ? " (archived)" : ""}</span>
          {#if isArchivedCategory}
            <button type="button" class="lb-btn" onclick={() => requestRestoreCategory(categoryFilter)}>Restore category</button>
          {:else}
            <button type="button" class="lb-btn" onclick={beginRenameCategory}>Rename</button>
            <button type="button" class="lb-btn" onclick={() => requestArchiveCategory(categoryFilter)}>Archive category</button>
          {/if}
        {/if}
      </div>
    {/if}

    {#if loadState === "error"}
      <div class="lb-banner-error">
        <p class="lb-banner-title">Link Bank failed to load</p>
        <p class="lb-muted">{errorMessage}</p>
      </div>
    {:else if loadState === "loading"}
      <div class="lb-panels">
        <div class="lb-list">
          {#each { length: 5 } as _}
            <div class="lb-skeleton-row"></div>
          {/each}
        </div>
        <div class="lb-detail"><p class="lb-muted">Loading…</p></div>
      </div>
    {:else}
      <div class="lb-panels">
        <!-- ── Compact link list ── -->
        <div class="lb-list">
          {#each filteredLinks as link (link.id)}
            <button type="button" class="lb-row" class:selected={selectedLinkId === link.id} onclick={() => selectLink(link)}>
              {#if link.pinned === "true"}<span class="lb-pin-mark" aria-hidden="true">◆</span>{/if}
              {#if link.favorite === "true"}<span class="lb-fav-mark" aria-hidden="true">★</span>{/if}
              <span class="lb-row-title">{link.name}</span>
              <span class="lb-row-category">{link.category || "Uncategorized"}</span>
            </button>
          {:else}
            <p class="lb-muted">No links match the current filter.</p>
          {/each}
        </div>

        <!-- ── Selected link / add / edit detail pane ── -->
        <div class="lb-detail">
          {#if detailMode === "add" || detailMode === "edit"}
            <form class="lb-form" onsubmit={(e) => { e.preventDefault(); handleSaveLink(); }}>
              <label class="lb-form-field">
                <span>Name *</span>
                <input class="lb-control" required bind:value={formName} />
              </label>
              <label class="lb-form-field">
                <span>URL *</span>
                <input class="lb-control" required type="url" placeholder="https://…" bind:value={formUrl} />
              </label>
              <label class="lb-form-field">
                <span>Category</span>
                <input class="lb-control" list="lb-category-options" bind:value={formCategory} />
                <datalist id="lb-category-options">
                  {#each allCategoryNames as cat}<option value={cat}></option>{/each}
                </datalist>
              </label>
              <label class="lb-form-field">
                <span>Tags</span>
                <input class="lb-control" placeholder="comma, separated" bind:value={formTags} />
              </label>
              <label class="lb-form-field">
                <span>Details</span>
                <textarea class="lb-control lb-textarea" bind:value={formDetails}></textarea>
              </label>
              {#if formError}<p class="lb-error">{formError}</p>{/if}
              <div class="lb-form-actions">
                <button type="submit" class="lb-btn lb-btn-primary" class:is-loading={saving} disabled={saving}>
                  {saving ? "Saving…" : detailMode === "add" ? "Add link" : "Save changes"}
                </button>
                <button type="button" class="lb-btn" onclick={cancelForm} disabled={saving}>Cancel</button>
              </div>
            </form>
          {:else if selectedLink}
            <div class="lb-view">
              <h3 class="lb-view-title">{selectedLink.name}</h3>
              <p class="lb-view-url">{selectedLink.url}</p>
              <p class="lb-view-category">{selectedLink.category || "Uncategorized"}</p>
              {#if selectedLink.tags}
                <div class="lb-tag-row">
                  {#each selectedLink.tags.split(",").map((t) => t.trim()).filter(Boolean) as tag}
                    <span class="lb-tag">{tag}</span>
                  {/each}
                </div>
              {/if}
              <p class="lb-view-details">{selectedLink.details || selectedLink.notes || "No details."}</p>
              <div class="lb-view-actions">
                <button type="button" class="lb-btn" onclick={() => openLink(selectedLink)}>Open</button>
                <button type="button" class="lb-btn" onclick={() => copyLinkUrl(selectedLink)}>Copy URL</button>
                <button type="button" class="lb-btn" onclick={() => togglePin(selectedLink)}>{selectedLink.pinned === "true" ? "Unpin" : "Pin"}</button>
                <button type="button" class="lb-btn" onclick={() => toggleFavorite(selectedLink)}>{selectedLink.favorite === "true" ? "Unfavorite" : "Favorite"}</button>
                <button type="button" class="lb-btn" onclick={() => beginEdit(selectedLink)}>Edit</button>
                {#if selectedLink.archived === "true"}
                  <button type="button" class="lb-btn" onclick={() => requestRestoreLink(selectedLink)}>Restore</button>
                {:else}
                  <button type="button" class="lb-btn" onclick={() => requestArchiveLink(selectedLink)}>Archive</button>
                {/if}
              </div>
            </div>
          {:else}
            <div class="lb-empty">
              <p class="lb-empty-title">Select a link</p>
              <p class="lb-muted">Pick a link from the list, or add a new one.</p>
            </div>
          {/if}
        </div>
      </div>
    {/if}
  </div>
</section>

{#if pendingAction}
  <ConfirmModal
    title={pendingAction.kind.startsWith("archive") ? "Archive?" : "Restore?"}
    actionLabel={pendingAction.kind === "archive-link"
      ? "Archive link"
      : pendingAction.kind === "restore-link"
        ? "Restore link"
        : pendingAction.kind === "archive-category"
          ? "Archive category"
          : "Restore category"}
    targetName={pendingAction.kind === "archive-link" || pendingAction.kind === "restore-link" ? pendingAction.link.name : pendingAction.name}
    reversible={true}
    onConfirm={confirmPendingAction}
    onCancel={cancelPendingAction}
  />
{/if}

<style>
  .lb-shell { display:flex; min-height:0; flex:1; gap:14px; }

  /* ── Category rail (never collapses at the list/detail stack breakpoint) ── */
  .lb-rail { flex:0 0 clamp(220px, 22vw, 280px); min-height:0; overflow-y:auto; display:flex; flex-direction:column; gap:3px; padding:12px; background:var(--color-workspace-panel); border:1px solid var(--color-border); border-radius:8px; }
  .lb-rail-divider { margin:10px 0 2px; font-size:10px; font-weight:800; text-transform:uppercase; letter-spacing:0.06em; color:var(--color-muted); }
  .lb-rail-item { display:flex; align-items:center; justify-content:space-between; gap:8px; width:100%; text-align:left; border:0; background:transparent; border-radius:6px; padding:6px 8px; font-size:12px; font-weight:650; color:var(--color-ink); cursor:pointer; transition:background 0.12s, color 0.12s; }
  .lb-rail-item:hover, .lb-rail-item.selected { background:var(--color-soft-pink-surface); color:var(--color-dbs-red); }
  .lb-rail-item:focus-visible { outline:2px solid var(--color-dbs-red); outline-offset:2px; }
  .lb-count { flex:0 0 auto; font-size:10px; font-weight:800; color:var(--color-muted-light); }
  .lb-rail-add { display:flex; gap:6px; margin-top:6px; }
  .lb-rail-add .lb-inline-input { flex:1; min-width:0; }

  /* ── Workspace ── */
  .lb-workspace { flex:1; min-width:0; min-height:0; display:flex; flex-direction:column; gap:12px; }
  .lb-toolbar { display:flex; align-items:flex-end; gap:10px; flex-wrap:wrap; }
  .lb-search { display:flex; align-items:center; gap:7px; flex:1 1 260px; min-width:200px; height:30px; padding:0 10px; border:1px solid var(--color-input-border); border-radius:7px; background:var(--color-workspace-panel); color:var(--color-muted); }
  .lb-search:focus-within { border-color:var(--color-dbs-red); color:var(--color-ink); }
  .lb-input { flex:1; min-width:0; border:0; background:transparent; color:var(--color-ink); font-size:12.5px; font-weight:600; outline:none; }
  .lb-field { display:flex; flex-direction:column; gap:4px; }
  .lb-field span { font-size:9.5px; font-weight:700; color:var(--color-muted); text-transform:uppercase; letter-spacing:0.05em; }
  .lb-control { height:30px; border:1px solid var(--color-input-border); border-radius:6px; background:var(--color-workspace-panel); color:var(--color-ink); font-size:12px; font-weight:600; padding:0 8px; outline:none; }
  .lb-control:focus, .lb-control:focus-visible { border-color:var(--color-dbs-red); }
  .lb-textarea { height:auto; min-height:72px; padding:8px; resize:vertical; font-family:var(--font); }
  .lb-inline-input { height:26px; padding:0 8px; border:1px solid var(--color-dbs-red); border-radius:6px; background:var(--color-workspace-panel); color:var(--color-ink); font-size:12px; font-weight:600; outline:none; }

  /* ── Buttons: default / hover / focus / active / disabled / loading ── */
  .lb-btn { height:30px; padding:0 12px; border:1px solid var(--color-border); border-radius:6px; background:var(--color-workspace-panel); color:var(--color-ink); font-size:11.5px; font-weight:700; cursor:pointer; white-space:nowrap; transition:background 0.12s, color 0.12s, border-color 0.12s, transform 0.12s; }
  .lb-btn:hover:not(:disabled) { border-color:var(--color-dbs-red); color:var(--color-dbs-red); }
  .lb-btn:focus-visible { outline:2px solid var(--color-dbs-red); outline-offset:2px; }
  .lb-btn:active:not(:disabled) { transform:translateY(1px); }
  .lb-btn:disabled { opacity:0.5; cursor:not-allowed; }
  .lb-btn.is-loading { cursor:progress; }
  .lb-btn-primary { background:var(--color-dbs-red); border-color:var(--color-dbs-red); color:var(--card-white); }
  .lb-btn-primary:hover:not(:disabled) { background:var(--color-dbs-red-hover); border-color:var(--color-dbs-red-hover); color:var(--card-white); }
  .lb-btn-primary:active:not(:disabled) { background:var(--color-dbs-red-active); }
  .lb-btn-primary:disabled { opacity:0.6; }

  .lb-import-summary { display:flex; align-items:center; justify-content:space-between; gap:10px; flex-wrap:wrap; padding:10px 12px; border:1px solid var(--color-soft-pink-border); background:var(--color-soft-pink-surface); border-radius:8px; }
  .lb-import-counts { margin:0; display:flex; gap:14px; flex-wrap:wrap; font-size:11.5px; font-weight:800; color:var(--color-dbs-red); }
  .lb-import-actions { display:flex; gap:8px; flex-wrap:wrap; }

  .lb-category-bar { display:flex; align-items:center; gap:8px; flex-wrap:wrap; padding:8px 10px; border:1px dashed var(--color-border); border-radius:7px; background:var(--color-workspace); }
  .lb-category-name { flex:1 1 auto; min-width:0; font-size:12.5px; font-weight:800; color:var(--color-ink-strong); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }

  .lb-panels { flex:1; min-height:0; display:grid; grid-template-columns:clamp(260px, 28vw, 360px) minmax(0, 1fr); gap:14px; align-items:stretch; }
  .lb-list, .lb-detail { min-width:0; min-height:0; background:var(--color-workspace-panel); border:1px solid var(--color-border); border-radius:8px; overflow-y:auto; }
  .lb-list { padding:8px; display:flex; flex-direction:column; gap:2px; }
  .lb-detail { padding:16px; display:flex; flex-direction:column; gap:12px; }

  .lb-row { display:flex; align-items:center; gap:7px; width:100%; text-align:left; border:0; background:transparent; border-radius:6px; padding:7px 8px; font-size:12px; font-weight:650; color:var(--color-ink); cursor:pointer; transition:background 0.12s, color 0.12s; }
  .lb-row:hover, .lb-row.selected { background:var(--color-soft-pink-surface); color:var(--color-dbs-red); }
  .lb-row:focus-visible { outline:2px solid var(--color-dbs-red); outline-offset:-2px; }
  .lb-row-title { flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .lb-row-category { flex:0 0 auto; font-size:9.5px; font-weight:800; text-transform:uppercase; letter-spacing:0.04em; color:var(--color-muted-light); }
  .lb-pin-mark, .lb-fav-mark { flex:0 0 auto; font-size:11px; color:var(--color-dbs-red); }

  .lb-skeleton-row { height:30px; border-radius:6px; margin-bottom:4px; background:linear-gradient(90deg, var(--color-row-alt) 25%, var(--color-row-hover) 50%, var(--color-row-alt) 75%); background-size:200% 100%; animation:lb-shimmer 1.3s ease-in-out infinite; }
  @keyframes lb-shimmer { 0% { background-position:200% 0; } 100% { background-position:-200% 0; } }

  .lb-form { display:flex; flex-direction:column; gap:10px; }
  .lb-form-field { display:flex; flex-direction:column; gap:4px; }
  .lb-form-field span { font-size:9.5px; font-weight:800; text-transform:uppercase; letter-spacing:0.05em; color:var(--color-muted); }
  .lb-form-actions { display:flex; gap:8px; }
  .lb-error { margin:0; font-size:11px; font-weight:800; color:var(--tag-red-ink); background:var(--tag-red-bg); border-radius:6px; padding:6px 8px; }

  .lb-view { display:flex; flex-direction:column; gap:8px; }
  .lb-view-title { margin:0; font-size:15px; font-weight:850; color:var(--color-ink-strong); }
  .lb-view-url { margin:0; font-size:12px; font-weight:650; color:var(--color-dbs-red); word-break:break-all; }
  .lb-view-category { margin:0; font-size:10.5px; font-weight:800; text-transform:uppercase; letter-spacing:0.05em; color:var(--color-muted); }
  .lb-view-details { margin:0; font-size:12px; color:var(--color-muted); line-height:1.5; white-space:pre-wrap; }
  .lb-tag-row { display:flex; gap:6px; flex-wrap:wrap; }
  .lb-tag { font-size:10px; font-weight:800; padding:2px 8px; border-radius:999px; background:var(--color-soft-pink-surface); color:var(--color-dbs-red); border:1px solid var(--color-soft-pink-border); }
  .lb-view-actions { display:flex; gap:8px; flex-wrap:wrap; margin-top:4px; }

  .lb-empty { display:flex; flex-direction:column; gap:6px; align-items:center; justify-content:center; flex:1; text-align:center; }
  .lb-empty-title { margin:0; font-size:14px; font-weight:800; color:var(--color-ink-strong); }

  .lb-muted { margin:0; font-size:11px; font-weight:500; color:var(--color-muted); line-height:1.5; }
  .lb-banner-error { margin:0; padding:10px 12px; font-size:11px; font-weight:700; color:var(--tag-red-ink); background:var(--tag-red-bg); border-radius:6px; }
  .lb-banner-title { margin:0 0 2px; font-weight:800; }

  /* Responsive: category rail stays put; list/detail stack at <=1200px. */
  @media (max-width:1200px) {
    .lb-panels { grid-template-columns:1fr; }
  }

  @media (prefers-reduced-motion:reduce) {
    .lb-rail-item, .lb-row, .lb-btn { transition:none; }
    .lb-skeleton-row { animation:none; }
  }
</style>
