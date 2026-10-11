import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

// The GitHub Pages build (VITE_STATIC_DEMO=true). Point SENTINEL_WEB_URL at its root, including
// the repository path, e.g. http://127.0.0.1:4173/SENTINEL-/ (see docs/DEPLOYMENT.md).
test.skip(process.env.SENTINEL_STATIC_DEMO !== "true", "SENTINEL_STATIC_DEMO=true is required");

function nav(page: Page) {
  return page.getByRole("navigation", { name: "Primary" });
}

async function audit(page: Page, name: string) {
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
  expect(results.violations, `${name}: ${results.violations.map((v) => `${v.id} (${v.nodes.length})`).join(", ")}`).toEqual([]);
}

async function noHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(1);
}

async function expectBanner(page: Page) {
  const banner = page.getByRole("note", { name: "Static demo" });
  await expect(banner).toContainText("Static demo, read only.");
  await expect(banner).toContainText("SYNTHETIC_DEMO");
  await expect(banner).toContainText("no PayPal call is made");
}

test("opens read-only without signing in, with the static demo banner", async ({ page }) => {
  await page.goto("./");
  await expect(page.getByRole("heading", { name: "Command Center" })).toBeVisible();
  await expectBanner(page);
  await expect(page.getByRole("button", { name: "Sign out" })).toHaveCount(0);
  await audit(page, "command center");
  await noHorizontalOverflow(page);
});

test("review queue, case, transaction and model card come from the snapshot", async ({ page }) => {
  await page.goto("./");
  await nav(page).getByRole("link", { name: "Review Queue" }).click();
  await expect(page.getByRole("heading", { name: "Review queue" })).toBeVisible();
  const first = page.getByRole("list", { name: "Cases" }).getByRole("link").first();
  await expect(first).toBeVisible();
  await audit(page, "review queue");
  await noHorizontalOverflow(page);

  await first.click();
  await expect(page.getByRole("heading", { name: /risk payment needs review/ })).toBeVisible();
  await expect(page.getByText("Model-generated", { exact: true })).toBeVisible();
  await expect(page.getByRole("list", { name: "Main factors behind this score" })).toBeVisible();
  // A viewer cannot act on cases, and the static build has no server to act on anyway.
  await expect(page.getByRole("button", { name: /claim/i })).toHaveCount(0);
  await expectBanner(page);
  await audit(page, "case detail");

  await nav(page).getByRole("link", { name: "Transactions" }).click();
  await expect(page.locator(".ag-row").first()).toBeVisible();
  await audit(page, "transactions");

  await nav(page).getByRole("link", { name: "Risk Model" }).click();
  await expect(page.getByText("Trained and tested on synthetic data only.")).toBeVisible();
  await audit(page, "risk model");
});

test("deep links load through the Pages 404 fallback", async ({ page }) => {
  await page.goto("./model");
  await expect(page.getByRole("heading", { name: "Risk model" })).toBeVisible();
  await page.goto("./cases/00000000-0000-0000-0000-000000000000");
  await expect(page.getByText(/not found/i).first()).toBeVisible();
});
