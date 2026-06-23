# Project Details UI — Fase 2: Icon & Design Language Overhaul (Notion Minimalist)

**Status:** Approved design (pending implementation)
**Date:** 2026-06-22
**Scope owner:** Sayyid Ibrahim
**Origin review:** User feedback on Project Details UI/UX (review points 5 & 6)
**Phase:** 2 of 4 — see _Phase Roadmap_ in Phase 1 spec for full schedule.

## Goal

Redesign the visual presentation of the Project Details screen to match a clean,
minimalist "Notion-like" aesthetic with tactical DBS Red accenting. This is achieved by
replacing raw ASCII glyphs with consistent, modern inline SVGs, softening shadows and
borders, removing high-contrast card accents, and relaxing page layout density through
adjusted padding and margins.

Review points covered by Fase 2: **5 and 6.**

## Non-goals

- Altering functional logic, backend operations, or bridge contracts.
- Adding third-party icon libraries (Lucide, FontAwesome, etc.) — all icons must remain
  inline SVGs to satisfy the codebase's frozen-dependency constraint.
- Modifying notes WYSIWYG editor (deferred to Fase 3) or sub-project detail views
  (deferred to Fase 4).

## Design Specification

### Section 1 — Card & Accent Overhaul (Review Point 6)

The Left-Border Card Accent pattern (`border-left: 3px solid var(--color-dbs-red)`) is
removed from all panels on the Project Details screen. It is replaced with a clean,
four-sided border structure.

**Section Card Styling (`.pd-section`):**

- Hapus: `border-left: 3px solid var(--color-dbs-red)`
- Tambah: `border: 1px solid var(--color-border)` (resolves to `#E5E7EB` / light gray)
- Background: `var(--color-workspace-panel)` (resolves to `#FFFFFF` / white)
- Border Radius: `8px`
- Box Shadow: `0 1px 3px rgba(0,0,0,0.05)` (replacing the previous deep `var(--shadow-card)`).

**DBS Red Accent Interaction Rules:**

- Merah DBS (`#B91C1C` / `var(--primary-red)`) is reserved strictly for interaction states:
  - Input/Select/Textarea focus state: `border-color: var(--primary-red); box-shadow: 0 0 0 2px var(--color-dbs-red-active);`
  - Button hover state: primary buttons darken slightly, secondary/tertiary buttons draw a red outline.
  - Active navigations (e.g. Back button hover).
  - High-risk buttons (Delete) and error states remain red.

### Section 2 — Spacing & Typography Overhaul (Review Point 6)

- **Pane Spacing:** The gap between the left and right pane (`.split`) is increased from `12px` to `16px`.
- **Card Spacing:** The gap between sections (`.pane` gap) is increased from `10px` to `14px`.
- **Card Internal Padding:** Card padding (`.pd-section` padding) is increased from `14px` to `18px`.
- **Typography Tone:**
  - Label text (`.pd-meta-label`, `.pd-dl-item dt`) color is changed to a soft gray-500 (`#6B7280`).
  - Body text (`.pd-dl-item dd`, input text) is changed to a soft gray-800 (`#1F2937`) to avoid harsh pure-black contrast.
  - Titles (`.pd-section-title`) retain weight but use `font-size: 14px` and color `var(--color-ink-strong)`.

### Section 3 — Icon Overhaul: ASCII to SVG (Review Point 5)

All legacy ASCII/Unicode glyphs in the Project Details screen are replaced with inline SVGs.
All SVGs share a standard style: `stroke-width: 2`, `stroke-linecap: round`, `stroke-linejoin: round`, and `fill: none` (unless filled is required). They size at `14px` or `16px` depending on context and default to color `var(--color-muted)` (`#6B7280`), transitioning to `var(--primary-red)` (`#B91C1C`) on hover/active.

Replacements:

1. **`▣` (Command Center & Title):**
   - Replace with a 2x2 grid icon (Layout).
   - Markup:
     ```html
     <svg
       xmlns="http://www.w3.org/2000/svg"
       width="14"
       height="14"
       viewBox="0 0 24 24"
       fill="none"
       stroke="currentColor"
       stroke-width="2"
       stroke-linecap="round"
       stroke-linejoin="round"
       class="pd-icon"
     >
       <rect x="3" y="3" width="7" height="9"></rect>
       <rect x="14" y="3" width="7" height="5"></rect>
       <rect x="14" y="12" width="7" height="9"></rect>
       <rect x="3" y="16" width="7" height="5"></rect>
     </svg>
     ```
2. **`←` (Back Arrow):**
   - Replace with a left arrow.
   - Markup:
     ```html
     <svg
       xmlns="http://www.w3.org/2000/svg"
       width="14"
       height="14"
       viewBox="0 0 24 24"
       fill="none"
       stroke="currentColor"
       stroke-width="2"
       stroke-linecap="round"
       stroke-linejoin="round"
       class="pd-icon"
     >
       <line x1="19" y1="12" x2="5" y2="12"></line>
       <polyline points="12 19 5 12 12 5"></polyline>
     </svg>
     ```
