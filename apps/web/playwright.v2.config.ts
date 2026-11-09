import { existsSync } from "node:fs";
import { defineConfig, devices } from "@playwright/test";
const executablePath =
  process.env.PLAYWRIGHT_CHROMIUM_PATH ??
  (existsSync("/usr/bin/chromium") ? "/usr/bin/chromium" : undefined);
export default defineConfig({
  testDir: "./e2e",
  testMatch: "v2-*.spec.ts",
  timeout: 45000,
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: process.env.SENTINEL_WEB_URL ?? "http://127.0.0.1:5175",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1440, height: 900 },
        launchOptions: executablePath ? { executablePath } : {},
      },
    },
  ],
});
