import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
test("shared live dossier layout hands off at the top and history restores the story", async ({
  page,
}) => {
  await page.goto("/__v2-preview");
  await page.locator(".v2-money-art").waitFor();
  await page.evaluate(() => scrollTo(0, innerHeight * 4));
  const enter = page.locator(".v2-scene-enter").getByRole("link", {
    name: "Enter SENTINEL",
    exact: true,
  });
  await expect(enter).toBeVisible();
  const before = await page
    .locator("[data-dossier-frame] .v2-workspace-intro h1")
    .boundingBox();
  expect(before).not.toBeNull();
  await enter.click();
  await expect(page).toHaveURL(/\/__v2-preview\/dossier$/);
  await expect.poll(() => page.evaluate(() => scrollY)).toBe(0);
  await expect(
    page.getByRole("heading", { name: "Payment dossier.", exact: true }),
  ).toBeInViewport();
  const after = await page.locator(".v2-workspace-intro h1").boundingBox();
  expect(Math.abs((before?.x ?? 0) - (after?.x ?? 0))).toBeLessThanOrEqual(2);
  expect(Math.abs((before?.y ?? 0) - (after?.y ?? 0))).toBeLessThanOrEqual(2);
  await page.evaluate(() => scrollTo(0, 150));
  await page.waitForTimeout(60);
  await page.reload();
  await expect.poll(() => page.evaluate(() => scrollY)).toBe(150);
  await page.goBack();
  await expect(page.locator(".v2-story")).toHaveAttribute("data-stage", "6");
  await page.goForward();
  await expect.poll(() => page.evaluate(() => scrollY)).toBe(150);
  await page.goto("/__v2-preview/dossier");
  await expect(
    page.getByRole("heading", { name: "Payment dossier.", exact: true }),
  ).toBeInViewport();
  await expect.poll(() => page.evaluate(() => scrollY)).toBe(0);
});
test("mobile primary action is above the fold and wallet responds without pinning", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/__v2-preview");
  const cta = page
    .locator(".v2-compact-hero")
    .getByRole("link", { name: "Enter SENTINEL" });
  await expect(cta).toBeInViewport();
  await expect(page.locator(".pin-spacer")).toHaveCount(0);
  const initial = await page
    .locator("[data-wallet-fold]")
    .getAttribute("style");
  await page.evaluate(() => scrollTo(0, 900));
  await page.waitForTimeout(100);
  expect(
    await page.locator("[data-wallet-fold]").getAttribute("style"),
  ).not.toEqual(initial);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.reload();
  const still = await page.locator("[data-wallet-fold]").getAttribute("style");
  await page.evaluate(() => scrollTo(0, 1300));
  await page.waitForTimeout(100);
  expect(
    await page.locator("[data-wallet-fold]").getAttribute("style"),
  ).toEqual(still);
});
test("wallet, main payment and field advance continuously and reverse exactly", async ({
  page,
}) => {
  await page.goto("/__v2-preview");
  await page.locator(".v2-money-art").waitFor();
  const sample = async (p: number) => {
    await page.evaluate((n) => scrollTo(0, n * innerHeight * 4), p);
    await expect
      .poll(async () =>
        Number(await page.locator(".v2-story").getAttribute("data-progress")),
      )
      .toBeCloseTo(p, 2);
    return page.locator(".v2-story").evaluate((el) => ({
      open: el.dataset.walletOpen,
      receipt: el
        .querySelector("[data-hero-receipt]")
        ?.getAttribute("transform"),
      wallet: el
        .querySelector("[data-wallet-placement]")
        ?.getAttribute("transform"),
      field: el.querySelector("[data-field]")?.getAttribute("style"),
    }));
  };
  const start = await sample(0),
    opened = await sample(0.2);
  expect(Number(opened.open)).toBeGreaterThan(0);
  expect(opened.receipt).not.toEqual(start.receipt);
  await expect(page.locator("[data-secondary-receipt]")).toContainText(
    "$249.00",
  );
  await sample(0.5);
  await expect(
    page.locator("[data-hero-receipt] [data-receipt-accent]"),
  ).toHaveAttribute("fill", "#FF865C");
  await expect(
    page.locator("[data-secondary-receipt] [data-receipt-accent]"),
  ).toHaveAttribute("fill", "#7547EB");
  await sample(0.565);
  await expect(
    page.locator(".v2-scene-copy [data-story-stage]:visible"),
  ).toHaveCount(1);
  const mid = await sample(0.65);
  expect(mid.field).toContain("opacity: 1");
  await sample(0.99);
  expect(await sample(0.65)).toEqual(mid);
  expect(await sample(0)).toEqual(start);
  await page.reload();
  await expect(page.locator(".pin-spacer")).toHaveCount(1);
});
test("command center is labeled simulated and navigation offers implemented destinations", async ({
  page,
}) => {
  await page.goto("/__v2-preview/command-center");
  await expect(
    page.getByRole("heading", { name: "Know what needs attention." }),
  ).toBeVisible();
  await expect(
    page.getByText("INTERACTIVE COMPOSITION PROTOTYPE / SIMULATED"),
  ).toBeVisible();
  const audit = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(audit.violations).toEqual([]);
  await page.getByRole("link", { name: "Review the payment" }).click();
  await expect(
    page.getByRole("article", { name: "Payment dossier" }),
  ).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByText("Menu", { exact: true }).click();
  await page
    .getByRole("navigation", { name: "Mobile workspace" })
    .getByRole("link", { name: "Transactions", exact: true })
    .click();
  await expect(page).toHaveURL(/workspace/);
});
