import { fileURLToPath, URL } from "node:url";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const apiTarget = process.env.SENTINEL_API_URL ?? "http://127.0.0.1:8000";

export default defineConfig({
  // GitHub Pages serves the static demo from /<repo>/ (see .github/workflows/pages.yml).
  base: process.env.SENTINEL_WEB_BASE ?? "/",
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
      "@contracts": fileURLToPath(new URL("../../packages/contracts", import.meta.url)),
    },
  },
  server: {
    port: 5173,
    // Same-origin API in development so session cookies stay first-party.
    proxy: { "/api": { target: apiTarget, changeOrigin: false } },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    css: false,
  },
});
