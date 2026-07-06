<script lang="ts">
  import { onDestroy, onMount, tick, untrack } from "svelte";
  import {
    callBridge,
    isPywebviewReady,
    rteAssetRead,
    rteDocumentSave,
    rteExportRequest,
    rteExportStatus,
    rteImageSave,
    saveRteFile,
  } from "../bridge";
  import { escapeHtml, htmlToMarkdown, renderMarkdown } from "../markdown";
  import type { RteCapabilityLevel, RteFormat, RteSaveReason, RteSaveStrategy } from "../types";
  import { IdleExportScheduler, docxCountdownLabel, docxStatusLabel, mapExportState } from "../rteDocxState";
  import type { DocxExportDisplay } from "../rteDocxState";
  import { Editor } from "@tiptap/core";
  import StarterKit from "@tiptap/starter-kit";
  // NOTE: Underline + Link are bundled INSIDE StarterKit v3 — re-registering them
  // throws a duplicate-name error, so we only configure them on StarterKit.
  import Subscript from "@tiptap/extension-subscript";
  import Superscript from "@tiptap/extension-superscript";
  import { FontFamily, TextStyle } from "@tiptap/extension-text-style";
  import { AssetImage } from "../extensions/AssetImage";
  import { Table } from "@tiptap/extension-table";
  import TableRow from "@tiptap/extension-table-row";
  import TableCell from "@tiptap/extension-table-cell";
  import TableHeader from "@tiptap/extension-table-header";
  import TaskList from "@tiptap/extension-task-list";
  import TaskItem from "@tiptap/extension-task-item";
  import TextAlign from "@tiptap/extension-text-align";
  import Color from "@tiptap/extension-color";
  import Highlight from "@tiptap/extension-highlight";
  import Placeholder from "@tiptap/extension-placeholder";
  import { FontSize } from "../extensions/FontSize";

  interface Props {
    projectPath: string;
    initialNotes: string;
    onSaved?: (notes: string) => void;
    /** Optional explicit file path (Piece B CR Docs). When set, the editor saves
     *  via saveRteFile instead of notes_update. Defaults to ``${projectPath}/notes.md``. */
    filePath?: string;
    /** How to interpret {@link initialNotes} / serialize editor output. */
    fileFormat?: RteFormat;
    /** When false the editor is read-only (e.g. IMPLEMENTED project state). */
    editable?: boolean;
    capability?: RteCapabilityLevel;
    saveStrategy?: RteSaveStrategy;
    supportedEditorFeatures?: string[];
    message?: string;
    onReady?: (api: { flushNow: () => Promise<boolean> } | undefined) => void;
    /** DOCX pipeline (D-0012): initial Tiptap JSON doc from rte_document_open. */
    initialDoc?: Record<string, unknown> | null;
    /** DOCX pipeline: revision of {@link initialDoc}. */
    initialRevision?: number;
    /** DOCX pipeline: true when initialNotes carries mammoth migration HTML. */
    needsMigration?: boolean;
  }
  let {
    projectPath,
    initialNotes,
    onSaved,
    filePath,
    fileFormat = "markdown",
    editable = true,
    capability = editable ? "editable" : "read_only",
    saveStrategy,
    supportedEditorFeatures = [],
    message = "",
    onReady,
    initialDoc = null,
    initialRevision = 0,
    needsMigration = false,
  }: Props = $props();

  /** Resolved target file: explicit path, else the project's notes.md. */
  const targetFile = $derived(filePath ?? `${projectPath.replace(/\/$/, "")}/notes.md`);
  const effectiveSaveStrategy = $derived(saveStrategy ?? (fileFormat === "text" ? "plain_text" : fileFormat === "html" ? "html" : "markdown"));
  const canEdit = $derived(editable && capability === "editable" && effectiveSaveStrategy !== "none");
  const isPlainTextMode = $derived(effectiveSaveStrategy === "plain_text");
  const directHtmlMode = $derived(effectiveSaveStrategy === "html" || effectiveSaveStrategy === "docx_legacy");
  /** DOCX pipeline mode: JSON source of truth, .docx = derived export. */
  const docxPipelineMode = $derived(effectiveSaveStrategy === "docx_pipeline");
  const richToolbarEnabled = $derived(canEdit && !isPlainTextMode && (supportedEditorFeatures.length === 0 || supportedEditorFeatures.some((feature) => feature !== "plain_text")));
  const ZOOM_MIN = 100;
  const ZOOM_MAX = 500;
  const ZOOM_STEP = 25;

  type SaveStatus = "idle" | "pending" | "saving" | "saved" | "error" | "offline";

  let text = $state(untrack(() => initialNotes ?? ""));
  let status = $state<SaveStatus>("idle");
  let errorText = $state("");
  let hostEl = $state<HTMLDivElement | null>(null);
  let editor: Editor | null = null;
  let toolbarEl = $state<HTMLElement | null>(null);
  let lastSaved = $state(untrack(() => initialNotes ?? ""));
  // Cheap dirty flag. The expensive serialize (getHTML + DOMParser + markdown
  // walk) runs only in flush(), not on every keystroke.
  let dirty = $state(false);
  let fullscreen = $state(false);
  let zoomPercent = $state(100);
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

  let colorOpen = $state(false);
  let colorMode: 'fore' | 'back' = $state('fore');
  let tableOpen = $state(false);
  let tableHover = $state({ rows: 1, cols: 1 });
  let emojiOpen = $state(false);
  let helpOpen = $state(false);
  let fontSelVal = $state('');
  let sizeSelVal = $state('');
  // Inline link dialog (replaces unreliable WebView2 prompt()).
  let linkOpen = $state(false);
  let linkUrl = $state('');
  let linkEditing = $state(false);
  // Inline image dialog.
  let imgOpen = $state(false);
  let imgUrl = $state('');
  let imgAlt = $state('');

  const FONTS = [
    { label: 'Times New Roman', value: '"Times New Roman", serif' },
    { label: 'Sans-serif', value: 'Inter, sans-serif' },
    { label: 'Serif', value: 'Georgia, serif' },
    { label: 'Monospace', value: '"Courier New", monospace' },
    { label: 'Arial', value: 'Arial' },
    { label: 'Calibri', value: 'Calibri' },
    { label: 'Verdana', value: 'Verdana' },
    { label: 'Trebuchet MS', value: '"Trebuchet MS"' },
    { label: 'Consolas', value: 'Consolas' },
    { label: 'Segoe UI', value: '"Segoe UI"' },
  ];

  const SIZES = [8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 24, 28, 32, 36, 42, 48, 56, 64, 72];

  const COLORS = [
    '#000000','#434343','#666666','#999999','#b7b7b7','#cccccc','#d9d9d9','#efefef',
    '#f3f3f3','#ffffff','#980000','#ff0000','#ff9900','#ffff00','#00ff00','#00ffff',
    '#4a86e8','#0000ff','#9900ff','#ff00ff','#e6b8af','#f4cccc','#fce5cd','#fff2cc',
    '#d9ead3','#d0e0e3','#c9daf8','#cfe2f3','#d9d2e9','#ead1dc','#dd7e6b','#ea9999',
    '#f9cb9c','#ffe599','#b6d7a8','#a2c4c9','#a4c2f4','#9fc5e8','#b4a7d6','#d5a6bd',
    '#cc4125','#e06666','#f6b26b','#ffd966','#93c47d','#76a5af','#6d9eeb','#6fa8dc',
    '#8e7cc3','#c27ba0','#a61c00','#cc0000','#e69138','#f1c232','#6aa84f','#45818e',
    '#3c78d8','#3d85c6','#674ea7','#a64d79','#85200c','#990000','#b45f06','#bf9000',
    '#38761d','#134f5c','#1155cc','#0b5394','#351c75','#741b47','#5b0f00','#660000',
    '#783f04','#7f6000','#274e13','#0c343d','#1c4587','#073763','#20124d','#4c1130',
  ];

  const EMOJIS = [
    '😀','😃','😄','😁','😅','😂','🤣','😊',
    '😇','🙂','😉','😌','😍','🥰','😘','😗',
    '😋','😛','😜','🤪','😝','🤑','🤗','🤭',
    '🤔','🤐','😑','😶','😏','😒','🙄','😤',
    '😢','😭','😰','🥶','🥵','🤯','😳','🥺',
    '❤️','🧡','💛','💚','💙','💜','🖤','🤍',
    '👍','👎','👊','✊','🤛','🤜','✌️','🤟',
    '🔥','⭐','✅','❌','🎉','🎊','💯','🚀',
  ];

  const AUTOSAVE_MS = 1000;
  const IDLE_EXPORT_MS = 5_000;
  const EXPORT_POLL_MS = 1000;
  let timer: ReturnType<typeof setTimeout> | undefined;

  // ── DOCX pipeline state (D-0012) ──
  let docRevision = 0;
  let lastSavedDocJson = "";
  let lastExportedRevision = 0;
  let migrationPending = false;
  /** Guards the asset-hydration transactions from marking the doc dirty. */
  let hydrating = false;
  let exportDisplay = $state<DocxExportDisplay>("idle");
  let exportCountdown = $state(0);
  let exportCountdownTimer: ReturnType<typeof setInterval> | undefined;
  let exportPollTimer: ReturnType<typeof setInterval> | undefined;
  const idleExport = new IdleExportScheduler(IDLE_EXPORT_MS, () => {
    stopExportCountdown();
    void requestDocxExport();
  });

  const baseStatusLabel = $derived(
    capability === "unsupported" ? "Unsupported format"
    : !canEdit ? "Read-only"
    : status === "saving" ? "Saving…"
    : status === "saved" ? "Saved"
    : status === "pending" ? "Unsaved changes"
    : status === "offline" ? "Offline — notes not saved in browser preview"
    : status === "error" ? `Save failed: ${errorText}`
    : "Saved",
  );
  const statusLabel = $derived(
    docxPipelineMode && canEdit && (status === "saved" || status === "idle")
      ? (exportCountdown > 0 && exportDisplay !== "exporting" ? docxCountdownLabel(exportCountdown) : docxStatusLabel(exportDisplay, baseStatusLabel))
      : baseStatusLabel,
  );

  function startExportCountdown(): void {
    stopExportCountdown();
    exportCountdown = 5;
    exportCountdownTimer = setInterval(() => {
      exportCountdown = Math.max(0, exportCountdown - 1);
      if (exportCountdown <= 0) stopExportCountdown();
    }, 1000);
  }

  function stopExportCountdown(): void {
    if (exportCountdownTimer !== undefined) {
      clearInterval(exportCountdownTimer);
      exportCountdownTimer = undefined;
    }
    exportCountdown = 0;
  }

  async function requestDocxExport(): Promise<void> {
    if (!docxPipelineMode || !canEdit || !isPywebviewReady()) return;
    if (lastExportedRevision >= docRevision && exportDisplay !== "locked") return;
    const resp = await rteExportRequest(targetFile);
    if (!resp.ok || !resp.data) {
      exportDisplay = "failed";
      return;
    }
    exportDisplay = mapExportState(resp.data);
    startExportPoll();
  }

  function startExportPoll(): void {
    stopExportPoll();
    exportPollTimer = setInterval(async () => {
      if (!isPywebviewReady()) { stopExportPoll(); return; }
      const resp = await rteExportStatus(targetFile);
      if (!resp.ok || !resp.data) { stopExportPoll(); return; }
      exportDisplay = mapExportState(resp.data);
      lastExportedRevision = resp.data.last_exported_revision;
      if (resp.data.state !== "running") stopExportPoll();
    }, EXPORT_POLL_MS);
  }

  function stopExportPoll(): void {
    if (exportPollTimer !== undefined) {
      clearInterval(exportPollTimer);
      exportPollTimer = undefined;
    }
  }

  function serializeEditor(): string {
    if (!editor) return text;
    if (isPlainTextMode) return editor.getText({ blockSeparator: "\n" });
    if (directHtmlMode) return editor.getHTML();
    return htmlToMarkdown(editor.getHTML());
  }

  function scheduleSave() {
    if (!canEdit) return;
    status = "pending";
    disposeSaveStarted = false;
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => void flush(), AUTOSAVE_MS);
  }

  /** DOCX pipeline save: JSON revision to source.json; export via reason/idle. */
  async function flushDocx(reason: RteSaveReason): Promise<boolean> {
    if (!editor) { status = "idle"; return true; }
    status = "saving";
    errorText = "";
    const content = editor.getJSON() as unknown as Record<string, unknown>;
    const canonical = JSON.stringify(content);
    if (canonical === lastSavedDocJson && !migrationPending) {
      dirty = false;
      status = "saved";
      return true;
    }
    const resp = await rteDocumentSave(targetFile, { content, base_revision: docRevision, reason });
    if (!resp.ok) {
      status = "error";
      errorText = resp.error.code === "RTE_REVISION_STALE"
        ? "Document changed elsewhere — reopen the file"
        : resp.error.message;
      return false;
    }
    const saved = resp.data;
    if (!saved) {
      status = "error";
      errorText = "Empty save response";
      return false;
    }
    docRevision = saved.revision;
    lastSavedDocJson = canonical;
    migrationPending = false;
    dirty = false;
    status = "saved";
    if (saved.export_scheduled) {
      exportDisplay = "exporting";
      idleExport.cancel();
      stopExportCountdown();
      startExportPoll();
    } else if (!saved.skipped) {
      idleExport.bump();
      startExportCountdown();
    }
    return true;
  }

  async function flush(reason: RteSaveReason = "autosave"): Promise<boolean> {
    if (timer) { clearTimeout(timer); timer = undefined; }
    if (!canEdit) { status = "idle"; return true; }
    if (!dirty && !(docxPipelineMode && migrationPending)) { status = "saved"; return true; }
    if (!editor) { status = "idle"; return true; }
    if (!isPywebviewReady()) { status = "offline"; return false; }
    if (docxPipelineMode) return flushDocx(reason);
    status = "saving";
    errorText = "";
    // Serialize ONCE at debounced save time. Never on every keystroke.
    const nextText = serializeEditor();
    if (nextText === lastSaved) { dirty = false; status = "saved"; return true; }
    const resp = filePath
      ? await saveRteFile(targetFile, nextText)
      : await callBridge("notes_update", projectPath, nextText);
    if (!resp.ok) { status = "error"; errorText = resp.error.message; return false; }
    text = nextText;
    lastSaved = nextText;
    dirty = false;
    status = "saved";
    onSaved?.(nextText);
    return true;
  }

  export async function flushNow(): Promise<boolean> {
    // Manual/switch flushes schedule the DOCX export immediately (flow-tiptap §8).
    const saved = await flush("manual");
    if (saved && docxPipelineMode && exportDisplay !== "exporting" && (idleExport.pending || exportDisplay === "locked")) {
      idleExport.cancel();
      stopExportCountdown();
      await requestDocxExport();
    }
    return saved;
  }

  async function saveSnapshot(
    filePath: string,
    project: string,
    isDirectHtml: boolean,
    html: string,
    savedText: string,
  ) {
    if (!isPywebviewReady()) return;
    if (!canEdit) return;
    const nextText = isPlainTextMode ? new DOMParser().parseFromString(html, "text/html").body.textContent || "" : isDirectHtml ? html : htmlToMarkdown(html);
    if (nextText === savedText) return;
    const resp = filePath
      ? await saveRteFile(filePath, nextText)
      : await callBridge("notes_update", project, nextText);
    if (!resp.ok) {
      console.warn("NotesEditor final autosave failed", resp.error.message);
    }
  }

  let disposeSaveStarted = false;

  function savePendingBeforeDispose() {
    if (disposeSaveStarted || !dirty || !editor) return;
    disposeSaveStarted = true;
    if (docxPipelineMode) {
      if (!canEdit || !isPywebviewReady()) return;
      const content = editor.getJSON() as unknown as Record<string, unknown>;
      void rteDocumentSave(targetFile, {
        content,
        base_revision: docRevision,
        reason: "switch",
      });
      return;
    }
    const pendingHtml = editor.getHTML();
    const filePath = targetFile;
    const project = projectPath;
    const isDirectHtml = directHtmlMode;
    const savedText = lastSaved;
    void saveSnapshot(filePath, project, isDirectHtml, pendingHtml, savedText);
  }

  function toggleFullscreen() {
    fullscreen = !fullscreen;
    if (fullscreen) {
      document.body.style.overflow = 'hidden';
      recalcHeight();
      window.addEventListener('resize', recalcHeight);
    } else {
      document.body.style.overflow = '';
      window.removeEventListener('resize', recalcHeight);
      const area = hostEl?.querySelector('.ne-textarea') as HTMLElement | null;
      if (area) { area.style.maxHeight = ''; area.style.height = ''; }
    }
  }

  function recalcHeight() {
    if (!fullscreen || !toolbarEl || !hostEl) return;
    const area = hostEl.querySelector('.ne-textarea') as HTMLElement | null;
    if (!area) return;
    area.style.maxHeight = 'none';
    const h = window.innerHeight - toolbarEl.getBoundingClientRect().height - 18;
    area.style.height = `${h}px`;
  }

  function closeAllPopovers() {
    colorOpen = false; tableOpen = false; emojiOpen = false;
    linkOpen = false; imgOpen = false; helpOpen = false;
  }

  function onWindowClick(e: MouseEvent) {
    const t = e.target as HTMLElement;
    if (t.closest('.ne-popover-wrap')) return;
    // Never run editor popover-close logic for clicks on titlebar chrome,
    // window controls, confirm/overlay regions, or modal dialogs. These must
    // navigate/act unimpeded even while the RTE window listener is attached.
    if (t.closest('.titlebar, .nav-tab, .notif-btn, .notif-popover, .win-controls, .win-btn, .page-header, .confirm-overlay, .dialog-backdrop')) return;
    closeAllPopovers();
  }

  function onEditorUpdate() {
    if (!editor || !canEdit || hydrating) return;
    dirty = true;
    scheduleSave();
  }

  // ── Image paste/drop upload (Win+Shift+S → Ctrl+V) ──

  function extractImageFile(dt: DataTransfer | null): File | null {
    if (!dt) return null;
    for (const item of Array.from(dt.items ?? [])) {
      if (item.kind === "file" && /^image\/(png|jpe?g|gif|webp)$/i.test(item.type)) {
        return item.getAsFile();
      }
    }
    return null;
  }

  function fileToBase64(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = () => reject(new Error("Could not read image from clipboard"));
      reader.onload = () => {
        const url = String(reader.result || "");
        const comma = url.indexOf(",");
        if (comma < 0) reject(new Error("Unexpected clipboard image data"));
        else resolve(url.slice(comma + 1));
      };
      reader.readAsDataURL(file);
    });
  }

  async function uploadAndInsertImage(file: File, pos?: number): Promise<void> {
    if (!editor) return;
    try {
      const b64 = await fileToBase64(file);
      const resp = await rteImageSave(targetFile, b64);
      if (!resp.ok || !resp.data) {
        status = "error";
        errorText = resp.ok ? "Empty image save response" : resp.error.message;
        return; // no broken image node on failure
      }
      const attrs = {
        src: resp.data.data_uri,
        assetId: resp.data.asset_id,
        assetSrc: resp.data.rel_src,
        alt: file.name || "Screenshot",
      };
      const chain = editor.chain().focus();
      if (typeof pos === "number") chain.insertContentAt(pos, { type: "image", attrs }).run();
      else chain.insertContent({ type: "image", attrs }).run();
      rev++;
    } catch (err) {
      status = "error";
      errorText = err instanceof Error ? err.message : String(err);
    }
  }

  /** Hydrate `.rte/assets/...` image refs (md files) into data URIs for display. */
  async function hydrateAssetImages(inst: Editor): Promise<void> {
    if (!isPywebviewReady()) return;
    const refs: { pos: number; src: string }[] = [];
    inst.state.doc.descendants((node, pos) => {
      if (node.type.name === "image") {
        const src = String(node.attrs.src || "");
        if (src.startsWith(".rte/assets/")) refs.push({ pos, src });
      }
    });
    for (const ref of refs) {
      const resp = await rteAssetRead(targetFile, ref.src);
      if (!resp.ok || !resp.data) continue;
      const node = inst.state.doc.nodeAt(ref.pos);
      if (!node || node.type.name !== "image") continue;
      hydrating = true;
      try {
        const tr = inst.state.tr.setNodeMarkup(ref.pos, undefined, {
          ...node.attrs,
          src: resp.data.data_uri,
          assetSrc: ref.src,
        });
        tr.setMeta("addToHistory", false);
        inst.view.dispatch(tr);
      } finally {
        hydrating = false;
      }
    }
  }

  function onKeydown(e: KeyboardEvent) {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
      e.preventDefault();
      void flushNow();
      return;
    }
    if (!(e.ctrlKey || e.metaKey) || capability === "unsupported" || !hostEl?.contains(e.target as Node)) return;
    if (e.key === "+" || e.key === "=") {
      e.preventDefault();
      zoomIn();
    } else if (e.key === "-") {
      e.preventDefault();
      zoomOut();
    }
  }

  function setZoom(next: number) {
    zoomPercent = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, next));
  }

  function zoomIn() { setZoom(zoomPercent + ZOOM_STEP); }
  function zoomOut() { setZoom(zoomPercent - ZOOM_STEP); }

  function onZoomWheel(e: WheelEvent) {
    if (!e.ctrlKey || capability === "unsupported") return;
    e.preventDefault();
    if (e.deltaY < 0) zoomIn();
    else if (e.deltaY > 0) zoomOut();
  }

  // ── Active-state helpers (reactive via a toolbar-only token) ──

  function isActive(name: string, attrs?: Record<string, unknown>): boolean {
    void uiTick;
    return editor?.isActive(name, attrs) ?? false;
  }

  /** TextAlign marks live as a node attribute; check it directly. */
  function alignIs(value: string): boolean {
    void uiTick;
    if (!editor) return false;
    const cur = (editor.getAttributes("paragraph").textAlign as string) || (editor.getAttributes("heading").textAlign as string) || "";
    return cur === value;
  }

  function applyFont() {
    if (!fontSelVal) return;
    editor?.chain().focus().setFontFamily(fontSelVal).run();
    rev++;
    (document.getElementById('ne-font-select') as HTMLSelectElement | null)?.blur();
  }

  function applySize() {
    const px = parseInt(sizeSelVal);
    if (isNaN(px)) editor?.chain().focus().unsetFontSize().run();
    else editor?.chain().focus().setFontSize(`${px}px`).run();
    rev++;
    (document.getElementById('ne-size-select') as HTMLSelectElement | null)?.blur();
  }

  function formatLink() {
    if (!editor) return;
    const prev = editor.getAttributes("link").href as string | undefined;
    linkEditing = !!prev;
    linkUrl = prev || "";
    openLinkDialog();
  }

  function openLinkDialog() {
    closeAllPopovers();
    linkOpen = true;
    tick().then(() => document.getElementById('ne-link-input')?.focus());
  }

  function closeLinkDialog() {
    linkOpen = false;
    linkUrl = '';
    linkEditing = false;
  }

  function confirmLink() {
    const url = linkUrl.trim();
    if (linkEditing) {
      if (url) editor?.chain().focus().extendMarkRange("link").setLink({ href: url }).run();
      else editor?.chain().focus().extendMarkRange("link").unsetLink().run();
    } else if (url) {
      editor?.chain().focus().setLink({ href: url }).run();
    }
    linkOpen = false;
    rev++;
  }

  function onLinkKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') { e.preventDefault(); confirmLink(); }
    else if (e.key === 'Escape') { e.preventDefault(); closeLinkDialog(); }
  }

  // ── Image dialog (browses local laptop images via the Python bridge) ──

  async function formatImage() {
    if (!editor) return;
    imgUrl = '';
    imgAlt = '';
    closeAllPopovers();
    if (isPywebviewReady()) {
      // Open the native file dialog and embed the chosen image as a data URI
      // (so it persists in notes.md without external references).
      const resp = await callBridge<{ data_uri: string | null; name?: string }>("util_choose_image");
      if (!resp.ok) { status = "error"; errorText = resp.error.message; return; }
      if (!resp.data?.data_uri) return; // user cancelled
      imgUrl = resp.data.data_uri;
      imgAlt = resp.data.name || '';
      imgOpen = true;
      tick().then(() => document.getElementById('ne-img-alt')?.focus());
      return;
    }
    // Browser-preview fallback: no native file dialog, so keep URL entry usable.
    imgOpen = true;
    tick().then(() => document.getElementById('ne-img-input')?.focus());
  }

  function closeImageDialog() {
    imgOpen = false;
    imgUrl = '';
    imgAlt = '';
  }

  function confirmImage() {
    const url = imgUrl.trim();
    if (url) {
      void insertImageAsAsset(url, imgAlt.trim());
    }
    imgOpen = false;
  }

  /** Insert a picked image; data URIs become asset files (D-0012), with a
   *  plain data-URI embed as the fallback so insertion never blocks. */
  async function insertImageAsAsset(url: string, alt: string): Promise<void> {
    if (!editor) return;
    if (url.startsWith("data:image/") && isPywebviewReady()) {
      const comma = url.indexOf(",");
      const b64 = comma >= 0 ? url.slice(comma + 1) : "";
      if (b64) {
        const resp = await rteImageSave(targetFile, b64);
        if (resp.ok && resp.data) {
          editor.chain().focus().insertContent({
            type: "image",
            attrs: {
              src: resp.data.data_uri,
              assetId: resp.data.asset_id,
              assetSrc: resp.data.rel_src,
              alt,
            },
          }).run();
          rev++;
          return;
        }
      }
    }
    editor.chain().focus().setImage({ src: url, alt }).run();
    rev++;
  }

  function onImageKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') { e.preventDefault(); confirmImage(); }
    else if (e.key === 'Escape') { e.preventDefault(); closeImageDialog(); }
  }

  function applyColor(color: string) {
    if (colorMode === 'back') editor?.chain().focus().toggleHighlight({ color }).run();
    else editor?.chain().focus().setColor(color).run();
    rev++;
    colorOpen = false;
  }

  function insertTable() {
    const { rows, cols } = tableHover;
    editor?.chain().focus().insertTable({ rows, cols, withHeaderRow: true }).run();
    tableOpen = false;
    rev++;
  }

  function insertEmoji(emoji: string) {
    editor?.chain().focus().insertContent(emoji).run();
    emojiOpen = false;
    rev++;
  }

  // ── Lifecycle ──

  function resetEditorChrome() {
    try {
      fullscreen = false;
      closeAllPopovers();
      if (typeof document !== "undefined") document.body.style.overflow = '';
      const area = hostEl?.querySelector('.ne-textarea') as HTMLElement | null;
      if (area) { area.style.maxHeight = ''; area.style.height = ''; }
    } catch {
      // Best-effort cleanup only. Never block top-level menu navigation.
    }
  }

  onMount(() => {
    onReady?.({ flushNow });
    window.addEventListener("app:navigate-away", resetEditorChrome);
    window.addEventListener("keydown", onKeydown);
  });

  onDestroy(() => {
    onReady?.(undefined);
    savePendingBeforeDispose();
    idleExport.cancel();
    stopExportCountdown();
    stopExportPoll();
    if (timer) clearTimeout(timer);
    if (typeof window !== "undefined") window.removeEventListener('resize', recalcHeight);
    if (typeof document !== "undefined") document.body.style.overflow = '';
    if (typeof window !== "undefined") window.removeEventListener('click', onWindowClick);
    if (typeof window !== "undefined") window.removeEventListener("app:navigate-away", resetEditorChrome);
    if (typeof window !== "undefined") window.removeEventListener("keydown", onKeydown);
  });

  let lastPath = "";
  let windowClickBound = false;

  // SSR guard: the app renders client-side in pywebview, but the test harness
  // renders server-side (window undefined there). Only build the Editor where a
  // DOM exists, so the toolbar still renders under SSR.
  const isBrowser = typeof window !== "undefined" && typeof document !== "undefined";

  function toEditorHtml(value: string, direct: boolean, plainText: boolean): string {
    if (direct) return value;
    if (plainText) return `<pre>${escapeHtml(value)}</pre>`;
    return renderMarkdown(value);
  }

  $effect(() => {
    if (!isBrowser || !hostEl || editor) return;
    const startText = untrack(() => initialNotes ?? "");
    const startPath = untrack(() => targetFile);
    const editableNow = untrack(() => canEdit);
    const direct = untrack(() => directHtmlMode);
    const plainText = untrack(() => isPlainTextMode);
    const format = untrack(() => fileFormat);
    const pipeline = untrack(() => docxPipelineMode);
    const startDoc = untrack(() => initialDoc);
    const startRevision = untrack(() => initialRevision ?? 0);
    const migrate = untrack(() => needsMigration);
    const shouldMigrate = pipeline && migrate;
    text = startText;
    lastSaved = startText;
    lastPath = startPath;
    dirty = false;
    disposeSaveStarted = false;
    docRevision = startRevision;
    lastExportedRevision = startRevision;
    lastSavedDocJson = "";
    migrationPending = shouldMigrate;
    exportDisplay = "idle";

    // Pipeline docs load their JSON source directly; migration passes
    // mammoth HTML through initialNotes exactly once.
    const startContent = pipeline && startDoc
      ? (startDoc as object)
      : toEditorHtml(startText, direct, plainText);

    const instance = new Editor({
      element: hostEl,
      editable: editableNow,
      content: startContent,
      extensions: [
        StarterKit.configure({
          // StarterKit v3 bundles bold/italic/strike/code, heading, blockquote,
          // codeBlock, bulletList/orderedList/listItem/listKeymap, hardBreak,
          // horizontalRule, undoRedo, link, underline.
          link: { openOnClick: false, autolink: true },
        }),
        Subscript,
        Superscript,
        TextStyle,
        FontFamily,
        Color,
        FontSize,
        Highlight.configure({ multicolor: true }),
        AssetImage.configure({ inline: true, allowBase64: true }),
        TaskList,
        TaskItem.configure({ nested: false }),
        TextAlign.configure({ types: ["heading", "paragraph"] }),
        Placeholder.configure({
          placeholder: format === "docx"
            ? "Write here (autosaves to Word)…"
            : format === "html"
              ? "Write here (autosaves)…"
              : "Write project notes (autosaves to notes.md)…",
        }),
        Table.configure({ resizable: true }),
        TableRow,
        TableHeader,
        TableCell,
      ],
      editorProps: {
        attributes: {
          class: "ne-textarea ne-editor-area",
          "aria-multiline": "true",
          role: "textbox",
        },
        // Manual paste/drop image capture (no FileHandler dep): consume the
        // event exactly once so duplicate nodes can never appear (spec §24).
        handlePaste: (_view, event) => {
          if (plainText || !untrack(() => canEdit) || !isPywebviewReady()) return false;
          const file = extractImageFile(event.clipboardData);
          if (!file) return false;
          event.preventDefault();
          void uploadAndInsertImage(file);
          return true;
        },
        handleDrop: (view, event, _slice, moved) => {
          if (moved || plainText || !untrack(() => canEdit) || !isPywebviewReady()) return false;
          const file = extractImageFile(event.dataTransfer);
          if (!file) return false;
          event.preventDefault();
          const pos = view.posAtCoords({ left: event.clientX, top: event.clientY })?.pos;
          void uploadAndInsertImage(file, pos);
          return true;
        },
      },
    });
    queueMicrotask(() => {
      if (editor !== instance) return;
      instance.on("transaction", scheduleToolbarRefresh);
      scheduleToolbarRefresh();
    });
    instance.on("update", onEditorUpdate);
    editor = instance;
    rev++;
    if (shouldMigrate) {
      // Persist the migrated legacy .docx content as revision 1 + first export.
      dirty = true;
      queueMicrotask(() => {
        if (editor !== instance) return;
        void flush("migration");
      });
    } else if (!pipeline && !plainText) {
      void hydrateAssetImages(instance);
    }
    if (!windowClickBound) {
      windowClickBound = true;
      window.addEventListener('click', onWindowClick);
    }
    return () => {
      savePendingBeforeDispose();
      instance.off("transaction", scheduleToolbarRefresh);
      if (toolbarRefreshFrame !== undefined) {
        cancelAnimationFrame(toolbarRefreshFrame);
        toolbarRefreshFrame = undefined;
      }
      try {
        instance.destroy();
      } catch (err) {
        console.warn("NotesEditor destroy failed", err);
      }
      editor = null;
      rev++;
    };
  });

  $effect(() => {
    const editableNow = canEdit;
    if (!editor) return;
    untrack(() => editor?.setEditable(editableNow, false));
  });

  $effect(() => {
    const nextPath = targetFile;
    if (!editor || nextPath === lastPath) return;
    const nextText = untrack(() => initialNotes ?? "");
    const direct = untrack(() => directHtmlMode);
    const plainText = untrack(() => isPlainTextMode);
    const pipeline = untrack(() => docxPipelineMode);
    const nextDoc = untrack(() => initialDoc);
    const nextRevision = untrack(() => initialRevision ?? 0);
    const migrate = untrack(() => needsMigration);
    const shouldMigrate = pipeline && migrate;
    lastPath = nextPath;
    text = nextText;
    lastSaved = nextText;
    dirty = false;
    disposeSaveStarted = false;
    idleExport.cancel();
    stopExportCountdown();
    stopExportPoll();
    docRevision = nextRevision;
    lastExportedRevision = nextRevision;
    lastSavedDocJson = "";
    migrationPending = shouldMigrate;
    exportDisplay = "idle";
    if (pipeline && nextDoc) {
      editor.commands.setContent(nextDoc as object, { emitUpdate: false });
    } else {
      editor.commands.setContent(toEditorHtml(nextText, direct, plainText), { emitUpdate: false });
      if (!pipeline && !plainText) void hydrateAssetImages(editor);
    }
    if (shouldMigrate) {
      dirty = true;
      queueMicrotask(() => {
        if (lastPath !== nextPath) return;
        void flush("migration");
      });
    }
  });
