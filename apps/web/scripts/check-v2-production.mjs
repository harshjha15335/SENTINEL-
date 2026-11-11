// Phase 2 deliberately promotes the approved experience; experimental previews remain retired.
import assert from "node:assert/strict";
import { existsSync, mkdirSync, readdirSync, writeFileSync } from "node:fs";
import { chromium } from "@playwright/test";
const output = process.env.SENTINEL_V2_ARTIFACTS ?? "test-results/v2-artifacts";
mkdirSync(output, { recursive: true });
const origin = process.env.SENTINEL_WEB_URL ?? "http://127.0.0.1:4175";
const browser = await chromium.launch({
  executablePath: existsSync("/usr/bin/chromium")
    ? "/usr/bin/chromium"
    : undefined,
});
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [],
  requests = [];
page.on("pageerror", (e) => errors.push(e.message));
page.on("request", (r) => {
  if (r.url().includes("/api/")) requests.push(r.url());
});
await page.goto(origin + "/");
await page.locator(".v2-story").waitFor();
assert.equal((await page.locator(".v2-wallet").count()) > 0, true);
await page.goto(origin + "/demo-payment");
await page
  .getByRole("heading", { name: "Payment dossier.", exact: true })
  .waitFor();
assert.deepEqual(
  requests,
  [],
  "Public experience must not read merchant services",
);
await page.goto(origin + "/app");
await page
  .getByRole("heading", { name: "Sign in to your workspace" })
  .waitFor();
assert.equal(await page.locator(".workspace-main").count(), 0);
await page.goto(origin + "/__v2-preview");
await page.getByRole("heading", { name: /That page has moved/i }).waitFor();
assert.equal(await page.locator(".v2-preview,.v2-story").count(), 0);
const assets = readdirSync("dist/assets");
assert.deepEqual(
  assets.filter((n) => /^(Preview|CommandCenter)-/.test(n)),
  [],
);
assert.deepEqual(errors, []);
const results = {
  publicMerchantRequests: 0,
  unauthenticatedApp: "sign-in",
  retiredPreview: "not-found",
  retiredPreviewChunks: 0,
  errors,
};
writeFileSync(
  `${output}/production-boundaries.json`,
  JSON.stringify(results, null, 2),
);
console.log(JSON.stringify(results));
await browser.close();
