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

/** Allow only http/https/data:image srcs; anything else is dropped. */
function sanitizeImgSrc(rawUrl: string): string {
  const url = rawUrl.trim();
  if (/^(https?:|data:image\/)/i.test(url)) {
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
  img: new Set(["src", "alt", "style"]),
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
  out = out.replace(
    /!\[([^\]]*)\]\(([^)\s]+)\)/g,
    (_m, alt, url) => `<img src="${sanitizeImgSrc(url)}" alt="${alt}" />`,
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
