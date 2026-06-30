<script lang="ts">
  import { onDestroy, tick, untrack } from "svelte";
  import { callBridge, isPywebviewReady } from "../bridge";
  import { renderMarkdown } from "../markdown";
  import { Editor } from "@tiptap/core";
  import StarterKit from "@tiptap/starter-kit";
  // NOTE: Underline + Link are bundled INSIDE StarterKit v3 — re-registering them
  // throws a duplicate-name error, so we only configure them on StarterKit.
  import Subscript from "@tiptap/extension-subscript";
  import Superscript from "@tiptap/extension-superscript";
  import { FontFamily, TextStyle } from "@tiptap/extension-text-style";
  import Image from "@tiptap/extension-image";
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
  }
  let { projectPath, initialNotes, onSaved }: Props = $props();

  type SaveStatus = "idle" | "pending" | "saving" | "saved" | "error" | "offline";

  let text = $state(untrack(() => initialNotes ?? ""));
  let status = $state<SaveStatus>("idle");
  let errorText = $state("");
  let hostEl = $state<HTMLDivElement | null>(null);
  let editor: Editor | null = $state(null);
  let toolbarEl = $state<HTMLElement | null>(null);
  let lastSaved = $state(untrack(() => initialNotes ?? ""));
  let fullscreen = $state(false);
  // Reactive refresh token: bumped on every editor transaction so isActive() /
  // getAttributes() in the markup re-evaluate (Editor is not a rune proxy).
  let rev = $state(0);

  let colorOpen = $state(false);
  let colorMode: 'fore' | 'back' = $state('fore');
  let tableOpen = $state(false);
  let tableHover = $state({ rows: 1, cols: 1 });
  let emojiOpen = $state(false);
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
  let timer: ReturnType<typeof setTimeout> | undefined;

  const statusLabel = $derived(
    status === "saving" ? "Saving…"
    : status === "saved" ? "Saved"
    : status === "pending" ? "Editing…"
    : status === "offline" ? "Offline — notes not saved in browser preview"
    : status === "error" ? `Save failed: ${errorText}`
    : "Autosave on",
  );

  function scheduleSave() {
    status = "pending";
    if (timer) clearTimeout(timer);
    timer = setTimeout(flush, AUTOSAVE_MS);
  }

  async function flush() {
    if (timer) { clearTimeout(timer); timer = undefined; }
    if (text === lastSaved) { status = "saved"; return; }
    if (!isPywebviewReady()) { status = "offline"; return; }
    status = "saving";
    errorText = "";
    const resp = await callBridge("notes_update", projectPath, text);
    if (!resp.ok) { status = "error"; errorText = resp.error.message; return; }
    lastSaved = text;
    status = "saved";
    onSaved?.(text);
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
    linkOpen = false; imgOpen = false;
  }

  function onWindowClick(e: MouseEvent) {
    const t = e.target as HTMLElement;
    if (t.closest('.ne-popover-wrap')) return;
    // Never run editor popover-close logic for clicks on titlebar chrome,
    // window controls, confirm/overlay regions, or modal dialogs. These must
    // navigate/act unimpeded even while the RTE window listener is attached.
    if (t.closest('.titlebar, .nav-tab, .notif-btn, .notif-popover, .win-controls, .win-btn, .app-header, .confirm-overlay, .dialog-backdrop')) return;
    closeAllPopovers();
  }

  // ── HTML-to-Markdown ──

  /** Escape characters that would break a markdown/HTML attribute value. */
  function escapeAttr(v: string): string {
    return v.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
  }

  /** Pull text-align out of an element's inline style or align attribute. */
  function extractAlign(el: HTMLElement): string {
    const attr = el.getAttribute("align");
    if (attr) return attr.toLowerCase();
    const m = (el.getAttribute("style") || "").match(/text-align:\s*([^;]+)/i);
    return m ? m[1].trim().toLowerCase() : "";
  }

  function domToMarkdown(node: Node): string {
    if (node.nodeType === Node.TEXT_NODE) return node.textContent || "";
    if (node.nodeType !== Node.ELEMENT_NODE) return "";
    const el = node as HTMLElement;
    const tag = el.tagName.toLowerCase();
    // Tiptap task item: <li data-type="taskItem" data-checked="false">…<div>text</div></li>
    if (el.dataset.type === "taskItem") {
      const checked = el.dataset.checked === "true";
      const ch = checked ? "x" : " ";
      const contentEl = el.querySelector("div") || el;
      const tc = Array.from(contentEl.childNodes).map(domToMarkdown).join("");
      return `- [${ch}] ${tc.trim()}\n`;
    }
    const children = Array.from(el.childNodes).map(domToMarkdown).join("");
    switch (tag) {
      case "h1": return `# ${children.trim()}\n\n`;
      case "h2": return `## ${children.trim()}\n\n`;
      case "h3": return `### ${children.trim()}\n\n`;
      case "blockquote": return `> ${children.trim()}\n\n`;
      case "li": {
        // Task items are handled above; normal list items take their marker
        // from the parent list type.
        return `${el.parentElement?.tagName === 'OL' ? '1.' : '-'} ${children.trim()}\n`;
      }
      case "ol": return `${children}\n`;
      case "ul": return `${children}\n`;
      case "strong": case "b": return `**${children}**`;
      case "em": case "i": return `*${children}*`;
      case "u": return `<u>${children}</u>`;
      case "s": case "strike": return `~~${children}~~`;
      case "sub": return `<sub>${children}</sub>`;
      case "sup": return `<sup>${children}</sup>`;
      case "pre":
        // Code block: emit as a fenced block so renderMarkdown lifts it back.
        return '```\n' + (el.textContent || '') + '\n```\n\n';
      case "code": return `\`${children}\``;
      case "a": return `[${children}](${el.getAttribute("href") || ""})`;
      case "p": {
        const align = extractAlign(el);
        const trimmed = children.trim();
        if (align) return `<p style="text-align:${align}">${trimmed}</p>\n\n`;
        return `${trimmed}\n\n`;
      }
      case "div": {
        const dAlign = extractAlign(el);
        if (dAlign) return `<div style="text-align:${dAlign}">${children}</div>\n`;
        return `${children}\n`;
      }
      case "hr": return "---\n\n";
      case "br": return "\n";
      case "img": {
        const src = el.getAttribute('src') || '';
        const alt = el.getAttribute('alt') || '';
        return `![${alt}](${src})`;
      }
      case "table": {
        // Render a GFM pipe table with a separator row after the header.
        const allRows = Array.from(el.querySelectorAll('tr'));
        if (allRows.length === 0) return children;
        const cellText = (c: Element) => (c.textContent || '').replace(/\|/g, '\\|').trim();
        const rowText = (tr: Element) => `| ${Array.from(tr.querySelectorAll('td,th')).map(cellText).join(' | ')} |`;
        const header = allRows[0];
        const cols = header.querySelectorAll('td,th').length;
        const sep = `| ${Array.from({ length: cols || 1 }, () => '---').join(' | ')} |`;
        const body = allRows.slice(1).map(rowText).join('\n');
        return `${rowText(header)}\n${sep}${body ? '\n' + body : ''}\n\n`;
      }
      case "tr": case "td": case "th": case "tbody": case "thead": case "caption": return children;
      case "font": {
        const attrs: string[] = [];
        const fc = el.getAttribute('color'); if (fc) attrs.push(`color="${escapeAttr(fc)}"`);
        const ff = el.getAttribute('face'); if (ff) attrs.push(`face="${escapeAttr(ff)}"`);
        if (attrs.length) return `<font ${attrs.join(' ')}>${children}</font>`;
        return children;
      }
      case "span": {
        const style = el.getAttribute('style') || '';
        if (style.trim()) return `<span style="${escapeAttr(style)}">${children}</span>`;
        return children;
      }
      case "mark": {
        // Tiptap highlight renders as <mark>; carry it as an inline-styled span.
        const c = el.getAttribute('data-color') || el.style.backgroundColor;
        if (c) return `<span style="background-color:${escapeAttr(c)}">${children}</span>`;
        return children;
      }
      default: return children;
    }
  }

  function htmlToMarkdown(html: string): string {
    if (!html) return "";
    const doc = new DOMParser().parseFromString(html, "text/html");
    let md = Array.from(doc.body.childNodes).map(domToMarkdown).join("");
    md = md.replace(/\n{3,}/g, "\n\n");
    return md.trim();
  }

  function onEditorUpdate() {
    if (!editor) return;
    text = htmlToMarkdown(editor.getHTML());
    scheduleSave();
  }

  // ── Active-state helpers (reactive via the rev token) ──

  function isActive(name: string, attrs?: Record<string, unknown>): boolean {
    return editor?.isActive(name, attrs) ?? false;
  }

  /** TextAlign marks live as a node attribute; check it directly. */
  function alignIs(value: string): boolean {
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
      editor?.chain().focus().setImage({ src: url, alt: imgAlt.trim() }).run();
      rev++;
    }
    imgOpen = false;
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

  onDestroy(() => {
    if (timer) clearTimeout(timer);
    window.removeEventListener('resize', recalcHeight);
    document.body.style.overflow = '';
    window.removeEventListener('click', onWindowClick);
  });

  let lastPath = "";
  let windowClickBound = false;

  // SSR guard: the app renders client-side in pywebview, but the test harness
  // renders server-side (window undefined there). Only build the Editor where a
  // DOM exists, so the toolbar still renders under SSR.
  const isBrowser = typeof window !== "undefined" && typeof document !== "undefined";

  $effect(() => {
    if (!isBrowser || !hostEl) return;
    if (editor) {
      // Project switch: reload content without rebuilding the editor.
      if (projectPath !== lastPath) {
        lastPath = projectPath;
        editor.commands.setContent(renderMarkdown(text), { emitUpdate: false });
        lastSaved = text;
      }
      return;
    }
    lastPath = projectPath;
    const instance = new Editor({
      element: hostEl,
      editable: true,
      content: renderMarkdown(untrack(() => text)),
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
        Image.configure({ inline: true, allowBase64: true }),
        TaskList,
        TaskItem.configure({ nested: false }),
        TextAlign.configure({ types: ["heading", "paragraph"] }),
        Placeholder.configure({ placeholder: "Write project notes (autosaves to notes.md)…" }),
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
      },
    });
    instance.on("transaction", () => { rev++; });
    instance.on("selectionUpdate", () => { rev++; });
    instance.on("update", onEditorUpdate);
    editor = instance;
    if (!windowClickBound) {
      windowClickBound = true;
      window.addEventListener('click', onWindowClick);
    }
    return () => { instance.destroy(); editor = null; };
  });

  // Reflect editor font family/size into the selects (after each transaction).
  $effect(() => {
    rev;
    if (!editor) return;
    fontSelVal = (editor.getAttributes("textStyle").fontFamily as string) || "";
  });
  $effect(() => {
    rev;
    if (!editor) return;
    const fs = (editor.getAttributes("fontSize").fontSize as string) || "";
    sizeSelVal = fs ? String(parseInt(fs)) : "";
  });
