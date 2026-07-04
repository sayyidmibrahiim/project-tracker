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
const DASHBOARD = readFileSync(resolve(__dirname, "../src/lib/components/Dashboard.svelte"), "utf8");

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

test("NotesEditor throttles toolbar refresh outside editor-mount effect", () => {
  assert.match(NE, /let rev = 0/);
  assert.doesNotMatch(NE, /let rev = \$state/);
  assert.match(NE, /let uiTick = \$state\(0\)/);
  assert.match(NE, /function scheduleToolbarRefresh\(\)[\s\S]*requestAnimationFrame[\s\S]*uiTick\+\+/);
  assert.match(NE, /queueMicrotask\([\s\S]*instance\.on\("transaction", scheduleToolbarRefresh\)/);
  assert.match(NE, /function isActive\([^)]*\)[^{]*\{\s*void uiTick;/);
  assert.match(NE, /function alignIs\([^)]*\)[^{]*\{\s*void uiTick;/);
  assert.match(NE, /instance\.off\("transaction", scheduleToolbarRefresh\)/);
});

test("NotesEditor defers DOCX migration save outside editor-mount effect", () => {
  assert.match(NE, /const shouldMigrate = pipeline && migrate/);
  assert.match(NE, /migrationPending = shouldMigrate/);
  assert.match(NE, /queueMicrotask\([\s\S]*flush\("migration"\)/);
  assert.doesNotMatch(NE, /if \(pipeline && migrationPending\) \{\s*dirty = true;\s*void flush\("migration"\);/);
});

test("NotesEditor shows a five-second DOCX idle-export countdown", () => {
  assert.match(NE, /docxCountdownLabel/);
  assert.match(NE, /const IDLE_EXPORT_MS = 5_000/);
  assert.match(NE, /let exportCountdown = \$state\(0\)/);
  assert.match(NE, /function startExportCountdown\(\)[\s\S]*exportCountdown = 5[\s\S]*setInterval/);
  assert.match(NE, /function stopExportCountdown\(\)[\s\S]*clearInterval[\s\S]*exportCountdown = 0/);
  assert.match(NE, /docxCountdownLabel\(exportCountdown\)/);
  assert.match(NE, /stopExportCountdown\(\);\s*void requestDocxExport\(\)/);
});

test("NotesEditor Ctrl+S skips pending DOCX countdown and retries locked export", () => {
  assert.match(NE, /export async function flushNow\(\): Promise<boolean> \{[\s\S]*idleExport\.pending/);
  assert.match(NE, /export async function flushNow\(\): Promise<boolean> \{[\s\S]*exportDisplay === "locked"/);
  assert.match(NE, /export async function flushNow\(\): Promise<boolean> \{[\s\S]*idleExport\.cancel\(\);[\s\S]*stopExportCountdown\(\);[\s\S]*await requestDocxExport\(\)/);
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

test("ProjectDetails routes docx CR docs through the pipeline (D-0012)", () => {
  // docx entries are editable via docx_pipeline unless the project is locked.
  assert.match(PD, /saveStrategy: isLocked \? "none" : "docx_pipeline"/);
  assert.match(PD, /rteDocumentOpen/);
  assert.match(PD, /initialDoc=\{crDocDocPayload\?\.content \?\? null\}/);
  assert.match(PD, /needsMigration=\{crDocDocPayload\?\.needs_migration \?\? false\}/);
  // The editor component owns the pipeline save path.
  const NE_SRC = readFileSync(resolve(__dirname, "../src/lib/components/NotesEditor.svelte"), "utf8");
  assert.match(NE_SRC, /docx_pipeline/);
  assert.match(NE_SRC, /rteDocumentSave/);
  assert.match(NE_SRC, /handlePaste/);
  assert.match(NE_SRC, /IdleExportScheduler/);
});

test("RTE interaction lock does not disable top menu navigation", () => {
  assert.match(APP, /interactionLocks/);
  assert.match(APP, /app:interaction-lock/);
  assert.match(APP, /interactionLocked=\{interactionLocked\}/);
  assert.match(DASHBOARD, /interactionLocked/);

  const navigateToBody = TB.match(/function navigateTo\(id: string\) \{([\s\S]*?)\n  \}/)?.[1] ?? "";
  assert.doesNotMatch(navigateToBody, /interactionLocked/);

  const navEach = TB.match(/<nav class="titlebar-nav">([\s\S]*?)<\/nav>/)?.[1] ?? "";
  assert.doesNotMatch(navEach, /disabled=\{interactionLocked\}/);
  assert.doesNotMatch(navEach, /aria-disabled=\{interactionLocked\}/);
});

test("RTE interaction lock has local cleanup and a 10-second app watchdog", () => {
  const selectCrDocBody = PD.match(/async function selectCrDoc\(path: string\) \{([\s\S]*?)\n  \}/)?.[1] ?? "";
  assert.match(selectCrDocBody, /setInteractionLock\("project-details-rte", true\)/);
  assert.match(selectCrDocBody, /finally \{[\s\S]*setInteractionLock\("project-details-rte", false\)/);

  assert.match(APP, /const INTERACTION_LOCK_WATCHDOG_MS = 10_000/);
  assert.match(APP, /setTimeout\([\s\S]*INTERACTION_LOCK_WATCHDOG_MS/);
  assert.match(APP, /interactionLocks = new Set\(\)/);
  assert.match(APP, /console\.warn\("interaction-lock watchdog released"\)/);
  assert.match(APP, /clearTimeout\(interactionLockWatchdog\)/);
});
