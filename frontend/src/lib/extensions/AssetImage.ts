// Image node with stable asset identity for the DOCX pipeline (D-0012).
//
// Extends the stock Tiptap Image extension with two attributes:
//   assetId  — content hash id of the stored asset file (16 hex chars)
//   assetSrc — path relative to the document folder (.rte/assets/<id>.<ext>);
//              markdown serialization prefers this over the (data URI) src.
// `src` stays a data URI for display, exactly like the legacy embed path, so
// existing base64 images keep working unchanged.

import Image from "@tiptap/extension-image";

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
    };
  },
});
