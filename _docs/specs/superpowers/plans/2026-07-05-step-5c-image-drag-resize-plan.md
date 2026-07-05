# Step 5c Image Drag-Resize Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add persisted drag-resize handles for rich-editor images in `.docx` pipeline documents and `notes.md`, while leaving `.txt` unchanged.

**Architecture:** Keep the resize behavior in `AssetImage.ts` as a minimal Tiptap NodeView, because the handle must attach to a ProseMirror image node and persist width through node attributes. Keep Markdown width persistence in `markdown.ts`; keep `NotesEditor.svelte` to CSS only. Do not touch backend export code because Step 5a already clamps images to printable width.

**Tech Stack:** Svelte 5, TypeScript, Tiptap v3, ProseMirror NodeView, Node test runner, existing Markdown renderer.

## Global Constraints

- Work only on branch `project-details/tiptap-docx-pipeline` from repo root `D:/Ibrahim/Projects/project_tracker`.
- One RTE behavior round only: image drag-resize.
- Modify only `frontend/src/lib/extensions/AssetImage.ts`, `frontend/src/lib/markdown.ts`, `frontend/src/lib/components/NotesEditor.svelte`, `frontend/tests/markdown.test.ts`, and `frontend/tests/project-details-fase3-fase4.test.mjs`.
- No backend changes. Step 5a already clamps exported image width to printable page width.
- No table changes. Existing Tiptap table column resize remains as-is.
- Never run frontend build while Project Tracker may be open.
- Do not commit implementation until automated verification passes and the user manually verifies the rebuilt app.

---

## File Structure

- `frontend/src/lib/extensions/AssetImage.ts`: owns image node attributes and the image resize NodeView.
- `frontend/src/lib/markdown.ts`: owns Markdown and sanitized inline HTML round-trip for resized images.
- `frontend/src/lib/components/NotesEditor.svelte`: owns only visual CSS for image wrapper and handle.
- `frontend/tests/markdown.test.ts`: proves Markdown width round-trip behavior.
- `frontend/tests/project-details-fase3-fase4.test.mjs`: source-contract tests for AssetImage NodeView and NotesEditor CSS.

### Task 1: Add failing Step 5c tests

**Files:**
- Modify: `frontend/tests/markdown.test.ts`
- Modify: `frontend/tests/project-details-fase3-fase4.test.mjs`

**Interfaces:**
- Consumes: current image Markdown behavior and current AssetImage source.
- Produces: failing tests for width persistence, AssetImage NodeView, and NotesEditor handle CSS.

- [ ] **Step 1: Add AssetImage source fixture to `frontend/tests/project-details-fase3-fase4.test.mjs`**

Add this constant after the existing component source constants:

```javascript
const AI = readFileSync(resolve(__dirname, "../src/lib/extensions/AssetImage.ts"), "utf8");
```

- [ ] **Step 2: Add failing source-contract tests to `frontend/tests/project-details-fase3-fase4.test.mjs`**

Add these tests after the existing `NotesEditor supports Word-like cross-format zoom` test:

```javascript
test("AssetImage supports persisted drag-resize width", () => {
  assert.match(AI, /import type \{ Node as PMNode \} from "@tiptap\/pm\/model"/);
  assert.match(AI, /width:\s*\{[\s\S]*getAttribute\("width"\)[\s\S]*renderHTML:[\s\S]*width/);
  assert.match(AI, /addNodeView\(\)/);
  assert.match(AI, /className = "ne-img-wrap"/);
  assert.match(AI, /className = "ne-img-handle"/);
  assert.match(AI, /Math\.max\(40/);
  assert.match(AI, /setNodeMarkup\(pos, undefined, \{ \.\.\.current\.attrs, width: nextWidth \}\)/);
});

test("NotesEditor styles the image resize handle", () => {
  assert.match(NE, /:global\(\.ne-editor-host \.ne-img-wrap\)\s*\{[^}]*position:relative;[^}]*display:inline-block;[^}]*max-width:100%;[^}]*line-height:0;/);
  assert.match(NE, /:global\(\.ne-editor-host \.ne-img-wrap img\)\s*\{[^}]*display:block;[^}]*max-width:100%;/);
  assert.match(NE, /:global\(\.ne-editor-host \.ne-img-handle\)\s*\{[^}]*position:absolute;[^}]*right:-5px;[^}]*bottom:-5px;[^}]*width:11px;[^}]*height:11px;[^}]*border:2px solid var\(--color-dbs-red\);[^}]*cursor:nwse-resize;[^}]*opacity:0;/);
  assert.match(NE, /:global\(\.ne-editor-host \.ne-img-wrap:hover \.ne-img-handle\),\s*:global\(\.ne-editor-host \.ProseMirror-selectednode \.ne-img-handle\)\s*\{[^}]*opacity:1;/);
});
```

