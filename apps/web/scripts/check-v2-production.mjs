import assert from "node:assert/strict";
import { existsSync, mkdirSync, readdirSync, writeFileSync } from "node:fs";
import { chromium } from "@playwright/test";
const output = process.env.SENTINEL_V2_ARTIFACTS ?? "test-results/v2-artifacts";
mkdirSync(output, { recursive: true });
const executablePath =
  process.env.PLAYWRIGHT_CHROMIUM_PATH ??
  (existsSync("/usr/bin/chromium") ? "/usr/bin/chromium" : undefined);
const browser = await chromium.launch(executablePath ? { executablePath } : {});
const page = await browser.newPage();
const requests = [];
const errors = [];
page.on("request", (r) => requests.push(r.url()));
page.on("pageerror", (e) => errors.push(e.message));
await page.goto("http://127.0.0.1:4175/__v2-preview");
await page
  .getByRole("heading", { name: "Sign in to your workspace" })
  .waitFor();
const previewRoots = await page.locator(".v2-preview").count();
const previewRequests = requests.filter((u) =>
  /Preview|Story|Dossier|gsap|space-grotesk|jetbrains|inter-latin|manrope|dm-sans|Wallet|MoneyStory|CommandCenter|ReceiptMorph/.test(u),
);
const previewAssets = readdirSync("dist/assets").filter((n) =>
  /Preview|Story|Dossier|gsap|space-grotesk|jetbrains|inter-latin|manrope|dm-sans|Wallet|MoneyStory|CommandCenter|ReceiptMorph/.test(n),
);
const staticPreviewAssets = readdirSync(
  (process.env.SENTINEL_V2_STATIC_DIST ?? "dist-static") + "/assets",
).filter((n) =>
  /Preview|Story|Dossier|gsap|space-grotesk|jetbrains|inter-latin|manrope|dm-sans|Wallet|MoneyStory|CommandCenter|ReceiptMorph/.test(n),
);
assert.equal(previewRoots, 0);
assert.deepEqual(previewRequests, []);
assert.deepEqual(previewAssets, []);
assert.deepEqual(staticPreviewAssets, []);
assert.deepEqual(errors, []);
const results = {
  previewRoots,
  previewRequests,
  previewAssets,
  staticPreviewAssets,
  errors,
};
writeFileSync(
  `${output}/production-isolation.json`,
  JSON.stringify(results, null, 2),
);
console.log(results);
await browser.close();
