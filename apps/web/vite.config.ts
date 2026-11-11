import { execFileSync } from "node:child_process";
import { cpSync, mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath, URL } from "node:url";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, type Plugin } from "vitest/config";

const apiTarget = process.env.SENTINEL_API_URL ?? "http://127.0.0.1:8000";

export default defineConfig({
  // GitHub Pages serves the static demo from /<repo>/ (see .github/workflows/pages.yml).
  base: process.env.SENTINEL_WEB_BASE ?? "/",
  plugins: [react(), tailwindcss(), staticSnapshot()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
      "@contracts": fileURLToPath(
        new URL("../../packages/contracts", import.meta.url),
      ),
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

/** Fail closed before emitting static assets; use the exporter's dependency-free gate. */
function staticSnapshot(): Plugin {
  let output = "";
  let snapshot = "";
  const validator = fileURLToPath(
    new URL("../api/scripts/validate_static_demo.py", import.meta.url),
  );
  return {
    name: "validated-static-snapshot",
    apply: "build",
    configResolved(config) {
      if (config.env.VITE_STATIC_DEMO !== "true") return;
      snapshot = process.env.SENTINEL_STATIC_SNAPSHOT_DIR ?? "";
      if (!snapshot)
        throw new Error(
          "Static builds require SENTINEL_STATIC_SNAPSHOT_DIR pointing to an approved export",
        );
      snapshot = resolve(snapshot);
      output = resolve(config.root, config.build.outDir, "demo-data");
    },
    buildStart() {
      if (snapshot)
        execFileSync(
          process.env.SENTINEL_PYTHON ?? "python3",
          [validator, snapshot],
          { stdio: "inherit" },
        );
    },
    writeBundle() {
      if (!snapshot) return;
      mkdirSync(output, { recursive: true });
      cpSync(snapshot, output, { recursive: true });
      execFileSync(
        process.env.SENTINEL_PYTHON ?? "python3",
        [validator, output],
        { stdio: "inherit" },
      );
    },
  };
}