- [ ] **Step 3: Add failing Markdown tests to `frontend/tests/markdown.test.ts`**

Add these tests after `asset image refs render with data-asset-src and round-trip to markdown`:

```typescript
test("resized asset image refs serialize as inline HTML with width", () => {
  const back = htmlToMarkdown(
    '<img src="data:image/png;base64,AAAA" alt="shot" data-asset-src=".rte/assets/ab12cd34ef56ab78.png" width="240">',
  );
  assert.equal(back, '<img src=".rte/assets/ab12cd34ef56ab78.png" alt="shot" width="240" />');
});

test("resized asset image HTML renders with a sanitized width", () => {
  const html = renderMarkdown('<img src=".rte/assets/ab12cd34ef56ab78.png" alt="shot" width="240" />');
  assert.match(html, /<img src="\.rte\/assets\/ab12cd34ef56ab78\.png" alt="shot" width="240">/);
});

test("asset image refs without width keep markdown image serialization", () => {
  const back = htmlToMarkdown(
    '<img src="data:image/png;base64,AAAA" alt="shot" data-asset-src=".rte/assets/ab12cd34ef56ab78.png">',
  );
  assert.equal(back, "![shot](.rte/assets/ab12cd34ef56ab78.png)");
});
```

- [ ] **Step 4: Run focused red tests**

Run:

```powershell
node --import ./frontend/tests/register-hooks.mjs --test --test-name-pattern "resized asset|AssetImage supports|image resize handle" ./frontend/tests/markdown.test.ts ./frontend/tests/project-details-fase3-fase4.test.mjs
```

Expected: fail because `AssetImage.ts` has no `width` attribute or NodeView, `NotesEditor.svelte` has no `.ne-img-handle` CSS, and `markdown.ts` serializes resized images as normal Markdown.

### Task 2: Implement minimal image drag-resize

**Files:**
- Modify: `frontend/src/lib/extensions/AssetImage.ts`
- Modify: `frontend/src/lib/markdown.ts`
- Modify: `frontend/src/lib/components/NotesEditor.svelte`

**Interfaces:**
- Consumes: existing AssetImage `assetId` and `assetSrc` attributes, existing `htmlToMarkdown()` and `renderMarkdown()` image behavior, existing `.ne-editor-host` CSS scope.
- Produces: AssetImage `width` attr, image resize NodeView, sanitized inline HTML width persistence, and scoped handle styling.

- [ ] **Step 1: Replace `frontend/src/lib/extensions/AssetImage.ts` with this implementation**

