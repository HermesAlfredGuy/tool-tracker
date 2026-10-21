// Section screenshots + layout diagnostics.
const { chromium } = require('/opt/data/integrations/node/node_modules/playwright');
const OUT = '/opt/data/studio/tool-tracker/shots';
(async () => {
  const browser = await chromium.launch({
    executablePath: '/opt/data/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome',
    args: ['--no-sandbox'],
  });
  for (const vp of [{ w: 1440, h: 1000, tag: 'd' }, { w: 390, h: 844, tag: 'm' }]) {
    const ctx = await browser.newContext({ viewport: { width: vp.w, height: vp.h }, deviceScaleFactor: 1 });
    const page = await ctx.newPage();
    await page.goto('http://127.0.0.1:9413/', { waitUntil: 'networkidle' });
    const diag = await page.evaluate(() => {
      const out = { docScroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth, over: [] };
      document.querySelectorAll('section, table, input, .proj, .stats, nav.toc').forEach((el) => {
        const r = el.getBoundingClientRect();
        if (r.right > window.innerWidth + 1 || r.left < -1) out.over.push(el.tagName + '#' + el.id + '.' + el.className + ' right=' + Math.round(r.right));
      });
      return out;
    });
    console.log(vp.tag, JSON.stringify(diag));
    for (const id of ['skills', 'services', 'crons', 'projects', 'runtimes']) {
      const el = await page.$('#' + id);
      if (el) await el.screenshot({ path: `${OUT}/${vp.tag}-${id}.png` });
    }
    await ctx.close();
  }
  await browser.close();
})();
