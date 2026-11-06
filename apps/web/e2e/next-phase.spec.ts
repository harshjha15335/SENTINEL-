import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const password = process.env.SENTINEL_JUDGE_PASSWORD ?? "";

test("viewer explores next-phase modules without financial or write controls", async ({ page }) => {
  test.skip(!password, "Private judge credential required");
  const errors: string[] = [];
  page.on("pageerror", e => errors.push(e.message));
  await page.goto("/login");
  await page.getByLabel("Work email").fill("judge@sentinel-demo.example");
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Command Center" })).toBeVisible();
  for (const [route, title] of [["policy", "Policy Lab"], ["monitoring", "Risk monitoring"], ["network", "Relationship explorer"], ["refunds", "Refund review"], ["disputes", "Dispute Copilot"]]) {
    await page.goto(`/${route}`);
    await expect(page.getByRole("heading", { name: title, exact: true })).toBeVisible();
    await page.waitForFunction(() => document.querySelectorAll(".animate-pulse").length === 0);
    if (route === "policy") {
      const response = page.waitForResponse(r => r.url().includes("/policy-lab/simulate?") && r.url().includes("high_threshold=0.2"));
      await page.getByLabel("HIGH threshold", { exact: true }).fill("0.2");
      expect((await response).status()).toBe(200);
      await expect(page.getByLabel("Policy name")).toHaveCount(0);
    }
    if (route === "network") {
      const record = page.getByRole("button", { name: /^Transaction:/ }).first();
      await record.click();
      await expect(record).toHaveAttribute("aria-pressed", "true");
    }
    if (route === "refunds") {
      await expect(page.getByRole("button", { name: /approve intent|request refund/i })).toHaveCount(0);
      await expect(page.getByText(/Pending approval/i).first()).toBeVisible();
    }
    if (route === "disputes") {
      await page.getByRole("button", { name: /Demonstration dispute/ }).click();
      await expect(page.getByRole("heading", { name: "Dispute context" })).toBeVisible();
      await expect(page.getByRole("button", { name: /Create labelled demo|Read-only sandbox sync|Generate response/i })).toHaveCount(0);
    }
    expect((await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze()).violations).toEqual([]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
    const dir = process.env.SENTINEL_SCREENSHOT_DIR;
    if (dir) await page.screenshot({ path: `${dir}/next-${route}-${test.info().project.name}.png`, fullPage: true });
  }
  expect(errors).toEqual([]);
});
