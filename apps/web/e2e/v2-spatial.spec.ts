import { expect, test } from "@playwright/test";
test("tape travels out of the housing and reverses with its evidence frames", async ({
  page,
}) => {
  await page.goto("/__v2-preview");
  await page.locator(".v2-spatial-art").waitFor();
  await page.evaluate(() => scrollTo(0, 0.6 * innerHeight * 4));
  await expect
    .poll(() => page.locator(".v2-story").getAttribute("data-stage"))
    .toBe("3");
  const state = await page.locator(".v2-story").evaluate((el) => ({
    distance: el.dataset.tapeDistance,
    path: el.querySelector("[data-strip-length]")?.getAttribute("d"),
    rotation: el.querySelector("[data-reel=left]")?.getAttribute("transform"),
    radius: el.querySelector("[data-wound=left]")?.getAttribute("r"),
  }));
  expect(Number(state.distance)).toBeGreaterThan(1500);
  const portGap = await page.locator(".v2-spatial-art").evaluate((svg) => {
    const machine = svg.querySelector<SVGSVGElement>(".v2-machine");
    const path = svg.querySelector<SVGPathElement>("[data-strip-length]");
    const machineMatrix = machine?.getScreenCTM(),
      pathMatrix = path?.getScreenCTM();
    if (!path || !machineMatrix || !pathMatrix)
      throw new Error("SVG coordinate system unavailable");
    const port = new DOMPoint(763, 380).matrixTransform(machineMatrix);
    const first = path.getPointAtLength(0);
    const tape = new DOMPoint(first.x, first.y).matrixTransform(pathMatrix);
    return Math.hypot(port.x - tape.x, port.y - tape.y);
  });
  expect(portGap).toBeLessThan(0.1);

  await expect(page.locator("[data-path-node]").nth(0)).toBeVisible();
  await page.evaluate(() => scrollTo(0, 0.9 * innerHeight * 4));
  await page.waitForFunction(
    () =>
      Number(
        document.querySelector(".v2-story")?.getAttribute("data-progress"),
      ) > 0.89,
  );
  await page.evaluate(() => scrollTo(0, 0.6 * innerHeight * 4));
  await page.waitForFunction(
    () =>
      document.querySelector(".v2-story")?.getAttribute("data-stage") === "3",
  );
  const reversed = await page.locator(".v2-story").evaluate((el) => ({
    distance: el.dataset.tapeDistance,
    path: el.querySelector("[data-strip-length]")?.getAttribute("d"),
    rotation: el.querySelector("[data-reel=left]")?.getAttribute("transform"),
    radius: el.querySelector("[data-wound=left]")?.getAttribute("r"),
  }));
  expect(reversed).toEqual(state);
});
test("shared live dossier layout hands off at the top and history restores the story", async ({
  page,
}) => {
  await page.goto("/__v2-preview");
  await page.locator(".v2-spatial-art").waitFor();
  await page.evaluate(() => scrollTo(0, innerHeight * 4));
  const enter = page.getByRole("link", {
    name: "Enter the demo workspace",
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
  await expect(page.locator(".v2-story")).toHaveAttribute("data-stage", "5");
  await page.goForward();
  await expect.poll(() => page.evaluate(() => scrollY)).toBe(150);
  await page.goto("/__v2-preview/dossier");
  await expect(
    page.getByRole("heading", { name: "Payment dossier.", exact: true }),
  ).toBeInViewport();
  await expect.poll(() => page.evaluate(() => scrollY)).toBe(0);
});
test("mobile primary action is above the fold and transport responds without pinning", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/__v2-preview");
  const cta = page
    .locator(".v2-compact-hero")
    .getByRole("link", { name: "Explore the workspace" });
  await expect(cta).toBeInViewport();
  await expect(page.locator(".pin-spacer")).toHaveCount(0);
  const initial = await page
    .locator("[data-reel=left]")
    .getAttribute("transform");
  await page.evaluate(() => scrollTo(0, 900));
  await page.waitForTimeout(100);
  expect(
    await page.locator("[data-reel=left]").getAttribute("transform"),
  ).not.toEqual(initial);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.reload();
  const still = await page
    .locator("[data-reel=left]")
    .getAttribute("transform");
  await page.evaluate(() => scrollTo(0, 1300));
  await page.waitForTimeout(100);
  expect(
    await page.locator("[data-reel=left]").getAttribute("transform"),
  ).toEqual(still);
});
