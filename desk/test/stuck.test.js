'use strict';
// T5 stuck list (src/stuck.js): sources, truth kept as a hash only, cap + fading, the morning line, and the scientist hook.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const S = require('../src/stuck');
const Puzzles = require('../src/games/puzzles');
const Sandbox = require('../src/sandbox');

const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), 'stuck-'));

test('stuck: scientist entries keep only a hash of the truth, never the answer', () => {
  const dir = tmp(); const L = new S.StuckList({ dir });
  const e = L.add(S.fromExperiment({ kind: 'python', question: 'What does this print?\nprint(6 * 7)', truth: '42\n', tries: 4, guesses: ['48', '36'] }));
  assert.ok(e); assert.strictEqual(e.truth.type, 'sha256'); assert.strictEqual(e.truth.norm, 'out');
  const raw = fs.readFileSync(path.join(dir, S.FILE), 'utf8');
  assert.ok(!/"42/.test(raw), 'plain answer must not be in the file');
  assert.match(e.context, /All 4 of my tries were wrong: "48", "36"/);
  assert.strictEqual(e.truth.value, S.truthHash('42', 'out'));
  assert.strictEqual(L.checkable().length, 1);
});

test('stuck: hash normalisation equals the real checkers (sandbox normOut, puzzles correct)', () => {
  for (const [a, b] of [['[1, 2]\n\n', '[1, 2]'], ['x  \r\ny', 'x\ny']]) assert.strictEqual(Sandbox.normOut(a) === Sandbox.normOut(b), S.truthHash(a, 'out') === S.truthHash(b, 'out'));
  for (const [a, b] of [['Answer: 1, 2, 3', '123'], ['a b c', 'abc'], ['D', 'd.'], ['12', '1 3'], ['ab', 'ba']]) {
    assert.strictEqual(Puzzles.correct(a, b), S.truthHash(a, 'puzzle') === S.truthHash(b, 'puzzle'), a + ' vs ' + b);
  }
  assert.strictEqual(S.normFor('puzzle:A'), 'puzzle'); assert.strictEqual(S.normFor('game:nim'), 'puzzle'); assert.strictEqual(S.normFor('python'), 'out');
  // the hash values the sleep side (sleepmlx insight.py) is tested against
  assert.strictEqual(S.truthHash('zebra-quartz-17\r\n  \n', 'out'), 'f63334c41ac8a1b855b28829a83ccfde85070251cde9e8af2c850dee3bfbea93');
  assert.strictEqual(S.truthHash('Answer: 1, 2 3.', 'puzzle'), 'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3');
});

test('stuck: the other sources carry no truth; quiz misses stay locked; bad input is refused', () => {
  const L = new S.StuckList({});
  assert.strictEqual(L.add(S.fromNotSure('The Moon is 300,000 km away', 0.41)).truth.type, 'none');
  assert.strictEqual(S.fromBenError({ n: 2, text: 'TypeError: x' }), null);
  assert.strictEqual(L.add(S.fromBenError({ n: 3, text: 'TypeError: x is undefined' })).source, 'ben-error');
  const q = L.add(S.fromQuizMiss('volcanoes', 'L1-q7'));
  assert.strictEqual(q.problem, 'weak spot in volcanoes (quiz L1-q7)'); assert.strictEqual(q.truth.type, 'none');
  assert.strictEqual(L.add({ source: 'made-up', problem: 'x' }), null);
  assert.strictEqual(L.add({ source: 'notsure', problem: '  ' }), null);
  assert.strictEqual(S.fromExperiment({ kind: 'python-own', question: 'Topic: loops', truth: '1' }), null);
  assert.strictEqual(L.checkable().length, 0);
});

test('stuck: repeats refresh, nights fade, low weight drops, cap evicts the weakest', () => {
  let t = 1000; const L = new S.StuckList({ now: () => t });
  const a = L.add({ source: 'notsure', problem: 'A' }); L.add({ source: 'notsure', problem: 'B' });
  let r = L.afterNight([]); assert.deepStrictEqual(r, { solved: 0, faded: 2, dropped: 0 });
  assert.strictEqual(L.items[0].weight, S.FADE);
  t++; assert.strictEqual(L.add({ source: 'notsure', problem: 'a ' }).id, a.id);   // same problem (case/space) -> same entry
  assert.strictEqual(L.items.find((x) => x.id === a.id).weight, 1);
  for (let i = 0; i < 4; i++) L.afterNight([]);
  assert.deepStrictEqual(L.items.map((x) => x.problem), ['A']);                     // B: 0.7^5 = 0.17 < 0.2, gone; A: 0.7^4 = 0.24
  for (let i = 0; i < S.CAP + 5; i++) { t++; L.add({ source: 'notsure', problem: 'P' + i }); }
  assert.strictEqual(L.items.length, S.CAP);
  assert.ok(!L.items.some((x) => x.problem === 'A'), 'the faded entry is evicted first');
});

test('stuck: a problem sleep solved leaves the list and is not re-added; the morning line only when something clicked', () => {
  const dir = tmp(); const L = new S.StuckList({ dir });
  const e = L.add({ source: 'scientist', kind: 'puzzle:A', norm: 'puzzle', problem: 'abc -> abd; xyz -> ?', truth: 'xza' });
  L.add({ source: 'notsure', problem: 'C' });
  const r = L.afterNight([e.id]); assert.strictEqual(r.solved, 1);
  assert.strictEqual(L.add({ source: 'scientist', problem: 'abc -> abd; xyz -> ?', truth: 'xza' }), null);
  assert.strictEqual(new S.StuckList({ dir }).items.length, 1);                      // persisted
  assert.strictEqual(S.morningLine({ clicked: [] }), null);
  assert.strictEqual(S.morningLine(null), null);
  assert.match(S.morningLine({ clicked: [{ id: e.id, problem: 'abc -> abd; xyz -> ?' }] }), /^Something clicked overnight: I solved 1 problem I was stuck on yesterday \(e\.g\. "abc -> abd; xyz -> \?"\), checked against the real answer\.$/);
  fs.writeFileSync(path.join(dir, S.RESULTS), JSON.stringify({ clicked: [{ id: 'x', problem: 'p' }] }));
  assert.strictEqual(S.readResults(dir).clicked.length, 1);
  assert.strictEqual(S.readResults(tmp()), null);
});

test('stuck: the scientist reports an experiment where every try was wrong (onStuck), and not one with a right try', async () => {
  const { Scientist } = require('../src/scientist');
  const got = [];
  const sci = new Scientist({ k: 2, pythonOk: false, onStuck: (x) => got.push(x), now: (() => { let t = 1; return () => t++; })() });
  sci.chooseKind = () => ({ kind: 'puzzle:A', why: 'test' });
  const ask = async () => '{"guess": "zzz", "confidence": 0.5}';
  const r1 = await sci.runOne({ ask, signal: null });
  assert.ok(r1.ran && !r1.anyRight);
  assert.strictEqual(got.length, 1);
  assert.strictEqual(got[0].kind, 'puzzle:A'); assert.ok(got[0].question); assert.strictEqual(got[0].truth, r1.truth); assert.deepStrictEqual(got[0].guesses, ['zzz', 'zzz']);
  const e = S.fromExperiment(got[0]); assert.strictEqual(e.norm, 'puzzle');
  const tk = sci.task('puzzle:A', sci.st.seed), truth = (await tk.test()).truth;   // the next experiment's answer (seeded generator)
  const before = got.length;
  const r2 = await sci.runOne({ ask: async () => JSON.stringify({ guess: String(truth), confidence: 0.9 }), signal: null });
  assert.ok(r2.ran && r2.anyRight);
  assert.strictEqual(got.length, before);
});

test("stuck: the morning uses each night's results once; earlier clicks clear the list but are not told again", () => {
  const dir = tmp(); const L = new S.StuckList({ dir });
  const a = L.add({ source: 'scientist', problem: 'A', truth: '1' }), b = L.add({ source: 'scientist', problem: 'B', truth: '2' }); L.add({ source: 'notsure', problem: 'C' });
  const res = { written_at: 5, date: '2026-11-04', night: 3, clicked: [{ id: a.id, problem: 'A' }, { id: b.id, problem: 'B', earlier: true }] };
  assert.match(L.morning(res), /solved 1 problem /);
  assert.deepStrictEqual(L.items.map((x) => x.problem), ['C']);
  assert.strictEqual(L.items[0].weight, S.FADE);
  assert.strictEqual(new S.StuckList({ dir }).morning(res), null);                   // same night again (after a restart): nothing
  assert.strictEqual(L.morning({ written_at: 6, clicked: [] }), null);              // nothing clicked: Glim says nothing
  assert.strictEqual(L.items[0].weight, Math.round(S.FADE * S.FADE * 1000) / 1000);
});
