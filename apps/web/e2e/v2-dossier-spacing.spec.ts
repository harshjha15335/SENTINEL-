import { expect, test } from "@playwright/test";

test("animated story chapter stays inside its glass panel", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await page.locator(".v2-money-art").waitFor();
  await page.evaluate(() => document.fonts.ready);

  const measures = await page
    .locator(".v2-money-story .v2-scene-copy [data-story-stage]")
    .first()
    .evaluate((stage) => {
      const label = stage.querySelector(".v2-eyebrow");
      if (!label) throw new Error("Story chapter label missing");
      const box = stage.getBoundingClientRect();
      const text = label.getBoundingClientRect();
      const style = getComputedStyle(stage);
      return {
        topGap: text.top - box.top,
        bottomGap: box.bottom - text.bottom,
        leftGap: text.left - box.left,
        hasBorder: style.borderTopStyle === "solid",
        paddingTop: parseFloat(style.paddingTop),
      };
    });

  expect(measures.hasBorder).toBeTruthy();
  expect(measures.paddingTop).toBeGreaterThanOrEqual(20);
  expect(measures.topGap).toBeGreaterThan(10);
  expect(measures.bottomGap).toBeGreaterThan(10);
  expect(measures.leftGap).toBeGreaterThan(10);
});

for (const width of [390, 768, 1024, 1280, 1440, 1744]) {
  test(`payment dossier content stays within its layout at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/demo-payment");
    await page.evaluate(() => document.fonts.ready);
    await expect(page.locator(".v2-risk")).toBeVisible();
    await expect(page.locator(".v2-fact-grid")).toBeVisible();

    const boxes = await page.locator(".v2-risk").evaluate((risk) => {
      const outer = risk.getBoundingClientRect();
      const selectors = [
        ".v2-section-label",
        ".v2-score",
        ".v2-factors",
        ".v2-review-note",
      ];
      return selectors.map((selector) => {
        const inner = risk.querySelector(selector);
        if (!inner) throw new Error(`Missing risk item: ${selector}`);
        const rect = inner.getBoundingClientRect();
        return {
          selector,
          leftInset: rect.left - outer.left,
          rightInset: outer.right - rect.right,
        };
      });
    });
    for (const item of boxes) {
      expect(item.leftInset, `${item.selector} left at ${width}`).toBeGreaterThanOrEqual(-1);
      expect(item.rightInset, `${item.selector} right at ${width}`).toBeGreaterThanOrEqual(-1);
    }

    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - window.innerWidth,
    );
    expect(overflow, `horizontal overflow at ${width}`).toBeLessThanOrEqual(1);

    const overflowingValues = await page
      .locator(".v2-fact-grid dd")
      .evaluateAll((values) =>
        values.filter((value) => value.scrollWidth > value.clientWidth + 1).map((value) => value.textContent),
      );
    expect(overflowingValues).toEqual([]);
  });
}
