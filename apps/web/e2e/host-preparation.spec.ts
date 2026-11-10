import { expect, test } from "@playwright/test";

test("enforced CSP supports real wallet scrolling, rewind, reduced motion and keyboard skip", async ({
  page,
}, info) => {
  await page.addInitScript(() => {
    (window as unknown as { csp: string[] }).csp = [];
    document.addEventListener("securitypolicyviolation", (e) =>
      (window as unknown as { csp: string[] }).csp.push(
        `${e.effectiveDirective}: ${e.blockedURI}`,
      ),
    );
  });
  const unexpected: string[] = [];
  page.on("request", (r) => {
    if (
      !r
        .url()
        .startsWith(
          `${new URL(process.env.SENTINEL_WEB_URL ?? "https://127.0.0.1:9448/").origin}/`,
        ) ||
      r.method() !== "GET" ||
      r.url().includes("/api/") ||
      r.url().includes("/demo-data/")
    )
      unexpected.push(r.url());
  });
  await page.goto("/#/");
  await expect(page.locator(".v2-story")).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  if (info.project.name === "desktop") {
    const sample = async (p: number) => {
      await page.evaluate((n) => scrollTo(0, n * innerHeight * 4), p);
      await expect
        .poll(async () =>
          Number(await page.locator(".v2-story").getAttribute("data-progress")),
        )
        .toBeCloseTo(p, 2);
      return page.locator("[data-wallet-placement]").getAttribute("transform");
    };
    const initial = await sample(0);
    await page.mouse.wheel(0, 900);
    await expect
      .poll(async () =>
        Number(await page.locator(".v2-story").getAttribute("data-progress")),
      )
      .toBeGreaterThan(0);
    const mid = await sample(0.35);
    await page.screenshot({ path: info.outputPath("wallet-under-csp.png") });
    expect(mid).not.toBe(initial);
    for (const p of [0.5, 0.65, 0.75, 0.999]) await sample(p);
    await expect(page.locator("[data-dossier-frame]")).toBeVisible();
    expect(await sample(0.35)).toBe(mid);
    expect(await sample(0)).toBe(initial);
    await page.getByRole("button", { name: "Skip story" }).focus();
    await page.keyboard.press("Enter");
    await expect(page.locator("#v2-after-story")).toBeFocused();
  } else {
    await expect(
      page
        .locator(".v2-compact-hero")
        .getByRole("link", { name: "Explore simulated demo" }),
    ).toBeInViewport();
    await expect(page.locator(".pin-spacer")).toHaveCount(0);
    await page.screenshot({
      path: info.outputPath("mobile-wallet-under-csp.png"),
    });
    const initial = await page
      .locator("[data-wallet-fold]")
      .getAttribute("style");
    await page.mouse.wheel(0, 900);
    await expect
      .poll(() => page.locator("[data-wallet-fold]").getAttribute("style"))
      .not.toBe(initial);
    await page.mouse.wheel(0, -900);
    await expect.poll(() => page.evaluate(() => scrollY)).toBe(0);
  }
  expect(
    await page.evaluate(() => (window as unknown as { csp: string[] }).csp),
  ).toEqual([]);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.reload();
  await expect(page.locator(".v2-story")).toBeVisible();
  const still = await page.locator("[data-wallet-fold]").getAttribute("style");
  await page.evaluate(() => scrollTo(0, 1300));
  await expect(page.locator("[data-wallet-fold]")).toHaveAttribute(
    "style",
    still ?? "",
  );
  expect(
    await page.evaluate(() => (window as unknown as { csp: string[] }).csp),
  ).toEqual([]);
  expect(unexpected).toEqual([]);
});

test("supported views render without CSP violations or external/API/write requests", async ({
  page,
}) => {
  const violations: string[] = [],
    errors: string[] = [],
    unexpected: string[] = [];
  await page.exposeFunction("recordCsp", (s: string) => violations.push(s));
  await page.addInitScript(() =>
    document.addEventListener("securitypolicyviolation", (e) => {
      void (
        window as unknown as { recordCsp: (s: string) => Promise<void> }
      ).recordCsp(`${e.effectiveDirective}: ${e.blockedURI}`);
    }),
  );
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("request", (r) => {
    if (
      !r
        .url()
        .startsWith(
          `${new URL(process.env.SENTINEL_WEB_URL ?? "https://127.0.0.1:9448/").origin}/`,
        ) ||
      r.method() !== "GET" ||
      r.url().includes("/api/")
    )
      unexpected.push(r.url());
  });
  for (const [route, selector] of [
    ["/demo-payment", ".v2-dossier"],
    ["/app/transactions", ".ag-row"],
    [
      "/app/transactions/1e054580-49f1-48be-a7a4-a4d4cf23647d",
      ".risk-assessment-layout",
    ],
    ["/app/cases/73823607-ce2b-4090-9fd4-d1e3119f28d6", "[role=tabpanel]"],
    ["/app/model", "main"],
    ["/app/policy", "main"],
  ]) {
    await page.goto(`/#${route}`);
    await expect(page.locator(selector).first()).toBeVisible();
    if (route === "/app/transactions") {
      await page
        .getByLabel("Search by PayPal order or capture ID")
        .fill("SIM-ORDER-1D6383BB55B0BF");
      await page.getByRole("button", { name: "Search", exact: true }).click();
      await expect(page.locator(".ag-row")).toHaveCount(1);
    }
    if (route.startsWith("/app/cases/"))
      await expect(
        page.getByRole("list", { name: "Main factors behind this score" }),
      ).toBeVisible();
    if (route === "/app/model")
      await expect(
        page.getByText("Trained and tested on synthetic data only."),
      ).toBeVisible();
    if (route !== "/demo-payment")
      await expect(
        page.getByRole("note", { name: "Static demo" }),
      ).toBeVisible();
  }
  expect(violations).toEqual([]);
  expect(errors).toEqual([]);
  expect(unexpected).toEqual([]);
});

test("CSP blocks injected inline scripts", async ({ page }) => {
  await page.goto("/#/");
  await page.evaluate(() => {
    (window as unknown as { injected: boolean }).injected = false;
    const el = document.createElement("script");
    el.textContent = "window.injected = true";
    document.head.append(el);
  });
  expect(
    await page.evaluate(
      () => (window as unknown as { injected: boolean }).injected,
    ),
  ).toBe(false);
});
