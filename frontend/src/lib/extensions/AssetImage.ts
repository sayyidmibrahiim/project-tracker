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

      const handle = document.createElement("span");
      handle.className = "ne-img-handle";
      handle.addEventListener("mousedown", (event) => {
        if (!editor.isEditable) return;
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
