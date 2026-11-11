import { expect, test } from "@playwright/test";

test("delayed transactions preserve grid/pagination geometry and all keyboard-accessible rows", async ({
  page,
}, info) => {
  let release: () => void = () => undefined;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/demo-data/transactions.json", async (route) => {
    await gate;
    await route.continue();
  });
  await page.goto("/#/app/transactions");
  await expect(
    page.getByLabel("Search by PayPal order or capture ID"),
  ).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  const before = await page.locator(".transaction-grid").boundingBox();
  const pagination = await page
    .getByRole("navigation", { name: "Pagination" })
    .boundingBox();
  await page.screenshot({ path: info.outputPath("grid-loading.png") });
  release();
  await expect(page.locator(".ag-row").first()).toBeVisible();
  const after = await page.locator(".transaction-grid").boundingBox();
  expect(after?.height).toBeCloseTo(before?.height ?? 0, 0);
  expect(
    (await page.getByRole("navigation", { name: "Pagination" }).boundingBox())
      ?.y,
  ).toBeCloseTo(pagination?.y ?? 0, 0);
  await page.screenshot({ path: info.outputPath("grid-loaded.png") });
  // Bring the whole nested scroll region onscreen before exercising its keyboard navigation.
  await page.locator(".transaction-grid").scrollIntoViewIfNeeded();
  await page
    .locator('.ag-row[row-index="0"] .ag-cell[col-id="paypal_order_id"]')
    .focus();
  await page.keyboard.press("Control+End");
  await expect(page.locator('.ag-row[row-index="24"]')).toBeInViewport();
  await page.keyboard.press("Control+Home");
  await expect(
    page.locator('.ag-row[row-index="0"] .ag-cell[col-id="paypal_order_id"]'),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("article", { name: "Payment dossier" }),
  ).toBeVisible();
});

test("late snapshot timestamp does not move the workspace", async ({
  page,
}) => {
  let release: () => void = () => undefined;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/demo-data/snapshot.json", async (route) => {
    await gate;
    await route.continue();
  });
  await page.goto("/#/app/transactions");
  await expect(page.locator(".ag-row").first()).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  const before = await page.getByRole("main").boundingBox();
  await expect(page.locator(".static-snapshot-time")).toHaveText(
    "loading date…",
  );
  release();
  await expect(page.locator(".static-snapshot-time")).not.toHaveText(
    "loading date…",
  );
  expect((await page.getByRole("main").boundingBox())?.y).toBeCloseTo(
    before?.y ?? 0,
    0,
  );
});

test("recorded risk progressively fills its reserved chart area", async ({
  page,
}, info) => {
  let release: () => void = () => undefined;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/demo-data/risk.json", async (route) => {
    await gate;
    await route.continue();
  });
  await page.goto("/#/app/transactions/1e054580-49f1-48be-a7a4-a4d4cf23647d");
  await expect(
    page.getByRole("heading", { name: "$249.00", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".risk-content")).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  const before = await page.locator(".risk-content").boundingBox();
  await page.screenshot({
    path: info.outputPath("risk-loading.png"),
    fullPage: true,
  });
  release();
  await expect(page.locator(".risk-assessment-layout")).toBeVisible();
  const after = await page.locator(".risk-content").boundingBox();
  expect(after?.height).toBeCloseTo(before?.height ?? 0, 0);
  await page.screenshot({
    path: info.outputPath("risk-loaded.png"),
    fullPage: true,
  });
});
