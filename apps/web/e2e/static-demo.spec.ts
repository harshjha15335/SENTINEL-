import { workspaceNavigate } from "./workspace-navigation";
import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

// The GitHub Pages build (VITE_STATIC_DEMO=true). Point SENTINEL_WEB_URL at its root, including
// the repository path, e.g. http://127.0.0.1:4173/SENTINEL-/ (see docs/DEPLOYMENT.md).
test.skip(
  process.env.SENTINEL_STATIC_DEMO !== "true",
  "SENTINEL_STATIC_DEMO=true is required",
);

function staticRoute(path: string) {
  return process.env.SENTINEL_STATIC_HASH === "true"
    ? `./#${path}`
    : `.${path}`;
}

async function audit(page: Page, name: string) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(
    results.violations,
    `${name}: ${results.violations.map((v) => `${v.id} (${v.nodes.length})`).join(", ")}`,
  ).toEqual([]);
}

async function noHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - window.innerWidth,
  );
  expect(overflow).toBeLessThanOrEqual(1);
}

async function expectBanner(page: Page) {
  const banner = page.getByRole("note", { name: "Static demo" });
  await expect(banner).toContainText("Static demo, read only.");
  await expect(banner).toContainText("SYNTHETIC_DEMO");
  await expect(banner).toContainText("no PayPal call is made");
}

test("opens read-only without signing in, with the static demo banner", async ({
  page,
}) => {
  await page.goto(staticRoute("/app"));
  await expect(
    page.getByRole("heading", { name: "Command Center" }),
  ).toBeVisible();
  await expectBanner(page);
  await expect(page.getByRole("button", { name: "Sign out" })).toHaveCount(0);
  await audit(page, "command center");
  await noHorizontalOverflow(page);
});

test("review queue, case, transaction and model card come from the snapshot", async ({
  page,
}) => {
  await page.goto(staticRoute("/app"));
  await workspaceNavigate(page, "Investigations");
  await expect(
    page.getByRole("heading", { name: "Review queue" }),
  ).toBeVisible();
  const first = page
    .getByRole("list", { name: "Cases" })
    .getByRole("link")
    .first();
  await expect(first).toBeVisible();
  await audit(page, "review queue");
  await noHorizontalOverflow(page);

  await first.click();
  await expect(
    page.getByRole("heading", { name: /risk payment needs review/ }),
  ).toBeVisible();
  await expect(
    page.getByText("Model-generated", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("list", { name: "Main factors behind this score" }),
  ).toBeVisible();
  // A viewer cannot act on cases, and the static build has no server to act on anyway.
  await expect(page.getByRole("button", { name: /claim/i })).toHaveCount(0);
  await expectBanner(page);
  await audit(page, "case detail");

  await workspaceNavigate(page, "Transactions");
  await expect(page.locator(".ag-row").first()).toBeVisible();
  await audit(page, "transactions");

  await workspaceNavigate(page, "Risk Intelligence");
  await expect(
    page.getByText("Trained and tested on synthetic data only."),
  ).toBeVisible();
  await audit(page, "risk model");
});

test("deep links load through the Pages 404 fallback", async ({ page }) => {
  await page.goto(staticRoute("/model"));
  await expect(page.getByRole("heading", { name: "Risk model" })).toBeVisible();
  await page.goto(staticRoute("/cases/00000000-0000-0000-0000-000000000000"));
  await expect(page.getByText(/not found/i).first()).toBeVisible();
  await page.goto(staticRoute("/app/transactions/invalid-id"));
  await expect(
    page.getByText("Transaction not found", { exact: true }),
  ).toBeVisible();
});

const SERVICE_ROUTES = [
  "policy",
  "monitoring",
  "disputes",
  "refunds",
  "network",
  "checkout",
  "settings",
  "demo",
  "operations",
];

test("service-only deep links explain availability without API calls or writes", async ({
  page,
}) => {
  const requests: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/api/") || request.method() !== "GET")
      requests.push(`${request.method()} ${request.url()}`);
  });
  for (const route of SERVICE_ROUTES) {
    await page.goto(staticRoute(`/${route}?case=demo&review=1`));
    await expect(page.getByText(/Requires the full application/)).toBeVisible();
    await expect(
      page.getByText("Resource not found", { exact: true }),
    ).toHaveCount(0);
    expect(page.url()).toContain("case=demo&review=1");
    await expect(
      page.getByRole("link", { name: "Return to Command Center" }),
    ).toBeVisible();
    await noHorizontalOverflow(page);
  }
  await audit(page, "unavailable service");
  await page.getByRole("link", { name: "Return to Command Center" }).click();
  await expect(
    page.getByRole("heading", { name: "Command Center" }),
  ).toBeVisible();
  await page.goBack();
  await expect(page.getByText(/Requires the full application/)).toBeVisible();
  await page.goForward();
  await expect(
    page.getByRole("heading", { name: "Command Center" }),
  ).toBeVisible();
  expect(requests).toEqual([]);
});

test("original missing-reference case opens its payment and safe case tabs", async ({
  page,
}) => {
  const requests: string[] = [];
  page.on("request", (r) => {
    if (r.url().includes("/api/") || r.method() !== "GET")
      requests.push(r.url());
  });
  await page.goto(
    staticRoute("/app/cases/73823607-ce2b-4090-9fd4-d1e3119f28d6?tab=evidence"),
  );
  await expect(
    page.getByText(/Requires the full application/).filter({ visible: true }),
  ).toBeVisible();
  await page.getByRole("tab", { name: "Decision & approvals" }).click();
  await expect(
    page.getByText(/Requires the full application/).filter({ visible: true }),
  ).toBeVisible();
  await page.getByRole("tab", { name: "Notes & activity" }).click();
  await expect(
    page.getByRole("heading", { name: "Activity", exact: true }),
  ).toBeVisible();
  await page.getByRole("tab", { name: "Investigation", exact: true }).click();
  await page.getByRole("link", { name: "Open payment", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "$249.00", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("SIM-ORDER-1D6383BB55B0BF", { exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "$249.00", exact: true }),
  ).toBeVisible();
  await noHorizontalOverflow(page);
  expect(requests).toEqual([]);
});

test("public homepage and demo never load merchant data; unknown routes offer recovery", async ({
  page,
}) => {
  const merchantRequests: string[] = [];
  page.on("request", (r) => {
    if (/\/api\/|\/demo-data\//.test(r.url())) merchantRequests.push(r.url());
  });
  await page.goto(staticRoute("/"));
  await expect(
    page.getByRole("heading", { name: /Every payment/ }),
  ).toBeVisible();
  await page.goto(staticRoute("/demo-payment"));
  await expect(
    page.getByRole("heading", { name: "Payment dossier." }),
  ).toBeVisible();
  expect(merchantRequests).toEqual([]);
  await page.goto(staticRoute("/app/unknown-workspace"));
  await expect(
    page.getByText("The address does not match a SENTINEL workspace."),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Back to Command Center" }),
  ).toBeVisible();
});
