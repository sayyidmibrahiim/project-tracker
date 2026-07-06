# Step 6 Toolbar SVG Icons Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace text/emoji glyphs on NotesEditor toolbar buttons with inline SVG icons (lucide-style strokes) while keeping every command handler byte-identical.

**Architecture:** Template-only edit in `NotesEditor.svelte`. Each targeted button keeps its exact `onmousedown`, `class:active`, `disabled`, and `title` attributes; only the child glyph is swapped for an inline `<svg>`. Contract tests assert SVG presence per button title and absence of old glyphs.

**Tech Stack:** Svelte 5 template, inline SVG, Node test runner source-contract tests.

## Global Constraints

- Branch `project-details/tiptap-docx-pipeline`, repo root `D:/Ibrahim/Projects/project_tracker`.
- One RTE behavior round only (RTE Change Safety). Do not bundle Step 7 or docs sync.
- Modify only `frontend/src/lib/components/NotesEditor.svelte` (template) and `frontend/tests/project-details-fase3-fase4.test.mjs`.
- SVG pattern: `width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"`. No icon library, no CDN (offline rule).
- Keep as text: B/I/U/S, x²/x₂, H1–H3/¶, font/size selects, `1.`/`•` lists, zoom, `?`, dialog action buttons, status glyphs. Emoji glyphs stay inside the picker grid.
- Never run `npm run build` while the app may be open.
- No commit until automated verification passes AND user manually verifies rebuilt app.

---

### Task 1: Failing source-contract test

**Files:**
- Modify: `frontend/tests/project-details-fase3-fase4.test.mjs`

**Interfaces:**
- Consumes: existing `NE` constant (NotesEditor source string).
- Produces: `test("NotesEditor toolbar uses inline SVG icons")` relied on by Task 2.

- [ ] **Step 1: Add test after `NotesEditor styles the image resize handle`**

```javascript
test("NotesEditor toolbar uses inline SVG icons", () => {
  const svgButtons = ["Undo", "Redo", "Blockquote", "Inline code", "Code block", "Indent", "Outdent", "Align left", "Align center", "Align right", "Justify", "Link", "Horizontal rule", "Table", "Image", "Emoji", "Checklist", "Clear formatting"];
  for (const title of svgButtons) {
    const re = new RegExp(`title="${title}"(?:(?!</button>)[\\s\\S])*?>\\s*<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">`);
    assert.match(NE, re, `toolbar button "${title}" must render an inline SVG icon`);
  }
  for (const glyph of [">↩<", ">↪<", ">❝<", ">→<", ">←<", ">≡L<", ">≡C<", ">≡R<", ">≡J<", ">🔗<", ">HR<", ">⊞<", ">🖼<", ">😊<", ">☑<", ">↺<"]) {
    assert.ok(!NE.includes(glyph), `old toolbar glyph ${glyph} must be gone`);
  }
});
```

- [ ] **Step 2: Run focused test, expect FAIL**

```powershell
node --import ./frontend/tests/register-hooks.mjs --test --test-name-pattern "toolbar uses inline SVG" ./frontend/tests/project-details-fase3-fase4.test.mjs
```

Expected: FAIL (`toolbar button "Undo" must render an inline SVG icon`).

### Task 2: Replace glyphs with inline SVGs

**Files:**
- Modify: `frontend/src/lib/components/NotesEditor.svelte` (template only; keep every attribute on each button unchanged)

**Interfaces:**
- Consumes: existing toolbar buttons located by `title` attribute.
- Produces: SVG children matching Task 1 regex.

- [ ] **Step 1: Swap each glyph for its SVG**

Shared prefix for every icon below: `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">`

