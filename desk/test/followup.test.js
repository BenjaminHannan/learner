'use strict';
const test = require('node:test');
const assert = require('node:assert');
const { shouldFollowUp } = require('../src/followup');

const now = new Date(2026, 9, 28, 9, 30);
const base = { now, lastDay: '2026-10-27', hour: 9, front: true, busy: false, asleep: false, lastActivity: new Date(2026, 9, 27, 22, 0).getTime(), enabled: true };
test('follow-up: runs when Ben opens the chat on a new day', () => assert.strictEqual(shouldFollowUp(base), true));
test('follow-up: once per day, only in waking hours', () => {
  assert.strictEqual(shouldFollowUp({ ...base, lastDay: '2026-10-28' }), false);
  assert.strictEqual(shouldFollowUp({ ...base, hour: 6 }), false);
  assert.strictEqual(shouldFollowUp({ ...base, hour: 22 }), false);
});
test('follow-up: needs the chat in front, Glim idle and awake, the setting on, and an older thread', () => {
  for (const o of [{ front: false }, { busy: true }, { asleep: true }, { enabled: false }, { lastActivity: 0 }, { lastActivity: new Date(2026, 9, 28, 8, 0).getTime() }]) assert.strictEqual(shouldFollowUp({ ...base, ...o }), false, JSON.stringify(o));
});
