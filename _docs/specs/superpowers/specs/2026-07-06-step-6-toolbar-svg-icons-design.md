# Step 6 Toolbar SVG Icons Design

## Goal

Replace text/emoji glyphs on NotesEditor toolbar buttons with crisp inline SVG icons so the toolbar reads professionally at 100%/125%/150% Windows scaling. Template-only change; no behavior, command, save, export, or CSS-token changes.

## Scope

- One RTE behavior round only: toolbar icon glyphs.
- Target branch: `project-details/tiptap-docx-pipeline`.
- Runtime file in scope: `frontend/src/lib/components/NotesEditor.svelte` (template only).
- Test file in scope: `frontend/tests/project-details-fase3-fase4.test.mjs`.
- No backend, no `markdown.ts`, no `AssetImage.ts`, no toolbar handler changes (`onmousedown` bodies, `rev++`, popover toggles stay byte-identical).

## Icons to replace (glyph → SVG)

| Button | Current glyph | SVG motif (lucide-style) |
| ------ | ------------- | ------------------------ |
| Undo | `↩` | curved arrow left |
| Redo | `↪` | curved arrow right |
| Blockquote | `❝` | double quote marks |
| Inline code | `</>` | chevrons |
| Code block | `</>`(2nd) | square + chevrons |
| Numbered list | `1.` | keep TEXT (typographic) |
| Bulleted list | `•` | keep TEXT (typographic) |
| Indent | `→` | chevron right + 3 lines |
| Outdent | `←` | chevron left + 3 lines |
| Align left | `≡L` | 3 lines flush left |
| Align center | `≡C` | 3 lines centered |
| Align right | `≡R` | 3 lines flush right |
| Justify | `≡J` | 3 full lines |
| Link | `🔗` | chain links (added: emoji cannot tint with currentColor; inconsistent with SVG set) |
| Horizontal rule | `HR` | single horizontal line |
| Table | `⊞` | grid rect |
| Image | `🖼` | rect + mountain + sun |
| Emoji trigger | `😊` | smile circle (emoji glyphs stay inside picker grid only) |
| Checklist | `☑` | list-checks |
| Clear formatting | `↺` | remove-formatting (strike T + x) |

Kept as styled TEXT (typographic by nature): B/I/U/S, x²/x₂, H1/H2/H3/¶, font/size selects, zoom −/%/+, `?` help, Cancel/OK/Insert/Remove action buttons, status glyphs.

## SVG spec

Inline only (offline rule — no icon library, no CDN). Same pattern as existing color/fullscreen SVGs in this file:

```html
<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">…</svg>
```

`currentColor` keeps existing hover red / active pink tinting via `.ne-tbtn` CSS. Buttons stay 24px tall; no CSS changes needed (`.ne-tbtn` already `inline-flex` centered).

## Test plan

Source-contract test in `project-details-fase3-fase4.test.mjs`:

1. Each replaced button (`title="Undo"`, `title="Redo"`, `title="Blockquote"`, `title="Inline code"`, `title="Code block"`, `title="Indent"`, `title="Outdent"`, `title="Align left"`, `title="Align center"`, `title="Align right"`, `title="Justify"`, `title="Link"`, `title="Horizontal rule"`, `title="Table"`, `title="Image"`, `title="Emoji"`, `title="Checklist"`, `title="Clear formatting"`) contains an inline `<svg` with `stroke="currentColor"`.
2. Old glyphs no longer appear as toolbar button children: `>↩<`, `>↪<`, `>❝<`, `>→<`, `>←<`, `>≡L<`, `>≡C<`, `>≡R<`, `>≡J<`, `>🔗<`, `>HR<`, `>⊞<`, `>🖼<`, `>😊<`, `>☑<`, `>↺<`.

Manual checklist: every icon sharp at 100%/125%/150% scaling, consistent stroke weight, hover red, active pink, buttons 24px, all commands still work, emoji picker grid unchanged.

## Failure handling

If manual check reports abnormal editor behavior or ugly icons: do not commit, restore uncommitted Step 6 files, rebuild baseline after app closes, record symptom, stop before Step 7.
