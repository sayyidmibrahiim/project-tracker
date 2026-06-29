<script lang="ts">
  import { onDestroy, tick, untrack } from "svelte";
  import { callBridge, isPywebviewReady } from "../bridge";
  import { renderMarkdown } from "../markdown";

  interface Props {
    projectPath: string;
    initialNotes: string;
    onSaved?: (notes: string) => void;
  }
  let { projectPath, initialNotes, onSaved }: Props = $props();

  type SaveStatus = "idle" | "pending" | "saving" | "saved" | "error" | "offline";

  type FormatState = {
    bold: boolean; italic: boolean; underline: boolean; strikethrough: boolean;
    subscript: boolean; superscript: boolean;
    heading: '' | 'p' | 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6';
    code: boolean; codeBlock: boolean; blockquote: boolean; link: boolean;
    orderedList: boolean; unorderedList: boolean; todo: boolean;
    align: '' | 'left' | 'center' | 'right' | 'justify';
    fontFamily: string; fontSize: string;
  };

  let text = $state(untrack(() => initialNotes ?? ""));
  let status = $state<SaveStatus>("idle");
  let errorText = $state("");
  let editorEl = $state<HTMLDivElement | null>(null);
  let toolbarEl = $state<HTMLElement | null>(null);
  let lastSaved = $state(untrack(() => initialNotes ?? ""));
  let fullscreen = $state(false);

  let fs = $state<FormatState>({
    bold: false, italic: false, underline: false, strikethrough: false,
    subscript: false, superscript: false,
    heading: '', code: false, codeBlock: false, blockquote: false, link: false,
    orderedList: false, unorderedList: false, todo: false,
    align: '', fontFamily: '', fontSize: '',
  });

  let colorOpen = $state(false);
  let colorMode: 'fore' | 'back' = $state('fore');
  let tableOpen = $state(false);
  let tableHover = $state({ rows: 1, cols: 1 });
  let emojiOpen = $state(false);
  let fontSelVal = $state('');
  let sizeSelVal = $state('');

  const FONTS = [
    { label: 'Sans-serif', value: 'Inter, sans-serif' },
    { label: 'Serif', value: 'Georgia, serif' },
    { label: 'Monospace', value: '"Courier New", monospace' },
    { label: 'Arial', value: 'Arial' },
    { label: 'Calibri', value: 'Calibri' },
    { label: 'Times New Roman', value: '"Times New Roman", serif' },
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
    timer = setTimeout(() => {
      if (editorEl) text = htmlToMarkdown(editorEl.innerHTML);
      flush();
    }, AUTOSAVE_MS);
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
      if (editorEl) { editorEl.style.maxHeight = ''; editorEl.style.height = ''; }
    }
  }

  function recalcHeight() {
    if (!fullscreen || !toolbarEl || !editorEl) return;
    editorEl.style.maxHeight = 'none';
    const other = editorEl.parentElement?.querySelector('.ne-toolbar');
    const h = other ? window.innerHeight - other.getBoundingClientRect().height - 18 : window.innerHeight;
    editorEl.style.height = `${h}px`;
  }

  function closeAllPopovers() {
    colorOpen = false; tableOpen = false; emojiOpen = false;
  }

  function onWindowClick(e: MouseEvent) {
    const t = e.target as HTMLElement;
    if (t.closest('.ne-popover-wrap')) return;
    closeAllPopovers();
  }

  // ── HTML-to-Markdown ──

  function domToMarkdown(node: Node): string {
    if (node.nodeType === Node.TEXT_NODE) return node.textContent || "";
    if (node.nodeType !== Node.ELEMENT_NODE) return "";
    const el = node as HTMLElement;
    const tag = el.tagName.toLowerCase();
    if (el.classList.contains("ne-todo-item")) {
      const cb = el.querySelector("input[type='checkbox']") as HTMLInputElement | null;
      const ts = el.querySelector("span") as HTMLElement | null;
      const ch = cb?.checked ? "x" : " ";
      const tc = ts ? Array.from(ts.childNodes).map(domToMarkdown).join("") : "";
      return `- [${ch}] ${tc.trim()}\n`;
    }
    const children = Array.from(el.childNodes).map(domToMarkdown).join("");
    switch (tag) {
      case "h1": return `# ${children.trim()}\n\n`;
      case "h2": return `## ${children.trim()}\n\n`;
      case "h3": return `### ${children.trim()}\n\n`;
      case "blockquote": return `> ${children.trim()}\n\n`;
      case "li": return `${el.parentElement?.tagName === 'OL' ? '1.' : '-'} ${children.trim()}\n`;
      case "ol": return `${children}\n`;
      case "ul": return `${children}\n`;
      case "strong": case "b": return `**${children}**`;
      case "em": case "i": return `*${children}*`;
      case "u": return `<u>${children}</u>`;
      case "s": case "strike": return `~~${children}~~`;
      case "sub": return `<sub>${children}</sub>`;
      case "sup": return `<sup>${children}</sup>`;
      case "code": return `\`${children}\``;
      case "a": return `[${children}](${el.getAttribute("href") || ""})`;
      case "p": return `${children.trim()}\n\n`;
      case "div": return `${children}\n`;
      case "hr": return "---\n\n";
      case "br": return "\n";
      case "table":
        const rows = Array.from(el.querySelectorAll('tr')).map(tr => {
          const cells = Array.from(tr.querySelectorAll('td,th')).map(c => c.textContent?.trim() || '').join(' | ');
          return `| ${cells} |`;
        }).join('\n');
        return `${rows}\n\n`;
      case "tr": case "td": case "th": case "tbody": case "thead": case "caption": return children;
      case "font": return children;
      case "span":
        const style = el.getAttribute('style') || '';
        if (style.includes('font-size') || style.includes('font-family') || style.includes('color') || style.includes('background-color')) {
          const m: string[] = [];
          if (style.includes('background-color')) { const c = style.match(/background-color:\s*([^;]+)/)?.[1]; if (c) m.push(`bg${c}`); }
          if (m.length) return `<span style="${style}">${children}</span>`;
        }
        return children;
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

  function syncToMarkdown() {
    if (editorEl) { text = htmlToMarkdown(editorEl.innerHTML); scheduleSave(); }
  }

  function onEditorInput() { scheduleSave(); }

  function onEditorBlur() {
    if (editorEl) text = htmlToMarkdown(editorEl.innerHTML);
    if (status === "pending" || timer) { if (timer) { clearTimeout(timer); timer = undefined; } flush(); }
  }

  function bindCheckboxListeners() {
    if (!editorEl) return;
    editorEl.querySelectorAll(".ne-todo-checkbox").forEach(box => {
      box.removeEventListener("change", syncToMarkdown);
      box.addEventListener("change", syncToMarkdown);
    });
  }

  // ── Active state detection ──

  function isInElement(tagOrClass: string): boolean {
    const sel = window.getSelection();
    if (!sel || !sel.rangeCount || !editorEl) return false;
    let el = sel.anchorNode as HTMLElement | null;
    if (el?.nodeType === Node.TEXT_NODE) el = el.parentElement;
    while (el && el !== editorEl) {
      if (tagOrClass.startsWith('.') && el.classList.contains(tagOrClass.slice(1))) return true;
      if (el.tagName.toLowerCase() === tagOrClass.toLowerCase()) return true;
      el = el.parentElement;
    }
    return false;
  }

  function detectListType(): { ordered: boolean; unordered: boolean } {
    const sel = window.getSelection();
    if (!sel || !sel.rangeCount) return { ordered: false, unordered: false };
    let el = sel.anchorNode as HTMLElement | null;
    if (el?.nodeType === Node.TEXT_NODE) el = el.parentElement;
    while (el && el !== editorEl) {
      const t = el.tagName.toLowerCase();
      if (t === 'ol') return { ordered: true, unordered: false };
      if (t === 'ul') return { ordered: false, unordered: true };
      el = el.parentElement;
    }
    return { ordered: false, unordered: false };
  }

  function updateFormatState() {
    if (!editorEl || !editorEl.contains(document.activeElement)) return;
    const sel = window.getSelection();
    if (!sel || !sel.rangeCount) return;
    try {
      const list = detectListType();
      let h: FormatState['heading'] = '';
      const rawH = document.queryCommandValue('formatBlock')?.toLowerCase() || '';
      if (/^h[1-6]$/.test(rawH)) h = rawH as FormatState['heading'];
      else if (rawH.includes('paragraph') || rawH === 'p') h = 'p';
      let al: FormatState['align'] = '';
      if (document.queryCommandState('justifyLeft')) al = 'left';
      else if (document.queryCommandState('justifyCenter')) al = 'center';
      else if (document.queryCommandState('justifyRight')) al = 'right';
      else if (document.queryCommandState('justifyFull')) al = 'justify';
      fs = {
        bold: document.queryCommandState('bold'),
        italic: document.queryCommandState('italic'),
        underline: document.queryCommandState('underline'),
        strikethrough: document.queryCommandState('strikeThrough'),
        subscript: document.queryCommandState('subscript'),
        superscript: document.queryCommandState('superscript'),
        heading: h,
        code: isInElement('code') && !isInElement('pre'),
        codeBlock: isInElement('pre'),
        blockquote: isInElement('blockquote'),
        link: isInElement('a'),
        orderedList: list.ordered,
        unorderedList: list.unordered,
        todo: isInElement('.ne-todo-item'),
        align: al,
        fontFamily: document.queryCommandValue('fontName') || '',
        fontSize: detectFontSize(),
      };
    } catch {}
  }

  // ── WYSIWYG commands ──

  function format(cmd: string, value: string = "") {
    document.execCommand(cmd, false, value || undefined);
    scheduleSave();
    tick().then(updateFormatState);
  }

  function formatSimple(cmd: string) {
    format(cmd, '');
  }

  function formatBlockCmd(tag: string) {
    format('formatBlock', `<${tag}>`);
  }

  function applyFont() {
    if (!fontSelVal) return;
    format('fontName', fontSelVal);
    (document.getElementById('ne-font-select') as HTMLSelectElement | null)?.blur();
  }

  function applySize() {
    const sel = window.getSelection();
    if (!sel || !sel.rangeCount || sel.isCollapsed) return;
    const px = parseInt(sizeSelVal);
    if (isNaN(px)) return;
    const range = sel.getRangeAt(0);
    const span = document.createElement('span');
    span.style.fontSize = `${px}px`;
    span.textContent = range.toString();
    range.deleteContents();
    range.insertNode(span);
    scheduleSave();
    tick().then(updateFormatState);
    (document.getElementById('ne-size-select') as HTMLSelectElement | null)?.blur();
  }

  function detectFontSize(): string {
    if (!editorEl) return '';
    const sel = window.getSelection();
    if (!sel || !sel.rangeCount) return '';
    let el = sel.anchorNode as HTMLElement | null;
    if (el?.nodeType === Node.TEXT_NODE) el = el.parentElement;
    while (el && el !== editorEl) {
      const s = el.style?.fontSize;
      if (s) { const px = parseFloat(s); if (!isNaN(px)) return Math.round(px).toString(); }
      el = el.parentElement;
    }
    if (el) return Math.round(parseFloat(window.getComputedStyle(el).fontSize)).toString();
    return '';
  }

  function formatCode() {
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0) return;
    const range = sel.getRangeAt(0);
    if (range.collapsed) return;
    const code = document.createElement("code");
    code.textContent = range.toString();
    range.deleteContents();
    range.insertNode(code);
    scheduleSave();
    tick().then(updateFormatState);
  }

  function formatCodeBlock() {
    if (!editorEl) return;
    editorEl.focus();
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0) return;
    let el = sel.anchorNode as HTMLElement | null;
    if (el?.nodeType === Node.TEXT_NODE) el = el.parentElement;
    while (el && el !== editorEl && el.tagName.toLowerCase() !== 'pre') el = el.parentElement;
    if (el && el.tagName.toLowerCase() === 'pre') {
      const parent = el.parentNode;
      if (parent) {
        const text = el.textContent || '';
        const p = document.createElement('p');
        p.textContent = text;
        parent.replaceChild(p, el);
        const range = document.createRange();
        range.selectNodeContents(p);
        sel.removeAllRanges();
        sel.addRange(range);
      }
    } else {
      const range = sel.getRangeAt(0);
      const text = range.toString() || 'Code block';
      const pre = document.createElement('pre');
      const code = document.createElement('code');
      code.textContent = text;
      pre.appendChild(code);
      range.deleteContents();
      range.insertNode(pre);
    }
    scheduleSave();
    tick().then(updateFormatState);
  }

  function formatLink() {
    if (!editorEl) return;
    editorEl.focus();
    const sel = window.getSelection();
    if (!sel || !sel.rangeCount) return;

    let el = sel.anchorNode as HTMLElement | null;
    if (el?.nodeType === Node.TEXT_NODE) el = el.parentElement;
    while (el && el !== editorEl && el.tagName.toLowerCase() !== 'a') el = el.parentElement;

    if (el && el.tagName.toLowerCase() === 'a') {
      const a = el as HTMLAnchorElement;
      const currentUrl = a.getAttribute('href') || '';
      const action = prompt("Edit URL (press OK to update, Cancel to remove link):", currentUrl);
      if (action === null) {
        const parent = a.parentNode;
        if (parent) {
          const text = document.createTextNode(a.textContent || '');
          parent.replaceChild(text, a);
          const range = document.createRange();
          range.selectNodeContents(parent);
          sel.removeAllRanges();
          sel.addRange(range);
        }
      } else if (action !== currentUrl) {
        a.setAttribute('href', action);
      }
      scheduleSave();
      tick().then(updateFormatState);
      return;
    }

    if (sel.isCollapsed) return;
    const url = prompt("Enter URL:");
    if (!url) return;
    const range = sel.getRangeAt(0);
    const a = document.createElement('a');
    a.setAttribute('href', url);
    a.textContent = range.toString();
    range.deleteContents();
    range.insertNode(a);
    scheduleSave();
    tick().then(updateFormatState);
  }

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
        range.insertNode(range.createContextualFragment(html));
      }
    }
    editorEl.focus();
    setTimeout(bindCheckboxListeners, 50);
    scheduleSave();
    tick().then(updateFormatState);
  }

  function formatImage() {
    if (!editorEl) return;
    editorEl.focus();
    const url = prompt("Enter image URL:");
    if (!url) return;
    const alt = prompt("Enter image description (alt text):") || '';
    const img = document.createElement('img');
    img.setAttribute('src', url);
    img.setAttribute('alt', alt);
    img.style.maxWidth = '100%';
    const sel = window.getSelection();
    if (sel && sel.rangeCount > 0) {
      sel.getRangeAt(0).insertNode(img);
    } else {
      editorEl.appendChild(img);
    }
    const space = document.createTextNode('\u00A0');
    img.parentNode?.insertBefore(space, img.nextSibling);
    scheduleSave();
    tick().then(updateFormatState);
  }

  function applyColor(color: string) {
    const cmd = colorMode === 'back' ? 'hiliteColor' : 'foreColor';
    document.execCommand(cmd, false, color);
    scheduleSave();
    colorOpen = false;
    tick().then(updateFormatState);
  }

  function insertTable() {
    const { rows, cols } = tableHover;
    const html = `<table border="1" style="border-collapse:collapse;width:100%;"><tbody>`;
    const rowsHtml = Array.from({ length: rows }, () => `<tr>${Array.from({ length: cols }, () => '<td style="border:1px solid #ccc;padding:4px;"><br></td>').join('')}</tr>`).join('');
    const full = `${html}${rowsHtml}</tbody></table><p><br></p>`;
    if (!editorEl) return;
    editorEl.focus();
    const sel = window.getSelection();
    if (sel && sel.rangeCount > 0) {
      sel.getRangeAt(0).insertNode(document.createRange().createContextualFragment(full));
    } else {
      editorEl.insertAdjacentHTML('beforeend', full);
    }
    tableOpen = false;
    scheduleSave();
    tick().then(updateFormatState);
  }

  function insertEmoji(emoji: string) {
    editorEl?.focus();
    document.execCommand('insertText', false, emoji);
    emojiOpen = false;
    scheduleSave();
    tick().then(updateFormatState);
  }

  // ── Lifecycle ──

  onDestroy(() => {
    if (timer) clearTimeout(timer);
    window.removeEventListener('resize', recalcHeight);
    document.body.style.overflow = '';
    window.removeEventListener('click', onWindowClick);
  });

  let lastPath = "";
  let stateDetectBound = false;

  $effect(() => {
    const notesContent = untrack(() => text);
    if (editorEl && projectPath !== lastPath) {
      lastPath = projectPath;
      editorEl.innerHTML = renderMarkdown(notesContent);
      bindCheckboxListeners();
    }
  });

  $effect(() => {
    if (editorEl && !stateDetectBound) {
      stateDetectBound = true;
      editorEl.addEventListener('keyup', updateFormatState);
      editorEl.addEventListener('mouseup', updateFormatState);
      document.addEventListener('selectionchange', updateFormatState);
      window.addEventListener('click', onWindowClick);
    }
  });

  $effect(() => {
    fontSelVal = fs.fontFamily || '';
  });
  $effect(() => {
    sizeSelVal = fs.fontSize || '';
  });
