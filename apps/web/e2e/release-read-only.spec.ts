import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

// Inspect current persisted demo data without writing records or initiating checkout.
test("release route audit preserves the read-only judge workflow", async ({ page }) => {
  test.setTimeout(180_000);
  const password = process.env.SENTINEL_JUDGE_PASSWORD;
  test.skip(!password, "Private judge credential required for complete route inspection");
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("/login");
  await page.getByLabel("Work email").fill("judge@sentinel-demo.example");
  await page.getByLabel("Password").fill(password!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Command Center" })).toBeVisible();
  const response = await page.request.get("/api/v1/demo/scenario");
  expect(response.status()).toBe(200);
  const scenario = await response.json();
  expect(scenario.data_origin).toBe("SIMULATED");
  const routes = [
    ["command-center", "/"], ["transactions", "/transactions"],
    ["payment", `/transactions/${scenario.transaction_id}`], ["model", "/model"],
    ["review-queue", "/cases"], ["investigation-evidence-approvals", `/cases/${scenario.case_id}`],
    ["refunds", "/refunds"], ["disputes", "/disputes"], ["policy", "/policy"],
    ["monitoring", "/monitoring"], ["network", "/network"], ["settings", "/settings"], ["judge-guide", "/demo"],
  ];
  for (const [name, path] of routes) {
    await page.goto(path);
    await expect(page.locator("main")).toBeVisible();
    await page.waitForFunction(() => document.querySelectorAll(".animate-pulse").length === 0);
    await expect(page.getByRole("heading", { name: /page not found/i })).toHaveCount(0);
    expect((await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze()).violations).toEqual([]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
    if (name === "investigation-evidence-approvals") {
      await expect(page.getByRole("button", { name: /upload evidence|run investigation|request approval/i })).toHaveCount(0);
    }
    const dir = process.env.SENTINEL_SCREENSHOT_DIR;
    if (dir) await page.screenshot({ path: `${dir}/release-${name}-${test.info().project.name}.png`, fullPage: true });
  }
  expect(errors).toEqual([]);
});
