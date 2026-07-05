# Editor Zoom Review Design

## Goal

Improve editor readability with a Word-like zoom system for every supported editor format, while giving DOCX page view a neutral gray workspace.

## Safety Sequence

1. Add DOCX gray workspace as one CSS-only round; build, manually verify, then commit.
2. Add cross-format zoom as a separate behavior round; build, manually verify, then commit.

Step 5b fixed page width is already committed. A zoom failure must not require rolling it back.

## DOCX Workspace

- Applies only to `.ne-editor-host.ne-docx-page`.
- Use `var(--main-panel-bg)` (`#E6E8EB`) behind the white page.
- Add `12px` workspace padding, `box-sizing:border-box`, and existing `6px` radius.
- Keep DOCX page width `720px`; Markdown/text remain full-width without page workspace.

## Zoom

- Supported formats: DOCX, Markdown, and plain text; unsupported MSG stays excluded.
- Minimum `100%`, maximum `500%`, step `25%`; initial value `100%`.
- Controls: minus button, clickable percentage reset, plus button.
- Shortcuts: `Ctrl + mouse wheel`, `Ctrl + +`/`Ctrl + =`, and `Ctrl + -`.
- Shortcuts act only when focus or pointer is inside editor, preventing whole-app/WebView zoom.
- Zoom value is shared while switching editor files during component lifetime and resets on app restart.
- CSS `zoom` scales rendering and layout so host scrollbars reflect visual size.
- Zoom never changes Tiptap content, font attributes, saved Markdown, source JSON, or DOCX export size.

## Verification

- Existing frontend source-contract tests cover workspace tokens, bounds, controls, shortcuts, scoping, and unsupported exclusion.
- Run svelte-check and full frontend tests after each round.
- Build only after explicit confirmation app is closed.
- Manual verification covers 100%, 125%, 250%, 500%; buttons; keyboard; wheel; DOCX/Markdown/text; fullscreen; save/export/file switching/titlebar responsiveness.

