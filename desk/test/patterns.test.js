'use strict';
// Task B, patterns = rules + analogy (interim, on the notes/timeline). Toy synthetic days only.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const P = require('../src/patterns');
const S = require('./synth-days');
const E = require('./patterns-eval');
const DiaryAO = require('../src/diary-ao');

const at = (d, h, m) => new Date(2026, 10, d, h, m || 0, 0).getTime();
const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), 'pat-'));

test('masking is rule-based: names, places, times and numbers go, the words that carry the shape stay', () => {
  assert.strictEqual(P.mask('Maya texted at 4pm: practice moved to Field 3 on Friday'), '<NAME> texted at <TIME>: practice moved to <PLACE> <NUM> on <TIME>');
  assert.strictEqual(P.mask('Sam Lee emailed: meeting moved to 3:30 pm tomorrow'), '<NAME> emailed: meeting moved to <TIME>');
  assert.strictEqual(P.mask('Bus to Kiro Park is running late'), 'Bus to <PLACE> is running late');
  assert.strictEqual(P.mask('Phone battery at 12 percent'), 'Phone battery at <NUM> percent');
  assert.strictEqual(P.mask('Maya and Jo are meeting at Kiro Mall after the game'), '<NAME> and <NAME> are meeting at <PLACE> after the game');
  assert.strictEqual(P.mask('see https://x.org/a or mail a@b.com'), 'see <LINK> or mail <LINK>');
  // same shape, different names -> the shape keys agree much more than the plain vectors
  const a = 'Maya texted: practice moved to 5pm', b = 'Zed texted: rehearsal moved to 6:30 pm';
  assert.ok(P.cos(P.shapeKey(a), P.shapeKey(b)) > P.cos(P.embed(a), P.embed(b)) + 0.2);
  const v = P.embed('hello there'); assert.strictEqual(v.length, P.DIM); assert.ok(Math.abs(P.cos(v, P.unpack(P.pack(v))) - 1) < 0.01);
});

test('recall: the shape channel uses at most 2 of the 5 slots, after the plain channel\'s best 3', () => {
  const tl = new P.Timeline({});
  for (let i = 0; i < 6; i++) tl.add({ t: at(2 + i, 10), text: 'Jordan Vale bought a red bike number ' + i + ' at the market' });
  tl.add({ t: at(3, 11), text: 'Kami texted: practice moved to 5pm' });
  tl.add({ t: at(4, 11), text: 'Rolo texted: dinner moved to 7pm' });
  tl.add({ t: at(5, 11), text: 'Pip texted: meeting moved to 9am' });
  const r = tl.recall('Jordan Vale bought a red bike', { k: 5 });
  assert.strictEqual(r.length, 5);
  assert.ok(r.slice(0, 3).every((x) => x.via === 'plain' && /Jordan/.test(x.item.text)), 'plain keeps its first 3 slots');
  assert.ok(r.filter((x) => x.via === 'shape').length <= 2);
  const s = tl.recall('Zed messaged: practice moved to 6pm', { k: 5 });
  assert.ok(s.some((x) => /Kami texted: practice/.test(x.item.text)));
});

test('analogy, offline (fixed pass marks; seeds 2+3): same-name recall does not drop; RESULT on the shape mark is reported, not assumed', () => {
  for (const seed of [2, 3]) {
    const a = E.analogy(seed);
    assert.ok(a.plainName - a.shapeName <= 2, 'same-name recall drop ' + (a.plainName - a.shapeName));
    assert.ok(a.shapeShape >= a.plainShape, 'the shape channel never makes same-shape recall worse');
    // Registered result (2026-11-04): plain recall@5 is already 100% on this set, so "shape >= plain + 20" FAILS (ceiling).
    // This line keeps that visible: if the set or the embedder changes and the mark is met, update the report.
    assert.ok(!(a.shapeShape >= a.plainShape + 20) || a.plainShape <= 80, 'unexpected: the analogy mark now passes; update docs/ingredients-decisions-B.md');
  }
});

