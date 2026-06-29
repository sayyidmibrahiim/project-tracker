/**
 * Minimal, dependency-free, XSS-safe Markdown → HTML renderer for the project
 * notes Preview (PRD §12.12).
 *
 * The PRD references marked.js, but the release-candidate rules forbid adding
 * dependencies, so this renders a safe Markdown subset that covers the notes
 * toolbar: headings (#/##/###), unordered lists (-/*), blockquotes (>), fenced
 * code blocks (```), inline code (`), bold (**), italic (*), and links
 * [text](url).
 *
 * Safety model: the entire input is HTML-escaped FIRST, so no raw HTML from the
 * note survives into the output. Only this renderer's own tags are emitted, and
 * link hrefs are restricted to http/https/mailto (anything else becomes "#").
 * The output is therefore safe to inject with Svelte's {@html ...}.
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

/** Render inline spans on an already-HTML-escaped line. */
function renderInline(escaped: string): string {
  let out = escaped;
  // Inline code first so its contents are not further transformed.
  out = out.replace(/`([^`]+)`/g, (_m, code) => `<code>${code}</code>`);
  // Links [label](url) — brackets/parens are not HTML-escaped, so this is safe.
  out = out.replace(
    /\[([^\]]+)\]\(([^)\s]+)\)/g,
    (_m, label, url) => `<a href="${sanitizeHref(url)}" target="_blank" rel="noopener noreferrer">${label}</a>`,
  );
  // Bold **text**.
  out = out.replace(/\*\*([^*]+)\*\*/g, (_m, t) => `<strong>${t}</strong>`);
  // Italic *text* (single asterisks that are not part of a bold run).
  out = out.replace(/(^|[^*])\*([^*\s][^*]*)\*/g, (_m, pre, t) => `${pre}<em>${t}</em>`);
  return out;
}

/** Render a Markdown subset to safe HTML. */
export function renderMarkdown(src: string): string {
  if (!src) return "";
  const escaped = escapeHtml(src);
  const lines = escaped.split(/\r?\n/);
  const out: string[] = [];
  let inList = false;
  let inCode = false;
  const codeBuf: string[] = [];

  const closeList = (): void => {
    if (inList) {
      out.push("</ul>");
      inList = false;
    }
  };

  for (const line of lines) {
    // Horizontal rule ---
    if (/^---\s*$/.test(line.trim())) {
      closeList();
      out.push('<hr />');
      continue;
    }
    // Fenced code block fences toggle raw-text capture.
    if (/^```/.test(line.trim())) {
      if (inCode) {
        out.push(`<pre><code>${codeBuf.join("\n")}</code></pre>`);
        codeBuf.length = 0;
        inCode = false;
      } else {
        closeList();
        inCode = true;
      }
      continue;
    }
    if (inCode) {
      codeBuf.push(line);
      continue;
    }

    if (/^### /.test(line)) {
      closeList();
      out.push(`<h3>${renderInline(line.slice(4))}</h3>`);
      continue;
    }
    if (/^## /.test(line)) {
      closeList();
      out.push(`<h2>${renderInline(line.slice(3))}</h2>`);
      continue;
    }
    if (/^# /.test(line)) {
      closeList();
      out.push(`<h1>${renderInline(line.slice(2))}</h1>`);
      continue;
    }
    // Blockquote: ">" was HTML-escaped to "&gt;".
    if (/^&gt; /.test(line)) {
      closeList();
      out.push(`<blockquote>${renderInline(line.slice(5))}</blockquote>`);
      continue;
    }
    if (/^\s*[-*] \[[xX ]\] /.test(line)) {
      closeList();
      const checked = /^\s*[-*] \[[xX]\] /.test(line);
      const content = line.replace(/^\s*[-*] \[[xX ]\] /, "");
      out.push(`<div class="ne-todo-item"><input type="checkbox" class="ne-todo-checkbox"${checked ? " checked" : ""} /> <span>${renderInline(content)}</span></div>`);
      continue;
    }
    if (/^\s*[-*] /.test(line)) {
      if (!inList) {
        out.push("<ul>");
        inList = true;
      }
      out.push(`<li>${renderInline(line.replace(/^\s*[-*] /, ""))}</li>`);
      continue;
    }
    if (line.trim() === "") {
      closeList();
      continue;
    }
    closeList();
    out.push(`<p>${renderInline(line)}</p>`);
  }

  if (inCode) {
    out.push(`<pre><code>${codeBuf.join("\n")}</code></pre>`);
  }
  closeList();
  return out.join("\n");
}
