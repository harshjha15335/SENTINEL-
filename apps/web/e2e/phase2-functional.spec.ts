import { expect, test, type Page } from "@playwright/test";
const password = process.env.SENTINEL_E2E_ANALYST_PASSWORD ?? "";
test.skip(!password, "Requires the dedicated local Phase 2 fixture runtime");
async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Work email").fill("analyst@northwind.example");
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Command Center", exact: true }),
  ).toBeVisible();
}
test("legacy deep link retains its query/hash through sign-in and canonical refresh", async ({
  page,
}) => {
  const id = "8891b311-1c44-4b99-95a5-45c3f3ba8be5";
  await page.goto(`/transactions/${id}?context=review#record`);
  await expect(
    page.getByRole("heading", { name: "Sign in to your workspace" }),
  ).toBeVisible();
  await page.getByLabel("Work email").fill("analyst@northwind.example");
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(
    new RegExp(`/app/transactions/${id}\\?context=review#record$`),
  );
  await expect(
    page.getByRole("heading", { name: "$1,200.00", exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "$1,200.00", exact: true }),
  ).toBeVisible();
});
test("transaction filters, pagination, page sorting and keyboard entry use the preserved services", async ({
  page,
}) => {
  await login(page);
  await page.goto("/app/transactions");
  await expect(page.locator(".ag-row").first()).toBeVisible();
  const filtered = page.waitForResponse(
    (r) =>
      r.url().includes("/api/v1/transactions?") &&
      r.url().includes("status=CAPTURED"),
  );
  await page.getByLabel("Status", { exact: true }).selectOption("CAPTURED");
  expect((await filtered).ok()).toBeTruthy();
  const origin = page.waitForResponse(
    (r) =>
      r.url().includes("/api/v1/transactions?") &&
      r.url().includes("data_origin=SYNTHETIC_DEMO"),
  );
  await page
    .getByLabel("Origin", { exact: true })
    .selectOption("SYNTHETIC_DEMO");
  expect((await origin).ok()).toBeTruthy();
  const next = page.waitForResponse(
    (r) =>
      r.url().includes("/api/v1/transactions?") &&
      r.url().includes("offset=25"),
  );
  await page.getByRole("button", { name: "Next page", exact: true }).click();
  expect((await next).ok()).toBeTruthy();
  await expect(page).toHaveURL(/page=1/);
  await page
    .getByRole("button", { name: "Previous page", exact: true })
    .click();
  const amount = page.locator('.ag-header-cell[col-id="amount_minor"]');
  await amount.click();
  await expect(amount).toHaveAttribute("aria-sort", "ascending");
  const cell = page.locator(".ag-row").first().locator(".ag-cell").first();
  await cell.focus();
  await cell.press("Enter");
  await expect(page).toHaveURL(/\/app\/transactions\/[a-f0-9-]+$/);
  await expect(
    page.getByRole("heading", { name: "Risk assessment", exact: true }),
  ).toBeVisible();
});
test("private data errors remain errors and session expiry returns to sign-in", async ({
  page,
}) => {
  await login(page);
  await page.route("**/api/v1/transactions?**", (r) =>
    r.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({
        error: {
          code: "unavailable",
          message: "Transaction service temporarily unavailable",
        },
      }),
    }),
  );
  await page.goto("/app/transactions");
  await expect(page.getByRole("alert")).toContainText(
    "Transaction service temporarily unavailable",
    { timeout: 15000 },
  );
  await expect(page.locator(".ag-row")).toHaveCount(0);
  await page.unroute("**/api/v1/transactions?**");
  await page.route(
    "**/api/v1/transactions/8891b311-1c44-4b99-95a5-45c3f3ba8be5",
    (r) =>
      r.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({
          error: { code: "unauthenticated", message: "Session expired" },
        }),
      }),
  );
  await page.goto("/app/transactions/8891b311-1c44-4b99-95a5-45c3f3ba8be5");
  await expect(page).toHaveURL(/\/login$/);
  await expect(
    page.getByRole("heading", { name: "Sign in to your workspace" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "$1,200.00", exact: true }),
  ).toHaveCount(0);
});
test("public home and demo do not request private services and expose distinct entry actions", async ({
  page,
}) => {
  const requests: string[] = [];
  page.on("request", (r) => {
    if (r.url().includes("/api/")) requests.push(r.url());
  });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Every payment has a story." }),
  ).toBeVisible();
  await expect(
    page
      .locator(".v2-scene-copy,.v2-compact-hero")
      .getByRole("link", { name: "Explore simulated demo" }),
  ).toBeVisible();
  await page
    .locator(".v2-scene-copy,.v2-compact-hero")
    .getByRole("link", { name: "Explore simulated demo" })
    .click();
  await expect(page).toHaveURL(/\/demo-payment$/);
  await expect(
    page.getByRole("article", { name: "Payment dossier" }),
  ).toBeVisible();
  expect(requests).toEqual([]);
  if (await page.locator(".v2-global-nav").isVisible()) {
    await page
      .getByRole("navigation", { name: "Demo workspace" })
      .getByRole("link", { name: "Transactions", exact: true })
      .click();
  } else {
    await page.locator(".v2-mobile-menu summary").click();
    await page
      .getByRole("navigation", { name: "Mobile workspace" })
      .getByRole("link", { name: "Transactions", exact: true })
      .click();
  }
  await expect(page).toHaveURL(/\/login$/);
});

