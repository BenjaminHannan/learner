// How late does each scene's picture work run? Loads the built video page (node tools/mkindex.mjs first) in headless Chromium and reads the GSAP timeline.
//   node tools/voice/extent.mjs [--dir PROJECT_DIR] [--out extent.json]
// Writes {"chNN-sNN": {t0, end, maxStart, maxEnd, startMargin, endMargin}}: margins are seconds between the scene end and the last picture tween's start / end.
// A scene whose pictures need more time than its speech gets a larger margin requirement in pace.py (--min).
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
const argv = process.argv.slice(2);
const arg = (k, d) => { const i = argv.indexOf(k); return i >= 0 ? argv[i + 1] : d; };
const dir = path.resolve(arg('--dir', '.'));
const out = arg('--out', path.join(dir, 'narration', 'extent.json'));
const require = createRequire(process.env.PLAYWRIGHT_DIR || '/opt/node22/lib/node_modules/');
const { chromium } = require('playwright');
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
p.on('pageerror', (e) => console.error('pageerror', e.message));
await p.goto('file://' + dir + '/index.html');
await p.waitForFunction(() => window.__timelines && window.__timelines.main && window.__TOTAL, null, { timeout: 60000 });
const data = await p.evaluate(() => {
  const tl = window.__timelines.main;
  const res = {};
  for (const tw of tl.getChildren(true, true, false)) {
    let ts; try { ts = tw.targets(); } catch (e) { continue; }
    const start = tw.globalTime(0), end = tw.globalTime(tw.duration());
    if (!isFinite(start) || !isFinite(end)) continue;
    for (const el of ts) {
      if (!(el instanceof Element)) continue;
      const sc = el.classList && el.classList.contains('scene') ? el : el.closest('.scene');
      if (!sc) continue;
      const id = sc.id.replace(/^sc-/, '');
      const r = res[id] || (res[id] = { shellStart: Infinity, shellEnd: -Infinity, maxStart: -Infinity, maxEnd: -Infinity });
      if (el === sc) { r.shellStart = Math.min(r.shellStart, start); r.shellEnd = Math.max(r.shellEnd, end, start); }
      else { r.maxStart = Math.max(r.maxStart, start); r.maxEnd = Math.max(r.maxEnd, end); }
    }
  }
  return res;
});
await b.close();
const o = {};
for (const [id, r] of Object.entries(data)) {
  if (!isFinite(r.shellEnd) || !isFinite(r.maxEnd)) continue;
  o[id] = { t0: +r.shellStart.toFixed(2), end: +r.shellEnd.toFixed(2), maxStart: +r.maxStart.toFixed(2), maxEnd: +r.maxEnd.toFixed(2),
    startMargin: +(r.shellEnd - r.maxStart).toFixed(2), endMargin: +(r.shellEnd - r.maxEnd).toFixed(2) };
}
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, JSON.stringify(o, null, 1));
console.log(`extent: ${Object.keys(o).length} scenes -> ${out}`);
