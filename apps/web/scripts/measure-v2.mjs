// Run from apps/web. Local lab observations, never field Core Web Vitals.
import { chromium } from "@playwright/test";
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
const output = process.env.SENTINEL_V2_ARTIFACTS ?? "test-results/v2-artifacts";
mkdirSync(output, { recursive: true });
const executablePath =
  process.env.PLAYWRIGHT_CHROMIUM_PATH ??
  (existsSync("/usr/bin/chromium") ? "/usr/bin/chromium" : undefined);
const browser = await chromium.launch({
  ...(executablePath ? { executablePath } : {}),
});
const results = {
  browser: browser.version(),
  viewport: "1440x900",
  cpu: "unthrottled shared cloud executor",
  network: "localhost, no throttling",
  url: "production homepage /",
  runs: [],
};
for (let i = 0; i < 3; i++) {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
  });
  await context.addInitScript(() => {
    window.__v2Lab = { lcp: 0, cls: 0, longTasks: [] };
    new PerformanceObserver((list) => {
      for (const e of list.getEntries()) window.__v2Lab.lcp = e.startTime;
    }).observe({ type: "largest-contentful-paint", buffered: true });
    new PerformanceObserver((list) => {
      for (const e of list.getEntries())
        if (!e.hadRecentInput) window.__v2Lab.cls += e.value;
    }).observe({ type: "layout-shift", buffered: true });
    new PerformanceObserver((list) => {
      for (const e of list.getEntries())
        window.__v2Lab.longTasks.push(e.duration);
    }).observe({ type: "longtask", buffered: true });
  });
  const page = await context.newPage();
  await page.goto("http://127.0.0.1:4175/");
  await page.locator(".v2-story").waitFor();
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(300);
  const metrics = await page.evaluate(() => ({
    lcp: window.__v2Lab.lcp,
    cls: window.__v2Lab.cls,
    initialLongTasks: window.__v2Lab.longTasks,
  }));
  await page.evaluate(() => {
    window.__v2Lab.longTasks = [];
  });
  const frames = await page.evaluate(
    () =>
      new Promise((resolve) => {
        const deltas = [];
        let previous = performance.now(),
          count = 0;
        const step = (now) => {
          deltas.push(now - previous);
          previous = now;
          window.scrollTo(0, Math.min(0.999, count / 120) * innerHeight * 4);
          count++;
          if (count <= 120) requestAnimationFrame(step);
          else resolve(deltas);
        };
        requestAnimationFrame(step);
      }),
  );
  const sorted = frames.slice(1).sort((a, b) => a - b);
  metrics.frameMedianMs = sorted[Math.floor(sorted.length * 0.5)];
  metrics.frameP95Ms = sorted[Math.floor(sorted.length * 0.95)];
  metrics.framesOver50ms = sorted.filter((n) => n > 50).length;
  metrics.scrollLongTasks = await page.evaluate(() => window.__v2Lab.longTasks);
  results.runs.push(metrics);
  await context.close();
}
writeFileSync(`${output}/performance.json`, JSON.stringify(results, null, 2));
console.log(JSON.stringify(results));
await browser.close();