</script>

<div class="ne-root" class:fullscreen>
  <div class="ne-toolbar" bind:this={toolbarEl}>
    <div class="ne-tools" aria-label="Visual formatting">

      <!-- Row: Undo/Redo | Font | Size -->
      <button type="button" class="ne-tbtn" title="Undo" onmousedown={(e) => { e.preventDefault(); formatSimple('undo'); }}>↩</button>
      <button type="button" class="ne-tbtn" title="Redo" onmousedown={(e) => { e.preventDefault(); formatSimple('redo'); }}>↪</button>
      <span class="ne-sep"></span>
      <select id="ne-font-select" class="ne-tbtn ne-tselect" bind:value={fontSelVal} onchange={applyFont} onclick={(e) => e.stopPropagation()}>
        {#each FONTS as f}
          <option value={f.value}>{f.label}</option>
        {/each}
      </select>
      <select id="ne-size-select" class="ne-tbtn ne-tselect" bind:value={sizeSelVal} onchange={applySize} onclick={(e) => e.stopPropagation()}>
        {#each SIZES as s}
          <option value={s}>{s}</option>
        {/each}
      </select>
      <span class="ne-sep"></span>

      <!-- Row: B I U S | Sup Sub -->
      <button type="button" class="ne-tbtn" class:active={fs.bold} title="Bold" onmousedown={(e) => { e.preventDefault(); formatSimple('bold'); }}><strong>B</strong></button>
      <button type="button" class="ne-tbtn" class:active={fs.italic} title="Italic" onmousedown={(e) => { e.preventDefault(); formatSimple('italic'); }}><em>I</em></button>
      <button type="button" class="ne-tbtn" class:active={fs.underline} title="Underline" onmousedown={(e) => { e.preventDefault(); formatSimple('underline'); }}><u>U</u></button>
      <button type="button" class="ne-tbtn" class:active={fs.strikethrough} title="Strikethrough" onmousedown={(e) => { e.preventDefault(); formatSimple('strikeThrough'); }}><s>S</s></button>
      <span class="ne-sep"></span>
      <button type="button" class="ne-tbtn" class:active={fs.superscript} title="Superscript" onmousedown={(e) => { e.preventDefault(); formatSimple('superscript'); }}>x<sup>2</sup></button>
      <button type="button" class="ne-tbtn" class:active={fs.subscript} title="Subscript" onmousedown={(e) => { e.preventDefault(); formatSimple('subscript'); }}>x<sub>2</sub></button>
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
      <button type="button" class="ne-tbtn" class:active={fs.heading === 'h1'} title="Heading 1" onmousedown={(e) => { e.preventDefault(); formatBlockCmd('h1'); }}>H1</button>
      <button type="button" class="ne-tbtn" class:active={fs.heading === 'h2'} title="Heading 2" onmousedown={(e) => { e.preventDefault(); formatBlockCmd('h2'); }}>H2</button>
      <button type="button" class="ne-tbtn" class:active={fs.heading === 'h3'} title="Heading 3" onmousedown={(e) => { e.preventDefault(); formatBlockCmd('h3'); }}>H3</button>
      <button type="button" class="ne-tbtn" class:active={fs.heading === 'p'} title="Paragraph" onmousedown={(e) => { e.preventDefault(); formatBlockCmd('p'); }}>¶</button>
      <span class="ne-sep"></span>
      <button type="button" class="ne-tbtn" class:active={fs.blockquote} title="Blockquote" onmousedown={(e) => { e.preventDefault(); formatBlockCmd('blockquote'); }}>❝</button>
      <button type="button" class="ne-tbtn" class:active={fs.code} title="Inline code" onmousedown={(e) => { e.preventDefault(); formatCode(); }}>{@html '&lt;/&gt;'}</button>
      <button type="button" class="ne-tbtn" class:active={fs.codeBlock} title="Code block" onmousedown={(e) => { e.preventDefault(); formatCodeBlock(); }}>{"</>"}</button>
      <span class="ne-sep"></span>

      <!-- Row: OL UL | Indent Outdent -->
      <button type="button" class="ne-tbtn" class:active={fs.orderedList} title="Numbered list" onmousedown={(e) => { e.preventDefault(); formatSimple('insertOrderedList'); }}>1.</button>
      <button type="button" class="ne-tbtn" class:active={fs.unorderedList} title="Bulleted list" onmousedown={(e) => { e.preventDefault(); formatSimple('insertUnorderedList'); }}>•</button>
      <span class="ne-sep"></span>
      <button type="button" class="ne-tbtn" title="Indent" onmousedown={(e) => { e.preventDefault(); formatSimple('indent'); }}>→</button>
      <button type="button" class="ne-tbtn" title="Outdent" onmousedown={(e) => { e.preventDefault(); formatSimple('outdent'); }}>←</button>
      <span class="ne-sep"></span>

      <!-- Row: Align L C R J -->
      <button type="button" class="ne-tbtn" class:active={fs.align === 'left'} title="Align left" onmousedown={(e) => { e.preventDefault(); formatSimple('justifyLeft'); }}>≡L</button>
      <button type="button" class="ne-tbtn" class:active={fs.align === 'center'} title="Align center" onmousedown={(e) => { e.preventDefault(); formatSimple('justifyCenter'); }}>≡C</button>
      <button type="button" class="ne-tbtn" class:active={fs.align === 'right'} title="Align right" onmousedown={(e) => { e.preventDefault(); formatSimple('justifyRight'); }}>≡R</button>
      <button type="button" class="ne-tbtn" class:active={fs.align === 'justify'} title="Justify" onmousedown={(e) => { e.preventDefault(); formatSimple('justifyFull'); }}>≡J</button>
      <span class="ne-sep"></span>

      <!-- Row: Link HR Table Image Emoji -->
      <button type="button" class="ne-tbtn" class:active={fs.link} title="Link" onmousedown={(e) => { e.preventDefault(); formatLink(); }}>🔗</button>
      <button type="button" class="ne-tbtn" title="Horizontal rule" onmousedown={(e) => { e.preventDefault(); formatSimple('insertHorizontalRule'); }}>HR</button>
      <div class="ne-popover-wrap">
        <button type="button" class="ne-tbtn" title="Table" onmousedown={(e) => { e.preventDefault(); tableOpen=!tableOpen; colorOpen=false; emojiOpen=false; }}>⊞</button>
        {#if tableOpen}
          <div class="ne-popover ne-table-pop">
              {#each Array(10) as _, r}
                <div class="ne-table-row">
                  {#each Array(10) as _, c}
                    <div role="gridcell" tabindex="-1" aria-label="Insert {r + 1} by {c + 1} table" class="ne-tcell" class:ne-thover={r < tableHover.rows && c < tableHover.cols} onmouseenter={() => tableHover = { rows: r + 1, cols: c + 1 }} onmousedown={(e) => { e.preventDefault(); tableHover = { rows: r + 1, cols: c + 1 }; }}></div>
                  {/each}
                </div>
              {/each}
            <div class="ne-table-label">{tableHover.rows} × {tableHover.cols}</div>
            <button type="button" class="ne-tbtn ne-insert-btn" onmousedown={(e) => { e.preventDefault(); insertTable(); }}>Insert table</button>
          </div>
        {/if}
      </div>
      <button type="button" class="ne-tbtn" title="Image" onmousedown={(e) => { e.preventDefault(); formatImage(); }}>🖼</button>
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

      <!-- Row: Todo RemoveFormat -->
      <button type="button" class="ne-tbtn" class:active={fs.todo} title="Checklist" onmousedown={(e) => { e.preventDefault(); formatChecklist(); }}>☑</button>
      <button type="button" class="ne-tbtn" title="Clear formatting" onmousedown={(e) => { e.preventDefault(); formatSimple('removeFormat'); }}>↺</button>
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

  <div
    class="ne-textarea ne-editor-area"
    class:ne-fs={fullscreen}
    contenteditable="true"
    bind:this={editorEl}
    oninput={onEditorInput}
    onblur={onEditorBlur}
    placeholder="Write project notes (autosaves to notes.md)…"
  ></div>
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
  .ne-insert-btn { width:100%; margin-top:2px; }
  .ne-emoji-btn { font-size:16px; width:22px; height:22px; border:0; background:transparent; cursor:pointer; border-radius:3px; padding:0; display:inline-flex; align-items:center; justify-content:center; }
  .ne-emoji-btn:hover { background:var(--soft-pink-surface); }
  .ne-textarea { width:100%; min-height:120px; max-height:300px; padding:10px; background:var(--color-workspace-panel); border:1px solid var(--soft-white-border); border-radius:6px; font-size:12px; font-family:var(--font); color:var(--color-ink); resize:vertical; outline:none; line-height:1.5; overflow-y:auto; flex:1 1 auto; }
  .ne-textarea:focus { border-color:var(--color-dbs-red); }
  .ne-textarea.ne-fs { max-height:none; resize:none; }
  .ne-textarea:empty::before { content:attr(placeholder); color:var(--color-muted); opacity:0.7; pointer-events:none; }
  :global(.ne-todo-item) { display:flex; align-items:center; gap:6px; margin:4px 0; }
  :global(.ne-todo-checkbox) { width:14px; height:14px; cursor:pointer; }
  .ne-status { display:flex; align-items:center; gap:6px; font-size:10px; font-weight:800; color:var(--color-muted); white-space:nowrap; }
  .ne-status.err { color:var(--color-dbs-red); }
  .ne-status.off { color:var(--tag-amber-ink); }
  .ne-dot { font-weight:900; }
  .ne-dot.ne-ok { color:var(--tag-green-ink); }
</style>
