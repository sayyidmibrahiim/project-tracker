// Image node with stable asset identity for the DOCX pipeline (D-0012).
//
// Extends the stock Tiptap Image extension with:
//   assetId  — content hash id of the stored asset file (16 hex chars)
//   assetSrc — path relative to the document folder (.rte/assets/<id>.<ext>);
//              markdown serialization prefers this over the (data URI) src.
//   width    — display width in px, set by the drag-resize handle. The DOCX
//              exporter reads it (clamped to the printable page width).
// `src` stays a data URI for display, exactly like the legacy embed path, so
// existing base64 images keep working unchanged.
//
// A custom node view adds a bottom-right drag handle so users can shrink
// images that would otherwise overflow the page margin in the export.

import Image from "@tiptap/extension-image";
import type { Node as PMNode } from "@tiptap/pm/model";

const MIN_WIDTH_PX = 40;

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
        parseHTML: (el: HTMLElement) => {
          const raw = el.getAttribute("width");
          const parsed = raw ? parseInt(raw, 10) : NaN;
          return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
        },
        renderHTML: (attrs: Record<string, unknown>) =>
          attrs.width ? { width: String(attrs.width) } : {},
      },
    };
  },

  addNodeView() {
    return ({ node, editor, getPos }) => {
      const wrap = document.createElement("span");
      wrap.className = "ne-img-wrap";
      const img = document.createElement("img");
      wrap.appendChild(img);

      let current: PMNode = node;
      const apply = (n: PMNode) => {
        img.src = String(n.attrs.src || "");
        img.alt = String(n.attrs.alt || "");
        if (n.attrs.assetId) img.setAttribute("data-asset-id", String(n.attrs.assetId));
        if (n.attrs.assetSrc) img.setAttribute("data-asset-src", String(n.attrs.assetSrc));
        const w = n.attrs.width;
        img.style.width = typeof w === "number" && w > 0 ? `${w}px` : "";
      };
      apply(node);

      if (editor.isEditable) {
        const handle = document.createElement("span");
        handle.className = "ne-img-handle";
        handle.title = "Drag to resize";
        handle.addEventListener("mousedown", (e: MouseEvent) => {
          e.preventDefault();
          e.stopPropagation();
          const startX = e.clientX;
          const startW = img.getBoundingClientRect().width || MIN_WIDTH_PX;
          const widthAt = (ev: MouseEvent) =>
            Math.max(MIN_WIDTH_PX, Math.round(startW + (ev.clientX - startX)));
          const onMove = (ev: MouseEvent) => {
            img.style.width = `${widthAt(ev)}px`;
          };
          const onUp = (ev: MouseEvent) => {
            window.removeEventListener("mousemove", onMove);
            window.removeEventListener("mouseup", onUp);
            const pos = typeof getPos === "function" ? getPos() : undefined;
            if (typeof pos !== "number") return;
            const tr = editor.view.state.tr.setNodeMarkup(pos, undefined, {
              ...current.attrs,
              width: widthAt(ev),
            });
            editor.view.dispatch(tr);
          };
          window.addEventListener("mousemove", onMove);
          window.addEventListener("mouseup", onUp);
        });
        wrap.appendChild(handle);
      }

      return {
        dom: wrap,
        update: (n: PMNode) => {
          if (n.type.name !== current.type.name) return false;
          current = n;
          apply(n);
          return true;
        },
      };
    };
  },
});