```typescript
// Image node with stable asset identity for the DOCX pipeline (D-0012).
//
// Extends the stock Tiptap Image extension with three attributes:
//   assetId  — content hash id of the stored asset file (16 hex chars)
//   assetSrc — path relative to the document folder (.rte/assets/<id>.<ext>);
//              markdown serialization prefers this over the (data URI) src.
//   width    — optional persisted display width in CSS pixels.
// `src` stays a data URI for display, exactly like the legacy embed path, so
// existing base64 images keep working unchanged.

import Image from "@tiptap/extension-image";
import type { Node as PMNode } from "@tiptap/pm/model";

function positiveInt(value: unknown): number | null {
  const n = Number(value);
  return Number.isInteger(n) && n > 0 ? n : null;
}

export const AssetImage = Image.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      assetId: {
        default: null,
        parseHTML: (el: HTMLElement) => el.getAttribute("data-asset-id"),
        renderHTML: (attrs: Record<string, unknown>) =>
          attrs.assetId ? { "data-asset-id": String(attrs.assetId) } : {},
      },
      assetSrc: {
        default: null,
        parseHTML: (el: HTMLElement) => el.getAttribute("data-asset-src"),
        renderHTML: (attrs: Record<string, unknown>) =>
          attrs.assetSrc ? { "data-asset-src": String(attrs.assetSrc) } : {},
      },
      width: {
        default: null,
        parseHTML: (el: HTMLElement) => positiveInt(el.getAttribute("width")),
        renderHTML: (attrs: Record<string, unknown>) => {
          const width = positiveInt(attrs.width);
          return width ? { width: String(width) } : {};
        },
      },
    };
  },

  addNodeView() {
    return ({ node, editor, getPos }) => {
      let current = node as PMNode;
      const dom = document.createElement("span");
      dom.className = "ne-img-wrap";
      const img = document.createElement("img");
      dom.appendChild(img);

      function apply(next: PMNode) {
        const attrs = next.attrs as Record<string, unknown>;
        img.src = String(attrs.src || "");
        img.alt = String(attrs.alt || "");
        if (attrs.assetId) img.dataset.assetId = String(attrs.assetId);
        else delete img.dataset.assetId;
        if (attrs.assetSrc) img.dataset.assetSrc = String(attrs.assetSrc);
        else delete img.dataset.assetSrc;
        const width = positiveInt(attrs.width);
        if (width) img.style.width = `${width}px`;
        else img.style.removeProperty("width");
      }

      if (editor.isEditable) {
        const handle = document.createElement("span");
        handle.className = "ne-img-handle";
        handle.addEventListener("mousedown", (event) => {
          event.preventDefault();
          event.stopPropagation();
          const startX = event.clientX;
          const startWidth = img.getBoundingClientRect().width || positiveInt(current.attrs.width) || 40;
          let nextWidth = Math.max(40, Math.round(startWidth));

          const onMove = (move: MouseEvent) => {
            nextWidth = Math.max(40, Math.round(startWidth + move.clientX - startX));
            img.style.width = `${nextWidth}px`;
          };
          const onUp = () => {
            document.removeEventListener("mousemove", onMove);
            document.removeEventListener("mouseup", onUp);
            const pos = getPos();
            if (typeof pos !== "number") return;
            editor.view.dispatch(editor.view.state.tr.setNodeMarkup(pos, undefined, { ...current.attrs, width: nextWidth }));
          };

          document.addEventListener("mousemove", onMove);
          document.addEventListener("mouseup", onUp);
        });
        dom.appendChild(handle);
      }

      apply(current);

      return {
        dom,
        update(nextNode: PMNode) {
          if (nextNode.type !== current.type) return false;
          current = nextNode;
          apply(current);
          return true;
        },
      };
    };
  },
});
```

- [ ] **Step 2: Add width support helpers to `frontend/src/lib/markdown.ts`**

Add these helpers after `stripHtmlTags()`:

```typescript
function positiveWidthAttr(value: string | null): string {
  const raw = (value || "").trim();
  return /^[1-9]\d*$/.test(raw) ? raw : "";
}

function imageMarkdown(src: string, alt: string, width: string): string {
  if (width) return `<img src="${escapeHtml(src)}" alt="${escapeHtml(alt)}" width="${width}" />`;
  return `![${alt}](${src})`;
}
```

- [ ] **Step 3: Allow sanitized `width` on image HTML in `frontend/src/lib/markdown.ts`**

Change:

```typescript
  img: new Set(["src", "alt", "style", "data-asset-src", "data-asset-id"]),
```

to:

```typescript
  img: new Set(["src", "alt", "style", "width", "data-asset-src", "data-asset-id"]),
```

Change `sanitizeAttr()` from:

```typescript
function sanitizeAttr(name: string, val: string): string {
  if (name === "href") return sanitizeHref(val);
  if (name === "src") return sanitizeImgSrc(val);
  if (name === "style") return sanitizeStyle(val);
  // Plain attributes: keep, but neutralize quote/angle-break characters.
  return val.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
```

to:

```typescript
function sanitizeAttr(name: string, val: string): string {
  if (name === "href") return sanitizeHref(val);
  if (name === "src") return sanitizeImgSrc(val);
  if (name === "style") return sanitizeStyle(val);
  if (name === "width") return positiveWidthAttr(val);
  // Plain attributes: keep, but neutralize quote/angle-break characters.
  return val.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
```

- [ ] **Step 4: Serialize DOM images with valid width to inline HTML in `frontend/src/lib/markdown.ts`**

Change the `case "img"` branch in `domNodeToMarkdown()` from:

```typescript
    case "img": return `![${el.getAttribute("alt") || ""}](${el.getAttribute("data-asset-src") || el.getAttribute("src") || ""})`;
```

to:

```typescript
    case "img": {
      const src = el.getAttribute("data-asset-src") || el.getAttribute("src") || "";
      const alt = el.getAttribute("alt") || "";
      const width = positiveWidthAttr(el.getAttribute("width"));
      return imageMarkdown(src, alt, width);
    }
```

- [ ] **Step 5: Preserve width image HTML in `fallbackHtmlToMarkdown()`**

Change the start of `fallbackHtmlToMarkdown()` from:

```typescript
function fallbackHtmlToMarkdown(html: string): string {
  return html
```

to:

