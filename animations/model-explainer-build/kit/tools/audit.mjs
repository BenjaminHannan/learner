// Reading-time and structure audit of content.js (does not render anything).
//   node tools/audit.mjs            all chapters
//   node tools/audit.mjs ch03       one chapter
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const win = {};
vm.runInNewContext(fs.readFileSync(path.join(root, 'content.js'), 'utf8'), { window: win });
const CT = win.CONTENT;
const want = process.argv.slice(2);
const SKIP = new Set(['id', 'src', 'notes', 'duration', 'illustration', 'at']);
const wc = (s) => String(s).split(/\s+/).filter(Boolean).length;
function words(v) {
  if (typeof v === 'string') return wc(v);
  if (typeof v === 'number') return 1;
  if (Array.isArray(v)) return v.reduce((a, x) => a + words(x), 0);
  if (v && typeof v === 'object') return Object.entries(v).reduce((a, [k, x]) => a + (SKIP.has(k) ? 0 : words(x)), 0);
  return 0;
}
let grand = 0, flags = 0;
for (const cid of CT.order) {
  if (want.length && !want.includes(cid)) continue;
  const ch = CT.chapters[cid];
  let sum = 0;
  console.log(`\n${cid}  ${ch.kicker || ''}  ${ch.title || ''}`);
  for (const s of ch.scenes) {
    const w = words(s);
    const need = 3 + w / 2.6;
    const issues = [];
    if (s.duration + 0.01 < need) issues.push(`TOO SHORT for ${w} words, needs >= ${need.toFixed(1)} s`);
    if (s.duration > 45) issues.push('longer than 45 s: split it');
    if (s.duration < 10) issues.push('shorter than 10 s');
    if (s.heading && s.heading.length > 48) issues.push(`heading ${s.heading.length} chars (max 48)`);
    for (const k of ['heading', 'caption']) if (!s[k] || (Array.isArray(s[k]) && !s[k].length)) issues.push('missing ' + k);
    if (!(s.src && s.src.length)) issues.push('missing src');
    // each caption sentence: size and its slot length
    const caps = (Array.isArray(s.caption) ? s.caption : s.caption ? [s.caption] : []).map((x) => (typeof x === 'string' ? { text: x } : x));
    const first = 0.6, last = s.duration - 0.4 - 0.3, n = caps.length, span = n ? (last - first) / n : 0;
    caps.forEach((c, i) => {
      const cw = wc(c.text);
      if (cw > 26 || c.text.length > 150) issues.push(`caption ${i + 1} is ${cw} words / ${c.text.length} chars (max 26 / 150)`);
      const start = c.at != null ? c.at * s.duration : first + i * span;
      const next = i < n - 1 ? (caps[i + 1].at != null ? caps[i + 1].at * s.duration : first + (i + 1) * span) : s.duration - 0.7;
      const slot = next - start;
      if (slot + 0.01 < 1.2 + cw / 2.8) issues.push(`caption ${i + 1} shows ${slot.toFixed(1)} s, needs >= ${(1.2 + cw / 2.8).toFixed(1)} s`);
    });
    if (issues.length) flags += issues.length;
    console.log(`  ${s.id.padEnd(5)} ${String(s.duration).padStart(5)} s  ${String(w).padStart(3)} words${issues.length ? '\n        <-- ' + issues.join('\n        <-- ') : ''}`);
    sum += s.duration;
  }
  const card = ch.card === false ? 0 : (CT.global.cardSeconds || 5);
  console.log(`  chapter total ${sum} s (+${card} s card), ${ch.scenes.length} scenes`);
  grand += sum + card;
}
console.log(`\nTOTAL ${grand.toFixed(0)} s = ${(grand / 60).toFixed(1)} min;  flags: ${flags}`);
