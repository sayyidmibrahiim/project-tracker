<script lang="ts">
  /**
   * Notes editor — Fase 3: Visual contenteditable WYSIWYG editor.
   *
   *  - Direct visual formatting (Bold, Italic, lists, quotes, checkboxes, links, code).
   *  - Automatic HTML-to-Markdown roundtrip conversion for saving to disk as notes.md.
   *  - Checklist toggle syncs back to markdown checkboxes ([ ] / [x]) and saves.
   *  - Proportional system fonts (Inter) for cleaner Notion-style nuance.
   */
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

  let text = $state(untrack(() => initialNotes ?? ""));
  let status = $state<SaveStatus>("idle");
  let errorText = $state("");
  let editorEl = $state<HTMLDivElement | null>(null);
  let lastSaved = $state(untrack(() => initialNotes ?? ""));

  const AUTOSAVE_MS = 1000;
  let timer: ReturnType<typeof setTimeout> | undefined;

  const statusLabel = $derived(
    status === "saving"
      ? "Saving…"
      : status === "saved"
        ? "Saved"
        : status === "pending"
          ? "Editing…"
          : status === "offline"
            ? "Offline — notes not saved in browser preview"
            : status === "error"
              ? `Save failed: ${errorText}`
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
    if (timer) {
      clearTimeout(timer);
      timer = undefined;
    }
    if (text === lastSaved) {
      status = "saved";
      return;
    }
    if (!isPywebviewReady()) {
      status = "offline";
      return;
    }
    status = "saving";
    errorText = "";
    const resp = await callBridge("notes_update", projectPath, text);
    if (!resp.ok) {
      status = "error";
      errorText = resp.error.message;
      return;
    }
    lastSaved = text;
    status = "saved";
    onSaved?.(text);
  }

  onDestroy(() => {
    if (timer) clearTimeout(timer);
  });

  // ── HTML-to-Markdown Bidirectional Roundtrip ──

  function domToMarkdown(node: Node): string {
    if (node.nodeType === Node.TEXT_NODE) {
      return node.textContent || "";
    }
    if (node.nodeType !== Node.ELEMENT_NODE) {
      return "";
    }
    const el = node as HTMLElement;
    const tagName = el.tagName.toLowerCase();

    // Check if it's a checklist item
    if (el.classList.contains("ne-todo-item")) {
      const checkbox = el.querySelector("input[type='checkbox']") as HTMLInputElement | null;
      const textSpan = el.querySelector("span") as HTMLElement | null;
      const checked = checkbox?.checked ? "x" : " ";
      const textContent = textSpan ? Array.from(textSpan.childNodes).map(domToMarkdown).join("") : "";
      return `- [${checked}] ${textContent.trim()}\n`;
    }

    const childrenMd = Array.from(el.childNodes).map(domToMarkdown).join("");

    switch (tagName) {
      case "h1": return `# ${childrenMd.trim()}\n\n`;
      case "h2": return `## ${childrenMd.trim()}\n\n`;
      case "h3": return `### ${childrenMd.trim()}\n\n`;
      case "blockquote": return `> ${childrenMd.trim()}\n\n`;
      case "li": return `- ${childrenMd.trim()}\n`;
      case "ul": return `${childrenMd}\n`;
      case "strong":
      case "b": return `**${childrenMd}**`;
      case "em":
      case "i": return `*${childrenMd}*`;
      case "code": return `\`${childrenMd}\``;
      case "a": return `[${childrenMd}](${el.getAttribute("href") || ""})`;
      case "p": return `${childrenMd.trim()}\n\n`;
      case "div": return `${childrenMd}\n`;
      case "br": return "\n";
      default: return childrenMd;
    }
  }

  function htmlToMarkdown(html: string): string {
    if (!html) return "";
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, "text/html");
    let md = Array.from(doc.body.childNodes).map(domToMarkdown).join("");
    md = md.replace(/\n{3,}/g, "\n\n");
    return md.trim();
  }

  function syncToMarkdown() {
    if (editorEl) {
      text = htmlToMarkdown(editorEl.innerHTML);
      scheduleSave();
    }
  }

  function onEditorInput() {
    scheduleSave();
  }

  function onEditorBlur() {
    if (editorEl) text = htmlToMarkdown(editorEl.innerHTML);
    if (status === "pending" || timer) {
      if (timer) { clearTimeout(timer); timer = undefined; }
      flush();
    }
  }

  function bindCheckboxListeners() {
    if (!editorEl) return;
    const boxes = editorEl.querySelectorAll(".ne-todo-checkbox");
    boxes.forEach(box => {
      box.removeEventListener("change", syncToMarkdown);
      box.addEventListener("change", syncToMarkdown);
    });
  }

  // Sync Markdown to HTML editor area on component initialization and path switches
  let lastPath = "";
  $effect(() => {
    const notesContent = untrack(() => text);
    if (editorEl && projectPath !== lastPath) {
      lastPath = projectPath;
      editorEl.innerHTML = renderMarkdown(notesContent);
      bindCheckboxListeners();
    }
  });

  // ── WYSIWYG commands ──

  function format(command: string, value: string = "") {
    document.execCommand(command, false, value);
    scheduleSave();
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
  }

  function formatLink() {
    const url = prompt("Enter URL:");
    if (url) format("createLink", url);
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
        const fragment = range.createContextualFragment(html);
        range.insertNode(fragment);
      }
    }
    editorEl.focus();
    setTimeout(bindCheckboxListeners, 50);
    scheduleSave();
  }
