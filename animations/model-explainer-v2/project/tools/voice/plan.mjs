// Narration plan: when each caption appears and how many seconds of speech fit in its slot.
//   node tools/voice/plan.mjs            writes narration/plan.json (all chapters)
// Timing mirrors main.js exactly (card seconds, caption onsets, FADE 0.4).
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..', '..');
const win = {};
vm.runInNewContext(fs.readFileSync(path.join(root, 'content.js'), 'utf8'), { window: win });
const CT = win.CONTENT, G = CT.global || {};
const cardSec = G.cardSeconds || 5, FADE = 0.4;
const WPS = 2.45;            // words per second the voice is budgeted at (voice speed 0.92 measures about 2.5)
const LEAD = 0.25, TAIL = 0.15;
const wc = (s) => String(s).split(/\s+/).filter(Boolean).length;
const segs = [];
let t = 0;
for (const cid of CT.order) {
  const ch = CT.chapters[cid];
  if (ch.card !== false) {
    // card: kicker + title, spoken in the first seconds; may run 0.5 s into the first scene (its first caption starts at +0.85)
    const text = `${ch.kicker || ''}. ${ch.title || ''}.`.replace(/^\. /, '');
    segs.push({ id: `${cid}.card`, ch: cid, scene: 'card', idx: 0, kind: 'card', start: +(t + 0.4).toFixed(2), end: +(t + cardSec + 0.5).toFixed(2), slot: +(cardSec + 0.1).toFixed(2), text, words: wc(text) });
    t += cardSec;
  }
  for (const sc of ch.scenes) {
    const d = sc.duration;
    const items = (Array.isArray(sc.caption) ? sc.caption : [sc.caption]).map((x) => (typeof x === 'string' ? { text: x } : x));
    const n = items.length, first = 0.6, last = d - FADE - 0.3, span = (last - first) / n;
    const on = items.map((it, i) => (it.at != null ? t + it.at * d : t + first + i * span));
    items.forEach((it, i) => {
      const start = on[i] + LEAD;
      const end = (i < n - 1 ? on[i + 1] : t + d - FADE) - TAIL;
      const slot = end - start;
      segs.push({ id: `${cid}.${sc.id}.c${i + 1}`, ch: cid, scene: sc.id, idx: i, kind: 'caption', onset: +on[i].toFixed(2), start: +start.toFixed(2), end: +end.toFixed(2), slot: +slot.toFixed(2),
        maxWords: Math.max(4, Math.floor(slot * WPS)), text: it.text, words: wc(it.text) });
    });
    t += d;
  }
}
// end card
const E = G.endCard;
if (E) {
  const text = `${E.title}. ${E.blurb}`;
  segs.push({ id: 'end.card', ch: 'end', scene: 'card', idx: 0, kind: 'card', start: +(t + 0.5).toFixed(2), end: +(t + (E.duration || 8) - 0.2).toFixed(2), slot: +((E.duration || 8) - 0.7).toFixed(2), text, words: wc(text) });
  t += E.duration || 8;
}
fs.mkdirSync(path.join(root, 'narration'), { recursive: true });
fs.writeFileSync(path.join(root, 'narration', 'plan.json'), JSON.stringify({ total: +t.toFixed(2), wps: WPS, segments: segs }, null, 1));
const over = segs.filter((s) => s.kind === 'caption' && s.words > s.maxWords);
console.log(`plan: ${segs.length} segments, ${t.toFixed(1)} s; captions over budget at ${WPS} words/s: ${over.length}`);
for (const s of over.slice(0, 40)) console.log(`  ${s.id} slot ${s.slot}s budget ${s.maxWords} words, caption ${s.words}`);
