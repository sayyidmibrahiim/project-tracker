/**
 * Second Brain completion — frontend contract tests (Task 7+).
 *
 * Source-structure assertions per the project's no-DOM-library convention:
 * types.ts holds only compile-time interfaces/type aliases (erased at
 * runtime), so contracts are verified by reading the source text rather than
 * importing and instantiating values. See project-details-fase1.test.mjs /
 * components.test.mjs for the same style.
 *
 * Task 7 covers only `frontend/src/lib/types.ts` DTOs. Later tasks (8, 9, 10)
 * append their own source-contract tests to this same file.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const TYPES = readFileSync(resolve(__dirname, "../src/lib/types.ts"), "utf8");
const NOTES = readFileSync(resolve(__dirname, "../src/lib/components/SecondBrainNotes.svelte"), "utf8");
const LINKBANK = readFileSync(resolve(__dirname, "../src/lib/components/LinkBank.svelte"), "utf8");
const SHELL = readFileSync(resolve(__dirname, "../src/lib/components/SecondBrain.svelte"), "utf8");

/** Grab the `<style>…</style>` block of a Svelte component. */
function styleBlock(source) {
  const match = source.match(/<style>([\s\S]*?)<\/style>/);
  assert.ok(match, "component has a scoped <style> block");
  return match[1];
}

/** Grab the body of `[async] function name(` up to the matching brace column. */
function fnBody(source, name) {
  const start = source.search(new RegExp(`(?:async\\s+)?function ${name}\\s*\\(`));
  assert.ok(start >= 0, `function ${name} not found`);
  // Body runs from the first "{" after the signature to the first "\n  }" (2-space dedent).
  const open = source.indexOf("{", start);
  const end = source.indexOf("\n  }", open);
  assert.ok(end > open, `function ${name} body not delimited`);
  return source.slice(open, end);
}

/** Extract the body of `export interface Name { ... }` (non-greedy, first match). */
function interfaceBody(source, name) {
  const match = source.match(new RegExp(`export interface ${name}\\s*\\{([\\s\\S]*?)\\n\\}`));
  assert.ok(match, `export interface ${name} not found`);
  return match[1];
}

/** Extract the RHS of `export type Name = ...;` (first match). */
function typeAliasBody(source, name) {
  const match = source.match(new RegExp(`export type ${name}\\s*=\\s*([^;]+);`));
  assert.ok(match, `export type ${name} not found`);
  return match[1];
}

// --- New Second Brain scalar type aliases ------------------------------------

test("SecondBrainSource is personal | project", () => {
  const body = typeAliasBody(TYPES, "SecondBrainSource");
  assert.match(body, /"personal"/);
  assert.match(body, /"project"/);
});

test("SecondBrainOpenMode classifies Markdown/text/DOCX/image/external", () => {
  const body = typeAliasBody(TYPES, "SecondBrainOpenMode");
  assert.match(body, /"markdown"/);
  assert.match(body, /"text"/);
  assert.match(body, /"docx"/);
  assert.match(body, /"image"/);
  assert.match(body, /"external"/);
});

test("SecondBrainPersonalStatus matches the workspace() contract", () => {
  const body = typeAliasBody(TYPES, "SecondBrainPersonalStatus");
  for (const value of ["ready", "unset", "missing", "invalid", "unreadable"]) {
    assert.match(body, new RegExp(`"${value}"`));
  }
});

test("SecondBrainSort matches the search() sort contract (default newest)", () => {
  const body = typeAliasBody(TYPES, "SecondBrainSort");
  assert.match(body, /"newest"/);
  assert.match(body, /"oldest"/);
  assert.match(body, /"az"/);
  assert.match(body, /"type"/);
});

// --- SecondBrainItem: existing fields preserved + Task 2 fields added --------

test("SecondBrainItem keeps existing fields and adds all Task 2 index fields", () => {
  const body = interfaceBody(TYPES, "SecondBrainItem");
  // Existing fields (must not be dropped).
  for (const field of ["id", "title", "path", "item_type", "updated_at", "pinned", "favorite", "excerpt"]) {
    assert.match(body, new RegExp(`\\b${field}\\??:`), `SecondBrainItem missing existing field ${field}`);
  }
  // Task 2 additions.
  for (const field of [
    "source",
    "relative_path",
    "tree_path",
    "parent_path",
    "open_mode",
    "file_format",
    "project_path",
    "project_state",
    "appcode",
    "year",
    "project_name",
    "drone_name",
    "locked",
    "tags",
    "match_reason",
  ]) {
    assert.match(body, new RegExp(`\\b${field}\\??:`), `SecondBrainItem missing added field ${field}`);
  }
  assert.match(body, /source:\s*SecondBrainSource/);
  assert.match(body, /open_mode:\s*SecondBrainOpenMode/);
  assert.match(body, /tags:\s*string\[\]/);
});

test("SecondBrainActivity id mirrors backend integer primary key", () => {
  assert.match(interfaceBody(TYPES, "SecondBrainActivity"), /\bid:\s*number\s*;/);
});

// --- SecondBrainWorkspace: mirrors workspace() from Task 2 -------------------

