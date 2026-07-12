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
