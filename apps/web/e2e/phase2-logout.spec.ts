import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
const password = process.env.SENTINEL_E2E_ANALYST_PASSWORD ?? "";
test.skip(!password, "Requires dedicated local fixture runtime");
async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Work email").fill("analyst@northwind.example");
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Sign out", exact: true }),
  ).toBeVisible();
}
for (const failure of ["503", "403", "network"]) {
  test(`logout ${failure} remains visibly failed, reloads authenticated and retries safely`, async ({
    page,
  }) => {
    await login(page);
    await page.route("**/api/v1/auth/logout", async (route) => {
      if (failure === "network") await route.abort("failed");
      else
        await route.fulfill({
          status: Number(failure),
          contentType: "application/json",
          body: JSON.stringify({
            error: { message: "Injected local logout failure" },
          }),
        });
    });
    await page.getByRole("button", { name: "Sign out", exact: true }).click();
    await expect(page.getByRole("alert")).toContainText(
      "Your session may still be active",
    );
    await expect(page).toHaveURL(/\/app$/);
    expect((await page.request.get("/api/v1/me")).status()).toBe(200);
    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBeTruthy();
    const retry = page.getByRole("button", {
      name: "Retry sign out",
      exact: true,
    });
    await retry.focus();
    await expect(retry).toBeFocused();
    await page.reload();
    await expect(
      page.getByRole("button", { name: "Sign out", exact: true }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Sign out", exact: true }).click();
    await expect(page.getByRole("alert")).toBeVisible();
    await page.unroute("**/api/v1/auth/logout");
    await page
      .getByRole("button", { name: "Retry sign out", exact: true })
      .press("Enter");
    await expect(
      page.getByRole("heading", { name: "Sign in to your workspace" }),
    ).toBeVisible();
    expect((await page.request.get("/api/v1/me")).status()).toBe(401);
    await page.reload();
    await expect(
      page.getByRole("heading", { name: "Sign in to your workspace" }),
    ).toBeVisible();
  });
}

test("server session expiry while logout is pending returns safely to sign-in", async ({
  page,
}) => {
  await login(page);
  await page.route("**/api/v1/auth/logout", async (route) => {
    // Revoke only this local fixture session, then simulate losing its response.
    const revoked = await route.fetch();
    expect(revoked.status()).toBe(204);
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ error: { message: "Lost logout response" } }),
    });
  });
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Sign in to your workspace" }),
  ).toBeVisible();
  expect((await page.request.get("/api/v1/me")).status()).toBe(401);
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Sign in to your workspace" }),
  ).toBeVisible();
});
