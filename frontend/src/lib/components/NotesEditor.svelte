<script lang="ts">
  /**
   * Notes editor — PRD §12.12.
   *
   *  - Autosave 1000ms after the last keystroke (replaces the old explicit
   *    "Save Notes" button — fewer clicks for the daily workflow). Status shows
   *    Editing… / Saving… / Saved / error, and a blur flushes a pending save.
   *  - Markdown toolbar inserts syntax at the caret (bold/italic/H1/H2/code/
   *    list/quote/link).
   *  - Edit/Preview toggle renders a safe Markdown subset (see lib/markdown.ts;
   *    no marked.js dependency is added).
   *
   * Notes remain editable regardless of Folder_State, matching PRD §12.11
   * ("all file ops disabled in PROD_READY and IMPLEMENTED states except
   * Add/Edit Notes") and the prior ProjectDetails behavior. All bridge access is
   * via callBridge; in a browser preview (no bridge) autosave reports "offline"
   * instead of erroring.
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
  let mode: "edit" | "preview" = $state("edit");
  let status = $state<SaveStatus>("idle");
  let errorText = $state("");
  let textarea: HTMLTextAreaElement | null = $state(null);
  let lastSaved = $state(untrack(() => initialNotes ?? ""));

  const AUTOSAVE_MS = 1000;
  let timer: ReturnType<typeof setTimeout> | undefined;

  const preview = $derived(renderMarkdown(text));
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
    timer = setTimeout(flush, AUTOSAVE_MS);
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

  function onInput() {
    scheduleSave();
  }
  function onBlur() {
    if (status === "pending") flush();
  }

  onDestroy(() => {
    if (timer) clearTimeout(timer);
  });

  async function surround(before: string, after: string) {
    const el = textarea;
    if (!el) {
      text = before + text + after;
      scheduleSave();
      return;
    }
    const s = el.selectionStart ?? text.length;
    const e = el.selectionEnd ?? s;
    const selected = text.slice(s, e);
    text = text.slice(0, s) + before + selected + after + text.slice(e);
    scheduleSave();
    await tick();
    el.focus();
    const pos = s + before.length + selected.length + after.length;
    try {
      el.setSelectionRange(pos, pos);
    } catch {
      /* ignore */
    }
  }

  async function prefixLine(prefix: string) {
    const el = textarea;
    if (!el) {
      text = prefix + text;
      scheduleSave();
      return;
    }
    const s = el.selectionStart ?? 0;
    const lineStart = text.lastIndexOf("\n", s - 1) + 1;
    text = text.slice(0, lineStart) + prefix + text.slice(lineStart);
    scheduleSave();
    await tick();
    el.focus();
    const pos = s + prefix.length;
    try {
      el.setSelectionRange(pos, pos);
    } catch {
      /* ignore */
    }
  }
</script>

<div class="ne-root">
  <div class="ne-toolbar">
    <div class="ne-tools" aria-label="Markdown formatting">
      <button type="button" class="ne-tbtn" title="Bold" onclick={() => surround("**", "**")}><strong>B</strong></button>
      <button type="button" class="ne-tbtn" title="Italic" onclick={() => surround("*", "*")}><em>I</em></button>
      <button type="button" class="ne-tbtn" title="Heading 1" onclick={() => prefixLine("# ")}>H1</button>
      <button type="button" class="ne-tbtn" title="Heading 2" onclick={() => prefixLine("## ")}>H2</button>
      <button type="button" class="ne-tbtn" title="Inline code" onclick={() => surround("`", "`")}>Code</button>
      <button type="button" class="ne-tbtn" title="Bulleted list" onclick={() => prefixLine("- ")}>List</button>
      <button type="button" class="ne-tbtn" title="Quote" onclick={() => prefixLine("> ")}>Quote</button>
      <button type="button" class="ne-tbtn" title="Link" onclick={() => surround("[", "](https://)")}>Link</button>
    </div>
    <div class="ne-modes" aria-label="Editor mode">
      <button type="button" class="ne-mode" class:active={mode === "edit"} onclick={() => (mode = "edit")}>Edit</button>
      <button type="button" class="ne-mode" class:active={mode === "preview"} onclick={() => (mode = "preview")}>Preview</button>
    </div>
  </div>

  {#if mode === "edit"}
    <textarea
      class="ne-textarea"
      bind:this={textarea}
      bind:value={text}
      oninput={onInput}
      onblur={onBlur}
      placeholder="Write project notes (Markdown — autosaves to notes.md)…"
      rows="8"
    ></textarea>
  {:else}
    <div class="ne-preview">
      {#if text.trim() === ""}
        <p class="ne-empty">Nothing to preview.</p>
      {:else}
        <!-- eslint-disable-next-line svelte/no-at-html-tags — renderMarkdown escapes all input and sanitizes hrefs -->
        {@html preview}
      {/if}
    </div>
  {/if}

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
  .ne-modes { display:flex; gap:3px; }
  .ne-mode { height:24px; padding:0 10px; border:1px solid #D7DCE2; border-radius:5px; background:#fff; color:var(--color-ink); font-size:10px; font-weight:850; cursor:pointer; }
  .ne-mode:hover { border-color:var(--color-dbs-red); color:var(--color-dbs-red); }
  .ne-mode.active { background:var(--color-dbs-red); border-color:var(--color-dbs-red); color:#fff; }
  .ne-textarea { width:100%; min-height:120px; max-height:300px; padding:10px; background:var(--color-workspace-panel); border:1px solid #D7DCE2; border-radius:6px; font-size:11px; font-family:"JetBrains Mono","Fira Code",monospace; color:var(--color-ink); resize:vertical; outline:none; line-height:1.5; }
  .ne-textarea:focus { border-color:var(--color-dbs-red); }
  .ne-preview { min-height:120px; max-height:300px; overflow-y:auto; padding:10px 12px; background:#fff; border:1px solid #D7DCE2; border-radius:6px; font-size:12px; color:var(--color-ink); line-height:1.55; }
  .ne-preview :global(h1) { font-size:17px; font-weight:900; margin:6px 0; }
  .ne-preview :global(h2) { font-size:15px; font-weight:900; margin:6px 0; }
  .ne-preview :global(h3) { font-size:13px; font-weight:900; margin:5px 0; }
  .ne-preview :global(p) { margin:5px 0; }
  .ne-preview :global(ul) { margin:5px 0; padding-left:20px; }
  .ne-preview :global(li) { margin:2px 0; }
  .ne-preview :global(blockquote) { margin:5px 0; padding:4px 10px; border-left:3px solid var(--color-dbs-red); background:var(--color-workspace-panel); color:var(--color-muted); }
  .ne-preview :global(code) { font-family:"JetBrains Mono","Fira Code",monospace; font-size:11px; background:var(--color-workspace-panel); padding:1px 4px; border-radius:3px; }
  .ne-preview :global(pre) { background:var(--color-workspace-panel); padding:8px 10px; border-radius:6px; overflow-x:auto; margin:6px 0; }
  .ne-preview :global(pre code) { background:transparent; padding:0; }
  .ne-preview :global(a) { color:var(--color-dbs-red); font-weight:800; }
  .ne-empty { color:var(--color-muted); font-style:italic; }
  .ne-status { display:flex; align-items:center; gap:6px; font-size:10px; font-weight:800; color:var(--color-muted); }
  .ne-status.err { color:var(--color-dbs-red); }
  .ne-status.off { color:#92400e; }
  .ne-dot { font-weight:900; }
  .ne-dot.ne-ok { color:#15803D; }
</style>
