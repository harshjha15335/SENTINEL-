import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
const shots =
  process.env.SENTINEL_SCREENSHOT_DIR ?? "test-results/v2-artifacts";
async function audit(page: Page) {
  const result = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(
    result.violations.map((v) => ({
      id: v.id,
      nodes: v.nodes.map((n) => n.target),
    })),
  ).toEqual([]);
}
async function progress(page: Page, p: number) {
  const top = await page
    .locator(".v2-story-track")
    .evaluate((el) => el.getBoundingClientRect().top + window.scrollY);
  await page.evaluate(
    ({ top, p }) => window.scrollTo(0, top + p * window.innerHeight * 4),
    { top, p },
  );
  await expect
    .poll(async () =>
      Number(await page.locator(".v2-story").getAttribute("data-progress")),
    )
    .toBeCloseTo(p, 2);
}
test("seven scroll checkpoints, rewind, restored position and clean remount", async ({
  page,
}) => {
  const errors: string[] = [];
  const apiCalls: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("request", (r) => {
    if (r.url().includes("/api/")) apiCalls.push(r.url());
  });
  await page.goto("/__v2-preview");
  await expect(
    page.getByRole("heading", {
      name: "Every payment has a story.",
    }),
  ).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  const initial = await page
    .locator("[data-wallet-placement]")
    .getAttribute("transform");
  await page.waitForTimeout(150);
  expect(
    await page.locator("[data-wallet-placement]").getAttribute("transform"),
  ).toEqual(initial);
  let middle: string | null = null;
  for (const [i, p] of [0, 0.2, 0.35, 0.5, 0.65, 0.75, 0.999].entries()) {
    await progress(page, p);
    if (i === 6)
      await expect(page.locator("[data-dossier-frame]")).toBeVisible();
    else await expect(page.locator("[data-story-stage]").nth(i)).toBeVisible();
    await page.screenshot({ path: `${shots}/reel-${i}.png` });
    if (p === 0.35)
      middle = await page
        .locator("[data-wallet-placement]")
        .getAttribute("transform");
  }
  await progress(page, 0.35);
  expect(
    await page.locator("[data-wallet-placement]").getAttribute("transform"),
  ).toEqual(middle);
  expect(middle).not.toEqual(initial);
  await page.reload();
  await expect(page.locator(".v2-story")).toHaveAttribute("data-stage", "2");
  await progress(page, 0);
  expect(
    await page.locator("[data-wallet-placement]").getAttribute("transform"),
  ).toEqual(initial);
  await audit(page);
  await page.getByRole("button", { name: "Skip story" }).click();
  await expect(page.locator("#v2-after-story")).toBeFocused();
  await expect(
    page.getByRole("heading", {
      name: "Money moves. Risk hides. SENTINEL reveals it.",
    }),
  ).toBeInViewport();
  await page.getByRole("link", { name: "Open the Payment Dossier" }).click();
  await expect(
    page.getByRole("heading", { name: "Payment dossier." }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Follow the money ↗", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Go to Risk analysis", exact: true })
    .click();
  await expect(page.locator(".v2-story")).toHaveAttribute("data-stage", "4");
  expect(await page.locator(".pin-spacer").count()).toBe(1);
  expect(errors).toEqual([]);
  expect(apiCalls).toEqual([]);
});
test("dossier examples, timeline and browser history stay deterministic", async ({
  page,
}) => {
  const apiCalls: string[] = [];
  page.on("request", (r) => {
    if (r.url().includes("/api/")) apiCalls.push(r.url());
  });
  await page.goto("/__v2-preview/dossier");
  await expect(
    page.getByRole("heading", { name: "$1,849.00 USD" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "02 Established pattern" }).click();
  await expect(
    page.getByRole("heading", { name: "$249.00 USD" }),
  ).toBeVisible();
  await expect(page.getByText("LOW RISK", { exact: true })).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "$249.00 USD" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "timeline 02" }).click();
  await expect(page.getByText("Demonstration order created")).toBeVisible();
  await page.getByRole("button", { name: "overview 01" }).click();
  await audit(page);
  await page.screenshot({
    path: `${shots}/dossier-desktop.png`,
    fullPage: true,
  });
  await page.goBack();
  await expect(
    page.getByRole("heading", { name: "$1,849.00 USD" }),
  ).toBeVisible();
  expect(apiCalls).toEqual([]);
});
for (const [width, height] of [
  [1920, 1080],
  [1440, 900],
  [1280, 800],
  [1024, 768],
  [768, 1024],
  [390, 844],
  [360, 800],
]) {
  test(`responsive reel and dossier ${width}x${height}`, async ({ page }) => {
    await page.setViewportSize({ width: width ?? 390, height: height ?? 844 });
    await page.goto("/__v2-preview");
    await expect(page.locator(".v2-wallet")).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth - window.innerWidth,
      ),
    ).toBeLessThanOrEqual(1);
    if ((width ?? 0) <= 900)
      await expect(
        page.getByRole("heading", {
          name: "Your next move, better informed.",
        }),
      ).toBeVisible();
    if (width === 390)
      await page.screenshot({ path: `${shots}/reel-mobile.png` });
    await page.goto("/__v2-preview/dossier");
    await expect(
      page.getByRole("heading", { name: "Payment dossier." }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth - window.innerWidth,
      ),
    ).toBeLessThanOrEqual(1);
    if (width === 390) {
      await audit(page);
      await page.screenshot({
        path: `${shots}/dossier-mobile.png`,
        fullPage: true,
      });
    }
  });
}
test("reduced motion exposes all narrative content and keyboard skip", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/__v2-preview");
  await expect(page.locator("[data-story-stage]")).toHaveCount(7);
  for (const el of await page.locator("[data-story-stage]").all())
    await expect(el).toBeVisible();
  expect(await page.locator(".pin-spacer").count()).toBe(0);
  await audit(page);
  await page.getByRole("button", { name: "Skip story" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("#v2-after-story")).toBeFocused();
});
test("unauthorized preview loads only the existing session check", async ({
  page,
}) => {
  const calls: string[] = [];
  await page.route("**/api/v1/me", (r) =>
    r.fulfill({
      status: 401,
      contentType: "application/json",
      body: JSON.stringify({
        error: { code: "unauthenticated", message: "Sign in required" },
      }),
    }),
  );
  page.on("request", (r) => {
    if (r.url().includes("/api/")) calls.push(new URL(r.url()).pathname);
  });
  await page.goto("/__v2-preview/workspace");
  await expect(
    page.getByRole("heading", { name: "Sign in to inspect real records." }),
  ).toBeVisible();
  expect(calls).toEqual(["/api/v1/me"]);
  await audit(page);
});

test("resize through mobile and back releases pin and preserves readable content", async ({
  page,
}) => {
  await page.goto("/__v2-preview");
  await page
    .getByRole("button", { name: "Go to Risk analysis", exact: true })
    .click();
  await expect(page.locator(".v2-story")).toHaveAttribute("data-stage", "4");
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator(".pin-spacer")).toHaveCount(0);
  for (const el of await page.locator("[data-story-stage]").all())
    await expect(el).toBeVisible();
  await page.setViewportSize({ width: 1440, height: 900 });
  await expect(page.locator(".pin-spacer")).toHaveCount(1);
  await page
    .getByRole("button", { name: "Go to The wallet", exact: true })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "Every payment has a story.",
    }),
  ).toBeVisible();
});
