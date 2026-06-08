/**
 * Dependency-free Node load hook that compiles `.svelte` modules for SSR.
 *
 * The leaf-component tests (`components.test.mjs`) compile a single `.svelte`
 * file by hand via `ssrHelper.mjs`. That approach cannot render a component
 * that imports OTHER `.svelte` files (e.g. `ProjectTransitions.svelte` pulls in
 * `ConfirmModal.svelte` + `DisabledHint.svelte`), because Node cannot import a
 * raw `.svelte` file and the hand-written temp file breaks relative resolution.
 *
 * This hook lets a test `import` a `.svelte` component directly: any `.svelte`
 * URL is read and compiled to server JS with the bundled `svelte/compiler`,
 * and returned as an ES module. Because the module keeps its original file URL,
 * its relative imports (`./ConfirmModal.svelte`, `../bridge`, `../folderLocks`)
 * resolve against the real source tree — child `.svelte` imports recurse back
 * through this hook, and extensionless `.ts` imports are handled by
 * `extensionless-resolve.mjs`.
 *
 * Additive and non-breaking: only `.svelte` specifiers are intercepted; every
 * other module is passed through untouched. No dependencies are added.
 *
 * Registered via `tests/register-hooks.mjs` (see `npm test`).
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { basename } from "node:path";
import { compile } from "svelte/compiler";

export async function load(url, context, nextLoad) {
  if (url.endsWith(".svelte")) {
    const path = fileURLToPath(url);
    const source = readFileSync(path, "utf8");
    const name = basename(path, ".svelte");
    const { js } = compile(source, { generate: "server", name });
    return { format: "module", source: js.code, shortCircuit: true };
  }
  return nextLoad(url, context);
}