```typescript
function fallbackHtmlToMarkdown(html: string): string {
  const keepImgs: string[] = [];
  return html
```

Change the `<img>` replacement in `fallbackHtmlToMarkdown()` from:

```typescript
    .replace(/<img\b([^>]*)>/gi, (_m, attrs) => {
      const assetSrc = attrs.match(/data-asset-src=["']([^"']*)["']/i)?.[1] || "";
      const src = assetSrc || attrs.match(/src=["']([^"']*)["']/i)?.[1] || "";
      const alt = attrs.match(/alt=["']([^"']*)["']/i)?.[1] || "";
      return `![${alt}](${src})`;
    })
```

to:

```typescript
    .replace(/<img\b([^>]*)>/gi, (_m, attrs) => {
      const assetSrc = attrs.match(/data-asset-src=["']([^"']*)["']/i)?.[1] || "";
      const src = assetSrc || attrs.match(/src=["']([^"']*)["']/i)?.[1] || "";
      const alt = attrs.match(/alt=["']([^"']*)["']/i)?.[1] || "";
      const width = positiveWidthAttr(attrs.match(/width=["']([^"']*)["']/i)?.[1] || "");
      const out = imageMarkdown(src, alt, width);
      if (!width) return out;
      keepImgs.push(out);
      return `\u0000K${keepImgs.length - 1}\u0000`;
    })
```

Change the end of the fallback chain from:

```typescript
    .replace(/<[^>]+>/g, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}
```

to:

```typescript
    .replace(/<[^>]+>/g, "")
    .replace(/\u0000K(\d+)\u0000/g, (_m, i) => keepImgs[Number(i)] ?? "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}
```

Use the escaped `\u0000` text shown above in source code. Do not paste a literal control character.

- [ ] **Step 6: Add scoped image resize CSS to `frontend/src/lib/components/NotesEditor.svelte`**

Insert these rules after the existing `:global(.ne-editor-host .ne-textarea img) { max-width:100%; }` rule:

```css
  :global(.ne-editor-host .ne-img-wrap) { position:relative; display:inline-block; max-width:100%; line-height:0; }
  :global(.ne-editor-host .ne-img-wrap img) { display:block; max-width:100%; }
  :global(.ne-editor-host .ne-img-handle) { position:absolute; right:-5px; bottom:-5px; width:11px; height:11px; background:var(--card-white); border:2px solid var(--color-dbs-red); border-radius:3px; cursor:nwse-resize; opacity:0; }
  :global(.ne-editor-host .ne-img-wrap:hover .ne-img-handle), :global(.ne-editor-host .ProseMirror-selectednode .ne-img-handle) { opacity:1; }
```

- [ ] **Step 7: Run focused green tests**

Run:

```powershell
node --import ./frontend/tests/register-hooks.mjs --test --test-name-pattern "resized asset|AssetImage supports|image resize handle" ./frontend/tests/markdown.test.ts ./frontend/tests/project-details-fase3-fase4.test.mjs
```

Expected: selected Step 5c tests pass.

### Task 3: Verify, build, manual gate, and commit

**Files:**
- Verify: `frontend/src/lib/extensions/AssetImage.ts`
- Verify: `frontend/src/lib/markdown.ts`
- Verify: `frontend/src/lib/components/NotesEditor.svelte`
- Verify: `frontend/tests/markdown.test.ts`
- Verify: `frontend/tests/project-details-fase3-fase4.test.mjs`

**Interfaces:**
- Consumes: Task 2 implementation.
- Produces: user-verified Step 5c implementation commit.

- [ ] **Step 1: Run frontend verification**

Run:

```powershell
npm --prefix frontend run check
node --import ./frontend/tests/register-hooks.mjs --test ./frontend/tests/*.test.mjs
git diff --check -- frontend/src/lib/extensions/AssetImage.ts frontend/src/lib/markdown.ts frontend/src/lib/components/NotesEditor.svelte frontend/tests/markdown.test.ts frontend/tests/project-details-fase3-fase4.test.mjs
```

Expected:

- `svelte-check found 0 errors and 0 warnings`.
- Frontend tests pass.
- `git diff --check` exits 0.

- [ ] **Step 2: Ask user to close Project Tracker before build**

Ask exactly:

```text
Tutup app Project Tracker dulu. Balas `closed`, nanti aku build Step 5c dan kasih checklist manual.
```

- [ ] **Step 3: Build only after user replies `closed`**

Run:

```powershell
npm --prefix frontend run build
```

Expected: Vite build exits 0. Existing chunk-size and Rollup annotation warnings are nonblocking if no new error appears.

