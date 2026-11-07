'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { score } = require('../src/night-learn/score');

function sample() {
  const train = [{ id: 'train', timeMs: 1 }];
  const held = Array.from({ length: 20 }, (_, i) => ({ id: `c${i}`, timeMs: 2 + i, kind: 'click', x: 0, y: 0 }));
  held.push({ id: 'k', timeMs: 22, kind: 'key', key: 'Enter' });
  const arm = () => Object.fromEntries(held.map(e => [e.id, e.kind === 'key' ? { key: 'Enter' } : { x: 0, y: 0 }]));
  const predictions = { old: arm(), candidate: arm(), noIntent: arm() };
  predictions.old.c0.x = 41;
  predictions.noIntent.c1.x = 41;
  return { train, held, predictions };
}
test('exactly five points over both controls passes, including a click at 40 pixels', () => {
  const s = sample(); s.predictions.candidate.c0.x = 40;
  const r = score(s);
  assert.equal(r.pass, true); assert.equal(r.counts.clickExamples, 20);
  assert.equal(r.rates.old.click, .95); assert.equal(r.rates.candidate.click, 1);
  assert.match(r.heldSha256, /^[a-f0-9]{64}$/);
});
test('a weak control comparison or worse keys fails', () => {
  let s = sample(); s.predictions.noIntent.c1.x = 0; assert.equal(score(s).pass, false);
  s = sample(); s.predictions.candidate.k.key = 'Tab'; assert.equal(score(s).pass, false);
});
test('rejects leakage, missing predictions and slices without key evidence', () => {
  let s = sample(); s.train[0].timeMs = 2; assert.throws(() => score(s), /later/);
  s = sample(); delete s.predictions.old.c0; assert.throws(() => score(s), /every held/);
  s = sample(); s.held.pop(); for (const p of Object.values(s.predictions)) delete p.k; assert.throws(() => score(s), /clicks and keys/);
});