test("SecondBrainWorkspace mirrors workspace() { items, warnings, personal_root, project_root, personal_status }", () => {
  const body = interfaceBody(TYPES, "SecondBrainWorkspace");
  assert.match(body, /items:\s*SecondBrainItem\[\]/);
  assert.match(body, /warnings:\s*string\[\]/);
  assert.match(body, /personal_root:/);
  assert.match(body, /project_root:/);
  assert.match(body, /personal_status:\s*SecondBrainPersonalStatus/);
});

// --- SecondBrainRelated: mirrors related() rows from Task 3 ------------------

test("SecondBrainRelated mirrors related() { item, reason, score } rows", () => {
  const body = interfaceBody(TYPES, "SecondBrainRelated");
  assert.match(body, /item:\s*SecondBrainItem/);
  assert.match(body, /reason:/);
  assert.match(body, /score:\s*number/);
});

// --- SecondBrainActivity: mirrors SecondBrainActivityRow from Task 5 --------

test("SecondBrainActivity mirrors SecondBrainActivityRow(id, item_id, path, title, source, action, timestamp)", () => {
  const body = interfaceBody(TYPES, "SecondBrainActivity");
  for (const field of ["id", "item_id", "path", "title", "source", "action", "timestamp"]) {
    assert.match(body, new RegExp(`\\b${field}:`), `SecondBrainActivity missing field ${field}`);
  }
  assert.match(body, /source:\s*SecondBrainSource/);
  // Supported actions from Task 5 item 2.
  for (const action of ["opened", "created", "edited", "renamed", "recycled", "opened_externally"]) {
    assert.match(body, new RegExp(`"${action}"`));
  }
});

// --- SecondBrainImage: guarded image preview read ----------------------------

test("SecondBrainImage exposes data_uri and name (mirrors util_choose_image shape)", () => {
  const body = interfaceBody(TYPES, "SecondBrainImage");
  assert.match(body, /data_uri:/);
  assert.match(body, /name:/);
});

// --- Link Bank DTOs (Task 6 contracts) ---------------------------------------

test("LinkItem carries canonical details/notes plus legacy-compatible description mapping", () => {
  const body = interfaceBody(TYPES, "LinkItem");
  for (const field of [
    "id",
    "name",
    "url",
    "category",
    "tags",
    "notes",
    "details",
    "archived",
    "created_at",
    "updated_at",
  ]) {
    assert.match(body, new RegExp(`\\b${field}\\??:`), `LinkItem missing field ${field}`);
  }
  // Legacy-compatible optional description mapping (canonical storage is details/notes).
  assert.match(body, /description\?:/);
});

test("LinkItem: pinned/favorite/archived must be literal \"true\" | \"false\", not bare string", () => {
  const body = interfaceBody(TYPES, "LinkItem");
  // All three booleans must be typed as literal string union, not bare `string`.
  assert.match(body, /pinned:\s*"true"\s*\|\s*"false"/);
  assert.match(body, /favorite:\s*"true"\s*\|\s*"false"/);
  assert.match(body, /archived:\s*"true"\s*\|\s*"false"/);
});

test("LinkItem: tags/details/pinned/favorite/created_at/updated_at must be required (not optional)", () => {
  const body = interfaceBody(TYPES, "LinkItem");
  // These fields are always populated by _normalize_link, so no `?`.
  assert.match(body, /tags:\s*string/);
  assert.match(body, /details:\s*string/);
  assert.match(body, /pinned:\s*"true"\s*\|\s*"false"/);
  assert.match(body, /favorite:\s*"true"\s*\|\s*"false"/);
  assert.match(body, /created_at:\s*string/);
  assert.match(body, /updated_at:\s*string/);
  // Verify none have the `?` optional marker.
  const requiredFields = ["tags:", "details:", "created_at:", "updated_at:"];
  for (const field of requiredFields) {
    // Check that the field exists without `?` before the colon.
    assert.ok(body.includes(field), `LinkItem missing required field ${field}`);
    // Double-check: make sure there's no `${field}?:` variant.
    const fieldWithOptional = field.replace(":", "?:");
    assert.ok(!body.includes(fieldWithOptional), `LinkItem field ${field} should not be optional`);
  }
});

test("LinkBankData adds archived_categories alongside categories/links", () => {
  const body = interfaceBody(TYPES, "LinkBankData");
  assert.match(body, /categories:\s*string\[\]/);
  assert.match(body, /archived_categories:\s*string\[\]/);
  assert.match(body, /links:\s*LinkItem\[\]/);
});

test("LinkImportPreview reports add/update/conflict/invalid counts and skipped rows without writing", () => {
  const body = interfaceBody(TYPES, "LinkImportPreview");
  for (const field of ["add", "update", "conflict", "invalid"]) {
    assert.match(body, new RegExp(`\\b${field}:\\s*number`), `LinkImportPreview missing count field ${field}`);
  }
  assert.match(body, /skipped:/);
});

test("LinkImportResult reflects the confirmed merge outcome", () => {
  const body = interfaceBody(TYPES, "LinkImportResult");
  for (const field of ["added", "updated", "conflicts", "invalid"]) {
    assert.match(body, new RegExp(`\\b${field}:\\s*number`), `LinkImportResult missing count field ${field}`);
  }
  assert.doesNotMatch(body, /bank\??:/);
});