test("shadow policy snapshot is submitted and independently approved without serving activation", async ({
  page,
}) => {
  test.setTimeout(150000);
  await login(page);
  const before = await (await page.request.get("/api/v1/risk/model")).json();
  await page.goto("/app/policy");
  const name = `V2 parity ${Date.now()} ${test.info().project.name}`;
  await page.getByLabel("Policy name", { exact: true }).fill(name);
  await page
    .getByLabel("Rationale", { exact: true })
    .fill(
      "Validate the reviewed policy workflow without changing any serving threshold.",
    );
  const saved = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/v1/policy-lab/drafts") &&
      r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Save proposed snapshot" }).click();
  expect((await saved).ok()).toBeTruthy();
  const item = page.locator("li").filter({ hasText: name }).last();
  await item
    .getByRole("button", { name: "Submit for independent review" })
    .click();
  await expect(
    item.getByText("PENDING_APPROVAL", { exact: true }),
  ).toBeVisible();
  await expect(
    item.getByRole("button", { name: "Approve shadow proposal" }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await page.getByLabel("Work email").fill("admin@northwind.example");
  await page
    .getByLabel("Password", { exact: true })
    .fill(process.env.SENTINEL_E2E_ADMIN_PASSWORD ?? "");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();
  await page.goto("/app/policy");
  const adminItem = page.locator("li").filter({ hasText: name }).last();
  await adminItem
    .getByRole("button", { name: "Approve shadow proposal" })
    .click();
  await expect(adminItem.getByText("APPROVED", { exact: true })).toBeVisible();
  const after = await (await page.request.get("/api/v1/risk/model")).json();
  expect(after.thresholds).toEqual(before.thresholds);
  await expect(page.getByRole("button", { name: /activate/i })).toHaveCount(0);
});
test("case claim, note, rescore, dispute draft, resolution and refund approval retain their boundaries", async ({
  page,
}) => {
  test.setTimeout(180000);
  await login(page);
  const cases = await (
    await page.request.get("/api/v1/cases?status=OPEN&limit=25&offset=0")
  ).json();
  const refunds = await (await page.request.get("/api/v1/refunds")).json();
  const used = new Set(refunds.map((r: { case_id: string }) => r.case_id));
  const chosen = cases.items.find(
    (c: { id: string; assignee: unknown }) => !c.assignee && !used.has(c.id),
  );
  expect(chosen).toBeTruthy();
  const id = chosen.id;
  await page.goto(`/app/cases/${id}`);
  const scoring = page.waitForResponse(
    (r) => r.url().includes("/risk") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Re-score", exact: true }).click();
  expect((await scoring).ok()).toBeTruthy();
  await page.getByRole("tab", { name: "Decision & approvals" }).click();
  await page
    .getByRole("button", { name: "Claim for review", exact: true })
    .click();
  await expect(
    page.getByText("Assigned to", { exact: false }).first(),
  ).toBeVisible();
  await page.getByRole("tab", { name: "Notes & activity" }).click();
  const note = `V2 action parity ${Date.now()}`;
  await page.getByLabel("Add a note", { exact: true }).fill(note);
  await page.getByRole("button", { name: "Add note", exact: true }).click();
  await expect(page.getByText(note, { exact: true })).toBeVisible();
  await page.goto(`/app/disputes?case=${id}`);
  const created = page.waitForResponse(
    (r) =>
      r.url().includes("/disputes/demo") && r.request().method() === "POST",
  );
  await page.getByLabel("Demo case ID", { exact: true }).fill(id);
  await page
    .getByRole("button", { name: "Create labelled demo dispute" })
    .click();
  expect((await created).ok()).toBeTruthy();
  await expect(
    page.getByRole("heading", { name: "Dispute context" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Assign to me" }).click();
  const draft = page.waitForResponse(
    (r) => r.url().endsWith("/drafts") && r.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Prepare deterministic draft" })
    .click();
  expect((await draft).ok()).toBeTruthy();
  const download = page
    .getByRole("link", { name: "Download private draft PDF" })
    .first();
  await expect(download).toBeVisible();
  const pdf = await page.request.get(
    (await download.getAttribute("href")) ?? "",
  );
  expect(pdf.ok()).toBeTruthy();
  expect(pdf.headers()["content-type"]).toContain("application/pdf");
  await expect(
    page.getByText("External submission is disabled."),
  ).toBeVisible();
  await page.goto(`/app/refunds?case=${id}`);
  await page.getByLabel("Partial amount (minor units)").fill("1");
  const request = page.waitForResponse(
    (r) =>
      r.url().endsWith(`/cases/${id}/refunds`) &&
      r.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Request independent approval" })
    .click();
  const requestResponse = await request;
  expect(requestResponse.ok()).toBeTruthy();
  const refund = await requestResponse.json();
  await expect(
    page.getByText(refund.snapshot_sha256, { exact: false }),
  ).toBeVisible();
  await page.goto(`/app/cases/${id}?tab=decision`);
  await page.getByRole("radio", { name: /^Legitimate/ }).check();
  await page
    .getByLabel("Reasoning", { exact: true })
    .fill(
      "Synthetic fixture reviewed for V2 parity; resolution changes no payment.",
    );
  await page.getByRole("button", { name: "Resolve case", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Outcome", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await page.getByLabel("Work email").fill("admin@northwind.example");
  await page
    .getByLabel("Password", { exact: true })
    .fill(process.env.SENTINEL_E2E_ADMIN_PASSWORD ?? "");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();
  await page.goto("/app/refunds");
  const card = page
    .locator("section.workspace-section")
    .filter({ hasText: refund.snapshot_sha256 });
  await card
    .getByRole("button", { name: "Approve intent", exact: true })
    .click();
  await expect(
    card.getByText(/Approved intent\. Financial execution/),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: /execute refund|submit refund/i }),
  ).toHaveCount(0);
  const final = await (await page.request.get("/api/v1/refunds")).json();
  const recorded = final.find((r: { id: string }) => r.id === refund.id);
  expect(recorded.status).toBe("APPROVED");
  expect(recorded.submission_started).toBeFalsy();
  expect(recorded.provider_refund_id).toBeNull();
});
