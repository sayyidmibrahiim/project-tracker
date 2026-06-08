/**
 * Registers the extensionless-resolve hook on the module loader thread.
 * Loaded via `node --import ./tests/register-hooks.mjs` before the test runner.
 */
import { register } from "node:module";

register("./extensionless-resolve.mjs", import.meta.url);
register("./svelte-loader.mjs", import.meta.url);