| Title | Replace child | With SVG body |
| ----- | ------------- | ------------- |
| Undo | `↩` | `<path d="M9 14 4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11"/>` |
| Redo | `↪` | `<path d="m15 14 5-5-5-5"/><path d="M20 9H9.5a5.5 5.5 0 0 0 0 11H13"/>` |
| Blockquote | `❝` | `<path d="M10 11H6a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h3a1 1 0 0 1 1 1v6c0 2-1 3-3 4"/><path d="M19 11h-4a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h3a1 1 0 0 1 1 1v6c0 2-1 3-3 4"/>` |
| Inline code | `{@html '&lt;/&gt;'}` | `<polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>` |
| Code block | `{"</>"}` | `<rect x="3" y="3" width="18" height="18" rx="2"/><path d="m10 9-2.5 3L10 15"/><path d="m14 9 2.5 3L14 15"/>` |
| Indent | `→` | `<polyline points="3 8 7 12 3 16"/><line x1="21" y1="6" x2="11" y2="6"/><line x1="21" y1="12" x2="11" y2="12"/><line x1="21" y1="18" x2="11" y2="18"/>` |
| Outdent | `←` | `<polyline points="7 8 3 12 7 16"/><line x1="21" y1="6" x2="11" y2="6"/><line x1="21" y1="12" x2="11" y2="12"/><line x1="21" y1="18" x2="11" y2="18"/>` |
| Align left | `≡L` | `<line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="15" y2="12"/><line x1="3" y1="18" x2="17" y2="18"/>` |
| Align center | `≡C` | `<line x1="3" y1="6" x2="21" y2="6"/><line x1="6" y1="12" x2="18" y2="12"/><line x1="5" y1="18" x2="19" y2="18"/>` |
| Align right | `≡R` | `<line x1="3" y1="6" x2="21" y2="6"/><line x1="9" y1="12" x2="21" y2="12"/><line x1="7" y1="18" x2="21" y2="18"/>` |
| Justify | `≡J` | `<line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>` |
| Link | `🔗` | `<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>` |
| Horizontal rule | `HR` | `<line x1="4" y1="12" x2="20" y2="12"/>` |
| Table | `⊞` | `<rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="3" y1="15" x2="21" y2="15"/><line x1="12" y1="3" x2="12" y2="21"/>` |
| Image | `🖼` | `<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="m21 15-5-5L5 21"/>` |
| Emoji | `😊` | `<circle cx="12" cy="12" r="9"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/>` |
| Checklist | `☑` | `<path d="m3 17 2 2 4-4"/><path d="m3 7 2 2 4-4"/><line x1="13" y1="6" x2="21" y2="6"/><line x1="13" y1="12" x2="21" y2="12"/><line x1="13" y1="18" x2="21" y2="18"/>` |
| Clear formatting | `↺` | `<path d="M4 7V4h16v3"/><path d="M5 20h6"/><path d="M13 4 8 20"/><line x1="15" y1="15" x2="21" y2="21"/><line x1="21" y1="15" x2="15" y2="21"/>` |

Note: the Emoji trigger button `title` is `Emoji`; picker grid emoji glyphs stay untouched.

- [ ] **Step 2: Run focused test, expect PASS**

```powershell
node --import ./frontend/tests/register-hooks.mjs --test --test-name-pattern "toolbar uses inline SVG" ./frontend/tests/project-details-fase3-fase4.test.mjs
```

Expected: PASS.

### Task 3: Verify, build gate, manual gate, commit

**Files:**
- Verify: both Step 6 files.

**Interfaces:**
- Consumes: Task 2 implementation.
- Produces: user-verified Step 6 commit `feat(rte): step 6 — svg toolbar icons`.

- [ ] **Step 1: Full verification**

```powershell
npm --prefix frontend run check
node --import ./frontend/tests/register-hooks.mjs --test ./frontend/tests/*.test.mjs
git diff --check -- frontend/src/lib/components/NotesEditor.svelte frontend/tests/project-details-fase3-fase4.test.mjs
```

Expected: 0 errors/0 warnings; all tests pass; diff check exit 0.

- [ ] **Step 2: Ask user to close app, build after `closed`**

```powershell
npm --prefix frontend run build
```

- [ ] **Step 3: Manual checklist (Indonesian), wait for `pass`**

Icons sharp at 100%/125%/150%, stroke consistent, hover red, active pink, 24px buttons, all commands work, emoji picker unchanged, editor regression normal.

- [ ] **Step 4: On `pass`: rerun verification, then commit only Step 6 files**

```powershell
git add -- frontend/src/lib/components/NotesEditor.svelte frontend/tests/project-details-fase3-fase4.test.mjs
git diff --cached --check
git commit -m "feat(rte): step 6 - svg toolbar icons"
```

Known nonblocking pre-commit failure: `test_project_list_returns_converted_rows` (pre-existing). Commit valid if hook prints `pre-commit: PASS`.

## Self-Review

- Spec coverage: all 18 SVG buttons + kept-text list + emoji-picker exception + test + gates covered.
- Placeholder scan: none.
- Type consistency: titles in Task 1 array match Task 2 table exactly (`Emoji` not `Emoji trigger`).
