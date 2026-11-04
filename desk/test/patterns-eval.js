'use strict';
// Task B offline pass marks (not part of the suite; run: node test/patterns-eval.js). Toy synthetic notes/days only.
// Seed 1 was the dev seed (the masker's first-word rule and TAU were set on it); seeds 2 and 3 are the scored ones.
const P = require('../src/patterns');
const S = require('./synth-days');

function analogy(seed) {
  const a = S.analogySet(seed); const tl = new P.Timeline({});
  for (const n of a.notes) { const x = tl.add({ t: n.t, text: n.text, kind: 'note' }); if (x) { x.shape = n.shape; x.src = n.id; } }
  const r5 = (qs, hit, slots) => 100 * qs.filter((q) => tl.recall(q.text, { k: 5, shapeSlots: slots }).some((r) => hit(q, r.item))).length / qs.length;
  const same = (q, it) => it.shape === q.shape, exact = (q, it) => it.src === q.target;
  return { plainShape: r5(a.shapeQueries, same, 0), shapeShape: r5(a.shapeQueries, same, 2), plainName: r5(a.nameQueries, exact, 0), shapeName: r5(a.nameQueries, exact, 2) };
}
function patterns(seed) {
  const d = S.patternDays(seed);
  const tl = new P.Timeline({ now: () => S.T0 + d.days * S.DAY });
  const tag = new Map(); for (const it of d.items) { const x = tl.add({ t: it.t, text: it.text }); if (x) tag.set(x.id, it.tag); }
  // zero model calls: nothing that could reach a model is allowed while patterns are made
  const calls = []; const http = require('http'), cp = require('child_process');
  const saved = { fetch: globalThis.fetch, req: http.request, spawn: cp.spawn, execFile: cp.execFile };
  globalThis.fetch = (...a) => { calls.push('fetch'); throw new Error('no model'); }; http.request = () => { calls.push('http'); throw new Error('no model'); };
  cp.spawn = () => { calls.push('spawn'); throw new Error('no model'); }; cp.execFile = () => { calls.push('execFile'); throw new Error('no model'); };
  let r; try { r = tl.sleep(); } finally { globalThis.fetch = saved.fetch; http.request = saved.req; cp.spawn = saved.spawn; cp.execFile = saved.execFile; }
  const maj = (p) => { const c = {}; for (const m of p.members) { const t = tag.get(m) || '?'; c[t] = (c[t] || 0) + 1; } return Object.entries(c).sort((a, b) => b[1] - a[1])[0][0]; };
  const found = new Set(); let spurious = 0;
  for (const p of r.patterns) { const m = maj(p); if (/^A\d/.test(m)) found.add(m); if (m === 'filler') spurious++; }
  let right = 0;
  for (const pl of d.planted) {
    const w = tl.whatFollows(pl.query); if (!w || !w.follow) continue;
    const fp = r.patterns.find((p) => p.template === w.follow.template);
    if (fp && maj(fp) === 'B' + pl.k) right++;
  }
  return { found: 100 * found.size / d.planted.length, spurious: 100 * spurious / Math.max(1, r.patterns.length), follows: 100 * right / d.planted.length, calls: calls.length, n: r.patterns.length };
}
module.exports = { analogy, patterns };
if (require.main === module) {
  const rows = [];
  for (const seed of [2, 3]) {
    const a = analogy(seed), p = patterns(seed);
    rows.push({ seed, ...a, ...p });
    console.log(JSON.stringify(rows[rows.length - 1]));
  }
  const ok = (b) => (b ? 'PASS' : 'FAIL');
  const all = (f) => rows.every(f);
  console.log('analogy: shape recall@5 >= plain + 20 ......', ok(all((r) => r.shapeShape >= r.plainShape + 20)), rows.map((r) => r.shapeShape + ' vs ' + r.plainShape).join('; '));
  console.log('analogy: same-name recall drop <= 2 .........', ok(all((r) => r.plainName - r.shapeName <= 2)), rows.map((r) => r.shapeName + ' vs ' + r.plainName).join('; '));
  console.log('analogy proven wrong (shape <= plain) .......', all((r) => r.shapeShape <= r.plainShape) ? 'YES (shape <= plain)' : 'no');
  console.log('patterns: planted found >= 80% ..............', ok(all((r) => r.found >= 80)), rows.map((r) => r.found).join('; '));
  console.log('patterns: spurious <= 10% ...................', ok(all((r) => r.spurious <= 10)), rows.map((r) => r.spurious.toFixed(1)).join('; '));
  console.log('patterns: "what follows" right >= 70% .......', ok(all((r) => r.follows >= 70)), rows.map((r) => r.follows).join('; '));
  console.log('patterns: model calls while made = 0 ........', ok(all((r) => r.calls === 0)), rows.map((r) => r.calls).join('; '));
}
