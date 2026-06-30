/**
 * Custom `fontSize` mark — there is no official Tiptap font-size extension, so we
 * extend the base Mark primitive and expose `fontSize` as an attribute rendered
 * to an inline `style="font-size: …"` on a span.
 *
 * Usage from the editor:
 *   editor.chain().focus().setFontSize('18px').run()
 *   editor.chain().focus().unsetFontSize().run()
 *   editor.getAttributes('fontSize').fontSize
 *
 * Kept dependency-free beyond @tiptap/core (D-0007).
 */
import { Mark } from "@tiptap/core";

declare module "@tiptap/core" {
  interface Commands<ReturnType> {
    fontSize: {
      /** Set a font size on the selection or pending marks (e.g. "18px"). */
      setFontSize: (size: string) => ReturnType;
      /** Remove the font size from the selection or pending marks. */
      unsetFontSize: () => ReturnType;
    };
  }
}

export const FontSize = Mark.create({
  name: "fontSize",

  addAttributes() {
    return {
      fontSize: {
        default: null,
        parseHTML: (el) => (el as HTMLElement).style.fontSize || null,
        renderHTML: (attrs) => {
          if (!attrs.fontSize) return {};
          return { style: `font-size: ${attrs.fontSize}` };
        },
      },
    };
  },

  parseHTML() {
    return [
      // Match any span carrying a font-size inline style.
      {
        tag: "span[style]",
        getAttrs: (el) => {
          if (typeof el === "string") return false;
          const fs = (el as HTMLElement).style.fontSize;
          return fs ? { fontSize: fs } : false;
        },
      },
    ];
  },

  renderHTML({ HTMLAttributes }) {
    return ["span", HTMLAttributes, 0];
  },

  addCommands() {
    return {
      setFontSize:
        (size: string) =>
        ({ commands }) =>
          commands.setMark(this.name, { fontSize: size }),
      unsetFontSize:
        () =>
        ({ commands }) =>
          commands.unsetMark(this.name),
    };
  },
});

export default FontSize;