- [ ] **Step 4: Give this manual checklist in Indonesian**

```text
Checklist Step 5c image drag-resize:

1. DOCX image resize
- Buka file `.docx`.
- Paste/drop image.
- Hover image.
- Ekspektasi berhasil: handle merah kecil muncul di kanan-bawah image.
- Drag handle lebih kecil dan lebih besar.
- Ekspektasi berhasil: ukuran image berubah live, minimal tidak bisa lebih kecil dari kira-kira 40px.
- Ekspektasi gagal: handle tidak muncul, drag tidak mengubah ukuran, cursor/editor jadi kacau.

2. DOCX persistence
- Setelah resize, tunggu autosave/export selesai.
- Switch ke file lain, balik ke `.docx`.
- Tutup dan buka ulang app kalau sempat.
- Ekspektasi berhasil: ukuran image tetap sama.
- Ekspektasi gagal: image balik ke ukuran awal atau hilang.

3. DOCX export
- Buka hasil `.docx` di Word.
- Ekspektasi berhasil: image mengikuti ukuran yang di-resize, tapi tetap tidak keluar dari area halaman.
- Ekspektasi gagal: image terlalu besar keluar halaman, ukuran tidak ikut, atau export gagal.

4. notes.md image resize
- Buka `notes.md`.
- Insert/paste image, resize, tunggu save.
- Switch file lalu balik.
- Ekspektasi berhasil: ukuran image tetap sama.
- Ekspektasi gagal: ukuran hilang atau Markdown image rusak.

5. notes.md image lama
- Buka notes yang punya image belum pernah di-resize.
- Ekspektasi berhasil: image lama tetap tampil normal.
- Ekspektasi gagal: image lama berubah jadi broken atau format aneh.

6. .txt regression
- Buka `.txt`.
- Ekspektasi berhasil: tetap plain text; tidak ada behavior image/resize baru.
- Ekspektasi gagal: editor txt jadi rich/image mode.

7. Interaksi editor
- Ketik dekat image, pilih image, klik toolbar, coba zoom, fullscreen, table column resize, switch file, titlebar nav.
- Ekspektasi berhasil: semua tetap normal.
- Ekspektasi gagal: typing lambat, selection macet, toolbar mati, zoom/fullscreen/table/titlebar rusak.

Kalau semua oke, balas `pass`. Kalau ada bug, kirim nomor checklist + gejala.
```

- [ ] **Step 5: If user reports failure, stop without commit**

Do not stack patches blindly. Record the failing checklist number and symptom. Restore only the uncommitted Step 5c changes if rollback is needed, rebuild baseline after app closes, and stop before Step 6.

- [ ] **Step 6: If user replies `pass`, run fresh verification before commit**

Run:

```powershell
npm --prefix frontend run check
node --import ./frontend/tests/register-hooks.mjs --test ./frontend/tests/*.test.mjs
git diff --check -- frontend/src/lib/extensions/AssetImage.ts frontend/src/lib/markdown.ts frontend/src/lib/components/NotesEditor.svelte frontend/tests/markdown.test.ts frontend/tests/project-details-fase3-fase4.test.mjs
```

Expected:

- `svelte-check found 0 errors and 0 warnings`.
- Frontend tests pass.
- `git diff --check` exits 0.

- [ ] **Step 7: Commit only Step 5c files**

Run:

```powershell
git add -- frontend/src/lib/extensions/AssetImage.ts frontend/src/lib/markdown.ts frontend/src/lib/components/NotesEditor.svelte frontend/tests/markdown.test.ts frontend/tests/project-details-fase3-fase4.test.mjs
git diff --cached --check
git commit -m "feat(rte): add image drag resize"
```

Expected: one implementation commit containing only Step 5c files. Known nonblocking `pytest --lf -x` failure in `test_project_list_returns_converted_rows` may appear during pre-commit; commit may proceed if hook prints `pre-commit: PASS`.

## Self-Review

- Spec coverage: `.docx`, `notes.md`, `.txt` unchanged, NodeView, width attribute, Markdown inline HTML persistence, CSS handle, tests, build gate, manual gate, failure handling, and commit boundary are covered.
- Placeholder scan: no deferred implementation text or incomplete file paths remain.
- Type consistency: `AssetImage`, `PMNode`, `width`, `assetId`, `assetSrc`, `positiveWidthAttr`, `imageMarkdown`, `ne-img-wrap`, and `ne-img-handle` are named consistently across tasks.
- Scope: five existing files only for implementation; no backend, export, table, zoom, toolbar, or Step 6 work.
