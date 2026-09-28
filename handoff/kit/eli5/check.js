// Overlap and fit check for an explainer page (Thread manager, 2026-09-28).
// Usage: NODE_PATH=$(npm root -g) node handoff/kit/eli5/check.js page.html
// Prints, for 400 px light and 720 px dark: SVG labels that leave their viewBox (OUT), labels that overlap (OVL),
// and the page's scroll width (must equal the viewport width). Saves page-400.png next to the page for a look.
const { chromium } = require('playwright');
const fs = require('fs');
const f = process.argv[2];
(async () => {
  const b = await chromium.launch();
  for (const [w, scheme] of [[400, 'light'], [720, 'dark']]) {
    const p = await b.newPage({ viewport: { width: w, height: 800 }, colorScheme: scheme });
    await p.setContent('<!doctype html><meta name=viewport content="width=device-width">' + fs.readFileSync(f, 'utf8'));
    await p.waitForTimeout(1000);
    const o = await p.evaluate(() => {
      const r = [];
      document.querySelectorAll('svg').forEach((s, i) => {
        const vb = s.viewBox.baseVal; const ts = [...s.querySelectorAll('text')];
        ts.forEach(t => { const bb = t.getBBox();
          if (bb.x < -1 || bb.x + bb.width > vb.width + 1 || bb.y < -1 || bb.y + bb.height > vb.height + 1) r.push('OUT ' + i + ': ' + t.textContent); });
        for (let a = 0; a < ts.length; a++) for (let c = a + 1; c < ts.length; c++) {
          const A = ts[a].getBBox(), B = ts[c].getBBox();
          if (A.x < B.x + B.width - 1 && B.x < A.x + A.width - 1 && A.y < B.y + B.height - 1 && B.y < A.y + A.height - 1) r.push('OVL ' + i + ': ' + ts[a].textContent + ' | ' + ts[c].textContent);
        }
      });
      return { problems: r, scrollWidth: document.documentElement.scrollWidth };
    });
    console.log(w, scheme, JSON.stringify(o));
    if (w === 400) await p.screenshot({ path: f.replace(/\.html$/, '') + '-400.png', fullPage: true });
    await p.close();
  }
  await b.close();
})();
