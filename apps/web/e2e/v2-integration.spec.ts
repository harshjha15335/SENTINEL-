import { readFileSync } from "node:fs";
import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
const shots =
  process.env.SENTINEL_SCREENSHOT_DIR ?? "test-results/v2-artifacts";
const credentialsFile = process.env.SENTINEL_V2_TEST_CREDENTIALS;
const secret = credentialsFile
  ? Object.fromEntries(
      readFileSync(credentialsFile, "utf8")
        .trim()
        .split("\n")
        .map((l) => {
          const i = l.indexOf("=");
          return [l.slice(0, i), l.slice(i + 1)];
        }),
    )
  : {};
const password = secret.SENTINEL_SEED_ANALYST_PASSWORD;
test.skip(
  !password,
  "Requires the dedicated local test database and credential file.",
);
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
  const response = await page.request.get("/api/v1/cases?limit=1&offset=0");
  expect(response.ok()).toBeTruthy();
  const data = (await response.json()) as {
    items: { id: string; transaction_id: string; title: string }[];
  };
  const c = data.items[0];
  expect(c).toBeDefined();
  if (!c) throw new Error("Seeded case missing");
  const txResponse = await page.request.get(
    `/api/v1/transactions/${c.transaction_id}`,
  );
  expect(txResponse.ok()).toBeTruthy();
  const t = (await txResponse.json()) as {
    paypal_order_id: string | null;
    amount_minor: number;
    currency: string;
  };
  const mutations: string[] = [];
  page.on("request", (r) => {
    if (r.url().includes("/api/") && r.method() !== "GET")
      mutations.push(r.method() + " " + new URL(r.url()).pathname);
  });
  await page.goto("/__v2-preview/workspace");
  await expect(page.getByLabel("Transaction results")).toBeVisible();
  if (t.paypal_order_id) {
    await page.getByLabel("Search order or capture ID").fill(t.paypal_order_id);
    await page.getByRole("button", { name: "Search", exact: true }).click();
    await page
      .getByRole("button", { name: new RegExp(t.paypal_order_id) })
      .click();
  } else {
    // Synthetic scenario records have no fabricated PayPal references; use the supported deep link.
    await page.goto(`/__v2-preview/workspace?id=${c.transaction_id}`);
  }
  await expect(
    page.getByRole("article", { name: "Payment dossier" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", {
      name: new RegExp(
        new Intl.NumberFormat("en-US", {
          style: "currency",
          currency: t.currency,
        })
          .format(t.amount_minor / 100)
          .replace(/[.*+?^${}()|[\]\\]/g, "\\$&"),
      ),
    }),
  ).toBeVisible();
  await expect(page.getByText("HIGH RISK", { exact: true })).toBeVisible();
  await expect(
    page.getByText("Model-generated", { exact: false }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("article", { name: "Payment dossier" }),
  ).toBeVisible();
  const axe = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(axe.violations).toEqual([]);
  await page.screenshot({
    path: `${shots}/dossier-authorized.png`,
    fullPage: true,
  });
  await page.getByRole("link", { name: new RegExp(c.title) }).click();
  await expect(
    page.getByRole("heading", { name: c.title, exact: true }),
  ).toBeVisible();
  expect(mutations).toEqual([]);
});
test("API failure stays an error; expiry hides private data; empty search remains empty", async ({
  page,
}) => {
  await login(page);
  await page.goto("/__v2-preview/workspace");
  await page.getByLabel("Search order or capture ID").fill("V2-NO-SUCH-ORDER");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(
    page.getByText("No transactions match this search."),
  ).toBeVisible();
  await page.route("**/api/v1/transactions?**", (r) =>
    r.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({
        error: { code: "unavailable", message: "Test database unavailable" },
      }),
    }),
  );
  await page.reload();
  await expect(page.getByRole("alert")).toContainText(
    "Test database unavailable",
  );
  await page.unroute("**/api/v1/transactions?**");
  await page.route("**/api/v1/me", (r) =>
    r.fulfill({
      status: 401,
      contentType: "application/json",
      body: JSON.stringify({
        error: { code: "unauthenticated", message: "Session expired" },
      }),
    }),
  );
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Sign in to inspect real records." }),
  ).toBeVisible();
  await expect(
    page.getByRole("article", { name: "Payment dossier" }),
  ).toHaveCount(0);
});

test("explorer filters, pagination and sorting preserve real API query semantics", async ({
  page,
}) => {
  await login(page);
  await page.goto("/__v2-preview/workspace");
  await expect(page.getByLabel("Transaction results")).toBeVisible();
  const filter = page.waitForResponse(
    (r) =>
      r.url().includes("/api/v1/transactions?") &&
      r.url().includes("status=CAPTURED"),
  );
  await page
    .getByLabel("Payment status", { exact: true })
    .selectOption("CAPTURED");
  expect((await filter).ok()).toBeTruthy();
  const origin = page.waitForResponse(
    (r) =>
      r.url().includes("/api/v1/transactions?") &&
      r.url().includes("data_origin=SYNTHETIC_DEMO"),
  );
  await page
    .getByLabel("Data origin", { exact: true })
    .selectOption("SYNTHETIC_DEMO");
  expect((await origin).ok()).toBeTruthy();
  await expect(page).toHaveURL(/status=CAPTURED/);
  await page
    .getByRole("button", { name: "Amount ascending · current page" })
    .click();
  await expect(
    page.getByRole("button", { name: "Amount descending · current page" }),
  ).toBeVisible();
  const next = page.getByRole("button", { name: "Next page" });
  if (await next.isEnabled()) {
    const response = page.waitForResponse(
      (r) =>
        r.url().includes("/api/v1/transactions?") &&
        r.url().includes("offset=10"),
    );
    await next.click();
    expect((await response).ok()).toBeTruthy();
    await expect(page).toHaveURL(/page=1/);
    await page.getByRole("button", { name: "Previous page" }).click();
  }
  await page.reload();
  await expect(page.getByLabel("Payment status", { exact: true })).toHaveValue(
    "CAPTURED",
  );
  await expect(page.getByLabel("Data origin", { exact: true })).toHaveValue(
    "SYNTHETIC_DEMO",
  );
});
