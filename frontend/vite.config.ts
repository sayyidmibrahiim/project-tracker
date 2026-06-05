import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [tailwindcss(), svelte()],

  build: {
    outDir: "../web/static",
    emptyOutDir: true,
  },

  server: {
    port: 5173,
    strictPort: true,
  },
});
