// Detailed loading lab. Layout entries are recorded without masking DOM or changing inputs.
import { chromium } from "../../apps/web/node_modules/@playwright/test/index.mjs";
import { writeFileSync } from "node:fs";
const [origin, output, mode = "controlled"] = process.argv.slice(2);
if (new URL(origin).hostname !== "127.0.0.1")
  throw Error("Local TLS exception is loopback only");
const browser = await chromium.launch({
  executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH ?? "/usr/bin/chromium",
});
const runs = [];
for (const profile of [
  {
    name: "desktop",
    viewport: { width: 1440, height: 900 },
    cpu: mode === "stress" ? 4 : 1,
  },
  { name: "mobile", viewport: { width: 390, height: 844 }, cpu: 4 },
]) {
  const scenarios =
    mode === "routes"
      ? [
          ["dashboard", "/app", ".workspace-page-title"],
          [
            "case",
            "/app/cases/73823607-ce2b-4090-9fd4-d1e3119f28d6",
            ".risk-assessment-layout",
          ],
          ["model", "/app/model", ".workspace-page-title"],
        ]
      : [
          ["homepage", "/", ".v2-story"],
          ["transactions", "/app/transactions", ".ag-row"],
          [
            "recorded-risk",
            "/app/transactions/1e054580-49f1-48be-a7a4-a4d4cf23647d",
            ".risk-assessment-layout",
          ],
        ];
  for (const [scenario, path, selector] of scenarios) {
    for (let sample = 1; sample <= (mode === "routes" ? 1 : 3); sample++) {
      const context = await browser.newContext({
          viewport: profile.viewport,
          ignoreHTTPSErrors: true,
          isMobile: profile.name === "mobile",
          hasTouch: profile.name === "mobile",
        }),
        page = await context.newPage(),
        cdp = await context.newCDPSession(page);
      await cdp.send("Network.enable");
      await cdp.send("Network.setCacheDisabled", { cacheDisabled: true });
      await cdp.send("Emulation.setCPUThrottlingRate", { rate: profile.cpu });
      if (mode === "stress")
        await cdp.send("Network.emulateNetworkConditions", {
          offline: false,
          latency: 100,
          downloadThroughput: 200000,
          uploadThroughput: 93750,
        });
      const failures = [];
      page.on("request", (r) => {
        if (
          !r.url().startsWith(origin + "/") ||
          r.method() !== "GET" ||
          r.url().includes("/api/")
        )
          failures.push(`${r.method()} ${r.url()}`);
      });
      await page.addInitScript(() => {
        window.__stability = {
          lcp: 0,
          cls: 0,
          shifts: [],
          longTasks: [],
          fonts: [],
          grid: {},
        };
        const node = (n) =>
          n
            ? {
                tag: n.nodeName,
                id: n.id,
                className: n.className?.baseVal ?? n.className,
                text: n.textContent?.slice(0, 100),
              }
            : null;
        new PerformanceObserver((list) => {
          for (const e of list.getEntries())
            window.__stability.lcp = e.startTime;
        }).observe({ type: "largest-contentful-paint", buffered: true });
        new PerformanceObserver((list) => {
          for (const e of list.getEntries()) {
            if (!e.hadRecentInput) window.__stability.cls += e.value;
            window.__stability.shifts.push({
              time: e.startTime,
              value: e.value,
              hadRecentInput: e.hadRecentInput,
              sources: e.sources.map((s) => ({
                node: node(s.node),
                previous: s.previousRect.toJSON(),
                current: s.currentRect.toJSON(),
              })),
            });
          }
        }).observe({ type: "layout-shift", buffered: true });
        new PerformanceObserver((list) => {
          for (const e of list.getEntries())
            window.__stability.longTasks.push({
              start: e.startTime,
              duration: e.duration,
            });
        }).observe({ type: "longtask", buffered: true });
        document.fonts.addEventListener("loadingdone", (e) =>
          window.__stability.fonts.push({
            time: performance.now(),
            faces: e.fontfaces.map((f) => ({
              family: f.family,
              weight: f.weight,
            })),
          }),
        );
        const observer = new MutationObserver(() => {
          const grid = window.__stability.grid;
          if (!grid.wrapperMs && document.querySelector(".ag-root-wrapper"))
            grid.wrapperMs = performance.now();
          if (!grid.rowsMs && document.querySelector(".ag-row")) {
            grid.rowsMs = performance.now();
            observer.disconnect();
          }
        });
        observer.observe(document, { childList: true, subtree: true });
      });
      await page.goto(`${origin}/#${path}`);
      await page.locator(selector).first().waitFor();
      await page.evaluate(() => document.fonts.ready);
      const readyMs = await page.evaluate(() => performance.now());
      await page.waitForTimeout(500);
      const clsAtGate2BWindow = await page.evaluate(
        () => window.__stability.cls,
      );
      await page.waitForTimeout(1500);
      const metrics = await page.evaluate(() => ({
        ...window.__stability,
        resources: performance.getEntriesByType("resource").map((r) => ({
          name: r.name.split("/").pop(),
          start: r.startTime,
          end: r.responseEnd,
          encoded: r.encodedBodySize,
          decoded: r.decodedBodySize,
          transfer: r.transferSize,
        })),
        navigation: performance.getEntriesByType("navigation")[0].toJSON(),
      }));
      const row = {
        profile: profile.name,
        scenario,
        sample,
        cpuSlowdown: profile.cpu,
        network:
          mode === "stress"
            ? "100ms latency / 1.6Mbps down / 0.75Mbps up"
            : "unthrottled loopback",
        readyMs,
        clsAtGate2BWindow,
        ...metrics,
        unexpectedRequests: failures,
      };
      row.totalTransferredBytes =
        row.navigation.transferSize +
        row.resources.reduce((n, e) => n + e.transfer, 0);
      if (row.grid.wrapperMs && row.grid.rowsMs)
        row.grid.mountToFirstRowsMs = row.grid.rowsMs - row.grid.wrapperMs;
      const response = row.resources.find(
        (r) => r.name === "transactions.json",
      );
      if (response && row.grid.rowsMs)
        row.grid.responseEndToRowsMs = row.grid.rowsMs - response.end;
      runs.push(row);
      console.log(
        JSON.stringify({
          mode,
          profile: row.profile,
          scenario,
          sample,
          cls: row.cls,
          readyMs,
        }),
      );
      await context.close();
    }
  }
}
const summary = [];
for (const profile of ["desktop", "mobile"])
  for (const scenario of [...new Set(runs.map((r) => r.scenario))]) {
    const samples = runs.filter(
        (r) => r.profile === profile && r.scenario === scenario,
      ),
      median = (key) =>
        samples.map((r) => r[key]).sort((a, b) => a - b)[
          Math.floor(samples.length / 2)
        ];
    summary.push({
      profile,
      scenario,
      samples: samples.length,
      maxCls: Math.max(...samples.map((r) => r.cls)),
      medianReadyMs: median("readyMs"),
      medianObservedLcpMs: median("lcp"),
      medianTotalTransferredBytes: median("totalTransferredBytes"),
      maxLongTaskMs: Math.max(
        0,
        ...samples.flatMap((r) => r.longTasks.map((t) => t.duration)),
      ),
      medianTransferredResourceBytes: samples
        .map((r) => r.resources.reduce((n, e) => n + e.transfer, 0))
        .sort((a, b) => a - b)[Math.floor(samples.length / 2)],
    });
  }
const result = {
  mode,
  browser: browser.version(),
  environment:
    "Shared cloud executor; cold browser cache, warm loopback HTTPS server. Controlled matches Gate2B CPU/network profiles. Stress adds simulated CPU/network constraints; not real-device or field measurements.",
  observation:
    "CLS is all entries without recent input; both 500ms after readiness and extended 2s observation retained. No recent input is synthesized and no layout entries are suppressed.",
  gridTiming:
    "DOM wrapper appearance to first rows includes data wait and rendering, not isolated AG Grid CPU time. ResponseEnd-to-rows includes JSON parsing/rendering.",
  runs,
  summary,
  passesTarget: runs.every(
    (r) => r.cls <= 0.1 && r.unexpectedRequests.length === 0,
  ),
};
writeFileSync(output, JSON.stringify(result, null, 2));
console.log(JSON.stringify(summary));
await browser.close();
if (
  (mode !== "routes" && !result.passesTarget) ||
  runs.some((r) => r.unexpectedRequests.length)
)
  process.exitCode = 1;
