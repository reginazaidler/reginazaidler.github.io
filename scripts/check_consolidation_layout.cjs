// Read-only browser checks. Never submit a contact form or contact external services.
const { chromium } = require(process.env.SITE_PLAYWRIGHT_MODULE || 'playwright');
const fs = require('node:fs/promises');
const assert = require('node:assert/strict');
const output = '/tmp/consolidation-layout-review';
const origin = 'http://127.0.0.1:8765';
const redirects = {
  'check-insurance-policies.html': 'insurance-double-coverage.html',
  'travel-insurance-check-before-flight.html': 'travel-insurance-abroad.html',
  'tsunami-in-japan-insurance-guide.html': 'travel-insurance-abroad.html',
};

(async () => {
  await fs.mkdir(output, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const results = [];
  try {
    for (const width of [1440, 390]) {
      const context = await browser.newContext({ viewport: { width, height: 1000 } });
      await context.route('**/*', route => {
        const host = new URL(route.request().url()).hostname;
        return ['127.0.0.1', 'fonts.googleapis.com', 'fonts.gstatic.com', 'cdn.tailwindcss.com'].includes(host)
          ? route.continue() : route.abort();
      });
      const page = await context.newPage();
      for (const [file, section] of [
        ['articles.html', '#cat-insurance'],
        ['insurance-double-coverage.html', '#policy-checklist'],
        ['travel-insurance-abroad.html', '#before-flight'],
        ['about.html', null],
      ]) {
        const response = await page.goto(`${origin}/${file}`, { waitUntil: 'networkidle' });
        assert.equal(response.status(), 200, file);
        await page.evaluate(() => document.fonts.ready);
        const layout = await page.evaluate(() => ({
          viewport: innerWidth,
          document: document.documentElement.scrollWidth,
          h1: document.querySelector('h1')?.innerText,
        }));
        assert.ok(layout.h1, `${file}: missing H1`);
        assert.ok(layout.document <= layout.viewport + 1, `${file} at ${width}px overflows: ${layout.document}`);
        await page.screenshot({ path: `${output}/${width}-${file}-top.png` });
        if (section) {
          await page.locator(section).scrollIntoViewIfNeeded();
          await page.screenshot({ path: `${output}/${width}-${file}-section.png` });
        }
        if (file === 'articles.html') {
          const categories = await page.locator('details[id^="cat-"]').evaluateAll(nodes => nodes.map(node => ({
            id: node.id, count: node.querySelectorAll('article.article-card').length,
            label: node.querySelector('.articles-accordion__hint').textContent,
          })));
          for (const category of categories) assert.equal(parseInt(category.label, 10), category.count);
          const itemCount = await page.locator('script[type="application/ld+json"]').evaluateAll(nodes => {
            const schemas = nodes.flatMap(node => { const value = JSON.parse(node.textContent); return value['@graph'] || [value]; });
            return schemas.find(node => node['@type'] === 'ItemList').itemListElement.length;
          });
          assert.equal(categories.reduce((total, category) => total + category.count, 0), itemCount);
          const category = page.locator('#cat-insurance');
          await category.locator('summary').click();
          assert.equal(await category.evaluate(node => node.open), false);
          await category.locator('summary').click();
          assert.equal(await category.evaluate(node => node.open), true);
        }
        results.push({ file, width, layout });
      }
      for (const [oldFile, target] of Object.entries(redirects)) {
        await page.goto(`${origin}/${oldFile}`, { waitUntil: 'domcontentloaded' });
        await page.waitForURL(`${origin}/${target}`);
        assert.equal(await page.locator('link[rel="canonical"]').getAttribute('href'), `https://vainzof.co.il/${target}`);
        results.push({ oldFile, target, width, browserRedirectPassed: true });
      }
      await context.close();
    }
    await fs.writeFile(`${output}/results.json`, JSON.stringify(results, null, 2));
    console.log('Desktop/mobile layouts, category interactions and three browser redirects passed.');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
