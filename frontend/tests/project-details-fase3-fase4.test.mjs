import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PD = readFileSync(resolve(__dirname, "../src/lib/components/ProjectDetails.svelte"), "utf8");
const NE = readFileSync(resolve(__dirname, "../src/lib/components/NotesEditor.svelte"), "utf8");

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
  assert.match(NE, /taskItem/);
  assert.match(NE, /checked \? "x" : " "/);
  assert.match(NE, /- \[\$\{ch\}\]/);
});

test("ProjectDetails disables CR and schedule inputs for drones", () => {
  assert.match(PD, /isSubproject/);
  assert.match(PD, /disabled=\{[^}]*isSubproject\}/);
  assert.match(PD, /pd-inherited-label/);
});
