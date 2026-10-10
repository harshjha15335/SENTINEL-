import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const ANALYST = { email: "analyst@northwind.example", password: process.env.SENTINEL_E2E_ANALYST_PASSWORD ?? "" };
const SHOTS = process.env.SENTINEL_SCREENSHOT_DIR;

async function signIn(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Work email").fill(ANALYST.email);
  await page.getByLabel("Password").fill(ANALYST.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Command Center" })).toBeVisible();
}

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

async function shot(page: Page, name: string, project: string) {
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/${project}-${name}.png`, fullPage: true });
}

test.skip(!ANALYST.password, "SENTINEL_E2E_ANALYST_PASSWORD is required");

test("simulated checkout flows into the transaction workspace", async ({ page }, info) => {
  await signIn(page);
  await audit(page, "command center");
  await noHorizontalOverflow(page);
  await shot(page, "1-command-center", info.project.name);

  await nav(page).getByRole("link", { name: "Sandbox Checkout" }).click();
  await expect(page.getByText("Simulated workflow")).toBeVisible();
  await page.getByText("Team Workspace").click();
  await audit(page, "checkout");
  await noHorizontalOverflow(page);
  await page.getByRole("button", { name: /simulate buyer approval/i }).click();
  await expect(page.getByText("Capture confirmed")).toBeVisible();
  await shot(page, "2-checkout", info.project.name);
  const orderId = (await page.locator("dd").first().textContent())?.trim() ?? "";
  expect(orderId).toMatch(/^SIM-ORDER-/);

  await nav(page).getByRole("link", { name: "Transactions" }).click();
  await expect(page.getByRole("heading", { name: "Transactions" })).toBeVisible();
  const row = page.locator(".ag-row", { hasText: orderId });
  await expect(row).toBeVisible();
  await audit(page, "transactions");
  await noHorizontalOverflow(page);
  await shot(page, "3-transactions", info.project.name);
  await row.click();

  await expect(page.getByRole("heading", { name: "$249.00" })).toBeVisible();
  await expect(page.getByText("PayPal order created")).toBeVisible();
  await expect(page.getByText("Capture response recorded")).toBeVisible();
  await expect(page.getByText("Not scored")).toBeVisible();
  await audit(page, "transaction detail");
  await noHorizontalOverflow(page);
  await shot(page, "4-transaction-detail", info.project.name);

  await nav(page).getByRole("link", { name: "Settings" }).click();
  await expect(page.getByText("Offline fixture")).toBeVisible();
  await audit(page, "settings");
  await shot(page, "5-settings", info.project.name);
});

test("unauthenticated users are sent to sign-in", async ({ page }) => {
  await page.goto("/transactions");
  await expect(page.getByRole("heading", { name: "Sign in to your workspace" })).toBeVisible();
  await audit(page, "login");
});
