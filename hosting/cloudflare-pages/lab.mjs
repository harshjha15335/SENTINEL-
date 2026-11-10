// Local lab only: warm preview server, cold browser caches, no CDN/real handset inference.
import { chromium } from "../../apps/web/node_modules/@playwright/test/index.mjs";
import { writeFileSync } from "node:fs";
const [
  origin = "https://127.0.0.1:9448",
  output = "/tmp/sentinel-host-lab.json",
] = process.argv.slice(2);
if (new URL(origin).hostname !== "127.0.0.1")
  throw Error("This TLS-exception lab is loopback only");
const browser = await chromium.launch({
  executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH ?? "/usr/bin/chromium",
});
const runs = [];
for (const profile of [
  { name: "desktop", viewport: { width: 1440, height: 900 }, cpu: 1 },
  { name: "mobile", viewport: { width: 390, height: 844 }, cpu: 4 },
]) {
  for (const [scenario, path, selector] of [
    ["homepage", "/", ".v2-story"],
    ["transactions", "/app/transactions", ".ag-row"],
    [
      "recorded-risk",
      "/app/transactions/1e054580-49f1-48be-a7a4-a4d4cf23647d",
      ".risk-assessment-layout",
    ],
  ]) {
    for (let sample = 1; sample <= 3; sample++) {
      const context = await browser.newContext({
        viewport: profile.viewport,
        ignoreHTTPSErrors: true,
        isMobile: profile.name === "mobile",
        hasTouch: profile.name === "mobile",
      });
      const page = await context.newPage(),
        cdp = await context.newCDPSession(page);
      await cdp.send("Network.enable");
      await cdp.send("Network.setCacheDisabled", { cacheDisabled: true });
      await cdp.send("Emulation.setCPUThrottlingRate", { rate: profile.cpu });
      await page.addInitScript(() => {
        window.__hostLab = { lcp: 0, cls: 0, longTasks: [] };
        new PerformanceObserver((list) => {
          for (const e of list.getEntries()) window.__hostLab.lcp = e.startTime;
        }).observe({ type: "largest-contentful-paint", buffered: true });
        new PerformanceObserver((list) => {
          for (const e of list.getEntries())
            if (!e.hadRecentInput) window.__hostLab.cls += e.value;
        }).observe({ type: "layout-shift", buffered: true });
        new PerformanceObserver((list) => {
          for (const e of list.getEntries())
            window.__hostLab.longTasks.push(e.duration);
        }).observe({ type: "longtask", buffered: true });
      });
      await page.goto(`${origin}/#${path}`);
      await page.locator(selector).first().waitFor();
      await page.evaluate(() => document.fonts.ready);
      const readyMs = await page.evaluate(() => performance.now());
      await page.waitForTimeout(500);
      const metrics = await page.evaluate(() => ({
        ...window.__hostLab,
        resources: performance
          .getEntriesByType("resource")
          .map((e) => ({
            name: e.name.split("/").pop(),
            encoded: e.encodedBodySize,
            decoded: e.decodedBodySize,
            transfer: e.transferSize,
          })),
        navigation: performance.getEntriesByType("navigation")[0].toJSON(),
      }));
      runs.push({
        profile: profile.name,
        cpuSlowdown: profile.cpu,
        scenario,
        sample,
        readyMs,
        ...metrics,
      });
      await context.close();
    }
  }
}
const summary = [];
for (const profile of ["desktop", "mobile"])
  for (const scenario of ["homepage", "transactions", "recorded-risk"]) {
    const sample = runs.filter(
        (r) => r.profile === profile && r.scenario === scenario,
      ),
      median = (key) => sample.map((r) => r[key]).sort((a, b) => a - b)[1];
    summary.push({
      profile,
      scenario,
      samples: 3,
      medianReadyMs: median("readyMs"),
      medianObservedLcpMs: median("lcp") || null,
      maxObservedCls: Math.max(...sample.map((r) => r.cls)),
      medianEncodedResourceBytes: sample
        .map((r) => r.resources.reduce((n, e) => n + e.encoded, 0))
        .sort((a, b) => a - b)[1],
    });
  }
const result = {
  browser: browser.version(),
  environment:
    "Shared cloud executor, warm loopback HTTPS preview with Brotli, cold browser caches. Mobile viewport + simulated 4x CPU slowdown. No network throttling, CDN, physical device or field CWV measurements.",
  runs,
  summary,
};
writeFileSync(output, JSON.stringify(result, null, 2));
console.log(JSON.stringify(summary));
await browser.close();