test('patterns in sleep, offline (fixed pass marks; seeds 2+3): >= 80% planted found, <= 10% spurious, >= 70% "what follows" right, zero model calls', () => {
  for (const seed of [2, 3]) {
    const p = E.patterns(seed);
    assert.ok(p.found >= 80, 'found ' + p.found); assert.ok(p.spurious <= 10, 'spurious ' + p.spurious); assert.ok(p.follows >= 70, 'follows ' + p.follows);
    assert.strictEqual(p.calls, 0, 'no model call while patterns are made');
  }
});

test('patterns.js cannot reach a model: it requires no model, network or process module', () => {
  const src = fs.readFileSync(path.join(__dirname, '..', 'src', 'patterns.js'), 'utf8');
  const reqs = [...src.matchAll(/require\(['"]([^'"]+)['"]\)/g)].map((m) => m[1]).sort();
  assert.deepStrictEqual(reqs, ['./senses', './shapekeys', './timesense', 'crypto', 'fs', 'path']);
  assert.doesNotMatch(src, /\bfetch\(|\bask\(|XMLHttpRequest/);
  // the learned shape keys (sleep track T3) are plain math: no requires at all
  const sk = fs.readFileSync(path.join(__dirname, '..', 'src', 'shapekeys.js'), 'utf8');
  assert.deepStrictEqual([...sk.matchAll(/require\(['"]([^'"]+)['"]\)/g)].map((m) => m[1]), []);
  assert.doesNotMatch(sk, /\bfetch\(|\bask\(|XMLHttpRequest/);
});

function plantedTimeline(o) {
  const d = S.patternDays(5); const tl = new P.Timeline({ now: () => S.T0 + d.days * S.DAY, ...(o || {}) });
  for (const it of d.items) tl.add({ t: it.t, text: it.text, status: /^A0$/.test(it.tag) && o && o.maybeA0 ? 'maybe' : 'seen' });
  return { tl, d };
}

test('patterns from maybe notes are marked maybe; wrong notes never join; the sleep handoff never carries patterns', () => {
  const { tl } = plantedTimeline({ maybeA0: true });
  const r = tl.sleep();
  const a0 = r.patterns.find((p) => /plans for the .* changed/.test(p.template));
  assert.ok(a0 && a0.maybe, 'A0 pattern is maybe');
  assert.ok(r.patterns.filter((p) => p !== a0).every((p) => !p.maybe));
  assert.match(P.patternLine(a0), /^Pattern \(seen \d+×, maybe\): /);
  // wrong notes are left out of clustering
  const w = new P.Timeline({});
  for (let i = 0; i < 5; i++) w.add({ t: at(2 + i, 9), text: 'Kami said the moon is cheese number ' + i, status: 'wrong' });
  assert.strictEqual(w.sleep().patterns.length, 0);
  const h = DiaryAO.sleepHandoff({ truth: null, surprises: [] });
  assert.deepStrictEqual(Object.keys(h).sort(), ['at', 'confirmed', 'corrections', 'surprises']);
});

test('"what usually happens after X": the answer comes from the counted followers, in time order', () => {
  const { tl } = plantedTimeline();
  tl.sleep();
  const w = tl.whatFollows('Zubo said dinner is ready');
  assert.ok(w && w.follow, 'found a follower');
  assert.match(w.follow.template, /desk for dinner/);
  assert.ok(w.follow.count >= 3 && w.follow.medianMin > 0 && w.follow.medianMin <= 60);
  assert.match(P.patternLine(w.pattern), /said dinner is ready → usually then: .*desk for dinner/);
});

test('pruning: unused patterns are filed (members kept); shown-and-never-true ones too; a filed one comes back with a new member', () => {
  let now = S.T0 + 8 * S.DAY;
  const d = S.patternDays(5); const tl = new P.Timeline({ now: () => now });
  for (const it of d.items) tl.add({ t: it.t, text: it.text });
  const r1 = tl.sleep(); const n1 = r1.patterns.length; assert.ok(n1 >= 10);
  const items = tl.items.length;
  // 15 days later, nothing new and nothing recalled -> everything is filed, members untouched
  now += 15 * S.DAY;
  const r2 = tl.sleep();
  assert.strictEqual(r2.patterns.length, 0); assert.strictEqual(tl.filed.length, n1); assert.strictEqual(tl.items.length, items, 'members are never deleted');
  assert.strictEqual(tl.patternsFor('Zubo said dinner is ready').length, 0, 'a filed pattern is not recalled');
  // a new "dinner is ready" brings that one pattern back
  tl.add({ t: now - 3600000, text: 'Quix said dinner is ready' });
  const r3 = tl.sleep(); assert.strictEqual(r3.revived, 1); assert.ok(tl.patterns.some((p) => /dinner is ready/.test(p.template)));
  // shown 10 times, its prediction never came true -> filed
  const p = tl.patterns.find((x) => /dinner is ready/.test(x.template));
  for (let i = 0; i < 10; i++) tl.markShown(p);
  const r4 = tl.sleep(); assert.ok(!tl.patterns.some((x) => x.id === p.id)); assert.match(tl.filed.find((x) => x.id === p.id).why, /never came true/);
  assert.ok(r4.filed >= 1);
});

test('a shown pattern whose prediction then happens counts as used (confirmed)', () => {
  const { tl } = plantedTimeline();
  tl.sleep();
  const hit = tl.patternsFor('Zubo said dinner is ready')[0];
  assert.ok(hit); assert.strictEqual(hit.p.hits, 1);
  tl.add({ t: S.T0 + 8 * S.DAY + 60000, text: 'Left the desk for dinner with Zubo' });
  assert.strictEqual(hit.p.confirmed, 1);
});

test('the timeline: private text dropped, saved and reloaded with times and patterns, truth notes keep their status', () => {
  const dir = tmp(); let now = at(4, 10);
  const tl = new P.Timeline({ dir, now: () => now, saveDelayMs: 0 });
  assert.strictEqual(tl.add({ text: 'my password is hunter2' }), null);
  tl.add({ text: 'Maya texted: practice moved to 5pm' });
  tl.syncNotes([{ id: 'n1', text: 'Octopuses have three hearts.', status: 'maybe', t: at(4, 9) }, { id: 'n2', text: 'The sun is a red dwarf.', status: 'wrong', correction: 'I thought the sun is a red dwarf; actually it is a G-type star', t: at(4, 8) }]);
  assert.strictEqual(tl.byRef.get('n1').status, 'maybe');
  assert.match(tl.byRef.get('n2').text, /^I thought/); assert.strictEqual(tl.byRef.get('n2').status, 'confirmed', 'a correction is the checked belief');
  tl.syncNotes([{ id: 'n1', text: 'Octopuses have three hearts.', status: 'confirmed', t: at(4, 9) }]);
  assert.strictEqual(tl.byRef.get('n1').status, 'confirmed');
  tl.flush();
  const back = new P.Timeline({ dir, now: () => now });
  assert.strictEqual(back.items.length, 3); assert.ok(back.items.every((x) => Number.isFinite(x.t) && x.k && x.m));
  assert.ok(!fs.readFileSync(path.join(dir, 'timeline.json'), 'utf8').includes('hunter2'));
});

test('old timeline rows without a time load as "time unknown"; recall, time questions and sleep still work', () => {
  const dir = tmp();
  fs.writeFileSync(path.join(dir, 'timeline.json'), JSON.stringify({ items: [{ text: 'an old note with no time' }, { text: 'Maya texted: practice moved', t: 'garbage' }, null, { t: 5 }] }));
  fs.writeFileSync(path.join(dir, 'patterns.json'), '{not json');
  const tl = new P.Timeline({ dir, now: () => at(4, 12) });
  assert.strictEqual(tl.items.length, 2); assert.ok(tl.items.every((x) => x.t === null));
  assert.ok(tl.recall('practice moved').length >= 1);
  assert.strictEqual(require('../src/timesense').answerTimeQuestion('how long ago did Maya text?', tl.items), null);
  tl.sleep();
  assert.ok(Number.isFinite(tl.add({ text: 'no time given' }).t), 'a new row without a time gets "now"');
});
