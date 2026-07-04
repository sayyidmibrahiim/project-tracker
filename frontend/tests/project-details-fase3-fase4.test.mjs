import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PD = readFileSync(resolve(__dirname, "../src/lib/components/ProjectDetails.svelte"), "utf8");
const NE = readFileSync(resolve(__dirname, "../src/lib/components/NotesEditor.svelte"), "utf8");
const APP = readFileSync(resolve(__dirname, "../src/App.svelte"), "utf8");
const TB = readFileSync(resolve(__dirname, "../src/lib/components/TitleBar.svelte"), "utf8");
const HEADER = readFileSync(resolve(__dirname, "../src/lib/components/Header.svelte"), "utf8");

test("NotesEditor uses a Tiptap contenteditable editor (not a textarea) for WYSIWYG", () => {
  // D-0007: the editing core is Tiptap (ProseMirror). The contenteditable is
  // mounted programmatically by the Editor instance (no literal attribute), so
  // we assert on the architecture rather than the markup.
  assert.match(NE, /from "@tiptap\/core"/);
  assert.match(NE, /new Editor\(/);
  assert.doesNotMatch(NE, /<textarea/);
});

test("NotesEditor converts Tiptap task items to markdown and vice-versa", () => {
  // The markdown contract is preserved: editor HTML → domToMarkdown → notes.md,
  // and renderMarkdown emits the Tiptap task-list shape on reload.
  assert.match(NE, /htmlToMarkdown/);
  assert.match(NE, /TaskList/);
  assert.match(NE, /TaskItem/);
  assert.match(NE, /htmlToMarkdown/);
});

test("NotesEditor saves pending dirty content before dispose clears debounce", () => {
  assert.match(NE, /function savePendingBeforeDispose\(/);
  assert.match(NE, /const pendingHtml = editor\.getHTML\(\)/);
  assert.match(NE, /void saveSnapshot\(/);
  assert.match(NE, /onDestroy\(\(\) => \{[\s\S]*savePendingBeforeDispose\(\)[\s\S]*clearTimeout\(timer\)/);
});

test("ProjectDetails uses isNonCr to switch identity and hide CR/Drone for Non-CR", () => {
  assert.match(PD, /isNonCr/);
  assert.match(PD, /set_non_cr_state/);
  assert.match(PD, /Non-CR state/);
  assert.doesNotMatch(PD, /isSubproject/);
});

test("ProjectDetails no longer exposes Export to Word UI for active RTE files", () => {
  assert.doesNotMatch(PD, /Export to Word/);
  assert.doesNotMatch(PD, /exportSelectedDocToWord/);
  assert.doesNotMatch(PD, /exportToDocx/);
});

test("ProjectDetails flushes active editor before switching CR docs", () => {
  assert.match(PD, /let rteEditorFlush/);
  assert.match(PD, /await rteEditorFlush\?\.\(\)/);
  assert.match(PD, /async function selectCrDoc\(path: string\)[\s\S]*await rteEditorFlush\?\.\(\)[\s\S]*selectedCrDocPath = path/);
});

test("ProjectDetails avoids bind:this RTE refs", () => {
  assert.match(PD, /onReady=\{setRteEditorApi\}/);
  assert.doesNotMatch(PD, /rteEditorRef/);
  assert.doesNotMatch(PD, /bind:this=\{rteEditor/);
});

test("ProjectDetails renders capability-aware read-only and unsupported states", () => {
  assert.match(PD, /capability/);
  assert.match(PD, /Read-only/);
  assert.match(PD, /Unsupported format/);
  assert.match(PD, /Save failed/);
});

test("RTE interaction lock does not disable top menu navigation", () => {
  assert.match(APP, /interactionLocks/);
  assert.match(APP, /app:interaction-lock/);
  assert.match(APP, /interactionLocked=\{interactionLocked\}/);
  assert.match(HEADER, /interactionLocked/);

  const navigateToBody = TB.match(/function navigateTo\(id: string\) \{([\s\S]*?)\n  \}/)?.[1] ?? "";
  assert.doesNotMatch(navigateToBody, /interactionLocked/);

  const navEach = TB.match(/<nav class="titlebar-nav">([\s\S]*?)<\/nav>/)?.[1] ?? "";
  assert.doesNotMatch(navEach, /disabled=\{interactionLocked\}/);
  assert.doesNotMatch(navEach, /aria-disabled=\{interactionLocked\}/);
});