</script>

<div class="ne-root" class:fullscreen>
  <div class="ne-toolbar" bind:this={toolbarEl}>
    <div class="ne-tools" aria-label="Visual formatting">

      <!-- Row: Undo/Redo | Font | Size -->
      <button type="button" class="ne-tbtn" title="Undo" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().undo().run(); rev++; }}>↩</button>
      <button type="button" class="ne-tbtn" title="Redo" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().redo().run(); rev++; }}>↪</button>
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
      <button type="button" class="ne-tbtn" class:active={isActive('bold')} title="Bold" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().toggleBold().run(); rev++; }}><strong>B</strong></button>
      <button type="button" class="ne-tbtn" class:active={isActive('italic')} title="Italic" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().toggleItalic().run(); rev++; }}><em>I</em></button>
      <button type="button" class="ne-tbtn" class:active={isActive('underline')} title="Underline" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().toggleUnderline().run(); rev++; }}><u>U</u></button>
      <button type="button" class="ne-tbtn" class:active={isActive('strike')} title="Strikethrough" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().toggleStrike().run(); rev++; }}><s>S</s></button>
      <span class="ne-sep"></span>
      <button type="button" class="ne-tbtn" class:active={isActive('superscript')} title="Superscript" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().toggleSuperscript().run(); rev++; }}>x<sup>2</sup></button>
      <button type="button" class="ne-tbtn" class:active={isActive('subscript')} title="Subscript" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().toggleSubscript().run(); rev++; }}>x<sub>2</sub></button>
      <span class="ne-sep"></span>

      <!-- Row: Forecolor | Backcolor -->
      <div class="ne-popover-wrap">
        <button type="button" class="ne-tbtn" title="Text color" onmousedown={(e) => { e.preventDefault(); colorMode='fore'; colorOpen=!colorOpen; tableOpen=false; emojiOpen=false; }}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M11 4L4 20h3l1-3h8l1 3h3L13 4h-2z"/><line x1="7.5" y1="14" x2="16.5" y2="14"/></svg>
        </button>
        <button type="button" class="ne-tbtn" title="Background color" onmousedown={(e) => { e.preventDefault(); colorMode='back'; colorOpen=!colorOpen; tableOpen=false; emojiOpen=false; }}>
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
      <button type="button" class="ne-tbtn" class:active={isActive('heading',{level:1})} title="Heading 1" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().toggleHeading({ level: 1 }).run(); rev++; }}>H1</button>
      <button type="button" class="ne-tbtn" class:active={isActive('heading',{level:2})} title="Heading 2" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().toggleHeading({ level: 2 }).run(); rev++; }}>H2</button>
      <button type="button" class="ne-tbtn" class:active={isActive('heading',{level:3})} title="Heading 3" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().toggleHeading({ level: 3 }).run(); rev++; }}>H3</button>
      <button type="button" class="ne-tbtn" class:active={isActive('paragraph')} title="Paragraph" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().setParagraph().run(); rev++; }}>¶</button>
      <span class="ne-sep"></span>
      <button type="button" class="ne-tbtn" class:active={isActive('blockquote')} title="Blockquote" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().toggleBlockquote().run(); rev++; }}>❝</button>
      <button type="button" class="ne-tbtn" class:active={isActive('code')} title="Inline code" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().toggleCode().run(); rev++; }}>{@html '&lt;/&gt;'}</button>
      <button type="button" class="ne-tbtn" class:active={isActive('codeBlock')} title="Code block" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().toggleCodeBlock().run(); rev++; }}>{"</>"}</button>
      <span class="ne-sep"></span>

      <!-- Row: OL UL | Indent Outdent -->
      <button type="button" class="ne-tbtn" class:active={isActive('orderedList')} title="Numbered list" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().toggleOrderedList().run(); rev++; }}>1.</button>
      <button type="button" class="ne-tbtn" class:active={isActive('bulletList')} title="Bulleted list" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().toggleBulletList().run(); rev++; }}>•</button>
      <span class="ne-sep"></span>
      <button type="button" class="ne-tbtn" title="Indent" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().sinkListItem('listItem').run(); rev++; }}>→</button>
      <button type="button" class="ne-tbtn" title="Outdent" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().liftListItem('listItem').run(); rev++; }}>←</button>
      <span class="ne-sep"></span>

      <!-- Row: Align L C R J -->
      <button type="button" class="ne-tbtn" class:active={alignIs('left')} title="Align left" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().setTextAlign('left').run(); rev++; }}>≡L</button>
      <button type="button" class="ne-tbtn" class:active={alignIs('center')} title="Align center" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().setTextAlign('center').run(); rev++; }}>≡C</button>
      <button type="button" class="ne-tbtn" class:active={alignIs('right')} title="Align right" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().setTextAlign('right').run(); rev++; }}>≡R</button>
      <button type="button" class="ne-tbtn" class:active={alignIs('justify')} title="Justify" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().setTextAlign('justify').run(); rev++; }}>≡J</button>
      <span class="ne-sep"></span>

      <!-- Row: Link HR Table Image Emoji -->
      <div class="ne-popover-wrap">
        <button type="button" class="ne-tbtn" class:active={isActive('link')} title="Link" onmousedown={(e) => { e.preventDefault(); formatLink(); }}>🔗</button>
        {#if linkOpen}
          <div class="ne-popover ne-link-pop">
            <label class="ne-field-label" for="ne-link-input">{linkEditing ? 'Edit URL' : 'Link URL'}</label>
            <input id="ne-link-input" class="ne-input" type="url" bind:value={linkUrl} placeholder="https://example.com" onkeydown={onLinkKeydown} onclick={(e) => e.stopPropagation()} onmousedown={(e) => e.stopPropagation()} />
            <div class="ne-dialog-actions">
              {#if linkEditing}
                <button type="button" class="ne-tbtn ne-act-btn" title="Remove link" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().extendMarkRange('link').unsetLink().run(); linkOpen=false; rev++; }}>Remove</button>
              {/if}
              <button type="button" class="ne-tbtn" title="Cancel" onmousedown={(e) => { e.preventDefault(); closeLinkDialog(); }}>Cancel</button>
              <button type="button" class="ne-tbtn ne-act-btn" title="Apply" onmousedown={(e) => { e.preventDefault(); confirmLink(); }}>OK</button>
            </div>
          </div>
        {/if}
      </div>
      <button type="button" class="ne-tbtn" title="Horizontal rule" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().setHorizontalRule().run(); rev++; }}>HR</button>
      <div class="ne-popover-wrap">
        <button type="button" class="ne-tbtn" title="Table" onmousedown={(e) => { e.preventDefault(); tableOpen=!tableOpen; colorOpen=false; emojiOpen=false; }}>⊞</button>
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
        <button type="button" class="ne-tbtn" title="Image" onmousedown={(e) => { e.preventDefault(); formatImage(); }}>🖼</button>
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
              <button type="button" class="ne-tbtn" title="Cancel" onmousedown={(e) => { e.preventDefault(); closeImageDialog(); }}>Cancel</button>
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
      <button type="button" class="ne-tbtn" class:active={isActive('taskList')} title="Checklist" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().toggleTaskList().run(); rev++; }}>☑</button>
      <button type="button" class="ne-tbtn" title="Clear formatting" onmousedown={(e) => { e.preventDefault(); editor?.chain().focus().unsetAllMarks().clearNodes().run(); rev++; }}>↺</button>
    </div>

    <div class="ne-actions">
      <button type="button" class="ne-tbtn ne-fsbtn" class:active={fullscreen} title={fullscreen ? "Exit fullscreen" : "Fullscreen"} onmousedown={(e) => { e.preventDefault(); toggleFullscreen(); }}>
        {#if fullscreen}
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><polyline points="4 14 10 14 10 20"/><polyline points="20 10 14 10 14 4"/><line x1="14" y1="10" x2="21" y2="3"/><line x1="10" y1="14" x2="3" y2="21"/></svg>
        {:else}
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>
        {/if}
      </button>
      <div class="ne-status" class:err={status === "error"} class:off={status === "offline"} role="status" title={status === "error" ? errorText : statusLabel}>
        {#if status === "saving"}<span class="ne-dot">◌</span>{:else if status === "saved"}<span class="ne-dot ne-ok">✓</span>{/if}
        <span>{statusLabel}</span>
      </div>
    </div>
  </div>

  <div class="ne-editor-host" bind:this={hostEl}></div>
</div>

<style>
  .ne-root { display:flex; flex-direction:column; gap:6px; }
  .ne-root.fullscreen { position:fixed; top:0; left:0; width:100vw; height:100vh; z-index:9999; background:var(--main-bg); padding:12px 14px; }
  .ne-toolbar { display:flex; align-items:flex-start; justify-content:space-between; gap:8px; flex:0 0 auto; }
  .ne-tools { display:flex; gap:3px; align-items:center; flex-wrap:wrap; flex:1; }
  .ne-actions { display:flex; align-items:center; gap:8px; flex:0 0 auto; }
  .ne-sep { display:inline-block; width:1px; height:16px; background:var(--soft-white-border); margin:0 2px; flex:0 0 auto; }
  .ne-tbtn { min-width:26px; height:24px; padding:0 6px; border:1px solid var(--soft-white-border); border-radius:5px; background:var(--card-white); color:var(--color-ink); font-size:10px; font-weight:850; cursor:pointer; display:inline-flex; align-items:center; justify-content:center; gap:2px; white-space:nowrap; }
  .ne-tbtn:hover { border-color:var(--color-dbs-red); color:var(--color-dbs-red); }
  .ne-tbtn.active { background:var(--soft-pink-surface); border-color:var(--color-dbs-red); color:var(--color-dbs-red); }
  .ne-tbtn:active { transform:scale(0.94); background:var(--soft-pink-surface); border-color:var(--color-dbs-red); }
  .ne-tselect:active { transform:none; }
  .ne-tbtn s { color:inherit; text-decoration:line-through; }
  .ne-tselect { min-width:68px; width:auto; padding:0 16px 0 6px; appearance:none; font-size:9px; background-image:linear-gradient(45deg,transparent 50%,var(--text-strong) 50%),linear-gradient(135deg,var(--text-strong) 50%,transparent 50%); background-position:calc(100% - 6px) 10px,calc(100% - 2px) 10px; background-size:4px 4px,4px 4px; background-repeat:no-repeat; background-color:var(--card-white); }
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
  .ne-editor-host { width:100%; }
  :global(.ne-editor-host .ne-textarea) { width:100%; min-height:120px; max-height:300px; padding:10px; background:var(--color-workspace-panel); border:1px solid var(--soft-white-border); border-radius:6px; font-size:12px; font-family:"Times New Roman", serif; color:var(--color-ink); resize:vertical; outline:none; line-height:1.5; overflow-y:auto; flex:1 1 auto; }
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
