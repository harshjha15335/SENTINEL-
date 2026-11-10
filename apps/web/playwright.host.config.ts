import { defineConfig, devices } from "@playwright/test";
const baseURL = process.env.SENTINEL_WEB_URL ?? "https://127.0.0.1:9448/";
if (!["127.0.0.1", "localhost"].includes(new URL(baseURL).hostname)) {
  throw new Error(
    "The test certificate exception is restricted to loopback; use normal TLS validation for public hosts",
  );
}
export default defineConfig({
  testDir: "./e2e",
  testMatch: [
    "static-demo.spec.ts",
    "host-preparation.spec.ts",
    "loading-stability.spec.ts",
  ],
  timeout: 90000,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL,
    ignoreHTTPSErrors: true, // Disposable local certificate only, never a public-host trust check.
    launchOptions: {
      executablePath:
        process.env.PLAYWRIGHT_CHROMIUM_PATH ?? "/usr/bin/chromium",
    },
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "desktop",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1440, height: 900 },
      },
    },
    {
      name: "mobile",
      use: { ...devices["Pixel 7"], viewport: { width: 390, height: 844 } },
    },
  ],
});
