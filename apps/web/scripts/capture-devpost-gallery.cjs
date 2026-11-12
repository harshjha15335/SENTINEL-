/**
 * Capture REAL browser screenshots of the deployed SENTINEL staging website.
 *
 * Only uses the public pages and the explicitly scoped read-only judge demo.
 * Does not request payment creation, refunds, AI generations or admin endpoints.
 * Output: 15 genuine 1440x960 (3:2) JPEG screenshots for Devpost, under 5 MB.
 */
const { chromium } = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');

const BASE = 'https://sentinel-v2-staging.onrender.com';
const OUT = path.resolve(__dirname, '../devpost-gallery');
fs.mkdirSync(OUT, { recursive: true });
const entries = [];

async function capture(page, filename, route, { anchor, anchorText, offset = 0, scrollY, wait = 900 } = {}) {
  const url = BASE + route;
  const response = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  if (!response || response.status() >= 400) {
    throw new Error('Non-success navigation for ' + route + ': ' + response?.status());
  }
  await page.waitForTimeout(wait);
  if (anchor) {
    try {
      await page.locator(anchor).first().scrollIntoViewIfNeeded({ timeout: 8000 });
      await page.waitForTimeout(200);
    } catch {
      console.log('INFO: optional section not visible for ' + route + ': ' + anchor);
    }
  }
  if (anchorText) {
    await page.getByText(anchorText, { exact: false }).first().scrollIntoViewIfNeeded({ timeout: 10000 });
    await page.waitForTimeout(300);
  }
  if (scrollY) await page.evaluate((y) => window.scrollTo({ top: y, behavior: 'instant' }), scrollY);
  if (offset) await page.evaluate((y) => window.scrollBy(0, y), offset);
  await page.waitForTimeout(280);
  const filepath = path.join(OUT, filename + '.jpg');
  await page.screenshot({ path: filepath, type: 'jpeg', quality: 84, animations: 'allow', caret: 'hide' });
  const bytes = fs.statSync(filepath).size;
  if (bytes > 5 * 1024 * 1024) throw new Error(filename + ' exceeds Devpost 5MB limit');
  if (bytes < 20000) throw new Error(filename + ' is unexpectedly small');
  const text = (await page.locator('body').innerText()).slice(0, 260);
  entries.push({ name: filename + '.jpg', title: filename, route, bytes, origin: url, firstVisibleText: text });
  console.log('CAPTURED', entries.length, filename, route, bytes);
}

async function run() {
  const browser = await chromium.launch({ headless: true, args: ['--disable-dev-shm-usage'] });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 960 },
    deviceScaleFactor: 1,
    colorScheme: 'light',
    locale: 'en-US',
    reducedMotion: 'no-preference',
    serviceWorkers: 'block',
  });
  const page = await context.newPage();
  try {
    await capture(page, '01-follow-the-money-landing', '/', { wait: 2600 });
    await capture(page, '02-public-payment-dossier', '/demo-payment', { wait: 1600 });
    await page.goto(BASE + '/login', { waitUntil: 'domcontentloaded', timeout: 60000 });
    const demoButton = page.getByRole('button', { name: /one.click judge demo/i });
    await demoButton.waitFor({ state: 'visible', timeout: 20000 });
    await page.waitForTimeout(750);
    await demoButton.click();
    await page.waitForURL('**/app/demo', { timeout: 30000 });
    await page.locator('a[href^="/app/transactions/"]').first().waitFor({ timeout: 30000 });
    const transaction = await page.locator('a[href^="/app/transactions/"]').first().getAttribute('href');
    const casePath = await page.locator('a[href^="/app/cases/"]').first().getAttribute('href');
    if (!transaction || !casePath) throw new Error('Read-only demo guide does not expose a transaction and case');
    if (!/^\/app\/transactions\/[0-9a-f-]{36}$/.test(transaction)) throw new Error('Invalid synthetic payment link');
    if (!/^\/app\/cases\/[0-9a-f-]{36}$/.test(casePath)) throw new Error('Invalid synthetic review case link');
    console.log('Validated synthetic demo links', transaction, casePath);
    await capture(page, '03-wallet-animation-intro', '/intro', {
      wait: 1800, scrollY: 2280,
    });
    await capture(page, '04-read-only-judge-demo', '/app/demo');
    await capture(page, '05-command-center-dashboard', '/app', { wait: 1800 });
    await capture(page, '06-payments-explorer', '/app/transactions', { wait: 1400 });
    await capture(page, '07-transaction-risk-and-timeline', transaction, { anchor: '.risk-record', wait: 1800 });
    await capture(page, '08-fraud-review-queue', '/app/cases', { wait: 1500 });
    await capture(page, '09-investigation-findings-and-citations', casePath, {
      anchor: '[aria-label="Investigation findings"]', wait: 1800, offset: -150,
    });
    await capture(page, '10-private-evidence-and-packets', casePath + '?tab=evidence', {
      anchor: '#workspace-panel-evidence', wait: 1200,
    });
    await capture(page, '11-human-decisions-and-approvals', casePath + '?tab=decision', {
      anchor: '#workspace-panel-decision', wait: 1200,
    });
    await capture(page, '12-risk-model-and-shap', '/app/model', { wait: 1400 });
    await capture(page, '13-policy-lab-roc-and-thresholds', '/app/policy', {
      wait: 2000, anchorText: 'ROC · AUC',
    });
    await capture(page, '14-risk-monitoring', '/app/monitoring', {
      wait: 1800, anchorText: 'Current window',
    });
    await capture(page, '15-relationship-explorer', '/app/network', {
      wait: 1800, anchor: '[aria-label="Relationship diagram"]',
    });
    if (entries.length !== 15) throw new Error('Expected 15 images, received ' + entries.length);
    fs.writeFileSync(path.join(OUT, 'manifest.json'), JSON.stringify({
      createdAt: new Date().toISOString(), source: BASE, width: 1440, height: 960,
      allImagesAreWebsiteScreenshots: true, accountType: 'read-only synthetic judge demo',
      images: entries,
    }, null, 2));
    console.log('SUCCESS: 15 authentic SENTINEL captures, 1440x960 (3:2), each <5MB');
  } catch (error) {
    fs.writeFileSync(path.join(OUT, 'capture-error.txt'), String(error.stack || error));
    throw error;
  } finally {
    await browser.close();
  }
}

run().catch((error) => { console.error(error); process.exitCode = 1; });
