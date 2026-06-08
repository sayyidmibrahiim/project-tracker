/**
 * Dependency-free Svelte 5 SSR render helper for component tests (Task 1.4).
 *
 * No DOM testing library (jsdom / @testing-library) is installed and the
 * release-candidate rules forbid adding dependencies, so component markup is
 * verified by compiling each `.svelte` file with the bundled `svelte/compiler`
 * and rendering it to an HTML string via `svelte/server`.
 *
 * This file is NOT a test file (it does not match the `*.test.*` glob) and is
 * outside `src/`, so `svelte-check` and `vite build` ignore it.
 */
import { readFileSync, writeFileSync, mkdirSync, rmSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve, basename } from "node:path";
import { randomBytes } from "node:crypto";
import { compile } from "svelte/compiler";
import { render } from "svelte/server";

const __dirname = dirname(fileURLToPath(import.meta.url));
const TMP_DIR = resolve(__dirname, ".svelte-ssr-tmp");

/**
 * Compile a `.svelte` component (path relative to this file) for SSR and
 * render it with the given props, returning the rendered HTML body string.
 */
export async function renderComponent(relativeSveltePath, props) {
  mkdirSync(TMP_DIR, { recursive: true });
  const absSrc = resolve(__dirname, relativeSveltePath);
  const source = readFileSync(absSrc, "utf8");
  const name = basename(relativeSveltePath, ".svelte");
  const { js } = compile(source, { generate: "server", name });
  const outFile = resolve(TMP_DIR, `${name}.${randomBytes(4).toString("hex")}.server.js`);
  writeFileSync(outFile, js.code, "utf8");
  const mod = await import(`file://${outFile}`);
  const Component = mod.default;
  const { body } = render(Component, { props });
  return body;
}

/** Remove the temporary compiled-component directory. */
export function cleanup() {
  rmSync(TMP_DIR, { recursive: true, force: true });
}