</script>

<div class="ne-root" class:fullscreen>
  <div class="ne-toolbar" bind:this={toolbarEl}>
    <div class="ne-tools" aria-label="Visual formatting" class:ne-tools-disabled={!richToolbarEnabled}>

      <!-- Row: Undo/Redo | Font | Size -->
      <button type="button" class="ne-tbtn" disabled={!richToolbarEnabled} title="Undo" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().undo().run(); rev++; }}>↩</button>
      <button type="button" class="ne-tbtn" disabled={!richToolbarEnabled} title="Redo" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().redo().run(); rev++; }}>↪</button>
      <span class="ne-sep"></span>
      <select id="ne-font-select" class="ne-tbtn ne-tselect" bind:value={fontSelVal} onchange={applyFont} onclick={(e) => e.stopPropagation()}>
        {#each FONTS as f}
          <option value={f.value}>{f.label}</option>
        {/each}
      </select>
      <select id="ne-size-select" class="ne-tbtn ne-tselect" bind:value={sizeSelVal} onchange={applySize} onclick={(e) => e.stopPropagation()}>
        <option value="">Size</option>
        {#each SIZES as s}
          <option value={s}>{s}</option>
        {/each}
      </select>
      <span class="ne-sep"></span>

      <!-- Row: B I U S | Sup Sub -->
      <button type="button" class="ne-tbtn" disabled={!richToolbarEnabled} class:active={isActive('bold')} title="Bold" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().toggleBold().run(); rev++; }}><strong>B</strong></button>
      <button type="button" class="ne-tbtn" disabled={!richToolbarEnabled} class:active={isActive('italic')} title="Italic" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().toggleItalic().run(); rev++; }}><em>I</em></button>
      <button type="button" class="ne-tbtn" disabled={!richToolbarEnabled} class:active={isActive('underline')} title="Underline" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().toggleUnderline().run(); rev++; }}><u>U</u></button>
      <button type="button" class="ne-tbtn" disabled={!richToolbarEnabled} class:active={isActive('strike')} title="Strikethrough" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().toggleStrike().run(); rev++; }}><s>S</s></button>
      <span class="ne-sep"></span>
      <button type="button" class="ne-tbtn" disabled={!richToolbarEnabled} class:active={isActive('superscript')} title="Superscript" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().toggleSuperscript().run(); rev++; }}>x<sup>2</sup></button>
      <button type="button" class="ne-tbtn" disabled={!richToolbarEnabled} class:active={isActive('subscript')} title="Subscript" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().toggleSubscript().run(); rev++; }}>x<sub>2</sub></button>
      <span class="ne-sep"></span>

      <!-- Row: Forecolor | Backcolor -->
      <div class="ne-popover-wrap">
        <button type="button" class="ne-tbtn" disabled={!richToolbarEnabled} title="Text color" onmousedown={(e) => { e.preventDefault(); colorMode='fore'; colorOpen=!colorOpen; tableOpen=false; emojiOpen=false; }}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M11 4L4 20h3l1-3h8l1 3h3L13 4h-2z"/><line x1="7.5" y1="14" x2="16.5" y2="14"/></svg>
        </button>
        <button type="button" class="ne-tbtn" disabled={!richToolbarEnabled} title="Background color" onmousedown={(e) => { e.preventDefault(); colorMode='back'; colorOpen=!colorOpen; tableOpen=false; emojiOpen=false; }}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="3" y="3" width="18" height="18" rx="2"/></svg>
        </button>
        {#if colorOpen}
          <div class="ne-popover">
            <div class="ne-color-grid">
              {#each COLORS as c}
                <button type="button" class="ne-swatch" style="background:{c}" title={c} aria-label={c} onmousedown={(e) => { e.preventDefault(); applyColor(c); }}></button>
              {/each}
            </div>
          </div>
        {/if}
      </div>
      <span class="ne-sep"></span>

      <!-- Row: H1 H2 H3 P | Quote Code -->
      <button type="button" class="ne-tbtn" disabled={!richToolbarEnabled} class:active={isActive('heading',{level:1})} title="Heading 1" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().toggleHeading({ level: 1 }).run(); rev++; }}>H1</button>
      <button type="button" class="ne-tbtn" disabled={!richToolbarEnabled} class:active={isActive('heading',{level:2})} title="Heading 2" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().toggleHeading({ level: 2 }).run(); rev++; }}>H2</button>
      <button type="button" class="ne-tbtn" disabled={!richToolbarEnabled} class:active={isActive('heading',{level:3})} title="Heading 3" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().toggleHeading({ level: 3 }).run(); rev++; }}>H3</button>
      <button type="button" class="ne-tbtn" disabled={!richToolbarEnabled} class:active={isActive('paragraph')} title="Paragraph" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().setParagraph().run(); rev++; }}>¶</button>
      <span class="ne-sep"></span>
      <button type="button" class="ne-tbtn" disabled={!richToolbarEnabled} class:active={isActive('blockquote')} title="Blockquote" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().toggleBlockquote().run(); rev++; }}>❝</button>
      <button type="button" class="ne-tbtn" disabled={!richToolbarEnabled} class:active={isActive('code')} title="Inline code" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().toggleCode().run(); rev++; }}>{@html '&lt;/&gt;'}</button>
      <button type="button" class="ne-tbtn" disabled={!richToolbarEnabled} class:active={isActive('codeBlock')} title="Code block" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().toggleCodeBlock().run(); rev++; }}>{"</>"}</button>
      <span class="ne-sep"></span>

      <!-- Row: OL UL | Indent Outdent -->
      <button type="button" class="ne-tbtn" disabled={!richToolbarEnabled} class:active={isActive('orderedList')} title="Numbered list" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().toggleOrderedList().run(); rev++; }}>1.</button>
      <button type="button" class="ne-tbtn" disabled={!richToolbarEnabled} class:active={isActive('bulletList')} title="Bulleted list" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().toggleBulletList().run(); rev++; }}>•</button>
      <span class="ne-sep"></span>
      <button type="button" class="ne-tbtn" disabled={!richToolbarEnabled} title="Indent" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().sinkListItem('listItem').run(); rev++; }}>→</button>
      <button type="button" class="ne-tbtn" disabled={!richToolbarEnabled} title="Outdent" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().liftListItem('listItem').run(); rev++; }}>←</button>
      <span class="ne-sep"></span>

      <!-- Row: Align L C R J -->
      <button type="button" class="ne-tbtn" disabled={!richToolbarEnabled} class:active={alignIs('left')} title="Align left" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().setTextAlign('left').run(); rev++; }}>≡L</button>
      <button type="button" class="ne-tbtn" disabled={!richToolbarEnabled} class:active={alignIs('center')} title="Align center" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().setTextAlign('center').run(); rev++; }}>≡C</button>
      <button type="button" class="ne-tbtn" disabled={!richToolbarEnabled} class:active={alignIs('right')} title="Align right" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().setTextAlign('right').run(); rev++; }}>≡R</button>
      <button type="button" class="ne-tbtn" disabled={!richToolbarEnabled} class:active={alignIs('justify')} title="Justify" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().setTextAlign('justify').run(); rev++; }}>≡J</button>
      <span class="ne-sep"></span>

      <!-- Row: Link HR Table Image Emoji -->
      <div class="ne-popover-wrap">
        <button type="button" class="ne-tbtn" disabled={!richToolbarEnabled} class:active={isActive('link')} title="Link" onmousedown={(e) => { e.preventDefault(); formatLink(); }}>🔗</button>
        {#if linkOpen}
          <div class="ne-popover ne-link-pop">
            <label class="ne-field-label" for="ne-link-input">{linkEditing ? 'Edit URL' : 'Link URL'}</label>
            <input id="ne-link-input" class="ne-input" type="url" bind:value={linkUrl} placeholder="https://example.com" onkeydown={onLinkKeydown} onclick={(e) => e.stopPropagation()} onmousedown={(e) => e.stopPropagation()} />
            <div class="ne-dialog-actions">
              {#if linkEditing}
                <button type="button" class="ne-tbtn ne-act-btn" title="Remove link" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().extendMarkRange('link').unsetLink().run(); linkOpen=false; rev++; }}>Remove</button>
              {/if}
              <button type="button" class="ne-tbtn" disabled={!richToolbarEnabled} title="Cancel" onmousedown={(e) => { e.preventDefault(); closeLinkDialog(); }}>Cancel</button>
              <button type="button" class="ne-tbtn ne-act-btn" title="Apply" onmousedown={(e) => { e.preventDefault(); confirmLink(); }}>OK</button>
            </div>
          </div>
        {/if}
      </div>
      <button type="button" class="ne-tbtn" disabled={!richToolbarEnabled} title="Horizontal rule" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().setHorizontalRule().run(); rev++; }}>HR</button>
      <div class="ne-popover-wrap">
        <button type="button" class="ne-tbtn" disabled={!richToolbarEnabled} title="Table" onmousedown={(e) => { e.preventDefault(); tableOpen=!tableOpen; colorOpen=false; emojiOpen=false; }}>⊞</button>
        {#if tableOpen}
          <div class="ne-popover ne-table-pop">
              {#each Array(10) as _, r}
                <div class="ne-table-row">
                  {#each Array(10) as _, c}
                    <div role="gridcell" tabindex="0" aria-label="Insert {r + 1} by {c + 1} table" class="ne-tcell" class:ne-thover={r < tableHover.rows && c < tableHover.cols} onmouseenter={() => tableHover = { rows: r + 1, cols: c + 1 }} onmousedown={(e) => { e.preventDefault(); tableHover = { rows: r + 1, cols: c + 1 }; }} onclick={() => insertTable()} onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); tableHover = { rows: r + 1, cols: c + 1 }; insertTable(); } }}></div>
                  {/each}
                </div>
              {/each}
            <div class="ne-table-label">{tableHover.rows} × {tableHover.cols}</div>
          </div>
        {/if}
      </div>
      <div class="ne-popover-wrap">
        <button type="button" class="ne-tbtn" disabled={!richToolbarEnabled} title="Image" onmousedown={(e) => { e.preventDefault(); formatImage(); }}>🖼</button>
        {#if imgOpen}
          <div class="ne-popover ne-link-pop">
            {#if imgUrl.startsWith('data:image/')}
              <div class="ne-image-picked">Local image selected</div>
            {:else}
              <label class="ne-field-label" for="ne-img-input">Image URL</label>
              <input id="ne-img-input" class="ne-input" type="url" bind:value={imgUrl} placeholder="https://example.com/img.png" onkeydown={onImageKeydown} onclick={(e) => e.stopPropagation()} onmousedown={(e) => e.stopPropagation()} />
            {/if}
            <label class="ne-field-label ne-alt-label" for="ne-img-alt">Description (alt)</label>
            <input id="ne-img-alt" class="ne-input" type="text" bind:value={imgAlt} placeholder="Optional alt text" onkeydown={onImageKeydown} onclick={(e) => e.stopPropagation()} onmousedown={(e) => e.stopPropagation()} />
            <div class="ne-dialog-actions">
              <button type="button" class="ne-tbtn" disabled={!richToolbarEnabled} title="Cancel" onmousedown={(e) => { e.preventDefault(); closeImageDialog(); }}>Cancel</button>
              <button type="button" class="ne-tbtn ne-act-btn" title="Insert" onmousedown={(e) => { e.preventDefault(); confirmImage(); }}>Insert</button>
            </div>
          </div>
        {/if}
      </div>
      <div class="ne-popover-wrap">
        <button type="button" class="ne-tbtn ne-emoji-trigger" title="Emoji" onmousedown={(e) => { e.preventDefault(); emojiOpen=!emojiOpen; colorOpen=false; tableOpen=false; }}>😊</button>
        {#if emojiOpen}
          <div class="ne-popover ne-emoji-pop">
            {#each EMOJIS as em}
              <button type="button" class="ne-emoji-btn" onmousedown={(e) => { e.preventDefault(); insertEmoji(em); }}>{em}</button>
            {/each}
          </div>
        {/if}
      </div>
      <span class="ne-sep"></span>

      <!-- Row: Todo ClearFormat -->
      <button type="button" class="ne-tbtn" disabled={!richToolbarEnabled} class:active={isActive('taskList')} title="Checklist" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().toggleTaskList().run(); rev++; }}>☑</button>
      <button type="button" class="ne-tbtn" disabled={!richToolbarEnabled} title="Clear formatting" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().unsetAllMarks().clearNodes().run(); rev++; }}>↺</button>
    </div>

    <div class="ne-actions">
      {#if capability !== "unsupported"}
        <div class="ne-zoom" aria-label="Editor zoom">
          <button type="button" class="ne-tbtn ne-zoom-btn" aria-label="Zoom out" title="Zoom out" disabled={zoomPercent <= ZOOM_MIN} onmousedown={(e) => { e.preventDefault(); zoomOut(); }}>−</button>
          <button type="button" class="ne-tbtn ne-zoom-val" aria-label="Reset zoom to 100%" title="Reset zoom to 100%" onmousedown={(e) => { e.preventDefault(); setZoom(100); }}>{zoomPercent}%</button>
          <button type="button" class="ne-tbtn ne-zoom-btn" aria-label="Zoom in" title="Zoom in" disabled={zoomPercent >= ZOOM_MAX} onmousedown={(e) => { e.preventDefault(); zoomIn(); }}>+</button>
        </div>
      {/if}
      <div class="ne-popover-wrap">
        <button type="button" class="ne-tbtn ne-help-btn" class:active={helpOpen} aria-label="Show editor shortcuts" aria-expanded={helpOpen} title="Shortcuts" onmousedown={(e) => { e.preventDefault(); const next = !helpOpen; closeAllPopovers(); helpOpen = next; }}>?</button>
        {#if helpOpen}
          <div class="ne-popover ne-help-pop">
            <div class="ne-help-row"><kbd class="ne-kbd">Ctrl+S</kbd><span>{docxPipelineMode ? 'Save + export DOCX now' : 'Save'}</span></div>
            <div class="ne-help-row"><kbd class="ne-kbd">Ctrl+B/I/U</kbd><span>Bold, italic, underline</span></div>
            <div class="ne-help-row"><kbd class="ne-kbd">Ctrl+Z / Ctrl+Y</kbd><span>Undo / redo</span></div>
            <div class="ne-help-row"><kbd class="ne-kbd">Win+Shift+S</kbd><span>Capture, then Ctrl+V to paste</span></div>
            <div class="ne-help-row"><kbd class="ne-kbd">Drop image</kbd><span>Insert image file</span></div>
            <div class="ne-help-row"><kbd class="ne-kbd">Drag edge</kbd><span>Resize image or table column</span></div>
            {#if docxPipelineMode}
              <div class="ne-help-row"><kbd class="ne-kbd">DOCX</kbd><span>DOCX exports automatically 5s after Saved</span></div>
            {/if}
          </div>
        {/if}
      </div>
      <button type="button" class="ne-tbtn ne-fsbtn" class:active={fullscreen} title={fullscreen ? "Exit fullscreen" : "Fullscreen"} onmousedown={(e) => { e.preventDefault(); toggleFullscreen(); }}>
        {#if fullscreen}
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><polyline points="4 14 10 14 10 20"/><polyline points="20 10 14 10 14 4"/><line x1="14" y1="10" x2="21" y2="3"/><line x1="10" y1="14" x2="3" y2="21"/></svg>
        {:else}
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>
        {/if}
      </button>
      <div class="ne-status" class:err={status === "error" || capability === "unsupported"} class:off={status === "offline" || !canEdit} role="status" title={status === "error" ? errorText : (message || statusLabel)}>
        {#if status === "saving"}<span class="ne-dot">◌</span>{:else if status === "saved"}<span class="ne-dot ne-ok">✓</span>{/if}
        <span>{statusLabel}</span>
      </div>
    </div>
  </div>

  <div class="ne-editor-host" class:ne-docx-page={docxPipelineMode} style={`--ne-zoom:${zoomPercent / 100}`} onwheel={onZoomWheel} bind:this={hostEl}></div>
</div>

<style>
  .ne-root { display:flex; flex-direction:column; gap:6px; }
  .ne-root.fullscreen { position:fixed; top:0; left:0; width:100vw; height:100vh; z-index:9999; background:var(--main-bg); padding:12px 14px; }
  .ne-toolbar { display:flex; align-items:flex-start; justify-content:space-between; gap:8px; flex:0 0 auto; }
  .ne-tools { display:flex; gap:3px; align-items:center; flex-wrap:wrap; flex:1; }
  .ne-actions { display:flex; align-items:center; gap:8px; flex:0 0 auto; }
  .ne-sep { display:inline-block; width:1px; height:16px; background:var(--soft-white-border); margin:0 2px; flex:0 0 auto; }
  .ne-tbtn { min-width:26px; height:24px; padding:0 6px; border:1px solid var(--soft-white-border); border-radius:5px; background:var(--card-white); color:var(--color-ink); font-size:10px; font-weight:850; cursor:pointer; display:inline-flex; align-items:center; justify-content:center; gap:2px; white-space:nowrap; }
  .ne-tbtn:hover:not(:disabled) { border-color:var(--color-dbs-red); color:var(--color-dbs-red); }
  .ne-tbtn.active { background:var(--soft-pink-surface); border-color:var(--color-dbs-red); color:var(--color-dbs-red); }
  .ne-tbtn:active:not(:disabled) { transform:scale(0.94); background:var(--soft-pink-surface); border-color:var(--color-dbs-red); }
  .ne-tbtn:disabled { opacity:0.45; cursor:not-allowed; }
  .ne-tools-disabled { opacity:0.78; }
  .ne-tselect:active { transform:none; }
  .ne-tbtn s { color:inherit; text-decoration:line-through; }
  .ne-tselect { min-width:68px; width:auto; padding:0 16px 0 6px; appearance:none; font-size:9px; background-image:linear-gradient(45deg,transparent 50%,var(--text-strong) 50%),linear-gradient(135deg,var(--text-strong) 50%,transparent 50%); background-position:calc(100% - 6px) 10px,calc(100% - 2px) 10px; background-size:4px 4px,4px 4px; background-repeat:no-repeat; background-color:var(--card-white); }
  .ne-zoom { display:inline-flex; align-items:center; gap:3px; }
  .ne-zoom-btn { min-width:24px; }
  .ne-zoom-val { min-width:48px; }
  .ne-fsbtn { min-width:30px; padding:0; }
  .ne-root.fullscreen .ne-tbtn { border-color:var(--input-border); }
  .ne-popover-wrap { position:relative; display:inline-flex; }
  .ne-popover { position:absolute; top:calc(100% + 4px); left:50%; transform:translateX(-50%); z-index:100; background:var(--card-white); border:1px solid var(--soft-white-border); border-radius:6px; box-shadow:var(--shadow-card); padding:6px; min-width:160px; max-height:320px; overflow-y:auto; }
  .ne-table-pop { left:auto; right:0; transform:none; padding:8px; }
  .ne-emoji-pop { left:auto; right:0; transform:none; display:grid; grid-template-columns:repeat(8,1fr); gap:2px; width:210px; padding:6px; }
  .ne-color-grid { display:grid; grid-template-columns:repeat(8,1fr); gap:2px; width:172px; }
  .ne-swatch { width:100%; aspect-ratio:1; border:1px solid var(--soft-white-border); border-radius:3px; cursor:pointer; padding:0; }
  .ne-swatch:hover { transform:scale(1.15); border-color:var(--color-dbs-red); }
  .ne-table-row { display:flex; gap:1px; margin-bottom:1px; }
  .ne-tcell { width:14px; height:14px; border:1px solid var(--input-border); border-radius:1px; cursor:pointer; }
  .ne-tcell.ne-thover { background:var(--color-dbs-red); border-color:var(--color-dbs-red); }
  .ne-table-label { text-align:center; font-size:9px; font-weight:800; color:var(--color-muted); margin:4px 0; }
  .ne-link-pop { left:auto; right:0; transform:none; padding:8px; width:200px; display:flex; flex-direction:column; gap:2px; }
  .ne-help-pop { left:auto; right:0; transform:none; padding:8px; width:250px; display:flex; flex-direction:column; gap:6px; }
  .ne-help-row { display:grid; grid-template-columns:auto 1fr; gap:8px; align-items:center; font-size:10px; color:var(--color-muted); line-height:1.3; }
  .ne-kbd { display:inline-flex; align-items:center; justify-content:center; min-height:18px; padding:1px 5px; border:1px solid var(--soft-white-border); border-radius:4px; background:var(--soft-pink-surface); color:var(--color-dbs-red); font-size:9px; font-weight:850; white-space:nowrap; }
  .ne-field-label { font-size:9px; font-weight:800; color:var(--color-muted); text-transform:uppercase; letter-spacing:0.3px; }
  .ne-alt-label { margin-top:4px; }
  .ne-image-picked { padding:4px 6px; border:1px solid var(--soft-white-border); border-radius:4px; font-size:10px; font-weight:800; color:var(--color-muted); background:var(--soft-pink-surface); }
  .ne-input { width:100%; padding:4px 6px; border:1px solid var(--soft-white-border); border-radius:4px; font-size:11px; font-family:var(--font); color:var(--color-ink); background:var(--card-white); outline:none; }
  .ne-input:focus { border-color:var(--color-dbs-red); }
  .ne-dialog-actions { display:flex; gap:4px; justify-content:flex-end; margin-top:6px; }
  .ne-act-btn { background:var(--soft-pink-surface); border-color:var(--color-dbs-red); color:var(--color-dbs-red); }
  .ne-emoji-btn { font-size:16px; width:22px; height:22px; border:0; background:transparent; cursor:pointer; border-radius:3px; padding:0; display:inline-flex; align-items:center; justify-content:center; }
  .ne-emoji-btn:hover { background:var(--soft-pink-surface); }

  /* Editor surface — Tiptap mounts its contenteditable inside this host.
     Default font is Times New Roman (DECISIONS D-0007 / bug 3 fix). */
  .ne-editor-host { width:100%; overflow-x:auto; }
  :global(.ne-editor-host .ne-textarea) { width:100%; min-height:120px; max-height:300px; padding:10px; background:var(--color-workspace-panel); border:1px solid var(--soft-white-border); border-radius:6px; font-size:12px; font-family:"Times New Roman", serif; color:var(--color-ink); resize:vertical; outline:none; line-height:1.5; overflow-y:auto; flex:1 1 auto; zoom:var(--ne-zoom, 1); }
  /* DOCX page: 184.6mm printable width at 96dpi = 698px,
     plus 20px padding and 2px border = 720px border-box. */
  .ne-editor-host.ne-docx-page { overflow-x:auto; box-sizing:border-box; padding:12px; background:var(--main-panel-bg); border-radius:6px; }
  :global(.ne-editor-host.ne-docx-page .ne-textarea) { width:720px; max-width:none; margin:0 auto; box-sizing:border-box; background:var(--color-workspace-panel); }
  :global(.ne-editor-host .ne-textarea:focus) { border-color:var(--color-dbs-red); }
  :global(.ne-editor-host .ne-textarea.ne-fs) { max-height:none; resize:none; }
  :global(.ne-editor-host .ne-textarea p.is-editor-empty:first-child::before) { content:attr(data-placeholder); color:var(--color-muted); opacity:0.7; pointer-events:none; float:left; height:0; }
  /* Bullets/numbers: Tailwind preflight sets list-style:none globally; restore
     real markers so bullet & ordered lists actually show them (bug 10 fix). */
  :global(.ne-editor-host .ne-textarea ul) { list-style:disc outside; padding-left:1.6em; margin:4px 0; }
  :global(.ne-editor-host .ne-textarea ol) { list-style:decimal outside; padding-left:1.6em; margin:4px 0; }
  :global(.ne-editor-host .ne-textarea ul[data-type="taskList"]) { list-style:none; padding-left:0; }
  :global(.ne-editor-host .ne-textarea ul[data-type="taskList"] li) { display:flex; align-items:flex-start; gap:6px; margin:4px 0; }
  :global(.ne-editor-host .ne-textarea ul[data-type="taskList"] li > div) { flex:1 1 auto; }
  :global(.ne-editor-host .ne-textarea ul[data-type="taskList"] li > label) { flex:0 0 auto; display:flex; align-items:center; }
  :global(.ne-editor-host .ne-textarea ul[data-type="taskList"] input[type="checkbox"]) { width:14px; height:14px; cursor:pointer; }
  :global(.ne-editor-host .ne-textarea h1) { font-size:24px; font-weight:900; margin:6px 0; line-height:1.2; }
  :global(.ne-editor-host .ne-textarea h2) { font-size:20px; font-weight:900; margin:6px 0; line-height:1.25; }
  :global(.ne-editor-host .ne-textarea h3) { font-size:16px; font-weight:900; margin:5px 0; line-height:1.3; }
  :global(.ne-editor-host .ne-textarea blockquote) { margin-left:1.4em; border-left:3px solid var(--soft-white-border); padding-left:8px; }
  :global(.ne-editor-host .ne-textarea pre) { background:var(--surface-dark); color:var(--card-white); padding:8px 10px; border-radius:6px; font-family:"Courier New", monospace; font-size:11px; overflow-x:auto; }
  :global(.ne-editor-host .ne-textarea code) { font-family:"Courier New", monospace; background:var(--soft-pink-surface); padding:0 3px; border-radius:3px; }
  :global(.ne-editor-host .ne-textarea pre code) { background:transparent; padding:0; }
  :global(.ne-editor-host .ne-textarea table) { border-collapse:collapse; table-layout:fixed; width:100%; margin:4px 0; }
  :global(.ne-editor-host .ne-textarea th), :global(.ne-editor-host .ne-textarea td) { border:1px solid var(--input-border); padding:4px 6px; position:relative; }
  :global(.ne-editor-host .ne-textarea th) { background:var(--soft-pink-surface); font-weight:800; }
  :global(.ne-editor-host .ne-textarea img) { max-width:100%; }
  :global(.ne-editor-host .ne-img-wrap) { position:relative; display:inline-block; max-width:100%; line-height:0; }
  :global(.ne-editor-host .ne-img-wrap img) { display:block; max-width:100%; }
  :global(.ne-editor-host .ne-img-handle) { position:absolute; right:-4px; bottom:-4px; width:8px; height:8px; background:var(--card-white); border:1px solid var(--color-dbs-red); border-radius:2px; box-shadow:0 1px 3px rgba(15,23,42,0.24); cursor:nwse-resize; opacity:0; }
  :global(.ne-editor-host .ne-img-wrap:hover .ne-img-handle), :global(.ne-editor-host .ProseMirror-selectednode .ne-img-handle) { opacity:1; }
  :global(.ne-editor-host .ne-textarea[contenteditable="false"] .ne-img-handle) { display:none; }
  /* Column-resize handle + cursor for resizable tables (bug 11). */
  :global(.ne-editor-host .ne-textarea .selectedCell) { background:var(--soft-pink-surface); }
  :global(.ne-editor-host .ne-textarea .column-resize-handle) { position:absolute; right:-2px; top:0; bottom:-2px; width:4px; background:var(--color-dbs-red); pointer-events:none; z-index:10; }
  :global(.ne-editor-host.resize-cursor) { cursor:col-resize; }

  .ne-status { display:flex; align-items:center; gap:6px; font-size:10px; font-weight:800; color:var(--color-muted); white-space:nowrap; }
  .ne-status.err { color:var(--color-dbs-red); }
  .ne-status.off { color:var(--tag-amber-ink); }
  .ne-dot { font-weight:900; }
  .ne-dot.ne-ok { color:var(--tag-green-ink); }
</style>
