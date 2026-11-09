import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const adminPassword = process.env.SENTINEL_E2E_ADMIN_PASSWORD ?? "";
const judgePassword = process.env.SENTINEL_JUDGE_PASSWORD ?? "";

test("administrator can inspect real operations state", async ({ page }) => {
  test.skip(!adminPassword, "Private administrator test credential required");
  await page.goto("/login");
  await page.getByLabel("Work email").fill("admin@northwind.example");
  await page.getByLabel("Password").fill(adminPassword);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("navigation").getByRole("link", { name: "Operations" }).click();
  await expect(page.getByRole("heading", { name: "Operations", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Worker heartbeats" })).toBeVisible();
  await expect(page.getByText("No verified merchant event recorded")).toBeVisible();
  await expect(page.getByText("Merchant scoring queue", { exact: true })).toBeVisible();
  expect((await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze()).violations).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
});

test("judge follows an isolated read-only investigation", async ({ page }) => {
  test.skip(!judgePassword, "Private viewer demo credential required");
  await page.goto("/login");
  await page.getByLabel("Work email").fill("judge@sentinel-demo.example");
  await page.getByLabel("Password").fill(judgePassword);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("navigation").getByRole("link", { name: "Demo guide" }).click();
  await expect(page.getByRole("heading", { name: "Explore SENTINEL" })).toBeVisible();
  await page.getByRole("link", { name: "Open the prepared investigation workbench" }).click();
  await expect(page.getByText(/Deterministic summary/).first()).toBeVisible();
  await expect(page.getByText("synthetic-demo-document.pdf").first()).toBeVisible();
  await expect(page.getByRole("button", { name: /upload evidence/i })).toHaveCount(0);
  expect((await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze()).violations).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
});
