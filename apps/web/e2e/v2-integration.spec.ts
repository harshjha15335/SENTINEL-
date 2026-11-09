import { readFileSync } from "node:fs";
import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
const file = process.env.SENTINEL_V2_TEST_CREDENTIALS;
const secret = file
  ? Object.fromEntries(
      readFileSync(file, "utf8")
        .trim()
        .split("\n")
        .map((l) => {
          const i = l.indexOf("=");
          return [l.slice(0, i), l.slice(i + 1)];
        }),
    )
  : {};
const password = secret.SENTINEL_SEED_ANALYST_PASSWORD;
test.skip(!password, "Requires dedicated local fixture credentials");
async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Work email").fill("analyst@northwind.example");
  await page.getByLabel("Password", { exact: true }).fill(password ?? "");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Command Center", exact: true }),
  ).toBeVisible();
}
test("actual session → search API → PostgreSQL record → dossier → existing case", async ({
  page,
}) => {
  await login(page);
  const list = await page.request.get("/api/v1/cases?status=OPEN&limit=1&offset=0");
  expect(list.ok()).toBeTruthy();
  const c = (await list.json()).items[0];
  expect(c).toBeDefined();
  const r = await page.request.get(`/api/v1/transactions/${c.transaction_id}`);
  expect(r.ok()).toBeTruthy();
  const t = await r.json();
  const mutations: string[] = [];
  page.on("request", (r) => {
    if (r.url().includes("/api/") && r.method() !== "GET")
      mutations.push(r.method());
  });
  if (t.paypal_order_id) {
    await page.goto("/app/transactions");
    await page
      .getByLabel("Search by PayPal order or capture ID")
      .fill(t.paypal_order_id);
    await page.getByRole("button", { name: "Search", exact: true }).click();
    await page.locator(".ag-row", { hasText: t.paypal_order_id }).click();
  } else await page.goto(`/app/transactions/${c.transaction_id}`);
  const amount = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: t.currency,
  }).format(t.amount_minor / 100);
  await expect(
    page.getByRole("article", { name: "Payment dossier" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: amount, exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Model-generated", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("list", { name: "Main factors behind this score" }),
  ).toBeVisible();
  const audit = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(audit.violations).toEqual([]);
  await page.getByRole("link", { name: c.title, exact: true }).click();
  await expect(
    page.getByRole("heading", { name: c.title, exact: true }),
  ).toBeVisible();
  expect(mutations).toEqual([]);
});
test("API failure stays an error; expiry hides private data; empty search remains empty", async ({
  page,
}) => {
  await login(page);
  await page.route("**/api/v1/transactions?**", (r) =>
    r.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({
        error: { code: "unavailable", message: "Record service unavailable" },
      }),
    }),
  );
  await page.goto("/app/transactions");
  await expect(page.getByRole("alert")).toContainText(
    "Record service unavailable",
    { timeout: 15000 },
  );
  await page.unroute("**/api/v1/transactions?**");
  await page
    .getByLabel("Search by PayPal order or capture ID")
    .fill("no-such-record-v2-parity");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(
    page.getByText("No transactions match these filters"),
  ).toBeVisible();
  await page.route(
    "**/api/v1/transactions/8891b311-1c44-4b99-95a5-45c3f3ba8be5",
    (r) =>
      r.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({
          error: { code: "unauthenticated", message: "Session expired" },
        }),
      }),
  );
  await page.goto("/app/transactions/8891b311-1c44-4b99-95a5-45c3f3ba8be5");
  await expect(
    page.getByRole("heading", { name: "Sign in to your workspace" }),
  ).toBeVisible();
  await expect(
    page.getByRole("article", { name: "Payment dossier" }),
  ).toHaveCount(0);
});
test("explorer filters, pagination and sorting preserve real API query semantics", async ({
  page,
}) => {
  await login(page);
  await page.goto("/app/transactions");
  await expect(page.locator(".ag-row").first()).toBeVisible();
  const status = page.waitForResponse(
    (r) =>
      r.url().includes("/api/v1/transactions?") &&
      r.url().includes("status=CAPTURED"),
  );
  await page.getByLabel("Status", { exact: true }).selectOption("CAPTURED");
  expect((await status).ok()).toBeTruthy();
  const origin = page.waitForResponse(
    (r) =>
      r.url().includes("/api/v1/transactions?") &&
      r.url().includes("data_origin=SYNTHETIC_DEMO"),
  );
  await page
    .getByLabel("Origin", { exact: true })
    .selectOption("SYNTHETIC_DEMO");
  expect((await origin).ok()).toBeTruthy();
  const next = page.waitForResponse(
    (r) =>
      r.url().includes("/api/v1/transactions?") &&
      r.url().includes("offset=25"),
  );
  await page.getByRole("button", { name: "Next page", exact: true }).click();
  expect((await next).ok()).toBeTruthy();
  await expect(page).toHaveURL(/page=1/);
  await page.reload();
  await expect(page.getByLabel("Status", { exact: true })).toHaveValue(
    "CAPTURED",
  );
  await expect(page.getByLabel("Origin", { exact: true })).toHaveValue(
    "SYNTHETIC_DEMO",
  );
});
