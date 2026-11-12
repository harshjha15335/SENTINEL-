import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
test("shared live dossier layout hands off at the top and history restores the story", async ({
  page,
}) => {
  await page.goto("/");
  await page.locator(".v2-money-art").waitFor();
  await page.evaluate(() => scrollTo(0, innerHeight * 4));
  const enter = page.locator(".v2-scene-enter").getByRole("link", {
    name: "Explore simulated demo",
    exact: true,
  });
  await expect(enter).toBeVisible();
  const before = await page
    .locator("[data-dossier-frame] .v2-workspace-intro h1")
    .boundingBox();
  expect(before).not.toBeNull();
  await enter.click();
  await expect(page).toHaveURL(/\/demo-payment$/);
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
  await page.goto("/demo-payment");
  await expect(
    page.getByRole("heading", { name: "Payment dossier.", exact: true }),
  ).toBeInViewport();
  await expect.poll(() => page.evaluate(() => scrollY)).toBe(0);
});
test("mobile primary action is above the fold and wallet responds without pinning", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  const cta = page
    .locator(".v2-compact-hero")
    .getByRole("link", { name: "Explore simulated demo" });
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
  await page.goto("/");
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
test("public demonstration navigation remains distinct from authenticated workspaces", async ({
  page,
}) => {
  await page.goto("/demo-payment");
  await expect(
    page.getByRole("heading", { name: "Payment dossier." }),
  ).toBeVisible();
  await expect(
    page.getByText("SIMULATED / PUBLIC-SAFE DEMONSTRATION"),
  ).toBeVisible();
  const audit = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(audit.violations).toEqual([]);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.locator(".v2-mobile-menu summary").click();
  await page
    .getByRole("navigation", { name: "Mobile workspace" })
    .getByRole("link", { name: "Transactions", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Sign in to your workspace" }),
  ).toBeVisible();
});
test("receipt becomes native dossier header without any workspace text scaling", async ({
  page,
}) => {
  await page.goto("/");
  await page.locator(".v2-money-art").waitFor();
  await page.evaluate(() => document.fonts.ready);
  const sample = async (p: number) => {
    await page.evaluate((n) => scrollTo(0, n * innerHeight * 4), p);
    await expect
      .poll(async () =>
        Number(await page.locator(".v2-story").getAttribute("data-progress")),
      )
      .toBeCloseTo(p, 2);
  };
  await sample(0.84);
  await expect(page.locator("[data-receipt-morph]")).toBeVisible();
  await expect(page.locator("[data-morph-amount]")).toHaveText("$1,849.00");
  const state = await page.locator("[data-morph-amount]").evaluate((e) => ({
    box: e.getBoundingClientRect().toJSON(),
    font: getComputedStyle(e).fontSize,
  }));
  for (const p of [0.84, 0.89, 0.94, 0.999]) {
    await sample(p);
    const transforms = await page
      .locator("[data-dossier-frame]")
      .evaluate((el) =>
        [el, ...Array.from(el.querySelectorAll("*"))]
          .filter(
            (e) => ["H1", "H2", "P", "SPAN"].includes(e.tagName) || e === el,
          )
          .map((e) => getComputedStyle(e).transform),
      );
    expect(transforms.every((t) => t === "none")).toBeTruthy();
  }
  await sample(0.84);
  expect(
    await page.locator("[data-morph-amount]").evaluate((e) => ({
      box: e.getBoundingClientRect().toJSON(),
      font: getComputedStyle(e).fontSize,
    })),
  ).toEqual(state);
  await sample(0.89);
  const carried = await page.locator("[data-morph-amount]").boundingBox(),
    target = await page
      .locator("[data-dossier-frame] [data-shared-amount]")
      .boundingBox();
  expect(Math.abs((carried?.x ?? 0) - (target?.x ?? 0))).toBeLessThan(1);
  expect(Math.abs((carried?.y ?? 0) - (target?.y ?? 0))).toBeLessThan(1);
  await expect(page.locator("[data-note]")).toHaveCount(6);
});

for (const viewport of [
  { width: 1890, height: 652 },
  { width: 1440, height: 900 },
  { width: 1280, height: 720 },
  { width: 1024, height: 768 },
  { width: 945, height: 326 },
]) {
  test(`dossier entry action does not cover the reveal at ${viewport.width}x${viewport.height}`, async ({
    page,
  }) => {
    await page.setViewportSize(viewport);
    await page.goto("/");
    await page.locator(".v2-money-art").waitFor();
    await page.evaluate(() => document.fonts.ready);
    await page.evaluate(() => scrollTo(0, innerHeight * 4 * 0.999));
    await expect(page.locator(".v2-story")).toHaveAttribute("data-stage", "6");
    const frame = await page.locator("[data-dossier-frame]").boundingBox();
    const action = page.locator(".v2-scene-enter");
    await expect(action).toBeVisible();
    const actionBounds = await action.boundingBox();
    expect(frame).not.toBeNull();
    expect(actionBounds).not.toBeNull();
    if (!frame || !actionBounds)
      throw new Error("Missing reveal or entry action bounds");
    expect(actionBounds.y).toBeGreaterThanOrEqual(frame.y + frame.height - 1);
    await action
      .getByRole("link", { name: "Explore simulated demo", exact: true })
      .click();
    await expect(page).toHaveURL(/\/demo-payment$/);
    await expect(
      page.getByRole("heading", { name: "Payment dossier.", exact: true }),
    ).toBeInViewport();
    await expect.poll(() => page.evaluate(() => scrollY)).toBe(0);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth - innerWidth,
      ),
    ).toBeLessThanOrEqual(1);
  });
}
