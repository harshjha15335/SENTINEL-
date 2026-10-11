import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

// Phase 4 vertical slice on a SYNTHETIC_DEMO high-risk case, without AI credentials:
// deterministic summary → evidence upload → packet → refund-intent request → admin approval.
const ANALYST = { email: "analyst@northwind.example", password: process.env.SENTINEL_E2E_ANALYST_PASSWORD ?? "" };
const ADMIN = { email: "admin@northwind.example", password: process.env.SENTINEL_E2E_ADMIN_PASSWORD ?? "" };
const SHOTS = process.env.SENTINEL_SCREENSHOT_DIR;

test.skip(!ANALYST.password || !ADMIN.password, "SENTINEL_E2E_ANALYST_PASSWORD and SENTINEL_E2E_ADMIN_PASSWORD are required");

async function signIn(page: Page, who: { email: string; password: string }) {
  await page.goto("/login");
  await page.getByLabel("Work email").fill(who.email);
  await page.getByLabel("Password").fill(who.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Command Center" })).toBeVisible();
}

async function audit(page: Page, name: string) {
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
  expect(results.violations, `${name}: ${results.violations.map((v) => `${v.id} (${v.nodes.length})`).join(", ")}`).toEqual([]);
}

async function noHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(1);
}

// A tiny valid PDF with a text layer.
function pdf(text: string): Buffer {
  const stream = `BT /F1 12 Tf 40 780 Td (${text}) Tj ET`;
  const objs = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    `<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`,
  ];
  let body = "%PDF-1.4\n";
  const offsets: number[] = [];
  objs.forEach((o, i) => {
    offsets.push(body.length);
    body += `${i + 1} 0 obj\n${o}\nendobj\n`;
  });
  const xref = body.length;
  body += `xref\n0 ${objs.length + 1}\n0000000000 65535 f \n`;
  for (const off of offsets) body += `${String(off).padStart(10, "0")} 00000 n \n`;
  body += `trailer\n<< /Size ${objs.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return Buffer.from(body, "latin1");
}

test("investigate, attach evidence, export a packet and approve refund intent", async ({ page }, info) => {
  test.setTimeout(120_000);
  await signIn(page, ANALYST);
  await page.getByRole("navigation", { name: "Primary" }).getByRole("link", { name: "Review Queue" }).click();
  await expect(page.getByRole("note", { name: "Review capacity warning" })).toBeVisible();
  // Each viewport works on its own case so runs do not collide.
  const index = info.project.name === "desktop" ? 2 : 3;
  await page.getByRole("list", { name: "Cases" }).getByRole("link").nth(index).click();
  await expect(page.getByRole("heading", { name: /risk payment needs review/ })).toBeVisible();
  const caseUrl = page.url();

  // 3. Verified payment and risk information.
  await expect(page.getByText("Investigation workbench ·")).toBeVisible();
  await expect(page.getByText(/Shadow policy:/)).toBeVisible();

  // 4. Investigation (deterministic: no AI credentials in this environment).
  await expect(page.getByText("AI provider not configured")).toBeVisible();
  await page.getByRole("button", { name: "Generate deterministic summary" }).click();
  const findings = page.getByRole("article", { name: "Investigation findings" });
  await expect(findings.getByText("Deterministic summary — AI provider unavailable", { exact: true })).toBeVisible({ timeout: 20_000 });
  await expect(findings.getByText("Rule-based")).toBeVisible();
  await expect(findings.getByText(/Verified facts \(\d+\)/)).toBeVisible();

  // 6. Evidence upload.
  await page.getByLabel("Upload evidence").setInputFiles({ name: "invoice-1001.pdf", mimeType: "application/pdf", buffer: pdf(`Invoice 1001 ${info.project.name} ${Date.now()}`) });
  await page.getByLabel("What is it?").selectOption("INVOICE");
  await page.getByRole("button", { name: "Upload", exact: true }).click();
  await expect(page.getByText("invoice-1001.pdf")).toBeVisible();
  await expect(page.getByRole("link", { name: "Download invoice-1001.pdf" })).toBeVisible();

  // 7. Evidence packet.
  await page.getByRole("button", { name: "Generate packet" }).click();
  const packetLink = page.getByRole("link", { name: /Download packet generated/ });
  await expect(packetLink).toBeVisible();
  const href = await packetLink.getAttribute("href");
  const resp = await page.request.get(href ?? "");
  expect(resp.status()).toBe(200);
  expect(resp.headers()["content-type"]).toBe("application/pdf");

  // 8. Approval request (refund intent; amount fixed by the server).
  await page.getByLabel(/Prepare refund/).check();
  await page.getByLabel("Justification").fill("High risk payer with earlier refunds; prepare refund for review.");
  await page.getByRole("button", { name: "Request approval" }).click();
  await expect(page.getByText(/You cannot decide your own request/)).toBeVisible();
  await audit(page, "workbench (analyst)");
  await noHorizontalOverflow(page);
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/${info.project.name}-9-workbench.png`, fullPage: true });

  // 9. Admin approves.
  await page.getByRole("button", { name: "Sign out" }).click();
  await signIn(page, ADMIN);
  await page.goto(caseUrl);
  await page.getByLabel("Decision note").fill("Snapshot and evidence reviewed.");
  await page.getByRole("button", { name: "Approve", exact: true }).click();
  await expect(page.getByText(/Approved by admin@northwind.example/)).toBeVisible();
  await expect(page.getByText(/no PayPal request was made/)).toBeVisible();

  // 10. Audit trail.
  const activity = page.getByRole("region", { name: "Activity" }).or(page.locator("section", { hasText: "Activity" }).last());
  for (const label of ["Investigation completed", "Evidence uploaded", "Evidence packet generated", "Approval requested", "Approval granted", "Approved action recorded (no payment executed)"]) {
    await expect(activity.getByText(label, { exact: true }).first()).toBeVisible();
  }
  await audit(page, "workbench (admin)");
  await noHorizontalOverflow(page);
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/${info.project.name}-10-approved.png`, fullPage: true });
});
