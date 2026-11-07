'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { splitEpisodes, splitByTime, correctionCandidates } = require('../src/night-learn/data');

test('episodes split on a gap and reject unordered time', () => {
  const events = [0, 100, 120101, 120102].map(timeMs => ({timeMs}));
  assert.deepEqual(splitEpisodes(events).map(e => e.length), [2, 2]);
  assert.throws(() => splitEpisodes([{timeMs: 2}, {timeMs: 1}]));
});
test('hold out the last fifth of elapsed day, including cutoff ties', () => {
  const rows = [0, 79, 80, 80, 100].map(timeMs => ({timeMs}));
  const result = splitByTime(rows, 0, 100);
  assert.equal(result.cutoffMs, 80);
  assert.deepEqual(result.train.map(r => r.timeMs), [0,79]);
  assert.deepEqual(result.held.map(r => r.timeMs), [80,80,100]);
  assert.throws(() => splitByTime([{timeMs:101}], 0, 100));
});
test('only eligible corrections are candidates and still require evidence verification', () => {
  const base = {action:{kind:'click'}, observation:'obs', evidence:'proof'};
  const items = correctionCandidates({schema:'hands-attempt/v1', attemptId:'a', corrections:[{...base,source:'ben'},{...base,source:'model'},{...base,source:'independently_verified', evidence:''}]});
  assert.equal(items.length, 1);
  assert.equal(items[0].weight, 3);
  assert.equal(items[0].verificationRequired, true);
});
