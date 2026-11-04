'use strict';
// Truth check before sleep (track I2): the shared rule, the verifiers, the night log, and the learners that call it.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
const TC = require('../src/truthcheck');
const { categorize } = require('../src/speakometer');
const { GAMES } = require('../src/games');
const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), 'tc-'));

const rows = (n, src, bad, none) => Array.from({ length: n }, (_, i) => ({ src, i, v: i < bad ? 'bad' : i < bad + none ? 'none' : 'ok' }));
const opt = { verify: (r) => r.v, sourceOf: (r) => r.src };

test('trusted source: bad rows dropped, unverifiable rows kept', () => {
  const r = TC.check(rows(40, 'a', 2, 5), opt);
  assert.equal(r.sources.a.mode, 'trusted');
  assert.equal(r.kept.length, 38);
  assert.ok(r.kept.every((x) => x.v !== 'bad'));
});

test('failed source (> 10 % wrong): only verified-ok rows kept', () => {
  const r = TC.check(rows(40, 'a', 12, 8).concat(rows(40, 'b', 0, 4)), opt);
  assert.equal(r.sources.a.mode, 'failed');
  assert.equal(r.sources.a.kept, 20);
  assert.ok(r.kept.filter((x) => x.src === 'a').every((x) => x.v === 'ok'));
  assert.equal(r.sources.b.kept, 40);   // the clean source keeps its unverifiable rows
  assert.equal(r.stats.failed, 1);
});

test('too few truths: no fail -> unchecked and kept; any fail -> ok rows only', () => {
  const a = TC.check(rows(30, 'a', 0, 25), opt);
  assert.equal(a.sources.a.mode, 'unchecked'); assert.equal(a.kept.length, 30);
  const b = TC.check(rows(30, 'b', 1, 25), opt);
  assert.equal(b.sources.b.mode, 'failed'); assert.equal(b.kept.length, 4);
});

test('a verifier that throws counts as no truth; sampling verifies at most `sample` rows per source', () => {
  const r = TC.check(rows(20, 'a', 0, 0), { verify: () => { throw new Error('x'); }, sourceOf: () => 'a' });
  assert.equal(r.stats.none, 20); assert.equal(r.kept.length, 20);
  let calls = 0; TC.check(rows(100, 'a', 0, 0), { verify: (x) => { calls++; return x.v; }, sourceOf: () => 'a', sample: 15 });
  assert.equal(calls, 15);
});

test('category verifier recomputes from raw app + title', () => {
  const v = TC.verifiers.category(categorize);
  assert.equal(v({ cat: 'video', raw: { app: 'Google Chrome', title: 'YouTube - talk' } }), true);
  assert.equal(v({ cat: 'code', raw: { app: 'Google Chrome', title: 'YouTube - talk' } }), false);
  assert.equal(v({ cat: 'code' }), null);
});

test('game verifier replays the rulebook (our move) and checks legality (opponent)', () => {
  const v = TC.verifiers.game(GAMES), g = GAMES.nim, s = g.init(5), m = g.moves(s)[0], mid = g.apply(s, m);
  assert.equal(v({ game: 'nim', who: 'me', s, m, s2: mid }), true);
  const other = g.apply(s, g.moves(s)[1]);
  assert.equal(v({ game: 'nim', who: 'me', s, m, s2: other }), false);
  const rep = g.replies(mid)[0];
  if (rep) { assert.equal(v({ game: 'nim', who: 'them', s: mid, s2: rep }), true); assert.equal(v({ game: 'nim', who: 'them', s: mid, s2: { ...rep, piles: rep.piles.map((p) => p + 5) } }), false); }
  const t = GAMES.maze, ts = t.init(3), tm = t.moves(ts)[0];
  assert.equal(v({ game: 'maze', who: 'me', s: ts, m: tm, s2: t.step(ts, tm) }), true);
  assert.equal(v({ game: 'nope', who: 'me', s: ts, m: tm, s2: ts }), null);
});

test('anchor-text, answer-hash and Ben-facts verifiers', () => {
  const a = TC.verifiers.anchorText({ r1: { id: 'r1', text: { subtitle: 'Hello there' } } });
  assert.equal(a({ id: 'r1', from: 'text', label: 'hello there' }), true);
  assert.equal(a({ id: 'r1', from: 'text', label: 'goodbye' }), false);
  assert.equal(a({ id: 'r1', from: 'eye', label: 'goodbye' }), null);
  const nf = { out: (s) => String(s).trim() }, h = crypto.createHash('sha256').update('42', 'utf8').digest('hex');
  const hv = TC.verifiers.answerHash(nf);
  assert.equal(hv({ answer: ' 42 ', truth: { norm: 'out', value: h } }), true);
  assert.equal(hv({ answer: '41', truth: { norm: 'out', value: h } }), false);
  assert.equal(hv({ answer: '41' }), null);
  const b = TC.verifiers.benFacts([{ subj: 'Ben', rel: 'school', obj: 'Dresden' }, { subj: 'Ben', rel: 'pet', obj: 'cat', status: 'maybe' }]);
  assert.equal(b({ subj: 'ben', rel: 'school', obj: 'dresden' }), true);
  assert.equal(b({ subj: 'Ben', rel: 'school', obj: 'Other' }), false);
  assert.equal(b({ subj: 'Ben', rel: 'pet', obj: 'dog' }), null);   // maybe notes are never a truth
});

