/**
 * Dependency-free Markdown → HTML renderer for the project notes editor
 * (PRD §12.12). Loaded into the NotesEditor contenteditable, so its output
 * must round-trip stably through domToMarkdown → notes.md → reload.
 *
 * Renders the toolbar's Markdown subset — headings (#/##/###), ordered and
 * unordered lists, blockquotes (>), fenced (```) and inline (`) code,
 * checkboxes (- [x]), bold (**), italic (*), strikethrough (~~), images
 * (![alt](src)), links [text](url), pipe tables, and horizontal rules (---).
 *
 * Safety model — selective sanitization (not escape-first):
 *   1. Fenced code blocks are lifted out first and their content is escaped, so
 *      tags inside code are shown literally.
 *   2. A whitelist of formatting tags (u, sub, sup, s, strike, span, div, p,
 *      font, img, pre, code, a, table, …) is recognized and sanitized in place
 *      (attributes restricted per tag; style/href/src sanitized). Whitelisted
 *      tags are held as placeholders while everything else is escaped.
 *   3. Non-whitelisted tags (script, iframe, object, …) are NOT recognized, so
 *      they fall through to escapeHtml and render as literal text — raw markup
 *      cannot be injected. Link hrefs are restricted to http/https/mailto and
 *      image srcs to http/https/data:image; anything else collapses.
 * The output is therefore safe to inject via {@html ...} / innerHTML.
 */

