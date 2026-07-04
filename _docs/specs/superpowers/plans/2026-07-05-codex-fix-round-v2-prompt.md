# Branch 2 Fix Round v2 — Prompt Plan untuk Codex Desktop

> Master completion plan yang lama sudah tersimpan di repo: `_docs/specs/superpowers/plans/2026-07-04-completion-master-plan.md`. File ini sekarang berisi plan untuk fix round v2 saja.

## Context

Fix round pertama (5 perubahan sekaligus di NotesEditor/AssetImage/markdown.ts/docx_writer) membuat RTE loading lama dan titlebar nav terkunci (`app:interaction-lock` menahan seluruh app saat RTE load hang) → full rollback ke `9882694` (commit rollback `3b4444e`). Root cause pasti tidak teridentifikasi (user lupa kondisi kejadian; hipotesis kuat: bundle `web/static` stale/di-build saat app terbuka + lock tanpa fail-safe). Pelajaran binding tercatat di CLAUDE.md/AGENTS.md §"RTE Change Safety".

Sekarang semua poin manual check (1–5 lama + 6–7 baru) dikerjakan ulang **satu behavior per step, user test di antara step**. Deliverable = prompt siap-tempel untuk Codex desktop. Claude = otak (spesifikasi presisi dari implementasi v1 yang sudah pernah hijau + pitfall yang sudah ketemu); Codex = tangan.

Keputusan yang sudah dikunci user:
- Poin 5: WYSIWYG page bounds (editor docx selebar area cetak, pengganti ruler) + backend clamp + drag-resize gambar. Margin default = Word Narrow 12.7mm.
- Poin 7: default size = **18 versi dropdown editor (18px ≈ 13.5pt di Word)**, font Times New Roman.

Step 0 (tambahan dari analisa incident): interaction-lock fail-safe, supaya satu hang di RTE tidak pernah lagi membekukan seluruh app.

---

## PROMPT UNTUK CODEX (copy mulai dari garis di bawah sampai akhir file)

