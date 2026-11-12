import { expect, test, type Page } from "@playwright/test";

const widths = [
  { width: 1920, height: 1080 },
  { width: 1440, height: 900 },
  { width: 1024, height: 768 },
  { width: 768, height: 1024 },
  { width: 390, height: 844 },
  { width: 360, height: 800 },
];

async function verifyDossierBounds(page: Page) {
  const findings = await page.evaluate(() => {
    const dossier = document.querySelector<HTMLElement>(".v2-dossier");
    if (!dossier) return ["Missing dossier"];
    const selectors = [
      ".v2-dossier-header h2",
      ".v2-dossier-header .v2-eyebrow",
      ".v2-record-status",
      ".v2-record-status .v2-classification",
      ".v2-evidence-ledger strong",
      ".v2-risk .v2-section-label",
      ".v2-risk .v2-score",
      ".v2-factors li span",
      ".v2-factors li strong",
      ".v2-review-note span",
      ".v2-fact-grid dd",
      ".v2-context-note p",
      ".v2-dossier-foot",
    ];
    const issues: string[] = [];
    const outer = dossier.getBoundingClientRect();
    for (const selector of selectors) {
      for (const target of dossier.querySelectorAll<HTMLElement>(selector)) {
        const rect = target.getBoundingClientRect();
        const parent = target.closest<HTMLElement>(".v2-risk") ?? dossier;
        const bounds = parent.getBoundingClientRect();
        if (
          rect.left < bounds.left - 2 ||
          rect.right > bounds.right + 2 ||
          rect.top < bounds.top - 2 ||
          rect.bottom > bounds.bottom + 2
        ) {
          issues.push(selector);
        }
        if (rect.left < outer.left - 2 || rect.right > outer.right + 2) {
          issues.push(selector + " beyond dossier");
        }
      }
    }
    if (document.documentElement.scrollWidth > innerWidth + 1)
      issues.push("page horizontal overflow");
    return issues;
  });
  expect(findings).toEqual([]);
}

for (const size of widths) {
  test("payment dossier retains readable margins at " + size.width + "x" + size.height, async ({
    page,
  }) => {
    await page.setViewportSize(size);
    await page.goto("/demo-payment");
    await expect(page.locator(".v2-dossier")).toBeVisible();
    await page.evaluate(() => document.fonts.ready);
    await verifyDossierBounds(page);
    await page.getByRole("button", { name: "02 Established pattern" }).click();
    await verifyDossierBounds(page);
    await page.getByRole("button", { name: "timeline 02" }).click();
    await expect(page.getByText("Event timeline")).toBeVisible();
    await page.getByRole("button", { name: "overview 01" }).click();
    await verifyDossierBounds(page);
  });
}

for (const size of [
  { width: 1440, height: 900 },
  { width: 1280, height: 720 },
]) {
  test("wallet edition does not overlap chapter glass at " + size.width + "x" + size.height, async ({
    page,
  }) => {
    await page.setViewportSize(size);
    await page.goto("/");
    await expect(page.locator(".v2-story-edition")).toBeVisible();
    await page.evaluate(() => document.fonts.ready);
    const edition = await page.locator(".v2-story-edition").boundingBox();
    const chapter = await page.locator(".v2-scene-copy").boundingBox();
    expect(edition).not.toBeNull();
    expect(chapter).not.toBeNull();
    if (!edition || !chapter) return;
    expect(chapter.y - (edition.y + edition.height)).toBeGreaterThanOrEqual(16);
    expect(edition.x).toBeGreaterThanOrEqual(0);
    expect(edition.x + edition.width).toBeLessThanOrEqual(size.width + 1);
  });
}
