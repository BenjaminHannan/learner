'use strict';
// The checker + "I'm not sure": one interface, methods in priority order, many tries, calibration, the learned slot.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const C = require('../src/checker');
const { rng } = require('../src/games');

const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), 'checker-'));

test('checker: score() uses the first method that applies (executor > quiz > truthnotes > learned > agreement)', () => {
  const k = new C.Checker();
  assert.deepStrictEqual(k.score('2+2?', '4', { check: (a) => a === '4', quizItem: { answer: '5' } }), { p_correct: 1, method: 'executor', verified: true });
  assert.strictEqual(k.score('q', 'Paris', { quizItem: { answer: 'Paris' } }).method, 'quiz');
  assert.strictEqual(k.score('q', 'Lyon', { quizItem: { answer: 'Paris' } }).p_correct, 0);
  const truth = { notes: [{ id: 'n1', status: 'confirmed', text: 'Octopuses have three hearts.' }, { id: 'n2', status: 'wrong', text: 'The Moon is made of cheese.' }, { id: 'n3', status: 'maybe', text: 'Cats have nine lives.' }] };
  assert.deepStrictEqual(k.score('q', 'octopuses have three hearts', { truth }), { p_correct: 1, method: 'truthnotes', verified: true, note: 'n1' });
  assert.strictEqual(k.score('q', 'The Moon is made of cheese', { truth }).p_correct, 0);
  // a `maybe` note is never treated as truth
  const m = k.score('q', 'Cats have nine lives.', { truth, tries: ['Cats have nine lives.', 'Cats have seven lives.'] });
  assert.strictEqual(m.method, 'agreement'); assert.strictEqual(m.untested, true); assert.strictEqual(m.verified, false);
  assert.strictEqual(m.p_correct, 0.5);
});

test('checker: with a verifiable try among K, the pick is a verified-correct one (100% on fake data)', () => {
  const k = new C.Checker(); const r = rng(42); let hits = 0, N = 500;
  for (let n = 0; n < N; n++) {
    const truth = String(Math.floor(r() * 100)); const K = 2 + Math.floor(r() * 7);
    // wrong tries are often the MAJORITY (so agreement alone would pick wrong), with exactly one or more correct ones somewhere
    const wrong = String(Number(truth) + 1);
    const tries = Array.from({ length: K }, () => (r() < 0.7 ? wrong : String(Math.floor(r() * 100) + 200)));
    tries[Math.floor(r() * K)] = truth;
    const p = k.pick('what number?', tries, { check: (a) => a === truth });
    if (p.answer === truth && p.verified && p.p_correct === 1) hits++;
  }
  assert.strictEqual(hits, N);
});

test('checker: a low top score is "not sure" (wonder list); hedge() says so', () => {
  const k = new C.Checker();
  const p = k.pick('why is the sky blue?', ['Rayleigh scattering of sunlight.', 'Because the ocean reflects it.', 'Ozone absorbs red light.', 'Dust in the air.'], {});
  assert.strictEqual(p.method, 'agreement'); assert.ok(p.p_correct < C.NOT_SURE); assert.strictEqual(p.notSure, true);
  const sure = k.pick('2+2', ['4', '4', '4', '5'], {});
  assert.strictEqual(sure.answer, '4'); assert.strictEqual(sure.notSure, false);
  assert.strictEqual(k.hedge('The sky is blue because of scattering.', 0.25), "I'm not sure, but the sky is blue because of scattering.");
  assert.strictEqual(k.hedge('Water boils at 100 C.', 0.9), 'Water boils at 100 C.');
  // all tries verified wrong -> not sure too
  assert.strictEqual(k.pick('q', ['1', '2'], { check: (a) => a === '3' }).notSure, true);
});

test('checker: ECE is correct on a hand-made example', () => {
  // bins of width 0.1: p=0.15 x4 (1 right) -> |0.15-0.25| = 0.10; p=0.85 x6 (6 right) -> |0.85-1| = 0.15
  // ECE = 0.4*0.10 + 0.6*0.15 = 0.13
  const pairs = [0.15, 0.15, 0.15, 0.15].map((p, i) => ({ p, y: i === 0 ? 1 : 0 })).concat(Array(6).fill(0).map(() => ({ p: 0.85, y: 1 })));
  const e = C.ece(pairs);
  assert.ok(Math.abs(e.ece - 0.13) < 1e-12, String(e.ece));
  assert.strictEqual(e.n, 10); assert.strictEqual(e.bins.length, 2);
  assert.strictEqual(C.ece([{ p: 0.75, y: 1 }, { p: 0.75, y: 1 }, { p: 0.75, y: 1 }, { p: 0.75, y: 0 }]).ece, 0, 'perfectly calibrated');
  assert.strictEqual(C.ece([]).ece, null);
  assert.strictEqual(C.ece([{ p: 1, y: 0 }]).ece, 1, 'p = 1 falls in the top bin');
});