```
You are working on Project Tracker at D:\Ibrahim\Projects\project_tracker (Windows, PowerShell).
Branch: project-details/tiptap-docx-pipeline (already checked out; HEAD = rollback commit 3b4444e). Do NOT create a new branch, do NOT touch main, do NOT delete branches.

READ FIRST (in this order, no coding before done):
1. AGENTS.md — especially section "RTE Change Safety (binding — incident 2026-07-04)"
2. _docs/session-notes.md — top entry "2026-07-04 (rollback — Branch 2 fix round)"
3. frontend/src/lib/components/NotesEditor.svelte (the whole file)
4. frontend/src/lib/rteDocxState.ts, frontend/src/lib/extensions/AssetImage.ts, frontend/src/lib/markdown.ts
5. infrastructure/docx_writer.py, services/rte_document_service.py

WHY THIS PROTOCOL EXISTS: a previous AI bundled all these changes in one round; the app became unusable (RTE slow-load + titlebar nav frozen via app:interaction-lock) and everything was rolled back. You are re-applying the same features ONE AT A TIME.

════════ EXECUTION PROTOCOL (MANDATORY) ════════
- Execute steps 0→7 strictly in order. ONE step per round.
- After EACH step run:
    npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run check   (must be 0 errors)
    npm --prefix D:/Ibrahim/Projects/project_tracker/frontend test        (must be 0 fail)
    D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_phase_e_notes_persistence.py -v   (only for steps touching Python)
    npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run build
  then STOP and tell the user: "Restart the app (python -m main from repo root) and test step N: <specific checks>". Wait for the user's OK before committing and starting the next step.
- Commit per step (conventional message, e.g. "fix(rte): step 1 — toolbar active states"). Never amend, never bundle two steps in one commit.
- If the user reports ANY abnormality after a step: git revert that single step's commit, record what happened in _docs/session-notes.md, and ask the user before retrying differently.
- HARD RULES: never run npm build while the app might be open (tell the user to close it first); web/static is gitignored so it does NOT follow git checkout — always rebuild after any branch operation; never write raw control characters (NUL) into source files — write escape sequences like \u0000 as six ASCII characters; no NEW Python test files (extend tests/test_phase_e_notes_persistence.py only); frontend new test files are allowed; run everything from repo root with the venv path above.
- Known pre-existing failures (NOT yours, do not fix, do not block on them): tests/test_phase_c_js_api_project.py::test_project_list_*, test_year_create.py (2), test_phase_d_app_web_project_service_adapter.py — they fail on main too.

════════ STEP 0 — interaction-lock fail-safe (prevents the "whole app frozen" symptom class) ════════
Files: frontend/src/App.svelte (listener for "app:interaction-lock"), frontend/src/lib/components/ProjectDetails.svelte (dispatchers).
- Find every place that engages the lock around RTE load/flush (search "app:interaction-lock"). Ensure every engage path releases in try/finally.
- In App.svelte's lock handler add a watchdog: when locked, setTimeout 10s → if still locked, force-release + console.warn("interaction-lock watchdog released"). Clear the timer on normal release.
- Acceptance: open a CR project, switch docs repeatedly — titlebar nav ALWAYS clickable within at most 10s even if a load hangs.

════════ STEP 1 — toolbar toggle active states ════════
File: frontend/src/lib/components/NotesEditor.svelte.
Root cause of the missing active states: the render token is a plain `let rev = 0;` (comment says non-reactive) so `class:active={isActive('bold')}` is never re-evaluated.
- Change to `let rev = $state(0);`. In `isActive()` and `alignIs()` add `void rev;` as the first line so template calls subscribe to it. Do NOT read `rev` inside any $effect (loop risk — that is why it was made non-reactive).
- The template already has class:active bindings on B/I/U/S, sup/sub, H1–H3/¶, quote/code/codeBlock, ol/ul, align L/C/R/J, link, checklist — no template changes needed.
- WATCH ITEM: if after this step the user reports slow typing or slow RTE load, fallback = keep rev non-reactive and add a separate `uiTick = $state(0)` bumped from a requestAnimationFrame-throttled `editor.on("transaction")` listener registered via queueMicrotask after mount. Only use the fallback if the simple version misbehaves.
- Acceptance: click into bold text → B button shows the red active style; toggling on/off updates immediately; typing latency unchanged; RTE loads normally; titlebar stays alive.

════════ STEP 2 — idle export 5s + live countdown in status ════════
Files: frontend/src/lib/components/NotesEditor.svelte, frontend/src/lib/rteDocxState.ts, frontend/tests/rte-docx-state.test.ts.
- NotesEditor: IDLE_EXPORT_MS 20_000 → 5_000.
- rteDocxState.ts: add
    export function docxCountdownLabel(secondsLeft: number): string {
      return `Saved — DOCX in ${Math.max(1, Math.round(secondsLeft))}s`;
    }
- NotesEditor: add `let exportCountdown = $state(0)` + a 1s setInterval started where flushDocx bumps idleExport (set 5, decrement, stop at 0). Stop it when: export becomes scheduled/running, in the doc-switch $effect, in onDestroy, and inside the idleExport callback before requestDocxExport(). statusLabel derived: in docx mode when status is saved/idle and exportCountdown>0 and display!=="exporting" → docxCountdownLabel(exportCountdown), else the existing docxStatusLabel(...).
- Test: docxCountdownLabel(5)==="Saved — DOCX in 5s"; (0.4)→"…1s".
- Acceptance: type in a .docx → "Saved — DOCX in 5s…4s…" → "Exporting DOCX…" → "DOCX saved". Ctrl+S skips straight to exporting.

════════ STEP 3 — hide .rte sidecar folders (Windows) ════════
File: services/rte_document_service.py (+ extend tests/test_phase_e_notes_persistence.py).
- Add a module helper:
    def _hide_dir_windows(path: Path) -> None:
        if sys.platform != "win32" or not path.is_dir(): return
        try:
            import ctypes
            ctypes.windll.kernel32.SetFileAttributesW(str(path), 0x02)  # FILE_ATTRIBUTE_HIDDEN
        except Exception: pass
  (import sys at top). Call it after writing in _store_source (on sidecar_dir) and after _atomic_write_bytes in save_image (on the document's sidecar_dir).
- Extend phase E tests: after a save_document, on win32 assert GetFileAttributesW(sidecar) & 0x02.
- Acceptance: _cr-docs/.rte invisible in Explorer (without "show hidden"); pipeline still saves/exports fine.

════════ STEP 4 — "?" shortcuts & tips popover ════════
File: frontend/src/lib/components/NotesEditor.svelte.
- Add `let helpOpen = $state(false)`; include `helpOpen = false` in closeAllPopovers().
- In the .ne-actions cluster (left of the fullscreen button) add a .ne-popover-wrap with a "?" .ne-tbtn (class:active={helpOpen}, aria-label) toggling helpOpen (close other popovers first). Popover rows (kbd chip + text): Ctrl+S = Save ("+ export DOCX now" in docx mode); Ctrl+B/I/U; Ctrl+Z / Ctrl+Y; Win+Shift+S then Ctrl+V = paste screenshot; drag & drop image file; drag image corner / table column edge to resize; docx-only: "DOCX exports automatically 5s after Saved".
- Style like the existing .ne-link-pop (right-aligned popover, ~250px, kbd chips with --soft-pink-surface / --soft-white-border tokens).
- Acceptance: "?" opens/closes, click-outside closes, consistent with design tokens at 3 window sizes.

════════ STEP 5a — backend: Narrow margins + never-cut-off clamp ════════
Files: infrastructure/docx_writer.py, services/rte_document_service.py, tests/test_phase_e_notes_persistence.py.
- DEFAULT_DOCUMENT_SETTINGS margins 20 → 12.7 (all four; Word "Narrow"). Update the 20 fallbacks in _apply_page_setup to 12.7 too.
- Add:
    def content_width_mm(settings) -> float:
        return max(210.0 - float(settings.get("margin_left_mm",12.7)) - float(settings.get("margin_right_mm",12.7)), 40.0)
  In _Renderer.__init__: self.content_width_px = content_width_mm(settings) / 25.4 * 96.0
- _image_run: max_width = Inches(self.content_width_px/96.0). If attrs width>0 → kwargs["width"] = min(Inches(w/96), max_width). Else probe the natural size:
    from docx.image.image import Image as _DocxImage
    probe = _DocxImage.from_file(str(path)); natural = Inches(probe.px_width / float(probe.horz_dpi or 96))
    if natural > max_width: kwargs["width"] = max_width
  (wrap the probe in try/except: pass).
- _table: before writing tcW widths, if the sum of specified col_widths_px > self.content_width_px → scale each proportionally.
- rte_document_service.save_document: when the revision bumps, also set source["document_settings"] = dict(DEFAULT_DOCUMENT_SETTINGS) so old 20mm sidecars migrate on the next save.
- Tests to add (patterns already proven green): defaults are 12.7 and content_width_mm ≈ 184.6; an export with image width 5000px + a 2-col table with colwidth [900,900] gives doc.inline_shapes[0].width <= Mm(184.6)+1000 EMU, and the sum of first-row w:tcW dxa <= 184.6/25.4*96*15 + 15.
- Acceptance: re-export a doc that previously overflowed → open in Word → nothing cut off at the right margin.

════════ STEP 5b — editor WYSIWYG page width (docx mode only) ════════
File: frontend/src/lib/components/NotesEditor.svelte.
- Host div gets class:ne-docx-page={docxPipelineMode}. CSS (:global):
    .ne-editor-host.ne-docx-page { overflow-x:auto; }
    .ne-editor-host.ne-docx-page .ne-textarea { width:720px; max-width:none; margin:0 auto; box-sizing:border-box; }
  (720px border-box = 698px printable [184.6mm @96dpi] + 2×10 padding + 2×1 border. Keep a comment explaining this.)
- Acceptance: docx editor area is a centered fixed page width; md editors unchanged; a 100%-width table in the editor equals the printable width in Word.

════════ STEP 5c — image drag-resize (highest-risk step, keep it alone) ════════
Files: frontend/src/lib/extensions/AssetImage.ts, frontend/src/lib/markdown.ts, NotesEditor.svelte (CSS only), frontend/tests/markdown.test.ts.
- AssetImage: add a `width` attribute (parseHTML from the width attr, positive integer else null; renderHTML → width="N") alongside assetId/assetSrc. Add addNodeView(): span.ne-img-wrap containing the img (apply src/alt/data-asset-id/data-asset-src/style.width from node attrs; keep a `current` node ref; update(n){ if different type return false; current=n; apply(n); return true; }). If editor.isEditable append span.ne-img-handle with a mousedown drag: track clientX delta from the img's bounding width, live-preview via img.style.width, on mouseup dispatch editor.view.state.tr.setNodeMarkup(getPos(), undefined, {...current.attrs, width}) (min 40px).
- markdown.ts: (1) TAG_ATTRS img += "width"; (2) DOM serializer img case: if the width attr is digits → emit `<img src="${assetSrc||src}" alt="${alt}" width="${w}" />` (inline HTML — markdown image syntax cannot hold width), else keep `![alt](src)`; (3) fallbackHtmlToMarkdown: same branch BUT the emitted tag would be destroyed by the final strip-all-tags replace — push the html into `keepImgs: string[]` and return the token `\u0000K<index>\u0000` — in the TS source write the string literal `\`\u0000K${keepImgs.length - 1}\u0000\`` where \u0000 is typed as the six ASCII characters backslash-u-0-0-0-0, NEVER a literal NUL byte, then AFTER the `<[^>]+>` strip add `.replace(/\u0000K(\d+)\u0000/g, (_m,i)=>keepImgs[Number(i)] ?? "")`.
- CSS in NotesEditor (:global under .ne-editor-host): .ne-img-wrap { position:relative; display:inline-block; max-width:100%; line-height:0; } .ne-img-wrap img { display:block; max-width:100%; } .ne-img-handle { position:absolute; right:-5px; bottom:-5px; width:11px; height:11px; background:var(--card-white); border:2px solid var(--color-dbs-red); border-radius:3px; cursor:nwse-resize; opacity:0; } .ne-img-wrap:hover .ne-img-handle, .ProseMirror-selectednode .ne-img-handle { opacity:1; }
- Tests (markdown.test.ts): htmlToMarkdown of an img with width+data-asset-src emits `<img src=".rte/assets/…" alt="shot" width="240" />`; renderMarkdown of that HTML keeps src + width.
- KNOWN PITFALL: node --test runs TS in strip-only mode — no TS parameter properties anywhere; type the node view loosely with `import type { Node as PMNode } from "@tiptap/pm/model"`.
- Acceptance: hover an image → red corner handle; drag shrinks/grows live; the size persists after doc switch and app restart (docx AND notes.md); export respects the size (still clamped by 5a); typing/cursor around images behaves normally. Table column drag already works (Table resizable:true) — verify unchanged.