test("LinkExportPayload carries a suggested name + content pair usable with util_save_file", () => {
  const body = interfaceBody(TYPES, "LinkExportPayload");
  assert.match(body, /suggested_name:\s*string/);
  assert.match(body, /content:\s*string/);
  assert.match(body, /format:/);
  assert.match(body, /"json"/);
  assert.match(body, /"csv"/);
});

// --- Guard: existing RTE/capability/feature/save-strategy types unweakened --

test("RteFileContent keeps its full required shape (not weakened)", () => {
  const body = interfaceBody(TYPES, "RteFileContent");
  assert.match(body, /content:\s*string;/);
  assert.match(body, /format:\s*RteFormat;/);
  assert.match(body, /editable:\s*boolean;/);
});

test("RteDocumentPayload keeps its full required shape (not weakened)", () => {
  const body = interfaceBody(TYPES, "RteDocumentPayload");
  assert.match(body, /needs_migration:\s*boolean;/);
  assert.match(body, /revision:\s*number;/);
  assert.match(body, /content_hash:\s*string;/);
  assert.match(body, /format:\s*"docx";/);
  assert.match(body, /editable:\s*boolean;/);
  assert.match(body, /capability:\s*RteCapabilityLevel;/);
  assert.match(body, /saveStrategy:\s*RteSaveStrategy;/);
  assert.match(body, /supportedEditorFeatures:\s*RteEditorFeature\[\];/);
  assert.match(body, /export:\s*RteExportState;/);
});

test("RteCapabilityLevel, RteSaveStrategy, RteEditorFeature type aliases are untouched", () => {
  assert.match(TYPES, /export type RteCapabilityLevel = "editable" \| "read_only" \| "unsupported";/);
  assert.match(
    TYPES,
    /export type RteSaveStrategy = "markdown" \| "plain_text" \| "html" \| "docx_legacy" \| "docx_pipeline" \| "none";/,
  );
  assert.match(TYPES, /export type RteEditorFeature =/);
});

// --- Task 8: SecondBrainNotes.svelte source contracts ------------------------

test("SecondBrainNotes imports and mounts the shared NotesEditor unchanged", () => {
  assert.match(NOTES, /import NotesEditor from "\.\/NotesEditor\.svelte"/);
  assert.match(NOTES, /<NotesEditor\b/);
});

test("SecondBrainNotes has no forked editor: no <textarea> and no markdown-toolbar shim", () => {
  assert.doesNotMatch(NOTES, /<textarea/);
  assert.doesNotMatch(NOTES, /insertMarkdown/);
});