test('checker: labels go to checker-labels.jsonl; (p, truth) pairs are logged when the truth arrives; report per method', () => {
  const dir = tmp(); const k = new C.Checker({ dir });
  k.label({ question: 'q1', answer: 'a', correct: true, p: 0.9, pMethod: 'self', method: 'executor', source: 'sandbox', truth: 'executor', kind: 'python' });
  k.label({ question: 'q2', answer: 'b', correct: false, p: 0.8, pMethod: 'self', method: 'executor', source: 'sandbox', truth: 'executor', kind: 'python' });
  const rows = fs.readFileSync(path.join(dir, 'checker-labels.jsonl'), 'utf8').trim().split('\n').map(JSON.parse);
  assert.strictEqual(rows.length, 2); assert.strictEqual(rows[1].correct, false); assert.strictEqual(rows[0].source, 'sandbox');
  // a claim's stated p, settled later by the truth check
  k.expect('Octopuses have three hearts.', 0.75, { method: 'agreement', kind: 'claim' });
  assert.strictEqual(new C.Checker({ dir }).settled('octopuses have three hearts', true).p, 0.75, 'the pending p survives a restart');
  assert.strictEqual(k.settled('never stated', true), null);
  const rep = new C.Checker({ dir }).report();
  assert.strictEqual(rep.overall.n, 3); assert.deepStrictEqual(Object.keys(rep.byMethod).sort(), ['agreement', 'self']);
  assert.match(new C.Checker({ dir }).reportLine(), /agreement 1 \(ECE 0\.25\) untested/);
});

test('checker: the learned slot is OFF by default and loads only when switched on AND its weights file exists', () => {
  const dir = tmp(); const file = path.join(dir, 'checker-head.json');
  const w = { version: 1, kind: 'logistic', dim: 3, w: [2, 0, 0], b: -1, model: 'nanbeige4.2-3b', layer: -1 };
  fs.writeFileSync(file, JSON.stringify(w));
  const off = new C.Checker({ dir });
  assert.strictEqual(off.learned.enabled, false); assert.strictEqual(off.learned.loaded(), false, 'off by default even with a file');
  assert.strictEqual(off.score('q', 'a', { hidden: [1, 0, 0], tries: ['a', 'b'] }).method, 'agreement');
  const noFile = new C.Checker({ dir: tmp(), learned: { enabled: true } });
  assert.strictEqual(noFile.learned.loaded(), false); assert.strictEqual(noFile.learned.why, 'no weights file');
  const on = new C.Checker({ dir, learned: { enabled: true } });
  assert.strictEqual(on.learned.loaded(), true);
  const s = on.score('q', 'a', { hidden: [1, 0, 0] });
  assert.strictEqual(s.method, 'learned'); assert.ok(Math.abs(s.p_correct - 1 / (1 + Math.exp(-1))) < 1e-12); assert.strictEqual(s.verified, false);
  assert.strictEqual(on.score('q', 'a', { hidden: [1, 0] }).method, 'none', 'wrong size: not used');
  assert.strictEqual(on.score('q', 'a', { hidden: [1, 0, 0], check: () => false }).method, 'executor', 'a verified method still outranks it');
  fs.writeFileSync(file, '{"version": 1, "kind": "logistic", "dim": 2, "w": [1]}');
  assert.strictEqual(new C.Checker({ dir, learned: { enabled: true } }).learned.why, 'bad weights file');
});

test('checker: K thinking-Mote tries -> the try whose claims agree most (or match a settled truth note); a lone claim is not sure', () => {
  const k = new C.Checker();
  const tries = [{ claims: ['Venus is the hottest planet.'], question: null }, { claims: ['Mercury is the hottest planet.'] }, { claims: ['The hottest planet is Venus.'] }, null];
  const p = k.pickThoughts('planets', tries, {});
  assert.strictEqual(p.method, 'agreement'); assert.strictEqual(p.index, 0, 'the claim two tries agree on');
  assert.strictEqual(p.p_correct, 0.5);
  const truth = { notes: [{ id: 'n', status: 'confirmed', text: 'Mercury is the hottest planet.' }] };   // (a fake note, for the test)
  const q = k.pickThoughts('planets', tries, { truth });
  assert.strictEqual(q.index, 1); assert.strictEqual(q.verified, true); assert.strictEqual(q.notSure, false);
  const lone = k.pickThoughts('x', [{ claims: ['A'] }, { claims: ['B'] }, { claims: ['C'] }, { claims: ['D'] }], {});
  assert.strictEqual(lone.notSure, true);
  assert.strictEqual(k.pickThoughts('x', [null, null], {}).method, 'none');
});
