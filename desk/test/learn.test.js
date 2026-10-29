'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { parseLearnConfig, parseLearnRequest } = require('../src/learn');
test('Learn setup distinguishes cancellation, bounded, indefinite and unclear durations', () => {
  for (const text of ['stop', 'cancel', 'never mind', 'stop asking and just answer']) assert.equal(parseLearnConfig(text).cancel, true);
  for (const text of ['until 5pm', '3 motes', 'for a while', '2 motes for zero hours']) assert.ok(['missing', 'invalid'].includes(parseLearnConfig(text).lifetime), text);
  assert.deepEqual(parseLearnConfig('one mote for two hours, then stop them'), { cancel: false, count: 1, lifetime: 'finite', hours: 2 });
  assert.equal(parseLearnConfig('3 Motes, until I stop them').lifetime, 'forever');
  assert.equal(parseLearnConfig('1 mote for 30 minutes').hours, 0.5);
  assert.deepEqual(parseLearnRequest('go learn spreadsheets with 5 motes for 2 hours'), { topic: 'spreadsheets', cancel: false, count: 5, lifetime: 'finite', hours: 2 });
});

test('direct requests retain the topic when a duration includes a stop instruction', () => {
  assert.equal(parseLearnRequest('go learn chess with one mote for two hours, then stop them').topic, 'chess');
  assert.equal(parseLearnRequest('study chess until 5pm').topic, 'chess');
  assert.equal(parseLearnRequest('study chess until 5pm').lifetime, 'invalid');
});

test('real Learn setup flow cancels, clarifies, retains a count, and reports startup errors', () => {
  const { learnFlow } = require('../src/learn');
  const calls = [];
  let outcome = { ok: true, count: 1, topic: 'chess' };
  const start = (...args) => { calls.push(args); return outcome; };
  let state = learnFlow({ text: 'go learn chess', isAsk: true, start });
  assert.equal(state.pending.topic, 'chess');
  state = learnFlow({ pending: state.pending, text: 'until 5pm', start });
  assert.match(state.note, /still pending/); assert.equal(calls.length, 0);
  state = learnFlow({ pending: state.pending, text: 'one', start });
  assert.equal(state.pending.count, 1); assert.equal(calls.length, 0);
  state = learnFlow({ pending: state.pending, text: 'two hours, then stop them', start });
  assert.deepEqual(calls, [['chess', 1, 2]]); assert.equal(state.pending, null);
  assert.match(state.note, /started 1 Motes/); assert.match(state.note, /training has not been confirmed/);
  state = learnFlow({ text: 'go learn chess', isAsk: true, start });
  state = learnFlow({ pending: state.pending, text: 'stop', start });
  assert.equal(state.pending, null); assert.match(state.note, /cancelled/); assert.equal(calls.length, 1);
  outcome = { error: 'duplicate name' };
  state = learnFlow({ text: 'go learn chess for 1 hour', isAsk: true, start });
  assert.match(state.note, /could not start any Motes: duplicate name/); assert.match(state.note, /Do not research/);
  outcome = { ok: true, count: 1, topic: 'chess', error: 'too many Motes' };
  state = learnFlow({ text: 'go learn chess with 3 motes for 1 hour', isAsk: true, start });
  assert.match(state.note, /Only some started: too many Motes/);
  state = learnFlow({ pending: { topic: 'chess' }, text: 'what is the weather?', start });
  assert.equal(state.handled, false); assert.equal(state.pending, null);
  assert.equal(require('../src/learn').parseLearnConfig('1').count, 1);
});