════════ STEP 6 — professional SVG icons for the toolbar ════════
File: frontend/src/lib/components/NotesEditor.svelte (template only).
- Replace the text/emoji glyphs on toolbar buttons with crisp inline SVGs: undo ↩, redo ↪, indent →, outdent ←, align ≡L/≡C/≡R/≡J, quote ❝, inline code, code block, HR, table ⊞, image 🖼, emoji trigger 😊 (keep emoji glyphs only inside the picker grid), checklist ☑, clear format ↺. Keep B/I/U/S, x², x₂, H1/H2/H3/¶ and the font/size selects as styled TEXT (typographic by nature, already read well).
- SVG spec: inline (no icon library, no CDN — offline rule), viewBox="0 0 24 24", fill="none", stroke="currentColor", stroke-width="2", stroke-linecap="round", stroke-linejoin="round", rendered at width/height 13–14 — same pattern as the existing color/fullscreen SVGs in this file. currentColor keeps hover/active tinting working.
- Acceptance: every icon sharp at 100%/125%/150% Windows scaling, consistent stroke weight, hover turns red, active state fills pink like today; buttons stay 24px tall.

════════ STEP 7 — default font Times New Roman + size 18 (editor px scale) ════════
Files: frontend/src/lib/components/NotesEditor.svelte, infrastructure/docx_writer.py, tests/test_phase_e_notes_persistence.py.
- Editor: .ne-editor-host .ne-textarea font-size 12px → 18px (font-family already "Times New Roman", serif). Initialize fontSelVal to the Times New Roman option value and sizeSelVal to "18" so the dropdowns display the real defaults.
- Exporter: DEFAULT_DOCUMENT_SETTINGS default_font_size_pt 11 → 13.5 (= 18px × 0.75 → Word shows 13.5pt; keeps editor↔Word WYSIWYG). default_font_family stays "Times New Roman".
- Extend a phase E assertion for the new default (13.5).
- Acceptance: a new empty doc types at 18px TNR; dropdowns show Times New Roman + 18; export opens in Word at 13.5pt TNR; explicit per-text font/size overrides still win.

════════ AFTER ALL STEPS ════════
- Docs sync: PRD.md §12.12 (5s idle + countdown, Narrow margins + WYSIWYG page + clamp, drag-resize, hidden .rte, help popover, default TNR 18px↔13.5pt, SVG toolbar), _docs/PROGRESS.md active-slice line, _docs/session-notes.md new entry. Commit docs separately.
- Give the user one final consolidated manual checklist covering steps 0–7.
- Do NOT merge to main. Merge only happens after the user says so.
```