test("SecondBrainNotes exposes the public refresh() and flush() API", () => {
  assert.match(NOTES, /export async function refresh\s*\(/);
  assert.match(NOTES, /export async function flush\s*\(/);
});

test("Selection flushes the current editor BEFORE assigning/loading the next item", () => {
  const body = fnBody(NOTES, "selectItem");
  const flushIdx = body.search(/flushCurrentEditor\s*\(/);
  const assignIdx = body.search(/selectedItem\s*=\s*item/);
  assert.ok(flushIdx >= 0, "selectItem must flush the current editor");
  assert.ok(assignIdx >= 0, "selectItem must assign the requested item");
  assert.ok(flushIdx < assignIdx, "flush must run before the selection assignment");
  // Abort + retain when flush reports a failed save.
  assert.match(body, /flushed === false/);
});

test("Selection rechecks its monotonic token after async flush before assigning", () => {
  const body = fnBody(NOTES, "selectItem");
  const flushIdx = body.search(/await\s+flushCurrentEditor\s*\(/);
  const tokenCheckIdx = body.search(/if\s*\(\s*token\s*!==\s*loadSeq\s*\)\s*return/);
  const assignIdx = body.search(/selectedItem\s*=\s*item/);
  assert.ok(flushIdx >= 0 && tokenCheckIdx > flushIdx, "token must be rechecked after flush");
  assert.ok(assignIdx > tokenCheckIdx, "stale selection must return before assignment");
});

test("Hidden mounted Notes ignores global shortcuts", () => {
  const body = fnBody(NOTES, "onKeydown");
  assert.match(body, /rootEl\.offsetParent\s*===\s*null/);
  assert.match(NOTES, /bind:this=\{rootEl\}/);
});

for (const functionName of ["commitRename", "confirmRecycle"]) {
  test(`${functionName} flushes dirty editor and aborts before filesystem mutation on failure`, () => {
    const body = fnBody(NOTES, functionName);
    const flushIdx = body.search(/await\s+flushCurrentEditor\s*\(/);
    const abortIdx = body.search(/flushed\s*===\s*false[\s\S]*?return/);
    const bridgeIdx = body.search(/await\s+callBridge[\s\S]*?"second_brain_(?:rename|recycle)"/);
    assert.ok(flushIdx >= 0, `${functionName} must flush first`);
    assert.ok(abortIdx > flushIdx && bridgeIdx > abortIdx, `${functionName} must abort before bridge mutation`);
  });
}

test("Public Notes refresh flushes then forces backend reindex", () => {
  const body = fnBody(NOTES, "refresh");
  const flushIdx = body.search(/await\s+flushCurrentEditor\s*\(/);
  const refreshIdx = body.search(/await\s+loadWorkspace\s*\(true\)/);
  assert.ok(flushIdx >= 0 && refreshIdx > flushIdx);
  assert.match(body, /flushed\s*===\s*false/);
  assert.match(fnBody(NOTES, "loadWorkspace"), /force\s*\?\s*"second_brain_refresh"/);
});

test("Selection uses the second-brain-rte interaction lock", () => {
  assert.match(NOTES, /"second-brain-rte"/);
  assert.match(NOTES, /app:interaction-lock/);
});

test("Selection routes docx→rteDocumentOpen, markdown/text→getRteFile, image→second_brain_image", () => {
  const body = fnBody(NOTES, "selectItem");
  assert.match(body, /rteDocumentOpen\s*\(/);
  assert.match(body, /getRteFile\s*\(/);
  assert.match(body, /"second_brain_image"/);
});

test("Stale loads are ignored via a monotonic request token", () => {
  assert.match(NOTES, /\+\+loadSeq/);
  assert.match(NOTES, /token !== loadSeq/);
});

test("Search is debounced at 150 ms with a stale-result guard", () => {
  assert.match(NOTES, /setTimeout\([^,]+,\s*150\)/);
  assert.match(NOTES, /\+\+searchSeq/);
  assert.match(NOTES, /seq !== searchSeq/);
});

test("Filters run without search text and date uses the backend YYYY-MM-DD contract", () => {
  const searchBody = fnBody(NOTES, "runSearch");
  const filterBody = fnBody(NOTES, "onFiltersChanged");
  assert.match(NOTES, /type="date"\s+bind:value=\{dateFilter\}/);
  assert.match(NOTES, /function hasActiveFilters\s*\(/);
  assert.match(searchBody, /!query\s*&&\s*!hasActiveFilters\s*\(\)/);
  assert.match(filterBody, /void\s+runSearch\s*\(\)/);
});

test("Clearing search invalidates any in-flight stale request", () => {
  const body = fnBody(NOTES, "runSearch");
  const seqIdx = body.search(/const\s+seq\s*=\s*\+\+searchSeq/);
  const emptyIdx = body.search(/if\s*\(\s*!query\s*&&/);
  assert.ok(seqIdx >= 0 && seqIdx < emptyIdx, "request token must advance before empty-search early return");
});

test("Tree identity is source-scoped so Personal and Project paths cannot collide", () => {
  const body = fnBody(NOTES, "buildTree");
  assert.match(NOTES, /function treeKey\s*\(source:\s*SecondBrainSource/);
  assert.match(body, /treeKey\(it\.source,\s*it\.tree_path\)/);
  assert.match(body, /treeKey\(node\.item\.source,\s*node\.item\.parent_path\)/);
});

test("Source ribbon exposes breadcrumb, file type, and capability state", () => {
  assert.match(NOTES, /sb-ribbon-breadcrumb/);
  assert.match(NOTES, /selectedItem\.tree_path/);
  assert.match(NOTES, /selectedItem\.file_format/);
  assert.match(NOTES, /Editable|Read-only|Preview|External/);
});

test("External-open activity records only after file_open succeeds", () => {
  const body = fnBody(NOTES, "openExternal");
  const openIdx = body.search(/await\s+callBridge\s*\(\s*"file_open"/);
  const okIdx = body.search(/if\s*\(\s*!resp\.ok\s*\)/);
  const activityIdx = body.search(/"opened_externally"/);
  assert.ok(openIdx >= 0 && okIdx > openIdx && activityIdx > okIdx);
});

test("onSaved records via second_brain_mark_saved (no excerpt duplication)", () => {
  assert.match(NOTES, /"second_brain_mark_saved"/);
});

test("Explorer sections use the approved labels", () => {
  for (const label of ["Search Results", "Pinned", "Favorites", "Personal Notes", "Project Documents"]) {
    assert.ok(NOTES.includes(label), `explorer missing section label "${label}"`);
  }
});

test("Recovery affordances expose Browse folder and Use default folder", () => {
  assert.match(NOTES, /Browse folder/);
  assert.match(NOTES, /Use default folder/);
  assert.match(NOTES, /"second_brain_use_default_folder"/);
});

test("Context shelf exposes Related and Activity backed by their bridges", () => {
  assert.match(NOTES, /Related/);
  assert.match(NOTES, /Activity/);
  assert.match(NOTES, /"second_brain_related"/);
  assert.match(NOTES, /"second_brain_activity_list"/);
});

test("Keyboard affordances: Ctrl+F search, F2 rename, Enter commit, Escape cancel, Delete recycle", () => {
  assert.match(NOTES, /ctrlKey|metaKey/);
  assert.match(NOTES, /"F2"/);
  assert.match(NOTES, /"Enter"/);
  assert.match(NOTES, /"Escape"/);
  assert.match(NOTES, /"Delete"/);
});

test("Inline rename/recycle bridges and pin/favorite/tags sidecar updates exist", () => {
  assert.match(NOTES, /"second_brain_rename"/);
  assert.match(NOTES, /"second_brain_recycle"/);
  assert.match(NOTES, /"second_brain_pin"/);
  assert.match(NOTES, /"second_brain_favorite"/);
  assert.match(NOTES, /"second_brain_tags"/);
});

test("Delete key recycle is gated to Personal items only", () => {
  // Delete handling must check source === "personal" before arming recycle.
  assert.match(NOTES, /"Delete"[\s\S]{0,160}source === "personal"/);
});

test("Scoped CSS uses the approved explorer width clamp, design tokens, reduced motion, responsive shelf", () => {
  const style = styleBlock(NOTES);
  assert.match(style, /clamp\(260px,\s*24vw,\s*340px\)/);
  assert.match(style, /var\(--color-/);
  assert.match(style, /prefers-reduced-motion/);
  assert.match(style, /@media/);
});

test("Scoped CSS uses tokens only — no raw hex literals", () => {
  const style = styleBlock(NOTES);
  assert.doesNotMatch(style, /#[0-9a-fA-F]{3,8}\b/);
});

// --- Task 8 review fix round 1: double-create / activity / tags / disabled / labels ---

test("commitCreate clears creating + createName BEFORE the create bridge call (double-create guard)", () => {
  const body = fnBody(NOTES, "commitCreate");
  const creatingIdx = body.search(/creating\s*=\s*false/);
  const nameIdx = body.search(/createName\s*=\s*""/);
  const bridgeIdx = body.search(/await callBridge\(\s*"second_brain_create"/);
  assert.ok(creatingIdx >= 0, "commitCreate must clear the creating guard");
  assert.ok(nameIdx >= 0, "commitCreate must clear createName");
  assert.ok(bridgeIdx >= 0, "commitCreate must call second_brain_create");
  assert.ok(creatingIdx < bridgeIdx, "creating guard must clear before the bridge await (blur re-entry no-ops)");
  assert.ok(nameIdx < bridgeIdx, "createName must clear before the bridge await (blur re-entry no-ops)");
});

// --- Final review fix: explorer hierarchy + complete Personal create flows ---

test("buildTree keys nodes by logical tree_path and synthesizes missing project ancestors", () => {
  const body = fnBody(NOTES, "buildTree");
  assert.match(body, /treeKey\(it\.source,\s*it\.tree_path\)/, "real nodes must be keyed by source + logical tree_path");
  assert.match(body, /while\s*\(parentPath\)/, "missing ancestor chain must be synthesized");
  assert.match(body, /id:\s*`tree:/, "synthetic project folders need stable UI-only IDs");
  assert.match(body, /node\.item\.parent_path/, "tree attachment must use logical parent_path");
});

test("Personal Notes exposes separate File and Folder create actions", () => {
  assert.match(NOTES, /beginCreate\(\s*"file"\s*\)/);
  assert.match(NOTES, /beginCreate\(\s*"folder"\s*\)/);
  assert.match(NOTES, />\+ File<|>Add File</);
  assert.match(NOTES, />\+ Folder<|>Add Folder</);
});

test("commitCreate defaults extensionless files to .md and routes folders separately", () => {
  const body = fnBody(NOTES, "commitCreate");
  assert.match(body, /(?:createKind|kind)\s*===\s*"file"/);
  assert.match(body, /`\$\{name\}\.md`/, "extensionless Personal files must default to .md");
  assert.match(body, /"second_brain_create"/);
  assert.match(body, /"second_brain_folder_create"/);
});

test("new Personal file refreshes the index then selects the returned created path", () => {
  const body = fnBody(NOTES, "commitCreate");
  const refreshIdx = body.search(/await loadWorkspace\(true\)/);
  const findIdx = body.indexOf("workspace?.items.find((it) => it.path === createdPath)");
  const selectIdx = body.search(/await selectItem\(createdItem\)/);
  assert.ok(refreshIdx >= 0, "create must refresh the filesystem index");
  assert.ok(findIdx > refreshIdx, "created item lookup must use the refreshed workspace");
  assert.ok(selectIdx > findIdx, "created file must be selected after lookup");
});

test("project items cannot enter rename or recycle flows", () => {
  const renameBody = fnBody(NOTES, "beginRename");
  const recycleBody = fnBody(NOTES, "confirmRecycle");
  const keyBody = fnBody(NOTES, "onKeydown");
  assert.match(renameBody, /item\.source\s*!==\s*"personal"[^\n]*return/);
  assert.match(recycleBody, /item\.source\s*!==\s*"personal"[^\n]*return/);
  assert.match(keyBody, /e\.key\s*===\s*"F2"\s*&&\s*selectedItem\.source\s*===\s*"personal"/);
  assert.match(NOTES, /disabled=\{selectedItem\.source\s*!==\s*"personal"\}[^>]*>Rename<|>Rename<[^\n]*disabled=\{selectedItem\.source\s*!==\s*"personal"\}/);
});

test("recordOpen records \"opened\" for inline-loaded/previewed selections, nothing for external", () => {
  const body = fnBody(NOTES, "recordOpen");
  assert.match(body, /item\.open_mode === "external"/, "recordOpen must special-case external items");
  assert.match(body, /"opened"/);
  assert.doesNotMatch(body, /"opened_externally"/, "recordOpen must not itself record opened_externally");
});

test("openExternal is the only call site that records \"opened_externally\"", () => {
  const body = fnBody(NOTES, "openExternal");
  assert.match(body, /"opened_externally"/);
  const externalCount = (NOTES.match(/"opened_externally"/g) || []).length;
  assert.equal(externalCount, 1, "opened_externally must be recorded from exactly one call site (openExternal)");
});

test("saveTagsFromInput guards against Enter+blur double-fire (one commit per edit)", () => {
  const body = fnBody(NOTES, "saveTagsFromInput");
  const guardCheckIdx = body.search(/savingTags\)\s*return/);
  const guardSetIdx = body.search(/savingTags\s*=\s*true/);
  const bridgeIdx = body.search(/await callBridge\(\s*"second_brain_tags"/);
  assert.ok(guardCheckIdx >= 0, "must bail early when a save is already in flight");
  assert.ok(guardSetIdx >= 0, "must set the guard before the bridge call");
  assert.ok(bridgeIdx >= 0, "must call second_brain_tags");
  assert.ok(guardSetIdx < bridgeIdx, "guard must be set before the await (blur re-entry no-ops)");
});

test("Personal create buttons are disabled while the personal folder is not ready", () => {
  const disabledButtons = NOTES.match(/<button[^>]*disabled=\{personalMissing\}[^>]*onclick=\{\(\) => beginCreate\("(?:file|folder)"\)\}[^>]*>/g) || [];
  assert.equal(disabledButtons.length, 2);
});

test("Related reason and Activity action labels use a global underscore-to-space replace", () => {
  assert.doesNotMatch(
    NOTES,
    /\.replace\("_",\s*" "\)/,
    "must use replaceAll (or a global regex), not single-shot replace, for underscore labels",
  );
  assert.match(NOTES, /row\.reason\.replaceAll\("_",\s*" "\)/);
  assert.match(NOTES, /row\.action\.replaceAll\("_",\s*" "\)/);
});

// --- Task 9: LinkBank.svelte source contracts --------------------------------

test("LinkBank exposes the public refresh(): Promise<void> API", () => {
  assert.match(LINKBANK, /export async function refresh\s*\(\s*\)\s*:\s*Promise<void>/);
});

test("LinkBank references every link-bank bridge facade by exact name", () => {
  for (const method of [
    "linkbank_get",
    "linkbank_update",
    "linkbank_add_link",
    "linkbank_archive_link",
    "linkbank_restore_link",
    "linkbank_category_create",
    "linkbank_category_rename",
    "linkbank_category_archive",
    "linkbank_category_restore",
    "linkbank_open",
    "linkbank_export_file",
    "linkbank_import_preview",
    "linkbank_import_merge",
  ]) {
    assert.match(LINKBANK, new RegExp(`"${method}"`), `LinkBank missing bridge call "${method}"`);
  }
  // Native save dialog for export.
  assert.match(LINKBANK, /"util_save_file"/);
});

test("LinkBank has no delete action and no target-blank/window.open navigation", () => {
  assert.doesNotMatch(LINKBANK, /\bDelete\b/, "no delete-labeled UI action anywhere");
  assert.doesNotMatch(LINKBANK, /target\s*=\s*["']_blank["']/);
  assert.doesNotMatch(LINKBANK, /window\.open\s*\(/);
});

test("Links open ONLY through linkbank_open (single call site)", () => {
  const body = fnBody(LINKBANK, "openLink");
  assert.match(body, /"linkbank_open"/);
  const callCount = (LINKBANK.match(/"linkbank_open"/g) || []).length;
  assert.equal(callCount, 1, "linkbank_open must be called from exactly one function");
});

test("Copy uses navigator.clipboard with a WebView (execCommand) fallback", () => {
  assert.match(LINKBANK, /navigator\.clipboard/);
  assert.match(LINKBANK, /execCommand\(\s*["']copy["']\s*\)/);
});

test("Pin/favorite route through the existing linkbank_update facade, not a dedicated pin/favorite bridge", () => {
  const pinBody = fnBody(LINKBANK, "togglePin");
  const favBody = fnBody(LINKBANK, "toggleFavorite");
  assert.match(pinBody, /"linkbank_update"/);
  assert.match(favBody, /"linkbank_update"/);
});

test("Add/Edit reuse the same detail-pane form (single save handler for both modes)", () => {
  const body = fnBody(LINKBANK, "handleSaveLink");
  assert.match(body, /"linkbank_add_link"/);
  assert.match(body, /"linkbank_update"/);
});

test("Client-side validation requires name+url before any add/edit bridge call (backend stays authoritative)", () => {
  const body = fnBody(LINKBANK, "handleSaveLink");
  const nameCheckIdx = body.search(/!name\s*\|\|\s*!url/);
  const bridgeIdx = Math.min(
    ...["linkbank_add_link", "linkbank_update"]
      .map((m) => body.indexOf(`"${m}"`))
      .filter((i) => i >= 0),
  );
  assert.ok(nameCheckIdx >= 0, "handleSaveLink must guard on missing name/url");
  assert.ok(nameCheckIdx < bridgeIdx, "name/url guard must run before the bridge call");
});

test("Archive/restore (link and category) are confirmation-gated: request* only stages, confirm* performs the bridge call", () => {
  for (const requestFn of ["requestArchiveLink", "requestRestoreLink", "requestArchiveCategory", "requestRestoreCategory"]) {
    const body = fnBody(LINKBANK, requestFn);
    assert.doesNotMatch(
      body,
      /await callBridge/,
      `${requestFn} must only stage a pending confirmation, not call the bridge directly`,
    );
  }
  const confirmBody = fnBody(LINKBANK, "confirmPendingAction");
  for (const method of ["linkbank_archive_link", "linkbank_restore_link", "linkbank_category_archive", "linkbank_category_restore"]) {
    assert.match(confirmBody, new RegExp(`"${method}"`), `confirmPendingAction missing "${method}"`);
  }
});

test("LinkBank mounts ConfirmModal for the gated archive/restore actions", () => {
  assert.match(LINKBANK, /import ConfirmModal from "\.\/ConfirmModal\.svelte"/);
  assert.match(LINKBANK, /<ConfirmModal\b/);
});

test("Import calls preview BEFORE any merge, and preview/merge come from separate functions", () => {
  const previewBody = fnBody(LINKBANK, "handleImportFile");
  assert.match(previewBody, /"linkbank_import_preview"/);
  assert.doesNotMatch(previewBody, /"linkbank_import_merge"/, "the preview handler must never itself call merge");

  const mergeBody = fnBody(LINKBANK, "confirmImportMerge");
  assert.match(mergeBody, /"linkbank_import_merge"/);

  const previewIdx = LINKBANK.indexOf('"linkbank_import_preview"');
  const mergeIdx = LINKBANK.indexOf('"linkbank_import_merge"');
  assert.ok(previewIdx >= 0 && mergeIdx >= 0, "both preview and merge calls must exist");
  assert.ok(previewIdx < mergeIdx, "preview call site must appear before merge call site in source");
});

test("Cancelling an import clears the pending payload without ever calling merge", () => {
  const body = fnBody(LINKBANK, "cancelImport");
  assert.doesNotMatch(body, /await callBridge/, "cancelImport must not call the bridge (writes nothing)");
  assert.match(body, /importPreview\s*=\s*null/);
  assert.match(body, /pendingImportPayload\s*=\s*null/);
});

test("Hidden file input accepts JSON and CSV", () => {
  assert.match(LINKBANK, /type="file"[^>]*accept="[^"]*\.json[^"]*\.csv[^"]*"/);
});

test("Export goes through linkbank_export_file for both json and csv, then the native util_save_file dialog", () => {
  const body = fnBody(LINKBANK, "exportBank");
  assert.match(body, /"linkbank_export_file"/);
  assert.match(body, /"util_save_file"/);
  assert.match(LINKBANK, /exportBank\(\s*["']json["']\s*\)/);
  assert.match(LINKBANK, /exportBank\(\s*["']csv["']\s*\)/);
});

test("Category rail exposes All, Pinned, Favorites, Archived plus active/archived category rows", () => {
  for (const label of ["All", "Pinned", "Favorites", "Archived"]) {
    assert.ok(LINKBANK.includes(`>${label}<`) || LINKBANK.includes(`>${label} `), `rail missing "${label}" row`);
  }
  assert.match(LINKBANK, /activeCategories|bank\.categories/);
  assert.match(LINKBANK, /archivedCategories|bank\.archived_categories/);
});

test("Responsive: at <=1200px the list/detail panel stacks, but the category rail is untouched by that breakpoint", () => {
  const style = styleBlock(LINKBANK);
  const mediaMatch = style.match(/@media\s*\(max-width:\s*1200px\)\s*\{([\s\S]*?)\n\s*\}\s*\n/);
  assert.ok(mediaMatch, "expected an @media (max-width: 1200px) block");
  const block = mediaMatch[1];
  assert.match(block, /grid-template-columns:\s*1fr/, "list/detail panel must collapse to a single column");
  assert.doesNotMatch(block, /\.lb-rail\b/, "the category rail must remain unaffected by the stack breakpoint");
});

test("Scoped CSS uses design tokens only (no raw hex) and supports reduced motion", () => {
  const style = styleBlock(LINKBANK);
  assert.doesNotMatch(style, /#[0-9a-fA-F]{3,8}\b/);
  assert.match(style, /var\(--color-/);
  assert.match(style, /prefers-reduced-motion/);
});

test("Buttons define default/hover/focus/active/disabled states", () => {
  const style = styleBlock(LINKBANK);
  assert.match(style, /\.lb-btn[^{]*\{/);
  assert.match(style, /\.lb-btn:hover/);
  assert.match(style, /\.lb-btn:focus-visible/);
  assert.match(style, /\.lb-btn:active/);
  assert.match(style, /\.lb-btn:disabled/);
});

// --- Task 9 review fix round 1: rename escape-blur race ----------------------

test("cancelRenameCategory clears renameCategoryValue (escape-blur race guard)", () => {
  const body = fnBody(LINKBANK, "cancelRenameCategory");
  assert.match(body, /renamingCategory\s*=\s*false/);
  assert.match(body, /renameCategoryValue\s*=\s*""/);
});

test("commitRenameCategory guards re-entry on renamingCategory BEFORE the bridge call (escape-blur race)", () => {
  const body = fnBody(LINKBANK, "commitRenameCategory");
  const guardIdx = body.search(/if\s*\(\s*!renamingCategory\s*\)\s*return/);
  const bridgeIdx = body.search(/await callBridge<LinkBankData>\(\s*"linkbank_category_rename"/);
  assert.ok(guardIdx >= 0, "commitRenameCategory must guard re-entry when renamingCategory is already false");
  assert.ok(bridgeIdx >= 0, "commitRenameCategory must call linkbank_category_rename");
  assert.ok(guardIdx < bridgeIdx, "the renamingCategory guard must run before the bridge call");
});

// --- Task 10: SecondBrain.svelte thin shell source contracts -----------------

test("Shell imports only the two workspace components (thin child imports)", () => {
  assert.match(SHELL, /import SecondBrainNotes from ["']\.\/SecondBrainNotes\.svelte["']/);
  assert.match(SHELL, /import LinkBank from ["']\.\/LinkBank\.svelte["']/);
});

test("Shell has no business bridge calls or forked editor implementation", () => {
  assert.doesNotMatch(SHELL, /callBridge/);
  assert.doesNotMatch(SHELL, /<textarea/);
  assert.doesNotMatch(SHELL, /insertMarkdown/);
});

test("Shell has no persistence of tab state (component-session-only)", () => {
  assert.doesNotMatch(SHELL, /localStorage|sessionStorage/);
});

test("Default active tab is Notes", () => {
  assert.match(SHELL, /activeTab[^=]*=\s*\$state\(\s*"notes"\s*\)/);
});

test("Notes workspace mounts exactly once outside any conditional (editor state never destroyed by tab switch)", () => {
  const matches = SHELL.match(/<SecondBrainNotes\b/g) || [];
  assert.equal(matches.length, 1, "SecondBrainNotes must be mounted exactly once");
  assert.doesNotMatch(
    SHELL,
    /\{#if[^}]*\}[\s\S]{0,120}<SecondBrainNotes/,
    "SecondBrainNotes must not be wrapped in a conditional block that would unmount it",
  );
});

test("Link Bank lazy-mounts on first selection and then stays mounted (hidden, not destroyed)", () => {
  assert.match(SHELL, /\{#if linkBankMounted\}[\s\S]*?<LinkBank\b/);
  assert.match(SHELL, /linkBankMounted\s*=\s*true/);
});

test("Switching from Notes to Link Bank flushes the Notes child first and aborts the switch on failure", () => {
  const body = fnBody(SHELL, "selectTab");
  const flushIdx = body.search(/notesRef\?\.flush\(\)/);
  const assignIdx = body.search(/activeTab\s*=\s*tab/);
  assert.ok(flushIdx >= 0, "selectTab must flush the Notes child before switching");
  assert.ok(assignIdx >= 0, "selectTab must assign the new active tab");
  assert.ok(flushIdx < assignIdx, "flush must run before the tab switch is committed");
  assert.match(body, /flushed === false/, "must abort the switch (return) when flush reports failure");
});

test("Refresh routes only to the active child", () => {
  const body = fnBody(SHELL, "refreshActive");
  assert.match(body, /activeTab === "notes"/);
  assert.match(body, /notesRef\?\.refresh\(\)/);
  assert.match(body, /linkBankRef\?\.refresh\(\)/);
});

test("Tab bar exposes accessible tablist/tab/tabpanel relationships", () => {
  assert.match(SHELL, /role="tablist"/);
  const tabMatches = SHELL.match(/role="tab"/g) || [];
  assert.equal(tabMatches.length, 2, "exactly two role=\"tab\" buttons (Notes, Link Bank)");
  assert.match(SHELL, /role="tabpanel"/);
  assert.match(SHELL, /aria-selected=\{/);
  assert.match(SHELL, /aria-controls=/);
  assert.match(SHELL, /aria-labelledby=/);
});

test("selectTab guards against concurrent switches via switching boolean", () => {
  const body = fnBody(SHELL, "selectTab");
  // Guard check must run before the flush await.
  const guardCheckIdx = body.search(/if\s*\(\s*switching\s*\|\|\s*tab\s*===\s*activeTab\s*\)\s*return/);
  const flushIdx = body.search(/await notesRef\?\.flush\(\)/);
  assert.ok(guardCheckIdx >= 0, "selectTab must guard on switching || tab === activeTab");
  assert.ok(flushIdx >= 0, "selectTab must call flush");
  assert.ok(guardCheckIdx < flushIdx, "guard check must run before the flush await");
  // switching must be set to true before the flush await.
  const guardSetIdx = body.search(/switching\s*=\s*true/);
  assert.ok(guardSetIdx >= 0, "selectTab must set switching = true");
  assert.ok(guardSetIdx < flushIdx, "switching must be set to true before the flush await");
  // switching must be reset in a finally block.
  assert.match(body, /finally\s*\{[\s\S]*?switching\s*=\s*false/);
});

test("No hard-coded hex colors in any of the three Second Brain components", () => {
  for (const [name, source] of [
    ["SecondBrain.svelte", SHELL],
    ["SecondBrainNotes.svelte", NOTES],
    ["LinkBank.svelte", LINKBANK],
  ]) {
    assert.doesNotMatch(source, /#[0-9a-fA-F]{3,8}\b/, `${name} must not contain raw hex colors`);
  }
});
