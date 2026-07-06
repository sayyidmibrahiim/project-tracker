/**
 * Unit tests for the dependency-free Markdown renderer used by the notes
 * Preview (PRD §12.12). Focus areas: the Markdown subset and — critically — the
 * XSS-safety contract (input is HTML-escaped first; only safe hrefs survive).
 *
 * Runs under `node --test` with native TypeScript type stripping (Node 24).
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import { renderMarkdown, escapeHtml, htmlToMarkdown } from "../src/lib/markdown.ts";

test("renders headings h1/h2/h3", () => {
  assert.match(renderMarkdown("# Title"), /<h1>Title<\/h1>/);
  assert.match(renderMarkdown("## Sub"), /<h2>Sub<\/h2>/);
  assert.match(renderMarkdown("### Small"), /<h3>Small<\/h3>/);
});

test("renders bold, italic, and inline code", () => {
  assert.match(renderMarkdown("**b**"), /<strong>b<\/strong>/);
  assert.match(renderMarkdown("*i*"), /<em>i<\/em>/);
  assert.match(renderMarkdown("`c`"), /<code>c<\/code>/);
});

test("renders unordered lists", () => {
  const html = renderMarkdown("- one\n- two");
  assert.match(html, /<ul>/);
  assert.match(html, /<li>one<\/li>/);
  assert.match(html, /<li>two<\/li>/);
  assert.match(html, /<\/ul>/);
});

test("renders blockquotes and fenced code blocks", () => {
  assert.match(renderMarkdown("> quote"), /<blockquote>quote<\/blockquote>/);
  const code = renderMarkdown("```\nlet x = 1\n```");
  assert.match(code, /<pre><code>let x = 1<\/code><\/pre>/);
});

test("escapes raw HTML so notes cannot inject markup (XSS-safe)", () => {
  const html = renderMarkdown("<script>alert(1)</script>");
  assert.doesNotMatch(html, /<script>/);
  assert.match(html, /&lt;script&gt;/);
});

test("renders http links but neutralizes javascript: hrefs", () => {
  const ok = renderMarkdown("[site](https://example.com)");
  assert.match(ok, /<a href="https:\/\/example\.com"/);
  assert.match(ok, /rel="noopener noreferrer"/);

  const bad = renderMarkdown("[x](javascript:alert(1))");
  assert.match(bad, /href="#"/);
  assert.doesNotMatch(bad, /javascript:/);
});

test("escapeHtml escapes the significant characters", () => {
  assert.equal(escapeHtml(`&<>"`), "&amp;&lt;&gt;&quot;");
});

test("empty input renders empty string", () => {
  assert.equal(renderMarkdown(""), "");
});

// ── New patterns added so every toolbar format round-trips through notes.md ──

test("renders strikethrough", () => {
  assert.match(renderMarkdown("~~done~~"), /<s>done<\/s>/);
});

test("renders ordered lists", () => {
  const html = renderMarkdown("1. one\n2. two");
  assert.match(html, /<ol>/);
  assert.match(html, /<li>one<\/li>/);
  assert.match(html, /<li>two<\/li>/);
  assert.match(html, /<\/ol>/);
});

test("renders images", () => {
  assert.match(renderMarkdown("![pic](https://example.com/a.png)"), /<img src="https:\/\/example\.com\/a\.png" alt="pic" \/>/);
});

test("renders pipe tables with a header separator", () => {
  const html = renderMarkdown("| h1 | h2 |\n| --- | --- |\n| a | b |");
  assert.match(html, /<table>/);
  assert.match(html, /<thead><tr><th>h1<\/th><th>h2<\/th><\/tr><\/thead>/);
  assert.match(html, /<tbody><tr><td>a<\/td><td>b<\/td><\/tr><\/tbody>/);
});

// ── Selective sanitization: whitelisted formatting HTML passes through ──

test("passes whitelisted formatting HTML through unescaped", () => {
  assert.match(renderMarkdown("<u>under</u>"), /<u>under<\/u>/);
  assert.match(renderMarkdown("<sub>2</sub>"), /<sub>2<\/sub>/);
  assert.match(renderMarkdown("<sup>2</sup>"), /<sup>2<\/sup>/);
  assert.match(renderMarkdown("<s>old</s>"), /<s>old<\/s>/);
});

test("preserves inline style attributes on span/p", () => {
  assert.match(renderMarkdown('<span style="color:red">red</span>'), /<span style="color: red">red<\/span>/);
  assert.match(renderMarkdown('<p style="text-align:center">c</p>'), /<p style="text-align: center">c<\/p>/);
});

test("drops dangerous style tokens (url/expression/javascript)", () => {
  // The dangerous declaration must be stripped, leaving the tag inert.
  const html = renderMarkdown('<span style="background:url(javascript:alert(1))">x</span>');
  assert.doesNotMatch(html, /javascript:alert/);
  assert.doesNotMatch(html, /url\(/);
});

test("drops image src with an unsafe scheme", () => {
  const html = renderMarkdown("![x](javascript:alert(1))");
  // An img whose src is dropped is omitted entirely.
  assert.doesNotMatch(html, /javascript:/);
});

// ── XSS whitelist boundary: still escapes non-whitelisted tags ──

test("escapes <script> but passes <u> (selective, not permissive)", () => {
  const html = renderMarkdown("<script>alert(1)</script> and <u>safe</u>");
  assert.doesNotMatch(html, /<script>/);
  assert.match(html, /&lt;script&gt;/);
  assert.match(html, /<u>safe<\/u>/);
});

test("serializes Tiptap HTML headings, lists, links, code, images, tables, and tasks to markdown", () => {
  const markdown = htmlToMarkdown(`
    <h1>Title</h1>
    <ul><li>one</li></ul>
    <a href="https://example.com">site</a>
    <pre><code>let x = 1</code></pre>
    <img src="https://example.com/a.png" alt="pic">
    <table><tr><th>A</th></tr><tr><td>B</td></tr></table>
    <ul data-type="taskList"><li data-type="taskItem" data-checked="true"><div>done</div></li></ul>
  `);

  assert.match(markdown, /# Title/);
  assert.match(markdown, /- one/);
  assert.match(markdown, /\[site\]\(https:\/\/example\.com\)/);
  assert.match(markdown, /```\nlet x = 1\n```/);
  assert.match(markdown, /!\[pic\]\(https:\/\/example\.com\/a\.png\)/);
  assert.match(markdown, /\| A \|\n\| --- \|\n\| B \|/);
  assert.match(markdown, /- \[x\] done/);
});


// ── RTE asset references (D-0012): .rte/assets round-trip ──

test("asset image refs render with data-asset-src and round-trip to markdown", () => {
  const md = "![shot](.rte/assets/ab12cd34ef56ab78.png)";
  const html = renderMarkdown(md);
  assert.match(html, /<img src="\.rte\/assets\/ab12cd34ef56ab78\.png"/);
  assert.match(html, /data-asset-src="\.rte\/assets\/ab12cd34ef56ab78\.png"/);

  // Serializing an editor img that carries data-asset-src prefers the stable
  // relative ref over its (display-only) data-URI src.
  const back = htmlToMarkdown(
    '<img src="data:image/png;base64,AAAA" alt="shot" data-asset-src=".rte/assets/ab12cd34ef56ab78.png">',
  );
  assert.match(back, /!\[shot\]\(\.rte\/assets\/ab12cd34ef56ab78\.png\)/);
});

test("resized asset image refs serialize as inline HTML with width", () => {
  const back = htmlToMarkdown(
    '<img src="data:image/png;base64,AAAA" alt="shot" data-asset-src=".rte/assets/ab12cd34ef56ab78.png" width="240">',
  );
  assert.equal(back, '<img src=".rte/assets/ab12cd34ef56ab78.png" alt="shot" width="240" />');
});

test("resized asset image HTML renders with a sanitized width", () => {
  const html = renderMarkdown('<img src=".rte/assets/ab12cd34ef56ab78.png" alt="shot" width="240" />');
  assert.match(html, /<img src="\.rte\/assets\/ab12cd34ef56ab78\.png" alt="shot" width="240">/);
});

test("asset image refs without width keep markdown image serialization", () => {
  const back = htmlToMarkdown(
    '<img src="data:image/png;base64,AAAA" alt="shot" data-asset-src=".rte/assets/ab12cd34ef56ab78.png">',
  );
  assert.equal(back, "![shot](.rte/assets/ab12cd34ef56ab78.png)");
});

test("base64 embeds without asset refs pass through unchanged (legacy notes)", () => {
  const back = htmlToMarkdown('<img src="data:image/png;base64,AAAA" alt="old">');
  assert.match(back, /!\[old\]\(data:image\/png;base64,AAAA\)/);
});

test("traversal and non-asset relative srcs are still dropped", () => {
  assert.match(renderMarkdown("![x](../secret.png)"), /<img src=""/);
  assert.match(renderMarkdown("![x](.rte/assets/../../x.png)"), /<img src=""/);
  assert.match(renderMarkdown("![x](.rte/assets/NOTHEX.png)"), /<img src=""/);
});
