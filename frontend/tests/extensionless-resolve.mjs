/**
 * Dependency-free Node module-resolution hook for the test runner.
 *
 * Source files under `src/` use extensionless relative imports (e.g.
 * `import ... from "./types"`) because Vite/svelte-check resolve them with
 * bundler semantics. Node's native ESM + TypeScript stripping requires explicit
 * extensions, so a test that transitively imports such a module (like
 * `bridge.ts` → `./types`) fails to resolve under a bare `node --test`.
 *
 * This hook adds a bundler-like fallback: when a relative specifier has no
 * extension and does not resolve as-is, it retries with `.ts`, `.mts`, `.js`,
 * and `.mjs`. Bare specifiers (`node:test`, `svelte/compiler`, …) and already
 * extensioned specifiers are left untouched. No dependencies are added.
 *
 * Registered via `tests/register-hooks.mjs` (see `npm test`).
 */
import { existsSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { dirname, resolve as resolvePath } from "node:path";

const CANDIDATE_EXTENSIONS = [".ts", ".mts", ".js", ".mjs"];

function hasExtension(specifier) {
  // Treat a trailing ".<letters>" segment as an explicit extension.
  return /\.[a-z]+$/i.test(specifier);
}

export async function resolve(specifier, context, nextResolve) {
  const isRelative = specifier.startsWith("./") || specifier.startsWith("../");
  if (isRelative && !hasExtension(specifier) && context.parentURL) {
    const parentPath = fileURLToPath(context.parentURL);
    const base = resolvePath(dirname(parentPath), specifier);
    for (const ext of CANDIDATE_EXTENSIONS) {
      if (existsSync(base + ext)) {
        return nextResolve(pathToFileURL(base + ext).href, context);
      }
    }
  }
  return nextResolve(specifier, context);
}
