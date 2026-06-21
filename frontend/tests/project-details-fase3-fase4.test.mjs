import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PD = readFileSync(resolve(__dirname, "../src/lib/components/ProjectDetails.svelte"), "utf8");
const NE = readFileSync(resolve(__dirname, "../src/lib/components/NotesEditor.svelte"), "utf8");

test("NotesEditor uses contenteditable instead of textarea for WYSIWYG", () => {
  assert.match(NE, /contenteditable="true"/);
  assert.doesNotMatch(NE, /<textarea/);
});

test("NotesEditor converts HTML checkboxes to markdown and vice-versa", () => {
  assert.match(NE, /htmlToMarkdown/);
  assert.match(NE, /ne-todo-checkbox/);
  assert.match(NE, /- \[ \]/);
  assert.match(NE, /- \[x\]/);
});

test("ProjectDetails disables CR and schedule inputs for sub-projects", () => {
  assert.match(PD, /isSubproject/);
  assert.match(PD, /disabled=\{[^}]*isSubproject\}/);
  assert.match(PD, /pd-inherited-label/);
});