test('TruthCheck writes one log line per learner per night; off = unchecked; note() for learners with no truth', () => {
  const dir = tmp(), tc = new TC.TruthCheck({ dir, now: () => 5 });
  const out = tc.run('x', rows(20, 'a', 3, 0), opt);
  assert.equal(out.kept.length, 17);
  tc.note('y', 'no truth here');
  const lines = fs.readFileSync(path.join(dir, TC.LOG), 'utf8').trim().split('\n').map(JSON.parse);
  assert.deepEqual(lines.map((l) => l.part), ['x', 'y']);
  assert.equal(lines[0].bad, 3); assert.equal(lines[1].mode, 'no-truth');
  const off = TC.forSettings({ truthCheck: false }, null).run('x', rows(20, 'a', 3, 0), opt);
  assert.equal(off.kept.length, 20); assert.equal(off.rec.mode, 'off');
  assert.equal(TC.forSettings({}, null).enabled, true);   // default ON
});

test('world model nightly: rulebook-failing rows never train (truth check on by default)', () => {
  const WM = require('../src/worldmodel');
  const dir = tmp(); let now = new Date(2026, 9, 5, 9).getTime(); const log = new WM.GameLog({ dir, now: () => now });
  const g = GAMES.maze;
  for (let i = 0; i < 30; i++) { const s = g.init(100 + i), m = g.moves(s)[0]; log.add({ game: 'maze', who: 'me', s, m, s2: g.step(s, m) }); }
  for (let i = 0; i < 30; i++) { const s = g.init(200 + i), m = g.moves(s)[0]; const s2 = JSON.parse(JSON.stringify(s)); s2.steps = s.steps + 9; log.add({ game: 'maze', who: 'me', s, m, s2 }); }
  const r = WM.nightly({ dir, log, now: () => now });
  assert.equal(r.rows, 30);   // the 30 poisoned rows were dropped before training
  const tl = fs.readFileSync(path.join(dir, TC.LOG), 'utf8').trim().split('\n').map(JSON.parse).pop();
  assert.equal(tl.part, 'worldmodel'); assert.equal(tl.bad, 30); assert.equal(tl.kept, 30);
  const r2 = WM.nightly({ dir: tmp(), log, now: () => now, truthCheck: false });
  assert.equal(r2.rows, 60);
});

test('sleep judges: guesser rows whose raw text disagrees are dropped before the night; raw kept by the break tracker', () => {
  const { BreakTracker } = require('../src/breaks');
  const got = []; const bt = new BreakTracker({ onRow: (r) => got.push(r) });
  const t0 = new Date(2026, 9, 5, 10).getTime();
  bt.tick(t0, 0, 'code', { app: 'Visual Studio Code', title: 'main.js' }); bt.tick(t0 + 60000, 999, 'other', { app: 'Finder', title: '' });
  assert.ok(got.length >= 1 && got[0].raw && got[0].raw.app === 'Visual Studio Code');
  const SJ = require('../src/sleepjudges');
  const J = new SJ.SleepJudges({ now: () => t0 + 8 * 3600000 });
  const day = new Date(2026, 9, 5, 9).getTime();
  for (let i = 0; i < 120; i++) J.record('guesser', { t: day + i * 60000, cat: i % 3 ? 'code' : 'game', work: true, sess: i % 50, hour: 9 + Math.floor(i / 60), soon: 0, raw: i % 3 ? { app: 'Visual Studio Code', title: 'x' } : { app: 'Visual Studio Code', title: 'y' } });
  const tc = new TC.TruthCheck({});
  J.run(SJ.guesserPart(), { k: { app: 0.8, when: 0.8, idle: 0.8 } }, { truthcheck: tc });
  assert.match(tc.lines[0], /^guesser: truth check 80 right, 40 wrong/);
});

test('sense sleep: a text-anchored label that no longer matches its record is dropped', () => {
  const SS = require('../src/sense-sleep');
  const recs = [{ id: '2026-10-05#1', ear: { off: 0, len: 4, shape: [4], encoder: 'w' }, text: { subtitle: 'hello' } }];
  const tc = new TC.TruthCheck({});
  const p = SS.buildPractice(recs, { truthcheck: tc, logicCheck: () => true });
  assert.equal(p.ear.length, 1);
  assert.match(tc.lines.find((l) => l.startsWith('sense-ear')), /1 right, 0 wrong/);
});