3. **`⚠` (Warning/Alert):**
   - Replace with a warning triangle.
   - Markup:
     ```html
     <svg
       xmlns="http://www.w3.org/2000/svg"
       width="14"
       height="14"
       viewBox="0 0 24 24"
       fill="none"
       stroke="currentColor"
       stroke-width="2"
       stroke-linecap="round"
       stroke-linejoin="round"
       class="pd-icon"
     >
       <path
         d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"
       ></path>
       <line x1="12" y1="9" x2="12" y2="13"></line>
       <line x1="12" y1="17" x2="12.01" y2="17"></line>
     </svg>
     ```
4. **`✗`/`✓` (Success/Error feedback):**
   - Success checkmark-circle:
     ```html
     <svg
       xmlns="http://www.w3.org/2000/svg"
       width="14"
       height="14"
       viewBox="0 0 24 24"
       fill="none"
       stroke="currentColor"
       stroke-width="2"
       stroke-linecap="round"
       stroke-linejoin="round"
       class="pd-icon"
     >
       <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
       <polyline points="22 4 12 14.01 9 11.01"></polyline>
     </svg>
     ```
   - Error x-circle:
     ```html
     <svg
       xmlns="http://www.w3.org/2000/svg"
       width="14"
       height="14"
       viewBox="0 0 24 24"
       fill="none"
       stroke="currentColor"
       stroke-width="2"
       stroke-linecap="round"
       stroke-linejoin="round"
       class="pd-icon"
     >
       <circle cx="12" cy="12" r="10"></circle>
       <line x1="15" y1="9" x2="9" y2="15"></line>
       <line x1="9" y1="9" x2="15" y2="15"></line>
     </svg>
     ```
5. **`⏳` (Saving/Pending):**
   - Replace with a spinner icon.
   - Markup:
     ```html
     <svg
       class="pd-spinner pd-icon"
       xmlns="http://www.w3.org/2000/svg"
       width="14"
       height="14"
       viewBox="0 0 24 24"
       fill="none"
       stroke="currentColor"
       stroke-width="2"
       stroke-linecap="round"
       stroke-linejoin="round"
     >
       <line x1="12" y1="2" x2="12" y2="6"></line>
       <line x1="12" y1="18" x2="12" y2="22"></line>
       <line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line>
       <line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line>
       <line x1="2" y1="12" x2="6" y2="12"></line>
       <line x1="18" y1="12" x2="22" y2="12"></line>
       <line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line>
       <line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line>
     </svg>
     ```
   - Add infinite CSS spin rotation in style.
6. **`📋` (Copy Link):**
   - Replace with clipboard icon.
   - Markup:
     ```html
     <svg
       xmlns="http://www.w3.org/2000/svg"
       width="14"
       height="14"
       viewBox="0 0 24 24"
       fill="none"
       stroke="currentColor"
       stroke-width="2"
       stroke-linecap="round"
       stroke-linejoin="round"
       class="pd-icon"
     >
       <path
         d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"
       ></path>
       <rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect>
     </svg>
     ```
7. **`↗` (Open Link):**
   - Replace with external-link arrow.
   - Markup:
     ```html
     <svg
       xmlns="http://www.w3.org/2000/svg"
       width="14"
       height="14"
       viewBox="0 0 24 24"
       fill="none"
       stroke="currentColor"
       stroke-width="2"
       stroke-linecap="round"
       stroke-linejoin="round"
       class="pd-icon"
     >
       <path
         d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"
       ></path>
       <polyline points="15 3 21 3 21 9"></polyline>
       <line x1="10" y1="14" x2="21" y2="3"></line>
     </svg>
     ```
8. **`✎` (Edit Link/Notes):**
   - Replace with pencil/edit icon.
   - Markup:
     ```html
     <svg
       xmlns="http://www.w3.org/2000/svg"
       width="14"
       height="14"
       viewBox="0 0 24 24"
       fill="none"
       stroke="currentColor"
       stroke-width="2"
       stroke-linecap="round"
       stroke-linejoin="round"
       class="pd-icon"
     >
       <path
         d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"
       ></path>
       <path d="M18.5 2.5a2.121 2.121 0 1 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
     </svg>
     ```
9. **`📁` (Open Folder):**
   - Replace with folder icon.
   - Markup:
     ```html
     <svg
       xmlns="http://www.w3.org/2000/svg"
       width="14"
       height="14"
       viewBox="0 0 24 24"
       fill="none"
       stroke="currentColor"
       stroke-width="2"
       stroke-linecap="round"
       stroke-linejoin="round"
       class="pd-icon"
     >
       <path
         d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"
       ></path>
     </svg>
     ```

## Testing Strategy

Since the tests are source-text assertions checking specific regexes, the test changes in Fase 2 will be:

1. **Update `project-details-fase1.test.mjs`** to replace raw ASCII characters checks with SVG structure checks. E.g.:
   - Check if `<svg` is present in the Command Center title and Back bar.
   - Check if clipboard, external-link, and pencil SVGs are matched.
2. **Update `as-is-prototype-parity.test.mjs`** if it asserts the ASCII characters (none found in Task 3 exploration grep, but audit to be safe).
3. **Verify compile check `npm run check`** has 0 warnings about unused styles (cleaning up `.panel-title-icon`, `.panel-card.accent` if changed).