</script>

<div class="ne-root">
  <div class="ne-toolbar">
    <div class="ne-tools" aria-label="Visual formatting">
      <button type="button" class="ne-tbtn" title="Bold" onmousedown={(e) => { e.preventDefault(); format('bold'); }}><strong>B</strong></button>
      <button type="button" class="ne-tbtn" title="Italic" onmousedown={(e) => { e.preventDefault(); format('italic'); }}><em>I</em></button>
      <button type="button" class="ne-tbtn" title="Heading 1" onmousedown={(e) => { e.preventDefault(); format('formatBlock', '<h1>'); }}>H1</button>
      <button type="button" class="ne-tbtn" title="Heading 2" onmousedown={(e) => { e.preventDefault(); format('formatBlock', '<h2>'); }}>H2</button>
      <button type="button" class="ne-tbtn" title="Inline code" onmousedown={(e) => { e.preventDefault(); formatCode(); }}>Code</button>
      <button type="button" class="ne-tbtn" title="Bulleted list" onmousedown={(e) => { e.preventDefault(); format('insertUnorderedList'); }}>List</button>
      <button type="button" class="ne-tbtn" title="Quote" onmousedown={(e) => { e.preventDefault(); format('formatBlock', '<blockquote>'); }}>Quote</button>
      <button type="button" class="ne-tbtn" title="Link" onmousedown={(e) => { e.preventDefault(); formatLink(); }}>Link</button>
      <button type="button" class="ne-tbtn" title="Checklist" onmousedown={(e) => { e.preventDefault(); formatChecklist(); }}>Todo</button>
    </div>
  </div>

  <div
    class="ne-textarea ne-editor-area"
    contenteditable="true"
    bind:this={editorEl}
    oninput={onEditorInput}
    onblur={onEditorBlur}
    placeholder="Write project notes (autosaves to notes.md)…"
  ></div>

  <div class="ne-status" class:err={status === "error"} class:off={status === "offline"} role="status">
    {#if status === "saving"}<span class="ne-dot">◌</span>{:else if status === "saved"}<span class="ne-dot ne-ok">✓</span>{/if}
    <span>{statusLabel}</span>
  </div>
</div>

<style>
  .ne-root { display:flex; flex-direction:column; gap:6px; }
  .ne-toolbar { display:flex; align-items:center; justify-content:space-between; gap:8px; flex-wrap:wrap; }
  .ne-tools { display:flex; gap:3px; flex-wrap:wrap; }
  .ne-tbtn { min-width:26px; height:24px; padding:0 7px; border:1px solid #D7DCE2; border-radius:5px; background:#fff; color:var(--color-ink); font-size:10px; font-weight:850; cursor:pointer; }
  .ne-tbtn:hover { border-color:var(--color-dbs-red); color:var(--color-dbs-red); }
  .ne-textarea { width:100%; min-height:120px; max-height:300px; padding:10px; background:var(--color-workspace-panel); border:1px solid #D7DCE2; border-radius:6px; font-size:12px; font-family:var(--font); color:var(--color-ink); resize:vertical; outline:none; line-height:1.5; overflow-y:auto; }
  .ne-textarea:focus { border-color:var(--color-dbs-red); }
  .ne-textarea:empty::before { content: attr(placeholder); color: var(--color-muted); opacity: 0.7; pointer-events: none; display: block; }
  :global(.ne-todo-item) { display: flex; align-items: center; gap: 6px; margin: 4px 0; }
  :global(.ne-todo-checkbox) { width: 14px; height: 14px; cursor: pointer; }
  .ne-status { display:flex; align-items:center; gap:6px; font-size:10px; font-weight:800; color:var(--color-muted); }
  .ne-status.err { color:var(--color-dbs-red); }
  .ne-status.off { color:#92400e; }
  .ne-dot { font-weight:900; }
  .ne-dot.ne-ok { color:#15803D; }
</style>
