// Screenshot the tool tracker at desktop + phone widths.
const { chromium } = require('/opt/data/integrations/node/node_modules/playwright');
const OUT = '/opt/data/studio/tool-tracker/shots';
(async () => {
  const fs = require('fs');
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({
    executablePath: '/opt/data/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome',
    args: ['--no-sandbox'],
  });
  const shots = [
    { name: 'desktop-top', viewport: { width: 1440, height: 1000 }, full: false },
    { name: 'desktop-full', viewport: { width: 1440, height: 1000 }, full: true },
    { name: 'phone-top', viewport: { width: 390, height: 844 }, full: false, mobile: true },
  ];
  for (const s of shots) {
    const ctx = await browser.newContext({
      viewport: s.viewport, deviceScaleFactor: s.mobile ? 2 : 1,
      isMobile: !!s.mobile, hasTouch: !!s.mobile,
    });
    const page = await ctx.newPage();
    const errs = [];
    page.on('console', (m) => m.type() === 'error' && errs.push(m.text()));
    page.on('pageerror', (e) => errs.push(String(e)));
    await page.goto('http://127.0.0.1:9413/', { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: `${OUT}/${s.name}.png`, fullPage: s.full });
    console.log(s.name, 'errors:', errs.length ? errs.join(' | ') : 'none');
    await ctx.close();
  }
  await browser.close();
})();
