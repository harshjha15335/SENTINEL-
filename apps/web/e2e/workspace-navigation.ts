import type { Page } from "@playwright/test";
/** Navigate the approved horizontal menu or its compact equivalent. */
export async function workspaceNavigate(page: Page, label: string) {
  const primary = page
    .getByRole("navigation", { name: "Primary" })
    .getByRole("link", { name: label, exact: true });
  if (await primary.isVisible()) {
    await primary.click();
    return;
  }
  const menu = page.locator(".workspace-menu");
  if ((await menu.getAttribute("open")) === null)
    await menu.locator("summary").click();
  await page
    .getByRole("navigation", { name: "All workspaces" })
    .getByRole("link", { name: label, exact: true })
    .click();
}
