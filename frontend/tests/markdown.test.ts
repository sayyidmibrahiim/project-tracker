/**
 * Unit tests for the dependency-free Markdown renderer used by the notes
 * Preview (PRD §12.12). Focus areas: the Markdown subset and — critically — the
 * XSS-safety contract (input is HTML-escaped first; only safe hrefs survive).
 *
 * Runs under `node --test` with native TypeScript type stripping (Node 24).
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import { renderMarkdown, escapeHtml } from "../src/lib/markdown.ts";

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