/** Escape the five HTML-significant characters. */
export function escapeHtml(input: string): string {
  return input
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Allow only http/https/mailto hrefs; everything else collapses to "#". */
function sanitizeHref(rawUrl: string): string {
  const url = rawUrl.trim();
  if (/^(https?:|mailto:)/i.test(url)) {
    return url;
  }
  return "#";
}

/** Relative RTE asset reference (D-0012): .rte/assets/<16-hex-id>.<ext>.
 *  The fixed shape admits no separators or dots beyond the extension, so
 *  path traversal cannot be expressed. */
const RTE_ASSET_SRC = /^\.rte\/assets\/[0-9a-f]{16}\.(png|jpe?g|gif|webp)$/;

/** Allow http/https/data:image srcs plus relative RTE asset refs. */
function sanitizeImgSrc(rawUrl: string): string {
  const url = rawUrl.trim();
  if (/^(https?:|data:image\/)/i.test(url) || RTE_ASSET_SRC.test(url)) {
    return url;
  }
  return "";
}

/** CSS properties considered safe to preserve on inline style attributes. */
const SAFE_STYLE_PROPS =
  /^(color|background-color|background|font-size|font-family|font-weight|font-style|text-align|text-decoration|vertical-align|line-height)$/i;

/**
 * Reduce an inline `style="…"` value to a safe declaration list. Drops the
 * whole style if it contains script-injection vectors (url(), expression(),
 * javascript:, @import, behavior:), then keeps only allow-listed properties.
 */
function sanitizeStyle(css: string): string {
  if (/\burl\s*\(|expression\s*\(|javascript:|@import|behavior\s*:/i.test(css)) {
    return "";
  }
  const out: string[] = [];
  for (const rawDecl of css.split(";")) {
    const decl = rawDecl.trim();
    if (!decl) continue;
    const idx = decl.indexOf(":");
    if (idx < 0) continue;
    const prop = decl.slice(0, idx).trim().toLowerCase();
    const val = decl.slice(idx + 1).trim();
    if (SAFE_STYLE_PROPS.test(prop)) {
      out.push(`${prop}: ${val}`);
    }
  }
  return out.join("; ");
}

/** Tags that may pass through (after attribute sanitization). */
const ALLOWED_TAGS = new Set([
  "u", "sub", "sup", "s", "strike", "code", "pre", "span", "div", "p", "font",
  "img", "br", "hr", "b", "strong", "em", "i", "blockquote", "a", "table",
  "thead", "tbody", "tr", "th", "td",
  // Tiptap task-list nodes (data-type distinguishes them from plain lists).
  "ul", "ol", "li", "label",
]);

/** Block-level tags: a line opening with one of these is emitted verbatim. */
const BLOCK_TAGS = new Set([
  "p", "div", "pre", "blockquote", "table", "thead", "tbody", "tr", "th", "td",
  "hr",
]);

/** Per-tag attribute allow-list. Unlisted tags get the default set. */
const TAG_ATTRS: Record<string, Set<string>> = {
  a: new Set(["href"]),
  img: new Set(["src", "alt", "style", "width", "data-asset-src", "data-asset-id"]),
  span: new Set(["style"]),
  div: new Set(["style", "align"]),
  p: new Set(["style", "align"]),
  font: new Set(["color", "face", "size"]),
  td: new Set(["style", "align", "colspan", "rowspan"]),
  th: new Set(["style", "align", "colspan", "rowspan"]),
  // Tiptap task-list shape: <ul data-type="taskList"><li data-type="taskItem" data-checked>…</li></ul>
  ul: new Set(["data-type", "style"]),
  ol: new Set(["start", "style"]),
  li: new Set(["data-type", "data-checked", "style"]),
  label: new Set([]),
};
const DEFAULT_ATTRS = new Set(["style", "align"]);

/** Sanitize a single attribute value by name. Empty string means "drop". */
function sanitizeAttr(name: string, val: string): string {
  if (name === "href") return sanitizeHref(val);
  if (name === "src") return sanitizeImgSrc(val);
  if (name === "style") return sanitizeStyle(val);
  // Plain attributes: keep, but neutralize quote/angle-break characters.
  return val.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/** Tags that render as void/self-closing elements. */
const VOID_TAGS = new Set(["br", "img", "hr"]);

/**
 * Parse a raw `<…>` token. Returns the sanitized HTML string for whitelisted
 * tags, or null when the tag is not allowed (so the caller leaves it to be
 * escaped — keeping non-whitelisted tags like <script> inert).
 */
function sanitizeTag(raw: string): { html: string; tag: string } | null {
  const closing = /^<\s*\//.test(raw);
  const m = raw.match(/^<\s*\/?\s*([a-zA-Z][a-zA-Z0-9]*)/);
  if (!m) return null;
  const tag = m[1].toLowerCase();
  if (!ALLOWED_TAGS.has(tag)) return null;
  if (closing) return { html: `</${tag}>`, tag };
  if (VOID_TAGS.has(tag)) {
    const allowed = TAG_ATTRS[tag] || DEFAULT_ATTRS;
    const attrs = parseAttrs(raw, allowed, tag);
    return { html: `<${tag}${attrs}>`, tag };
  }
  const allowed = TAG_ATTRS[tag] || DEFAULT_ATTRS;
  const attrs = parseAttrs(raw, allowed, tag);
  return { html: `<${tag}${attrs}>`, tag };
}

/** Extract and sanitize the allowed attributes from an opening tag. */
function parseAttrs(raw: string, allowed: Set<string>, tag: string): string {
  const out: string[] = [];
  const attrRe = /([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))/g;
  let am: RegExpExecArray | null;
  let hasAlt = false;
  let hasSrc = false;
  while ((am = attrRe.exec(raw)) !== null) {
    const name = am[1].toLowerCase();
    const val = am[2] ?? am[3] ?? am[4] ?? "";
    if (!allowed.has(name)) continue;
    if (name === "alt") hasAlt = true;
    if (name === "src") hasSrc = true;
    const sval = sanitizeAttr(name, val);
    if (sval || name === "alt") out.push(`${name}="${sval}"`);
  }
  // <img> must always carry alt and a valid src.
  if (tag === "img") {
    if (!hasAlt) out.push('alt=""');
    if (!hasSrc) return ""; // an image with no usable src is dropped entirely
  }
  return out.length ? " " + out.join(" ") : "";
}

/** A protected token restored verbatim at the end of rendering. */
interface Placeholder {
  html: string;
  tag: string;
  /** True for code blocks: emit the line untouched (no inline parsing). */
  opaque: boolean;
}

/** Lift fenced code blocks out first so tags inside them are shown literally. */
function liftCodeFences(src: string, placeholders: Placeholder[]): string {
  return src.replace(/```[^\n`]*\n?([\s\S]*?)```/g, (_m, content: string) => {
    const body = content.replace(/^\n/, "").replace(/\n$/, "");
    placeholders.push({ html: `<pre><code>${escapeHtml(body)}</code></pre>`, tag: "pre", opaque: true });
    return `\u0000${placeholders.length - 1}\u0000`;
  });
}

/** Replace whitelisted HTML tags with placeholders; leave others to be escaped. */
function protectHtml(src: string, placeholders: Placeholder[]): string {
  const tagRe = /<[\/!]?[a-zA-Z][^>]*>/g;
  return src.replace(tagRe, (whole) => {
    const res = sanitizeTag(whole);
    if (!res) return whole; // not whitelisted → survives escapeHtml below
    placeholders.push({ html: res.html, tag: res.tag, opaque: false });
    return `\u0000${placeholders.length - 1}\u0000`;
  });
}

/** Render inline spans on an already-HTML-escaped line. Placeholders survive. */
function renderInline(escaped: string): string {
  let out = escaped;
  // Inline code first so its contents are not further transformed.
  out = out.replace(/`([^`]+)`/g, (_m, code) => `<code>${code}</code>`);
  // Images ![alt](url) — before links so the `!` prefix is consumed here.
  // Relative asset refs additionally carry data-asset-src so the editor's
  // AssetImage node keeps the stable reference while src gets hydrated to a
  // data URI for display (D-0012).
  out = out.replace(
    /!\[([^\]]*)\]\(([^)\s]+)\)/g,
    (_m, alt, url) => {
      const src = sanitizeImgSrc(url);
      const assetAttr = RTE_ASSET_SRC.test(src) ? ` data-asset-src="${src}"` : "";
      return `<img src="${src}" alt="${alt}"${assetAttr} />`;
    },
  );
  // Links [label](url) — brackets/parens are not HTML-escaped, so this is safe.
  out = out.replace(
    /\[([^\]]+)\]\(([^)\s]+)\)/g,
    (_m, label, url) => `<a href="${sanitizeHref(url)}" target="_blank" rel="noopener noreferrer">${label}</a>`,
  );
  // Bold **text**.
  out = out.replace(/\*\*([^*]+)\*\*/g, (_m, t) => `<strong>${t}</strong>`);
  // Italic *text* (single asterisks that are not part of a bold run).
  out = out.replace(/(^|[^*])\*([^*\s][^*]*)\*/g, (_m, pre, t) => `${pre}<em>${t}</em>`);
  // Strikethrough ~~text~~.
  out = out.replace(/~~([^~]+)~~/g, (_m, t) => `<s>${t}</s>`);
  return out;
}

/** Collapse a run of pipe-table lines into a <table>; returns "" if not a table. */
function renderPipeTable(tableLines: string[]): string {
  // Split each `| … |` line into trimmed cells, dropping the empty ends.
  const splitRow = (line: string): string[] =>
    line.replace(/^\s*\|/, "").replace(/\|\s*$/, "").split("|").map((c) => renderInline(c.trim()));
  // A separator row is made only of `-`, `:`, spaces and pipes.
  const isSeparator = (line: string): boolean =>
    /^\s*\|?[\s:|-]*-[\s:|-]*\|?\s*$/.test(line) && line.includes("-");

  const rows: string[][] = [];
  let headerIdx = -1;
  tableLines.forEach((line, i) => {
    if (isSeparator(line)) {
      if (headerIdx === -1) headerIdx = rows.length === 0 ? 0 : rows.length - 1;
      return; // separator lines are consumed, not rendered
    }
    rows.push(splitRow(line));
  });

  if (rows.length === 0) return "";
  const hasHeader = headerIdx >= 0 && rows.length > 1;
  const header = hasHeader ? rows[0] : [];
  const body = hasHeader ? rows.slice(1) : rows;

  const wrapCell = (cells: string[], tag: "th" | "td"): string =>
    `<tr>${cells.map((c) => `<${tag}>${c}</${tag}>`).join("")}</tr>`;

  let html = "<table>";
  if (hasHeader) {
    html += `<thead>${wrapCell(header, "th")}</thead>`;
  }
  if (body.length) {
    html += `<tbody>${body.map((r) => wrapCell(r, "td")).join("")}</tbody>`;
  }
  html += "</table>";
  return html;
}

/** Render a Markdown subset to safe HTML. */
export function renderMarkdown(src: string): string {
  if (!src) return "";

  const placeholders: Placeholder[] = [];
  // 1. Lift fenced code blocks (their content is escaped, never tag-parsed).
  let work = liftCodeFences(src, placeholders);
  // 2. Protect whitelisted HTML tags; non-whitelisted tags remain for escaping.
  work = protectHtml(work, placeholders);
  // 3. Escape everything still standing (placeholders use \u0000 and survive).
  const escaped = escapeHtml(work);
  const lines = escaped.split(/\r?\n/);
  const out: string[] = [];
  let ulOpen = false;
  let olOpen = false;

  const closeLists = (): void => {
    if (ulOpen) { out.push("</ul>"); ulOpen = false; }
    if (olOpen) { out.push("</ol>"); olOpen = false; }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Opaque block (a lifted code fence): emit untouched.
    const opaqueM = line.match(/^\u0000(\d+)\u0000$/);
    if (opaqueM) {
      const ph = placeholders[Number(opaqueM[1])];
      if (ph?.opaque) { closeLists(); out.push(ph.html); continue; }
    }

    // Horizontal rule ---
    if (/^---\s*$/.test(line.trim())) { closeLists(); out.push("<hr />"); continue; }
    // Leftover (unmatched) fence — render literally rather than mis-parsing.
    if (/^```/.test(line.trim())) { closeLists(); out.push("<p>```</p>"); continue; }

    // Pipe table: a run of consecutive `| … |` lines.
    if (/^\s*\|.*\|\s*$/.test(line)) {
      const tableLines: string[] = [];
      while (i < lines.length && /^\s*\|.*\|\s*$/.test(lines[i])) {
        tableLines.push(lines[i]);
        i++;
      }
      i--; // undo the overshoot so the outer loop advances past the block
      closeLists();
      out.push(renderPipeTable(tableLines));
      continue;
    }

    if (/^### /.test(line)) { closeLists(); out.push(`<h3>${renderInline(line.slice(4))}</h3>`); continue; }
    if (/^## /.test(line)) { closeLists(); out.push(`<h2>${renderInline(line.slice(3))}</h2>`); continue; }
    if (/^# /.test(line)) { closeLists(); out.push(`<h1>${renderInline(line.slice(2))}</h1>`); continue; }
    // Blockquote: ">" was HTML-escaped to "&gt;".
    if (/^&gt; /.test(line)) { closeLists(); out.push(`<blockquote>${renderInline(line.slice(5))}</blockquote>`); continue; }
    if (/^\s*[-*] \[[xX ]\] /.test(line)) {
      closeLists();
      const checked = /^\s*[-*] \[[xX]\] /.test(line);
      const content = line.replace(/^\s*[-*] \[[xX ]\] /, "");
      // Emit Tiptap's native task-list shape so the load path round-trips
      // cleanly into the editor's TaskList/TaskItem nodes (DECISIONS D-0007).
      out.push(`<ul data-type="taskList"><li data-type="taskItem" data-checked="${checked ? "true" : "false"}"><label><input type="checkbox"${checked ? " checked" : ""} /><span></span></label><div>${renderInline(content) || "<br>"}</div></li></ul>`);
      continue;
    }
    if (/^\s*[-*] /.test(line)) {
      if (olOpen) { out.push("</ol>"); olOpen = false; }
      if (!ulOpen) { out.push("<ul>"); ulOpen = true; }
      out.push(`<li>${renderInline(line.replace(/^\s*[-*] /, ""))}</li>`);
      continue;
    }
    if (/^\s*\d+\.\s/.test(line)) {
      if (ulOpen) { out.push("</ul>"); ulOpen = false; }
      if (!olOpen) { out.push("<ol>"); olOpen = true; }
      out.push(`<li>${renderInline(line.replace(/^\s*\d+\.\s/, ""))}</li>`);
      continue;
    }
    if (line.trim() === "") { closeLists(); continue; }

    // Raw HTML block line (e.g. aligned <p>/<div>): starts with a block open tag.
    const blkM = line.match(/^\u0000(\d+)\u0000/);
    if (blkM) {
      const ph = placeholders[Number(blkM[1])];
      if (ph && BLOCK_TAGS.has(ph.tag)) { closeLists(); out.push(renderInline(line)); continue; }
    }

    closeLists();
    out.push(`<p>${renderInline(line)}</p>`);
  }

  closeLists();
  let result = out.join("\n");
  // 4. Restore protected tags (and code blocks) into the final HTML.
  result = result.replace(/\u0000(\d+)\u0000/g, (_m, idxStr) => {
    const ph = placeholders[Number(idxStr)];
    return ph ? ph.html : "";
  });
  return result;
}

/** Escape characters that would break a markdown/HTML attribute value. */
function escapeMarkdownAttr(value: string): string {
  return value.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
}

function decodeHtmlEntities(value: string): string {
  return value
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"');
}

function stripHtmlTags(value: string): string {
  return decodeHtmlEntities(value.replace(/<[^>]+>/g, "")).trim();
}

function domNodeToMarkdown(node: Node): string {
  if (node.nodeType === Node.TEXT_NODE) return node.textContent || "";
  if (node.nodeType !== Node.ELEMENT_NODE) return "";
  const el = node as HTMLElement;
  const tag = el.tagName.toLowerCase();
  if (el.dataset.type === "taskItem") {
    const checked = el.dataset.checked === "true";
    const ch = checked ? "x" : " ";
    const contentEl = el.querySelector("div") || el;
    const text = Array.from(contentEl.childNodes).map(domNodeToMarkdown).join("").trim();
    return `- [${ch}] ${text}\n`;
  }
  const children = Array.from(el.childNodes).map(domNodeToMarkdown).join("");
  switch (tag) {
    case "h1": return `# ${children.trim()}\n\n`;
    case "h2": return `## ${children.trim()}\n\n`;
    case "h3": return `### ${children.trim()}\n\n`;
    case "blockquote": return `> ${children.trim()}\n\n`;
    case "li": return `${el.parentElement?.tagName === "OL" ? "1." : "-"} ${children.trim()}\n`;
    case "ol":
    case "ul": return `${children}\n`;
    case "strong":
    case "b": return `**${children}**`;
    case "em":
    case "i": return `*${children}*`;
    case "u": return `<u>${children}</u>`;
    case "s":
    case "strike": return `~~${children}~~`;
    case "sub": return `<sub>${children}</sub>`;
    case "sup": return `<sup>${children}</sup>`;
    case "pre": return "```\n" + (el.textContent || "") + "\n```\n\n";
    case "code": return `\`${children}\``;
    case "a": return `[${children}](${el.getAttribute("href") || ""})`;
    case "p": return `${children.trim()}\n\n`;
    case "div": return `${children}\n`;
    case "hr": return "---\n\n";
    case "br": return "\n";
    // Asset-backed images serialize their stable relative ref, never the
    // (large, display-only) data-URI src (D-0012).
    case "img": {
      const src = el.getAttribute("data-asset-src") || el.getAttribute("src") || "";
      const alt = el.getAttribute("alt") || "";
      const width = el.getAttribute("width") || "";
      // Markdown image syntax cannot hold a width, so resized images
      // round-trip as whitelisted inline HTML instead.
      if (/^\d+$/.test(width)) return `<img src="${src}" alt="${escapeMarkdownAttr(alt)}" width="${width}" />`;
      return `![${alt}](${src})`;
    }
    case "table": {
      const rows = Array.from(el.querySelectorAll("tr"));
      if (rows.length === 0) return children;
      const cellText = (cell: Element) => (cell.textContent || "").replace(/\|/g, "\\|").trim();
      const rowText = (row: Element) => `| ${Array.from(row.querySelectorAll("td,th")).map(cellText).join(" | ")} |`;
      const header = rows[0];
      const cols = header.querySelectorAll("td,th").length || 1;
      const sep = `| ${Array.from({ length: cols }, () => "---").join(" | ")} |`;
      const body = rows.slice(1).map(rowText).join("\n");
      return `${rowText(header)}\n${sep}${body ? "\n" + body : ""}\n\n`;
    }
    case "tr":
    case "td":
    case "th":
    case "tbody":
    case "thead": return children;
    case "font": {
      const attrs: string[] = [];
      const color = el.getAttribute("color");
      const face = el.getAttribute("face");
      if (color) attrs.push(`color="${escapeMarkdownAttr(color)}"`);
      if (face) attrs.push(`face="${escapeMarkdownAttr(face)}"`);
      return attrs.length ? `<font ${attrs.join(" ")}>${children}</font>` : children;
    }
    case "span": {
      const style = el.getAttribute("style") || "";
      return style.trim() ? `<span style="${escapeMarkdownAttr(style)}">${children}</span>` : children;
    }
    case "mark": {
      const color = el.getAttribute("data-color") || el.style.backgroundColor;
      return color ? `<span style="background-color:${escapeMarkdownAttr(color)}">${children}</span>` : children;
    }
    default: return children;
  }
}

function fallbackHtmlToMarkdown(html: string): string {
  // Inline-HTML img output (resized images) must survive the final
  // strip-all-tags pass, so it is tokenized and restored at the end.
  const keepImgs: string[] = [];
  return html
    .replace(/<pre[^>]*>\s*<code[^>]*>([\s\S]*?)<\/code>\s*<\/pre>/gi, (_m, code) => `\n\n\`\`\`\n${stripHtmlTags(code)}\n\`\`\`\n\n`)
    .replace(/<li[^>]*data-type=["']taskItem["'][^>]*data-checked=["'](true|false)["'][^>]*>([\s\S]*?)<\/li>/gi, (_m, checked, body) => `\n- [${checked === "true" ? "x" : " "}] ${stripHtmlTags(body)}\n`)
    .replace(/<table[^>]*>([\s\S]*?)<\/table>/gi, (_m, table) => {
      const tableHtml = String(table);
      const rows = Array.from(tableHtml.matchAll(/<tr[^>]*>([\s\S]*?)<\/tr>/gi)).map((row) =>
        Array.from(String(row[1]).matchAll(/<t[dh][^>]*>([\s\S]*?)<\/t[dh]>/gi)).map((cell) => stripHtmlTags(String(cell[1]))),
      );
      if (rows.length === 0) return "";
      const rowText = (row: string[]) => `| ${row.join(" | ")} |`;
      return `\n${rowText(rows[0])}\n| ${rows[0].map(() => "---").join(" | ")} |${rows.slice(1).map((row) => `\n${rowText(row)}`).join("")}\n\n`;
    })
    .replace(/<h1[^>]*>([\s\S]*?)<\/h1>/gi, (_m, text) => `\n# ${stripHtmlTags(text)}\n\n`)
    .replace(/<h2[^>]*>([\s\S]*?)<\/h2>/gi, (_m, text) => `\n## ${stripHtmlTags(text)}\n\n`)
    .replace(/<h3[^>]*>([\s\S]*?)<\/h3>/gi, (_m, text) => `\n### ${stripHtmlTags(text)}\n\n`)
    .replace(/<img\b([^>]*)>/gi, (_m, attrs) => {
      const assetSrc = attrs.match(/data-asset-src=["']([^"']*)["']/i)?.[1] || "";
      const src = assetSrc || attrs.match(/src=["']([^"']*)["']/i)?.[1] || "";
      const alt = attrs.match(/alt=["']([^"']*)["']/i)?.[1] || "";
      const width = attrs.match(/width=["'](\d+)["']/i)?.[1] || "";
      if (width) {
        keepImgs.push(`<img src="${src}" alt="${alt}" width="${width}" />`);
        return `\u0000K${keepImgs.length - 1}\u0000`;
      }
      return `![${alt}](${src})`;
    })
    .replace(/<a\b[^>]*href=["']([^"']*)["'][^>]*>([\s\S]*?)<\/a>/gi, (_m, href, text) => `[${stripHtmlTags(text)}](${href})`)
    .replace(/<ul(?![^>]*data-type=["']taskList["'])[^>]*>([\s\S]*?)<\/ul>/gi, (_m, list) =>
      Array.from(String(list).matchAll(/<li[^>]*>([\s\S]*?)<\/li>/gi)).map((item) => `- ${stripHtmlTags(String(item[1]))}`).join("\n") + "\n",
    )
    .replace(/<ol[^>]*>([\s\S]*?)<\/ol>/gi, (_m, list) =>
      Array.from(String(list).matchAll(/<li[^>]*>([\s\S]*?)<\/li>/gi)).map((item) => `1. ${stripHtmlTags(String(item[1]))}`).join("\n") + "\n",
    )
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<\/p>|<\/div>/gi, "\n\n")
    .replace(/<[^>]+>/g, "")
    .replace(/\u0000K(\d+)\u0000/g, (_m, i) => keepImgs[Number(i)] ?? "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

/** Serialize Tiptap/editor HTML back to the supported notes.md Markdown subset. */
export function htmlToMarkdown(html: string): string {
  if (!html) return "";
  if (typeof DOMParser === "undefined") return fallbackHtmlToMarkdown(html);
  const doc = new DOMParser().parseFromString(html, "text/html");
  let markdown = Array.from(doc.body.childNodes).map(domNodeToMarkdown).join("");
  markdown = markdown.replace(/\n{3,}/g, "\n\n");
  return markdown.trim();
}
